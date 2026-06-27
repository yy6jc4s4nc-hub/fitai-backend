import os
import smtplib
from email.message import EmailMessage


def smtp_configured() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def send_password_reset_email(*, to_email: str, code: str) -> None:
    if not smtp_configured():
        raise RuntimeError("SMTP не настроен на сервере")

    message = EmailMessage()
    message["Subject"] = "FitAI — код для сброса пароля"
    message["From"] = os.environ["SMTP_FROM"]
    message["To"] = to_email
    message.set_content(
        f"Ваш код для сброса пароля FitAI: {code}\n\n"
        f"Код действует 15 минут.\n"
        f"Если вы не запрашивали сброс, просто проигнорируйте это письмо."
    )

    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASSWORD")

    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(message)
