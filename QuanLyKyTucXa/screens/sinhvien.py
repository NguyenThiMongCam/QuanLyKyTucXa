"""Trang Sinh viên (quản trị) - giao diện xanh trắng theo mẫu thiết kế.

File này cũng chứa các thành phần giao diện dùng chung mà trang Phòng (phong.py) import:
    GREEN_FG, LINE, Card, Chip, DataTable, IconButton, SearchBox, fold

- Danh sách sinh viên + phòng đang ở (huy hiệu xanh), tìm kiếm tức thì (không dấu cũng tìm được)
- Lọc nhanh: Tất cả / Đang ở KTX / Chưa xếp phòng
- Thêm / Sửa / Xóa (kiểm tra dữ liệu, nhập sai thì giữ lại nội dung để sửa)
- Nhập / Xuất Excel (.xlsx, chỉ dùng thư viện chuẩn) và CSV
"""
import csv
import re
import sqlite3
import tkinter as tk
import unicodedata
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import database as db
from screens import xlsx_io
from screens.base import error, form_dialog, parse_date
from screens.login import (BORDER, FONT, INPUT_BORDER, MUTED, NAVY, PAGE_BG, PLACEHOLDER, PRIMARY, SEL_BG, TEXT,
                           rounded_rect)

GREEN_FG, GREEN_BG = "#0E7A3B", "#E4F6EA"
LINE, HEAD_BG = "#E6ECF7", "#F3F7FD"
DANGER = "#C0392B"


def fold(text):
    """Bỏ dấu + chữ thường để tìm kiếm: 'Nguyễn Đức' -> 'nguyen duc'."""
    s = unicodedata.normalize("NFD", str(text or "").lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _bg_of(widget):
    try:
        return widget.cget("bg")
    except tk.TclError:
        return PAGE_BG


# ====================================================================== thành phần giao diện dùng chung
class Card(tk.Frame):
    """Khung trắng viền mảnh. Đặt nội dung vào `card.inner`. Có thể ép chiều cao bằng card.config(height=...)."""

    def __init__(self, master):
        super().__init__(master, bg=BORDER)
        self.pack_propagate(False)
        self.inner = tk.Frame(self, bg="white")
        self.inner.pack(fill="both", expand=True, padx=1, pady=1)


class Chip(tk.Canvas):
    """Nút lọc dạng viên thuốc. chip.set(văn bản, đang chọn)."""
    H = 40

    def __init__(self, master, command):
        super().__init__(master, height=self.H, width=80, bg=_bg_of(master), highlightthickness=0, cursor="hand2")
        self.command, self.text, self.active = command, "", False
        self.font = tkfont.Font(family=FONT, size=10, weight="bold")
        self.bind("<Button-1>", lambda _e: self.command())

    def set(self, text, active=False):
        self.text, self.active = text, bool(active)
        self.config(width=self.font.measure(text) + 36)
        self._draw()

    def _draw(self):
        self.delete("all")
        w = int(self.cget("width"))
        on = self.active
        rounded_rect(self, 1, 1, w - 1, self.H - 1, 19, fill=SEL_BG if on else "white",
                     outline=PRIMARY if on else BORDER)
        self.create_text(w / 2, self.H / 2, text=self.text, font=self.font, fill=NAVY if on else "#33466A")


def draw_icon(cv, name, cx, cy, color):
    kw = dict(fill=color, width=2, capstyle="round", joinstyle="round")
    if name == "plus":
        cv.create_line(cx - 7, cy, cx + 7, cy, **kw)
        cv.create_line(cx, cy - 7, cx, cy + 7, **kw)
    elif name == "edit":
        cv.create_line(cx - 6, cy + 6, cx + 5, cy - 5, **dict(kw, width=3))
        cv.create_line(cx - 8, cy + 8, cx - 3, cy + 8, **kw)
    elif name == "trash":
        cv.create_line(cx - 8, cy - 4, cx + 8, cy - 4, **kw)
        cv.create_line(cx - 3, cy - 7, cx + 3, cy - 7, **kw)
        cv.create_line(cx - 5, cy - 2, cx - 4, cy + 8, cx + 4, cy + 8, cx + 5, cy - 2, **kw)
    elif name == "list":
        for dy in (-5, 0, 5):
            cv.create_line(cx - 7, cy + dy, cx + 7, cy + dy, **kw)
    elif name in ("down", "up"):                       # mũi tên + khay
        d = 1 if name == "down" else -1
        cv.create_line(cx, cy - 7 * d, cx, cy + 3 * d, **kw)
        cv.create_line(cx - 4, cy - 1 * d, cx, cy + 3 * d, cx + 4, cy - 1 * d, **kw)
        cv.create_line(cx - 7, cy + 8 * d, cx + 7, cy + 8 * d, **kw)


class IconButton(tk.Canvas):
    """Nút có biểu tượng vẽ sẵn. style: primary | outline | danger. set_enabled(False) để làm mờ."""
    H = 44
    # bg, bg khi rê chuột, chữ, viền, chữ khi vô hiệu
    STYLES = {"primary": (PRIMARY, NAVY, "white", PRIMARY, "#9DB8E8"),
              "outline": ("white", "#EEF4FF", NAVY, INPUT_BORDER, "#9AA8C0"),
              "danger": ("white", "#FDECEC", DANGER, "#F0CFCB", "#E4A9A3")}

    def __init__(self, master, text, icon, command, style="outline", enabled=True):
        self.font = tkfont.Font(family=FONT, size=10, weight="bold")
        super().__init__(master, height=self.H, width=self.font.measure(text) + 62, bg=_bg_of(master),
                         highlightthickness=0)
        self.text, self.icon, self.command, self.style = text, icon, command, style
        self.enabled, self.hover = enabled, False
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Button-1>", self._click)
        self._draw()

    def set_enabled(self, flag):
        self.enabled = bool(flag)
        self._draw()

    def _set_hover(self, flag):
        self.hover = flag
        self._draw()

    def _click(self, _e=None):
        if self.enabled:
            self.command()

    def _draw(self):
        bg, hover, fg, border, dis = self.STYLES[self.style]
        self.delete("all")
        self.config(cursor="hand2" if self.enabled else "arrow")
        w = int(self.cget("width"))
        if not self.enabled:
            fill, line, color = ("#EEF2F9" if self.style == "primary" else "white"), BORDER, dis
            if self.style == "primary":
                fill, line = "#BFD3F5", "#BFD3F5"
                color = "white"
        else:
            fill, line, color = (hover if self.hover else bg), border, fg
        rounded_rect(self, 1, 1, w - 1, self.H - 1, 10, fill=fill, outline=line)
        draw_icon(self, self.icon, 28, self.H / 2, color)
        self.create_text(46, self.H / 2, text=self.text, anchor="w", font=self.font, fill=color)


class SearchBox(tk.Frame):
    """Ô tìm kiếm có biểu tượng kính lúp và chữ gợi ý. Gắn với tk.StringVar `var` (ghi đè var.set() vẫn hiển thị đúng)."""

    def __init__(self, master, var, placeholder, width=340):
        super().__init__(master, bg=INPUT_BORDER, width=width, height=46)
        self.pack_propagate(False)
        inner = tk.Frame(self, bg="white")
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        icon = tk.Canvas(inner, width=40, height=44, bg="white", highlightthickness=0)
        icon.create_oval(14, 14, 25, 25, outline=PLACEHOLDER, width=2)
        icon.create_line(24, 24, 30, 30, fill=PLACEHOLDER, width=2, capstyle="round")
        icon.pack(side="left")
        self.var = var
        self.entry = tk.Entry(inner, textvariable=var, bd=0, relief="flat", font=(FONT, 11), bg="white", fg=TEXT,
                              insertbackground=TEXT, highlightthickness=0)
        self.entry.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=10)
        self.hint = tk.Label(inner, text=placeholder, bg="white", fg=PLACEHOLDER, font=(FONT, 10), anchor="w")
        self.hint.place(in_=self.entry, x=0, rely=0.5, anchor="w")
        self.hint.bind("<Button-1>", lambda _e: self.entry.focus_set())
        var.trace_add("write", lambda *_: self._sync())
        self._sync()

    def _sync(self):
        try:
            if self.var.get():
                self.hint.place_forget()
            else:
                self.hint.place(in_=self.entry, x=0, rely=0.5, anchor="w")
        except tk.TclError:                              # widget đã bị hủy khi chuyển trang
            pass


class DataTable(tk.Frame):
    """Bảng vẽ bằng Canvas: cột radio chọn dòng, tiêu đề cố định, cuộn dọc, bấm đôi để mở.

    columns: [(khóa, tiêu đề, rộng tối thiểu, tỉ lệ giãn)]; key: tên cột khóa chính (vd. "MaPhong").
    Lớp con có thể ghi đè _draw_cell(key, row, x, cy, maxw, tag) -> True nếu tự vẽ ô đó.
    """
    HEAD_H, ROW_H, RADIO_W = 46, 47, 52
    bold_keys = ()
    navy_keys = ()

    def __init__(self, master, on_select, on_open, columns, key):
        super().__init__(master, bg="white")
        self.on_select, self.on_open, self.columns, self.key = on_select, on_open, columns, key
        self.rows, self.selected = [], None
        self.f_norm = tkfont.Font(family=FONT, size=10)
        self.f_bold = tkfont.Font(family=FONT, size=10, weight="bold")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.head = tk.Canvas(self, height=self.HEAD_H, bg=HEAD_BG, highlightthickness=0)
        self.head.grid(row=0, column=0, sticky="ew")
        self.body = tk.Canvas(self, bg="white", highlightthickness=0, yscrollincrement=24, cursor="hand2")
        self.body.grid(row=1, column=0, sticky="nsew")
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.body.yview)
        self.body.configure(yscrollcommand=self._on_scroll)
        self.body.bind("<Configure>", lambda _e: self._draw())
        self.body.bind("<Button-1>", self._click)
        self.body.bind("<Double-1>", self._double)
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.body.bind(ev, self._wheel)

    # ---- dữ liệu
    def load(self, rows):
        self.rows = list(rows)
        if self.selected is not None and all(r[self.key] != self.selected for r in self.rows):
            self.selected = None
            self.on_select(None)
        self._draw()

    def select(self, ident, scroll=False):
        old, self.selected = self.selected, ident
        self._draw()
        if scroll and ident is not None:
            idx = next((i for i, r in enumerate(self.rows) if r[self.key] == ident), None)
            total = max(len(self.rows) * self.ROW_H, 1)
            if idx is not None and total > self.body.winfo_height() > 1:
                top, h = self.body.canvasy(0), self.body.winfo_height()
                y1 = idx * self.ROW_H
                if y1 < top or y1 + self.ROW_H > top + h:
                    self.body.yview_moveto(max(0.0, min(y1 - self.ROW_H, total - h) / total))
        if old != ident:
            self.on_select(ident)

    # ---- vẽ
    def _layout(self, width):
        avail = max(width - self.RADIO_W, 1)
        mins = sum(c[2] for c in self.columns)
        extra = max(0, avail - mins)
        wsum = sum(c[3] for c in self.columns) or 1
        out, x = [], self.RADIO_W
        for key, _head, mn, wt in self.columns:
            w = mn + extra * wt / wsum
            out.append((key, x, w))
            x += w
        return out

    def _fit(self, text, maxw, font):
        text = "" if text is None else str(text)
        if font.measure(text) <= maxw:
            return text
        while text and font.measure(text + "…") > maxw:
            text = text[:-1]
        return text + "…" if text else ""

    def _badge(self, text, fg, fill, tx, cy, maxw, tag):
        text = self._fit(text, max(maxw - 24, 10), self.f_bold)
        bw = min(maxw, self.f_bold.measure(text) + 24)
        rounded_rect(self.body, tx, cy - 11, tx + bw, cy + 11, 11, fill=fill, outline=fill, tags=tag)
        self.body.create_text(tx + bw / 2, cy, text=text, font=self.f_bold, fill=fg, tags=tag)

    def _draw_cell(self, key, r, tx, cy, maxw, tag):
        return False

    def _draw(self):
        b, h = self.body, self.head
        b.delete("all")
        h.delete("all")
        w = max(b.winfo_width(), 1)
        cols = self._layout(w)
        for (key, x, cw), col in zip(cols, self.columns):
            h.create_text(x + 12, self.HEAD_H / 2, text=col[1], anchor="w", font=self.f_bold, fill="#3B4A6B")
        h.create_line(0, self.HEAD_H - 1, w + 2000, self.HEAD_H - 1, fill=LINE)
        if not self.rows:
            b.create_text(w / 2, 60, text="Không có dữ liệu phù hợp.", fill=MUTED, font=self.f_norm)
            b.configure(scrollregion=(0, 0, w, 1))
            return
        for i, r in enumerate(self.rows):
            y, cy, tag = i * self.ROW_H, i * self.ROW_H + self.ROW_H / 2, f"row{i}"
            sel = r[self.key] == self.selected
            if sel:
                b.create_rectangle(0, y, w, y + self.ROW_H, fill=SEL_BG, outline=SEL_BG, tags=tag)
            b.create_oval(18, cy - 8, 34, cy + 8, outline=PRIMARY if sel else "#8A97B0", width=2, tags=tag)
            if sel:
                b.create_oval(22, cy - 4, 30, cy + 4, fill=PRIMARY, outline=PRIMARY, tags=tag)
            for key, x, cw in cols:
                tx, maxw = x + 12, max(cw - 24, 10)
                if self._draw_cell(key, r, tx, cy, maxw, tag):
                    continue
                bold = key in self.bold_keys
                font = self.f_bold if bold else self.f_norm
                b.create_text(tx, cy, text=self._fit(r.get(key), maxw, font), anchor="w", font=font, tags=tag,
                              fill=NAVY if key in self.navy_keys else TEXT)
            b.create_line(0, y + self.ROW_H - 1, w, y + self.ROW_H - 1, fill=LINE, tags=tag)
        b.configure(scrollregion=(0, 0, w, len(self.rows) * self.ROW_H))

    # ---- chuột
    def _row_at(self, e):
        i = int(self.body.canvasy(e.y) // self.ROW_H)
        return self.rows[i][self.key] if 0 <= i < len(self.rows) else None

    def _click(self, e):
        ident = self._row_at(e)
        if ident is not None:
            self.select(ident)

    def _double(self, e):
        ident = self._row_at(e)
        if ident is not None:
            self.select(ident)
            self.on_open()

    def _wheel(self, e):
        step = -1 if (getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0) else 1
        self.body.yview_scroll(step * 2, "units")

    def _on_scroll(self, first, last):
        self.sb.set(first, last)
        if float(first) > 0 or float(last) < 1:
            self.sb.grid(row=1, column=1, sticky="ns")
        else:
            self.sb.grid_remove()


# ====================================================================== dữ liệu sinh viên
FILTERS = ["Tất cả", "Đang ở KTX", "Chưa xếp phòng"]
STUDENT_COLS = [("MaSV", "Mã SV", 84, 0.7), ("HoTen", "Họ và tên", 160, 1.5), ("NgaySinh", "Ngày sinh", 104, 0.9),
                ("GioiTinh", "Giới tính", 84, 0.7), ("Lop", "Lớp", 110, 1.0), ("SDT", "SĐT", 112, 1.0),
                ("QueQuan", "Quê quán", 112, 1.1), ("Phong", "Phòng đang ở", 124, 1.0)]
FIELDS = [("HoTen", "Họ và tên", "entry", None), ("NgaySinh", "Ngày sinh (dd/mm/yyyy)", "entry", None),
          ("GioiTinh", "Giới tính", "combo", ["Nam", "Nữ"]), ("Lop", "Lớp", "entry", None),
          ("SDT", "Số điện thoại", "entry", None), ("QueQuan", "Quê quán", "entry", None)]
EXPORT_HEADERS = ["Mã SV", "Họ và tên", "Ngày sinh", "Giới tính", "Lớp", "SĐT", "Quê quán", "Phòng đang ở"]
EXPORT_KEYS = ["MaSV", "HoTen", "NgaySinh", "GioiTinh", "Lop", "SDT", "QueQuan", "Phong"]
# tên cột (đã bỏ dấu) chấp nhận khi nhập file
ALIASES = {"MaSV": {"ma sv", "masv", "mssv", "ma sinh vien"},
           "HoTen": {"ho va ten", "ho ten", "hoten", "ten", "ten sinh vien"},
           "NgaySinh": {"ngay sinh", "ngaysinh"},
           "GioiTinh": {"gioi tinh", "gioitinh"},
           "Lop": {"lop"},
           "SDT": {"sdt", "so dien thoai", "dien thoai"},
           "QueQuan": {"que quan", "quequan", "dia chi"}}


def load_students():
    """Danh sách sinh viên + phòng đang ở (Phong, '' nếu chưa xếp) + cờ DangO."""
    out = []
    for r in db.query("""
            SELECT s.MaSV, s.HoTen, s.NgaySinh, s.GioiTinh, s.Lop, s.SDT, s.QueQuan,
                   (SELECT GROUP_CONCAT(p.TenPhong, ', ') FROM HopDong h JOIN Phong p ON p.MaPhong=h.MaPhong
                    WHERE h.MaSV=s.MaSV AND h.TrangThai='Đang thuê') AS Phong
            FROM SinhVien s ORDER BY s.MaSV"""):
        d = {k: ("" if v is None else v) for k, v in dict(r).items()}
        d["DangO"] = bool(d["Phong"])
        d["_hay"] = fold(f"{d['MaSV']} {d['HoTen']} {d['Lop']} {d['SDT']}")
        out.append(d)
    return out


def normalize_date(s):
    """Chấp nhận dd/mm/yyyy, yyyy-mm-dd, số serial của Excel. Trả về 'dd/mm/yyyy' hoặc None nếu sai."""
    s = (s or "").strip()
    if not s:
        return ""
    try:
        if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", s):
            d = parse_date(s)
        elif re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}([ T].*)?", s):
            d = datetime.strptime(re.split(r"[ T]", s)[0], "%Y-%m-%d")
        elif re.fullmatch(r"\d+(\.\d+)?", s) and 1 <= float(s) < 80000:
            d = datetime(1899, 12, 30) + timedelta(days=int(float(s)))
        else:
            return None
    except ValueError:
        return None
    if d.year < 1900 or d.date() > date.today():
        return None
    return d.strftime("%d/%m/%Y")


def clean_student(d):
    """Chuẩn hóa + kiểm tra dữ liệu một sinh viên. Trả về (dữ liệu sạch, thông báo lỗi hoặc None)."""
    c = {k: re.sub(r"\s+", " ", str(d.get(k) or "")).strip() for k in ("HoTen", "NgaySinh", "GioiTinh", "Lop", "SDT", "QueQuan")}
    if not c["HoTen"]:
        return c, "Họ và tên không được để trống."
    nd = normalize_date(c["NgaySinh"])
    if nd is None:
        return c, "Ngày sinh không hợp lệ (định dạng dd/mm/yyyy, không ở tương lai)."
    c["NgaySinh"] = nd
    g = fold(c["GioiTinh"])
    if g in ("nam", "male", "m"):
        c["GioiTinh"] = "Nam"
    elif g in ("nu", "female", "f"):
        c["GioiTinh"] = "Nữ"
    elif g:
        return c, "Giới tính chỉ nhận 'Nam' hoặc 'Nữ'."
    phone = re.sub(r"[ .\-()]", "", c["SDT"])
    if phone:
        if re.fullmatch(r"[1-9]\d{8,9}", phone):         # Excel làm mất số 0 đầu
            phone = "0" + phone
        if not re.fullmatch(r"0\d{9,10}", phone):
            return c, "Số điện thoại phải gồm 10-11 chữ số và bắt đầu bằng 0."
    c["SDT"] = phone
    return c, None


# ====================================================================== bảng + màn hình
class StudentTable(DataTable):
    bold_keys, navy_keys = ("MaSV", "HoTen"), ("HoTen",)

    def __init__(self, master, on_select, on_open):
        super().__init__(master, on_select, on_open, STUDENT_COLS, "MaSV")

    def _draw_cell(self, key, r, tx, cy, maxw, tag):
        if key == "Phong":
            if r["Phong"]:
                self._badge(r["Phong"], GREEN_FG, GREEN_BG, tx, cy, maxw, tag)
            else:
                self.body.create_text(tx, cy, text="—", anchor="w", font=self.f_norm, fill=MUTED, tags=tag)
            return True
        return False


class SinhVienScreen(tk.Frame):
    def __init__(self, master, user=None):
        super().__init__(master, bg=PAGE_BG)
        self.user = user
        self.filter, self.sel = FILTERS[0], None
        self.rows, self.shown, self.counts = [], [], {n: 0 for n in FILTERS}
        self.kw = tk.StringVar(master=self)              # main.goto() điền sẵn ô tìm kiếm qua biến này
        self._build()
        self.refresh()
        self.kw.trace_add("write", lambda *_: self.apply())

    # ---- dựng giao diện
    def _build(self):
        pad = dict(padx=40)
        head = tk.Frame(self, bg=PAGE_BG)
        head.pack(fill="x", pady=(30, 0), **pad)
        box = tk.Frame(head, bg=PAGE_BG)
        box.pack(side="left")
        tk.Label(box, text="Quản lý sinh viên", bg=PAGE_BG, fg=NAVY, font=(FONT, 20, "bold")).pack(anchor="w")
        tk.Label(box, text="Danh sách sinh viên đăng ký ở ký túc xá", bg=PAGE_BG, fg=MUTED,
                 font=(FONT, 10)).pack(anchor="w")
        SearchBox(head, self.kw, "Tìm theo tên, mã SV, lớp, SĐT...").pack(side="right", anchor="n")

        bar = tk.Frame(self, bg=PAGE_BG)
        bar.pack(fill="x", pady=(16, 0), **pad)
        IconButton(bar, "Thêm", "plus", self.on_add, "primary").pack(side="left", padx=(0, 10))
        self.btn_edit = IconButton(bar, "Sửa", "edit", self.on_edit, "outline", enabled=False)
        self.btn_edit.pack(side="left", padx=(0, 10))
        self.btn_del = IconButton(bar, "Xóa", "trash", self.on_delete, "danger", enabled=False)
        self.btn_del.pack(side="left")
        IconButton(bar, "Xuất Excel", "up", self.on_export, "outline").pack(side="right")
        IconButton(bar, "Nhập Excel", "down", self.on_import, "outline").pack(side="right", padx=(0, 10))

        chips = tk.Frame(self, bg=PAGE_BG)
        chips.pack(fill="x", pady=(14, 14), **pad)
        self.chips = {}
        for name in FILTERS:
            self.chips[name] = Chip(chips, lambda n=name: self.set_filter(n))
            self.chips[name].pack(side="left", padx=(0, 10))

        card = Card(self)
        card.pack(fill="both", expand=True, padx=40, pady=(0, 30))
        foot = tk.Frame(card.inner, bg="white")
        foot.pack(side="bottom", fill="x")
        tk.Frame(foot, bg=LINE, height=1).pack(fill="x")
        row = tk.Frame(foot, bg="white")
        row.pack(fill="x", padx=16, pady=10)
        self.foot_l = tk.Label(row, bg="white", fg=MUTED, font=(FONT, 9))
        self.foot_l.pack(side="left")
        tk.Label(row, text="Bấm vào một dòng để chọn, sau đó dùng nút Sửa hoặc Xóa", bg="white", fg=MUTED,
                 font=(FONT, 9)).pack(side="right")
        self.table = StudentTable(card.inner, self._on_pick, self.on_edit)
        self.table.pack(fill="both", expand=True)

    # ---- dữ liệu / bộ lọc
    def refresh(self):
        self.rows = load_students()
        self.counts = {"Tất cả": len(self.rows),
                       "Đang ở KTX": sum(1 for r in self.rows if r["DangO"]),
                       "Chưa xếp phòng": sum(1 for r in self.rows if not r["DangO"])}
        self.apply()

    def set_filter(self, name):
        if name in FILTERS:
            self.filter = name
            self.apply()

    def apply(self):
        kw = fold(self.kw.get().strip())
        self.shown = [r for r in self.rows
                      if (self.filter == "Tất cả" or (r["DangO"] == (self.filter == "Đang ở KTX")))
                      and (not kw or kw in r["_hay"])]
        for name, chip in self.chips.items():
            chip.set(f"{name} ({self.counts[name]})", name == self.filter)
        self.table.selected = self.sel
        self.table.load(self.shown)
        self.foot_l.config(text=f"Hiển thị {len(self.shown)} / {len(self.rows)} sinh viên")

    def _on_pick(self, ma):
        self.sel = ma
        self.btn_edit.set_enabled(ma is not None)
        self.btn_del.set_enabled(ma is not None)

    def _student(self, ma):
        return next((r for r in self.rows if r["MaSV"] == ma), None)

    # ---- thêm / sửa / xóa
    def _ask(self, title, values=None):
        """Mở form, kiểm tra; nếu sai thì báo lỗi và mở lại với nội dung đã nhập. Trả về dict sạch hoặc None."""
        values = values or {}
        while True:
            d = form_dialog(self, title, FIELDS, values)
            if not d:
                return None
            clean, err = clean_student(d)
            if not err:
                return clean
            error(err)
            values = clean

    def on_add(self):
        d = self._ask("Thêm sinh viên")
        if not d:
            return
        new_id = db.execute("INSERT INTO SinhVien(HoTen,NgaySinh,GioiTinh,Lop,SDT,QueQuan) VALUES(?,?,?,?,?,?)",
                            (d["HoTen"], d["NgaySinh"], d["GioiTinh"], d["Lop"], d["SDT"], d["QueQuan"]))
        db.ghi_nhat_ky("sv", f"Thêm sinh viên **{d['HoTen']}**")
        self.filter = FILTERS[0]
        self.kw.set("")
        self.refresh()
        self.table.select(new_id, scroll=True)

    def on_edit(self):
        r = self._student(self.sel)
        if not r:
            return
        d = self._ask("Cập nhật sinh viên", r)
        if not d:
            return
        db.execute("UPDATE SinhVien SET HoTen=?,NgaySinh=?,GioiTinh=?,Lop=?,SDT=?,QueQuan=? WHERE MaSV=?",
                   (d["HoTen"], d["NgaySinh"], d["GioiTinh"], d["Lop"], d["SDT"], d["QueQuan"], r["MaSV"]))
        self.refresh()

    def on_delete(self):
        r = self._student(self.sel)
        if not r:
            return
        if r["DangO"]:
            return error(f"Sinh viên {r['HoTen']} đang ở phòng {r['Phong']}.\n"
                         "Hãy kết thúc hợp đồng của sinh viên này trước khi xóa.")
        if not messagebox.askyesno("Xác nhận", f"Bạn có chắc chắn muốn xóa sinh viên {r['HoTen']}?"):
            return
        try:
            db.execute("DELETE FROM SinhVien WHERE MaSV=?", (r["MaSV"],))
        except sqlite3.IntegrityError:
            return error("Không thể xóa vì sinh viên này còn hợp đồng cũ hoặc yêu cầu liên quan.")
        db.ghi_nhat_ky("sv", f"Xóa sinh viên **{r['HoTen']}**")
        self.refresh()

    # ---- xuất / nhập Excel
    def on_export(self):
        if not self.shown:
            return messagebox.showinfo("Thông báo", "Không có dữ liệu để xuất.")
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".xlsx", initialfile=f"sinh_vien_{date.today():%Y%m%d}.xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")])
        if not path:
            return
        data = [[r[k] for k in EXPORT_KEYS] for r in self.shown]
        try:
            if path.lower().endswith(".csv"):
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f)
                    w.writerow(EXPORT_HEADERS)
                    w.writerows(data)
            else:
                xlsx_io.write_xlsx(path, EXPORT_HEADERS, data, widths=[10, 26, 14, 11, 14, 14, 18, 16],
                                   sheet_name="Sinh viên")
        except OSError as e:
            return error(f"Không ghi được file: {e}")
        messagebox.showinfo("Thành công", f"Đã xuất {len(data)} sinh viên ra file:\n{path}")

    @staticmethod
    def _read_table(path):
        if path.lower().endswith(".xlsx"):
            return xlsx_io.read_xlsx(path)
        raw = open(path, "rb").read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp1258", errors="replace")
        try:
            dialect = csv.Sniffer().sniff(text[:2048], delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        return [[c.strip() for c in row] for row in csv.reader(text.splitlines(), dialect)]

    def on_import(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("Excel / CSV", "*.xlsx *.csv"), ("Tất cả", "*.*")])
        if not path:
            return
        try:
            table = self._read_table(path)
        except (OSError, ValueError, csv.Error) as e:
            return error(f"Không đọc được file: {e}")
        # tìm dòng tiêu đề trong 5 dòng đầu
        colmap, start = {}, 0
        for i, row in enumerate(table[:5]):
            m = {k: j for j, cell in enumerate(row) for k, names in ALIASES.items() if fold(cell).strip() in names}
            if "HoTen" in m:
                colmap, start = m, i + 1
                break
        if not colmap:
            return error("Không tìm thấy dòng tiêu đề có cột 'Họ và tên'.\n"
                         "Hãy dùng file do nút 'Xuất Excel' tạo ra làm mẫu.")
        added = updated = 0
        errors = []
        conn = db.get_conn()
        try:
            with conn:
                for n, row in enumerate(table[start:], start=start + 1):
                    if not any(str(c).strip() for c in row):
                        continue
                    raw = {k: (row[j] if j < len(row) else "") for k, j in colmap.items()}
                    d, err = clean_student(raw)
                    if err:
                        errors.append(f"Dòng {n}: {err}")
                        continue
                    ma = raw.get("MaSV", "").strip()
                    ma = int(ma) if ma.isdigit() and int(ma) > 0 else None
                    vals = (d["HoTen"], d["NgaySinh"], d["GioiTinh"], d["Lop"], d["SDT"], d["QueQuan"])
                    if ma and conn.execute("SELECT 1 FROM SinhVien WHERE MaSV=?", (ma,)).fetchone():
                        conn.execute("UPDATE SinhVien SET HoTen=?,NgaySinh=?,GioiTinh=?,Lop=?,SDT=?,QueQuan=? "
                                     "WHERE MaSV=?", vals + (ma,))
                        updated += 1
                    elif ma:
                        conn.execute("INSERT INTO SinhVien(HoTen,NgaySinh,GioiTinh,Lop,SDT,QueQuan,MaSV) "
                                     "VALUES(?,?,?,?,?,?,?)", vals + (ma,))
                        added += 1
                    else:
                        conn.execute("INSERT INTO SinhVien(HoTen,NgaySinh,GioiTinh,Lop,SDT,QueQuan) "
                                     "VALUES(?,?,?,?,?,?)", vals)
                        added += 1
        except sqlite3.Error as e:
            return error(f"Lỗi cơ sở dữ liệu, không có dòng nào được lưu:\n{e}")
        finally:
            conn.close()
        if added or updated:
            db.ghi_nhat_ky("sv", f"Nhập Excel: thêm **{added}**, cập nhật **{updated}** sinh viên")
        self.refresh()
        msg = f"Đã thêm {added} và cập nhật {updated} sinh viên."
        if errors:
            msg += f"\n\nBỏ qua {len(errors)} dòng lỗi:\n" + "\n".join(errors[:8]) + ("\n..." if len(errors) > 8 else "")
        (messagebox.showwarning if errors else messagebox.showinfo)("Kết quả nhập", msg)
