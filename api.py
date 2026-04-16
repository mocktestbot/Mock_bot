# api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pymongo
import config

app = FastAPI()

# CORS इनेबल करना (ताकि GitHub Pages इस API से डेटा ले सके)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # प्रोडक्शन में यहाँ अपनी गिटहब वेबसाइट का लिंक डालें
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB कनेक्शन
client = pymongo.MongoClient(config.MONGO_URI)
db = client['mock_test_db']
tests_col = db['tests']
scores_col = db['scores']

@app.get("/")
def read_root():
    return {"status": "API is running fast and smooth! 🚀"}

@app.get("/api/test/{test_id}")
def get_test_data(test_id: str):
    """HTML पेज को टेस्ट का डेटा भेजना"""
    test_data = tests_col.find_one({"test_id": test_id}, {"_id": 0})
    
    if not test_data:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # अगर टेस्ट पब्लिक नहीं है, तो सिर्फ एडमिन के लिए चलेगा (Preview Mode)
    # यहाँ हम समय सीमा भी सेट कर सकते हैं (अभी 15 प्रश्न = 15 मिनट डिफ़ॉल्ट मान लेते हैं)
    time_limit_minutes = len(test_data["questions"]) * 1  # 1 मिनट प्रति प्रश्न

    return {
        "test_name": test_data["test_name"],
        "positive_mark": test_data["positive_mark"],
        "negative_mark": test_data["negative_mark"],
        "cutoff": test_data["cutoff"],
        "time_limit": time_limit_minutes,
        "questions": test_data["questions"]
    }

# FastAPI सर्वर को शुरू करने का कमांड (Procfile या Render के लिए)
# uvicorn api:app --host 0.0.0.0 --port 10000
