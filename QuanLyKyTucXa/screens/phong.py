import tkinter as tk
from tkinter import ttk

import database as db
from screens.base import CrudScreen, error, form_dialog, money, pick_id


# ==============================
# MAU SAC GIAO DIEN HUIT
# ==============================

HUIT_BLUE = "#034EA2"
HUIT_BLUE_DARK = "#023B7A"
HUIT_BLUE_LIGHT = "#EAF2FB"
HUIT_RED = "#ED1C24"

NAVY = "#142B4A"

BG = "#F4F7FB"
TEXT = "#263445"
MUTED = "#64748B"
WHITE = "#FFFFFF"
BORDER = "#DCE5F0"


# ==============================
# GIAO DIEN CHUNG
# ==============================

class _PhongStyle:

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self._setup_phong_style()

    def _setup_phong_style(self):

        style = ttk.Style(self)

        # Nen va tieu de
        style.configure(
            "Phong.TFrame",
            background=BG
        )

        style.configure(
            "Phong.TLabel",
            background=BG,
            foreground=TEXT,
            font=("Segoe UI", 10)
        )

        style.configure(
            "PhongTitle.TLabel",
            background=BG,
            foreground=HUIT_BLUE_DARK,
            font=("Segoe UI", 17, "bold")
        )

        style.configure(
            "PhongSub.TLabel",
            background=BG,
            foreground=MUTED,
            font=("Segoe UI", 9)
        )

        # Nut bam
        style.configure(
            "Phong.TButton",
            font=("Segoe UI", 9, "bold"),
            padding=(12, 8),
            background=HUIT_BLUE_LIGHT,
            foreground=HUIT_BLUE_DARK,
            borderwidth=0
        )

        style.map(
            "Phong.TButton",
            background=[
                ("pressed", "#D4E4F7"),
                ("active", "#DCEAF9")
            ],
            foreground=[
                ("disabled", "#9AA8B8")
            ]
        )

        # O nhap
        style.configure(
            "Phong.TEntry",
            padding=(8, 7),
            fieldbackground=WHITE
        )

        style.configure(
            "Phong.TCombobox",
            padding=(7, 6),
            fieldbackground=WHITE
        )

        # Bang du lieu
        style.configure(
            "Phong.Treeview",
            background=WHITE,
            foreground=TEXT,
            fieldbackground=WHITE,
            rowheight=36,
            font=("Segoe UI", 9),
            borderwidth=0
        )

        # Tieu de cot - nen xanh nhat/trang, chu mau xanh duong đậm
        style.configure(
            "Phong.Treeview.Heading",
            background="#E2EEFC",
            foreground=HUIT_BLUE_DARK,
            font=("Segoe UI", 9, "bold"),
            padding=(8, 10),
            relief="flat"
        )

        style.map(
            "Phong.Treeview",
            background=[
                ("selected", "#C9DDF5")
            ],
            foreground=[
                ("selected", NAVY)
            ]
        )

        style.map(
            "Phong.Treeview.Heading",
            background=[
                ("active", "#D4E4F7")
            ],
            foreground=[
                ("active", HUIT_BLUE_DARK)
            ]
        )

        self.configure(style="Phong.TFrame")

        # Ap dung giao dien cho cac widget con
        for child in self.winfo_children():
            self._style_children(child)

        if hasattr(self, "table") and hasattr(self.table, "tree"):

            tree = self.table.tree

            tree.configure(style="Phong.Treeview")

            tree.tag_configure(
                "odd",
                background="#F7FAFE",
                foreground=TEXT
            )

            tree.tag_configure(
                "even",
                background=WHITE,
                foreground=TEXT
            )

            tree.tag_configure(
                "active_status",
                foreground="#16834A"
            )

            tree.tag_configure(
                "maintenance",
                foreground="#C47A12"
            )

            self._stripe_rows()

    def _style_children(self, parent):

        for widget in parent.winfo_children():

            if isinstance(widget, ttk.Frame):

                try:
                    widget.configure(style="Phong.TFrame")
                except tk.TclError:
                    pass

                self._style_children(widget)

            elif isinstance(widget, ttk.Label):

                current = str(widget.cget("style"))

                if "Title" not in current:
                    widget.configure(style="Phong.TLabel")

            elif isinstance(widget, ttk.Button):

                widget.configure(style="Phong.TButton")

            elif isinstance(widget, ttk.Entry):

                widget.configure(style="Phong.TEntry")

            elif isinstance(widget, ttk.Combobox):

                widget.configure(style="Phong.TCombobox")

    def _stripe_rows(self):

        if not hasattr(self, "table") or not hasattr(self.table, "tree"):
            return

        tree = self.table.tree

        for index, item in enumerate(tree.get_children()):

            values = tree.item(item, "values")

            tags = [
                "odd" if index % 2 == 0 else "even"
            ]

            status = str(values[-1]).lower() if values else ""

            if "bảo trì" in status or "bao tri" in status:

                tags.append("maintenance")

            elif "hoạt động" in status or "hoat dong" in status:

                tags.append("active_status")

            tree.item(item, tags=tuple(tags))

    def refresh(self):

        super().refresh()
        self._stripe_rows()


# ==============================
# QUAN LY LOAI PHONG
# ==============================

class LoaiPhongScreen(_PhongStyle, CrudScreen):

    title = "QUẢN LÝ LOẠI PHÒNG"

    columns = [
        ("MaLoai", "Mã", 65),
        ("TenLoai", "Tên loại phòng", 220),
        ("SoGiuong", "Số giường", 100),
        ("GiaThue", "Giá thuê (đ/người/tháng)", 190),
    ]

    FIELDS = [
        ("TenLoai", "Tên loại phòng", "entry", None),
        ("SoGiuong", "Số giường", "entry", None),
        ("GiaThue", "Giá thuê (đ/người/tháng)", "entry", None),
    ]

    def rows(self, kw):

        return [
            dict(r, GiaThue=money(r["GiaThue"]))
            for r in db.query(
                "SELECT * FROM LoaiPhong WHERE TenLoai LIKE ? ORDER BY MaLoai",
                (f"%{kw}%",)
            )
        ]

    def _check(self, d):

        if not d["TenLoai"].strip():
            return "Tên loại không được để trống."

        if not (d["SoGiuong"].isdigit() and int(d["SoGiuong"]) > 0):
            return "Số giường phải là số nguyên dương."

        if not (d["GiaThue"].isdigit() and int(d["GiaThue"]) > 0):
            return "Giá thuê phải là số nguyên dương."

    def add(self):

        d = form_dialog(
            self,
            "Thêm loại phòng",
            self.FIELDS
        )

        if d:

            err = self._check(d)

            if err:
                return error(err)

            db.execute(
                "INSERT INTO LoaiPhong(TenLoai,SoGiuong,GiaThue) VALUES(?,?,?)",
                (
                    d["TenLoai"].strip(),
                    int(d["SoGiuong"]),
                    int(d["GiaThue"])
                )
            )

    def edit(self, id_):

        cur = dict(
            db.query(
                "SELECT * FROM LoaiPhong WHERE MaLoai=?",
                (id_,),
                one=True
            )
        )

        d = form_dialog(
            self,
            "Cập nhật loại phòng",
            self.FIELDS,
            cur
        )

        if d:

            err = self._check(d)

            if err:
                return error(err)

            db.execute(
                "UPDATE LoaiPhong SET TenLoai=?,SoGiuong=?,GiaThue=? WHERE MaLoai=?",
                (
                    d["TenLoai"].strip(),
                    int(d["SoGiuong"]),
                    int(d["GiaThue"]),
                    id_
                )
            )

    def delete(self, id_):

        db.execute(
            "DELETE FROM LoaiPhong WHERE MaLoai=?",
            (id_,)
        )


# ==============================
# QUAN LY PHONG KY TUC XA
# ==============================

class PhongScreen(_PhongStyle, CrudScreen):

    title = "QUẢN LÝ PHÒNG KÝ TÚC XÁ"

    columns = [
        ("MaPhong", "Mã", 60),
        ("TenPhong", "Tên phòng", 115),
        ("TenLoai", "Loại phòng", 145),
        ("Tang", "Tầng", 60),
        ("SoGiuong", "Số giường", 85),
        ("DangO", "Đang ở", 75),
        ("GiaThue", "Giá/người/tháng", 145),
        ("TinhTrang", "Trạng thái", 110),
    ]

    extra = [
        ("🏷 Quản lý loại phòng", "open_loai")
    ]

    def rows(self, kw):

        out = []
        keyword = kw.strip().lower()

        for p in db.danh_sach_phong():

            searchable = " ".join([
                str(p.get("MaPhong", "")),
                str(p.get("TenPhong", "")),
                str(p.get("TenLoai", "")),
                str(p.get("Tang", "")),
                str(p.get("TinhTrang", ""))
            ]).lower()

            if keyword in searchable:

                out.append(
                    dict(p, GiaThue=money(p["GiaThue"]))
                )

        return out

    def on_extra(self, method):

        if method == "open_loai":

            win = tk.Toplevel(self)

            win.title("Quản lý loại phòng")
            win.geometry("820x500")
            win.minsize(680, 420)
            win.configure(bg=BG)

            LoaiPhongScreen(win).pack(
                fill="both",
                expand=True
            )

            win.transient(self.winfo_toplevel())
            win.grab_set()
            win.wait_window()

            self.refresh()

    def _loai_opts(self):

        return [
            f"{r['MaLoai']} - {r['TenLoai']} ({r['SoGiuong']} giường)"
            for r in db.query(
                "SELECT * FROM LoaiPhong ORDER BY MaLoai"
            )
        ]

    def _fields(self):

        return [
            ("TenPhong", "Tên phòng", "entry", None),
            ("Loai", "Loại phòng", "combo", self._loai_opts()),
            ("Tang", "Tầng", "entry", None),
            ("TrangThai", "Trạng thái", "combo", ["Hoạt động", "Bảo trì"])
        ]

    def _check(self, d, id_=None):

        if not d["TenPhong"].strip():
            return "Tên phòng không được để trống."

        if not d["Tang"].isdigit() or int(d["Tang"]) < 0:
            return "Tầng phải là số nguyên không âm."

        dup = db.query(
            "SELECT MaPhong FROM Phong WHERE TenPhong=? AND MaPhong<>?",
            (d["TenPhong"].strip(), id_ or 0),
            one=True
        )

        if dup:
            return "Tên phòng đã tồn tại."

    def add(self):

        if not self._loai_opts():

            return error(
                "Hãy thêm loại phòng trước (nút Quản lý loại phòng)."
            )

        d = form_dialog(
            self,
            "Thêm phòng mới",
            self._fields()
        )

        if d:

            err = self._check(d)

            if err:
                return error(err)

            db.execute(
                "INSERT INTO Phong(TenPhong,MaLoai,Tang,TrangThai) VALUES(?,?,?,?)",
                (
                    d["TenPhong"].strip(),
                    pick_id(d["Loai"]),
                    int(d["Tang"]),
                    d["TrangThai"]
                )
            )

    def edit(self, id_):

        cur = dict(
            db.query(
                "SELECT * FROM Phong WHERE MaPhong=?",
                (id_,),
                one=True
            )
        )

        opts = self._loai_opts()

        if not opts:
            return error("Chưa có dữ liệu loại phòng.")

        cur["Loai"] = next(
            (o for o in opts if pick_id(o) == cur["MaLoai"]),
            opts[0]
        )

        d = form_dialog(
            self,
            "Cập nhật thông tin phòng",
            self._fields(),
            cur
        )

        if d:

            err = self._check(d, id_)

            if err:
                return error(err)

            db.execute(
                "UPDATE Phong SET TenPhong=?,MaLoai=?,Tang=?,TrangThai=? WHERE MaPhong=?",
                (
                    d["TenPhong"].strip(),
                    pick_id(d["Loai"]),
                    int(d["Tang"]),
                    d["TrangThai"],
                    id_
                )
            )

    def delete(self, id_):

        db.execute(
            "DELETE FROM Phong WHERE MaPhong=?",
            (id_,)
        )