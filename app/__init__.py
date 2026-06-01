from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config['SECRET_KEY'] = 'vvm-museum-secret-key-2024'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app.instance_path, 'museum.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Vui lòng đăng nhập để tiếp tục.'
    login_manager.login_message_category = 'warning'

    from app.routes import main
    app.register_blueprint(main)

    # Inject 'now' vào tất cả templates (dùng cho footer year)
    from datetime import datetime
    @app.context_processor
    def inject_now():
        return {'now': datetime.utcnow()}

    with app.app_context():
        db.create_all()
        _seed_data()

    return app

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))

def _seed_data():
    from app.models import User, Category, Artifact

    if User.query.count() == 0:
        admin = User(username='admin', email='admin@vvmuseum.vn', role='admin')
        admin.set_password('Admin@123')
        db.session.add(admin)
        db.session.commit()

    if Category.query.count() == 0:
        cats = [
            Category(name='Vũ khí bộ binh',         icon='fa-gun',          description='Súng trường, tiểu liên, lưỡi lê'),
            Category(name='Phương tiện chiến đấu',   icon='fa-tank',         description='Xe tăng, xe bọc thép, pháo'),
            Category(name='Không quân',               icon='fa-jet-fighter',  description='Máy bay, tên lửa, radar'),
            Category(name='Hải quân',                 icon='fa-ship',         description='Tàu chiến, ngư lôi, thủy lôi'),
            Category(name='Huân huy chương',          icon='fa-medal',        description='Huân chương, huy chương các cấp'),
            Category(name='Quân trang',               icon='fa-shirt',        description='Quân phục, ba lô, dụng cụ chiến trường'),
        ]
        db.session.add_all(cats)
        db.session.commit()

    if Artifact.query.count() == 0:
        admin = User.query.filter_by(role='admin').first()
        samples = [
            Artifact(
                name='Súng trường tấn công AK-47',
                period='Kháng chiến chống Mỹ (1955–1975)',
                origin='Liên Xô – trang bị QĐNDVN',
                description='Súng trường tấn công AK-47 do kỹ sư Mikhail Kalashnikov thiết kế năm 1947. Đây là vũ khí bộ binh chủ lực của Quân đội Nhân dân Việt Nam trong cuộc kháng chiến chống Mỹ cứu nước. Khẩu súng nổi tiếng với độ bền cao, hoạt động tốt trong mọi điều kiện khắc nghiệt của chiến trường nhiệt đới Việt Nam.',
                category_id=1, user_id=admin.id,
                image_filename='ak47.jpg',
            ),
            Artifact(
                name='Xe tăng T-54 (Số hiệu 843)',
                period='Chiến dịch Hồ Chí Minh (30/4/1975)',
                origin='Liên Xô – Lữ đoàn tăng thiết giáp 203',
                description='Xe tăng T-54 mang số hiệu 843 – chiếc xe tăng lịch sử đã húc đổ cổng Dinh Độc Lập vào trưa ngày 30/4/1975, đánh dấu sự toàn thắng của chiến dịch Hồ Chí Minh lịch sử. Hiện vật biểu tượng của ngày giải phóng miền Nam, thống nhất đất nước.',
                category_id=2, user_id=admin.id,
                image_filename='tank_54.jpg',
            ),
            Artifact(
                name='Máy bay tiêm kích MiG-21 PFM',
                period='Chiến tranh phá hoại miền Bắc (1965–1973)',
                origin='Liên Xô – Trung đoàn Không quân 921 "Sao Đỏ"',
                description='MiG-21 PFM là át chủ bài của Không quân Nhân dân Việt Nam trong cuộc chiến tranh phá hoại. Các phi công huyền thoại như Nguyễn Văn Cốc đã lái loại máy bay này bắn hạ nhiều máy bay hiện đại nhất của Mỹ. Số hiệu 5121 từng tham gia nhiều trận không chiến lịch sử.',
                category_id=3, user_id=admin.id,
                image_filename='mig21.jpg',
            ),
            Artifact(
                name='Huân chương Chiến công Hạng Nhất',
                period='1954–1975',
                origin='Nhà nước Việt Nam Dân chủ Cộng hòa',
                description='Huân chương Chiến công Hạng Nhất – phần thưởng cao quý được Nhà nước trao tặng cho các tập thể và cá nhân lập thành tích xuất sắc trong chiến đấu bảo vệ Tổ quốc. Làm từ vàng và men màu, mang hình ngôi sao năm cánh biểu trưng cho sức mạnh và tinh thần anh dũng của quân đội nhân dân.',
                category_id=5, user_id=admin.id,
                image_filename='huanchuong.png',
            ),
        ]
        db.session.add_all(samples)
        db.session.commit()
