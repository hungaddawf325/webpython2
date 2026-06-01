import os
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, current_app)
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models import User, Category, Artifact, Comment

main = Blueprint('main', __name__)

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _allowed(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def _save_image(file) -> str | None:
    """Lưu file ảnh, trả về tên file đã lưu hoặc None."""
    if file and _allowed(file.filename):
        fn = secure_filename(file.filename)
        ts = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
        fn = f"{ts}_{fn}"
        path = os.path.join(current_app.config['UPLOAD_FOLDER'], fn)
        file.save(path)
        return fn
    return None


def _admin_required(func):
    """Decorator kiểm tra quyền admin."""
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Bạn không có quyền truy cập trang này.', 'error')
            return redirect(url_for('main.index'))
        return func(*args, **kwargs)
    return wrapper



@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email    = request.form.get('email',    '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm',  '')


        error = None
        if not username or not email or not password:
            error = 'Vui lòng điền đầy đủ thông tin.'
        elif len(password) < 6:
            error = 'Mật khẩu phải có ít nhất 6 ký tự.'
        elif password != confirm:
            error = 'Mật khẩu xác nhận không khớp.'
        elif User.query.filter_by(username=username).first():
            error = 'Tên đăng nhập đã tồn tại.'
        elif User.query.filter_by(email=email).first():
            error = 'Email đã được sử dụng.'

        if error:
            flash(error, 'error')
        else:
            user = User(username=username, email=email)
            user.set_password(password)

            if User.query.count() == 0:
                user.role = 'admin'
            db.session.add(user)
            db.session.commit()
            flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('main.login'))

    return render_template('register.html')


@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'Chào mừng trở lại, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))

        flash('Sai tên đăng nhập hoặc mật khẩu.', 'error')

    return render_template('login.html')


@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Đã đăng xuất thành công.', 'info')
    return redirect(url_for('main.index'))



@main.route('/')
def index():

    search      = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    period_f    = request.args.get('period', '').strip()
    page        = request.args.get('page', 1, type=int)

    query = Artifact.query

    if search:
        like = f'%{search}%'
        query = query.filter(
            db.or_(
                Artifact.name.ilike(like),
                Artifact.description.ilike(like),
                Artifact.origin.ilike(like),
                Artifact.period.ilike(like),
            )
        )
    if category_id:
        query = query.filter_by(category_id=category_id)
    if period_f:
        query = query.filter(Artifact.period.ilike(f'%{period_f}%'))

    pagination  = query.order_by(Artifact.created_at.desc()).paginate(
        page=page, per_page=9, error_out=False
    )
    categories  = Category.query.all()
    periods     = (
        db.session.query(Artifact.period)
        .filter(Artifact.period.isnot(None), Artifact.period != '')
        .distinct().all()
    )

    return render_template(
        'index.html',
        pagination=pagination,
        artifacts=pagination.items,
        categories=categories,
        periods=[p[0] for p in periods],
        search=search,
        category_id=category_id,
        period_f=period_f,
        total_artifacts=Artifact.query.count(),
        total_users=User.query.count(),
    )



@main.route('/search-ajax')
def search_ajax():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    results = Artifact.query.filter(
        db.or_(
            Artifact.name.ilike(f'%{q}%'),
            Artifact.origin.ilike(f'%{q}%'),
        )
    ).limit(8).all()
    return jsonify([
        {
            'id':     a.id,
            'name':   a.name,
            'period': a.period or '',
            'url':    url_for('main.artifact_detail', id=a.id),
        }
        for a in results
    ])



@main.route('/artifact/<int:id>', methods=['GET', 'POST'])
def artifact_detail(id):
    artifact = Artifact.query.get_or_404(id)


    artifact.views += 1
    db.session.commit()


    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('Vui lòng đăng nhập để bình luận.', 'warning')
            return redirect(url_for('main.login'))
        content = request.form.get('content', '').strip()
        if not content:
            flash('Nội dung bình luận không được để trống.', 'error')
        else:
            cmt = Comment(content=content,
                          user_id=current_user.id,
                          artifact_id=artifact.id)
            db.session.add(cmt)
            db.session.commit()
            flash('Đã gửi bình luận.', 'success')
        return redirect(url_for('main.artifact_detail', id=id))

    related = (
        Artifact.query
        .filter(Artifact.category_id == artifact.category_id,
                Artifact.id != artifact.id)
        .limit(4).all()
    )
    comments = (
        Comment.query
        .filter_by(artifact_id=id)
        .order_by(Comment.created_at.desc())
        .all()
    )
    return render_template(
        'artifact_detail.html',
        artifact=artifact,
        related=related,
        comments=comments,
    )


@main.route('/comment/<int:cid>/delete', methods=['POST'])
@login_required
def delete_comment(cid):
    cmt = Comment.query.get_or_404(cid)
    artifact_id = cmt.artifact_id
    if current_user.id != cmt.user_id and not current_user.is_admin():
        flash('Bạn không có quyền xóa bình luận này.', 'error')
        return redirect(url_for('main.artifact_detail', id=artifact_id))
    db.session.delete(cmt)
    db.session.commit()
    flash('Đã xóa bình luận.', 'info')
    return redirect(url_for('main.artifact_detail', id=artifact_id))



@main.route('/admin')
@login_required
@_admin_required
def admin_dashboard():
    return render_template(
        'admin/dashboard.html',
        total_artifacts=Artifact.query.count(),
        total_users=User.query.count(),
        total_comments=Comment.query.count(),
        total_categories=Category.query.count(),
        recent_artifacts=Artifact.query.order_by(
            Artifact.created_at.desc()).limit(10).all(),
        users=User.query.order_by(User.created_at.desc()).all(),
        categories=Category.query.all(),
    )



@main.route('/admin/artifact/add', methods=['GET', 'POST'])
@login_required
@_admin_required
def add_artifact():
    categories = Category.query.all()

    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        period      = request.form.get('period', '').strip()
        origin      = request.form.get('origin', '').strip()
        category_id = request.form.get('category_id', type=int)
        image_file  = request.files.get('image')

        if not name or not description:
            flash('Tên và mô tả là bắt buộc.', 'error')
        else:
            img_fn = _save_image(image_file)
            artifact = Artifact(
                name=name, description=description,
                period=period, origin=origin,
                category_id=category_id,
                image_filename=img_fn,
                user_id=current_user.id,
            )
            db.session.add(artifact)
            db.session.commit()
            flash(f'Đã thêm hiện vật "{name}" thành công!', 'success')
            return redirect(url_for('main.artifact_detail', id=artifact.id))

    return render_template('admin/add_artifact.html', categories=categories)



@main.route('/admin/artifact/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@_admin_required
def edit_artifact(id):
    artifact   = Artifact.query.get_or_404(id)
    categories = Category.query.all()

    if request.method == 'POST':
        artifact.name        = request.form.get('name', '').strip()
        artifact.description = request.form.get('description', '').strip()
        artifact.period      = request.form.get('period', '').strip()
        artifact.origin      = request.form.get('origin', '').strip()
        artifact.category_id = request.form.get('category_id', type=int)
        artifact.updated_at  = datetime.utcnow()

        image_file = request.files.get('image')
        if image_file and image_file.filename:
            img_fn = _save_image(image_file)
            if img_fn:
                artifact.image_filename = img_fn

        db.session.commit()
        flash('Cập nhật hiện vật thành công!', 'success')
        return redirect(url_for('main.artifact_detail', id=id))

    return render_template('admin/edit_artifact.html',
                           artifact=artifact, categories=categories)



@main.route('/admin/artifact/<int:id>/delete', methods=['POST'])
@login_required
@_admin_required
def delete_artifact(id):
    artifact = Artifact.query.get_or_404(id)
    db.session.delete(artifact)
    db.session.commit()
    flash('Đã xóa hiện vật.', 'info')
    return redirect(url_for('main.index'))



@main.route('/admin/user/<int:uid>/role', methods=['POST'])
@login_required
@_admin_required
def change_role(uid):
    user     = User.query.get_or_404(uid)
    new_role = request.form.get('role')
    if new_role in ('admin', 'user') and user.id != current_user.id:
        user.role = new_role
        db.session.commit()
        flash(f'Đã cập nhật quyền cho {user.username} → {new_role}.', 'success')
    return redirect(url_for('main.admin_dashboard'))



@main.route('/admin/category/add', methods=['POST'])
@login_required
@_admin_required
def add_category():
    name = request.form.get('name', '').strip()
    desc = request.form.get('description', '').strip()
    icon = request.form.get('icon', 'fa-box-archive').strip()
    if name:
        if Category.query.filter_by(name=name).first():
            flash('Danh mục đã tồn tại.', 'error')
        else:
            db.session.add(Category(name=name, description=desc, icon=icon))
            db.session.commit()
            flash('Đã thêm danh mục.', 'success')
    return redirect(url_for('main.admin_dashboard'))


@main.route('/admin/category/<int:cid>/delete', methods=['POST'])
@login_required
@_admin_required
def delete_category(cid):
    cat = Category.query.get_or_404(cid)
    db.session.delete(cat)
    db.session.commit()
    flash('Đã xóa danh mục.', 'info')
    return redirect(url_for('main.admin_dashboard'))
