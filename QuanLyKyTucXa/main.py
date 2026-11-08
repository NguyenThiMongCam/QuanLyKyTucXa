"""Ứng dụng Quản lý Ký túc xá - chạy: python main.py"""
import tkinter as tk
from tkinter import ttk

import database as db
from screens.dashboard import DashboardScreen
from screens.dichvu import DichVuScreen
from screens.hoadon import HoaDonScreen
from screens.hopdong import HopDongScreen
from screens.login import PRIMARY, LoginScreen
from screens.nhanvien import NhanVienScreen
from screens.phong import PhongScreen
from screens.sinhvien import SinhVienScreen
from screens.student_home import StudentHomeScreen
from screens.thongke import ThongKeScreen

MENU = [("🏠 Trang chủ", DashboardScreen, False), ("🎓 Sinh viên", SinhVienScreen, False),
        ("🛏 Phòng", PhongScreen, False), ("📄 Hợp đồng", HopDongScreen, False),
        ("💰 Hóa đơn", HoaDonScreen, False), ("💡 Dịch vụ", DichVuScreen, False),
        ("📊 Thống kê", ThongKeScreen, False), ("👤 Nhân viên", NhanVienScreen, True)]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        db.init_db()
        self.title("Quản lý ký túc xá")
        self.geometry("1180x740")
        ttk.Style(self).configure("Treeview", rowheight=26)
        self.user = None
        self.content = None
        self.show_login()

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    # ------------------------------------------------------------------ đăng nhập
    def show_login(self):
        self._clear()
        self.user = None
        self.minsize(980, 700)
        LoginScreen(self, self.on_login).pack(fill="both", expand=True)

    def on_login(self, user, kind):
        """kind: 'staff' (admin/nhân viên) hoặc 'student' (sinh viên)."""
        self.user = user
        if kind == "student":
            self.show_student()
        else:
            self.show_main()

    # ------------------------------------------------------------------ giao diện sinh viên
    def show_student(self):
        self._clear()
        self.minsize(900, 560)
        bar = tk.Frame(self, bg=PRIMARY)
        bar.pack(fill="x")
        tk.Label(bar, text="KÝ TÚC XÁ SINH VIÊN", bg=PRIMARY, fg="white",
                 font=("Segoe UI", 13, "bold")).pack(side="left", padx=16, pady=12)
        tk.Button(bar, text="⏻ Đăng xuất", bg=PRIMARY, fg="white", relief="flat", cursor="hand2",
                  activebackground="#0B3C8C", activeforeground="white", font=("Segoe UI", 10, "bold"),
                  command=self.show_login).pack(side="right", padx=12)
        StudentHomeScreen(self, self.user).pack(fill="both", expand=True)

    # ------------------------------------------------------------------ giao diện quản trị
    def show_main(self):
        self._clear()
        self.minsize(900, 560)
        side = tk.Frame(self, bg="#1e293b", width=190)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Label(side, text="KÝ TÚC XÁ", bg="#1e293b", fg="white", font=("Segoe UI", 14, "bold")).pack(pady=(18, 2))
        tk.Label(side, text=f"{self.user['HoTen']} ({self.user['VaiTro']})", bg="#1e293b", fg="#94a3b8",
                 font=("Segoe UI", 9), wraplength=170).pack(pady=(0, 14))
        for text, cls, admin_only in MENU:
            if admin_only and self.user["VaiTro"] != "admin":
                continue
            tk.Button(side, text=text, anchor="w", padx=16, bg="#1e293b", fg="white", relief="flat",
                      activebackground="#334155", activeforeground="white", font=("Segoe UI", 11),
                      command=lambda c=cls: self.open(c)).pack(fill="x", pady=1)
        tk.Button(side, text="⏻ Đăng xuất", anchor="w", padx=16, bg="#1e293b", fg="#fca5a5", relief="flat",
                  activebackground="#334155", font=("Segoe UI", 11), command=self.show_login).pack(side="bottom", fill="x", pady=12)
        self.content = ttk.Frame(self)
        self.content.pack(side="left", fill="both", expand=True)
        self.open(DashboardScreen)

    def open(self, cls):
        for w in self.content.winfo_children():
            w.destroy()
        cls(self.content, self.user).pack(fill="both", expand=True)


if __name__ == "__main__":
    App().mainloop()
