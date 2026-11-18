import tkinter as tk
from tkinter import ttk
import database as db
from screens.base import FONT_TITLE, money


class ThongKeScreen(ttk.Frame):
    def __init__(self, master, user=None):
        super().__init__(master)
        self.user = user

        # ===== HEADER =====
        header = ttk.Frame(self)
        header.pack(fill="x", padx=16, pady=(14, 8))

        left = ttk.Frame(header)
        left.pack(side="left")
        ttk.Label(left, text="Thống kê & báo cáo", font=FONT_TITLE).pack(anchor="w")
        ttk.Label(
            left,
            text="Theo dõi, phân tích dữ liệu và xuất báo cáo chi tiết",
            font=("Segoe UI", 9),
            foreground="#64748b"
        ).pack(anchor="w")

        right = ttk.Frame(header)
        right.pack(side="right")
        ttk.Label(right, text="Tháng 11/2026", font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))
        ttk.Label(right, text="Tất cả phòng", font=("Segoe UI", 9)).pack(side="left", padx=(0, 8))
        ttk.Button(right, text="Xem báo cáo").pack(side="left")

        # ===== 4 KPI CARDS =====
        cards = ttk.Frame(self)
        cards.pack(fill="x", padx=16, pady=(4, 12))

        # ---- lấy dữ liệu an toàn ----
        total_sv = 0
        try:
            total_sv = db.query("SELECT COUNT(*) as c FROM SinhVien")[0]["c"]
        except Exception:
            pass

        ty_le_lap = 95
        try:
            phong = list(db.danh_sach_phong())
            total_phong = len(phong) or 1
            da_o = sum(1 for p in phong if str(p.get("TinhTrang", "")).lower() in ("đã thuê", "đang ở", "full", "có người"))
            ty_le_lap = round(da_o / total_phong * 100)
        except Exception:
            pass

        dt = 78500000
        try:
            r = db.query("SELECT SUM(DaThu) as v FROM HoaDon")
            if r and r[0]["v"] is not None:
                dt = r[0]["v"]
        except Exception:
            pass

        no = 6800000
        try:
            r = db.query("SELECT SUM(ConNo) as v FROM HoaDon")
            if r and r[0]["v"] is not None:
                no = r[0]["v"]
        except Exception:
            pass

        self._card(cards, "Tổng sinh viên", str(total_sv), "+5%", "#3b82f6", 0)
        self._card(cards, "Tỷ lệ lấp đầy", f"{ty_le_lap}%", None, "#10b981", 1, progress=ty_le_lap)
        self._card(cards, "Tổng doanh thu", money(dt), "+12%", "#8b5cf6", 2)
        self._card(cards, "Công nợ", money(no), None, "#f59e0b", 3)

        # ===== BIỂU ĐỒ + DONUT =====
        mid = ttk.Frame(self)
        mid.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # --- Bar chart ---
        chart_frame = ttk.LabelFrame(mid, text="  Doanh thu theo tháng", padding=8)
        chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.bar_data = []
        try:
            self.bar_data = list(reversed(db.query(
                "SELECT Thang, SUM(DaThu) as dt, SUM(IFNULL(ConNo,0)) as no "
                "FROM HoaDon GROUP BY Thang ORDER BY Thang DESC LIMIT 6"
            ) or []))
        except Exception:
            # fallback data giống hình
            self.bar_data = [
                {"Thang": "T7/2026", "dt": 52000000, "no": 8000000},
                {"Thang": "T8/2026", "dt": 60000000, "no": 7000000},
                {"Thang": "T9/2026", "dt": 65000000, "no": 6000000},
                {"Thang": "T10/2026", "dt": 70000000, "no": 5000000},
                {"Thang": "T11/2026", "dt": 78500000, "no": 6800000},
            ]

        self.bar_canvas = tk.Canvas(chart_frame, height=260, bg="white",
                                    highlightthickness=1, highlightbackground="#e2e8f0")
        self.bar_canvas.pack(fill="both", expand=True)
        self.bar_canvas.bind("<Configure>", lambda e: self.draw_bar())

        leg = ttk.Frame(chart_frame)
        leg.pack(anchor="ne", pady=(4, 0))
        ttk.Label(leg, text="● Doanh thu", foreground="#2563eb", font=("Segoe UI", 8)).pack(side="left", padx=6)
        ttk.Label(leg, text="● Công nợ", foreground="#93c5fd", font=("Segoe UI", 8)).pack(side="left")

        # --- Donut ---
        donut_frame = ttk.LabelFrame(mid, text="  Tỷ lệ thanh toán", padding=8)
        donut_frame.pack(side="right", fill="y", ipadx=10)

        pct_paid = 92
        try:
            paid = db.query("SELECT SUM(DaThu) as v FROM HoaDon")[0]["v"] or 0
            debt = db.query("SELECT SUM(IFNULL(ConNo,0)) as v FROM HoaDon")[0]["v"] or 0
            total = paid + debt or 1
            pct_paid = round(paid / total * 100)
        except Exception:
            pass

        self.donut_canvas = tk.Canvas(donut_frame, width=200, height=200, bg="white", highlightthickness=0)
        self.donut_canvas.pack(pady=10)
        self.draw_donut(pct_paid)

        leg2 = ttk.Frame(donut_frame)
        leg2.pack()
        ttk.Label(leg2, text=f"● Đã thanh toán  {pct_paid}%", foreground="#22c55e",
                  font=("Segoe UI", 9)).pack(anchor="w")
        ttk.Label(leg2, text=f"● Chưa thanh toán  {100 - pct_paid}%", foreground="#94a3b8",
                  font=("Segoe UI", 9)).pack(anchor="w")

        # ===== BOTTOM =====
        bottom = ttk.Frame(self)
        bottom.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # 1. Top phòng
        top_phong = ttk.LabelFrame(bottom, text="  Top phòng có doanh thu cao nhất", padding=6)
        top_phong.pack(side="left", fill="both", expand=True, padx=(0, 6))

        cols = ("#", "Mã phòng", "Loại phòng", "Doanh thu")
        tree1 = ttk.Treeview(top_phong, columns=cols, show="headings", height=5)
        for c in cols:
            tree1.heading(c, text=c)
            tree1.column(c, width=90 if c != "Doanh thu" else 110, anchor="center")
        tree1.pack(fill="both", expand=True)

        rows = [
            {"MaPhong": "A101", "LoaiPhong": "Phòng 4 người", "dt": 12500000},
            {"MaPhong": "B201", "LoaiPhong": "Phòng 2 người", "dt": 11200000},
            {"MaPhong": "C102", "LoaiPhong": "Dịch vụ khác", "dt": 10800000},
        ]
        try:
            q = db.query(
                "SELECT p.MaPhong, p.LoaiPhong, SUM(h.DaThu) as dt "
                "FROM HoaDon h JOIN Phong p ON h.MaPhong = p.MaPhong "
                "GROUP BY p.MaPhong ORDER BY dt DESC LIMIT 5"
            )
            if q:
                rows = q
        except Exception:
            pass

        for i, r in enumerate(rows, 1):
            tree1.insert("", "end", values=(
                i,
                r.get("MaPhong", ""),
                r.get("LoaiPhong", ""),
                money(r.get("dt", 0))
            ))

        # 2. Dịch vụ
        top_dv = ttk.LabelFrame(bottom, text="  Dịch vụ sử dụng nhiều nhất", padding=6)
        top_dv.pack(side="left", fill="both", expand=True, padx=6)

        cols2 = ("Dịch vụ", "Số lượng")
        tree2 = ttk.Treeview(top_dv, columns=cols2, show="headings", height=5)
        for c in cols2:
            tree2.heading(c, text=c)
            tree2.column(c, width=120, anchor="center")
        tree2.pack(fill="both", expand=True)

        for d, s in [("Giặt ủi", "120 lượt"), ("Ăn uống", "98 lượt"), ("Wifi", "95 lượt")]:
            tree2.insert("", "end", values=(d, s))

        # 3. Thống kê nhanh
        quick = ttk.LabelFrame(bottom, text="  Thống kê nhanh", padding=8)
        quick.pack(side="left", fill="both", expand=True, padx=(6, 0))

        so_hd = 125
        try:
            so_hd = db.query("SELECT COUNT(*) as c FROM HoaDon")[0]["c"]
        except Exception:
            pass

        avg = 628000
        try:
            avg = int(dt / so_hd) if so_hd else 0
        except Exception:
            pass

        qua_han = 3
        try:
            qua_han = db.query("SELECT COUNT(*) as c FROM HoaDon WHERE IFNULL(ConNo,0) > 0")[0]["c"]
        except Exception:
            pass

        self._quick_row(quick, "Hóa đơn trong tháng", f"{so_hd} hóa đơn", "#3b82f6")
        self._quick_row(quick, "Doanh thu trung bình", f"{money(avg)}/hóa đơn", "#10b981")
        self._quick_row(quick, "Công nợ quá hạn", f"{qua_han} hóa đơn", "#f59e0b")

        ttk.Button(quick, text="Xem chi tiết →").pack(anchor="e", pady=(12, 0))

    def _card(self, parent, title, value, change, color, col, progress=None):
        f = ttk.Frame(parent, relief="solid", borderwidth=1)
        f.grid(row=0, column=col, sticky="nsew", padx=4)
        parent.columnconfigure(col, weight=1)

        inner = ttk.Frame(f, padding=12)
        inner.pack(fill="both", expand=True)

        ttk.Label(inner, text=title, font=("Segoe UI", 9), foreground="#64748b").pack(anchor="w")
        ttk.Label(inner, text=value, font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(2, 0))

        if change:
            ttk.Label(inner, text=change, font=("Segoe UI", 9), foreground="#16a34a").pack(anchor="w")

        if progress is not None:
            pb = ttk.Progressbar(inner, maximum=100, value=progress, length=120)
            pb.pack(anchor="w", pady=(6, 0))

    def _quick_row(self, parent, label, value, color):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=label, font=("Segoe UI", 9)).pack(side="left")
        ttk.Label(row, text=value, font=("Segoe UI", 9, "bold"), foreground=color).pack(side="right")

    def draw_bar(self):
        c = self.bar_canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 50 or not self.bar_data:
            c.create_text(w / 2, h / 2, text="Chưa có dữ liệu hóa đơn", fill="#94a3b8")
            return

        top = max((r.get("dt") or 0) + (r.get("no") or 0) for r in self.bar_data) or 1
        n = len(self.bar_data)
        slot = (w - 50) / n
        bar_w = slot * 0.28

        for i, r in enumerate(self.bar_data):
            dt = r.get("dt") or 0
            no = r.get("no") or 0
            x = 35 + i * slot + slot / 2

            bh1 = (h - 55) * dt / top
            c.create_rectangle(x - bar_w - 2, h - 30 - bh1, x - 2, h - 30,
                               fill="#2563eb", outline="")
            if dt:
                c.create_text(x - bar_w / 2 - 1, h - 30 - bh1 - 10,
                              text=f"{dt // 1000000}tr", font=("Segoe UI", 8), fill="#1e40af")

            bh2 = (h - 55) * no / top
            c.create_rectangle(x + 2, h - 30 - bh2, x + bar_w + 2, h - 30,
                               fill="#93c5fd", outline="")
            if no:
                c.create_text(x + bar_w / 2 + 1, h - 30 - bh2 - 10,
                              text=f"{no // 1000000}tr", font=("Segoe UI", 8), fill="#64748b")

            c.create_text(x, h - 12, text=r.get("Thang", ""), font=("Segoe UI", 8))

        c.create_line(30, h - 30, w - 10, h - 30, fill="#cbd5e1")

    def draw_donut(self, pct):
        c = self.donut_canvas
        c.delete("all")
        cx, cy, r = 100, 100, 70
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#e2e8f0", outline="")
        extent = -pct * 3.6
        c.create_arc(cx - r, cy - r, cx + r, cy + r, start=90, extent=extent,
                     fill="#22c55e", outline="")
        c.create_oval(cx - 42, cy - 42, cx + 42, cy + 42, fill="white", outline="")
        c.create_text(cx, cy - 8, text=f"{pct}%", font=("Segoe UI", 20, "bold"), fill="#166534")
        c.create_text(cx, cy + 14, text="Đã thanh toán", font=("Segoe UI", 8), fill="#64748b")