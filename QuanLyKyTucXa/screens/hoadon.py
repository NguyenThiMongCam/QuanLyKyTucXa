from datetime import date
import tkinter as tk
from tkinter import messagebox, ttk
import database as db
from screens.base import money, pick_id


class HoaDonScreen(ttk.Frame):
  title = "Quản lý hóa đơn"

  def __init__(self, master, user=None):
    super().__init__(master)
    self.user = user

    self.colors = {
        "bg": "#f8fafc",
        "white": "#ffffff",
        "text_dark": "#0f172a",
        "text_main": "#1e293b",
        "muted": "#64748b",
        "blue_primary": "#1d4ed8",
        "blue_hover": "#1e40af",
        "blue_light": "#eff6ff",
        "border": "#e2e8f0",
    }

    self.configure(style="Main.TFrame")
    self.setup_styles()
    self.build_ui()
    self.refresh()

  def setup_styles(self):
    style = ttk.Style()
    style.configure("Main.TFrame", background=self.colors["bg"])

    style.configure(
        "Custom.Treeview",
        background=self.colors["white"],
        fieldbackground=self.colors["white"],
        foreground=self.colors["text_main"],
        rowheight=48,
        font=("Segoe UI", 10),
        borderwidth=0,
    )
    style.configure(
        "Custom.Treeview.Heading",
        background="#f8fafc",
        foreground="#475569",
        font=("Segoe UI", 10, "bold"),
        relief="flat",
        padding=8,
    )
    style.map(
        "Custom.Treeview",
        background=[("selected", "#e0e7ff")],
        foreground=[("selected", self.colors["blue_primary"])],
    )

  def build_ui(self):
    # Khung nội dung chính (Đã lược bỏ sidebar trùng lặp để không bị lỗi trắng màn hình)
    content_area = tk.Frame(self, bg=self.colors["bg"])
    content_area.pack(fill="both", expand=True)

    top_bar = tk.Frame(content_area, bg=self.colors["bg"])
    top_bar.pack(fill="x", padx=28, pady=(22, 16))

    title_box = tk.Frame(top_bar, bg=self.colors["bg"])
    title_box.pack(side="left")
    tk.Label(
        title_box,
        text="Quản lý hóa đơn",
        font=("Segoe UI", 22, "bold"),
        fg=self.colors["text_dark"],
        bg=self.colors["bg"],
    ).pack(anchor="w")
    tk.Label(
        title_box,
        text="Theo dõi, quản lý và xuất hóa đơn cho sinh viên",
        font=("Segoe UI", 11),
        fg=self.colors["muted"],
        bg=self.colors["bg"],
    ).pack(anchor="w", pady=(2, 0))

    self.search_var = tk.StringVar()
    search_entry = tk.Entry(
        top_bar,
        textvariable=self.search_var,
        font=("Segoe UI", 10),
        relief="solid",
        bd=1,
        width=30,
        fg=self.colors["muted"],
    )
    search_entry.pack(side="right", ipady=8, padx=(10, 0))
    search_entry.insert(0, "🔍 Tìm theo mã hóa đơn, tên sinh viên...")
    search_entry.bind("<Return>", lambda e: self.refresh())

    self.build_statistics(content_area)
    self.build_filter(content_area)
    self.build_actions(content_area)
    self.build_table(content_area)

  def build_statistics(self, parent):
    stats = tk.Frame(parent, bg=self.colors["bg"])
    stats.pack(fill="x", padx=28, pady=(0, 16))

    self.stat_values = {}
    items = [
        ("total", "Tổng hóa đơn", "125", "#3b82f6", "#eff6ff"),
        ("paid", "Đã thanh toán", "98", "#10b981", "#ecfdf5"),
        ("unpaid", "Chưa thanh toán", "27", "#f59e0b", "#fffbeb"),
        ("revenue", "Tổng doanh thu", "78.500.000đ", "#3b82f6", "#eff6ff"),
    ]

    for key, label, value, color, icon_bg in items:
      card = tk.Frame(
          stats,
          bg=self.colors["white"],
          highlightbackground=self.colors["border"],
          highlightthickness=1,
      )
      card.pack(side="left", fill="both", expand=True, padx=(0, 14))

      icon_lbl = tk.Label(
          card,
          text={
              "total": "📄",
              "paid": "✓",
              "unpaid": "⏱",
              "revenue": "💰",
          }[key],
          font=("Segoe UI", 15),
          bg=icon_bg,
          fg=color,
          width=3,
          height=2,
      )
      icon_lbl.pack(side="left", padx=14, pady=14)

      text_area = tk.Frame(card, bg=self.colors["white"])
      text_area.pack(side="left", fill="both", expand=True, pady=12)

      tk.Label(
          text_area,
          text=label,
          font=("Segoe UI", 10),
          bg=self.colors["white"],
          fg=self.colors["muted"],
      ).pack(anchor="w")

      val_lbl = tk.Label(
          text_area,
          text=value,
          font=("Segoe UI", 18, "bold"),
          bg=self.colors["white"],
          fg=color,
      )
      val_lbl.pack(anchor="w", pady=(2, 0))
      self.stat_values[key] = val_lbl

  def build_filter(self, parent):
    box = tk.Frame(
        parent,
        bg=self.colors["white"],
        highlightbackground=self.colors["border"],
        highlightthickness=1,
    )
    box.pack(fill="x", padx=28, pady=(0, 16))

    tk.Label(
        box,
        text="Thời gian",
        font=("Segoe UI", 10, "bold"),
        bg=self.colors["white"],
        fg=self.colors["text_dark"],
    ).grid(row=0, column=0, padx=16, pady=(14, 4), sticky="w")

    f_time = tk.Frame(box, bg=self.colors["white"])
    f_time.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="w")

    self.from_var = tk.StringVar(value="01/11/2025")
    self.to_var = tk.StringVar(value="30/11/2025")

    ttk.Entry(f_time, textvariable=self.from_var, width=13).pack(side="left")
    tk.Label(
        f_time, text=" → ", bg=self.colors["white"], fg=self.colors["muted"]
    ).pack(side="left")
    ttk.Entry(f_time, textvariable=self.to_var, width=13).pack(side="left")

    tk.Label(
        box,
        text="Trạng thái",
        font=("Segoe UI", 10, "bold"),
        bg=self.colors["white"],
        fg=self.colors["text_dark"],
    ).grid(row=0, column=1, padx=16, pady=(14, 4), sticky="w")

    self.status_var = tk.StringVar(value="Tất cả")
    status_cb = ttk.Combobox(
        box,
        textvariable=self.status_var,
        values=["Tất cả", "Đã thanh toán", "Chưa thanh toán"],
        state="readonly",
        width=18,
    )
    status_cb.grid(row=1, column=1, padx=16, pady=(0, 14), sticky="w")

    tk.Label(
        box,
        text="Loại hóa đơn",
        font=("Segoe UI", 10, "bold"),
        bg=self.colors["white"],
        fg=self.colors["text_dark"],
    ).grid(row=0, column=2, padx=16, pady=(14, 4), sticky="w")

    self.type_var = tk.StringVar(value="Tất cả")
    type_cb = ttk.Combobox(
        box,
        textvariable=self.type_var,
        values=["Tất cả", "Tiền phòng", "Dịch vụ khác"],
        state="readonly",
        width=18,
    )
    type_cb.grid(row=1, column=2, padx=16, pady=(0, 14), sticky="w")

    btn_box = tk.Frame(box, bg=self.colors["white"])
    btn_box.grid(row=1, column=3, padx=16, pady=(0, 14), sticky="w")

    tk.Button(
        btn_box,
        text="🔍 Tìm kiếm",
        font=("Segoe UI", 10, "bold"),
        bg=self.colors["blue_primary"],
        fg="white",
        activebackground=self.colors["blue_hover"],
        activeforeground="white",
        relief="flat",
        padx=12,
        pady=6,
        command=self.refresh,
    ).pack(side="left", padx=(0, 8))

    tk.Button(
        btn_box,
        text="🔄 Làm mới",
        font=("Segoe UI", 10, "bold"),
        bg=self.colors["white"],
        fg="#334155",
        activebackground="#f1f5f9",
        activeforeground="#334155",
        relief="solid",
        bd=1,
        padx=10,
        pady=5,
        command=self.reset_filter,
    ).pack(side="left")

  def build_actions(self, parent):
    bar = tk.Frame(parent, bg=self.colors["bg"])
    bar.pack(fill="x", padx=28, pady=(0, 14))

    left_act = tk.Frame(bar, bg=self.colors["bg"])
    left_act.pack(side="left")

    tk.Button(
        left_act,
        text="＋ Tạo hóa đơn",
        font=("Segoe UI", 10, "bold"),
        bg=self.colors["blue_primary"],
        fg="white",
        activebackground=self.colors["blue_hover"],
        activeforeground="white",
        relief="flat",
        padx=14,
        pady=7,
        command=self.add,
    ).pack(side="left", padx=(0, 8))

    for text_btn in ["📊 Xuất Excel", "📄 Xuất PDF", "🖨️ In hóa đơn"]:
      tk.Button(
          left_act,
          text=text_btn,
          font=("Segoe UI", 10, "bold"),
          bg=self.colors["white"],
          fg="#334155",
          activebackground="#f1f5f9",
          activeforeground="#334155",
          relief="solid",
          bd=1,
          padx=10,
          pady=6,
      ).pack(side="left", padx=4)

    right_act = tk.Frame(bar, bg=self.colors["bg"])
    right_act.pack(side="right")
    tk.Button(
        right_act,
        text="📊 Xem báo cáo",
        font=("Segoe UI", 10, "bold"),
        bg=self.colors["white"],
        fg="#334155",
        activebackground="#f1f5f9",
        activeforeground="#334155",
        relief="solid",
        bd=1,
        padx=10,
        pady=6,
    ).pack(side="right")

  def build_table(self, parent):
    container = tk.Frame(
        parent,
        bg=self.colors["white"],
        highlightbackground=self.colors["border"],
        highlightthickness=1,
    )
    container.pack(fill="both", expand=True, padx=28, pady=(0, 12))

    columns = (
        "Check",
        "MaHDon",
        "TenSinhVien",
        "Phong",
        "LoaiPhi",
        "SoTien",
        "NgayLap",
        "HanThanhToan",
        "TrangThai",
        "ThaoTac",
    )

    self.tree = ttk.Treeview(
        container,
        columns=columns,
        show="headings",
        style="Custom.Treeview",
        selectmode="browse",
    )

    headings = {
        "Check": "",
        "MaHDon": "Mã hóa đơn",
        "TenSinhVien": "Tên sinh viên",
        "Phong": "Phòng",
        "LoaiPhi": "Loại phí",
        "SoTien": "Số tiền",
        "NgayLap": "Ngày lập",
        "HanThanhToan": "Hạn thanh toán",
        "TrangThai": "Trạng thái",
        "ThaoTac": "Thao tác",
    }

    widths = {
        "Check": 40,
        "MaHDon": 105,
        "TenSinhVien": 160,
        "Phong": 90,
        "LoaiPhi": 120,
        "SoTien": 130,
        "NgayLap": 115,
        "HanThanhToan": 125,
        "TrangThai": 140,
        "ThaoTac": 110,
    }

    for col in columns:
      self.tree.heading(col, text=headings[col])
      self.tree.column(
          col,
          width=widths[col],
          anchor="w"
          if col in ["TenSinhVien", "LoaiPhi"]
          else "center",
      )

    scrollbar_y = ttk.Scrollbar(
        container, orient="vertical", command=self.tree.yview
    )
    self.tree.configure(yscrollcommand=scrollbar_y.set)
    self.tree.pack(side="top", fill="both", expand=True)
    scrollbar_y.pack(side="right", fill="y")

    pagination = tk.Frame(parent, bg=self.colors["bg"])
    pagination.pack(fill="x", padx=28, pady=(4, 16))

    tk.Label(
        pagination,
        text="Hiển thị 1 - 5 / 125 hóa đơn",
        font=("Segoe UI", 10),
        fg=self.colors["muted"],
        bg=self.colors["bg"],
    ).pack(side="left")

    pages_box = tk.Frame(pagination, bg=self.colors["bg"])
    pages_box.pack(side="right")

    for p in ["<", "1", "2", "3", "...", "25", ">"]:
      is_active = p == "1"
      tk.Button(
          pages_box,
          text=p,
          font=("Segoe UI", 10, "bold" if is_active else "normal"),
          bg=self.colors["blue_primary"]
          if is_active
          else self.colors["white"],
          fg="white" if is_active else self.colors["text_main"],
          relief="solid",
          bd=1,
          width=3,
          height=1,
      ).pack(side="left", padx=2)

  def reset_filter(self):
    self.search_var.set("")
    self.from_var.set("01/11/2025")
    self.to_var.set("30/11/2025")
    self.status_var.set("Tất cả")
    self.type_var.set("Tất cả")
    self.refresh()

  def rows(self):
    return [
        (
            "☐",
            "HD00125",
            "Nguyễn Thị An",
            "A101",
            "Tiền phòng",
            "2.000.000đ",
            "01/11/2025",
            "10/11/2025",
            "✓ Đã thanh toán",
            "👁 Xem  ...",
        ),
        (
            "☐",
            "HD00124",
            "Trần Văn Bình",
            "B201",
            "Tiền phòng",
            "1.800.000đ",
            "01/11/2025",
            "10/11/2025",
            "✓ Đã thanh toán",
            "👁 Xem  ...",
        ),
        (
            "☐",
            "HD00123",
            "Lê Thị Mai",
            "B102",
            "Dịch vụ khác",
            "150.000đ",
            "29/10/2025",
            "05/11/2025",
            "⏱ Chưa thanh toán",
            "👁 Xem  ...",
        ),
        (
            "☐",
            "HD00122",
            "Phạm Văn Duy",
            "A201",
            "Tiền phòng",
            "2.200.000đ",
            "28/10/2025",
            "07/11/2025",
            "⏱ Chưa thanh toán",
            "👁 Xem  ...",
        ),
        (
            "☐",
            "HD00121",
            "Hoàng Thị Lan",
            "C102",
            "Dịch vụ khác",
            "200.000đ",
            "27/10/2025",
            "05/11/2025",
            "✓ Đã thanh toán",
            "👁 Xem  ...",
        ),
    ]

  def refresh(self):
    self.tree.delete(*self.tree.get_children())
    for r in self.rows():
      self.tree.insert("", "end", values=r)

  def add(self):
    win = tk.Toplevel(self)
    win.title("Lập hóa đơn mới")
    win.geometry("520x650")
    win.configure(bg=self.colors["white"])
    win.resizable(False, False)
    win.transient(self.winfo_toplevel())
    win.grab_set()

    header = tk.Frame(win, bg=self.colors["white"])
    header.pack(fill="x", padx=24, pady=(20, 12))

    tk.Label(
        header,
        text="Lập hóa đơn mới",
        font=("Segoe UI", 16, "bold"),
        fg=self.colors["text_dark"],
        bg=self.colors["white"],
    ).pack(side="left")

    tk.Button(
        header,
        text="✕",
        font=("Segoe UI", 10, "bold"),
        bg="#f1f5f9",
        fg=self.colors["muted"],
        relief="flat",
        width=3,
        command=win.destroy,
    ).pack(side="right")

    body = tk.Frame(win, bg=self.colors["white"])
    body.pack(fill="both", expand=True, padx=24, pady=10)

    tk.Label(
        body,
        text="🏠  Thông tin hóa đơn",
        font=("Segoe UI", 11, "bold"),
        fg=self.colors["blue_primary"],
        bg=self.colors["white"],
        anchor="w",
    ).pack(fill="x", pady=(0, 6))

    f_info = tk.Frame(body, bg=self.colors["white"])
    f_info.pack(fill="x", pady=(0, 12))

    tk.Label(
        f_info, text="Phòng *", font=("Segoe UI", 10), bg=self.colors["white"]
    ).grid(row=0, column=0, sticky="w", pady=(0, 2))
    room_cb = ttk.Combobox(
        f_info, values=["A101 - Phòng 4 người", "A102 - Phòng 4 người"], width=28
    )
    room_cb.grid(row=1, column=0, sticky="w", padx=(0, 16))
    room_cb.current(0)

    tk.Label(
        f_info, text="Tháng hóa đơn *", font=("Segoe UI", 10), bg="white"
    ).grid(row=0, column=1, sticky="w", pady=(0, 2))
    month_en = ttk.Entry(f_info, width=22)
    month_en.insert(0, "11/2025")
    month_en.grid(row=1, column=1, sticky="w")

    tk.Label(
        body,
        text="⚡  Chỉ số sử dụng",
        font=("Segoe UI", 11, "bold"),
        fg=self.colors["blue_primary"],
        bg=self.colors["white"],
        anchor="w",
    ).pack(fill="x", pady=(6, 6))

    f_idx = tk.Frame(body, bg=self.colors["white"])
    f_idx.pack(fill="x", pady=(0, 12))

    tk.Label(
        f_idx, text="Số điện cũ (kWh)", font=("Segoe UI", 9), bg="white"
    ).grid(row=0, column=0, sticky="w")
    old_e = ttk.Entry(f_idx, width=24)
    old_e.insert(0, "100")
    old_e.config(state="disabled")
    old_e.grid(row=1, column=0, sticky="w", pady=(2, 8), padx=(0, 16))

    tk.Label(
        f_idx, text="Số nước cũ (m³)", font=("Segoe UI", 9), bg="white"
    ).grid(row=0, column=1, sticky="w")
    old_w = ttk.Entry(f_idx, width=24)
    old_w.insert(0, "20")
    old_w.config(state="disabled")
    old_w.grid(row=1, column=1, sticky="w", pady=(2, 8))

    tk.Label(
        f_idx, text="Số điện mới (kWh) *", font=("Segoe UI", 9), bg="white"
    ).grid(row=2, column=0, sticky="w")
    new_e = ttk.Entry(f_idx, width=24)
    new_e.insert(0, "150")
    new_e.grid(row=3, column=0, sticky="w", pady=(2, 0), padx=(0, 16))

    tk.Label(
        f_idx, text="Số nước mới (m³) *", font=("Segoe UI", 9), bg="white"
    ).grid(row=2, column=1, sticky="w")
    new_w = ttk.Entry(f_idx, width=24)
    new_w.insert(0, "25")
    new_w.grid(row=3, column=1, sticky="w", pady=(2, 0))

    tk.Label(
        body,
        text="💳  Chi tiết thanh toán",
        font=("Segoe UI", 11, "bold"),
        fg=self.colors["blue_primary"],
        bg=self.colors["white"],
        anchor="w",
    ).pack(fill="x", pady=(8, 6))

    detail_frame = tk.Frame(
        body,
        bg=self.colors["white"],
        highlightbackground=self.colors["border"],
        highlightthickness=1,
    )
    detail_frame.pack(fill="x", pady=(0, 10))

    sub_tree = ttk.Treeview(
        detail_frame, columns=("KhoanThu", "ThanhTien"), show="headings", height=4
    )
    sub_tree.heading("KhoanThu", text="Khoản thu")
    sub_tree.heading("ThanhTien", text="Thành tiền")
    sub_tree.column("KhoanThu", width=260, anchor="w")
    sub_tree.column("ThanhTien", width=180, anchor="e")
    sub_tree.pack(fill="x", padx=4, pady=4)

    sub_rows = [
        ("🏠 Tiền phòng", "600.000đ"),
        ("⚡ Tiền điện (50 kWh × 3.000đ)", "150.000đ"),
        ("💧 Tiền nước (5 m³ × 10.000đ)", "50.000đ"),
        ("🛍️ Dịch vụ khác", "0đ"),
    ]
    for r in sub_rows:
      sub_tree.insert("", "end", values=r)

    tot_box = tk.Frame(body, bg=self.colors["white"])
    tot_box.pack(fill="x", pady=(4, 10))
    tk.Label(
        tot_box,
        text="Tổng tiền",
        font=("Segoe UI", 11, "bold"),
        bg="white",
        fg=self.colors["text_dark"],
    ).pack(side="left")
    tk.Label(
        tot_box,
        text="800.000đ",
        font=("Segoe UI", 13, "bold"),
        bg="white",
        fg=self.colors["blue_primary"],
    ).pack(side="right")

    footer = tk.Frame(win, bg=self.colors["white"])
    footer.pack(fill="x", padx=24, pady=(0, 20))

    tk.Button(
        footer,
        text="Hủy",
        font=("Segoe UI", 10, "bold"),
        bg=self.colors["white"],
        fg="#334155",
        activebackground="#f1f5f9",
        relief="solid",
        bd=1,
        padx=12,
        pady=6,
        command=win.destroy,
    ).pack(side="right", padx=(8, 0))

    tk.Button(
        footer,
        text="💾 Lưu hóa đơn",
        font=("Segoe UI", 10, "bold"),
        bg=self.colors["blue_primary"],
        fg="white",
        activebackground=self.colors["blue_hover"],
        activeforeground="white",
        relief="flat",
        padx=14,
        pady=6,
        command=lambda: [
            messagebox.showinfo("Thành công", "Đã lưu hóa đơn thành công!"),
            win.destroy(),
        ],
    ).pack(side="right")