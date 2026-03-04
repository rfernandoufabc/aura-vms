from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from extensions import db
from models import Camera, CameraApp, CameraModel, Permission, GroupPermission, User, Group
from functools import wraps

cameras_bp = Blueprint('cameras', __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def is_master_admin():
    return session.get('is_admin') and session.get('username') == 'admin'

# ── API: lista apps/modelos para o formulário JS ──
@cameras_bp.route('/api/camera-apps')
@login_required
def api_camera_apps():
    apps = CameraApp.query.all()
    return jsonify([{
        'id': a.id,
        'name': a.name,
        'rtsp_template': a.rtsp_template,
        'models': [{'id': m.id, 'name': m.name} for m in a.models]
    } for a in apps])

# ── Listar câmeras ──
@cameras_bp.route('/cameras', methods=['GET', 'POST'])
@login_required
def cameras():
    user_id = session['user_id']

    if request.method == 'POST':
        name        = request.form.get('name', '').strip()
        app_id      = request.form.get('app_id', type=int)
        model_id    = request.form.get('model_id', type=int)
        ip_address  = request.form.get('ip_address', '').strip()
        port        = request.form.get('port', '554').strip()
        cam_user    = request.form.get('cam_username', '').strip()
        cam_pass    = request.form.get('cam_password', '')
        show_active = request.form.get('show_active_viewers') == '1'

        if not ip_address:
            flash("Endereço IP é obrigatório.", "error")
            return redirect(url_for('cameras.cameras'))

        # Preenche app_brand/model_name a partir dos novos models
        app_brand  = None
        model_name = None
        if app_id:
            app_obj = CameraApp.query.get(app_id)
            if app_obj:
                app_brand = app_obj.name
        if model_id:
            model_obj = CameraModel.query.get(model_id)
            if model_obj:
                model_name = model_obj.name

        cam = Camera(
            owner_id=user_id,
            name=name,
            app_id=app_id,
            model_id=model_id,
            app_brand=app_brand,
            model_name=model_name,
            ip_address=ip_address,
            port=port,
            cam_username=cam_user,
            cam_password=cam_pass,
            show_active_viewers=show_active
        )
        db.session.add(cam)
        db.session.commit()
        flash("Câmera adicionada!", "success")
        return redirect(url_for('cameras.cameras'))

    own_cams = Camera.query.filter_by(owner_id=user_id).all()
    cams_by_user = None
    all_users = []

    if is_master_admin():
        all_users_q = User.query.order_by(User.username).all()
        cams_by_user = {}
        for u in all_users_q:
            cams_by_user[u] = Camera.query.filter_by(owner_id=u.id).all()
        all_users = all_users_q

    return render_template('cameras.html',
                           own_cams=own_cams,
                           cams_by_user=cams_by_user,
                           all_users=all_users)


# ── Editar câmera ──
@cameras_bp.route('/cameras/<int:cam_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_camera(cam_id):
    cam = Camera.query.get_or_404(cam_id)
    user_id = session['user_id']

    if cam.owner_id != user_id and not is_master_admin():
        flash("Sem permissão.", "error")
        return redirect(url_for('cameras.cameras'))

    all_users  = User.query.order_by(User.username).all()
    all_groups = Group.query.filter_by(owner_id=cam.owner_id).order_by(Group.name).all()

    # Usuários que já têm permissão
    permitted_user_ids  = {p.user_id for p in cam.permissions}
    # Grupos que já têm permissão
    permitted_group_ids = {gp.group_id for gp in cam.group_permissions}

    # Usuários disponíveis (exceto o dono)
    available_users  = [u for u in all_users  if u.id != cam.owner_id and u.id not in permitted_user_ids]
    # Grupos disponíveis
    available_groups = [g for g in all_groups if g.id not in permitted_group_ids]

    if request.method == 'POST':
        action = request.form.get('action', 'update')

        if action == 'update':
            cam.name = request.form.get('name', '').strip()
            cam.ip_address = request.form.get('ip_address', '').strip()
            cam.port = request.form.get('port', '554').strip()
            cam.cam_username = request.form.get('cam_username', '').strip()
            new_pass = request.form.get('cam_password', '')
            if new_pass:
                cam.cam_password = new_pass
            cam.show_active_viewers = request.form.get('show_active_viewers') == '1'

            # Atualiza app/modelo pelos IDs
            app_id = request.form.get('app_id', type=int)
            model_id = request.form.get('model_id', type=int)
            cam.app_id = app_id
            cam.model_id = model_id
            cam.app_brand = CameraApp.query.get(app_id).name if app_id else ''
            cam.model_name = CameraModel.query.get(model_id).name if model_id else ''

            db.session.commit()
            flash("Câmera atualizada!", "success")

        elif action == 'add_user_permission':
            uid       = request.form.get('user_id', type=int)
            can_view  = request.form.get('can_view')    == '1'
            can_ctrl  = request.form.get('can_control') == '1'
            if uid and not Permission.query.filter_by(camera_id=cam_id, user_id=uid).first():
                db.session.add(Permission(
                    camera_id=cam_id, user_id=uid,
                    can_view=can_view, can_control=can_ctrl
                ))
                db.session.commit()
                flash("Permissão adicionada!", "success")

        elif action == 'remove_user_permission':
            perm_id = request.form.get('perm_id', type=int)
            perm = Permission.query.get(perm_id)
            if perm and perm.camera_id == cam_id:
                db.session.delete(perm)
                db.session.commit()
                flash("Permissão removida.", "success")

        elif action == 'add_group_permission':
            gid      = request.form.get('group_id', type=int)
            can_view = request.form.get('can_view')    == '1'
            can_ctrl = request.form.get('can_control') == '1'
            if gid and not GroupPermission.query.filter_by(camera_id=cam_id, group_id=gid).first():
                db.session.add(GroupPermission(
                    camera_id=cam_id, group_id=gid,
                    can_view=can_view, can_control=can_ctrl
                ))
                db.session.commit()
                flash("Permissão de grupo adicionada!", "success")

        elif action == 'remove_group_permission':
            gp_id = request.form.get('gp_id', type=int)
            gp = GroupPermission.query.get(gp_id)
            if gp and gp.camera_id == cam_id:
                db.session.delete(gp)
                db.session.commit()
                flash("Permissão de grupo removida.", "success")

        return redirect(url_for('cameras.edit_camera', cam_id=cam_id))

    return render_template('edit_camera.html',
                           cam=cam,
                           available_users=available_users,
                           available_groups=available_groups)


# ── Deletar câmera ──
@cameras_bp.route('/cameras/<int:cam_id>/delete', methods=['POST'])
@login_required
def delete_camera(cam_id):
    cam = Camera.query.get_or_404(cam_id)
    if cam.owner_id != session['user_id'] and not is_master_admin():
        flash("Sem permissão.", "error")
        return redirect(url_for('cameras.cameras'))

    Permission.query.filter_by(camera_id=cam_id).delete()
    GroupPermission.query.filter_by(camera_id=cam_id).delete()
    db.session.delete(cam)
    db.session.commit()
    flash("Câmera removida!", "success")
    return redirect(url_for('cameras.cameras'))


# ── Transferir câmera (master admin) ──
@cameras_bp.route('/cameras/<int:cam_id>/transfer', methods=['POST'])
@login_required
def transfer_camera(cam_id):
    if not is_master_admin():
        flash("Sem permissão.", "error")
        return redirect(url_for('cameras.cameras'))

    cam = Camera.query.get_or_404(cam_id)
    new_owner_id = request.form.get('new_owner_id', type=int)
    if new_owner_id:
        cam.owner_id = new_owner_id
        db.session.commit()
        flash("Câmera transferida!", "success")
    return redirect(url_for('cameras.cameras'))