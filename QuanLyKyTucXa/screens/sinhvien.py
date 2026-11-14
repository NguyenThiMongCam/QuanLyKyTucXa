
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

import database as db
from screens.base import valid_date


# =========================================================
# CẤU HÌNH GIAO DIỆN - PHONG CÁCH HUIT
# =========================================================

COLORS = {
    "primary": "#0B54A0",
    "primary_hover": "#08427F",
    "background": "#F3F6FA",
    "white": "#FFFFFF",
    "text": "#243247",
    "muted": "#718096",
    "border": "#E1E8F0",
    "green": "#16865B",
    "green_bg": "#E8F5EE",
    "red": "#D64545",
    "red_hover": "#B83232",
    "blue_light": "#EAF2FB",
    "row_alt": "#F7F9FC",
}

FONT = "Segoe UI"


FIELDS = [
    ("HoTen", "Họ và tên", "entry", None),
    ("NgaySinh", "Ngày sinh (dd/mm/yyyy)", "entry", None),
    ("GioiTinh", "Giới tính", "combo", ["Nam", "Nữ"]),
    ("Lop", "Lớp", "entry", None),
    ("SDT", "Số điện thoại", "entry", None),
    ("QueQuan", "Quê quán", "entry", None),
]


def validate(data):
    if not data["HoTen"]:
        return "Họ tên không được để trống."

    if data["NgaySinh"] and not valid_date(data["NgaySinh"]):
        return "Ngày sinh phải có dạng dd/mm/yyyy."

    if data["SDT"]:
        if not (data["SDT"].isdigit() and 9 <= len(data["SDT"]) <= 11):
            return "Số điện thoại phải gồm 9-11 chữ số."

    return None


class SinhVienScreen(ttk.Frame):

    title = "Quản lý sinh viên"

    columns = [
        ("MaSV", "Mã sinh viên", 100),
        ("HoTen", "Họ và tên", 200),
        ("NgaySinh", "Ngày sinh", 110),
        ("GioiTinh", "Giới tính", 90),
        ("Lop", "Lớp", 110),
        ("SDT", "Số điện thoại", 130),
        ("QueQuan", "Quê quán", 180),
        ("Phong", "Phòng đang ở", 120),
    ]

    def __init__(self, master, user=None):
        super().__init__(master)

        self.user = user
        self.kw = tk.StringVar()
        self.all_rows = []

        self.configure(style="SV.TFrame")

        self.setup_style()
        self.build_interface()
        self.refresh()

    # =====================================================
    # STYLE
    # =====================================================

    def setup_style(self):
        style = ttk.Style(self)

        style.configure(
            "SV.TFrame",
            background=COLORS["background"]
        )

        style.configure(
            "SV.Treeview",
            background=COLORS["white"],
            foreground=COLORS["text"],
            fieldbackground=COLORS["white"],
            rowheight=38,
            font=(FONT, 10),
            borderwidth=0
        )

        style.configure(
            "SV.Treeview.Heading",
            background=COLORS["blue_light"],
            foreground=COLORS["primary"],
            font=(FONT, 10, "bold"),
            padding=(10, 12),
            relief="flat"
        )

        style.map(
            "SV.Treeview",
            background=[("selected", "#DCEBFA")],
            foreground=[("selected", COLORS["primary"])]
        )

        style.map(
            "SV.Treeview.Heading",
            background=[("active", "#DCEBFA")]
        )

        style.configure(
            "SV.TEntry",
            padding=9,
            font=(FONT, 10)
        )

    # =====================================================
    # GIAO DIỆN CHÍNH
    # =====================================================

    def build_interface(self):

        container = tk.Frame(
            self,
            bg=COLORS["background"]
        )
        container.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=20
        )

        # ---------------- TIÊU ĐỀ ----------------

        header = tk.Frame(
            container,
            bg=COLORS["background"]
        )
        header.pack(fill="x", pady=(0, 18))

        title_area = tk.Frame(
            header,
            bg=COLORS["background"]
        )
        title_area.pack(side="left")

        tk.Label(
            title_area,
            text="QUẢN LÝ SINH VIÊN",
            font=(FONT, 20, "bold"),
            fg=COLORS["primary"],
            bg=COLORS["background"]
        ).pack(anchor="w")

        tk.Label(
            title_area,
            text="Quản lý thông tin và danh sách sinh viên ký túc xá",
            font=(FONT, 10),
            fg=COLORS["muted"],
            bg=COLORS["background"]
        ).pack(anchor="w", pady=(5, 0))

        # ---------------- THẺ THỐNG KÊ ----------------

        stats = tk.Frame(
            container,
            bg=COLORS["background"]
        )
        stats.pack(fill="x", pady=(0, 18))

        self.stat_total = self.create_stat_card(
            stats,
            "TỔNG SINH VIÊN",
            "0",
            COLORS["primary"]
        )

        self.stat_male = self.create_stat_card(
            stats,
            "SINH VIÊN NAM",
            "0",
            COLORS["green"]
        )

        self.stat_female = self.create_stat_card(
            stats,
            "SINH VIÊN NỮ",
            "0",
            "#8B5CF6"
        )

        self.stat_staying = self.create_stat_card(
            stats,
            "ĐANG Ở KÝ TÚC XÁ",
            "0",
            "#D97706"
        )

        # ---------------- KHU VỰC DANH SÁCH ----------------

        content = tk.Frame(
            container,
            bg=COLORS["white"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        content.pack(fill="both", expand=True)

        # Thanh tiêu đề bảng

        table_header = tk.Frame(
            content,
            bg=COLORS["white"]
        )
        table_header.pack(
            fill="x",
            padx=18,
            pady=(16, 12)
        )

        tk.Label(
            table_header,
            text="Danh sách sinh viên",
            font=(FONT, 13, "bold"),
            fg=COLORS["text"],
            bg=COLORS["white"]
        ).pack(side="left")

        # Tìm kiếm

        search_area = tk.Frame(
            table_header,
            bg=COLORS["white"]
        )
        search_area.pack(side="right")

        self.search_entry = ttk.Entry(
            search_area,
            textvariable=self.kw,
            width=28,
            style="SV.TEntry"
        )
        self.search_entry.pack(side="left", padx=(0, 7))
        self.search_entry.bind(
            "<Return>",
            lambda event: self.refresh()
        )

        self.create_button(
            search_area,
            "Tìm kiếm",
            self.refresh,
            COLORS["primary"],
            COLORS["primary_hover"]
        ).pack(side="left")

        # ---------------- CÁC NÚT CHỨC NĂNG ----------------

        toolbar = tk.Frame(
            content,
            bg=COLORS["white"]
        )
        toolbar.pack(
            fill="x",
            padx=18,
            pady=(0, 14)
        )

        self.create_button(
            toolbar,
            "+ Thêm sinh viên",
            self.add,
            COLORS["primary"],
            COLORS["primary_hover"]
        ).pack(side="left", padx=(0, 8))

        self.create_button(
            toolbar,
            "Sửa thông tin",
            self.on_edit,
            "#EAF2FB",
            "#DCEBFA",
            COLORS["primary"]
        ).pack(side="left", padx=(0, 8))

        self.create_button(
            toolbar,
            "Xóa sinh viên",
            self.on_delete,
            "#FDECEC",
            "#FBDADA",
            COLORS["red"]
        ).pack(side="left", padx=(0, 8))

        self.create_button(
            toolbar,
            "Làm mới",
            self.refresh,
            "#F1F4F8",
            "#E2E8F0",
            COLORS["text"]
        ).pack(side="left")

        # Số lượng kết quả

        self.result_label = tk.Label(
            toolbar,
            text="Hiển thị 0 sinh viên",
            font=(FONT, 9),
            fg=COLORS["muted"],
            bg=COLORS["white"]
        )
        self.result_label.pack(side="right")

        # ---------------- BẢNG DỮ LIỆU ----------------

        table_area = tk.Frame(
            content,
            bg=COLORS["white"]
        )
        table_area.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=(0, 10)
        )

        column_keys = [column[0] for column in self.columns]

        self.tree = ttk.Treeview(
            table_area,
            columns=column_keys,
            show="headings",
            selectmode="browse",
            style="SV.Treeview"
        )

        for key, heading, width in self.columns:
            self.tree.heading(key, text=heading)
            self.tree.column(
                key,
                width=width,
                minwidth=70,
                anchor="w",
                stretch=True
            )

        self.tree.tag_configure(
            "even",
            background=COLORS["white"]
        )

        self.tree.tag_configure(
            "odd",
            background=COLORS["row_alt"]
        )

        vertical_scroll = ttk.Scrollbar(
            table_area,
            orient="vertical",
            command=self.tree.yview
        )

        horizontal_scroll = ttk.Scrollbar(
            table_area,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=vertical_scroll.set,
            xscrollcommand=horizontal_scroll.set
        )

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        vertical_scroll.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        horizontal_scroll.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        table_area.grid_rowconfigure(0, weight=1)
        table_area.grid_columnconfigure(0, weight=1)

        self.tree.bind(
            "<Double-1>",
            lambda event: self.on_edit()
        )

        # ---------------- CHÂN TRANG ----------------

        footer = tk.Frame(
            content,
            bg=COLORS["white"]
        )
        footer.pack(
            fill="x",
            padx=18,
            pady=(0, 13)
        )

        tk.Label(
            footer,
            text="Hệ thống quản lý ký túc xá",
            font=(FONT, 9),
            fg=COLORS["muted"],
            bg=COLORS["white"]
        ).pack(side="left")

        tk.Label(
            footer,
            text="HUIT",
            font=(FONT, 9, "bold"),
            fg=COLORS["primary"],
            bg=COLORS["white"]
        ).pack(side="right")

    # =====================================================
    # THẺ THỐNG KÊ
    # =====================================================

    def create_stat_card(self, parent, title, value, color):

        card = tk.Frame(
            parent,
            bg=COLORS["white"],
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )

        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10)
        )

        tk.Frame(
            card,
            bg=color,
            width=4
        ).pack(side="left", fill="y")

        body = tk.Frame(
            card,
            bg=COLORS["white"]
        )
        body.pack(
            side="left",
            fill="both",
            expand=True,
            padx=14,
            pady=12
        )

        tk.Label(
            body,
            text=title,
            font=(FONT, 8, "bold"),
            fg=COLORS["muted"],
            bg=COLORS["white"]
        ).pack(anchor="w")

        number = tk.Label(
            body,
            text=value,
            font=(FONT, 21, "bold"),
            fg=color,
            bg=COLORS["white"]
        )
        number.pack(anchor="w", pady=(4, 0))

        return number

    # =====================================================
    # NÚT CHỨC NĂNG
    # =====================================================

    def create_button(
        self,
        parent,
        text,
        command,
        background,
        hover,
        foreground=COLORS["white"]
    ):

        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=background,
            fg=foreground,
            activebackground=hover,
            activeforeground=foreground,
            font=(FONT, 9, "bold"),
            relief="flat",
            bd=0,
            padx=14,
            pady=9,
            cursor="hand2"
        )

        button.bind(
            "<Enter>",
            lambda event: button.configure(bg=hover)
        )

        button.bind(
            "<Leave>",
            lambda event: button.configure(bg=background)
        )

        return button

    # =====================================================
    # LẤY DỮ LIỆU
    # =====================================================

    def rows(self, keyword=""):

        like = f"%{keyword}%"

        return db.query("""
            SELECT
                s.*,
                COALESCE(
                    (
                        SELECT p.TenPhong
                        FROM HopDong h
                        JOIN Phong p ON p.MaPhong = h.MaPhong
                        WHERE h.MaSV = s.MaSV
                        AND h.TrangThai = 'Đang thuê'
                        LIMIT 1
                    ),
                    ''
                ) AS Phong

            FROM SinhVien s

            WHERE
                CAST(s.MaSV AS TEXT) LIKE ?
                OR s.HoTen LIKE ?
                OR s.Lop LIKE ?
                OR s.SDT LIKE ?

            ORDER BY s.MaSV
        """, (like, like, like, like))

    # =====================================================
    # CẬP NHẬT DỮ LIỆU
    # =====================================================

    def refresh(self):

        keyword = self.kw.get().strip()

        self.all_rows = self.rows(keyword)

        self.tree.delete(*self.tree.get_children())

        for index, row in enumerate(self.all_rows):

            values = [
                row[key]
                for key, heading, width in self.columns
            ]

            tag = "even" if index % 2 == 0 else "odd"

            self.tree.insert(
                "",
                "end",
                iid=str(row["MaSV"]),
                values=values,
                tags=(tag,)
            )

        self.update_statistics()

        self.result_label.configure(
            text=f"Hiển thị {len(self.all_rows)} sinh viên"
        )

    # =====================================================
    # THỐNG KÊ
    # =====================================================

    def update_statistics(self):

        total = len(self.all_rows)

        male = sum(
            1 for row in self.all_rows
            if str(row["GioiTinh"]).strip().lower() == "nam"
        )

        female = sum(
            1 for row in self.all_rows
            if str(row["GioiTinh"]).strip().lower() == "nữ"
        )

        staying = sum(
            1 for row in self.all_rows
            if row["Phong"]
        )

        self.stat_total.configure(text=str(total))
        self.stat_male.configure(text=str(male))
        self.stat_female.configure(text=str(female))
        self.stat_staying.configure(text=str(staying))

    # =====================================================
    # LẤY SINH VIÊN ĐANG CHỌN
    # =====================================================

    def selected_id(self):

        selected = self.tree.selection()

        if not selected:
            messagebox.showwarning(
                "Thông báo",
                "Vui lòng chọn sinh viên trong danh sách."
            )
            return None

        return int(selected[0])

    # =====================================================
    # FORM THÊM / SỬA
    # =====================================================

    def form_dialog(self, title, values=None):

        values = values or {}

        window = tk.Toplevel(self)
        window.title(title)
        window.configure(bg=COLORS["background"])
        window.resizable(False, False)
        window.transient(self.winfo_toplevel())

        window.update_idletasks()

        width = 470
        height = 490

        x = (
            window.winfo_screenwidth() - width
        ) // 2

        y = (
            window.winfo_screenheight() - height
        ) // 2

        window.geometry(f"{width}x{height}+{x}+{y}")

        # Tiêu đề form

        header = tk.Frame(
            window,
            bg=COLORS["primary"]
        )
        header.pack(fill="x")

        tk.Label(
            header,
            text=title,
            font=(FONT, 15, "bold"),
            fg=COLORS["white"],
            bg=COLORS["primary"]
        ).pack(
            anchor="w",
            padx=22,
            pady=18
        )

        body = tk.Frame(
            window,
            bg=COLORS["white"]
        )
        body.pack(
            fill="both",
            expand=True,
            padx=18,
            pady=18
        )

        widgets = {}

        for index, (key, label, kind, options) in enumerate(FIELDS):

            tk.Label(
                body,
                text=label,
                font=(FONT, 9, "bold"),
                fg=COLORS["text"],
                bg=COLORS["white"]
            ).grid(
                row=index,
                column=0,
                sticky="w",
                pady=9
            )

            if kind == "combo":

                widget = ttk.Combobox(
                    body,
                    values=options,
                    state="readonly",
                    width=34,
                    font=(FONT, 10)
                )

                current = values.get(key)

                if current in options:
                    widget.set(current)
                elif options:
                    widget.set(options[0])

            else:

                widget = ttk.Entry(
                    body,
                    width=37,
                    font=(FONT, 10)
                )

                current = values.get(key)

                if current is not None:
                    widget.insert(0, str(current))

            widget.grid(
                row=index,
                column=1,
                sticky="ew",
                padx=(15, 0),
                pady=7,
                ipady=5
            )

            widgets[key] = widget

        body.grid_columnconfigure(1, weight=1)

        result = {}

        def save():

            data = {
                key: widget.get().strip()
                for key, widget in widgets.items()
            }

            error_text = validate(data)

            if error_text:
                messagebox.showerror(
                    "Thông tin không hợp lệ",
                    error_text,
                    parent=window
                )
                return

            result.update(data)
            window.destroy()

        # Nút

        button_area = tk.Frame(
            body,
            bg=COLORS["white"]
        )
        button_area.grid(
            row=len(FIELDS),
            column=0,
            columnspan=2,
            sticky="e",
            pady=(25, 5)
        )

        self.create_button(
            button_area,
            "Hủy",
            window.destroy,
            "#F1F4F8",
            "#E2E8F0",
            COLORS["text"]
        ).pack(side="left", padx=5)

        self.create_button(
            button_area,
            "Lưu thông tin",
            save,
            COLORS["primary"],
            COLORS["primary_hover"]
        ).pack(side="left", padx=5)

        window.bind("<Return>", lambda event: save())
        window.bind("<Escape>", lambda event: window.destroy())

        window.grab_set()
        window.wait_window()

        return result or None

    # =====================================================
    # THÊM SINH VIÊN
    # =====================================================

    def add(self):

        data = self.form_dialog("THÊM SINH VIÊN")

        if not data:
            return

        try:

            db.execute("""
                INSERT INTO SinhVien
                (
                    HoTen,
                    NgaySinh,
                    GioiTinh,
                    Lop,
                    SDT,
                    QueQuan
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data["HoTen"],
                data["NgaySinh"],
                data["GioiTinh"],
                data["Lop"],
                data["SDT"],
                data["QueQuan"]
            ))

            db.ghi_nhat_ky(
                "sv",
                f"Thêm sinh viên **{data['HoTen']}**"
            )

            messagebox.showinfo(
                "Thành công",
                "Thêm sinh viên thành công."
            )

            self.refresh()

        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Lỗi",
                "Không thể thêm sinh viên. Vui lòng kiểm tra lại dữ liệu."
            )

    # =====================================================
    # SỬA SINH VIÊN
    # =====================================================

    def edit(self, id_):

        current = db.query(
            "SELECT * FROM SinhVien WHERE MaSV = ?",
            (id_,),
            one=True
        )

        if not current:
            messagebox.showerror(
                "Lỗi",
                "Không tìm thấy sinh viên cần sửa."
            )
            return

        current = dict(current)

        data = self.form_dialog(
            "CẬP NHẬT THÔNG TIN SINH VIÊN",
            current
        )

        if not data:
            return

        try:

            db.execute("""
                UPDATE SinhVien
                SET
                    HoTen = ?,
                    NgaySinh = ?,
                    GioiTinh = ?,
                    Lop = ?,
                    SDT = ?,
                    QueQuan = ?
                WHERE MaSV = ?
            """, (
                data["HoTen"],
                data["NgaySinh"],
                data["GioiTinh"],
                data["Lop"],
                data["SDT"],
                data["QueQuan"],
                id_
            ))

            db.ghi_nhat_ky(
                "sv",
                f"Cập nhật thông tin sinh viên **{data['HoTen']}**"
            )

            messagebox.showinfo(
                "Thành công",
                "Cập nhật thông tin sinh viên thành công."
            )

            self.refresh()

        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Lỗi",
                "Không thể cập nhật thông tin sinh viên."
            )

    def on_edit(self):

        id_ = self.selected_id()

        if id_ is not None:
            self.edit(id_)

    # =====================================================
    # XÓA SINH VIÊN
    # =====================================================

    def delete(self, id_):

        db.execute(
            "DELETE FROM SinhVien WHERE MaSV = ?",
            (id_,)
        )

    def on_delete(self):

        id_ = self.selected_id()

        if id_ is None:
            return

        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa sinh viên này không?\n\n"
            "Thao tác này có thể không khôi phục được."
        )

        if not confirm:
            return

        try:

            current = db.query(
                "SELECT HoTen FROM SinhVien WHERE MaSV = ?",
                (id_,),
                one=True
            )

            self.delete(id_)

            if current:
                db.ghi_nhat_ky(
                    "sv",
                    f"Xóa sinh viên **{current['HoTen']}**"
                )

            messagebox.showinfo(
                "Thành công",
                "Đã xóa sinh viên."
            )

            self.refresh()

        except sqlite3.IntegrityError:

            messagebox.showerror(
                "Không thể xóa",
                "Sinh viên này đang có dữ liệu liên quan "
                "trong hệ thống nên không thể xóa."
            )

    # =====================================================
    # TƯƠNG THÍCH VỚI CÁCH GỌI TỪ MAIN.PY
    # =====================================================

    def on_add(self):
        self.add()
        self.refresh()

    def on_extra(self, method):
        id_ = self.selected_id()

        if id_ is not None:
            getattr(self, method)(id_)
            self.refresh()
