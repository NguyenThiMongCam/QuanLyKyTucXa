"""Màn hình quản lý nhân viên - giao diện hiện đại theo mẫu thiết kế."""
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

import database as db

BG = "#F2F6FF"
WHITE = "#FFFFFF"
NAVY = "#123B78"
BLUE = "#1760C5"
BLUE2 = "#1685E8"
MUTED = "#71809A"
BORDER = "#DCE6F7"
GREEN = "#15945B"
GREEN_BG = "#E0F7EC"
ORANGE = "#B87508"
ORANGE_BG = "#FFF0CC"
RED = "#E34B61"
FONT = "Segoe UI"


def _rounded(parent, **kw):
    f = tk.Frame(parent, bg=WHITE, highlightthickness=1, highlightbackground=BORDER, **kw)
    return f


class NhanVienScreen(tk.Frame):
    """Quản lý tài khoản, thông tin liên hệ và phân công phòng cho từng nhân viên."""

    def __init__(self, master, user=None):
        super().__init__(master, bg=BG)
        self.user = user or {}
        self.page = 0
        self.page_size = 5
        self.selected_id = None
        self.rows_data = []
        self.kw = tk.StringVar(master=self)
        self._style()
        self._build()
        self.refresh()
        self.kw.trace_add("write", lambda *_: self._search())

    def _style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("Staff.Treeview", background=WHITE, fieldbackground=WHITE,
                     foreground="#18345F", rowheight=56, borderwidth=0,
                     font=(FONT, 10))
        st.configure("Staff.Treeview.Heading", background="#F3F7FF",
                     foreground=NAVY, font=(FONT, 10, "bold"),
                     relief="flat", padding=(8, 13))
        st.map("Staff.Treeview", background=[("selected", "#E6F0FF")],
               foreground=[("selected", NAVY)])
        st.configure("Staff.Vertical.TScrollbar", background="#E6ECF7",
                     troughcolor=WHITE, bordercolor=WHITE, arrowcolor=MUTED)

    def _build(self):
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=24, pady=(18, 20))

        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x")
        left = tk.Frame(header, bg=BG)
        left.pack(side="left", fill="x", expand=True)
        tk.Label(left, text="Quản lý nhân viên", bg=BG, fg="#1452A5",
                 font=(FONT, 20, "bold")).pack(anchor="w")
        tk.Label(left, text="Quản lý thông tin nhân viên và phân quyền hệ thống",
                 bg=BG, fg=NAVY, font=(FONT, 9)).pack(anchor="w", pady=(3, 0))

        right = tk.Frame(header, bg=BG)
        right.pack(side="right", anchor="n")
        search = tk.Entry(right, textvariable=self.kw, relief="flat", bg=WHITE,
                          fg=NAVY, insertbackground=BLUE, font=(FONT, 9),
                          highlightthickness=1, highlightbackground=BORDER,
                          highlightcolor=BLUE, width=27)
        search.pack(side="left", ipady=9, padx=(0, 10))
        search.insert(0, "")
        self.add_btn = tk.Button(right, text="＋  Thêm nhân viên", command=self.on_add,
                                 bg=BLUE, fg=WHITE, activebackground="#0E4FAE",
                                 activeforeground=WHITE, relief="flat", bd=0,
                                 font=(FONT, 9, "bold"), padx=15, pady=10,
                                 cursor="hand2")
        self.add_btn.pack(side="left")

        stats = tk.Frame(outer, bg=BG)
        stats.pack(fill="x", pady=(17, 16))
        for i in range(4):
            stats.columnconfigure(i, weight=1, uniform="stats")
        self.stat_values = []
        self._stat(stats, 0, "Tổng nhân viên", "👥", BLUE)
        self._stat(stats, 1, "Quản lý", "▣", "#1676D2")
        self._stat(stats, 2, "Nhân viên", "⚙", "#1685E8")
        self._stat(stats, 3, "Đang hoạt động", "✉", GREEN)

        card = _rounded(outer)
        card.pack(fill="both", expand=True)
        toolbar = tk.Frame(card, bg=WHITE)
        toolbar.pack(fill="x", padx=17, pady=(12, 10))
        self.count_label = tk.Label(toolbar, text="Hiển thị", bg=WHITE, fg=NAVY,
                                    font=(FONT, 9))
        self.count_label.pack(side="left")
        self.page_size_var = tk.StringVar(value="5")
        cb = ttk.Combobox(toolbar, textvariable=self.page_size_var, values=("5", "10", "20"),
                          state="readonly", width=4, font=(FONT, 9))
        cb.pack(side="left", padx=7, ipady=3)
        cb.bind("<<ComboboxSelected>>", lambda _e: self._change_page_size())
        tk.Label(toolbar, text="bản ghi", bg=WHITE, fg=NAVY, font=(FONT, 9)).pack(side="left")

        export = tk.Frame(toolbar, bg=WHITE)
        export.pack(side="right")
        tk.Button(export, text="▣  Xuất Excel", command=self.export_excel,
                  bg=WHITE, fg=NAVY, activebackground="#F3F7FF",
                  relief="flat", highlightthickness=1, highlightbackground=BORDER,
                  font=(FONT, 9, "bold"), padx=12, pady=7, cursor="hand2").pack(side="left", padx=(0, 8))
        tk.Button(export, text="▣  Xuất PDF", command=self.export_pdf,
                  bg=WHITE, fg=NAVY, activebackground="#F3F7FF",
                  relief="flat", highlightthickness=1, highlightbackground=BORDER,
                  font=(FONT, 9, "bold"), padx=12, pady=7, cursor="hand2").pack(side="left")

        line = tk.Frame(card, bg=BORDER, height=1)
        line.pack(fill="x")
        table_wrap = tk.Frame(card, bg=WHITE)
        table_wrap.pack(fill="both", expand=True, padx=8, pady=4)
        cols = ("stt", "name", "role", "phone", "email", "rooms", "status", "actions")
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings",
                                 style="Staff.Treeview", selectmode="browse")
        headings = [("stt", "STT", 42), ("name", "Tên nhân viên", 150),
                    ("role", "Chức vụ", 95), ("phone", "Số điện thoại", 112),
                    ("email", "Email", 135), ("rooms", "Phòng phụ trách", 145),
                    ("status", "Trạng thái", 105), ("actions", "Thao tác", 80)]
        for key, title, width in headings:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=55, anchor="w" if key != "stt" else "center",
                             stretch=True)
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview,
                           style="Staff.Vertical.TScrollbar")
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<<TreeviewSelect>>", self._picked)
        self.tree.bind("<Double-1>", lambda _e: self.on_edit())
        self.tree.bind("<Button-1>", self._action_click, add="+")

        foot = tk.Frame(card, bg=WHITE)
        foot.pack(fill="x", padx=17, pady=(8, 13))
        self.footer_text = tk.Label(foot, bg=WHITE, fg=MUTED, font=(FONT, 9))
        self.footer_text.pack(side="left")
        nav = tk.Frame(foot, bg=WHITE)
        nav.pack(side="right")
        self.prev_btn = tk.Button(nav, text="‹", command=lambda: self._go(-1),
                                  bg=WHITE, fg=NAVY, relief="flat", highlightthickness=1,
                                  highlightbackground=BORDER, width=3, font=(FONT, 12))
        self.prev_btn.pack(side="left", padx=3)
        self.page_label = tk.Label(nav, text="1", bg=BLUE, fg=WHITE, width=3,
                                   font=(FONT, 9, "bold"), pady=7)
        self.page_label.pack(side="left", padx=3)
        self.next_btn = tk.Button(nav, text="›", command=lambda: self._go(1),
                                  bg=WHITE, fg=NAVY, relief="flat", highlightthickness=1,
                                  highlightbackground=BORDER, width=3, font=(FONT, 12))
        self.next_btn.pack(side="left", padx=3)

    def _stat(self, parent, col, label, symbol, color):
        box = tk.Frame(parent, bg=WHITE, highlightthickness=1, highlightbackground=BORDER)
        box.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 10, 0), ipady=9)
        top = tk.Frame(box, bg=WHITE)
        top.pack(fill="x", padx=12, pady=(4, 0))
        bubble = tk.Label(top, text=symbol, bg="#E5F1FF", fg=color,
                          font=(FONT, 18, "bold"), width=3, height=1)
        bubble.pack(side="left", padx=(0, 9), ipady=7)
        txt = tk.Frame(top, bg=WHITE)
        txt.pack(side="left", fill="x", expand=True)
        tk.Label(txt, text=label, bg=WHITE, fg=NAVY,
                 font=(FONT, 9, "bold")).pack(anchor="w")
        value = tk.Label(txt, text="0", bg=WHITE, fg="#174F9D",
                         font=(FONT, 20, "bold"))
        value.pack(anchor="w", pady=(2, 0))
        self.stat_values.append(value)

    def refresh(self):
        self.selected_id = None
        self.rows_data = [dict(r) for r in db.query("""
            SELECT n.MaNV, n.TenDangNhap, n.HoTen, n.VaiTro,
                   COALESCE(n.SoDienThoai, '') AS SoDienThoai,
                   COALESCE(n.Email, '') AS Email,
                   COALESCE(n.TrangThai, 'Đang hoạt động') AS TrangThai,
                   COALESCE((SELECT GROUP_CONCAT(p.TenPhong, ', ')
                     FROM PhanCongPhong pc JOIN Phong p ON p.MaPhong=pc.MaPhong
                     WHERE pc.MaNV=n.MaNV), 'Chưa phân công') AS PhongPhuTrach
            FROM NhanVien n ORDER BY n.MaNV
        """)]
        self.stat_values[0].config(text=str(len(self.rows_data)))
        self.stat_values[1].config(text=str(sum(r["VaiTro"] == "admin" for r in self.rows_data)))
        self.stat_values[2].config(text=str(sum(r["VaiTro"] != "admin" for r in self.rows_data)))
        self.stat_values[3].config(text=str(sum(r["TrangThai"] == "Đang hoạt động" for r in self.rows_data)))
        self._render()

    def _search(self):
        self.page = 0
        self._render()

    def _filtered(self):
        key = self.kw.get().strip().lower()
        if not key:
            return self.rows_data
        return [r for r in self.rows_data if key in " ".join(str(r[k]) for k in
                ("HoTen", "TenDangNhap", "VaiTro", "SoDienThoai", "Email", "PhongPhuTrach")).lower()]

    def _render(self):
        filtered = self._filtered()
        pages = max(1, (len(filtered) + self.page_size - 1) // self.page_size)
        self.page = min(self.page, pages - 1)
        self.tree.delete(*self.tree.get_children())
        start = self.page * self.page_size
        for idx, r in enumerate(filtered[start:start + self.page_size], start + 1):
            role = "Quản lý" if r["VaiTro"] == "admin" else "Nhân viên"
            rooms = r["PhongPhuTrach"]
            if len(rooms) > 27:
                rooms = rooms[:24] + "..."
            self.tree.insert("", "end", iid=str(r["MaNV"]),
                             values=(idx, r["HoTen"], role, r["SoDienThoai"] or "—",
                                     r["Email"] or "—", rooms,
                                     r["TrangThai"], "✎     🗑"))
        self.count_label.config(text="Hiển thị")
        self.footer_text.config(text=f"Hiển thị {min(start + 1, len(filtered)) if filtered else 0} - "
                                     f"{min(start + self.page_size, len(filtered))} / {len(filtered)} nhân viên")
        self.page_label.config(text=f"{self.page + 1}/{pages}")
        self.prev_btn.config(state="normal" if self.page > 0 else "disabled")
        self.next_btn.config(state="normal" if self.page < pages - 1 else "disabled")

    def _picked(self, _event=None):
        sel = self.tree.selection()
        self.selected_id = int(sel[0]) if sel else None

    def _action_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        col = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        if region == "cell" and col == "#8" and item:
            self.tree.selection_set(item)
            self.selected_id = int(item)
            # Cột thao tác hiển thị biểu tượng sửa và xóa.
            if event.x < self.tree.winfo_width() - 39:
                self.after(20, self.on_edit)
            else:
                self.after(20, self.on_delete)

    def _go(self, step):
        self.page += step
        self._render()

    def _change_page_size(self):
        self.page_size = int(self.page_size_var.get())
        self.page = 0
        self._render()

    def _room_options(self):
        return [dict(r) for r in db.query("SELECT MaPhong, TenPhong FROM Phong ORDER BY TenPhong")]

    def _dialog(self, title, current=None):
        current = current or {}
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=WHITE)
        win.transient(self.winfo_toplevel())
        win.resizable(False, False)
        win.grab_set()
        win.geometry("540x650")
        win.update_idletasks()
        x = self.winfo_rootx() + max(20, (self.winfo_width() - 540) // 2)
        y = self.winfo_rooty() + max(20, (self.winfo_height() - 650) // 2)
        win.geometry(f"+{x}+{y}")

        head = tk.Frame(win, bg=WHITE)
        head.pack(fill="x", padx=22, pady=(17, 10))
        tk.Label(head, text="♟", bg=WHITE, fg=BLUE2, font=(FONT, 18, "bold")).pack(side="left", padx=(0, 9))
        tk.Label(head, text=title, bg=WHITE, fg=NAVY, font=(FONT, 15, "bold")).pack(side="left")
        tk.Button(head, text="×", command=win.destroy, bg=WHITE, fg=NAVY,
                  relief="flat", font=(FONT, 17), cursor="hand2").pack(side="right")

        body = tk.Frame(win, bg=WHITE)
        body.pack(fill="both", expand=True, padx=24, pady=5)
        vars_ = {}
        def field(label, key, default="", kind="entry", values=None, required=False):
            tk.Label(body, text=label + (" *" if required else ""), bg=WHITE, fg=NAVY,
                     font=(FONT, 9, "bold" if required else "normal")).pack(anchor="w", pady=(8, 4))
            var = tk.StringVar(value=str(current.get(key, default) or ""))
            vars_[key] = var
            if kind == "combo":
                w = ttk.Combobox(body, textvariable=var, values=values or [], state="readonly",
                                 font=(FONT, 9))
            else:
                w = tk.Entry(body, textvariable=var, relief="flat", bg="#FBFCFF",
                             fg=NAVY, font=(FONT, 10), highlightthickness=1,
                             highlightbackground=BORDER, highlightcolor=BLUE,
                             show="*" if kind == "password" else "")
            w.pack(fill="x", ipady=7)
            return w

        field("Tên nhân viên", "HoTen", required=True)
        field("Tên đăng nhập", "TenDangNhap", required=True)
        field("Chức vụ", "VaiTro", "nhanvien", "combo", ["nhanvien", "admin"])
        field("Số điện thoại", "SoDienThoai")
        field("Email", "Email")
        field("Mật khẩu" + (" (để trống nếu không đổi)" if current else ""), "MatKhau",
              kind="password")
        field("Trạng thái", "TrangThai", "Đang hoạt động", "combo",
              ["Đang hoạt động", "Tạm khóa"])

        tk.Label(body, text="Phòng phụ trách", bg=WHITE, fg=NAVY,
                 font=(FONT, 9, "bold")).pack(anchor="w", pady=(12, 5))
        room_frame = tk.Frame(body, bg="#FBFCFF", highlightthickness=1, highlightbackground=BORDER)
        room_frame.pack(fill="both", expand=True)
        room_list = tk.Listbox(room_frame, selectmode="multiple", height=5,
                               bg="#FBFCFF", fg=NAVY, relief="flat",
                               font=(FONT, 9), selectbackground="#DCEBFF",
                               selectforeground=NAVY, activestyle="none")
        room_list.pack(side="left", fill="both", expand=True, padx=8, pady=6)
        room_sb = ttk.Scrollbar(room_frame, orient="vertical", command=room_list.yview)
        room_sb.pack(side="right", fill="y")
        room_list.configure(yscrollcommand=room_sb.set)
        rooms = self._room_options()
        assigned = {r["MaPhong"] for r in db.query("SELECT MaPhong FROM PhanCongPhong WHERE MaNV=?",
                                                   (current.get("MaNV"),))} if current.get("MaNV") else set()
        for i, room in enumerate(rooms):
            room_list.insert("end", room["TenPhong"])
            if room["MaPhong"] in assigned:
                room_list.selection_set(i)

        result = {}
        def save():
            values = {k: v.get().strip() for k, v in vars_.items()}
            if not values["HoTen"] or not values["TenDangNhap"]:
                messagebox.showwarning("Thiếu thông tin", "Vui lòng nhập tên nhân viên và tên đăng nhập.", parent=win)
                return
            if not current and len(values["MatKhau"]) < 6:
                messagebox.showwarning("Mật khẩu", "Mật khẩu phải có ít nhất 6 ký tự.", parent=win)
                return
            if values["MatKhau"] and len(values["MatKhau"]) < 6:
                messagebox.showwarning("Mật khẩu", "Mật khẩu phải có ít nhất 6 ký tự.", parent=win)
                return
            values["Rooms"] = [rooms[i]["MaPhong"] for i in room_list.curselection()]
            result.update(values)
            win.destroy()

        footer = tk.Frame(win, bg=WHITE, highlightthickness=1, highlightbackground=BORDER)
        footer.pack(fill="x", side="bottom", padx=0, pady=(8, 0))
        tk.Button(footer, text="Hủy", command=win.destroy, bg=WHITE, fg=NAVY,
                  relief="flat", highlightthickness=1, highlightbackground=BORDER,
                  font=(FONT, 9, "bold"), padx=20, pady=8).pack(side="right", padx=(8, 20), pady=10)
        tk.Button(footer, text="Lưu", command=save, bg=BLUE, fg=WHITE,
                  activebackground="#0E4FAE", relief="flat", font=(FONT, 9, "bold"),
                  padx=24, pady=8, cursor="hand2").pack(side="right", pady=10)
        win.wait_window()
        return result or None

    def _save_rooms(self, ma_nv, room_ids):
        db.execute("DELETE FROM PhanCongPhong WHERE MaNV=?", (ma_nv,))
        for ma_phong in room_ids:
            db.execute("INSERT OR IGNORE INTO PhanCongPhong(MaNV,MaPhong) VALUES(?,?)",
                       (ma_nv, ma_phong))

    def on_add(self):
        d = self._dialog("Thêm nhân viên")
        if not d:
            return
        try:
            ma = db.execute("""INSERT INTO NhanVien
                (TenDangNhap,MatKhau,HoTen,VaiTro,SoDienThoai,Email,TrangThai)
                VALUES(?,?,?,?,?,?,?)""",
                (d["TenDangNhap"], db.hash_pw(d["MatKhau"]), d["HoTen"], d["VaiTro"],
                 d["SoDienThoai"], d["Email"], d["TrangThai"]))
            self._save_rooms(ma, d["Rooms"])
        except sqlite3.IntegrityError:
            messagebox.showerror("Lỗi", "Tên đăng nhập đã tồn tại.")
            return
        self.refresh()

    def on_edit(self):
        if not self.selected_id:
            messagebox.showwarning("Thông báo", "Vui lòng chọn nhân viên cần sửa.")
            return
        cur = dict(db.query("SELECT * FROM NhanVien WHERE MaNV=?", (self.selected_id,), one=True))
        cur.setdefault("SoDienThoai", "")
        cur.setdefault("Email", "")
        cur.setdefault("TrangThai", "Đang hoạt động")
        d = self._dialog("Cập nhật nhân viên", cur)
        if not d:
            return
        try:
            if d["MatKhau"]:
                db.execute("""UPDATE NhanVien SET TenDangNhap=?,HoTen=?,VaiTro=?,
                    SoDienThoai=?,Email=?,TrangThai=?,MatKhau=? WHERE MaNV=?""",
                    (d["TenDangNhap"], d["HoTen"], d["VaiTro"], d["SoDienThoai"],
                     d["Email"], d["TrangThai"], db.hash_pw(d["MatKhau"]), self.selected_id))
            else:
                db.execute("""UPDATE NhanVien SET TenDangNhap=?,HoTen=?,VaiTro=?,
                    SoDienThoai=?,Email=?,TrangThai=? WHERE MaNV=?""",
                    (d["TenDangNhap"], d["HoTen"], d["VaiTro"], d["SoDienThoai"],
                     d["Email"], d["TrangThai"], self.selected_id))
            self._save_rooms(self.selected_id, d["Rooms"])
        except sqlite3.IntegrityError:
            messagebox.showerror("Lỗi", "Tên đăng nhập đã tồn tại.")
            return
        self.refresh()

    def on_delete(self):
        if not self.selected_id:
            messagebox.showwarning("Thông báo", "Vui lòng chọn nhân viên cần xóa.")
            return
        if self.user and self.selected_id == self.user.get("MaNV"):
            messagebox.showerror("Không thể xóa", "Không thể xóa tài khoản đang đăng nhập.")
            return
        if not messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa nhân viên này?"):
            return
        db.execute("DELETE FROM PhanCongPhong WHERE MaNV=?", (self.selected_id,))
        db.execute("DELETE FROM NhanVien WHERE MaNV=?", (self.selected_id,))
        self.refresh()

    def export_excel(self):
        from tkinter import filedialog
        from screens.xlsx_io import write_xlsx
        path = filedialog.asksaveasfilename(
            parent=self, defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
            initialfile="DanhSachNhanVien.xlsx")
        if not path:
            return
        headers = ["Mã NV", "Họ tên", "Tên đăng nhập", "Chức vụ", "Số điện thoại",
                   "Email", "Phòng phụ trách", "Trạng thái"]
        rows = [[r["MaNV"], r["HoTen"], r["TenDangNhap"],
                 "Quản lý" if r["VaiTro"] == "admin" else "Nhân viên",
                 r["SoDienThoai"], r["Email"], r["PhongPhuTrach"], r["TrangThai"]]
                for r in self._filtered()]
        write_xlsx(path, headers, rows, sheet_name="NhanVien")
        messagebox.showinfo("Xuất Excel", "Đã xuất danh sách nhân viên thành công.", parent=self)

    def export_pdf(self):
        from tkinter import filedialog
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".pdf",
                filetypes=[("PDF", "*.pdf")], initialfile="DanhSachNhanVien.pdf")
            if not path:
                return
            styles = getSampleStyleSheet()
            data = [["Mã", "Tên nhân viên", "Chức vụ", "Số điện thoại", "Email", "Phòng phụ trách", "Trạng thái"]]
            for r in self._filtered():
                data.append([r["MaNV"], r["HoTen"], "Quản lý" if r["VaiTro"] == "admin" else "Nhân viên",
                             r["SoDienThoai"], r["Email"], r["PhongPhuTrach"], r["TrangThai"]])
            doc = SimpleDocTemplate(path, pagesize=landscape(A4))
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF2FF")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#123B78")),
                ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#DCE6F7")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]))
            doc.build([Paragraph("DANH SÁCH NHÂN VIÊN", styles["Title"]), Spacer(1, 12), table])
            messagebox.showinfo("Xuất PDF", "Đã xuất danh sách nhân viên thành công.", parent=self)
        except ImportError:
            messagebox.showwarning("Thiếu thư viện", "Cần cài reportlab bằng lệnh: pip install reportlab", parent=self)

