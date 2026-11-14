"""Tầng dữ liệu: SQLite (có sẵn trong Python, không cần cài MySQL)."""
import hashlib
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kytucxa.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS LoaiPhong(
    MaLoai INTEGER PRIMARY KEY AUTOINCREMENT, TenLoai TEXT NOT NULL,
    SoGiuong INTEGER NOT NULL, GiaThue INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS Phong(
    MaPhong INTEGER PRIMARY KEY AUTOINCREMENT, TenPhong TEXT NOT NULL UNIQUE,
    MaLoai INTEGER NOT NULL REFERENCES LoaiPhong(MaLoai),
    Tang INTEGER NOT NULL, TrangThai TEXT NOT NULL DEFAULT 'Hoạt động');
CREATE TABLE IF NOT EXISTS SinhVien(
    MaSV INTEGER PRIMARY KEY AUTOINCREMENT, HoTen TEXT NOT NULL, NgaySinh TEXT,
    GioiTinh TEXT, Lop TEXT, SDT TEXT, QueQuan TEXT, MatKhau TEXT);
CREATE TABLE IF NOT EXISTS HopDong(
    MaHD INTEGER PRIMARY KEY AUTOINCREMENT,
    MaSV INTEGER NOT NULL REFERENCES SinhVien(MaSV),
    MaPhong INTEGER NOT NULL REFERENCES Phong(MaPhong),
    NgayBatDau TEXT NOT NULL, NgayKetThuc TEXT NOT NULL,
    TrangThai TEXT NOT NULL DEFAULT 'Đang thuê');
CREATE TABLE IF NOT EXISTS DichVu(
    MaDV INTEGER PRIMARY KEY AUTOINCREMENT, TenDV TEXT NOT NULL UNIQUE,
    DonGia INTEGER NOT NULL, DonVi TEXT);
CREATE TABLE IF NOT EXISTS HoaDon(
    MaHDon INTEGER PRIMARY KEY AUTOINCREMENT,
    MaPhong INTEGER NOT NULL REFERENCES Phong(MaPhong),
    Thang TEXT NOT NULL, TienPhong INTEGER, SoDien REAL, SoNuoc REAL,
    TienDien INTEGER, TienNuoc INTEGER, TongTien INTEGER,
    DaThu INTEGER NOT NULL DEFAULT 0, TrangThai TEXT NOT NULL DEFAULT 'Chưa thu',
    NgayThu TEXT, UNIQUE(MaPhong, Thang));
CREATE TABLE IF NOT EXISTS NhanVien(
    MaNV INTEGER PRIMARY KEY AUTOINCREMENT, TenDangNhap TEXT NOT NULL UNIQUE,
    MatKhau TEXT NOT NULL, HoTen TEXT NOT NULL, VaiTro TEXT NOT NULL DEFAULT 'nhanvien');
CREATE TABLE IF NOT EXISTS ThongBao(
    MaTB INTEGER PRIMARY KEY AUTOINCREMENT, TieuDe TEXT NOT NULL, NoiDung TEXT, Ngay TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS YeuCau(
    MaYC INTEGER PRIMARY KEY AUTOINCREMENT,
    MaSV INTEGER NOT NULL REFERENCES SinhVien(MaSV),
    Loai TEXT NOT NULL, NoiDung TEXT NOT NULL, NgayGui TEXT NOT NULL,
    TrangThai TEXT NOT NULL DEFAULT 'Chờ xử lý');
CREATE TABLE IF NOT EXISTS CauHinh(Khoa TEXT PRIMARY KEY, GiaTri TEXT);
CREATE TABLE IF NOT EXISTS ThanhToan(
    MaTT INTEGER PRIMARY KEY AUTOINCREMENT,
    MaHDon INTEGER NOT NULL REFERENCES HoaDon(MaHDon),
    SoTien INTEGER NOT NULL, HinhThuc TEXT NOT NULL, GhiChu TEXT,
    Ngay TEXT NOT NULL, NguoiThu TEXT);
CREATE TABLE IF NOT EXISTS NhatKy(
    MaNK INTEGER PRIMARY KEY AUTOINCREMENT, ThoiGian TEXT NOT NULL, Loai TEXT NOT NULL, NoiDung TEXT NOT NULL);
"""

# Cấu hình hiển thị cho sinh viên (sửa trực tiếp trong bảng CauHinh nếu cần)
DEFAULT_CONFIG = {
    "gio_mo_cong": "05:00",
    "gio_dong_cong": "23:00",
    "gio_yen_tinh": "22:30 - 05:00",
    "lien_he_dien_thoai": "[SỐ ĐIỆN THOẠI]",
    "lien_he_email": "[EMAIL KTX]",
    "lien_he_van_phong": "[ĐỊA CHỈ / GIỜ LÀM VIỆC]",
    "noi_quy": "\n".join([
        "Giữ gìn vệ sinh phòng ở và khu vực chung.",
        "Không gây ồn ào trong giờ yên tĩnh.",
        "Không nấu ăn, không dùng thiết bị điện công suất lớn trong phòng.",
        "Khách đến thăm phải đăng ký và rời ký túc xá trước giờ đóng cổng.",
        "Không tự ý chuyển phòng hoặc đổi giường khi chưa được Ban quản lý đồng ý.",
        "Báo ngay cho Ban quản lý khi phát hiện hư hỏng hoặc sự cố điện, nước.",
    ]),
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def query(sql, params=(), one=False):
    conn = get_conn()
    try:
        cur = conn.execute(sql, params)
        return cur.fetchone() if one else cur.fetchall()
    finally:
        conn.close()


def execute(sql, params=()):
    conn = get_conn()
    try:
        with conn:
            return conn.execute(sql, params).lastrowid
    finally:
        conn.close()


def hash_pw(pw):
    return hashlib.sha256(("KTX$" + pw).encode("utf-8")).hexdigest()


def login(username, password):
    row = query("SELECT * FROM NhanVien WHERE TenDangNhap=? AND MatKhau=?",
                (username, hash_pw(password)), one=True)
    return dict(row) if row else None


DEFAULT_STUDENT_PW = "123456"  # mật khẩu mặc định của sinh viên chưa đặt mật khẩu riêng


def login_sinh_vien(ma_sv, password):
    """Đăng nhập sinh viên bằng mã sinh viên (MaSV).
    Trả về dict thông tin sinh viên (kèm 'DangO' = có hợp đồng đang thuê) hoặc None nếu sai."""
    try:
        ma = int(str(ma_sv).strip())
    except ValueError:
        return None
    row = query("SELECT * FROM SinhVien WHERE MaSV=?", (ma,), one=True)
    if not row:
        return None
    stored = row["MatKhau"] or hash_pw(DEFAULT_STUDENT_PW)
    if stored != hash_pw(password):
        return None
    d = dict(row)
    d.pop("MatKhau", None)
    d["DangO"] = query("SELECT COUNT(*) FROM HopDong WHERE MaSV=? AND TrangThai='Đang thuê'",
                       (ma,), one=True)[0] > 0
    return d


def get_config(key, default=""):
    row = query("SELECT GiaTri FROM CauHinh WHERE Khoa=?", (key,), one=True)
    return row["GiaTri"] if row and row["GiaTri"] is not None else default


def tao_yeu_cau(ma_sv, loai, noi_dung):
    """Sinh viên gửi yêu cầu (loai: 'Sửa chữa' | 'Về muộn' | 'Gia hạn') tới Ban quản lý."""
    ma = execute("INSERT INTO YeuCau(MaSV,Loai,NoiDung,NgayGui) VALUES(?,?,?,?)",
                 (ma_sv, loai, noi_dung, datetime.now().strftime("%d/%m/%Y")))
    sv = query("SELECT HoTen FROM SinhVien WHERE MaSV=?", (ma_sv,), one=True)
    ghi_nhat_ky("yeucau", f"Yêu cầu {loai.lower()} từ **{sv['HoTen'] if sv else ma_sv}**")
    return ma


def ghi_nhat_ky(loai, noi_dung):
    """Ghi một dòng vào 'Hoạt động gần đây' của trang chủ quản trị.
    loai: thu | phong | hoadon | sv | yeucau.  Dùng **...** để in đậm một đoạn."""
    execute("INSERT INTO NhatKy(ThoiGian,Loai,NoiDung) VALUES(?,?,?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), loai, noi_dung))


def cap_nhat_sinh_vien(ma_sv, ho_ten, sdt, que_quan):
    """Sinh viên tự cập nhật họ tên, số điện thoại, quê quán."""
    execute("UPDATE SinhVien SET HoTen=?, SDT=?, QueQuan=? WHERE MaSV=?", (ho_ten, sdt, que_quan, ma_sv))


def doi_mat_khau_sinh_vien(ma_sv, mat_khau_cu, mat_khau_moi):
    """Đổi mật khẩu sinh viên. Trả về True nếu thành công, False nếu mật khẩu cũ sai."""
    if not login_sinh_vien(ma_sv, mat_khau_cu):
        return False
    execute("UPDATE SinhVien SET MatKhau=? WHERE MaSV=?", (hash_pw(mat_khau_moi), ma_sv))
    return True


def danh_sach_phong():
    """Danh sách phòng kèm số người đang ở và tình trạng (Trống/Còn chỗ/Đầy/Bảo trì)."""
    rows = query("""
        SELECT p.MaPhong, p.TenPhong, p.Tang, p.TrangThai, l.MaLoai, l.TenLoai,
               l.SoGiuong, l.GiaThue,
               (SELECT COUNT(*) FROM HopDong h WHERE h.MaPhong=p.MaPhong
                AND h.TrangThai='Đang thuê') AS DangO
        FROM Phong p JOIN LoaiPhong l ON l.MaLoai=p.MaLoai ORDER BY p.TenPhong""")
    out = []
    for r in rows:
        d = dict(r)
        if d["TrangThai"] == "Bảo trì":
            d["TinhTrang"] = "Bảo trì"
        elif d["DangO"] == 0:
            d["TinhTrang"] = "Trống"
        elif d["DangO"] >= d["SoGiuong"]:
            d["TinhTrang"] = "Đầy"
        else:
            d["TinhTrang"] = "Còn chỗ"
        out.append(d)
    return out


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    _migrate()
    _seed_content()
    _backfill_log()
    if query("SELECT COUNT(*) FROM NhanVien", one=True)[0] == 0:
        _seed()


def _migrate():
    """Nâng cấp file kytucxa.db cũ: thêm cột MatKhau cho bảng SinhVien."""
    cols = [r["name"] for r in query("PRAGMA table_info(SinhVien)")]
    if "MatKhau" not in cols:
        execute("ALTER TABLE SinhVien ADD COLUMN MatKhau TEXT")


def _seed_content():
    """Nội dung mẫu cho giao diện sinh viên: thông báo + cấu hình (chỉ thêm khi còn thiếu)."""
    if query("SELECT COUNT(*) FROM ThongBao", one=True)[0] == 0:
        for ngay, tieu_de, noi_dung in [
                ("01/11/2026", "Kiểm tra phòng định kỳ",
                 "Ban quản lý kiểm tra vệ sinh và an toàn phòng ở trong tuần này."),
                ("05/11/2026", "Đăng ký gia hạn ở ký túc xá học kỳ mới",
                 "Mở đăng ký trực tuyến đến hết ngày 30/11. Hoàn tất ngay trên hệ thống."),
                ("08/11/2026", "Lịch cắt nước bảo trì Khu A",
                 "Dự kiến từ 08:00 đến 11:00 ngày 10/11. Sinh viên chủ động trữ nước.")]:
            execute("INSERT INTO ThongBao(TieuDe,NoiDung,Ngay) VALUES(?,?,?)", (tieu_de, noi_dung, ngay))
    for k, v in DEFAULT_CONFIG.items():
        execute("INSERT OR IGNORE INTO CauHinh(Khoa,GiaTri) VALUES(?,?)", (k, v))


def _backfill_log():
    """Lần đầu có bảng NhatKy: dựng sẵn vài dòng từ dữ liệu đã có (thanh toán, hợp đồng gần nhất)."""
    if query("SELECT COUNT(*) FROM NhatKy", one=True)[0]:
        return

    def to_iso(d):                       # dd/mm/yyyy -> yyyy-mm-dd 00:00:00
        try:
            return datetime.strptime(d, "%d/%m/%Y").strftime("%Y-%m-%d 00:00:00")
        except (TypeError, ValueError):
            return datetime.now().strftime("%Y-%m-%d 00:00:00")

    for r in query("""SELECT t.SoTien, t.Ngay, p.TenPhong FROM ThanhToan t JOIN HoaDon h ON h.MaHDon=t.MaHDon
                      JOIN Phong p ON p.MaPhong=h.MaPhong ORDER BY t.MaTT DESC LIMIT 4"""):
        execute("INSERT INTO NhatKy(ThoiGian,Loai,NoiDung) VALUES(?,?,?)",
                (to_iso(r["Ngay"]), "thu", f"Thu **{r['SoTien']:,} đ** – phòng {r['TenPhong']}".replace(",", ".")))
    for r in query("""SELECT s.HoTen, p.TenPhong, h.NgayBatDau FROM HopDong h JOIN SinhVien s ON s.MaSV=h.MaSV
                      JOIN Phong p ON p.MaPhong=h.MaPhong ORDER BY h.MaHD DESC LIMIT 4"""):
        execute("INSERT INTO NhatKy(ThoiGian,Loai,NoiDung) VALUES(?,?,?)",
                (to_iso(r["NgayBatDau"]), "phong", f"Đăng ký phòng {r['TenPhong']} – **{r['HoTen']}**"))


def _seed():
    execute("INSERT INTO NhanVien(TenDangNhap,MatKhau,HoTen,VaiTro) VALUES(?,?,?,?)",
            ("admin", hash_pw("admin123"), "Quản trị viên", "admin"))
    execute("INSERT INTO NhanVien(TenDangNhap,MatKhau,HoTen,VaiTro) VALUES(?,?,?,?)",
            ("nhanvien", hash_pw("123456"), "Nhân viên KTX", "nhanvien"))
    for t, g, p in [("Phòng 4 người", 4, 600000), ("Phòng 6 người", 6, 450000),
                    ("Phòng 2 người", 2, 900000)]:
        execute("INSERT INTO LoaiPhong(TenLoai,SoGiuong,GiaThue) VALUES(?,?,?)", (t, g, p))
    for ten, loai, tang, tt in [("A101", 1, 1, "Hoạt động"), ("A102", 1, 1, "Hoạt động"),
                                ("A201", 2, 2, "Hoạt động"), ("B101", 3, 1, "Hoạt động"),
                                ("B201", 3, 2, "Bảo trì")]:
        execute("INSERT INTO Phong(TenPhong,MaLoai,Tang,TrangThai) VALUES(?,?,?,?)",
                (ten, loai, tang, tt))
    for ten, gia, dv in [("Điện", 3500, "kWh"), ("Nước", 15000, "m³"), ("Internet", 50000, "tháng")]:
        execute("INSERT INTO DichVu(TenDV,DonGia,DonVi) VALUES(?,?,?)", (ten, gia, dv))
    svs = [("Nguyễn Văn An", "12/05/2005", "Nam", "DHKTPM17A", "0901234567", "Đồng Nai"),
           ("Trần Thị Bình", "20/08/2005", "Nữ", "DHKHDL17B", "0912345678", "Long An"),
           ("Lê Minh Cường", "03/02/2004", "Nam", "DHTTNT17A", "0923456789", "Bình Dương"),
           ("Phạm Thu Dung", "15/11/2005", "Nữ", "DHKTPM17B", "0934567890", "Tiền Giang"),
           ("Hoàng Gia Huy", "27/07/2004", "Nam", "DHATTT17A", "0945678901", "Cần Thơ")]
    for s in svs:
        execute("INSERT INTO SinhVien(HoTen,NgaySinh,GioiTinh,Lop,SDT,QueQuan) VALUES(?,?,?,?,?,?)", s)
    for sv, ph in [(1, 1), (3, 1), (5, 1), (2, 3), (4, 3)]:
        execute("INSERT INTO HopDong(MaSV,MaPhong,NgayBatDau,NgayKetThuc) VALUES(?,?,?,?)",
                (sv, ph, "01/09/2026", "30/06/2027"))