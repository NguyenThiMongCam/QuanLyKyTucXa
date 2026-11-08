"""Tầng dữ liệu: SQLite (có sẵn trong Python, không cần cài MySQL)."""
import hashlib
import os
import sqlite3

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
"""


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
    if query("SELECT COUNT(*) FROM NhanVien", one=True)[0] == 0:
        _seed()


def _migrate():
    """Nâng cấp file kytucxa.db cũ: thêm cột MatKhau cho bảng SinhVien."""
    cols = [r["name"] for r in query("PRAGMA table_info(SinhVien)")]
    if "MatKhau" not in cols:
        execute("ALTER TABLE SinhVien ADD COLUMN MatKhau TEXT")


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
