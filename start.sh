#!/bin/bash
# FastAPI को बैकग्राउंड में चलाएं
uvicorn api:app --host 0.0.0.0 --port $PORT &
# बॉट को चालू करें
python main.py
