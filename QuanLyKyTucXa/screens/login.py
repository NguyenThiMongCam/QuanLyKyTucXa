"""Màn hình đăng nhập - giao diện xanh/trắng (Tkinter).

LoginScreen(master, on_success): khi đăng nhập đúng sẽ gọi on_success(user, "staff")
Cổng này CHỈ dành cho quản lý (admin / nhân viên, bảng NhanVien).
"""
import json
import os
import tkinter as tk
from tkinter import messagebox

import database as db

FONT = "Segoe UI"
PRIMARY, NAVY = "#1558C0", "#0B3C8C"
HERO, HERO_ACCENT, HERO_TEXT = "#0B3C8C", "#1E5BC0", "#D6E4FB"
PAGE_BG, BORDER, INPUT_BORDER = "#F3F7FD", "#DCE6F7", "#CBD8EE"
TEXT, MUTED, PLACEHOLDER = "#0F2447", "#4A5A78", "#6B7A96"
SEL_BG, IDLE_BG, IDLE_BORDER = "#E3EEFF", "#F6F9FE", "#D5E1F5"
ERROR = "#B3261E"
ROLE = "admin"   # khóa dùng để nhớ tên đăng nhập trong remember.json
SHADOW = ("#EFF4FC", "#E9F0FA", "#E2EBF8")   # 3 lớp bóng, từ ngoài vào trong

# File nhớ đăng nhập (chỉ lưu vai trò + tên đăng nhập, KHÔNG lưu mật khẩu)
REMEMBER_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "remember.json")


def load_remember():
    try:
        with open(REMEMBER_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_remember(data):
    try:
        with open(REMEMBER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except OSError:
        pass


def rounded_rect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


class FlatButton(tk.Label):
    """Nút phẳng có màu nền + hiệu ứng rê chuột (tk.Button không đổi được màu trên macOS)."""

    def __init__(self, master, text, command, bg=PRIMARY, hover=NAVY, fg="white",
                 font=(FONT, 11, "bold"), **kw):
        super().__init__(master, text=text, bg=bg, fg=fg, font=font, cursor="hand2", takefocus=1, **kw)
        self._bg, self._hover, self._command = bg, hover, command
        self.bind("<Enter>", lambda _e: self.config(bg=self._hover))
        self.bind("<Leave>", lambda _e: self.config(bg=self._bg))
        self.bind("<Button-1>", self._click)
        self.bind("<space>", self._click)

    def _click(self, _e=None):
        self.focus_set()
        self._command()


class Field(tk.Frame):
    """Ô nhập có viền bo, chữ gợi ý (placeholder) và nút Hiện/Ẩn cho mật khẩu."""

    def __init__(self, master, placeholder="", secret=False):
        super().__init__(master, bg="white", highlightthickness=2, highlightbackground=INPUT_BORDER)
        self.placeholder, self.secret = placeholder, secret
        self._ph, self._reveal = False, False
        self.entry = tk.Entry(self, relief="flat", bd=0, font=(FONT, 11), bg="white", fg=TEXT,
                              insertbackground=TEXT, highlightthickness=0)
        if secret:
            self.toggle = tk.Label(self, text="Hiện", bg="white", fg=PRIMARY, cursor="hand2",
                                   font=(FONT, 10, "bold"))
            self.toggle.pack(side="right", padx=(4, 12))
            self.toggle.bind("<Button-1>", self._toggle)
        self.entry.pack(side="left", fill="x", expand=True, padx=(12, 4), ipady=8)
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self._show_placeholder()

    def _mask(self):
        return "" if (not self.secret or self._reveal) else "•"

    def _show_placeholder(self):
        if not self.entry.get():
            self._ph = True
            self.entry.config(fg=PLACEHOLDER, show="")
            self.entry.insert(0, self.placeholder)

    def _focus_in(self, _e=None):
        self.config(highlightbackground=PRIMARY)
        if self._ph:
            self.entry.delete(0, "end")
            self._ph = False
            self.entry.config(fg=TEXT, show=self._mask())

    def _focus_out(self, _e=None):
        self.config(highlightbackground=INPUT_BORDER)
        self._show_placeholder()

    def _toggle(self, _e=None):
        self._reveal = not self._reveal
        self.toggle.config(text="Ẩn" if self._reveal else "Hiện")
        if not self._ph:
            self.entry.config(show=self._mask())

    def get(self):
        return "" if self._ph else self.entry.get()

    def set(self, value):
        self.entry.delete(0, "end")
        self._ph = False
        self.entry.config(fg=TEXT, show=self._mask())
        self.entry.insert(0, value)
        if not value:
            self._show_placeholder()

    def clear(self):
        self.set("")

    def set_placeholder(self, text):
        self.placeholder = text
        if self._ph:
            self.entry.delete(0, "end")
            self.entry.insert(0, text)

    def focus_entry(self):
        self.entry.focus_set()


class RoundedCard(tk.Canvas):
    """Thẻ trắng bo góc + bóng mờ. Đặt widget con vào self.inner."""
    INSET = 10   # lề giữa mép thẻ và khung nội dung (để góc vuông không lòi ra ngoài góc bo)

    def __init__(self, master, outside=PAGE_BG, radius=24, pad=20):
        super().__init__(master, bg=outside, highlightthickness=0, bd=0)
        self.radius, self.pad = radius, pad
        self.inner = tk.Frame(self, bg="white")
        self.create_window(pad + self.INSET, pad + self.INSET, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._redraw)

    def _redraw(self, _e=None):
        w = self.inner.winfo_reqwidth() + 2 * self.INSET
        h = self.inner.winfo_reqheight() + 2 * self.INSET
        p, r = self.pad, self.radius
        self.config(width=w + 2 * p, height=h + 2 * p)
        self.delete("bg")
        for i, color in enumerate(SHADOW):          # bóng đổ lệch xuống 6px
            g = (len(SHADOW) - i) * 3
            rounded_rect(self, p - g, p - g + 6, p + w + g, p + h + g + 6, r + g,
                         fill=color, outline="", tags="bg")
        rounded_rect(self, p, p, p + w, p + h, r, fill="white", outline=BORDER, tags="bg")
        self.tag_lower("bg")


class LoginScreen(tk.Frame):
    def __init__(self, master, on_success):
        super().__init__(master, bg=PAGE_BG)
        self.on_success = on_success
        self._top = master.winfo_toplevel()
        self.remember = tk.BooleanVar(value=False)
        self._saved = load_remember()

        self._build_header()
        self._build_footer()
        body = tk.Frame(self, bg=PAGE_BG)
        body.pack(fill="both", expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1, uniform="half")
        body.columnconfigure(1, weight=1, uniform="half")
        self._build_hero(body)
        self._build_form(body)

        # Điền sẵn tên đăng nhập đã nhớ (nếu có)
        self.remember.set(bool(self._saved.get("users")))
        last = self._saved.get("users", {}).get(ROLE, "")
        if last and self.remember.get():
            self.uid.set(last)

        self._top.bind("<Return>", self._submit)
        self.bind("<Destroy>", self._on_destroy)
        self.after(150, self._focus_first)

    # ------------------------------------------------------------------ giao diện
    def _build_header(self):
        head = tk.Frame(self, bg="white")
        head.pack(side="top", fill="x")
        tk.Frame(head, bg=BORDER, height=1).pack(side="bottom", fill="x")
        inner = tk.Frame(head, bg="white")
        inner.pack(fill="x", padx=40, pady=12)
        logo = tk.Canvas(inner, width=48, height=48, bg="white", highlightthickness=0)
        rounded_rect(logo, 1, 1, 47, 47, 12, fill=PRIMARY, outline=PRIMARY)
        logo.create_text(24, 24, text="🎓", font=(FONT, 17), fill="white")
        logo.pack(side="left")
        txt = tk.Frame(inner, bg="white")
        txt.pack(side="left", padx=14)
        tk.Label(txt, text="BỘ CÔNG THƯƠNG", bg="white", fg=MUTED, font=(FONT, 9, "bold")).pack(anchor="w")
        tk.Label(txt, text="TRƯỜNG ĐẠI HỌC CÔNG THƯƠNG TP. HỒ CHÍ MINH", bg="white", fg=NAVY,
                 font=(FONT, 13, "bold")).pack(anchor="w")
        tk.Label(inner, text="Hệ thống quản lý ký túc xá", bg="white", fg=PRIMARY,
                 font=(FONT, 10, "bold")).pack(side="right")

    def _build_footer(self):
        foot = tk.Frame(self, bg="white")
        foot.pack(side="bottom", fill="x")
        tk.Frame(foot, bg=BORDER, height=1).pack(side="top", fill="x")
        tk.Label(foot, text="© Trường Đại học Công Thương TP.HCM · Ban quản lý ký túc xá",
                 bg="white", fg=MUTED, font=(FONT, 9)).pack(anchor="w", padx=40, pady=8)

    def _build_hero(self, body):
        left = tk.Frame(body, bg=HERO)
        left.grid(row=0, column=0, sticky="nsew")
        box = tk.Frame(left, bg=HERO)
        box.place(relx=0, x=56, rely=0.5, anchor="w")
        tk.Label(box, text="Ký túc xá sinh viên", bg=HERO_ACCENT, fg="white", font=(FONT, 10, "bold"),
                 padx=12, pady=4).pack(anchor="w")
        tk.Label(box, text="Quản lý ký túc xá\nnhanh gọn, minh bạch", bg=HERO, fg="white",
                 font=(FONT, 26, "bold"), justify="left").pack(anchor="w", pady=(14, 8))
        tk.Label(box, text="Đăng nhập bằng mã sinh viên để xem thông tin phòng, hóa đơn điện nước, "
                           "gửi yêu cầu sửa chữa và nhận thông báo từ Ban quản lý.",
                 bg=HERO, fg=HERO_TEXT, font=(FONT, 11), wraplength=400, justify="left").pack(anchor="w")
        features = [
            ("🏠", "Đăng ký & gia hạn phòng", "trực tuyến, xem tình trạng chỗ ở"),
            ("💳", "Tra cứu hóa đơn", "tiền phòng, điện, nước theo từng tháng"),
            ("🔧", "Gửi yêu cầu sửa chữa", "và theo dõi tiến độ xử lý"),
            ("🔔", "Nhận thông báo", "lịch cắt điện nước, nội quy và sự kiện"),
        ]
        lst = tk.Frame(box, bg=HERO)
        lst.pack(anchor="w", pady=(22, 18))
        for icon, title, desc in features:
            row = tk.Frame(lst, bg=HERO)
            row.pack(anchor="w", pady=7)
            tk.Label(row, text=icon, bg=HERO_ACCENT, fg="white", font=(FONT, 13), width=3, pady=6).pack(side="left")
            col = tk.Frame(row, bg=HERO)
            col.pack(side="left", padx=14)
            # Một dòng: tiêu đề in đậm + mô tả chữ thường (giống thiết kế)
            tk.Label(col, text=title, bg=HERO, fg="white", font=(FONT, 10, "bold")).pack(side="left")
            tk.Label(col, text=" " + desc, bg=HERO, fg=HERO_TEXT, font=(FONT, 10)).pack(side="left")
        tk.Label(box, text="Cần hỗ trợ? Liên hệ Ban quản lý KTX: [SỐ ĐIỆN THOẠI] · [EMAIL KTX]",
                 bg=HERO, fg=HERO_TEXT, font=(FONT, 9)).pack(anchor="w")

    def _build_form(self, body):
        right = tk.Frame(body, bg=PAGE_BG)
        right.grid(row=0, column=1, sticky="nsew")
        card = RoundedCard(right)
        card.place(relx=0.5, rely=0.5, anchor="center")
        pad = tk.Frame(card.inner, bg="white")
        pad.pack(padx=22, pady=18)
        pad.columnconfigure(0, minsize=380, weight=1)

        def put(r, widget, pady=(0, 0)):
            widget.grid(row=r, column=0, sticky="ew", pady=pady)

        put(0, tk.Label(pad, text="Đăng nhập hệ thống", bg="white", fg=NAVY, font=(FONT, 19, "bold"),
                        anchor="w"), pady=(0, 2))
        put(1, tk.Label(pad, text="Nhập thông tin tài khoản dành cho quản lý.", bg="white", fg=MUTED,
                        font=(FONT, 10), anchor="w"), pady=(0, 16))

        # Thẻ "QUẢN LÝ" (thay cho 2 nút chọn vai trò cũ)
        badge = tk.Frame(pad, bg=SEL_BG, highlightthickness=2, highlightbackground=PRIMARY)
        tk.Label(badge, text="🛡", bg=SEL_BG, fg=NAVY, font=(FONT, 13)).pack(side="left", padx=(14, 8), pady=10)
        tk.Label(badge, text="QUẢN LÝ", bg=SEL_BG, fg=NAVY, font=(FONT, 10, "bold")).pack(side="left")
        put(2, badge, pady=(0, 16))

        put(3, tk.Label(pad, text="Tên đăng nhập", bg="white", fg=TEXT, font=(FONT, 10, "bold"), anchor="w"),
            pady=(0, 4))
        self.uid = Field(pad, "Nhập tên đăng nhập quản lý")
        put(4, self.uid, pady=(0, 12))
        put(5, tk.Label(pad, text="Mật khẩu", bg="white", fg=TEXT, font=(FONT, 10, "bold"), anchor="w"),
            pady=(0, 4))
        self.pw = Field(pad, "Nhập mật khẩu", secret=True)
        put(6, self.pw, pady=(0, 10))

        opts = tk.Frame(pad, bg="white")
        tk.Checkbutton(opts, text="Ghi nhớ đăng nhập trên máy này", variable=self.remember, bg="white",
                       activebackground="white", fg=TEXT, font=(FONT, 10), highlightthickness=0,
                       cursor="hand2").pack(side="left")
        forgot = tk.Label(opts, text="Quên mật khẩu?", bg="white", fg=PRIMARY, font=(FONT, 10, "bold"),
                          cursor="hand2")
        forgot.pack(side="right")
        forgot.bind("<Button-1>", lambda _e: messagebox.showinfo(
            "Quên mật khẩu", "Vui lòng liên hệ quản trị hệ thống để được cấp lại mật khẩu."))
        put(7, opts, pady=(0, 6))

        self.msg = tk.Label(pad, text="", bg="white", fg=ERROR, font=(FONT, 10), anchor="w",
                            justify="left", wraplength=380)
        put(8, self.msg, pady=(0, 6))
        put(9, FlatButton(pad, "Đăng nhập", self._submit, pady=11, font=(FONT, 12, "bold")))
        put(10, tk.Label(pad, text="Tài khoản quản lý do quản trị hệ thống cấp. Nếu quên hoặc bị khóa "
                                   "tài khoản, vui lòng liên hệ quản trị viên để được hỗ trợ.",
                         bg="white", fg=MUTED, font=(FONT, 9), wraplength=380, justify="center"),
            pady=(12, 0))

    # ------------------------------------------------------------------ xử lý
    def _focus_first(self):
        try:
            (self.pw if self.uid.get() else self.uid).focus_entry()
        except tk.TclError:
            pass

    def _error(self, text):
        self.msg.config(text=text)

    def _submit(self, _e=None):
        username, password = self.uid.get().strip(), self.pw.get()
        if not username or not password:
            self._error("Vui lòng nhập tên đăng nhập và mật khẩu.")
            return
        user = db.login(username, password)
        if not user:
            self._error("Sai tên đăng nhập hoặc mật khẩu.")
            return
        self._remember(username)
        self._top.unbind("<Return>")
        self.on_success(user, "staff")

    def _remember(self, username):
        users = self._saved.get("users", {})
        if self.remember.get():
            users[ROLE] = username          # chỉ nhớ tên đăng nhập, KHÔNG lưu mật khẩu
            save_remember({"role": ROLE, "users": users})
        else:
            save_remember({})

    def _on_destroy(self, e):
        if e.widget is self:
            try:
                self._top.unbind("<Return>")
            except tk.TclError:
                pass