# -*- coding: utf-8 -*-
"""界面层：DPI、多屏定位、悬浮图标、结果窗、设置窗、框选遮罩

视觉约定：
  深色卡片 + 单一蓝色强调色 + 细边框，不使用原生边框
  所有弹出窗淡入/淡出，避免突兀
"""
import ctypes
import math
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

DEFAULT_THEME = "midnight"

# 每套主题 = 配色 + 字体 + 动效
# anim_in: fade 淡入 / slide 上滑入场 / pop 快速弹出
# reveal:  instant 整段显示 / typewriter 逐字浮现（reveal_cps = 每秒字数）
THEMES = {
    "midnight": {
        "label": "午夜蓝",
        "alpha": 0.97, "icon_radius": 0.30, "overlay_alpha": 0.45,
        "font": "Microsoft YaHei UI", "anim_in": "slide", "reveal": "instant",
        "colors": {
            "BG": "#0e1320", "CARD": "#141b2c", "HEAD": "#182035",
            "FG": "#e8eefb", "FG_DIM": "#93a0b8",
            "BLUE": "#4a8dff", "BLUE_HOVER": "#6ba5ff", "BLUE_SOFT": "#1d2a4a",
            "ACCENT_DOWN": "#3573e6", "ON_ACCENT": "#ffffff", "ICON_OUTLINE": "#8db4ff",
            "BORDER": "#273251", "DANGER": "#e0625b",
            "SELECT_BG": "#2a4480", "SELECT_FG": "#ffffff",
            "SUBTLE": "#64708a", "THUMB": "#35415e", "THUMB_HOVER": "#4a5878",
            "OVERLAY_BG": "#05070d", "PILL_BG": "#182035", "PILL_FG": "#e8eefb",
            "SIZE_FG": "#c2cee4", "GHOST_HOVER": "#212c49",
        },
    },
    "obsidian": {
        "label": "曜石金",
        "alpha": 0.95, "icon_radius": 0.20, "overlay_alpha": 0.46,
        "font": "KaiTi", "anim_in": "fade", "reveal": "typewriter", "reveal_cps": 40,
        "colors": {
            "BG": "#131210", "CARD": "#1b1915", "HEAD": "#221f19",
            "FG": "#f2ebdc", "FG_DIM": "#a89e88",
            "BLUE": "#d9a441", "BLUE_HOVER": "#efbc5e", "BLUE_SOFT": "#332b1a",
            "ACCENT_DOWN": "#a97d29", "ON_ACCENT": "#241c0a", "ICON_OUTLINE": "#f0cd7a",
            "BORDER": "#3a3327", "DANGER": "#cf5a52",
            "SELECT_BG": "#4a3a1e", "SELECT_FG": "#f7efdd",
            "SUBTLE": "#7a7264", "THUMB": "#4a4438", "THUMB_HOVER": "#635c4c",
            "OVERLAY_BG": "#0a0a08", "PILL_BG": "#221f19", "PILL_FG": "#f2ebdc",
            "SIZE_FG": "#d8cfbc", "GHOST_HOVER": "#2a261f",
        },
    },
    "aurora": {
        "label": "极光青",
        "alpha": 0.94, "icon_radius": 0.34, "overlay_alpha": 0.40,
        "font": "DengXian", "anim_in": "slide", "reveal": "typewriter", "reveal_cps": 60,
        "colors": {
            "BG": "#0a1315", "CARD": "#101d20", "HEAD": "#142629",
            "FG": "#e2f5f4", "FG_DIM": "#8fb2b3",
            "BLUE": "#27c3ad", "BLUE_HOVER": "#48dfc8", "BLUE_SOFT": "#123330",
            "ACCENT_DOWN": "#189180", "ON_ACCENT": "#04201b", "ICON_OUTLINE": "#6ee7d3",
            "BORDER": "#1e3a3d", "DANGER": "#d9584f",
            "SELECT_BG": "#16514b", "SELECT_FG": "#e9fffc",
            "SUBTLE": "#6f8b8c", "THUMB": "#2f4a4d", "THUMB_HOVER": "#446064",
            "OVERLAY_BG": "#050a0b", "PILL_BG": "#142629", "PILL_FG": "#e2f5f4",
            "SIZE_FG": "#bfe0de", "GHOST_HOVER": "#1c3236",
        },
    },
    "glass": {
        "label": "磨砂紫",
        "alpha": 0.88, "icon_radius": 0.30, "overlay_alpha": 0.36,
        "font": "Microsoft YaHei UI", "anim_in": "pop", "reveal": "instant",
        "colors": {
            "BG": "#1b1d22", "CARD": "#23262a", "HEAD": "#2a2e33",
            "FG": "#eceef2", "FG_DIM": "#9aa1ad",
            "BLUE": "#8b7bf0", "BLUE_HOVER": "#a596ff", "BLUE_SOFT": "#2f2b45",
            "ACCENT_DOWN": "#6d5cd8", "ON_ACCENT": "#ffffff", "ICON_OUTLINE": "#b0a4ff",
            "BORDER": "#3a3f47", "DANGER": "#d9534f",
            "SELECT_BG": "#3f3a63", "SELECT_FG": "#ffffff",
            "SUBTLE": "#747b87", "THUMB": "#4a5058", "THUMB_HOVER": "#626a75",
            "OVERLAY_BG": "#0c0d10", "PILL_BG": "#2a2e33", "PILL_FG": "#eceef2",
            "SIZE_FG": "#ccd2dc", "GHOST_HOVER": "#33383f",
        },
    },
    "sakura": {
        "label": "樱雾白",
        "alpha": 1.0, "icon_radius": 0.28, "overlay_alpha": 0.34,
        "font": "SimSun", "anim_in": "fade", "reveal": "typewriter", "reveal_cps": 30,
        "colors": {
            "BG": "#faf6f8", "CARD": "#ffffff", "HEAD": "#f4eaef",
            "FG": "#2c2329", "FG_DIM": "#8a7780",
            "BLUE": "#d9558a", "BLUE_HOVER": "#e875a5", "BLUE_SOFT": "#f8e2ea",
            "ACCENT_DOWN": "#b93c6d", "ON_ACCENT": "#ffffff", "ICON_OUTLINE": "#f0a7c4",
            "BORDER": "#e8d9e1", "DANGER": "#c9483f",
            "SELECT_BG": "#f3c9da", "SELECT_FG": "#3a2029",
            "SUBTLE": "#a2909a", "THUMB": "#d8c6cf", "THUMB_HOVER": "#c2adb9",
            "OVERLAY_BG": "#2b2226", "PILL_BG": "#ffffff", "PILL_FG": "#2c2329",
            "SIZE_FG": "#6b5a63", "GHOST_HOVER": "#efe2e8",
        },
    },
}

WINDOW_ALPHA = 0.96      # 结果窗不透明度（由主题覆盖）
ICON_RADIUS = 0.26       # 图标圆角比例
OVERLAY_ALPHA = 0.42     # 截图遮罩压暗程度
FONT_FAMILY = "Microsoft YaHei UI"   # 界面字体（由主题覆盖）
ANIM_IN = "slide"        # 窗口入场动画：fade / slide / pop
REVEAL = "instant"       # 译文呈现：instant / typewriter
REVEAL_CPS = 50          # 逐字浮现速度（字/秒）
CURRENT_THEME = DEFAULT_THEME


def set_theme(theme_id):
    """切换主题：把该主题的配色/字体/动效写入模块全局，新建窗口即生效"""
    global WINDOW_ALPHA, ICON_RADIUS, OVERLAY_ALPHA, FONT_FAMILY, ANIM_IN, REVEAL, REVEAL_CPS
    global CURRENT_THEME
    theme = THEMES.get(theme_id) or THEMES[DEFAULT_THEME]
    CURRENT_THEME = theme_id if theme_id in THEMES else DEFAULT_THEME
    globals().update(theme["colors"])
    WINDOW_ALPHA = theme["alpha"]
    ICON_RADIUS = theme["icon_radius"]
    OVERLAY_ALPHA = theme["overlay_alpha"]
    FONT_FAMILY = theme.get("font", "Microsoft YaHei UI")
    ANIM_IN = theme.get("anim_in", "fade")
    REVEAL = theme.get("reveal", "instant")
    REVEAL_CPS = int(theme.get("reveal_cps", 50))


set_theme(DEFAULT_THEME)


def rgb(hex_color):
    """#rrggbb -> (r, g, b)，供 PIL 绘制托盘图标用"""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def popup_theme_menu(win, x, y, on_pick):
    """右键主题菜单：在 (x, y) 弹出主题列表，选中回调 on_pick(theme_id)"""
    if on_pick is None:
        return
    m = tk.Menu(win, tearoff=0, bg=CARD, fg=FG,
                activebackground=BLUE, activeforeground=ON_ACCENT,
                bd=1, relief="flat", font=_font(9))
    for tid, t in THEMES.items():
        mark = "● " if tid == CURRENT_THEME else "　"
        m.add_command(label=mark + t["label"],
                      command=lambda i=tid: on_pick(i))
    try:
        m.tk_popup(x, y)
    finally:
        m.grab_release()

PROVIDER_LABEL = {
    "youdao-demo": "有道",
    "mymemory": "MyMemory",
    "google": "Google",
    "baidu": "百度",
}


# ---------------- 主题 ----------------
def apply_theme(root):
    """统一 ttk 控件外观（设置窗使用）"""
    try:
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=FG,
                        font=(FONT_FAMILY, 9))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG)
        style.configure("Dim.TLabel", foreground=FG_DIM)
        style.configure("Title.TLabel", font=(FONT_FAMILY, 12, "bold"))
        style.configure("TSeparator", background=BORDER)
        style.configure("TLabelframe", background=BG, bordercolor=BORDER,
                        relief="flat", borderwidth=1)
        style.configure("TLabelframe.Label", background=BG, foreground=FG_DIM,
                        font=(FONT_FAMILY, 9, "bold"))
        style.configure("TEntry", fieldbackground=CARD, foreground=FG, insertcolor=FG,
                        bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                        padding=4)
        style.map("TEntry", bordercolor=[("focus", BLUE)], lightcolor=[("focus", BLUE)])
        style.configure("TCombobox", fieldbackground=CARD, background=CARD,
                        foreground=FG, arrowcolor=FG_DIM, bordercolor=BORDER,
                        lightcolor=BORDER, darkcolor=BORDER,
                        selectbackground=CARD, selectforeground=FG, padding=3)
        style.map("TCombobox",
                  fieldbackground=[("readonly", CARD), ("focus", CARD)],
                  background=[("readonly", CARD), ("active", HEAD)],
                  foreground=[("readonly", FG)],
                  arrowcolor=[("active", BLUE_HOVER)],
                  bordercolor=[("focus", BLUE), ("active", BLUE)])
        style.configure("TSpinbox", fieldbackground=CARD, foreground=FG,
                        background=CARD, arrowcolor=FG_DIM, bordercolor=BORDER,
                        lightcolor=BORDER, darkcolor=BORDER, padding=3)
        style.map("TSpinbox", arrowcolor=[("active", BLUE_HOVER)],
                  bordercolor=[("focus", BLUE), ("active", BLUE)],
                  fieldbackground=[("focus", CARD)])
        style.configure("TCheckbutton", background=BG, foreground=FG,
                        indicatorbackground=CARD, indicatorforeground="#ffffff",
                        upperbordercolor=BORDER, lowerbordercolor=BORDER,
                        focuscolor=BG)
        style.map("TCheckbutton",
                  background=[("active", BG)],
                  indicatorbackground=[("selected", BLUE), ("active", BLUE_SOFT)],
                  indicatorforeground=[("selected", "#ffffff")],
                  foreground=[("active", "#ffffff")])
        style.configure("Accent.TButton", background=BLUE, foreground=ON_ACCENT,
                        borderwidth=0, focusthickness=0, padding=(14, 6),
                        font=(FONT_FAMILY, 9, "bold"))
        style.map("Accent.TButton",
                  background=[("active", BLUE_HOVER), ("pressed", ACCENT_DOWN)],
                  foreground=[("disabled", FG_DIM)])
        style.configure("Ghost.TButton", background=HEAD, foreground=FG_DIM,
                        borderwidth=0, padding=(12, 6))
        style.map("Ghost.TButton", background=[("active", GHOST_HOVER)],
                  foreground=[("active", FG)])
    except Exception:
        pass


class SlimScroll(tk.Canvas):
    """自绘 6px 细滑块：Windows 原生滚动条无法套用深色配色，这里完全自绘"""

    def __init__(self, master, target, width=6, bg=CARD,
                 thumb=None, thumb_hover=None):
        super().__init__(master, width=width, bg=bg, highlightthickness=0,
                         bd=0, takefocus=0)
        self.target = target
        self.w = width
        self.thumb_color = THUMB if thumb is None else thumb
        self.thumb_hover = THUMB_HOVER if thumb_hover is None else thumb_hover
        self.first = 0.0
        self.last = 1.0
        self._y0 = 0
        self._y1 = 0
        self._drag = None
        self.bind("<Configure>", lambda e: self._draw())
        self.bind("<Button-1>", self._press)
        self.bind("<B1-Motion>", self._move)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag", None))
        self.bind("<Enter>", lambda e: self._draw(hover=True))
        self.bind("<Leave>", lambda e: self._draw(hover=False))

    # Text 的 yscrollcommand 回调
    def set(self, first, last):
        try:
            self.first, self.last = float(first), float(last)
        except Exception:
            self.first, self.last = 0.0, 1.0
        self._draw()

    def _draw(self, hover=False):
        try:
            self.delete("all")
            h = max(1, self.winfo_height())
            span = self.last - self.first
            if span >= 0.999:
                return
            y0 = int(self.first * h)
            y1 = int(self.last * h)
            if y1 - y0 < 22:
                mid = (y0 + y1) // 2
                y0, y1 = mid - 11, mid + 11
            y0 = max(1, min(h - 2, y0))
            y1 = max(y0 + 4, min(h - 1, y1))
            self._y0, self._y1 = y0, y1
            fill = self.thumb_hover if (hover or self._drag) else self.thumb_color
            self.create_rectangle(self.w - 5, y0, self.w - 1, y1,
                                  fill=fill, outline="")
        except Exception:
            pass

    def _press(self, e):
        h = max(1, self.winfo_height())
        span = self.last - self.first
        pos = e.y / h
        if not (self._y0 <= e.y <= self._y1):
            self.target.yview_moveto(max(0.0, min(1.0 - span, pos - span / 2)))
        self._drag = e.y
        self._draw(hover=True)

    def _move(self, e):
        if self._drag is None:
            return
        h = max(1, self.winfo_height())
        span = self.last - self.first
        delta = (e.y - self._drag) / h
        self._drag = e.y
        self.target.yview_moveto(max(0.0, min(1.0 - span, self.first + delta)))


def fade(win, start, end, steps=7, delay=14, on_done=None):
    """窗口透明度补间；step 失败（窗口已销毁）时静默停止"""
    try:
        alpha = float(start)
        delta = (end - start) / float(max(1, steps))
    except Exception:
        return

    def _step(i):
        try:
            if not win.winfo_exists():
                return
            a = max(0.0, min(1.0, start + delta * i))
            win.attributes("-alpha", a)
        except Exception:
            return
        if i < steps:
            win.after(delay, lambda: _step(i + 1))
        elif on_done:
            try:
                on_done()
            except Exception:
                pass

    try:
        win.attributes("-alpha", alpha)
    except Exception:
        pass
    _step(0)


# ---------------- DPI 与多屏 ----------------
def enable_dpi_awareness():
    """声明 DPI 感知，避免高缩放比例下坐标偏移"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)   # PER_MONITOR
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def monitor_rects():
    """枚举所有显示器矩形：[(left, top, right, bottom), ...]"""
    rects = []
    try:
        proto = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                                   ctypes.POINTER(_RECT), ctypes.c_double)

        def _cb(hmon, hdc, lprc, data):
            r = lprc.contents
            rects.append((r.left, r.top, r.right, r.bottom))
            return 1

        ctypes.windll.user32.EnumDisplayMonitors(0, 0, proto(_cb), 0)
    except Exception:
        pass
    if not rects:
        try:
            w = ctypes.windll.user32.GetSystemMetrics(0)
            h = ctypes.windll.user32.GetSystemMetrics(1)
        except Exception:
            w, h = 1920, 1080
        rects = [(0, 0, w, h)]
    return rects


def virtual_screen():
    """整个虚拟桌面范围（多屏可能含负坐标）"""
    try:
        u = ctypes.windll.user32
        x = u.GetSystemMetrics(76)
        y = u.GetSystemMetrics(77)
        w = u.GetSystemMetrics(78)
        h = u.GetSystemMetrics(79)
        if w > 0 and h > 0:
            return x, y, w, h
    except Exception:
        pass
    r = monitor_rects()[0]
    return r[0], r[1], r[2] - r[0], r[3] - r[1]


def fit_position(x, y, w, h, margin=8):
    """把窗口 (x, y, w, h) 收进光标所在那块显示器；多屏负坐标也能正确处理"""
    rects = monitor_rects()
    chosen = None
    for r in rects:
        if r[0] <= x < r[2] and r[1] <= y < r[3]:
            chosen = r
            break
    if chosen is None:  # 光标在屏幕间隙：取中心距离最近的显示器
        chosen = min(rects, key=lambda r: (x - (r[0] + r[2]) / 2) ** 2 +
                                            (y - (r[1] + r[3]) / 2) ** 2)
    l, t, r, b = chosen
    max_x = r - w - margin
    max_y = b - h - margin
    nx = min(max(x, l + margin), max(max_x, l + margin))
    ny = min(max(y, t + margin), max(max_y, t + margin))
    return int(nx), int(ny)


def _font(px_size, bold=False):
    return (FONT_FAMILY, int(px_size), "bold") if bold else (FONT_FAMILY, int(px_size))


def animate_in(win, final_x, final_y, alpha):
    """窗口入场动画：fade 淡入 / slide 上滑 / pop 快速弹出（带 ease-out）"""
    if ANIM_IN == "fade":
        win.geometry(f"+{final_x}+{final_y}")
        fade(win, 0.0, alpha, steps=5, delay=12)
        return
    offset, steps = (14, 6) if ANIM_IN == "slide" else (6, 3)

    def _step(i):
        try:
            if not win.winfo_exists():
                return
            k = i / steps
            ease = 1 - (1 - k) ** 2
            dy = int(offset * (1 - ease))
            win.geometry(f"+{final_x}+{final_y + dy}")
            win.attributes("-alpha", alpha * ease)
        except Exception:
            return
        if i < steps:
            win.after(14, lambda: _step(i + 1))

    try:
        win.attributes("-alpha", 0.0)
    except Exception:
        pass
    _step(0)


# ---------------- 悬浮「译」图标 ----------------
class IconWindow:
    """圆角渐变徽标；悬停变亮，点击/悬停即翻译"""

    def __init__(self, master, size=34, on_trigger=None, on_theme=None):
        from PIL import Image, ImageDraw, ImageFont, ImageTk

        self.size = int(size)
        self.on_trigger = on_trigger
        self.on_theme = on_theme
        self._imgs = {}
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.pad = 2
        side = self.size + self.pad * 2

        key = "#ff00ff"
        try:
            self.win.attributes("-transparentcolor", key)
            bg_color = key
        except Exception:
            bg_color = BG

        self.canvas = tk.Canvas(self.win, width=side, height=side,
                                bg=bg_color, highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self._imgs["normal"] = self._make_badge(Image, ImageDraw, ImageFont, ImageTk, BLUE)
        self._imgs["hover"] = self._make_badge(Image, ImageDraw, ImageFont, ImageTk, BLUE_HOVER)
        self.item = self.canvas.create_image(self.pad, self.pad, anchor="nw",
                                             image=self._imgs["normal"])
        self.canvas.bind("<Enter>", self._on_enter)
        self.canvas.bind("<Leave>", self._on_leave)
        self.canvas.bind("<Button-1>", self._trigger)
        self.canvas.bind("<Button-3>", self._theme_menu)
        self.win.withdraw()

    def _make_badge(self, Image, ImageDraw, ImageFont, ImageTk, color):
        """4 倍超采样后缩放，圆角边缘更平滑"""
        s = self.size
        scale = 4
        px = s * scale
        img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        radius = int(s * ICON_RADIUS) * scale
        # 竖向渐变：强调色 -> 按下色
        top = color
        bottom = ACCENT_DOWN
        grad = Image.new("RGBA", (1, px))
        gd = ImageDraw.Draw(grad)
        r1, g1, b1 = int(top[1:3], 16), int(top[3:5], 16), int(top[5:7], 16)
        r2, g2, b2 = int(bottom[1:3], 16), int(bottom[3:5], 16), int(bottom[5:7], 16)
        for i in range(px):
            k = i / float(px - 1)
            gd.point((0, i), fill=(int(r1 + (r2 - r1) * k),
                                   int(g1 + (g2 - g1) * k),
                                   int(b1 + (b2 - b1) * k), 255))
        grad = grad.resize((px, px))
        mask = Image.new("L", (px, px), 0)
        md = ImageDraw.Draw(mask)
        md.rounded_rectangle((0, 0, px - 1, px - 1), radius=radius, fill=255)
        img.paste(grad, (0, 0), mask)

        d.rounded_rectangle((scale // 2, scale // 2, px - 1 - scale // 2, px - 1 - scale // 2),
                            radius=radius, outline=ICON_OUTLINE, width=scale)
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", int(s * 0.56 * scale))
        except Exception:
            font = ImageFont.load_default()
        d.text((px / 2, px / 2), "译", font=font, fill=ON_ACCENT, anchor="mm")
        img = img.resize((s, s), Image.LANCZOS)
        # 硬边处理：alpha 只有 0/255，避免半透明边缘与透明色混合产生紫边
        alpha = img.getchannel("A").point(lambda v: 255 if v > 200 else 0)
        img.putalpha(alpha)
        return ImageTk.PhotoImage(img)

    # ---- 状态 ----
    def _on_enter(self, _e=None):
        try:
            self.canvas.itemconfigure(self.item, image=self._imgs["hover"])
        except Exception:
            pass
        if self.on_trigger:
            self.on_trigger()

    def _on_leave(self, _e=None):
        try:
            self.canvas.itemconfigure(self.item, image=self._imgs["normal"])
        except Exception:
            pass

    def _trigger(self, _e=None):
        if self.on_trigger:
            self.on_trigger()

    def _theme_menu(self, e):
        popup_theme_menu(self.win, e.x_root, e.y_root, self.on_theme)
    # ---- 显示/隐藏 ----
    def show(self, x, y):
        w = h = self.size + self.pad * 2
        px, py = fit_position(x + 14, y + 16, w, h)
        self.win.geometry(f"+{px}+{py}")
        self.win.deiconify()
        fade(self.win, 0.0, 1.0, steps=4, delay=12)

    def hide(self):
        try:
            fade(self.win, 1.0, 0.0, steps=3, delay=10, on_done=self.win.withdraw)
        except Exception:
            self.win.withdraw()

    def visible(self):
        return bool(self.win.winfo_ismapped())

    def bounds(self):
        """返回 (l, t, r, b)，用于判断点击是否落在图标上"""
        if not self.visible():
            return None
        return (self.win.winfo_x(), self.win.winfo_y(),
                self.win.winfo_x() + self.win.winfo_width(),
                self.win.winfo_y() + self.win.winfo_height())


# ---------------- 结果窗 ----------------
class ResultWindow:
    """无边框置顶卡片：标题栏带来源标签，译文可选中复制，长文限高滚动"""

    def __init__(self, master, font_size=11, max_height=460, on_copy=None, on_speak=None,
                 on_theme=None, bilingual=False):
        self.fs = font_size
        self.bilingual = bilingual
        self.src_text = ""             # 本轮原文（双语对照 / 朗读英文用）
        try:
            linespace = tkfont.Font(family=FONT_FAMILY,
                                    size=int(font_size)).metrics("linespace")
        except Exception:
            linespace = font_size + 9
        self.line_h = max(1, int(linespace) + 5)   # 行高 + spacing3
        # 减去标题栏/正文内边距/底栏约 70px，让整窗高度不超过配置值
        self.max_lines = max(3, int((max_height - 70) / self.line_h))
        self.on_copy = on_copy
        self.on_speak = on_speak
        self.on_theme = on_theme
        self._speaking = False
        self.provider = ""
        self._anim_id = None
        self._reveal_id = None       # 逐字浮现定时器
        self._reveal_target = ""     # 目标全文
        self._reveal_len = 0         # 已浮现字数

        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.configure(bg=BG)

        card = tk.Frame(self.win, bg=CARD, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill="both", expand=True)

        # 标题栏（右键标题栏空白处可快速切换主题）
        head = tk.Frame(card, bg=HEAD)
        head.pack(fill="x")
        logo = tk.Label(head, text="译", bg=HEAD, fg=BLUE,
                        font=_font(9, True))
        logo.pack(side="left", padx=(11, 5), pady=5)
        self.chip = tk.Label(head, text="", bg=HEAD, fg=FG_DIM,
                             font=_font(8), padx=0)
        self.chip.pack(side="left", pady=5)
        for w in (head, logo, self.chip):
            w.bind("<Button-3>", self._theme_menu)

        self.close_btn = tk.Label(head, text="×", bg=HEAD, fg=FG_DIM, cursor="hand2",
                                  font=_font(11, True), padx=10)
        self.close_btn.pack(side="right", pady=1)
        self.copy_btn = tk.Label(head, text="复制", bg=HEAD, fg=FG_DIM, cursor="hand2",
                                 font=_font(9), padx=8)
        self.copy_btn.pack(side="right", pady=1)
        self.read_btn = tk.Label(head, text="朗读", bg=HEAD, fg=FG_DIM, cursor="hand2",
                                 font=_font(9), padx=8)
        self.read_btn.pack(side="right", pady=1)

        # 正文
        body = tk.Frame(card, bg=CARD)
        body.pack(fill="both", expand=True)
        self.text = tk.Text(body, bg=CARD, fg=FG, bd=0, highlightthickness=0,
                            font=_font(font_size), wrap="word", width=52, height=3,
                            padx=14, pady=10, cursor="arrow",
                            spacing1=0, spacing3=5,
                            selectbackground=SELECT_BG, selectforeground=SELECT_FG,
                            insertwidth=0)
        self.scroll = SlimScroll(body, target=self.text, width=6)
        self.text.configure(yscrollcommand=self.scroll.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        # 底栏
        foot = tk.Frame(card, bg=CARD)
        foot.pack(fill="x")
        tk.Label(foot, text="Esc 关闭", bg=CARD, fg=SUBTLE,
                 font=_font(8)).pack(side="right", padx=10, pady=(0, 6))

        self.text.configure(state="disabled")
        self.close_btn.bind("<Button-1>", lambda e: self.hide())
        self.copy_btn.bind("<Button-1>", lambda e: self._copy())
        self.copy_btn.bind("<Enter>", lambda e: self.copy_btn.config(fg=FG))
        self.copy_btn.bind("<Leave>", lambda e: self.copy_btn.config(fg=FG_DIM))
        self.read_btn.bind("<Button-1>", lambda e: self._speak())
        self.read_btn.bind("<Enter>", lambda e: self.read_btn.config(fg=FG))
        self.read_btn.bind("<Leave>", lambda e: self.read_btn.config(
            fg=BLUE if self._speaking else FG_DIM))
        self.close_btn.bind("<Enter>", lambda e: self.close_btn.config(fg="#ffffff", bg=DANGER))
        self.close_btn.bind("<Leave>", lambda e: self.close_btn.config(fg=FG_DIM, bg=HEAD))
        self.win.bind("<Escape>", lambda e: self.hide())
        self.win.withdraw()

    # ---- 内容 ----
    def set_provider(self, name):
        label = PROVIDER_LABEL.get(name, "")
        self.provider = name
        try:
            self.chip.config(text=f"· {label}" if label else "")
        except Exception:
            pass

    def _set_text(self, text):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self.text.configure(state="disabled")

    def _wrap_lines(self, text):
        """按字体实测宽度估算换行行数（中英文都准确，且不依赖窗口已显示）"""
        try:
            f = tkfont.Font(font=self.text.cget("font"))
            inner = max(80, int(self.text.cget("width")) * f.measure("0") - 28)
            n = 0
            for para in text.split("\n"):
                n += max(1, math.ceil(f.measure(para) / inner))
            return max(2, n)
        except Exception:
            return max(2, text.count("\n") + 1)

    def _apply(self, text):
        """统一入口：写内容 + 定高 + 按需显示滚动条"""
        self._set_text(text)
        raw = self._wrap_lines(text)
        self.text.configure(height=min(raw, self.max_lines))
        if raw > self.max_lines:
            self.scroll.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")
        else:
            self.scroll.place_forget()
            try:
                self.text.yview_moveto(0)
            except Exception:
                pass

    def _place(self, x, y):
        self.win.update_idletasks()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        px, py = fit_position(x, y, w, h)
        self.win.geometry(f"+{px}+{py}")

    # ---- 显示 ----
    def show_at(self, x, y, text="翻译中…"):
        self._stop_loading()
        self._cancel_reveal()
        self.src_text = ""
        self._apply(text)
        self._place(x + 12, y + 18)
        self.win.deiconify()
        animate_in(self.win, self.win.winfo_x(), self.win.winfo_y(), WINDOW_ALPHA)

    def show_loading(self, x, y):
        """显示「正在翻译」并循环省略号，直到 update_text 覆盖"""
        self._stop_loading()
        self._cancel_reveal()
        self.src_text = ""
        self._apply("正在翻译")
        self._place(x + 12, y + 18)
        self.win.deiconify()
        animate_in(self.win, self.win.winfo_x(), self.win.winfo_y(), WINDOW_ALPHA)
        start = self.win.winfo_toplevel()
        self._dots = 0
        self._poll_dots(start)

    def _poll_dots(self, win):
        try:
            if not self.visible():
                return
            self._dots = (self._dots + 1) % 4
            self._set_text("正在翻译" + "·" * self._dots + " " * (3 - self._dots))
            self._anim_id = win.after(320, lambda: self._poll_dots(win))
        except tk.TclError:
            self._anim_id = None

    def _stop_loading(self):
        if self._anim_id is not None:
            try:
                self.win.after_cancel(self._anim_id)
            except Exception:
                pass
            self._anim_id = None

    # ---- 逐字浮现 ----
    def _cancel_reveal(self):
        if self._reveal_id is not None:
            try:
                self.win.after_cancel(self._reveal_id)
            except Exception:
                pass
            self._reveal_id = None
        self._reveal_target = ""
        self._reveal_len = 0

    def _reveal_step(self):
        self._reveal_id = None
        if not self.visible():
            return
        step = max(1, int(REVEAL_CPS * 0.03))
        self._reveal_len = min(len(self._reveal_target), self._reveal_len + step)
        self._apply(self._reveal_target[:self._reveal_len])
        if self._reveal_len < len(self._reveal_target):
            self._reveal_id = self.win.after(30, self._reveal_step)
        else:
            self._reposition()

    def _reposition(self):
        self.win.update_idletasks()
        w, h = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
        px, py = fit_position(self.win.winfo_x(), self.win.winfo_y(), w, h)
        self.win.geometry(f"+{px}+{py}")

    def _with_src(self, text):
        """双语对照：译文后附原文；报错/空文本不拼"""
        if not self.src_text.strip() or not text.strip() or text.startswith("翻译失败"):
            return text
        from translator import bilingual_text
        return bilingual_text(self.src_text, text)

    def update_text(self, text):
        self._stop_loading()
        if not self.visible():
            return
        if self.bilingual:
            text = self._with_src(text)
        if REVEAL == "typewriter":
            # 目标文本只增不减：流式翻译不断追加，浮现指针继续往前走
            self._reveal_target = text
            if self._reveal_id is None:
                self._reveal_id = self.win.after(0, self._reveal_step)
        else:
            self._cancel_reveal()
            self._apply(text)
            self._reposition()

    def _full_text(self):
        """复制/朗读取全文：逐字浮现中途也取完整译文"""
        if self._reveal_id is not None and self._reveal_target:
            return self._reveal_target
        return self.text.get("1.0", "end").strip()

    def _theme_menu(self, e):
        popup_theme_menu(self.win, e.x_root, e.y_root, self.on_theme)

    def _copy(self):
        try:
            self.win.clipboard_clear()
            self.win.clipboard_append(self._full_text())
            self.copy_btn.config(text="已复制", fg=BLUE_HOVER)
            self.win.after(1200, lambda: self.copy_btn.config(text="复制", fg=FG_DIM))
            if self.on_copy:
                self.on_copy()
        except Exception:
            pass

    def _speak(self):
        """点「朗读」把当前译文交给外部朗读；再点一次是停止"""
        if not self.on_speak:
            return
        try:
            text = "" if self._speaking else self._full_text()
        except Exception:
            text = ""
        self.on_speak(text)

    def set_speaking(self, on):
        """外部在开始/结束朗读时回调，用于切换按钮文案"""
        self._speaking = bool(on)
        try:
            self.read_btn.config(text="停止" if on else "朗读",
                                 fg=BLUE if on else FG_DIM)
        except Exception:
            pass

    def hide(self):
        self._stop_loading()
        self._cancel_reveal()
        if self._speaking and self.on_speak:
            try:
                self.on_speak("")          # 关窗时顺带停止朗读
            except Exception:
                pass
        try:
            fade(self.win, WINDOW_ALPHA, 0.0, steps=3, delay=10, on_done=self.win.withdraw)
        except Exception:
            self.win.withdraw()

    def visible(self):
        return bool(self.win.winfo_ismapped())

    def bounds(self):
        if not self.visible():
            return None
        return (self.win.winfo_x(), self.win.winfo_y(),
                self.win.winfo_x() + self.win.winfo_width(),
                self.win.winfo_y() + self.win.winfo_height())


# ---------------- 设置窗 ----------------
class SettingsDialog:
    def __init__(self, master, cfg, on_save, on_theme=None):
        self.on_save = on_save
        self.on_theme = on_theme      # 选中主题立即回调 on_theme(theme_id)
        self.cfg = cfg
        set_theme(cfg.get("ui", {}).get("theme", DEFAULT_THEME))
        apply_theme(master)      # 设置窗跟随当前主题
        self.win = tk.Toplevel(master)
        self.win.title("划词翻译 · 设置")
        self.win.configure(bg=BG)
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)

        outer = tk.Frame(self.win, bg=BG, padx=18, pady=14)
        outer.pack(fill="both", expand=True)
        tk.Label(outer, text="划词翻译", bg=BG, fg=FG,
                 font=_font(13, True)).pack(anchor="w")
        tk.Label(outer, text="拖选即译 · 截图取词 · 全部免费", bg=BG, fg=FG_DIM,
                 font=_font(8)).pack(anchor="w", pady=(2, 12))

        ui = cfg.get("ui", {})
        bh = cfg.get("behavior", {})

        # —— 翻译 ——
        sec1 = ttk.Labelframe(outer, text=" 翻译源 ", padding=(12, 8))
        sec1.pack(fill="x", pady=(0, 10))
        self._provider_map = {
            "自动（免密钥：有道 → MyMemory）": "auto",
            "有道演示（免密钥）": "youdao",
            "MyMemory（免密钥）": "mymemory",
        }
        display = {v: k for k, v in self._provider_map.items()}
        row = ttk.Frame(sec1)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text="翻译源", width=14).pack(side="left")
        self.provider = ttk.Combobox(row, values=list(self._provider_map.keys()),
                                     width=30, state="readonly")
        self.provider.set(display.get(cfg.get("provider", "auto"),
                                      "自动（免密钥：有道 → MyMemory）"))
        self.provider.pack(side="left", fill="x", expand=True)

        ttk.Label(sec1, text="全部免密钥，开箱即用",
                  style="Dim.TLabel").pack(anchor="w", pady=(6, 0))

        # —— 外观 ——
        sec2 = ttk.Labelframe(outer, text=" 外观 ", padding=(12, 8))
        sec2.pack(fill="x", pady=(0, 10))
        row = ttk.Frame(sec2)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text="结果字号", width=14).pack(side="left")
        self.font = tk.IntVar(value=int(ui.get("font_size", 11)))
        ttk.Spinbox(row, from_=8, to=16, textvariable=self.font, width=6).pack(side="left")
        ttk.Label(row, text="    结果最大高度(px)", width=22).pack(side="left")
        self.maxh = tk.IntVar(value=int(ui.get("max_result_height", 460)))
        ttk.Spinbox(row, from_=200, to=900, increment=20, textvariable=self.maxh,
                    width=6).pack(side="left")

        row = ttk.Frame(sec2)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text="界面主题", width=14).pack(side="left")
        self._theme_map = {v["label"]: k for k, v in THEMES.items()}
        theme_display = {v: k for k, v in self._theme_map.items()}
        self.theme = ttk.Combobox(row, values=list(self._theme_map.keys()),
                                  width=12, state="readonly")
        self.theme.set(theme_display.get(ui.get("theme", DEFAULT_THEME),
                                         THEMES[DEFAULT_THEME]["label"]))
        self.theme.pack(side="left")
        self.theme.bind("<<ComboboxSelected>>", self._on_theme_pick)
        ttk.Label(row, text="  选中即生效", style="Dim.TLabel").pack(side="left")

        row = ttk.Frame(sec2)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text="图标大小(px)", width=14).pack(side="left")
        self.icon_size = tk.IntVar(value=int(ui.get("icon_size", 34)))
        ttk.Spinbox(row, from_=24, to=56, increment=2, textvariable=self.icon_size,
                    width=6).pack(side="left")

        self.bilingual = tk.BooleanVar(value=bool(ui.get("bilingual", True)))
        ttk.Checkbutton(sec2, text="双语对照（译文下方附英文原文）",
                        variable=self.bilingual).pack(anchor="w", pady=2)

        # —— 行为 ——
        sec3 = ttk.Labelframe(outer, text=" 行为 ", padding=(12, 8))
        sec3.pack(fill="x", pady=(0, 10))
        self.drag_on = tk.BooleanVar(value=bool(bh.get("drag_enabled", True)))
        ttk.Checkbutton(sec3, text="启用拖选翻译（关闭后仅保留截图翻译）",
                        variable=self.drag_on).pack(anchor="w", pady=2)
        self.autostart = tk.BooleanVar(value=bool(cfg.get("autostart", False)))
        ttk.Checkbutton(sec3, text="开机自动启动", variable=self.autostart).pack(anchor="w", pady=2)

        row = ttk.Frame(sec3)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text="退出快捷键", width=14).pack(side="left")
        self.hk_quit = ttk.Entry(row, width=16)
        self.hk_quit.insert(0, bh.get("hotkey_quit", "ctrl+alt+q"))
        self.hk_quit.pack(side="left")
        ttk.Label(row, text="    截图翻译", width=12).pack(side="left")
        self.hk_ocr = ttk.Entry(row, width=16)
        self.hk_ocr.insert(0, bh.get("hotkey_ocr", "ctrl+alt+s"))
        self.hk_ocr.pack(side="left")

        # —— 底栏 ——
        foot = tk.Frame(outer, bg=BG)
        foot.pack(fill="x", pady=(4, 0))
        tk.Label(foot, text="配置文件：%APPDATA%\\hxy-translate\\config.json",
                 bg=BG, fg=SUBTLE, font=_font(8)).pack(side="left")
        ttk.Button(foot, text="保存", style="Accent.TButton",
                   command=self._save).pack(side="right")
        ttk.Button(foot, text="取消", style="Ghost.TButton",
                   command=self.win.destroy).pack(side="right", padx=(0, 8))

    def _on_theme_pick(self, _evt=None):
        """主题下拉选中后立即切换，无需点保存（延迟一拍，等下拉事件处理完）"""
        tid = self._theme_map.get(self.theme.get())
        if tid and self.on_theme:
            cb = self.on_theme
            self.win.after(30, lambda: cb(tid))

    def _save(self):
        new = dict(self.cfg)
        new["provider"] = self._provider_map.get(self.provider.get(), "auto")
        ui = dict(new.get("ui", {}))
        ui["font_size"] = int(self.font.get())
        ui["max_result_height"] = int(self.maxh.get())
        ui["icon_size"] = int(self.icon_size.get())
        ui["theme"] = self._theme_map.get(self.theme.get(), DEFAULT_THEME)
        ui["bilingual"] = bool(self.bilingual.get())
        new["ui"] = ui
        bh = dict(new.get("behavior", {}))
        bh["drag_enabled"] = bool(self.drag_on.get())
        bh["hotkey_quit"] = self.hk_quit.get().strip() or "ctrl+alt+q"
        bh["hotkey_ocr"] = self.hk_ocr.get().strip() or "ctrl+alt+s"
        new["behavior"] = bh
        new["autostart"] = bool(self.autostart.get())
        try:
            self.on_save(new)
        finally:
            self.win.destroy()


# ---------------- 框选遮罩（截图翻译） ----------------
class SelectionOverlay:
    """整屏压暗 + 拖拽虚线选框 + 尺寸提示 + 底部操作提示"""

    def __init__(self, master, on_done, on_cancel=None):
        self.on_done = on_done
        self.on_cancel = on_cancel
        vx, vy, vw, vh = virtual_screen()
        self.origin = (vx, vy)
        self.win = tk.Toplevel(master)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.geometry(f"{vw}x{vh}+{vx}+{vy}")
        self.canvas = tk.Canvas(self.win, bg=OVERLAY_BG, highlightthickness=0,
                                cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.start = None
        self.rect = None
        self.size_label = None

        # 底部提示胶囊
        pill_w, pill_h = 330, 34
        px = vw // 2
        py = vh - 70
        self.canvas.create_rectangle(px - pill_w / 2, py, px + pill_w / 2, py + pill_h,
                                     fill=PILL_BG, outline=BLUE, width=1)
        self.canvas.create_text(px, py + pill_h / 2,
                                text="拖拽框选要翻译的区域 · Esc 取消",
                                fill=PILL_FG, font=(FONT_FAMILY, 10))

        self.canvas.bind("<Button-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.win.bind("<Escape>", lambda e: self._cancel())
        self.win.focus_force()
        fade(self.win, 0.0, OVERLAY_ALPHA, steps=5, delay=12)

    def _press(self, e):
        self.start = (e.x_root, e.y_root)
        if self.rect:
            self.canvas.delete(self.rect)
            self.rect = None
        if self.size_label:
            self.canvas.delete(self.size_label)
            self.size_label = None

    def _drag(self, e):
        if not self.start:
            return
        ox, oy = self.origin
        x0, y0 = self.start[0] - ox, self.start[1] - oy
        x1, y1 = e.x_root - ox, e.y_root - oy
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(x0, y0, x1, y1, outline=BLUE_HOVER,
                                                 width=2, dash=(5, 3))
        if self.size_label:
            self.canvas.delete(self.size_label)
        self.size_label = self.canvas.create_text(
            x1 + 10, y1 + 12, anchor="nw", fill=SIZE_FG,
            font=(FONT_FAMILY, 9),
            text="%d × %d" % (abs(x1 - x0), abs(y1 - y0)))

    def _release(self, e):
        if not self.start:
            return self._cancel()
        x0, y0 = self.start
        x1, y1 = e.x_root, e.y_root
        left, right = sorted((x0, x1))
        top, bottom = sorted((y0, y1))
        self.win.destroy()
        if right - left < 8 or bottom - top < 8:
            if self.on_cancel:
                self.on_cancel()
            return
        self.on_done((left, top, right, bottom))

    def _cancel(self):
        try:
            self.win.destroy()
        except Exception:
            pass
        if self.on_cancel:
            self.on_cancel()
