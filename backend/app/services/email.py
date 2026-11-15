"""Outgoing email."""

import os


def send_reset_email(to_email: str, reset_link: str) -> None:
    """Send the password-reset link over Gmail SMTP. Falls back to logging the
    link if SMTP isn't configured or the send fails, so the flow never hard-crashes."""
    import smtplib
    from email.message import EmailMessage

    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not smtp_user or not smtp_pass:
        print(f"[reset] SMTP not configured — reset link for {to_email}: {reset_link}")
        return

    msg = EmailMessage()
    msg["Subject"] = "Reset your Dishlog password"
    msg["From"]    = smtp_user
    msg["To"]      = to_email
    msg.set_content(
        f"We received a request to reset your Dishlog password.\n\n"
        f"Reset it here (link expires in 1 hour):\n{reset_link}\n\n"
        f"If you didn't request this, you can safely ignore this email."
    )
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception as exc:
        print(f"[reset] Email send failed ({exc}) — link for {to_email}: {reset_link}")
