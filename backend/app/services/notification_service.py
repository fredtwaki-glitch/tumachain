from app.services.email_service import email_service

class NotificationService:
    def payment_received(self,to_email,amount,asset,status="PENDING"):
        email_service.send_payment_notification(to_email,str(amount),asset)

notification_service=NotificationService()
