from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import database

app = FastAPI()

# यह कोड आपकी वेबसाइट (GitHub) को डेटा लेने की परमिशन देता है
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "API is Live!"}

@app.get("/get_test/{test_id}")
def get_test(test_id: str):
    # डेटाबेस से टेस्ट खोजना
    test_data = database.tests_col.find_one({"test_id": test_id}, {"_id": 0})
    
    if not test_data:
        raise HTTPException(status_code=404, detail="Test not found")
        
    return test_data
