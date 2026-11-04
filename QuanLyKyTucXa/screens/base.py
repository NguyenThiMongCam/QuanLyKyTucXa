"""Thành phần giao diện dùng chung: bảng, hộp thoại nhập liệu, màn hình CRUD."""
import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

FONT_TITLE = ("Segoe UI", 15, "bold")


def money(n):
    return f"{int(n or 0):,}".replace(",", ".")


def error(msg):
    messagebox.showerror("Lỗi", msg)


def parse_date(s):
    return datetime.strptime(s, "%d/%m/%Y")


def valid_date(s):
    try:
        parse_date(s)
        return True
    except ValueError:
        return False


def pick_id(text):
    """Lấy mã từ chuỗi combobox dạng '3 - Tên'."""
    return int(text.split(" - ")[0])


class Table(ttk.Frame):
    def __init__(self, master, columns):
        super().__init__(master)
        self.keys = [c[0] for c in columns]
        self.tree = ttk.Treeview(self, columns=self.keys, show="headings", selectmode="browse")
        for key, head, width in columns:
            self.tree.heading(key, text=head)
            self.tree.column(key, width=width, anchor="w")
        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    def load(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", iid=str(r[self.keys[0]]),
                             values=[r[k] for k in self.keys])

    def selected(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None


def form_dialog(parent, title, fields, values=None):
    """fields: [(key, nhãn, 'entry'|'combo'|'password', danh sách lựa chọn)]. Trả về dict hoặc None."""
    values = values or {}
    win = tk.Toplevel(parent)
    win.title(title)
    win.transient(parent.winfo_toplevel())
    win.resizable(False, False)
    widgets, result = {}, {}
    for i, (key, label, kind, opts) in enumerate(fields):
        ttk.Label(win, text=label).grid(row=i, column=0, sticky="w", padx=12, pady=6)
        if kind == "combo":
            w = ttk.Combobox(win, values=opts, state="readonly", width=34)
            w.set(values.get(key) or (opts[0] if opts else ""))
        else:
            w = ttk.Entry(win, width=37, show="*" if kind == "password" else "")
            v = values.get(key)
            w.insert(0, "" if v is None else str(v))
        w.grid(row=i, column=1, padx=12, pady=6)
        widgets[key] = w

    def ok(_e=None):
        result.update({k: w.get().strip() for k, w in widgets.items()})
        win.destroy()

    bar = ttk.Frame(win)
    bar.grid(row=len(fields), column=0, columnspan=2, pady=10)
    ttk.Button(bar, text="Lưu", command=ok).pack(side="left", padx=6)
    ttk.Button(bar, text="Hủy", command=win.destroy).pack(side="left", padx=6)
    win.bind("<Return>", ok)
    win.bind("<Escape>", lambda _e: win.destroy())
    win.grab_set()
    win.wait_window()
    return result or None


class CrudScreen(ttk.Frame):
    """Màn hình danh sách + tìm kiếm + Thêm/Sửa/Xóa. Lớp con cài rows/add/edit/delete."""
    title = ""
    columns = []
    show_add = show_edit = show_delete = True
    extra = []  # [(nhãn nút, tên phương thức nhận id)]

    def __init__(self, master, user=None):
        super().__init__(master)
        self.user = user
        top = ttk.Frame(self)
        top.pack(fill="x", padx=12, pady=(10, 4))
        ttk.Label(top, text=self.title, font=FONT_TITLE).pack(side="left")
        self.kw = tk.StringVar()
        e = ttk.Entry(top, textvariable=self.kw, width=26)
        e.pack(side="right")
        e.bind("<Return>", lambda _e: self.refresh())
        ttk.Button(top, text="🔍 Tìm", command=self.refresh).pack(side="right", padx=4)
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=12, pady=4)
        if self.show_add:
            ttk.Button(bar, text="➕ Thêm", command=self.on_add).pack(side="left", padx=2)
        if self.show_edit:
            ttk.Button(bar, text="✏️ Sửa", command=self.on_edit).pack(side="left", padx=2)
        if self.show_delete:
            ttk.Button(bar, text="🗑 Xóa", command=self.on_delete).pack(side="left", padx=2)
        for text, method in self.extra:
            ttk.Button(bar, text=text, command=lambda m=method: self.on_extra(m)).pack(side="left", padx=2)
        self.table = Table(self, self.columns)
        self.table.pack(fill="both", expand=True, padx=12, pady=8)
        self.refresh()

    def refresh(self):
        self.table.load(self.rows(self.kw.get().strip()))

    def _need_sel(self):
        s = self.table.selected()
        if s is None:
            messagebox.showwarning("Thông báo", "Vui lòng chọn một dòng trong bảng.")
        return s

    def on_add(self):
        self.add()
        self.refresh()

    def on_edit(self):
        s = self._need_sel()
        if s is not None:
            self.edit(s)
            self.refresh()

    def on_delete(self):
        s = self._need_sel()
        if s is not None and messagebox.askyesno("Xác nhận", "Bạn có chắc chắn muốn xóa?"):
            try:
                self.delete(s)
            except sqlite3.IntegrityError:
                error("Không thể xóa vì dữ liệu này đang được sử dụng ở mục khác.")
            self.refresh()

    def on_extra(self, method):
        s = self._need_sel()
        if s is not None:
            getattr(self, method)(s)
            self.refresh()

    # --- lớp con ghi đè ---
    def rows(self, kw): return []
    def add(self): pass
    def edit(self, id_): pass
    def delete(self, id_): pass
