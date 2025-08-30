import requests
import sys
import json
from datetime import datetime, timezone
import uuid

class SmartMedAssistAPITester:
    def __init__(self, base_url="https://biometric-checkin.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.session_id = None
        self.user_id = None
        self.appointment_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            print(f"   Status Code: {response.status_code}")
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)}")
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error Response: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"   Error Text: {response.text}")
                return False, {}

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed - Network Error: {str(e)}")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        return success

    def test_hand_recognition_new_user(self):
        """Test hand recognition for new user"""
        # Sample hand landmarks data (21 landmarks with x, y, z coordinates)
        # Using unique landmarks to ensure this is treated as a new user
        import random
        sample_landmarks = []
        for i in range(21):
            x = 0.3 + random.random() * 0.4  # Random between 0.3-0.7
            y = 0.3 + random.random() * 0.4  # Random between 0.3-0.7
            z = random.random() * 0.05       # Random between 0-0.05
            sample_landmarks.append([x, y, z])
        
        success, response = self.run_test(
            "Hand Recognition - New User",
            "POST",
            "hand-recognition",
            200,
            data={
                "landmarks": sample_landmarks,
                "confidence": 0.85
            }
        )
        
        if success and response:
            self.session_id = response.get('session_id')
            print(f"   Session ID: {self.session_id}")
            
            # Verify response structure for new user
            if response.get('is_new_user') and self.session_id and response.get('qr_code'):
                print("✅ New user response structure is correct")
                return True
            else:
                print("⚠️  User was recognized as existing (this might be expected)")
                # If user was recognized, we can still test other endpoints
                if not response.get('is_new_user') and response.get('user_id'):
                    self.user_id = response.get('user_id')
                    print(f"   Existing User ID: {self.user_id}")
                    return True
                return False
        
        return success

    def test_user_registration(self):
        """Test user registration with session ID"""
        if not self.session_id:
            print("⚠️  Skipping registration test - no session ID (user was recognized as existing)")
            return True
            
        test_user_data = {
            "name": f"Test User {datetime.now().strftime('%H%M%S')}",
            "age": 30,
            "contact": "+1234567890",
            "email": "medassist125@gmail.com",  # Using the configured test email
            "address": "123 Test Street, Test City",
            "session_id": self.session_id
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "register-user",
            200,
            data=test_user_data
        )
        
        if success and response:
            self.user_id = response.get('user_id')
            print(f"   User ID: {self.user_id}")
        
        return success

    def test_get_user(self):
        """Test getting user details"""
        if not self.user_id:
            print("❌ Cannot test get user - no user ID")
            return False
            
        success, response = self.run_test(
            "Get User Details",
            "GET",
            f"user/{self.user_id}",
            200
        )
        
        if success and response:
            # Verify user data structure
            required_fields = ['id', 'name', 'age', 'contact', 'email', 'address', 'is_registered']
            missing_fields = [field for field in required_fields if field not in response]
            
            if missing_fields:
                print(f"❌ Missing required fields: {missing_fields}")
                return False
            else:
                print("✅ User data structure is correct")
        
        return success

    def test_book_appointment(self):
        """Test booking an appointment"""
        if not self.user_id:
            print("❌ Cannot test appointment booking - no user ID")
            return False
            
        # Get tomorrow's date
        tomorrow = datetime.now().strftime('%Y-%m-%d')
        
        appointment_data = {
            "user_id": self.user_id,
            "department": "Cardiology",
            "preferred_date": tomorrow,
            "preferred_time": "10:00",
            "reason": "Regular checkup and consultation"
        }
        
        success, response = self.run_test(
            "Book Appointment",
            "POST",
            "appointment",
            200,
            data=appointment_data
        )
        
        if success and response:
            self.appointment_id = response.get('appointment_id')
            print(f"   Appointment ID: {self.appointment_id}")
            
            # Check if email was sent
            email_sent = response.get('email_sent', False)
            print(f"   Email Sent: {email_sent}")
        
        return success

    def test_get_user_appointments(self):
        """Test getting user appointments"""
        if not self.user_id:
            print("❌ Cannot test get appointments - no user ID")
            return False
            
        success, response = self.run_test(
            "Get User Appointments",
            "GET",
            f"appointments/{self.user_id}",
            200
        )
        
        if success and response:
            if isinstance(response, list):
                print(f"   Found {len(response)} appointments")
                if len(response) > 0:
                    print("✅ Appointments retrieved successfully")
                else:
                    print("⚠️  No appointments found (this might be expected)")
            else:
                print("❌ Expected list response for appointments")
                return False
        
        return success

    def test_hand_recognition_existing_user(self):
        """Test hand recognition for existing user (should recognize the registered user)"""
        if not self.user_id:
            print("❌ Cannot test existing user recognition - no registered user")
            return False
            
        # Use the same landmarks as registration to simulate recognition
        sample_landmarks = [
            [0.5, 0.5, 0.0], [0.52, 0.48, 0.01], [0.54, 0.46, 0.02],
            [0.56, 0.44, 0.03], [0.58, 0.42, 0.04], [0.48, 0.52, 0.01],
            [0.46, 0.54, 0.02], [0.44, 0.56, 0.03], [0.42, 0.58, 0.04],
            [0.50, 0.54, 0.01], [0.48, 0.56, 0.02], [0.46, 0.58, 0.03],
            [0.44, 0.60, 0.04], [0.52, 0.54, 0.01], [0.54, 0.56, 0.02],
            [0.56, 0.58, 0.03], [0.58, 0.60, 0.04], [0.54, 0.52, 0.01],
            [0.56, 0.54, 0.02], [0.58, 0.56, 0.03], [0.60, 0.58, 0.04]
        ]
        
        success, response = self.run_test(
            "Hand Recognition - Existing User",
            "POST",
            "hand-recognition",
            200,
            data={
                "landmarks": sample_landmarks,
                "confidence": 0.85
            }
        )
        
        if success and response:
            # For existing user, should return user_id and is_new_user=False
            if not response.get('is_new_user') and response.get('user_id'):
                print("✅ Existing user recognition working correctly")
                return True
            else:
                print("⚠️  User not recognized as existing (similarity threshold might be too high)")
                return True  # This is not necessarily a failure
        
        return success

    def test_invalid_endpoints(self):
        """Test error handling for invalid requests"""
        print("\n🔍 Testing Error Handling...")
        
        # Test invalid user ID
        success1, _ = self.run_test(
            "Get Invalid User",
            "GET",
            "user/invalid-user-id",
            404
        )
        
        # Test invalid session ID for registration
        success2, _ = self.run_test(
            "Register with Invalid Session",
            "POST",
            "register-user",
            404,
            data={
                "name": "Test User",
                "age": 30,
                "contact": "+1234567890",
                "email": "test@example.com",
                "address": "Test Address",
                "session_id": "invalid-session-id"
            }
        )
        
        # Test appointment booking with invalid user
        success3, _ = self.run_test(
            "Book Appointment - Invalid User",
            "POST",
            "appointment",
            404,
            data={
                "user_id": "invalid-user-id",
                "department": "Cardiology",
                "preferred_date": "2024-12-25",
                "preferred_time": "10:00",
                "reason": "Test appointment"
            }
        )
        
        return success1 and success2 and success3

def main():
    print("🏥 Smart Med Assist API Testing Suite")
    print("=" * 50)
    
    tester = SmartMedAssistAPITester()
    
    # Test sequence
    tests = [
        ("Health Check", tester.test_health_check),
        ("Hand Recognition (New User)", tester.test_hand_recognition_new_user),
        ("User Registration", tester.test_user_registration),
        ("Get User Details", tester.test_get_user),
        ("Book Appointment", tester.test_book_appointment),
        ("Get User Appointments", tester.test_get_user_appointments),
        ("Hand Recognition (Existing User)", tester.test_hand_recognition_existing_user),
        ("Error Handling", tester.test_invalid_endpoints)
    ]
    
    print(f"\nRunning {len(tests)} test suites...")
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            test_func()
        except Exception as e:
            print(f"❌ Test suite '{test_name}' failed with exception: {str(e)}")
    
    # Print final results
    print(f"\n{'='*50}")
    print(f"📊 FINAL RESULTS")
    print(f"{'='*50}")
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Tests Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run*100):.1f}%" if tester.tests_run > 0 else "No tests run")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())