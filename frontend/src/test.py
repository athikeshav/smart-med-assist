import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7)

stable_counter = 0
THRESHOLD = 30  # ~1 second if 30fps
gesture_triggered = False

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        
        stable_counter += 1
    else:
        stable_counter = 0

    if stable_counter > THRESHOLD and not gesture_triggered:
        print("Gesture recognized! Moving to next page...")
        gesture_triggered = True
        # 🚀 Call your function here to go to the next page
        # e.g., show_menu_page()
        break  # <-- exit current loop if needed

    cv2.imshow("Hand Detection", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
