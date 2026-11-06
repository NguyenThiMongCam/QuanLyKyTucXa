import database as db
from screens.base import CrudScreen, error, form_dialog, money


class DichVuScreen(CrudScreen):
    title = "Dịch vụ (điện, nước, ...)"
    columns = [("MaDV", "Mã", 50), ("TenDV", "Tên dịch vụ", 200), ("DonGia", "Đơn giá (đ)", 120), ("DonVi", "Đơn vị", 100)]
    FIELDS = [("TenDV", "Tên dịch vụ", "entry", None), ("DonGia", "Đơn giá (đ)", "entry", None),
              ("DonVi", "Đơn vị tính", "entry", None)]

    def rows(self, kw):
        return [dict(r, DonGia=money(r["DonGia"])) for r in
                db.query("SELECT * FROM DichVu WHERE TenDV LIKE ? ORDER BY MaDV", (f"%{kw}%",))]

    def _check(self, d):
        if not d["TenDV"]:
            return "Tên dịch vụ không được để trống."
        if not d["DonGia"].isdigit():
            return "Đơn giá phải là số nguyên không âm."

    def add(self):
        d = form_dialog(self, "Thêm dịch vụ", self.FIELDS)
        if d:
            err = self._check(d)
            if err:
                return error(err)
            try:
                db.execute("INSERT INTO DichVu(TenDV,DonGia,DonVi) VALUES(?,?,?)",
                           (d["TenDV"], int(d["DonGia"]), d["DonVi"]))
            except Exception:
                error("Tên dịch vụ đã tồn tại.")

    def edit(self, id_):
        cur = dict(db.query("SELECT * FROM DichVu WHERE MaDV=?", (id_,), one=True))
        d = form_dialog(self, "Sửa dịch vụ", self.FIELDS, cur)
        if d:
            err = self._check(d)
            if err:
                return error(err)
            try:
                db.execute("UPDATE DichVu SET TenDV=?,DonGia=?,DonVi=? WHERE MaDV=?",
                           (d["TenDV"], int(d["DonGia"]), d["DonVi"], id_))
            except Exception:
                error("Tên dịch vụ đã tồn tại.")

    def delete(self, id_):
        db.execute("DELETE FROM DichVu WHERE MaDV=?", (id_,))
