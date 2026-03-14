import os
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from extensions import db
from oauth_mail import send_email
from routes.account_help import account_help_bp
from routes.view import view_bp

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'sua-chave-secreta-aqui'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'avatars')
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4 MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db.init_app(app)

EMAIL_SERIALIZER = URLSafeTimedSerializer(app.config['SECRET_KEY'])
EMAIL_TOKEN_MAX_AGE = 1800

ADMIN_DEFAULT_PASSWORD = 'admin123'

from models import User, Camera, Permission, Group, GroupMember, GroupPermission

from routes.cameras import cameras_bp

app.register_blueprint(cameras_bp)
app.register_blueprint(view_bp)
app.register_blueprint(account_help_bp)


def _generate_email_token(email: str) -> str:
    return EMAIL_SERIALIZER.dumps(email, salt='email-confirm')


def _confirm_email_token(token: str):
    try:
        email = EMAIL_SERIALIZER.loads(token, salt='email-confirm', max_age=EMAIL_TOKEN_MAX_AGE)
        return email
    except (SignatureExpired, BadSignature):
        return None


def _send_confirmation_email(to_email: str, username: str, token: str):
    confirm_url = url_for('confirm_email', token=token, _external=True)
    html = f"""
    <p>Olá, <strong>{username}</strong>!</p>
    <p>Clique no link abaixo para confirmar seu e-mail:</p>
    <p><a href="{confirm_url}">{confirm_url}</a></p>
    <p>O link expira em 30 minutos.</p>
    """
    send_email(to_email, 'Vizy — Confirme seu e-mail', html)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash("Faça login para continuar.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('is_admin'):
            flash("Acesso restrito a administradores.", "error")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)

    return decorated


def is_master_admin() -> bool:
    return session.get('username') == 'admin'


@app.context_processor
def inject_current_user():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        return {'current_user': user}
    return {'current_user': None}


def _seed_admin():
    existing = User.query.filter_by(username='admin').first()
    if not existing:
        admin = User(
            username='admin',
            password_hash=generate_password_hash(ADMIN_DEFAULT_PASSWORD),
            first_name='Admin',
            last_name='Master',
            email_verified=True,
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()


def _seed_default_users():
    default_users = [
        {
            'first_name': 'Beatriz',
            'last_name': 'Fugagnolli Giacon',
            'username': 'beatriz.giacon',
            'email': 'beatriz.giacon@aluno.ufabc.edu.br',
            'password': '11202410010',
        },
        {
            'first_name': 'Jonathan',
            'last_name': 'Ferreira',
            'username': 'j.ferreira',
            'email': 'j.ferreira@aluno.ufabc.edu.br',
            'password': '11201921823',
        },
        {
            'first_name': 'Raphael',
            'last_name': 'Correa do Nascimento',
            'username': 'r.correa',
            'email': 'r.correa@aluno.ufabc.edu.br',
            'password': '11201811432',
        },
        {
            'first_name': 'Rafael',
            'last_name': 'Fernando Pereira',
            'username': 'r.fernando',
            'email': 'r.fernando@aluno.ufabc.edu.br',
            'password': '11201811401',
        },
    ]

    for u in default_users:
        if User.query.filter_by(username=u['username']).first():
            continue

        new_user = User(
            username=u['username'],
            password_hash=generate_password_hash(u['password']),
            first_name=u['first_name'],
            last_name=u['last_name'],
            email=u['email'],
            email_verified=True,
            is_admin=True,
        )
        db.session.add(new_user)

    db.session.commit()


def _seed_camera_apps():
    from models import CameraApp, CameraModel

    apps_data = [
        {
            'name': 'V380',
            'rtsp_template': 'rtsp://{user}:{password}@{ip}:{port}/live/ch00_0',
            'models': ['VR CAM']
        },
        {
            'name': 'Yoosee',
            'rtsp_template': 'rtsp://{user}:{password}@{ip}:{port}/onvif1',
            'models': ['LeBoss']
        }, {
            'name': 'Genérico / ONVIF',
            'rtsp_template': 'rtsp://{user}:{password}@{ip}:{port}/stream1',
            'models': ['Genérico']
        },
    ]

    for app_data in apps_data:
        app_obj = CameraApp.query.filter_by(name=app_data['name']).first()
        if not app_obj:
            app_obj = CameraApp(
                name=app_data['name'],
                rtsp_template=app_data['rtsp_template']
            )
            db.session.add(app_obj)
            db.session.flush()

        for model_name in app_data['models']:
            if not CameraModel.query.filter_by(app_id=app_obj.id, name=model_name).first():
                db.session.add(CameraModel(app_id=app_obj.id, name=model_name))

    db.session.commit()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'login':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            user = User.query.filter_by(username=username).first()

            if not user or not check_password_hash(user.password_hash, password):
                flash("Usuário ou senha inválidos.", "error")
                return redirect(url_for('login'))

            if not user.email_verified:
                flash("Confirme seu e-mail antes de fazer login.", "error")
                return redirect(url_for('login'))

            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            return redirect(url_for('dashboard'))

        elif action == 'register':
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip().lower()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            if password != confirm_password:
                flash("As senhas não coincidem.", "error")
                return redirect(url_for('login'))

            if len(password) < 8:
                flash("A senha deve ter no mínimo 8 caracteres.", "error")
                return redirect(url_for('login'))

            if User.query.filter_by(username=username).first():
                flash("Nome de usuário já em uso.", "error")
                return redirect(url_for('login'))

            if User.query.filter_by(email=email).first() or \
                    User.query.filter_by(email_pending=email).first():
                flash("E-mail já cadastrado.", "error")
                return redirect(url_for('login'))

            new_user = User(
                username=username,
                password_hash=generate_password_hash(password),
                first_name=first_name,
                last_name=last_name,
                email_pending=email,
                email_verified=False,
                is_admin=False
            )
            db.session.add(new_user)
            db.session.commit()

            token = _generate_email_token(email)
            _send_confirmation_email(email, username, token)
            flash("Conta criada! Verifique seu e-mail para confirmar.", "success")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash("Sessão encerrada.", "success")
    return redirect(url_for('login'))


@app.route('/confirm-email/<token>')
def confirm_email(token):
    email = _confirm_email_token(token)
    if not email:
        flash("Link inválido ou expirado.", "error")
        return redirect(url_for('login'))

    user = User.query.filter_by(email_pending=email).first()
    if not user:
        flash("Nenhum cadastro pendente para este e-mail.", "error")
        return redirect(url_for('login'))

    user.email = email
    user.email_pending = None
    user.email_verified = True
    db.session.commit()
    flash("E-mail confirmado com sucesso! Faça o login.", "success")
    return redirect(url_for('login'))


@app.route('/resend-confirmation', methods=['POST'])
def resend_confirmation():
    email = request.form.get('email', '').strip().lower()
    user = User.query.filter_by(email_pending=email, email_verified=False).first()
    if user:
        token = _generate_email_token(email)
        _send_confirmation_email(email, user.username, token)
    flash("Se este e-mail estiver cadastrado e pendente, um novo link foi enviado.", "success")
    return redirect(url_for('login'))


@app.route('/')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/users', methods=['GET', 'POST'])
@admin_required
def users():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip().lower()
        email_verified = request.form.get('email_verified') == '1'

        make_admin = False
        if is_master_admin() and request.form.get('is_admin') == '1':
            make_admin = True

        if not username or not password:
            flash("Usuário e senha são obrigatórios.", "error")
            return redirect(url_for('users'))

        if User.query.filter_by(username=username).first():
            flash("Nome de usuário já em uso.", "error")
            return redirect(url_for('users'))

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            is_admin=make_admin
        )

        if email:
            if email_verified:
                new_user.email = email
                new_user.email_verified = True
            else:
                new_user.email_pending = email
                new_user.email_verified = False
                token = _generate_email_token(email)
                _send_confirmation_email(email, username, token)
        else:
            new_user.email_verified = True

        db.session.add(new_user)
        db.session.commit()
        flash(f"Usuário '{username}' cadastrado com sucesso!", "success")
        return redirect(url_for('users'))

    all_users = User.query.all()
    return render_template('users.html', users=all_users)


@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if not is_master_admin() and user.is_admin:
        flash("Apenas o admin master pode editar contas de administradores.", "error")
        return redirect(url_for('users'))

    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        new_username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        email = request.form.get('email', '').strip().lower()
        force_verified = request.form.get('force_verified') == '1'

        if is_master_admin() and user.username != 'admin':
            user.is_admin = request.form.get('is_admin') == '1'

        if user.username == 'admin':
            new_username = 'admin'

        if new_username and new_username != user.username:
            if User.query.filter_by(username=new_username).first():
                flash("Nome de usuário já em uso.", "error")
                return redirect(url_for('edit_user', user_id=user_id))
            user.username = new_username

        user.first_name = first_name
        user.last_name = last_name

        if password:
            user.password_hash = generate_password_hash(password)

        if user.id == session.get('user_id'):
            session['username'] = user.username
            session['is_admin'] = user.is_admin

        if email:
            email_changed = (email != user.email and email != user.email_pending)
            if email_changed:
                if force_verified:
                    user.email = email
                    user.email_pending = None
                    user.email_verified = True
                else:
                    user.email_pending = email
                    user.email_verified = False
                    token = _generate_email_token(email)
                    _send_confirmation_email(email, user.username, token)
            elif force_verified and not user.email_verified:
                user.email = user.email_pending or user.email
                user.email_pending = None
                user.email_verified = True

        db.session.commit()
        flash(f"Usuário '{user.username}' atualizado!", "success")
        return redirect(url_for('users'))

    return render_template('edit_user.html', user=user)


@app.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.username == 'admin':
        flash("A conta admin master não pode ser excluída.", "error")
        return redirect(url_for('users'))

    if not is_master_admin() and user.is_admin:
        flash("Apenas o admin master pode excluir contas de administradores.", "error")
        return redirect(url_for('users'))

    if user.id == session.get('user_id'):
        flash("Você não pode excluir sua própria conta.", "error")
        return redirect(url_for('users'))

    for cam in user.cameras_owned:
        Permission.query.filter_by(camera_id=cam.id).delete()
        GroupPermission.query.filter_by(camera_id=cam.id).delete()
        db.session.delete(cam)
    Permission.query.filter_by(user_id=user_id).delete()
    GroupMember.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    flash(f"Usuário '{user.username}' removido!", "success")
    return redirect(url_for('users'))


@app.route('/groups', methods=['GET', 'POST'])
@login_required
def groups():
    user_id = session['user_id']

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash("O nome do grupo é obrigatório.", "error")
            return redirect(url_for('groups'))

        if Group.query.filter_by(owner_id=user_id, name=name).first():
            flash("Você já possui um grupo com esse nome.", "error")
            return redirect(url_for('groups'))

        group = Group(name=name, description=description, owner_id=user_id)
        db.session.add(group)
        db.session.commit()
        flash(f"Grupo '{name}' criado com sucesso!", "success")
        return redirect(url_for('groups'))

    if is_master_admin():
        all_groups = Group.query.join(User, Group.owner_id == User.id) \
            .order_by(User.username, Group.name).all()
    else:
        all_groups = Group.query.filter_by(owner_id=user_id) \
            .order_by(Group.name).all()

    all_users = User.query.order_by(User.username).all() if is_master_admin() else []
    return render_template('groups.html', groups=all_groups, all_users=all_users)


@app.route('/groups/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_group(group_id):
    group = Group.query.get_or_404(group_id)

    if not is_master_admin() and group.owner_id != session['user_id']:
        flash("Você não tem permissão para editar este grupo.", "error")
        return redirect(url_for('groups'))

    owner = User.query.get(group.owner_id)
    owner_cameras = Camera.query.filter_by(owner_id=group.owner_id).all()
    all_users = User.query.order_by(User.username).all()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_info':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            if not name:
                flash("O nome do grupo é obrigatório.", "error")
                return redirect(url_for('edit_group', group_id=group_id))
            existing = Group.query.filter_by(owner_id=group.owner_id, name=name).first()
            if existing and existing.id != group_id:
                flash("Já existe um grupo com esse nome.", "error")
                return redirect(url_for('edit_group', group_id=group_id))
            group.name = name
            group.description = description
            db.session.commit()
            flash("Grupo atualizado!", "success")

        elif action == 'add_member':
            uid = request.form.get('user_id', type=int)
            if uid:
                if GroupMember.query.filter_by(group_id=group_id, user_id=uid).first():
                    flash("Usuário já é membro deste grupo.", "error")
                else:
                    db.session.add(GroupMember(group_id=group_id, user_id=uid))
                    db.session.commit()
                    flash("Membro adicionado!", "success")

        elif action == 'remove_member':
            member_id = request.form.get('member_id', type=int)
            member = GroupMember.query.get(member_id)
            if member and member.group_id == group_id:
                db.session.delete(member)
                db.session.commit()
                flash("Membro removido.", "success")

        elif action == 'add_camera':
            camera_id = request.form.get('camera_id', type=int)
            can_view = request.form.get('can_view') == '1'
            if camera_id:
                cam = Camera.query.get(camera_id)
                if not cam or cam.owner_id != group.owner_id:
                    flash("Câmera inválida.", "error")
                elif GroupPermission.query.filter_by(group_id=group_id, camera_id=camera_id).first():
                    flash("Câmera já está vinculada a este grupo.", "error")
                else:
                    db.session.add(GroupPermission(
                        group_id=group_id, camera_id=camera_id,
                        can_view=can_view))
                    db.session.commit()
                    flash("Câmera adicionada ao grupo!", "success")

        elif action == 'remove_camera':
            gp_id = request.form.get('gp_id', type=int)
            gp = GroupPermission.query.get(gp_id)
            if gp and gp.group_id == group_id:
                db.session.delete(gp)
                db.session.commit()
                flash("Câmera removida do grupo.", "success")

        return redirect(url_for('edit_group', group_id=group_id))

    member_ids = {m.user_id for m in group.members}
    camera_ids = {gp.camera_id for gp in group.permissions}
    non_members = [u for u in all_users if u.id not in member_ids and u.id != group.owner_id]
    avail_cameras = [c for c in owner_cameras if c.id not in camera_ids]

    return render_template('edit_group.html',
                           group=group,
                           owner=owner,
                           non_members=non_members,
                           avail_cameras=avail_cameras)


@app.route('/groups/<int:group_id>/delete', methods=['POST'])
@login_required
def delete_group(group_id):
    group = Group.query.get_or_404(group_id)

    if not is_master_admin() and group.owner_id != session['user_id']:
        flash("Você não tem permissão para excluir este grupo.", "error")
        return redirect(url_for('groups'))

    db.session.delete(group)
    db.session.commit()
    flash(f"Grupo '{group.name}' removido!", "success")
    return redirect(url_for('groups'))


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get_or_404(session['user_id'])

    if request.method == 'POST':
        action = request.form.get('action', 'update_info')

        if action == 'update_info':
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            user.first_name = first_name
            user.last_name = last_name
            db.session.commit()
            flash("Perfil atualizado!", "success")

        elif action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')

            if not check_password_hash(user.password_hash, current_pw):
                flash("Senha atual incorreta.", "error")
                return redirect(url_for('profile'))

            if len(new_pw) < 8:
                flash("A nova senha deve ter no mínimo 8 caracteres.", "error")
                return redirect(url_for('profile'))

            if new_pw != confirm_pw:
                flash("As senhas não coincidem.", "error")
                return redirect(url_for('profile'))

            user.password_hash = generate_password_hash(new_pw)
            db.session.commit()
            flash("Senha alterada com sucesso!", "success")

        elif action == 'upload_photo':
            file = request.files.get('photo')
            if file and file.filename and _allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{user.id}.{ext}"
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                # Remove old photo if different extension
                for old_ext in ALLOWED_EXTENSIONS:
                    old_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{user.id}.{old_ext}")
                    if old_ext != ext and os.path.exists(old_path):
                        os.remove(old_path)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user.profile_photo = f"uploads/avatars/{filename}"
                db.session.commit()
                flash("Foto de perfil atualizada!", "success")
            else:
                flash("Formato de arquivo inválido. Use PNG, JPG, GIF ou WebP.", "error")

        elif action == 'remove_photo':
            if user.profile_photo:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                        os.path.basename(user.profile_photo))
                if os.path.exists(old_path):
                    os.remove(old_path)
                user.profile_photo = None
                db.session.commit()
                flash("Foto removida.", "success")

        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)


def _migrate_db():
    """Apply schema migrations not handled by db.create_all()."""
    from sqlalchemy import text
    migrations = [
        "ALTER TABLE user ADD COLUMN profile_photo VARCHAR(200)",
    ]
    with db.engine.connect() as conn:
        for sql in migrations:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                pass  # Column already exists or other benign error


with app.app_context():
    db.create_all()
    _migrate_db()
    _seed_admin()
    _seed_camera_apps()
    _seed_default_users()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
