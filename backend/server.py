from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
from datetime import datetime, timezone
import os
import uuid
import qrcode
import base64
import io
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from pathlib import Path
import logging
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app
app = FastAPI(title="Smart Med Assist API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = os.environ.get('SMTP_EMAIL')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')

# Pydantic Models
class HandFeatures(BaseModel):
    landmarks: List[List[float]]  # 21 landmarks with x, y, z coordinates
    confidence: float

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None
    age: Optional[int] = None
    contact: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    hand_features: Optional[HandFeatures] = None
    session_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_registered: bool = False

class UserRegistration(BaseModel):
    name: str
    age: int
    contact: str
    email: EmailStr
    address: str
    session_id: str

class HandRecognitionRequest(BaseModel):
    landmarks: List[List[float]]
    confidence: float

class HandRecognitionResponse(BaseModel):
    user_id: Optional[str]
    is_new_user: bool
    session_id: Optional[str]
    qr_code: Optional[str] = None

class QRRegistrationSession(BaseModel):
    session_id: str
    hand_features: HandFeatures
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime

class Appointment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    department: str
    preferred_date: str
    preferred_time: str
    reason: str
    status: str = "scheduled"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AppointmentRequest(BaseModel):
    user_id: str
    department: str
    preferred_date: str
    preferred_time: str
    reason: str

# Utility functions
def calculate_hand_similarity(landmarks1: List[List[float]], landmarks2: List[List[float]]) -> float:
    """Calculate similarity between two hand landmark sets"""
    if len(landmarks1) != len(landmarks2):
        return 0.0
    
    total_distance = 0.0
    for i in range(len(landmarks1)):
        for j in range(len(landmarks1[i])):
            total_distance += abs(landmarks1[i][j] - landmarks2[i][j])
    
    # Convert distance to similarity score (0-1)
    max_distance = len(landmarks1) * len(landmarks1[0])
    similarity = max(0, 1 - (total_distance / max_distance))
    return similarity

def generate_qr_code(data: str) -> str:
    """Generate QR code and return as base64 string"""
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, 'PNG')  # Remove format parameter
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        logging.error(f"QR code generation failed: {e}")
        return ""

async def send_appointment_email(user_email: str, user_name: str, appointment_details: dict):
    """Send appointment confirmation email"""
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = "Appointment Confirmation - Smart Med Assist"
        message["From"] = SMTP_EMAIL
        message["To"] = user_email

        html = f"""
        <html>
          <body>
            <h2>Appointment Confirmation</h2>
            <p>Dear {user_name},</p>
            <p>Your appointment has been successfully scheduled:</p>
            <ul>
              <li><strong>Department:</strong> {appointment_details['department']}</li>
              <li><strong>Date:</strong> {appointment_details['preferred_date']}</li>
              <li><strong>Time:</strong> {appointment_details['preferred_time']}</li>
              <li><strong>Reason:</strong> {appointment_details['reason']}</li>
            </ul>
            <p>Please arrive 15 minutes before your scheduled time.</p>
            <p>Thank you for choosing Smart Med Assist!</p>
          </body>
        </html>
        """

        part = MIMEText(html, "html")
        message.attach(part)

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, user_email, message.as_string())
            
        return True
    except Exception as e:
        logging.error(f"Email sending failed: {e}")
        return False

# API Routes
@api_router.post("/hand-recognition", response_model=HandRecognitionResponse)
async def recognize_hand(request: HandRecognitionRequest):
    """Recognize hand features and return user info or new user session"""
    try:
        # Search for existing user with similar hand features
        users = await db.users.find({"is_registered": True}).to_list(None)
        
        best_match = None
        best_similarity = 0.0
        similarity_threshold = 0.85  # Adjust based on testing
        
        for user in users:
            if user.get('hand_features'):
                similarity = calculate_hand_similarity(
                    request.landmarks,
                    user['hand_features']['landmarks']
                )
                if similarity > best_similarity and similarity > similarity_threshold:
                    best_similarity = similarity
                    best_match = user
        
        if best_match:
            # Existing user recognized
            return HandRecognitionResponse(
                user_id=best_match['id'],
                is_new_user=False,
                session_id=None
            )
        else:
            # New user - create temporary session
            session_id = str(uuid.uuid4())
            expires_at = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
            
            qr_session = QRRegistrationSession(
                session_id=session_id,
                hand_features=HandFeatures(
                    landmarks=request.landmarks,
                    confidence=request.confidence
                ),
                expires_at=expires_at
            )
            
            await db.qr_sessions.insert_one(qr_session.dict())
            
            # Generate QR code for registration
            registration_url = f"https://biometric-checkin.preview.emergentagent.com/register/{session_id}"
            qr_code_data = generate_qr_code(registration_url)
            
            return HandRecognitionResponse(
                user_id=None,
                is_new_user=True,
                session_id=session_id,
                qr_code=qr_code_data
            )
            
    except Exception as e:
        logging.error(f"Hand recognition error: {e}")
        raise HTTPException(status_code=500, detail="Hand recognition failed")

@api_router.post("/register-user")
async def register_user(registration: UserRegistration):
    """Complete user registration with QR code session"""
    try:
        # Get QR session
        qr_session = await db.qr_sessions.find_one({"session_id": registration.session_id})
        if not qr_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if session is expired
        expires_at = qr_session['expires_at']
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        elif expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=400, detail="Session expired")
        
        # Create new user
        user = User(
            name=registration.name,
            age=registration.age,
            contact=registration.contact,
            email=registration.email,
            address=registration.address,
            hand_features=HandFeatures(**qr_session['hand_features']),
            is_registered=True
        )
        
        await db.users.insert_one(user.dict())
        
        # Clean up session
        await db.qr_sessions.delete_one({"session_id": registration.session_id})
        
        return {"message": "User registered successfully", "user_id": user.id}
        
    except Exception as e:
        logging.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@api_router.post("/virtual-register")
async def virtual_keyboard_register(user_data: dict, session_id: str):
    """Register user via virtual keyboard input"""
    try:
        # Get QR session for hand features
        qr_session = await db.qr_sessions.find_one({"session_id": session_id})
        if not qr_session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Create new user
        user = User(
            name=user_data.get('name'),
            age=user_data.get('age'),
            contact=user_data.get('contact'),
            email=user_data.get('email'),
            address=user_data.get('address'),
            hand_features=HandFeatures(**qr_session['hand_features']),
            is_registered=True
        )
        
        await db.users.insert_one(user.dict())
        
        # Clean up session
        await db.qr_sessions.delete_one({"session_id": session_id})
        
        return {"message": "User registered successfully", "user_id": user.id}
        
    except Exception as e:
        logging.error(f"Virtual registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@api_router.get("/user/{user_id}")
async def get_user(user_id: str):
    """Get user details"""
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Remove MongoDB ObjectId to avoid serialization issues
    if '_id' in user:
        del user['_id']
    
    return user

@api_router.post("/appointment")
async def book_appointment(appointment_req: AppointmentRequest):
    """Book an appointment"""
    try:
        # Get user details
        user = await db.users.find_one({"id": appointment_req.user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create appointment
        appointment = Appointment(
            user_id=appointment_req.user_id,
            department=appointment_req.department,
            preferred_date=appointment_req.preferred_date,
            preferred_time=appointment_req.preferred_time,
            reason=appointment_req.reason
        )
        
        await db.appointments.insert_one(appointment.dict())
        
        # Send confirmation email
        if user.get('email'):
            appointment_details = {
                'department': appointment_req.department,
                'preferred_date': appointment_req.preferred_date,
                'preferred_time': appointment_req.preferred_time,
                'reason': appointment_req.reason
            }
            
            email_sent = await send_appointment_email(
                user['email'],
                user['name'],
                appointment_details
            )
            
            return {
                "message": "Appointment booked successfully",
                "appointment_id": appointment.id,
                "email_sent": email_sent
            }
        
        return {
            "message": "Appointment booked successfully",
            "appointment_id": appointment.id,
            "email_sent": False
        }
        
    except Exception as e:
        logging.error(f"Appointment booking error: {e}")
        raise HTTPException(status_code=500, detail="Appointment booking failed")

@api_router.get("/appointments/{user_id}")
async def get_user_appointments(user_id: str):
    """Get user appointments"""
    appointments = await db.appointments.find({"user_id": user_id}).to_list(None)
    
    # Remove MongoDB ObjectId to avoid serialization issues
    for appointment in appointments:
        if '_id' in appointment:
            del appointment['_id']
    
    return appointments

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()