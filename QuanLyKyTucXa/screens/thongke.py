import tkinter as tk
from tkinter import ttk
import database as db
from screens.base import FONT_TITLE, money


class ThongKeScreen(ttk.Frame):
    def __init__(self, master, user=None):
        super().__init__(master)
        ttk.Label(self, text="Thống kê & báo cáo", font=FONT_TITLE).pack(anchor="w", padx=16, pady=(14, 6))

        info = ttk.Frame(self)
        info.pack(fill="x", padx=16)
        gt = db.query("SELECT GioiTinh, COUNT(*) c FROM SinhVien GROUP BY GioiTinh")
        ttk.Label(info, text="Sinh viên theo giới tính: " + (", ".join(f"{r['GioiTinh'] or 'Khác'}: {r['c']}" for r in gt) or "chưa có dữ liệu")).pack(anchor="w")
        counts = {}
        for p in db.danh_sach_phong():
            counts[p["TinhTrang"]] = counts.get(p["TinhTrang"], 0) + 1
        ttk.Label(info, text="Phòng theo trạng thái: " + (", ".join(f"{k}: {v}" for k, v in counts.items()) or "chưa có dữ liệu")).pack(anchor="w", pady=2)

        ttk.Label(self, text="Doanh thu đã thu theo tháng (đồng)", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        self.data = list(reversed(db.query(
            "SELECT Thang, SUM(DaThu) v FROM HoaDon GROUP BY Thang ORDER BY Thang DESC LIMIT 12")))
        self.canvas = tk.Canvas(self, height=320, bg="white", highlightthickness=1, highlightbackground="#cbd5e1")
        self.canvas.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.canvas.bind("<Configure>", lambda _e: self.draw())

    def draw(self):
        c = self.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if not self.data:
            c.create_text(w / 2, h / 2, text="Chưa có dữ liệu hóa đơn")
            return
        top = max(r["v"] for r in self.data) or 1
        n = len(self.data)
        slot = (w - 60) / n
        for i, r in enumerate(self.data):
            bh = (h - 70) * r["v"] / top
            x0 = 40 + i * slot + slot * 0.2
            x1 = 40 + (i + 1) * slot - slot * 0.2
            c.create_rectangle(x0, h - 30 - bh, x1, h - 30, fill="#2563eb", outline="")
            c.create_text((x0 + x1) / 2, h - 30 - bh - 10, text=money(r["v"]), font=("Segoe UI", 8))
            c.create_text((x0 + x1) / 2, h - 14, text=r["Thang"], font=("Segoe UI", 8))
        c.create_line(35, h - 30, w - 10, h - 30, fill="#94a3b8")
