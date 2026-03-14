import threading

from functools import wraps

from flask import Blueprint, session, jsonify

from models import Camera, Permission, GroupPermission, GroupMember, Group, User

view_bp = Blueprint('view', __name__)

# ── Active viewer tracking ──────────────────────────────────────────────────
_viewers_lock = threading.Lock()
_camera_viewers: dict = {}   # cam_id (int) -> set of user_ids


def _add_viewer(cam_id: int, user_id: int) -> int:
    with _viewers_lock:
        if cam_id not in _camera_viewers:
            _camera_viewers[cam_id] = set()
        _camera_viewers[cam_id].add(user_id)
        return len(_camera_viewers[cam_id])


def _remove_viewer(cam_id: int, user_id: int) -> int:
    with _viewers_lock:
        if cam_id in _camera_viewers:
            _camera_viewers[cam_id].discard(user_id)
            count = len(_camera_viewers[cam_id])
            if count == 0:
                del _camera_viewers[cam_id]
            return count
        return 0


def _get_viewer_ids(cam_id: int) -> set:
    with _viewers_lock:
        return set(_camera_viewers.get(cam_id, set()))


def _is_first_viewer(cam_id: int) -> bool:
    """Returns True when the camera has no viewers yet (before adding the new one)."""
    with _viewers_lock:
        return cam_id not in _camera_viewers or len(_camera_viewers[cam_id]) == 0


def _is_last_viewer(cam_id: int, user_id: int) -> bool:
    """Returns True when this user is the only viewer of the camera."""
    with _viewers_lock:
        viewers = _camera_viewers.get(cam_id, set())
        return viewers == {user_id} or len(viewers) == 0


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            from flask import redirect, url_for
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated


def get_accessible_cameras(user_id):
    own_cams = Camera.query.filter_by(owner_id=user_id).all()

    perms = Permission.query.filter_by(user_id=user_id, can_view=True).all()
    perm_cam_ids = {p.camera_id for p in perms}

    memberships = GroupMember.query.filter_by(user_id=user_id).all()
    group_ids = {m.group_id for m in memberships}
    group_perms = GroupPermission.query.filter(
        GroupPermission.group_id.in_(group_ids),
        GroupPermission.can_view == True
    ).all() if group_ids else []
    group_cam_ids = {gp.camera_id for gp in group_perms}

    all_cam_ids = perm_cam_ids | group_cam_ids

    shared_cams = Camera.query.filter(
        Camera.id.in_(all_cam_ids),
        Camera.owner_id != user_id
    ).all() if all_cam_ids else []

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

    grouped = []
    if user_id in owners_map:
        grouped.append(owners_map.pop(user_id))
    grouped.extend(owners_map.values())

    return grouped


def get_accessible_groups_for_view(user_id):
    """Return groups (with their accessible cameras) available for batch-open."""
    accessible_cam_ids = set()
    for g in get_accessible_cameras(user_id):
        for cam in g['cameras']:
            accessible_cam_ids.add(cam.id)

    cam_by_id = {c.id: c for c in Camera.query.filter(
        Camera.id.in_(accessible_cam_ids)
    ).all()} if accessible_cam_ids else {}

    # Owned groups
    owned_groups = Group.query.filter_by(owner_id=user_id).order_by(Group.name).all()
    # Member groups
    memberships = GroupMember.query.filter_by(user_id=user_id).all()
    member_group_ids = {m.group_id for m in memberships}
    member_groups = Group.query.filter(
        Group.id.in_(member_group_ids)
    ).order_by(Group.name).all() if member_group_ids else []

    seen = set()
    result = []
    for group in list(owned_groups) + list(member_groups):
        if group.id in seen:
            continue
        seen.add(group.id)
        gp_list = GroupPermission.query.filter_by(
            group_id=group.id, can_view=True
        ).all()
        cams = [cam_by_id[gp.camera_id]
                for gp in gp_list if gp.camera_id in cam_by_id]
        if cams:
            result.append({'group': group, 'cameras': cams})

    return result


def build_rtsp_url(cam: Camera) -> str:
    if cam.app_id and cam.app and cam.app.rtsp_template:
        return (
            cam.app.rtsp_template
            .replace('{user}', cam.cam_username or '')
            .replace('{password}', cam.cam_password or '')
            .replace('{pass}', cam.cam_password or '')
            .replace('{ip}', cam.ip_address)
            .replace('{port}', cam.port or '554')
        )

    brand = (cam.app_brand or '').lower()
    user_part = ''
    if cam.cam_username:
        pwd = f":{cam.cam_password}" if cam.cam_password else ''
        user_part = f"{cam.cam_username}{pwd}@"

    ip = cam.ip_address
    port = cam.port or '554'

    if 'v380' in brand or 'yoosee' in brand:
        return f"rtsp://{user_part}{ip}:{port}/live/ch00_0"

    if 'onvif' in brand or 'ptz' in brand or 'hikvision' in brand or 'dahua' in brand:
        return f"rtsp://{user_part}{ip}:{port}/onvif1"

    return f"rtsp://{user_part}{ip}:{port}/stream1"


@view_bp.route('/view')
@login_required
def view():
    import os
    import re
    from flask import request, session, render_template
    user_id = session['user_id']
    grouped_cameras = get_accessible_cameras(user_id)
    accessible_groups = get_accessible_groups_for_view(user_id)

    req_hostname = request.host.split(':')[0]

    padrao_ip = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')

    if padrao_ip.match(req_hostname) or req_hostname == 'localhost':
        go2rtc_port = os.environ.get('GO2RTC_PORT', '1984')
        go2rtc_url = f"http://{req_hostname}:{go2rtc_port}"
    else:
        go2rtc_url = f"https://video.{req_hostname}"

    return render_template('view.html',
                           grouped_cameras=grouped_cameras,
                           accessible_groups=accessible_groups,
                           go2rtc_url=go2rtc_url)


@view_bp.route('/view/add-cam/<int:cam_id>', methods=['POST'])
@login_required
def add_cam(cam_id):
    import os, logging
    import requests as req

    user_id = session['user_id']
    cam = Camera.query.get_or_404(cam_id)

    has_access = cam.owner_id == user_id
    if not has_access:
        perm = Permission.query.filter_by(
            camera_id=cam_id, user_id=user_id, can_view=True
        ).first()
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

    go2rtc_base = os.environ.get('GO2RTC_URL', 'http://localhost:1984').rstrip('/')
    stream_name = f"cam_{cam_id}"

    # Only register in go2rtc if this is the first viewer
    first_viewer = _is_first_viewer(cam_id)

    if first_viewer:
        rtsp_url = build_rtsp_url(cam)
        logging.info(f"[go2rtc] Registrando stream '{stream_name}' → {rtsp_url}")
        try:
            resp = req.put(
                f"{go2rtc_base}/api/streams",
                params={'name': stream_name, 'src': rtsp_url},
                timeout=5
            )
            logging.info(f"[go2rtc] Resposta: {resp.status_code} — {resp.text}")
            if resp.status_code not in (200, 201):
                return jsonify({
                    'ok': False,
                    'error': f"go2rtc retornou {resp.status_code}: {resp.text}"
                }), 500
        except req.exceptions.ConnectionError:
            return jsonify({
                'ok': False,
                'error': 'Não foi possível conectar ao go2rtc. Verifique se está rodando.'
            }), 500
        except Exception as e:
            logging.exception("[go2rtc] Erro inesperado")
            return jsonify({'ok': False, 'error': str(e)}), 500
    else:
        logging.info(f"[go2rtc] Stream '{stream_name}' já registrado, reutilizando.")

    count = _add_viewer(cam_id, user_id)
    viewer_ids = _get_viewer_ids(cam_id)
    viewers = []
    for uid in viewer_ids:
        u = User.query.get(uid)
        if u:
            viewers.append({'id': uid, 'username': u.username,
                            'first_name': u.first_name or u.username})

    return jsonify({'ok': True, 'stream': stream_name,
                    'viewer_count': count, 'viewers': viewers})


@view_bp.route('/view/remove-cam/<int:cam_id>', methods=['POST'])
@login_required
def remove_cam(cam_id):
    import os, logging
    import requests as req

    user_id = session['user_id']
    last_viewer = _is_last_viewer(cam_id, user_id)
    _remove_viewer(cam_id, user_id)

    go2rtc_base = os.environ.get('GO2RTC_URL', 'http://localhost:1984').rstrip('/')
    stream_name = f"cam_{cam_id}"

    if last_viewer:
        logging.info(f"[go2rtc] Último viewer saiu. Removendo stream '{stream_name}'")
        try:
            resp = req.delete(
                f"{go2rtc_base}/api/streams",
                params={'name': stream_name},
                timeout=5
            )
            logging.info(f"[go2rtc] Remoção: {resp.status_code}")
        except Exception as e:
            logging.warning(f"[go2rtc] Erro ao remover stream: {e}")
    else:
        logging.info(f"[go2rtc] Stream '{stream_name}' mantido (outros viewers ainda ativos).")

    return jsonify({'ok': True})


@view_bp.route('/view/cam-viewers/<int:cam_id>')
@login_required
def cam_viewers(cam_id):
    """Return the list of users currently viewing a camera."""
    cam = Camera.query.get_or_404(cam_id)
    user_id = session['user_id']

    # Only allow the camera owner or users with access to see viewers
    has_access = cam.owner_id == user_id
    if not has_access:
        perm = Permission.query.filter_by(
            camera_id=cam_id, user_id=user_id, can_view=True
        ).first()
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

    viewer_ids = _get_viewer_ids(cam_id)
    viewers = []
    for uid in viewer_ids:
        u = User.query.get(uid)
        if u:
            viewers.append({'id': uid, 'username': u.username,
                            'first_name': u.first_name or u.username})

    return jsonify({'ok': True, 'viewer_count': len(viewers), 'viewers': viewers})
