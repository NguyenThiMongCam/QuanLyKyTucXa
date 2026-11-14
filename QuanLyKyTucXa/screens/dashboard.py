"""Trang chủ quản trị - giao diện xanh trắng.

Gồm: lời chào + ô tìm kiếm chung, nút thao tác nhanh, 6 thẻ thống kê, biểu đồ doanh thu 6 tháng,
tình trạng phòng, "Cần xử lý hôm nay" (hợp đồng, công nợ, hóa đơn, yêu cầu của sinh viên) và
"Hoạt động gần đây". Mọi nút đều chuyển sang đúng trang chức năng (qua App.goto trong main.py).
"""
import csv
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox, ttk

import database as db
from screens.base import error, money, parse_date
from screens.login import BORDER, FONT, MUTED, NAVY, PAGE_BG, PRIMARY, SEL_BG, TEXT, FlatButton, rounded_rect
from screens.student_home import ScrollFrame, card

WEEKDAYS = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
SOON_DAYS = 7                                    # "sắp hết hạn" trên trang chủ = trong 7 ngày
PLACEHOLDER = "Tìm sinh viên, phòng, hóa đơn..."
TAGS = {"Hợp đồng": ("#FFF1D6", "#9A6700"), "Công nợ": ("#FDE8E8", "#B42318"), "Hóa đơn": ("#E3EEFF", "#1558C0"),
        "Sửa chữa": ("#DDF5E6", "#0E7A3B"), "Gia hạn": ("#EEE8FF", "#5B3FC4")}
DOTS = {"thu": "#1558C0", "phong": "#22A06B", "hoadon": "#E58A12", "sv": "#7FA6E8", "yeucau": "#C0392B"}
ROOM_COLORS = [("Đầy", "Đã đầy", "#1558C0"), ("Còn chỗ", "Còn chỗ", "#2FA866"),
               ("Trống", "Trống", "#7FA6E8"), ("Bảo trì", "Bảo trì", "#8A97B0")]


# ---------------------------------------------------------------------- truy vấn dữ liệu
def scalar(sql, params=()):
    return db.query(sql, params, one=True)[0] or 0


def last_months(n=6, today=None):
    t = today or date.today()
    y, m, out = t.year, t.month, []
    for _ in range(n):
        out.append((y, m))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return out[::-1]


def revenue_series(n=6, today=None):
    """[(nhãn 'T11', số tiền đã thu của các hóa đơn tháng đó)] cho n tháng gần nhất."""
    return [(f"T{m}", scalar("SELECT SUM(DaThu) FROM HoaDon WHERE Thang=?", (f"{y}-{m:02d}",)))
            for y, m in last_months(n, today)]


def room_summary():
    phongs = db.danh_sach_phong()
    counts = {k: sum(1 for p in phongs if p["TinhTrang"] == k) for k, _l, _c in ROOM_COLORS}
    return {"counts": counts, "rooms": len(phongs), "cho": sum(p["SoGiuong"] for p in phongs),
            "dango": sum(p["DangO"] for p in phongs), "phongs": phongs}


def pending_requests(loais=("Sửa chữa", "Về muộn")):
    q = ",".join("?" * len(loais))
    return db.query(f"""
        SELECT y.MaYC, y.Loai, y.NoiDung, y.NgayGui, s.HoTen,
               (SELECT p.TenPhong FROM HopDong h JOIN Phong p ON p.MaPhong=h.MaPhong
                WHERE h.MaSV=y.MaSV AND h.TrangThai='Đang thuê' LIMIT 1) AS TenPhong
        FROM YeuCau y JOIN SinhVien s ON s.MaSV=y.MaSV
        WHERE y.TrangThai='Chờ xử lý' AND y.Loai IN ({q}) ORDER BY y.MaYC""", tuple(loais))


def todo_items(today=None):
    """Danh sách việc cần xử lý: [{tag, text, btn, go:(trang, tham số...)}]. text dùng **...** để in đậm."""
    today = today or date.today()
    out = []
    soon = over = 0
    for r in db.query("SELECT NgayKetThuc FROM HopDong WHERE TrangThai='Đang thuê'"):
        left = (parse_date(r["NgayKetThuc"]).date() - today).days
        if left < 0:
            over += 1
        elif left <= SOON_DAYS:
            soon += 1
    if soon:
        out.append({"tag": "Hợp đồng", "text": f"**{soon} hợp đồng** sắp hết hạn trong {SOON_DAYS} ngày", "btn": "Xem",
                    "go": ("hopdong", {"flt": "Sắp hết hạn"})})
    if over:
        out.append({"tag": "Hợp đồng", "text": f"**{over} hợp đồng** đã quá hạn, cần gia hạn hoặc kết thúc", "btn": "Xem",
                    "go": ("hopdong", {"flt": "Quá hạn"})})
    debts = db.query("""SELECT p.TenPhong, h.Thang, h.TongTien-h.DaThu AS No FROM HoaDon h JOIN Phong p ON p.MaPhong=h.MaPhong
                        WHERE h.TongTien>h.DaThu ORDER BY No DESC""")
    if len(debts) == 1:
        d = debts[0]
        out.append({"tag": "Công nợ", "text": f"**Phòng {d['TenPhong']}** còn nợ {money(d['No'])} đ (tháng {int(d['Thang'][5:])})",
                    "btn": "Thu tiền", "go": ("hoadon", {"keyword": d["TenPhong"]})})
    elif debts:
        out.append({"tag": "Công nợ", "text": f"**{len(debts)} hóa đơn** còn nợ, tổng {money(sum(d['No'] for d in debts))} đ",
                    "btn": "Thu tiền", "go": ("hoadon", {})})
    thang = today.strftime("%Y-%m")
    chua = scalar("""SELECT COUNT(*) FROM Phong p WHERE p.TrangThai!='Bảo trì'
                     AND EXISTS(SELECT 1 FROM HopDong h WHERE h.MaPhong=p.MaPhong AND h.TrangThai='Đang thuê')
                     AND NOT EXISTS(SELECT 1 FROM HoaDon d WHERE d.MaPhong=p.MaPhong AND d.Thang=?)""", (thang,))
    if chua:
        out.append({"tag": "Hóa đơn", "text": f"**{chua} phòng** chưa lập hóa đơn tháng {today.month}", "btn": "Lập hóa đơn",
                    "go": ("hoadon", {"action": "on_add"})})
    reqs = pending_requests()
    if reqs:
        rooms = sorted({r["TenPhong"] for r in reqs if r["TenPhong"]})
        src = f"từ phòng {rooms[0]}" if len(rooms) == 1 else f"từ {len(reqs)} sinh viên"
        out.append({"tag": "Sửa chữa", "text": f"**{len(reqs)} yêu cầu mới** {src}", "btn": "Xử lý", "go": ("requests", {})})
    gh = db.query("SELECT COUNT(*) FROM YeuCau WHERE Loai='Gia hạn' AND TrangThai='Chờ xử lý'", one=True)[0]
    if gh:
        out.append({"tag": "Gia hạn", "text": f"**{gh} yêu cầu gia hạn** đang chờ duyệt", "btn": "Duyệt",
                    "go": ("hopdong", {"action": "on_requests"})})
    return out


def recent_activity(limit=4):
    return db.query("SELECT * FROM NhatKy ORDER BY MaNK DESC LIMIT ?", (limit,))


def time_label(ts, now=None):
    now = now or datetime.now()
    try:
        t = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return ""
    if t.date() == now.date():
        return t.strftime("%H:%M")
    if t.date() == now.date() - timedelta(days=1):
        return "Hôm qua"
    return t.strftime("%d/%m")


def search_all(text):
    like = f"%{text}%"
    res = []
    for s in db.query("SELECT MaSV,HoTen,Lop FROM SinhVien WHERE CAST(MaSV AS TEXT) LIKE ? OR HoTen LIKE ? OR Lop LIKE ? "
                      "ORDER BY MaSV LIMIT 6", (like,) * 3):
        res.append(("Sinh viên", f"{s['HoTen']} · MSSV {s['MaSV']}" + (f" · {s['Lop']}" if s["Lop"] else ""),
                    ("sinhvien", {"keyword": s["HoTen"]})))
    for p in db.query("SELECT TenPhong FROM Phong WHERE TenPhong LIKE ? ORDER BY TenPhong LIMIT 4", (like,)):
        res.append(("Phòng", f"Phòng {p['TenPhong']}", ("phong", {"keyword": p["TenPhong"]})))
    for h in db.query("SELECT p.TenPhong, h.Thang FROM HoaDon h JOIN Phong p ON p.MaPhong=h.MaPhong "
                      "WHERE p.TenPhong LIKE ? OR h.Thang LIKE ? ORDER BY h.Thang DESC LIMIT 4", (like,) * 2):
        res.append(("Hóa đơn", f"Hóa đơn phòng {h['TenPhong']} · {h['Thang']}", ("hoadon", {"keyword": h["TenPhong"]})))
    return res


# ---------------------------------------------------------------------- thành phần giao diện
def rich(parent, text, bg="white", size=10, fg=TEXT):
    """Nhãn có đoạn in đậm: các phần nằm giữa **...** được in đậm."""
    f = tk.Frame(parent, bg=bg)
    for i, part in enumerate(text.split("**")):
        if part:
            tk.Label(f, text=part, bg=bg, fg=NAVY if i % 2 else fg,
                     font=(FONT, size, "bold" if i % 2 else "normal")).pack(side="left")
    return f


def outline_btn(parent, text, cmd, **kw):
    return FlatButton(parent, text, cmd, bg="white", hover=SEL_BG, fg=NAVY, font=(FONT, 10, "bold"), padx=14, pady=8,
                      highlightthickness=1, highlightbackground=BORDER, **kw)


def draw_chart(cv, data, height):
    cv.delete("all")
    w = cv.winfo_width()
    if not isinstance(w, int) or w < 60:
        return
    top, bottom, left = 30, 26, 8
    base = height - bottom
    mx = max(v for _l, v in data) if data else 0
    if mx <= 0:
        cv.create_text(w / 2, height / 2, text="Chưa có dữ liệu thu tiền", fill=MUTED, font=(FONT, 10))
        return
    for g in (1 / 3, 2 / 3, 1):
        y = base - (base - top) * g
        cv.create_line(left, y, w - left, y, fill="#E6EDF8")
    cv.create_line(left, base, w - left, base, fill="#D5DFF0")
    slot = (w - 2 * left) / len(data)
    bw = min(62, slot * 0.58)
    for i, (lab, v) in enumerate(data):
        cx = left + slot * (i + 0.5)
        bh = max((base - top) * v / mx, 3 if v else 0)
        color = PRIMARY if i == len(data) - 1 else "#9DB8E8"
        if bh > 14:
            rounded_rect(cv, cx - bw / 2, base - bh, cx + bw / 2, base, 7, fill=color, outline=color)
        elif bh:
            cv.create_rectangle(cx - bw / 2, base - bh, cx + bw / 2, base, fill=color, outline=color)
        cv.create_text(cx, base - bh - 11, text=f"{v / 1e6:.1f}".replace(".", ","), fill=NAVY, font=(FONT, 9, "bold"))
        cv.create_text(cx, base + 14, text=lab, fill=MUTED, font=(FONT, 9))


# ---------------------------------------------------------------------- màn hình
class DashboardScreen(tk.Frame):
    CHART_H = 220

    def __init__(self, master, user=None):
        super().__init__(master, bg=PAGE_BG)
        self.user = user or {}
        self.app = master.winfo_toplevel()
        sc = ScrollFrame(self)
        sc.pack(fill="both", expand=True)
        self.body = tk.Frame(sc.inner, bg=PAGE_BG)
        self.body.pack(fill="x", padx=26, pady=20)
        self.render()

    def refresh(self):
        for w in self.body.winfo_children():
            w.destroy()
        self.render()

    def go(self, target):
        page, kw = target
        if page == "requests":
            return self.requests_dialog()
        if hasattr(self.app, "goto"):
            self.app.goto(page, **kw)

    # ---- dựng giao diện
    def render(self):
        b, today = self.body, date.today()
        head = tk.Frame(b, bg=PAGE_BG)
        head.pack(fill="x")
        left = tk.Frame(head, bg=PAGE_BG)
        left.pack(side="left")
        tk.Label(left, text="Trang chủ", bg=PAGE_BG, fg=NAVY, font=(FONT, 20, "bold")).pack(anchor="w")
        tk.Label(left, text=f"Xin chào, {self.user.get('HoTen', '')} · Tổng quan hoạt động ký túc xá · "
                            f"{WEEKDAYS[today.weekday()]}, {today:%d/%m/%Y}", bg=PAGE_BG, fg=MUTED,
                 font=(FONT, 10)).pack(anchor="w")
        sb = tk.Frame(head, bg="white", highlightthickness=1, highlightbackground=BORDER)
        sb.pack(side="right", anchor="n")
        tk.Label(sb, text="🔍", bg="white", fg=MUTED).pack(side="left", padx=(10, 0))
        self.q = tk.StringVar()
        self.entry = tk.Entry(sb, textvariable=self.q, relief="flat", bd=0, width=30, font=(FONT, 10), bg="white", fg=MUTED)
        self.entry.pack(side="left", padx=6, pady=9)
        self.entry.insert(0, PLACEHOLDER)
        self.entry.bind("<FocusIn>", self._focus_in)
        self.entry.bind("<FocusOut>", self._focus_out)
        self.entry.bind("<Return>", lambda _e: self.search())

        bar = tk.Frame(b, bg=PAGE_BG)
        bar.pack(fill="x", pady=(14, 14))
        FlatButton(bar, "＋  Đăng ký phòng", lambda: self.go(("hopdong", {"action": "on_add"})), padx=16,
                   pady=9).pack(side="left", padx=(0, 8))
        for text, tgt in (("🧾  Lập hóa đơn", ("hoadon", {"action": "on_add"})), ("💵  Thu tiền", ("hoadon", {})),
                          ("👤  Thêm sinh viên", ("sinhvien", {"action": "on_add"}))):
            outline_btn(bar, text, lambda t=tgt: self.go(t)).pack(side="left", padx=4)
        outline_btn(bar, "📥  Xuất báo cáo", self.export_report).pack(side="right")

        self.stats()
        row2 = tk.Frame(b, bg=PAGE_BG)
        row2.pack(fill="x", pady=(14, 0))
        row2.columnconfigure(0, weight=3, uniform="r2")
        row2.columnconfigure(1, weight=2, uniform="r2")
        self.revenue_card(row2).grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.room_card(row2).grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        row3 = tk.Frame(b, bg=PAGE_BG)
        row3.pack(fill="x", pady=(14, 0))
        row3.columnconfigure(0, weight=3, uniform="r3")
        row3.columnconfigure(1, weight=2, uniform="r3")
        self.todo_card(row3).grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        self.activity_card(row3).grid(row=0, column=1, sticky="nsew", padx=(7, 0))

    def stats(self):
        thang = date.today().strftime("%Y-%m")
        rs = room_summary()
        items = [("🎓", "#E3EEFF", "Tổng sinh viên", scalar("SELECT COUNT(*) FROM SinhVien"), NAVY),
                 ("🏠", "#DDF3F5", "Đang ở KTX", scalar("SELECT COUNT(DISTINCT MaSV) FROM HopDong WHERE TrangThai='Đang thuê'"), NAVY),
                 ("🛏", "#EDE8FF", "Tổng số phòng", rs["rooms"], NAVY),
                 ("✔", "#DDF5E6", "Phòng còn chỗ", rs["counts"]["Còn chỗ"] + rs["counts"]["Trống"], NAVY),
                 ("＄", "#FFF0E0", f"Doanh thu tháng {date.today().month}",
                  money(scalar("SELECT SUM(DaThu) FROM HoaDon WHERE Thang=?", (thang,))) + " đ", NAVY),
                 ("❗", "#FDE8E8", "Tổng công nợ", money(scalar("SELECT SUM(TongTien-DaThu) FROM HoaDon")) + " đ", "#B42318")]
        grid = tk.Frame(self.body, bg=PAGE_BG)
        grid.pack(fill="x")
        for i, (ico, tint, name, val, color) in enumerate(items):
            grid.columnconfigure(i, weight=1, uniform="st")
            c = card(grid)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0 if i == len(items) - 1 else 6))
            t = tk.Canvas(c, width=36, height=36, bg="white", highlightthickness=0)
            rounded_rect(t, 1, 1, 35, 35, 9, fill=tint, outline=tint)
            t.create_text(18, 18, text=ico, font=(FONT, 12), fill=NAVY)
            t.pack(anchor="w", padx=14, pady=(14, 4))
            tk.Label(c, text=name, bg="white", fg=MUTED, font=(FONT, 9)).pack(anchor="w", padx=14)
            tk.Label(c, text=str(val), bg="white", fg=color, font=(FONT, 15, "bold"), wraplength=130,
                     justify="left").pack(anchor="w", padx=14, pady=(0, 14))

    def _section(self, parent, title, sub=None, badge=None, badge_style=("#E3EEFF", NAVY)):
        c = card(parent)
        top = tk.Frame(c, bg="white")
        top.pack(fill="x", padx=18, pady=(16, 6))
        box = tk.Frame(top, bg="white")
        box.pack(side="left")
        tk.Label(box, text=title, bg="white", fg=NAVY, font=(FONT, 13, "bold")).pack(anchor="w")
        if sub:
            tk.Label(box, text=sub, bg="white", fg=MUTED, font=(FONT, 9)).pack(anchor="w")
        if badge:
            tk.Label(top, text=f"  {badge}  ", bg=badge_style[0], fg=badge_style[1], font=(FONT, 9, "bold")).pack(side="right")
        return c

    def revenue_card(self, parent):
        data = revenue_series()
        months = last_months()
        c = self._section(parent, "Doanh thu 6 tháng gần nhất", "Số tiền đã thu, đơn vị: triệu đồng",
                          f"T{months[0][1]} – T{months[-1][1]}/{months[-1][0]}")
        cv = tk.Canvas(c, height=self.CHART_H, bg="white", highlightthickness=0)
        cv.pack(fill="x", padx=14, pady=(0, 12))
        cv.bind("<Configure>", lambda _e: draw_chart(cv, data, self.CHART_H))
        return c

    def room_card(self, parent):
        rs = room_summary()
        c = self._section(parent, "Tình trạng phòng", f"{rs['rooms']} phòng · {rs['cho']} chỗ")
        for key, label, color in ROOM_COLORS:
            n = rs["counts"][key]
            line = tk.Frame(c, bg="white")
            line.pack(fill="x", padx=18, pady=(8, 0))
            tk.Label(line, text=label, bg="white", fg=TEXT, font=(FONT, 10, "bold")).pack(side="left")
            tk.Label(line, text=str(n), bg="white", fg=TEXT, font=(FONT, 10)).pack(side="right")
            bar = tk.Canvas(c, height=8, bg="#E8EFFA", highlightthickness=0)
            bar.pack(fill="x", padx=18, pady=(3, 0))
            ratio = n / rs["rooms"] if rs["rooms"] else 0
            bar.bind("<Configure>", lambda e, bar=bar, ratio=ratio, color=color: (
                bar.delete("all"), bar.create_rectangle(0, 0, int(e.width * ratio), 8, fill=color, outline="")))
        pct = round(rs["dango"] * 100 / rs["cho"]) if rs["cho"] else 0
        tk.Frame(c, bg=BORDER, height=1).pack(fill="x", padx=18, pady=(14, 8))
        rich(c, f"Tỷ lệ lấp đầy: **{rs['dango']} / {rs['cho']} chỗ ({pct}%)**", size=9, fg=MUTED).pack(
            anchor="w", padx=18, pady=(0, 14))
        return c

    def todo_card(self, parent):
        items = todo_items()
        c = self._section(parent, "Cần xử lý hôm nay", badge=f"{len(items)} việc" if items else None,
                          badge_style=("#FDE8E8", "#B42318"))
        if not items:
            tk.Label(c, text="🎉  Hôm nay không có việc nào cần xử lý.", bg="white", fg=MUTED, font=(FONT, 10)).pack(
                anchor="w", padx=18, pady=(6, 20))
        for i, it in enumerate(items):
            if i:
                tk.Frame(c, bg="#EEF2F8", height=1).pack(fill="x", padx=18)
            row = tk.Frame(c, bg="white")
            row.pack(fill="x", padx=18, pady=9)
            bg, fg = TAGS[it["tag"]]
            tk.Label(row, text=f" {it['tag']} ", bg=bg, fg=fg, font=(FONT, 9, "bold"), width=9).pack(side="left", padx=(0, 10))
            rich(row, it["text"]).pack(side="left")
            outline_btn(row, it["btn"], lambda t=it["go"]: self.go(t)).pack(side="right")
        tk.Frame(c, bg="white", height=8).pack()
        return c

    def activity_card(self, parent):
        c = self._section(parent, "Hoạt động gần đây")
        acts = recent_activity()
        if not acts:
            tk.Label(c, text="Chưa có hoạt động nào được ghi lại.", bg="white", fg=MUTED, font=(FONT, 10)).pack(
                anchor="w", padx=18, pady=(6, 20))
        for i, a in enumerate(acts):
            if i:
                tk.Frame(c, bg="#EEF2F8", height=1).pack(fill="x", padx=18)
            row = tk.Frame(c, bg="white")
            row.pack(fill="x", padx=18, pady=10)
            dot = tk.Canvas(row, width=12, height=12, bg="white", highlightthickness=0)
            dot.create_oval(2, 2, 10, 10, fill=DOTS.get(a["Loai"], PRIMARY), outline="")
            dot.pack(side="left", padx=(0, 10))
            rich(row, a["NoiDung"]).pack(side="left")
            tk.Label(row, text=time_label(a["ThoiGian"]), bg="white", fg=MUTED, font=(FONT, 9)).pack(side="right")
        tk.Frame(c, bg="white", height=8).pack()
        return c

    # ---- tìm kiếm chung
    def _focus_in(self, _e):
        if self.entry.get() == PLACEHOLDER:
            self.entry.delete(0, "end")
            self.entry.config(fg=TEXT)

    def _focus_out(self, _e):
        if not self.entry.get().strip():
            self.entry.delete(0, "end")
            self.entry.insert(0, PLACEHOLDER)
            self.entry.config(fg=MUTED)

    def search(self):
        text = self.entry.get().strip()
        if not text or text == PLACEHOLDER:
            return
        res = search_all(text)
        if not res:
            return messagebox.showinfo("Tìm kiếm", f"Không tìm thấy kết quả cho “{text}”.")
        if len(res) == 1:
            return self.go(res[0][2])
        win = tk.Toplevel(self)
        win.title(f"Kết quả cho “{text}”")
        win.configure(bg="white")
        win.transient(self.winfo_toplevel())
        tk.Label(win, text=f"{len(res)} kết quả - bấm đúp để mở", bg="white", fg=NAVY, font=(FONT, 11, "bold")).pack(
            anchor="w", padx=16, pady=(14, 6))
        lb = tk.Listbox(win, width=56, height=min(10, len(res)), font=(FONT, 10), activestyle="none", bd=0,
                        highlightthickness=1, highlightbackground=BORDER, selectbackground=PRIMARY)
        for kind, label, _t in res:
            lb.insert("end", f"  [{kind}]  {label}")
        lb.pack(padx=16, pady=(0, 14))

        def open_sel(_e=None):
            sel = lb.curselection()
            if sel:
                win.destroy()
                self.go(res[sel[0]][2])
        lb.bind("<Double-1>", open_sel)
        lb.bind("<Return>", open_sel)
        win.bind("<Escape>", lambda _e: win.destroy())
        lb.selection_set(0)
        lb.focus_set()

    # ---- xử lý yêu cầu sửa chữa / về muộn của sinh viên
    def requests_dialog(self):
        win = tk.Toplevel(self)
        win.title("Yêu cầu của sinh viên")
        win.configure(bg=PAGE_BG)
        win.transient(self.winfo_toplevel())
        tk.Label(win, text="Yêu cầu sửa chữa / về muộn đang chờ xử lý", bg=PAGE_BG, fg=NAVY,
                 font=(FONT, 14, "bold")).pack(anchor="w", padx=18, pady=(16, 8))
        cols = [("MaYC", "Mã", 50), ("HoTen", "Sinh viên", 150), ("TenPhong", "Phòng", 70), ("Loai", "Loại", 90),
                ("NoiDung", "Nội dung", 290), ("NgayGui", "Ngày gửi", 90)]
        tv = ttk.Treeview(win, columns=[c[0] for c in cols], show="headings", selectmode="browse", height=8)
        for k, h, w in cols:
            tv.heading(k, text=h)
            tv.column(k, width=w, anchor="w")
        tv.pack(fill="both", expand=True, padx=18)

        def load():
            tv.delete(*tv.get_children())
            for r in pending_requests():
                tv.insert("", "end", iid=str(r["MaYC"]), values=[r[c[0]] or "—" for c in cols])

        def decide(status):
            sel = tv.selection()
            if not sel:
                return messagebox.showwarning("Thông báo", "Vui lòng chọn một yêu cầu.", parent=win)
            r = db.query("SELECT y.*, s.HoTen FROM YeuCau y JOIN SinhVien s ON s.MaSV=y.MaSV WHERE y.MaYC=?",
                         (int(sel[0]),), one=True)
            db.execute("UPDATE YeuCau SET TrangThai=? WHERE MaYC=?", (status, r["MaYC"]))
            db.ghi_nhat_ky("yeucau", f"{status} yêu cầu {r['Loai'].lower()} của **{r['HoTen']}**")
            load()
            self.refresh()

        bar = tk.Frame(win, bg=PAGE_BG)
        bar.pack(fill="x", padx=18, pady=12)
        FlatButton(bar, "✔  Đã xử lý", lambda: decide("Đã xử lý"), padx=14, pady=7).pack(side="left")
        FlatButton(bar, "✖  Từ chối", lambda: decide("Từ chối"), bg="white", hover=SEL_BG, fg="#B42318", padx=14, pady=7,
                   highlightthickness=1, highlightbackground=BORDER).pack(side="left", padx=8)
        FlatButton(bar, "Đóng", win.destroy, bg="white", hover=SEL_BG, fg=NAVY, padx=14, pady=7,
                   highlightthickness=1, highlightbackground=BORDER).pack(side="right")
        load()
        win.bind("<Escape>", lambda _e: win.destroy())
        win.grab_set()

    # ---- xuất báo cáo tổng quan
    def export_report(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile=f"bao_cao_ktx_{date.today():%Y%m%d}.csv")
        if not path:
            return
        rs = room_summary()
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["BÁO CÁO TỔNG QUAN KÝ TÚC XÁ - HUIT", f"{date.today():%d/%m/%Y}"])
                w.writerow([])
                w.writerow(["Chỉ số", "Giá trị"])
                w.writerow(["Tổng sinh viên", scalar("SELECT COUNT(*) FROM SinhVien")])
                w.writerow(["Sinh viên đang ở", scalar("SELECT COUNT(DISTINCT MaSV) FROM HopDong WHERE TrangThai='Đang thuê'")])
                w.writerow(["Tổng số phòng", rs["rooms"]])
                w.writerow(["Tổng số chỗ / đang ở", f"{rs['cho']} / {rs['dango']}"])
                w.writerow(["Tổng công nợ (đ)", scalar("SELECT SUM(TongTien-DaThu) FROM HoaDon")])
                w.writerow([])
                w.writerow(["Tháng", "Doanh thu đã thu (đ)"])
                for (y, m), (_l, v) in zip(last_months(), revenue_series()):
                    w.writerow([f"{y}-{m:02d}", v])
                w.writerow([])
                w.writerow(["Phòng", "Loại", "Đang ở", "Số giường", "Tình trạng"])
                for p in rs["phongs"]:
                    w.writerow([p["TenPhong"], p["TenLoai"], p["DangO"], p["SoGiuong"], p["TinhTrang"]])
                w.writerow([])
                w.writerow(["Phòng", "Tháng", "Còn nợ (đ)"])
                for d in db.query("""SELECT p.TenPhong, h.Thang, h.TongTien-h.DaThu AS No FROM HoaDon h
                                     JOIN Phong p ON p.MaPhong=h.MaPhong WHERE h.TongTien>h.DaThu ORDER BY h.Thang, p.TenPhong"""):
                    w.writerow([d["TenPhong"], d["Thang"], d["No"]])
        except OSError as e:
            return error(f"Không ghi được file: {e}")
        messagebox.showinfo("Thành công", f"Đã xuất báo cáo:\n{path}")