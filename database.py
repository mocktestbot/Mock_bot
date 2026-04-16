# database.py
import pymongo
from datetime import datetime
from config import MONGO_URI

# MongoDB से कनेक्शन
try:
    client = pymongo.MongoClient(MONGO_URI)
    db = client['mock_test_db']
    
    # कलेक्शन्स (टेबल्स)
    users_col = db['users']
    tests_col = db['tests']
    scores_col = db['scores']
    categories_col = db['categories']
    print("✅ Database Connected Successfully!")
except Exception as e:
    print(f"❌ Database Connection Error: {e}")

# ==========================================
# यूज़र मैनेजमेंट (User Management)
# ==========================================

def register_user(user_id, first_name, username):
    """नया छात्र जुड़ने पर डेटाबेस में सेव करना"""
    try:
        user = users_col.find_one({"user_id": user_id})
        if not user:
            users_col.insert_one({
                "user_id": user_id,
                "first_name": first_name,
                "username": username,
                "join_date": datetime.now(),
                "is_banned": False,
                "total_tests_attempted": 0
            })
            return True
        return False
    except Exception as e:
        print(f"Error in register_user: {e}")
        return False

def check_banned(user_id):
    """चेक करना कि छात्र बैन तो नहीं है"""
    try:
        user = users_col.find_one({"user_id": user_id})
        if user and user.get("is_banned", False):
            return True
        return False
    except:
        return False

def update_ban_status(user_id, status: bool):
    """छात्र को बैन या अनबैन करना"""
    users_col.update_one({"user_id": user_id}, {"$set": {"is_banned": status}})

# ==========================================
# टेस्ट और कैटेगरी मैनेजमेंट (Test Management)
# ==========================================

def add_category(exam_name, subject_name):
    """नई परीक्षा और विषय जोड़ना"""
    categories_col.update_one(
        {"exam_name": exam_name},
        {"$addToSet": {"subjects": subject_name}},
        upsert=True
    )

def get_all_exams():
    """सभी परीक्षाओं की लिस्ट निकालना"""
    return [doc['exam_name'] for doc in categories_col.find()]

def get_subjects_by_exam(exam_name):
    """परीक्षा के अनुसार विषयों की लिस्ट निकालना"""
    doc = categories_col.find_one({"exam_name": exam_name})
    return doc.get("subjects", []) if doc else []

def save_test(test_id, exam_name, subject_name, test_name, pos_mark, neg_mark, cutoff, questions_data):
    """JSON फाइल से आए प्रश्नों को डेटाबेस में सेव करना"""
    tests_col.insert_one({
        "test_id": test_id,
        "exam_name": exam_name,
        "subject_name": subject_name,
        "test_name": test_name,
        "positive_mark": pos_mark,
        "negative_mark": neg_mark,
        "cutoff": cutoff,
        "is_public": False, # शुरुआत में प्राइवेट रहेगा (Preview Mode के लिए)
        "upload_date": datetime.now(),
        "questions": questions_data
    })

def make_test_public(test_id):
    """चेक करने के बाद टेस्ट को पब्लिक करना"""
    tests_col.update_one({"test_id": test_id}, {"$set": {"is_public": True}})

def get_tests(exam_name, subject_name, only_public=True):
    """छात्रों को दिखाने के लिए टेस्ट लिस्ट निकालना"""
    query = {"exam_name": exam_name, "subject_name": subject_name}
    if only_public:
        query["is_public"] = True
    return list(tests_col.find(query, {"_id": 0, "test_id": 1, "test_name": 1}))

# ==========================================
# स्कोर और स्टैट्स (Scores & Stats)
# ==========================================

def get_bot_stats():
    """एडमिन डैशबोर्ड के लिए लाइव आंकड़े निकालना"""
    total_users = users_col.count_documents({})
    banned_users = users_col.count_documents({"is_banned": True})
    total_tests = tests_col.count_documents({"is_public": True})
    total_attempts = scores_col.count_documents({})
    
    return {
        "total_users": total_users,
        "banned_users": banned_users,
        "total_tests": total_tests,
        "total_attempts": total_attempts
    }
