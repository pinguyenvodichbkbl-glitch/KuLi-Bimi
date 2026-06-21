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
import os
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
# Do kho: [De, Trung binh, Kho]
GAP_SIZES       = [320, 260, 220]   # Khe ho doc giua 2 ong
PIPE_SPEEDS     = [2, 3, 4]         # Toc do bay cua ong
SPAWN_INTERVALS = [200, 160, 130]   # Khoang cach ngang giua cac ong




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


BIRD_IMG = None # Hinh anh chim se duoc load trong main()
BIRD_IMG_PINK = None
BIRD_IMG_RED = None
BG_IMG   = None # Hinh nen


# Bien dung chung camera <-> game
flap_flag      = False
cam_running    = False
cam_status     = "Chua bat camera"
hand_detected  = False
is_fist        = False    # True khi dang nam tay


d_base         = 0.0      # Khoang cach co ban khi tay tha long (0.0 = chua hieu chuan)
d_fist         = 0.0      # Khoang cach khi nam tay (0.0 = chua hieu chuan)
calibrate_flag = False
calibrate_fist_flag = False
current_dist   = 0.0      # Khoang cach hien tai (de ve HUD)




# =============================================================================
# HAM TINH KHOANG CACH 2 DIEM
# =============================================================================
def dist(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)




# =============================================================================
# CAMERA THREAD
# =============================================================================
def camera_thread():
    global flap_flag, cam_running, cam_status, hand_detected, is_fist
    global d_base, d_fist, calibrate_flag, calibrate_fist_flag, current_dist


    mp_hands  = mp.solutions.hands
    mp_draw   = mp.solutions.drawing_utils
    hands_det = mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.6,
    )


    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
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


                current_dist = avg_dist


                # Hieu chuan
                if calibrate_flag:
                    d_base = avg_dist
                    calibrate_flag = False
                if calibrate_fist_flag:
                    d_fist = avg_dist
                    calibrate_fist_flag = False


                # Phat hien nam tay (su dung Hieu chuan dong)
                if d_base > 0 and d_fist > 0 and d_base > d_fist:
                    threshold = d_fist
                elif d_base > 0:
                    # fallback
                    threshold = d_base * 0.8
                else:
                    threshold = -1.0
               
                is_fist = (threshold > 0) and (avg_dist <= threshold)


                # Chi flap khi CHUYEN TU MO -> NAM (tranh giu nam lien tuc)
                if is_fist and not prev_fist:
                    flap_flag = True


                prev_fist = is_fist


                # Hien thi khoang cach de debug
                cv2.putText(frame,
                            f"Dist: {avg_dist:.3f} | Thr: {threshold:.3f}",
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
       
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            calibrate_flag = True
        elif key == ord('v'):
            calibrate_fist_flag = True


    cap.release()
    cv2.destroyAllWindows()
    cam_running = False




# =============================================================================
# CLASS PIPE
# =============================================================================
class Pipe:
    WIDTH = 30


    def __init__(self, x, gap_y, gap_size):
        self.x        = x
        self.gap_y    = gap_y
        self.gap_size = gap_size


    def move(self, speed):
        self.x -= speed


    def draw(self, surf):
        top_h = self.gap_y
        bot_y = self.gap_y + self.gap_size
        bot_h = SCREEN_H - bot_y
        pygame.draw.rect(surf, GREEN, (self.x, 0, self.WIDTH, top_h))
        pygame.draw.rect(surf, (0, 160, 0), (self.x - 4, top_h - 16, self.WIDTH + 8, 16))
        pygame.draw.rect(surf, GREEN, (self.x, bot_y, self.WIDTH, bot_h))
        pygame.draw.rect(surf, (0, 160, 0), (self.x - 4, bot_y, self.WIDTH + 8, 16))


    def collides_with(self, bx, by, bw, bh):
        r   = pygame.Rect(bx, by, bw, bh)
        top = pygame.Rect(self.x, 0, self.WIDTH, self.gap_y)
        bot = pygame.Rect(self.x, self.gap_y + self.gap_size, self.WIDTH, SCREEN_H)
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


    def __init__(self, level):
        self.x      = self.START_X
        self.y      = float(self.START_Y)
        self.vy     = 0.0
        global BIRD_IMG, BIRD_IMG_PINK, BIRD_IMG_RED
       
        # Chon mau chim theo muc do
        if level == 1 and BIRD_IMG_PINK:
            base_img = BIRD_IMG_PINK
        elif level == 2 and BIRD_IMG_RED:
            base_img = BIRD_IMG_RED
        else:
            base_img = BIRD_IMG
           
        # Scale chim len de nhin ro hon (goc la 34x24)
        self.img    = pygame.transform.scale(base_img, (51, 36))
        self.width  = self.img.get_width()
        self.height = self.img.get_height()


    def flap(self):
        self.vy = -6.0


    def update(self):
        self.vy += 0.15
        self.y  += self.vy
        if self.y < 0:
            self.y  = 0
            self.vy = 0


    def draw(self, surf):
        # Xoay con chim dua theo van toc roi
        angle = -self.vy * 3
        angle = max(-45, min(angle, 25))
        rotated_img = pygame.transform.rotate(self.img, angle)
       
        # Ve hinh o vi tri center de luc xoay khong bi lech toa do
        new_rect = rotated_img.get_rect(center=(self.x + self.width // 2, int(self.y) + self.height // 2))
        surf.blit(rotated_img, new_rect.topleft)


    @property
    def rect(self):
        # Thu nho Hitbox (vung va cham) vao trong mot chut de de choi hon
        return pygame.Rect(self.x + 6, int(self.y) + 6, self.width - 12, self.height - 12)




# =============================================================================
# MAN HINH MENU
# =============================================================================
def draw_menu(surf, font_big, font_med, font_sm):
    global d_base, d_fist
    if BG_IMG:
        surf.blit(BG_IMG, (0, 0))
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200)) # Den cuc toi
        surf.blit(overlay, (0, 0))
    else:
        surf.fill(DARK)


    title = font_big.render("FLAPPY BIRD", True, YELLOW)
    surf.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 30))


    sep = font_med.render("-" * 30, True, RED)
    surf.blit(sep, (SCREEN_W // 2 - sep.get_width() // 2, 85))


    cam_col = GREEN if cam_running else GRAY
    cs = font_sm.render("Camera: " + cam_status, True, cam_col)
    surf.blit(cs, (SCREEN_W // 2 - cs.get_width() // 2, 115))


    fist_col = GREEN if is_fist else (RED if hand_detected else GRAY)
    fist_txt = "NAM TAY: Co!" if is_fist else ("Mo tay" if hand_detected else "Khong thay tay")
    fs = font_sm.render("Trang thai: " + fist_txt, True, fist_col)
    surf.blit(fs, (SCREEN_W // 2 - fs.get_width() // 2, 145))


    # Giai thich hieu chuan
    surf.blit(font_sm.render("--- HUONG DAN HIEU CHUAN ROM ---", True, YELLOW), (SCREEN_W // 2 - 170, 180))
    surf.blit(font_sm.render("1. Tha long tay: An [C] de luu ROM Mo.", True, WHITE), (SCREEN_W // 2 - 290, 210))
    surf.blit(font_sm.render("2. Nam chat tay: An [V] de luu ROM Nam.", True, WHITE), (SCREEN_W // 2 - 290, 235))
   
    status_str = "-> Trang thai: CHUA HIEU CHUAN (Can an C va V)!"
    cal_col = RED
    if d_base > 0 and d_fist > 0:
        status_str = f"-> DA HIEU CHUAN (Mo: {d_base:.1f} | Nam: {d_fist:.1f})"
        cal_col = GREEN
    elif d_base > 0:
        status_str = f"-> HIEU CHUAN MO: {d_base:.1f} (Thieu an V de Nam)"
        cal_col = YELLOW


    surf.blit(font_sm.render(status_str, True, cal_col), (SCREEN_W // 2 - 290, 260))


    options = [
        ("0", "Huong dan", WHITE),
        ("1", "De",        GREEN),
        ("2", "Trung binh", YELLOW),
        ("3", "Kho",        RED),
        ("Q", "Thoat",      GRAY),
    ]
    for i, (key, label, col) in enumerate(options):
        txt = font_med.render("[" + key + "] " + label, True, col)
        surf.blit(txt, (SCREEN_W // 2 - 120, 330 + i * 42))


    hint = font_sm.render("Nhan phim de chon - Menu se tu cap nhat khi ban an", True, GRAY)
    surf.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 36))




# =============================================================================
# MAN HINH HUONG DAN
# =============================================================================
def show_instructions(surf, font_big, font_med, font_sm, clock):
    if BG_IMG:
        surf.blit(BG_IMG, (0, 0))
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surf.blit(overlay, (0, 0))
    else:
        surf.fill(DARK)
    t = font_big.render("HUONG DAN", True, YELLOW)
    surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, 35))


    lines = [
        ("Dieu khien bang TAY (MediaPipe):", CYAN),
        ("  Bop / Nam tay  ->  chim bay len", GREEN),
        ("  Mo tay ra      ->  chim roi xuong", WHITE),
        ("  * An [C] de hieu chuan tay tha long (ROM Mo)", YELLOW),
        ("  * An [V] de hieu chuan tay nam chat (ROM Nam)", YELLOW),
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
    if BG_IMG:
        surf.blit(BG_IMG, (0, 0))
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surf.blit(overlay, (0, 0))
    else:
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
    speed  = PIPE_SPEEDS[level]
    bird   = Bird(level)
    pipes  = []
    score  = 0
    paused = False


    base_interval = SPAWN_INTERVALS[level]
    current_spawn_interval = base_interval + random.randint(-15, 25)


    def new_pipe():
        base_gap = GAP_SIZES[level]
        actual_gap = base_gap + random.randint(-20, 20)
        gap_y = random.randint(60, SCREEN_H - actual_gap - 60)
        return Pipe(WIN_W + 40, gap_y, actual_gap)


    pipes.append(new_pipe())
    spawn_timer = 0


    def draw_hud():
        pygame.draw.rect(surf, WHITE, (0, 0, WIN_W, SCREEN_H), 2)
        if BG_IMG:
            overlay = pygame.Surface((SCREEN_W - WIN_W, SCREEN_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160)) # Den mo
            surf.blit(overlay, (WIN_W, 0))
        else:
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


        # --- Thanh tien trinh ROM ---
        surf.blit(font_sm.render("ROM thuc te", True, CYAN), (WIN_W + 20, 280))
        bar_w = 260
        bar_h = 20
        bar_x = WIN_W + 20
        bar_y = 305
       
        # Ve nen xam
        pygame.draw.rect(surf, GRAY, (bar_x, bar_y, bar_w, bar_h))
       
        if d_base > 0 and d_fist > 0 and d_base > d_fist:
            rom_range = d_base - d_fist
            current_effort = max(0.0, min(1.0, (d_base - current_dist) / rom_range))
           
            fill_w = int(bar_w * current_effort)
            fill_color = GREEN if is_fist else ORANGE
            pygame.draw.rect(surf, fill_color, (bar_x, bar_y, fill_w, bar_h))
           
            # Ve vach dich (Threshold)
            thr_x = bar_x + bar_w
            pygame.draw.line(surf, RED, (thr_x, bar_y - 5), (thr_x, bar_y + bar_h + 5), 3)
           
            surf.blit(font_sm.render(f"Luc hien tai: {int(current_effort*100)}%", True, WHITE), (bar_x, bar_y + 25))
        elif d_base > 0:
            current_effort = max(0.0, min(1.0, 1.0 - (current_dist / d_base)))
            fill_w = int(bar_w * current_effort)
            fill_color = GREEN if is_fist else ORANGE
            pygame.draw.rect(surf, fill_color, (bar_x, bar_y, fill_w, bar_h))
            thr_x = bar_x + int(bar_w * 0.2)
            pygame.draw.line(surf, RED, (thr_x, bar_y - 5), (thr_x, bar_y + bar_h + 5), 3)
            surf.blit(font_sm.render("Chua hieu chuan NAM (Nhan V)", True, YELLOW), (bar_x, bar_y + 25))
        else:
            surf.blit(font_sm.render("Chua hieu chuan (Nhan C va V)", True, RED), (bar_x, bar_y + 25))


        # Phim
        surf.blit(font_sm.render("-- Phim --", True, GRAY),                   (WIN_W + 20, 370))
        for i, s in enumerate(["SPACE/len: bay", "D: dung", "ESC: menu"]):
            surf.blit(font_sm.render(s, True, WHITE), (WIN_W + 20, 398 + i * 34))


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
            if BG_IMG:
                surf.blit(BG_IMG, (0, 0))
            else:
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
        if spawn_timer >= current_spawn_interval:
            spawn_timer = 0
            pipes.append(new_pipe())
            current_spawn_interval = base_interval + random.randint(-15, 25)


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
        if BG_IMG:
            surf.blit(BG_IMG, (0, 0))
        else:
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


    global BIRD_IMG, BIRD_IMG_PINK, BIRD_IMG_RED, BG_IMG
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
       
        # Load chim chinh
        BIRD_IMG = pygame.image.load(os.path.join(base_path, "bird.png")).convert_alpha()
        try:
            BIRD_IMG_PINK = pygame.image.load(os.path.join(base_path, "bird_pink.png")).convert_alpha()
            BIRD_IMG_RED = pygame.image.load(os.path.join(base_path, "bird_red.png")).convert_alpha()
        except:
            BIRD_IMG_PINK = BIRD_IMG
            BIRD_IMG_RED = BIRD_IMG
           
        # Load hinh nen FULL man hinh
        bg_path = os.path.join(base_path, "bg.png")
        bg_img_raw = pygame.image.load(bg_path).convert()
        BG_IMG = pygame.transform.scale(bg_img_raw, (SCREEN_W, SCREEN_H))
    except Exception as e:
        print("Loi load anh:", e)
        BIRD_IMG = pygame.Surface((34, 24))
        BIRD_IMG.fill(YELLOW)
        BG_IMG = None


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
        chosen = None
        while chosen is None:
            draw_menu(surf, font_big, font_med, font_sm)
            pygame.display.flip()
           
            clock.tick(30)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    cam_running = False
                    pygame.quit()
                    sys.exit()
                if ev.type == pygame.KEYDOWN:
                    global calibrate_flag, calibrate_fist_flag
                    if ev.key == pygame.K_0:
                        show_instructions(surf, font_big, font_med, font_sm, clock)
                        chosen = -1
                    elif ev.key == pygame.K_1:
                        chosen = 0
                    elif ev.key == pygame.K_2:
                        chosen = 1
                    elif ev.key == pygame.K_3:
                        chosen = 2
                    elif ev.key == pygame.K_c:
                        calibrate_flag = True
                    elif ev.key == pygame.K_v:
                        calibrate_fist_flag = True
                    elif ev.key in (pygame.K_q, pygame.K_ESCAPE):
                        cam_running = False
                        pygame.quit()
                        sys.exit()


        if chosen in (0, 1, 2):
            play(surf, fonts, clock, chosen, best_score)




if __name__ == "__main__":
    main()

