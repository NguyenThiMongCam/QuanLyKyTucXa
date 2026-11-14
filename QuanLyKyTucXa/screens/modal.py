"""Hộp thoại nhập liệu kiểu "modal" theo mẫu thiết kế (Thêm / Sửa sinh viên, Thêm / Sửa phòng).

Cách dùng:
    fields = [{"key": "TenPhong", "label": "Tên phòng", "ph": "Ví dụ: A301", "required": True},
              {"key": "Tang", "label": "Tầng", "ph": "1", "required": True},
              {"key": "TrangThai", "label": "Trạng thái", "kind": "combo", "opts": ["Hoạt động", "Bảo trì"]}]
    data = form_modal(self, "Thêm phòng", fields, values={...}, validate=ham_kiem_tra, width=520)
    # data = dict giá trị (đã qua validate) hoặc None nếu người dùng bấm Hủy / ×

Mỗi trường (dict):
    key       khóa trong dict kết quả                       label     nhãn hiển thị
    kind      "entry" (mặc định) | "combo"                  opts      danh sách chọn (cho combo)
    ph        chữ gợi ý (placeholder)                       required  True -> thêm dấu * sau nhãn
    span      1 (nửa dòng, mặc định) | 2 (cả dòng)          readonly  True -> hiện nhưng không cho sửa

validate(values) -> (data, loi):
    values : dict chuỗi người dùng đã nhập
    data   : dict kết quả sạch (hoặc None nếu có lỗi)
    loi    : None | "thông báo" | ("khóa_trường", "thông báo")
    Có lỗi thì hộp thoại KHÔNG đóng, hiện thông báo màu đỏ và đưa con trỏ về đúng ô cần sửa,
    nên nội dung đã gõ không bị mất.
"""
import tkinter as tk
from tkinter import ttk

from screens.login import ERROR, FONT, INPUT_BORDER, NAVY, TEXT, FlatButton, Field

DIVIDER = "#E9EEF8"
READONLY_BG = "#F1F4FA"
PAD_X = 28


class FormModal(tk.Toplevel):
    def __init__(self, parent, title, fields, values=None, validate=None, width=700, submit_text="Lưu"):
        super().__init__(parent)
        self.title(title)
        self.configure(bg="white")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.fields, self.validate, self.min_width = fields, validate, width
        self.widgets, self.result = {}, None
        values = values or {}

        self._build_header(title)
        self._build_body(values)
        self._build_footer(submit_text)

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _e: self._cancel())
        self.bind("<Return>", self._on_return)

    # ---------------------------------------------------------------- dựng giao diện
    def _build_header(self, title):
        head = tk.Frame(self, bg="white")
        head.pack(fill="x", padx=PAD_X, pady=(22, 18))
        tk.Label(head, text=title, bg="white", fg=NAVY, font=(FONT, 15, "bold")).pack(side="left")
        box = tk.Frame(head, bg=INPUT_BORDER, padx=1, pady=1)          # nút × có viền bo vuông
        box.pack(side="right")
        FlatButton(box, "×", self._cancel, bg="white", hover="#EEF4FF", fg=NAVY, font=(FONT, 16),
                   padx=14, pady=3).pack()
        tk.Frame(self, bg=DIVIDER, height=1).pack(fill="x")

    def _build_body(self, values):
        body = tk.Frame(self, bg="white")
        body.pack(fill="x", padx=PAD_X, pady=(18, 4))
        body.columnconfigure(0, weight=1, uniform="col")
        body.columnconfigure(1, weight=1, uniform="col")

        row = col = 0
        for f in self.fields:
            span = 2 if f.get("span") == 2 else 1
            if span == 2 and col == 1:                                  # trường cả dòng luôn bắt đầu dòng mới
                row, col = row + 1, 0
            cell = tk.Frame(body, bg="white")
            cell.grid(row=row, column=col, columnspan=span, sticky="ew", pady=(0, 14),
                      padx=(0, 12) if (span == 1 and col == 0) else ((12, 0) if span == 1 else 0))
            label = f["label"] + (" *" if f.get("required") else "")
            tk.Label(cell, text=label, bg="white", fg=TEXT, font=(FONT, 10, "bold"), anchor="w").pack(fill="x",
                                                                                                    pady=(0, 6))
            self.widgets[f["key"]] = self._make_input(cell, f, values.get(f["key"]))
            if span == 2 or col == 1:
                row, col = row + 1, 0
            else:
                col = 1

        self.msg = tk.Label(body, text="", bg="white", fg=ERROR, font=(FONT, 10), anchor="w", justify="left",
                            wraplength=self.min_width - 2 * PAD_X)
        self.msg.grid(row=row + 1, column=0, columnspan=2, sticky="ew")

    def _make_input(self, cell, f, value):
        value = "" if value is None else str(value)
        if f.get("kind") == "combo":
            opts = list(f.get("opts") or [])
            w = ttk.Combobox(cell, values=opts, state="readonly", font=(FONT, 11))
            w.set(value if value in opts else (opts[0] if opts else ""))
            w.pack(fill="x", ipady=7)
            w.bind("<<ComboboxSelected>>", lambda _e, w=w: w.selection_clear())
            if f.get("readonly"):
                w.config(state="disabled")
            return w
        w = Field(cell, placeholder=f.get("ph", ""))
        w.pack(fill="x")
        if value:
            w.set(value)
        if f.get("readonly"):                                           # đặt giá trị TRƯỚC rồi mới khóa ô
            w.entry.config(state="readonly", readonlybackground=READONLY_BG, fg="#5A6785")
            w.config(highlightbackground=DIVIDER)
        return w

    def _build_footer(self, submit_text):
        tk.Frame(self, bg=DIVIDER, height=1).pack(fill="x", pady=(8, 0))
        bar = tk.Frame(self, bg="white")
        bar.pack(fill="x", padx=PAD_X, pady=16)
        FlatButton(bar, submit_text, self._submit, padx=26, pady=9).pack(side="right")
        box = tk.Frame(bar, bg=INPUT_BORDER, padx=1, pady=1)
        box.pack(side="right", padx=(0, 12))
        FlatButton(box, "Hủy", self._cancel, bg="white", hover="#EEF4FF", fg=NAVY, padx=22, pady=8).pack()

    # ---------------------------------------------------------------- xử lý
    @staticmethod
    def _value(w):
        return w.get().strip()

    def _focus(self, key):
        w = self.widgets.get(key)
        if w is None:
            return
        try:
            (w.entry if isinstance(w, Field) else w).focus_set()
        except tk.TclError:
            pass

    def _on_return(self, _e=None):
        """Enter = Lưu, trừ khi con trỏ đang đứng trên một nút (khi đó Enter bấm đúng nút đó, vd. Hủy)."""
        try:
            w = self.focus_get()
        except (KeyError, tk.TclError):                                 # tkinter lỗi khi focus nằm ở popdown của combobox
            w = None
        if isinstance(w, FlatButton):
            w._click()
        else:
            self._submit()

    def _submit(self):
        values = {k: self._value(w) for k, w in self.widgets.items()}
        data, err = (values, None) if self.validate is None else self.validate(values)
        if err:
            key, text = err if isinstance(err, tuple) else (None, err)
            self.msg.config(text=text)
            self._focus(key)
            return
        self.result = data
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

    # ---------------------------------------------------------------- hiển thị
    def _center(self):
        self.update_idletasks()
        w, h = max(self.winfo_reqwidth(), self.min_width), self.winfo_reqheight()
        top = self.master.winfo_toplevel()
        x = top.winfo_rootx() + (top.winfo_width() - w) // 2
        y = top.winfo_rooty() + (top.winfo_height() - h) // 2
        x = max(0, min(x, self.winfo_screenwidth() - w))
        y = max(0, min(y, self.winfo_screenheight() - h - 60))
        self.geometry(f"{w}x{h}+{x}+{y}")

    def show(self):
        """Hiện hộp thoại, chờ người dùng đóng, trả về dict kết quả hoặc None."""
        self._center()
        try:                                                            # grab_set cần cửa sổ đã hiện (Linux/macOS)
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        first = next((f["key"] for f in self.fields if not f.get("readonly")), None)
        self._focus(first)
        self.wait_window()
        return self.result


def form_modal(parent, title, fields, values=None, validate=None, width=700, submit_text="Lưu"):
    return FormModal(parent, title, fields, values, validate, width, submit_text).show()

