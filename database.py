import pymongo
from datetime import datetime
import config

try:
    client = pymongo.MongoClient(config.MONGO_URI)
    db = client['mock_test_db']
    users_col = db['users']
    tests_col = db['tests']
    scores_col = db['scores']
    categories_col = db['categories']
    print("✅ Database Connected Successfully!")
except Exception as e:
    print(f"❌ DB Error: {e}")

def register_user(user_id, first_name, username):
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({"user_id": user_id, "first_name": first_name, "username": username, "join_date": datetime.now(), "is_banned": False, "total_tests_attempted": 0})
        return True 
    return False 

def check_banned(user_id):
    user = users_col.find_one({"user_id": user_id})
    return user.get("is_banned", False) if user else False

def update_ban_status(user_id, status: bool):
    users_col.update_one({"user_id": user_id}, {"$set": {"is_banned": status}})

def add_category(exam_name, subject_name):
    categories_col.update_one({"exam_name": exam_name}, {"$addToSet": {"subjects": subject_name}}, upsert=True)

def get_all_exams():
    return [doc['exam_name'] for doc in categories_col.find()]

def get_subjects_by_exam(exam_name):
    doc = categories_col.find_one({"exam_name": exam_name})
    return doc.get("subjects", []) if doc else []

def save_test(test_id, exam_name, subject_name, test_name, pos_mark, neg_mark, cutoff, time_limit, questions_data):
    tests_col.insert_one({
        "test_id": test_id, "exam_name": exam_name, "subject_name": subject_name, 
        "test_name": test_name, "positive_mark": pos_mark, "negative_mark": neg_mark, 
        "cutoff": cutoff, "time_limit": time_limit, "is_public": False, "questions": questions_data
    })

def make_test_public(test_id):
    tests_col.update_one({"test_id": test_id}, {"$set": {"is_public": True}})

def get_test_details(test_id):
    return tests_col.find_one({"test_id": test_id})

def get_public_tests(exam_name, subject_name):
    return list(tests_col.find({"exam_name": exam_name, "subject_name": subject_name, "is_public": True}, {"_id": 0, "test_id": 1, "test_name": 1}))

def delete_exam(exam_name):
    categories_col.delete_one({"exam_name": exam_name})
    tests_col.delete_many({"exam_name": exam_name})

def delete_subject(exam_name, subject_name):
    categories_col.update_one({"exam_name": exam_name}, {"$pull": {"subjects": subject_name}})
    tests_col.delete_many({"exam_name": exam_name, "subject_name": subject_name})

def delete_test(test_id):
    tests_col.delete_one({"test_id": test_id})

def get_bot_stats():
    return {"total_users": users_col.count_documents({}), "banned_users": users_col.count_documents({"is_banned": True}), "total_tests": tests_col.count_documents({"is_public": True}), "total_attempts": scores_col.count_documents({})}

def get_all_users():
    return [user['user_id'] for user in users_col.find({}, {"_id": 0, "user_id": 1})]

def get_user_info(user_id):
    return users_col.find_one({"user_id": user_id}, {"_id": 0})

# ==========================================
# 📊 स्कोरकार्ड और स्मार्ट लीडरबोर्ड (Fixed)
# ==========================================
def save_score(user_id, first_name, test_id, test_name, score, accuracy):
    t_info = get_test_details(test_id)
    exam_name = t_info['exam_name'] if t_info else "General"
    subject_name = t_info['subject_name'] if t_info else "General"

    existing = scores_col.find_one({"user_id": user_id, "test_id": test_id})
    is_first_attempt = False if existing else True

    scores_col.insert_one({
        "user_id": user_id, "first_name": first_name, "test_id": test_id, "test_name": test_name, 
        "exam_name": exam_name, "subject_name": subject_name, "score": score, 
        "accuracy": accuracy, "is_first_attempt": is_first_attempt, "date": datetime.now()
    })
    if is_first_attempt:
        users_col.update_one({"user_id": user_id}, {"$inc": {"total_tests_attempted": 1}})

def get_attempted_exams(user_id):
    return scores_col.distinct("exam_name", {"user_id": user_id})

def get_attempted_subjects(user_id, exam_name):
    return scores_col.distinct("subject_name", {"user_id": user_id, "exam_name": exam_name})

def get_attempted_tests(user_id, exam_name, subject_name):
    tests = scores_col.find({"user_id": user_id, "exam_name": exam_name, "subject_name": subject_name}).sort("date", -1)
    unique_tests = {}
    for t in tests:
        if t['test_id'] not in unique_tests: unique_tests[t['test_id']] = t
    return list(unique_tests.values())

def get_test_scorecard(user_id, test_id):
    return scores_col.find_one({"user_id": user_id, "test_id": test_id}, sort=[("date", -1)])

def get_smart_leaderboard(user_id):
    pipeline = [
        {"$match": {"is_first_attempt": True}},
        {"$group": {"_id": "$user_id", "first_name": {"$first": "$first_name"}, "total_score": {"$sum": "$score"}}},
        {"$sort": {"total_score": -1}}
    ]
    all_users = list(scores_col.aggregate(pipeline))
    
    top_10 = all_users[:10]
    user_rank = None
    user_data = None
    
    for i, res in enumerate(all_users):
        if res["_id"] == user_id:
            user_rank = i + 1
            user_data = res
            break
            
    return top_10, user_rank, user_data
