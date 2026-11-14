"""Trang Phòng (quản trị) - giao diện xanh trắng theo mẫu thiết kế.

- 4 thẻ thống kê: tổng số phòng, giường còn trống, tỷ lệ lấp đầy (có thanh tiến độ), phòng đang bảo trì
- Lọc nhanh theo tình trạng (Còn chỗ / Trống / Đầy / Bảo trì) + lọc theo tầng + tìm kiếm tức thì
- Hai kiểu xem: "Danh sách" (bảng) và "Sơ đồ giường" (từng phòng với từng giường, tên sinh viên đang ở)
- Thêm / Sửa / Xóa phòng, nút "Loại phòng" mở bảng quản lý loại phòng
"""
import sqlite3
import tkinter as tk
from math import ceil
from tkinter import messagebox, ttk
from tkinter import font as tkfont

import database as db
from screens.base import CrudScreen, error, form_dialog, money, pick_id
from screens.login import BORDER, FONT, MUTED, NAVY, PAGE_BG, PRIMARY, SEL_BG, TEXT, rounded_rect
from screens.modal import form_modal
from screens.sinhvien import (GREEN_FG, LINE, Card, Chip, DataTable, IconButton, SearchBox, fold)

STATUS_STYLE = {"Còn chỗ": ("#0E7A3B", "#E4F6EA"), "Trống": ("#1D4F9F", "#DCE9FB"),
                "Đầy": ("#B42318", "#FDE8E8"), "Bảo trì": ("#8A5A00", "#FFF0D0")}
FILTERS = ["Tất cả", "Còn chỗ", "Trống", "Đầy", "Bảo trì"]
ALL_FLOORS = "Tất cả các tầng"
TRACK, BAR_OK, BAR_FULL = "#D9E1F0", "#1E9E4A", "#C0392B"
MAINT_FG = STATUS_STYLE["Bảo trì"][0]

# cột bảng: (khóa, tiêu đề, rộng tối thiểu, tỉ lệ giãn)
ROOM_COLS = [("MaPhong", "Mã", 50, 0.4), ("TenPhong", "Tên phòng", 90, 0.9), ("TenLoai", "Loại phòng", 120, 1.3),
             ("Tang", "Tầng", 56, 0.4), ("SoGiuong", "Số giường", 76, 0.6), ("DangO", "Đang ở", 150, 1.3),
             ("Gia", "Giá/người/tháng", 120, 1.1), ("TinhTrang", "Trạng thái", 100, 0.9)]


# ---------------------------------------------------------------------- dữ liệu
def load_rooms():
    """Danh sách phòng + tên các sinh viên đang ở (Nguoi) + giá đã định dạng (Gia)."""
    people = {}
    for r in db.query("SELECT h.MaPhong, s.HoTen FROM HopDong h JOIN SinhVien s ON s.MaSV=h.MaSV "
                      "WHERE h.TrangThai='Đang thuê' ORDER BY h.MaHD"):
        people.setdefault(r["MaPhong"], []).append(r["HoTen"])
    out = []
    for p in db.danh_sach_phong():
        d = dict(p)
        d["Gia"] = money(d["GiaThue"])
        d["Nguoi"] = people.get(d["MaPhong"], [])
        d["_hay"] = fold(f"{d['TenPhong']} {d['TenLoai']}")
        out.append(d)
    return out


def stats(rooms):
    """Phòng bảo trì không tính vào sức chứa, nên giường trống / tỷ lệ chỉ tính trên phòng đang hoạt động."""
    act = [r for r in rooms if r["TrangThai"] != "Bảo trì"]
    cap = sum(r["SoGiuong"] for r in act)
    occ = sum(min(r["DangO"], r["SoGiuong"]) for r in act)
    return {"total": len(rooms), "free": cap - occ, "rate": round(occ * 100 / cap) if cap else 0,
            "maint": len(rooms) - len(act)}


def fit(text, maxw, font):
    text = str(text)
    if font.measure(text) <= maxw:
        return text
    while text and font.measure(text + "…") > maxw:
        text = text[:-1]
    return text + "…" if text else ""


# ---------------------------------------------------------------------- loại phòng (giữ nguyên)
class LoaiPhongScreen(CrudScreen):
    title = "Loại phòng"
    columns = [("MaLoai", "Mã", 50), ("TenLoai", "Tên loại", 200), ("SoGiuong", "Số giường", 90),
               ("GiaThue", "Giá thuê (đ/người/tháng)", 180)]
    FIELDS = [("TenLoai", "Tên loại phòng", "entry", None),
              ("SoGiuong", "Số giường", "entry", None),
              ("GiaThue", "Giá thuê (đ/người/tháng)", "entry", None)]

    def rows(self, kw):
        return [dict(r, GiaThue=money(r["GiaThue"])) for r in
                db.query("SELECT * FROM LoaiPhong WHERE TenLoai LIKE ? ORDER BY MaLoai", (f"%{kw}%",))]

    def _check(self, d):
        if not d["TenLoai"]:
            return "Tên loại không được để trống."
        if not (d["SoGiuong"].isdigit() and int(d["SoGiuong"]) > 0):
            return "Số giường phải là số nguyên dương."
        if not (d["GiaThue"].isdigit() and int(d["GiaThue"]) > 0):
            return "Giá thuê phải là số nguyên dương."

    def add(self):
        d = form_dialog(self, "Thêm loại phòng", self.FIELDS)
        if d:
            err = self._check(d)
            if err:
                return error(err)
            db.execute("INSERT INTO LoaiPhong(TenLoai,SoGiuong,GiaThue) VALUES(?,?,?)",
                       (d["TenLoai"], int(d["SoGiuong"]), int(d["GiaThue"])))

    def edit(self, id_):
        cur = dict(db.query("SELECT * FROM LoaiPhong WHERE MaLoai=?", (id_,), one=True))
        d = form_dialog(self, "Sửa loại phòng", self.FIELDS, cur)
        if d:
            err = self._check(d)
            if err:
                return error(err)
            db.execute("UPDATE LoaiPhong SET TenLoai=?,SoGiuong=?,GiaThue=? WHERE MaLoai=?",
                       (d["TenLoai"], int(d["SoGiuong"]), int(d["GiaThue"]), id_))

    def delete(self, id_):
        db.execute("DELETE FROM LoaiPhong WHERE MaLoai=?", (id_,))


# ---------------------------------------------------------------------- bảng danh sách
class RoomTable(DataTable):
    bold_keys, navy_keys = ("TenPhong",), ("TenPhong",)

    def __init__(self, master, on_select, on_open):
        super().__init__(master, on_select, on_open, ROOM_COLS, "MaPhong")

    def _draw_cell(self, key, r, tx, cy, maxw, tag):
        b = self.body
        if key == "TinhTrang":
            fg, fill = STATUS_STYLE[r["TinhTrang"]]
            self._badge(r["TinhTrang"], fg, fill, tx, cy, maxw, tag)
            return True
        if key == "DangO":                              # thanh tiến độ + "3/4"
            bw = max(24, min(72, maxw - 44))
            frac = min(r["DangO"] / r["SoGiuong"], 1) if r["SoGiuong"] else 0
            color = BAR_FULL if r["TinhTrang"] == "Đầy" else BAR_OK
            rounded_rect(b, tx, cy - 3, tx + bw, cy + 3, 3, fill=TRACK, outline=TRACK, tags=tag)
            if frac > 0:
                rounded_rect(b, tx, cy - 3, tx + max(6, bw * frac), cy + 3, 3, fill=color, outline=color, tags=tag)
            b.create_text(tx + bw + 10, cy, text=f"{r['DangO']}/{r['SoGiuong']}", anchor="w", font=self.f_bold,
                          fill=TEXT, tags=tag)
            return True
        return False


# ---------------------------------------------------------------------- sơ đồ giường
TILE_W, GAP, BED_W, BED_H = 264, 16, 116, 28


class BedMap(tk.Frame):
    """Sơ đồ giường: mỗi phòng là một ô, mỗi giường là một ô nhỏ (tên sinh viên hoặc 'Trống'), nhóm theo tầng."""

    def __init__(self, master, on_select, on_open):
        super().__init__(master, bg="white")
        self.on_select, self.on_open = on_select, on_open
        self.rooms, self.selected, self._hit, self._total = [], None, [], 1
        self.f_head = tkfont.Font(family=FONT, size=11, weight="bold")
        self.f_title = tkfont.Font(family=FONT, size=12, weight="bold")
        self.f_norm = tkfont.Font(family=FONT, size=9)
        self.f_bed = tkfont.Font(family=FONT, size=9, weight="bold")
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

    def load(self, rooms):
        self.rooms = rooms
        if self.selected is not None and all(r["MaPhong"] != self.selected for r in rooms):
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
                    self.cv.yview_moveto(max(0.0, (box[1] - GAP) / self._total))
        if old != ma:
            self.on_select(ma)

    @staticmethod
    def _tile_h(r):
        return 62 + ceil(max(r["SoGiuong"], 1) / 2) * (BED_H + 8) + 8

    def _draw(self):
        cv = self.cv
        cv.delete("all")
        self._hit = []
        w = max(cv.winfo_width(), 1)
        if not self.rooms:
            cv.create_text(w / 2, 70, text="Không có phòng nào phù hợp.", fill=MUTED, font=self.f_norm)
            self._total = 1
            cv.configure(scrollregion=(0, 0, w, 1))
            return
        per, y = max(1, (w - GAP) // (TILE_W + GAP)), GAP
        for fl in sorted({r["Tang"] for r in self.rooms}):
            cv.create_text(GAP, y + 10, text=f"Tầng {fl}", anchor="w", font=self.f_head, fill=NAVY)
            y += 32
            group = [r for r in self.rooms if r["Tang"] == fl]
            for i in range(0, len(group), per):
                line = group[i:i + per]
                h = max(self._tile_h(r) for r in line)
                for k, r in enumerate(line):
                    self._tile(r, GAP + k * (TILE_W + GAP), y, h)
                y += h + GAP
            y += 4
        self._total = y
        cv.configure(scrollregion=(0, 0, w, y))

    def _tile(self, r, x, y, h):
        cv, sel = self.cv, r["MaPhong"] == self.selected
        rounded_rect(cv, x, y, x + TILE_W, y + h, 12, fill=SEL_BG if sel else "#FAFCFF",
                     outline=PRIMARY if sel else BORDER, width=2 if sel else 1)
        cv.create_text(x + 16, y + 24, text=r["TenPhong"], anchor="w", font=self.f_title, fill=NAVY)
        fg, fill = STATUS_STYLE[r["TinhTrang"]]
        bw = self.f_bed.measure(r["TinhTrang"]) + 20
        rounded_rect(cv, x + TILE_W - 16 - bw, y + 12, x + TILE_W - 16, y + 36, 12, fill=fill, outline=fill)
        cv.create_text(x + TILE_W - 16 - bw / 2, y + 24, text=r["TinhTrang"], font=self.f_bed, fill=fg)
        cv.create_text(x + 16, y + 46, anchor="w", font=self.f_norm, fill=MUTED,
                       text=fit(f"{r['TenLoai']} · {r['Gia']} đ/tháng · {r['DangO']}/{r['SoGiuong']}",
                                TILE_W - 32, self.f_norm))
        maint = r["TrangThai"] == "Bảo trì"
        for i in range(r["SoGiuong"]):
            bx, by = x + 16 + (i % 2) * (BED_W + 8), y + 62 + (i // 2) * (BED_H + 8)
            if i < len(r["Nguoi"]):
                rounded_rect(cv, bx, by, bx + BED_W, by + BED_H, 8, fill="#DCE9FB", outline="#B9D0F5")
                cv.create_text(bx + 10, by + BED_H / 2, anchor="w", font=self.f_bed, fill=NAVY,
                               text=fit(r["Nguoi"][i], BED_W - 20, self.f_bed))
            else:
                rounded_rect(cv, bx, by, bx + BED_W, by + BED_H, 8, fill="#F1F3F7" if maint else "white",
                             outline="#D5DBE6" if maint else "#BFE3CB")
                cv.create_text(bx + 10, by + BED_H / 2, anchor="w", font=self.f_norm,
                               fill="#8A94A6" if maint else GREEN_FG, text="Không dùng" if maint else "Trống")
        self._hit.append((x, y, x + TILE_W, y + h, r["MaPhong"]))

    def _room_at(self, e):
        cy = self.cv.canvasy(e.y)
        return next((h[4] for h in self._hit if h[0] <= e.x <= h[2] and h[1] <= cy <= h[3]), None)

    def _click(self, e):
        ma = self._room_at(e)
        if ma is not None:
            self.select(ma)

    def _double(self, e):
        ma = self._room_at(e)
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


# ---------------------------------------------------------------------- màn hình
class PhongScreen(tk.Frame):
    def __init__(self, master, user=None):
        super().__init__(master, bg=PAGE_BG)
        self.user = user
        self.filter, self.floor, self.view, self.sel, self._rate = FILTERS[0], ALL_FLOORS, "list", None, 0
        self.rows, self.shown, self.counts = [], [], {n: 0 for n in FILTERS}
        self.kw = tk.StringVar(master=self)          # main.goto() điền sẵn ô tìm kiếm qua biến này
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
        tk.Label(box, text="Quản lý phòng", bg=PAGE_BG, fg=NAVY, font=(FONT, 20, "bold")).pack(anchor="w")
        tk.Label(box, text="Theo dõi tình trạng phòng, giường trống và giá thuê", bg=PAGE_BG, fg=MUTED,
                 font=(FONT, 10)).pack(anchor="w")
        SearchBox(head, self.kw, "Tìm theo tên phòng, loại phòng...").pack(side="right", anchor="n")

        self.stats = tk.Frame(self, bg=PAGE_BG)
        self.stats.pack(fill="x", pady=(16, 0), **pad)
        for i in range(4):
            self.stats.columnconfigure(i, weight=1, uniform="s")
        self.v_total = self._stat(0, "Tổng số phòng", NAVY)
        self.v_free = self._stat(1, "Giường còn trống", GREEN_FG)
        self.v_rate = self._stat(2, "Tỷ lệ lấp đầy", NAVY, bar=True)
        self.v_maint = self._stat(3, "Phòng đang bảo trì", MAINT_FG)

        bar = tk.Frame(self, bg=PAGE_BG)
        bar.pack(fill="x", pady=(16, 0), **pad)
        IconButton(bar, "Thêm", "plus", self.on_add, "primary").pack(side="left", padx=(0, 10))
        self.btn_edit = IconButton(bar, "Sửa", "edit", self.on_edit, "outline", enabled=False)
        self.btn_edit.pack(side="left", padx=(0, 10))
        self.btn_del = IconButton(bar, "Xóa", "trash", self.on_delete, "danger", enabled=False)
        self.btn_del.pack(side="left", padx=(0, 10))
        IconButton(bar, "Loại phòng", "list", self.on_types, "outline").pack(side="left")
        self.view_chips = {}
        for key in ("map", "list"):                  # pack phải: "Sơ đồ giường" nằm ngoài cùng bên phải
            self.view_chips[key] = Chip(bar, lambda k=key: self.set_view(k))
            self.view_chips[key].pack(side="right", padx=(10, 0) if key == "map" else 0)

        chips = tk.Frame(self, bg=PAGE_BG)
        chips.pack(fill="x", pady=(14, 14), **pad)
        self.chips = {}
        for name in FILTERS:
            self.chips[name] = Chip(chips, lambda n=name: self.set_filter(n))
            self.chips[name].pack(side="left", padx=(0, 10))
        self.floor_var = tk.StringVar(master=self, value=ALL_FLOORS)
        self.floor_cb = ttk.Combobox(chips, textvariable=self.floor_var, state="readonly", width=16,
                                     values=[ALL_FLOORS], font=(FONT, 10))
        self.floor_cb.pack(side="left", ipady=7)
        self.floor_cb.bind("<<ComboboxSelected>>", lambda _e: self.set_floor(self.floor_var.get()))

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
        self.table = RoomTable(card.inner, self._on_pick, self.on_edit)
        self.bedmap = BedMap(card.inner, self._on_pick, self.on_edit)
        self.table.pack(fill="both", expand=True)

    def _stat(self, col, title, color, bar=False):
        c = Card(self.stats)
        c.config(height=108)
        c.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 16, 0))
        tk.Label(c.inner, text=title, bg="white", fg=MUTED, font=(FONT, 10, "bold")).pack(anchor="w", padx=18,
                                                                                         pady=(14, 0))
        val = tk.Label(c.inner, text="0", bg="white", fg=color, font=(FONT, 24, "bold"))
        val.pack(anchor="w", padx=18)
        if bar:
            self.rate_bar = tk.Canvas(c.inner, height=8, bg="white", highlightthickness=0)
            self.rate_bar.pack(fill="x", padx=18)
            self.rate_bar.bind("<Configure>", lambda _e: self._paint_bar())
        return val

    def _paint_bar(self):
        cv, w = self.rate_bar, max(self.rate_bar.winfo_width(), 1)
        cv.delete("all")
        rounded_rect(cv, 0, 1, w, 7, 3, fill=TRACK, outline=TRACK)
        if self._rate > 0:
            rounded_rect(cv, 0, 1, max(6, w * min(self._rate, 100) / 100), 7, 3, fill=BAR_OK, outline=BAR_OK)

    # ---- dữ liệu / bộ lọc
    def refresh(self):
        self.rows = load_rooms()
        self.counts = {n: sum(1 for r in self.rows if n == FILTERS[0] or r["TinhTrang"] == n) for n in FILTERS}
        s = stats(self.rows)
        self.v_total.config(text=str(s["total"]))
        self.v_free.config(text=str(s["free"]))
        self.v_rate.config(text=f"{s['rate']}%")
        self.v_maint.config(text=str(s["maint"]))
        self._rate = s["rate"]
        self._paint_bar()
        floors = [f"Tầng {t}" for t in sorted({r["Tang"] for r in self.rows})]
        self.floor_cb.config(values=[ALL_FLOORS] + floors)
        if self.floor not in floors:
            self.floor = ALL_FLOORS
            self.floor_var.set(ALL_FLOORS)
        self.apply()

    def set_filter(self, name):
        if name in FILTERS:
            self.filter = name
            self.apply()

    def set_floor(self, name):
        self.floor = name
        self.apply()

    def set_view(self, key):
        if key == self.view:
            return
        self.view = key
        shown, hidden = (self.table, self.bedmap) if key == "list" else (self.bedmap, self.table)
        hidden.pack_forget()
        shown.selected = self.sel
        shown.pack(fill="both", expand=True)
        self.apply()

    def apply(self):
        kw = fold(self.kw.get().strip())
        fl = None if self.floor == ALL_FLOORS else int(self.floor.split()[-1])
        self.shown = [r for r in self.rows
                      if (self.filter == FILTERS[0] or r["TinhTrang"] == self.filter)
                      and (fl is None or r["Tang"] == fl) and (not kw or kw in r["_hay"])]
        for name, chip in self.chips.items():
            chip.set(f"{name} ({self.counts[name]})", name == self.filter)
        self.view_chips["list"].set("Danh sách", self.view == "list")
        self.view_chips["map"].set("Sơ đồ giường", self.view == "map")
        for w in (self.table, self.bedmap):          # đồng bộ dòng đang chọn giữa hai kiểu xem
            w.selected = self.sel
            w.load(self.shown)
        self.foot_l.config(text=f"Hiển thị {len(self.shown)} / {len(self.rows)} phòng")

    def _on_pick(self, ma):
        self.sel = ma
        self.btn_edit.set_enabled(ma is not None)
        self.btn_del.set_enabled(ma is not None)

    def _room(self, ma):
        return next((r for r in self.rows if r["MaPhong"] == ma), None)

    # ---- thêm / sửa / xóa
    def _loai_opts(self):
        return [f"{r['MaLoai']} - {r['TenLoai']} ({r['SoGiuong']} giường)"
                for r in db.query("SELECT * FROM LoaiPhong ORDER BY MaLoai")]

    def _fields(self):
        """Các ô của hộp thoại Thêm / Cập nhật phòng (mỗi ô một dòng, theo mẫu thiết kế)."""
        return [{"key": "TenPhong", "label": "Tên phòng", "ph": "Ví dụ: A301", "required": True, "span": 2},
                {"key": "Loai", "label": "Loại phòng", "kind": "combo", "opts": self._loai_opts(), "span": 2},
                {"key": "Tang", "label": "Tầng", "ph": "1", "required": True, "span": 2},
                {"key": "TrangThai", "label": "Trạng thái", "kind": "combo", "opts": ["Hoạt động", "Bảo trì"],
                 "span": 2}]

    @staticmethod
    def _validator(room=None):
        """Hàm kiểm tra cho hộp thoại. room=None: đang THÊM; có giá trị: đang SỬA phòng đó (dict từ load_rooms).
        Lỗi thì hộp thoại giữ nguyên nội dung và đưa con trỏ về đúng ô."""
        def check(v):
            if not v["TenPhong"]:
                return None, ("TenPhong", "Tên phòng không được để trống.")
            if not (v["Tang"].isascii() and v["Tang"].isdigit() and int(v["Tang"]) <= 99):
                return None, ("Tang", "Tầng phải là số nguyên từ 0 đến 99.")
            if db.query("SELECT 1 FROM Phong WHERE TenPhong=? COLLATE NOCASE AND MaPhong<>?",
                        (v["TenPhong"], room["MaPhong"] if room else 0), one=True):
                return None, ("TenPhong", f"Tên phòng {v['TenPhong']} đã tồn tại.")
            if room:                                    # đổi loại phòng không được làm thiếu giường cho người đang ở
                beds = db.query("SELECT SoGiuong FROM LoaiPhong WHERE MaLoai=?", (pick_id(v["Loai"]),),
                                one=True)["SoGiuong"]
                if beds < room["DangO"]:
                    return None, ("Loai", f"Phòng đang có {room['DangO']} sinh viên ở, "
                                          f"không thể đổi sang loại chỉ có {beds} giường.")
            return dict(v, Tang=int(v["Tang"])), None
        return check

    def on_add(self):
        if not self._loai_opts():
            return error("Hãy thêm loại phòng trước (nút Loại phòng).")
        d = form_modal(self, "Thêm phòng", self._fields(), validate=self._validator(), width=540)
        if not d:
            return
        try:
            new_id = db.execute("INSERT INTO Phong(TenPhong,MaLoai,Tang,TrangThai) VALUES(?,?,?,?)",
                                (d["TenPhong"], pick_id(d["Loai"]), d["Tang"], d["TrangThai"]))
        except sqlite3.IntegrityError:
            return error("Không lưu được: tên phòng đã tồn tại.")
        db.ghi_nhat_ky("phong", f"Thêm phòng **{d['TenPhong']}**")
        self.filter, self.floor = FILTERS[0], ALL_FLOORS
        self.floor_var.set(ALL_FLOORS)
        self.kw.set("")
        self.refresh()
        (self.table if self.view == "list" else self.bedmap).select(new_id, scroll=True)

    def on_edit(self):
        r = self._room(self.sel)
        if not r:
            return
        cur = dict(db.query("SELECT * FROM Phong WHERE MaPhong=?", (r["MaPhong"],), one=True))
        opts = self._loai_opts()
        cur["Loai"] = next((o for o in opts if pick_id(o) == cur["MaLoai"]), opts[0])
        d = form_modal(self, "Cập nhật phòng", self._fields(), cur, validate=self._validator(r), width=540)
        if not d:
            return
        if d["TrangThai"] == "Bảo trì" and r["DangO"] and not messagebox.askyesno(
                "Xác nhận", f"Phòng {r['TenPhong']} đang có {r['DangO']} sinh viên ở. Vẫn chuyển sang bảo trì?"):
            return
        db.execute("UPDATE Phong SET TenPhong=?,MaLoai=?,Tang=?,TrangThai=? WHERE MaPhong=?",
                   (d["TenPhong"], pick_id(d["Loai"]), d["Tang"], d["TrangThai"], r["MaPhong"]))
        db.ghi_nhat_ky("phong", f"Cập nhật phòng **{d['TenPhong']}**")
        self.refresh()

    def on_delete(self):
        r = self._room(self.sel)
        if not r:
            return
        if r["DangO"]:
            return error(f"Phòng {r['TenPhong']} đang có {r['DangO']} sinh viên ở.\n"
                         "Hãy kết thúc hợp đồng của họ trước khi xóa phòng.")
        if not messagebox.askyesno("Xác nhận", f"Bạn có chắc chắn muốn xóa phòng {r['TenPhong']}?"):
            return
        try:
            db.execute("DELETE FROM Phong WHERE MaPhong=?", (r["MaPhong"],))
        except sqlite3.IntegrityError:
            error("Không thể xóa vì phòng này còn hợp đồng hoặc hóa đơn liên quan.")
        self.refresh()

    def on_types(self):
        win = tk.Toplevel(self)
        win.title("Loại phòng")
        win.geometry("640x420")
        LoaiPhongScreen(win).pack(fill="both", expand=True)
        win.transient(self.winfo_toplevel())
        win.grab_set()
        win.wait_window()
        self.refresh()