import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useParams, useLocation } from 'react-router-dom';
import axios from 'axios';
import { HandLandmarker, FilesetResolver, DrawingUtils } from '@mediapipe/tasks-vision';
import QRCode from 'react-qr-code';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Custom hook for MediaPipe hand detection
const useHandDetection = () => {
  const [handLandmarker, setHandLandmarker] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const initializeHandLandmarker = async () => {
      try {
        const vision = await FilesetResolver.forVisionTasks(
          "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm"
        );
        
        const landmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
            delegate: "GPU"
          },
          runningMode: "VIDEO",
          numHands: 1,
          minHandDetectionConfidence: 0.7,
          minHandPresenceConfidence: 0.7,
          minTrackingConfidence: 0.5
        });
        
        setHandLandmarker(landmarker);
        setIsLoading(false);
      } catch (err) {
        console.error('Error initializing hand landmarker:', err);
        setError(err.message);
        setIsLoading(false);
      }
    };

    initializeHandLandmarker();
  }, []);

  return { handLandmarker, isLoading, error };
};

// Welcome Screen Component
const WelcomeScreen = () => {
  const navigate = useNavigate();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const { handLandmarker, isLoading } = useHandDetection();
  
  const [cameraReady, setCameraReady] = useState(false);
  const [handDetected, setHandDetected] = useState(false);
  const [processingGesture, setProcessingGesture] = useState(false);
  const [lastDetectionTime, setLastDetectionTime] = useState(0);
  const [detectionResults, setDetectionResults] = useState(null);
  
  // Initialize camera
  useEffect(() => {
    const initCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { 
            width: 1280, 
            height: 720,
            facingMode: 'user'
          }
        });
        
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => {
            setCameraReady(true);
          };
        }
      } catch (error) {
        console.error('Error accessing camera:', error);
      }
    };

    initCamera();
  }, []);

  // Hand detection loop
  useEffect(() => {
    let animationId;
    
    const detectHands = () => {
      if (handLandmarker && videoRef.current && cameraReady && canvasRef.current) {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        
        // Set canvas dimensions
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Detect hand landmarks
        const now = performance.now();
        const results = handLandmarker.detectForVideo(video, now);
        
        if (results.landmarks && results.landmarks.length > 0) {
          setHandDetected(true);
          setDetectionResults(results);
          setLastDetectionTime(now);
          
          // Draw hand landmarks
          const drawingUtils = new DrawingUtils(ctx);
          for (const landmarks of results.landmarks) {
            drawingUtils.drawConnectors(landmarks, HandLandmarker.HAND_CONNECTIONS, {
              color: "#00FF00",
              lineWidth: 2
            });
            drawingUtils.drawLandmarks(landmarks, { color: "#FF0000", lineWidth: 1 });
          }
          
          // Auto-process after 2 seconds of stable detection
          if (now - lastDetectionTime > 2000 && !processingGesture) {
            processHandForRecognition(results);
          }
        } else {
          setHandDetected(false);
          if (now - lastDetectionTime > 1000) {
            setDetectionResults(null);
          }
        }
      }
      
      animationId = requestAnimationFrame(detectHands);
    };
    
    if (handLandmarker && cameraReady) {
      detectHands();
    }
    
    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, [handLandmarker, cameraReady, lastDetectionTime, processingGesture]);

  const processHandForRecognition = async (results) => {
    if (processingGesture || !results.landmarks || results.landmarks.length === 0) return;
    
    setProcessingGesture(true);
    
    try {
      const landmarks = results.landmarks[0];
      const confidence = results.handednesses?.[0]?.[0]?.score || 0.8;
      
      const response = await axios.post(`${API}/hand-recognition`, {
        landmarks: landmarks.map(landmark => [landmark.x, landmark.y, landmark.z]),
        confidence: confidence
      });
      
      if (response.data.is_new_user) {
        navigate('/registration', { 
          state: { 
            sessionId: response.data.session_id,
            qrCode: response.data.qr_code 
          }
        });
      } else {
        navigate('/dashboard', { 
          state: { userId: response.data.user_id }
        });
      }
      
    } catch (error) {
      console.error('Hand recognition failed:', error);
      setProcessingGesture(false);
    }
  };

  if (isLoading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <p>Initializing Smart Med Assist...</p>
      </div>
    );
  }

  return (
    <div className="welcome-screen">
      <div className="header">
        <h1>Smart Med Assist</h1>
        <p className="subtitle">Touchless Hospital Kiosk System</p>
      </div>
      
      <div className="camera-section">
        <div className="video-container">
          <video 
            ref={videoRef}
            autoPlay
            playsInline
            className="camera-feed"
          />
          <canvas 
            ref={canvasRef}
            className="hand-overlay"
          />
        </div>
        
        <div className="instructions">
          {!cameraReady ? (
            <p>Initializing camera...</p>
          ) : !handDetected ? (
            <p>Please place your hand in front of the camera</p>
          ) : processingGesture ? (
            <p>Processing... Please hold still</p>
          ) : (
            <p>Hand detected! Hold steady for recognition...</p>
          )}
        </div>
        
        <div className="status-indicators">
          <div className={`status-indicator ${cameraReady ? 'active' : ''}`}>
            Camera Ready
          </div>
          <div className={`status-indicator ${handDetected ? 'active' : ''}`}>
            Hand Detected
          </div>
          <div className={`status-indicator ${processingGesture ? 'active' : ''}`}>
            Processing
          </div>
        </div>
      </div>
    </div>
  );
};

// Registration Screen Component
const RegistrationScreen = () => {
  const navigate = useNavigate();
  const { state } = useLocation();
  const [registrationMethod, setRegistrationMethod] = useState(null);
  const [showQRCode, setShowQRCode] = useState(false);
  
  useEffect(() => {
    if (!state?.sessionId) {
      navigate('/');
    }
  }, [state?.sessionId, navigate]);

  if (!state?.sessionId) {
    return null;
  }

  const handleQRRegistration = () => {
    setRegistrationMethod('qr');
    setShowQRCode(true);
  };

  const handleVirtualKeyboard = () => {
    setRegistrationMethod('virtual');
    navigate('/virtual-registration', { 
      state: { sessionId: state.sessionId }
    });
  };

  return (
    <div className="registration-screen">
      <div className="header">
        <h1>New User Registration</h1>
        <p>Choose your registration method</p>
      </div>
      
      {!showQRCode ? (
        <div className="registration-options">
          <div className="option-card" onClick={handleQRRegistration}>
            <div className="option-icon">📱</div>
            <h3>Mobile Registration</h3>
            <p>Scan QR code with your phone to fill details</p>
          </div>
          
          <div className="option-card" onClick={handleVirtualKeyboard}>
            <div className="option-icon">⌨️</div>
            <h3>Virtual Keyboard</h3>
            <p>Use gesture-controlled keyboard</p>
          </div>
        </div>
      ) : (
        <div className="qr-section">
          <h3>Scan with your phone</h3>
          <div className="qr-code-container">
            {state.qrCode && (
              <img 
                src={`data:image/png;base64,${state.qrCode}`}
                alt="Registration QR Code"
                className="qr-code"
              />
            )}
          </div>
          <p>Scan this QR code with your phone to complete registration</p>
          <button onClick={() => setShowQRCode(false)} className="back-button">
            Choose Different Method
          </button>
        </div>
      )}
    </div>
  );
};

// Mobile Registration Form (accessed via QR code)
const MobileRegistrationForm = () => {
  const { sessionId } = useParams();
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    contact: '',
    email: '',
    address: ''
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      await axios.post(`${API}/register-user`, {
        ...formData,
        age: parseInt(formData.age),
        session_id: sessionId
      });
      
      setSuccess(true);
    } catch (error) {
      console.error('Registration failed:', error);
      alert('Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="mobile-form success">
        <h2>✅ Registration Successful!</h2>
        <p>You can now use the kiosk for appointments.</p>
      </div>
    );
  }

  return (
    <div className="mobile-form">
      <h2>Complete Your Registration</h2>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Full Name"
          value={formData.name}
          onChange={(e) => setFormData({...formData, name: e.target.value})}
          required
        />
        <input
          type="number"
          placeholder="Age"
          value={formData.age}
          onChange={(e) => setFormData({...formData, age: e.target.value})}
          required
        />
        <input
          type="tel"
          placeholder="Contact Number"
          value={formData.contact}
          onChange={(e) => setFormData({...formData, contact: e.target.value})}
          required
        />
        <input
          type="email"
          placeholder="Email Address"
          value={formData.email}
          onChange={(e) => setFormData({...formData, email: e.target.value})}
          required
        />
        <textarea
          placeholder="Address"
          value={formData.address}
          onChange={(e) => setFormData({...formData, address: e.target.value})}
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Registering...' : 'Complete Registration'}
        </button>
      </form>
    </div>
  );
};

// Dashboard Component
const Dashboard = () => {
  const navigate = useNavigate();
  const { state } = useLocation();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        if (state?.userId) {
          const response = await axios.get(`${API}/user/${state.userId}`);
          setUser(response.data);
        }
      } catch (error) {
        console.error('Error fetching user:', error);
        navigate('/');
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [state?.userId, navigate]);

  const handleBookAppointment = () => {
    navigate('/appointment', { 
      state: { userId: state?.userId }
    });
  };

  if (loading) {
    return <div className="loading-screen">Loading...</div>;
  }

  return (
    <div className="dashboard">
      <div className="header">
        <h1>Welcome, {user?.name}!</h1>
        <p>What would you like to do today?</p>
      </div>
      
      <div className="dashboard-options">
        <div className="option-card" onClick={handleBookAppointment}>
          <div className="option-icon">🏥</div>
          <h3>Book Appointment</h3>
          <p>Schedule a new appointment</p>
        </div>
        
        <div className="option-card" onClick={() => navigate('/appointments', { state: { userId: state?.userId } })}>
          <div className="option-icon">📅</div>
          <h3>My Appointments</h3>
          <p>View scheduled appointments</p>
        </div>
        
        <div className="option-card">
          <div className="option-icon">🗺️</div>
          <h3>Hospital Map</h3>
          <p>Find departments & facilities</p>
        </div>
      </div>
    </div>
  );
};

// Appointment Booking Component
const AppointmentBooking = () => {
  const navigate = useNavigate();
  const { state } = useLocation();
  const [appointmentData, setAppointmentData] = useState({
    department: '',
    preferred_date: '',
    preferred_time: '',
    reason: ''
  });
  const [loading, setLoading] = useState(false);

  const departments = [
    'Cardiology', 'Neurology', 'Orthopedics', 'Dermatology',
    'Gastroenterology', 'Pulmonology', 'Endocrinology', 'General Medicine'
  ];

  const timeSlots = [
    '09:00', '09:30', '10:00', '10:30', '11:00', '11:30',
    '14:00', '14:30', '15:00', '15:30', '16:00', '16:30'
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const response = await axios.post(`${API}/appointment`, {
        user_id: state?.userId,
        ...appointmentData
      });
      
      alert('Appointment booked successfully! Confirmation email sent.');
      navigate('/dashboard', { state: { userId: state?.userId } });
      
    } catch (error) {
      console.error('Appointment booking failed:', error);
      alert('Failed to book appointment. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="appointment-booking">
      <div className="header">
        <h1>Book Appointment</h1>
        <p>Fill in the details below</p>
      </div>
      
      <form onSubmit={handleSubmit} className="appointment-form">
        <div className="form-group">
          <label>Department</label>
          <select
            value={appointmentData.department}
            onChange={(e) => setAppointmentData({...appointmentData, department: e.target.value})}
            required
          >
            <option value="">Select Department</option>
            {departments.map(dept => (
              <option key={dept} value={dept}>{dept}</option>
            ))}
          </select>
        </div>
        
        <div className="form-group">
          <label>Preferred Date</label>
          <input
            type="date"
            value={appointmentData.preferred_date}
            onChange={(e) => setAppointmentData({...appointmentData, preferred_date: e.target.value})}
            min={new Date().toISOString().split('T')[0]}
            required
          />
        </div>
        
        <div className="form-group">
          <label>Preferred Time</label>
          <select
            value={appointmentData.preferred_time}
            onChange={(e) => setAppointmentData({...appointmentData, preferred_time: e.target.value})}
            required
          >
            <option value="">Select Time</option>
            {timeSlots.map(time => (
              <option key={time} value={time}>{time}</option>
            ))}
          </select>
        </div>
        
        <div className="form-group">
          <label>Reason for Visit</label>
          <textarea
            value={appointmentData.reason}
            onChange={(e) => setAppointmentData({...appointmentData, reason: e.target.value})}
            placeholder="Describe your symptoms or reason for visit"
            required
          />
        </div>
        
        <button type="submit" disabled={loading} className="book-button">
          {loading ? 'Booking...' : 'Book Appointment'}
        </button>
        
        <button 
          type="button" 
          onClick={() => navigate('/dashboard', { state: { userId: state?.userId } })}
          className="back-button"
        >
          Back to Dashboard
        </button>
      </form>
    </div>
  );
};

// Main App Component
function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<WelcomeScreen />} />
          <Route path="/registration" element={<RegistrationScreen />} />
          <Route path="/register/:sessionId" element={<MobileRegistrationForm />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/appointment" element={<AppointmentBooking />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;