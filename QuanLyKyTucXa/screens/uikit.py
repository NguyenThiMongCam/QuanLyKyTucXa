"""Thành phần giao diện bổ sung dùng chung cho các trang Dịch vụ / Nhân viên.

Độc lập với screens/sinhvien.py nên không bị ảnh hưởng khi bộ thành phần ở đó thay đổi:
- glyph(): biểu tượng nét mảnh trong ô 16x16 (quạt, điện, đèn, nước, cửa, giường, wifi, người, đồng hồ...)
- ActionButton: nút bo góc có icon, đổi chữ / icon / kiểu được (primary | outline | danger | success)
- draw_dot(), room_cell(), two_lines(), fit(): vẽ vòng tròn icon, ô 2 dòng, rút gọn chữ
"""
import tkinter as tk
from math import cos, pi, sin
from tkinter import font as tkfont

from screens.login import BORDER, FONT, MUTED, NAVY, PAGE_BG, PRIMARY, TEXT, rounded_rect

DANGER, GREEN_FG = "#C0392B", "#0E7A3B"
TRACK, BAR_OK = "#D9E1F0", "#1E9E4A"

# bg, bg khi rê chuột, chữ, viền, chữ khi vô hiệu
STYLES = {"primary": (PRIMARY, NAVY, "white", PRIMARY, "#9DB8E8"),
          "outline": ("white", "#EEF4FF", NAVY, "#CBD8EE", "#9AA8C0"),
          "danger": ("white", "#FDECEC", DANGER, "#F0CFCB", "#E4A9A3"),
          "success": ("white", "#EAF8EF", GREEN_FG, "#BFE3CB", "#9CC7AB")}


def _bg_of(widget):
    try:
        return widget.cget("bg")
    except tk.TclError:
        return PAGE_BG


def fit(text, maxw, font):
    """Rút gọn chữ cho vừa bề rộng maxw bằng dấu …"""
    text = "" if text is None else str(text)
    if font.measure(text) <= maxw:
        return text
    while text and font.measure(text + "…") > maxw:
        text = text[:-1]
    return text + "…" if text else ""


def glyph(cv, name, x, y, color, w=1.8, sc=1, tags=()):
    """Vẽ icon nét mảnh trong ô 16x16 (nhân hệ số sc) tại góc trên-trái (x, y)."""
    def P(*p):
        return [v * sc + (x if i % 2 == 0 else y) for i, v in enumerate(p)]

    def line(*p, **kw):
        cv.create_line(*P(*p), fill=color, width=w, capstyle="round", joinstyle="round", tags=tags, **kw)
    if name == "plus":
        line(8, 3, 8, 13)
        line(3, 8, 13, 8)
    elif name == "edit":
        line(2.5, 13.5, 3.2, 10, 11, 2.2, 13.8, 5, 6, 12.8, 2.5, 13.5)
        line(9.2, 4, 12, 6.8)
    elif name == "trash":
        line(2.5, 4.5, 13.5, 4.5)
        line(6, 4.5, 6, 2.5, 10, 2.5, 10, 4.5)
        line(4, 4.5, 4.8, 13.5, 11.2, 13.5, 12, 4.5)
        line(6.8, 7, 6.8, 11)
        line(9.2, 7, 9.2, 11)
    elif name in ("download", "upload"):
        line(2.5, 10, 2.5, 13.5, 13.5, 13.5, 13.5, 10)
        if name == "download":
            line(8, 2.5, 8, 10.5)
            line(4.8, 7.5, 8, 10.7, 11.2, 7.5)
        else:
            line(8, 10.5, 8, 2.5)
            line(4.8, 5.5, 8, 2.3, 11.2, 5.5)
    elif name == "list":
        line(2.5, 4, 13.5, 4)
        line(2.5, 8, 13.5, 8)
        line(2.5, 12, 9.5, 12)
    elif name == "search":
        cv.create_oval(*P(2, 2, 11, 11), outline=color, width=w, tags=tags)
        line(10, 10, 14, 14)
    elif name == "user":                                  # người
        cv.create_oval(*P(5.2, 2.2, 10.8, 7.8), outline=color, width=w, tags=tags)
        cv.create_arc(*P(2.5, 9.5, 13.5, 20.5), start=30, extent=120, style="arc", outline=color, width=w, tags=tags)
    elif name == "users":                                 # nhóm người
        cv.create_oval(*P(2.5, 3, 7, 7.5), outline=color, width=w, tags=tags)
        cv.create_arc(*P(1, 9, 8.5, 17), start=20, extent=140, style="arc", outline=color, width=w, tags=tags)
        cv.create_oval(*P(9, 3, 13.5, 7.5), outline=color, width=w, tags=tags)
        cv.create_arc(*P(7.5, 9, 15, 17), start=20, extent=140, style="arc", outline=color, width=w, tags=tags)
    elif name == "briefcase":                             # cặp công tác
        cv.create_rectangle(*P(2, 5.5, 14, 13.5), outline=color, width=w, tags=tags)
        line(6, 5.5, 6, 3.2, 10, 3.2, 10, 5.5)
        line(2, 9, 14, 9)
    elif name == "gear":                                  # bánh răng
        cv.create_oval(*P(5.2, 5.2, 10.8, 10.8), outline=color, width=w, tags=tags)
        for k in range(8):
            a = k * pi / 4
            line(8 + 4.3 * cos(a), 8 + 4.3 * sin(a), 8 + 6.5 * cos(a), 8 + 6.5 * sin(a))
    elif name == "mail":                                  # thư
        cv.create_rectangle(*P(2, 3.5, 14, 12.5), outline=color, width=w, tags=tags)
        line(2.3, 4, 8, 9, 13.7, 4)
    elif name == "clock":                                 # đồng hồ
        cv.create_oval(*P(2.5, 2.5, 13.5, 13.5), outline=color, width=w, tags=tags)
        line(8, 5, 8, 8, 10.5, 9.5)
    elif name == "check":
        line(3, 8.5, 6.8, 12, 13, 4.5)
    elif name == "tool":                                  # cờ lê
        line(3, 13, 8.2, 7.8)
        cv.create_oval(*P(7.5, 2, 13.5, 8), outline=color, width=w, tags=tags)
    elif name == "fan":                                   # quạt: 3 cánh
        for a in (-1.57, 0.52, 2.62):
            pts = (8, 8) + tuple(8 + 6.3 * f(a + d) for d in (-0.5, 0.5) for f in (cos, sin))
            cv.create_polygon(*P(*pts), fill=color, outline=color, smooth=True, tags=tags)
    elif name == "bolt":                                  # điện
        line(9.5, 1.5, 4, 9, 8, 9, 6.5, 14.5, 12, 7, 8, 7, 9.5, 1.5)
    elif name == "bulb":                                  # bóng đèn
        cv.create_oval(*P(4, 1.5, 12, 9.5), outline=color, width=w, tags=tags)
        line(6, 12, 10, 12)
        line(6.8, 14.2, 9.2, 14.2)
        line(6.5, 9.2, 6.5, 12)
        line(9.5, 9.2, 9.5, 12)
    elif name == "drop":                                  # nước
        line(8, 2, 4.8, 7.6, 4.6, 10, 6, 12.6, 8, 13.6, 10, 12.6, 11.4, 10, 11.2, 7.6, 8, 2, smooth=True)
    elif name == "door":                                  # cửa
        line(4, 14, 4, 2.5, 12, 2.5, 12, 14)
        line(2.5, 14, 13.5, 14)
        cv.create_oval(*P(9, 8, 10.4, 9.4), fill=color, outline=color, tags=tags)
    elif name == "bed":                                   # giường / tủ
        line(2.5, 3.5, 2.5, 13)
        line(2.5, 10.5, 13.5, 10.5, 13.5, 13)
        line(2.5, 8, 13.5, 8, 13.5, 10.5)
        cv.create_rectangle(*P(4.2, 5.2, 7.6, 7.6), outline=color, width=w, tags=tags)
    elif name == "wifi":                                  # mạng
        for r in (3, 6, 9):
            cv.create_arc(*P(8 - r, 12.5 - r, 8 + r, 12.5 + r), start=48, extent=84, style="arc",
                          outline=color, width=w, tags=tags)
        cv.create_oval(*P(7.2, 11.7, 8.8, 13.3), fill=color, outline=color, tags=tags)


class ActionButton(tk.Canvas):
    """Nút bo góc có icon (cùng kích thước / màu với IconButton của trang Sinh viên) + restyle() để đổi vai trò."""
    H = 44

    def __init__(self, master, text, icon, command, style="outline", enabled=True):
        self.font = tkfont.Font(family=FONT, size=10, weight="bold")
        self.text, self.icon, self.command, self.style = text, icon, command, style
        super().__init__(master, height=self.H, width=self._width(), bg=_bg_of(master), highlightthickness=0)
        self.enabled, self.hover = enabled, False
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Button-1>", lambda _e: self.command() if self.enabled else None)
        self._draw()

    def _width(self):
        return self.font.measure(self.text) + (62 if self.icon else 36)

    def set_enabled(self, flag):
        self.enabled = bool(flag)
        self._draw()

    def _set_hover(self, flag):
        self.hover = flag and self.enabled
        self._draw()

    def restyle(self, text, icon, style):
        self.text, self.icon, self.style = text, icon, style
        self.config(width=self._width())
        self._draw()

    def _draw(self):
        bg, hover, fg, border, dis = STYLES[self.style]
        self.delete("all")
        self.config(cursor="hand2" if self.enabled else "arrow")
        w = int(self.cget("width"))
        if not self.enabled:
            fill, line, color = ("#BFD3F5", "#BFD3F5", "white") if self.style == "primary" else ("white", BORDER, dis)
        else:
            fill, line, color = (hover if self.hover else bg), border, fg
        rounded_rect(self, 1, 1, w - 1, self.H - 1, 10, fill=fill, outline=line)
        if self.icon:
            glyph(self, self.icon, 20, self.H / 2 - 8, color)
        self.create_text(46 if self.icon else 18, self.H / 2, text=self.text, anchor="w", font=self.font, fill=color)


def draw_dot(cv, icon, fg, bg, cx, cy, r=12, tags=()):
    """Vòng tròn màu chứa biểu tượng."""
    cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=bg, outline=bg, tags=tags)
    s = r * 1.05 / 8
    glyph(cv, icon, cx - 8 * s, cy - 8 * s, fg, w=1.5, sc=s, tags=tags)


def _small(t):
    """Font chữ nhỏ của bảng (bảng chung của sinhvien.py không có sẵn nên tạo khi cần)."""
    if "f_small" not in vars(t):
        t.f_small = tkfont.Font(family=FONT, size=8)
    return t.f_small


def room_cell(t, r, tx, cy, maxw, tag):
    """Ô 2 dòng trong bảng: tên phòng + người phụ trách."""
    b, pt, fs = t.body, r.get("PhuTrach"), _small(t)
    b.create_text(tx, cy - 8, text=t._fit(r["TenPhong"], maxw, t.f_bold), anchor="w", font=t.f_bold, fill=NAVY,
                  tags=tag)
    glyph(b, "user", tx, cy + 3, MUTED if pt else "#B0B8C8", w=1.2, sc=0.7, tags=tag)
    b.create_text(tx + 14, cy + 9, text=t._fit(pt or "Chưa phân công", maxw - 14, fs), anchor="w", font=fs,
                  fill=MUTED if pt else "#B0B8C8", tags=tag)


def two_lines(t, tx, cy, maxw, tag, top, sub, sub_fg=MUTED):
    """Ô 2 dòng: dòng trên bình thường, dòng dưới chữ nhỏ; không có dữ liệu thì hiện '—'."""
    b, fs = t.body, _small(t)
    if not top:
        b.create_text(tx, cy, text="—", anchor="w", font=t.f_norm, fill="#B0B8C8", tags=tag)
        return
    b.create_text(tx, cy - 7, text=t._fit(top, maxw, t.f_norm), anchor="w", font=t.f_norm, fill=TEXT, tags=tag)
    b.create_text(tx, cy + 9, text=t._fit(sub, maxw, fs), anchor="w", font=fs, fill=sub_fg, tags=tag)