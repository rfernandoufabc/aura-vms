from datetime import datetime

from extensions import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    email_verified = db.Column(db.Boolean, default=False)
    email_pending = db.Column(db.String(120), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cameras_owned = db.relationship('Camera', backref='owner', lazy=True)
    permissions = db.relationship('Permission', backref='user', lazy=True)
    group_memberships = db.relationship('GroupMember', backref='user', lazy=True)


class AuthToken(db.Model):
    __tablename__ = 'auth_token'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(128), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token_type = db.Column(db.String(20), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref='auth_tokens', lazy=True)


class Camera(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    app_id = db.Column(db.Integer, db.ForeignKey('camera_app.id'), nullable=True)
    model_id = db.Column(db.Integer, db.ForeignKey('camera_model.id'), nullable=True)
    app_brand = db.Column(db.String(80))
    model_name = db.Column(db.String(80))
    ip_address = db.Column(db.String(120), nullable=False)
    port = db.Column(db.String(10), default='554')
    cam_username = db.Column(db.String(80))
    cam_password = db.Column(db.String(80))
    show_active_viewers = db.Column(db.Boolean, default=False)
    permissions = db.relationship('Permission', backref='camera', lazy=True)
    group_permissions = db.relationship('GroupPermission', backref='camera', lazy=True)


class CameraApp(db.Model):
    __tablename__ = 'camera_app'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    rtsp_template = db.Column(db.String(200), nullable=False)
    models = db.relationship('CameraModel', backref='app', lazy=True)
    cameras = db.relationship('Camera', backref='app', lazy=True)


class CameraModel(db.Model):
    __tablename__ = 'camera_model'
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('camera_app.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    cameras = db.relationship('Camera', backref='model_ref', lazy=True)


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'), nullable=False)
    can_view = db.Column(db.Boolean, default=True)
    can_control = db.Column(db.Boolean, default=False)


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', backref='groups_owned', lazy=True)
    members = db.relationship('GroupMember', backref='group', lazy=True, cascade='all, delete-orphan')
    permissions = db.relationship('GroupPermission', backref='group', lazy=True, cascade='all, delete-orphan')
    __table_args__ = (db.UniqueConstraint('owner_id', 'name', name='uq_group_owner_name'),)


class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('group_id', 'user_id', name='uq_group_member'),)


class GroupPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'), nullable=False)
    can_view = db.Column(db.Boolean, default=True)
    can_control = db.Column(db.Boolean, default=False)
    __table_args__ = (db.UniqueConstraint('group_id', 'camera_id', name='uq_group_camera'),)
