<<<<<<< HEAD
# Smart Med Assist - Complete System

A complete biometric healthcare kiosk system with hand recognition, user registration, and appointment booking.

## 🎯 Features

- **Biometric Hand Recognition** - MediaPipe-powered hand detection and user authentication
- **QR Code Registration** - Mobile-friendly user registration via QR code scanning
- **Virtual Keyboard Registration** - Touch-based registration interface
- **Appointment Booking** - Complete scheduling system with email confirmations
- **User Dashboard** - Modern interface for all services
- **Email Notifications** - Automated appointment confirmations
- **Responsive Design** - Works on all devices and screen sizes
- **Touchless Interface** - Optimized for kiosk use

## 📁 Project Structure

```
smart-med-assist/
├── backend/
│   ├── server.py              # FastAPI backend server
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Environment variables
└── frontend/
    ├── node_modules
    ├── public/
    │   └── index.html         # Main HTML file
    ├── src/
    │   ├── App.js             # Main React application
    │   ├── App.css            # Application styles
    │   ├── index.js           # React entry point
    │   └── index.css          # Base styles
    ├── package.json           # Node.js dependencies
    └── README.md              # This file
    ├── start_app.bat
    └──package_lock.json
```

## 🚀 Installation & Setup

### Prerequisites

- Python 3.8+ 
- Node.js 16+
- MongoDB (local or cloud)
- Gmail account (for email notifications)

### Backend Setup

1. **Navigate to backend directory:**
```bash
cd backend
```

2. **Create virtual environment:**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
Edit `backend/.env`:
```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="smart_med_assist"
CORS_ORIGINS="*"
SMTP_EMAIL="your_email@gmail.com"
SMTP_PASSWORD="your_app_password"
```

**Gmail Setup for Email:**
- Enable 2-Factor Authentication in Gmail
- Generate App Password: Google Account → Security → App passwords
- Use the app password in SMTP_PASSWORD

5. **Start MongoDB:**
```bash
# If using local MongoDB
mongod

# Or use MongoDB Atlas (cloud)
```

6. **Run backend server:**
```bash
python server.py
```
Server will start at `http://localhost:8000`

### Frontend Setup

1. **Navigate to frontend directory:**
```bash
cd frontend
```

2. **Install dependencies:**
```bash
npm install
```

3. **Start development server:**
```bash
npm start
```
Application will open at `http://localhost:3000`

## 🔧 Configuration

### Environment Variables

**Backend (.env):**
- `MONGO_URL`: MongoDB connection string
- `DB_NAME`: Database name
- `CORS_ORIGINS`: Allowed origins (use "*" for development)
- `SMTP_EMAIL`: Gmail address for sending emails
- `SMTP_PASSWORD`: Gmail app password

**Frontend:**
- Proxy is configured in `package.json` to connect to backend
- MediaPipe CDN is used for hand detection models

### Camera Permissions

The application requires camera access for hand detection:
1. Allow camera permissions when prompted
2. Ensure HTTPS in production for camera access
3. Test camera functionality in supported browsers (Chrome, Firefox, Safari)

## 📱 Usage

### For Kiosk Operation:

1. **System Initialization:**
   - Camera initializes and loads hand detection models
   - System shows ready status when fully loaded

2. **User Authentication:**
   - Place hand in front of camera
   - System detects and processes hand landmarks
   - Existing users are automatically recognized
   - New users are prompted for registration

3. **Registration Process:**
   - Choose QR code registration (mobile-friendly)
   - Or use virtual keyboard for direct input
   - Complete registration form
   - System saves biometric data for future recognition

4. **Dashboard & Services:**
   - Access appointment booking
   - View scheduled appointments
   - Navigate hospital services
   - Profile management

### For Mobile Registration:

1. Scan QR code displayed on kiosk
2. Fill registration form on mobile device
3. Submit to complete registration
4. Return to kiosk for biometric authentication

## 🛠️ Development

### Adding New Features

**Backend (FastAPI):**
```python
@api_router.post("/new-endpoint")
async def new_feature(request: RequestModel):
    # Implementation
    return {"result": "data"}
```

**Frontend (React):**
```javascript
const NewComponent = () => {
    // Component logic
    return <div>New Feature</div>;
};
```

### Database Schema

**Users Collection:**
```javascript
{
  id: "uuid",
  name: "string",
  age: "number",
  contact: "string", 
  email: "string",
  address: "string",
  hand_features: {
    landmarks: [[x,y,z], ...], // 21 landmarks
    confidence: "number"
  },
  is_registered: "boolean",
  created_at: "datetime"
}
```

**Appointments Collection:**
```javascript
{
  id: "uuid",
  user_id: "string",
  department: "string",
  preferred_date: "string",
  preferred_time: "string", 
  reason: "string",
  status: "scheduled|completed|cancelled",
  created_at: "datetime"
}
```

## 🔐 Security Features

- **Biometric Data Protection:** Hand landmarks stored securely
- **Session Management:** Temporary sessions for registration
- **Data Encryption:** All API communications
- **Access Control:** User-based data isolation
- **Privacy Compliance:** GDPR-ready data handling

## 📊 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/hand-recognition` | Process hand landmarks for user recognition |
| POST | `/api/register-user` | Complete user registration |
| GET | `/api/user/{user_id}` | Get user details |
| POST | `/api/appointment` | Book new appointment |
| GET | `/api/appointments/{user_id}` | Get user appointments |
| GET | `/api/health` | System health check |

## 🚀 Production Deployment

### Backend Deployment

1. **Use production WSGI server:**
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker server:app
```

2. **Environment setup:**
   - Use production MongoDB
   - Configure proper CORS origins
   - Set up SSL certificates
   - Use environment-specific configs

3. **Docker deployment:**
```dockerfile
FROM python:3.9
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "server:app"]
```

### Frontend Deployment

1. **Build for production:**
```bash
npm run build
```

2. **Deploy to web server:**
   - Upload `build/` folder to web server
   - Configure nginx/Apache for SPA routing
   - Set up HTTPS for camera access

## 🛡️ Troubleshooting

### Common Issues:

**Camera not working:**
- Check browser permissions
- Ensure HTTPS in production
- Verify camera hardware

**Hand detection fails:**
- Ensure good lighting
- Check MediaPipe model loading
- Verify network connectivity

**Email not sending:**
- Check Gmail app password
- Verify SMTP configuration
- Check network firewall

**Database connection issues:**
- Verify MongoDB is running
- Check connection string
- Confirm network access

## 📞 Support

For technical support or questions:
- Check troubleshooting section
- Review API documentation
- Test with provided examples
- Verify all dependencies are installed

## 📄 License

This project is provided as a complete working example of a Smart Medical Assistant system. Use and modify as needed for your healthcare facility.

---

**Smart Med Assist** - Revolutionizing healthcare through touchless technology 🏥✋
=======
# Here are your Instructions
>>>>>>> 3015558cad3875b9710a34cf5cc51466e9c67e34
