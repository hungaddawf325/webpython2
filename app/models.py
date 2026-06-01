from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'user'

    id         = db.Column(db.Integer, primary_key=True)
    username   = db.Column(db.String(80),  unique=True, nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role       = db.Column(db.String(20),  default='user')   # 'admin' | 'user'
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)


    artifacts  = db.relationship('Artifact', backref='author',   lazy=True)
    comments   = db.relationship('Comment',  backref='commenter', lazy=True)


    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_admin(self) -> bool:
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username} [{self.role}]>'



class Category(db.Model):
    __tablename__ = 'category'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False, unique=True)
    icon        = db.Column(db.String(60),  default='fa-box-archive')
    description = db.Column(db.Text)


    artifacts   = db.relationship('Artifact', backref='category', lazy=True)

    def __repr__(self):
        return f'<Category {self.name}>'



class Artifact(db.Model):
    __tablename__ = 'artifact'

    id               = db.Column(db.Integer, primary_key=True)
    name             = db.Column(db.String(200), nullable=False)
    period           = db.Column(db.String(150))   # Giai đoạn lịch sử
    origin           = db.Column(db.String(200))   # Xuất xứ / nguồn gốc
    description      = db.Column(db.Text,    nullable=False)
    image_filename   = db.Column(db.String(300))   # Tên file ảnh đã upload
    views            = db.Column(db.Integer, default=0)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, default=datetime.utcnow,
                                               onupdate=datetime.utcnow)

    # Khóa ngoại
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'),     nullable=False)

    # Quan hệ
    comments    = db.relationship('Comment', backref='artifact',
                                  lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Artifact {self.name}>'



class Comment(db.Model):
    __tablename__ = 'comment'

    id          = db.Column(db.Integer, primary_key=True)
    content     = db.Column(db.Text, nullable=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # Khóa ngoại
    user_id     = db.Column(db.Integer, db.ForeignKey('user.id'),     nullable=False)
    artifact_id = db.Column(db.Integer, db.ForeignKey('artifact.id'), nullable=False)

    def __repr__(self):
        return f'<Comment by user {self.user_id} on artifact {self.artifact_id}>'
