from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import database

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ScoreData(BaseModel):
    user_id: int
    first_name: str
    test_id: str
    test_name: str
    score: float
    accuracy: str

@app.get("/")
def read_root(): return {"status": "API Live"}

@app.get("/get_test/{test_id}")
def get_test(test_id: str):
    t = database.tests_col.find_one({"test_id": test_id}, {"_id": 0})
    if not t: raise HTTPException(status_code=404, detail="Test not found")
    return t

@app.post("/submit_score")
def submit_score(data: ScoreData):
    database.save_score(data.user_id, data.first_name, data.test_id, data.test_name, data.score, data.accuracy)
    return {"status": "success"}
