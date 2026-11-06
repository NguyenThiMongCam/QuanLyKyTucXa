"""Ứng dụng Quản lý Ký túc xá - chạy: python main.py"""
import tkinter as tk
from tkinter import ttk

import database as db
from screens.dashboard import DashboardScreen
from screens.dichvu import DichVuScreen
from screens.hoadon import HoaDonScreen
from screens.hopdong import HopDongScreen
from screens.nhanvien import NhanVienScreen
from screens.phong import PhongScreen
from screens.sinhvien import SinhVienScreen
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
        self.geometry("1150x680")
        self.minsize(900, 560)
        ttk.Style(self).configure("Treeview", rowheight=26)
        self.user = None
        self.content = None
        self.show_login()

    def _clear(self):
        for w in self.winfo_children():
            w.destroy()

    def show_login(self):
        self._clear()
        self.user = None
        box = ttk.Frame(self, padding=30)
        box.place(relx=0.5, rely=0.45, anchor="center")
        ttk.Label(box, text="QUẢN LÝ KÝ TÚC XÁ", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 18))
        ttk.Label(box, text="Tên đăng nhập").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Label(box, text="Mật khẩu").grid(row=2, column=0, sticky="w", pady=6)
        self.u, self.p = ttk.Entry(box, width=28), ttk.Entry(box, width=28, show="*")
        self.u.grid(row=1, column=1, padx=8)
        self.p.grid(row=2, column=1, padx=8)
        self.msg = ttk.Label(box, foreground="#dc2626")
        self.msg.grid(row=3, column=0, columnspan=2, pady=6)
        ttk.Button(box, text="Đăng nhập", command=self.do_login).grid(row=4, column=0, columnspan=2, pady=4)
        self.u.focus()
        self.bind("<Return>", lambda _e: self.do_login())

    def do_login(self):
        user = db.login(self.u.get().strip(), self.p.get())
        if not user:
            self.msg.config(text="Sai tên đăng nhập hoặc mật khẩu.")
            return
        self.unbind("<Return>")
        self.user = user
        self.show_main()

    def show_main(self):
        self._clear()
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
# if __name__ == "__main__":
#     App().mainloop()
