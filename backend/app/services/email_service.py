"""
Development/mock email provider.

In production this would be swapped for a real provider (SES, SendGrid,
Postmark, etc.) behind the same interface. For now it just records what
would have been sent, so tests and local dev can inspect it without a
real inbox.
"""
from typing import List, Dict


class MockEmailService:
    def __init__(self) -> None:
        self.sent_emails: List[Dict[str, str]] = []

    def send_verification_email(self, to_email: str, token: str) -> None:
        self.sent_emails.append(
            {
                "to": to_email,
                "subject": "Verify your Pay-via-Mail account",
                "body": f"Your verification token is: {token}",
            }
        )

    def send_payment_notification(self, to_email: str, amount: str, asset: str) -> None:
        self.sent_emails.append(
            {
                "to": to_email,
                "subject": "You've received a crypto payment",
                "body": f"You have a pending payment of {amount} {asset}. Log in to view it.",
            }
        )


# Module-level singleton for simplicity in Phase 1.
email_service = MockEmailService()
