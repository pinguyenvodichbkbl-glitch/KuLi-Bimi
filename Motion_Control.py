import cv2
import mediapipe as mp


class MotionController:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()


        self.cap = cv2.VideoCapture(0)


        self.hand_up = False
        self.prev_hand_up = False


    def update(self):
        success, img = self.cap.read()


        if not success:
            return False


        img = cv2.flip(img, 1)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


        results = self.pose.process(rgb)


        self.hand_up = False


        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark


            # tay phải
            wrist = lm[16]
            shoulder = lm[12]


            # nếu cổ tay cao hơn vai => giơ tay
            if wrist.y < shoulder.y:
                self.hand_up = True


        # Chỉ trả về True khi vừa giơ lên
        flap = False
        if self.hand_up and not self.prev_hand_up:
            flap = True


        self.prev_hand_up = self.hand_up


        return flap


    def close(self):
        self.cap.release()
        cv2.destroyAllWindows()

