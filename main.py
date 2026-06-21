"""
Run: python flappy_bird.py
Requires: pip install kivy
"""

import random
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import (
    Color, Rectangle, Ellipse, RoundedRectangle, Triangle, PushMatrix,
    PopMatrix, Rotate, Translate
)
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.properties import NumericProperty, BooleanProperty

# ── Responsive dimensions ─────────────────────────────────────────────────────
# Read actual screen size BEFORE Window.size is forced anywhere.
# On Android/iOS kivy sets Window.size to the real display automatically.
# On desktop we default to a portrait phone ratio.

def _init_dims():
    w = Window.width  or 480
    h = Window.height or 720
    # Keep a portrait aspect; on landscape desktop just use 480×720
    if w > h:
        w, h = 480, 720
    return w, h

WIN_W, WIN_H = _init_dims()

# Derive all gameplay constants from screen size so they scale properly
SCALE        = WIN_H / 720          # baseline ratio
FPS          = 60
GRAVITY      = -0.55  * SCALE
FLAP_VEL     = 9.5   * SCALE
PIPE_WIDTH   = int(72  * SCALE)
PIPE_GAP     = int(190 * SCALE)
PIPE_SPEED   = 3.2   * SCALE
PIPE_SPAWN_X = WIN_W + 20
GROUND_H     = int(90  * SCALE)
BIRD_W       = int(44  * SCALE)
BIRD_H       = int(34  * SCALE)
PIPE_MIN_H   = int(80  * SCALE)
PIPE_MAX_H   = WIN_H - PIPE_GAP - int(80 * SCALE)

# Palette
SKY_TOP   = (0.27, 0.65, 0.97, 1)
SKY_BOT   = (0.60, 0.85, 1.00, 1)
GROUND_C  = (0.42, 0.28, 0.15, 1)
GRASS_C   = (0.27, 0.72, 0.22, 1)
PIPE_BODY = (0.22, 0.69, 0.17, 1)
PIPE_RIM  = (0.17, 0.56, 0.12, 1)
BIRD_BODY = (0.98, 0.82, 0.15, 1)
BIRD_WING = (0.98, 0.70, 0.10, 1)
BIRD_EYE  = (1.00, 1.00, 1.00, 1)
BIRD_PUP  = (0.10, 0.10, 0.10, 1)
BIRD_BEAK = (0.98, 0.55, 0.10, 1)



# ── Pipe pair ─────────────────────────────────────────────────────────────────

class PipePair(Widget):
    passed = BooleanProperty(False)

    def __init__(self, x, gap_y, **kw):
        super().__init__(**kw)
        self.size    = (PIPE_WIDTH, WIN_H)
        self.pos     = (x, 0)
        self.gap_y   = gap_y
        self.gap_top = gap_y + PIPE_GAP
        self._draw()

    def _draw(self):
        self.canvas.clear()
        x  = self.x
        gb = self.gap_y
        gt = self.gap_top
        rw = PIPE_WIDTH + int(14 * SCALE)
        rh = int(22 * SCALE)

        with self.canvas:
            # bottom body
            Color(*PIPE_BODY)
            Rectangle(pos=(x, GROUND_H), size=(PIPE_WIDTH, gb - GROUND_H))
            # bottom rim
            Color(*PIPE_RIM)
            RoundedRectangle(pos=(x - int(7*SCALE), gb - rh),
                             size=(rw, rh), radius=[4]*4)
            # bottom highlight
            Color(1, 1, 1, 0.12)
            Rectangle(pos=(x + int(6*SCALE), GROUND_H),
                      size=(int(10*SCALE), gb - GROUND_H - rh))

            # top body
            Color(*PIPE_BODY)
            Rectangle(pos=(x, gt), size=(PIPE_WIDTH, WIN_H - gt))
            # top rim
            Color(*PIPE_RIM)
            RoundedRectangle(pos=(x - int(7*SCALE), gt),
                             size=(rw, rh), radius=[4]*4)
            # top highlight
            Color(1, 1, 1, 0.12)
            Rectangle(pos=(x + int(6*SCALE), gt + rh),
                      size=(int(10*SCALE), WIN_H - gt - rh))

    def update(self):
        self.x -= PIPE_SPEED
        self._draw()

    @property
    def rect_bottom(self):
        return (self.x, GROUND_H, PIPE_WIDTH, self.gap_y - GROUND_H)

    @property
    def rect_top(self):
        return (self.x, self.gap_top, PIPE_WIDTH, WIN_H - self.gap_top)


# ── Bird ──────────────────────────────────────────────────────────────────────

class Bird(Widget):
    vy = NumericProperty(0)

    # Wing animation frames: how far the wing hangs below centre (normalised)
    WING_CYCLE = [0.30, 0.55, 0.85, 0.55]

    def __init__(self, **kw):
        super().__init__(**kw)
        self.size      = (BIRD_W, BIRD_H)
        self.pos       = (WIN_W * 0.28, WIN_H * 0.55)
        self._wing_t   = 0
        self._wing_idx = 0
        self._dead     = False
        self._tilt     = 0.0   # current visual angle in degrees (+up / -down)
        self._draw()

    # ── physics ───────────────────────────────────────────────────────────────

    def flap(self):
        if not self._dead:
            self.vy    = FLAP_VEL
            self._tilt = 25.0        # snap nose-up on flap
            self._wing_idx = 0

    def update(self):
        if self._dead:
            self.vy    = max(self.vy + GRAVITY * 2.5, -20 * SCALE)
            self.y    += self.vy
            self._tilt = max(self._tilt - 4, -90)   # spin nose-down on death
            self._draw()
            return

        self.vy = max(self.vy + GRAVITY, -12 * SCALE)
        self.y += self.vy

        # Smooth tilt:
        #   • positive vy (rising)  → tilt toward +25°  (nose up)
        #   • negative vy (falling) → tilt toward -45°  (nose down / dive)
        target = 25.0 if self.vy > 0 else max(-45.0, self.vy * 5 / SCALE)
        self._tilt += (target - self._tilt) * 0.18   # lerp speed

        # Wing animation
        self._wing_t += 1
        if self._wing_t % 5 == 0:
            self._wing_idx = (self._wing_idx + 1) % len(self.WING_CYCLE)

        self._draw()

    def die(self):
        self._dead = True

    # ── drawing with rotation ─────────────────────────────────────────────────

    def _draw(self):
        self.canvas.clear()
        x, y = self.pos
        w, h = BIRD_W, BIRD_H
        cx = x + w / 2
        cy = y + h / 2

        wing_drop = self.WING_CYCLE[self._wing_idx] * (h * 0.45)

        with self.canvas:
            PushMatrix()
            # Rotate around bird centre; positive = CCW (nose-up)
            Rotate(angle=self._tilt, origin=(cx, cy))

            # drop shadow
            Color(0, 0, 0, 0.12)
            Ellipse(pos=(cx - 14*SCALE, y - 5*SCALE), size=(28*SCALE, 8*SCALE))

            # wing (drawn behind body)
            Color(*BIRD_WING)
            Ellipse(pos=(cx - 10*SCALE, cy - wing_drop), size=(22*SCALE, 13*SCALE))

            # body
            Color(*BIRD_BODY)
            Ellipse(pos=(x + 2*SCALE, y + 2*SCALE), size=(w - 4*SCALE, h - 4*SCALE))

            # belly highlight
            Color(1, 1, 1, 0.20)
            Ellipse(pos=(cx - 6*SCALE, cy - 2*SCALE), size=(14*SCALE, 9*SCALE))

            # eye white
            Color(*BIRD_EYE)
            Ellipse(pos=(cx + 3*SCALE, cy + 3*SCALE), size=(12*SCALE, 11*SCALE))

            # pupil
            Color(*BIRD_PUP)
            Ellipse(pos=(cx + 7*SCALE, cy + 5*SCALE), size=(5*SCALE, 5*SCALE))

            # beak — points right; rotation handles the tilt visually
            Color(*BIRD_BEAK)
            Triangle(points=[
                cx + 13*SCALE, cy + 3*SCALE,
                cx + 22*SCALE, cy + 1*SCALE,
                cx + 13*SCALE, cy - 2*SCALE,
            ])

            PopMatrix()

    # ── hitbox (inset for fairness) ───────────────────────────────────────────

    @property
    def hitbox(self):
        m = int(5 * SCALE)
        return (self.x + m, self.y + m, BIRD_W - m * 2, BIRD_H - m * 2)


# ── HUD ───────────────────────────────────────────────────────────────────────

class HUD(FloatLayout):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.size = (WIN_W, WIN_H)

        self.score_lbl = Label(
            text='0', font_size=dp(52), bold=True,
            color=(1, 1, 1, 1), outline_color=(0, 0, 0, 1), outline_width=3,
            pos_hint={'center_x': 0.5, 'top': 0.92},
            size_hint=(None, None), size=(WIN_W, dp(70))
        )
        self.add_widget(self.score_lbl)

        self.msg_lbl = Label(
            text='Tap / Space to start', font_size=dp(24), bold=True,
            color=(1, 1, 1, 1), outline_color=(0, 0, 0, 1), outline_width=2,
            pos_hint={'center_x': 0.5, 'center_y': 0.45},
            size_hint=(None, None), size=(WIN_W, dp(40))
        )
        self.add_widget(self.msg_lbl)

        self.best_lbl = Label(
            text='', font_size=dp(18),
            color=(1, 0.9, 0.3, 1), outline_color=(0, 0, 0, 1), outline_width=2,
            pos_hint={'center_x': 0.5, 'center_y': 0.39},
            size_hint=(None, None), size=(WIN_W, dp(30))
        )
        self.add_widget(self.best_lbl)

    def set_score(self, n):   self.score_lbl.text = str(n)
    def set_message(self, t): self.msg_lbl.text   = t
    def set_best(self, n):    self.best_lbl.text  = f'Best: {n}' if n else ''
    def hide_message(self):
        self.msg_lbl.text  = ''
        self.best_lbl.text = ''


# ── Main game ─────────────────────────────────────────────────────────────────

class FlappyGame(FloatLayout):
    STATE_IDLE    = 'idle'
    STATE_PLAYING = 'playing'
    STATE_DEAD    = 'dead'

    def __init__(self, **kw):
        super().__init__(**kw)
        self.size       = (WIN_W, WIN_H)
        self.state      = self.STATE_IDLE
        self.score      = 0
        self.best_score = 0
        self._pipes     = []

        self._next_pipe = 0
        self._ground_x  = 0

        # sky
        with self.canvas.before:
            Color(*SKY_TOP)
            Rectangle(pos=(0, GROUND_H), size=(WIN_W, WIN_H - GROUND_H))

        # distant hills
        with self.canvas:
            Color(0.40, 0.75, 0.30, 0.35)
            Ellipse(pos=(-40,        GROUND_H - int(10*SCALE)), size=(int(260*SCALE), int(90*SCALE)))
            Ellipse(pos=(WIN_W//3,   GROUND_H - int(20*SCALE)), size=(int(320*SCALE), int(80*SCALE)))
            Ellipse(pos=(WIN_W*3//4, GROUND_H - int(10*SCALE)), size=(int(200*SCALE), int(75*SCALE)))

        # scrolling ground
        with self.canvas:
            Color(*GROUND_C)
            self._ground_rect = Rectangle(pos=(0, 0), size=(WIN_W * 3, GROUND_H - int(14*SCALE)))
            Color(*GRASS_C)
            self._grass_rect  = Rectangle(pos=(0, GROUND_H - int(16*SCALE)), size=(WIN_W * 3, int(18*SCALE)))


        self._bird = Bird()
        self.add_widget(self._bird)

        # HUD on top
        self._hud = HUD()
        self.add_widget(self._hud)
        self._hud.set_score(0)
        self._hud.set_message('Tap / Space to start')

        # input
        self._keyboard = Window.request_keyboard(self._on_kb_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        self.bind(on_touch_down=self._on_touch)

        Clock.schedule_interval(self._tick, 1 / FPS)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _spawn_pipe(self):
        gap_y = random.randint(PIPE_MIN_H, PIPE_MAX_H)
        p = PipePair(PIPE_SPAWN_X, gap_y)
        self._pipes.append(p)
        self.add_widget(p, index=len(self.children))

    def _reset(self):
        for p in self._pipes:
            self.remove_widget(p)
        self._pipes.clear()

        self.remove_widget(self._bird)
        self._bird = Bird()
        self.add_widget(self._bird, index=1)

        self.score      = 0
        self._next_pipe = int(80 * SCALE)
        self._hud.set_score(0)
        self._hud.hide_message()
        self.state = self.STATE_PLAYING

    # ── collision ─────────────────────────────────────────────────────────────

    @staticmethod
    def _overlap(ax, ay, aw, ah, bx, by, bw, bh):
        return (ax < bx + bw and ax + aw > bx and
                ay < by + bh and ay + ah > by)

    def _check_collisions(self):
        bx, by, bw, bh = self._bird.hitbox
        if by <= GROUND_H or by + bh >= WIN_H:
            return True
        for p in self._pipes:
            for rx, ry, rw, rh in (p.rect_bottom, p.rect_top):
                if self._overlap(bx, by, bw, bh, rx, ry, rw, rh):
                    return True
        return False

    # ── tick ──────────────────────────────────────────────────────────────────

    def _tick(self, dt):
        if self.state != self.STATE_PLAYING:
            return

        # ground scroll
        self._ground_x = (self._ground_x - PIPE_SPEED) % WIN_W
        self._ground_rect.pos = (-self._ground_x, 0)
        self._grass_rect.pos  = (-self._ground_x, GROUND_H - int(16*SCALE))

        self._bird.update()

        # pipe spawning
        self._next_pipe -= 1
        if self._next_pipe <= 0:
            self._spawn_pipe()
            self._next_pipe = int(WIN_W * 0.75 / PIPE_SPEED)

        to_remove = []
        for p in self._pipes:
            p.update()
            if not p.passed and p.x + PIPE_WIDTH < self._bird.x:
                p.passed = True
                self.score += 1
                self._hud.set_score(self.score)
            if p.right < -10:
                to_remove.append(p)
        for p in to_remove:
            self._pipes.remove(p)
            self.remove_widget(p)

        if self._check_collisions():
            self._die()

    # ── state transitions ─────────────────────────────────────────────────────

    def _die(self):
        self.state = self.STATE_DEAD
        self._bird.die()
        if self.score > self.best_score:
            self.best_score = self.score
        self._hud.set_message('Tap / Space to restart')
        self._hud.set_best(self.best_score)

    def _action(self):
        if self.state == self.STATE_IDLE:
            self._reset()
        elif self.state == self.STATE_PLAYING:
            self._bird.flap()
        elif self.state == self.STATE_DEAD:
            Clock.schedule_once(lambda dt: self._reset(), 0.25)

    # ── input ─────────────────────────────────────────────────────────────────

    def _on_key_down(self, kb, keycode, text, modifiers):
        if keycode[1] in ('spacebar', 'up', 'w'):
            self._action()
        return True

    def _on_touch(self, instance, touch):
        self._action()

    def _on_kb_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard = None


# ── App ───────────────────────────────────────────────────────────────────────

class FlappyBirdApp(App):
    title = 'Flappy Bird'

    def build(self):
        # Desktop: set a sensible portrait window.
        # Android/iOS: Window.size is already the real screen — don't override.
        import platform
        if platform.system() in ('Windows', 'Darwin', 'Linux'):
            Window.size = (WIN_W, WIN_H)
            Window.resizable = False
        Window.clearcolor = SKY_BOT
        return FlappyGame()


if __name__ == '__main__':
    FlappyBirdApp().run()
