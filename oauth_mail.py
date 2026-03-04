# oauth_mail.py
import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


GMAIL_USER = os.environ.get('GMAIL_USER', '')
GMAIL_PASS = os.environ.get('GMAIL_PASS', '')


def send_email(to_email: str, subject: str, html_body: str) -> None:
    """Envia um e-mail HTML via Gmail SMTP.

    Raises:
        ValueError: se as credenciais não estiverem configuradas.
        smtplib.SMTPException: em caso de falha no envio.
    """
    if not GMAIL_USER or not GMAIL_PASS:
        raise ValueError(
            "Credenciais de e-mail não configuradas. "
            "Defina GMAIL_USER e GMAIL_PASS nas variáveis de ambiente."
        )

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = GMAIL_USER
    msg['To']      = to_email
    msg.attach(MIMEText(html_body, 'html'))

    context = ssl.create_default_context()
    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.login(GMAIL_USER, GMAIL_PASS)
        smtp.sendmail(GMAIL_USER, to_email, msg.as_string())