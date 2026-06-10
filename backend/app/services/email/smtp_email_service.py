from email.message import EmailMessage
import smtplib

from app.core.config import Settings


class EmailConfigurationError(Exception):
    pass


class EmailSendError(Exception):
    pass


class SmtpEmailService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send_html_email(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> None:
        self._validate_configuration()
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.settings.smtp_from_email
        message["To"] = to_email
        message.set_content(text_body)
        message.add_alternative(html_body, subtype="html")

        try:
            if self.settings.smtp_port == 465:
                with smtplib.SMTP_SSL(
                    self.settings.smtp_host,
                    self.settings.smtp_port,
                    timeout=15,
                ) as smtp:
                    self._login_if_configured(smtp)
                    smtp.send_message(message)
            else:
                with smtplib.SMTP(
                    self.settings.smtp_host,
                    self.settings.smtp_port,
                    timeout=15,
                ) as smtp:
                    if self.settings.smtp_user.strip() or self.settings.smtp_password.strip():
                        smtp.starttls()
                    self._login_if_configured(smtp)
                    smtp.send_message(message)
        except smtplib.SMTPException as error:
            raise EmailSendError(f"SMTP send failed: {error}") from error
        except OSError as error:
            raise EmailSendError(f"Could not connect to SMTP server: {error}") from error

    def _validate_configuration(self) -> None:
        if self.settings.smtp_host.strip() == "":
            raise EmailConfigurationError("SMTP_HOST is required.")
        if self.settings.smtp_from_email.strip() == "":
            raise EmailConfigurationError("SMTP_FROM_EMAIL is required.")
        if self.settings.smtp_port <= 0:
            raise EmailConfigurationError("SMTP_PORT must be a positive integer.")

    def _login_if_configured(self, smtp: smtplib.SMTP | smtplib.SMTP_SSL) -> None:
        if self.settings.smtp_user.strip() == "":
            return

        smtp.login(self.settings.smtp_user, self.settings.smtp_password)
