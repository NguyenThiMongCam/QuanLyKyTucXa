"""Trang Sinh viên (quản trị) - giao diện xanh trắng theo mẫu thiết kế.

- Tìm kiếm tức thì (không phân biệt hoa/thường và dấu tiếng Việt)
- Lọc nhanh: Tất cả / Đang ở KTX / Chưa xếp phòng
- Bấm một dòng để chọn (nút radio), sau đó dùng nút Sửa / Xóa (nhấp đúp = Sửa)
- Nhập / Xuất Excel (.xlsx cần thư viện openpyxl; nếu chưa cài sẽ dùng .csv mở được bằng Excel)
"""
import csv
import os
import re
import sqlite3
import tkinter as tk
import unicodedata
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import database as db
from screens.base import error, form_dialog, valid_date
from screens.login import BORDER, FONT, MUTED, NAVY, PAGE_BG, PLACEHOLDER, PRIMARY, SEL_BG, TEXT, rounded_rect

try:
    import openpyxl
except ImportError:          # chạy được không cần cài thêm; chỉ mất tính năng .xlsx
    openpyxl = None

FIELDS = [("HoTen", "Họ và tên", "entry", None),
          ("NgaySinh", "Ngày sinh (dd/mm/yyyy)", "entry", None),
          ("GioiTinh", "Giới tính", "combo", ["Nam", "Nữ"]),
          ("Lop", "Lớp", "entry", None),
          ("SDT", "Số điện thoại", "entry", None),
          ("QueQuan", "Quê quán", "entry", None)]
KEYS = tuple(f[0] for f in FIELDS)
FILTERS = ["Tất cả", "Đang ở KTX", "Chưa xếp phòng"]
HEADERS = ["Mã SV", "Họ và tên", "Ngày sinh", "Giới tính", "Lớp", "SĐT", "Quê quán", "Phòng đang ở"]

# cột bảng: (khóa, tiêu đề, rộng tối thiểu, tỉ lệ giãn)
COLUMNS = [("MaSV", "Mã SV", 70, 0.6), ("HoTen", "Họ và tên", 140, 1.5), ("NgaySinh", "Ngày sinh", 92, 0.9),
           ("GioiTinh", "Giới tính", 70, 0.6), ("Lop", "Lớp", 96, 1.0), ("SDT", "SĐT", 100, 1.0),
           ("QueQuan", "Quê quán", 96, 1.0), ("Phong", "Phòng đang ở", 104, 0.9)]
RADIO_W, PAD, ROW_H, HEAD_H = 62, 10, 47, 46
LINE, HEAD_BG, ROW_HOVER = "#E8EEF8", "#F7F9FE", "#F6F9FE"
GREEN_FG, GREEN_BG, GREY_FG, GREY_BG = "#0E7A3B", "#E4F6EA", "#5B6B88", "#EEF2F8"
DANGER = "#C0392B"


# ---------------------------------------------------------------------- tiện ích dữ liệu
def fold(s):
    """Bỏ dấu + chữ thường để tìm kiếm: 'Nguyễn' -> 'nguyen'."""
    s = unicodedata.normalize("NFD", str(s or "")).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def validate(d):
    if not d["HoTen"]:
        return "Họ tên không được để trống."
    if d["NgaySinh"] and not valid_date(d["NgaySinh"]):
        return "Ngày sinh phải có dạng dd/mm/yyyy."
    if d["SDT"] and not (d["SDT"].isdigit() and 9 <= len(d["SDT"]) <= 11):
        return "Số điện thoại phải gồm 9-11 chữ số."
    return None


def load_students():
    out = []
    for r in db.query("""
            SELECT s.*, COALESCE((SELECT p.TenPhong FROM HopDong h JOIN Phong p ON p.MaPhong=h.MaPhong
                   WHERE h.MaSV=s.MaSV AND h.TrangThai='Đang thuê' LIMIT 1), '') AS Phong
            FROM SinhVien s ORDER BY s.MaSV"""):
        d = dict(r)
        d["_hay"] = fold(f"{d['MaSV']} {d['HoTen']} {d['Lop'] or ''} {d['SDT'] or ''}")
        out.append(d)
    return out


# ---------------------------------------------------------------------- nhập / xuất Excel
HEADER_ALIASES = {"hoten": "HoTen", "hovaten": "HoTen", "tensinhvien": "HoTen", "ngaysinh": "NgaySinh",
                  "gioitinh": "GioiTinh", "lop": "Lop", "sdt": "SDT", "dienthoai": "SDT",
                  "sodienthoai": "SDT", "quequan": "QueQuan"}


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, date):                       # datetime cũng là date
        return v.strftime("%d/%m/%Y")
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


def _norm_date(s):
    for f in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, f).strftime("%d/%m/%Y")
        except ValueError:
            pass
    return s


def parse_import(rows):
    """rows: các dòng của file (list các ô). Trả về (danh sách sinh viên hợp lệ, danh sách lỗi)."""
    head, cols = None, {}
    for i, row in enumerate(rows[:10]):
        m = {}
        for j, v in enumerate(row):
            k = HEADER_ALIASES.get(re.sub(r"[^a-z0-9]", "", fold(_cell(v))))
            if k and k not in m:
                m[k] = j
        if "HoTen" in m:
            head, cols = i, m
            break
    if head is None:
        raise ValueError("Không tìm thấy dòng tiêu đề có cột \"Họ và tên\".\n"
                         "Các cột cần có: Họ và tên, Ngày sinh, Giới tính, Lớp, SĐT, Quê quán.")
    ok, errs = [], []
    for n, row in enumerate(rows[head + 1:], start=head + 2):
        if not any(_cell(v) for v in row):
            continue
        d = {"_row": n}
        for k in KEYS:
            j = cols.get(k)
            raw = row[j] if j is not None and j < len(row) else None
            d[k] = _cell(raw)
            if k == "SDT" and isinstance(raw, (int, float)) and len(d[k]) == 9:
                d[k] = "0" + d[k]                 # Excel làm mất số 0 đầu của số điện thoại
        d["NgaySinh"] = _norm_date(d["NgaySinh"])
        d["GioiTinh"] = {"nam": "Nam", "nu": "Nữ"}.get(fold(d["GioiTinh"]), d["GioiTinh"])
        err = validate(d) or (None if d["GioiTinh"] in ("Nam", "Nữ") else "Giới tính phải là Nam hoặc Nữ.")
        (errs.append(f"Dòng {n}: {err}") if err else ok.append(d))
    return ok, errs


def read_table(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        if openpyxl is None:
            raise RuntimeError("Máy chưa cài thư viện openpyxl nên chưa đọc được file .xlsx.\n"
                               "Cài bằng lệnh: pip install openpyxl\nhoặc lưu file thành .csv (UTF-8) rồi nhập lại.")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            return [list(r) for r in wb.active.iter_rows(values_only=True)]
        finally:
            wb.close()
    if ext == ".csv":
        with open(path, newline="", encoding="utf-8-sig") as f:
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            return list(csv.reader(f, dialect))
    raise ValueError("Chỉ hỗ trợ file .xlsx hoặc .csv.")


def write_table(path, rows):
    data = [[r["MaSV"], r["HoTen"], r["NgaySinh"] or "", r["GioiTinh"] or "", r["Lop"] or "",
             r["SDT"] or "", r["QueQuan"] or "", r["Phong"] or ""] for r in rows]
    if path.lower().endswith(".xlsx"):
        if openpyxl is None:
            raise RuntimeError("Máy chưa cài openpyxl nên chưa ghi được .xlsx (pip install openpyxl). Hãy chọn .csv.")
        from openpyxl.styles import Font
        from openpyxl.utils import get_column_letter
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Sinh viên"
        ws.append(HEADERS)
        for row in data:
            ws.append(row)
        for c in ws[1]:
            c.font = Font(bold=True)
        for i, w in enumerate([8, 26, 12, 10, 14, 14, 18, 14], 1):
            ws.column_dimensions[get_column_letter(i)].width = w
        wb.save(path)
    else:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(HEADERS)
            w.writerows(data)


# ---------------------------------------------------------------------- thành phần giao diện
def draw_icon(cv, name, x, y, color, w=1.8):
    """Vẽ icon nét mảnh 16x16 px tại góc trên-trái (x, y)."""
    def line(*p):
        cv.create_line(*[v + (x if i % 2 == 0 else y) for i, v in enumerate(p)], fill=color, width=w,
                       capstyle="round", joinstyle="round")
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
    elif name == "search":
        cv.create_oval(x + 2, y + 2, x + 11, y + 11, outline=color, width=w)
        line(10, 10, 14, 14)


BTN = {"primary": dict(bg=PRIMARY, hover=NAVY, border=PRIMARY, fg="white",
                       off_bg="#9DB7E6", off_border="#9DB7E6", off_fg="white"),
       "outline": dict(bg="white", hover="#F3F7FD", border=BORDER, fg=NAVY,
                       off_bg="#F6F8FD", off_border="#E3EAF6", off_fg="#9AAACB"),
       "danger": dict(bg="white", hover="#FDF1F1", border="#F1C9C9", fg=DANGER,
                      off_bg="#FCF8F8", off_border="#F3E4E4", off_fg="#E3A5A5")}


class IconButton(tk.Canvas):
    """Nút bo góc có icon; kind: primary / outline / danger. Có thể tắt bằng set_enabled(False)."""

    def __init__(self, master, text, icon, command, kind="outline", enabled=True):
        super().__init__(master, height=44, bg=PAGE_BG, highlightthickness=0)
        self.text, self.icon, self.command, self.kind = text, icon, command, kind
        self.font = tkfont.Font(family=FONT, size=10, weight="bold")
        self._w, self._h = 40 + self.font.measure(text) + 18, 44
        self.config(width=self._w)
        self.enabled, self.hover = enabled, False
        self.bind("<Enter>", lambda _e: self._set_hover(True))
        self.bind("<Leave>", lambda _e: self._set_hover(False))
        self.bind("<Button-1>", lambda _e: self.command() if self.enabled else None)
        self.set_enabled(enabled)

    def _set_hover(self, flag):
        self.hover = flag and self.enabled
        self._paint()

    def set_enabled(self, flag):
        self.enabled = flag
        self.config(cursor="hand2" if flag else "arrow")
        self._paint()

    def _paint(self):
        s, on = BTN[self.kind], self.enabled
        bg = (s["hover"] if self.hover else s["bg"]) if on else s["off_bg"]
        fg = s["fg"] if on else s["off_fg"]
        self.delete("all")
        rounded_rect(self, 1, 1, self._w - 1, self._h - 1, 10, fill=bg, outline=s["border"] if on else s["off_border"])
        draw_icon(self, self.icon, 16, self._h / 2 - 8, fg)
        self.create_text(40, self._h / 2, text=self.text, anchor="w", font=self.font, fill=fg)


class Chip(tk.Canvas):
    """Nút lọc dạng viên thuốc: 'Tất cả (5)'."""

    def __init__(self, master, command):
        super().__init__(master, height=42, bg=PAGE_BG, highlightthickness=0, cursor="hand2")
        self.font = tkfont.Font(family=FONT, size=10, weight="bold")
        self.text, self.on, self.hover, self._w = "", False, False, 60
        self.bind("<Button-1>", lambda _e: command())
        self.bind("<Enter>", lambda _e: self._hover(True))
        self.bind("<Leave>", lambda _e: self._hover(False))

    def _hover(self, flag):
        self.hover = flag
        self._paint()

    def set(self, text, on):
        self.text, self.on = text, on
        self._w = self.font.measure(text) + 38
        self.config(width=self._w)
        self._paint()

    def _paint(self):
        self.delete("all")
        fill = SEL_BG if self.on else ("#F3F7FD" if self.hover else "white")
        rounded_rect(self, 1, 1, self._w - 1, 41, 20, fill=fill, outline=PRIMARY if self.on else BORDER)
        self.create_text(self._w / 2, 21, text=self.text, font=self.font, fill=PRIMARY if self.on else NAVY)


class SearchBox(tk.Canvas):
    """Ô tìm kiếm bo góc có icon kính lúp và chữ gợi ý; gắn với StringVar `var`."""

    def __init__(self, master, var, placeholder, width=340, height=44):
        super().__init__(master, width=width, height=height, bg=PAGE_BG, highlightthickness=0)
        self._box = rounded_rect(self, 1, 1, width - 1, height - 1, 10, fill="white", outline=BORDER)
        draw_icon(self, "search", 14, height / 2 - 8, PLACEHOLDER, 1.6)
        self.entry = tk.Entry(self, textvariable=var, relief="flat", bd=0, font=(FONT, 10), bg="white", fg=TEXT,
                              insertbackground=TEXT, highlightthickness=0)
        self.create_window(40, height / 2, window=self.entry, anchor="w", width=width - 56, height=24)
        hint = tk.Label(self, text=placeholder, bg="white", fg=PLACEHOLDER, font=(FONT, 10), cursor="xterm")
        self._hint = self.create_window(40, height / 2, window=hint, anchor="w")   # nằm đè lên ô nhập
        hint.bind("<Button-1>", lambda _e: self.entry.focus_set())
        self.entry.bind("<FocusIn>", lambda _e: self.itemconfigure(self._box, outline=PRIMARY))
        self.entry.bind("<FocusOut>", lambda _e: self.itemconfigure(self._box, outline=BORDER))
        var.trace_add("write", lambda *_: self._sync(var))
        self._sync(var)

    def _sync(self, var):
        self.itemconfigure(self._hint, state="hidden" if var.get() else "normal")


class Card(tk.Canvas):
    """Thẻ trắng bo góc, có viền. Đặt nội dung vào self.inner."""
    INSET = 4

    def __init__(self, master, radius=12):
        super().__init__(master, bg=PAGE_BG, highlightthickness=0)
        self.radius = radius
        self.inner = tk.Frame(self, bg="white")
        self._win = self.create_window(self.INSET, self.INSET, window=self.inner, anchor="nw")
        self.bind("<Configure>", self._resize)

    def _resize(self, e):
        self.delete("box")
        rounded_rect(self, 1, 1, e.width - 1, e.height - 1, self.radius, fill="white", outline=BORDER, tags="box")
        self.tag_lower("box")
        self.itemconfigure(self._win, width=e.width - 2 * self.INSET, height=e.height - 2 * self.INSET)


class StudentTable(tk.Frame):
    """Bảng vẽ trên Canvas: nút radio chọn dòng, chữ đậm, huy hiệu phòng bo tròn, cuộn bằng chuột."""

    def __init__(self, master, on_select, on_open):
        super().__init__(master, bg="white")
        self.on_select, self.on_open = on_select, on_open
        self.rows, self.selected, self.hover, self._xs, self._w = [], None, None, [], 1
        self.f_norm = tkfont.Font(family=FONT, size=10)
        self.f_bold = tkfont.Font(family=FONT, size=10, weight="bold")
        self.f_badge = tkfont.Font(family=FONT, size=9, weight="bold")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.head = tk.Canvas(self, height=HEAD_H, bg=HEAD_BG, highlightthickness=0)
        self.head.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.body = tk.Canvas(self, bg="white", highlightthickness=0, yscrollincrement=ROW_H // 2)
        self.body.grid(row=1, column=0, sticky="nsew")
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.body.yview)
        self.body.configure(yscrollcommand=self._on_scroll)
        self.body.bind("<Configure>", lambda _e: self._draw())
        self.body.bind("<Motion>", self._motion)
        self.body.bind("<Leave>", lambda _e: self._set_hover(None))
        self.body.bind("<Button-1>", self._click)
        self.body.bind("<Double-1>", self._double)
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.body.bind(ev, self._wheel)

    # ---- dữ liệu
    def load(self, rows):
        self.rows = rows
        if self.selected is not None and self._index(self.selected) is None:
            self.selected = None
            self.on_select(None)
        self._draw()

    def _index(self, ma):
        return next((i for i, r in enumerate(self.rows) if r["MaSV"] == ma), None)

    def select(self, ma, scroll=False):
        old, self.selected = self.selected, ma
        for key in (old, ma):
            i = self._index(key) if key is not None else None
            if i is not None:
                self._draw_row(i)
        if scroll and ma is not None:
            self._scroll_to(ma)
        if old != ma:
            self.on_select(ma)

    def _scroll_to(self, ma):
        i, total, view = self._index(ma), len(self.rows) * ROW_H, self.body.winfo_height()
        if i is None or total <= view:
            return
        top, y = self.body.canvasy(0), i * ROW_H
        if y < top or y + ROW_H > top + view:
            self.body.yview_moveto(max(0.0, (y - view / 2) / total))

    # ---- vẽ
    def _layout(self, width):
        avail = max(width - RADIO_W, 1)
        base = sum(c[2] for c in COLUMNS)
        extra, scale = max(avail - base, 0), min(avail / base, 1)
        tw, x, out = sum(c[3] for c in COLUMNS), RADIO_W, []
        for c in COLUMNS:
            w = c[2] * scale + extra * c[3] / tw
            out.append((x, w))
            x += w
        return out

    def _fit(self, text, maxw, font):
        text = str(text)
        if font.measure(text) <= maxw:
            return text
        while text and font.measure(text + "…") > maxw:
            text = text[:-1]
        return text + "…" if text else ""

    def _draw(self):
        self._w = max(self.body.winfo_width(), 1)
        self._xs = self._layout(self._w)
        self.head.delete("all")
        self.head.create_line(0, HEAD_H - 1, 5000, HEAD_H - 1, fill=LINE)
        for (_k, title, *_), (x, cw) in zip(COLUMNS, self._xs):
            self.head.create_text(x + PAD, HEAD_H / 2, text=title, anchor="w", font=self.f_bold, fill=MUTED)
        self.body.delete("all")
        for i in range(len(self.rows)):
            self._draw_row(i)
        self.body.configure(scrollregion=(0, 0, self._w, len(self.rows) * ROW_H))

    def _draw_row(self, i):
        b, r, tag = self.body, self.rows[i], f"r{i}"
        b.delete(tag)
        y = i * ROW_H
        cy = y + ROW_H / 2
        sel = r["MaSV"] == self.selected
        bg = SEL_BG if sel else (ROW_HOVER if i == self.hover else "white")
        b.create_rectangle(0, y, self._w, y + ROW_H, fill=bg, outline="", tags=tag)
        b.create_line(0, y + ROW_H - 1, self._w, y + ROW_H - 1, fill=LINE, tags=tag)
        b.create_oval(18, cy - 8, 34, cy + 8, fill="white", outline=PRIMARY if sel else "#9FB0CC",
                      width=2 if sel else 1, tags=tag)
        if sel:
            b.create_oval(22, cy - 4, 30, cy + 4, fill=PRIMARY, outline=PRIMARY, tags=tag)
        for (key, *_), (x, cw) in zip(COLUMNS, self._xs):
            tx, maxw = x + PAD, cw - 2 * PAD
            if key == "Phong":
                has = bool(r["Phong"])
                label = r["Phong"] if has else "Chưa xếp"
                fg, fill = (GREEN_FG, GREEN_BG) if has else (GREY_FG, GREY_BG)
                bw = min(self.f_badge.measure(label) + 24, max(maxw, 30))
                rounded_rect(b, tx, cy - 12, tx + bw, cy + 12, 12, fill=fill, outline=fill, tags=tag)
                b.create_text(tx + bw / 2, cy, text=self._fit(label, bw - 12, self.f_badge), font=self.f_badge,
                              fill=fg, tags=tag)
                continue
            font = self.f_bold if key in ("MaSV", "HoTen") else self.f_norm
            fg = NAVY if key == "HoTen" else TEXT
            b.create_text(tx, cy, text=self._fit(r[key] or "", maxw, font), anchor="w", font=font, fill=fg, tags=tag)

    # ---- chuột
    def _row_at(self, e):
        i = int(self.body.canvasy(e.y) // ROW_H)
        return i if 0 <= i < len(self.rows) else None

    def _set_hover(self, i):
        old, self.hover = self.hover, i
        self.body.config(cursor="hand2" if i is not None else "")
        for k in (old, i):
            if k is not None and k < len(self.rows):
                self._draw_row(k)

    def _motion(self, e):
        i = self._row_at(e)
        if i != self.hover:
            self._set_hover(i)

    def _click(self, e):
        i = self._row_at(e)
        if i is not None:
            self.select(self.rows[i]["MaSV"])

    def _double(self, e):
        i = self._row_at(e)
        if i is not None:
            self.select(self.rows[i]["MaSV"])
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


# ---------------------------------------------------------------------- màn hình
class SinhVienScreen(tk.Frame):
    def __init__(self, master, user=None):
        super().__init__(master, bg=PAGE_BG)
        self.user = user
        self.filter, self.sel = FILTERS[0], None
        self.rows, self.shown, self.counts = [], [], {n: 0 for n in FILTERS}
        self.kw = tk.StringVar(master=self)          # main.goto() điền sẵn ô tìm kiếm qua biến này
        self._build()
        self.refresh()
        self.kw.trace_add("write", lambda *_: self.apply())

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
        IconButton(bar, "Xuất Excel", "upload", self.on_export).pack(side="right")
        IconButton(bar, "Nhập Excel", "download", self.on_import).pack(side="right", padx=(0, 10))

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
        in_room = sum(1 for r in self.rows if r["Phong"])
        self.counts = {FILTERS[0]: len(self.rows), FILTERS[1]: in_room, FILTERS[2]: len(self.rows) - in_room}
        self.apply()

    def set_filter(self, name):
        if name in FILTERS:
            self.filter = name
            self.apply()

    def apply(self):
        kw = fold(self.kw.get().strip())
        keep = {FILTERS[0]: lambda r: True, FILTERS[1]: lambda r: bool(r["Phong"]),
                FILTERS[2]: lambda r: not r["Phong"]}[self.filter]
        self.shown = [r for r in self.rows if keep(r) and (not kw or kw in r["_hay"])]
        for name, chip in self.chips.items():
            chip.set(f"{name} ({self.counts[name]})", name == self.filter)
        self.table.load(self.shown)
        self.foot_l.config(text=f"Hiển thị {len(self.shown)} / {len(self.rows)} sinh viên")

    def _on_pick(self, ma):
        self.sel = ma
        self.btn_edit.set_enabled(ma is not None)
        self.btn_del.set_enabled(ma is not None)

    # ---- thêm / sửa / xóa
    def on_add(self):
        d = form_dialog(self, "Thêm sinh viên", FIELDS)
        if not d:
            return
        err = validate(d)
        if err:
            return error(err)
        new_id = db.execute("INSERT INTO SinhVien(HoTen,NgaySinh,GioiTinh,Lop,SDT,QueQuan) VALUES(?,?,?,?,?,?)",
                            tuple(d[k] for k in KEYS))
        db.ghi_nhat_ky("sv", f"Thêm sinh viên **{d['HoTen']}**")
        self.filter = FILTERS[0]
        self.kw.set("")
        self.refresh()
        self.table.select(new_id, scroll=True)

    def on_edit(self):
        if self.sel is None:
            return
        cur = dict(db.query("SELECT * FROM SinhVien WHERE MaSV=?", (self.sel,), one=True))
        d = form_dialog(self, "Sửa thông tin sinh viên", FIELDS, cur)
        if not d:
            return
        err = validate(d)
        if err:
            return error(err)
        db.execute("UPDATE SinhVien SET HoTen=?,NgaySinh=?,GioiTinh=?,Lop=?,SDT=?,QueQuan=? WHERE MaSV=?",
                   tuple(d[k] for k in KEYS) + (self.sel,))
        self.refresh()

    def on_delete(self):
        r = next((x for x in self.rows if x["MaSV"] == self.sel), None)
        if not r:
            return
        extra = f"\n\nSinh viên đang ở phòng {r['Phong']}." if r["Phong"] else ""
        if not messagebox.askyesno("Xác nhận", f"Bạn có chắc chắn muốn xóa sinh viên {r['HoTen']}?{extra}"):
            return
        try:
            db.execute("DELETE FROM SinhVien WHERE MaSV=?", (r["MaSV"],))
        except sqlite3.IntegrityError:
            error("Không thể xóa vì dữ liệu này đang được sử dụng ở mục khác (hợp đồng, yêu cầu...).")
        self.refresh()

    # ---- Excel
    def on_export(self):
        if not self.shown:
            return messagebox.showinfo("Thông báo", "Không có dữ liệu để xuất.")
        ext = ".xlsx" if openpyxl else ".csv"
        types = ([("Excel", "*.xlsx")] if openpyxl else []) + [("CSV (mở được bằng Excel)", "*.csv")]
        path = filedialog.asksaveasfilename(defaultextension=ext, filetypes=types,
                                            initialfile=f"sinh_vien_{date.today():%Y%m%d}{ext}")
        if not path:
            return
        try:
            write_table(path, self.shown)
        except (OSError, RuntimeError) as e:
            return error(f"Không ghi được file: {e}")
        messagebox.showinfo("Thành công", f"Đã xuất {len(self.shown)} sinh viên ra:\n{path}")

    def on_import(self):
        path = filedialog.askopenfilename(title="Nhập sinh viên từ Excel",
                                          filetypes=[("Excel / CSV", "*.xlsx *.xlsm *.csv"), ("Tất cả", "*.*")])
        if not path:
            return
        try:
            ok, errs = parse_import(read_table(path))
        except Exception as e:                       # file hỏng / sai định dạng / thiếu openpyxl
            return error(f"Không đọc được file:\n{e}")
        seen = {(fold(r["HoTen"]), r["NgaySinh"] or "") for r in self.rows}
        new = []
        for d in ok:
            key = (fold(d["HoTen"]), d["NgaySinh"])
            if key in seen:
                errs.append(f"Dòng {d['_row']}: trùng sinh viên đã có ({d['HoTen']}).")
            else:
                seen.add(key)
                new.append(d)
        for d in new:
            db.execute("INSERT INTO SinhVien(HoTen,NgaySinh,GioiTinh,Lop,SDT,QueQuan) VALUES(?,?,?,?,?,?)",
                       tuple(d[k] for k in KEYS))
        if new:
            db.ghi_nhat_ky("sv", f"Nhập **{len(new)}** sinh viên từ file {os.path.basename(path)}")
            self.filter = FILTERS[0]
            self.kw.set("")
            self.refresh()
        msg = f"Đã nhập {len(new)} sinh viên."
        if errs:
            msg += f"\nBỏ qua {len(errs)} dòng:\n" + "\n".join(errs[:8]) + ("\n…" if len(errs) > 8 else "")
        (messagebox.showinfo if new else messagebox.showwarning)("Kết quả nhập Excel", msg)

