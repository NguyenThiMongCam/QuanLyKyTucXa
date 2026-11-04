import database as db
from screens.base import CrudScreen, error, form_dialog


class NhanVienScreen(CrudScreen):
    title = "Tài khoản nhân viên"
    columns = [("MaNV", "Mã", 50), ("TenDangNhap", "Tên đăng nhập", 160), ("HoTen", "Họ tên", 200), ("VaiTro", "Vai trò", 100)]

    def rows(self, kw):
        like = f"%{kw}%"
        return db.query("SELECT MaNV,TenDangNhap,HoTen,VaiTro FROM NhanVien WHERE TenDangNhap LIKE ? OR HoTen LIKE ? ORDER BY MaNV", (like, like))

    def _fields(self, editing):
        return [("TenDangNhap", "Tên đăng nhập", "entry", None), ("HoTen", "Họ tên", "entry", None),
                ("VaiTro", "Vai trò", "combo", ["nhanvien", "admin"]),
                ("MatKhau", "Mật khẩu" + (" (để trống = giữ nguyên)" if editing else ""), "password", None)]

    def add(self):
        d = form_dialog(self, "Thêm nhân viên", self._fields(False))
        if not d:
            return
        if not (d["TenDangNhap"] and d["HoTen"]) or len(d["MatKhau"]) < 6:
            return error("Nhập đủ thông tin; mật khẩu tối thiểu 6 ký tự.")
        try:
            db.execute("INSERT INTO NhanVien(TenDangNhap,MatKhau,HoTen,VaiTro) VALUES(?,?,?,?)",
                       (d["TenDangNhap"], db.hash_pw(d["MatKhau"]), d["HoTen"], d["VaiTro"]))
        except Exception:
            error("Tên đăng nhập đã tồn tại.")

    def edit(self, id_):
        cur = dict(db.query("SELECT * FROM NhanVien WHERE MaNV=?", (id_,), one=True))
        cur["MatKhau"] = ""
        d = form_dialog(self, "Sửa tài khoản", self._fields(True), cur)
        if not d:
            return
        if not (d["TenDangNhap"] and d["HoTen"]) or (d["MatKhau"] and len(d["MatKhau"]) < 6):
            return error("Nhập đủ thông tin; mật khẩu (nếu đổi) tối thiểu 6 ký tự.")
        try:
            if d["MatKhau"]:
                db.execute("UPDATE NhanVien SET TenDangNhap=?,HoTen=?,VaiTro=?,MatKhau=? WHERE MaNV=?",
                           (d["TenDangNhap"], d["HoTen"], d["VaiTro"], db.hash_pw(d["MatKhau"]), id_))
            else:
                db.execute("UPDATE NhanVien SET TenDangNhap=?,HoTen=?,VaiTro=? WHERE MaNV=?",
                           (d["TenDangNhap"], d["HoTen"], d["VaiTro"], id_))
        except Exception:
            error("Tên đăng nhập đã tồn tại.")

    def delete(self, id_):
        if id_ == self.user["MaNV"]:
            return error("Không thể xóa tài khoản đang đăng nhập.")
        db.execute("DELETE FROM NhanVien WHERE MaNV=?", (id_,))
