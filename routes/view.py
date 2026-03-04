from flask import Blueprint, render_template, session, jsonify
from functools import wraps
from models import Camera, Permission, GroupPermission, GroupMember
from extensions import db

view_bp = Blueprint('view', __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            from flask import redirect, url_for
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_accessible_cameras(user_id):
    """Retorna câmeras agrupadas por dono que o usuário pode visualizar."""
    from models import User

    # Câmeras próprias
    own_cams = Camera.query.filter_by(owner_id=user_id).all()

    # Câmeras com permissão individual
    perms = Permission.query.filter_by(user_id=user_id, can_view=True).all()
    perm_cam_ids = {p.camera_id for p in perms}

    # Câmeras via grupos
    memberships = GroupMember.query.filter_by(user_id=user_id).all()
    group_ids = {m.group_id for m in memberships}
    group_perms = GroupPermission.query.filter(
        GroupPermission.group_id.in_(group_ids),
        GroupPermission.can_view == True
    ).all() if group_ids else []
    group_cam_ids = {gp.camera_id for gp in group_perms}

    all_cam_ids = perm_cam_ids | group_cam_ids

    # Busca câmeras de outros donos
    shared_cams = Camera.query.filter(
        Camera.id.in_(all_cam_ids),
        Camera.owner_id != user_id
    ).all() if all_cam_ids else []

    # Agrupa por dono
    owners_map = {}
    for cam in own_cams:
        owner = cam.owner
        if owner.id not in owners_map:
            owners_map[owner.id] = {'owner': owner, 'cameras': []}
        owners_map[owner.id]['cameras'].append(cam)

    for cam in shared_cams:
        owner = cam.owner
        if owner.id not in owners_map:
            owners_map[owner.id] = {'owner': owner, 'cameras': []}
        owners_map[owner.id]['cameras'].append(cam)

    # Garante que o próprio usuário apareça primeiro
    grouped = []
    if user_id in owners_map:
        grouped.append(owners_map.pop(user_id))
    grouped.extend(owners_map.values())

    return grouped


@view_bp.route('/view')
@login_required
def view():
    import os
    user_id = session['user_id']
    grouped_cameras = get_accessible_cameras(user_id)
    go2rtc_url = os.environ.get('GO2RTC_URL', 'http://localhost:1984')
    return render_template('view.html',
                           grouped_cameras=grouped_cameras,
                           go2rtc_url=go2rtc_url)


@view_bp.route('/view/add-cam/<int:cam_id>', methods=['POST'])
@login_required
def add_cam(cam_id):
    import subprocess, os
    user_id = session['user_id']

    cam = Camera.query.get_or_404(cam_id)

    # Verifica acesso
    has_access = cam.owner_id == user_id
    if not has_access:
        perm = Permission.query.filter_by(camera_id=cam_id, user_id=user_id, can_view=True).first()
        has_access = perm is not None
    if not has_access:
        memberships = GroupMember.query.filter_by(user_id=user_id).all()
        group_ids = {m.group_id for m in memberships}
        if group_ids:
            gp = GroupPermission.query.filter(
                GroupPermission.camera_id == cam_id,
                GroupPermission.group_id.in_(group_ids),
                GroupPermission.can_view == True
            ).first()
            has_access = gp is not None

    if not has_access:
        return jsonify({'ok': False, 'error': 'Sem permissão'}), 403

    # Monta URL RTSP
    user_part = ''
    if cam.cam_username:
        user_part = f"{cam.cam_username}:{cam.cam_password}@" if cam.cam_password else f"{cam.cam_username}@"
    rtsp_url = f"rtsp://{user_part}{cam.ip_address}:{cam.port or '554'}/stream1"

    # Usa template do app se disponível
    if cam.app_id and cam.app and cam.app.rtsp_template:
        rtsp_url = cam.app.rtsp_template \
            .replace('{user}', cam.cam_username or '') \
            .replace('{password}', cam.cam_password or '') \
            .replace('{ip}', cam.ip_address) \
            .replace('{port}', cam.port or '554')

    go2rtc_url = os.environ.get('GO2RTC_URL', 'http://localhost:1984')
    stream_name = f"cam_{cam_id}"

    try:
        import requests as req
        resp = req.post(
            f"{go2rtc_url}/api/streams",
            params={'name': stream_name, 'src': rtsp_url},
            timeout=5
        )
        return jsonify({'ok': True, 'stream': stream_name})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@view_bp.route('/view/remove-cam/<int:cam_id>', methods=['POST'])
@login_required
def remove_cam(cam_id):
    import os
    go2rtc_url = os.environ.get('GO2RTC_URL', 'http://localhost:1984')
    stream_name = f"cam_{cam_id}"
    try:
        import requests as req
        req.delete(f"{go2rtc_url}/api/streams", params={'name': stream_name}, timeout=5)
    except Exception:
        pass
    return jsonify({'ok': True})