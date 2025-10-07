import pygame
import random
import sys
import os
import math
from math import hypot

WIDTH, HEIGHT = 900, 600
FPS = 700
TIME_LIMIT = 60  # 秒
MAG_SIZE = 12     # 装填数
RELOAD_TIME = 1.0  # s
SHOT_COOLDOWN = 0.12  # s
SLOWMO_TIME = 1.2
SLOWMO_SCALE = 0.4
SHAKE_DECAY = 10.0
BG_COLOR = (255, 245, 235)

SCORES = {
    "ame": 1,
    "candy": 1,
    "plush": 2,
    "hako": 3,
    "gold": 5,   # ボーナス
    "bomb": -4,  # 減点
}

def radius_for(kind, base=28):
    if kind == "plush": return base + 6
    if kind == "hako":  return base + 12
    if kind == "ame":   return base - 4
    if kind == "gold":  return base - 10
    if kind == "bomb":  return base - 2
    return base

PLATFORM_X = 80
PLATFORM_W = WIDTH - PLATFORM_X * 2
PLATFORM_THICK = 20
PLATFORM_Y_TOP = HEIGHT // 3 + 40
PLATFORM_Y_BOTTOM = PLATFORM_Y_TOP + 120
PLATFORM_COLOR = (160, 110, 50)
PLATFORM_POST_COLOR = (120, 80, 40)

# 初期化
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("お祭り射的ゲーム+")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont(None, 36)
SMALL = pygame.font.SysFont(None, 24)
BIG = pygame.font.SysFont(None, 64)

# アセット（スクリプトと同じフォルダに画像・音を置いてください）
BASE_DIR = os.path.dirname(__file__)
def load_image(name):
    try:
        return pygame.image.load(os.path.join(BASE_DIR, name)).convert_alpha()
    except Exception:
        return None

IMAGES = {
    "candy": load_image("candy.png"),
    "plush": load_image("plush.png"),
    "hako":  load_image("hako.png"),
    "ame":   load_image("ame.png"),
    "gold":  load_image("gold.png"),   # 任意
    "bomb":  load_image("bomb.png"),   # 任意
}

# ヒット音（任意）
HIT_SOUND = None
SHOT_SOUND = None
RELOAD_SOUND = None
try:
    HIT_SOUND = pygame.mixer.Sound(os.path.join(BASE_DIR, "hit.wav"))
except Exception:
    pass
try:
    SHOT_SOUND = pygame.mixer.Sound(os.path.join(BASE_DIR, "shot.wav"))
except Exception:
    pass
try:
    RELOAD_SOUND = pygame.mixer.Sound(os.path.join(BASE_DIR, "reload.wav"))
except Exception:
    pass


AVAILABLE_KINDS = [k for k, v in IMAGES.items() if v is not None] or ["candy","plush","hako","ame","gold","bomb"]
if not AVAILABLE_KINDS:
    print("エラー: candy.png / plush.png / hako.png / ame.png / gold.png / bomb.pngのいずれかを配置してください。")
    pygame.quit()
    sys.exit(1)
def draw_background(surf):
    surf.fill(BG_COLOR)
    stripe_h = 44
    for i in range(0, WIDTH // 40 + 2):
        rect = (i*40 - 20, 0, 20, stripe_h)
        color = (255, 80, 80) if i % 2 == 0 else (255, 255, 255)
        pygame.draw.rect(surf, color, rect)

    # 提灯
    for i in range(7):
        lx = 50 + i * 130
        ly = 46
        pygame.draw.line(surf, (100,50,20), (lx, ly-10), (lx, ly+10), 3)
        pygame.draw.ellipse(surf, (255, 200, 80), (lx-18, ly-2, 36, 40))
        pygame.draw.ellipse(surf, (255, 160, 50), (lx-10, ly+12, 20, 8))

    # 棚
    rtop = pygame.Rect(PLATFORM_X, PLATFORM_Y_TOP, PLATFORM_W, PLATFORM_THICK)
    rbot = pygame.Rect(PLATFORM_X, PLATFORM_Y_BOTTOM, PLATFORM_W, PLATFORM_THICK)
    pygame.draw.rect(surf, PLATFORM_COLOR, rtop, border_radius=6)
    pygame.draw.rect(surf, PLATFORM_COLOR, rbot, border_radius=6)
    post_w = 12
    pygame.draw.rect(surf, PLATFORM_POST_COLOR,
                     (PLATFORM_X + 10, PLATFORM_Y_TOP + PLATFORM_THICK, post_w, PLATFORM_Y_BOTTOM - PLATFORM_Y_TOP + 60))
    pygame.draw.rect(surf, PLATFORM_POST_COLOR,
                     (PLATFORM_X + PLATFORM_W - 10 - post_w, PLATFORM_Y_TOP + PLATFORM_THICK, post_w, PLATFORM_Y_BOTTOM - PLATFORM_Y_TOP + 60))
    for i in range(6):
        x = PLATFORM_X + 20 + i * (PLATFORM_W // 6)
        pygame.draw.line(surf, (140, 90, 40), (x, PLATFORM_Y_TOP + 4), (x + 20, PLATFORM_Y_TOP + PLATFORM_THICK - 4), 2)
        pygame.draw.line(surf, (140, 90, 40), (x, PLATFORM_Y_BOTTOM + 4), (x + 20, PLATFORM_Y_BOTTOM + PLATFORM_THICK - 4), 2)

def place_non_overlapping(kind, tier, existing, padding=6):
    radius = radius_for(kind)
    platform_y = PLATFORM_Y_TOP if tier == 0 else PLATFORM_Y_BOTTOM
    min_x = PLATFORM_X + 20 + radius
    max_x = PLATFORM_X + PLATFORM_W - 20 - radius
    for _ in range(300):
        x = random.randint(int(min_x), int(max_x))
        y = platform_y - radius - 2
        ok = True
        for ex in existing:
            dx = ex[0] - x
            dy = ex[1] - y
            sep = math.hypot(dx, dy)
            if sep < (ex[2] + radius + padding):
                ok = False
                break
        if ok:
            return x, y
    return random.randint(int(min_x), int(max_x)), platform_y - radius - 2

def clamp(v, lo, hi): return max(lo, min(hi, v))

# =========================
# パーティクル（簡易プール）
# =========================
class ParticlePool:
    def __init__(self, max_n=240):
        self.max_n = max_n
        self.data = []

    def spawn_burst(self, x, y, color, n=18):
        for _ in range(n):
            if len(self.data) >= self.max_n:
                self.data.pop(0)
            self.data.append([x, y,
                              random.uniform(-3, 3), random.uniform(-5, 1),
                              random.randint(6, 14), color, random.randint(18, 36)])

    def update(self):
        alive = []
        for p in self.data:
            p[0] += p[2]
            p[1] += p[3]
            p[6] -= 1
            p[3] += 0.2
            p[4] -= 0.25
            if p[6] > 0 and p[4] > 0:
                alive.append(p)
        self.data = alive

    def draw(self, surf):
        for p in self.data:
            pygame.draw.circle(surf, p[5], (int(p[0]), int(p[1])), max(1, int(p[4])))

# =========================
# 的
# =========================
class Target:
    def __init__(self, kind, base_x, base_y, tier, wiggle=3.0):
        self.kind = kind
        self.tier = tier
        self.base_x = base_x
        self.base_y = base_y
        self.x = float(base_x)
        self.y = float(base_y)
        self.radius = radius_for(kind)
        self.image = IMAGES.get(kind)
        self.surf = None
        self._make_surf()
        self.angle = random.uniform(0, math.pi*2)
        self.standing = True
        self.falling = False
        self.vx = 0.0
        self.vy = 0.0
        self.wiggle = wiggle  # ゆらぎ幅
        # 横移動 少しずつ（bomb/goldは速め）
        sp = random.uniform(0.2, 0.6)
        if kind in ("gold", "bomb"):
            sp = random.uniform(0.5, 1.4)
        self.move_speed = sp * (1 if random.random() < 0.5 else -1)

    def _make_surf(self):
        if self.image:
            scale = (self.radius*2) / max(1, max(self.image.get_width(), self.image.get_height()))
            w = max(1, int(self.image.get_width()*scale))
            h = max(1, int(self.image.get_height()*scale))
            self.surf = pygame.transform.smoothscale(self.image, (w, h))
        else:
            self.surf = None

    def hit_test(self, px, py):
        return hypot(self.x - px, self.y - py) <= self.radius

    def knock_over(self):
        if not self.standing: return
        self.standing = False
        self.falling = True
        self.vx = random.uniform(-180, 180)
        self.vy = -260
        if HIT_SOUND:
            try: HIT_SOUND.play()
            except: pass

    def update(self, dt, level_speed=1.0):
        if self.standing:
            self.angle += 2.5 * dt
            self.x = self.base_x + (self.wiggle * math.sin(self.angle))
            # レール内を左右にゆっくり移動
            self.base_x += self.move_speed * 40 * dt * level_speed
            rail_l = PLATFORM_X + 20 + self.radius
            rail_r = PLATFORM_X + PLATFORM_W - 20 - self.radius
            if self.base_x < rail_l or self.base_x > rail_r:
                self.move_speed *= -1
                self.base_x = clamp(self.base_x, rail_l, rail_r)
            self.y = self.base_y
        elif self.falling:
            g = 1200.0
            self.vy += g * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            if self.y > HEIGHT + 120 or self.x < -300 or self.x > WIDTH + 300:
                return False  # 退場（ゲーム側でリスポーン）
        return True

    def draw(self, surf):
        if self.surf:
            rect = self.surf.get_rect(center=(int(self.x), int(self.y)))
            surf.blit(self.surf, rect)
        else:
            # 画像ないときは色分け円
            color = (240,120,160)
            if self.kind == "plush": color = (150,180,255)
            if self.kind == "hako":  color = (240,200,120)
            if self.kind == "ame":   color = (255,200,140)
            if self.kind == "gold":  color = (255,230,80)
            if self.kind == "bomb":  color = (50,50,50)
            pygame.draw.circle(surf, color, (int(self.x), int(self.y)), self.radius)

# =========================
# ゲーム本体
# =========================
class Game:
    def __init__(self):
        self.reset(full=True)

    def reset(self, full=False):
        self.score = 0
        self.combo = 0
        self.multiplier = 1.0
        self.ammo = MAG_SIZE
        self.reload_timer = 0.0
        self.cooldown = 0.0
        self.time_left = TIME_LIMIT
        self.level = 1
        self.level_time = 0.0
        self.targets = []
        self.particles = ParticlePool()
        self.flash_timer = 0.0
        self.slowmo_timer = 0.0
        self.shake = 0.0
        self.paused = False
        self.gameover = False
        self.mouse_pos = (WIDTH//2, HEIGHT//2)
        pygame.mouse.set_visible(False)
        # 既存配置を作って重ならないように初期生成
        self.spawn_initial(14)
        if full:
            self.hiscore = self.load_hiscore()

    def load_hiscore(self):
        path = os.path.join(BASE_DIR, "hiscore.txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        except Exception:
            return 0

    def save_hiscore(self):
        try:
            with open(os.path.join(BASE_DIR, "hiscore.txt"), "w", encoding="utf-8") as f:
                f.write(str(self.hiscore))
        except Exception:
            pass

    def spawn_initial(self, count):
        placed = []
        for _ in range(count):
            kind = self.roll_kind()
            tier = random.choice([0,1])
            x,y = place_non_overlapping(kind, tier, placed, padding=10)
            r = radius_for(kind)
            placed.append((x,y,r))
            wiggle = 3.0 + self.level * 0.7
            self.targets.append(Target(kind, x, y, tier, wiggle=wiggle))

    def roll_kind(self):
        # 時間/レベルで金的や爆弾の確率が変化
        # 基本: 通常80%, gold 10-18%, bomb 5-10%
        gold_p = clamp(0.10 + (self.level-1)*0.02, 0.10, 0.18)
        bomb_p = clamp(0.06 + (self.level-1)*0.015, 0.06, 0.10)
        r = random.random()
        if r < gold_p:
            return "gold"
        if r < gold_p + bomb_p:
            return "bomb"
        return random.choice(["candy","plush","hako","ame"])

    def respawn_one(self):
        kind = self.roll_kind()
        tier = random.choice([0,1])
        placed = [(t.base_x, t.base_y, t.radius) for t in self.targets if t.standing]
        x,y = place_non_overlapping(kind, tier, placed, padding=10)
        wiggle = 3.0 + self.level * 0.7
        self.targets.append(Target(kind, x, y, tier, wiggle=wiggle))

    def shoot(self, pos):
        if self.gameover or self.paused:
            return
        if self.reload_timer > 0 or self.cooldown > 0:
            return
        if self.ammo <= 0:
            # 自動リロード
            self.begin_reload()
            return

        self.ammo -= 1
        self.cooldown = SHOT_COOLDOWN
        if SHOT_SOUND:
            try: SHOT_SOUND.play()
            except: pass
        self.shake += 3.0

        mx, my = pos
        hit_any = False
        random.shuffle(self.targets)
        for t in self.targets:
            if t.standing and t.hit_test(mx, my):
                hit_any = True
                t.knock_over()
                # スコア計算
                base = SCORES.get(t.kind, 1)
                if t.kind == "bomb":
                    self.combo = 0
                    self.multiplier = 1.0
                else:
                    self.combo += 1
                    self.multiplier = clamp(1.0 + self.combo*0.1, 1.0, 3.0)
                add = int(base * self.multiplier)
                self.score += add
                # 演出
                col = (255,200,140)
                if t.kind == "candy": col = (255,150,200)
                if t.kind == "plush": col = (200,200,255)
                if t.kind == "hako":  col = (255,230,160)
                if t.kind == "ame":   col = (255,200,140)
                if t.kind == "gold":  col = (255,230,90)
                if t.kind == "bomb":  col = (90,90,90)
                self.particles.spawn_burst(t.x, t.y, col, n=22 if t.kind!="bomb" else 14)
                self.flash_timer = 0.06
                if t.kind == "gold":
                    self.slowmo_timer = SLOWMO_TIME
                break
        if not hit_any:
            # ミスでコンボリセット（優しめ：軽減）
            self.combo = 0
            self.multiplier = 1.0

    def begin_reload(self):
        if self.reload_timer <= 0 and self.ammo < MAG_SIZE:
            self.reload_timer = RELOAD_TIME
            if RELOAD_SOUND:
                try: RELOAD_SOUND.play()
                except: pass

    def update(self, dt):
        if self.gameover or self.paused:
            return
        # スローモーション
        slo = 1.0
        if self.slowmo_timer > 0:
            self.slowmo_timer -= dt
            slo = SLOWMO_SCALE

        dt_eff = dt * slo
        self.time_left -= dt_eff
        self.level_time += dt_eff

        # レベルアップ（20秒毎）
        while self.level_time >= 20 and self.level < 6:
            self.level += 1
            self.level_time -= 20
            # レベル上昇時にスポーンを少し増やす
            for _ in range(2):
                self.respawn_one()

        # 弾関連
        if self.cooldown > 0:
            self.cooldown -= dt
        if self.reload_timer > 0:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.ammo = MAG_SIZE

        # 的の更新＆掃除
        level_speed = 1.0 + (self.level-1)*0.15
        alive = []
        removed = 0
        for t in self.targets:
            keep = t.update(dt_eff, level_speed=level_speed)
            if keep:
                alive.append(t)
            else:
                removed += 1
        self.targets = alive
        # 足りなければリスポーン
        target_cap = 14 + (self.level-1)*2
        while len(self.targets) < target_cap:
            self.respawn_one()

        # 演出
        self.particles.update()
        if self.flash_timer > 0:
            self.flash_timer -= dt
        if self.shake > 0:
            self.shake -= SHAKE_DECAY * dt
            if self.shake < 0: self.shake = 0

        # タイムアップ
        if self.time_left <= 0:
            self.gameover = True
            self.time_left = 0
            if self.score > getattr(self, "hiscore", 0):
                self.hiscore = self.score
                self.save_hiscore()

    def draw(self, surf):
        # 画面シェイク
        ox = int(random.uniform(-self.shake, self.shake))
        oy = int(random.uniform(-self.shake, self.shake))

        draw_background(surf)
        # 的
        for t in self.targets:
            t.draw(surf)
        # パーティクル
        self.particles.draw(surf)

        # ヒットフラッシュ
        if self.flash_timer > 0:
            alpha = int(120 * (self.flash_timer/0.06))
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((255,255,255, alpha))
            surf.blit(flash, (0,0))

        # UI
        bar = pygame.Surface((WIDTH, 48), pygame.SRCALPHA)
        pygame.draw.rect(bar, (255,255,255,210), bar.get_rect())
        surf.blit(bar, (0, HEIGHT-52))
        txt = FONT.render(f"Score {self.score}", True, (30,30,30))
        mtxt = FONT.render(f"x{self.multiplier:.1f}  Combo {self.combo}", True, (60,60,60))
        ttxt = FONT.render(f"Time {int(self.time_left)}", True, (30,30,30))
        levt = FONT.render(f"Lv.{self.level}", True, (30,30,30))
        ammo_str = "|" * self.ammo + "." * (MAG_SIZE - self.ammo)
        atxt = FONT.render(f"[{ammo_str}]", True, (30,30,30))
        surf.blit(txt, (12, HEIGHT-46))
        surf.blit(mtxt, (190, HEIGHT-46))
        surf.blit(ttxt, (540, HEIGHT-46))
        surf.blit(levt, (700, HEIGHT-46))
        surf.blit(atxt, (800-20, HEIGHT-46))

        # スローモーション表示
        if self.slowmo_timer > 0:
            s = SMALL.render("SLOW", True, (20,20,20))
            pygame.draw.rect(surf, (255,255,255), (10, 60, 84, 28), border_radius=6)
            surf.blit(s, (20, 64))

        # ポーズ／ゲームオーバー
        if self.paused:
            msg = BIG.render("PAUSED", True, (255,255,255))
            surf.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 - 36))
        if self.gameover:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(170)
            overlay.fill((10,10,40))
            surf.blit(overlay, (0,0))
            over = BIG.render(f"Time up! Score: {self.score}", True, (255,255,255))
            surf.blit(over, (WIDTH//2 - over.get_width()//2, HEIGHT//2 - 60))
            hs = FONT.render(f"High Score: {self.hiscore}", True, (230,230,230))
            surf.blit(hs, (WIDTH//2 - hs.get_width()//2, HEIGHT//2 + 4))
            sub = FONT.render("Press R to restart / ESC to quit", True, (220,220,220))
            surf.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2 + 44))

        # クロスヘア
        mx, my = self.mouse_pos
        pygame.draw.circle(surf, (20,20,20), (mx, my), 18, 2)
        pygame.draw.line(surf, (20,20,20), (mx-24, my), (mx-6, my), 2)
        pygame.draw.line(surf, (20,20,20), (mx+6, my), (mx+24, my), 2)
        pygame.draw.line(surf, (20,20,20), (mx, my-24), (mx, my-6), 2)
        pygame.draw.line(surf, (20,20,20), (mx, my+6), (mx, my+24), 2)

        # シェイクオフセット反映（最後にまとめて）
        if self.shake > 0 and not (self.paused or self.gameover):
            screen_scroll = pygame.Surface((WIDTH, HEIGHT))
            screen_scroll.blit(surf, (0,0))
            surf.blit(screen_scroll, (ox, oy))

# =========================
# メインループ
# =========================
def main():
    game = Game()
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    if game.gameover:
                        game.reset()
                    else:
                        game.begin_reload()
                elif event.key == pygame.K_p:
                    if not game.gameover:
                        game.paused = not game.paused

            elif event.type == pygame.MOUSEMOTION:
                game.mouse_pos = event.pos

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左クリック
                    game.shoot(event.pos)

        game.update(dt)
        game.draw(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()