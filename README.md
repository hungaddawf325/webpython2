# 🏛️ Bảo Tàng Lịch Sử Quân Sự Việt Nam

> Ứng dụng web Flask quản lý và trưng bày hiện vật lịch sử quân sự Việt Nam.

---

## 📁 Cấu trúc thư mục

```
vvm_museum/
├── app/
│   ├── __init__.py          # Khởi tạo Flask app và SQLAlchemy
│   ├── models.py            # Models: User, Category, Artifact, Comment
│   ├── routes.py            # Toàn bộ routes (auth, CRUD, admin, AJAX)
│   ├── static/
│   │   ├── css/style.css    # Giao diện Military Editorial
│   │   └── uploads/         # Ảnh hiện vật do admin upload
│   └── templates/
│       ├── base.html        # Layout chung (navbar, footer, flash)
│       ├── index.html       # Trang chủ (tìm kiếm AJAX, lọc, phân trang)
│       ├── login.html       # Đăng nhập
│       ├── register.html    # Đăng ký
│       ├── artifact_detail.html  # Chi tiết hiện vật + bình luận
│       └── admin/
│           ├── dashboard.html    # Bảng điều khiển admin
│           ├── add_artifact.html # Thêm hiện vật
│           └── edit_artifact.html# Sửa hiện vật
├── instance/
│   └── museum.db            # SQLite database (tự tạo khi chạy)
├── run.py                   # Khởi chạy ứng dụng
├── requirements.txt         # Thư viện cần cài
└── README.md
```

---

## ⚙️ Cài đặt và chạy

### 1. Clone về máy
```bash
git clone https://github.com/your-username/vvm_museum.git
cd vvm_museum
```

### 2. Tạo môi trường ảo
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Cài thư viện
```bash
pip install -r requirements.txt
```

### 4. Chạy ứng dụng
```bash
python run.py
```

Mở trình duyệt tại: **http://localhost:5000**

---

## 🔑 Tài khoản mặc định

| Vai trò | Username | Password  |
|---------|----------|-----------|
| Admin   | `admin`  | `Admin@123` |

> **Lưu ý:** User đầu tiên đăng ký sẽ tự động được cấp quyền Admin.

---

## ✨ Tính năng

| Tính năng | Mô tả |
|-----------|-------|
| **Đăng nhập / Đăng ký** | Xác thực người dùng với Flask-Login |
| **Phân quyền** | Admin / User với quyền hạn khác nhau |
| **CRUD Hiện vật** | Thêm, sửa, xóa hiện vật (Admin) |
| **Upload ảnh** | Admin upload ảnh hiện vật (PNG, JPG, GIF) |
| **Tìm kiếm AJAX** | Gợi ý tìm kiếm realtime không reload trang |
| **Lọc dữ liệu** | Lọc theo danh mục, giai đoạn lịch sử |
| **Phân trang** | Hiển thị 9 hiện vật/trang |
| **Bình luận** | User đăng nhập có thể bình luận |
| **Quản trị** | Dashboard thống kê, quản lý user & danh mục |

---

## 🗄️ Cơ sở dữ liệu

Sử dụng **SQLite** với 4 bảng:

- **User** – Người dùng (id, username, email, password_hash, role)
- **Category** – Danh mục hiện vật (id, name, icon, description)
- **Artifact** – Hiện vật (id, name, period, origin, description, image_filename, views, category_id, user_id)
- **Comment** – Bình luận (id, content, created_at, user_id, artifact_id)

---

## 👥 Phân công nhóm

| Thành viên | Công việc |
|------------|-----------|
| Thành viên 1 | Models, Database, `__init__.py`, `routes.py` (Auth + CRUD) |
| Thành viên 2 | Templates HTML, CSS, Giao diện trang chủ & chi tiết |
| Thành viên 3 | Admin dashboard, Upload ảnh, AJAX search, README, Deploy |

---

## 🎨 Giao diện

- **Font:** Bebas Neue (tiêu đề) + Oswald (UI) + Source Serif 4 (nội dung)
- **Màu sắc:** Khaki đậm · Đỏ cờ (#C0392B) · Vàng đồng (#C9A84C)
- **Aesthetic:** Military Editorial – tôn vinh lịch sử hào hùng dân tộc

---

*Đồ án môn Lập trình Web – Khoa Công nghệ Thông tin*
