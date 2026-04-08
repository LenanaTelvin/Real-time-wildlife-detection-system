# backend/src/services/otp_service.py
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os

class OTPService:
    
    @staticmethod
    def generate_otp():
        """Generate a 6-digit OTP"""
        return str(random.randint(100000, 999999))
    
    @staticmethod
    def send_otp_email(email, otp_code):
        """Send OTP via email"""
        smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_user = os.environ.get('SMTP_USER', '')
        smtp_password = os.environ.get('SMTP_PASSWORD', '')
        
        if not smtp_user or not smtp_password:
            print(f"⚠️ Email not configured. OTP for {email}: {otp_code}")
            return True
        
        subject = "Verify Your Email - Wildlife Detection System"
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #1a472a 0%, #0d2818 100%); padding: 20px; text-align: center;">
                <h1 style="color: #00ff88;">Wildlife Detection System</h1>
            </div>
            <div style="padding: 20px; border: 1px solid #ddd;">
                <h2>Email Verification</h2>
                <p>Thank you for registering! Please use the following OTP to verify your email address:</p>
                <div style="background: #f4f4f4; padding: 15px; text-align: center; font-size: 32px; letter-spacing: 5px; font-weight: bold;">
                    {otp_code}
                </div>
                <p>This OTP is valid for <strong>10 minutes</strong>.</p>
                <p>If you didn't create an account, please ignore this email.</p>
                <hr>
                <p style="color: #666; font-size: 12px;">Wildlife Detection System - Protecting Wildlife Through Technology</p>
            </div>
        </body>
        </html>
        """
        
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()
            print(f"✅ OTP email sent to {email}")
            return True
        except Exception as e:
            print(f"❌ Failed to send email: {e}")
            return False
    
    @staticmethod
    def create_and_send_otp(email):
        """Generate and send OTP, store in database"""
        from ..models.user import User
        
        otp_code = OTPService.generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        # Store OTP in database
        User.update_otp(email, otp_code, expires_at)
        
        # Send email
        return OTPService.send_otp_email(email, otp_code)