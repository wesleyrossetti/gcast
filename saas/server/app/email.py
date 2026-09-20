from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER

logger = logging.getLogger("app.email")


def send_invite_email(to: str, org_name: str, role: str, invite_link: str) -> None:
    subject = f"Convite para {org_name} — Chromecast Manager"
    text = (
        f"Você foi convidado para a organização \"{org_name}\" no Chromecast Manager "
        f"como {role}.\n\nAceite o convite (expira em 7 dias):\n{invite_link}\n"
    )
    html = f"""
    <div style="font-family:sans-serif;max-width:480px">
      <h2>Você foi convidado!</h2>
      <p>Você foi convidado para a organização <strong>{org_name}</strong> no
      Chromecast Manager, como <strong>{role}</strong>.</p>
      <p><a href="{invite_link}" style="background:#e84343;color:#fff;padding:10px 20px;
         border-radius:6px;text-decoration:none;display:inline-block">Aceitar convite</a></p>
      <p style="color:#888;font-size:0.85em">Esse link expira em 7 dias. Se você não
      esperava esse convite, pode ignorar este e-mail.</p>
    </div>
    """

    if not SMTP_HOST:
        logger.warning(
            "SMTP não configurado — link de convite para %s (org=%s, role=%s): %s",
            to, org_name, role, invite_link,
        )
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            if SMTP_USER:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM, [to], msg.as_string())
        logger.info("E-mail de convite enviado para %s", to)
    except Exception as exc:
        logger.error("Falha ao enviar e-mail de convite para %s: %s", to, exc)
        logger.warning("Link de convite (fallback após falha de envio): %s", invite_link)
