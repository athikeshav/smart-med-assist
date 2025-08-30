import React, { useState, useEffect, useRef, useCallback, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useParams, useLocation } from 'react-router-dom';
import axios from 'axios';
import { HandLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';
import QRCode from 'react-qr-code';
import './App.css';

const API_BASE = process.env.REACT_APP_BACKEND_URL || 'https://92dbfcf425b8.ngrok-free.app';
const API = `${API_BASE}/api`;
const NGROK_URL = process.env.REACT_APP_NGROK_URL || 'https://ea99a72b55ff.ngrok-free.app';

const StreamContext = createContext(null);

// Custom hook for hand detection
const useHandDetection = () => {
  const [handLandmarker, setHandLandmarker] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const initializeHandLandmarker = async () => {
      try {
        console.log('Initializing HandLandmarker...');
        const vision = await FilesetResolver.forVisionTasks(
          'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm'
        );
        const landmarker = await HandLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath:
              'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
            delegate: 'CPU',
          },
          runningMode: 'VIDEO',
          numHands: 1,
          minHandDetectionConfidence: 0.2,
          minHandPresenceConfidence: 0.2,
          minTrackingConfidence: 0.2,
        });
        setHandLandmarker(landmarker);
        setIsLoading(false);
        console.log('HandLandmarker initialized successfully');
      } catch (err) {
        console.error('Error initializing hand landmarker:', err);
        setError(err.message || 'Failed to initialize hand detection');
        setIsLoading(false);
      }
    };
    initializeHandLandmarker();
  }, []);

  return { handLandmarker, isLoading, error };
};

// HandRecognitionScreen with hand detection
const HandRecognitionScreen = () => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const { handLandmarker, isLoading, error } = useHandDetection();
  const navigate = useNavigate();
  const stream = useContext(StreamContext);
  const [status, setStatus] = useState('Show your hand to begin');
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    if (videoRef.current && stream) {
      videoRef.current.srcObject = stream;
      videoRef.current.play().catch(e => console.error('Video play error:', e));
    }
  }, [stream]);

  const processHandFeatures = useCallback(
    async (results) => {
      if (processing || !results.landmarks || results.landmarks.length === 0) return;

      setProcessing(true);
      setStatus('Scanning hand features...');
      try {
        const landmarks = results.landmarks[0].map(({ x, y, z }) => [x, y, z]);
        const confidence = results.handednesses?.[0]?.[0]?.score || 0.8;
        console.log('Landmarks sent to backend:', landmarks);
        console.log('Confidence sent to backend:', confidence);
        console.log('Full request to backend:', { landmarks, confidence });

        const response = await axios.post(
          `${API}/hand-recognition`,
          { landmarks, confidence },
          { timeout: 5000 }
        );
        console.log('Full backend response:', response.data);

        if (response.data.is_new_user) {
          setStatus('New user detected. Redirecting to QR code...');
          navigate('/qr-code', { state: { sessionId: response.data.session_id } });
        } else if (response.data.registered) {
          setStatus('User recognized. Redirecting...');
          navigate('/home');
        } else {
          setStatus('User exists but not registered. Please register first.');
        }
      } catch (err) {
        console.error('Error processing hand features:', err);
        setStatus('Error processing hand features. Check console.');
      } finally {
        setProcessing(false);
      }
    },
    [processing, navigate]
  );

  useEffect(() => {
    let animationId;
    const detectHands = () => {
      if (handLandmarker && videoRef.current && videoRef.current.readyState >= 2) {
        const results = handLandmarker.detectForVideo(videoRef.current, performance.now());
        processHandFeatures(results);
      }
      animationId = requestAnimationFrame(detectHands);
    };

    if (handLandmarker) {
      detectHands();
    }

    return () => cancelAnimationFrame(animationId);
  }, [handLandmarker, processHandFeatures]);

  if (isLoading) return <div className="loading">Initializing...</div>;
  if (error) return <div className="error">Error: {error}</div>;

  return (
    <div className="hand-recognition-screen">
      <h1>Smart Med Assist</h1>
      <div className="camera-section">
        <video ref={videoRef} autoPlay playsInline muted className="camera-feed" />
        <canvas ref={canvasRef} className="hand-overlay" width={800} height={600} />
      </div>
      <p className="status">{status}</p>
    </div>
  );
};

// QRCodeScreen
const QRCodeScreen = () => {
  const { state } = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (!state?.sessionId) {
      navigate('/');
    }
  }, [state?.sessionId, navigate]);

  if (!state?.sessionId) return null;

  const qrUrl = `${NGROK_URL}/register/${state.sessionId}`;

  const handleBackToLogin = () => {
    navigate('/');
  };

  return (
    <div className="qr-code-screen">
      <h1>Register New User</h1>
      <div className="qr-section">
        <p>Scan the QR code on your device to fill details:</p>
        <div className="qr-code-container">
          <QRCode value={qrUrl} size={250} />
        </div>
        <p>URL: <code>{qrUrl}</code></p>
        <button onClick={handleBackToLogin}>Back to Login</button>
      </div>
    </div>
  );
};

// MobileRegistrationForm
const MobileRegistrationForm = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    contact: '',
    email: '',
    address: '',
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(
        `${API}/register-user`,
        { sessionId, ...formData },
        { timeout: 5000 }
      );
      console.log('Registration response:', response.data);

      if (response.data.message === 'Registration successful') {
        setSuccess(true);
        // Do not redirect to /home on QR-scanned device; stay on success screen
      } else {
        setError('Registration failed. Please try again.');
      }
    } catch (err) {
      console.error('Registration error:', err);
      setError('Failed to submit registration. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading...</div>;
  if (success) return <div className="success">Registration successful!</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="mobile-registration-form">
      <h1>Complete Registration</h1>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Full Name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          required
        />
        <input
          type="number"
          placeholder="Age"
          value={formData.age}
          onChange={(e) => setFormData({ ...formData, age: e.target.value })}
          required
        />
        <input
          type="text"
          placeholder="Contact Number"
          value={formData.contact}
          onChange={(e) => setFormData({ ...formData, contact: e.target.value })}
          required
        />
        <input
          type="email"
          placeholder="Email Address"
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          required
        />
        <textarea
          placeholder="Address"
          value={formData.address}
          onChange={(e) => setFormData({ ...formData, address: e.target.value })}
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Submitting...' : 'Submit'}
        </button>
      </form>
    </div>
  );
};

// HomeScreen
const HomeScreen = () => {
  const navigate = useNavigate();

  const handleBookAppointment = () => {
    navigate('/book-appointment');
  };

  const handleExit = () => {
    navigate('/');
  };

  return (
    <div className="home-screen">
      <h1>Welcome Home</h1>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <button onClick={handleBookAppointment}>Book Appointment</button>
        <button onClick={handleExit}>Exit</button>
      </div>
    </div>
  );
};

// BookAppointmentScreen
const BookAppointmentScreen = () => {
  const navigate = useNavigate();
  const [department, setDepartment] = useState('');
  const [time, setTime] = useState('');
  const [date] = useState(new Date().toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' }).replace(/\//g, '-'));
  const [confirmation, setConfirmation] = useState(false);
  const departments = ['Cardiology', 'Gynecology', 'Pediatrics', 'General Medicine'];
  const times = Array.from({ length: 9 }, (_, i) => `${9 + i}:00`).concat(['17:00']);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (department && time) {
      setConfirmation(true);
      setTimeout(() => {
        console.log('Appointment booked:', { department, time, date });
        navigate('/home');
      }, 2000); // Delay 2 seconds before redirecting
    } else {
      alert('Please select department and time.');
    }
  };

  if (confirmation) return <div className="success">Appointment confirmed!</div>;

  return (
    <div className="appointment-screen">
      <h1>Book Appointment</h1>
      <form onSubmit={handleSubmit}>
        <div className="options-container">
          <h3>Select Department</h3>
          <div className="boxes">
            {departments.map((dept) => (
              <div
                key={dept}
                className={`box ${department === dept ? 'selected' : ''}`}
                onClick={() => setDepartment(dept)}
              >
                {dept}
              </div>
            ))}
          </div>

          <h3>Select Time</h3>
          <div className="boxes">
            {times.map((t) => (
              <div
                key={t}
                className={`box ${time === t ? 'selected' : ''}`}
                onClick={() => setTime(t)}
              >
                {t}
              </div>
            ))}
          </div>

          <h3>Date</h3>
          <div className="box disabled">{date}</div>
        </div>
        <button type="submit">Book Appointment</button>
      </form>
    </div>
  );
};

// Main App Component
const App = () => {
  const [stream, setStream] = useState(null);
  const videoRef = useRef(null);

  useEffect(() => {
    const initCamera = async () => {
      try {
        console.log('Requesting camera access...');
        const s = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 800 }, height: { ideal: 600 }, facingMode: 'user' },
        });
        setStream(s);
        if (videoRef.current) {
          videoRef.current.srcObject = s;
          videoRef.current.play().catch(e => console.error('Video play error:', e));
        }
      } catch (err) {
        console.error('Global camera access error:', err);
      }
    };
    initCamera();

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  return (
    <StreamContext.Provider value={stream}>
      <video ref={videoRef} autoPlay playsInline muted style={{ display: 'none' }} />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HandRecognitionScreen />} />
          <Route path="/qr-code" element={<QRCodeScreen />} />
          <Route path="/register/:sessionId" element={<MobileRegistrationForm />} />
          <Route path="/home" element={<HomeScreen />} />
          <Route path="/book-appointment" element={<BookAppointmentScreen />} />
        </Routes>
      </BrowserRouter>
    </StreamContext.Provider>
  );
};

export default App;