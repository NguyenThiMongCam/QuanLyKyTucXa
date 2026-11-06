import tkinter as tk
import database as db
from screens.base import CrudScreen, error, form_dialog, money, pick_id


class LoaiPhongScreen(CrudScreen):
    title = "Loại phòng"
    columns = [("MaLoai", "Mã", 50), ("TenLoai", "Tên loại", 200), ("SoGiuong", "Số giường", 90),
               ("GiaThue", "Giá thuê (đ/người/tháng)", 180)]
    FIELDS = [("TenLoai", "Tên loại phòng", "entry", None),
              ("SoGiuong", "Số giường", "entry", None),
              ("GiaThue", "Giá thuê (đ/người/tháng)", "entry", None)]

    def rows(self, kw):
        return [dict(r, GiaThue=money(r["GiaThue"])) for r in
                db.query("SELECT * FROM LoaiPhong WHERE TenLoai LIKE ? ORDER BY MaLoai", (f"%{kw}%",))]

    def _check(self, d):
        if not d["TenLoai"]:
            return "Tên loại không được để trống."
        if not (d["SoGiuong"].isdigit() and int(d["SoGiuong"]) > 0):
            return "Số giường phải là số nguyên dương."
        if not (d["GiaThue"].isdigit() and int(d["GiaThue"]) > 0):
            return "Giá thuê phải là số nguyên dương."

    def add(self):
        d = form_dialog(self, "Thêm loại phòng", self.FIELDS)
        if d:
            err = self._check(d)
            if err:
                return error(err)
            db.execute("INSERT INTO LoaiPhong(TenLoai,SoGiuong,GiaThue) VALUES(?,?,?)",
                       (d["TenLoai"], int(d["SoGiuong"]), int(d["GiaThue"])))

    def edit(self, id_):
        cur = dict(db.query("SELECT * FROM LoaiPhong WHERE MaLoai=?", (id_,), one=True))
        d = form_dialog(self, "Sửa loại phòng", self.FIELDS, cur)
        if d:
            err = self._check(d)
            if err:
                return error(err)
            db.execute("UPDATE LoaiPhong SET TenLoai=?,SoGiuong=?,GiaThue=? WHERE MaLoai=?",
                       (d["TenLoai"], int(d["SoGiuong"]), int(d["GiaThue"]), id_))

    def delete(self, id_):
        db.execute("DELETE FROM LoaiPhong WHERE MaLoai=?", (id_,))


class PhongScreen(CrudScreen):
    title = "Quản lý phòng"
    columns = [("MaPhong", "Mã", 50), ("TenPhong", "Tên phòng", 90), ("TenLoai", "Loại phòng", 130),
               ("Tang", "Tầng", 50), ("SoGiuong", "Số giường", 80), ("DangO", "Đang ở", 70),
               ("GiaThue", "Giá/người/tháng", 130), ("TinhTrang", "Trạng thái", 90)]
    extra = [("🏷 Loại phòng", "open_loai")]

    def rows(self, kw):
        out = []
        for p in db.danh_sach_phong():
            if kw.lower() in (p["TenPhong"] + p["TenLoai"] + p["TinhTrang"]).lower():
                out.append(dict(p, GiaThue=money(p["GiaThue"])))
        return out

    def on_extra(self, method):  # nút "Loại phòng" không cần chọn dòng
        if method == "open_loai":
            win = tk.Toplevel(self)
            win.title("Loại phòng")
            win.geometry("640x420")
            LoaiPhongScreen(win).pack(fill="both", expand=True)
            win.transient(self.winfo_toplevel())
            win.grab_set()
            win.wait_window()
            self.refresh()

    def _loai_opts(self):
        return [f"{r['MaLoai']} - {r['TenLoai']} ({r['SoGiuong']} giường)"
                for r in db.query("SELECT * FROM LoaiPhong ORDER BY MaLoai")]

    def _fields(self):
        return [("TenPhong", "Tên phòng", "entry", None),
                ("Loai", "Loại phòng", "combo", self._loai_opts()),
                ("Tang", "Tầng", "entry", None),
                ("TrangThai", "Trạng thái", "combo", ["Hoạt động", "Bảo trì"])]

    def _check(self, d, id_=None):
        if not d["TenPhong"]:
            return "Tên phòng không được để trống."
        if not d["Tang"].isdigit():
            return "Tầng phải là số nguyên."
        dup = db.query("SELECT MaPhong FROM Phong WHERE TenPhong=? AND MaPhong<>?",
                       (d["TenPhong"], id_ or 0), one=True)
        if dup:
            return "Tên phòng đã tồn tại."

    def add(self):
        if not self._loai_opts():
            return error("Hãy thêm loại phòng trước (nút Loại phòng).")
        d = form_dialog(self, "Thêm phòng", self._fields())
        if d:
            err = self._check(d)
            if err:
                return error(err)
            db.execute("INSERT INTO Phong(TenPhong,MaLoai,Tang,TrangThai) VALUES(?,?,?,?)",
                       (d["TenPhong"], pick_id(d["Loai"]), int(d["Tang"]), d["TrangThai"]))

    def edit(self, id_):
        cur = dict(db.query("SELECT * FROM Phong WHERE MaPhong=?", (id_,), one=True))
        opts = self._loai_opts()
        cur["Loai"] = next((o for o in opts if pick_id(o) == cur["MaLoai"]), opts[0])
        d = form_dialog(self, "Cập nhật phòng", self._fields(), cur)
        if d:
            err = self._check(d, id_)
            if err:
                return error(err)
            db.execute("UPDATE Phong SET TenPhong=?,MaLoai=?,Tang=?,TrangThai=? WHERE MaPhong=?",
                       (d["TenPhong"], pick_id(d["Loai"]), int(d["Tang"]), d["TrangThai"], id_))

    def delete(self, id_):
        db.execute("DELETE FROM Phong WHERE MaPhong=?", (id_,))
