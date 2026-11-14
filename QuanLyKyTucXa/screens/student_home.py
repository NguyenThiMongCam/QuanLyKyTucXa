"""Giao diện sinh viên: thanh menu bên trái + các trang
(Trang chủ, Phòng của tôi, Hợp đồng, Hóa đơn, Dịch vụ & sửa chữa, Thông báo, Nội quy, Hồ sơ cá nhân).
Sinh viên tự cập nhật họ tên / SĐT / quê quán, đổi mật khẩu và gửi yêu cầu cho Ban quản lý."""
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import database as db
from screens.base import Table, error, form_dialog, money, parse_date, valid_date
from screens.sidebar import Sidebar
from screens.login import BORDER, FONT, MUTED, NAVY, PAGE_BG, PRIMARY, SEL_BG, TEXT, FlatButton, rounded_rect



# ---------------------------------------------------------------------- truy vấn dữ liệu
def get_student(ma):
    d = dict(db.query("SELECT * FROM SinhVien WHERE MaSV=?", (ma,), one=True))
    d.pop("MatKhau", None)
    return d


def get_contract(ma):
    """Hợp đồng đang thuê (kèm thông tin phòng) hoặc None."""
    return db.query("""SELECT h.MaHD, h.NgayBatDau, h.NgayKetThuc, p.MaPhong, p.TenPhong, p.Tang,
                              l.TenLoai, l.SoGiuong, l.GiaThue
                       FROM HopDong h JOIN Phong p ON p.MaPhong=h.MaPhong
                       JOIN LoaiPhong l ON l.MaLoai=p.MaLoai
                       WHERE h.MaSV=? AND h.TrangThai='Đang thuê' ORDER BY h.MaHD DESC""", (ma,), one=True)


def get_contracts(ma):
    return db.query("""SELECT h.MaHD, p.TenPhong, h.NgayBatDau, h.NgayKetThuc, h.TrangThai
                       FROM HopDong h JOIN Phong p ON p.MaPhong=h.MaPhong
                       WHERE h.MaSV=? ORDER BY h.MaHD DESC""", (ma,))


def get_roommates(ma_phong):
    return db.query("""SELECT s.MaSV, s.HoTen, s.Lop, s.SDT FROM HopDong h JOIN SinhVien s ON s.MaSV=h.MaSV
                       WHERE h.MaPhong=? AND h.TrangThai='Đang thuê' ORDER BY s.HoTen""", (ma_phong,))


def get_bills(ma_phong, limit=-1):
    return db.query("SELECT * FROM HoaDon WHERE MaPhong=? ORDER BY Thang DESC LIMIT ?", (ma_phong, limit))


def get_notices(limit=-1):
    return db.query("SELECT * FROM ThongBao ORDER BY MaTB DESC LIMIT ?", (limit,))


def get_requests(ma):
    return db.query("SELECT * FROM YeuCau WHERE MaSV=? ORDER BY MaYC DESC", (ma,))


def initials(name):
    parts = (name or "?").split()
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) > 1 else parts[0][:2].upper()


def days_left(end_text):
    try:
        return (parse_date(end_text) - datetime.now()).days + 1
    except ValueError:
        return None


# ---------------------------------------------------------------------- thành phần giao diện
def card(parent, bg="white", border=BORDER, **kw):
    return tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=border, **kw)


def autowrap(label, container, pad):
    """Tự xuống dòng theo bề rộng khung chứa."""
    container.bind("<Configure>", lambda e: label.config(wraplength=max(100, e.width - pad)), add="+")


def section(parent, title, link_text=None, link_cmd=None, **kw):
    c = card(parent, **kw)
    top = tk.Frame(c, bg="white")
    top.pack(fill="x", padx=16, pady=(14, 6))
    tk.Label(top, text=title, bg="white", fg=NAVY, font=(FONT, 12, "bold")).pack(side="left")
    if link_text:
        lk = tk.Label(top, text=link_text, bg="white", fg=PRIMARY, cursor="hand2", font=(FONT, 9, "bold"))
        lk.pack(side="right")
        lk.bind("<Button-1>", lambda _e: link_cmd())
    return c


class ScrollFrame(tk.Frame):
    """Khung cuộn dọc (cuộn bằng thanh trượt hoặc con lăn chuột)."""

    def __init__(self, master):
        super().__init__(master, bg=PAGE_BG)
        self.canvas = tk.Canvas(self, bg=PAGE_BG, highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=PAGE_BG)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.bind("<Enter>", lambda _e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.bind("<Leave>", lambda _e: self.canvas.unbind_all("<MouseWheel>"))

    def _wheel(self, e):
        try:
            self.canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")
        except tk.TclError:
            pass


class Page(tk.Frame):
    def __init__(self, master, shell):
        super().__init__(master, bg=PAGE_BG)
        self.shell, self.user = shell, shell.user
        scroll = ScrollFrame(self)
        scroll.pack(fill="both", expand=True)
        self.body = tk.Frame(scroll.inner, bg=PAGE_BG)
        self.body.pack(fill="x", padx=28, pady=22)

    def heading(self, title, sub=""):
        tk.Label(self.body, text=title, bg=PAGE_BG, fg=NAVY, font=(FONT, 18, "bold")).pack(anchor="w")
        if sub:
            tk.Label(self.body, text=sub, bg=PAGE_BG, fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=(2, 0))
        tk.Frame(self.body, bg=PAGE_BG, height=12).pack()

    def note(self, text):
        tk.Label(self.body, text=text, bg=PAGE_BG, fg=MUTED, font=(FONT, 11)).pack(anchor="w", pady=8)

    def table(self, parent, columns, rows, max_rows=12):
        t = Table(parent, columns)
        t.pack(fill="x", padx=0, pady=0)
        t.load(rows)
        t.tree.configure(height=max(3, min(len(rows), max_rows)))
        return t


def stat_card(parent, col, title, value, sub, link=None):
    c = card(parent)
    c.grid(row=0, column=col, sticky="nsew", padx=(0, 0 if col == 3 else 12))
    tk.Label(c, text=title, bg="white", fg=MUTED, font=(FONT, 9, "bold")).pack(anchor="w", padx=16, pady=(14, 0))
    tk.Label(c, text=value, bg="white", fg=NAVY, font=(FONT, 19, "bold")).pack(anchor="w", padx=16)
    row = tk.Frame(c, bg="white")
    row.pack(anchor="w", padx=16, pady=(0, 14))
    tk.Label(row, text=sub, bg="white", fg=MUTED, font=(FONT, 9)).pack(side="left")
    if link:
        lk = tk.Label(row, text=" · " + link[0], bg="white", fg=PRIMARY, cursor="hand2", font=(FONT, 9, "bold"))
        lk.pack(side="left")
        lk.bind("<Button-1>", lambda _e: link[1]())


def bill_rows(rows):
    return [{"Thang": r["Thang"], "TienPhong": money(r["TienPhong"]), "TienDien": money(r["TienDien"]),
             "TienNuoc": money(r["TienNuoc"]), "TongTien": money(r["TongTien"]), "DaThu": money(r["DaThu"]),
             "CongNo": money(r["TongTien"] - r["DaThu"]), "TrangThai": r["TrangThai"]} for r in rows]


BILL_COLS = [("Thang", "Tháng", 80), ("TienPhong", "Tiền phòng", 100), ("TienDien", "Tiền điện", 90),
             ("TienNuoc", "Tiền nước", 90), ("TongTien", "Tổng", 100), ("DaThu", "Đã thu", 100),
             ("CongNo", "Còn nợ", 100), ("TrangThai", "Trạng thái", 110)]
HOME_BILL_COLS = [("Thang", "Tháng", 70), ("TienPhong", "Tiền phòng", 90), ("TienDien", "Điện", 80),
                  ("TienNuoc", "Nước", 80), ("TongTien", "Tổng", 90), ("TrangThai", "Trạng thái", 100)]


# ---------------------------------------------------------------------- các trang
class HomePage(Page):
    def __init__(self, master, shell):
        super().__init__(master, shell)
        u = self.user
        hd = get_contract(u["MaSV"])
        self._banner(hd)
        if not hd:
            self.note("Bạn chưa ở ký túc xá. Vui lòng liên hệ Ban quản lý để đăng ký phòng.")
            return
        bills, mates = get_bills(hd["MaPhong"]), get_roommates(hd["MaPhong"])
        self._stats(hd, bills, mates)

        cols = tk.Frame(self.body, bg=PAGE_BG)
        cols.pack(fill="x")
        right = tk.Frame(cols, bg=PAGE_BG)
        right.pack(side="right", anchor="n", padx=(16, 0))
        tk.Frame(right, bg=PAGE_BG, width=300, height=1).pack()
        left = tk.Frame(cols, bg=PAGE_BG)
        left.pack(side="left", fill="both", expand=True, anchor="n")

        # --- cột trái: thông báo + hóa đơn
        nb = section(left, "Thông báo từ Ban quản lý", "Xem tất cả", lambda: self.shell.show("notice"))
        nb.pack(fill="x", pady=(0, 16))
        for i, tb in enumerate(get_notices(3)):
            if i:
                tk.Frame(nb, bg=BORDER, height=1).pack(fill="x", padx=16)
            row = tk.Frame(nb, bg="white")
            row.pack(fill="x", padx=16, pady=8)
            tk.Label(row, text=tb["Ngay"][:5], bg=SEL_BG, fg=NAVY, font=(FONT, 9, "bold"), padx=8,
                     pady=3).pack(side="left", anchor="n")
            col = tk.Frame(row, bg="white")
            col.pack(side="left", fill="x", expand=True, padx=12)
            tk.Label(col, text=tb["TieuDe"], bg="white", fg=TEXT, font=(FONT, 10, "bold"), anchor="w").pack(anchor="w")
            body = tk.Label(col, text=tb["NoiDung"] or "", bg="white", fg=MUTED, font=(FONT, 9), justify="left",
                            anchor="w", wraplength=360)
            body.pack(anchor="w")
            autowrap(body, row, 110)
        if not get_notices(1):
            tk.Label(nb, text="Chưa có thông báo.", bg="white", fg=MUTED, font=(FONT, 10)).pack(padx=16, pady=10)
        tk.Frame(nb, bg="white", height=6).pack()

        bb = section(left, "Hóa đơn gần đây", "Lịch sử thanh toán", lambda: self.shell.show("bill"))
        bb.pack(fill="x")
        inner = tk.Frame(bb, bg="white")
        inner.pack(fill="x", padx=12, pady=(0, 12))
        self.table(inner, HOME_BILL_COLS, bill_rows(bills[:5]), max_rows=5)

        # --- cột phải: thành viên, giờ giấc, liên hệ
        mb = section(right, f"Thành viên phòng {hd['TenPhong']}")
        mb.pack(fill="x", pady=(0, 16))
        for m in mates:
            me = m["MaSV"] == u["MaSV"]
            r = tk.Frame(mb, bg="white")
            r.pack(fill="x", padx=16, pady=5)
            tk.Label(r, text=initials(m["HoTen"]), bg=PRIMARY if me else SEL_BG, fg="white" if me else NAVY,
                     width=4, pady=6, font=(FONT, 10, "bold")).pack(side="left")
            tk.Label(r, text=m["HoTen"] + (" (bạn)" if me else ""), bg="white", fg=TEXT,
                     font=(FONT, 10, "bold" if me else "normal")).pack(side="left", padx=10)
        tk.Frame(mb, bg="white", height=8).pack()

        gb = section(right, "Giờ giấc & nội quy")
        gb.pack(fill="x", pady=(0, 16))
        for label, key in (("Cổng mở cửa", "gio_mo_cong"), ("Cổng đóng cửa", "gio_dong_cong"),
                           ("Giờ yên tĩnh", "gio_yen_tinh")):
            r = tk.Frame(gb, bg="white")
            r.pack(fill="x", padx=16, pady=3)
            tk.Label(r, text=label, bg="white", fg=MUTED, font=(FONT, 10)).pack(side="left")
            tk.Label(r, text=db.get_config(key), bg="white", fg=TEXT, font=(FONT, 10, "bold")).pack(side="right")
        lk = tk.Label(gb, text="Xem nội quy đầy đủ →", bg="white", fg=PRIMARY, cursor="hand2", font=(FONT, 10, "bold"))
        lk.pack(anchor="w", padx=16, pady=(8, 14))
        lk.bind("<Button-1>", lambda _e: self.shell.show("rules"))

        cb = card(right, bg="#EAF2FF", border="#CFE0FB")
        cb.pack(fill="x")
        tk.Label(cb, text="Liên hệ Ban quản lý", bg="#EAF2FF", fg=NAVY, font=(FONT, 12, "bold")).pack(
            anchor="w", padx=16, pady=(14, 6))
        for label, key in (("Điện thoại", "lien_he_dien_thoai"), ("Email", "lien_he_email"),
                           ("Văn phòng", "lien_he_van_phong")):
            tk.Label(cb, text=f"{label}: {db.get_config(key)}", bg="#EAF2FF", fg="#2B3D63", font=(FONT, 10),
                     anchor="w", justify="left", wraplength=270).pack(anchor="w", padx=16, pady=1)
        tk.Frame(cb, bg="#EAF2FF", height=12).pack()

        tk.Label(self.body, text="Dữ liệu trên trang được lấy từ hệ thống ký túc xá.", bg=PAGE_BG, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w", pady=(16, 0))

    def _banner(self, hd):
        u, shell = self.user, self.shell
        ban = tk.Frame(self.body, bg=PRIMARY)
        ban.pack(fill="x")
        inner = tk.Frame(ban, bg=PRIMARY)
        inner.pack(fill="x", padx=26, pady=22)
        row = tk.Frame(inner, bg=PRIMARY)
        row.pack(anchor="w")
        tk.Label(row, text=f"Xin chào, {u['HoTen']}", bg=PRIMARY, fg="white", font=(FONT, 22, "bold")).pack(side="left")
        rename = tk.Label(row, text="✏ Đổi tên", bg="#1E5BC0", fg="white", cursor="hand2", padx=10, pady=3,
                          font=(FONT, 9, "bold"))
        rename.pack(side="left", padx=14)
        rename.bind("<Button-1>", lambda _e: shell.edit_profile())
        state = "Đang ở ký túc xá" if hd else "Chưa ở ký túc xá"
        tk.Label(inner, text=f"MSSV {u['MaSV']} · Lớp {u['Lop'] or '-'} · {state}", bg=PRIMARY, fg="#DCE9FD",
                 font=(FONT, 10)).pack(anchor="w", pady=(4, 14))
        acts = tk.Frame(inner, bg=PRIMARY)
        acts.pack(anchor="w")
        for text, cmd in (("💳  Thanh toán", lambda: shell.show("bill")),
                          ("🔧  Báo sửa chữa", lambda: shell.new_request("Sửa chữa")),
                          ("📅  Đăng ký về muộn", lambda: shell.new_request("Về muộn"))):
            FlatButton(acts, text, cmd, bg="white", hover=SEL_BG, fg=NAVY, font=(FONT, 10, "bold"),
                       padx=14, pady=9).pack(side="left", padx=(0, 10))

    def _stats(self, hd, bills, mates):
        shell = self.shell
        no = sum(b["TongTien"] - b["DaThu"] for b in bills)
        unpaid = [b for b in bills if b["TongTien"] - b["DaThu"] > 0]
        share = round(no / max(len(mates), 1))
        con = days_left(hd["NgayKetThuc"])
        fixing = [r for r in get_requests(self.user["MaSV"]) if r["Loai"] == "Sửa chữa" and r["TrangThai"] != "Đã xong"]
        stats = tk.Frame(self.body, bg=PAGE_BG)
        stats.pack(fill="x", pady=16)
        stats.columnconfigure((0, 1, 2, 3), weight=1, uniform="stat")
        stat_card(stats, 0, "PHÒNG HIỆN TẠI", hd["TenPhong"], f"Tầng {hd['Tang']} · {hd['TenLoai']}")
        stat_card(stats, 1, "HỢP ĐỒNG", hd["NgayKetThuc"],
                  "Đã hết hạn" if (con is not None and con < 0) else (f"Còn {con} ngày" if con is not None else "Hết hạn"),
                  link=("Gia hạn", lambda: shell.new_request("Gia hạn")))
        stat_card(stats, 2, "CẦN THANH TOÁN", money(share) + " đ",
                  f"Phần của bạn · tháng {unpaid[0]['Thang']}" if unpaid else "Không có khoản nợ")
        if fixing:
            txt = fixing[0]["NoiDung"]
            stat_card(stats, 3, "YÊU CẦU SỬA CHỮA", f"{len(fixing)} đang xử lý", txt if len(txt) <= 26 else txt[:25] + "…")
        else:
            stat_card(stats, 3, "YÊU CẦU SỬA CHỮA", "Không có", "Chưa có yêu cầu nào")


class RoomPage(Page):
    def __init__(self, master, shell):
        super().__init__(master, shell)
        self.heading("Phòng của tôi")
        hd = get_contract(self.user["MaSV"])
        if not hd:
            return self.note("Bạn chưa ở ký túc xá.")
        c = card(self.body)
        c.pack(fill="x")
        tk.Label(c, text=f"Phòng {hd['TenPhong']}", bg="white", fg=NAVY, font=(FONT, 16, "bold")).pack(
            anchor="w", padx=18, pady=(14, 0))
        tk.Label(c, text=f"Tầng {hd['Tang']} · {hd['TenLoai']} · {hd['SoGiuong']} giường · "
                         f"{money(hd['GiaThue'])} đ/người/tháng", bg="white", fg=MUTED,
                 font=(FONT, 10)).pack(anchor="w", padx=18, pady=(2, 14))
        tk.Label(self.body, text="Thành viên cùng phòng", bg=PAGE_BG, fg=NAVY,
                 font=(FONT, 12, "bold")).pack(anchor="w", pady=(16, 6))
        self.table(self.body, [("MaSV", "Mã SV", 70), ("HoTen", "Họ và tên", 220), ("Lop", "Lớp", 110),
                               ("SDT", "SĐT", 120)], [dict(r) for r in get_roommates(hd["MaPhong"])])


class ContractPage(Page):
    def __init__(self, master, shell):
        super().__init__(master, shell)
        self.heading("Hợp đồng của tôi", "Lịch sử hợp đồng thuê phòng ký túc xá")
        if get_contract(self.user["MaSV"]):
            FlatButton(self.body, "🔄  Xin gia hạn hợp đồng", lambda: shell.new_request("Gia hạn"),
                       padx=16, pady=9).pack(anchor="w", pady=(0, 12))
        self.table(self.body, [("MaHD", "Mã HĐ", 70), ("TenPhong", "Phòng", 90), ("NgayBatDau", "Bắt đầu", 110),
                               ("NgayKetThuc", "Kết thúc", 110), ("TrangThai", "Trạng thái", 120)],
                   [dict(r) for r in get_contracts(self.user["MaSV"])])


class BillPage(Page):
    def __init__(self, master, shell):
        super().__init__(master, shell)
        self.heading("Hóa đơn", "Hóa đơn được tính theo phòng (tiền phòng, điện, nước)")
        hd = get_contract(self.user["MaSV"])
        if not hd:
            return self.note("Bạn chưa ở ký túc xá nên chưa có hóa đơn.")
        self.table(self.body, BILL_COLS, bill_rows(get_bills(hd["MaPhong"])))


class ServicePage(Page):
    def __init__(self, master, shell):
        super().__init__(master, shell)
        self.heading("Dịch vụ & sửa chữa", "Gửi yêu cầu tới Ban quản lý và theo dõi tiến độ xử lý")
        bar = tk.Frame(self.body, bg=PAGE_BG)
        bar.pack(anchor="w", pady=(0, 12))
        for text, loai, solid in (("🔧  Báo sửa chữa", "Sửa chữa", True), ("📅  Đăng ký về muộn", "Về muộn", False),
                                  ("🔄  Xin gia hạn", "Gia hạn", False)):
            FlatButton(bar, text, lambda l=loai: shell.new_request(l), bg=PRIMARY if solid else "white",
                       hover=NAVY if solid else SEL_BG, fg="white" if solid else NAVY,
                       padx=16, pady=9).pack(side="left", padx=(0, 10))
        rows = [{"MaYC": r["MaYC"], "Loai": r["Loai"], "NoiDung": r["NoiDung"], "NgayGui": r["NgayGui"],
                 "TrangThai": r["TrangThai"]} for r in get_requests(self.user["MaSV"])]
        self.table(self.body, [("MaYC", "Mã", 50), ("Loai", "Loại", 90), ("NoiDung", "Nội dung", 420),
                               ("NgayGui", "Ngày gửi", 100), ("TrangThai", "Trạng thái", 110)], rows)
        if not rows:
            self.note("Bạn chưa gửi yêu cầu nào.")


class NoticePage(Page):
    def __init__(self, master, shell):
        super().__init__(master, shell)
        self.heading("Thông báo", "Thông báo từ Ban quản lý ký túc xá")
        self.table(self.body, [("MaTB", "Mã", 50), ("Ngay", "Ngày", 100), ("TieuDe", "Tiêu đề", 260),
                               ("NoiDung", "Nội dung", 460)], [dict(r) for r in get_notices()])


class RulesPage(Page):
    def __init__(self, master, shell):
        super().__init__(master, shell)
        self.heading("Nội quy ký túc xá", "Sinh viên vui lòng đọc và tuân thủ")
        c = card(self.body)
        c.pack(fill="x")
        rules = [x.strip() for x in db.get_config("noi_quy").split("\n") if x.strip()]
        for i, text in enumerate(rules, 1):
            row = tk.Frame(c, bg="white")
            row.pack(fill="x", padx=20, pady=7)
            tk.Label(row, text=str(i), bg=SEL_BG, fg=NAVY, width=3, pady=3, font=(FONT, 10, "bold")).pack(
                side="left", anchor="n")
            lb = tk.Label(row, text=text, bg="white", fg=TEXT, font=(FONT, 11), justify="left", anchor="w",
                          wraplength=600)
            lb.pack(side="left", padx=12, fill="x", expand=True)
            autowrap(lb, row, 80)
        g = card(self.body)
        g.pack(fill="x", pady=16)
        for label, key in (("Cổng mở cửa", "gio_mo_cong"), ("Cổng đóng cửa", "gio_dong_cong"),
                           ("Giờ yên tĩnh", "gio_yen_tinh")):
            r = tk.Frame(g, bg="white")
            r.pack(fill="x", padx=20, pady=6)
            tk.Label(r, text=label, width=16, anchor="w", bg="white", fg=MUTED, font=(FONT, 10)).pack(side="left")
            tk.Label(r, text=db.get_config(key), bg="white", fg=TEXT, font=(FONT, 11, "bold")).pack(side="left")


class ProfilePage(Page):
    def __init__(self, master, shell):
        super().__init__(master, shell)
        self.heading("Hồ sơ cá nhân", "Bạn có thể tự cập nhật họ tên, số điện thoại và quê quán")
        u = get_student(self.user["MaSV"])
        c = card(self.body)
        c.pack(fill="x")
        for label, key in (("Mã sinh viên", "MaSV"), ("Họ và tên", "HoTen"), ("Ngày sinh", "NgaySinh"),
                           ("Giới tính", "GioiTinh"), ("Lớp", "Lop"), ("Số điện thoại", "SDT"),
                           ("Quê quán", "QueQuan")):
            r = tk.Frame(c, bg="white")
            r.pack(fill="x", padx=20, pady=6)
            tk.Label(r, text=label, width=16, anchor="w", bg="white", fg=MUTED, font=(FONT, 10)).pack(side="left")
            tk.Label(r, text=u.get(key) or "-", anchor="w", bg="white", fg=TEXT, font=(FONT, 11, "bold")).pack(side="left")
        bar = tk.Frame(self.body, bg=PAGE_BG)
        bar.pack(anchor="w", pady=16)
        FlatButton(bar, "✏ Cập nhật thông tin", shell.edit_profile, padx=16, pady=9).pack(side="left", padx=(0, 10))
        FlatButton(bar, "🔒 Đổi mật khẩu", shell.change_password, bg="white", hover=SEL_BG, fg=NAVY,
                   padx=16, pady=9).pack(side="left")


# ---------------------------------------------------------------------- khung chính của sinh viên
class StudentShell(tk.Frame):
    PAGES = [("home", "Trang chủ", HomePage), ("room", "Phòng của tôi", RoomPage),
             ("contract", "Hợp đồng", ContractPage), ("bill", "Hóa đơn", BillPage),
             ("service", "Dịch vụ & sửa chữa", ServicePage), ("notice", "Thông báo", NoticePage),
             ("rules", "Nội quy", RulesPage), ("profile", "Hồ sơ cá nhân", ProfilePage)]
    ICONS = {"home": "home", "room": "room", "contract": "contract", "bill": "bill", "service": "service",
             "notice": "notice", "rules": "rules", "profile": "staff"}

    def __init__(self, master, user, on_logout):
        super().__init__(master, bg=PAGE_BG)
        self.user, self.on_logout = user, on_logout
        self.current = None
        self.side = Sidebar(self, "", [(k, t, self.ICONS[k]) for k, t, _c in self.PAGES], self.show, self.on_logout)
        self.side.pack(side="left", fill="y")

        self.content = tk.Frame(self, bg=PAGE_BG)
        self.content.pack(side="left", fill="both", expand=True)
        self._refresh_who()
        self.show("home")

    def _refresh_who(self):
        self.side.set_subtitle(f"Sinh viên\n{self.user['HoTen']} · MSSV {self.user['MaSV']}")

    def show(self, key):
        self.current = key
        self.side.set_active(key)
        for w in self.content.winfo_children():
            w.destroy()
        cls = next(c for k, _t, c in self.PAGES if k == key)
        cls(self.content, self).pack(fill="both", expand=True)

    # --- cập nhật thông tin cá nhân (họ tên, SĐT, quê quán) ---
    def edit_profile(self):
        cur = get_student(self.user["MaSV"])
        fields = [("HoTen", "Họ và tên", "entry", None), ("SDT", "Số điện thoại", "entry", None),
                  ("QueQuan", "Quê quán", "entry", None)]
        d = form_dialog(self, "Cập nhật thông tin cá nhân", fields, cur)
        if not d:
            return
        if not d["HoTen"]:
            return error("Họ tên không được để trống.")
        if d["SDT"] and not (d["SDT"].isdigit() and 9 <= len(d["SDT"]) <= 11):
            return error("Số điện thoại phải gồm 9-11 chữ số.")
        db.cap_nhat_sinh_vien(self.user["MaSV"], d["HoTen"], d["SDT"], d["QueQuan"])
        self.user.update(get_student(self.user["MaSV"]))
        self._refresh_who()
        self.show(self.current)
        messagebox.showinfo("Thông báo", "Đã cập nhật thông tin cá nhân.")

    def change_password(self):
        fields = [("Cu", "Mật khẩu hiện tại", "password", None), ("Moi", "Mật khẩu mới", "password", None),
                  ("Lai", "Nhập lại mật khẩu mới", "password", None)]
        d = form_dialog(self, "Đổi mật khẩu", fields)
        if not d:
            return
        if len(d["Moi"]) < 6:
            return error("Mật khẩu mới phải có ít nhất 6 ký tự.")
        if d["Moi"] != d["Lai"]:
            return error("Mật khẩu nhập lại không khớp.")
        if not db.doi_mat_khau_sinh_vien(self.user["MaSV"], d["Cu"], d["Moi"]):
            return error("Mật khẩu hiện tại không đúng.")
        messagebox.showinfo("Thông báo", "Đã đổi mật khẩu.")

    # --- gửi yêu cầu tới Ban quản lý: 'Sửa chữa' | 'Về muộn' | 'Gia hạn' ---
    def new_request(self, loai):
        hd = get_contract(self.user["MaSV"])
        if not hd:
            return error("Bạn chưa ở ký túc xá nên chưa gửi được yêu cầu này.")
        today = datetime.now().strftime("%d/%m/%Y")
        if loai == "Sửa chữa":
            d = form_dialog(self, "Báo sửa chữa", [("MoTa", "Mô tả sự cố", "entry", None)])
            if not d:
                return
            if not d["MoTa"]:
                return error("Vui lòng mô tả sự cố cần sửa.")
            text = d["MoTa"]
        elif loai == "Về muộn":
            d = form_dialog(self, "Đăng ký về muộn",
                            [("Ngay", "Ngày (dd/mm/yyyy)", "entry", None), ("Gio", "Giờ về dự kiến (HH:MM)", "entry", None),
                             ("LyDo", "Lý do", "entry", None)], {"Ngay": today, "Gio": "23:30"})
            if not d:
                return
            try:
                datetime.strptime(d["Gio"], "%H:%M")
            except ValueError:
                return error("Giờ phải có dạng HH:MM, ví dụ 23:30.")
            if not valid_date(d["Ngay"]):
                return error("Ngày phải có dạng dd/mm/yyyy.")
            if not d["LyDo"]:
                return error("Vui lòng nhập lý do về muộn.")
            text = f"Về muộn ngày {d['Ngay']} lúc {d['Gio']}. Lý do: {d['LyDo']}"
        else:
            d = form_dialog(self, "Xin gia hạn hợp đồng",
                            [("Ngay", f"Ngày kết thúc mới (hiện {hd['NgayKetThuc']})", "entry", None)])
            if not d:
                return
            if not valid_date(d["Ngay"]) or parse_date(d["Ngay"]) <= parse_date(hd["NgayKetThuc"]):
                return error("Nhập ngày dd/mm/yyyy và phải sau ngày kết thúc hiện tại.")
            text = f"Xin gia hạn hợp đồng đến {d['Ngay']}"
        db.tao_yeu_cau(self.user["MaSV"], loai, text)
        messagebox.showinfo("Đã gửi", "Yêu cầu của bạn đã được gửi đến Ban quản lý.")
        self.show(self.current)