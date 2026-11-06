import tkinter as tk
from datetime import date
from tkinter import ttk
import database as db
from screens.base import FONT_TITLE, money


def scalar(sql, params=()):
    return db.query(sql, params, one=True)[0] or 0


class DashboardScreen(ttk.Frame):
    def __init__(self, master, user):
        super().__init__(master)
        ttk.Label(self, text=f"Xin chào, {user['HoTen']}", font=FONT_TITLE).pack(anchor="w", padx=16, pady=(14, 2))
        ttk.Label(self, text="Tổng quan hoạt động ký túc xá").pack(anchor="w", padx=16)
        phongs = db.danh_sach_phong()
        thang = date.today().strftime("%Y-%m")
        cards = [
            ("Tổng số sinh viên", scalar("SELECT COUNT(*) FROM SinhVien"), "#2563eb"),
            ("Sinh viên đang ở", scalar("SELECT COUNT(DISTINCT MaSV) FROM HopDong WHERE TrangThai='Đang thuê'"), "#0891b2"),
            ("Tổng số phòng", len(phongs), "#7c3aed"),
            ("Phòng còn chỗ trống", sum(1 for p in phongs if p["TinhTrang"] in ("Trống", "Còn chỗ")), "#16a34a"),
            (f"Doanh thu tháng {thang}", money(scalar("SELECT SUM(DaThu) FROM HoaDon WHERE Thang=?", (thang,))) + " đ", "#ea580c"),
            ("Tổng công nợ", money(scalar("SELECT SUM(TongTien-DaThu) FROM HoaDon")) + " đ", "#dc2626"),
        ]
        grid = ttk.Frame(self)
        grid.pack(fill="x", padx=12, pady=16)
        for i, (name, val, color) in enumerate(cards):
            c = tk.Frame(grid, bg=color, padx=18, pady=14)
            c.grid(row=i // 3, column=i % 3, padx=8, pady=8, sticky="nsew")
            tk.Label(c, text=name, bg=color, fg="white", font=("Segoe UI", 10)).pack(anchor="w")
            tk.Label(c, text=str(val), bg=color, fg="white", font=("Segoe UI", 20, "bold")).pack(anchor="w")
            grid.columnconfigure(i % 3, weight=1)
#   grid = ttk.Frame(self)
#         grid.pack(fill="x", padx=12, pady=16)
#         for i, (name, val, color) in enumerate(cards):
#             c = tk.Frame(grid, bg=color, padx=18, pady=14)
#             c.grid(row=i // 3, column=i % 3, padx=8, pady=8, sticky="nsew")
#             tk.Label(c, text=name, bg=color, fg="white", font=("Segoe UI", 10)).pack(anchor="w")
#             tk.Label(c, text=str(val), bg=color, fg="white", font=("Segoe UI", 20, "bold")).pack(anchor="w")
#             grid.columnconfigure(i % 3, weight=1)
