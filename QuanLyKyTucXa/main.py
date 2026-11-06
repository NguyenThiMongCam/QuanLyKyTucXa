
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

import database as db

from screens.dashboard import DashboardScreen
from screens.dichvu import DichVuScreen
from screens.hoadon import HoaDonScreen
from screens.hopdong import HopDongScreen
from screens.nhanvien import NhanVienScreen
from screens.phong import PhongScreen
from screens.sinhvien import SinhVienScreen
from screens.thongke import ThongKeScreen


# DANH SÁCH MENU QUẢN LÝ
MENU = [
    ("Trang chủ", DashboardScreen, False),
    ("Sinh viên", SinhVienScreen, False),
    ("Phòng", PhongScreen, False),
    ("Hợp đồng", HopDongScreen, False),
    ("Hóa đơn", HoaDonScreen, False),
    ("Dịch vụ", DichVuScreen, False),
    ("Thống kê", ThongKeScreen, False),
    ("Nhân viên", NhanVienScreen, True)
]

BLUE = "#0756A5"
DARK_BLUE = "#12345A"
LIGHT_BG = "#F1F5F9"
WHITE = "#FFFFFF"

REMEMBER_FILE = "login_config.json"


class App(tk.Tk):

    def __init__(self):
        super().__init__()

        db.init_db()

        self.title("Hệ thống quản lý ký túc xá - HUIT")
        self.geometry("1200x750")
        self.minsize(950, 620)
        self.configure(bg=LIGHT_BG)

        self.user = None
        self.role = tk.StringVar(value="student")
        self.student_status = tk.StringVar(value="current")
        self.content = None

        self.setup_style()
        self.show_login()

    # ==============================
    # GIAO DIỆN CHUNG
    # ==============================

    def setup_style(self):

        style = ttk.Style(self)

        style.theme_use("clam")

        style.configure(
            "TLabel",
            background=LIGHT_BG,
            foreground=DARK_BLUE,
            font=("Segoe UI", 10)
        )

        style.configure(
            "TEntry",
            padding=9
        )

        style.configure(
            "Treeview",
            rowheight=32,
            font=("Segoe UI", 10)
        )

        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
            background="#DBEAFE"
        )

    # ==============================
    # ĐỌC TÀI KHOẢN ĐÃ GHI NHỚ
    # ==============================

    def load_remembered(self):

        try:
            with open(REMEMBER_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("username", "")

        except (FileNotFoundError, json.JSONDecodeError):
            return ""

    def save_remembered(self):

        if self.remember.get():

            data = {
                "username": self.username.get().strip()
            }

            with open(REMEMBER_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)

        else:

            if os.path.exists(REMEMBER_FILE):
                os.remove(REMEMBER_FILE)

    # ==============================
    # MÀN HÌNH ĐĂNG NHẬP
    # ==============================

    def show_login(self):

        for widget in self.winfo_children():
            widget.destroy()

        self.user = None

        self.role.set("student")
        self.student_status.set("current")

        self.configure(bg=LIGHT_BG)

        # Thanh đầu trang HUIT
        header = tk.Frame(
            self,
            bg=BLUE,
            height=125
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="HUIT",
            bg=BLUE,
            fg=WHITE,
            font=("Segoe UI", 30, "bold")
        ).pack(pady=(12, 0))

        tk.Label(
            header,
            text="TRƯỜNG ĐẠI HỌC CÔNG THƯƠNG TP. HỒ CHÍ MINH",
            bg=BLUE,
            fg=WHITE,
            font=("Segoe UI", 15, "bold")
        ).pack()

        tk.Label(
            header,
            text="HỆ THỐNG QUẢN LÝ KÝ TÚC XÁ",
            bg=BLUE,
            fg="#DBEAFE",
            font=("Segoe UI", 10)
        ).pack(pady=5)

        # Khung đăng nhập
        card = tk.Frame(
            self,
            bg=WHITE,
            padx=35,
            pady=25,
            highlightthickness=1,
            highlightbackground="#CBD5E1"
        )

        card.place(
            relx=0.5,
            rely=0.56,
            anchor="center"
        )

        tk.Label(
            card,
            text="ĐĂNG NHẬP HỆ THỐNG",
            bg=WHITE,
            fg=BLUE,
            font=("Segoe UI", 19, "bold")
        ).pack(pady=(0, 20))

        # Chọn loại tài khoản
        tk.Label(
            card,
            text="VUI LÒNG CHỌN LOẠI TÀI KHOẢN",
            bg=WHITE,
            fg=DARK_BLUE,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        role_frame = tk.Frame(card, bg=WHITE)
        role_frame.pack(fill="x", pady=12)

        ttk.Radiobutton(
            role_frame,
            text="Sinh viên",
            variable=self.role,
            value="student",
            command=self.update_login_form
        ).pack(side="left", padx=(0, 35))

        ttk.Radiobutton(
            role_frame,
            text="Quản lý",
            variable=self.role,
            value="manager",
            command=self.update_login_form
        ).pack(side="left")

        # Tình trạng sinh viên
        self.status_frame = tk.Frame(card, bg=WHITE)

        tk.Label(
            self.status_frame,
            text="Tình trạng cư trú:",
            bg=WHITE,
            fg=DARK_BLUE,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")

        ttk.Radiobutton(
            self.status_frame,
            text="Sinh viên đang ở ký túc xá",
            variable=self.student_status,
            value="current"
        ).pack(anchor="w", pady=3)

        ttk.Radiobutton(
            self.status_frame,
            text="Sinh viên chưa ở ký túc xá",
            variable=self.student_status,
            value="new"
        ).pack(anchor="w", pady=3)

        self.status_frame.pack(fill="x", pady=5)

        # Tên đăng nhập
        tk.Label(
            card,
            text="Tên đăng nhập / Mã sinh viên",
            bg=WHITE,
            fg=DARK_BLUE,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(10, 5))

        self.username = ttk.Entry(card, width=42)
        self.username.pack(fill="x", ipady=4)

        # Mật khẩu
        tk.Label(
            card,
            text="Mật khẩu",
            bg=WHITE,
            fg=DARK_BLUE,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(12, 5))

        self.password = ttk.Entry(
            card,
            width=42,
            show="*"
        )
        self.password.pack(fill="x", ipady=4)

        # Ghi nhớ tài khoản
        self.remember = tk.BooleanVar(value=False)

        remembered = self.load_remembered()

        if remembered:
            self.username.insert(0, remembered)
            self.remember.set(True)

        ttk.Checkbutton(
            card,
            text="Ghi nhớ tài khoản trên máy này",
            variable=self.remember
        ).pack(anchor="w", pady=12)

        # Thông báo
        self.message = tk.Label(
            card,
            text="",
            bg=WHITE,
            fg="#DC2626",
            font=("Segoe UI", 9)
        )
        self.message.pack(pady=5)

        # Nút đăng nhập
        tk.Button(
            card,
            text="ĐĂNG NHẬP",
            command=self.login,
            bg=BLUE,
            fg=WHITE,
            activebackground="#064785",
            activeforeground=WHITE,
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            cursor="hand2",
            pady=12
        ).pack(fill="x", pady=5)

        tk.Label(
            card,
            text="Trường Đại học Công Thương TP. Hồ Chí Minh",
            bg=WHITE,
            fg="#64748B",
            font=("Segoe UI", 8)
        ).pack(pady=(12, 0))

        self.update_login_form()

        self.bind("<Return>", lambda event: self.login())

        self.username.focus()

    # ==============================
    # THAY ĐỔI LOẠI TÀI KHOẢN
    # ==============================

    def update_login_form(self):

        if self.role.get() == "student":

            self.status_frame.pack(fill="x", pady=5)

        else:

            self.status_frame.pack_forget()

        self.message.config(text="")

    # ==============================
    # KIỂM TRA ĐĂNG NHẬP
    # ==============================

    def login(self):

        username = self.username.get().strip()
        password = self.password.get()

        if not username or not password:

            self.message.config(
                text="Vui lòng nhập đầy đủ tài khoản và mật khẩu."
            )
            return

        # Sinh viên chưa ở không được đăng nhập
        if (
            self.role.get() == "student"
            and self.student_status.get() == "new"
        ):

            self.message.config(
                text="Sinh viên chưa ở KTX chưa được cấp quyền truy cập."
            )
            return

        # Kiểm tra tài khoản trong database
        user = db.login(username, password)

        if not user:

            self.message.config(
                text="Tài khoản hoặc mật khẩu không chính xác."
            )
            return

        role_name = str(user.get("VaiTro", "")).lower()

        # Đăng nhập quản lý
        if self.role.get() == "manager":

            if role_name not in ("admin", "quanly", "quản lý", "nhanvien"):

                self.message.config(
                    text="Tài khoản này không có quyền quản lý."
                )
                return

        # Đăng nhập sinh viên
        else:

            if role_name not in ("sinhvien", "sinh viên", "student"):

                self.message.config(
                    text="Tài khoản chưa được cấp quyền sinh viên."
                )
                return

            status = str(
                user.get(
                    "TrangThaiCuTru",
                    user.get("TrangThai", "")
                )
            ).lower()

            if status not in (
                "đang ở",
                "dang o",
                "đang thuê",
                "dang thue",
                "current"
            ):

                self.message.config(
                    text="Bạn chưa có quyền truy cập vì chưa ở KTX."
                )
                return

        self.save_remembered()

        self.unbind("<Return>")

        self.user = user

        if self.role.get() == "student":

            self.show_student_home()

        else:

            self.show_manager_home()

    # ==============================
    # GIAO DIỆN QUẢN LÝ
    # ==============================

    def show_manager_home(self):

        for widget in self.winfo_children():
            widget.destroy()

        self.configure(bg=LIGHT_BG)

        # Menu bên trái
        side = tk.Frame(
            self,
            bg=DARK_BLUE,
            width=225
        )
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        tk.Label(
            side,
            text="HUIT",
            bg=DARK_BLUE,
            fg=WHITE,
            font=("Segoe UI", 25, "bold")
        ).pack(pady=(25, 5))

        tk.Label(
            side,
            text="QUẢN LÝ KÝ TÚC XÁ",
            bg=DARK_BLUE,
            fg=WHITE,
            font=("Segoe UI", 10, "bold")
        ).pack(pady=(0, 25))

        for name, screen, admin_only in MENU:

            if admin_only and self.user["VaiTro"] != "admin":
                continue

            tk.Button(
                side,
                text=name,
                anchor="w",
                padx=22,
                pady=11,
                bg=DARK_BLUE,
                fg=WHITE,
                activebackground=BLUE,
                activeforeground=WHITE,
                relief="flat",
                font=("Segoe UI", 10),
                cursor="hand2",
                command=lambda c=screen: self.open_screen(c)
            ).pack(fill="x", padx=8, pady=2)

        tk.Button(
            side,
            text="ĐĂNG XUẤT",
            command=self.show_login,
            bg="#DC2626",
            fg=WHITE,
            relief="flat",
            pady=10
        ).pack(side="bottom", fill="x", padx=12, pady=18)

        # Khu vực nội dung
        right = tk.Frame(self, bg=LIGHT_BG)
        right.pack(side="left", fill="both", expand=True)

        header = tk.Frame(
            right,
            bg=WHITE,
            height=65
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="TRUNG TÂM QUẢN LÝ KÝ TÚC XÁ",
            bg=WHITE,
            fg=BLUE,
            font=("Segoe UI", 13, "bold")
        ).pack(side="left", padx=22)

        tk.Label(
            header,
            text=self.user["HoTen"],
            bg=WHITE,
            fg=DARK_BLUE,
            font=("Segoe UI", 10, "bold")
        ).pack(side="right", padx=22)

        self.content = tk.Frame(right, bg=LIGHT_BG)
        self.content.pack(fill="both", expand=True)

        self.open_screen(DashboardScreen)

    # ==============================
    # CHUYỂN TRANG QUẢN LÝ
    # ==============================

    def open_screen(self, screen_class):

        for widget in self.content.winfo_children():
            widget.destroy()

        screen_class(
            self.content,
            self.user
        ).pack(fill="both", expand=True)

    # ==============================
    # GIAO DIỆN SINH VIÊN
    # ==============================

    def show_student_home(self):

        for widget in self.winfo_children():
            widget.destroy()

        self.configure(bg=LIGHT_BG)

        header = tk.Frame(
            self,
            bg=BLUE,
            height=115
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header,
            text="HUIT",
            bg=BLUE,
            fg=WHITE,
            font=("Segoe UI", 25, "bold")
        ).pack(pady=(12, 0))

        tk.Label(
            header,
            text="CỔNG THÔNG TIN SINH VIÊN KÝ TÚC XÁ",
            bg=BLUE,
            fg=WHITE,
            font=("Segoe UI", 13, "bold")
        ).pack()

        card = tk.Frame(
            self,
            bg=WHITE,
            padx=35,
            pady=30
        )
        card.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            card,
            text="XIN CHÀO SINH VIÊN",
            bg=WHITE,
            fg=BLUE,
            font=("Segoe UI", 19, "bold")
        ).pack(pady=10)

        tk.Label(
            card,
            text="Họ và tên: " + str(self.user.get("HoTen", "")),
            bg=WHITE,
            font=("Segoe UI", 12)
        ).pack(anchor="w", pady=8)

        tk.Label(
            card,
            text="Mã sinh viên: " + str(
                self.user.get("MaSV", "")
            ),
            bg=WHITE,
            font=("Segoe UI", 12)
        ).pack(anchor="w", pady=8)

        tk.Label(
            card,
            text="Trạng thái: ĐANG Ở KÝ TÚC XÁ",
            bg=WHITE,
            fg="#16A34A",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=8)

        tk.Label(
            card,
            text="Vui lòng liên hệ ban quản lý nếu cần hỗ trợ.",
            bg=WHITE,
            fg="#64748B"
        ).pack(pady=15)

        tk.Button(
            card,
            text="ĐĂNG XUẤT",
            command=self.show_login,
            bg=BLUE,
            fg=WHITE,
            relief="flat",
            padx=25,
            pady=10
        ).pack(fill="x")


if __name__ == "__main__":

    app = App()
    app.mainloop()
