
import re
import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from tkinter import font as tkfont

import database as db
from screens.base import error, money, pick_id, valid_date
from screens.login import BORDER, FONT, MUTED, NAVY, PAGE_BG, PRIMARY, SEL_BG, TEXT, FlatButton, rounded_rect
from screens.modal import form_modal
from screens.sinhvien import Card, Chip, DataTable, SearchBox, fold
from screens.uikit import (BAR_OK, DANGER, GREEN_FG, TRACK, ActionButton, draw_dot, fit, glyph, room_cell, two_lines)

LINE = "#E6ECF7"

SCHEMA = """
CREATE TABLE IF NOT EXISTS SuaChua(
    MaSC INTEGER PRIMARY KEY AUTOINCREMENT,
    MaPhong INTEGER NOT NULL REFERENCES Phong(MaPhong) ON DELETE CASCADE,
    HangMuc TEXT NOT NULL, MoTa TEXT, MucDo TEXT NOT NULL DEFAULT 'Bình thường',
    TrangThai TEXT NOT NULL DEFAULT 'Chờ xử lý', NgayBao TEXT NOT NULL, NgayXong TEXT,
    NguoiXuLy TEXT, ChiPhi INTEGER NOT NULL DEFAULT 0,
    MaYC INTEGER REFERENCES YeuCau(MaYC) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS PhuTrachPhong(
    MaPhong INTEGER PRIMARY KEY REFERENCES Phong(MaPhong) ON DELETE CASCADE,
    MaNV INTEGER REFERENCES NhanVien(MaNV) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS PhiDichVu(
    MaPhi INTEGER PRIMARY KEY AUTOINCREMENT,
    MaPhong INTEGER NOT NULL REFERENCES Phong(MaPhong) ON DELETE CASCADE,
    MaDV INTEGER NOT NULL REFERENCES DichVu(MaDV),
    Thang TEXT NOT NULL, SoLuong INTEGER NOT NULL DEFAULT 1, TinhTheo TEXT NOT NULL DEFAULT 'người',
    DonGia INTEGER NOT NULL, ThanhTien INTEGER NOT NULL, TrangThai TEXT NOT NULL DEFAULT 'Chưa thu',
    NgayThu TEXT, HinhThuc TEXT, GhiChu TEXT, UNIQUE(MaPhong, MaDV, Thang));
CREATE TABLE IF NOT EXISTS CauHinhDV(Khoa TEXT PRIMARY KEY);
"""
NEW_COLUMNS = [("SuaChua", "NgayNhan", "TEXT"), ("SuaChua", "NguoiBao", "TEXT")]   # cho CSDL đã có bảng SuaChua cũ

# hạng mục: tên -> (icon, màu chữ/icon, màu nền)
CATS = {"Quạt": ("fan", "#1D4F9F", "#DCE9FB"), "Điện": ("bolt", "#8A5A00", "#FFF0D0"),
        "Đèn": ("bulb", "#8A6D00", "#FFF7CC"), "Nước": ("drop", "#0B6E8A", "#D8F1F8"),
        "Cửa/Khóa": ("door", "#5B3FC4", "#EEE8FF"), "Giường/Tủ": ("bed", "#0E7A3B", "#E4F6EA"),
        "Internet": ("wifi", "#1558C0", "#E3EEFF"), "Khác": ("tool", "#5B6B88", "#EEF2F8")}
# dịch vụ thu phí: (từ khóa không dấu) -> kiểu biểu tượng
SERVICES = [(("wifi", "internet", "mang"), ("wifi", "#1558C0", "#E3EEFF")), (("rac",), ("trash", "#0E7A3B", "#E4F6EA")),
            (("nuoc",), ("drop", "#0B6E8A", "#D8F1F8")), (("dien",), ("bolt", "#8A5A00", "#FFF0D0"))]
LEVELS = {"Bình thường": ("#5B6B88", "#EEF2F8"), "Cao": ("#8A5A00", "#FFF0D0"), "Khẩn cấp": ("#B42318", "#FDE8E8")}
STATES = {"Chờ xử lý": ("#8A5A00", "#FFF0D0"), "Đang sửa": ("#1D4F9F", "#DCE9FB"), "Đã xong": ("#0E7A3B", "#E4F6EA")}
FEE_STATES = {"Chưa thu": ("#8A5A00", "#FFF0D0"), "Đã thu": ("#0E7A3B", "#E4F6EA")}
DOT = {"Chờ xử lý": "#E58A12", "Đang sửa": "#1558C0", "Đã xong": "#22A06B"}
RANK = {"Khẩn cấp": 0, "Cao": 1, "Bình thường": 2}
FILTERS = ["Cần xử lý", "Chờ xử lý", "Đang sửa", "Đã xong"]
FEE_FILTERS = ["Tất cả", "Chưa thu", "Đã thu"]
ALL_CATS, ALL_SVC, ALL_MONTHS = "Tất cả hạng mục", "Tất cả dịch vụ", "Tất cả tháng"
TABS = [("issues", "Danh sách sự cố"), ("rooms", "Theo phòng"), ("fees", "Thu phí dịch vụ"),
        ("price", "Bảng giá dịch vụ")]
HINTS = {"issues": "Bấm vào một dòng để chọn, nhấp đúp để xem chi tiết",
         "rooms": "Bấm vào một sự cố trong ô phòng để chọn, nhấp đúp để xem chi tiết",
         "fees": "Bấm vào một dòng để chọn, sau đó dùng nút Thu tiền, Sửa hoặc Xóa",
         "price": "Bấm vào một dòng để chọn, sau đó dùng nút Sửa hoặc Xóa"}
# nút theo tab: (khóa nút, chữ, icon, kiểu)
BUTTONS = {
    "issues": [("add", "Báo sự cố", "plus", "primary"), ("edit", "Sửa", "edit", "outline"),
               ("del", "Xóa", "trash", "danger"), ("start", "Nhận sửa", "tool", "outline"),
               ("done", "Hoàn thành", "check", "success"), ("assign", "Phân công", "user", "outline")],
    "fees": [("add", "Tạo phiếu thu", "plus", "primary"), ("edit", "Sửa", "edit", "outline"),
             ("del", "Xóa", "trash", "danger"), ("start", "Thu tiền", "check", "success")],
    "price": [("add", "Thêm", "plus", "primary"), ("edit", "Sửa", "edit", "outline"), ("del", "Xóa", "trash", "danger")]}
BUTTONS["rooms"] = BUTTONS["issues"]

# từ khóa (không dấu) để đoán hạng mục từ nội dung yêu cầu của sinh viên
KEYWORDS = [("Quạt", ("quat",)), ("Đèn", ("den", "bong")), ("Điện", ("dien", "o cam", "cau dao", "chap", "day")),
            ("Nước", ("nuoc", "voi", "ong", "ro", "toilet", "bon", "cong")), ("Cửa/Khóa", ("cua", "khoa", "chia")),
            ("Giường/Tủ", ("giuong", "tu", "ban", "ghe", "ke", "nem")), ("Internet", ("wifi", "mang", "internet"))]


# ---------------------------------------------------------------------- tiện ích
def today():
    return datetime.now().strftime("%d/%m/%Y")


def this_month():
    return datetime.now().strftime("%Y-%m")


def month_label(m):                      # '2026-11' -> '11/2026'
    y, mo = m.split("-")
    return f"{mo}/{y}"


def label_month(s):                      # '11/2026' -> '2026-11'
    mo, y = s.split("/")
    return f"{y}-{mo}"


def has_word(f, k):
    return (k in f) if " " in k else (k in set(re.findall(r"\w+", f)))


def guess_cat(text):
    """Đoán hạng mục từ mô tả: 'quạt trần kêu to' -> 'Quạt'."""
    f = fold(text)
    for cat, kws in KEYWORDS:
        if any(has_word(f, k) for k in kws):
            return cat
    return "Khác"


def svc_style(name):
    f = fold(name)
    for kws, st in SERVICES:
        if any(has_word(f, k) for k in kws):
            return st
    return ("list", "#5B6B88", "#EEF2F8")


def initials(name):
    parts = (name or "").split()
    if not parts:
        return "?"
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else parts[0][:2].upper()


def wrap(text, maxw, font, lines=2):
    """Ngắt dòng theo từ, tối đa `lines` dòng (dòng cuối rút gọn bằng …)."""
    out, cur = [], ""
    for w in str(text or "").split():
        t = (cur + " " + w).strip()
        if font.measure(t) <= maxw or not cur:
            cur = t
        else:
            out.append(cur)
            cur = w
    out.append(cur)
    if len(out) > lines:
        out = out[:lines]
        out[-1] = fit(out[-1] + "…", maxw, font)
    return [fit(o, maxw, font) for o in out if o]


def repair_date(it):
    """(ngày, nhãn) hiển thị ở cột 'Ngày sửa'."""
    if it["NgayXong"]:
        return it["NgayXong"], "Hoàn thành"
    if it["NgayNhan"]:
        return it["NgayNhan"], "Bắt đầu sửa"
    return "", ""


# ---------------------------------------------------------------------- dữ liệu
def ensure_table():
    conn = db.get_conn()
    try:
        conn.executescript(SCHEMA)
        for table, col, decl in NEW_COLUMNS:
            if col not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        # tặng sẵn dịch vụ "Thu gom rác" một lần duy nhất (sửa giá hoặc xóa ở tab Bảng giá dịch vụ)
        if not conn.execute("SELECT 1 FROM CauHinhDV WHERE Khoa='seed_rac'").fetchone():
            if not conn.execute("SELECT 1 FROM DichVu WHERE TenDV LIKE '%rác%'").fetchone():
                conn.execute("INSERT INTO DichVu(TenDV,DonGia,DonVi) VALUES('Thu gom rác',15000,'tháng')")
            conn.execute("INSERT INTO CauHinhDV(Khoa) VALUES('seed_rac')")
        conn.commit()
    finally:
        conn.close()


def load_rooms():
    return [dict(r) for r in db.query("""
        SELECT p.MaPhong, p.TenPhong, p.Tang, nv.HoTen AS PhuTrach, nv.MaNV AS MaNV
        FROM Phong p LEFT JOIN PhuTrachPhong pt ON pt.MaPhong=p.MaPhong
        LEFT JOIN NhanVien nv ON nv.MaNV=pt.MaNV ORDER BY p.TenPhong""")]


def load_issues():
    out = []
    for r in db.query("""
            SELECT sc.*, p.TenPhong, p.Tang, nv.HoTen AS PhuTrach, COALESCE(sc.NguoiBao, s.HoTen, '') AS Bao
            FROM SuaChua sc JOIN Phong p ON p.MaPhong=sc.MaPhong
            LEFT JOIN PhuTrachPhong pt ON pt.MaPhong=p.MaPhong LEFT JOIN NhanVien nv ON nv.MaNV=pt.MaNV
            LEFT JOIN YeuCau y ON y.MaYC=sc.MaYC LEFT JOIN SinhVien s ON s.MaSV=y.MaSV"""):
        d = dict(r)
        d["_hay"] = fold(f"{d['TenPhong']} {d['HangMuc']} {d['MoTa'] or ''} {d['NguoiXuLy'] or ''} "
                         f"{d['PhuTrach'] or ''} {d['Bao']}")
        out.append(d)
    # việc đang mở: khẩn cấp trước, cũ trước; việc đã xong: mới nhất trước
    out.sort(key=lambda d: (d["TrangThai"] == "Đã xong", 0 if d["TrangThai"] == "Đã xong" else RANK[d["MucDo"]],
                            -d["MaSC"] if d["TrangThai"] == "Đã xong" else d["MaSC"]))
    return out


def stats(issues, rooms):
    open_ = [i for i in issues if i["TrangThai"] != "Đã xong"]
    return {"rooms_bad": len({i["MaPhong"] for i in open_}), "rooms": len(rooms),
            "cho": sum(1 for i in open_ if i["TrangThai"] == "Chờ xử lý"),
            "dang": sum(1 for i in open_ if i["TrangThai"] == "Đang sửa"),
            "gap": sum(1 for i in open_ if i["MucDo"] == "Khẩn cấp")}


def pending_requests():
    """Yêu cầu 'Sửa chữa' của sinh viên đang chờ và chưa có phiếu sửa chữa."""
    return db.query("""
        SELECT y.MaYC, y.NoiDung, y.NgayGui, s.HoTen,
               (SELECT p.MaPhong FROM HopDong h JOIN Phong p ON p.MaPhong=h.MaPhong
                 WHERE h.MaSV=y.MaSV AND h.TrangThai='Đang thuê' LIMIT 1) AS MaPhong,
               (SELECT p.TenPhong FROM HopDong h JOIN Phong p ON p.MaPhong=h.MaPhong
                 WHERE h.MaSV=y.MaSV AND h.TrangThai='Đang thuê' LIMIT 1) AS TenPhong
        FROM YeuCau y JOIN SinhVien s ON s.MaSV=y.MaSV
        WHERE y.Loai='Sửa chữa' AND y.TrangThai='Chờ xử lý'
          AND NOT EXISTS (SELECT 1 FROM SuaChua c WHERE c.MaYC=y.MaYC)
        ORDER BY y.MaYC""")


def fee_services():
    """Dịch vụ thu theo tháng (điện, nước tính theo số đo trong hóa đơn nên không nằm ở đây)."""
    return db.query("SELECT * FROM DichVu WHERE TenDV NOT IN ('Điện','Nước') ORDER BY MaDV")


def load_fees():
    out = []
    for r in db.query("""
            SELECT f.*, p.TenPhong, p.Tang, d.TenDV, nv.HoTen AS PhuTrach
            FROM PhiDichVu f JOIN Phong p ON p.MaPhong=f.MaPhong JOIN DichVu d ON d.MaDV=f.MaDV
            LEFT JOIN PhuTrachPhong pt ON pt.MaPhong=p.MaPhong LEFT JOIN NhanVien nv ON nv.MaNV=pt.MaNV
            ORDER BY f.Thang DESC, p.TenPhong, d.TenDV"""):
        d = dict(r)
        d.update(ThangHT=month_label(d["Thang"]), Gia=money(d["DonGia"]), Tien=money(d["ThanhTien"]),
                 SL=f"{d['SoLuong']} {d['TinhTheo']}")
        d["_hay"] = fold(f"{d['TenPhong']} {d['TenDV']} {d['ThangHT']} {d['PhuTrach'] or ''}")
        out.append(d)
    return out


def fee_stats(fees):
    paid = [f for f in fees if f["TrangThai"] == "Đã thu"]
    total, got = sum(f["ThanhTien"] for f in fees), sum(f["ThanhTien"] for f in paid)
    return {"n": len(fees), "n_paid": len(paid), "total": total, "paid": got, "due": total - got}


def generate_fees(month, ma_dv=None, per_person=True):
    """Tạo phiếu thu tháng `month` cho mọi phòng đang có người ở. Trả về (số phiếu mới, số phiếu đã có nên bỏ qua)."""
    svcs = [r for r in fee_services() if ma_dv in (None, r["MaDV"])]
    rooms = db.query("""SELECT p.MaPhong, COUNT(h.MaHD) AS n FROM Phong p
                        JOIN HopDong h ON h.MaPhong=p.MaPhong AND h.TrangThai='Đang thuê'
                        WHERE p.TrangThai<>'Bảo trì' GROUP BY p.MaPhong""")
    have = {(r["MaPhong"], r["MaDV"]) for r in db.query("SELECT MaPhong, MaDV FROM PhiDichVu WHERE Thang=?", (month,))}
    made = skipped = 0
    for rm in rooms:
        for sv in svcs:
            if (rm["MaPhong"], sv["MaDV"]) in have:
                skipped += 1
                continue
            qty = rm["n"] if per_person else 1
            db.execute("INSERT INTO PhiDichVu(MaPhong,MaDV,Thang,SoLuong,TinhTheo,DonGia,ThanhTien) "
                       "VALUES(?,?,?,?,?,?,?)", (rm["MaPhong"], sv["MaDV"], month, qty,
                                                 "người" if per_person else "phòng", sv["DonGia"], sv["DonGia"] * qty))
            made += 1
    return made, skipped


def price_rows():
    return [dict(r, Gia=money(r["DonGia"])) for r in db.query("SELECT * FROM DichVu ORDER BY MaDV")]


def F(key, label, kind="entry", opts=None, ph="", required=False, span=1):
    """Mô tả một trường của form_modal."""
    return {"key": key, "label": label, "kind": kind, "opts": opts or [], "ph": ph, "required": required, "span": span}


PAY_METHODS = ["Tiền mặt", "Chuyển khoản"]
PRICE_FIELDS = [F("TenDV", "Tên dịch vụ", ph="Ví dụ: Thu gom rác", required=True, span=2),
                F("DonGia", "Đơn giá (đ)", ph="15000", required=True), F("DonVi", "Đơn vị tính", ph="tháng")]


def price_check(d):
    if not d["TenDV"]:
        return "Tên dịch vụ không được để trống."
    if not d["DonGia"].isdigit():
        return "Đơn giá phải là số nguyên không âm."
    return None


# ---------------------------------------------------------------------- vẽ chung
def icon_dot(cv, cat, cx, cy, r=12, tags=()):
    icon, fg, bg = CATS.get(cat, CATS["Khác"])
    draw_dot(cv, icon, fg, bg, cx, cy, r, tags)


# ---------------------------------------------------------------------- các bảng
class _Table(DataTable):
    """Bảng dùng chung + font chữ nhỏ cho dòng phụ + thông báo riêng khi chưa có dữ liệu."""
    empty_text = ""

    def __init__(self, master, on_select, on_open, columns, key):
        super().__init__(master, on_select, on_open, columns, key)
        self.f_small = tkfont.Font(family=FONT, size=8)

    def _draw(self):
        super()._draw()
        if not self.rows and self.empty_text:
            self.body.delete("all")
            self.body.create_text(max(self.body.winfo_width(), 1) / 2, 70, text=self.empty_text, font=self.f_norm,
                                  fill=MUTED)


ISSUE_COLS = [("MaSC", "Mã", 40, 0.3), ("TenPhong", "Phòng · phụ trách", 130, 1.3), ("HangMuc", "Hạng mục", 110, 1.1),
              ("MoTa", "Mô tả", 120, 1.7), ("MucDo", "Mức độ", 116, 0.9), ("NgayBao", "Ngày gửi", 98, 0.9),
              ("NgaySua", "Ngày sửa", 100, 0.9), ("TrangThai", "Trạng thái", 96, 0.8)]


class IssueTable(_Table):
    empty_text = "Chưa có sự cố nào. Bấm \"Báo sự cố\" để thêm."

    def __init__(self, master, on_select, on_open):
        super().__init__(master, on_select, on_open, ISSUE_COLS, "MaSC")

    def _draw_cell(self, key, r, tx, cy, maxw, tag):
        if key == "TenPhong":
            room_cell(self, r, tx, cy, maxw, tag)
        elif key == "HangMuc":
            icon_dot(self.body, r["HangMuc"], tx + 12, cy, 12, tag)
            self.body.create_text(tx + 32, cy, text=self._fit(r["HangMuc"], maxw - 32, self.f_norm), anchor="w",
                                  font=self.f_norm, fill=TEXT, tags=tag)
        elif key in ("MucDo", "TrangThai"):
            fg, fill = (LEVELS if key == "MucDo" else STATES)[r[key]]
            self._badge(r[key], fg, fill, tx, cy, maxw, tag)
        elif key == "NgayBao":
            two_lines(self, tx, cy, maxw, tag, r["NgayBao"], r["Bao"] and f"bởi {r['Bao']}")
        elif key == "NgaySua":
            d, label = repair_date(r)
            two_lines(self, tx, cy, maxw, tag, d, label, GREEN_FG if r["NgayXong"] else "#1D4F9F")
        else:
            return False
        return True


FEE_COLS = [("TenPhong", "Phòng · phụ trách", 130, 1.3), ("TenDV", "Dịch vụ", 130, 1.3), ("ThangHT", "Tháng", 74, 0.6),
            ("SL", "Số lượng", 84, 0.7), ("Gia", "Đơn giá (đ)", 84, 0.8), ("Tien", "Thành tiền (đ)", 100, 0.9),
            ("TrangThai", "Trạng thái", 96, 0.8), ("NgayThu", "Ngày thu", 96, 0.9)]


class FeeTable(_Table):
    bold_keys = ("Tien",)
    empty_text = "Chưa có phiếu thu nào. Bấm \"Tạo phiếu thu\" để lập phí dịch vụ cho cả tháng."

    def __init__(self, master, on_select, on_open):
        super().__init__(master, on_select, on_open, FEE_COLS, "MaPhi")

    def _draw_cell(self, key, r, tx, cy, maxw, tag):
        if key == "TenPhong":
            room_cell(self, r, tx, cy, maxw, tag)
        elif key == "TenDV":
            icon, fg, bg = svc_style(r["TenDV"])
            draw_dot(self.body, icon, fg, bg, tx + 12, cy, 12, tag)
            self.body.create_text(tx + 32, cy, text=self._fit(r["TenDV"], maxw - 32, self.f_norm), anchor="w",
                                  font=self.f_norm, fill=TEXT, tags=tag)
        elif key == "TrangThai":
            fg, fill = FEE_STATES[r["TrangThai"]]
            self._badge(r["TrangThai"], fg, fill, tx, cy, maxw, tag)
        elif key == "NgayThu":
            two_lines(self, tx, cy, maxw, tag, r["NgayThu"], r["HinhThuc"] or "")
        else:
            return False
        return True


class PriceTable(_Table):
    bold_keys, navy_keys = ("TenDV",), ("TenDV",)
    empty_text = "Chưa có dịch vụ nào."

    def __init__(self, master, on_select, on_open):
        super().__init__(master, on_select, on_open,
                         [("MaDV", "Mã", 50, 0.4), ("TenDV", "Tên dịch vụ", 200, 2.0), ("Gia", "Đơn giá (đ)", 120, 1.0),
                          ("DonVi", "Đơn vị", 100, 1.0)], "MaDV")


# ---------------------------------------------------------------------- sơ đồ theo phòng
TILE_W, GAP, ROW = 250, 14, 32


class RoomIssueMap(tk.Frame):
    """Mỗi phòng một ô (kèm người phụ trách); trong ô liệt kê từng sự cố với biểu tượng hạng mục."""

    def __init__(self, master, on_select, on_open):
        super().__init__(master, bg="white")
        self.on_select, self.on_open = on_select, on_open
        self.groups, self.selected, self._hit, self._total, self._tw = [], None, [], 1, TILE_W
        self.f_head = tkfont.Font(family=FONT, size=11, weight="bold")
        self.f_title = tkfont.Font(family=FONT, size=12, weight="bold")
        self.f_norm = tkfont.Font(family=FONT, size=9)
        self.f_bold = tkfont.Font(family=FONT, size=9, weight="bold")
        self.f_small = tkfont.Font(family=FONT, size=8)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.cv = tk.Canvas(self, bg="white", highlightthickness=0, yscrollincrement=24)
        self.cv.grid(row=0, column=0, sticky="nsew")
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=self._on_scroll)
        self.cv.bind("<Configure>", lambda _e: self._draw())
        self.cv.bind("<Button-1>", self._click)
        self.cv.bind("<Double-1>", self._double)
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.cv.bind(ev, self._wheel)

    def load(self, groups):
        self.groups = groups
        ids = {i["MaSC"] for g in groups for i in g["Issues"]}
        if self.selected is not None and self.selected not in ids:
            self.selected = None
            self.on_select(None)
        self._draw()

    def select(self, ma, scroll=False):
        old, self.selected = self.selected, ma
        self._draw()
        if scroll and ma is not None:
            box = next((h for h in self._hit if h[4] == ma), None)
            if box and self._total > self.cv.winfo_height():
                top = self.cv.canvasy(0)
                if box[1] < top or box[3] > top + self.cv.winfo_height():
                    self.cv.yview_moveto(max(0.0, (box[1] - 70) / self._total))
        if old != ma:
            self.on_select(ma)

    @staticmethod
    def _tile_h(g):
        return 68 + max(len(g["Issues"]), 1) * ROW + 10

    def _draw(self):
        cv = self.cv
        cv.delete("all")
        self._hit = []
        w = max(cv.winfo_width(), 1)
        if not self.groups:
            cv.create_text(w / 2, 70, text="Không có phòng nào phù hợp.", fill=MUTED, font=self.f_norm)
            self._total = 1
            cv.configure(scrollregion=(0, 0, w, 1))
            return
        per, y = max(1, (w - GAP) // (TILE_W + GAP)), GAP
        self._tw = max(200, (w - GAP) // per - GAP)        # ô giãn đều cho vừa chiều ngang
        for fl in sorted({g["Tang"] for g in self.groups}):
            cv.create_text(GAP, y + 10, text=f"Tầng {fl}", anchor="w", font=self.f_head, fill=NAVY)
            y += 32
            rooms = [g for g in self.groups if g["Tang"] == fl]
            for i in range(0, len(rooms), per):
                line = rooms[i:i + per]
                h = max(self._tile_h(g) for g in line)
                for k, g in enumerate(line):
                    self._tile(g, GAP + k * (self._tw + GAP), y, h)
                y += h + GAP
            y += 4
        self._total = y
        cv.configure(scrollregion=(0, 0, w, y))

    def _tile(self, g, x, y, h):
        cv, items, tw = self.cv, g["Issues"], self._tw
        open_ = [i for i in items if i["TrangThai"] != "Đã xong"]
        if any(i["MucDo"] == "Khẩn cấp" for i in open_):
            border, pill, (pfg, pbg) = "#F1B5B5", f"{len(open_)} sự cố", LEVELS["Khẩn cấp"]
        elif open_:
            border, pill, (pfg, pbg) = "#F5D9A8", f"{len(open_)} sự cố", STATES["Chờ xử lý"]
        else:
            border, pill, (pfg, pbg) = "#BFE3CB", ("Ổn định" if not items else "Đã sửa xong"), STATES["Đã xong"]
        rounded_rect(cv, x, y, x + tw, y + h, 12, fill="#FAFCFF", outline=border)
        cv.create_text(x + 16, y + 22, text=g["TenPhong"], anchor="w", font=self.f_title, fill=NAVY)
        bw = self.f_bold.measure(pill) + 22
        rounded_rect(cv, x + tw - 14 - bw, y + 10, x + tw - 14, y + 34, 12, fill=pbg, outline=pbg)
        cv.create_text(x + tw - 14 - bw / 2, y + 22, text=pill, font=self.f_bold, fill=pfg)
        pt = g.get("PhuTrach")
        glyph(cv, "user", x + 16, y + 36, MUTED if pt else "#B0B8C8", w=1.3, sc=0.75)
        cv.create_text(x + 32, y + 43, anchor="w", font=self.f_small, fill=MUTED if pt else "#B0B8C8",
                       text=fit(f"Phụ trách: {pt}" if pt else "Chưa phân công", tw - 48, self.f_small))
        cv.create_line(x + 14, y + 58, x + tw - 14, y + 58, fill=LINE)
        if not items:
            cy = y + 62 + (ROW - 2) / 2
            cv.create_oval(x + 17, cy - 11, x + 39, cy + 11, fill="#E4F6EA", outline="#E4F6EA")
            glyph(cv, "check", x + 22, cy - 6, GREEN_FG, w=1.6, sc=0.75)
            cv.create_text(x + 48, cy, text="Không có sự cố", anchor="w", font=self.f_norm, fill=GREEN_FG)
            return
        for k, it in enumerate(items):
            ry = y + 62 + k * ROW
            if it["MaSC"] == self.selected:
                rounded_rect(cv, x + 8, ry, x + tw - 8, ry + ROW - 2, 8, fill=SEL_BG, outline=PRIMARY)
            cy = ry + (ROW - 2) / 2
            icon_dot(cv, it["HangMuc"], x + 28, cy, 11)
            label = it["HangMuc"]
            cv.create_text(x + 46, cy, text=label, anchor="w", font=self.f_bold,
                           fill=MUTED if it["TrangThai"] == "Đã xong" else NAVY)
            rest_x = x + 46 + self.f_bold.measure(label) + 6
            cv.create_text(rest_x, cy, anchor="w", font=self.f_norm, fill=MUTED,
                           text=fit(it["MoTa"] or "", x + tw - 34 - rest_x, self.f_norm))
            cv.create_oval(x + tw - 24, cy - 4, x + tw - 16, cy + 4, fill=DOT[it["TrangThai"]],
                           outline=DOT[it["TrangThai"]])
            self._hit.append((x + 8, ry, x + tw - 8, ry + ROW - 2, it["MaSC"]))

    def _issue_at(self, e):
        cy = self.cv.canvasy(e.y)
        return next((h[4] for h in self._hit if h[0] <= e.x <= h[2] and h[1] <= cy <= h[3]), None)

    def _click(self, e):
        ma = self._issue_at(e)
        if ma is not None:
            self.select(ma)

    def _double(self, e):
        ma = self._issue_at(e)
        if ma is not None:
            self.select(ma)
            self.on_open()

    def _wheel(self, e):
        step = -1 if (getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0) else 1
        self.cv.yview_scroll(step * 2, "units")

    def _on_scroll(self, first, last):
        self.sb.set(first, last)
        if float(first) > 0 or float(last) < 1:
            self.sb.grid(row=0, column=1, sticky="ns")
        else:
            self.sb.grid_remove()


# ---------------------------------------------------------------------- hộp thoại chi tiết sự cố
def pill(cv, x_right, cy, text, fg, bg, font):
    bw = font.measure(text) + 24
    rounded_rect(cv, x_right - bw, cy - 12, x_right, cy + 12, 12, fill=bg, outline=bg)
    cv.create_text(x_right - bw / 2, cy, text=text, font=font, fill=fg)


def draw_detail(cv, it, w=640, h=392):
    """Vẽ phiếu chi tiết: hạng mục, mô tả, người phụ trách / người báo và đường tiến độ 3 bước."""
    def F(size, bold=False):
        return tkfont.Font(family=FONT, size=size, weight="bold" if bold else "normal")
    f15, f10b, f10, f9b, f9, f8 = F(15, True), F(10, True), F(10), F(9, True), F(9), F(8)
    rounded_rect(cv, 1, 1, w - 1, h - 1, 14, fill="white", outline=BORDER)
    icon_dot(cv, it["HangMuc"], 46, 48, 22)
    cv.create_text(82, 40, text=f"{it['HangMuc']} · phòng {it['TenPhong']}", anchor="w", font=f15, fill=NAVY)
    cv.create_text(82, 62, text=f"Phiếu #{it['MaSC']} · mức độ {it['MucDo'].lower()}", anchor="w", font=f9, fill=MUTED)
    pill(cv, w - 24, 48, it["TrangThai"], *STATES[it["TrangThai"]], f9b)
    # mô tả
    rounded_rect(cv, 24, 88, w - 24, 154, 10, fill="#F7F9FE", outline=LINE)
    cv.create_text(40, 102, text="Mô tả sự cố", anchor="w", font=f8, fill=MUTED)
    for k, line in enumerate(wrap(it["MoTa"] or "(không có mô tả)", w - 80, f10, 2)):
        cv.create_text(40, 122 + k * 18, text=line, anchor="w", font=f10, fill=TEXT)
    # người phụ trách / người báo
    mid = w / 2
    for x1, x2, label, name in ((24, mid - 8, "Phụ trách phòng", it.get("PhuTrach")),
                                (mid + 8, w - 24, "Người báo", it.get("Bao"))):
        rounded_rect(cv, x1, 168, x2, 232, 10, fill="#FAFCFF", outline=LINE)
        cv.create_oval(x1 + 14, 182, x1 + 50, 218, fill=NAVY if name else "#D5DBE6", outline="")
        cv.create_text(x1 + 32, 200, text=initials(name) if name else "?", font=f10b, fill="white")
        cv.create_text(x1 + 62, 189, text=label, anchor="w", font=f8, fill=MUTED)
        cv.create_text(x1 + 62, 210, text=fit(name or "Chưa có", x2 - x1 - 76, f10b), anchor="w", font=f10b,
                       fill=NAVY if name else "#A0AABB")
    # đường tiến độ
    cv.create_text(24, 254, text="Tiến độ", anchor="w", font=f9b, fill=MUTED)
    done = it["TrangThai"] == "Đã xong"
    started = bool(it["NgayNhan"]) or it["TrangThai"] in ("Đang sửa", "Đã xong")
    nodes = [("Gửi yêu cầu", it["NgayBao"], f"bởi {it['Bao']}" if it.get("Bao") else "", True, DOT["Chờ xử lý"]),
             ("Nhận sửa", it["NgayNhan"] or ("—" if not started else "đã nhận"),
              f"Xử lý: {it['NguoiXuLy']}" if it["NguoiXuLy"] else "", started, DOT["Đang sửa"]),
             ("Hoàn thành", it["NgayXong"] or "—", f"Chi phí {money(it['ChiPhi'])} đ" if it["ChiPhi"] else "",
              done, DOT["Đã xong"])]
    xs, cy = [w * 0.17, w * 0.5, w * 0.83], 296
    for k in range(2):
        cv.create_line(xs[k] + 18, cy, xs[k + 1] - 18, cy, width=3, fill=nodes[k + 1][4] if nodes[k + 1][3] else "#DDE3EE")
    for x, (title, date, sub, reached, color) in zip(xs, nodes):
        cv.create_oval(x - 15, cy - 15, x + 15, cy + 15, fill=color if reached else "white",
                       outline=color if reached else "#C9D3E6", width=2)
        if reached:
            glyph(cv, "check", x - 7, cy - 7, "white", w=2, sc=0.9)
        cv.create_text(x, cy + 32, text=title, font=f10b, fill=NAVY if reached else MUTED)
        cv.create_text(x, cy + 51, text=date, font=f10, fill=TEXT if reached else "#A0AABB")
        if sub:
            cv.create_text(x, cy + 69, text=fit(sub, 170, f9), font=f9, fill=MUTED)


class IssueDetail(tk.Toplevel):
    """Cửa sổ chi tiết sự cố; `result` = 'edit' | 'start' | 'done' | None để trang gọi tiếp thao tác tương ứng."""
    W, H = 640, 392

    def __init__(self, master, it):
        super().__init__(master)
        self.title(f"Chi tiết sự cố #{it['MaSC']}")
        self.configure(bg=PAGE_BG)
        self.resizable(False, False)
        self.result = None
        cv = tk.Canvas(self, width=self.W, height=self.H, bg=PAGE_BG, highlightthickness=0)
        cv.pack(padx=18, pady=(18, 10))
        draw_detail(cv, it, self.W, self.H)
        bar = tk.Frame(self, bg=PAGE_BG)
        bar.pack(fill="x", padx=18, pady=(0, 18))
        ActionButton(bar, "Đóng", "", self.destroy, "outline").pack(side="right")
        if it["TrangThai"] != "Đã xong":
            ActionButton(bar, "Hoàn thành", "check", lambda: self._go("done"), "success").pack(side="left", padx=(0, 10))
        if it["TrangThai"] == "Chờ xử lý":
            ActionButton(bar, "Nhận sửa", "tool", lambda: self._go("start"), "outline").pack(side="left", padx=(0, 10))
        ActionButton(bar, "Sửa", "edit", lambda: self._go("edit"), "outline").pack(side="left")
        self.bind("<Escape>", lambda _e: self.destroy())

    def _go(self, what):
        self.result = what
        self.destroy()


# ---------------------------------------------------------------------- màn hình
class DichVuScreen(tk.Frame):
    def __init__(self, master, user=None):
        super().__init__(master, bg=PAGE_BG)
        ensure_table()
        self.user = user
        self.tab, self.filter, self.cat = "issues", FILTERS[0], ALL_CATS
        self.ffilter, self.svc, self.month = FEE_FILTERS[0], ALL_SVC, this_month()
        self.sel = self.fsel = self.psel = None     # sự cố / phiếu thu / dịch vụ đang chọn
        self.issues, self.rooms, self.fees, self.prices, self.shown, self.fshown = [], [], [], [], [], []
        self.counts = {n: 0 for n in FILTERS}
        self.fcounts = {n: 0 for n in FEE_FILTERS}
        self._frac, self._bar_color, self._cards, self._n_req = 0, "#E58A12", [], 0
        self.kw = tk.StringVar(master=self)         # main.goto() điền sẵn ô tìm kiếm qua biến này
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
        tk.Label(box, text="Dịch vụ & sửa chữa", bg=PAGE_BG, fg=NAVY, font=(FONT, 20, "bold")).pack(anchor="w")
        tk.Label(box, text="Theo dõi phòng nào đang hỏng gì, ai phụ trách, tiến độ sửa chữa và thu phí dịch vụ",
                 bg=PAGE_BG, fg=MUTED, font=(FONT, 10)).pack(anchor="w")
        SearchBox(head, self.kw, "Tìm theo phòng, hạng mục, người phụ trách...").pack(side="right", anchor="n")

        self.stats = tk.Frame(self, bg=PAGE_BG)
        self.stats.pack(fill="x", pady=(16, 0), **pad)
        for i in range(4):
            self.stats.columnconfigure(i, weight=1, uniform="s")
        self.stat_titles, self.stat_vals = [], []
        for i in range(4):
            t, v = self._stat(i, bar=(i == 0))
            self.stat_titles.append(t)
            self.stat_vals.append(v)

        self.banner = tk.Frame(self, bg="#FFF7E6", highlightthickness=1, highlightbackground="#F5D9A8")
        self.banner_l = tk.Label(self.banner, bg="#FFF7E6", fg="#8A5A00", font=(FONT, 10, "bold"))
        self.banner_l.pack(side="left", padx=14, pady=9)
        link = tk.Label(self.banner, text="Xem & tạo phiếu  →", bg="#FFF7E6", fg=PRIMARY, font=(FONT, 10, "bold"),
                        cursor="hand2")
        link.pack(side="right", padx=14)
        link.bind("<Button-1>", lambda _e: self.on_requests())

        self.bar_row = tk.Frame(self, bg=PAGE_BG)
        self.bar_row.pack(fill="x", pady=(16, 0), **pad)
        handlers = {"add": self.on_add, "edit": self.on_edit, "del": self.on_delete, "start": self.on_start,
                    "done": self.on_done, "assign": self.on_assign}
        self.btn = {k: ActionButton(self.bar_row, k, "", handlers[k], enabled=(k in ("add", "assign")))
                    for k in handlers}
        self._btn_order = []

        self.chips_row = tk.Frame(self, bg=PAGE_BG)
        self.chips_row.pack(fill="x", pady=(14, 14), **pad)
        self.chips = {n: Chip(self.chips_row, lambda n=n: self.set_filter(n)) for n in FILTERS}
        self.fchips = {n: Chip(self.chips_row, lambda n=n: self.set_ffilter(n)) for n in FEE_FILTERS}
        self.cat_var = tk.StringVar(master=self, value=ALL_CATS)
        self.svc_var = tk.StringVar(master=self, value=ALL_SVC)
        self.month_var = tk.StringVar(master=self, value=month_label(self.month))
        self.cb_cat = self._combo(self.cat_var, [ALL_CATS] + list(CATS), self.set_cat, 16)
        self.cb_svc = self._combo(self.svc_var, [ALL_SVC], self.set_svc, 16)
        self.cb_month = self._combo(self.month_var, [ALL_MONTHS], self.set_month, 12)
        self._filter_ui = {"chips": [], "combos": []}

        self.card = Card(self)
        self.card.pack(fill="both", expand=True, padx=40, pady=(0, 30))
        inner = self.card.inner
        tabs = tk.Frame(inner, bg="white")
        tabs.pack(side="top", fill="x")
        self.tab_lbl = {}
        for key, text in TABS:
            cell = tk.Frame(tabs, bg="white")
            cell.pack(side="left", padx=(14, 0))
            lbl = tk.Label(cell, text=text, bg="white", font=(FONT, 10, "bold"), cursor="hand2")
            lbl.pack(padx=6, pady=(12, 8))
            line = tk.Frame(cell, bg="white", height=3)
            line.pack(fill="x")
            lbl.bind("<Button-1>", lambda _e, k=key: self.set_tab(k))
            self.tab_lbl[key] = (lbl, line)
        tk.Frame(inner, bg=LINE, height=1).pack(side="top", fill="x")
        foot = tk.Frame(inner, bg="white")
        foot.pack(side="bottom", fill="x")
        tk.Frame(foot, bg=LINE, height=1).pack(fill="x")
        row = tk.Frame(foot, bg="white")
        row.pack(fill="x", padx=16, pady=10)
        self.foot_l = tk.Label(row, bg="white", fg=MUTED, font=(FONT, 9))
        self.foot_l.pack(side="left")
        self.foot_r = tk.Label(row, bg="white", fg=MUTED, font=(FONT, 9))
        self.foot_r.pack(side="right")
        self.views = {"issues": IssueTable(inner, self._on_pick, self.on_detail),
                      "rooms": RoomIssueMap(inner, self._on_pick, self.on_detail),
                      "fees": FeeTable(inner, self._on_pick_fee, self.on_edit),
                      "price": PriceTable(inner, self._on_pick_price, self.on_edit)}
        self.views[self.tab].pack(fill="both", expand=True)
        self._style_tabs()
        self._layout_tab()

    def _combo(self, var, values, handler, width):
        cb = ttk.Combobox(self.chips_row, textvariable=var, state="readonly", width=width, values=values,
                          font=(FONT, 10))
        cb.bind("<<ComboboxSelected>>", lambda _e: handler(var.get()))
        return cb

    def _stat(self, col, bar=False):
        c = Card(self.stats)
        c.config(height=108)
        c.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 16, 0))
        title = tk.Label(c.inner, text="", bg="white", fg=MUTED, font=(FONT, 10, "bold"))
        title.pack(anchor="w", padx=18, pady=(14, 0))
        val = tk.Label(c.inner, text="0", bg="white", fg=NAVY, font=(FONT, 24, "bold"))
        val.pack(anchor="w", padx=18)
        if bar:
            self.bar = tk.Canvas(c.inner, height=8, bg="white", highlightthickness=0)
            self.bar.pack(fill="x", padx=18)
            self.bar.bind("<Configure>", lambda _e: self._paint_bar())
        return title, val

    def _paint_bar(self):
        cv, w = self.bar, max(self.bar.winfo_width(), 1)
        cv.delete("all")
        rounded_rect(cv, 0, 1, w, 7, 3, fill=TRACK, outline=TRACK)
        if self._frac > 0:
            rounded_rect(cv, 0, 1, max(6, w * self._frac), 7, 3, fill=self._bar_color, outline=self._bar_color)

    def _style_tabs(self):
        for key, (lbl, line) in self.tab_lbl.items():
            on = key == self.tab
            lbl.config(fg=PRIMARY if on else MUTED)
            line.config(bg=PRIMARY if on else "white")

    def _layout_tab(self):
        """Hàng nút và hàng bộ lọc thay đổi theo tab."""
        for b in self.btn.values():
            b.pack_forget()
        self._btn_order = []
        for key, text, icon, kind in BUTTONS[self.tab]:
            self.btn[key].restyle(text, icon, kind)
            self.btn[key].pack(side="left", padx=(0, 10))
            self._btn_order.append(self.btn[key])
        for w in list(self.chips.values()) + list(self.fchips.values()) + [self.cb_cat, self.cb_svc, self.cb_month]:
            w.pack_forget()
        if self.tab == "fees":
            chips, combos = list(self.fchips.values()), [self.cb_svc, self.cb_month]
        elif self.tab == "price":
            chips, combos = [], []
        else:
            chips, combos = list(self.chips.values()), [self.cb_cat]
        for c in chips:
            c.pack(side="left", padx=(0, 10))
        for c in combos:
            c.pack(side="left", ipady=7, padx=(0, 10))
        self._filter_ui = {"chips": chips, "combos": [(c, v) for c, v in
                                                       ((self.cb_cat, self.cat_var), (self.cb_svc, self.svc_var),
                                                        (self.cb_month, self.month_var)) if c in combos]}
        if self.tab == "price":
            self.chips_row.pack_forget()
        else:
            self.chips_row.pack(fill="x", padx=40, pady=(14, 14), before=self.card)
        self._place_banner()

    # ---- dữ liệu / bộ lọc
    def refresh(self):
        self.issues, self.rooms = load_issues(), load_rooms()
        self.fees, self.prices = load_fees(), price_rows()
        s = stats(self.issues, self.rooms)
        self.counts = {FILTERS[0]: s["cho"] + s["dang"], FILTERS[1]: s["cho"], FILTERS[2]: s["dang"],
                       FILTERS[3]: sum(1 for i in self.issues if i["TrangThai"] == "Đã xong")}
        months = sorted({f["Thang"] for f in self.fees} | {this_month()}, reverse=True)
        self.cb_month.config(values=[ALL_MONTHS] + [month_label(m) for m in months])
        self.cb_svc.config(values=[ALL_SVC] + [r["TenDV"] for r in fee_services()])
        self._n_req = len(pending_requests())
        self.banner_l.config(text=f"Có {self._n_req} yêu cầu sửa chữa mới từ sinh viên chưa tạo phiếu.")
        self._place_banner()
        self.apply()

    def _place_banner(self):
        """Dải thông báo yêu cầu của sinh viên chỉ hiện ở hai tab sự cố."""
        if self._n_req and self.tab in ("issues", "rooms"):
            self.banner.pack(fill="x", padx=40, pady=(14, 0), after=self.stats)
        else:
            self.banner.pack_forget()

    def set_tab(self, key):
        if key == self.tab:
            return
        self.views[self.tab].pack_forget()
        self.tab = key
        self.views[key].pack(fill="both", expand=True)
        self._style_tabs()
        self._layout_tab()
        self.apply()

    def set_filter(self, name):
        if name in FILTERS:
            self.filter = name
            self.apply()

    def set_ffilter(self, name):
        if name in FEE_FILTERS:
            self.ffilter = name
            self.apply()

    def set_cat(self, name):
        self.cat = name
        self.apply()

    def set_svc(self, name):
        self.svc = name
        self.apply()

    def set_month(self, label):
        self.month = None if label == ALL_MONTHS else label_month(label)
        self.apply()

    def _fee_scope(self, f):
        return (self.month is None or f["Thang"] == self.month) and (self.svc == ALL_SVC or f["TenDV"] == self.svc)

    def apply(self):
        kw = fold(self.kw.get().strip())
        f, cat = self.filter, self.cat
        self.shown = [i for i in self.issues
                      if ((i["TrangThai"] != "Đã xong") if f == FILTERS[0] else i["TrangThai"] == f)
                      and (cat == ALL_CATS or i["HangMuc"] == cat) and (not kw or kw in i["_hay"])]
        by = {}
        for i in self.shown:
            by.setdefault(i["MaPhong"], []).append(i)
        groups = []
        for r in self.rooms:        # phòng ổn định chỉ hiện ở bộ lọc "Cần xử lý" (để thấy toàn cảnh)
            items = by.get(r["MaPhong"], [])
            healthy_ok = f == FILTERS[0] and cat == ALL_CATS and (
                not kw or kw in fold(f"{r['TenPhong']} {r['PhuTrach'] or ''}"))
            if items or healthy_ok:
                groups.append(dict(r, Issues=items))
        base = [x for x in self.fees if self._fee_scope(x) and (not kw or kw in x["_hay"])]
        self.fcounts = {FEE_FILTERS[0]: len(base), FEE_FILTERS[1]: sum(1 for x in base if x["TrangThai"] == "Chưa thu"),
                        FEE_FILTERS[2]: sum(1 for x in base if x["TrangThai"] == "Đã thu")}
        self.fshown = [x for x in base if self.ffilter == FEE_FILTERS[0] or x["TrangThai"] == self.ffilter]
        prices = [p for p in self.prices if not kw or kw in fold(p["TenDV"])]
        for name, chip in self.chips.items():
            chip.set(f"{name} ({self.counts[name]})", name == self.filter)
        for name, chip in self.fchips.items():
            chip.set(f"{name} ({self.fcounts[name]})", name == self.ffilter)
        for w, data, sel in ((self.views["issues"], self.shown, self.sel), (self.views["rooms"], groups, self.sel),
                             (self.views["fees"], self.fshown, self.fsel), (self.views["price"], prices, self.psel)):
            w.selected = sel
            w.load(data)
        if self.tab == "issues":
            self.foot_l.config(text=f"Hiển thị {len(self.shown)} / {len(self.issues)} sự cố")
        elif self.tab == "rooms":
            bad = sum(1 for g in groups if g["Issues"])
            self.foot_l.config(text=f"Hiển thị {len(groups)} phòng · {bad} phòng có sự cố")
        elif self.tab == "fees":
            self.foot_l.config(text=f"Hiển thị {len(self.fshown)} / {len(self.fees)} phiếu thu · "
                                    f"tổng {money(sum(x['ThanhTien'] for x in self.fshown))} đ")
        else:
            self.foot_l.config(text=f"Hiển thị {len(prices)} / {len(self.prices)} dịch vụ")
        self.foot_r.config(text=HINTS[self.tab])
        self._update_stats()
        self._sync_buttons()

    def _update_stats(self):
        if self.tab == "fees":
            s = fee_stats([x for x in self.fees if self._fee_scope(x)])
            self._cards = [("Phiếu đã thu", f"{s['n_paid']} / {s['n']}", NAVY), ("Phải thu (đ)", money(s["total"]), NAVY),
                           ("Đã thu (đ)", money(s["paid"]), GREEN_FG), ("Còn thiếu (đ)", money(s["due"]), DANGER)]
            self._frac, self._bar_color = (s["n_paid"] / s["n"] if s["n"] else 0), BAR_OK
        else:
            s = stats(self.issues, self.rooms)
            self._cards = [("Phòng cần sửa", f"{s['rooms_bad']} / {s['rooms']}", NAVY),
                           ("Chờ xử lý", str(s["cho"]), "#8A5A00"), ("Đang sửa", str(s["dang"]), "#1D4F9F"),
                           ("Khẩn cấp", str(s["gap"]), DANGER)]
            self._frac, self._bar_color = (s["rooms_bad"] / s["rooms"] if s["rooms"] else 0), "#E58A12"
        for (t, v, c), tl, vl in zip(self._cards, self.stat_titles, self.stat_vals):
            tl.config(text=t)
            vl.config(text=v, fg=c)
        self._paint_bar()

    def _on_pick(self, ma):
        self.sel = ma
        self._sync_buttons()

    def _on_pick_fee(self, ma):
        self.fsel = ma
        self._sync_buttons()

    def _on_pick_price(self, ma):
        self.psel = ma
        self._sync_buttons()

    def _issue(self, ma=None):
        ma = self.sel if ma is None else ma
        return next((i for i in self.issues if i["MaSC"] == ma), None)

    def _fee(self):
        return next((x for x in self.fees if x["MaPhi"] == self.fsel), None)

    def _me(self):
        try:
            return self.user["HoTen"] or ""
        except (TypeError, KeyError, IndexError):
            return ""

    def _sync_buttons(self):
        b = self.btn
        if self.tab == "price":
            has, start, done = self.psel is not None, False, False
        elif self.tab == "fees":
            f = self._fee()
            has, start, done = f is not None, bool(f and f["TrangThai"] == "Chưa thu"), False
        else:
            it = self._issue()
            has = it is not None
            start, done = bool(it and it["TrangThai"] == "Chờ xử lý"), bool(it and it["TrangThai"] != "Đã xong")
        b["edit"].set_enabled(has)
        b["del"].set_enabled(has)
        b["start"].set_enabled(start)
        b["done"].set_enabled(done)
        b["add"].set_enabled(True)
        b["assign"].set_enabled(True)

    # ---- sự cố: thêm / sửa / xóa
    def _room_opts(self):
        return [f"{r['MaPhong']} - {r['TenPhong']}" for r in self.rooms]

    def _issue_fields(self, full=False):
        f = [F("Phong", "Phòng", "combo", self._room_opts(), required=True),
             F("HangMuc", "Hạng mục", "combo", list(CATS), required=True),
             F("MoTa", "Mô tả sự cố", ph="Ví dụ: quạt trần kêu to, mất điện ổ cắm...", required=True, span=2),
             F("MucDo", "Mức độ", "combo", list(LEVELS)), F("NgayBao", "Ngày gửi yêu cầu", ph="dd/mm/yyyy")]
        if full:
            f += [F("TrangThai", "Trạng thái", "combo", list(STATES)), F("NguoiXuLy", "Người xử lý"),
                  F("NgayNhan", "Ngày sửa", ph="dd/mm/yyyy"), F("NgayXong", "Ngày hoàn thành", ph="dd/mm/yyyy"),
                  F("ChiPhi", "Chi phí (đ)", ph="0")]
        return f

    @staticmethod
    def _sync_request(it, status):
        """Giữ trạng thái yêu cầu gốc của sinh viên khớp với tiến độ phiếu sửa chữa."""
        if it and it["MaYC"]:
            db.execute("UPDATE YeuCau SET TrangThai=? WHERE MaYC=? AND TrangThai<>'Từ chối'",
                       ("Đã xử lý" if status == "Đã xong" else "Đang xử lý", it["MaYC"]))

    def _add_issue(self, prefill=None, ma_yc=None, nguoi_bao=None):
        if not self.rooms:
            error("Chưa có phòng nào để báo sự cố.")
            return None
        init = {"NgayBao": today(), "MucDo": "Bình thường"}
        init.update(prefill or {})
        d = form_modal(self, "Báo sự cố / hư hỏng", self._issue_fields(), init, validate_issue, width=600)
        if not d:
            return None
        bao = nguoi_bao or (f"{self._me()} (BQL)" if self._me() else "Ban quản lý")
        new_id = db.execute("INSERT INTO SuaChua(MaPhong,HangMuc,MoTa,MucDo,NgayBao,NguoiBao,MaYC) VALUES(?,?,?,?,?,?,?)",
                            (pick_id(d["Phong"]), d["HangMuc"], d["MoTa"], d["MucDo"], d["NgayBao"] or today(), bao,
                             ma_yc))
        if ma_yc:
            db.execute("UPDATE YeuCau SET TrangThai='Đang xử lý' WHERE MaYC=?", (ma_yc,))
        db.ghi_nhat_ky("phong", f"Báo sự cố **{d['HangMuc'].lower()}** phòng {d['Phong'].split(' - ', 1)[-1]}")
        self.filter, self.cat = FILTERS[0], ALL_CATS
        self.cat_var.set(ALL_CATS)
        self.kw.set("")
        self.refresh()
        return new_id

    def on_add(self):
        if self.tab == "price":
            return self._price_add()
        if self.tab == "fees":
            return self._fee_generate()
        new_id = self._add_issue()
        if new_id:
            self.views[self.tab].select(new_id, scroll=True)

    def on_edit(self):
        if self.tab == "price":
            return self._price_edit()
        if self.tab == "fees":
            return self._fee_edit()
        it = self._issue()
        if not it:
            return
        cur = {"Phong": f"{it['MaPhong']} - {it['TenPhong']}", "HangMuc": it["HangMuc"], "MoTa": it["MoTa"],
               "MucDo": it["MucDo"], "NgayBao": it["NgayBao"], "TrangThai": it["TrangThai"],
               "NguoiXuLy": it["NguoiXuLy"], "NgayNhan": it["NgayNhan"], "NgayXong": it["NgayXong"],
               "ChiPhi": it["ChiPhi"]}
        d = form_modal(self, "Cập nhật sự cố", self._issue_fields(full=True), cur, validate_issue, width=600)
        if not d:
            return
        xong = (d["NgayXong"] or today()) if d["TrangThai"] == "Đã xong" else None
        nhan = d["NgayNhan"] or (today() if d["TrangThai"] in ("Đang sửa", "Đã xong") else None)
        db.execute("UPDATE SuaChua SET MaPhong=?,HangMuc=?,MoTa=?,MucDo=?,NgayBao=?,TrangThai=?,NguoiXuLy=?,"
                   "NgayNhan=?,NgayXong=?,ChiPhi=? WHERE MaSC=?",
                   (pick_id(d["Phong"]), d["HangMuc"], d["MoTa"], d["MucDo"], d["NgayBao"] or it["NgayBao"],
                    d["TrangThai"], d["NguoiXuLy"] or None, nhan, xong, int(d["ChiPhi"] or 0), it["MaSC"]))
        self._sync_request(it, d["TrangThai"])
        self.refresh()

    def on_delete(self):
        if self.tab == "price":
            return self._price_delete()
        if self.tab == "fees":
            return self._fee_delete()
        it = self._issue()
        if not it:
            return
        if not messagebox.askyesno("Xác nhận", f"Xóa sự cố {it['HangMuc'].lower()} của phòng {it['TenPhong']}?"):
            return
        db.execute("DELETE FROM SuaChua WHERE MaSC=?", (it["MaSC"],))
        if it["MaYC"]:          # trả yêu cầu về hàng chờ để không bị mất
            db.execute("UPDATE YeuCau SET TrangThai='Chờ xử lý' WHERE MaYC=? AND TrangThai='Đang xử lý'", (it["MaYC"],))
        self.sel = None
        self.refresh()

    def on_start(self):
        if self.tab == "fees":
            return self._fee_collect()
        it = self._issue()
        if not it or it["TrangThai"] != "Chờ xử lý":
            return
        d = form_modal(self, "Nhận sửa", [F("NguoiXuLy", "Người xử lý"), F("NgayNhan", "Ngày sửa", ph="dd/mm/yyyy")],
                       {"NguoiXuLy": it["NguoiXuLy"] or self._me(), "NgayNhan": today()}, validate_start, width=520)
        if not d:
            return
        db.execute("UPDATE SuaChua SET TrangThai='Đang sửa', NguoiXuLy=?, NgayNhan=? WHERE MaSC=?",
                   (d["NguoiXuLy"] or None, d["NgayNhan"] or today(), it["MaSC"]))
        self._sync_request(it, "Đang sửa")
        self.refresh()

    def on_done(self):
        it = self._issue()
        if not it or it["TrangThai"] == "Đã xong":
            return
        d = form_modal(self, "Hoàn thành sửa chữa",
                       [F("NguoiXuLy", "Người xử lý"), F("NgayXong", "Ngày hoàn thành", ph="dd/mm/yyyy"),
                        F("ChiPhi", "Chi phí (đ)", ph="0")],
                       {"NguoiXuLy": it["NguoiXuLy"] or self._me(), "NgayXong": today(), "ChiPhi": it["ChiPhi"] or 0},
                       validate_done, width=520)
        if not d:
            return
        db.execute("UPDATE SuaChua SET TrangThai='Đã xong', NguoiXuLy=?, NgayXong=?, ChiPhi=?, "
                   "NgayNhan=COALESCE(NgayNhan, ?) WHERE MaSC=?",
                   (d["NguoiXuLy"] or None, d["NgayXong"] or today(), int(d["ChiPhi"] or 0),
                    d["NgayXong"] or today(), it["MaSC"]))
        self._sync_request(it, "Đã xong")
        db.ghi_nhat_ky("phong", f"Đã sửa xong **{it['HangMuc'].lower()}** phòng {it['TenPhong']}")
        self.refresh()

    def on_detail(self):
        it = self._issue()
        if not it:
            return
        dlg = IssueDetail(self, it)
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()
        dlg.wait_window()
        {"edit": self.on_edit, "start": self.on_start, "done": self.on_done}.get(dlg.result, lambda: None)()

    # ---- phân công người phụ trách phòng
    def on_assign(self):
        try:        # chỉ nhân viên đang hoạt động; hiện kèm chức vụ nếu trang Nhân viên đã có cột đó
            staff = db.query("SELECT MaNV, HoTen, ChucVu FROM NhanVien "
                             "WHERE COALESCE(TrangThai,'Đang hoạt động')='Đang hoạt động' ORDER BY MaNV")
        except sqlite3.OperationalError:
            staff = db.query("SELECT MaNV, HoTen, NULL AS ChucVu FROM NhanVien ORDER BY MaNV")
        if not self.rooms or not staff:
            return error("Chưa có phòng hoặc nhân viên để phân công.")
        opts = ["0 - (Bỏ phân công)"] + [f"{r['MaNV']} - {r['HoTen']}" + (f" ({r['ChucVu']})" if r["ChucVu"] else "")
                                         for r in staff]
        it = self._issue() if self.tab != "fees" else None
        fee = self._fee() if self.tab == "fees" else None
        ma = it["MaPhong"] if it else (fee["MaPhong"] if fee else self.rooms[0]["MaPhong"])
        room = next(r for r in self.rooms if r["MaPhong"] == ma)
        cur_nv = next((o for o in opts if room["MaNV"] and pick_id(o) == room["MaNV"]), opts[0])
        scope = ["Chỉ phòng này", "Cả tầng này"]
        d = form_modal(self, "Phân công người phụ trách phòng",
                       [F("Phong", "Phòng", "combo", self._room_opts(), span=2),
                        F("NV", "Người phụ trách", "combo", opts, span=2),
                        F("PhamVi", "Áp dụng cho", "combo", scope, span=2)],
                       {"Phong": f"{room['MaPhong']} - {room['TenPhong']}", "NV": cur_nv, "PhamVi": scope[0]},
                       width=520)
        if not d:
            return
        target = next(r for r in self.rooms if r["MaPhong"] == pick_id(d["Phong"]))
        rooms = [r for r in self.rooms if r["Tang"] == target["Tang"]] if d["PhamVi"] == scope[1] else [target]
        nv = pick_id(d["NV"])
        for r in rooms:
            if nv:
                db.execute("INSERT OR REPLACE INTO PhuTrachPhong(MaPhong,MaNV) VALUES(?,?)", (r["MaPhong"], nv))
            else:
                db.execute("DELETE FROM PhuTrachPhong WHERE MaPhong=?", (r["MaPhong"],))
        who = d["NV"].split(" - ", 1)[-1]
        db.ghi_nhat_ky("phong", f"Phân công **{who}** phụ trách {len(rooms)} phòng" if nv
                       else f"Bỏ phân công phụ trách {len(rooms)} phòng")
        self.refresh()

    # ---- thu phí dịch vụ (rác, wifi...)
    def _fee_generate(self):
        svcs = fee_services()
        if not svcs:
            return error("Chưa có dịch vụ nào để thu phí.\nHãy thêm ở tab \"Bảng giá dịch vụ\" (ví dụ: Thu gom rác, Wifi).")
        opts = [ALL_SVC] + [f"{r['MaDV']} - {r['TenDV']} ({money(r['DonGia'])}đ/{r['DonVi']})" for r in svcs]
        per = ["Số người đang ở", "Phòng"]
        d = form_modal(self, "Tạo phiếu thu phí dịch vụ",
                       [F("Thang", "Tháng", ph="YYYY-MM, ví dụ 2026-11", required=True), F("Tinh", "Tính theo", "combo", per),
                        F("DV", "Dịch vụ", "combo", opts, span=2)],
                       {"Thang": this_month(), "DV": opts[0], "Tinh": per[0]}, validate_fee_generate, width=560)
        if not d:
            return
        made, skipped = generate_fees(d["Thang"], None if d["DV"] == ALL_SVC else pick_id(d["DV"]),
                                      d["Tinh"] == per[0])
        if not made and not skipped:
            return messagebox.showinfo("Thông báo", "Không có phòng nào đang có người ở để lập phiếu thu.")
        msg = f"Đã tạo {made} phiếu thu tháng {month_label(d['Thang'])}."
        if skipped:
            msg += f"\nBỏ qua {skipped} phiếu đã có từ trước."
        db.ghi_nhat_ky("thu", f"Lập **{made}** phiếu thu phí dịch vụ tháng {month_label(d['Thang'])}")
        self.month, self.svc, self.ffilter = d["Thang"], ALL_SVC, FEE_FILTERS[0]
        self.month_var.set(month_label(d["Thang"]))
        self.svc_var.set(ALL_SVC)
        self.kw.set("")
        self.refresh()
        messagebox.showinfo("Hoàn tất", msg)

    def _fee_collect(self):
        f = self._fee()
        if not f or f["TrangThai"] == "Đã thu":
            return
        d = form_modal(self, f"Thu tiền - phòng {f['TenPhong']} ({f['TenDV']}, {f['ThangHT']})",
                       [F("HinhThuc", "Hình thức thu", "combo", PAY_METHODS), F("NgayThu", "Ngày thu", ph="dd/mm/yyyy")],
                       {"HinhThuc": PAY_METHODS[0], "NgayThu": today()}, validate_collect, width=520)
        if not d:
            return
        db.execute("UPDATE PhiDichVu SET TrangThai='Đã thu', NgayThu=?, HinhThuc=? WHERE MaPhi=?",
                   (d["NgayThu"] or today(), d["HinhThuc"], f["MaPhi"]))
        db.ghi_nhat_ky("thu", f"Thu phí **{f['TenDV']}** phòng {f['TenPhong']}: {f['Tien']}đ")
        self.refresh()

    def _fee_edit(self):
        f = self._fee()
        if not f:
            return
        d = form_modal(self, f"Sửa phiếu thu - phòng {f['TenPhong']}",
                       [F("SoLuong", f"Số lượng ({f['TinhTheo']})", required=True), F("DonGia", "Đơn giá (đ)", required=True),
                        F("TrangThai", "Trạng thái", "combo", list(FEE_STATES)),
                        F("HinhThuc", "Hình thức thu", "combo", PAY_METHODS),
                        F("NgayThu", "Ngày thu", ph="dd/mm/yyyy"), F("GhiChu", "Ghi chú", span=2)],
                       {"SoLuong": f["SoLuong"], "DonGia": f["DonGia"], "TrangThai": f["TrangThai"],
                        "HinhThuc": f["HinhThuc"] or PAY_METHODS[0], "NgayThu": f["NgayThu"], "GhiChu": f["GhiChu"]},
                       validate_fee_edit, width=600)
        if not d:
            return
        paid = d["TrangThai"] == "Đã thu"
        db.execute("UPDATE PhiDichVu SET SoLuong=?,DonGia=?,ThanhTien=?,TrangThai=?,NgayThu=?,HinhThuc=?,GhiChu=? "
                   "WHERE MaPhi=?",
                   (int(d["SoLuong"]), int(d["DonGia"]), int(d["SoLuong"]) * int(d["DonGia"]), d["TrangThai"],
                    (d["NgayThu"] or today()) if paid else None, d["HinhThuc"] if paid else None,
                    d["GhiChu"] or None, f["MaPhi"]))
        self.refresh()

    def _fee_delete(self):
        f = self._fee()
        if not f:
            return
        extra = "\n\nPhiếu này ĐÃ THU tiền, xóa sẽ mất lịch sử thu." if f["TrangThai"] == "Đã thu" else ""
        if not messagebox.askyesno("Xác nhận", f"Xóa phiếu thu {f['TenDV']} phòng {f['TenPhong']} ({f['ThangHT']})?{extra}"):
            return
        db.execute("DELETE FROM PhiDichVu WHERE MaPhi=?", (f["MaPhi"],))
        self.fsel = None
        self.refresh()

    # ---- yêu cầu sửa chữa từ sinh viên
    def on_requests(self):
        win = tk.Toplevel(self)
        win.title("Yêu cầu sửa chữa từ sinh viên")
        win.configure(bg=PAGE_BG)
        win.transient(self.winfo_toplevel())
        tk.Label(win, text="Yêu cầu sửa chữa chưa tạo phiếu", bg=PAGE_BG, fg=NAVY,
                 font=(FONT, 14, "bold")).pack(anchor="w", padx=18, pady=(16, 8))
        cols = [("MaYC", "Mã", 50), ("HoTen", "Sinh viên", 150), ("TenPhong", "Phòng", 70),
                ("NoiDung", "Nội dung", 300), ("NgayGui", "Ngày gửi", 90)]
        tv = ttk.Treeview(win, columns=[c[0] for c in cols], show="headings", selectmode="browse", height=8)
        for k, h, w in cols:
            tv.heading(k, text=h)
            tv.column(k, width=w, anchor="w")
        tv.pack(fill="both", expand=True, padx=18)

        def load():
            tv.delete(*tv.get_children())
            for r in pending_requests():
                tv.insert("", "end", iid=str(r["MaYC"]), values=[r[c[0]] or "—" for c in cols])

        def picked():
            sel = tv.selection()
            if not sel:
                messagebox.showwarning("Thông báo", "Vui lòng chọn một yêu cầu.", parent=win)
                return None
            return next(r for r in pending_requests() if r["MaYC"] == int(sel[0]))

        def make():
            r = picked()
            if not r:
                return
            pre = {"HangMuc": guess_cat(r["NoiDung"]), "MoTa": r["NoiDung"], "NgayBao": r["NgayGui"] or today()}
            if r["MaPhong"]:
                pre["Phong"] = f"{r['MaPhong']} - {r['TenPhong']}"
            self._add_issue(pre, ma_yc=r["MaYC"], nguoi_bao=r["HoTen"])
            load()

        def reject():
            r = picked()
            if r:
                db.execute("UPDATE YeuCau SET TrangThai='Từ chối' WHERE MaYC=?", (r["MaYC"],))
                db.ghi_nhat_ky("yeucau", f"Từ chối yêu cầu sửa chữa của **{r['HoTen']}**")
                load()
                self.refresh()

        bar = tk.Frame(win, bg=PAGE_BG)
        bar.pack(fill="x", padx=18, pady=12)
        FlatButton(bar, "Tạo phiếu sửa chữa", make, padx=14, pady=7).pack(side="left")
        FlatButton(bar, "Từ chối", reject, bg="white", hover=SEL_BG, fg="#B42318", padx=14, pady=7,
                   highlightthickness=1, highlightbackground=BORDER).pack(side="left", padx=8)
        FlatButton(bar, "Đóng", win.destroy, bg="white", hover=SEL_BG, fg=NAVY, padx=14, pady=7,
                   highlightthickness=1, highlightbackground=BORDER).pack(side="right")
        load()
        win.bind("<Escape>", lambda _e: win.destroy())
        win.grab_set()
        win.wait_window()
        self.refresh()

    # ---- bảng giá dịch vụ
    def _price_add(self):
        d = form_modal(self, "Thêm dịch vụ", PRICE_FIELDS, {"DonVi": "tháng"}, price_validator(), width=560)
        if not d:
            return
        new_id = db.execute("INSERT INTO DichVu(TenDV,DonGia,DonVi) VALUES(?,?,?)",
                            (d["TenDV"], int(d["DonGia"]), d["DonVi"]))
        self.kw.set("")
        self.refresh()
        self.views["price"].select(new_id, scroll=True)

    def _price_edit(self):
        cur = db.query("SELECT * FROM DichVu WHERE MaDV=?", (self.psel,), one=True)
        if not cur:
            return
        d = form_modal(self, "Sửa dịch vụ", PRICE_FIELDS, dict(cur), price_validator(self.psel), width=560)
        if not d:
            return
        db.execute("UPDATE DichVu SET TenDV=?,DonGia=?,DonVi=? WHERE MaDV=?",
                   (d["TenDV"], int(d["DonGia"]), d["DonVi"], self.psel))
        self.refresh()

    def _price_delete(self):
        cur = db.query("SELECT * FROM DichVu WHERE MaDV=?", (self.psel,), one=True)
        if not cur:
            return
        if cur["TenDV"] in ("Điện", "Nước"):
            return error(f"Dịch vụ \"{cur['TenDV']}\" được dùng để tính hóa đơn nên không thể xóa.\n"
                         "Bạn vẫn có thể sửa đơn giá.")
        if not messagebox.askyesno("Xác nhận", f"Xóa dịch vụ {cur['TenDV']}?"):
            return
        try:
            db.execute("DELETE FROM DichVu WHERE MaDV=?", (self.psel,))
        except sqlite3.IntegrityError:
            return error("Dịch vụ này đã có phiếu thu phí nên không thể xóa.\n"
                         "Bạn có thể sửa đơn giá hoặc xóa các phiếu thu trước.")
        self.psel = None
        self.refresh()


# ---------------------------------------------------------------------- kiểm tra dữ liệu cho form_modal
# validate(values) -> (data, loi); loi = (khóa ô, thông báo) để hộp thoại giữ nguyên nội dung và đưa con trỏ về đúng ô
LABELS = {"NgayBao": "Ngày gửi", "NgayNhan": "Ngày sửa", "NgayXong": "Ngày hoàn thành", "NgayThu": "Ngày thu",
          "ChiPhi": "Chi phí", "SoLuong": "Số lượng", "DonGia": "Đơn giá"}


def make_validator(required=None, dates=(), digits=()):
    def validate(v):
        for k, msg in (required or {}).items():
            if not v.get(k):
                return None, (k, msg)
        for k in dates:
            if v.get(k) and not valid_date(v[k]):
                return None, (k, f"{LABELS[k]} phải có dạng dd/mm/yyyy.")
        for k in digits:
            if v.get(k) and not str(v[k]).isdigit():
                return None, (k, f"{LABELS[k]} phải là số nguyên không âm.")
        return v, None
    return validate


validate_issue = make_validator({"MoTa": "Hãy mô tả sự cố (ví dụ: quạt trần kêu to, mất điện ổ cắm...)."},
                                dates=("NgayBao", "NgayNhan", "NgayXong"), digits=("ChiPhi",))
validate_start = make_validator(dates=("NgayNhan",))
validate_done = make_validator(dates=("NgayXong",), digits=("ChiPhi",))
validate_collect = make_validator(dates=("NgayThu",))
validate_fee_edit = make_validator({"SoLuong": "Hãy nhập số lượng.", "DonGia": "Hãy nhập đơn giá."},
                                   dates=("NgayThu",), digits=("SoLuong", "DonGia"))


def validate_fee_generate(v):
    try:
        datetime.strptime(v.get("Thang", ""), "%Y-%m")
    except ValueError:
        return None, ("Thang", "Tháng phải có dạng YYYY-MM, ví dụ 2026-11.")
    return v, None


def price_validator(cur_id=0):
    def validate(v):
        err = price_check(v)
        if err:
            return None, ("TenDV" if not v.get("TenDV") else "DonGia", err)
        if db.query("SELECT 1 FROM DichVu WHERE TenDV=? AND MaDV<>?", (v["TenDV"], cur_id or 0), one=True):
            return None, ("TenDV", "Tên dịch vụ đã tồn tại.")
        return v, None
    return validate