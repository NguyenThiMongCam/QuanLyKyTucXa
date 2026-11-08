import tkinter as tk
from tkinter import ttk

import database as db
from screens.base import CrudScreen, error, money, pick_id


# ==============================
# MÀU SẮC
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
GREEN = "#16834A"
ORANGE = "#C47A12"


# ==============================
# FORM DIALOG HIỆN ĐẠI
# ==============================
def modern_form_dialog(parent, title, fields, initial=None):
    result = {}
    win = tk.Toplevel(parent)
    win.title(title)
    win.configure(bg=WHITE)
    win.resizable(False, False)
    win.transient(parent.winfo_toplevel())
    win.grab_set()

    w, h = 420, 400
    x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

    container = tk.Frame(win, bg=WHITE, padx=28, pady=24)
    container.pack(fill="both", expand=True)

    tk.Label(
        container, text=title,
        font=("Segoe UI", 16, "bold"),
        fg=HUIT_BLUE_DARK, bg=WHITE
    ).pack(anchor="w", pady=(0, 18))

    entries = {}

    for key, label, kind, options in fields:
        tk.Label(
            container,
            text=label + (" *" if key in ("TenPhong", "Tang") else ""),
            font=("Segoe UI", 9), fg=TEXT, bg=WHITE
        ).pack(anchor="w", pady=(8, 3))

        if kind == "entry":
            ent = ttk.Entry(container, font=("Segoe UI", 10))
            ent.pack(fill="x", ipady=6)

            if key == "TenPhong":
                ph = "Ví dụ: A301"
                ent.insert(0, ph)
                ent.config(foreground=MUTED)

                def on_in(e, entry=ent, p=ph):
                    if entry.get() == p:
                        entry.delete(0, "end")
                        entry.config(foreground=TEXT)

                def on_out(e, entry=ent, p=ph):
                    if not entry.get().strip():
                        entry.insert(0, p)
                        entry.config(foreground=MUTED)

                ent.bind("<FocusIn>", on_in)
                ent.bind("<FocusOut>", on_out)

            if initial and key in initial:
                val = str(initial.get(key, ""))
                if key == "TenPhong" and val:
                    ent.delete(0, "end")
                    ent.insert(0, val)
                    ent.config(foreground=TEXT)
                elif key != "TenPhong":
                    ent.insert(0, val)

            entries[key] = ent

        elif kind == "combo":
            cb = ttk.Combobox(
                container, values=options or [],
                state="readonly", font=("Segoe UI", 10)
            )
            cb.pack(fill="x", ipady=5)
            if initial and key in initial:
                cb.set(initial[key])
            elif options:
                cb.current(0)
            entries[key] = cb

    tk.Frame(container, bg=WHITE, height=18).pack()

    btn_frame = tk.Frame(container, bg=WHITE)
    btn_frame.pack(fill="x")

    def on_cancel():
        win.destroy()

    def on_save():
        data = {}
        for k, widget in entries.items():
            val = widget.get().strip()
            if k == "TenPhong" and val == "Ví dụ: A301":
                val = ""
            data[k] = val
        result.update(data)
        win.destroy()

    tk.Button(
        btn_frame, text="Hủy",
        font=("Segoe UI", 10), fg=TEXT, bg=WHITE,
        activebackground="#F1F5F9",
        relief="solid", borderwidth=1,
        highlightthickness=1, highlightbackground=BORDER,
        padx=18, pady=7, cursor="hand2",
        command=on_cancel
    ).pack(side="right", padx=(8, 0))

    tk.Button(
        btn_frame, text="Lưu",
        font=("Segoe UI", 10, "bold"),
        fg=WHITE, bg=HUIT_BLUE,
        activebackground=HUIT_BLUE_DARK, activeforeground=WHITE,
        relief="flat", padx=22, pady=7, cursor="hand2",
        command=on_save
    ).pack(side="right")

    win.wait_window()
    return result if result else None


# ==============================
# STYLE
# ==============================
class _PhongStyle:
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self._setup_phong_style()

    def _setup_phong_style(self):
        style = ttk.Style(self)
        style.configure("Phong.TFrame", background=BG)
        style.configure("Phong.TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("PhongTitle.TLabel", background=BG, foreground=HUIT_BLUE_DARK, font=("Segoe UI", 18, "bold"))
        style.configure("PhongSub.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))

        style.configure(
            "Phong.TButton",
            font=("Segoe UI", 9, "bold"),
            padding=(12, 8),
            background=HUIT_BLUE_LIGHT,
            foreground=HUIT_BLUE_DARK,
            borderwidth=0
        )
        style.map("Phong.TButton",
                  background=[("pressed", "#D4E4F7"), ("active", "#DCEAF9")],
                  foreground=[("disabled", "#9AA8B8")])

        style.configure("Phong.TEntry", padding=(8, 7), fieldbackground=WHITE)
        style.configure("Phong.TCombobox", padding=(7, 6), fieldbackground=WHITE)

        style.configure(
            "Phong.Treeview",
            background=WHITE, foreground=TEXT,
            fieldbackground=WHITE, rowheight=38,
            font=("Segoe UI", 9), borderwidth=0
        )
        style.configure(
            "Phong.Treeview.Heading",
            background="#E2EEFC", foreground=HUIT_BLUE_DARK,
            font=("Segoe UI", 9, "bold"),
            padding=(8, 10), relief="flat"
        )
        style.map("Phong.Treeview",
                  background=[("selected", "#C9DDF5")],
                  foreground=[("selected", NAVY)])
        style.map("Phong.Treeview.Heading",
                  background=[("active", "#D4E4F7")],
                  foreground=[("active", HUIT_BLUE_DARK)])

        self.configure(style="Phong.TFrame")

        for child in self.winfo_children():
            self._style_children(child)

        if hasattr(self, "table") and hasattr(self.table, "tree"):
            tree = self.table.tree
            tree.configure(style="Phong.Treeview")
            tree.tag_configure("odd", background="#F7FAFE", foreground=TEXT)
            tree.tag_configure("even", background=WHITE, foreground=TEXT)
            tree.tag_configure("active_status", foreground=GREEN)
            tree.tag_configure("maintenance", foreground=ORANGE)
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
            tags = ["odd" if index % 2 == 0 else "even"]
            status = str(values[-1]).lower() if values else ""
            if "bảo trì" in status or "bao tri" in status:
                tags.append("maintenance")
            elif "hoạt động" in status or "hoat dong" in status:
                tags.append("active_status")
            tree.item(item, tags=tuple(tags))

    def refresh(self):
        super().refresh()
        self._stripe_rows()
        if hasattr(self, "_update_stats"):
            self._update_stats()


# ==============================
# QUẢN LÝ LOẠI PHÒNG
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
        d = modern_form_dialog(self, "Thêm loại phòng", self.FIELDS)
        if d:
            err = self._check(d)
            if err:
                return error(err)
            db.execute(
                "INSERT INTO LoaiPhong(TenLoai,SoGiuong,GiaThue) VALUES(?,?,?)",
                (d["TenLoai"].strip(), int(d["SoGiuong"]), int(d["GiaThue"]))
            )

    def edit(self, id_):
        cur = dict(db.query("SELECT * FROM LoaiPhong WHERE MaLoai=?", (id_,), one=True))
        d = modern_form_dialog(self, "Cập nhật loại phòng", self.FIELDS, cur)
        if d:
            err = self._check(d)
            if err:
                return error(err)
            db.execute(
                "UPDATE LoaiPhong SET TenLoai=?,SoGiuong=?,GiaThue=? WHERE MaLoai=?",
                (d["TenLoai"].strip(), int(d["SoGiuong"]), int(d["GiaThue"]), id_)
            )

    def delete(self, id_):
        db.execute("DELETE FROM LoaiPhong WHERE MaLoai=?", (id_,))


# ==============================
# QUẢN LÝ PHÒNG (GIAO DIỆN GIỐNG ẢNH)
# ==============================
class PhongScreen(_PhongStyle, CrudScreen):
    title = "QUẢN LÝ PHÒNG"

    columns = [
        ("MaPhong", "Mã", 60),
        ("TenPhong", "Tên phòng", 110),
        ("TenLoai", "Loại phòng", 140),
        ("Tang", "Tầng", 60),
        ("SoGiuong", "Số giường", 85),
        ("DangO", "Đang ở", 75),
        ("GiaThue", "Giá/người/tháng", 140),
        ("TinhTrang", "Trạng thái", 110),
    ]

    extra = [
        ("🏷 Quản lý loại phòng", "open_loai")
    ]

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self._build_header_and_stats()

    def _build_header_and_stats(self):
        # Xóa header mặc định của CrudScreen nếu có
        for child in self.winfo_children():
            if isinstance(child, ttk.Frame) and child != getattr(self, "table", None):
                pass

        # ===== HEADER =====
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=20, pady=(16, 8), before=self.table if hasattr(self, "table") else None)

        # Tiêu đề + mô tả
        title_frame = tk.Frame(header, bg=BG)
        title_frame.pack(side="left", fill="y")

        tk.Label(
            title_frame, text="Quản lý phòng",
            font=("Segoe UI", 18, "bold"),
            fg=HUIT_BLUE_DARK, bg=BG
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text="Theo dõi tình trạng phòng, giường trống và giá thuê",
            font=("Segoe UI", 9), fg=MUTED, bg=BG
        ).pack(anchor="w", pady=(2, 0))

        # Nút + Thêm
        btn_add = tk.Button(
            header, text="+ Thêm",
            font=("Segoe UI", 10, "bold"),
            fg=WHITE, bg=HUIT_BLUE,
            activebackground=HUIT_BLUE_DARK, activeforeground=WHITE,
            relief="flat", padx=16, pady=8, cursor="hand2",
            command=self.add
        )
        btn_add.pack(side="right", padx=(8, 0))

        # ===== STATS CARDS =====
        stats = tk.Frame(self, bg=BG)
        stats.pack(fill="x", padx=20, pady=(4, 12))

        def make_card(parent, title, value, unit="", color=HUIT_BLUE_DARK):
            card = tk.Frame(parent, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
            card.pack(side="left", fill="both", expand=True, padx=(0, 12))

            inner = tk.Frame(card, bg=WHITE, padx=16, pady=12)
            inner.pack(fill="both", expand=True)

            tk.Label(inner, text=title, font=("Segoe UI", 9), fg=MUTED, bg=WHITE).pack(anchor="w")
            val_frame = tk.Frame(inner, bg=WHITE)
            val_frame.pack(anchor="w", pady=(4, 0))
            tk.Label(val_frame, text=str(value), font=("Segoe UI", 22, "bold"), fg=color, bg=WHITE).pack(side="left")
            if unit:
                tk.Label(val_frame, text=unit, font=("Segoe UI", 11), fg=MUTED, bg=WHITE).pack(side="left", padx=(4, 0), pady=(6, 0))
            return card

        self.card_total = make_card(stats, "Tổng số phòng", "0")
        self.card_empty = make_card(stats, "Phòng đang trống", "0", color=GREEN)
        self.card_rate = make_card(stats, "Tỷ lệ lấp đầy", "0", "%", color=HUIT_BLUE)

        # Lưu reference để cập nhật
        self.lbl_total = self.card_total.winfo_children()[0].winfo_children()[1].winfo_children()[0]
        self.lbl_empty = self.card_empty.winfo_children()[0].winfo_children()[1].winfo_children()[0]
        self.lbl_rate = self.card_rate.winfo_children()[0].winfo_children()[1].winfo_children()[0]

        # ===== THANH TÌM KIẾM =====
        search_frame = tk.Frame(self, bg=BG)
        search_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, font=("Segoe UI", 10))
        search_entry.pack(side="left", fill="x", expand=True, ipady=6)
        search_entry.insert(0, "Tìm theo tên phòng, loại phòng...")
        search_entry.config(foreground=MUTED)

        def on_focus_in(e):
            if search_entry.get() == "Tìm theo tên phòng, loại phòng...":
                search_entry.delete(0, "end")
                search_entry.config(foreground=TEXT)

        def on_focus_out(e):
            if not search_entry.get().strip():
                search_entry.insert(0, "Tìm theo tên phòng, loại phòng...")
                search_entry.config(foreground=MUTED)

        search_entry.bind("<FocusIn>", on_focus_in)
        search_entry.bind("<FocusOut>", on_focus_out)
        search_entry.bind("<KeyRelease>", lambda e: self.refresh())

        # Gọi cập nhật thống kê lần đầu
        self.after(100, self._update_stats)

    def _update_stats(self):
        try:
            rooms = db.danh_sach_phong()
            total = len(rooms)
            empty = sum(1 for r in rooms if str(r.get("DangO", "0")) in ("0", "0/0") or "trống" in str(r.get("TinhTrang", "")).lower())
            # Tính tỷ lệ lấp đầy đơn giản
            filled = 0
            capacity = 0
            for r in rooms:
                try:
                    dang_o = str(r.get("DangO", "0")).split("/")[0]
                    so_giuong = int(r.get("SoGiuong", 0) or 0)
                    filled += int(dang_o)
                    capacity += so_giuong
                except:
                    pass
            rate = round(filled / capacity * 100) if capacity > 0 else 0

            self.lbl_total.config(text=str(total))
            self.lbl_empty.config(text=str(empty))
            self.lbl_rate.config(text=str(rate))
        except Exception:
            pass

    def rows(self, kw):
        out = []
        keyword = (kw or "").strip().lower()
        if keyword == "tìm theo tên phòng, loại phòng...":
            keyword = ""

        for p in db.danh_sach_phong():
            searchable = " ".join([
                str(p.get("MaPhong", "")),
                str(p.get("TenPhong", "")),
                str(p.get("TenLoai", "")),
                str(p.get("Tang", "")),
                str(p.get("TinhTrang", ""))
            ]).lower()
            if not keyword or keyword in searchable:
                out.append(dict(p, GiaThue=money(p["GiaThue"])))
        return out

    def on_extra(self, method):
        if method == "open_loai":
            win = tk.Toplevel(self)
            win.title("Quản lý loại phòng")
            win.geometry("820x500")
            win.minsize(680, 420)
            win.configure(bg=BG)
            LoaiPhongScreen(win).pack(fill="both", expand=True)
            win.transient(self.winfo_toplevel())
            win.grab_set()
            win.wait_window()
            self.refresh()

    def _loai_opts(self):
        return [
            f"{r['MaLoai']} - {r['TenLoai']} ({r['SoGiuong']} giường)"
            for r in db.query("SELECT * FROM LoaiPhong ORDER BY MaLoai")
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
            return error("Hãy thêm loại phòng trước (nút Quản lý loại phòng).")

        d = modern_form_dialog(self, "Thêm phòng", self._fields())
        if d:
            err = self._check(d)
            if err:
                return error(err)
            db.execute(
                "INSERT INTO Phong(TenPhong,MaLoai,Tang,TrangThai) VALUES(?,?,?,?)",
                (d["TenPhong"].strip(), pick_id(d["Loai"]), int(d["Tang"]), d["TrangThai"])
            )
            self.refresh()

    def edit(self, id_):
        cur = dict(db.query("SELECT * FROM Phong WHERE MaPhong=?", (id_,), one=True))
        opts = self._loai_opts()
        if not opts:
            return error("Chưa có dữ liệu loại phòng.")

        cur["Loai"] = next((o for o in opts if pick_id(o) == cur["MaLoai"]), opts[0])

        d = modern_form_dialog(self, "Cập nhật thông tin phòng", self._fields(), cur)
        if d:
            err = self._check(d, id_)
            if err:
                return error(err)
            db.execute(
                "UPDATE Phong SET TenPhong=?,MaLoai=?,Tang=?,TrangThai=? WHERE MaPhong=?",
                (d["TenPhong"].strip(), pick_id(d["Loai"]), int(d["Tang"]), d["TrangThai"], id_)
            )
            self.refresh()

    def delete(self, id_):
        db.execute("DELETE FROM Phong WHERE MaPhong=?", (id_,))
        self.refresh()