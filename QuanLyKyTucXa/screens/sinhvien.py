
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

import database as db
from screens.base import CrudScreen, error, form_dialog, valid_date


# =========================================================
# HUIT COLOR THEME
# =========================================================

BLUE = "#1958B8"
BLUE_DARK = "#10346D"
BLUE_LIGHT = "#E7F0FF"

BG = "#F2F6FC"
WHITE = "#FFFFFF"

TEXT = "#183153"
MUTED = "#64748B"
BORDER = "#DCE6F5"

GREEN = "#16834A"
GREEN_BG = "#E2F5EA"

ORANGE = "#D58A24"
ORANGE_BG = "#FFF3DF"

RED = "#D46A6A"
RED_BG = "#FFF0F0"


# =========================================================
# FORM DATA
# =========================================================

FIELDS = [
    ("HoTen", "Họ và tên", "entry", None),
    ("NgaySinh", "Ngày sinh (dd/mm/yyyy)", "entry", None),
    ("GioiTinh", "Giới tính", "combo", ["Nam", "Nữ"]),
    ("Lop", "Lớp", "entry", None),
    ("SDT", "Số điện thoại", "entry", None),
    ("QueQuan", "Quê quán", "entry", None)
]


def validate(d):

    if not d["HoTen"]:
        return "Họ tên không được để trống."

    if d["NgaySinh"] and not valid_date(d["NgaySinh"]):
        return "Ngày sinh phải có dạng dd/mm/yyyy."

    if d["SDT"] and not (
        d["SDT"].isdigit() and 9 <= len(d["SDT"]) <= 11
    ):
        return "Số điện thoại phải gồm 9-11 chữ số."

    return None


# =========================================================
# SINH VIEN SCREEN
# =========================================================

class SinhVienScreen(CrudScreen):

    title = "Quản lý sinh viên"

    columns = [
        ("MaSV", "Mã SV", 90),
        ("HoTen", "Họ và tên", 180),
        ("NgaySinh", "Ngày sinh", 110),
        ("GioiTinh", "Giới tính", 90),
        ("Lop", "Lớp", 120),
        ("SDT", "SĐT", 130),
        ("QueQuan", "Quê quán", 140),
        ("Phong", "Phòng đang ở", 120)
    ]

    def __init__(self, master, *args, **kwargs):

        ttk.Frame.__init__(self, master)

        self.configure(style="HUIT.Main.TFrame")

        self.keyword = tk.StringVar()
        self.filter_type = tk.StringVar(value="all")

        self._setup_style()
        self._build_interface()
        self.refresh()

    # =====================================================
    # STYLE
    # =====================================================

    def _setup_style(self):

        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "HUIT.Main.TFrame",
            background=BG
        )

        style.configure(
            "HUIT.Card.TFrame",
            background=WHITE
        )

        style.configure(
            "HUIT.Title.TLabel",
            background=BG,
            foreground=BLUE_DARK,
            font=("Segoe UI", 23, "bold")
        )

        style.configure(
            "HUIT.Sub.TLabel",
            background=BG,
            foreground=MUTED,
            font=("Segoe UI", 10)
        )

        style.configure(
            "HUIT.CardTitle.TLabel",
            background=WHITE,
            foreground=MUTED,
            font=("Segoe UI", 9, "bold")
        )

        style.configure(
            "HUIT.CardValue.TLabel",
            background=WHITE,
            foreground=BLUE,
            font=("Segoe UI", 23, "bold")
        )

        style.configure(
            "HUIT.Treeview",
            background=WHITE,
            foreground=TEXT,
            fieldbackground=WHITE,
            font=("Segoe UI", 10),
            rowheight=46,
            borderwidth=0
        )

        style.configure(
            "HUIT.Treeview.Heading",
            background="#F3F7FD",
            foreground="#536783",
            font=("Segoe UI", 10, "bold"),
            padding=(10, 13),
            relief="flat"
        )

        style.map(
            "HUIT.Treeview.Heading",
            background=[
                ("active", BLUE_LIGHT)
            ]
        )

        style.map(
            "HUIT.Treeview",
            background=[
                ("selected", BLUE)
            ],
            foreground=[
                ("selected", WHITE)
            ]
        )

        style.configure(
            "HUIT.Primary.TButton",
            background=BLUE,
            foreground=WHITE,
            font=("Segoe UI", 10, "bold"),
            padding=(16, 10),
            borderwidth=0
        )

        style.map(
            "HUIT.Primary.TButton",
            background=[
                ("active", "#286CCB"),
                ("pressed", BLUE_DARK)
            ],
            foreground=[
                ("active", WHITE)
            ]
        )

        style.configure(
            "HUIT.TButton",
            background=WHITE,
            foreground=BLUE_DARK,
            font=("Segoe UI", 9, "bold"),
            padding=(13, 9),
            borderwidth=1,
            relief="solid"
        )

        style.map(
            "HUIT.TButton",
            background=[
                ("active", BLUE_LIGHT),
                ("pressed", "#D6E5FC")
            ]
        )

        style.configure(
            "HUIT.Danger.TButton",
            background=WHITE,
            foreground=RED,
            font=("Segoe UI", 9, "bold"),
            padding=(13, 9),
            borderwidth=1,
            relief="solid"
        )

        style.map(
            "HUIT.Danger.TButton",
            background=[
                ("active", RED_BG)
            ]
        )

        style.configure(
            "HUIT.TEntry",
            fieldbackground=WHITE,
            foreground=TEXT,
            insertcolor=BLUE,
            padding=10,
            bordercolor=BORDER
        )

        style.map(
            "HUIT.TEntry",
            bordercolor=[
                ("focus", BLUE)
            ]
        )

        style.configure(
            "HUIT.Filter.TButton",
            background=WHITE,
            foreground="#526581",
            font=("Segoe UI", 9, "bold"),
            padding=(14, 9),
            borderwidth=1,
            relief="solid"
        )

        style.configure(
            "HUIT.ActiveFilter.TButton",
            background=BLUE_LIGHT,
            foreground=BLUE_DARK,
            font=("Segoe UI", 9, "bold"),
            padding=(14, 9),
            borderwidth=1,
            relief="solid"
        )

    # =====================================================
    # MAIN INTERFACE
    # =====================================================

    def _build_interface(self):

        container = ttk.Frame(
            self,
            style="HUIT.Main.TFrame",
            padding=(26, 22)
        )

        container.pack(
            fill="both",
            expand=True
        )

        # HEADER

        header = ttk.Frame(
            container,
            style="HUIT.Main.TFrame"
        )

        header.pack(fill="x")

        title_box = ttk.Frame(
            header,
            style="HUIT.Main.TFrame"
        )

        title_box.pack(side="left")

        ttk.Label(
            title_box,
            text="Quản lý sinh viên",
            style="HUIT.Title.TLabel"
        ).pack(anchor="w")

        ttk.Label(
            title_box,
            text="Danh sách sinh viên đăng ký ở ký túc xá",
            style="HUIT.Sub.TLabel"
        ).pack(
            anchor="w",
            pady=(4, 0)
        )

        # SEARCH

        search_box = ttk.Frame(
            header,
            style="HUIT.Main.TFrame"
        )

        search_box.pack(side="right")

        search = ttk.Entry(
            search_box,
            textvariable=self.keyword,
            width=34,
            style="HUIT.TEntry"
        )

        search.pack(
            side="left",
            ipady=5
        )

        search.insert(0, "")

        search.bind(
            "<Return>",
            lambda event: self.refresh()
        )

        ttk.Button(
            search_box,
            text="Tìm kiếm",
            command=self.refresh,
            style="HUIT.Primary.TButton"
        ).pack(
            side="left",
            padx=(8, 0)
        )

        # ACTION BUTTONS

        action_bar = ttk.Frame(
            container,
            style="HUIT.Main.TFrame"
        )

        action_bar.pack(
            fill="x",
            pady=(20, 18)
        )

        ttk.Button(
            action_bar,
            text="+  Thêm",
            command=self.add,
            style="HUIT.Primary.TButton"
        ).pack(side="left")

        ttk.Button(
            action_bar,
            text="✎  Sửa",
            command=self._edit_selected,
            style="HUIT.TButton"
        ).pack(
            side="left",
            padx=8
        )

        ttk.Button(
            action_bar,
            text="▤  Xóa",
            command=self._delete_selected,
            style="HUIT.Danger.TButton"
        ).pack(side="left")

        # STATISTICS

        stats = ttk.Frame(
            container,
            style="HUIT.Main.TFrame"
        )

        stats.pack(
            fill="x",
            pady=(0, 18)
        )

        self.stat_total = self._create_stat(
            stats,
            "TỔNG SINH VIÊN",
            "0"
        )

        self.stat_room = self._create_stat(
            stats,
            "ĐANG Ở KTX",
            "0"
        )

        self.stat_free = self._create_stat(
            stats,
            "CHƯA XẾP PHÒNG",
            "0"
        )

        # FILTER

        filter_bar = ttk.Frame(
            container,
            style="HUIT.Main.TFrame"
        )

        filter_bar.pack(
            fill="x",
            pady=(0, 14)
        )

        self.filter_buttons = {}

        filters = [
            ("all", "Tất cả"),
            ("room", "Đang ở KTX"),
            ("free", "Chưa xếp phòng")
        ]

        for key, label in filters:

            btn = ttk.Button(
                filter_bar,
                text=label,
                style="HUIT.Filter.TButton",
                command=lambda k=key: self._change_filter(k)
            )

            btn.pack(
                side="left",
                padx=(0, 9)
            )

            self.filter_buttons[key] = btn

        self._update_filter_style()

        # TABLE CARD

        panel = ttk.Frame(
            container,
            style="HUIT.Card.TFrame",
            padding=12
        )

        panel.pack(
            fill="both",
            expand=True
        )

        # TABLE

        table_frame = ttk.Frame(
            panel,
            style="HUIT.Card.TFrame"
        )

        table_frame.pack(
            fill="both",
            expand=True
        )

        keys = (
            "MaSV",
            "HoTen",
            "NgaySinh",
            "GioiTinh",
            "Lop",
            "SDT",
            "QueQuan",
            "Phong"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=keys,
            show="headings",
            selectmode="browse",
            style="HUIT.Treeview"
        )

        for key, label, width in self.columns:

            self.tree.heading(
                key,
                text=label
            )

            self.tree.column(
                key,
                width=width,
                minwidth=65,
                anchor="center" if key in (
                    "MaSV",
                    "NgaySinh",
                    "GioiTinh",
                    "Phong"
                ) else "w"
            )

        scroll_y = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )

        scroll_x = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        scroll_y.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        scroll_x.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        table_frame.rowconfigure(
            0,
            weight=1
        )

        table_frame.columnconfigure(
            0,
            weight=1
        )

        self.tree.tag_configure(
            "even",
            background=WHITE,
            foreground=TEXT
        )

        self.tree.tag_configure(
            "odd",
            background="#F8FAFE",
            foreground=TEXT
        )

        self.tree.tag_configure(
            "room",
            foreground=GREEN
        )

        self.tree.bind(
            "<Double-1>",
            lambda event: self._edit_selected()
        )

        # FOOTER

        footer = ttk.Frame(
            panel,
            style="HUIT.Card.TFrame"
        )

        footer.pack(
            fill="x",
            pady=(10, 0)
        )

        self.lbl_count = tk.Label(
            footer,
            text="Hiển thị 0 sinh viên",
            bg=WHITE,
            fg=MUTED,
            font=("Segoe UI", 9)
        )

        self.lbl_count.pack(side="left")

        tk.Label(
            footer,
            text="Chọn một sinh viên để thực hiện thao tác",
            bg=WHITE,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(side="right")

    # =====================================================
    # STATISTIC CARDS
    # =====================================================

    def _create_stat(self, parent, label, value):

        card = ttk.Frame(
            parent,
            style="HUIT.Card.TFrame",
            padding=(17, 13)
        )

        card.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 12)
        )

        ttk.Label(
            card,
            text=label,
            style="HUIT.CardTitle.TLabel"
        ).pack(anchor="w")

        result = ttk.Label(
            card,
            text=value,
            style="HUIT.CardValue.TLabel"
        )

        result.pack(
            anchor="w",
            pady=(5, 0)
        )

        return result

    # =====================================================
    # FILTER
    # =====================================================

    def _change_filter(self, key):

        self.filter_type.set(key)

        self._update_filter_style()

        self.refresh()

    def _update_filter_style(self):

        for key, btn in self.filter_buttons.items():

            if key == self.filter_type.get():

                btn.configure(
                    style="HUIT.ActiveFilter.TButton"
                )

            else:

                btn.configure(
                    style="HUIT.Filter.TButton"
                )

    # =====================================================
    # GET DATA
    # =====================================================

    def rows(self, kw):

        like = f"%{kw}%"

        return db.query("""
            SELECT s.*,
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

            WHERE CAST(s.MaSV AS TEXT) LIKE ?
                OR s.HoTen LIKE ?
                OR s.Lop LIKE ?
                OR s.SDT LIKE ?

            ORDER BY s.MaSV
        """, (like,) * 4)

    # =====================================================
    # REFRESH TABLE
    # =====================================================

    def refresh(self):

        try:

            kw = self.keyword.get().strip()

            data = self.rows(kw)

            total = len(data)

            room_count = sum(
                1 for item in data if item["Phong"]
            )

            free_count = total - room_count

            self.stat_total.configure(
                text=str(total)
            )

            self.stat_room.configure(
                text=str(room_count)
            )

            self.stat_free.configure(
                text=str(free_count)
            )

            for item in self.tree.get_children():

                self.tree.delete(item)

            displayed = 0

            for index, item in enumerate(data):

                room = item["Phong"]

                if self.filter_type.get() == "room" and not room:
                    continue

                if self.filter_type.get() == "free" and room:
                    continue

                values = (
                    item["MaSV"],
                    item["HoTen"],
                    item["NgaySinh"],
                    item["GioiTinh"],
                    item["Lop"],
                    item["SDT"],
                    item["QueQuan"],
                    room if room else "Chưa xếp"
                )

                tag = "even" if displayed % 2 == 0 else "odd"

                if room:
                    tag = "room"

                self.tree.insert(
                    "",
                    "end",
                    iid=str(item["MaSV"]),
                    values=values,
                    tags=(tag,)
                )

                displayed += 1

            self.lbl_count.configure(
                text=f"Hiển thị {displayed} / {total} sinh viên"
            )

        except Exception as e:

            error(f"Không thể tải danh sách sinh viên: {e}")

    # =====================================================
    # SELECTED STUDENT
    # =====================================================

    def _selected_id(self):

        selected = self.tree.selection()

        if not selected:

            messagebox.showwarning(
                "Thông báo",
                "Vui lòng chọn sinh viên cần thao tác.",
                parent=self
            )

            return None

        return selected[0]

    # =====================================================
    # ADD
    # =====================================================

    def add(self):

        d = form_dialog(
            self,
            "Thêm sinh viên",
            FIELDS
        )

        if not d:
            return

        err = validate(d)

        if err:
            return error(err)

        try:

            db.execute("""
                INSERT INTO SinhVien(
                    HoTen,
                    NgaySinh,
                    GioiTinh,
                    Lop,
                    SDT,
                    QueQuan
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, tuple(
                d[k] for k in (
                    "HoTen",
                    "NgaySinh",
                    "GioiTinh",
                    "Lop",
                    "SDT",
                    "QueQuan"
                )
            ))

            messagebox.showinfo(
                "Thành công",
                "Thêm sinh viên thành công!",
                parent=self
            )

            self.refresh()

        except Exception as e:

            error(f"Không thể thêm sinh viên: {e}")

    # =====================================================
    # EDIT
    # =====================================================

    def _edit_selected(self):

        id_ = self._selected_id()

        if id_ is not None:
            self.edit(id_)

    def edit(self, id_):

        try:

            result = db.query(
                "SELECT * FROM SinhVien WHERE MaSV=?",
                (id_,),
                one=True
            )

            if not result:
                return error("Không tìm thấy sinh viên.")

            cur = dict(result)

            d = form_dialog(
                self,
                "Sửa thông tin sinh viên",
                FIELDS,
                cur
            )

            if not d:
                return

            err = validate(d)

            if err:
                return error(err)

            db.execute("""
                UPDATE SinhVien
                SET
                    HoTen=?,
                    NgaySinh=?,
                    GioiTinh=?,
                    Lop=?,
                    SDT=?,
                    QueQuan=?
                WHERE MaSV=?
            """, tuple(
                d[k] for k in (
                    "HoTen",
                    "NgaySinh",
                    "GioiTinh",
                    "Lop",
                    "SDT",
                    "QueQuan"
                )
            ) + (id_,))

            messagebox.showinfo(
                "Thành công",
                "Cập nhật thông tin thành công!",
                parent=self
            )

            self.refresh()

        except Exception as e:

            error(f"Không thể cập nhật sinh viên: {e}")

    # =====================================================
    # DELETE
    # =====================================================

    def _delete_selected(self):

        id_ = self._selected_id()

        if id_ is not None:
            self.delete(id_)

    def delete(self, id_):

        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa sinh viên này không?",
            parent=self
        )

        if not confirm:
            return

        try:

            db.execute(
                "DELETE FROM SinhVien WHERE MaSV=?",
                (id_,)
            )

            messagebox.showinfo(
                "Thành công",
                "Đã xóa sinh viên!",
                parent=self
            )

            self.refresh()

        except Exception as e:

            error(f"Không thể xóa sinh viên: {e}")
