from datetime import date
from tkinter import messagebox
import database as db
from screens.base import CrudScreen, error, form_dialog, parse_date, pick_id, valid_date


class HopDongScreen(CrudScreen):
    title = "Hợp đồng thuê phòng"
    show_edit = False
    columns = [("MaHD", "Mã HĐ", 60), ("HoTen", "Sinh viên", 170), ("TenPhong", "Phòng", 80),
               ("NgayBatDau", "Bắt đầu", 100), ("NgayKetThuc", "Kết thúc", 100), ("TrangThai", "Trạng thái", 100)]
    extra = [("⏹ Kết thúc hợp đồng", "ket_thuc")]

    def rows(self, kw):
        like = f"%{kw}%"
        return db.query("""
            SELECT h.MaHD, s.HoTen, p.TenPhong, h.NgayBatDau, h.NgayKetThuc, h.TrangThai
            FROM HopDong h JOIN SinhVien s ON s.MaSV=h.MaSV JOIN Phong p ON p.MaPhong=h.MaPhong
            WHERE s.HoTen LIKE ? OR p.TenPhong LIKE ? OR h.TrangThai LIKE ?
            ORDER BY h.MaHD DESC""", (like,) * 3)

    def add(self):
        svs = [f"{r['MaSV']} - {r['HoTen']}" for r in db.query(
            "SELECT MaSV,HoTen FROM SinhVien WHERE MaSV NOT IN "
            "(SELECT MaSV FROM HopDong WHERE TrangThai='Đang thuê') ORDER BY HoTen")]
        phongs = [f"{p['MaPhong']} - {p['TenPhong']} (còn {p['SoGiuong'] - p['DangO']} chỗ)"
                  for p in db.danh_sach_phong() if p["TinhTrang"] in ("Trống", "Còn chỗ")]
        if not svs:
            return error("Không có sinh viên nào chưa có phòng.")
        if not phongs:
            return error("Hiện không còn phòng trống.")
        fields = [("SV", "Sinh viên", "combo", svs), ("Phong", "Phòng", "combo", phongs),
                  ("NgayBatDau", "Ngày bắt đầu (dd/mm/yyyy)", "entry", None),
                  ("NgayKetThuc", "Ngày kết thúc (dd/mm/yyyy)", "entry", None)]
        d = form_dialog(self, "Đăng ký phòng", fields,
                        {"NgayBatDau": date.today().strftime("%d/%m/%Y")})
        if not d:
            return
        if not (valid_date(d["NgayBatDau"]) and valid_date(d["NgayKetThuc"])):
            return error("Ngày phải có dạng dd/mm/yyyy.")
        if parse_date(d["NgayKetThuc"]) <= parse_date(d["NgayBatDau"]):
            return error("Ngày kết thúc phải sau ngày bắt đầu.")
        db.execute("INSERT INTO HopDong(MaSV,MaPhong,NgayBatDau,NgayKetThuc) VALUES(?,?,?,?)",
                   (pick_id(d["SV"]), pick_id(d["Phong"]), d["NgayBatDau"], d["NgayKetThuc"]))

    def ket_thuc(self, id_):
        row = db.query("SELECT TrangThai FROM HopDong WHERE MaHD=?", (id_,), one=True)
        if row["TrangThai"] != "Đang thuê":
            return messagebox.showinfo("Thông báo", "Hợp đồng này đã kết thúc.")
        if messagebox.askyesno("Xác nhận", "Kết thúc hợp đồng và trả phòng?"):
            db.execute("UPDATE HopDong SET TrangThai='Đã kết thúc', NgayKetThuc=? WHERE MaHD=?",
                       (date.today().strftime("%d/%m/%Y"), id_))

    def delete(self, id_):
        db.execute("DELETE FROM HopDong WHERE MaHD=?", (id_,))
