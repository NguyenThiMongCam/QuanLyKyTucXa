"""Trang Quản lý hóa đơn (quản trị) - giao diện xanh trắng theo mẫu thiết kế.

Dữ liệu dùng chung với các trang khác (không có số liệu riêng):
  - Hóa đơn tính theo PHÒNG - THÁNG (bảng HoaDon). "Tên sinh viên" lấy từ Hợp đồng 'Đang thuê' của phòng đó.
  - Tiền phòng = giá thuê của loại phòng x số sinh viên đang ở (trang Phòng + Hợp đồng).
  - Đơn giá điện / nước / dịch vụ theo tháng (Internet...) lấy từ trang Dịch vụ.
  - Thu tiền ghi vào ThanhToan + HoaDon.DaThu -> Trang chủ (doanh thu, công nợ), Thống kê, trang sinh viên tự khớp.

Tính năng: thẻ thống kê, lọc theo kỳ hóa đơn / trạng thái / loại, tìm kiếm không dấu, phân trang, lập hóa đơn
(chỉ số điện nước cũ - mới, tổng tiền hiện ngay), thu tiền nhiều lần, biên lai, nhắc nợ, xuất Excel,
xuất PDF / in hóa đơn (mở trang in của trình duyệt), báo cáo theo tháng.
"""
import calendar
import html
import math
import re
import sqlite3
import tempfile
import tkinter as tk
import webbrowser
from datetime import date, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import database as db
from screens import xlsx_io
from screens.base import error, money
from screens.login import (BORDER, ERROR, FONT, INPUT_BORDER, MUTED, NAVY, PAGE_BG, PRIMARY, SEL_BG, TEXT, Field,
                           FlatButton, rounded_rect)
from screens.modal import form_modal
from screens.sinhvien import GREEN_BG, GREEN_FG, LINE, Card, DataTable, IconButton, SearchBox, fold

HAN_NOP_NGAY = 10                     # hạn thanh toán: ngày 10 của tháng kế tiếp
HINH_THUC = ["Tiền mặt", "Chuyển khoản", "Ví điện tử"]
PAGE_SIZE = 8
SECTION_BG, READONLY_BG = "#F1F5FC", "#F1F4FA"
ORANGE, ORANGE_BG = "#B45309", "#FFF0D9"

# trạng thái lưu trong DB (HoaDon.TrangThai + "Quá hạn" tính khi hiển thị) -> chữ hiển thị, màu chữ, màu nền
STATE_LABEL = {"Đã thu": "Đã thanh toán", "Thu một phần": "Thanh toán một phần", "Chưa thu": "Chưa thanh toán",
               "Quá hạn": "Quá hạn"}
STATE_STYLE = {"Đã thu": (GREEN_FG, GREEN_BG), "Thu một phần": (PRIMARY, "#E3EEFF"),
               "Chưa thu": (ORANGE, ORANGE_BG), "Quá hạn": ("#B42318", "#FDE8E8")}
STATUS_FILTERS = ["Tất cả"] + list(STATE_LABEL.values())
LABEL_TO_STATE = {v: k for k, v in STATE_LABEL.items()}
TYPE_BASE, TYPE_SERVICE = "Phòng + điện nước", "Phòng + điện nước + dịch vụ"
TYPE_FILTERS = ["Tất cả", TYPE_BASE, TYPE_SERVICE]

TABLE_COLS = [("MaHD", "Mã hóa đơn", 96, 0.9), ("SV", "Tên sinh viên", 140, 1.5), ("TenPhong", "Phòng", 64, 0.6),
              ("LoaiPhi", "Loại phí", 132, 1.3), ("SoTien", "Số tiền", 100, 1.0), ("NgayLap", "Ngày lập", 90, 0.9),
              ("HanTT", "Hạn thanh toán", 108, 1.0), ("Tinh", "Trạng thái", 140, 1.2), ("Thao", "Thao tác", 112, 0.9)]


# ====================================================================== dữ liệu
def ensure_columns():
    """Tự thêm các cột hóa đơn mới nếu file kytucxa.db cũ chưa có (kể cả khi chưa chép đè database.py mới)."""
    have = {r["name"] for r in db.query("PRAGMA table_info(HoaDon)")}
    for col, typ in (("NgayLap", "TEXT"), ("TienKhac", "INTEGER DEFAULT 0"), ("ChiSoDien", "REAL"),
                     ("ChiSoNuoc", "REAL")):
        if col not in have:
            db.execute(f"ALTER TABLE HoaDon ADD COLUMN {col} {typ}")


def rate(name):
    r = db.query("SELECT DonGia FROM DichVu WHERE TenDV=?", (name,), one=True)
    return r["DonGia"] if r else None


def monthly_services():
    """Dịch vụ tính theo tháng (đơn vị 'tháng', vd. Internet) - cột 'Dịch vụ khác' của hóa đơn."""
    return [dict(r) for r in db.query("SELECT TenDV, DonGia, DonVi FROM DichVu ORDER BY MaDV")
            if fold(r["DonVi"] or "") == "thang"]


def month_start(thang):
    return date(int(thang[:4]), int(thang[5:7]), 1)


def month_end(thang):
    y, m = int(thang[:4]), int(thang[5:7])
    return date(y, m, calendar.monthrange(y, m)[1])


def han_nop(thang):
    """Hạn thanh toán của hóa đơn tháng 'YYYY-MM' -> date (ngày 10 tháng sau)."""
    y, m = int(thang[:4]), int(thang[5:7])
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return date(y, m, HAN_NOP_NGAY)


def parse_thang(text):
    """'11/2025' | '2025-11' | '11-2025' -> '2025-11'; sai định dạng -> None."""
    t = (text or "").strip()
    m = re.fullmatch(r"(\d{1,2})\s*[/\-]\s*(\d{4})", t)
    if m:
        mo, y = int(m.group(1)), int(m.group(2))
    else:
        m = re.fullmatch(r"(\d{4})\s*[/\-]\s*(\d{1,2})", t)
        if not m:
            return None
        y, mo = int(m.group(1)), int(m.group(2))
    return f"{y:04d}-{mo:02d}" if 1 <= mo <= 12 and 2000 <= y <= 2100 else None


def classify(r, today=None):
    """Trạng thái hiển thị: Đã thu / Quá hạn / Thu một phần / Chưa thu."""
    today = today or date.today()
    if r["DaThu"] >= r["TongTien"]:
        return "Đã thu"
    if today > han_nop(r["Thang"]):
        return "Quá hạn"
    return "Thu một phần" if r["DaThu"] > 0 else "Chưa thu"


def fmt_num(x):
    return f"{x:g}"


def dmy(d):
    return d.strftime("%d/%m/%Y")


def meter_old(ma_phong, thang):
    """Chỉ số điện / nước CŨ của phòng khi lập hóa đơn tháng `thang`: lấy chỉ số mới của hóa đơn trước đó.
    Hóa đơn cũ chưa lưu chỉ số thì cộng dồn số tiêu thụ. Trả về (điện cũ, nước cũ, là hóa đơn đầu tiên?)."""
    prev = db.query("SELECT SoDien,SoNuoc,ChiSoDien,ChiSoNuoc FROM HoaDon WHERE MaPhong=? AND Thang<? "
                    "ORDER BY Thang", (ma_phong, thang))
    if not prev:
        return 0.0, 0.0, True

    def old(read, use):
        if prev[-1][read] is not None:
            return float(prev[-1][read])
        return float(sum((p[use] or 0) for p in prev))
    return old("ChiSoDien", "SoDien"), old("ChiSoNuoc", "SoNuoc"), False


def compute(room, dien, nuoc, su_dien, su_nuoc, services):
    """Các khoản của hóa đơn. room: dict từ db.danh_sach_phong(); services: dịch vụ tháng được chọn."""
    n = room["DangO"]
    d = {"TienPhong": room["GiaThue"] * n, "TienDien": round(su_dien * dien), "TienNuoc": round(su_nuoc * nuoc),
         "TienKhac": sum(s["DonGia"] for s in services) * n}
    d["TongTien"] = d["TienPhong"] + d["TienDien"] + d["TienNuoc"] + d["TienKhac"]
    return d


def load_invoices():
    ensure_columns()
    people = {}
    for r in db.query("""SELECT c.MaPhong, s.MaSV, s.HoTen FROM HopDong c JOIN SinhVien s ON s.MaSV=c.MaSV
                         WHERE c.TrangThai='Đang thuê' ORDER BY s.HoTen"""):
        people.setdefault(r["MaPhong"], []).append((r["MaSV"], r["HoTen"]))
    out = []
    for r in db.query("""SELECT h.*, p.TenPhong FROM HoaDon h JOIN Phong p ON p.MaPhong=h.MaPhong
                         ORDER BY h.Thang DESC, p.TenPhong"""):
        d = dict(r)
        for k in ("TienPhong", "TienDien", "TienNuoc", "TienKhac", "TongTien", "DaThu", "SoDien", "SoNuoc"):
            d[k] = d.get(k) or 0
        d["CongNo"] = d["TongTien"] - d["DaThu"]
        d["Tinh"] = classify(d)
        d["TinhText"] = STATE_LABEL[d["Tinh"]]
        d["MaHD"] = f"HD{d['MaHDon']:05d}"
        ppl = people.get(d["MaPhong"], [])
        d["SoNguoi"] = len(ppl)
        d["SVTen"] = ppl[0][1] if ppl else "—"
        d["SVThem"] = max(len(ppl) - 1, 0)
        d["SVAll"] = ", ".join(n for _m, n in ppl)
        d["LoaiPhi"] = TYPE_SERVICE if d["TienKhac"] > 0 else TYPE_BASE
        d["NgayLap"] = d.get("NgayLap") or dmy(month_end(d["Thang"]))
        d["HanTT"] = dmy(han_nop(d["Thang"]))
        d["SoTien"] = f"{money(d['TongTien'])}đ"
        d["_hay"] = fold(f"{d['MaHD']} {d['MaHDon']} {d['TenPhong']} {d['Thang']} {d['LoaiPhi']} {d['TinhText']} "
                         f"{d['SVAll']} " + " ".join(str(m) for m, _n in ppl))
        out.append(d)
    return out


def payments_of(ma_hdon):
    return db.query("SELECT * FROM ThanhToan WHERE MaHDon=? ORDER BY MaTT", (ma_hdon,))


def receipt_text(r, pays):
    n = max(1, r["SoNguoi"])
    lines = ["KÝ TÚC XÁ - TRƯỜNG ĐH CÔNG THƯƠNG TP.HCM (HUIT)", "BIÊN LAI THANH TOÁN TIỀN NỘI TRÚ", "=" * 48,
             f"Hóa đơn {r['MaHD']}  |  Phòng {r['TenPhong']}  |  Tháng {r['Thang']}",
             f"Sinh viên   : {r['SVAll'] or '—'}",
             f"Tiền phòng  : {money(r['TienPhong']):>14} đ",
             f"Tiền điện   : {money(r['TienDien']):>14} đ ({fmt_num(r['SoDien'])} kWh)",
             f"Tiền nước   : {money(r['TienNuoc']):>14} đ ({fmt_num(r['SoNuoc'])} m³)",
             f"Dịch vụ khác: {money(r['TienKhac']):>14} đ", "-" * 48,
             f"Tổng cộng   : {money(r['TongTien']):>14} đ", f"Đã thu      : {money(r['DaThu']):>14} đ",
             f"Còn nợ      : {money(r['CongNo']):>14} đ", f"Mỗi người ({n}): {money(round(r['TongTien'] / n)):>10} đ",
             "-" * 48, "Lịch sử thanh toán:"]
    lines += [f"  {p['Ngay']}  {money(p['SoTien']):>12} đ  {p['HinhThuc']}" + (f"  ({p['GhiChu']})" if p["GhiChu"] else "")
              for p in pays] or ["  (chưa có)"]
    lines.append(f"In lúc {datetime.now():%d/%m/%Y %H:%M}")
    return "\n".join(lines)


def invoices_html(rows, auto_print=True, banner=""):
    """Trang HTML để in / lưu PDF bằng trình duyệt: mỗi hóa đơn một trang."""
    pages = []
    for r in rows:
        pays = payments_of(r["MaHDon"])
        fg, bg = STATE_STYLE[r["Tinh"]]
        items = [("Tiền phòng", f"{money(r['TienPhong'])} đ"),
                 (f"Tiền điện ({fmt_num(r['SoDien'])} kWh)", f"{money(r['TienDien'])} đ"),
                 (f"Tiền nước ({fmt_num(r['SoNuoc'])} m³)", f"{money(r['TienNuoc'])} đ"),
                 ("Dịch vụ khác", f"{money(r['TienKhac'])} đ")]
        rows_html = "".join(f"<tr><td>{html.escape(k)}</td><td class='r'>{v}</td></tr>" for k, v in items)
        pay_html = "".join(f"<li>{html.escape(p['Ngay'] or '')} · {money(p['SoTien'])} đ · {html.escape(p['HinhThuc'] or '')}"
                           + (f" · {html.escape(p['GhiChu'])}" if p["GhiChu"] else "") + "</li>" for p in pays) \
            or "<li>Chưa có lần thanh toán nào.</li>"
        pages.append(f"""<section><h1>KÝ TÚC XÁ - ĐH CÔNG THƯƠNG TP.HCM (HUIT)</h1>
<h2>HÓA ĐƠN TIỀN NỘI TRÚ {html.escape(r['MaHD'])}</h2>
<p>Phòng <b>{html.escape(r['TenPhong'])}</b> · Tháng <b>{r['Thang']}</b> · Ngày lập {r['NgayLap']} · Hạn thanh toán <b>{r['HanTT']}</b></p>
<p>Sinh viên: {html.escape(r['SVAll'] or '—')}</p>
<table><tr><th>Khoản thu</th><th class='r'>Thành tiền</th></tr>{rows_html}
<tr class='t'><td>Tổng tiền</td><td class='r'>{money(r['TongTien'])} đ</td></tr>
<tr><td>Đã thanh toán</td><td class='r'>{money(r['DaThu'])} đ</td></tr>
<tr><td>Còn nợ</td><td class='r'>{money(r['CongNo'])} đ</td></tr></table>
<p>Trạng thái: <span style='background:{bg};color:{fg};padding:2px 10px;border-radius:10px;font-weight:600'>{r['TinhText']}</span></p>
<h3>Lịch sử thanh toán</h3><ul>{pay_html}</ul></section>""")
    script = "<script>window.onload=function(){window.print()}</script>" if auto_print else ""
    note = f"<div class='note'>{html.escape(banner)}</div>" if banner else ""
    return f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>Hóa đơn ký túc xá</title><style>
body{{font-family:'Segoe UI',Arial,sans-serif;color:#0F2447;margin:24px}} section{{max-width:640px;margin:0 auto 40px;page-break-after:always}}
h1{{font-size:15px;color:#0B3C8C;margin:0}} h2{{font-size:19px;margin:6px 0 12px}} h3{{font-size:14px;color:#0B3C8C}}
table{{width:100%;border-collapse:collapse;margin:10px 0}} td,th{{border:1px solid #DCE6F7;padding:7px 10px;text-align:left}}
th{{background:#F1F5FC}} .r{{text-align:right}} .t td{{font-weight:700;background:#E3EEFF}}
.note{{background:#FFF4DC;border:1px solid #F0D9A0;padding:10px 14px;margin-bottom:20px;border-radius:8px}}
@media print{{.note{{display:none}} body{{margin:0}}}}</style></head><body>{note}{''.join(pages)}{script}</body></html>"""


# ====================================================================== bảng
class InvoiceTable(DataTable):
    """Bảng hóa đơn: tên sinh viên (+n người), huy hiệu trạng thái, cột Thao tác gồm nút 'Xem' và menu '···'."""
    bold_keys, navy_keys = ("MaHD", "SoTien"), ("MaHD",)
    XEM_W, MORE_W = 54, 30

    def __init__(self, master, on_select, on_open, on_menu):
        self.on_menu = on_menu
        super().__init__(master, on_select, on_open, TABLE_COLS, "MaHDon")

    def _draw_cell(self, key, r, tx, cy, maxw, tag):
        b = self.body
        if key == "SV":
            name = self._fit(r["SVTen"], max(maxw - (34 if r["SVThem"] else 0), 20), self.f_norm)
            b.create_text(tx, cy, text=name, anchor="w", font=self.f_norm, fill=TEXT, tags=tag)
            if r["SVThem"]:
                b.create_text(tx + self.f_norm.measure(name) + 6, cy, text=f"+{r['SVThem']}", anchor="w",
                              font=self.f_bold, fill=PRIMARY, tags=tag)
            return True
        if key == "Tinh":
            fg, bg = STATE_STYLE[r["Tinh"]]
            self._badge(r["TinhText"], fg, bg, tx, cy, maxw, tag)
            return True
        if key == "Thao":
            rounded_rect(b, tx, cy - 13, tx + self.XEM_W, cy + 13, 8, fill=SEL_BG, outline=SEL_BG, tags=tag)
            b.create_text(tx + self.XEM_W / 2, cy, text="Xem", font=self.f_bold, fill=PRIMARY, tags=tag)
            mx = tx + self.XEM_W + 8
            rounded_rect(b, mx, cy - 13, mx + self.MORE_W, cy + 13, 8, fill="white", outline=INPUT_BORDER, tags=tag)
            b.create_text(mx + self.MORE_W / 2, cy - 1, text="···", font=self.f_bold, fill=NAVY, tags=tag)
            return True
        return False

    def _action_x(self):
        for key, x, _cw in self._layout(max(self.body.winfo_width(), 1)):
            if key == "Thao":
                return x + 12
        return None

    def _click(self, e):
        i = int(self.body.canvasy(e.y) // self.ROW_H)
        ax = self._action_x()
        if 0 <= i < len(self.rows) and ax is not None:
            ident = self.rows[i][self.key]
            if ax <= e.x <= ax + self.XEM_W:
                self.select(ident)
                return self.on_open()
            if ax + self.XEM_W + 8 <= e.x <= ax + self.XEM_W + 8 + self.MORE_W:
                self.select(ident)
                return self.on_menu(e)
        super()._click(e)


class PageBar(tk.Frame):
    """Nút chuyển trang: ‹ 1 2 3 … 25 ›"""

    def __init__(self, master, on_page):
        super().__init__(master, bg="white")
        self.on_page = on_page

    def set(self, page, pages):
        for w in self.winfo_children():
            w.destroy()

        def btn(text, target, active=False, enabled=True):
            lb = tk.Label(self, text=text, width=3, pady=3, bg=PRIMARY if active else "white",
                          fg="white" if active else (NAVY if enabled else "#A8B4CC"), font=(FONT, 10, "bold"),
                          highlightthickness=1, highlightbackground=PRIMARY if active else BORDER,
                          cursor="hand2" if enabled and not active else "arrow")
            lb.pack(side="left", padx=3)
            if enabled and not active:
                lb.bind("<Button-1>", lambda _e, t=target: self.on_page(t))

        btn("‹", page - 1, enabled=page > 1)
        prev = 0
        for n in sorted({1, pages, page - 1, page, page + 1} & set(range(1, pages + 1))):
            if n - prev > 1:
                btn("…", None, enabled=False)
            btn(str(n), n, active=n == page)
            prev = n
        btn("›", page + 1, enabled=page < pages)


# ====================================================================== hộp thoại "Lập hóa đơn mới"
class InvoiceDialog(tk.Toplevel):
    """Chọn phòng + tháng, nhập chỉ số điện nước mới; chỉ số cũ lấy từ hóa đơn trước, tổng tiền cập nhật ngay."""
    W = 580

    def __init__(self, parent, rooms, dien, nuoc, services):
        super().__init__(parent)
        self.title("Lập hóa đơn mới")
        self.configure(bg="white")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.rooms = {f"{p['MaPhong']} - {p['TenPhong']} · {p['TenLoai']} · {p['DangO']} SV": p for p in rooms}
        self.dien, self.nuoc, self.services = dien, nuoc, services
        self.result, self._key, self.first = None, None, True
        self.svc_vars = [tk.BooleanVar(master=self, value=False) for _ in services]
        self._build()
        self._recalc()
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _e: self.destroy())

    # ---- dựng giao diện
    def _section(self, parent, text):
        tk.Label(parent, text="  " + text, bg=SECTION_BG, fg=NAVY, font=(FONT, 10, "bold"), anchor="w",
                 pady=6).pack(fill="x", pady=(10, 0))

    @staticmethod
    def _cell(parent, col, label, padx):
        cell = tk.Frame(parent, bg="white")
        cell.grid(row=0 if col < 2 else 1, column=col % 2, sticky="ew", padx=padx, pady=(8, 0))
        tk.Label(cell, text=label, bg="white", fg=TEXT, font=(FONT, 10, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        return cell

    def _build(self):
        head = tk.Frame(self, bg="white")
        head.pack(fill="x", padx=24, pady=(20, 6))
        tk.Label(head, text="Lập hóa đơn mới", bg="white", fg=NAVY, font=(FONT, 15, "bold")).pack(side="left")
        box = tk.Frame(head, bg=INPUT_BORDER, padx=1, pady=1)
        box.pack(side="right")
        FlatButton(box, "×", self.destroy, bg="white", hover="#EEF4FF", fg=NAVY, font=(FONT, 16), padx=12,
                   pady=2).pack()
        body = tk.Frame(self, bg="white")
        body.pack(fill="x", padx=24)

        # --- thông tin hóa đơn
        self._section(body, "Thông tin hóa đơn")
        g = tk.Frame(body, bg="white")
        g.pack(fill="x")
        g.columnconfigure((0, 1), weight=1, uniform="c")
        c = self._cell(g, 0, "Phòng *", (0, 8))
        self.room_cb = ttk.Combobox(c, values=list(self.rooms), state="readonly", font=(FONT, 10))
        self.room_cb.set(next(iter(self.rooms)))
        self.room_cb.pack(fill="x", ipady=7)
        self.room_cb.bind("<<ComboboxSelected>>", lambda _e: (self.room_cb.selection_clear(), self._recalc()))
        c = self._cell(g, 1, "Tháng hóa đơn *", (8, 0))
        self.thang = Field(c, placeholder="MM/YYYY")
        self.thang.pack(fill="x")
        self.thang.set(date.today().strftime("%m/%Y"))
        self.thang.entry.bind("<KeyRelease>", lambda _e: self._recalc())

        # --- chỉ số sử dụng
        self._section(body, "Chỉ số sử dụng")
        g = tk.Frame(body, bg="white")
        g.pack(fill="x")
        g.columnconfigure((0, 1), weight=1, uniform="c")
        self.old_d = Field(self._cell(g, 0, "Số điện cũ (kWh)", (0, 8)), placeholder="0")
        self.old_n = Field(self._cell(g, 1, "Số nước cũ (m³)", (8, 0)), placeholder="0")
        self.new_d = Field(self._cell(g, 2, "Số điện mới (kWh) *", (0, 8)), placeholder="Nhập chỉ số mới")
        self.new_n = Field(self._cell(g, 3, "Số nước mới (m³) *", (8, 0)), placeholder="Nhập chỉ số mới")
        for f in (self.old_d, self.old_n, self.new_d, self.new_n):
            f.pack(fill="x")
            f.entry.bind("<KeyRelease>", lambda _e: self._recalc())
        self.hint = tk.Label(body, text="", bg="white", fg=MUTED, font=(FONT, 9), anchor="w")
        self.hint.pack(fill="x", pady=(4, 0))

        if self.services:
            sv = tk.Frame(body, bg="white")
            sv.pack(fill="x", pady=(4, 0))
            tk.Label(sv, text="Dịch vụ theo tháng (tính theo đầu người):", bg="white", fg=TEXT,
                     font=(FONT, 10, "bold")).pack(anchor="w")
            for s, var in zip(self.services, self.svc_vars):
                tk.Checkbutton(sv, text=f"{s['TenDV']} - {money(s['DonGia'])}đ/{s['DonVi']}", variable=var,
                               command=self._recalc, bg="white", activebackground="white", fg=TEXT,
                               font=(FONT, 10), anchor="w").pack(anchor="w")

        # --- chi tiết thanh toán
        self._section(body, "Chi tiết thanh toán")
        tbl = tk.Frame(body, bg=LINE)
        tbl.pack(fill="x", pady=(8, 0))
        tbl.columnconfigure(0, weight=1)
        for col, text in enumerate(("Khoản thu", "Thành tiền")):
            tk.Label(tbl, text=text, bg=SECTION_BG, fg=NAVY, font=(FONT, 10, "bold"), pady=5,
                     anchor="w" if col == 0 else "e").grid(row=0, column=col, sticky="ew", padx=(0, 1 if col == 0 else 0),
                                                           pady=(0, 1))
        self.cells = {}
        for i, key in enumerate(("phong", "dien", "nuoc", "khac"), start=1):
            a = tk.Label(tbl, bg="white", fg=TEXT, font=(FONT, 10), anchor="w", padx=10, pady=4)
            b = tk.Label(tbl, bg="white", fg=TEXT, font=(FONT, 10), anchor="e", padx=10, pady=4)
            a.grid(row=i, column=0, sticky="ew", padx=(0, 1), pady=(0, 1))
            b.grid(row=i, column=1, sticky="ew", pady=(0, 1))
            self.cells[key] = (a, b)
        ta = tk.Label(tbl, text="Tổng tiền", bg=SEL_BG, fg=NAVY, font=(FONT, 11, "bold"), anchor="w", padx=10, pady=7)
        tb = tk.Label(tbl, bg=SEL_BG, fg=NAVY, font=(FONT, 12, "bold"), anchor="e", padx=10, pady=7)
        ta.grid(row=5, column=0, sticky="ew", padx=(0, 1))
        tb.grid(row=5, column=1, sticky="ew")
        self.total_lb = tb

        self.msg = tk.Label(body, text="", bg="white", fg=ERROR, font=(FONT, 10), anchor="w", justify="left",
                            wraplength=self.W - 48)
        self.msg.pack(fill="x", pady=(8, 0))
        bar = tk.Frame(self, bg="white")
        bar.pack(fill="x", padx=24, pady=(6, 18))
        FlatButton(bar, "Lưu hóa đơn", self._submit, padx=22, pady=9).pack(side="right")
        box = tk.Frame(bar, bg=INPUT_BORDER, padx=1, pady=1)
        box.pack(side="right", padx=(0, 10))
        FlatButton(box, "Hủy", self.destroy, bg="white", hover="#EEF4FF", fg=NAVY, padx=22, pady=8).pack()
        self.bind("<Return>", lambda _e: self._submit())

    # ---- tính toán
    @staticmethod
    def _num(field):
        t = field.get().strip().replace(",", ".")
        try:
            v = float(t)
        except ValueError:
            return None
        return v if v >= 0 else None

    @staticmethod
    def _put(field, text, readonly):
        e = field.entry
        e.config(state="normal")
        field.set(text)
        if readonly:
            e.config(state="readonly", readonlybackground=READONLY_BG, fg="#5A6785")
            field.config(highlightbackground=SECTION_BG)
        else:
            e.config(readonlybackground="white", fg=TEXT)
            field.config(highlightbackground=INPUT_BORDER)

    def _room(self):
        return self.rooms.get(self.room_cb.get())

    def _checked(self):
        return [s for s, v in zip(self.services, self.svc_vars) if v.get()]

    def _readings(self):
        """(điện cũ, nước cũ, điện mới, nước mới) - None nếu ô chưa nhập / sai."""
        return self._num(self.old_d), self._num(self.old_n), self._num(self.new_d), self._num(self.new_n)

    def _recalc(self):
        room, thang = self._room(), parse_thang(self.thang.get())
        key = (room["MaPhong"] if room else None, thang)
        if room and thang and key != self._key:                   # đổi phòng / tháng -> nạp lại chỉ số cũ
            self._key = key
            dc, nc, self.first = meter_old(room["MaPhong"], thang)
            self._put(self.old_d, fmt_num(dc), readonly=not self.first)
            self._put(self.old_n, fmt_num(nc), readonly=not self.first)
            self.hint.config(text="Hóa đơn đầu tiên của phòng: có thể nhập chỉ số cũ (chỉ số đầu kỳ) nếu khác 0."
                             if self.first else "Chỉ số cũ lấy tự động từ hóa đơn tháng trước của phòng.")
        od, on, nd, nn = self._readings()
        su_d = max(nd - od, 0) if None not in (od, nd) else 0
        su_n = max(nn - on, 0) if None not in (on, nn) else 0
        if not room:
            return
        c = compute(room, self.dien, self.nuoc, su_d, su_n, self._checked())
        names = ", ".join(s["TenDV"] for s in self._checked())
        labels = {"phong": (f"Tiền phòng ({money(room['GiaThue'])}đ × {room['DangO']} SV)", c["TienPhong"]),
                  "dien": (f"Tiền điện ({fmt_num(su_d)} kWh × {money(self.dien)}đ)", c["TienDien"]),
                  "nuoc": (f"Tiền nước ({fmt_num(su_n)} m³ × {money(self.nuoc)}đ)", c["TienNuoc"]),
                  "khac": ("Dịch vụ khác" + (f" ({names} × {room['DangO']} SV)" if names else ""), c["TienKhac"])}
        for k, (text, val) in labels.items():
            self.cells[k][0].config(text=text)
            self.cells[k][1].config(text=f"{money(val)}đ")
        self.total_lb.config(text=f"{money(c['TongTien'])}đ")

    def _submit(self):
        room, thang = self._room(), parse_thang(self.thang.get())
        od, on, nd, nn = self._readings()
        err = None
        if not room:
            err = "Hãy chọn phòng."
        elif thang is None:
            err = "Tháng hóa đơn không hợp lệ (dạng MM/YYYY, ví dụ 11/2025)."
        elif od is None or on is None:
            err = "Chỉ số cũ phải là số không âm."
        elif nd is None or nn is None:
            err = "Hãy nhập số điện mới và số nước mới (số không âm)."
        elif nd < od:
            err = f"Số điện mới phải lớn hơn hoặc bằng số điện cũ ({fmt_num(od)})."
        elif nn < on:
            err = f"Số nước mới phải lớn hơn hoặc bằng số nước cũ ({fmt_num(on)})."
        elif db.query("SELECT 1 FROM HoaDon WHERE MaPhong=? AND Thang=?", (room["MaPhong"], thang), one=True):
            err = f"Phòng {room['TenPhong']} đã có hóa đơn tháng {thang[5:]}/{thang[:4]}."
        if err:
            self.msg.config(text=err)
            return
        c = compute(room, self.dien, self.nuoc, nd - od, nn - on, self._checked())
        self.result = dict(c, MaPhong=room["MaPhong"], TenPhong=room["TenPhong"], Thang=thang, SoDien=round(nd - od, 2),
                           SoNuoc=round(nn - on, 2), ChiSoDien=nd, ChiSoNuoc=nn)
        self.destroy()

    def show(self):
        self.update_idletasks()
        w, h = max(self.winfo_reqwidth(), self.W), self.winfo_reqheight()
        top = self.master.winfo_toplevel()
        x = max(0, min(top.winfo_rootx() + (top.winfo_width() - w) // 2, self.winfo_screenwidth() - w))
        y = max(0, min(top.winfo_rooty() + (top.winfo_height() - h) // 2, self.winfo_screenheight() - h - 60))
        self.geometry(f"{w}x{h}+{x}+{y}")
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        self.new_d.focus_entry()
        self.wait_window()
        return self.result


# ====================================================================== màn hình
class HoaDonScreen(tk.Frame):
    def __init__(self, master, user=None):
        super().__init__(master, bg=PAGE_BG)
        self.user = user or {}
        self.filter, self.sel, self.page_no = "Tất cả", None, 1       # filter: tên trạng thái trong DB hoặc "Tất cả"
        self.range = (None, None)                                       # kỳ hóa đơn đang lọc (từ ngày, đến ngày)
        self.rows, self.shown = [], []
        self.kw = tk.StringVar(master=self)              # main.goto() điền sẵn ô tìm kiếm qua biến này
        self.status_var = tk.StringVar(master=self, value=STATUS_FILTERS[0])
        self.type_var = tk.StringVar(master=self, value=TYPE_FILTERS[0])
        st = ttk.Style(self)
        st.configure("HDR.Treeview", rowheight=30, font=(FONT, 10), background="white", fieldbackground="white")
        st.configure("HDR.Treeview.Heading", font=(FONT, 10, "bold"))
        self._build()
        self.refresh()
        self.kw.trace_add("write", lambda *_: self._search_changed())

    # ---- dựng giao diện
    def _build(self):
        pad = dict(padx=40)
        head = tk.Frame(self, bg=PAGE_BG)
        head.pack(fill="x", pady=(30, 0), **pad)
        box = tk.Frame(head, bg=PAGE_BG)
        box.pack(side="left")
        tk.Label(box, text="Quản lý hóa đơn", bg=PAGE_BG, fg=NAVY, font=(FONT, 20, "bold")).pack(anchor="w")
        tk.Label(box, text="Theo dõi, quản lý và xuất hóa đơn cho sinh viên", bg=PAGE_BG, fg=MUTED,
                 font=(FONT, 10)).pack(anchor="w")
        SearchBox(head, self.kw, "Tìm theo mã hóa đơn, tên sinh viên, phòng...").pack(side="right", anchor="n")

        # --- 4 thẻ thống kê
        self.stats = tk.Frame(self, bg=PAGE_BG)
        self.stats.pack(fill="x", pady=(16, 0), **pad)
        for i in range(4):
            self.stats.columnconfigure(i, weight=1, uniform="s")
        self.v_total = self._stat(0, "file", "Tổng hóa đơn", NAVY, "#E3EEFF")
        self.v_paid = self._stat(1, "check", "Đã thanh toán", GREEN_FG, "#DDF3E6")
        self.v_unpaid = self._stat(2, "clock", "Chưa thanh toán", "#E58A12", "#FFF0D9")
        self.v_revenue = self._stat(3, "money", "Tổng doanh thu", NAVY, "#E3EEFF")

        # --- bộ lọc
        fc = Card(self)
        fc.config(height=102)
        fc.pack(fill="x", pady=(16, 0), **pad)
        row = tk.Frame(fc.inner, bg="white")
        row.pack(fill="both", expand=True, padx=20, pady=(10, 0))

        def group(title, width=None):
            g = tk.Frame(row, bg="white")
            g.pack(side="left", padx=(0, 20), anchor="n")
            tk.Label(g, text=title, bg="white", fg=NAVY, font=(FONT, 10, "bold")).pack(anchor="w", pady=(0, 4))
            return g

        g = group("Thời gian (kỳ hóa đơn)")
        line = tk.Frame(g, bg="white")
        line.pack()
        self.f_from, self.f_to = Field(line, placeholder="dd/mm/yyyy"), Field(line, placeholder="dd/mm/yyyy")
        for i, f in enumerate((self.f_from, self.f_to)):
            f.entry.config(width=11)
            f.pack(side="left")
            f.entry.bind("<Return>", lambda _e: (self.on_search(), "break")[1])
            if i == 0:
                tk.Label(line, text="  →  ", bg="white", fg=MUTED, font=(FONT, 11)).pack(side="left")
        for title, var, values in (("Trạng thái", self.status_var, STATUS_FILTERS),
                                   ("Loại hóa đơn", self.type_var, TYPE_FILTERS)):
            g = group(title)
            cb = ttk.Combobox(g, textvariable=var, values=values, state="readonly", font=(FONT, 10),
                              width=24 if var is self.type_var else 19)
            cb.pack(ipady=7)
            cb.bind("<<ComboboxSelected>>", lambda _e, c=cb: (c.selection_clear(), self._filters_changed()))
        btns = tk.Frame(row, bg="white")
        btns.pack(side="right", anchor="s", pady=(0, 14))
        IconButton(btns, "Tìm kiếm", "search", self.on_search, "primary").pack(side="left", padx=(0, 10))
        IconButton(btns, "Làm mới", "refresh", self.on_reset, "outline").pack(side="left")

        # --- thanh công cụ
        bar = tk.Frame(self, bg=PAGE_BG)
        bar.pack(fill="x", pady=(16, 0), **pad)
        IconButton(bar, "Tạo hóa đơn", "plus", self.on_add, "primary").pack(side="left", padx=(0, 10))
        IconButton(bar, "Xuất Excel", "sheet", self.export_excel, "outline").pack(side="left", padx=(0, 10))
        IconButton(bar, "Xuất PDF", "pdf", self.export_pdf, "outline").pack(side="left", padx=(0, 10))
        IconButton(bar, "In hóa đơn", "print", self.print_invoices, "outline").pack(side="left", padx=(0, 10))
        IconButton(bar, "Nhắc nợ", "bell", self.on_remind, "outline").pack(side="left")
        IconButton(bar, "Xem báo cáo", "chart", self.on_report, "outline").pack(side="right")

        # --- bảng + phân trang
        card = Card(self)
        card.pack(fill="both", expand=True, padx=40, pady=(14, 30))
        foot = tk.Frame(card.inner, bg="white")
        foot.pack(side="bottom", fill="x")
        tk.Frame(foot, bg=LINE, height=1).pack(fill="x")
        frow = tk.Frame(foot, bg="white")
        frow.pack(fill="x", padx=16, pady=8)
        self.foot_l = tk.Label(frow, bg="white", fg=MUTED, font=(FONT, 9))
        self.foot_l.pack(side="left")
        self.pager = PageBar(frow, self.go_page)
        self.pager.pack(side="right")
        self.table = InvoiceTable(card.inner, self._on_pick, self.on_detail, self._row_menu)
        self.table.pack(fill="both", expand=True)

    def _stat(self, col, icon, title, color, tint):
        c = Card(self.stats)
        c.config(height=92)
        c.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else 16, 0))
        cv = tk.Canvas(c.inner, width=64, height=64, bg="white", highlightthickness=0)
        cv.pack(side="left", padx=(16, 12), pady=12)
        cv.create_oval(2, 2, 62, 62, fill=tint, outline=tint)
        kw = dict(fill=color, width=3, capstyle="round", joinstyle="round")
        if icon == "file":
            cv.create_rectangle(22, 17, 42, 47, outline=color, width=3)
            cv.create_line(27, 28, 37, 28, **kw)
            cv.create_line(27, 36, 37, 36, **kw)
        elif icon == "check":
            cv.create_oval(16, 16, 48, 48, fill=color, outline=color)
            cv.create_line(24, 33, 30, 39, 41, 26, fill="white", width=4, capstyle="round", joinstyle="round")
        elif icon == "clock":
            cv.create_oval(16, 16, 48, 48, outline=color, width=3)
            cv.create_line(32, 24, 32, 33, 39, 37, **kw)
        else:
            cv.create_text(32, 32, text="₫", font=(FONT, 22, "bold"), fill=color)
        box = tk.Frame(c.inner, bg="white")
        box.pack(side="left", fill="both", expand=True)
        tk.Label(box, text=title, bg="white", fg=MUTED, font=(FONT, 10)).pack(anchor="w", pady=(18, 0))
        val = tk.Label(box, text="0", bg="white", fg=color, font=(FONT, 21, "bold"))
        val.pack(anchor="w")
        return val

    # ---- dữ liệu / bộ lọc
    def refresh(self):
        self.rows = load_invoices()
        self.apply()

    def _in_range(self):
        d1, d2 = self.range
        return [r for r in self.rows if (not d1 or month_end(r["Thang"]) >= d1)
                and (not d2 or month_start(r["Thang"]) <= d2)]

    def set_filter(self, name):
        """Chọn sẵn bộ lọc trạng thái (nhận cả tên trong DB 'Chưa thu' lẫn chữ hiển thị 'Chưa thanh toán')."""
        name = LABEL_TO_STATE.get(name, name)
        if name == "Tất cả" or name in STATE_LABEL:
            self.filter = name
            self.status_var.set("Tất cả" if name == "Tất cả" else STATE_LABEL[name])
            self.page_no = 1
            self.apply()

    def _filters_changed(self):
        self.filter = LABEL_TO_STATE.get(self.status_var.get(), "Tất cả")
        self.page_no = 1
        self.apply()

    def _search_changed(self):
        self.page_no = 1
        self.apply()

    @staticmethod
    def _parse_day(field):
        t = field.get().strip()
        if not t:
            return None
        return datetime.strptime(t, "%d/%m/%Y").date()

    def on_search(self):
        try:
            d1, d2 = self._parse_day(self.f_from), self._parse_day(self.f_to)
        except ValueError:
            return error("Ngày không hợp lệ. Hãy nhập theo dạng dd/mm/yyyy (ví dụ 01/11/2026).")
        if d1 and d2 and d1 > d2:
            return error("'Từ ngày' phải trước hoặc bằng 'Đến ngày'.")
        self.range, self.page_no = (d1, d2), 1
        self.apply()

    def on_reset(self):
        self.f_from.clear()
        self.f_to.clear()
        self.range, self.filter, self.page_no = (None, None), "Tất cả", 1
        self.status_var.set(STATUS_FILTERS[0])
        self.type_var.set(TYPE_FILTERS[0])
        self.kw.set("")
        self.refresh()

    def go_page(self, n):
        self.page_no = n
        self.apply()

    def apply(self):
        base = self._in_range()                                         # thống kê tính theo kỳ hóa đơn đang lọc
        paid = [r for r in base if r["Tinh"] == "Đã thu"]
        self.v_total.config(text=str(len(base)))
        self.v_paid.config(text=str(len(paid)))
        self.v_unpaid.config(text=str(len(base) - len(paid)))
        self.v_revenue.config(text=f"{money(sum(r['DaThu'] for r in base))}đ")
        kw, typ = fold(self.kw.get().strip()), self.type_var.get()
        self.shown = [r for r in base if (self.filter == "Tất cả" or r["Tinh"] == self.filter)
                      and (typ == "Tất cả" or r["LoaiPhi"] == typ) and (not kw or kw in r["_hay"])]
        pages = max(1, math.ceil(len(self.shown) / PAGE_SIZE))
        if self.sel is not None:                                         # giữ trang chứa hóa đơn đang chọn (vd. vừa lập)
            idx = next((i for i, r in enumerate(self.shown) if r["MaHDon"] == self.sel), None)
            if idx is not None and self._want_sel:
                self.page_no = idx // PAGE_SIZE + 1
        self._want_sel = False
        self.page_no = min(max(self.page_no, 1), pages)
        start = (self.page_no - 1) * PAGE_SIZE
        chunk = self.shown[start:start + PAGE_SIZE]
        self.table.selected = self.sel
        self.table.load(chunk)
        self.pager.set(self.page_no, pages)
        n = len(self.shown)
        self.foot_l.config(text=f"Hiển thị {start + 1} - {start + len(chunk)} / {n} hóa đơn" if n
                           else "Không có hóa đơn nào phù hợp.")

    _want_sel = False

    def _on_pick(self, ma):
        self.sel = ma

    def _selected_row(self):
        return next((r for r in self.rows if r["MaHDon"] == self.sel), None)

    def _need(self):
        r = self._selected_row()
        if r is None:
            messagebox.showwarning("Thông báo", "Vui lòng chọn một hóa đơn trong bảng.")
        return r

    # ---- menu '···' của từng dòng
    def _row_menu(self, e):
        r = self._selected_row()
        if not r:
            return
        m = tk.Menu(self, tearoff=0, font=(FONT, 10))
        m.add_command(label="Xem biên lai", command=self.on_detail)
        m.add_command(label="Thu tiền", command=lambda: self.pay(r), state="normal" if r["CongNo"] > 0 else "disabled")
        m.add_command(label="Lưu biên lai (.txt)", command=lambda: self.save_receipt(r, payments_of(r["MaHDon"])))
        m.add_separator()
        m.add_command(label="Xóa hóa đơn", command=self.on_delete, foreground="#B42318")
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    # ---- lập hóa đơn
    def on_add(self):
        rooms = [p for p in db.danh_sach_phong() if p["DangO"] > 0]
        if not rooms:
            return error("Chưa có phòng nào có sinh viên đang ở.")
        dien, nuoc = rate("Điện"), rate("Nước")
        if dien is None or nuoc is None:
            return error("Cần khai báo đơn giá 'Điện' và 'Nước' ở mục Dịch vụ.")
        d = InvoiceDialog(self, rooms, dien, nuoc, monthly_services()).show()
        if not d:
            return
        try:
            new_id = db.execute("""INSERT INTO HoaDon(MaPhong,Thang,TienPhong,SoDien,SoNuoc,TienDien,TienNuoc,TongTien,
                                                      NgayLap,TienKhac,ChiSoDien,ChiSoNuoc)
                                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                                (d["MaPhong"], d["Thang"], d["TienPhong"], d["SoDien"], d["SoNuoc"], d["TienDien"],
                                 d["TienNuoc"], d["TongTien"], dmy(date.today()), d["TienKhac"], d["ChiSoDien"],
                                 d["ChiSoNuoc"]))
        except sqlite3.IntegrityError:
            return error("Phòng này đã có hóa đơn trong tháng đó.")
        db.ghi_nhat_ky("hoadon", f"Lập hóa đơn tháng {d['Thang'][5:]} – phòng **{d['TenPhong']}**")
        self.f_from.clear()
        self.f_to.clear()
        self.range, self.filter, self.sel, self._want_sel = (None, None), "Tất cả", new_id, True
        self.status_var.set(STATUS_FILTERS[0])
        self.type_var.set(TYPE_FILTERS[0])
        self.kw.set("")
        self.refresh()

    # ---- thu tiền
    def on_pay(self):
        r = self._need()
        if r:
            self.pay(r)

    def pay(self, r):
        con_no = r["CongNo"]
        if con_no <= 0:
            return messagebox.showinfo("Thông báo", "Hóa đơn này đã thu đủ.")

        def check(v):
            raw = v["SoTien"].replace(".", "").replace(",", "").replace(" ", "")
            if not (raw.isascii() and raw.isdigit()):
                return None, ("SoTien", "Số tiền phải là số nguyên (đồng).")
            so = int(raw)
            if not 0 < so <= con_no:
                return None, ("SoTien", f"Số tiền phải từ 1 đến {money(con_no)} đ.")
            return dict(v, SoTien=so), None

        fields = [{"key": "SoTien", "label": f"Số tiền thu (còn nợ {money(con_no)} đ)", "ph": "Số tiền",
                   "required": True, "span": 2},
                  {"key": "HinhThuc", "label": "Hình thức", "kind": "combo", "opts": HINH_THUC, "span": 2},
                  {"key": "GhiChu", "label": "Ghi chú (mã giao dịch, người nộp…)", "ph": "Không bắt buộc",
                   "span": 2}]
        d = form_modal(self, f"Thu tiền - phòng {r['TenPhong']} ({r['Thang']})", fields,
                       {"SoTien": str(con_no), "HinhThuc": HINH_THUC[0]}, validate=check, width=540,
                       submit_text="Thu tiền")
        if not d:
            return
        so = d["SoTien"]
        da_thu = r["DaThu"] + so
        tt = "Đã thu" if da_thu >= r["TongTien"] else "Thu một phần"
        ngay = dmy(date.today())
        db.execute("INSERT INTO ThanhToan(MaHDon,SoTien,HinhThuc,GhiChu,Ngay,NguoiThu) VALUES(?,?,?,?,?,?)",
                   (r["MaHDon"], so, d["HinhThuc"], d["GhiChu"], ngay, self.user.get("HoTen", "")))
        db.execute("UPDATE HoaDon SET DaThu=?, TrangThai=?, NgayThu=? WHERE MaHDon=?", (da_thu, tt, ngay, r["MaHDon"]))
        db.ghi_nhat_ky("thu", f"Thu **{money(so)} đ** – phòng {r['TenPhong']}")
        self.refresh()
        messagebox.showinfo("Thành công", f"Đã thu {money(so)} đ ({d['HinhThuc']}). "
                                          + ("Hóa đơn đã thu đủ." if tt == "Đã thu" else f"Còn nợ {money(con_no - so)} đ."))

    # ---- biên lai / chi tiết
    def on_detail(self):
        r = self._need()
        if not r:
            return
        pays = payments_of(r["MaHDon"])
        fg, bg = STATE_STYLE[r["Tinh"]]
        n = max(1, r["SoNguoi"])
        win = tk.Toplevel(self)
        win.title(f"Hóa đơn {r['MaHD']}")
        win.configure(bg="white")
        win.transient(self.winfo_toplevel())
        win.resizable(False, False)
        top = tk.Frame(win, bg=PRIMARY)
        top.pack(fill="x")
        tk.Label(top, text=f"Phòng {r['TenPhong']} · Tháng {r['Thang']}", bg=PRIMARY, fg="white",
                 font=(FONT, 15, "bold")).pack(anchor="w", padx=20, pady=(16, 0))
        tk.Label(top, text=f"{r['MaHD']} · lập {r['NgayLap']} · hạn thanh toán {r['HanTT']}", bg=PRIMARY, fg="#CFE0FF",
                 font=(FONT, 10)).pack(anchor="w", padx=20, pady=(0, 14))
        body = tk.Frame(win, bg="white")
        body.pack(fill="x", padx=20, pady=12)
        items = [("Sinh viên", r["SVAll"] or "—"), ("Tiền phòng", f"{money(r['TienPhong'])} đ"),
                 ("Tiền điện", f"{money(r['TienDien'])} đ ({fmt_num(r['SoDien'])} kWh)"),
                 ("Tiền nước", f"{money(r['TienNuoc'])} đ ({fmt_num(r['SoNuoc'])} m³)"),
                 ("Dịch vụ khác", f"{money(r['TienKhac'])} đ"), ("Tổng cộng", f"{money(r['TongTien'])} đ"),
                 ("Đã thu", f"{money(r['DaThu'])} đ"), ("Còn nợ", f"{money(r['CongNo'])} đ"),
                 (f"Mỗi người ({n} SV)", f"{money(round(r['TongTien'] / n))} đ"), ("Trạng thái", r["TinhText"])]
        for i, (k, v) in enumerate(items):
            tk.Label(body, text=k, bg="white", fg=MUTED, font=(FONT, 10), width=18, anchor="w").grid(row=i, column=0, pady=3)
            if k == "Trạng thái":
                tk.Label(body, text=f" {v} ", bg=bg, fg=fg, font=(FONT, 10, "bold")).grid(row=i, column=1, sticky="w")
            else:
                tk.Label(body, text=v, bg="white", fg=TEXT, font=(FONT, 10, "bold"), wraplength=330,
                         justify="left").grid(row=i, column=1, sticky="w")
        tk.Label(win, text="Lịch sử thanh toán", bg="white", fg=NAVY, font=(FONT, 11, "bold")).pack(anchor="w", padx=20)
        hist = tk.Frame(win, bg="white")
        hist.pack(fill="x", padx=20, pady=(2, 8))
        if not pays:
            tk.Label(hist, text="Chưa có lần thanh toán nào.", bg="white", fg=MUTED, font=(FONT, 10)).pack(anchor="w")
        for p in pays:
            txt = f"{p['Ngay']}  ·  {money(p['SoTien'])} đ  ·  {p['HinhThuc']}" + (f"  ·  {p['GhiChu']}" if p["GhiChu"] else "")
            tk.Label(hist, text=txt, bg="white", fg=TEXT, font=(FONT, 10)).pack(anchor="w")
        bar = tk.Frame(win, bg="white")
        bar.pack(fill="x", padx=20, pady=(4, 16))
        if r["CongNo"] > 0:
            FlatButton(bar, "Thu tiền", lambda: (win.destroy(), self.pay(r)), padx=16, pady=8).pack(side="left")
        FlatButton(bar, "Lưu biên lai", lambda: self.save_receipt(r, pays), bg="white", hover=SEL_BG, fg=NAVY, padx=14,
                   pady=7, highlightthickness=1, highlightbackground=BORDER).pack(side="left", padx=8)
        FlatButton(bar, "Đóng", win.destroy, bg="white", hover=SEL_BG, fg=NAVY, padx=14, pady=7,
                   highlightthickness=1, highlightbackground=BORDER).pack(side="right")
        win.bind("<Escape>", lambda _e: win.destroy())
        try:
            win.wait_visibility()
            win.grab_set()
        except tk.TclError:
            pass

    def save_receipt(self, r, pays):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Văn bản", "*.txt")],
                                            initialfile=f"bien_lai_{r['TenPhong']}_{r['Thang']}.txt")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(receipt_text(r, pays))
        except OSError as e:
            return error(f"Không ghi được file: {e}")
        messagebox.showinfo("Thành công", f"Đã lưu biên lai:\n{path}")

    # ---- nhắc nợ: đăng thông báo để sinh viên thấy trên trang chủ
    def on_remind(self):
        debtors = [r for r in self._in_range() if r["CongNo"] > 0]
        if not debtors:
            return messagebox.showinfo("Thông báo", "Không có phòng nào còn nợ.")
        over = [r for r in debtors if r["Tinh"] == "Quá hạn"]
        use = over or debtors
        label = "quá hạn" if over else "còn nợ"
        lst = "; ".join(f"{r['TenPhong']} ({money(r['CongNo'])} đ)" for r in use)
        if not messagebox.askyesno("Nhắc nợ", f"Đăng thông báo nhắc {len(use)} phòng {label}?\n\n{lst}"):
            return
        ngay = dmy(date.today())
        title = f"Nhắc đóng tiền nội trú ({label})"
        if db.query("SELECT 1 FROM ThongBao WHERE TieuDe=? AND Ngay=?", (title, ngay), one=True):
            return messagebox.showinfo("Thông báo", "Hôm nay đã đăng thông báo nhắc nợ rồi.")
        db.execute("INSERT INTO ThongBao(TieuDe,NoiDung,Ngay) VALUES(?,?,?)",
                   (title, f"Các phòng {label}: {lst}. Vui lòng nộp tại Ban quản lý ký túc xá.", ngay))
        messagebox.showinfo("Thành công", "Đã đăng thông báo, sinh viên sẽ thấy ở trang chủ.")

    # ---- xóa
    def on_delete(self):
        r = self._need()
        if not r:
            return
        extra = f"\n\nHóa đơn đã thu {money(r['DaThu'])} đ, lịch sử thanh toán cũng bị xóa." if r["DaThu"] else ""
        if messagebox.askyesno("Xác nhận xóa", f"Xóa hóa đơn {r['MaHD']} (phòng {r['TenPhong']}, {r['Thang']})?{extra}"):
            db.execute("DELETE FROM ThanhToan WHERE MaHDon=?", (r["MaHDon"],))
            db.execute("DELETE FROM HoaDon WHERE MaHDon=?", (r["MaHDon"],))
            db.ghi_nhat_ky("hoadon", f"Xóa hóa đơn tháng {r['Thang'][5:]} – phòng **{r['TenPhong']}**")
            self.sel = None
            self.refresh()

    # ---- xuất Excel / PDF / in
    def export_excel(self):
        if not self.shown:
            return messagebox.showinfo("Thông báo", "Không có dữ liệu để xuất.")
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                            initialfile=f"hoa_don_{date.today():%Y%m%d}.xlsx")
        if not path:
            return
        heads = ["Mã hóa đơn", "Sinh viên trong phòng", "Phòng", "Tháng", "Loại phí", "Tiền phòng", "Tiền điện",
                 "Tiền nước", "Dịch vụ khác", "Tổng tiền", "Đã thu", "Còn nợ", "Ngày lập", "Hạn thanh toán",
                 "Trạng thái"]
        keys = ["MaHD", "SVAll", "TenPhong", "Thang", "LoaiPhi", "TienPhong", "TienDien", "TienNuoc", "TienKhac",
                "TongTien", "DaThu", "CongNo", "NgayLap", "HanTT", "TinhText"]
        try:
            xlsx_io.write_xlsx(path, heads, [[r[k] for k in keys] for r in self.shown],
                               widths=[13, 34, 8, 10, 28, 13, 12, 12, 13, 13, 12, 12, 12, 14, 22],
                               sheet_name="Hóa đơn")
        except OSError as e:
            return error(f"Không ghi được file: {e}")
        messagebox.showinfo("Thành công", f"Đã xuất {len(self.shown)} hóa đơn:\n{path}")

    def _printable(self):
        """Hóa đơn đang chọn; chưa chọn thì tất cả hóa đơn đang lọc (hỏi lại nếu nhiều)."""
        r = self._selected_row()
        if r:
            return [r]
        if not self.shown:
            messagebox.showinfo("Thông báo", "Không có hóa đơn nào để in.")
            return []
        if len(self.shown) > 1 and not messagebox.askyesno(
                "Xác nhận", f"Chưa chọn hóa đơn nào. In / xuất tất cả {len(self.shown)} hóa đơn đang lọc?"):
            return []
        return self.shown

    def _open_html(self, rows, banner):
        if not rows:
            return
        with tempfile.NamedTemporaryFile("w", suffix=".html", prefix="hoadon_", delete=False, encoding="utf-8") as f:
            f.write(invoices_html(rows, True, banner))
            path = f.name
        webbrowser.open(Path(path).as_uri())

    def export_pdf(self):
        rows = self._printable()
        if rows:
            messagebox.showinfo("Xuất PDF", "Trình duyệt sẽ mở trang in: ở mục 'Máy in' hãy chọn "
                                            "'Lưu dưới dạng PDF' (Save as PDF) rồi bấm Lưu.")
            self._open_html(rows, "Chọn 'Lưu dưới dạng PDF' ở mục Máy in để lưu file PDF.")

    def print_invoices(self):
        self._open_html(self._printable(), "")

    # ---- báo cáo
    def on_report(self):
        if not self.rows:
            return messagebox.showinfo("Thông báo", "Chưa có hóa đơn nào để lập báo cáo.")
        win = tk.Toplevel(self)
        win.title("Báo cáo hóa đơn theo tháng")
        win.configure(bg="white")
        win.transient(self.winfo_toplevel())
        tk.Label(win, text="Báo cáo hóa đơn theo tháng", bg="white", fg=NAVY, font=(FONT, 15, "bold")).pack(
            anchor="w", padx=20, pady=(16, 2))
        tk.Label(win, text="Số liệu cùng nguồn với Trang chủ và Thống kê (doanh thu = tiền đã thu theo tháng hóa đơn).",
                 bg="white", fg=MUTED, font=(FONT, 9)).pack(anchor="w", padx=20)
        cols = [("Thang", "Tháng", 80, "center"), ("SoHD", "Số HĐ", 70, "center"), ("Tong", "Phải thu", 120, "e"),
                ("Thu", "Đã thu (doanh thu)", 140, "e"), ("No", "Còn nợ", 120, "e"), ("Ty", "Tỷ lệ thu", 80, "center")]
        tv = ttk.Treeview(win, columns=[c[0] for c in cols], show="headings", height=min(12, len({r["Thang"] for r in self.rows}) + 1),
                          style="HDR.Treeview")
        for key, text, w, anchor in cols:
            tv.heading(key, text=text)
            tv.column(key, width=w, anchor=anchor)
        by = {}
        for r in self.rows:
            a = by.setdefault(r["Thang"], [0, 0, 0])
            a[0] += 1
            a[1] += r["TongTien"]
            a[2] += r["DaThu"]
        tot = [0, 0, 0]
        for thang in sorted(by, reverse=True):
            n, t, p = by[thang]
            tot = [tot[0] + n, tot[1] + t, tot[2] + p]
            tv.insert("", "end", values=(f"{thang[5:]}/{thang[:4]}", n, f"{money(t)}đ", f"{money(p)}đ", f"{money(t - p)}đ",
                                         f"{round(p * 100 / t) if t else 0}%"))
        tv.insert("", "end", values=("TỔNG", tot[0], f"{money(tot[1])}đ", f"{money(tot[2])}đ", f"{money(tot[1] - tot[2])}đ",
                                     f"{round(tot[2] * 100 / tot[1]) if tot[1] else 0}%"), tags=("sum",))
        tv.tag_configure("sum", background=SEL_BG, font=(FONT, 10, "bold"))
        tv.pack(padx=20, pady=12)
        debt = sorted((r for r in self.rows if r["CongNo"] > 0), key=lambda r: -r["CongNo"])[:5]
        if debt:
            tk.Label(win, text="Phòng còn nợ nhiều nhất", bg="white", fg=NAVY, font=(FONT, 11, "bold")).pack(anchor="w", padx=20)
            for r in debt:
                tk.Label(win, text=f"Phòng {r['TenPhong']} · tháng {r['Thang'][5:]}/{r['Thang'][:4]} · nợ {money(r['CongNo'])}đ"
                                   f" ({r['TinhText'].lower()})", bg="white", fg=TEXT, font=(FONT, 10)).pack(anchor="w", padx=20)
        FlatButton(win, "Đóng", win.destroy, bg="white", hover=SEL_BG, fg=NAVY, padx=18, pady=7, highlightthickness=1,
                   highlightbackground=BORDER).pack(anchor="e", padx=20, pady=14)
        win.bind("<Escape>", lambda _e: win.destroy())
