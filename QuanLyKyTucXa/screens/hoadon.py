from datetime import date, datetime
from tkinter import simpledialog
import database as db
from screens.base import CrudScreen, error, form_dialog, money, pick_id


def rate(name):
    r = db.query("SELECT DonGia FROM DichVu WHERE TenDV=?", (name,), one=True)
    return r["DonGia"] if r else None


class HoaDonScreen(CrudScreen):
    title = "Hóa đơn & công nợ"
    show_edit = False
    columns = [("MaHDon", "Mã", 50), ("TenPhong", "Phòng", 70), ("Thang", "Tháng", 80),
               ("TienPhong", "Tiền phòng", 90), ("TienDien", "Tiền điện", 80), ("TienNuoc", "Tiền nước", 80),
               ("TongTien", "Tổng", 90), ("DaThu", "Đã thu", 90), ("CongNo", "Còn nợ", 90),
               ("TrangThai", "Trạng thái", 100)]
    extra = [("💵 Thu tiền", "thu_tien")]

    def rows(self, kw):
        like = f"%{kw}%"
        out = []
        for r in db.query("""
                SELECT h.*, p.TenPhong FROM HoaDon h JOIN Phong p ON p.MaPhong=h.MaPhong
                WHERE p.TenPhong LIKE ? OR h.Thang LIKE ? OR h.TrangThai LIKE ?
                ORDER BY h.Thang DESC, p.TenPhong""", (like,) * 3):
            d = dict(r)
            d["CongNo"] = d["TongTien"] - d["DaThu"]
            for k in ("TienPhong", "TienDien", "TienNuoc", "TongTien", "DaThu", "CongNo"):
                d[k] = money(d[k])
            out.append(d)
        return out

    def add(self):
        phongs = [p for p in db.danh_sach_phong() if p["DangO"] > 0]
        if not phongs:
            return error("Chưa có phòng nào có sinh viên đang ở.")
        dien, nuoc = rate("Điện"), rate("Nước")
        if dien is None or nuoc is None:
            return error("Cần khai báo đơn giá 'Điện' và 'Nước' ở mục Dịch vụ.")
        fields = [("Phong", "Phòng", "combo", [f"{p['MaPhong']} - {p['TenPhong']}" for p in phongs]),
                  ("Thang", "Tháng (YYYY-MM)", "entry", None),
                  ("SoDien", "Số điện (kWh)", "entry", None), ("SoNuoc", "Số nước (m³)", "entry", None)]
        d = form_dialog(self, "Lập hóa đơn", fields,
                        {"Thang": date.today().strftime("%Y-%m"), "SoDien": "0", "SoNuoc": "0"})
        if not d:
            return
        try:
            datetime.strptime(d["Thang"], "%Y-%m")
            so_dien, so_nuoc = float(d["SoDien"]), float(d["SoNuoc"])
            if so_dien < 0 or so_nuoc < 0:
                raise ValueError
        except ValueError:
            return error("Tháng phải có dạng YYYY-MM; số điện, số nước phải là số không âm.")
        ma = pick_id(d["Phong"])
        p = next(x for x in phongs if x["MaPhong"] == ma)
        tien_phong = p["GiaThue"] * p["DangO"]
        tien_dien, tien_nuoc = round(so_dien * dien), round(so_nuoc * nuoc)
        try:
            db.execute("""INSERT INTO HoaDon(MaPhong,Thang,TienPhong,SoDien,SoNuoc,TienDien,TienNuoc,TongTien)
                          VALUES(?,?,?,?,?,?,?,?)""",
                       (ma, d["Thang"], tien_phong, so_dien, so_nuoc, tien_dien, tien_nuoc,
                        tien_phong + tien_dien + tien_nuoc))
        except Exception:
            error("Phòng này đã có hóa đơn trong tháng đó.")

    def thu_tien(self, id_):
        r = db.query("SELECT TongTien, DaThu FROM HoaDon WHERE MaHDon=?", (id_,), one=True)
        con_no = r["TongTien"] - r["DaThu"]
        if con_no <= 0:
            return error("Hóa đơn này đã thu đủ.")
        so = simpledialog.askinteger("Thu tiền", f"Còn nợ {money(con_no)} đ. Số tiền thu:",
                                     initialvalue=con_no, minvalue=1, maxvalue=con_no, parent=self)
        if so:
            da_thu = r["DaThu"] + so
            tt = "Đã thu" if da_thu >= r["TongTien"] else "Thu một phần"
            db.execute("UPDATE HoaDon SET DaThu=?, TrangThai=?, NgayThu=? WHERE MaHDon=?",
                       (da_thu, tt, date.today().strftime("%d/%m/%Y"), id_))

    def delete(self, id_):
        db.execute("DELETE FROM HoaDon WHERE MaHDon=?", (id_,))
