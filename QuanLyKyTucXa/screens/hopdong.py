import calendar
import csv
import re
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

import database as db
from screens.base import error, form_dialog, money, parse_date, pick_id, valid_date

# Các thành phần giao diện định nghĩa trực tiếp tại hopdong.py
FONT = "Segoe UI"

PRIMARY = "#1558C0"
NAVY = "#0B3C8C"
PAGE_BG = "#F3F7FD"
BORDER = "#DCE6F7"
TEXT = "#0F2447"
MUTED = "#4A5A78"
SEL_BG = "#E3EEFF"


class FlatButton(tk.Label):
    def __init__(
        self, master, text, command,
        bg=PRIMARY, hover=NAVY, fg="white",
        font=(FONT, 11, "bold"), **kw
    ):
        super().__init__(
            master,
            text=text,
            bg=bg,
            fg=fg,
            font=font,
            cursor="hand2",
            takefocus=1,
            **kw
        )

        self._bg = bg
        self._hover = hover
        self._command = command

        self.bind(
            "<Enter>",
            lambda e: self.config(bg=self._hover)
        )
        self.bind(
            "<Leave>",
            lambda e: self.config(bg=self._bg)
        )
        self.bind("<Button-1>", self._click)
        self.bind("<space>", self._click)

    def _click(self, event=None):
        self.focus_set()
        self._command()

SAP_HET_HAN = 30
WARN_BG = "#FFF3D6"
OVER_BG = "#FCE8E8"
DONE_FG = "#8998B0"
STATE_STYLE = {
    "Đang thuê": ("#147A42", "#E5F5E9"),
    "Sắp hết hạn": ("#A66A08", "#FFF3D6"),
    "Quá hạn": ("#B42318", "#FCE8E8"),
    "Đã kết thúc": ("#6F7F98", "#EEF1F6"),
}
FILTERS = ["Tất cả", "Đang thuê", "Sắp hết hạn", "Quá hạn", "Đã kết thúc"]
COLUMNS = [
    ("MaHD", "Mã HĐ", 58, "center"),
    ("MaSV", "Mã SV", 58, "center"),
    ("HoTen", "Sinh viên", 150, "w"),
    ("TenPhong", "Phòng", 68, "center"),
    ("NgayBatDau", "Bắt đầu", 95, "center"),
    ("NgayKetThuc", "Kết thúc", 95, "center"),
    ("ConLai", "Còn lại", 85, "center"),
    ("Tinh", "Trạng thái", 105, "center"),
]


def add_months(d, n):
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return d.replace(year=y, month=m, day=min(d.day, calendar.monthrange(y, m)[1]))


def fmt(d):
    return d.strftime("%d/%m/%Y")


def classify(row, today=None):
    today = today or date.today()
    if row["TrangThai"] != "Đang thuê":
        return "Đã kết thúc", None
    left = (parse_date(row["NgayKetThuc"]).date() - today).days
    if left < 0:
        return "Quá hạn", left
    if left <= SAP_HET_HAN:
        return "Sắp hết hạn", left
    return "Đang thuê", left


def left_text(state, left):
    if left is None:
        return "—"
    if left < 0:
        return f"Quá {-left} ngày"
    if left == 0:
        return "Hôm nay"
    return f"{left} ngày"


def load_contracts():
    rows = db.query("""
        SELECT h.MaHD, h.MaSV, s.HoTen, s.SDT, s.Lop,
               h.MaPhong, p.TenPhong, p.Tang, l.TenLoai, l.GiaThue,
               h.NgayBatDau, h.NgayKetThuc, h.TrangThai
        FROM HopDong h
        JOIN SinhVien s ON s.MaSV=h.MaSV
        JOIN Phong p ON p.MaPhong=h.MaPhong
        JOIN LoaiPhong l ON l.MaLoai=p.MaLoai
        ORDER BY h.MaHD DESC
    """)
    result = []
    for row in rows:
        item = dict(row)
        item["Tinh"], item["Left"] = classify(item)
        item["ConLai"] = left_text(item["Tinh"], item["Left"])
        result.append(item)
    return result


def room_debt(room_id):
    row = db.query("""
        SELECT COALESCE(SUM(TongTien-DaThu),0) AS n, COUNT(*) AS c
        FROM HoaDon WHERE MaPhong=? AND TongTien>DaThu
    """, (room_id,), one=True)
    return row["n"], row["c"]


def pending_extensions():
    return db.query("""
        SELECT y.MaYC, y.MaSV, s.HoTen, y.NoiDung, y.NgayGui,
               (SELECT h.MaHD FROM HopDong h
                WHERE h.MaSV=y.MaSV AND h.TrangThai='Đang thuê' LIMIT 1) AS MaHD
        FROM YeuCau y JOIN SinhVien s ON s.MaSV=y.MaSV
        WHERE y.Loai='Gia hạn' AND y.TrangThai='Chờ xử lý'
        ORDER BY y.MaYC
    """)


def requested_date(text):
    match = re.search(r"(\d{2}/\d{2}/\d{4})", text or "")
    return match.group(1) if match and valid_date(match.group(1)) else None


class LineIcon(tk.Canvas):
    """Icon vector nhỏ, không phụ thuộc emoji hoặc file ảnh."""

    def __init__(self, master, kind, color=NAVY, size=14, bg="white"):
        super().__init__(
            master, width=size, height=size, bg=bg,
            highlightthickness=0, bd=0
        )
        self.kind, self.color, self.size = kind, color, size
        self._draw()

    def _draw(self):
        s, c = self.size, self.color

        def line(*pts, width=1.6):
            self.create_line(
                *pts, fill=c, width=width,
                capstyle="round", joinstyle="round"
            )

        def oval(x1, y1, x2, y2, width=1.5):
            self.create_oval(x1, y1, x2, y2, outline=c, width=width)

        def rect(x1, y1, x2, y2, width=1.4):
            self.create_rectangle(x1, y1, x2, y2, outline=c, width=width)

        if self.kind == "search":
            oval(s*.12, s*.10, s*.66, s*.64)
            line(s*.59, s*.59, s*.90, s*.90, width=2)
        elif self.kind == "plus":
            line(s*.5, s*.13, s*.5, s*.87, width=2)
            line(s*.13, s*.5, s*.87, s*.5, width=2)
        elif self.kind == "extend":
            self.create_arc(
                s*.13, s*.13, s*.85, s*.85,
                start=35, extent=290, style="arc",
                outline=c, width=1.8
            )
            line(s*.70, s*.10, s*.88, s*.14, s*.83, s*.31)
        elif self.kind == "stop":
            rect(s*.20, s*.20, s*.80, s*.80, 1.8)
        elif self.kind == "detail":
            oval(s*.13, s*.13, s*.87, s*.87)
            self.create_text(
                s*.5, s*.51, text="i", fill=c,
                font=(FONT, max(8, int(s*.68)), "bold")
            )
        elif self.kind == "delete":
            rect(s*.25, s*.30, s*.75, s*.88)
            line(s*.17, s*.23, s*.83, s*.23)
            line(s*.38, s*.13, s*.62, s*.13)
            line(s*.42, s*.41, s*.42, s*.75)
            line(s*.58, s*.41, s*.58, s*.75)
        elif self.kind == "export":
            line(s*.5, s*.12, s*.5, s*.68, width=1.8)
            line(s*.29, s*.48, s*.5, s*.69, s*.71, s*.48, width=1.8)
            line(s*.18, s*.84, s*.82, s*.84)
        elif self.kind == "mail":
            rect(s*.12, s*.22, s*.88, s*.78)
            line(s*.14, s*.27, s*.5, s*.54, s*.86, s*.27)
        elif self.kind == "file":
            rect(s*.20, s*.12, s*.80, s*.88)
            line(s*.32, s*.40, s*.68, s*.40)
            line(s*.32, s*.55, s*.68, s*.55)
        elif self.kind == "chart":
            line(s*.13, s*.88, s*.13, s*.12)
            line(s*.13, s*.88, s*.90, s*.88)
            rect(s*.25, s*.58, s*.39, s*.86, 1)
            rect(s*.47, s*.39, s*.61, s*.86, 1)
            rect(s*.69, s*.20, s*.83, s*.86, 1)
        elif self.kind == "calendar":
            rect(s*.13, s*.22, s*.87, s*.88)
            line(s*.13, s*.40, s*.87, s*.40)
            line(s*.34, s*.10, s*.34, s*.30)
            line(s*.66, s*.10, s*.66, s*.30)
        elif self.kind == "close":
            line(s*.22, s*.22, s*.78, s*.78, width=2)
            line(s*.78, s*.22, s*.22, s*.78, width=2)


class ActionButton(tk.Frame):
    """Nút nhỏ dạng phẳng, biểu tượng vẽ Canvas nên không bị lỗi font."""

    def __init__(
        self, master, text, command, icon=None, primary=False,
        fg=None, padx=7, pady=5
    ):
        bg = PRIMARY if primary else "white"
        color = fg or ("white" if primary else NAVY)
        border = PRIMARY if primary else BORDER

        super().__init__(
            master, bg=bg, cursor="hand2",
            highlightthickness=1,
            highlightbackground=border,
            highlightcolor=border, bd=0
        )

        self.command = command
        self.normal_bg = bg
        self.hover_bg = "#0D469F" if primary else SEL_BG

        if icon:
            self.icon = LineIcon(self, icon, color, 13, bg)
            self.icon.pack(side="left", padx=(padx, 4), pady=pady)
        else:
            self.icon = None

        self.label = tk.Label(
            self, text=text, bg=bg, fg=color,
            font=(FONT, 8, "bold"), cursor="hand2"
        )
        self.label.pack(
            side="left",
            padx=(0 if icon else padx, padx),
            pady=pady
        )

        for widget in (self, self.label, self.icon):
            if widget is not None:
                widget.bind("<Button-1>", self._click)
                widget.bind("<Enter>", self._enter)
                widget.bind("<Leave>", self._leave)

    def _click(self, _event=None):
        self.command()

    def _paint(self, color):
        self.configure(bg=color)
        self.label.configure(bg=color)
        if self.icon:
            self.icon.configure(bg=color)

    def _enter(self, _event=None):
        self._paint(self.hover_bg)

    def _leave(self, _event=None):
        self._paint(self.normal_bg)


class HopDongScreen(tk.Frame):
    def __init__(self, master, user=None):
        super().__init__(master, bg=PAGE_BG)
        self.user = user
        self.filter = "Tất cả"
        self.sort_col, self.sort_rev = "MaHD", True
        self.rows, self.shown = [], []
        self.counts = {name: 0 for name in FILTERS}
        self._style()
        self._build()
        self.refresh()

    def _style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "HD.Treeview",
            rowheight=32, font=(FONT, 8),
            background="white", fieldbackground="white",
            foreground=TEXT, borderwidth=0
        )
        style.configure(
            "HD.Treeview.Heading",
            font=(FONT, 8, "bold"),
            background="#E8F0FC", foreground=NAVY,
            relief="flat", padding=(5, 7)
        )
        style.map(
            "HD.Treeview",
            background=[("selected", PRIMARY)],
            foreground=[("selected", "white")]
        )

    def _build(self):
        # Tiêu đề và ô tìm kiếm
        head = tk.Frame(self, bg=PAGE_BG)
        head.pack(fill="x", padx=16, pady=(12, 1))

        title_box = tk.Frame(head, bg=PAGE_BG)
        title_box.pack(side="left", fill="x", expand=True)

        tk.Label(
            title_box, text="Hợp đồng thuê phòng",
            bg=PAGE_BG, fg=NAVY,
            font=(FONT, 15, "bold")
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="Theo dõi thời hạn, gia hạn và kết thúc hợp đồng của sinh viên nội trú",
            bg=PAGE_BG, fg=MUTED, font=(FONT, 8)
        ).pack(anchor="w", pady=(1, 0))

        search = tk.Frame(
            head, bg="white",
            highlightthickness=1,
            highlightbackground=BORDER
        )
        search.pack(
            side="right", anchor="n",
            padx=(10, 0), pady=1
        )

        LineIcon(
            search, "search", "#6F8DB7", 13, "white"
        ).pack(side="left", padx=(7, 3), pady=5)

        self.kw = tk.StringVar()
        entry = tk.Entry(
            search, textvariable=self.kw,
            relief="flat", bd=0, width=22,
            font=(FONT, 8), bg="white", fg=TEXT
        )
        entry.pack(side="left", padx=(0, 7), pady=5)
        entry.bind("<KeyRelease>", lambda _e: self.apply())
        entry.bind("<Return>", lambda _e: self.apply())

        # Bốn thẻ thống kê
        self.stats = tk.Frame(self, bg=PAGE_BG)
        self.stats.pack(fill="x", padx=16, pady=(9, 0))

        for i in range(4):
            self.stats.columnconfigure(
                i, weight=1, uniform="contract_stats"
            )

        # Thanh thao tác
        bar = tk.Frame(self, bg=PAGE_BG)
        bar.pack(fill="x", padx=16, pady=(8, 6))

        ActionButton(
            bar, "Thêm hợp đồng", self.on_add,
            icon="plus", primary=True
        ).pack(side="left", padx=(0, 4))

        ActionButton(
            bar, "Gia hạn", self.on_extend,
            icon="extend"
        ).pack(side="left", padx=3)

        ActionButton(
            bar, "Kết thúc", self.on_end,
            icon="stop"
        ).pack(side="left", padx=3)

        ActionButton(
            bar, "Chi tiết", self.on_detail,
            icon="detail"
        ).pack(side="left", padx=3)

        ActionButton(
            bar, "Xóa", self.on_delete,
            icon="delete"
        ).pack(side="left", padx=3)

        right = tk.Frame(bar, bg=PAGE_BG)
        right.pack(side="right")

        self.req_btn = ActionButton(
            right, "Yêu cầu gia hạn", self.on_requests,
            icon="mail"
        )
        self.req_btn.pack(side="left", padx=3)

        ActionButton(
            right, "Xuất CSV", self.export_csv,
            icon="export"
        ).pack(side="left", padx=(3, 0))

        # Các chip lọc trạng thái
        self.chips_box = tk.Frame(self, bg=PAGE_BG)
        self.chips_box.pack(
            fill="x", padx=16, pady=(0, 6)
        )

        self.chips = {}

        for name in FILTERS:
            chip = tk.Label(
                self.chips_box, text=name,
                bg="white", fg=NAVY,
                font=(FONT, 8, "bold"),
                padx=9, pady=4,
                cursor="hand2",
                highlightthickness=1,
                highlightbackground=BORDER
            )
            chip.pack(side="left", padx=(0, 5))
            chip.bind(
                "<Button-1>",
                lambda _e, n=name: self.set_filter(n)
            )
            self.chips[name] = chip

        # Bảng dữ liệu
        wrap = tk.Frame(
            self, bg="white",
            highlightthickness=1,
            highlightbackground=BORDER
        )
        wrap.pack(fill="x", padx=16, pady=(0, 3))

        self.tree = ttk.Treeview(
            wrap,
            columns=[c[0] for c in COLUMNS],
            show="headings",
            selectmode="browse",
            style="HD.Treeview",
            height=6
        )

        for key, heading, width, anchor in COLUMNS:
            self.tree.heading(
                key, text=heading,
                command=lambda k=key: self.sort_by(k)
            )
            self.tree.column(
                key, width=width, minwidth=45,
                anchor=anchor, stretch=(key == "HoTen")
            )

        scroll = ttk.Scrollbar(
            wrap, orient="vertical",
            command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="x", expand=True)
        self.scroll = scroll

        self.tree.tag_configure(
            "warn", background=WARN_BG
        )
        self.tree.tag_configure(
            "over", background=OVER_BG
        )
        self.tree.tag_configure(
            "done", foreground=DONE_FG
        )

        self.tree.bind(
            "<Double-1>",
            lambda _e: self.on_detail()
        )

        self.foot = tk.Label(
            self, bg=PAGE_BG, fg=MUTED,
            font=(FONT, 7), anchor="w"
        )
        self.foot.pack(
            fill="x", padx=16, pady=(1, 7)
        )

    def _stat(
        self, col, title, value, sub,
        color, icon, icon_bg, flt=None
    ):
        card = tk.Frame(
            self.stats, bg="white", height=94,
            highlightthickness=1,
            highlightbackground=BORDER,
            cursor="hand2" if flt else ""
        )
        card.grid(
            row=0, column=col, sticky="nsew",
            padx=(0 if col == 0 else 6, 0)
        )
        card.grid_propagate(False)

        # Thẻ thống kê chữ thuần theo ảnh mẫu.
        text_box = tk.Frame(card, bg="white")
        text_box.pack(
            side="left", fill="both", expand=True,
            padx=9, pady=10
        )

        tk.Label(
            text_box, text=title,
            bg="white", fg=MUTED,
            font=(FONT, 7, "bold")
        ).pack(anchor="w")

        tk.Label(
            text_box, text=str(value),
            bg="white", fg=color,
            font=(FONT, 17, "bold")
        ).pack(anchor="w", pady=(1, 0))

        tk.Label(
            text_box, text=sub,
            bg="white", fg=MUTED,
            font=(FONT, 7)
        ).pack(anchor="w")

        if flt:
            for widget in (
                card, *card.winfo_children(),
                *text_box.winfo_children()
            ):
                widget.bind(
                    "<Button-1>",
                    lambda _e, f=flt: self.set_filter(f)
                )

    def refresh(self):
        self.rows = load_contracts()

        counts = {
            name: sum(
                1 for row in self.rows
                if name == "Tất cả" or row["Tinh"] == name
            )
            for name in FILTERS
        }

        # Đang thuê tính theo trạng thái gốc trong CSDL.
        counts["Đang thuê"] = sum(
            1 for row in self.rows
            if row["TrangThai"] == "Đang thuê"
        )

        self.counts = counts

        for widget in self.stats.winfo_children():
            widget.destroy()

        pending = len(pending_extensions())

        self._stat(
            0, "ĐANG THUÊ", counts["Đang thuê"],
            f"trên tổng {len(self.rows)} hợp đồng",
            PRIMARY, "file", "#E8F0FF", "Đang thuê"
        )

        self._stat(
            1, "SẮP HẾT HẠN", counts["Sắp hết hạn"],
            f"trong {SAP_HET_HAN} ngày tới",
            "#B7791F", "calendar", "#FFF2D9",
            "Sắp hết hạn"
        )

        self._stat(
            2, "QUÁ HẠN", counts["Quá hạn"],
            "cần gia hạn hoặc kết thúc",
            "#C0392B", "clock", "#FDECEC",
            "Quá hạn"
        )

        self._stat(
            3, "YÊU CẦU GIA HẠN", pending,
            "sinh viên đang chờ duyệt",
            "#16814A", "mail", "#E5F6EC"
        )

        self.req_btn.label.config(
            text=(
                f"Yêu cầu gia hạn ({pending})"
                if pending else "Yêu cầu gia hạn"
            )
        )

        self.apply()

    def set_filter(self, name):
        self.filter = name
        self.apply()

    def sort_by(self, col):
        self.sort_rev = (
            not self.sort_rev
            if self.sort_col == col else False
        )
        self.sort_col = col
        self.apply()

    def _sort_key(self, row):
        col = self.sort_col

        if col in ("MaHD", "MaSV"):
            return row[col]

        if col in ("NgayBatDau", "NgayKetThuc"):
            return parse_date(row[col])

        if col == "ConLai":
            return (
                row["Left"]
                if row["Left"] is not None else 10**9
            )

        return str(row[col]).lower()

    def apply(self):
        for name, chip in self.chips.items():
            active = name == self.filter
            chip.config(
                text=f"{name} ({self.counts.get(name, 0)})",
                bg=PRIMARY if active else "white",
                fg="white" if active else NAVY,
                highlightbackground=PRIMARY if active else BORDER
            )

        keyword = self.kw.get().strip().lower()
        rows = []

        for row in self.rows:
            if self.filter == "Đang thuê":
                status_ok = row["TrangThai"] == "Đang thuê"
            else:
                status_ok = (
                    self.filter == "Tất cả"
                    or row["Tinh"] == self.filter
                )

            searchable = (
                f"{row['MaHD']} {row['MaSV']} {row['HoTen']} "
                f"{row['TenPhong']} {row['Lop'] or ''} {row['Tinh']}"
            ).lower()

            if status_ok and (
                not keyword or keyword in searchable
            ):
                rows.append(row)

        rows.sort(
            key=self._sort_key,
            reverse=self.sort_rev
        )
        self.shown = rows

        keep = self.selected()
        self.tree.delete(*self.tree.get_children())

        # Bảng chỉ cao bằng số dòng thực tế, tối đa 6 dòng.
        self.tree.configure(
            height=max(1, min(6, len(rows)))
        )

        if len(rows) > 6:
            self.scroll.pack(side="right", fill="y")
        else:
            self.scroll.pack_forget()

        tags = {
            "Sắp hết hạn": "warn",
            "Quá hạn": "over",
            "Đã kết thúc": "done"
        }

        for row in rows:
            self.tree.insert(
                "", "end",
                iid=str(row["MaHD"]),
                tags=(tags.get(row["Tinh"], ""),),
                values=[
                    row[col[0]] for col in COLUMNS
                ]
            )

        # Giữ dòng đang chọn hoặc chọn dòng đầu tiên.
        if keep is not None and self.tree.exists(str(keep)):
            self.tree.selection_set(str(keep))
        elif rows:
            self.tree.selection_set(str(rows[0]["MaHD"]))

        if rows:
            self.foot.config(
                text=(
                    f"Hiển thị {len(rows)}/{len(self.rows)} hợp đồng · "
                    "nhấp tiêu đề cột để sắp xếp · "
                    "nhấp đúp để xem chi tiết"
                )
            )
        else:
            self.foot.config(
                text="Không có hợp đồng nào phù hợp."
            )

    def selected(self):
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    def _need(self):
        selected = self.selected()

        if selected is None:
            messagebox.showwarning(
                "Thông báo",
                "Vui lòng chọn một hợp đồng trong bảng.",
                parent=self
            )
            return None

        return next(
            (
                row for row in self.rows
                if row["MaHD"] == selected
            ),
            None
        )

    # ------------------------------------------------------------------
    # THÊM HỢP ĐỒNG
    # ------------------------------------------------------------------
    def on_add(self):
        students = [
            f"{r['MaSV']} - {r['HoTen']}"
            for r in db.query(
                "SELECT MaSV,HoTen FROM SinhVien WHERE MaSV NOT IN "
                "(SELECT MaSV FROM HopDong WHERE TrangThai='Đang thuê') "
                "ORDER BY HoTen"
            )
        ]

        rooms = [
            f"{p['MaPhong']} - {p['TenPhong']} "
            f"(còn {p['SoGiuong']-p['DangO']} chỗ)"
            for p in db.danh_sach_phong()
            if p["TinhTrang"] in ("Trống", "Còn chỗ")
        ]

        if not students:
            return error(
                "Không có sinh viên nào chưa có phòng."
            )

        if not rooms:
            return error(
                "Hiện không còn phòng trống."
            )

        data = form_dialog(self, "Đăng ký phòng", [
            ("SV", "Sinh viên", "combo", students),
            ("Phong", "Phòng", "combo", rooms),
            ("NgayBatDau", "Ngày bắt đầu (dd/mm/yyyy)", "entry", None),
            (
                "ThoiHan", "Thời hạn hợp đồng", "combo",
                ["3 tháng", "6 tháng", "9 tháng", "12 tháng"]
            ),
            (
                "NgayKetThuc",
                "Hoặc ngày kết thúc (để trống = theo thời hạn)",
                "entry", None
            ),
        ], {
            "NgayBatDau": fmt(date.today()),
            "ThoiHan": "12 tháng"
        })

        if not data:
            return

        if not valid_date(data["NgayBatDau"]):
            return error(
                "Ngày bắt đầu phải có dạng dd/mm/yyyy."
            )

        start = parse_date(data["NgayBatDau"]).date()

        if data["NgayKetThuc"]:
            if not valid_date(data["NgayKetThuc"]):
                return error(
                    "Ngày kết thúc phải có dạng dd/mm/yyyy."
                )
            end = parse_date(data["NgayKetThuc"]).date()
        else:
            end = add_months(
                start,
                int(data["ThoiHan"].split()[0])
            )

        if end <= start:
            return error(
                "Ngày kết thúc phải sau ngày bắt đầu."
            )

        student_id = pick_id(data["SV"])
        room_id = pick_id(data["Phong"])

        if db.query(
            "SELECT 1 FROM HopDong "
            "WHERE MaSV=? AND TrangThai='Đang thuê'",
            (student_id,), one=True
        ):
            return error(
                "Sinh viên này đã có hợp đồng đang thuê."
            )

        db.execute(
            "INSERT INTO HopDong"
            "(MaSV,MaPhong,NgayBatDau,NgayKetThuc) "
            "VALUES(?,?,?,?)",
            (student_id, room_id, fmt(start), fmt(end))
        )

        room_name = db.query(
            "SELECT TenPhong FROM Phong WHERE MaPhong=?",
            (room_id,), one=True
        )["TenPhong"]

        db.ghi_nhat_ky(
            "phong",
            f"Đăng ký phòng {room_name} – "
            f"**{data['SV'].split(' - ', 1)[-1]}**"
        )

        self.refresh()

        messagebox.showinfo(
            "Thành công",
            f"Đã tạo hợp đồng từ {fmt(start)} đến {fmt(end)}.",
            parent=self
        )

    # ------------------------------------------------------------------
    # GIA HẠN
    # ------------------------------------------------------------------
    def on_extend(self):
        row = self._need()
        if row:
            self.extend(row)

    def extend(self, row, new_end=None):
        if row["TrangThai"] != "Đang thuê":
            return messagebox.showinfo(
                "Thông báo",
                "Chỉ gia hạn được hợp đồng đang thuê.",
                parent=self
            )

        current_end = parse_date(
            row["NgayKetThuc"]
        ).date()

        if new_end is None:
            data = form_dialog(
                self, f"Gia hạn hợp đồng #{row['MaHD']}", [
                    (
                        "Them",
                        f"Gia hạn thêm (hiện hết hạn {row['NgayKetThuc']})",
                        "combo",
                        ["1 tháng", "3 tháng", "6 tháng", "9 tháng", "12 tháng"]
                    ),
                    (
                        "Ngay",
                        "Hoặc ngày kết thúc mới (dd/mm/yyyy)",
                        "entry", None
                    ),
                ],
                {"Them": "6 tháng"}
            )

            if not data:
                return

            if data["Ngay"]:
                if not valid_date(data["Ngay"]):
                    return error(
                        "Ngày phải có dạng dd/mm/yyyy."
                    )
                new_end = parse_date(data["Ngay"]).date()
            else:
                new_end = add_months(
                    current_end,
                    int(data["Them"].split()[0])
                )

        if new_end <= current_end:
            return error(
                "Ngày kết thúc mới phải sau ngày kết thúc hiện tại."
            )

        if new_end <= date.today():
            return error(
                "Ngày kết thúc mới vẫn trong quá khứ, "
                "hợp đồng sẽ tiếp tục quá hạn."
            )

        db.execute(
            "UPDATE HopDong SET NgayKetThuc=? WHERE MaHD=?",
            (fmt(new_end), row["MaHD"])
        )

        db.ghi_nhat_ky(
            "phong",
            f"Gia hạn hợp đồng **{row['HoTen']}** đến {fmt(new_end)}"
        )

        self.refresh()

        messagebox.showinfo(
            "Thành công",
            f"Đã gia hạn hợp đồng #{row['MaHD']} đến {fmt(new_end)}.",
            parent=self
        )

    # ------------------------------------------------------------------
    # KẾT THÚC / XÓA
    # ------------------------------------------------------------------
    def on_end(self):
        row = self._need()

        if not row:
            return

        if row["TrangThai"] != "Đang thuê":
            return messagebox.showinfo(
                "Thông báo",
                "Hợp đồng này đã kết thúc.",
                parent=self
            )

        debt, count = room_debt(row["MaPhong"])

        msg = (
            f"Kết thúc hợp đồng của {row['HoTen']} "
            f"và trả phòng {row['TenPhong']}?"
        )

        if count:
            msg += (
                f"\n\nPhòng còn {count} hóa đơn chưa thu đủ "
                f"(tổng nợ {money(debt)} đ)."
            )

        if messagebox.askyesno(
            "Xác nhận", msg, parent=self
        ):
            db.execute(
                "UPDATE HopDong SET TrangThai='Đã kết thúc', "
                "NgayKetThuc=? WHERE MaHD=?",
                (fmt(date.today()), row["MaHD"])
            )
            self.refresh()

    def on_delete(self):
        row = self._need()

        if not row:
            return

        extra = (
            "\n\nHợp đồng đang thuê: sinh viên sẽ được gỡ khỏi phòng."
            if row["TrangThai"] == "Đang thuê" else ""
        )

        if messagebox.askyesno(
            "Xác nhận xóa",
            f"Xóa hợp đồng #{row['MaHD']} của {row['HoTen']}?{extra}",
            parent=self
        ):
            db.execute(
                "DELETE FROM HopDong WHERE MaHD=?",
                (row["MaHD"],)
            )
            self.refresh()

    # ------------------------------------------------------------------
    # CHI TIẾT
    # ------------------------------------------------------------------
    def on_detail(self):
        row = self._need()

        if not row:
            return

        start = parse_date(row["NgayBatDau"]).date()
        end = parse_date(row["NgayKetThuc"]).date()
        months = max(1, round((end - start).days / 30.4))
        debt, count = room_debt(row["MaPhong"])
        fg, bg = STATE_STYLE[row["Tinh"]]

        win = tk.Toplevel(self)
        win.title(f"Hợp đồng #{row['MaHD']}")
        win.configure(bg="white")
        win.transient(self.winfo_toplevel())
        win.resizable(False, False)

        top = tk.Frame(win, bg=PRIMARY)
        top.pack(fill="x")

        tk.Label(
            top, text=f"Hợp đồng #{row['MaHD']}",
            bg=PRIMARY, fg="white",
            font=(FONT, 14, "bold")
        ).pack(anchor="w", padx=18, pady=(14, 0))

        tk.Label(
            top,
            text=f"{row['HoTen']} · Phòng {row['TenPhong']}",
            bg=PRIMARY, fg="#D8E6FF",
            font=(FONT, 9)
        ).pack(anchor="w", padx=18, pady=(2, 12))

        body = tk.Frame(win, bg="white")
        body.pack(fill="both", padx=18, pady=12)

        items = [
            ("Trạng thái", row["Tinh"]),
            ("Mã sinh viên", row["MaSV"]),
            ("Lớp", row["Lop"] or "—"),
            ("Điện thoại", row["SDT"] or "—"),
            (
                "Phòng",
                f"{row['TenPhong']} · Tầng {row['Tang']} · {row['TenLoai']}"
            ),
            (
                "Thời hạn",
                f"{row['NgayBatDau']} → {row['NgayKetThuc']} "
                f"(~{months} tháng)"
            ),
            ("Còn lại", row["ConLai"]),
            (
                "Giá thuê",
                f"{money(row['GiaThue'])} đ/người/tháng"
            ),
            (
                "Giá trị hợp đồng",
                f"≈ {money(row['GiaThue'] * months)} đ"
            ),
            (
                "Công nợ phòng",
                f"{money(debt)} đ ({count} hóa đơn)"
                if count else "Không có"
            ),
        ]

        for i, (label, value) in enumerate(items):
            tk.Label(
                body, text=label,
                bg="white", fg=MUTED,
                font=(FONT, 9), anchor="w", width=16
            ).grid(
                row=i, column=0,
                sticky="w", pady=4
            )

            if label == "Trạng thái":
                tk.Label(
                    body, text=f" {value} ",
                    bg=bg, fg=fg,
                    font=(FONT, 9, "bold")
                ).grid(
                    row=i, column=1, sticky="w"
                )
            else:
                tk.Label(
                    body, text=str(value),
                    bg="white", fg=TEXT,
                    font=(FONT, 9, "bold"), anchor="w"
                ).grid(
                    row=i, column=1, sticky="w"
                )

        buttons = tk.Frame(win, bg="white")
        buttons.pack(
            fill="x", padx=18, pady=(0, 14)
        )

        if row["TrangThai"] == "Đang thuê":
            FlatButton(
                buttons, "Gia hạn",
                lambda: (win.destroy(), self.extend(row)),
                padx=13, pady=7
            ).pack(side="left")

        FlatButton(
            buttons, "Đóng", win.destroy,
            bg="white", hover=SEL_BG, fg=NAVY,
            padx=13, pady=7,
            highlightthickness=1,
            highlightbackground=BORDER
        ).pack(side="right")

        win.bind("<Escape>", lambda _e: win.destroy())
        win.grab_set()

    # ------------------------------------------------------------------
    # XUẤT CSV
    # ------------------------------------------------------------------
    def export_csv(self):
        if not self.shown:
            return messagebox.showinfo(
                "Thông báo",
                "Không có dữ liệu để xuất.",
                parent=self
            )

        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"hop_dong_{date.today():%Y%m%d}.csv"
        )

        if not path:
            return

        try:
            with open(
                path, "w",
                newline="", encoding="utf-8-sig"
            ) as file:
                writer = csv.writer(file)

                writer.writerow(
                    [col[1] for col in COLUMNS]
                    + ["Điện thoại", "Lớp"]
                )

                for row in self.shown:
                    writer.writerow(
                        [row[col[0]] for col in COLUMNS]
                        + [row["SDT"] or "", row["Lop"] or ""]
                    )

        except OSError as exc:
            return error(f"Không ghi được file: {exc}")

        messagebox.showinfo(
            "Thành công",
            f"Đã xuất {len(self.shown)} hợp đồng ra:\n{path}",
            parent=self
        )

    # ------------------------------------------------------------------
    # YÊU CẦU GIA HẠN
    # ------------------------------------------------------------------
    def on_requests(self):
        win = tk.Toplevel(self)
        win.title("Yêu cầu gia hạn từ sinh viên")
        win.configure(bg=PAGE_BG)
        win.transient(self.winfo_toplevel())
        win.geometry("720x390")
        win.minsize(620, 340)

        tk.Label(
            win, text="Yêu cầu gia hạn đang chờ duyệt",
            bg=PAGE_BG, fg=NAVY,
            font=(FONT, 13, "bold")
        ).pack(anchor="w", padx=16, pady=(13, 8))

        columns = [
            ("MaYC", "Mã YC", 55),
            ("HoTen", "Sinh viên", 150),
            ("NgayGui", "Ngày gửi", 90),
            ("NoiDung", "Nội dung", 270),
            ("Hien", "Hết hạn hiện tại", 110)
        ]

        table = ttk.Treeview(
            win,
            columns=[col[0] for col in columns],
            show="headings",
            selectmode="browse",
            style="HD.Treeview",
            height=8
        )

        for key, heading, width in columns:
            table.heading(key, text=heading)
            table.column(
                key, width=width, anchor="w"
            )

        table.pack(
            fill="both", expand=True, padx=16
        )

        def load():
            table.delete(*table.get_children())

            for request in pending_extensions():
                contract = next(
                    (
                        r for r in self.rows
                        if r["MaHD"] == request["MaHD"]
                    ),
                    None
                )

                table.insert(
                    "", "end",
                    iid=str(request["MaYC"]),
                    values=(
                        request["MaYC"],
                        request["HoTen"],
                        request["NgayGui"],
                        request["NoiDung"],
                        contract["NgayKetThuc"] if contract else "—"
                    )
                )

        def decide(approved):
            selection = table.selection()

            if not selection:
                return messagebox.showwarning(
                    "Thông báo",
                    "Vui lòng chọn một yêu cầu.",
                    parent=win
                )

            request = db.query(
                "SELECT * FROM YeuCau WHERE MaYC=?",
                (int(selection[0]),), one=True
            )

            if approved:
                contract = next(
                    (
                        r for r in self.rows
                        if r["MaSV"] == request["MaSV"]
                        and r["TrangThai"] == "Đang thuê"
                    ),
                    None
                )

                new_date = requested_date(request["NoiDung"])

                if not contract:
                    return error(
                        "Sinh viên này không còn hợp đồng đang thuê."
                    )

                if not new_date:
                    return error(
                        "Không đọc được ngày gia hạn trong yêu cầu."
                    )

                new_end = parse_date(new_date).date()

                if new_end <= parse_date(
                    contract["NgayKetThuc"]
                ).date():
                    return error(
                        "Ngày xin gia hạn không sau ngày "
                        "kết thúc hiện tại."
                    )

                db.execute(
                    "UPDATE HopDong SET NgayKetThuc=? WHERE MaHD=?",
                    (fmt(new_end), contract["MaHD"])
                )

            db.execute(
                "UPDATE YeuCau SET TrangThai=? WHERE MaYC=?",
                (
                    "Đã duyệt" if approved else "Từ chối",
                    request["MaYC"]
                )
            )

            self.refresh()
            load()

        bar = tk.Frame(win, bg=PAGE_BG)
        bar.pack(fill="x", padx=16, pady=10)

        ActionButton(
            bar, "Duyệt & gia hạn",
            lambda: decide(True),
            icon="detail", primary=True
        ).pack(side="left")

        ActionButton(
            bar, "Từ chối",
            lambda: decide(False),
            icon="close", fg="#B42318"
        ).pack(side="left", padx=7)

        ActionButton(
            bar, "Đóng", win.destroy
        ).pack(side="right")

        load()
        win.bind("<Escape>", lambda _e: win.destroy())
        win.grab_set()
