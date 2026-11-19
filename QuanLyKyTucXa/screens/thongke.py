
import html
import math
import os
import tempfile
import tkinter as tk
import webbrowser
from datetime import date, datetime
from itertools import combinations
from tkinter import messagebox, ttk
from tkinter import font as tkfont

import database as db
from screens.base import error, money, parse_date
from screens.hoadon import load_invoices, month_end, monthly_services
from screens.hopdong import classify as classify_contract
from screens.login import BORDER, FONT, INPUT_BORDER, MUTED, NAVY, PAGE_BG, PRIMARY, TEXT, rounded_rect
from screens.sinhvien import GREEN_BG, GREEN_FG, LINE, Card, IconButton, SearchBox, fold

ALL_ROOMS = "Tất cả phòng"
C_REV, C_DEBT, C_PAID = "#1558C0", "#A9D3FF", "#22A94B"
ORANGE, RED = "#E8791B", "#B42318"
SOFT = "#E3EEFF"
CHART_MONTHS = 5


# ====================================================================== tính toán (không phụ thuộc giao diện)
def month_key(d):
    return f"{d.year:04d}-{d.month:02d}"


def shift_month(m, k):
    y, mo = int(m[:4]), int(m[5:7])
    t = y * 12 + (mo - 1) + k
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


def month_label(m):
    return f"Tháng {m[5:7]}/{m[:4]}"


def short_month(m):
    return f"T{int(m[5:7])}/{m[:4]}"


def fmt_short(v):
    """52.000.000 -> '52tr', 78.500.000 -> '78.5tr', 800.000 -> '800k'."""
    v = float(v or 0)
    if v >= 1e9:
        return f"{v / 1e9:.1f}".rstrip("0").rstrip(".") + "tỷ"
    if v >= 1e6:
        return f"{v / 1e6:.1f}".rstrip("0").rstrip(".") + "tr"
    if v >= 1e3:
        return f"{v / 1e3:.0f}k"
    return str(int(v))


def trend(cur, prev):
    """(chữ, màu chữ, màu nền) của nhãn so với tháng trước; None nếu không có gì để so."""
    if not cur and not prev:
        return None
    if not prev:
        return "↑ mới", GREEN_FG, GREEN_BG
    pct = round((cur - prev) * 100 / prev)
    if pct > 0:
        return f"↑ +{pct}%", GREEN_FG, GREEN_BG
    if pct < 0:
        return f"↓ {pct}%", RED, "#FDE8E8"
    return "→ 0%", PRIMARY, SOFT


def nice_step(top, ticks=5):
    """Bước chia trục tung đẹp (1/2/5 x 10^k) sao cho khoảng ticks vạch."""
    raw = max(top, 1) / ticks
    p = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * p:
            return m * p
    return 10 * p


def residents(day, ma_phong=None):
    """Số sinh viên đang ở tại ngày `day` (theo ngày hợp đồng; hợp đồng còn 'Đang thuê' tính là còn ở)."""
    n = 0
    for h in db.query("SELECT MaPhong, NgayBatDau, NgayKetThuc, TrangThai FROM HopDong"):
        if ma_phong and h["MaPhong"] != ma_phong:
            continue
        try:
            start, end = parse_date(h["NgayBatDau"]).date(), parse_date(h["NgayKetThuc"]).date()
        except (ValueError, TypeError):
            continue
        if start <= day and (day <= end or h["TrangThai"] == "Đang thuê"):
            n += 1
    return n


def services_used(inv, monthly, max_people=12):
    """Dịch vụ tháng (vd. Internet) đã được tính trong hóa đơn - suy ra từ 'Dịch vụ khác' = tổng giá x số người."""
    k = inv["TienKhac"]
    if k <= 0 or not monthly:
        return []
    tries = ([inv["SoNguoi"]] if inv["SoNguoi"] else []) + list(range(1, max_people + 1))
    for n in tries:
        for r in range(1, len(monthly) + 1):
            for combo in combinations(monthly, r):
                if sum(s["DonGia"] for s in combo) * n == k:
                    return [s["TenDV"] for s in combo]
    return [s["TenDV"] for s in monthly]


def compute_stats(month, ma_phong=None, today=None):
    """Toàn bộ số liệu của trang cho (tháng 'YYYY-MM', phòng hoặc None = tất cả)."""
    today = today or date.today()
    rooms = {p["MaPhong"]: p for p in db.danh_sach_phong()}
    invs = [r for r in load_invoices() if not ma_phong or r["MaPhong"] == ma_phong]
    by_month = {}
    for r in invs:
        a = by_month.setdefault(r["Thang"], {"rev": 0, "billed": 0, "n": 0})
        a["rev"] += r["DaThu"]
        a["billed"] += r["TongTien"]
        a["n"] += 1
    cur = by_month.get(month, {"rev": 0, "billed": 0, "n": 0})
    prev = by_month.get(shift_month(month, -1), {"rev": 0, "billed": 0, "n": 0})
    s = {"month": month, "room": ma_phong, "revenue": cur["rev"], "billed": cur["billed"],
         "debt": cur["billed"] - cur["rev"], "n_inv": cur["n"], "prev_revenue": prev["rev"]}
    s["pay_rate"] = round(cur["rev"] * 100 / cur["billed"]) if cur["billed"] else None
    s["avg_inv"] = round(cur["rev"] / cur["n"]) if cur["n"] else 0

    ref = min(month_end(month), today)                       # tháng hiện tại: tính tới hôm nay
    ref_prev = min(month_end(shift_month(month, -1)), today)
    s["students"], s["prev_students"] = residents(ref, ma_phong), residents(ref_prev, ma_phong)
    if ma_phong:
        s["capacity"] = rooms[ma_phong]["SoGiuong"] if ma_phong in rooms else 0
    else:
        s["capacity"] = sum(p["SoGiuong"] for p in rooms.values() if p["TinhTrang"] != "Bảo trì")
    s["occupancy"] = min(100, round(s["students"] * 100 / s["capacity"])) if s["capacity"] else 0

    months = [shift_month(month, k) for k in range(-(CHART_MONTHS - 1), 1)]
    s["series"] = [(m, by_month.get(m, {"rev": 0})["rev"],
                    by_month.get(m, {"billed": 0, "rev": 0})["billed"] - by_month.get(m, {"rev": 0})["rev"])
                   for m in months]

    cur_inv = [r for r in invs if r["Thang"] == month]
    per_room = {}
    for r in cur_inv:
        per_room[r["MaPhong"]] = per_room.get(r["MaPhong"], 0) + r["DaThu"]
    top = sorted(per_room.items(), key=lambda kv: (-kv[1], rooms.get(kv[0], {}).get("TenPhong", "")))[:3]
    s["top_rooms"] = [{"MaPhong": m, "TenPhong": rooms[m]["TenPhong"], "TenLoai": rooms[m]["TenLoai"], "Thu": v}
                      for m, v in top if m in rooms]

    monthly = monthly_services()
    usage = {}
    for r in cur_inv:
        names = [d["TenDV"] for d in db.query("SELECT TenDV FROM DichVu")
                 if (r["TienDien"] > 0 and fold(d["TenDV"]) == "dien") or (r["TienNuoc"] > 0 and fold(d["TenDV"]) == "nuoc")]
        names += services_used(r, monthly)
        for nme in set(names):
            usage[nme] = usage.get(nme, 0) + 1
    s["services"] = sorted(usage.items(), key=lambda kv: (-kv[1], kv[0]))[:3]

    s["overdue"] = sum(1 for r in invs if r["Tinh"] == "Quá hạn" and r["Thang"] <= month)
    return s


def notifications():
    """[(nội dung, trang, tham số goto)] việc cần xử lý, dùng cho chuông thông báo."""
    out = []
    n = sum(1 for r in load_invoices() if r["Tinh"] == "Quá hạn")
    if n:
        out.append((f"{n} hóa đơn quá hạn thanh toán", "hoadon", {"flt": "Quá hạn"}, n))
    soon = over = 0
    for h in db.query("SELECT * FROM HopDong"):
        try:
            label, _left = classify_contract(h)
        except (ValueError, TypeError, KeyError):
            continue
        soon += label == "Sắp hết hạn"
        over += label == "Quá hạn"
    if soon:
        out.append((f"{soon} hợp đồng sắp hết hạn", "hopdong", {"flt": "Sắp hết hạn"}, soon))
    if over:
        out.append((f"{over} hợp đồng đã quá hạn", "hopdong", {"flt": "Quá hạn"}, over))
    q = db.query("SELECT COUNT(*) FROM YeuCau WHERE TrangThai='Chờ xử lý'", one=True)[0]
    if q:
        out.append((f"{q} yêu cầu của sinh viên chờ xử lý", "dashboard", {}, q))
    return out


# ====================================================================== biểu tượng vẽ tay
def mini_icon(parent, kind, size=34, bg="white", tint=SOFT):
    """Biểu tượng nhỏ trong ô vuông bo góc."""
    cv = tk.Canvas(parent, width=size, height=size, bg=bg, highlightthickness=0)
    c = size / 2
    rounded_rect(cv, 0, 0, size, size, 9, fill=tint, outline=tint)
    kw = dict(fill=PRIMARY, width=2, capstyle="round", joinstyle="round")
    if kind == "calendar":
        cv.create_rectangle(c - 8, c - 7, c + 8, c + 8, outline=PRIMARY, width=2)
        cv.create_line(c - 8, c - 2, c + 8, c - 2, **kw)
        cv.create_line(c - 4, c - 10, c - 4, c - 5, **kw)
        cv.create_line(c + 4, c - 10, c + 4, c - 5, **kw)
    elif kind == "dollar":
        cv.create_text(c, c, text="$", font=(FONT, int(size * 0.5), "bold"), fill=GREEN_FG)
    elif kind == "clock":
        cv.create_oval(c - 9, c - 9, c + 9, c + 9, outline=ORANGE, width=2)
        cv.create_line(c, c - 5, c, c, c + 4, c + 3, fill=ORANGE, width=2, capstyle="round", joinstyle="round")
    elif kind == "bolt":
        cv.create_polygon(c + 2, c - 10, c - 6, c + 2, c, c + 2, c - 2, c + 10, c + 7, c - 3, c + 1, c - 3,
                          fill="#F5A524", outline="#F5A524", joinstyle="round")
    elif kind == "drop":
        cv.create_polygon(c, c - 10, c - 7, c + 1, c - 5, c + 7, c, c + 10, c + 5, c + 7, c + 7, c + 1,
                          fill="#3B9BF0", outline="#3B9BF0", smooth=True)
    elif kind == "wifi":
        for r in (4, 8, 12):
            cv.create_arc(c - r, c - r + 4, c + r, c + r + 4, start=45, extent=90, style="arc", outline=PRIMARY, width=2)
        cv.create_oval(c - 1.5, c + 4, c + 1.5, c + 7, fill=PRIMARY, outline=PRIMARY)
    else:                                                   # dịch vụ khác: nhãn giá
        cv.create_polygon(c - 8, c - 3, c, c - 9, c + 8, c - 3, c + 8, c + 8, c - 8, c + 8, fill=PRIMARY, outline=PRIMARY)
    return cv


def title_icon(parent, kind, bg="white"):
    """Biểu tượng nhỏ cạnh tiêu đề thẻ (cúp / sao / tia sét / biểu đồ / hình tròn)."""
    cv = tk.Canvas(parent, width=26, height=26, bg=bg, highlightthickness=0)
    if kind == "trophy":
        cv.create_polygon(7, 5, 19, 5, 18, 13, 14, 16, 12, 16, 8, 13, fill="#F4B400", outline="#F4B400")
        cv.create_rectangle(11, 16, 15, 20, fill="#F4B400", outline="#F4B400")
        cv.create_rectangle(8, 20, 18, 23, fill="#F4B400", outline="#F4B400")
    elif kind == "star":
        pts = []
        for i in range(10):
            r = 10 if i % 2 == 0 else 4.2
            a = math.radians(-90 + i * 36)
            pts += [13 + r * math.cos(a), 14 + r * math.sin(a)]
        cv.create_polygon(*pts, fill="#F4B400", outline="#F4B400", joinstyle="round")
    elif kind == "bolt":
        cv.create_polygon(15, 3, 6, 15, 12, 15, 10, 24, 20, 11, 14, 11, fill="#F4B400", outline="#F4B400")
    elif kind == "bars":
        for x, h in ((5, 9), (11, 16), (17, 12)):
            cv.create_rectangle(x, 23 - h, x + 5, 23, fill=PRIMARY, outline=PRIMARY)
    elif kind == "pie":
        cv.create_oval(4, 4, 22, 22, fill=PRIMARY, outline=PRIMARY)
        cv.create_arc(4, 4, 22, 22, start=40, extent=70, fill="white", outline="white")
    return cv


def kpi_icon(cv, kind):
    c = PRIMARY
    cv.create_oval(2, 2, 62, 62, fill=SOFT if kind != "alert" else "#FFF1E3", outline="")
    if kind == "home":
        cv.create_polygon(32, 16, 14, 32, 20, 32, 20, 46, 29, 46, 29, 37, 35, 37, 35, 46, 44, 46, 44, 32, 50, 32,
                          fill=c, outline=c, joinstyle="round")
    elif kind == "bed":
        cv.create_rectangle(15, 22, 19, 44, fill=c, outline=c)
        cv.create_rectangle(15, 34, 49, 40, fill=c, outline=c)
        cv.create_rectangle(45, 40, 49, 44, fill=c, outline=c)
        cv.create_rectangle(21, 26, 33, 33, fill=c, outline=c)
        cv.create_rectangle(35, 28, 49, 34, fill=c, outline=c)
    elif kind == "money":
        cv.create_polygon(26, 14, 38, 14, 34, 22, 30, 22, fill=c, outline=c)
        cv.create_oval(17, 21, 47, 49, fill=c, outline=c)
        cv.create_text(32, 36, text="$", font=(FONT, 15, "bold"), fill="white")
    elif kind == "alert":
        cv.create_oval(16, 16, 48, 48, fill=ORANGE, outline=ORANGE)
        cv.create_line(32, 23, 32, 34, fill="white", width=4, capstyle="round")
        cv.create_oval(30, 38, 34, 42, fill="white", outline="white")


# ====================================================================== khung cuộn dọc
class ScrollFrame(tk.Frame):
    """Khung cuộn dọc: cửa sổ thấp vẫn xem được hết trang."""

    def __init__(self, master):
        super().__init__(master, bg=PAGE_BG)
        self.cv = tk.Canvas(self, bg=PAGE_BG, highlightthickness=0)
        self.sb = ttk.Scrollbar(self, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=self._on_scroll)
        self.cv.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.cv, bg=PAGE_BG)
        self.win = self.cv.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda _e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>", lambda e: self.cv.itemconfigure(self.win, width=e.width))
        self.bind("<Enter>", lambda _e: self._bind_wheel())
        self.bind("<Leave>", lambda _e: self._unbind_wheel())

    def _on_scroll(self, a, b):
        self.sb.set(a, b)
        if float(a) <= 0 and float(b) >= 1:
            self.sb.pack_forget()
        elif not self.sb.winfo_ismapped():
            self.sb.pack(side="right", fill="y")

    def _bind_wheel(self):
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(ev, self._wheel)

    def _unbind_wheel(self):
        for ev in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.unbind_all(ev)

    def _wheel(self, e):
        try:
            if self.cv.yview() == (0.0, 1.0):
                return
            step = -1 if (getattr(e, "num", 0) == 4 or getattr(e, "delta", 0) > 0) else 1
            self.cv.yview_scroll(step * 3, "units")
        except tk.TclError:
            self._unbind_wheel()


# ====================================================================== màn hình
class ThongKeScreen(tk.Frame):
    def __init__(self, master, user=None):
        super().__init__(master, bg=PAGE_BG)
        self.user = user or {}
        self.s = {}
        self.f_norm = tkfont.Font(family=FONT, size=10)
        self.f_bold = tkfont.Font(family=FONT, size=10, weight="bold")
        today = date.today()
        months = {r["Thang"] for r in db.query("SELECT DISTINCT Thang FROM HoaDon")} | {month_key(today)}
        self.months = sorted(months, reverse=True)
        self.rooms = [(p["MaPhong"], p["TenPhong"]) for p in db.danh_sach_phong()]
        self.month_var = tk.StringVar(master=self, value=month_label(month_key(today)))
        self.room_var = tk.StringVar(master=self, value=ALL_ROOMS)
        self.kw = tk.StringVar(master=self)
        self.scroll = ScrollFrame(self)
        self.scroll.pack(fill="both", expand=True)
        self._build(self.scroll.inner)
        self.refresh()

    # ---- điều hướng sang trang khác (đã lọc sẵn)
    def go(self, page, **kw):
        app = self.winfo_toplevel()
        if hasattr(app, "goto"):
            app.goto(page, **kw)

    def _link(self, widget, page, **kw):
        """Cho cả khung (và mọi thành phần con) bấm được để chuyển trang."""
        widget.configure(cursor="hand2")
        widget.bind("<Button-1>", lambda _e: self.go(page, **kw), add="+")
        for c in widget.winfo_children():
            self._link(c, page, **kw)

    # ---- dựng giao diện
    def _build(self, root):
        pad = 40
        head = tk.Frame(root, bg=PAGE_BG)
        head.pack(fill="x", padx=pad, pady=(28, 0))
        box = tk.Frame(head, bg=PAGE_BG)
        box.pack(side="left")
        tk.Label(box, text="Thống kê & báo cáo", bg=PAGE_BG, fg=NAVY, font=(FONT, 20, "bold")).pack(anchor="w")
        tk.Label(box, text="Theo dõi, phân tích dữ liệu và xuất báo cáo chi tiết", bg=PAGE_BG, fg=MUTED,
                 font=(FONT, 10)).pack(anchor="w")

        right = tk.Frame(head, bg=PAGE_BG)
        right.pack(side="right", anchor="n")
        top = tk.Frame(right, bg=PAGE_BG)
        top.pack(anchor="e")
        self._admin_chip(top).pack(side="right", padx=(14, 0))
        self.bell = tk.Canvas(top, width=44, height=44, bg=PAGE_BG, highlightthickness=0, cursor="hand2")
        self.bell.pack(side="right")
        self.bell.bind("<Button-1>", self._show_bell)
        search = SearchBox(top, self.kw, "Tìm sinh viên, phòng, hóa đơn...", width=290)
        search.pack(side="right", padx=(0, 14))
        search.entry.bind("<Return>", lambda _e: self._global_search())
        filt = tk.Frame(right, bg=PAGE_BG)
        filt.pack(anchor="e", pady=(8, 0))
        IconButton(filt, "Xem báo cáo", "chart", self.on_report, "primary").pack(side="right")
        for var, values, w in ((self.room_var, [ALL_ROOMS] + [n for _m, n in self.rooms], 14),
                               (self.month_var, [month_label(m) for m in self.months], 15)):
            cb = ttk.Combobox(filt, textvariable=var, values=values, width=w, state="readonly", font=(FONT, 10))
            cb.pack(side="right", padx=(0, 10), ipady=6)
            cb.bind("<<ComboboxSelected>>", lambda _e: self.refresh())

        # --- 4 thẻ số liệu
        cards = tk.Frame(root, bg=PAGE_BG)
        cards.pack(fill="x", padx=pad, pady=(18, 16))
        self.kpi = {}
        for i, (key, icon, title) in enumerate((("students", "home", "Sinh viên đang ở"),
                                                ("occupancy", "bed", "Tỷ lệ lấp đầy"),
                                                ("revenue", "money", "Tổng doanh thu"),
                                                ("debt", "alert", "Công nợ"))):
            cards.columnconfigure(i, weight=1, uniform="k")
            c = Card(cards)
            c.grid(row=0, column=i, sticky="ew", padx=(0, 0 if i == 3 else 14))
            c.config(height=110)
            cv = tk.Canvas(c.inner, width=64, height=64, bg="white", highlightthickness=0)
            cv.place(x=18, y=22)
            kpi_icon(cv, icon)
            tk.Label(c.inner, text=title, bg="white", fg="#33466A", font=(FONT, 10)).place(x=96, y=20)
            val = tk.Label(c.inner, text="0", bg="white", fg=ORANGE if key == "debt" else NAVY, font=(FONT, 17, "bold"))
            val.place(x=94, y=42)
            self.kpi[key] = {"val": val, "card": c}
            if key == "occupancy":
                bar = tk.Canvas(c.inner, height=8, bg="white", highlightthickness=0)
                bar.place(x=96, y=84, relwidth=1.0, width=-114)
                self.kpi[key]["bar"] = bar
            elif key in ("students", "revenue"):
                pill = tk.Canvas(c.inner, height=26, width=70, bg="white", highlightthickness=0)
                pill.place(relx=1.0, rely=1.0, x=-14, y=-14, anchor="se")
                self.kpi[key]["pill"] = pill
        self._link(self.kpi["students"]["card"], "sinhvien", flt="Đang ở KTX")
        self._link(self.kpi["occupancy"]["card"], "phong")
        self._link(self.kpi["revenue"]["card"], "hoadon", flt="Đã thu")
        self._link(self.kpi["debt"]["card"], "hoadon", flt="Chưa thu")

        # --- biểu đồ + vành khuyên
        mid = tk.Frame(root, bg=PAGE_BG)
        mid.pack(fill="x", padx=pad, pady=(0, 16))
        mid.columnconfigure(0, weight=7, uniform="m")
        mid.columnconfigure(1, weight=3, uniform="m")
        c1 = Card(mid)
        c1.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        c1.config(height=330)
        h1 = tk.Frame(c1.inner, bg="white")
        h1.pack(fill="x", padx=18, pady=(14, 0))
        title_icon(h1, "bars").pack(side="left")
        tk.Label(h1, text="Doanh thu theo tháng", bg="white", fg=NAVY, font=(FONT, 12, "bold")).pack(side="left", padx=6)
        leg = tk.Frame(h1, bg="white")
        leg.pack(side="right")
        for color, text in ((C_REV, "Doanh thu"), (C_DEBT, "Công nợ")):
            d = tk.Canvas(leg, width=12, height=12, bg="white", highlightthickness=0)
            d.create_oval(1, 1, 11, 11, fill=color, outline=color)
            d.pack(side="left", padx=(12, 4))
            tk.Label(leg, text=text, bg="white", fg=TEXT, font=(FONT, 10)).pack(side="left")
        self.chart = tk.Canvas(c1.inner, bg="white", highlightthickness=0)
        self.chart.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.chart.bind("<Configure>", lambda _e: self.draw_chart())

        c2 = Card(mid)
        c2.grid(row=0, column=1, sticky="nsew")
        h2 = tk.Frame(c2.inner, bg="white")
        h2.pack(fill="x", padx=18, pady=(14, 0))
        title_icon(h2, "pie").pack(side="left")
        tk.Label(h2, text="Tỷ lệ thanh toán", bg="white", fg=NAVY, font=(FONT, 12, "bold")).pack(side="left", padx=6)
        body = tk.Frame(c2.inner, bg="white")
        body.pack(fill="both", expand=True, padx=10, pady=8)
        self.donut = tk.Canvas(body, width=210, height=210, bg="white", highlightthickness=0)
        self.donut.pack(side="top", pady=(6, 4))
        lg = tk.Frame(body, bg="white")
        lg.pack(side="top")
        self.legend = {}
        for key, color, text in (("paid", C_PAID, "Đã thanh toán"), ("unpaid", C_DEBT, "Chưa thanh toán")):
            row = tk.Frame(lg, bg="white")
            row.pack(fill="x", pady=2)
            d = tk.Canvas(row, width=12, height=12, bg="white", highlightthickness=0)
            d.create_oval(1, 1, 11, 11, fill=color, outline=color)
            d.pack(side="left", padx=(0, 6))
            tk.Label(row, text=text, bg="white", fg=TEXT, font=(FONT, 10)).pack(side="left")
            self.legend[key] = tk.Label(row, text="", bg="white", fg=TEXT, font=(FONT, 10, "bold"))
            self.legend[key].pack(side="right", padx=(24, 0))

        # --- 3 thẻ dưới
        bot = tk.Frame(root, bg=PAGE_BG)
        bot.pack(fill="x", padx=pad, pady=(0, 30))
        for i, w in enumerate((36, 29, 32)):
            bot.columnconfigure(i, weight=w, uniform="b")
        self.top_card = self._small_card(bot, 0, "trophy", "Top phòng có doanh thu cao nhất")
        self.svc_card = self._small_card(bot, 1, "star", "Dịch vụ sử dụng nhiều nhất")
        self.quick_card = self._small_card(bot, 2, "bolt", "Thống kê nhanh")

    def _small_card(self, parent, col, icon, title):
        c = Card(parent)
        c.grid(row=0, column=col, sticky="nsew", padx=(0, 0 if col == 2 else 14))
        c.config(height=262)
        h = tk.Frame(c.inner, bg="white")
        h.pack(fill="x", padx=18, pady=(14, 8))
        title_icon(h, icon).pack(side="left")
        tk.Label(h, text=title, bg="white", fg=NAVY, font=(FONT, 12, "bold")).pack(side="left", padx=6)
        body = tk.Frame(c.inner, bg="white")
        body.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        return body

    def _admin_chip(self, parent):
        name = (self.user.get("HoTen") or "Admin")
        chip = tk.Frame(parent, bg=PAGE_BG)
        cv = tk.Canvas(chip, width=40, height=40, bg=PAGE_BG, highlightthickness=0)
        cv.create_oval(2, 2, 38, 38, fill=PRIMARY, outline=PRIMARY)
        cv.create_text(20, 20, text=name.strip()[:1].upper() or "A", fill="white", font=(FONT, 13, "bold"))
        cv.pack(side="left")
        short = "Admin" if self.user.get("VaiTro") == "admin" else name.split(" ")[-1]
        tk.Label(chip, text=short, bg=PAGE_BG, fg=NAVY, font=(FONT, 10, "bold")).pack(side="left", padx=(8, 2))
        tk.Label(chip, text="⌄", bg=PAGE_BG, fg=NAVY, font=(FONT, 10)).pack(side="left")
        return chip

    # ---- cập nhật dữ liệu
    def _selected(self):
        m = next((k for k in self.months if month_label(k) == self.month_var.get()), self.months[0])
        room = next((ma for ma, name in self.rooms if name == self.room_var.get()), None)
        return m, room

    def refresh(self):
        m, room = self._selected()
        self.s = s = compute_stats(m, room)
        k = self.kpi
        k["students"]["val"].config(text=str(s["students"]))
        k["occupancy"]["val"].config(text=f"{s['occupancy']}%")
        k["revenue"]["val"].config(text=f"{money(s['revenue'])}đ")
        k["debt"]["val"].config(text=f"{money(s['debt'])}đ")
        self._set_pill(k["students"]["pill"], trend(s["students"], s["prev_students"]))
        self._set_pill(k["revenue"]["pill"], trend(s["revenue"], s["prev_revenue"]))
        bar = k["occupancy"]["bar"]
        bar.delete("all")
        w = max(bar.winfo_width(), 1)
        rounded_rect(bar, 0, 0, w, 8, 4, fill="#DDE6F5", outline="#DDE6F5")
        if s["occupancy"]:
            rounded_rect(bar, 0, 0, max(8, w * s["occupancy"] / 100), 8, 4, fill=C_PAID, outline=C_PAID)
        bar.bind("<Configure>", lambda _e: self.refresh_bar())
        self.draw_chart()
        self.draw_donut()
        self._fill_top()
        self._fill_services()
        self._fill_quick()
        self._draw_bell()

    def refresh_bar(self):
        bar, s = self.kpi["occupancy"]["bar"], self.s
        bar.delete("all")
        w = max(bar.winfo_width(), 1)
        rounded_rect(bar, 0, 0, w, 8, 4, fill="#DDE6F5", outline="#DDE6F5")
        if s.get("occupancy"):
            rounded_rect(bar, 0, 0, max(8, w * s["occupancy"] / 100), 8, 4, fill=C_PAID, outline=C_PAID)

    @staticmethod
    def _set_pill(cv, t):
        cv.delete("all")
        if not t:
            return
        text, fg, bg = t
        f = tkfont.Font(family=FONT, size=9, weight="bold")
        w = f.measure(text) + 20
        cv.config(width=w)
        rounded_rect(cv, 0, 0, w, 26, 13, fill=bg, outline=bg)
        cv.create_text(w / 2, 13, text=text, font=f, fill=fg)

    # ---- biểu đồ cột
    def draw_chart(self):
        cv = self.chart
        cv.delete("all")
        w, h = max(cv.winfo_width(), 1), max(cv.winfo_height(), 1)
        series = self.s.get("series") or []
        if not series:
            return
        left, bottom, top = 56, 34, 22
        peak = max([max(r, d) for _m, r, d in series] + [1])
        step = nice_step(peak)
        ymax = step * math.ceil(peak / step)
        ph = h - bottom - top
        y_of = lambda v: top + ph * (1 - v / ymax)
        f = tkfont.Font(family=FONT, size=9)
        fb = tkfont.Font(family=FONT, size=9, weight="bold")
        v = 0
        while v <= ymax + 1e-6:
            y = y_of(v)
            cv.create_line(left, y, w - 12, y, fill="#E6ECF7")
            cv.create_text(left - 8, y, text=fmt_short(v) if v else "0", anchor="e", font=f, fill=MUTED)
            v += step
        slot = (w - left - 12) / len(series)
        bw = min(46, slot * 0.28)
        for i, (m, rev, debt) in enumerate(series):
            cx = left + slot * (i + 0.5)
            for x0, val, color in ((cx - bw - 3, rev, C_REV), (cx + 3, debt, C_DEBT)):
                y1 = y_of(val)
                cv.create_rectangle(x0, y1, x0 + bw, y_of(0), fill=color, outline=color)
                cv.create_text(x0 + bw / 2, y1 - 9, text=fmt_short(val), font=fb, fill=NAVY if color == C_REV else MUTED)
            cv.create_text(cx, h - bottom + 16, text=short_month(m), font=f, fill=TEXT)

    # ---- vành khuyên tỷ lệ thanh toán
    def draw_donut(self):
        cv, s = self.donut, self.s
        cv.delete("all")
        box = (22, 22, 188, 188)
        rate = s.get("pay_rate")
        if rate is None:
            cv.create_arc(*box, start=0, extent=359.9, style="arc", outline="#E1E8F5", width=30)
            cv.create_text(105, 100, text="—", font=(FONT, 24, "bold"), fill=NAVY)
            cv.create_text(105, 128, text="Chưa có hóa đơn", font=(FONT, 9), fill=MUTED)
            self.legend["paid"].config(text="—")
            self.legend["unpaid"].config(text="—")
            return
        cv.create_arc(*box, start=0, extent=359.9, style="arc", outline=C_DEBT, width=30)
        if rate >= 100:
            cv.create_arc(*box, start=0, extent=359.9, style="arc", outline=C_PAID, width=30)
        elif rate > 0:
            cv.create_arc(*box, start=90, extent=-3.6 * rate, style="arc", outline=C_PAID, width=30)
        cv.create_text(105, 98, text=f"{rate}%", font=(FONT, 24, "bold"), fill=NAVY)
        cv.create_text(105, 128, text="Đã thanh toán", font=(FONT, 9), fill=TEXT)
        self.legend["paid"].config(text=f"{rate}%")
        self.legend["unpaid"].config(text=f"{100 - rate}%")

    # ---- 3 thẻ dưới
    @staticmethod
    def _clear(frame):
        for w in frame.winfo_children():
            w.destroy()

    def _table(self, body, heads, rows, widths, empty):
        """Bảng nhỏ: dòng tiêu đề nền nhạt + các dòng; rows = [(danh sách ô, hành động bấm)]."""
        head = tk.Frame(body, bg="#F3F7FD")
        head.pack(fill="x")
        for i, (t, w) in enumerate(zip(heads, widths)):
            head.columnconfigure(i, weight=w)
            tk.Label(head, text=t, bg="#F3F7FD", fg=TEXT, font=self.f_bold,
                     anchor="e" if i == len(heads) - 1 else "w").grid(row=0, column=i, sticky="ew", padx=8, pady=7)
        if not rows:
            tk.Label(body, text=empty, bg="white", fg=MUTED, font=self.f_norm).pack(pady=24)
            return
        for cells, action in rows:
            row = tk.Frame(body, bg="white")
            row.pack(fill="x")
            for i, w in enumerate(widths):
                row.columnconfigure(i, weight=w)
            for i, cell in enumerate(cells):
                if isinstance(cell, tuple):                    # (biểu tượng, chữ)
                    f = tk.Frame(row, bg="white")
                    mini_icon(f, cell[0], 28).pack(side="left", padx=(0, 8))
                    tk.Label(f, text=cell[1], bg="white", fg=TEXT, font=self.f_norm).pack(side="left")
                    f.grid(row=0, column=i, sticky="w", padx=8, pady=6)
                else:
                    last = i == len(cells) - 1
                    tk.Label(row, text=cell, bg="white", fg=TEXT,
                             font=self.f_bold if i in (1, len(cells) - 1) else self.f_norm,
                             anchor="e" if last else "w").grid(row=0, column=i, sticky="ew", padx=8, pady=9)
            tk.Frame(body, bg=LINE, height=1).pack(fill="x")
            if action:
                self._link(row, action[0], **action[1])

    def _fill_top(self):
        self._clear(self.top_card)
        rows = [([str(i), r["TenPhong"], r["TenLoai"], f"{money(r['Thu'])}đ"], ("phong", {"keyword": r["TenPhong"]}))
                for i, r in enumerate(self.s["top_rooms"], 1)]
        self._table(self.top_card, ["#", "Mã phòng", "Loại phòng", "Doanh thu"], rows, (1, 3, 5, 5),
                    "Chưa có doanh thu trong tháng này.")

    def _fill_services(self):
        self._clear(self.svc_card)
        icons = {"dien": "bolt", "nuoc": "drop", "internet": "wifi", "wifi": "wifi"}
        rows = [([(icons.get(fold(n), "tag"), n), f"{c} lượt"], ("dichvu", {"keyword": n}))
                for n, c in self.s["services"]]
        self._table(self.svc_card, ["Dịch vụ", "Số lượng"], rows, (6, 3), "Chưa có dịch vụ nào được tính trong tháng.")

    def _fill_quick(self):
        self._clear(self.quick_card)
        s = self.s
        box = tk.Frame(self.quick_card, bg="white", highlightthickness=1, highlightbackground=LINE)
        box.pack(fill="x")
        items = (("calendar", "Hóa đơn trong tháng", f"{s['n_inv']} hóa đơn", TEXT, ("hoadon", {})),
                 ("dollar", "Doanh thu TB / hóa đơn", f"{money(s['avg_inv'])}đ", TEXT, ("hoadon", {"flt": "Đã thu"})),
                 ("clock", "Công nợ quá hạn", f"{s['overdue']} hóa đơn", ORANGE if s["overdue"] else TEXT,
                  ("hoadon", {"flt": "Quá hạn"})))
        for i, (icon, label, value, color, (page, kw)) in enumerate(items):
            row = tk.Frame(box, bg="white")
            row.pack(fill="x", padx=8, pady=5)
            mini_icon(row, icon, 30).pack(side="left")
            tk.Label(row, text=label, bg="white", fg=TEXT, font=self.f_norm).pack(side="left", padx=10)
            tk.Label(row, text=value, bg="white", fg=color, font=self.f_bold).pack(side="right")
            self._link(row, page, **kw)
            if i < 2:
                tk.Frame(box, bg=LINE, height=1).pack(fill="x", padx=8)
        IconButton(self.quick_card, "Xem chi tiết  →", "list", lambda: self.go("hoadon"), "outline").pack(
            side="right", pady=(12, 0))

    # ---- chuông thông báo
    def _draw_bell(self):
        cv = self.bell
        cv.delete("all")
        rounded_rect(cv, 2, 2, 42, 42, 12, fill="white", outline=BORDER)
        from screens.sinhvien import draw_icon
        draw_icon(cv, "bell", 22, 22, NAVY)
        self._notes = notifications()
        n = sum(x[3] for x in self._notes)
        if n:
            cv.create_oval(26, 0, 44, 18, fill="#E5484D", outline="white", width=2)
            cv.create_text(35, 9, text="9+" if n > 9 else str(n), fill="white", font=(FONT, 8, "bold"))

    def _show_bell(self, e):
        menu = tk.Menu(self, tearoff=0, font=(FONT, 10))
        if not self._notes:
            menu.add_command(label="Không có việc cần xử lý", state="disabled")
        for text, page, kw, _n in self._notes:
            menu.add_command(label=text, command=lambda p=page, k=kw: self.go(p, **k))
        try:
            menu.tk_popup(e.x_root, e.y_root + 20)
        finally:
            menu.grab_release()

    # ---- tìm kiếm toàn hệ thống (Enter)
    def _global_search(self):
        from screens.dashboard import show_search_results
        show_search_results(self, self.kw.get(), lambda t: self.go(t[0], **t[1]), self.user.get("VaiTro") == "admin")

    # ---- xuất báo cáo: trang in mở bằng trình duyệt -> Lưu thành PDF
    def on_report(self):
        s = self.s
        room = self.room_var.get()
        e = html.escape
        series = "".join(f"<tr><td>{short_month(m)}</td><td class=r>{money(r)}đ</td><td class=r>{money(d)}đ</td></tr>"
                         for m, r, d in s["series"])
        top = "".join(f"<tr><td>{i}</td><td>{e(r['TenPhong'])}</td><td>{e(r['TenLoai'])}</td>"
                      f"<td class=r>{money(r['Thu'])}đ</td></tr>" for i, r in enumerate(s["top_rooms"], 1)) \
            or "<tr><td colspan=4>Chưa có dữ liệu</td></tr>"
        svc = "".join(f"<tr><td>{e(n)}</td><td class=r>{c} lượt</td></tr>" for n, c in s["services"]) \
            or "<tr><td colspan=2>Chưa có dữ liệu</td></tr>"
        rate = f"{s['pay_rate']}%" if s["pay_rate"] is not None else "—"
        page = (f"<!doctype html><html lang='vi'><meta charset='utf-8'><title>Báo cáo {month_label(s['month'])}</title>"
                "<style>body{font-family:'Segoe UI',Arial,sans-serif;margin:32px;color:#14213D}h1{color:#0B3D91;margin:0}"
                "h2{color:#0B3D91;font-size:16px;margin:24px 0 6px}p{color:#51607F}table{border-collapse:collapse;width:100%}"
                "th{background:#F3F7FD;text-align:left}th,td{border:1px solid #DCE6F7;padding:7px 10px;font-size:13px}"
                ".r{text-align:right}</style>"
                f"<h1>Báo cáo thống kê ký túc xá</h1><p>{month_label(s['month'])} · {e(room)} · xuất lúc "
                f"{datetime.now():%d/%m/%Y %H:%M}</p><h2>Tổng quan</h2><table>"
                f"<tr><th>Sinh viên đang ở</th><td class=r>{s['students']}</td></tr>"
                f"<tr><th>Tỷ lệ lấp đầy</th><td class=r>{s['occupancy']}% ({s['students']}/{s['capacity']} giường)</td></tr>"
                f"<tr><th>Tổng doanh thu (đã thu)</th><td class=r>{money(s['revenue'])}đ</td></tr>"
                f"<tr><th>Công nợ</th><td class=r>{money(s['debt'])}đ</td></tr>"
                f"<tr><th>Tỷ lệ thanh toán</th><td class=r>{rate}</td></tr>"
                f"<tr><th>Hóa đơn trong tháng</th><td class=r>{s['n_inv']}</td></tr>"
                f"<tr><th>Công nợ quá hạn</th><td class=r>{s['overdue']} hóa đơn</td></tr></table>"
                f"<h2>Doanh thu theo tháng</h2><table><tr><th>Tháng</th><th class=r>Doanh thu</th><th class=r>Công nợ</th></tr>"
                f"{series}</table><h2>Top phòng có doanh thu cao nhất</h2><table><tr><th>#</th><th>Mã phòng</th>"
                f"<th>Loại phòng</th><th class=r>Doanh thu</th></tr>{top}</table><h2>Dịch vụ sử dụng nhiều nhất</h2>"
                f"<table><tr><th>Dịch vụ</th><th class=r>Số lượng</th></tr>{svc}</table>"
                "<script>window.onload=function(){window.print()}</script></html>")
        path = os.path.join(tempfile.gettempdir(), f"bao_cao_{s['month']}.html")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(page)
        except OSError as ex:
            return error(f"Không tạo được file: {ex}")
        if not webbrowser.open("file://" + path.replace("\\", "/")):
            messagebox.showinfo("Xuất báo cáo", f"Hãy mở file này bằng trình duyệt rồi chọn In → Lưu thành PDF:\n{path}")
