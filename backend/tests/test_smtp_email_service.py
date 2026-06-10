import unittest

from app.core.config import Settings
from app.services.email.smtp_email_service import (
    EmailConfigurationError,
    SmtpEmailService,
)


class SmtpEmailServiceTests(unittest.TestCase):
    def test_missing_host_raises_configuration_error(self) -> None:
        service = SmtpEmailService(
            Settings(
                smtp_host="",
                smtp_from_email="noreply@example.com",
            )
        )

        with self.assertRaises(EmailConfigurationError):
            service.send_html_email(
                to_email="user@example.com",
                subject="Digest",
                html_body="<p>Hello</p>",
                text_body="Hello",
            )

    def test_missing_from_email_raises_configuration_error(self) -> None:
        service = SmtpEmailService(
            Settings(
                smtp_host="smtp.example.com",
                smtp_from_email="",
            )
        )

        with self.assertRaises(EmailConfigurationError):
            service.send_html_email(
                to_email="user@example.com",
                subject="Digest",
                html_body="<p>Hello</p>",
                text_body="Hello",
            )


if __name__ == "__main__":
    unittest.main()
