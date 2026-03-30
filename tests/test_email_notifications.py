import asyncio

import app.services.email as email_service


class TestEmailNotifications:
    def test_send_withdrawal_request_alert_email_invokes_fastmail(self, monkeypatch):
        sent = {}

        async def fake_send_message(self, message):
            sent["subject"] = message.subject
            sent["recipients"] = message.recipients
            sent["body"] = message.body
            return True

        monkeypatch.setattr(email_service.FastMail, "send_message", fake_send_message)

        result = asyncio.run(
            email_service.send_withdrawal_request_alert_email(
                ["admin1@test.com"],
                "Test Partner",
                1250.0,
                "req-123",
                "partner",
            )
        )

        assert result is True
        assert sent["subject"] == "New withdrawal request pending approval"
        assert [recipient.email for recipient in sent["recipients"]] == ["admin1@test.com"]
        assert "req-123" in sent["body"]

    def test_send_withdrawal_request_submitted_email_formats_message(self, monkeypatch):
        sent = {}

        async def fake_send_message(self, message):
            sent["subject"] = message.subject
            sent["recipients"] = message.recipients
            sent["body"] = message.body
            return True

        monkeypatch.setattr(email_service.FastMail, "send_message", fake_send_message)

        result = asyncio.run(
            email_service.send_withdrawal_request_submitted_email(
                "partner@test.com",
                "Partner Test",
                1200.0,
                "req-456",
                "partner",
            )
        )

        assert result is True
        assert sent["subject"] == "Withdrawal request submitted"
        assert [recipient.email for recipient in sent["recipients"]] == ["partner@test.com"]
        assert "req-456" in sent["body"]
