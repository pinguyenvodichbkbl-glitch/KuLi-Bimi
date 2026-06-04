"""
Flappy Bird - Python + MediaPipe (Nam tay de bay)
Yeu cau: pip install pygame opencv-python mediapipe
Chay:    python huy.py

Dieu khien:
  - NAM TAY (bop long ban tay)  ->  chim bay len
  - SPACE / len                 ->  backup ban phim
  - D                           ->  tam dung
  - ESC                         ->  ve menu
"""

import pygame
import random
import sys
import threading
import math
import cv2
import mediapipe as mp

# =============================================================================
# HANG SO
# =============================================================================
SCREEN_W       = 900
SCREEN_H       = 600
WIN_W          = 560
GAP_SIZE       = 180
PIPE_SPEED     = [3, 5, 9]
SPAWN_INTERVAL = 140
FIST_THRESHOLD = 0.3    # nguong nam tay: nho hon = phai nam chat hon

# Mau sac
WHITE  = (255, 255, 255)
GREEN  = (0,   200, 0  )
RED    = (220, 50,  50 )
YELLOW = (240, 200, 0  )
CYAN   = (0,   200, 220)
ORANGE = (255, 140, 0  )
GRAY   = (180, 180, 180)
DARK   = (30,  30,  30 )
PANEL  = (20,  20,  50 )

BIRD_SKINS = [
    [" /--o\\", "|___>"],
    [" ///  ",  "*//>O>"],
    [" \\\\\\\\    ", "*\\\\\\\\*O)>", " ****   ", " ////    "],
]
SKIN_COLORS = [YELLOW, CYAN, ORANGE]

# Bien dung chung camera <-> game
flap_flag     = False
cam_running   = False
cam_status    = "Chua bat camera"
hand_detected = False
is_fist       = False    # True khi dang nam tay


# =============================================================================
# HAM TINH KHOANG CACH 2 DIEM
# =============================================================================
def dist(a, b):
    return math.sqrt((a.x - b.x) * 2 + (a.y - b.y) * 2)


# =============================================================================
# CAMERA THREAD
# =============================================================================
def camera_thread():
    global flap_flag, cam_running, cam_status, hand_detected, is_fist

    mp_hands  = mp.solutions.hands
    mp_draw   = mp.solutions.drawing_utils
    hands_det = mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        cam_status  = "Khong tim thay webcam!"
        cam_running = False
        return

    cam_status  = "Camera san sang"
    prev_fist   = False    # trang thai nam tay frame truoc

    while cam_running:
        ret, frame = cap.read()
        if not ret:
            break

        frame  = cv2.flip(frame, 1)
        h, w   = frame.shape[:2]
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands_det.process(rgb)

        hand_detected = result.multi_hand_landmarks is not None
        is_fist       = False

        if result.multi_hand_landmarks:
            for hand_lm in result.multi_hand_landmarks:

                # Ve skeleton tay
                mp_draw.draw_landmarks(
                    frame, hand_lm, mp_hands.HAND_CONNECTIONS,
                    mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4),
                    mp_draw.DrawingSpec(color=(255, 255, 255), thickness=2),
                )

                # Lay cac diem landmark
                wrist  = hand_lm.landmark[0]
                tip_8  = hand_lm.landmark[8]   # ngon tro
                tip_12 = hand_lm.landmark[12]  # ngon giua
                tip_16 = hand_lm.landmark[16]  # ngon ao
                tip_20 = hand_lm.landmark[20]  # ngon ut

                # Tinh khoang cach trung binh dau ngon -> co tay
                avg_dist = (
                    dist(tip_8,  wrist) +
                    dist(tip_12, wrist) +
                    dist(tip_16, wrist) +
                    dist(tip_20, wrist)
                ) / 4

                # Phat hien nam tay
                is_fist = avg_dist < FIST_THRESHOLD

                # Chi flap khi CHUYEN TU MO -> NAM (tranh giu nam lien tuc)
                if is_fist and not prev_fist:
                    flap_flag = True

                prev_fist = is_fist

                # Hien thi khoang cach de debug
                cv2.putText(frame,
                            "Dist: {:.3f}".format(avg_dist),
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

            # Hien thi trang thai
            if is_fist:
                cv2.putText(frame, "NAM TAY - FLAP!",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                # Ve khung xanh khi nam
                cv2.rectangle(frame, (5, 5), (w - 5, h - 5), (0, 255, 0), 3)
            else:
                cv2.putText(frame, "MO TAY - giu de roi",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 150, 255), 2)
        else:
            prev_fist = False
            cv2.putText(frame, "Khong thay tay - Dua tay vao camera",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2)

        cv2.putText(frame, "Q: dong camera",
                    (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        small = cv2.resize(frame, (320, 240))
        cv2.imshow("Camera - Flappy Bird", small)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    cam_running = False


# =============================================================================
# CLASS PIPE
# =============================================================================
class Pipe:
    WIDTH = 30

    def __init__(self, x, gap_y):
        self.x     = x
        self.gap_y = gap_y

    def move(self, speed):
        self.x -= speed

    def draw(self, surf):
        top_h = self.gap_y
        bot_y = self.gap_y + GAP_SIZE
        bot_h = SCREEN_H - bot_y
        pygame.draw.rect(surf, GREEN, (self.x, 0, self.WIDTH, top_h))
        pygame.draw.rect(surf, (0, 160, 0), (self.x - 4, top_h - 16, self.WIDTH + 8, 16))
        pygame.draw.rect(surf, GREEN, (self.x, bot_y, self.WIDTH, bot_h))
        pygame.draw.rect(surf, (0, 160, 0), (self.x - 4, bot_y, self.WIDTH + 8, 16))

    def collides_with(self, bx, by, bw, bh):
        r   = pygame.Rect(bx, by, bw, bh)
        top = pygame.Rect(self.x, 0, self.WIDTH, self.gap_y)
        bot = pygame.Rect(self.x, self.gap_y + GAP_SIZE, self.WIDTH, SCREEN_H)
        return r.colliderect(top) or r.colliderect(bot)

    @property
    def right(self):
        return self.x + self.WIDTH


# =============================================================================
# CLASS BIRD
# =============================================================================
class Bird:
    START_X = 60
    START_Y = 200

    def __init__(self, skin, font):
        self.x      = self.START_X
        self.y      = float(self.START_Y)
        self.vy     = 0.0
        self.lines  = BIRD_SKINS[skin]
        self.color  = SKIN_COLORS[skin]
        self.font   = font
        sample      = font.render(self.lines[0], True, WHITE)
        self.ch_h   = sample.get_height()
        self.width  = sample.get_width()
        self.height = self.ch_h * len(self.lines)

    def flap(self):
        self.vy = -7.0

    def update(self):
        self.vy += 0.35
        self.y  += self.vy
        if self.y < 0:
            self.y  = 0
            self.vy = 0

    def draw(self, surf):
        iy = int(self.y)
        for i, line in enumerate(self.lines):
            img = self.font.render(line, True, self.color)
            surf.blit(img, (self.x, iy + i * self.ch_h))

    @property
    def rect(self):
        return pygame.Rect(self.x + 2, int(self.y) + 2, self.width - 4, self.height - 4)


# =============================================================================
# MAN HINH MENU
# =============================================================================
def draw_menu(surf, font_big, font_med, font_sm):
    surf.fill(DARK)

    title = font_big.render("FLAPPY BIRD", True, YELLOW)
    surf.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 55))

    sep = font_med.render("-" * 30, True, RED)
    surf.blit(sep, (SCREEN_W // 2 - sep.get_width() // 2, 125))

    cam_col = GREEN if cam_running else GRAY
    cs = font_sm.render("Camera: " + cam_status, True, cam_col)
    surf.blit(cs, (SCREEN_W // 2 - cs.get_width() // 2, 168))

    fist_col = GREEN if is_fist else (RED if hand_detected else GRAY)
    fist_txt = "NAM TAY: Co!" if is_fist else ("Mo tay" if hand_detected else "Khong thay tay")
    fs = font_sm.render("Trang thai: " + fist_txt, True, fist_col)
    surf.blit(fs, (SCREEN_W // 2 - fs.get_width() // 2, 198))

    options = [
        ("0", "Huong dan", WHITE),
        ("1", "De",        GREEN),
        ("2", "Trung binh", YELLOW),
        ("3", "Kho",        RED),
        ("Q", "Thoat",      GRAY),
    ]
    for i, (key, label, col) in enumerate(options):
        txt = font_med.render("[" + key + "]  " + label, True, col)
        surf.blit(txt, (SCREEN_W // 2 - 120, 228 + i * 52))

    hint = font_sm.render("Nhan phim de chon", True, GRAY)
    surf.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 36))


# =============================================================================
# MAN HINH HUONG DAN
# =============================================================================
def show_instructions(surf, font_big, font_med, font_sm, clock):
    surf.fill(DARK)
    t = font_big.render("HUONG DAN", True, YELLOW)
    surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 35))

    lines = [
        ("Dieu khien bang TAY (MediaPipe):", CYAN),
        ("  Bop / Nam tay  ->  chim bay len", GREEN),
        ("  Mo tay ra      ->  chim roi xuong", WHITE),
        ("  * Chi flap khi MO -> NAM (khong giu)", GRAY),
        ("", WHITE),
        ("Dieu khien bang BAN PHIM (backup):", CYAN),
        ("  SPACE / len  ->  chim bay len", GREEN),
        ("  D            ->  tam dung / tiep tuc", WHITE),
        ("  ESC          ->  ve menu", WHITE),
        ("", WHITE),
        ("Nhan bat ky phim nao de quay lai...", GRAY),
    ]
    for i, (line, col) in enumerate(lines):
        img = font_sm.render(line, True, col)
        surf.blit(img, (55, 110 + i * 42))

    pygame.display.flip()
    waiting = True
    while waiting:
        clock.tick(30)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                waiting = False


# =============================================================================
# MAN HINH GAME OVER
# =============================================================================
def show_gameover(surf, font_big, font_med, font_sm, clock, score, best):
    surf.fill(DARK)

    g = font_big.render("GAME OVER", True, RED)
    surf.blit(g, (SCREEN_W // 2 - g.get_width() // 2, 140))

    sc = font_med.render("Diem cua ban : " + str(score), True, YELLOW)
    surf.blit(sc, (SCREEN_W // 2 - sc.get_width() // 2, 255))

    bsc = font_med.render("Diem cao nhat: " + str(best), True, CYAN)
    surf.blit(bsc, (SCREEN_W // 2 - bsc.get_width() // 2, 315))

    hint = font_sm.render("Nhan bat ky phim nao de ve menu...", True, GRAY)
    surf.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 65))

    pygame.display.flip()
    waiting = True
    while waiting:
        clock.tick(30)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                waiting = False


# =============================================================================
# VONG LAP GAME CHINH
# =============================================================================
def play(surf, fonts, clock, level, best_score):
    global flap_flag

    font_big, font_med, font_sm, font_mono = fonts
    speed  = PIPE_SPEED[level]
    bird   = Bird(level, font_mono)
    pipes  = []
    score  = 0
    paused = False

    def new_pipe():
        gap_y = random.randint(60, SCREEN_H - GAP_SIZE - 60)
        return Pipe(WIN_W + 40, gap_y)

    pipes.append(new_pipe())
    spawn_timer = 0

    def draw_hud():
        pygame.draw.rect(surf, WHITE, (0, 0, WIN_W, SCREEN_H), 2)
        pygame.draw.rect(surf, PANEL, (WIN_W, 0, SCREEN_W - WIN_W, SCREEN_H))

        lbl = ["DE", "TRUNG BINH", "KHO"][level]
        surf.blit(font_sm.render("Level: " + lbl, True, CYAN),                (WIN_W + 20, 22))
        surf.blit(font_med.render("Diem: " + str(score), True, RED),          (WIN_W + 20, 60))
        surf.blit(font_sm.render("Best: " + str(best_score[0]), True, GRAY),  (WIN_W + 20, 108))

        # Trang thai camera
        cam_col  = GREEN if cam_running else GRAY
        hand_col = GREEN if hand_detected else RED
        fist_col = GREEN if is_fist else GRAY
        surf.blit(font_sm.render("-- Camera --", True, GRAY),                 (WIN_W + 20, 160))
        surf.blit(font_sm.render("Webcam: " + ("ON" if cam_running else "OFF"), True, cam_col), (WIN_W + 20, 190))
        surf.blit(font_sm.render("Tay: " + ("Co" if hand_detected else "Khong"), True, hand_col), (WIN_W + 20, 218))
        surf.blit(font_sm.render("Nam: " + ("CO!" if is_fist else "Mo"), True, fist_col), (WIN_W + 20, 246))

        # Phim
        surf.blit(font_sm.render("-- Phim --", True, GRAY),                   (WIN_W + 20, 290))
        for i, s in enumerate(["SPACE/len: bay", "D: dung", "ESC: menu"]):
            surf.blit(font_sm.render(s, True, WHITE), (WIN_W + 20, 318 + i * 34))

        if paused:
            pt = font_big.render("TAM DUNG", True, YELLOW)
            surf.blit(pt, (WIN_W // 2 - pt.get_width() // 2, SCREEN_H // 2 - 30))

    running = True
    while running:
        clock.tick(60)

        # Doc flap tu camera (nam tay)
        if flap_flag and not paused:
            bird.flap()
            flap_flag = False

        # Xu ly event ban phim
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_SPACE, pygame.K_UP) and not paused:
                    bird.flap()
                if ev.key in (pygame.K_d, pygame.K_p):
                    paused = not paused
                if ev.key == pygame.K_ESCAPE:
                    return

        if paused:
            surf.fill(DARK)
            pygame.draw.rect(surf, (20, 30, 60), (0, 0, WIN_W, SCREEN_H // 2))
            pygame.draw.rect(surf, (20, 40, 80), (0, SCREEN_H // 2, WIN_W, SCREEN_H // 2))
            for p in pipes:
                p.draw(surf)
            bird.draw(surf)
            draw_hud()
            pygame.display.flip()
            continue

        # Cap nhat logic
        bird.update()
        spawn_timer += 1
        if spawn_timer >= SPAWN_INTERVAL:
            spawn_timer = 0
            pipes.append(new_pipe())

        for p in pipes:
            p.move(speed)

        for p in pipes:
            if not hasattr(p, "scored") and p.right < bird.x:
                p.scored = True
                score += 1

        pipes = [p for p in pipes if p.right > -20]

        # Kiem tra va cham
        hit_floor = bird.rect.bottom >= SCREEN_H
        hit_pipe  = any(
            p.collides_with(bird.rect.x, bird.rect.y, bird.rect.width, bird.rect.height)
            for p in pipes
        )

        if hit_floor or hit_pipe:
            if score > best_score[0]:
                best_score[0] = score
            show_gameover(surf, font_big, font_med, font_sm, clock, score, best_score[0])
            return

        # Ve man hinh
        surf.fill(DARK)
        pygame.draw.rect(surf, (20, 30, 60), (0, 0, WIN_W, SCREEN_H // 2))
        pygame.draw.rect(surf, (20, 40, 80), (0, SCREEN_H // 2, WIN_W, SCREEN_H // 2))
        for p in pipes:
            p.draw(surf)
        bird.draw(surf)
        draw_hud()
        pygame.display.flip()


# =============================================================================
# MAIN
# =============================================================================
def main():
    global cam_running

    pygame.init()
    surf  = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Flappy Bird - Nam tay de bay")
    clock = pygame.time.Clock()

    font_big  = pygame.font.SysFont("consolas", 52, bold=True)
    font_med  = pygame.font.SysFont("consolas", 32, bold=True)
    font_sm   = pygame.font.SysFont("consolas", 22)
    font_mono = pygame.font.SysFont("consolas", 20)
    fonts = (font_big, font_med, font_sm, font_mono)

    best_score = [0]

    # Khoi dong camera tren luong rieng
    cam_running = True
    t = threading.Thread(target=camera_thread, daemon=True)
    t.start()

    while True:
        draw_menu(surf, font_big, font_med, font_sm)
        pygame.display.flip()

        chosen = None
        while chosen is None:
            clock.tick(30)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    cam_running = False
                    pygame.quit()
                    sys.exit()
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_0:
                        show_instructions(surf, font_big, font_med, font_sm, clock)
                        chosen = -1
                    elif ev.key == pygame.K_1:
                        chosen = 0
                    elif ev.key == pygame.K_2:
                        chosen = 1
                    elif ev.key == pygame.K_3:
                        chosen = 2
                    elif ev.key in (pygame.K_q, pygame.K_ESCAPE):
                        cam_running = False
                        pygame.quit()
                        sys.exit()

        if chosen in (0, 1, 2):
            play(surf, fonts, clock, chosen, best_score)


if _name_ == "_main_":
    main()
