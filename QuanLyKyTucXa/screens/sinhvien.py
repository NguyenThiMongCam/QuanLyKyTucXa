"""Màn hình quản lý sinh viên - giao diện Admin Dashboard xanh/trắng.
Chỉ thay file này; không yêu cầu sửa main.py, base.py hoặc database.py.
"""
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import database as db
from screens.base import valid_date

# Palette đồng bộ với ảnh tham khảo
BG = "#F3F7FD"
WHITE = "#FFFFFF"
NAVY = "#10366F"
BLUE = "#1959C5"
BLUE_DARK = "#10449F"
TEXT = "#172F55"
MUTED = "#607395"
BORDER = "#D8E3F5"
PALE_BLUE = "#EAF1FF"
GREEN = "#087A43"
GREEN_BG = "#E4F5EB"
RED = "#D65C5C"
FONT = "Segoe UI"

FIELDS = [
    ("HoTen", "Họ và tên *", "Nguyễn Văn A", "entry"),
    ("MaSV", "Mã sinh viên *", "Nhập mã sinh viên", "entry"),
    ("NgaySinh", "Ngày sinh (dd/mm/yyyy)", "12/05/2005", "entry"),
    ("GioiTinh", "Giới tính", "Nam", "combo"),
    ("CCCD", "CCCD", "12 chữ số", "entry"),
    ("SDT", "Số điện thoại", "09xxxxxxxx", "entry"),
    ("Lop", "Lớp", "DHKTPM17A", "entry"),
    ("Email", "Email", "ten@example.com", "entry"),
    ("QueQuan", "Quê quán", "Xã/Phường, Tỉnh/Thành phố", "entry"),
]


def ensure_extra_columns():
    """Thêm CCCD/Email ngay từ màn hình này nếu CSDL cũ chưa có 2 cột."""
    columns = [r["name"] for r in db.query("PRAGMA table_info(SinhVien)")]
    if "CCCD" not in columns:
        db.execute("ALTER TABLE SinhVien ADD COLUMN CCCD TEXT")
    if "Email" not in columns:
        db.execute("ALTER TABLE SinhVien ADD COLUMN Email TEXT")


def validate(data):
    if not data.get("HoTen", "").strip():
        return "Họ và tên không được để trống."
    if not data.get("MaSV", "").strip() or not data["MaSV"].isdigit():
        return "Mã sinh viên bắt buộc và phải là số."
    if data.get("NgaySinh") and not valid_date(data["NgaySinh"]):
        return "Ngày sinh phải có dạng dd/mm/yyyy."
    sdt = data.get("SDT", "").strip()
    if sdt and not (sdt.isdigit() and 9 <= len(sdt) <= 11):
        return "Số điện thoại phải gồm 9-11 chữ số."
    cccd = data.get("CCCD", "").strip()
    if cccd and not (cccd.isdigit() and len(cccd) == 12):
        return "CCCD phải gồm đúng 12 chữ số."
    email = data.get("Email", "").strip()
    if email and not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        return "Email không đúng định dạng."
    return None


class SinhVienScreen(tk.Frame):
    """Màn hình quản lý sinh viên; tương thích cách khởi tạo trong main.py."""

    def __init__(self, master, user=None):
        super().__init__(master, bg=BG)
        self.user = user
        ensure_extra_columns()
        self.search_var = tk.StringVar()
        self.filter_var = tk.StringVar(value="Tất cả")
        self.selected_id = None
        self._build()
        self.refresh()

    # ----------------------------- UI helpers -----------------------------
    def _button(self, parent, text, command, bg=WHITE, fg=NAVY,
                border=BORDER, padx=13, pady=9):
        return tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
            relief="flat", bd=0, highlightthickness=1,
            highlightbackground=border, highlightcolor=border,
            cursor="hand2", font=(FONT, 10, "bold"),
            padx=padx, pady=pady
        )

    def _build(self):
        # Header
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=28, pady=(24, 17))
        title_box = tk.Frame(header, bg=BG)
        title_box.pack(side="left", anchor="w")
        tk.Frame(title_box, bg=BLUE, width=5, height=48).pack(side="left", padx=(0, 13))
        title_text = tk.Frame(title_box, bg=BG)
        title_text.pack(side="left")
        tk.Label(title_text, text="Quản lý sinh viên", bg=BG, fg=NAVY,
                 font=(FONT, 21, "bold")).pack(anchor="w")
        tk.Label(title_text, text="Danh sách sinh viên đăng ký ở ký túc xá",
                 bg=BG, fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=(3, 0))

        search = tk.Frame(header, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        search.pack(side="right", anchor="n", pady=4)
        tk.Label(search, text="⌕", bg=WHITE, fg=BLUE, font=(FONT, 17)).pack(side="left", padx=(11, 4))
        ent = tk.Entry(search, textvariable=self.search_var, relief="flat", bd=0,
                       bg=WHITE, fg=TEXT, insertbackground=BLUE, font=(FONT, 10), width=31)
        ent.pack(side="left", ipady=10, padx=(0, 12))
        ent.bind("<KeyRelease>", lambda _e: self.refresh())
        ent.bind("<Return>", lambda _e: self.refresh())

        # Summary cards
        stats = tk.Frame(self, bg=BG)
        stats.pack(fill="x", padx=28, pady=(0, 18))
        self.stat_total = self._stat_card(stats, "Tổng sinh viên", "Toàn bộ sinh viên", "#EAF1FF", "♙")
        self.stat_occupied = self._stat_card(stats, "Đang ở ký túc xá", "Đã được xếp phòng", "#E7F7EF", "⌂")
        self.stat_empty = self._stat_card(stats, "Chưa xếp phòng", "Chưa có phòng ở", "#FFF3E5", "◷")

        # Toolbar
        toolbar = tk.Frame(self, bg=BG)
        toolbar.pack(fill="x", padx=28, pady=(0, 13))
        left = tk.Frame(toolbar, bg=BG)
        left.pack(side="left")
        self._button(left, "+  Thêm", self.add, BLUE, WHITE, BLUE, 16).pack(side="left", padx=(0, 9))
        self._button(left, "✎  Sửa", self.edit_selected, WHITE, NAVY, BORDER).pack(side="left", padx=(0, 9))
        self._button(left, "⌫  Xóa", self.delete_selected, "#FFF5F5", RED, "#F1DADA").pack(side="left")
        right = tk.Frame(toolbar, bg=BG)
        right.pack(side="right")
        self._button(right, "↓  Nhập Excel", self.import_excel).pack(side="left", padx=(0, 9))
        self._button(right, "↑  Xuất Excel", self.export_excel).pack(side="left")

        # Filters
        filter_bar = tk.Frame(self, bg=BG)
        filter_bar.pack(fill="x", padx=28, pady=(0, 14))
        tk.Label(filter_bar, text="DANH SÁCH:", bg=BG, fg=MUTED,
                 font=(FONT, 9, "bold")).pack(side="left", padx=(0, 12))
        self.filter_buttons = {}
        for name in ("Tất cả", "Đang ở KTX", "Chưa xếp phòng"):
            btn = self._button(filter_bar, name, lambda n=name: self.set_filter(n),
                               WHITE, MUTED, BORDER, padx=14, pady=7)
            btn.pack(side="left", padx=(0, 8))
            self.filter_buttons[name] = btn

        # Table card
        card = tk.Frame(self, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True, padx=28, pady=(0, 25))
        table_wrap = tk.Frame(card, bg=WHITE)
        table_wrap.pack(fill="both", expand=True, padx=1, pady=1)

        style = ttk.Style(self)
        style.configure("Student.Treeview", background=WHITE, fieldbackground=WHITE,
                        foreground=TEXT, rowheight=45, borderwidth=0,
                        font=(FONT, 10))
        style.configure("Student.Treeview.Heading", background="#F0F5FD",
                        foreground="#526687", relief="flat", borderwidth=0,
                        font=(FONT, 10, "bold"), padding=(9, 14))
        style.map("Student.Treeview", background=[("selected", "#E4EEFF")],
                  foreground=[("selected", NAVY)])

        self.columns = ("MaSV", "HoTen", "NgaySinh", "GioiTinh", "Lop", "SDT", "QueQuan", "Phong")
        self.tree = ttk.Treeview(table_wrap, columns=self.columns, show="tree headings",
                                 style="Student.Treeview", selectmode="browse")
        self.tree.heading("#0", text="")
        self.tree.column("#0", width=34, minwidth=34, stretch=False, anchor="center")
        heads = {"MaSV": "Mã SV", "HoTen": "Họ và tên", "NgaySinh": "Ngày sinh",
                 "GioiTinh": "Giới tính", "Lop": "Lớp", "SDT": "SĐT",
                 "QueQuan": "Quê quán", "Phong": "Phòng đang ở"}
        widths = {"MaSV": 92, "HoTen": 155, "NgaySinh": 108, "GioiTinh": 78,
                  "Lop": 108, "SDT": 112, "QueQuan": 115, "Phong": 105}
        for col in self.columns:
            self.tree.heading(col, text=heads[col], anchor="w")
            self.tree.column(col, width=widths[col], minwidth=65, anchor="w", stretch=True)
        self.tree.tag_configure("odd", background=WHITE)
        self.tree.tag_configure("even", background="#F8FAFE")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda _e: self.edit_selected())

        footer = tk.Frame(card, bg=WHITE)
        footer.pack(fill="x", side="bottom")
        tk.Frame(footer, bg=BORDER, height=1).pack(fill="x")
        self.footer_left = tk.Label(footer, text="", bg=WHITE, fg=MUTED, font=(FONT, 9))
        self.footer_left.pack(side="left", padx=16, pady=11)
        tk.Label(footer, text="Chọn một dòng để Sửa hoặc Xóa", bg=WHITE,
                 fg=MUTED, font=(FONT, 9)).pack(side="right", padx=16, pady=11)

    def _stat_card(self, parent, title, subtitle, icon_bg, icon):
        card = tk.Frame(parent, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(side="left", fill="both", expand=True, padx=(0, 12))
        content = tk.Frame(card, bg=WHITE)
        content.pack(fill="both", padx=16, pady=13)
        top = tk.Frame(content, bg=WHITE)
        top.pack(fill="x")
        icon_box = tk.Frame(top, bg=icon_bg, width=39, height=39)
        icon_box.pack(side="left")
        icon_box.pack_propagate(False)
        tk.Label(icon_box, text=icon, bg=icon_bg, fg=BLUE, font=(FONT, 16, "bold")).pack(expand=True)
        number = tk.Label(top, text="0", bg=WHITE, fg=NAVY, font=(FONT, 22, "bold"))
        number.pack(side="right")
        tk.Label(content, text=title, bg=WHITE, fg=TEXT,
                 font=(FONT, 10, "bold")).pack(anchor="w", pady=(8, 1))
        tk.Label(content, text=subtitle, bg=WHITE, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w")
        return number

    # ----------------------------- data -----------------------------
    def rows(self, keyword=""):
        like = f"%{keyword}%"
        return db.query("""
            SELECT s.*,
              COALESCE((SELECT p.TenPhong FROM HopDong h
                JOIN Phong p ON p.MaPhong=h.MaPhong
                WHERE h.MaSV=s.MaSV AND h.TrangThai='Đang thuê' LIMIT 1), '') AS Phong
            FROM SinhVien s
            WHERE CAST(s.MaSV AS TEXT) LIKE ? OR s.HoTen LIKE ?
               OR s.Lop LIKE ? OR s.SDT LIKE ?
            ORDER BY s.MaSV
        """, (like, like, like, like))

    def refresh(self):
        if not hasattr(self, "tree"):
            return
        self.tree.delete(*self.tree.get_children())
        all_rows = self.rows(self.search_var.get().strip())
        total = len(all_rows)
        occupied = sum(1 for r in all_rows if r["Phong"])
        unassigned = total - occupied
        self.stat_total.configure(text=str(total))
        self.stat_occupied.configure(text=str(occupied))
        self.stat_empty.configure(text=str(unassigned))

        mode = self.filter_var.get()
        visible = all_rows
        if mode == "Đang ở KTX":
            visible = [r for r in all_rows if r["Phong"]]
        elif mode == "Chưa xếp phòng":
            visible = [r for r in all_rows if not r["Phong"]]

        for i, r in enumerate(visible):
            vals = [r[k] or "" for k in self.columns]
            self.tree.insert("", "end", iid=str(r["MaSV"]), text="◯",
                             values=vals, tags=("even" if i % 2 else "odd",))

        self.filter_buttons["Tất cả"].configure(text=f"Tất cả ({total})")
        self.filter_buttons["Đang ở KTX"].configure(text=f"Đang ở KTX ({occupied})")
        self.filter_buttons["Chưa xếp phòng"].configure(text=f"Chưa xếp phòng ({unassigned})")
        self.footer_left.configure(text=f"Hiển thị {len(visible)} / {total} sinh viên")
        self.selected_id = None

    def set_filter(self, value):
        self.filter_var.set(value)
        for name, btn in self.filter_buttons.items():
            if name == value:
                btn.configure(bg=PALE_BLUE, fg=BLUE_DARK, highlightbackground=BLUE)
            else:
                btn.configure(bg=WHITE, fg=MUTED, highlightbackground=BORDER)
        self.refresh()

    def _on_select(self, _event=None):
        selected = self.tree.selection()
        self.selected_id = int(selected[0]) if selected else None

    def _next_id(self):
        row = db.query("SELECT COALESCE(MAX(MaSV),0)+1 AS next_id FROM SinhVien", one=True)
        return int(row["next_id"])

    # ----------------------------- add/edit form -----------------------------
    def _form(self, title, values=None):
        values = values or {}
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=WHITE)
        win.resizable(False, False)
        win.transient(self.winfo_toplevel())
        width, height = 680, 630
        self.update_idletasks()
        x = self.winfo_rootx() + max(0, (self.winfo_width() - width) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - height) // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")

        top = tk.Frame(win, bg=WHITE)
        top.pack(fill="x", padx=28, pady=(19, 16))
        tk.Label(top, text=title, bg=WHITE, fg=NAVY,
                 font=(FONT, 16, "bold")).pack(side="left")
        tk.Button(top, text="×", command=win.destroy, bg=WHITE, fg=BLUE_DARK,
                  activebackground=PALE_BLUE, relief="flat", bd=0,
                  font=(FONT, 19), cursor="hand2", width=2).pack(side="right")
        tk.Frame(win, bg="#E8EEF8", height=1).pack(fill="x")

        body = tk.Frame(win, bg=WHITE)
        body.pack(fill="both", expand=True, padx=28, pady=(20, 10))
        widgets = {}
        for key, label, placeholder, kind in FIELDS:
            rowcol = {
                "HoTen": (0, 0), "MaSV": (0, 1),
                "NgaySinh": (1, 0), "GioiTinh": (1, 1),
                "CCCD": (2, 0), "SDT": (2, 1),
                "Lop": (3, 0), "Email": (3, 1),
                "QueQuan": (4, 0)
            }
            row, col = rowcol[key]
            span = 2 if key == "QueQuan" else 1
            cell = tk.Frame(body, bg=WHITE)
            cell.grid(row=row, column=col, columnspan=span, sticky="ew",
                      padx=(0, 18 if col == 0 and span == 1 else 0), pady=(0, 15))
            tk.Label(cell, text=label, bg=WHITE, fg=TEXT,
                     font=(FONT, 10, "bold")).pack(anchor="w", pady=(0, 7))
            if kind == "combo":
                widget = ttk.Combobox(cell, values=["Nam", "Nữ"], state="readonly", font=(FONT, 10))
                widget.set(values.get(key) or "Nam")
                widget.pack(fill="x", ipady=7)
            else:
                widget = tk.Entry(cell, font=(FONT, 10), relief="flat", bd=0,
                                  bg=WHITE, fg=TEXT, insertbackground=BLUE,
                                  highlightthickness=1, highlightbackground=BORDER,
                                  highlightcolor=BLUE)
                value = values.get(key)
                if key == "MaSV" and not values:
                    value = self._next_id()
                if value not in (None, ""):
                    widget.insert(0, str(value))
                elif not values:
                    widget.insert(0, placeholder)
                    widget.configure(fg="#8798B5")
                    widget.bind("<FocusIn>", lambda e, w=widget, p=placeholder: self._clear_hint(w, p))
                    widget.bind("<FocusOut>", lambda e, w=widget, p=placeholder: self._restore_hint(w, p))
                widget.pack(fill="x", ipady=10, padx=1)
            widgets[key] = widget
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        result = {"data": None}
        def save():
            data = {}
            for key, widget in widgets.items():
                value = widget.get().strip()
                placeholder = next(f[2] for f in FIELDS if f[0] == key)
                if key != "GioiTinh" and value == placeholder and widget.cget("fg") == "#8798B5":
                    value = ""
                data[key] = value
            error = validate(data)
            if error:
                messagebox.showerror("Dữ liệu chưa hợp lệ", error, parent=win)
                return
            result["data"] = data
            win.destroy()

        footer = tk.Frame(win, bg=WHITE, highlightbackground="#E8EEF8", highlightthickness=1)
        footer.pack(fill="x", side="bottom")
        buttons = tk.Frame(footer, bg=WHITE)
        buttons.pack(side="right", padx=28, pady=15)
        self._button(buttons, "Hủy", win.destroy, WHITE, BLUE_DARK, BORDER, 16, 9).pack(side="left", padx=(0, 11))
        self._button(buttons, "Lưu", save, BLUE, WHITE, BLUE, 18, 9).pack(side="left")
        win.bind("<Escape>", lambda _e: win.destroy())
        win.bind("<Return>", lambda _e: save())
        win.grab_set()
        win.wait_window()
        return result["data"]

    @staticmethod
    def _clear_hint(widget, placeholder):
        if widget.get() == placeholder and widget.cget("fg") == "#8798B5":
            widget.delete(0, "end")
            widget.configure(fg=TEXT)

    @staticmethod
    def _restore_hint(widget, placeholder):
        if not widget.get().strip():
            widget.insert(0, placeholder)
            widget.configure(fg="#8798B5")

    # ----------------------------- CRUD -----------------------------
    def add(self):
        data = self._form("Thêm sinh viên")
        if not data:
            return
        try:
            db.execute("""INSERT INTO SinhVien
                (MaSV,HoTen,NgaySinh,GioiTinh,Lop,SDT,QueQuan,CCCD,Email)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (int(data["MaSV"]), data["HoTen"], data["NgaySinh"], data["GioiTinh"],
                 data["Lop"], data["SDT"], data["QueQuan"], data["CCCD"], data["Email"]))
        except Exception as exc:
            messagebox.showerror("Không thể thêm sinh viên", str(exc), parent=self)
        self.refresh()

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Thông báo", "Vui lòng chọn một sinh viên trong bảng.", parent=self)
            return
        sid = int(selected[0])
        current = db.query("SELECT * FROM SinhVien WHERE MaSV=?", (sid,), one=True)
        if not current:
            return
        data = self._form("Sửa thông tin sinh viên", dict(current))
        if not data:
            return
        try:
            db.execute("""UPDATE SinhVien SET MaSV=?,HoTen=?,NgaySinh=?,GioiTinh=?,
                Lop=?,SDT=?,QueQuan=?,CCCD=?,Email=? WHERE MaSV=?""",
                (int(data["MaSV"]), data["HoTen"], data["NgaySinh"], data["GioiTinh"],
                 data["Lop"], data["SDT"], data["QueQuan"], data["CCCD"], data["Email"], sid))
        except Exception as exc:
            messagebox.showerror("Không thể cập nhật", str(exc), parent=self)
        self.refresh()

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Thông báo", "Vui lòng chọn một sinh viên trong bảng.", parent=self)
            return
        sid = int(selected[0])
        if not messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa sinh viên này?", parent=self):
            return
        try:
            db.execute("DELETE FROM SinhVien WHERE MaSV=?", (sid,))
        except Exception:
            messagebox.showerror("Không thể xóa", "Sinh viên đang có hợp đồng hoặc dữ liệu liên quan.", parent=self)
        self.refresh()

    # ----------------------------- Excel -----------------------------
    def export_excel(self):
        try:
            from openpyxl import Workbook
        except ImportError:
            messagebox.showerror("Thiếu thư viện", "Cài thư viện bằng lệnh: pip install openpyxl", parent=self)
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".xlsx",
            filetypes=[("Excel Workbook", "*.xlsx")], initialfile="DanhSachSinhVien.xlsx")
        if not path:
            return
        wb = Workbook()
        ws = wb.active
        ws.title = "SinhVien"
        ws.append(["Mã SV", "Họ và tên", "Ngày sinh", "Giới tính", "Lớp", "SĐT", "Quê quán", "CCCD", "Email"])
        for r in self.rows(self.search_var.get().strip()):
            ws.append([r[k] or "" for k in ("MaSV", "HoTen", "NgaySinh", "GioiTinh", "Lop", "SDT", "QueQuan", "CCCD", "Email")])
        for column in ws.columns:
            letter = column[0].column_letter
            ws.column_dimensions[letter].width = min(max(max(len(str(c.value or "")) for c in column) + 3, 12), 32)
        wb.save(path)
        messagebox.showinfo("Thành công", "Đã xuất danh sách sinh viên.", parent=self)

    def import_excel(self):
        try:
            from openpyxl import load_workbook
        except ImportError:
            messagebox.showerror("Thiếu thư viện", "Cài thư viện bằng lệnh: pip install openpyxl", parent=self)
            return
        path = filedialog.askopenfilename(parent=self, filetypes=[("Excel Workbook", "*.xlsx")])
        if not path:
            return
        try:
            ws = load_workbook(path, data_only=True).active
            aliases = {
                "ma sv": "MaSV", "mã sv": "MaSV", "mã sinh viên": "MaSV", "masv": "MaSV",
                "họ và tên": "HoTen", "hoten": "HoTen", "ngày sinh": "NgaySinh", "ngaysinh": "NgaySinh",
                "giới tính": "GioiTinh", "gioitinh": "GioiTinh", "lớp": "Lop", "lop": "Lop",
                "sđt": "SDT", "sdt": "SDT", "quê quán": "QueQuan", "quequan": "QueQuan",
                "cccd": "CCCD", "email": "Email"
            }
            header = {str(c.value).strip().lower(): i for i, c in enumerate(ws[1]) if c.value is not None}
            mapping = {aliases[k]: i for k, i in header.items() if k in aliases}
            if "HoTen" not in mapping:
                raise ValueError("Excel cần có cột 'Họ và tên' hoặc 'HoTen'.")
            count = 0
            for cells in ws.iter_rows(min_row=2, values_only=True):
                data = {k: ("" if cells[i] is None else str(cells[i]).strip()) for k, i in mapping.items()}
                if not data.get("HoTen"):
                    continue
                data.setdefault("MaSV", str(self._next_id()))
                for key in ("NgaySinh", "GioiTinh", "Lop", "SDT", "QueQuan", "CCCD", "Email"):
                    data.setdefault(key, "")
                if validate(data):
                    continue
                db.execute("""INSERT OR REPLACE INTO SinhVien
                    (MaSV,HoTen,NgaySinh,GioiTinh,Lop,SDT,QueQuan,CCCD,Email)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (int(data["MaSV"]), data["HoTen"], data["NgaySinh"], data["GioiTinh"] or "Nam",
                     data["Lop"], data["SDT"], data["QueQuan"], data["CCCD"], data["Email"]))
                count += 1
            self.refresh()
            messagebox.showinfo("Nhập Excel", f"Đã nhập/cập nhật {count} sinh viên.", parent=self)
        except Exception as exc:
            messagebox.showerror("Lỗi nhập Excel", str(exc), parent=self)

