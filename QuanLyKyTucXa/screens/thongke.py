
import tkinter as tk
from tkinter import ttk

import database as db
from screens.base import FONT_TITLE, money


class ThongKeScreen(ttk.Frame):
    """Màn hình thống kê dùng đúng cấu trúc SQLite hiện tại."""

    def __init__(self, master, user=None):
        super().__init__(master)
        self.user = user
        self.configure(padding=0)

        # HEADER
        header = ttk.Frame(self)
        header.pack(fill="x", padx=16, pady=(14, 8))

        left = ttk.Frame(header)
        left.pack(side="left")

        ttk.Label(
            left,
            text="Thống kê & báo cáo",
            font=FONT_TITLE
        ).pack(anchor="w")

        ttk.Label(
            left,
            text="Theo dõi tình hình sinh viên, phòng ở và thu chi",
            foreground="#64748b",
            font=("Segoe UI", 9)
        ).pack(anchor="w")

        ttk.Button(
            header,
            text="Làm mới",
            command=self.refresh,
            style="Accent.TButton"
        ).pack(side="right", anchor="e")

        # LẤY DỮ LIỆU
        self.refresh_data()

        # 4 THẺ THỐNG KÊ
        cards = ttk.Frame(self)
        cards.pack(fill="x", padx=16, pady=(4, 12))

        self._card(
            cards, "Tổng sinh viên",
            str(self.total_sv), "Đang được quản lý", 0
        )

        self._card(
            cards, "Tỷ lệ lấp đầy",
            f"{self.occupancy}%",
            f"{self.occupied_beds}/{self.total_beds} giường", 1
        )

        self._card(
            cards, "Tổng đã thu",
            money(self.paid), "Theo dữ liệu hóa đơn", 2
        )

        self._card(
            cards, "Công nợ còn lại",
            money(self.debt), "Tổng tiền chưa thu", 3
        )

        # BIỂU ĐỒ
        mid = ttk.Frame(self)
        mid.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        chart_frame = ttk.LabelFrame(
            mid,
            text="  Doanh thu và công nợ theo tháng  ",
            padding=8
        )
        chart_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 8)
        )

        self.bar_canvas = tk.Canvas(
            chart_frame,
            height=235,
            bg="white",
            highlightthickness=1,
            highlightbackground="#e2e8f0"
        )
        self.bar_canvas.pack(fill="both", expand=True)
        self.bar_canvas.bind(
            "<Configure>",
            lambda _e: self.draw_bar()
        )

        legend = ttk.Frame(chart_frame)
        legend.pack(anchor="e", pady=(5, 0))

        ttk.Label(
            legend,
            text="● Đã thu",
            foreground="#2563eb"
        ).pack(side="left", padx=6)

        ttk.Label(
            legend,
            text="● Còn nợ",
            foreground="#f59e0b"
        ).pack(side="left")

        # BIỂU ĐỒ TRÒN
        donut_frame = ttk.LabelFrame(
            mid,
            text="  Tình hình thanh toán  ",
            padding=8
        )
        donut_frame.pack(side="right", fill="y")

        self.donut_canvas = tk.Canvas(
            donut_frame,
            width=190,
            height=190,
            bg="white",
            highlightthickness=0
        )
        self.donut_canvas.pack(pady=8)

        self.draw_donut(self.pct_paid)

        ttk.Label(
            donut_frame,
            text=f"Đã thu: {self.pct_paid}%",
            foreground="#16a34a"
        ).pack(anchor="w")

        ttk.Label(
            donut_frame,
            text=f"Còn nợ: {100-self.pct_paid}%",
            foreground="#d97706"
        ).pack(anchor="w")

        # PHẦN THỐNG KÊ BÊN DƯỚI
        bottom = ttk.Frame(self)
        bottom.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # TOP PHÒNG
        room_box = ttk.LabelFrame(
            bottom,
            text="  Top phòng có doanh thu cao nhất  ",
            padding=6
        )
        room_box.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 6)
        )

        cols = ("room", "type", "paid")

        self.room_tree = ttk.Treeview(
            room_box,
            columns=cols,
            show="headings",
            height=5
        )

        for key, label, width in [
            ("room", "Tên phòng", 95),
            ("type", "Loại phòng", 125),
            ("paid", "Đã thu", 110)
        ]:
            self.room_tree.heading(key, text=label)
            self.room_tree.column(
                key,
                width=width,
                anchor="center"
            )

        self.room_tree.pack(fill="both", expand=True)
        self.load_top_rooms()

        # THỐNG KÊ PHÒNG
        status_box = ttk.LabelFrame(
            bottom,
            text="  Thống kê phòng ở  ",
            padding=8
        )
        status_box.pack(
            side="left",
            fill="both",
            expand=True,
            padx=6
        )

        for label, value, color in [
            ("Phòng đang hoạt động", self.active_rooms, "#2563eb"),
            ("Phòng bảo trì", self.maintenance_rooms, "#d97706"),
            ("Phòng còn chỗ", self.available_rooms, "#16a34a"),
            ("Phòng đã đầy", self.full_rooms, "#7c3aed")
        ]:
            self._quick_row(
                status_box, label, str(value), color
            )

        # THỐNG KÊ HÓA ĐƠN
        quick = ttk.LabelFrame(
            bottom,
            text="  Thống kê hóa đơn  ",
            padding=8
        )
        quick.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(6, 0)
        )

        self._quick_row(
            quick, "Tổng số hóa đơn",
            str(self.invoice_count), "#2563eb"
        )

        self._quick_row(
            quick, "Doanh thu trung bình",
            money(self.avg_paid), "#16a34a"
        )

        self._quick_row(
            quick, "Hóa đơn còn nợ",
            str(self.unpaid_count), "#d97706"
        )

    # LẤY DỮ LIỆU DATABASE
    def refresh_data(self):
        self.total_sv = db.query(
            "SELECT COUNT(*) c FROM SinhVien",
            one=True
        )["c"]

        rooms = db.danh_sach_phong()

        self.total_rooms = len(rooms)

        self.total_beds = sum(
            int(p.get("SoGiuong") or 0) for p in rooms
        )

        self.occupied_beds = sum(
            min(
                int(p.get("DangO") or 0),
                int(p.get("SoGiuong") or 0)
            )
            for p in rooms
        )

        self.occupancy = (
            round(self.occupied_beds / self.total_beds * 100)
            if self.total_beds else 0
        )

        self.active_rooms = sum(
            1 for p in rooms
            if p.get("TrangThai") == "Hoạt động"
        )

        self.maintenance_rooms = sum(
            1 for p in rooms
            if p.get("TinhTrang") == "Bảo trì"
        )

        self.available_rooms = sum(
            1 for p in rooms
            if p.get("TinhTrang") in ("Trống", "Còn chỗ")
        )

        self.full_rooms = sum(
            1 for p in rooms
            if p.get("TinhTrang") == "Đầy"
        )

        sums = db.query(
            "SELECT COALESCE(SUM(DaThu),0) paid, "
            "COALESCE(SUM(MAX(COALESCE(TongTien,0)-"
            "COALESCE(DaThu,0),0)),0) debt "
            "FROM HoaDon",
            one=True
        )

        self.paid = sums["paid"] or 0
        self.debt = sums["debt"] or 0

        total = self.paid + self.debt

        self.pct_paid = (
            round(self.paid / total * 100)
            if total else 0
        )

        self.invoice_count = db.query(
            "SELECT COUNT(*) c FROM HoaDon",
            one=True
        )["c"]

        self.unpaid_count = db.query(
            "SELECT COUNT(*) c FROM HoaDon "
            "WHERE COALESCE(TongTien,0)>COALESCE(DaThu,0)",
            one=True
        )["c"]

        self.avg_paid = (
            round(self.paid / self.invoice_count)
            if self.invoice_count else 0
        )

        self.bar_data = list(reversed(db.query(
            "SELECT Thang, COALESCE(SUM(DaThu),0) paid, "
            "COALESCE(SUM(MAX(COALESCE(TongTien,0)-"
            "COALESCE(DaThu,0),0)),0) debt "
            "FROM HoaDon GROUP BY Thang "
            "ORDER BY Thang DESC LIMIT 6"
        )))

    # LÀM MỚI
    def refresh(self):
        parent = self.master
        user = self.user

        self.destroy()

        fresh = ThongKeScreen(parent, user)
        fresh.pack(fill="both", expand=True)

    # THẺ THỐNG KÊ
    def _card(self, parent, title, value, note, col):
        frame = ttk.Frame(
            parent,
            relief="solid",
            borderwidth=1,
            padding=11
        )

        frame.grid(
            row=0,
            column=col,
            sticky="nsew",
            padx=4
        )

        parent.columnconfigure(col, weight=1)

        ttk.Label(
            frame,
            text=title,
            foreground="#64748b",
            font=("Segoe UI", 9)
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text=value,
            font=("Segoe UI", 17, "bold")
        ).pack(anchor="w", pady=(3, 1))

        ttk.Label(
            frame,
            text=note,
            foreground="#64748b",
            font=("Segoe UI", 8)
        ).pack(anchor="w")

    # DÒNG THỐNG KÊ NHANH
    def _quick_row(self, parent, label, value, color):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=5)

        ttk.Label(
            row,
            text=label,
            font=("Segoe UI", 9)
        ).pack(side="left")

        ttk.Label(
            row,
            text=value,
            font=("Segoe UI", 9, "bold"),
            foreground=color
        ).pack(side="right")

    # BIỂU ĐỒ CỘT
    def draw_bar(self):
        c = self.bar_canvas
        c.delete("all")

        w = c.winfo_width()
        h = c.winfo_height()

        if w < 80 or h < 80:
            return

        if not self.bar_data:
            c.create_text(
                w / 2, h / 2,
                text="Chưa có dữ liệu hóa đơn",
                fill="#94a3b8"
            )
            return

        top = max(
            [
                (r["paid"] or 0) + (r["debt"] or 0)
                for r in self.bar_data
            ] or [0]
        ) or 1

        n = len(self.bar_data)
        slot = (w - 55) / n
        base = h - 30
        chart_h = h - 65

        for i, row in enumerate(self.bar_data):
            x = 35 + i * slot + slot / 2
            bw = max(8, slot * 0.23)

            for offset, key, color in [
                (-bw - 2, "paid", "#2563eb"),
                (2, "debt", "#f59e0b")
            ]:
                value = row[key] or 0
                bh = chart_h * value / top

                c.create_rectangle(
                    x + offset,
                    base - bh,
                    x + offset + bw,
                    base,
                    fill=color,
                    outline=""
                )

            c.create_text(
                x,
                h - 12,
                text=str(row["Thang"]),
                font=("Segoe UI", 8),
                fill="#475569"
            )

        c.create_line(
            25, base, w - 10, base,
            fill="#cbd5e1"
        )

    # BIỂU ĐỒ TRÒN
    def draw_donut(self, pct):
        c = self.donut_canvas
        c.delete("all")

        cx, cy, radius = 95, 95, 68

        c.create_oval(
            cx - radius,
            cy - radius,
            cx + radius,
            cy + radius,
            fill="#e2e8f0",
            outline=""
        )

        if pct > 0:
            c.create_arc(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                start=90,
                extent=-pct * 3.6,
                fill="#22c55e",
                outline=""
            )

        c.create_oval(
            cx - 42,
            cy - 42,
            cx + 42,
            cy + 42,
            fill="white",
            outline=""
        )

        c.create_text(
            cx,
            cy - 7,
            text=f"{pct}%",
            font=("Segoe UI", 19, "bold"),
            fill="#166534"
        )

        c.create_text(
            cx,
            cy + 15,
            text="Đã thu",
            font=("Segoe UI", 8),
            fill="#64748b"
        )

    # TOP PHÒNG DOANH THU CAO
    def load_top_rooms(self):
        rows = db.query(
            "SELECT p.TenPhong, l.TenLoai, "
            "COALESCE(SUM(h.DaThu),0) paid "
            "FROM Phong p "
            "JOIN LoaiPhong l ON l.MaLoai=p.MaLoai "
            "LEFT JOIN HoaDon h ON h.MaPhong=p.MaPhong "
            "GROUP BY p.MaPhong, p.TenPhong, l.TenLoai "
            "ORDER BY paid DESC LIMIT 5"
        )

        for row in rows:
            self.room_tree.insert(
                "",
                "end",
                values=(
                    row["TenPhong"],
                    row["TenLoai"],
                    money(row["paid"])
                )
            )
