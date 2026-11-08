"""Trang chủ dành cho sinh viên (sau khi đăng nhập bằng mã sinh viên)."""
import tkinter as tk
from tkinter import ttk

import database as db
from screens.base import FONT_TITLE, Table, money


class StudentHomeScreen(ttk.Frame):
    def __init__(self, master, user):
        super().__init__(master)
        self.user = user
        ttk.Label(self, text=f"Xin chào, {user['HoTen']}", font=FONT_TITLE).pack(anchor="w", padx=16, pady=(14, 0))
        ttk.Label(self, text=f"Mã SV: {user['MaSV']}  ·  Lớp: {user['Lop'] or '-'}  ·  SĐT: {user['SDT'] or '-'}"
                  ).pack(anchor="w", padx=16, pady=(2, 10))

        hd = db.query("""SELECT h.NgayBatDau, h.NgayKetThuc, p.MaPhong, p.TenPhong, p.Tang, l.TenLoai, l.GiaThue
                         FROM HopDong h JOIN Phong p ON p.MaPhong=h.MaPhong
                         JOIN LoaiPhong l ON l.MaLoai=p.MaLoai
                         WHERE h.MaSV=? AND h.TrangThai='Đang thuê' ORDER BY h.MaHD DESC""",
                      (user["MaSV"],), one=True)

        room = ttk.LabelFrame(self, text="Phòng đang ở", padding=12)
        room.pack(fill="x", padx=16, pady=6)
        if hd:
            ttk.Label(room, text=f"Phòng {hd['TenPhong']} · Tầng {hd['Tang']} · {hd['TenLoai']}",
                      font=("Segoe UI", 11, "bold")).pack(anchor="w")
            ttk.Label(room, text=f"Hợp đồng: {hd['NgayBatDau']} → {hd['NgayKetThuc']}  ·  "
                                 f"Giá: {money(hd['GiaThue'])} đ/người/tháng").pack(anchor="w", pady=(4, 0))
        else:
            ttk.Label(room, text="Bạn chưa ở ký túc xá. Vui lòng liên hệ Ban quản lý để đăng ký phòng."
                      ).pack(anchor="w")
            return

        bills = ttk.LabelFrame(self, text="Hóa đơn gần đây của phòng", padding=8)
        bills.pack(fill="both", expand=True, padx=16, pady=6)
        table = Table(bills, [("Thang", "Tháng", 120), ("TongTien", "Tổng tiền (đ)", 160),
                              ("TrangThai", "Trạng thái", 140)])
        table.pack(fill="both", expand=True)
        rows = db.query("SELECT MaHDon, Thang, TongTien, TrangThai FROM HoaDon WHERE MaPhong=? "
                        "ORDER BY MaHDon DESC LIMIT 6", (hd["MaPhong"],))
        table.load([{"Thang": r["Thang"], "TongTien": money(r["TongTien"]), "TrangThai": r["TrangThai"]}
                    for r in rows])
