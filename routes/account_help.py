import os
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash

from extensions import db
from models import User, AuthToken
from oauth_mail import send_email

account_help_bp = Blueprint('account_help', __name__)


def _build_confirmation_email(username: str, confirm_url: str) -> str:
    return f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;">
        <h2>Confirme seu e-mail — Vizy</h2>
        <p>Olá, <strong>@{username}</strong>!</p>
        <p>Clique no botão abaixo para ativar sua conta:</p>
        <a href="{confirm_url}"
           style="display:inline-block;padding:12px 24px;background:#9D4EDD;
                  color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">
            ✅ Confirmar e-mail
        </a><p style="margin-top:20px;color:#888;font-size:.85em;">
            O link expira em 24 horas. Se não foi você, ignore este e-mail.
        </p>
    </div>
    """


def _build_reset_email(username: str, reset_url: str) -> str:
    return f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;">
        <h2>Redefinição de senha — Vizy</h2>
        <p>Olá, <strong>@{username}</strong>!</p>
        <p>Clique no botão abaixo para criar uma nova senha:</p>
        <a href="{reset_url}"
           style="display:inline-block;padding:12px 24px;background:#9D4EDD;
                  color:#fff;border-radius:8px;text-decoration:none;font-weight:600;">
            🔑 Redefinir senha
        </a>
        <p style="margin-top:20px;color:#888;font-size:.85em;">
            O link expira em 1 hora. Se não foi você, ignore este e-mail.
        </p>
    </div>
    """


@account_help_bp.route('/account-help')
def account_help():
    return render_template('account_help.html')


@account_help_bp.route('/account-help/resend-confirmation', methods=['POST'])
def resend_confirmation():
    email = request.form.get('email', '').strip().lower()

    user = User.query.filter_by(email=email).first()

    if not user or user.email_verified:
        flash('Se o e-mail estiver cadastrado e pendente de confirmação, '
              'você receberá o link em breve.', 'success')
        return redirect(url_for('account_help.account_help'))

    AuthToken.query.filter_by(user_id=user.id, token_type='confirm', used=False).delete()
    db.session.flush()

    token_value = secrets.token_urlsafe(48)
    token = AuthToken(
        token=token_value,
        user_id=user.id,
        token_type='confirm',
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.session.add(token)
    db.session.commit()

    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    confirm_url = f"{base_url}/confirm-email/{token_value}"

    try:
        send_email(
            to_email=user.email,
            subject='Vizy — Confirme seu e-mail',
            html_body=_build_confirmation_email(user.username, confirm_url),
        )
    except Exception as exc:
        db.session.rollback()
        flash('Erro ao enviar e-mail. Tente novamente mais tarde.', 'error')
        return redirect(url_for('account_help.account_help'))

    flash('Se o e-mail estiver cadastrado e pendente de confirmação, '
          'você receberá o link em breve.', 'success')
    return redirect(url_for('account_help.account_help'))


@account_help_bp.route('/account-help/reset-password', methods=['POST'])
def request_reset_password():
    email = request.form.get('email', '').strip().lower()

    user = User.query.filter_by(email=email).first()

    if not user:
        flash('Se o e-mail estiver cadastrado, você receberá o link em breve.', 'success')
        return redirect(url_for('account_help.account_help'))

    AuthToken.query.filter_by(user_id=user.id, token_type='reset', used=False).delete()
    db.session.flush()

    token_value = secrets.token_urlsafe(48)
    token = AuthToken(
        token=token_value,
        user_id=user.id,
        token_type='reset',
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.session.add(token)
    db.session.commit()

    base_url = os.environ.get('BASE_URL', request.host_url.rstrip('/'))
    reset_url = f"{base_url}/reset-password/{token_value}"

    try:
        send_email(
            to_email=user.email,
            subject='Vizy — Redefinição de senha',
            html_body=_build_reset_email(user.username, reset_url),
        )
    except Exception:
        db.session.rollback()
        flash('Erro ao enviar e-mail. Tente novamente mais tarde.', 'error')
        return redirect(url_for('account_help.account_help'))

    flash('Se o e-mail estiver cadastrado, você receberá o link em breve.', 'success')
    return redirect(url_for('account_help.account_help'))


@account_help_bp.route('/confirm-email/<token_value>')
def confirm_email(token_value: str):
    token = AuthToken.query.filter_by(
        token=token_value,
        token_type='confirm',
        used=False,
    ).first()

    if not token or token.expires_at < datetime.utcnow():
        flash('Link inválido ou expirado. Solicite um novo.', 'error')
        return redirect(url_for('account_help.account_help'))

    token.used = True
    token.user.email_verified = True
    db.session.commit()

    flash('E-mail confirmado com sucesso! Faça login.', 'success')
    return redirect(url_for('login'))


@account_help_bp.route('/reset-password/<token_value>', methods=['GET', 'POST'])
def reset_password(token_value: str):
    token = AuthToken.query.filter_by(
        token=token_value,
        token_type='reset',
        used=False,
    ).first()

    if not token or token.expires_at < datetime.utcnow():
        flash('Link inválido ou expirado. Solicite um novo.', 'error')
        return redirect(url_for('account_help.account_help'))

    if request.method == 'GET':
        return render_template('reset_password.html', token=token_value)

    password = request.form.get('password', '')
    confirm = request.form.get('password_confirm', '')

    if len(password) < 8:
        flash('A senha deve ter no mínimo 8 caracteres.', 'error')
        return render_template('reset_password.html', token=token_value)

    if password != confirm:
        flash('As senhas não coincidem.', 'error')
        return render_template('reset_password.html', token=token_value)

    from werkzeug.security import generate_password_hash
    token.user.password_hash = generate_password_hash(password)
    token.used = True
    db.session.commit()

    flash('Senha redefinida com sucesso! Faça login.', 'success')
    return redirect(url_for('login'))
