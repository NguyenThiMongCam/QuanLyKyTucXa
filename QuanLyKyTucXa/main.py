"""Ứng dụng Quản lý Ký túc xá - chạy: python main.py"""
import tkinter as tk
from tkinter import ttk

import database as db
from screens.dashboard import DashboardScreen
from screens.dichvu import DichVuScreen
from screens.hoadon import HoaDonScreen
from screens.hopdong import HopDongScreen
from screens.login import PAGE_BG, LoginScreen
from screens.sidebar import Sidebar
from screens.nhanvien import NhanVienScreen
from screens.phong import PhongScreen
from screens.sinhvien import SinhVienScreen
from screens.student_home import StudentShell
from screens.thongke import ThongKeScreen

MENU = [("Trang chủ", "home", DashboardScreen, False, "dashboard"), ("Sinh viên", "student", SinhVienScreen, False, "sinhvien"),
        ("Phòng", "room", PhongScreen, False, "phong"), ("Hợp đồng", "contract", HopDongScreen, False, "hopdong"),
        ("Hóa đơn", "bill", HoaDonScreen, False, "hoadon"), ("Dịch vụ", "service", DichVuScreen, False, "dichvu"),
        ("Thống kê", "stats", ThongKeScreen, False, "thongke"), ("Nhân viên", "staff", NhanVienScreen, True, "nhanvien")]


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
        self.minsize(1100, 680)
        StudentShell(self, self.user, self.show_login).pack(fill="both", expand=True)

    # ------------------------------------------------------------------ giao diện quản trị
    def show_main(self):
        self._clear()
        self.minsize(1100, 640)
        role = "Quản trị viên" if self.user["VaiTro"] == "admin" else "Nhân viên"
        items = [(i, text, icon) for i, (text, icon, _cls, admin_only, _n) in enumerate(MENU)
                 if not admin_only or self.user["VaiTro"] == "admin"]
        name = self.user["HoTen"]
        self.side = Sidebar(self, role if name == role else f"{role} ({name})", items,
                            lambda i: self.open(i), self.show_login)
        self.side.pack(side="left", fill="y")
        self.content = tk.Frame(self, bg=PAGE_BG)
        self.content.pack(side="left", fill="both", expand=True)
        self.open(0)

    def open(self, index):
        self.side.set_active(index)
        for w in self.content.winfo_children():
            w.destroy()
        self.page = MENU[index][2](self.content, self.user)
        self.page.pack(fill="both", expand=True)

    def goto(self, name, action=None, keyword=None, flt=None):
        """Chuyển sang trang `name` (dashboard, sinhvien, phong, hopdong, hoadon, ...) - dùng cho nút ở Trang chủ.
        keyword: điền sẵn ô tìm kiếm; flt: chọn sẵn bộ lọc; action: tên phương thức chạy sau khi mở (vd. on_add)."""
        idx = next((i for i, m in enumerate(MENU) if m[4] == name), None)
        if idx is None or (MENU[idx][3] and self.user["VaiTro"] != "admin"):
            return
        self.open(idx)
        page = self.page
        if keyword and hasattr(page, "kw"):
            page.kw.set(keyword)
            (page.apply if hasattr(page, "apply") else page.refresh)()
        if flt and hasattr(page, "set_filter"):
            page.set_filter(flt)
        if action and hasattr(page, action):
            self.after(80, getattr(page, action))


if __name__ == "__main__":
    App().mainloop()