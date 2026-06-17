import smtplib
from email.message import EmailMessage

from ..config import get_settings


def notify_human(to_email: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not to_email or not settings.smtp_host:
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)
    return True

