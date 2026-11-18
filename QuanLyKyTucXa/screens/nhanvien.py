"""Trang Nhân viên (chỉ quản lý/admin thấy) - giao diện theo mẫu thiết kế.

Dữ liệu dùng chung với các trang khác:
  * Chức vụ   -> quyết định quyền đăng nhập ("Quản lý" = admin; các chức vụ khác = nhân viên).
  * Trạng thái "Tạm khóa" -> tài khoản không đăng nhập được (màn hình đăng nhập báo rõ lý do).
  * Phòng phụ trách -> cột Phong.MaNV: trang Phòng hiển thị cột "Phụ trách" và cho chọn lại nhân viên phụ trách,
    nên sửa ở trang nào thì trang kia cũng đổi theo.
Tính năng: tìm kiếm tức thì (không dấu cũng tìm được, tìm cả tên phòng), chọn số bản ghi / phân trang,
tick chọn nhiều dòng để xóa, ảnh đại diện (PNG/GIF; JPG nếu máy có Pillow), xuất Excel, xuất PDF (qua trình duyệt).
"""
import html
import math
import os
import re
import shutil
import sqlite3
import tempfile
import tkinter as tk
import webbrowser
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import database as db
from screens import xlsx_io
from screens.base import error
from screens.login import (BORDER, ERROR, FONT, INPUT_BORDER, MUTED, NAVY, PAGE_BG, PLACEHOLDER, PRIMARY, SEL_BG, TEXT,
                           FlatButton, rounded_rect)
from screens.sinhvien import GREEN_BG, GREEN_FG, LINE, Card, DataTable, IconButton, SearchBox, draw_icon, fold

ACTIVE, LOCKED = "Đang hoạt động", "Tạm khóa"
ORANGE_FG, ORANGE_BG = "#A8590B", "#FDEBD3"
AVATAR_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "avatars")
SOFT_BLUE = "#E3EEFF"
PAGE_SIZES = ["5", "10", "20", "50"]

STAFF_COLS = [("STT", "STT", 44, 0.3), ("Anh", "Ảnh đại diện", 92, 0.8), ("HoTen", "Tên nhân viên", 150, 1.5),
              ("ChucVu", "Chức vụ", 88, 0.9), ("Phong", "Phòng phụ trách", 116, 1.2), ("SDT", "Số điện thoại", 104, 1.0),
              ("Email", "Email", 160, 1.4), ("TrangThai", "Trạng thái", 140, 1.2), ("ThaoTac", "Thao tác", 96, 0.8)]
CENTER = {"STT", "Anh", "TrangThai", "ThaoTac"}


# ====================================================================== ảnh đại diện
_IMG_CACHE = {}


def load_avatar(path, size):
    """Ảnh vuông size x size (cắt giữa). Trả về PhotoImage hoặc None nếu không đọc được."""
    if not path or not os.path.isfile(path):
        return None
    key = (path, size, os.path.getmtime(path))
    if key in _IMG_CACHE:
        return _IMG_CACHE[key]
    img = None
    try:
        try:
            from PIL import Image, ImageTk                     # có Pillow thì đọc được cả JPG, ảnh đẹp hơn
            im = Image.open(path).convert("RGB")
            w, h = im.size
            s = min(w, h)
            im = im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((size, size))
            img = ImageTk.PhotoImage(im)
        except ImportError:                                    # chỉ dùng tkinter: PNG / GIF
            src = tk.PhotoImage(file=path)
            w, h = src.width(), src.height()
            s = min(w, h)
            x0, y0 = (w - s) // 2, (h - s) // 2
            img = tk.PhotoImage()
            if s >= size:
                n = max(1, round(s / size))
                img.tk.call(img.name, "copy", src.name, "-from", x0, y0, x0 + s, y0 + s, "-subsample", n, n)
            else:
                z = max(1, round(size / s))
                img.tk.call(img.name, "copy", src.name, "-from", x0, y0, x0 + s, y0 + s, "-zoom", z, z)
    except (tk.TclError, OSError, ValueError):
        return None
    _IMG_CACHE[key] = img
    return img


def draw_avatar(cv, cx, cy, size, path, bg):
    """Vẽ ảnh tròn (hoặc hình người mặc định nếu chưa có ảnh) tại tâm (cx, cy). Trả về ảnh để giữ tham chiếu."""
    r = size / 2
    img = load_avatar(path, size)
    if img is not None:
        cv.create_image(cx, cy, image=img)
        w = size * 0.23                                         # vòng màu nền che 4 góc ảnh -> thành hình tròn
        cv.create_oval(cx - r - w / 2, cy - r - w / 2, cx + r + w / 2, cy + r + w / 2, outline=bg, width=w)
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline=BORDER, width=1)
        return img
    cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=SOFT_BLUE, outline=SOFT_BLUE)
    cv.create_oval(cx - r * .27, cy - r * .5, cx + r * .27, cy + r * .04, fill="#4B8BE8", outline="")
    cv.create_arc(cx - r * .55, cy + r * .12, cx + r * .55, cy + r * 1.15, start=0, extent=180, fill="#4B8BE8",
                  outline="")
    return None


# ====================================================================== thành phần nhỏ
class Pill(tk.Canvas):
    """Nhãn bo tròn (vd. '↑ +1')."""

    def __init__(self, master, text="", fg=GREEN_FG, fill=GREEN_BG, bg="white"):
        self.font = tkfont.Font(family=FONT, size=9, weight="bold")
        super().__init__(master, height=28, bg=bg, highlightthickness=0)
        self.fg, self.fill = fg, fill
        self.set(text)

    def set(self, text):
        w = self.font.measure(text) + 22
        self.config(width=w)
        self.delete("all")
        rounded_rect(self, 0, 0, w, 28, 14, fill=self.fill, outline=self.fill)
        self.create_text(w / 2, 14, text=text, font=self.font, fill=self.fg)


class PageBtn(tk.Canvas):
    """Nút phân trang vuông bo góc: ←  1  2  →"""

    def __init__(self, master, text, command, active=False, enabled=True):
        super().__init__(master, width=42, height=42, bg="white", highlightthickness=0,
                         cursor="hand2" if enabled else "arrow")
        font = tkfont.Font(family=FONT, size=11, weight="bold")
        rounded_rect(self, 1, 1, 41, 41, 10, fill=PRIMARY if active else "white", outline=PRIMARY if active else BORDER)
        color = "white" if active else (NAVY if enabled else "#B8C4DA")
        if text in ("prev", "next"):
            d = -1 if text == "prev" else 1
            self.create_line(21 - 8 * d, 21, 21 + 8 * d, 21, fill=color, width=2, capstyle="round")
            self.create_line(21 + 2 * d, 14, 21 + 8 * d, 21, 21 + 2 * d, 28, fill=color, width=2, capstyle="round",
                             joinstyle="round")
        else:
            self.create_text(21, 21, text=text, font=font, fill=color)
        if enabled:
            self.bind("<Button-1>", lambda _e: command())


def stat_icon(cv, kind):
    """Biểu tượng trong thẻ thống kê (vẽ tay): người / cặp tài liệu / bánh răng / thư."""
    c = PRIMARY
    cv.create_oval(2, 2, 70, 70, fill=SOFT_BLUE, outline=SOFT_BLUE)
    if kind == "people":
        for dx, s in ((-13, .75), (13, .75), (0, 1.0)):
            cx = 36 + dx
            cv.create_oval(cx - 6 * s, 24 - 2 * s, cx + 6 * s, 24 + 10 * s, fill=c, outline="")
            cv.create_arc(cx - 11 * s, 36, cx + 11 * s, 36 + 24 * s, start=0, extent=180, fill=c, outline="")
    elif kind == "case":
        cv.create_rectangle(29, 21, 43, 29, outline=c, width=3)
        rounded_rect(cv, 20, 27, 52, 50, 4, fill=c, outline=c)
        cv.create_line(20, 37, 52, 37, fill=SOFT_BLUE, width=2)
        cv.create_rectangle(33, 34, 39, 40, fill=SOFT_BLUE, outline=SOFT_BLUE)
    elif kind == "gear":
        for i in range(8):
            a = math.radians(i * 45)
            cv.create_line(36 + 10 * math.cos(a), 36 + 10 * math.sin(a), 36 + 17 * math.cos(a), 36 + 17 * math.sin(a),
                           fill=c, width=7)
        cv.create_oval(24, 24, 48, 48, fill=c, outline=c)
        cv.create_oval(31, 31, 41, 41, fill=SOFT_BLUE, outline=SOFT_BLUE)
    elif kind == "mail":
        rounded_rect(cv, 19, 24, 53, 49, 4, fill=c, outline=c)
        cv.create_line(21, 27, 36, 40, 51, 27, fill="white", width=2.5, capstyle="round", joinstyle="round")


class StaffTable(DataTable):
    """Bảng nhân viên: ô tick chọn nhiều dòng, ảnh tròn, huy hiệu trạng thái, nút Sửa/Xóa trên từng dòng."""
    ROW_H, RADIO_W = 62, 58
    AV = 42

    def __init__(self, master, handlers):
        super().__init__(master, lambda _i: None, lambda: None, STAFF_COLS, "MaNV")
        self.h = handlers                    # {"toggle": f(ma), "toggle_all": f(), "edit": f(ma), "delete": f(ma)}
        self.checked = set()
        self._imgs, self._hits = [], []
        self.body.config(cursor="arrow")
        self.head.bind("<Button-1>", self._head_click)

    def load(self, rows):
        self.rows = list(rows)
        self._draw()

    def _layout(self, width):                # cửa sổ hẹp thì thu nhỏ đều các cột thay vì bị cắt
        avail = max(width - self.RADIO_W, 1)
        mins = sum(c[2] for c in self.columns)
        if avail >= mins:
            return super()._layout(width)
        out, x, k = [], self.RADIO_W, avail / mins
        for key, _h, mn, _w in self.columns:
            out.append((key, x, mn * k))
            x += mn * k
        return out

    @staticmethod
    def _check(cv, cx, cy, state):
        fill = PRIMARY if state else "white"
        rounded_rect(cv, cx - 9, cy - 9, cx + 9, cy + 9, 4, fill=fill, outline=PRIMARY if state else "#8A97B0")
        if state == 1:
            cv.create_line(cx - 4, cy, cx - 1, cy + 4, cx + 5, cy - 4, fill="white", width=2, capstyle="round",
                           joinstyle="round")
        elif state == 2:                                       # chọn một phần
            cv.create_line(cx - 4, cy, cx + 4, cy, fill="white", width=2, capstyle="round")

    def _badge_center(self, text, fg, fill, x, cw, cy):
        text = self._fit(text, max(cw - 20, 10), self.f_bold)
        bw = self.f_bold.measure(text) + 22
        bx = x + (cw - bw) / 2
        rounded_rect(self.body, bx, cy - 13, bx + bw, cy + 13, 13, fill=fill, outline=fill)
        self.body.create_text(bx + bw / 2, cy, text=text, font=self.f_bold, fill=fg)

    def _draw(self):
        b, h = self.body, self.head
        b.delete("all")
        h.delete("all")
        self._imgs, self._hits = [], []
        w = max(b.winfo_width(), 1)
        cols = self._layout(w)
        ids = [r["MaNV"] for r in self.rows]
        n = sum(1 for i in ids if i in self.checked)
        self._check(h, 29, self.HEAD_H / 2, 0 if n == 0 else (1 if n == len(ids) else 2))
        for (key, x, cw), col in zip(cols, self.columns):
            if key in CENTER:
                h.create_text(x + cw / 2, self.HEAD_H / 2, text=col[1], font=self.f_bold, fill="#3B4A6B")
            else:
                h.create_text(x + 12, self.HEAD_H / 2, text=col[1], anchor="w", font=self.f_bold, fill="#3B4A6B")
        h.create_line(0, self.HEAD_H - 1, w + 2000, self.HEAD_H - 1, fill=LINE)
        if not self.rows:
            b.create_text(w / 2, 70, text="Không có nhân viên phù hợp.", fill=MUTED, font=self.f_norm)
            b.configure(scrollregion=(0, 0, w, 1))
            return
        for i, r in enumerate(self.rows):
            y, cy = i * self.ROW_H, i * self.ROW_H + self.ROW_H / 2
            checked = r["MaNV"] in self.checked
            bg = SEL_BG if checked else "white"
            if checked:
                b.create_rectangle(0, y, w, y + self.ROW_H, fill=bg, outline=bg)
            self._check(b, 29, cy, 1 if checked else 0)
            hits = {}
            for key, x, cw in cols:
                mx, maxw = x + 12, max(cw - 24, 10)
                if key == "Anh":
                    img = draw_avatar(b, x + cw / 2, cy, self.AV, r.get("AnhPath"), bg)
                    if img is not None:
                        self._imgs.append(img)
                elif key == "TrangThai":
                    fg, fill = (GREEN_FG, GREEN_BG) if r["TrangThai"] == ACTIVE else (ORANGE_FG, ORANGE_BG)
                    self._badge_center(r["TrangThai"], fg, fill, x, cw, cy)
                elif key == "ThaoTac":
                    bw, gap = 34, 8
                    x0 = x + (cw - 2 * bw - gap) / 2
                    for name, ic, fg_c, bg_c in (("edit", "edit", PRIMARY, "#E3EEFF"),
                                                 ("delete", "trash", "#D43B3B", "#FDE8E8")):
                        rounded_rect(b, x0, cy - 17, x0 + bw, cy + 17, 8, fill=bg_c, outline=bg_c)
                        draw_icon(b, ic, x0 + bw / 2, cy, fg_c)
                        hits[name] = (x0, cy - 17, x0 + bw, cy + 17)
                        x0 += bw + gap
                elif key == "STT":
                    b.create_text(x + cw / 2, cy, text=str(r["STT"]), font=self.f_norm, fill=TEXT)
                elif key in ("Phong", "SDT") and not r[key]:
                    b.create_text(mx, cy, text="—", anchor="w", font=self.f_norm, fill=MUTED)
                else:
                    font = self.f_bold if key == "HoTen" else self.f_norm
                    b.create_text(mx, cy, text=self._fit(r.get(key), maxw, font), anchor="w", font=font, fill=TEXT)
            self._hits.append(hits)
            b.create_line(0, y + self.ROW_H - 1, w, y + self.ROW_H - 1, fill=LINE)
        b.configure(scrollregion=(0, 0, w, len(self.rows) * self.ROW_H))

    # ---- chuột
    def _click(self, e):
        cx, cy = self.body.canvasx(e.x), self.body.canvasy(e.y)
        i = int(cy // self.ROW_H)
        if not 0 <= i < len(self.rows):
            return
        ma = self.rows[i]["MaNV"]
        for name, (x1, y1, x2, y2) in self._hits[i].items():
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                return self.h[name](ma)
        if cx < self.RADIO_W:
            self.h["toggle"](ma)

    def _double(self, e):
        i = int(self.body.canvasy(e.y) // self.ROW_H)
        if 0 <= i < len(self.rows) and self.body.canvasx(e.x) >= self.RADIO_W:
            self.h["edit"](self.rows[i]["MaNV"])

    def _head_click(self, e):
        if e.x < self.RADIO_W:
            self.h["toggle_all"]()


# ====================================================================== hộp thoại thêm / sửa
class _Entry(tk.Frame):
    """Ô nhập có viền xanh khi được chọn + chữ gợi ý mờ."""

    def __init__(self, master, placeholder="", value="", show=None):
        super().__init__(master, bg=INPUT_BORDER)
        self.var = tk.StringVar(master=self, value=value)
        inner = tk.Frame(self, bg="white")
        inner.pack(fill="x", padx=1, pady=1)
        self.entry = tk.Entry(inner, textvariable=self.var, bd=0, relief="flat", font=(FONT, 11), bg="white", fg=TEXT,
                              insertbackground=TEXT, highlightthickness=0, show=show or "")
        self.entry.pack(fill="x", padx=12, pady=8)
        self.hint = tk.Label(inner, text=placeholder, bg="white", fg=PLACEHOLDER, font=(FONT, 11), anchor="w")
        self.hint.bind("<Button-1>", lambda _e: self.entry.focus_set())
        self.var.trace_add("write", lambda *_: self._sync())
        self.entry.bind("<FocusIn>", lambda _e: self.config(bg=PRIMARY))
        self.entry.bind("<FocusOut>", lambda _e: self.config(bg=INPUT_BORDER))
        self._sync()

    def _sync(self):
        try:
            if self.var.get():
                self.hint.place_forget()
            else:
                self.hint.place(in_=self.entry, x=0, rely=0.5, anchor="w")
        except tk.TclError:
            pass

    def get(self):
        return self.var.get().strip()

    def focus_set(self):
        self.entry.focus_set()


class _RoomChip(tk.Canvas):
    """Nút chọn phòng phụ trách (bấm để bật/tắt)."""

    def __init__(self, master, text, on, hint=""):
        self.font = tkfont.Font(family=FONT, size=10, weight="bold")
        self.text = text                                       # tên phòng (không kèm gợi ý)
        self.label = text + (f"  · {hint}" if hint else "")
        self.w = self.font.measure(self.label) + 28
        super().__init__(master, width=self.w, height=36, bg="white", highlightthickness=0, cursor="hand2")
        self.on = on
        self.bind("<Button-1>", lambda _e: self.toggle())
        self._draw()

    def toggle(self):
        self.on = not self.on
        self._draw()

    def _draw(self):
        self.delete("all")
        rounded_rect(self, 1, 1, self.w - 1, 35, 17, fill=SEL_BG if self.on else "white",
                     outline=PRIMARY if self.on else BORDER)
        self.create_text(self.w / 2, 18, text=self.label, font=self.font, fill=NAVY if self.on else "#51607F")


def staff_dialog(parent, title, values, rooms, check):
    """Hộp thoại Thêm/Sửa nhân viên. values: dict giá trị ban đầu (rỗng = thêm mới).
    rooms: [(MaPhong, TenPhong, gợi ý tên NV khác đang phụ trách)]; values['Phongs'] = các MaPhong đang phụ trách.
    check(dữ liệu) -> None | (khóa ô, thông báo). Lỗi hiện ngay trong hộp thoại, không mất dữ liệu đã nhập."""
    editing = bool(values.get("MaNV"))
    top = parent.winfo_toplevel()
    win = tk.Toplevel(top, bg="white")
    win.title(title)
    win.transient(top)
    win.resizable(False, False)
    st = {"anh": None}                     # đường dẫn ảnh mới được chọn
    W = {}

    head = tk.Frame(win, bg="white")
    head.pack(fill="x", padx=28, pady=(22, 16))
    ic = tk.Canvas(head, width=30, height=30, bg="white", highlightthickness=0)
    ic.create_oval(8, 3, 18, 13, fill=PRIMARY, outline="")
    ic.create_arc(2, 15, 24, 38, start=0, extent=180, fill=PRIMARY, outline="")
    ic.pack(side="left")
    tk.Label(head, text=title, bg="white", fg=NAVY, font=(FONT, 15, "bold")).pack(side="left", padx=(8, 0))
    box = tk.Frame(head, bg=INPUT_BORDER, padx=1, pady=1)
    box.pack(side="right")
    FlatButton(box, "×", win.destroy, bg="white", hover="#EEF4FF", fg=NAVY, font=(FONT, 16), padx=14, pady=3).pack()
    tk.Frame(win, bg=LINE, height=1).pack(fill="x")

    body = tk.Frame(win, bg="white")
    body.pack(fill="x", padx=28, pady=(18, 0))
    left = tk.Frame(body, bg="white")
    left.pack(side="left", anchor="n", padx=(0, 22))
    av = tk.Canvas(left, width=128, height=128, bg="white", highlightthickness=0)
    av.pack()
    keep = []

    def paint_avatar():
        av.delete("all")
        keep[:] = [draw_avatar(av, 64, 64, 120, st["anh"] or values.get("AnhPath"), "white")]

    def pick_image():
        p = filedialog.askopenfilename(parent=win, title="Chọn ảnh đại diện",
                                       filetypes=[("Ảnh", "*.png *.gif *.jpg *.jpeg"), ("Tất cả", "*.*")])
        if not p:
            return
        if load_avatar(p, 120) is None:
            msg.config(text="⚠ Không đọc được ảnh này. Hãy chọn ảnh PNG hoặc GIF "
                            "(JPG chỉ dùng được khi máy đã cài Pillow).")
            return
        st["anh"] = p
        msg.config(text="")
        paint_avatar()

    FlatButton(left, "Chọn ảnh", pick_image, bg="white", hover="#EEF4FF", fg=NAVY, font=(FONT, 10, "bold"),
               padx=18, pady=9, highlightthickness=1, highlightbackground=INPUT_BORDER).pack(pady=(10, 0), fill="x")

    right = tk.Frame(body, bg="white")
    right.pack(side="left", fill="x", expand=True)

    def label(parent_, text, req=False):
        tk.Label(parent_, text=text + (" *" if req else ""), bg="white", fg=TEXT, font=(FONT, 10, "bold"),
                 anchor="w").pack(fill="x", pady=(0, 5))

    def entry(parent_, key, text, ph, req=False, show=None):
        label(parent_, text, req)
        W[key] = _Entry(parent_, ph, str(values.get(key) or ""), show)
        W[key].pack(fill="x", pady=(0, 12))

    def combo(parent_, key, text, opts, req=False):
        label(parent_, text, req)
        c = ttk.Combobox(parent_, values=opts, state="readonly", font=(FONT, 11))
        c.set(values.get(key) if values.get(key) in opts else opts[0])
        c.pack(fill="x", ipady=6, pady=(0, 12))
        W[key] = c

    entry(right, "HoTen", "Tên nhân viên", "Nguyễn Thị Mai", True)
    combo(right, "ChucVu", "Chức vụ", db.CHUC_VU, True)
    entry(right, "SDT", "Số điện thoại", "09xxxxxxxx", True)
    entry(right, "Email", "Email", "ten@kytucxa.vn", True)
    combo(right, "TrangThai", "Trạng thái", [ACTIVE, LOCKED])

    # phòng phụ trách
    sec = tk.Frame(win, bg="white")
    sec.pack(fill="x", padx=28)
    label(sec, "Phòng phụ trách (bấm để chọn nhiều phòng)")
    wrap = tk.Frame(sec, bg="white")
    wrap.pack(fill="x", pady=(0, 6))
    chips = {}
    mine = set(values.get("Phongs") or [])
    if not rooms:
        tk.Label(wrap, text="Chưa có phòng nào. Hãy thêm phòng ở trang Phòng.", bg="white", fg=MUTED,
                 font=(FONT, 10)).pack(anchor="w")
    for i, (ma, ten, other) in enumerate(rooms):
        c = _RoomChip(wrap, ten, ma in mine, "" if ma in mine else other)
        c.grid(row=i // 6, column=i % 6, padx=(0, 8), pady=(0, 8), sticky="w")
        chips[ma] = c
    tk.Label(sec, text="Phòng có ghi tên người khác sẽ được chuyển sang nhân viên này nếu bạn chọn.", bg="white",
             fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(0, 10))

    # tài khoản đăng nhập
    tk.Frame(win, bg=LINE, height=1).pack(fill="x", padx=28)
    acc = tk.Frame(win, bg="white")
    acc.pack(fill="x", padx=28, pady=(14, 0))
    acc.columnconfigure(0, weight=1, uniform="a")
    acc.columnconfigure(1, weight=1, uniform="a")
    c0, c1 = tk.Frame(acc, bg="white"), tk.Frame(acc, bg="white")
    c0.grid(row=0, column=0, sticky="ew", padx=(0, 10))
    c1.grid(row=0, column=1, sticky="ew", padx=(10, 0))
    entry(c0, "TenDangNhap", "Tên đăng nhập", "vd: mai", True)
    entry(c1, "MatKhau", "Mật khẩu" + (" (để trống = giữ nguyên)" if editing else ""),
          "Tối thiểu 6 ký tự", not editing, show="•")

    def auto_username(_e=None):            # chưa gõ tên đăng nhập thì gợi ý từ email
        if not W["TenDangNhap"].get() and "@" in W["Email"].get():
            W["TenDangNhap"].var.set(re.sub(r"[^A-Za-z0-9._]", "", W["Email"].get().split("@")[0]))
    W["Email"].entry.bind("<FocusOut>", auto_username, add="+")

    msg = tk.Label(win, text="", bg="white", fg=ERROR, font=(FONT, 10), anchor="w", justify="left", wraplength=640)
    msg.pack(fill="x", padx=28, pady=(0, 6))
    tk.Frame(win, bg=LINE, height=1).pack(fill="x")
    result = {}

    def save(_e=None):
        d = {k: (w.get().strip() if isinstance(w, _Entry) else w.get()) for k, w in W.items()}
        d["Phongs"] = [ma for ma, c in chips.items() if c.on]
        d["AnhSrc"] = st["anh"]
        d["MaNV"] = values.get("MaNV")
        err = check(d)
        if err:
            key, text = err
            msg.config(text="⚠ " + text)
            if isinstance(W.get(key), _Entry):
                W[key].focus_set()
            return
        result.update(d)
        win.destroy()

    foot = tk.Frame(win, bg="white")
    foot.pack(fill="x", padx=28, pady=16)
    FlatButton(foot, "Lưu", save, font=(FONT, 11, "bold"), padx=24, pady=10).pack(side="right")
    FlatButton(foot, "Hủy", win.destroy, bg="white", hover="#EEF4FF", fg=NAVY, font=(FONT, 11, "bold"), padx=20,
               pady=10, highlightthickness=1, highlightbackground=INPUT_BORDER).pack(side="right", padx=(0, 12))
    win.bind("<Escape>", lambda _e: win.destroy())
    win.bind("<Return>", save)
    paint_avatar()
    win.update_idletasks()
    x = top.winfo_rootx() + max((top.winfo_width() - win.winfo_reqwidth()) // 2, 0)
    y = top.winfo_rooty() + max((top.winfo_height() - win.winfo_reqheight()) // 3, 0)
    win.geometry(f"+{x}+{y}")
    win.after(60, W["HoTen"].focus_set)
    try:
        win.grab_set()
    except tk.TclError:
        pass
    win.wait_window()
    return result or None


# ====================================================================== dữ liệu
def load_staff():
    """Nhân viên + chuỗi phòng phụ trách (lấy từ Phong.MaNV, cùng nguồn với trang Phòng)."""
    rooms = {}
    for r in db.query("SELECT MaNV, MaPhong, TenPhong FROM Phong WHERE MaNV IS NOT NULL ORDER BY TenPhong"):
        rooms.setdefault(r["MaNV"], []).append((r["MaPhong"], r["TenPhong"]))
    out = []
    for r in db.query("SELECT * FROM NhanVien ORDER BY MaNV"):
        d = {k: ("" if v is None else v) for k, v in dict(r).items()}
        d["Phongs"] = [m for m, _t in rooms.get(d["MaNV"], [])]
        d["Phong"] = ", ".join(t for _m, t in rooms.get(d["MaNV"], []))
        d["TrangThai"] = d["TrangThai"] or ACTIVE
        d["AnhPath"] = os.path.join(os.path.dirname(AVATAR_DIR), d["Anh"]) if d["Anh"] else None
        d["_hay"] = fold(f"{d['HoTen']} {d['ChucVu']} {d['Email']} {d['SDT']} {d['Phong']} {d['TenDangNhap']}")
        out.append(d)
    return out


def room_choices():
    """[(MaPhong, TenPhong, tên ngắn của NV đang phụ trách)] cho hộp thoại."""
    return [(r["MaPhong"], r["TenPhong"], (r["NhanVienPT"] or "").split(" ")[-1]) for r in db.danh_sach_phong()]


def clean_staff(d):
    """Chuẩn hóa + kiểm tra định dạng. Trả về (dict sạch, None) hoặc (None, (khóa, thông báo))."""
    c = dict(d)
    c["HoTen"] = re.sub(r"\s+", " ", d["HoTen"]).strip()
    if not c["HoTen"]:
        return None, ("HoTen", "Tên nhân viên không được để trống.")
    phone = re.sub(r"[ .\-()]", "", d["SDT"])
    if re.fullmatch(r"[1-9]\d{8,9}", phone):
        phone = "0" + phone
    if not re.fullmatch(r"0\d{9,10}", phone):
        return None, ("SDT", "Số điện thoại phải gồm 10-11 chữ số và bắt đầu bằng 0.")
    c["SDT"] = phone
    c["Email"] = d["Email"].strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", c["Email"]):
        return None, ("Email", "Email không hợp lệ (ví dụ: ten@kytucxa.vn).")
    c["TenDangNhap"] = d["TenDangNhap"].strip()
    if not re.fullmatch(r"[A-Za-z0-9._]{3,30}", c["TenDangNhap"]):
        return None, ("TenDangNhap", "Tên đăng nhập gồm 3-30 ký tự chữ không dấu, số, dấu chấm hoặc gạch dưới.")
    if (not d.get("MaNV") and len(d["MatKhau"]) < 6) or (d["MatKhau"] and len(d["MatKhau"]) < 6):
        return None, ("MatKhau", "Mật khẩu tối thiểu 6 ký tự.")
    return c, None


# ====================================================================== màn hình
class NhanVienScreen(tk.Frame):
    HEADERS = ["STT", "Tên nhân viên", "Chức vụ", "Phòng phụ trách", "Số điện thoại", "Email", "Trạng thái"]

    def __init__(self, master, user=None):
        super().__init__(master, bg=PAGE_BG)
        self.user = user or {}
        self.rows, self.shown = [], []
        self.page, self.size = 1, 5
        self.kw = tk.StringVar(master=self)               # main.goto() / tìm kiếm ở Trang chủ điền sẵn qua biến này
        self._build()
        self.refresh()
        self.kw.trace_add("write", lambda *_: self._search_changed())

    # ---- dựng giao diện
    def _build(self):
        head = tk.Frame(self, bg=PAGE_BG)
        head.pack(fill="x", padx=40, pady=(30, 0))
        box = tk.Frame(head, bg=PAGE_BG)
        box.pack(side="left")
        tk.Label(box, text="Quản lý nhân viên", bg=PAGE_BG, fg=NAVY, font=(FONT, 20, "bold")).pack(anchor="w")
        tk.Label(box, text="Quản lý thông tin nhân viên và phân quyền hệ thống", bg=PAGE_BG, fg=MUTED,
                 font=(FONT, 10)).pack(anchor="w")
        IconButton(head, "Thêm nhân viên", "plus", self.on_add, "primary").pack(side="right", anchor="n", padx=(12, 0))
        SearchBox(head, self.kw, "Tìm theo tên, chức vụ, email, phòng...", width=330).pack(side="right", anchor="n")

        cards = tk.Frame(self, bg=PAGE_BG)
        cards.pack(fill="x", padx=40, pady=(18, 16))
        self.vals, self.pills = {}, {}
        for i, (kind, icon, title) in enumerate((("total", "people", "Tổng nhân viên"), ("mgr", "case", "Quản lý"),
                                                 ("staff", "gear", "Nhân viên"), ("active", "mail", "Đang hoạt động"))):
            cards.columnconfigure(i, weight=1, uniform="c")
            c = Card(cards)
            c.grid(row=0, column=i, sticky="ew", padx=(0, 0 if i == 3 else 14))
            c.config(height=108)
            cv = tk.Canvas(c.inner, width=72, height=72, bg="white", highlightthickness=0)
            cv.place(x=18, y=18)
            stat_icon(cv, icon)
            tk.Label(c.inner, text=title, bg="white", fg="#33466A", font=(FONT, 10, "bold")).place(x=102, y=20)
            self.vals[kind] = tk.Label(c.inner, text="0", bg="white", fg=NAVY, font=(FONT, 24, "bold"))
            self.vals[kind].place(x=100, y=42)
            self.pills[kind] = Pill(c.inner, "↑ +0")
            self.pills[kind].place(relx=1.0, rely=1.0, x=-16, y=-14, anchor="se")

        card = Card(self)
        card.pack(fill="both", expand=True, padx=40, pady=(0, 30))
        inner = card.inner
        tools = tk.Frame(inner, bg="white")
        tools.pack(fill="x", padx=22, pady=(16, 12))
        tk.Label(tools, text="Hiển thị", bg="white", fg=TEXT, font=(FONT, 10)).pack(side="left")
        self.size_var = tk.StringVar(master=self, value=str(self.size))
        cb = ttk.Combobox(tools, textvariable=self.size_var, values=PAGE_SIZES, width=4, state="readonly",
                          font=(FONT, 10))
        cb.pack(side="left", padx=8)
        cb.bind("<<ComboboxSelected>>", lambda _e: self._size_changed())
        tk.Label(tools, text="bản ghi", bg="white", fg=TEXT, font=(FONT, 10)).pack(side="left")
        self.btn_bulk = IconButton(tools, "Xóa đã chọn", "trash", self.on_delete_checked, "danger")
        IconButton(tools, "Xuất PDF", "pdf", self.on_export_pdf, "outline").pack(side="right")
        IconButton(tools, "Xuất Excel", "sheet", self.on_export_excel, "outline").pack(side="right", padx=(0, 10))

        foot = tk.Frame(inner, bg="white")
        foot.pack(side="bottom", fill="x")
        tk.Frame(foot, bg=LINE, height=1).pack(fill="x")
        row = tk.Frame(foot, bg="white")
        row.pack(fill="x", padx=22, pady=12)
        self.foot_l = tk.Label(row, bg="white", fg=TEXT, font=(FONT, 10))
        self.foot_l.pack(side="left")
        self.pager = tk.Frame(row, bg="white")
        self.pager.pack(side="right")

        self.table = StaffTable(inner, {"toggle": self._toggle, "toggle_all": self._toggle_all,
                                        "edit": self.on_edit, "delete": self.on_delete})
        self.table.pack(fill="both", expand=True)

    # ---- dữ liệu / bộ lọc / phân trang
    def refresh(self):
        self.rows = load_staff()
        self.table.checked &= {r["MaNV"] for r in self.rows}
        limit = (date.today() - timedelta(days=30)).isoformat()
        groups = {"total": self.rows, "mgr": [r for r in self.rows if r["ChucVu"] == "Quản lý"],
                  "staff": [r for r in self.rows if r["ChucVu"] != "Quản lý"],
                  "active": [r for r in self.rows if r["TrangThai"] == ACTIVE]}
        for k, rs in groups.items():
            self.vals[k].config(text=str(len(rs)))
            self.pills[k].set(f"↑ +{sum(1 for r in rs if (r['NgayTao'] or '2000-01-01')[:10] >= limit)}")
        self.apply()

    def _search_changed(self):
        self.page = 1
        self.apply()

    def _size_changed(self):
        self.size, self.page = int(self.size_var.get()), 1
        self.apply()

    def apply(self):
        kw = fold(self.kw.get().strip())
        self.shown = [r for r in self.rows if not kw or kw in r["_hay"]]
        total = len(self.shown)
        pages = max(1, math.ceil(total / self.size))
        self.page = min(max(self.page, 1), pages)
        start = (self.page - 1) * self.size
        chunk = [dict(r, STT=start + i + 1) for i, r in enumerate(self.shown[start:start + self.size])]
        self.table.load(chunk)
        self.foot_l.config(text=(f"Hiển thị {start + 1} - {start + len(chunk)} / {total} nhân viên" if total
                                 else "Không có nhân viên nào"))
        for w in self.pager.winfo_children():
            w.destroy()
        PageBtn(self.pager, "prev", lambda: self.goto_page(self.page - 1), enabled=self.page > 1).pack(
            side="left", padx=3)
        for p in range(1, pages + 1):
            PageBtn(self.pager, str(p), lambda p=p: self.goto_page(p), active=p == self.page).pack(side="left", padx=3)
        PageBtn(self.pager, "next", lambda: self.goto_page(self.page + 1), enabled=self.page < pages).pack(
            side="left", padx=3)
        self._sync_bulk()

    def goto_page(self, p):
        self.page = p
        self.apply()

    # ---- chọn nhiều dòng
    def _toggle(self, ma):
        self.table.checked ^= {ma}
        self.table._draw()
        self._sync_bulk()

    def _toggle_all(self):
        ids = {r["MaNV"] for r in self.table.rows}
        self.table.checked = (self.table.checked - ids) if ids <= self.table.checked else (self.table.checked | ids)
        self.table._draw()
        self._sync_bulk()

    def _sync_bulk(self):
        n = len(self.table.checked)
        if n:
            self.btn_bulk.text = f"Xóa đã chọn ({n})"
            self.btn_bulk.config(width=self.btn_bulk.font.measure(self.btn_bulk.text) + 62)
            self.btn_bulk._draw()
            self.btn_bulk.pack(side="left", padx=(18, 0))
        else:
            self.btn_bulk.pack_forget()

    def _find(self, ma):
        return next((r for r in self.rows if r["MaNV"] == ma), None)

    # ---- thêm / sửa
    def _check(self, d):
        """Kiểm tra toàn bộ (định dạng + trùng + quyền). Trả về None hoặc (khóa ô, thông báo)."""
        clean, err = clean_staff(d)
        if err:
            return err
        ma = d.get("MaNV") or 0
        d.update(clean)
        if db.query("SELECT 1 FROM NhanVien WHERE LOWER(Email)=? AND MaNV<>?", (d["Email"], ma), one=True):
            return "Email", "Email này đã được dùng cho nhân viên khác."
        if db.query("SELECT 1 FROM NhanVien WHERE LOWER(TenDangNhap)=LOWER(?) AND MaNV<>?", (d["TenDangNhap"], ma),
                    one=True):
            return "TenDangNhap", f"Tên đăng nhập '{d['TenDangNhap']}' đã tồn tại."
        if ma and ma == self.user.get("MaNV"):
            if d["ChucVu"] != "Quản lý":
                return "HoTen", "Bạn không thể tự hạ chức vụ của chính mình (sẽ mất quyền vào trang này)."
            if d["TrangThai"] == LOCKED:
                return "HoTen", "Bạn không thể tự khóa tài khoản đang đăng nhập."
        return None

    @staticmethod
    def _save_avatar(ma, src):
        if not src:
            return
        os.makedirs(AVATAR_DIR, exist_ok=True)
        ext = os.path.splitext(src)[1].lower() or ".png"
        for old in os.listdir(AVATAR_DIR):
            if old.startswith(f"nv_{ma}."):
                os.remove(os.path.join(AVATAR_DIR, old))
        shutil.copyfile(src, os.path.join(AVATAR_DIR, f"nv_{ma}{ext}"))
        db.execute("UPDATE NhanVien SET Anh=? WHERE MaNV=?", (f"avatars/nv_{ma}{ext}", ma))

    @staticmethod
    def _assign_rooms(ma, phongs):
        """Phòng được chọn -> do `ma` phụ trách; phòng bỏ chọn (trước đó của ma) -> chưa phân công."""
        conn = db.get_conn()
        try:
            with conn:
                conn.execute("UPDATE Phong SET MaNV=NULL WHERE MaNV=?", (ma,))
                for p in phongs:
                    conn.execute("UPDATE Phong SET MaNV=? WHERE MaPhong=?", (ma, p))
        finally:
            conn.close()

    def on_add(self):
        d = staff_dialog(self, "Thêm nhân viên", {"ChucVu": "Nhân viên", "TrangThai": ACTIVE}, room_choices(),
                         self._check)
        if not d:
            return
        ma = db.execute("INSERT INTO NhanVien(TenDangNhap,MatKhau,HoTen,VaiTro,ChucVu,SDT,Email,TrangThai,NgayTao) "
                        "VALUES(?,?,?,?,?,?,?,?,?)",
                        (d["TenDangNhap"], db.hash_pw(d["MatKhau"]), d["HoTen"], db.vai_tro_cua(d["ChucVu"]),
                         d["ChucVu"], d["SDT"], d["Email"], d["TrangThai"], date.today().isoformat()))
        self._save_avatar(ma, d["AnhSrc"])
        self._assign_rooms(ma, d["Phongs"])
        db.ghi_nhat_ky("nv", f"Thêm nhân viên **{d['HoTen']}** ({d['ChucVu']})")
        self.kw.set("")
        self.refresh()
        idx = next((i for i, r in enumerate(self.rows) if r["MaNV"] == ma), 0)
        self.goto_page(idx // self.size + 1)

    def on_edit(self, ma):
        r = self._find(ma)
        if not r:
            return
        d = staff_dialog(self, "Cập nhật nhân viên", dict(r, MatKhau=""), room_choices(), self._check)
        if not d:
            return
        sql = ("UPDATE NhanVien SET TenDangNhap=?,HoTen=?,VaiTro=?,ChucVu=?,SDT=?,Email=?,TrangThai=?"
               + (",MatKhau=?" if d["MatKhau"] else "") + " WHERE MaNV=?")
        args = [d["TenDangNhap"], d["HoTen"], db.vai_tro_cua(d["ChucVu"]), d["ChucVu"], d["SDT"], d["Email"],
                d["TrangThai"]] + ([db.hash_pw(d["MatKhau"])] if d["MatKhau"] else []) + [ma]
        db.execute(sql, tuple(args))
        self._save_avatar(ma, d["AnhSrc"])
        self._assign_rooms(ma, d["Phongs"])
        if ma == self.user.get("MaNV"):
            self.user.update(HoTen=d["HoTen"], Email=d["Email"], SDT=d["SDT"], ChucVu=d["ChucVu"])
        db.ghi_nhat_ky("nv", f"Cập nhật nhân viên **{d['HoTen']}**")
        self.refresh()

    # ---- xóa
    def _delete_many(self, ids):
        names = []
        conn = db.get_conn()
        try:
            with conn:
                for ma in ids:
                    row = conn.execute("SELECT HoTen FROM NhanVien WHERE MaNV=?", (ma,)).fetchone()
                    if not row:
                        continue
                    conn.execute("UPDATE Phong SET MaNV=NULL WHERE MaNV=?", (ma,))   # phòng trở về "chưa phân công"
                    conn.execute("DELETE FROM NhanVien WHERE MaNV=?", (ma,))
                    names.append(row[0])
        except sqlite3.IntegrityError:
            return error("Không thể xóa vì nhân viên này đang được dùng ở mục khác.")
        finally:
            conn.close()
        if os.path.isdir(AVATAR_DIR):
            for f in os.listdir(AVATAR_DIR):
                if any(f.startswith(f"nv_{ma}.") for ma in ids):
                    os.remove(os.path.join(AVATAR_DIR, f))
        if names:
            db.ghi_nhat_ky("nv", "Xóa nhân viên **" + "**, **".join(names) + "**")
        self.table.checked -= set(ids)
        self.refresh()

    def on_delete(self, ma):
        r = self._find(ma)
        if not r:
            return
        if ma == self.user.get("MaNV"):
            return error("Không thể xóa tài khoản đang đăng nhập.")
        extra = f"\nPhòng đang phụ trách ({r['Phong']}) sẽ trở về trạng thái chưa phân công." if r["Phong"] else ""
        if messagebox.askyesno("Xác nhận", f"Bạn có chắc chắn muốn xóa nhân viên {r['HoTen']}?{extra}"):
            self._delete_many([ma])

    def on_delete_checked(self):
        ids = sorted(self.table.checked)
        if self.user.get("MaNV") in ids:
            return error("Trong danh sách chọn có tài khoản đang đăng nhập; hãy bỏ chọn tài khoản đó.")
        if ids and messagebox.askyesno("Xác nhận", f"Xóa {len(ids)} nhân viên đã chọn?"):
            self._delete_many(ids)

    # ---- xuất file
    def _export_rows(self):
        return [[i, r["HoTen"], r["ChucVu"], r["Phong"], r["SDT"], r["Email"], r["TrangThai"]]
                for i, r in enumerate(self.shown, start=1)]

    def on_export_excel(self):
        if not self.shown:
            return messagebox.showinfo("Thông báo", "Không có dữ liệu để xuất.")
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".xlsx",
                                            initialfile=f"nhan_vien_{date.today():%Y%m%d}.xlsx",
                                            filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        try:
            xlsx_io.write_xlsx(path, self.HEADERS, self._export_rows(), widths=[6, 26, 14, 22, 16, 28, 16],
                               sheet_name="Nhân viên")
        except OSError as e:
            return error(f"Không ghi được file: {e}")
        messagebox.showinfo("Thành công", f"Đã xuất {len(self.shown)} nhân viên ra file:\n{path}")

    def on_export_pdf(self):
        """Tạo trang báo cáo HTML rồi mở bằng trình duyệt: hộp thoại in hiện ra, chọn 'Lưu thành PDF'."""
        if not self.shown:
            return messagebox.showinfo("Thông báo", "Không có dữ liệu để xuất.")
        th = "".join(f"<th>{html.escape(h)}</th>" for h in self.HEADERS)
        tr = "".join("<tr>" + "".join(f"<td>{html.escape(str(v) if v != '' else '—')}</td>" for v in row) + "</tr>"
                     for row in self._export_rows())
        page = (f"<!doctype html><html lang='vi'><meta charset='utf-8'><title>Danh sách nhân viên</title>"
                f"<style>body{{font-family:'Segoe UI',Arial,sans-serif;margin:32px;color:#14213D}}"
                f"h1{{color:#0B3D91;margin:0}}p{{color:#51607F}}table{{border-collapse:collapse;width:100%;margin-top:18px}}"
                f"th{{background:#F3F7FD;text-align:left}}th,td{{border:1px solid #DCE6F7;padding:8px 10px;font-size:13px}}"
                f"</style><h1>Danh sách nhân viên ký túc xá</h1><p>Ngày xuất: {datetime.now():%d/%m/%Y %H:%M} · "
                f"{len(self.shown)} nhân viên</p><table><tr>{th}</tr>{tr}</table>"
                f"<script>window.onload=function(){{window.print()}}</script></html>")
        path = os.path.join(tempfile.gettempdir(), f"nhan_vien_{date.today():%Y%m%d}.html")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(page)
        except OSError as e:
            return error(f"Không tạo được file: {e}")
        if not webbrowser.open("file://" + path.replace("\\", "/")):
            messagebox.showinfo("Xuất PDF", f"Hãy mở file này bằng trình duyệt rồi chọn In → Lưu thành PDF:\n{path}")

