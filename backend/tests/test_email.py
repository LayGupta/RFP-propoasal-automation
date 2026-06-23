"""test_email.py — Email service tests"""

from unittest.mock import patch, MagicMock


def test_send_email_success():
    with patch("app.services.email_service.get_settings") as mock_settings:
        mock_settings.return_value.SMTP_USER = "test@gmail.com"
        mock_settings.return_value.SMTP_PASSWORD = "testpass"
        mock_settings.return_value.SMTP_HOST = "smtp.gmail.com"
        mock_settings.return_value.SMTP_PORT = 587

        with patch("app.services.email_service.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            from app.services.email_service import send_email
            result = send_email("recipient@example.com", "Test Subject", "Test body")
            assert result is True


def test_send_email_no_credentials():
    with patch("app.services.email_service.get_settings") as mock_settings:
        mock_settings.return_value.SMTP_USER = ""
        mock_settings.return_value.SMTP_PASSWORD = ""

        from app.services.email_service import send_email
        result = send_email("recipient@example.com", "Test", "Body")
        assert result is False
