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


def build_rtsp_url(cam: Camera) -> str:
    """Monta a URL RTSP correta baseada no app/modelo da câmera."""

    # Prioridade 1: template do CameraApp cadastrado no banco
    if cam.app_id and cam.app and cam.app.rtsp_template:
        return (
            cam.app.rtsp_template
            .replace('{user}',     cam.cam_username or '')
            .replace('{password}', cam.cam_password or '')
            .replace('{pass}',     cam.cam_password or '')
            .replace('{ip}',       cam.ip_address)
            .replace('{port}',     cam.port or '554')
        )

    # Prioridade 2: detecção pelo app_brand legado
    brand = (cam.app_brand or '').lower()
    user_part = ''
    if cam.cam_username:
        pwd = f":{cam.cam_password}" if cam.cam_password else ''
        user_part = f"{cam.cam_username}{pwd}@"

    ip   = cam.ip_address
    port = cam.port or '554'

    if 'v380' in brand or 'yoosee' in brand:
        # V380 / Yoosee (Airwick, Lâmpada)
        return f"rtsp://{user_part}{ip}:{port}/live/ch00_0"

    if 'onvif' in brand or 'ptz' in brand or 'hikvision' in brand or 'dahua' in brand:
        # Câmeras PTZ compatíveis com ONVIF
        return f"rtsp://{user_part}{ip}:{port}/onvif1"

    # Fallback genérico
    return f"rtsp://{user_part}{ip}:{port}/stream1"


@view_bp.route('/view')
@login_required
def view():
    import os
    from flask import request
    user_id = session['user_id']
    grouped_cameras = get_accessible_cameras(user_id)

    # Porta do go2rtc (pode ser sobrescrita por variável de ambiente)
    go2rtc_port = os.environ.get('GO2RTC_PORT', '1984')

    # Usa o mesmo host que o cliente usou para acessar o Flask,
    # mas substitui a porta pela do go2rtc
    req_host = request.host.split(':')[0]  # ex: "192.168.137.1" ou "localhost"
    go2rtc_url = f"http://{req_host}:{go2rtc_port}"

    return render_template('view.html',
                           grouped_cameras=grouped_cameras,
                           go2rtc_url=go2rtc_url)


@view_bp.route('/view/add-cam/<int:cam_id>', methods=['POST'])
@login_required
def add_cam(cam_id):
    import os, logging
    import requests as req

    user_id = session['user_id']
    cam = Camera.query.get_or_404(cam_id)

    # ── Verifica acesso ──────────────────────────────────────────────
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

    # ── Monta URL RTSP ───────────────────────────────────────────────
    rtsp_url    = build_rtsp_url(cam)
    go2rtc_base = os.environ.get('GO2RTC_URL', 'http://localhost:1984').rstrip('/')
    stream_name = f"cam_{cam_id}"

    logging.info(f"[go2rtc] Registrando stream '{stream_name}' → {rtsp_url}")

    try:
        # PUT /api/streams cria ou sobrescreve a stream (correto conforme OpenAPI)
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

        return jsonify({'ok': True, 'stream': stream_name})

    except req.exceptions.ConnectionError:
        return jsonify({
            'ok': False,
            'error': 'Não foi possível conectar ao go2rtc. Verifique se está rodando.'
        }), 500
    except Exception as e:
        logging.exception("[go2rtc] Erro inesperado")
        return jsonify({'ok': False, 'error': str(e)}), 500


@view_bp.route('/view/remove-cam/<int:cam_id>', methods=['POST'])
@login_required
def remove_cam(cam_id):
    import os, logging
    import requests as req

    go2rtc_base = os.environ.get('GO2RTC_URL', 'http://localhost:1984').rstrip('/')
    stream_name = f"cam_{cam_id}"

    logging.info(f"[go2rtc] Removendo stream '{stream_name}'")

    try:
        resp = req.delete(
            f"{go2rtc_base}/api/streams",
            params={'name': stream_name},
            timeout=5
        )
        logging.info(f"[go2rtc] Remoção: {resp.status_code}")
    except Exception as e:
        logging.warning(f"[go2rtc] Erro ao remover stream: {e}")

    return jsonify({'ok': True})
