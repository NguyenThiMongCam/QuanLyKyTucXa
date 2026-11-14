"""Thanh điều hướng bên trái dùng chung cho giao diện quản trị và sinh viên (icon nét mảnh, mục đang chọn bo tròn)."""
import tkinter as tk

from screens.icons_data import ICONS
from screens.login import FONT, PRIMARY, rounded_rect

SIDE, SIDE_HOVER, SIDE_TEXT = "#0B2F6B", "#16408A", "#D6E4FB"


def load_icon(name):
    """Nạp icon từ dữ liệu nhúng sẵn (icons_data.py); lỗi thì trả None để thanh bên dùng chấm dự phòng."""
    try:
        return tk.PhotoImage(data=ICONS[name])
    except (KeyError, tk.TclError):
        return None


class Sidebar(tk.Frame):
    """items: [(key, nhãn, tên icon)]. Gọi on_select(key) khi bấm; set_active(key) để tô mục đang chọn."""

    def __init__(self, master, subtitle, items, on_select, on_logout, width=260):
        super().__init__(master, bg=SIDE, width=width)
        self.pack_propagate(False)
        self.rows, self.active = {}, None
        self._img = {}                                  # giữ tham chiếu ảnh để Tk không xóa
        logo = tk.Canvas(self, width=92, height=44, bg=SIDE, highlightthickness=0)
        rounded_rect(logo, 1, 1, 91, 43, 11, fill=PRIMARY, outline=PRIMARY)
        logo.create_text(46, 23, text="HUIT", font=(FONT, 17, "bold"), fill="white")
        logo.pack(pady=(28, 8))
        tk.Label(self, text="KÝ TÚC XÁ", bg=SIDE, fg="white", font=(FONT, 16, "bold")).pack()
        tk.Label(self, text="Trường ĐH Công Thương TP.HCM", bg=SIDE, fg="#9DB8E8", font=(FONT, 9)).pack(pady=(1, 0))
        self.sub = tk.Label(self, text=subtitle, bg=SIDE, fg="#BBD0F2", font=(FONT, 10), wraplength=width - 40)
        self.sub.pack(pady=(10, 22))
        for key, text, icon in items:
            self._row(self, key, text, icon, lambda k=key: on_select(k), red=False)
        self._row(self, "_logout", "Đăng xuất", "logout", on_logout, red=True, bottom=True)

    def _row(self, parent, key, text, icon, command, red, bottom=False):
        fg = "#FFC9C9" if red else SIDE_TEXT
        row = tk.Frame(parent, bg=SIDE, cursor="hand2")
        if bottom:
            row.pack(side="bottom", fill="x", padx=16, pady=(0, 22))
        else:
            row.pack(fill="x", padx=16, pady=2)
        suffix = "_red" if red else ""
        self._img[key] = (load_icon(icon + suffix), load_icon(icon + "_on"), load_icon(icon))
        if self._img[key][0]:                      # có icon: ô ảnh 20x20 px
            ic = tk.Label(row, image=self._img[key][0], bg=SIDE, width=20, height=20)
        else:                                      # thiếu file icon: dùng chấm nhỏ (width/height tính bằng KÝ TỰ, không phải px)
            ic = tk.Label(row, text="●", bg=SIDE, fg=fg, font=(FONT, 9), width=2)
        ic.pack(side="left", padx=(16, 10), pady=12)
        lb = tk.Label(row, text=text, bg=SIDE, fg=fg, font=(FONT, 11, "bold"), anchor="w")
        lb.pack(side="left", fill="x", expand=True)
        self.rows[key] = (row, ic, lb, red)
        for w in (row, ic, lb):
            w.bind("<Button-1>", lambda _e: command())
            w.bind("<Enter>", lambda _e, k=key: self._paint(k, hover=True))
            w.bind("<Leave>", lambda _e, k=key: self._paint(k, hover=False))

    def _paint(self, key, hover=False):
        row, ic, lb, red = self.rows[key]
        on = key == self.active
        bg = PRIMARY if on else (("#7A1F2B" if red else SIDE_HOVER) if hover else SIDE)
        fg = "white" if on else ("#FFC9C9" if red else SIDE_TEXT)
        for w in (row, ic, lb):
            w.config(bg=bg)
        lb.config(fg=fg)
        if not self._img[key][0]:
            ic.config(fg=fg)
        imgs = self._img[key]
        img = imgs[1] if on else imgs[0]
        if img:
            ic.config(image=img)

    def set_active(self, key):
        old, self.active = self.active, key
        for k in (old, key):
            if k in self.rows:
                self._paint(k)

    def set_subtitle(self, text):
        self.sub.config(text=text)