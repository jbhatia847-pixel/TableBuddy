"""
Table Buddy Mobile / Arcade
---------------------------
Features 6 animated expressions, procedural audio, weather report,
clock/date screen, eye-blinking, and custom visual particle effects.

Controls:
    1-6 / Tap 1-6 -> Switch expressions (Happy, Sleepy, Awkward, Angry, Fear, Relax)
    CTRL or T     -> Toggle Clock / Date screen
    W             -> Toggle Weather report
    ESC           -> Quit
"""

import sys
import math
import random
import json
import ssl
import threading
import urllib.request
from datetime import datetime
import pygame

# Initialize Pygame & Audio
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=1)

# ---------------------------------------------------------------------------
# Display Setup
# ---------------------------------------------------------------------------
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN if WIDTH > 800 else 0)
pygame.display.set_caption("Table Buddy Arcade")

BLACK = (10, 10, 18)
WHITE = (255, 255, 255)

EXPR_COLORS = {
    1: (0, 220, 255),    # Cyan - Happy
    2: (100, 140, 255),  # Soft Blue - Sleep
    3: (255, 180, 50),   # Yellow/Amber - Awkward
    4: (255, 60, 90),    # Red - Angry
    5: (180, 70, 255),   # Purple - Fear
    6: (80, 240, 160),   # Mint Green - Relax
}
TIME_COLOR = (255, 210, 50)  # Amber for Clock

font_sm = pygame.font.SysFont("consolas", max(12, int(HEIGHT * 0.020)))
font_md = pygame.font.SysFont("consolas", max(18, int(HEIGHT * 0.030)), bold=True)
font_lg = pygame.font.SysFont("consolas", max(32, int(HEIGHT * 0.050)), bold=True)

clock = pygame.time.Clock()

CENTER_X, CENTER_Y = WIDTH // 2, HEIGHT // 2
SCREEN_WIDTH = int(min(WIDTH, HEIGHT) * 0.75)
SCREEN_HEIGHT = int(min(WIDTH, HEIGHT) * 0.50)

# State Variables
current_expression = 1
change_time = pygame.time.get_ticks()
last_frame_time = pygame.time.get_ticks()
mode = "face"  # "face", "time", "weather"

blink_timer = 0.0
is_blinking = False

EXPR_TEXTS = {
    1: "I am feeling super happy today!",
    2: "I am so sleepy... zZZz",
    3: "Uh... this is kinda awkward",
    4: "I am really angry right now!",
    5: "Eek! I am so scared!!",
    6: "Ah... completely calm and relaxed ~"
}

# ---------------------------------------------------------------------------
# Advanced Procedural Sound Synthesizer
# ---------------------------------------------------------------------------
def generate_synth_sound(freq_start, freq_end, duration=0.18, wave_type='sine'):
    sample_rate = 22050
    total_samples = int(sample_rate * duration)
    buf = bytearray()
    for i in range(total_samples):
        t = i / total_samples
        freq = freq_start + (freq_end - freq_start) * t
        phase = 2 * math.pi * freq * (i / sample_rate)
        
        if wave_type == 'square':
            val = 12000 if math.sin(phase) > 0 else -12000
        elif wave_type == 'saw':
            val = int(12000 * (2 * (phase / (2 * math.pi) - math.floor(0.5 + phase / (2 * math.pi)))))
        elif wave_type == 'noise':
            val = random.randint(-12000, 12000)
        else:  # Sine
            val = int(14000 * math.sin(phase))
        
        envelope = math.sin(math.pi * t)
        val = int(val * envelope)
        buf.extend(val.to_bytes(2, byteorder='little', signed=True))
        
    return pygame.mixer.Sound(buffer=bytes(buf))

SOUNDS = {
    1: generate_synth_sound(523, 1046, 0.20, 'sine'),     # Happy high chirp
    2: generate_synth_sound(280, 120, 0.35, 'sine'),      # Sleepy drop
    3: generate_synth_sound(350, 280, 0.22, 'square'),    # Awkward boop
    4: generate_synth_sound(180, 70, 0.28, 'saw'),        # Angry bass growl
    5: generate_synth_sound(800, 200, 0.22, 'noise'),     # Fear screech
    6: generate_synth_sound(330, 493, 0.30, 'sine'),      # Relax chord
    'time': generate_synth_sound(523, 659, 0.15, 'sine'),
    'weather': generate_synth_sound(587, 880, 0.18, 'sine')
}

def play_sound(key):
    if key in SOUNDS:
        SOUNDS[key].play()

# ---------------------------------------------------------------------------
# Weather Fetcher
# ---------------------------------------------------------------------------
weather_data = {"temp": "--", "cond": "Fetching Weather...", "is_rainy": False}

def fetch_weather():
    global weather_data
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        url = "https://api.open-meteo.com/v1/forecast?latitude=28.61&longitude=77.20&current_weather=true"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
            data = json.loads(response.read().decode())
            curr = data.get("current_weather", {})
            temp = curr.get("temperature", "--")
            code = curr.get("weathercode", 0)
            
            cond_map = {
                0: "Clear Sky", 1: "Mainly Clear", 2: "Partly Cloudy", 3: "Overcast",
                45: "Foggy", 48: "Depositing Rime Fog", 51: "Light Drizzle",
                61: "Slight Rain", 63: "Moderate Rain", 65: "Heavy Rain",
                71: "Slight Snow", 80: "Rain Showers", 95: "Thunderstorm"
            }
            
            weather_data["temp"] = f"{temp} Celsius"
            weather_data["cond"] = cond_map.get(code, "Clear Sky")
            weather_data["is_rainy"] = code in [51, 61, 63, 65, 80, 95]
    except Exception:
        weather_data["temp"] = "24 Celsius"
        weather_data["cond"] = "Partly Cloudy"
        weather_data["is_rainy"] = False

threading.Thread(target=fetch_weather, daemon=True).start()

# ---------------------------------------------------------------------------
# Math & Visual Helpers
# ---------------------------------------------------------------------------
def lerp(a, b, t):
    return a + (b - a) * t

def ease_out_elastic(t):
    if t == 0 or t == 1:
        return t
    return math.pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1

# Background and Particle Systems
bg_particles = [
    {"x": random.uniform(0, WIDTH), "y": random.uniform(0, HEIGHT), "r": random.uniform(1.5, 3.5), "speed": random.uniform(15, 45)}
    for _ in range(30)
]
special_particles = []
zzz_particles = []
rain_particles = [{"x": random.uniform(0, WIDTH), "y": random.uniform(0, HEIGHT), "len": random.uniform(10, 20), "speed": random.uniform(200, 400)} for _ in range(40)]
sweat_y = 0.0

def draw_arcade_bezel(rect, color):
    glow_surf = pygame.Surface((rect.width + 60, rect.height + 60), pygame.SRCALPHA)
    for i in range(4, 0, -1):
        alpha = int(30 / i)
        g_rect = pygame.Rect(30 - i * 5, 30 - i * 5, rect.width + i * 10, rect.height + i * 10)
        pygame.draw.rect(glow_surf, (*color, alpha), g_rect, width=6, border_radius=30)
    screen.blit(glow_surf, (rect.x - 30, rect.y - 30))

    pygame.draw.rect(screen, (20, 22, 32), rect.inflate(30, 30), border_radius=24)
    pygame.draw.rect(screen, color, rect.inflate(30, 30), width=3, border_radius=24)
    
    pygame.draw.rect(screen, (8, 10, 18), rect, border_radius=18)
    pygame.draw.rect(screen, color, rect, width=4, border_radius=18)

    for y in range(rect.top + 4, rect.bottom - 4, 6):
        pygame.draw.line(screen, (0, 0, 0, 90), (rect.left + 4, y), (rect.right - 4, y), 2)

def draw_eyes_and_mouth(expr, rect, color, blinking):
    global sweat_y
    cx, cy = rect.center
    sw, sh = rect.width, rect.height
    eye_r = int(sh * 0.15)
    off_x = int(sw * 0.22)
    off_y = int(sh * 0.16)
    
    lx, ly = cx - off_x, cy - off_y
    rx, ry = cx + off_x, cy - off_y

    # If blinking, render closed eyes for all expressions
    if blinking and expr not in [2, 6]:
        pygame.draw.line(screen, color, (lx - eye_r, ly), (lx + eye_r, ly), 5)
        pygame.draw.line(screen, color, (rx - eye_r, ry), (rx + eye_r, ry), 5)
        m_rect = pygame.Rect(0, 0, int(sw * 0.18), int(sh * 0.18))
        m_rect.center = (cx, cy + int(sh * 0.18))
        pygame.draw.arc(screen, color, m_rect, 3.4, 6.0, 4)
        return

    # 1. HAPPY
    if expr == 1:
        for ex, ey in [(lx, ly), (rx, ry)]:
            pygame.draw.circle(screen, color, (ex, ey), eye_r)
            pygame.draw.circle(screen, WHITE, (ex + int(eye_r*0.25), ey - int(eye_r*0.28)), int(eye_r*0.35))
            pygame.draw.circle(screen, WHITE, (ex - int(eye_r*0.28), ey + int(eye_r*0.28)), int(eye_r*0.20))
        m_rect = pygame.Rect(0, 0, int(sw * 0.22), int(sh * 0.26))
        m_rect.center = (cx, cy + int(sh * 0.2))
        pygame.draw.arc(screen, color, m_rect, math.pi, 2 * math.pi, 5)
        pygame.draw.line(screen, color, m_rect.topleft, m_rect.topright, 5)

    # 2. SLEEP
    elif expr == 2:
        for ex, ey in [(lx, ly), (rx, ry)]:
            arc_r = pygame.Rect(ex - eye_r, ey - eye_r, eye_r * 2, eye_r * 2)
            pygame.draw.arc(screen, color, arc_r, 3.3, 6.1, 5)
        pygame.draw.circle(screen, color, (cx, cy + int(sh * 0.2)), int(sh * 0.08), 4)

        if random.random() < 0.06:
            zzz_particles.append({"x": rx + 15, "y": ry - 10, "size": 16, "alpha": 255})
        for z in zzz_particles[:]:
            z["y"] -= 0.8
            z["x"] += 0.3
            z["alpha"] -= 2
            if z["alpha"] <= 0:
                zzz_particles.remove(z)
            else:
                z_f = pygame.font.SysFont("consolas", int(z["size"]), bold=True)
                txt = z_f.render("Z", True, color)
                screen.blit(txt, (z["x"], z["y"]))

    # 3. AWKWARD
    elif expr == 3:
        for ex, ey in [(lx, ly), (rx, ry)]:
            pygame.draw.circle(screen, color, (ex, ey), eye_r, 4)
            pygame.draw.circle(screen, color, (ex + int(eye_r*0.4), ey), int(eye_r*0.45))
        pts = [(cx - 30 + i*8, cy + int(sh*0.2) + (6 if i%2==0 else -6)) for i in range(8)]
        pygame.draw.lines(screen, color, False, pts, 4)
        
        sweat_y = (sweat_y + 1.2) % (sh * 0.38)
        pygame.draw.circle(screen, (0, 200, 255), (rx + int(eye_r*1.4), ly + int(sweat_y)), 6)

    # 4. ANGRY
    elif expr == 4:
        for ex, ey in [(lx, ly), (rx, ry)]:
            pygame.draw.circle(screen, color, (ex, ey), eye_r)
        pygame.draw.line(screen, color, (lx - eye_r, ly - eye_r - 8), (lx + eye_r, ly - eye_r + 8), 7)
        pygame.draw.line(screen, color, (rx - eye_r, ry - eye_r + 8), (rx + eye_r, ry - eye_r - 8), 7)
        pygame.draw.line(screen, color, (cx - 28, cy + int(sh*0.2)), (cx + 28, cy + int(sh*0.2)), 6)

    # 5. FEAR
    elif expr == 5:
        for ex, ey in [(lx, ly), (rx, ry)]:
            pygame.draw.circle(screen, color, (ex, ey), int(eye_r * 1.25), 4)
            pygame.draw.circle(screen, color, (ex, ey), int(eye_r * 0.35))
        m_y = cy + int(sh * 0.2) + random.randint(-2, 2)
        pygame.draw.ellipse(screen, color, (cx - 16, m_y, 32, 22), 4)

    # 6. RELAX
    elif expr == 6:
        for ex, ey in [(lx, ly), (rx, ry)]:
            arc_r = pygame.Rect(ex - eye_r, ey - eye_r, eye_r * 2, eye_r * 2)
            pygame.draw.arc(screen, color, arc_r, 0.2, 2.9, 5)
        m_rect = pygame.Rect(0, 0, int(sw * 0.16), int(sh * 0.16))
        m_rect.center = (cx, cy + int(sh * 0.18))
        pygame.draw.arc(screen, color, m_rect, 3.4, 6.0, 5)

# ---------------------------------------------------------------------------
# Main Loop
# ---------------------------------------------------------------------------
running = True
while running:
    now_ms = pygame.time.get_ticks()
    dt = max(0.001, (now_ms - last_frame_time) / 1000.0)
    last_frame_time = now_ms

    # Blinking Timer Logic
    blink_timer += dt
    if blink_timer > 3.8:
        is_blinking = True
        if blink_timer > 3.95:
            is_blinking = False
            blink_timer = 0.0

    active_color = TIME_COLOR if mode == "time" else EXPR_COLORS[current_expression]
    screen.fill(BLACK)

    # Drifting Background Particles
    for p in bg_particles:
        p["y"] = (p["y"] - p["speed"] * dt) % HEIGHT
        pygame.draw.circle(screen, active_color, (int(p["x"]), int(p["y"])), max(1, int(p["r"])))

    # Special Particle Effects based on active expression
    if mode == "face":
        if current_expression == 4 and random.random() < 0.3:  # Angry Embers
            special_particles.append({"x": random.uniform(CENTER_X - 150, CENTER_X + 150), "y": CENTER_Y + 100, "vy": -random.uniform(50, 150), "r": random.uniform(2, 5), "life": 1.0})
        elif current_expression == 1 and random.random() < 0.2:  # Happy Sparkles
            special_particles.append({"x": random.uniform(CENTER_X - 180, CENTER_X + 180), "y": random.uniform(CENTER_Y - 100, CENTER_Y + 100), "vy": -random.uniform(20, 60), "r": random.uniform(2, 4), "life": 1.0})

        for sp in special_particles[:]:
            sp["y"] += sp["vy"] * dt
            sp["life"] -= dt
            if sp["life"] <= 0:
                special_particles.remove(sp)
            else:
                alpha = int(255 * sp["life"])
                p_surf = pygame.Surface((int(sp["r"]*2), int(sp["r"]*2)), pygame.SRCALPHA)
                pygame.draw.circle(p_surf, (*active_color, alpha), (int(sp["r"]), int(sp["r"])), int(sp["r"]))
                screen.blit(p_surf, (sp["x"], sp["y"]))

    # Elastic Switch Scale & Breathing
    elapsed = now_ms - change_time
    scale = lerp(0.6, 1.0, ease_out_elastic(min(1.0, elapsed / 400.0)))
    breathe = math.sin(now_ms / 450.0) * 6

    # Screen Shake for Fear
    shake_x = random.randint(-4, 4) if (mode == "face" and current_expression == 5) else 0
    shake_y = random.randint(-4, 4) if (mode == "face" and current_expression == 5) else 0

    sw = int(SCREEN_WIDTH * scale)
    sh = int((SCREEN_HEIGHT + breathe) * scale)
    screen_rect = pygame.Rect(0, 0, sw, sh)
    screen_rect.center = (CENTER_X + shake_x, CENTER_Y + shake_y - int(HEIGHT * 0.04))

    draw_arcade_bezel(screen_rect, active_color)

    # Mode Rendering
    if mode == "time":
        now = datetime.now()
        date_str = now.strftime("%A, %d %B %Y")
        time_str = now.strftime("%H:%M:%S") if (now_ms // 500) % 2 == 0 else now.strftime("%H %M %S")
        
        lbl_surf = font_sm.render("TIME AND DATE", True, WHITE)
        d_surf = font_md.render(date_str, True, TIME_COLOR)
        t_surf = font_lg.render(time_str, True, TIME_COLOR)
        
        screen.blit(lbl_surf, (CENTER_X - lbl_surf.get_width() // 2, screen_rect.centery - 65))
        screen.blit(d_surf, (CENTER_X - d_surf.get_width() // 2, screen_rect.centery - 30))
        screen.blit(t_surf, (CENTER_X - t_surf.get_width() // 2, screen_rect.centery + 15))

    elif mode == "weather":
        lbl_surf = font_sm.render("WEATHER REPORT", True, WHITE)
        t_surf = font_lg.render(f"Temperature: {weather_data['temp']}", True, active_color)
        c_surf = font_md.render(f"Condition: {weather_data['cond']}", True, WHITE)
        
        screen.blit(lbl_surf, (CENTER_X - lbl_surf.get_width() // 2, screen_rect.centery - 65))
        screen.blit(t_surf, (CENTER_X - t_surf.get_width() // 2, screen_rect.centery - 25))
        screen.blit(c_surf, (CENTER_X - c_surf.get_width() // 2, screen_rect.centery + 25))

        # Rain animation on weather screen
        if weather_data["is_rainy"]:
            for r in rain_particles:
                r["y"] = (r["y"] + r["speed"] * dt) % HEIGHT
                pygame.draw.line(screen, (100, 200, 255, 180), (r["x"], r["y"]), (r["x"], r["y"] + r["len"]), 2)

    else:
        draw_eyes_and_mouth(current_expression, screen_rect, active_color, is_blinking)

        txt_surf = font_md.render(EXPR_TEXTS[current_expression], True, active_color)
        bubble_rect = txt_surf.get_rect(center=(CENTER_X, screen_rect.bottom + int(HEIGHT * 0.05)))
        pygame.draw.rect(screen, (20, 22, 35), bubble_rect.inflate(30, 16), border_radius=12)
        pygame.draw.rect(screen, active_color, bubble_rect.inflate(30, 16), width=2, border_radius=12)
        screen.blit(txt_surf, bubble_rect)

    # Touch UI Control Bar
    btn_w = min(50, int(WIDTH / 10))
    btn_h = int(HEIGHT * 0.07)
    btn_y = HEIGHT - btn_h - 15
    btn_rects = {}

    for i in range(1, 7):
        bx = int(WIDTH * 0.03) + (i - 1) * int(btn_w * 1.12)
        rect = pygame.Rect(bx, btn_y, btn_w, btn_h)
        btn_rects[i] = rect
        bg = EXPR_COLORS[i] if (mode == "face" and current_expression == i) else (30, 30, 45)
        pygame.draw.rect(screen, bg, rect, border_radius=8)
        b_txt = font_sm.render(str(i), True, WHITE)
        screen.blit(b_txt, b_txt.get_rect(center=rect.center))

    time_rect = pygame.Rect(WIDTH - int(WIDTH * 0.32), btn_y, int(WIDTH * 0.14), btn_h)
    wx_rect = pygame.Rect(WIDTH - int(WIDTH * 0.16), btn_y, int(WIDTH * 0.14), btn_h)

    pygame.draw.rect(screen, TIME_COLOR if mode == "time" else (30, 30, 45), time_rect, border_radius=8)
    pygame.draw.rect(screen, (0, 200, 220) if mode == "weather" else (30, 30, 45), wx_rect, border_radius=8)

    t_btn_txt = font_sm.render("TIME", True, WHITE)
    w_btn_txt = font_sm.render("WEATHER", True, WHITE)
    screen.blit(t_btn_txt, t_btn_txt.get_rect(center=time_rect.center))
    screen.blit(w_btn_txt, w_btn_txt.get_rect(center=wx_rect.center))

    # Input Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key in (pygame.K_LCTRL, pygame.K_RCTRL, pygame.K_t):
                mode = "time"
                change_time = now_ms
                play_sound('time')
            elif event.key == pygame.K_w:
                mode = "weather"
                change_time = now_ms
                play_sound('weather')
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6):
                current_expression = int(event.unicode)
                mode = "face"
                change_time = now_ms
                play_sound(current_expression)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            pos = event.pos
            for btn_num, rect in btn_rects.items():
                if rect.collidepoint(pos):
                    current_expression = btn_num
                    mode = "face"
                    change_time = now_ms
                    play_sound(current_expression)

            if time_rect.collidepoint(pos):
                mode = "time"
                change_time = now_ms
                play_sound('time')

            if wx_rect.collidepoint(pos):
                mode = "weather"
                change_time = now_ms
                play_sound('weather')

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()