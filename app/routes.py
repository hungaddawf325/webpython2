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


@main.route('/admin/category/<int:cid>/delete', methods=['POST'])
@login_required
@_admin_required
def delete_category(cid):
    cat = Category.query.get_or_404(cid)
    db.session.delete(cat)
    db.session.commit()
    flash('Đã xóa danh mục.', 'info')
    return redirect(url_for('main.admin_dashboard'))


PREDEFINED = [
    (
        ['xin chào', 'chào', 'hello', 'hi', 'hey', 'alo', 'bắt đầu'],
        '🏛️ Xin chào! Tôi là hướng dẫn viên ảo của **Bảo Tàng Lịch Sử Quân Sự Việt Nam**.\n\nTôi có thể giúp bạn tìm hiểu về các hiện vật, lịch sử quân sự và các sự kiện lịch sử hào hùng của dân tộc. Bạn muốn biết gì hôm nay? ⭐'
    ),
    (
        ['cảm ơn', 'thanks', 'thank you', 'tks', 'cám ơn'],
        '🎖️ Không có gì! Rất vui được phục vụ bạn. Nếu còn câu hỏi nào về lịch sử quân sự Việt Nam, đừng ngại hỏi nhé!'
    ),
    (
        ['tạm biệt', 'bye', 'goodbye', 'hẹn gặp lại'],
        '⭐ Tạm biệt! Cảm ơn đã ghé thăm Bảo Tàng Quân Sự Việt Nam. Hẹn gặp lại bạn!'
    ),

    # ── Bảo tàng ────────────────────────────────────────────────────
    (
        ['bảo tàng', 'museum', 'địa chỉ', 'ở đâu', 'tham quan', 'giờ mở cửa', 'vé'],
        '🏛️ **Bảo Tàng Lịch Sử Quân Sự Việt Nam**\n\n📍 Địa chỉ: 28A Điện Biên Phủ, Ba Đình, Hà Nội\n⏰ Giờ mở cửa: 8h00 – 17h00 (Thứ 3 đến Chủ nhật)\n🎫 Vé vào cửa: Miễn phí cho trẻ em dưới 6 tuổi\n\nBảo tàng lưu giữ hơn 150.000 hiện vật quý giá về lịch sử quân sự Việt Nam qua các thời kỳ.'
    ),
    (
        ['danh mục', 'loại hiện vật', 'có những gì', 'trưng bày gì', 'xem gì'],
        '🏛️ Bảo tàng có **6 danh mục hiện vật** chính:\n\n🔫 **Vũ khí bộ binh** – Súng trường, tiểu liên, lưỡi lê\n🚗 **Phương tiện chiến đấu** – Xe tăng, xe bọc thép, pháo\n✈️ **Không quân** – Máy bay, tên lửa, radar\n⚓ **Hải quân** – Tàu chiến, ngư lôi\n🎖️ **Huân huy chương** – Huân chương các cấp\n👕 **Quân trang** – Quân phục, dụng cụ chiến trường'
    ),

    # ── Xe tăng T-54 ────────────────────────────────────────────────
    (
        ['xe tăng', 't-54', 't54', '843', 'dinh độc lập', 'lữ đoàn 203', '30/4', '30 tháng 4'],
        '🚗 **Xe tăng T-54 số hiệu 843** – Biểu tượng của ngày Giải phóng!\n\nChiếc xe tăng huyền thoại này thuộc Lữ đoàn tăng thiết giáp 203 đã húc đổ cổng Dinh Độc Lập vào trưa ngày **30/4/1975**, đánh dấu sự toàn thắng của Chiến dịch Hồ Chí Minh và thống nhất đất nước.\n\nT-54 do Liên Xô sản xuất, nặng 36 tấn, trang bị pháo 100mm. Đây là một trong những hiện vật quý nhất của bảo tàng! ⭐'
    ),

    # ── AK-47 ───────────────────────────────────────────────────────
    (
        ['ak47', 'ak-47', 'kalashnikov', 'súng trường', 'súng ak', 'tiểu liên'],
        '🔫 **Súng trường tấn công AK-47**\n\nDo kỹ sư Mikhail Kalashnikov (Liên Xô) thiết kế năm 1947, AK-47 là vũ khí bộ binh chủ lực của Quân đội Nhân dân Việt Nam trong kháng chiến chống Mỹ.\n\nNổi tiếng với độ bền cao, hoạt động tốt trong mọi điều kiện khắc nghiệt của chiến trường nhiệt đới. Khẩu súng này đã theo bước chân người lính qua rừng sâu, bùn lầy, đến ngày toàn thắng! 🎖️'
    ),

    # ── MiG-21 ──────────────────────────────────────────────────────
    (
        ['mig', 'mig-21', 'máy bay', 'tiêm kích', 'không quân', 'phi công', '5121', 'sao đỏ', 'nguyễn văn cốc', 'f-4', 'f-105'],
        '✈️ **Máy bay tiêm kích MiG-21 PFM – Số hiệu 5121**\n\nĐây là "át chủ bài" của Không quân Nhân dân Việt Nam trong chiến tranh phá hoại miền Bắc (1965–1973).\n\nThuộc Trung đoàn Không quân 921 "Sao Đỏ", các phi công huyền thoại như **Nguyễn Văn Cốc** (bắn hạ 9 máy bay Mỹ) đã lái MiG-21 đánh bại những F-105 và F-4 Phantom hiện đại nhất của Mỹ! ⭐'
    ),

    # ── Huân chương ─────────────────────────────────────────────────
    (
        ['huân chương', 'huy chương', 'chiến công', 'phần thưởng', 'bằng khen', 'khen thưởng'],
        '🎖️ **Huân chương Chiến công Hạng Nhất**\n\nĐây là phần thưởng cao quý của Nhà nước trao tặng cho các tập thể và cá nhân lập thành tích xuất sắc trong chiến đấu bảo vệ Tổ quốc.\n\nLàm từ vàng và men màu, mang hình ngôi sao năm cánh – biểu tượng của sức mạnh và tinh thần anh dũng của Quân đội Nhân dân Việt Nam. Mỗi chiếc huân chương là một câu chuyện hy sinh và cống hiến! ⭐'
    ),

    # ── Kháng chiến chống Pháp ───────────────────────────────────────
    (
        ['chống pháp', 'kháng pháp', 'điện biên phủ', 'điện biên', '1954', 'thực dân', 'võ nguyên giáp', 'hồ chí minh'],
        '⭐ **Kháng chiến chống Pháp (1945–1954)**\n\nSau Cách mạng tháng Tám 1945, thực dân Pháp quay lại xâm lược. Dưới sự lãnh đạo của Chủ tịch Hồ Chí Minh và Đại tướng Võ Nguyên Giáp, quân dân ta đã tiến hành 9 năm kháng chiến trường kỳ.\n\n**Chiến thắng Điện Biên Phủ (7/5/1954)** là đỉnh cao – lần đầu tiên trong lịch sử, một dân tộc thuộc địa châu Á đánh bại hoàn toàn quân đội thực dân châu Âu! 🎖️'
    ),

    # ── Kháng chiến chống Mỹ ────────────────────────────────────────
    (
        ['chống mỹ', 'kháng mỹ', '1975', 'giải phóng', 'thống nhất', 'chiến tranh việt nam', 'hồ chí minh campaign', 'chiến dịch'],
        '⭐ **Kháng chiến chống Mỹ (1955–1975)**\n\n20 năm trường kỳ kháng chiến, quân dân Việt Nam đã đánh bại đế quốc Mỹ – siêu cường quân sự mạnh nhất thế giới.\n\n**30/4/1975**: Chiến dịch Hồ Chí Minh toàn thắng, miền Nam hoàn toàn giải phóng, đất nước thống nhất sau hơn 20 năm chia cắt. Chiến thắng này là một trong những trang sử hào hùng nhất của dân tộc Việt Nam! 🎖️'
    ),

    # ── Lịch sử quân sự ─────────────────────────────────────────────
    (
        ['lịch sử', 'lịch sử quân sự', 'truyền thống', 'anh hùng', 'liệt sĩ', 'hy sinh'],
        '🏛️ **Lịch sử quân sự Việt Nam** trải dài hàng nghìn năm dựng nước và giữ nước:\n\n• **938**: Ngô Quyền đánh tan quân Nam Hán trên sông Bạch Đằng\n• **1285, 1288**: Trần Hưng Đạo 3 lần đánh bại quân Mông Nguyên\n• **1954**: Chiến thắng Điện Biên Phủ lịch sử\n• **1975**: Đại thắng mùa Xuân, thống nhất đất nước\n\nMỗi hiện vật trong bảo tàng là minh chứng cho tinh thần bất khuất của dân tộc! ⭐'
    ),

    # ── Hỗ trợ sử dụng web ──────────────────────────────────────────
    (
        ['tìm kiếm', 'tìm hiện vật', 'cách tìm', 'lọc', 'search'],
        '🔍 **Cách tìm kiếm hiện vật trên website:**\n\n1. Dùng **ô tìm kiếm** ở trang chủ – gợi ý tự động khi gõ\n2. Chọn **danh mục** (Vũ khí, Xe tăng, Không quân...)\n3. Lọc theo **giai đoạn lịch sử**\n4. Nhấn **XEM CHI TIẾT** để đọc đầy đủ thông tin\n\nBạn muốn tìm hiện vật nào cụ thể không? 🏛️'
    ),
    (
        ['bình luận', 'comment', 'đăng ký', 'đăng nhập', 'tài khoản'],
        '👤 **Tính năng thành viên:**\n\n• **Đăng ký** tài khoản miễn phí để tham gia bình luận\n• Chia sẻ suy nghĩ về các hiện vật lịch sử\n• Admin có thể **thêm/sửa/xóa** hiện vật\n\nBấm **ĐĂNG KÝ** trên thanh menu để tạo tài khoản nhé! ⭐'
    ),

    # ── Không biết ──────────────────────────────────────────────────
    (
        ['không biết', 'không rõ', 'chưa biết'],
        '🤔 Câu hỏi thú vị! Tôi sẽ cố gắng tìm thêm thông tin về vấn đề này cho bạn. Trong khi đó, bạn có thể tham khảo các hiện vật đang trưng bày trên trang chủ nhé! 🏛️'
    ),
]


def _find_predefined(user_msg: str):
    """Tìm câu trả lời có sẵn dựa theo từ khóa. Trả về str hoặc None."""
    msg_lower = user_msg.lower().strip()
    # Loại bỏ dấu câu
    for ch in '?!.,;:':
        msg_lower = msg_lower.replace(ch, '')

    best_match = None
    best_count = 0

    for keywords, answer in PREDEFINED:
        count = sum(1 for kw in keywords if kw in msg_lower)
        if count > best_count:
            best_count = count
            best_match = answer

    return best_match if best_count >= 1 else None


def _call_gemini(user_msg: str, history: list, artifacts_info: str) -> str:
    """Gọi Gemini API, trả về chuỗi reply hoặc raise Exception."""
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise Exception('Thư viện google-genai chưa được cài. Chạy: pip install google-genai')

    api_key = os.environ.get('GEMINI_API_KEY', '')
    if not api_key or api_key == 'your_gemini_api_key_here':
        raise Exception('GEMINI_API_KEY chưa được cấu hình trong file .env')

    system_prompt = f"""Bạn là Hướng Dẫn Viên Ảo của Bảo Tàng Lịch Sử Quân Sự Việt Nam.
Trả lời bằng tiếng Việt, ngắn gọn (3-4 câu), thân thiện.
Chỉ trả lời về lịch sử quân sự, hiện vật bảo tàng.
Không bịa đặt thông tin lịch sử.

Hiện vật đang trưng bày:
{artifacts_info}"""

    client   = genai.Client(api_key=api_key)
    contents = history + [types.Content(role='user', parts=[types.Part(text=user_msg)])]

    response  = client.models.generate_content(
        model    = 'gemini-2.0-flash',
        config   = types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=512,
        ),
        contents = contents,
    )
    return response.text or 'Xin lỗi, tôi không thể trả lời câu hỏi này.'


# Lịch sử Gemini chat theo session
_gemini_histories = {}


@main.route('/chatbot', methods=['POST'])
def chatbot():
    """
    Hybrid chatbot:
    1. Tìm câu trả lời có sẵn theo từ khóa
    2. Không tìm thấy → gọi Gemini API
    3. Gemini lỗi → thông báo rõ ràng
    """
    try:
        data       = request.get_json(silent=True) or {}
        user_msg   = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')

        if not user_msg:
            return jsonify({'error': 'Tin nhắn không được để trống.'}), 400

        # ── BƯỚC 1: Tìm câu trả lời có sẵn ───────────────────────
        predefined_reply = _find_predefined(user_msg)
        if predefined_reply:
            return jsonify({
                'reply':  predefined_reply,
                'source': 'local'   # để debug biết dùng câu có sẵn
            })

        # ── BƯỚC 2: Không có câu sẵn → gọi Gemini ─────────────────
        # Lấy danh sách hiện vật từ DB
        try:
            artifacts_info = '\n'.join([
                f"- {a.name} ({a.period or 'không rõ giai đoạn'})"
                for a in Artifact.query.limit(20).all()
            ])
        except Exception:
            artifacts_info = '(Không tải được)'

        # Lịch sử Gemini của session này
        if session_id not in _gemini_histories:
            _gemini_histories[session_id] = []
        history = _gemini_histories[session_id]

        try:
            from google.genai import types
            bot_reply = _call_gemini(user_msg, history, artifacts_info)

            # Lưu lịch sử để Gemini nhớ ngữ cảnh
            from google.genai import types as gtypes
            history.append(gtypes.Content(role='user',  parts=[gtypes.Part(text=user_msg)]))
            history.append(gtypes.Content(role='model', parts=[gtypes.Part(text=bot_reply)]))
            if len(history) > 20:
                _gemini_histories[session_id] = history[-20:]

            return jsonify({'reply': bot_reply, 'source': 'gemini'})

        except Exception as api_err:
            # ── BƯỚC 3: Gemini lỗi → fallback thông báo thân thiện ──
            err = str(api_err)
            if 'chưa được cấu hình' in err or '.env' in err:
                fallback = '🤔 Câu hỏi này tôi chưa có câu trả lời có sẵn.\n\nBạn có thể hỏi về: **xe tăng T-54, súng AK-47, MiG-21, huân chương, lịch sử kháng chiến** hoặc thông tin về bảo tàng nhé! 🏛️'
            elif 'quota' in err.lower() or '429' in err or 'rate' in err.lower():
                fallback = '⏳ Hệ thống AI đang bận, vui lòng thử lại sau 1 phút.\n\nTrong lúc chờ, bạn thử hỏi về: **xe tăng T-54, AK-47, MiG-21** hoặc xem trực tiếp các hiện vật trên trang chủ nhé! 🏛️'
            else:
                fallback = '🤔 Câu hỏi này tôi chưa có thông tin đầy đủ.\n\nBạn có thể hỏi về các chủ đề tôi biết rõ: **xe tăng, súng AK-47, máy bay MiG-21, huân chương, kháng chiến chống Pháp/Mỹ**. 🎖️'

            return jsonify({'reply': fallback, 'source': 'fallback'})

    except Exception as e:
        return jsonify({'error': f'Lỗi hệ thống: {str(e)}'}), 500


@main.route('/chatbot/clear', methods=['POST'])
def chatbot_clear():
    """Xóa lịch sử chat Gemini của session."""
    data       = request.get_json(silent=True) or {}
    session_id = data.get('session_id', 'default')
    _gemini_histories.pop(session_id, None)
    return jsonify({'status': 'cleared'})
