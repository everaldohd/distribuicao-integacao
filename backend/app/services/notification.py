"""Serviço de notificação por e-mail usando smtplib."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def _send_email(to: str, subject: str, html_body: str):
    if not settings.SMTP_USER:
        logger.warning(f"SMTP não configurado. E-mail para {to} não enviado: {subject}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to, msg.as_string())
        logger.info(f"E-mail enviado para {to}: {subject}")
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail para {to}: {e}")


def notify_schedule_published(user_email: str, user_name: str, year: int, month: int):
    subject = f"Escala {month:02d}/{year} publicada"
    body = f"""
    <p>Olá, <b>{user_name}</b>!</p>
    <p>A escala de <b>{month:02d}/{year}</b> foi publicada. Acesse o sistema para consultar suas atribuições.</p>
    """
    _send_email(user_email, subject, body)


def notify_exchange_requested(target_email: str, target_name: str, requester_name: str):
    subject = "Solicitação de troca de escala recebida"
    body = f"""
    <p>Olá, <b>{target_name}</b>!</p>
    <p><b>{requester_name}</b> solicitou uma troca de escala com você. Acesse o sistema para aceitar ou recusar.</p>
    """
    _send_email(target_email, subject, body)


def notify_exchange_resolved(requester_email: str, requester_name: str, accepted: bool):
    status = "aceita" if accepted else "recusada"
    subject = f"Sua solicitação de troca foi {status}"
    body = f"""
    <p>Olá, <b>{requester_name}</b>!</p>
    <p>Sua solicitação de troca de escala foi <b>{status}</b>.</p>
    """
    _send_email(requester_email, subject, body)


def notify_manual_fill(user_email: str, user_name: str, shift_date: str, shift_type: str):
    subject = "Seu turno foi atribuído manualmente"
    body = f"""
    <p>Olá, <b>{user_name}</b>!</p>
    <p>Um gestor atribuiu você manualmente ao turno <b>{shift_type}</b> do dia <b>{shift_date}</b>.</p>
    """
    _send_email(user_email, subject, body)
