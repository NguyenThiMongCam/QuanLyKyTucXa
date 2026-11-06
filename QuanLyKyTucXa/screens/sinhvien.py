
"""Màn hình quản lý sinh viên - HUIT Blue."""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

import database as db
from screens.base import error, valid_date, parse_date, pick_id


# ==================== HUIT BLUE BRAND THEME ====================
# Giao diện lấy cảm hứng từ website/nhận diện HUIT:
# xanh dương chủ đạo, xanh navy, nền trắng và xanh rất nhạt.

HUIT_BLUE_PRIMARY = "#0B54A0"
HUIT_BLUE_DARK = "#073B73"
HUIT_BLUE_HOVER = "#1769AA"
HUIT_BLUE_LIGHT = "#E8F1FB"
HUIT_NAVY = "#12345A"
HUIT_BLUE = "#1769AA"

BG = "#F4F7FB"
CARD = "#FFFFFF"
INK = "#243247"
MUTED = "#718096"
PRIMARY = HUIT_BLUE_PRIMARY
BORDER = "#DFE7F0"

SOFT_BLUE = "#EAF2FB"
SOFT_SAGE = "#EFF5FC"
SOFT_BEIGE = "#F3F6FA"

# Màu phân biệt giới tính, giữ nhẹ nhàng và không dùng đỏ làm màu chủ đạo
MALE_BG = "#EAF3FC"
MALE_FG = "#285A83"
FEMALE_BG = "#F1EDFA"
FEMALE_FG = "#7252A3"
OTHER_BG = "#EEF2F7"
OTHER_FG = "#58677A"

class SinhVienScreen(ttk.Frame):
    title = "Quản lý sinh viên"

    def __init__(self, master, user=None):
        super().__init__(master)

        self.user = user
        self.configure(style="SV.TFrame")

        self._styles()
        self._build()
        self.refresh()

    # ==================== CÀI ĐẶT GIAO DIỆN ====================

    def _styles(self):
        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Khung và nhãn tổng thể
        style.configure("SV.TFrame", background=BG)
        style.configure("SV.Card.TFrame", background=CARD, relief="flat", borderwidth=0)
        style.configure("SV.TLabel", background=BG, foreground=INK, font=("Segoe UI", 10))
        style.configure("SV.Title.TLabel", background=BG, foreground=HUIT_NAVY,
                        font=("Segoe UI", 23, "bold"))
        style.configure("SV.Sub.TLabel", background=BG, foreground=MUTED,
                        font=("Segoe UI", 9))
        style.configure("SV.CardTitle.TLabel", background=CARD, foreground=MUTED,
                        font=("Segoe UI", 9, "bold"))
        style.configure("SV.CardValue.TLabel", background=CARD, foreground=HUIT_BLUE_PRIMARY,
                        font=("Segoe UI", 23, "bold"))

        # Bảng dữ liệu
        style.configure("SV.Treeview", rowheight=43, font=("Segoe UI", 9),
                        background=CARD, fieldbackground=CARD, foreground=INK,
                        borderwidth=0, relief="flat")
        style.configure("SV.Treeview.Heading", font=("Segoe UI", 9, "bold"),
                        background=HUIT_NAVY, foreground="#FFFFFF",
                        padding=(10, 14), relief="flat")
        style.map("SV.Treeview.Heading",
                  background=[("active", HUIT_BLUE)],
                  foreground=[("active", "#FFFFFF")])
        style.map("SV.Treeview",
                  background=[("selected", HUIT_BLUE_PRIMARY)],
                  foreground=[("selected", "#FFFFFF")])

        # Nút hành động chính
        style.configure("SV.Primary.TButton", font=("Segoe UI", 9, "bold"),
                        background=HUIT_BLUE_PRIMARY, foreground="#FFFFFF",
                        padding=(16, 10), borderwidth=0, focuscolor=HUIT_BLUE_PRIMARY)
        style.map("SV.Primary.TButton",
                  background=[("disabled", "#A9C5E3"),
                              ("pressed", HUIT_BLUE_DARK),
                              ("active", HUIT_BLUE_HOVER)],
                  foreground=[("disabled", "#FFFFFF"), ("!disabled", "#FFFFFF")])

        # Nút thông thường
        style.configure("SV.TButton", font=("Segoe UI", 9, "bold"),
                        background=SOFT_BLUE, foreground=HUIT_NAVY,
                        padding=(13, 9), borderwidth=0, focuscolor=SOFT_BLUE)
        style.map("SV.TButton",
                  background=[("pressed", "#D5E2EF"), ("active", "#DCE8F4")],
                  foreground=[("active", HUIT_BLUE_PRIMARY)])

        # Nút xóa
        style.configure("SV.Danger.TButton", font=("Segoe UI", 9, "bold"),
                        background="#FFF4E5", foreground="#9A5B00",
                        padding=(13, 9), borderwidth=0)
        style.map("SV.Danger.TButton",
                  background=[("pressed", "#F5E4C8"), ("active", "#FCEFD9")])

        # Ô nhập liệu
        style.configure("SV.TEntry", fieldbackground="#FFFFFF", foreground=INK,
                        insertcolor=HUIT_BLUE_PRIMARY, padding=10, bordercolor=BORDER,
                        lightcolor=BORDER, darkcolor=BORDER)
        style.map("SV.TEntry", bordercolor=[("focus", HUIT_BLUE_PRIMARY)],
                  lightcolor=[("focus", HUIT_BLUE_PRIMARY)],
                  darkcolor=[("focus", HUIT_BLUE_PRIMARY)])

        # Hộp chọn
        style.configure("SV.TCombobox", fieldbackground="#FFFFFF",
                        background="#FFFFFF", foreground=INK, padding=9,
                        bordercolor=BORDER, arrowcolor=HUIT_BLUE_PRIMARY)
        style.map("SV.TCombobox",
                  fieldbackground=[("readonly", "#FFFFFF"), ("focus", "#FFFFFF")],
                  foreground=[("readonly", INK)],
                  bordercolor=[("focus", HUIT_BLUE_PRIMARY)])

        # Thanh cuộn
        style.configure("Vertical.TScrollbar", background="#DCE3EC",
                        troughcolor=BG, borderwidth=0, arrowcolor=HUIT_NAVY)
        style.configure("Horizontal.TScrollbar", background="#DCE3EC",
                        troughcolor=BG, borderwidth=0, arrowcolor=HUIT_NAVY)

    # ==================== XÂY DỰNG GIAO DIỆN ====================

    def _build(self):

        wrap = ttk.Frame(
            self,
            style="SV.TFrame",
            padding=(22, 18)
        )

        wrap.pack(
            fill="both",
            expand=True
        )

        # Tiêu đề
        header = ttk.Frame(
            wrap,
            style="SV.TFrame"
        )

        header.pack(fill="x")

        title_box = ttk.Frame(
            header,
            style="SV.TFrame"
        )

        title_box.pack(side="left")

        ttk.Label(
            title_box,
            text="Quản lý sinh viên",
            style="SV.Title.TLabel"
        ).pack(anchor="w")

        ttk.Label(
            title_box,
            text="Theo dõi hồ sơ, thông tin liên hệ và tình trạng lưu trú",
            style="SV.Sub.TLabel"
        ).pack(
            anchor="w",
            pady=(3, 0)
        )

        ttk.Button(
            header,
            text="＋  Thêm sinh viên",
            command=self.add,
            style="SV.Primary.TButton"
        ).pack(
            side="right",
            padx=(8, 0),
            ipady=5
        )

        # Thẻ thống kê
        stats = ttk.Frame(
            wrap,
            style="SV.TFrame"
        )

        stats.pack(
            fill="x",
            pady=17
        )

        self.stat_total = self._stat_card(
            stats,
            "TỔNG SINH VIÊN",
            "0"
        )

        self.stat_room = self._stat_card(
            stats,
            "ĐANG CÓ PHÒNG",
            "0"
        )

        self.stat_free = self._stat_card(
            stats,
            "CHƯA XẾP PHÒNG",
            "0"
        )

        # Khung danh sách
        panel = ttk.Frame(
            wrap,
            style="SV.Card.TFrame",
            padding=14
        )

        panel.pack(
            fill="both",
            expand=True
        )

        # Thanh tìm kiếm
        toolbar = ttk.Frame(
            panel,
            style="SV.Card.TFrame"
        )

        toolbar.pack(
            fill="x",
            pady=(0, 12)
        )

        ttk.Label(
            toolbar,
            text="Danh sách sinh viên",
            background=CARD,
            foreground=INK,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")

        self.kw = tk.StringVar()

        search = ttk.Entry(
            toolbar,
            textvariable=self.kw,
            width=30,
            style="SV.TEntry"
        )

        search.pack(
            side="right",
            padx=(6, 0),
            ipady=5
        )

        search.bind(
            "<Return>",
            lambda _e: self.refresh()
        )

        ttk.Button(
            toolbar,
            text="Tìm kiếm",
            command=self.refresh,
            style="SV.Primary.TButton"
        ).pack(side="right")

        ttk.Button(
            toolbar,
            text="Làm mới",
            command=self._clear_search,
            style="SV.TButton"
        ).pack(
            side="right",
            padx=6
        )

        # Các nút chức năng
        actions = ttk.Frame(
            panel,
            style="SV.Card.TFrame"
        )

        actions.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Button(
            actions,
            text="✎  Chỉnh sửa",
            command=self.edit,
            style="SV.TButton"
        ).pack(
            side="left",
            padx=(0, 6)
        )

        ttk.Button(
            actions,
            text="⌂  Xếp / đổi phòng",
            command=self.assign_room,
            style="SV.TButton"
        ).pack(
            side="left",
            padx=6
        )

        ttk.Button(
            actions,
            text="Xóa sinh viên",
            command=self.delete,
            style="SV.Danger.TButton"
        ).pack(
            side="left",
            padx=6
        )

        # Chú thích màu giới tính
        legend = ttk.Frame(
            panel,
            style="SV.Card.TFrame"
        )

        legend.pack(
            fill="x",
            pady=(0, 10)
        )

        tk.Label(
            legend,
            text="● Nam",
            bg=CARD,
            fg=MALE_FG,
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=(2, 12))

        tk.Label(
            legend,
            text="● Nữ",
            bg=CARD,
            fg=FEMALE_FG,
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=12)

        tk.Label(
            legend,
            text="● Khác",
            bg=CARD,
            fg=OTHER_FG,
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=12)

        # Bảng dữ liệu
        table_wrap = ttk.Frame(
            panel,
            style="SV.Card.TFrame"
        )

        table_wrap.pack(
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
            "Phong",
            "TrangThaiPhong"
        )

        self.tree = ttk.Treeview(
            table_wrap,
            columns=keys,
            show="headings",
            selectmode="browse",
            style="SV.Treeview"
        )

        headings = [
            ("MaSV", "MÃ SV", 65),
            ("HoTen", "HỌ VÀ TÊN", 175),
            ("NgaySinh", "NGÀY SINH", 95),
            ("GioiTinh", "GIỚI TÍNH", 85),
            ("Lop", "LỚP", 105),
            ("SDT", "SỐ ĐIỆN THOẠI", 115),
            ("QueQuan", "QUÊ QUÁN", 130),
            ("Phong", "PHÒNG", 75),
            ("TrangThaiPhong", "TÌNH TRẠNG", 110)
        ]

        for key, label, width in headings:

            self.tree.heading(
                key,
                text=label
            )

            self.tree.column(
                key,
                width=width,
                minwidth=55,
                anchor=(
                    "center"
                    if key in (
                        "MaSV",
                        "NgaySinh",
                        "GioiTinh",
                        "Phong",
                        "TrangThaiPhong"
                    )
                    else "w"
                )
            )

        # Thanh cuộn
        sy = ttk.Scrollbar(
            table_wrap,
            orient="vertical",
            command=self.tree.yview
        )

        sx = ttk.Scrollbar(
            table_wrap,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=sy.set,
            xscrollcommand=sx.set
        )

        self.tree.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        sy.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        sx.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        table_wrap.rowconfigure(
            0,
            weight=1
        )

        table_wrap.columnconfigure(
            0,
            weight=1
        )

        self.tree.bind(
            "<Double-1>",
            lambda _e: self.edit()
        )

        # Màu từng dòng theo giới tính
        self.tree.tag_configure(
            "nam",
            background=MALE_BG,
            foreground=MALE_FG
        )

        self.tree.tag_configure(
            "nu",
            background=FEMALE_BG,
            foreground=FEMALE_FG
        )

        self.tree.tag_configure(
            "khac",
            background=OTHER_BG,
            foreground=OTHER_FG
        )

    # ==================== THẺ THỐNG KÊ ====================

    def _stat_card(self, parent, label, value):

        card = ttk.Frame(
            parent,
            style="SV.Card.TFrame",
            padding=(15, 12)
        )

        card.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 10)
        )

        ttk.Label(
            card,
            text=label,
            style="SV.CardTitle.TLabel"
        ).pack(anchor="w")

        val = ttk.Label(
            card,
            text=value,
            style="SV.CardValue.TLabel"
        )

        val.pack(
            anchor="w",
            pady=(5, 0)
        )

        return val

    # ==================== LÀM MỚI VÀ TÌM KIẾM ====================

    def _clear_search(self):
        self.kw.set("")
        self.refresh()

    def refresh(self):

        kw = self.kw.get().strip()
        like = f"%{kw}%"

        rows = db.query("""
            SELECT s.*,
                   h.MaHD,
                   h.MaPhong,
                   COALESCE(p.TenPhong, '') AS Phong,

                   CASE
                       WHEN h.MaHD IS NULL
                       THEN 'Chưa xếp phòng'
                       ELSE h.TrangThai
                   END AS TrangThaiPhong,

                   COALESCE(h.NgayBatDau, '') AS NgayBatDau,
                   COALESCE(h.NgayKetThuc, '') AS NgayKetThuc

            FROM SinhVien s

            LEFT JOIN HopDong h
                ON h.MaSV = s.MaSV
                AND h.TrangThai = 'Đang thuê'

            LEFT JOIN Phong p
                ON p.MaPhong = h.MaPhong

            WHERE CAST(s.MaSV AS TEXT) LIKE ?
                OR s.HoTen LIKE ?
                OR s.Lop LIKE ?
                OR s.SDT LIKE ?
                OR p.TenPhong LIKE ?

            ORDER BY s.MaSV
        """, (like,) * 5)

        self.tree.delete(
            *self.tree.get_children()
        )

        for r in rows:

            gender = (
                (r["GioiTinh"] or "")
                .strip()
                .lower()
            )

            if gender == "nam":
                tag = "nam"

            elif gender in ("nữ", "nu"):
                tag = "nu"

            else:
                tag = "khac"

            self.tree.insert(
                "",
                "end",
                iid=str(r["MaSV"]),
                tags=(tag,),
                values=(
                    r["MaSV"],
                    r["HoTen"],
                    r["NgaySinh"] or "",
                    r["GioiTinh"] or "",
                    r["Lop"] or "",
                    r["SDT"] or "",
                    r["QueQuan"] or "",
                    r["Phong"] or "—",
                    r["TrangThaiPhong"]
                )
            )

        # Cập nhật số liệu thống kê
        total = db.query(
            "SELECT COUNT(*) FROM SinhVien",
            one=True
        )[0]

        housed = db.query("""
            SELECT COUNT(DISTINCT MaSV)
            FROM HopDong
            WHERE TrangThai = 'Đang thuê'
        """, one=True)[0]

        self.stat_total.config(
            text=str(total)
        )

        self.stat_room.config(
            text=str(housed)
        )

        self.stat_free.config(
            text=str(total - housed)
        )

    # ==================== LẤY SINH VIÊN ĐƯỢC CHỌN ====================

    def _selected_id(self):

        selected = self.tree.selection()

        if not selected:

            messagebox.showwarning(
                "Chưa chọn sinh viên",
                "Vui lòng chọn một sinh viên trong danh sách."
            )

            return None

        return int(selected[0])

    # ==================== DANH SÁCH PHÒNG ====================

    def _room_options(self, current_room_id=None):

        options = [
            "0 - Chưa xếp phòng"
        ]

        for p in db.danh_sach_phong():

            available = (
                p["SoGiuong"] - p["DangO"]
            )

            is_current = (
                p["MaPhong"] == current_room_id
            )

            if (
                p["TinhTrang"] in ("Trống", "Còn chỗ")
                or is_current
            ):

                note = (
                    "phòng hiện tại"
                    if is_current
                    else f"còn {available} chỗ"
                )

                options.append(
                    f"{p['MaPhong']} - {p['TenPhong']} ({note})"
                )

        return options

    # ==================== FORM THÊM / SỬA ====================

    def _dialog(
        self,
        title,
        current=None,
        current_contract=None
    ):

        current = current or {}
        current_contract = current_contract or {}

        room_id = current_contract.get("MaPhong")

        rooms = self._room_options(room_id)

        win = tk.Toplevel(self)

        win.title(title)
        win.configure(bg=CARD)
        win.transient(self.winfo_toplevel())
        win.resizable(False, False)
        win.grab_set()

        outer = tk.Frame(
            win,
            bg=CARD,
            padx=24,
            pady=20
        )

        outer.pack(
            fill="both",
            expand=True
        )

        tk.Label(
            outer,
            text=title,
            bg=CARD,
            fg=INK,
            font=("Segoe UI", 16, "bold")
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 14)
        )

        fields = [
            ("HoTen", "Họ và tên", "entry"),
            ("NgaySinh", "Ngày sinh (dd/mm/yyyy)", "entry"),
            ("GioiTinh", "Giới tính", "combo"),
            ("Lop", "Lớp", "entry"),
            ("SDT", "Số điện thoại", "entry"),
            ("QueQuan", "Quê quán", "entry"),
            ("Phong", "Phòng ở", "room"),
            ("NgayBatDau", "Ngày bắt đầu ở", "entry"),
            ("NgayKetThuc", "Ngày kết thúc dự kiến", "entry")
        ]

        widgets = {}

        defaults = dict(current)

        defaults["Phong"] = next(
            (
                x for x in rooms
                if room_id and pick_id(x) == room_id
            ),
            rooms[0]
        )

        defaults["NgayBatDau"] = (
            current_contract.get("NgayBatDau")
            or date.today().strftime("%d/%m/%Y")
        )

        defaults["NgayKetThuc"] = (
            current_contract.get("NgayKetThuc")
            or ""
        )

        for i, (key, label, kind) in enumerate(
            fields,
            start=1
        ):

            tk.Label(
                outer,
                text=label,
                bg=CARD,
                fg=HUIT_NAVY,
                font=("Segoe UI", 9, "bold")
            ).grid(
                row=i,
                column=0,
                sticky="w",
                pady=6,
                padx=(0, 18)
            )

            if kind == "combo":

                w = ttk.Combobox(
                    outer,
                    values=["Nam", "Nữ", "Khác"],
                    state="readonly",
                    width=34,
                    style="SV.TCombobox"
                )

                w.set(
                    defaults.get(key) or "Nam"
                )

            elif kind == "room":

                w = ttk.Combobox(
                    outer,
                    values=rooms,
                    state="readonly",
                    width=34,
                    style="SV.TCombobox"
                )

                w.set(
                    defaults["Phong"]
                )

            else:

                w = ttk.Entry(
                    outer,
                    width=37,
                    style="SV.TEntry"
                )

                value = defaults.get(key)

                if value is not None:
                    w.insert(0, str(value))

            w.grid(
                row=i,
                column=1,
                sticky="ew",
                pady=6,
                ipady=4
            )

            widgets[key] = w

        tk.Label(
            outer,
            text="Chọn “Chưa xếp phòng” nếu sinh viên chưa đăng ký lưu trú.",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 8)
        ).grid(
            row=10,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(4, 10)
        )

        result = {}

        def submit():

            result.update({
                k: w.get().strip()
                for k, w in widgets.items()
            })

            win.destroy()

        buttons = tk.Frame(
            outer,
            bg=CARD
        )

        buttons.grid(
            row=11,
            column=0,
            columnspan=2,
            sticky="e",
            pady=(8, 0)
        )

        ttk.Button(
            buttons,
            text="Hủy",
            command=win.destroy,
            style="SV.TButton"
        ).pack(
            side="right",
            padx=(8, 0)
        )

        ttk.Button(
            buttons,
            text="Lưu thông tin",
            command=submit,
            style="SV.Primary.TButton"
        ).pack(side="right")

        win.bind(
            "<Return>",
            lambda _e: submit()
        )

        win.bind(
            "<Escape>",
            lambda _e: win.destroy()
        )

        win.wait_window()

        return result or None

    # ==================== KIỂM TRA DỮ LIỆU ====================

    def _validate(self, d):

        if not d["HoTen"]:
            return "Họ tên không được để trống."

        if (
            d["NgaySinh"]
            and not valid_date(d["NgaySinh"])
        ):
            return "Ngày sinh phải có dạng dd/mm/yyyy."

        if d["SDT"] and not (
            d["SDT"].isdigit()
            and 9 <= len(d["SDT"]) <= 11
        ):
            return "Số điện thoại phải gồm 9–11 chữ số."

        room_id = pick_id(d["Phong"])

        if room_id:

            if (
                not valid_date(d["NgayBatDau"])
                or not valid_date(d["NgayKetThuc"])
            ):
                return (
                    "Vui lòng nhập ngày bắt đầu và ngày kết thúc "
                    "theo dạng dd/mm/yyyy."
                )

            if (
                parse_date(d["NgayKetThuc"])
                <= parse_date(d["NgayBatDau"])
            ):
                return "Ngày kết thúc phải sau ngày bắt đầu."

            room = next(
                (
                    p for p in db.danh_sach_phong()
                    if p["MaPhong"] == room_id
                ),
                None
            )

            if not room:
                return "Phòng được chọn không còn tồn tại."

            if room["TinhTrang"] == "Bảo trì":
                return "Phòng đang bảo trì, vui lòng chọn phòng khác."

            if (
                room["DangO"] >= room["SoGiuong"]
                and room_id != getattr(
                    self,
                    "_editing_room_id",
                    None
                )
            ):
                return "Phòng đã đủ số lượng sinh viên."

        return None

    # ==================== THÊM SINH VIÊN ====================

    def add(self):

        self._editing_room_id = None

        d = self._dialog(
            "Thêm sinh viên"
        )

        if not d:
            return

        err = self._validate(d)

        if err:
            return error(err)

        sv_id = db.execute("""
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
            d[k]
            for k in (
                "HoTen",
                "NgaySinh",
                "GioiTinh",
                "Lop",
                "SDT",
                "QueQuan"
            )
        ))

        room_id = pick_id(d["Phong"])

        if room_id:

            db.execute("""
                INSERT INTO HopDong(
                    MaSV,
                    MaPhong,
                    NgayBatDau,
                    NgayKetThuc
                )
                VALUES (?, ?, ?, ?)
            """, (
                sv_id,
                room_id,
                d["NgayBatDau"],
                d["NgayKetThuc"]
            ))

        self.refresh()

    # ==================== CHỈNH SỬA SINH VIÊN ====================

    def edit(self):

        sv_id = self._selected_id()

        if sv_id is None:
            return

        current = db.query(
            "SELECT * FROM SinhVien WHERE MaSV=?",
            (sv_id,),
            one=True
        )

        contract = db.query("""
            SELECT *
            FROM HopDong
            WHERE MaSV=?
                AND TrangThai='Đang thuê'
            LIMIT 1
        """, (sv_id,), one=True)

        self._editing_room_id = (
            contract["MaPhong"]
            if contract
            else None
        )

        d = self._dialog(
            "Cập nhật sinh viên",
            dict(current),
            dict(contract) if contract else None
        )

        if not d:
            return

        err = self._validate(d)

        if err:
            return error(err)

        db.execute("""
            UPDATE SinhVien
            SET HoTen=?,
                NgaySinh=?,
                GioiTinh=?,
                Lop=?,
                SDT=?,
                QueQuan=?
            WHERE MaSV=?
        """, tuple(
            d[k]
            for k in (
                "HoTen",
                "NgaySinh",
                "GioiTinh",
                "Lop",
                "SDT",
                "QueQuan"
            )
        ) + (sv_id,))

        self._save_room(
            sv_id,
            d,
            contract
        )

        self.refresh()

    # ==================== XẾP / ĐỔI PHÒNG ====================

    def assign_room(self):

        sv_id = self._selected_id()

        if sv_id is None:
            return

        current = db.query(
            "SELECT * FROM SinhVien WHERE MaSV=?",
            (sv_id,),
            one=True
        )

        contract = db.query("""
            SELECT *
            FROM HopDong
            WHERE MaSV=?
                AND TrangThai='Đang thuê'
            LIMIT 1
        """, (sv_id,), one=True)

        self._editing_room_id = (
            contract["MaPhong"]
            if contract
            else None
        )

        d = self._dialog(
            "Xếp / đổi phòng cho sinh viên",
            dict(current),
            dict(contract) if contract else None
        )

        if not d:
            return

        err = self._validate(d)

        if err:
            return error(err)

        self._save_room(
            sv_id,
            d,
            contract
        )

        self.refresh()

    def _save_room(self, sv_id, d, contract):

        room_id = pick_id(d["Phong"])

        if contract:

            if room_id:

                db.execute("""
                    UPDATE HopDong
                    SET MaPhong=?,
                        NgayBatDau=?,
                        NgayKetThuc=?
                    WHERE MaHD=?
                """, (
                    room_id,
                    d["NgayBatDau"],
                    d["NgayKetThuc"],
                    contract["MaHD"]
                ))

            else:

                db.execute("""
                    UPDATE HopDong
                    SET TrangThai='Đã kết thúc',
                        NgayKetThuc=?
                    WHERE MaHD=?
                """, (
                    date.today().strftime("%d/%m/%Y"),
                    contract["MaHD"]
                ))

        elif room_id:

            db.execute("""
                INSERT INTO HopDong(
                    MaSV,
                    MaPhong,
                    NgayBatDau,
                    NgayKetThuc
                )
                VALUES (?, ?, ?, ?)
            """, (
                sv_id,
                room_id,
                d["NgayBatDau"],
                d["NgayKetThuc"]
            ))

    # ==================== XÓA SINH VIÊN ====================

    def delete(self):

        sv_id = self._selected_id()

        if sv_id is None:
            return

        confirm = messagebox.askyesno(
            "Xác nhận xóa",
            "Bạn có chắc muốn xóa sinh viên này?"
        )

        if not confirm:
            return

        try:

            db.execute(
                "DELETE FROM SinhVien WHERE MaSV=?",
                (sv_id,)
            )

        except Exception as exc:

            messagebox.showerror(
                "Không thể xóa",
                "Sinh viên đang có dữ liệu hợp đồng hoặc hóa đơn liên quan.\n"
                "Hãy kết thúc/xử lý dữ liệu liên quan trước.\n\n"
                + str(exc)
            )

            return

        self.refresh()


