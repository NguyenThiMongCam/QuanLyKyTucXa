import database as db
from screens.base import CrudScreen, error, form_dialog, valid_date

FIELDS = [("HoTen", "Họ và tên", "entry", None),
          ("NgaySinh", "Ngày sinh (dd/mm/yyyy)", "entry", None),
          ("GioiTinh", "Giới tính", "combo", ["Nam", "Nữ"]),
          ("Lop", "Lớp", "entry", None),
          ("SDT", "Số điện thoại", "entry", None),
          ("QueQuan", "Quê quán", "entry", None)]


def validate(d):
    if not d["HoTen"]:
        return "Họ tên không được để trống."
    if d["NgaySinh"] and not valid_date(d["NgaySinh"]):
        return "Ngày sinh phải có dạng dd/mm/yyyy."
    if d["SDT"] and not (d["SDT"].isdigit() and 9 <= len(d["SDT"]) <= 11):
        return "Số điện thoại phải gồm 9-11 chữ số."
    return None


class SinhVienScreen(CrudScreen):
    title = "Quản lý sinh viên"
    columns = [("MaSV", "Mã SV", 60), ("HoTen", "Họ và tên", 170), ("NgaySinh", "Ngày sinh", 90),
               ("GioiTinh", "Giới tính", 70), ("Lop", "Lớp", 90), ("SDT", "SĐT", 100),
               ("QueQuan", "Quê quán", 130), ("Phong", "Phòng đang ở", 90)]

    def rows(self, kw):
        like = f"%{kw}%"
        return db.query("""
            SELECT s.*, COALESCE((SELECT p.TenPhong FROM HopDong h JOIN Phong p ON p.MaPhong=h.MaPhong
                   WHERE h.MaSV=s.MaSV AND h.TrangThai='Đang thuê' LIMIT 1), '') AS Phong
            FROM SinhVien s
            WHERE CAST(s.MaSV AS TEXT) LIKE ? OR s.HoTen LIKE ? OR s.Lop LIKE ? OR s.SDT LIKE ?
            ORDER BY s.MaSV""", (like,) * 4)

    def add(self):
        d = form_dialog(self, "Thêm sinh viên", FIELDS)
        if not d:
            return
        err = validate(d)
        if err:
            return error(err)
        db.execute("INSERT INTO SinhVien(HoTen,NgaySinh,GioiTinh,Lop,SDT,QueQuan) VALUES(?,?,?,?,?,?)",
                   tuple(d[k] for k in ("HoTen", "NgaySinh", "GioiTinh", "Lop", "SDT", "QueQuan")))

    def edit(self, id_):
        cur = dict(db.query("SELECT * FROM SinhVien WHERE MaSV=?", (id_,), one=True))
        d = form_dialog(self, "Sửa thông tin sinh viên", FIELDS, cur)
        if not d:
            return
        err = validate(d)
        if err:
            return error(err)
        db.execute("UPDATE SinhVien SET HoTen=?,NgaySinh=?,GioiTinh=?,Lop=?,SDT=?,QueQuan=? WHERE MaSV=?",
                   tuple(d[k] for k in ("HoTen", "NgaySinh", "GioiTinh", "Lop", "SDT", "QueQuan")) + (id_,))

    def delete(self, id_):
        db.execute("DELETE FROM SinhVien WHERE MaSV=?", (id_,))
