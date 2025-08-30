from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient
import uuid
from fastapi.middleware.cors import CORSMiddleware
import logging
import math
import numpy as np

# Configure logging to ensure output in terminal
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.debug("Server starting...")

app = FastAPI()

# MongoDB connection
try:
    client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    client.admin.command('ping')  # Test connection
    logger.info("Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {str(e)}")
    raise Exception(f"MongoDB connection failed: {str(e)}")

db = client["hand_features_db"]
hand_data_collection = db["hand_data"]
user_data_collection = db["user_data"]

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HandData(BaseModel):
    landmarks: list
    confidence: float

class UserData(BaseModel):
    sessionId: str
    name: str
    age: int
    contact: str
    email: str
    address: str

def normalize_landmarks(landmarks):
    logger.debug(f"Normalizing landmarks: {landmarks}")
    try:
        landmarks_array = np.array(landmarks)
        mean = np.mean(landmarks_array, axis=0)
        std = np.std(landmarks_array, axis=0)
        normalized = (landmarks_array - mean) / (std + 1e-10)
        return normalized.tolist()
    except Exception as e:
        logger.error(f"Error normalizing landmarks: {str(e)}")
        raise

def calculate_similarity(landmarks1, landmarks2):
    if len(landmarks1) != len(landmarks2):
        logger.warning(f"Landmark length mismatch: {len(landmarks1)} vs {len(landmarks2)}")
        return float('inf')
    total_distance = 0
    for p1, p2 in zip(landmarks1, landmarks2):
        dist = sum((a - b) ** 2 for a, b in zip(p1, p2)) ** 0.5
        total_distance += dist
    similarity = total_distance / len(landmarks1)
    logger.debug(f"Calculated similarity: {similarity}")
    return similarity

@app.get("/api/health")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok"}

@app.post("/api/hand-recognition")
async def store_hand_features(data: HandData):
    logger.info(f"Received request for /api/hand-recognition with landmarks: {data.landmarks}")
    try:
        normalized_landmarks = normalize_landmarks(data.landmarks)
        
        cursor = hand_data_collection.find({})
        for doc in cursor:
            if 'landmarks' in doc:
                stored_landmarks = normalize_landmarks(doc['landmarks'])
                similarity = calculate_similarity(normalized_landmarks, stored_landmarks)
                logger.info(f"Comparing with stored landmarks: similarity = {similarity}")
                if similarity < 0.5:  # Relaxed threshold
                    registered = doc.get("registered", False)
                    return {"is_new_user": False, "message": "User exists", "similarity": similarity, "registered": registered}
        
        session_id = str(uuid.uuid4())
        hand_data_collection.insert_one({
            "landmarks": data.landmarks,
            "normalized_landmarks": normalized_landmarks,
            "confidence": data.confidence,
            "session_id": session_id,
            "registered": False
        })
        logger.info(f"Stored new hand data with session_id: {session_id}")
        return {"is_new_user": True, "session_id": session_id, "message": "Hand features stored", "registered": False}
    except Exception as e:
        logger.error(f"Error in hand-recognition: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/api/register-user")
async def register_user(data: UserData):
    logger.info(f"Received request for /api/register-user with sessionId: {data.sessionId}")
    try:
        if not hand_data_collection.find_one({"session_id": data.sessionId}):
            logger.error("Session ID not found")
            raise HTTPException(status_code=404, detail="Session ID not found")
        user_data_collection.insert_one(data.dict())
        hand_data_collection.update_one(
            {"session_id": data.sessionId},
            {"$set": {"registered": True}}
        )
        logger.info("Registration successful")
        return {"message": "Registration successful"}
    except Exception as e:
        logger.error(f"Error in register-user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))