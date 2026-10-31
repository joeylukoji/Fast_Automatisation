"""Envoi Gmail via SMTP + mot de passe d'application (raccourci de hackathon).

Un vrai connecteur passerait par OAuth 2.0 ; ici on évite cette configuration.
Créer un « mot de passe d'application » dans le compte Google (2FA requise).
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage


def send_email(to: str, subject: str, body: str, html: str | None = None) -> dict:
    """html facultatif : e-mail multipart (texte + alternative HTML)."""
    user = os.getenv("KERNEL_GMAIL_USER")
    password = os.getenv("KERNEL_GMAIL_APP_PASSWORD")
    if not user or not password:
        raise RuntimeError("KERNEL_GMAIL_USER et KERNEL_GMAIL_APP_PASSWORD doivent être définis.")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = user, to, subject
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
    return {"sent_to": to}
