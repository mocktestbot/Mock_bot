# database.py
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

# --- User Management ---
def register_user(user_id, first_name, username):
    if not users_col.find_one({"user_id": user_id}):
        users_col.insert_one({"user_id": user_id, "first_name": first_name, "username": username, "join_date": datetime.now(), "is_banned": False, "total_tests_attempted": 0})

def check_banned(user_id):
    user = users_col.find_one({"user_id": user_id})
    return user.get("is_banned", False) if user else False

def update_ban_status(user_id, status: bool):
    users_col.update_one({"user_id": user_id}, {"$set": {"is_banned": status}})

# --- Category & Test Management ---
def add_category(exam_name, subject_name):
    categories_col.update_one({"exam_name": exam_name}, {"$addToSet": {"subjects": subject_name}}, upsert=True)

def get_all_exams():
    return [doc['exam_name'] for doc in categories_col.find()]

def get_subjects_by_exam(exam_name):
    doc = categories_col.find_one({"exam_name": exam_name})
    return doc.get("subjects", []) if doc else []

def save_test(test_id, exam_name, subject_name, test_name, pos_mark, neg_mark, cutoff, questions_data):
    tests_col.insert_one({"test_id": test_id, "exam_name": exam_name, "subject_name": subject_name, "test_name": test_name, "positive_mark": pos_mark, "negative_mark": neg_mark, "cutoff": cutoff, "is_public": False, "questions": questions_data})

def make_test_public(test_id):
    tests_col.update_one({"test_id": test_id}, {"$set": {"is_public": True}})

def get_public_tests(exam_name, subject_name):
    return list(tests_col.find({"exam_name": exam_name, "subject_name": subject_name, "is_public": True}, {"_id": 0, "test_id": 1, "test_name": 1}))

# --- Delete (Manage) Features ---
def delete_exam(exam_name):
    categories_col.delete_one({"exam_name": exam_name})
    tests_col.delete_many({"exam_name": exam_name})

def delete_subject(exam_name, subject_name):
    categories_col.update_one({"exam_name": exam_name}, {"$pull": {"subjects": subject_name}})
    tests_col.delete_many({"exam_name": exam_name, "subject_name": subject_name})

def delete_test(test_id):
    tests_col.delete_one({"test_id": test_id})

# --- Stats ---
def get_bot_stats():
    return {"total_users": users_col.count_documents({}), "banned_users": users_col.count_documents({"is_banned": True}), "total_tests": tests_col.count_documents({"is_public": True}), "total_attempts": scores_col.count_documents({})}
