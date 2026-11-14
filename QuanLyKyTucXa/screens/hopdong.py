
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
import database as db
from screens.base import money, pick_id


BG = "#F3F6FC"
NAVY = "#172554"
BLUE = "#2563EB"
GREEN = "#059669"
ORANGE = "#D97706"
RED = "#DC2626"
WHITE = "#FFFFFF"
TEXT = "#1E293B"
MUTED = "#64748B"


class HopDongScreen(tk.Frame):
    def __init__(self, master, user=None):
        super().__init__(master, bg=BG)
        self.user = user
        self.selected_id = None
        self.build_ui()
        self.refresh()

    def build_ui(self):
        header = tk.Frame(self, bg=NAVY, height=105)
        header.pack(fill="x")
        header.pack_propagate(False)

        left = tk.Frame(header, bg=NAVY)
        left.pack(side="left", padx=25, pady=17)

        tk.Label(
            left,
            text="QUẢN LÝ HỢP ĐỒNG",
            bg=NAVY,
            fg=WHITE,
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w")

        tk.Label(
            left,
            text="Quản lý thông tin thuê phòng và thời hạn hợp đồng sinh viên",
            bg=NAVY,
            fg="#BFDBFE",
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(5, 0))

        tk.Label(
            header,
            text="📄",
            bg=NAVY,
            fg=WHITE,
            font=("Segoe UI", 32)
        ).pack(side="right", padx=30)

        cards = tk.Frame(self, bg=BG)
        cards.pack(fill="x", padx=20, pady=18)

        self.card_values = {}

        card_data = [
            ("TỔNG HỢP ĐỒNG", "0", BLUE),
            ("ĐANG THUÊ", "0", GREEN),
            ("ĐÃ KẾT THÚC", "0", ORANGE),
            ("SINH VIÊN ĐANG Ở", "0", NAVY)
        ]

        for i, (title, value, color) in enumerate(card_data):
            card = tk.Frame(
                cards,
                bg=WHITE,
                highlightbackground="#E2E8F0",
                highlightthickness=1
            )
            card.grid(
                row=0,
                column=i,
                padx=6,
                sticky="nsew"
            )

            tk.Frame(card, bg=color, height=4).pack(fill="x")

            content = tk.Frame(
                card,
                bg=WHITE,
                padx=13,
                pady=13
            )
            content.pack(fill="both", expand=True)

            tk.Label(
                content,
                text=title,
                bg=WHITE,
                fg=MUTED,
                font=("Segoe UI", 9, "bold")
            ).pack(anchor="w")

            value_label = tk.Label(
                content,
                text=value,
                bg=WHITE,
                fg=color,
                font=("Segoe UI", 19, "bold")
            )
            value_label.pack(anchor="w", pady=(8, 2))

            self.card_values[title] = value_label
            cards.columnconfigure(i, weight=1)

        toolbar = tk.Frame(
            self,
            bg=WHITE,
            padx=15,
            pady=13
        )
        toolbar.pack(fill="x", padx=20, pady=(0, 12))

        tk.Label(
            toolbar,
            text="DANH SÁCH HỢP ĐỒNG",
            bg=WHITE,
            fg=TEXT,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=(0, 18))

        self.search_var = tk.StringVar()

        search = ttk.Entry(
            toolbar,
            textvariable=self.search_var,
            font=("Segoe UI", 10),
            width=25
        )
        search.pack(side="right", padx=(6, 0), ipady=5)
        search.bind("<Return>", lambda e: self.refresh())

        tk.Button(
            toolbar,
            text="🔍 Tìm kiếm",
            command=self.refresh,
            bg="#E0EAFF",
            fg=BLUE,
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=8,
            cursor="hand2"
        ).pack(side="right", padx=5)

        actions = tk.Frame(self, bg=BG)
        actions.pack(fill="x", padx=20, pady=(0, 12))

        self.make_button(
            actions,
            "＋ Tạo hợp đồng",
            BLUE,
            WHITE,
            self.add
        )

        self.make_button(
            actions,
            "✓ Kết thúc hợp đồng",
            ORANGE,
            WHITE,
            self.ket_thuc
        )

        self.make_button(
            actions,
            "↻ Làm mới",
            "#E2E8F0",
            TEXT,
            self.refresh
        )

        self.make_button(
            actions,
            "🗑 Xóa hợp đồng",
            "#FEE2E2",
            RED,
            self.delete
        )

        table_box = tk.Frame(
            self,
            bg=WHITE,
            highlightbackground="#E2E8F0",
            highlightthickness=1
        )
        table_box.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 18)
        )

        style = ttk.Style()

        style.configure(
            "Contract.Treeview",
            background=WHITE,
            foreground=TEXT,
            rowheight=39,
            fieldbackground=WHITE,
            font=("Segoe UI", 10)
        )

        style.configure(
            "Contract.Treeview.Heading",
            background="#E8EEF9",
            foreground=NAVY,
            font=("Segoe UI", 9, "bold"),
            padding=11
        )

        style.map(
            "Contract.Treeview",
            background=[("selected", "#BFDBFE")],
            foreground=[("selected", NAVY)]
        )

        columns = (
            "MaHD",
            "HoTen",
            "TenPhong",
            "NgayBatDau",
            "NgayKetThuc",
            "TrangThai"
        )

        self.tree = ttk.Treeview(
            table_box,
            columns=columns,
            show="headings",
            style="Contract.Treeview",
            selectmode="browse"
        )

        headings = [
            ("MaHD", "MÃ HỢP ĐỒNG", 100),
            ("HoTen", "HỌ TÊN SINH VIÊN", 220),
            ("TenPhong", "PHÒNG", 110),
            ("NgayBatDau", "NGÀY BẮT ĐẦU", 140),
            ("NgayKetThuc", "NGÀY KẾT THÚC", 140),
            ("TrangThai", "TRẠNG THÁI", 130)
        ]

        for key, title, width in headings:
            self.tree.heading(key, text=title)
            self.tree.column(
                key,
                width=width,
                minwidth=70,
                anchor="center"
            )

        scrollbar_y = ttk.Scrollbar(
            table_box,
            orient="vertical",
            command=self.tree.yview
        )

        scrollbar_x = ttk.Scrollbar(
            table_box,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set
        )

        self.tree.pack(side="top", fill="both", expand=True)
        scrollbar_y.pack(side="right", fill="y")
        scrollbar_x.pack(side="bottom", fill="x")

        self.tree.tag_configure("odd", background="#F8FAFC")
        self.tree.tag_configure("even", background=WHITE)
        self.tree.tag_configure("active", foreground=GREEN)
        self.tree.tag_configure("ended", foreground=ORANGE)

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.select_row
        )

        self.status = tk.Label(
            self,
            text="Sẵn sàng",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9)
        )
        self.status.pack(anchor="w", padx=22, pady=(0, 5))

    def make_button(self, parent, text, bg, fg, command):
        tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            relief="flat",
            padx=15,
            pady=9,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
            activebackground=bg,
            activeforeground=fg
        ).pack(side="left", padx=(0, 8))

    def select_row(self, event=None):
        selected = self.tree.selection()
        self.selected_id = int(selected[0]) if selected else None

    def rows(self, kw):
        like = f"%{kw}%"

        return db.query("""
            SELECT h.MaHD, s.HoTen, p.TenPhong,
                   h.NgayBatDau, h.NgayKetThuc, h.TrangThai
            FROM HopDong h
            JOIN SinhVien s ON s.MaSV=h.MaSV
            JOIN Phong p ON p.MaPhong=h.MaPhong
            WHERE s.HoTen LIKE ?
            OR p.TenPhong LIKE ?
            OR h.TrangThai LIKE ?
            OR CAST(h.MaHD AS TEXT) LIKE ?
            ORDER BY h.MaHD DESC
        """, (like, like, like, like))

    def refresh(self):
        rows = self.rows(self.search_var.get().strip())

        self.tree.delete(*self.tree.get_children())

        for i, r in enumerate(rows):
            values = (
                r["MaHD"],
                r["HoTen"],
                r["TenPhong"],
                r["NgayBatDau"],
                r["NgayKetThuc"],
                r["TrangThai"]
            )

            if r["TrangThai"] == "Đang thuê":
                tag = "active"
            elif r["TrangThai"] == "Đã kết thúc":
                tag = "ended"
            else:
                tag = "odd" if i % 2 else "even"

            self.tree.insert(
                "",
                "end",
                iid=str(r["MaHD"]),
                values=values,
                tags=(tag,)
            )

        total = db.query("""
            SELECT
                COUNT(*) AS Tong,
                SUM(CASE WHEN TrangThai='Đang thuê' THEN 1 ELSE 0 END) AS DangThue,
                SUM(CASE WHEN TrangThai='Đã kết thúc' THEN 1 ELSE 0 END) AS DaKetThuc
            FROM HopDong
        """, one=True)

        sinh_vien = db.query("""
            SELECT COUNT(DISTINCT MaSV)
            FROM HopDong
            WHERE TrangThai='Đang thuê'
        """, one=True)[0]

        self.card_values["TỔNG HỢP ĐỒNG"].config(
            text=str(total["Tong"] or 0)
        )

        self.card_values["ĐANG THUÊ"].config(
            text=str(total["DangThue"] or 0)
        )

        self.card_values["ĐÃ KẾT THÚC"].config(
            text=str(total["DaKetThuc"] or 0)
        )

        self.card_values["SINH VIÊN ĐANG Ở"].config(
            text=str(sinh_vien)
        )

        self.status.config(
            text=f"Đang hiển thị {len(rows)} hợp đồng"
        )

        self.selected_id = None

    def open_form(self, fields, values=None):
        win = tk.Toplevel(self)
        win.title("Tạo hợp đồng thuê phòng")
        win.geometry("570x450")
        win.resizable(False, False)
        win.configure(bg=BG)
        win.transient(self.winfo_toplevel())
        win.grab_set()

        header = tk.Frame(
            win,
            bg=NAVY,
            padx=25,
            pady=20
        )
        header.pack(fill="x")

        tk.Label(
            header,
            text="TẠO HỢP ĐỒNG MỚI",
            bg=NAVY,
            fg=WHITE,
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Điền thông tin sinh viên và thời hạn thuê phòng",
            bg=NAVY,
            fg="#BFDBFE",
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(5, 0))

        body = tk.Frame(
            win,
            bg=WHITE,
            padx=25,
            pady=20
        )
        body.pack(fill="both", expand=True, padx=15, pady=15)

        widgets = {}
        values = values or {}

        for i, (key, label, kind, options) in enumerate(fields):
            tk.Label(
                body,
                text=label,
                bg=WHITE,
                fg=TEXT,
                font=("Segoe UI", 10, "bold")
            ).grid(row=i, column=0, sticky="w", pady=11)

            if kind == "combo":
                widget = ttk.Combobox(
                    body,
                    values=options,
                    state="readonly",
                    width=35,
                    font=("Segoe UI", 10)
                )
                widget.set(values.get(key) or (options[0] if options else ""))
            else:
                widget = ttk.Entry(
                    body,
                    width=37,
                    font=("Segoe UI", 10)
                )
                widget.insert(0, str(values.get(key, "")))

            widget.grid(
                row=i,
                column=1,
                padx=(15, 0),
                pady=11,
                ipady=5
            )

            widgets[key] = widget

        result = {}

        def save(event=None):
            result.update({
                key: widget.get().strip()
                for key, widget in widgets.items()
            })
            win.destroy()

        buttons = tk.Frame(body, bg=WHITE)
        buttons.grid(
            row=len(fields),
            column=0,
            columnspan=2,
            sticky="e",
            pady=(20, 0)
        )

        tk.Button(
            buttons,
            text="Hủy",
            command=win.destroy,
            bg="#E2E8F0",
            fg=TEXT,
            relief="flat",
            padx=20,
            pady=9
        ).pack(side="left", padx=5)

        tk.Button(
            buttons,
            text="Lưu hợp đồng",
            command=save,
            bg=BLUE,
            fg=WHITE,
            relief="flat",
            padx=20,
            pady=9,
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=5)

        win.bind("<Return>", save)
        win.bind("<Escape>", lambda e: win.destroy())
        win.wait_window()

        return result or None

    def add(self):
        svs = [
            f"{r['MaSV']} - {r['HoTen']}"
            for r in db.query("""
                SELECT MaSV, HoTen
                FROM SinhVien
                WHERE MaSV NOT IN (
                    SELECT MaSV
                    FROM HopDong
                    WHERE TrangThai='Đang thuê'
                )
                ORDER BY HoTen
            """)
        ]

        phongs = [
            f"{p['MaPhong']} - {p['TenPhong']} "
            f"(còn {p['SoGiuong'] - p['DangO']} chỗ)"
            for p in db.danh_sach_phong()
            if p["TinhTrang"] in ("Trống", "Còn chỗ")
        ]

        if not svs:
            return messagebox.showwarning(
                "Thông báo",
                "Không có sinh viên nào chưa có phòng."
            )

        if not phongs:
            return messagebox.showwarning(
                "Thông báo",
                "Hiện không còn phòng trống."
            )

        fields = [
            ("SV", "Chọn sinh viên", "combo", svs),
            ("Phong", "Chọn phòng còn chỗ", "combo", phongs),
            ("NgayBatDau", "Ngày bắt đầu (dd/mm/yyyy)", "entry", None),
            ("NgayKetThuc", "Ngày kết thúc (dd/mm/yyyy)", "entry", None)
        ]

        d = self.open_form(
            fields,
            {
                "NgayBatDau": date.today().strftime("%d/%m/%Y")
            }
        )

        if not d:
            return

        try:
            bat_dau = datetime.strptime(
                d["NgayBatDau"],
                "%d/%m/%Y"
            )

            ket_thuc = datetime.strptime(
                d["NgayKetThuc"],
                "%d/%m/%Y"
            )

            if ket_thuc <= bat_dau:
                raise ValueError

        except ValueError:
            return messagebox.showerror(
                "Ngày không hợp lệ",
                "Ngày phải đúng dạng dd/mm/yyyy và ngày kết thúc phải sau ngày bắt đầu."
            )

        ma_sv = pick_id(d["SV"])
        ma_phong = pick_id(d["Phong"])

        current_student = db.query("""
            SELECT COUNT(*)
            FROM HopDong
            WHERE MaSV=? AND TrangThai='Đang thuê'
        """, (ma_sv,), one=True)[0]

        if current_student:
            return messagebox.showerror(
                "Không thể tạo hợp đồng",
                "Sinh viên này đã có hợp đồng đang thuê."
            )

        room = next(
            (p for p in db.danh_sach_phong() if p["MaPhong"] == ma_phong),
            None
        )

        if (
            room is None
            or room["TinhTrang"] not in ("Trống", "Còn chỗ")
            or room["DangO"] >= room["SoGiuong"]
        ):
            return messagebox.showerror(
                "Phòng không còn chỗ",
                "Vui lòng chọn phòng khác."
            )

        db.execute("""
            INSERT INTO HopDong(
                MaSV, MaPhong, NgayBatDau, NgayKetThuc
            )
            VALUES(?,?,?,?)
        """, (
            ma_sv,
            ma_phong,
            d["NgayBatDau"],
            d["NgayKetThuc"]
        ))

        messagebox.showinfo(
            "Thành công",
            "Đã tạo hợp đồng thuê phòng thành công!"
        )

        self.refresh()

    def ket_thuc(self):
        selected = self.tree.selection()

        if not selected:
            return messagebox.showwarning(
                "Thông báo",
                "Vui lòng chọn hợp đồng cần kết thúc."
            )

        id_ = int(selected[0])

        row = db.query(
            "SELECT TrangThai FROM HopDong WHERE MaHD=?",
            (id_,),
            one=True
        )

        if not row or row["TrangThai"] != "Đang thuê":
            return messagebox.showinfo(
                "Thông báo",
                "Hợp đồng này đã kết thúc."
            )

        if messagebox.askyesno(
            "Xác nhận kết thúc",
            "Bạn có chắc chắn muốn kết thúc hợp đồng này và trả phòng?"
        ):
            db.execute("""
                UPDATE HopDong
                SET TrangThai='Đã kết thúc',
                    NgayKetThuc=?
                WHERE MaHD=?
            """, (
                date.today().strftime("%d/%m/%Y"),
                id_
            ))

            messagebox.showinfo(
                "Thành công",
                "Đã kết thúc hợp đồng và cập nhật trạng thái phòng!"
            )

            self.refresh()

    def delete(self):
        selected = self.tree.selection()

        if not selected:
            return messagebox.showwarning(
                "Thông báo",
                "Vui lòng chọn hợp đồng cần xóa."
            )

        id_ = int(selected[0])

        if messagebox.askyesno(
            "Xác nhận xóa",
            "Bạn có chắc chắn muốn xóa hợp đồng này không?"
        ):
            try:
                db.execute(
                    "DELETE FROM HopDong WHERE MaHD=?",
                    (id_,)
                )

                self.refresh()

            except Exception:
                messagebox.showerror(
                    "Không thể xóa",
                    "Hợp đồng đang được sử dụng hoặc có dữ liệu liên quan."
                )