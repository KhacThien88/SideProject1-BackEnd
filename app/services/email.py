"""
Email Service với AWS SES Integration
Xử lý gửi email verification và các loại email khác
"""

import boto3
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
import logging

from app.core.config import settings
from app.core.database import get_dynamodb_resource
from app.utils.logger import get_logger
from app.models.otp import OTPTable, generate_otp_code, create_otp_expiry

logger = get_logger(__name__)


class EmailService:
    """Service để gửi email qua AWS SES"""
    
    def __init__(self):
        self.ses_client = boto3.client(
            'ses',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
        self.dynamodb = get_dynamodb_resource()
        
    async def send_otp_verification_email(
        self, 
        email: str, 
        user_id: str,
        user_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Gửi email OTP verification cho user mới đăng ký
        
        Args:
            email: Email của user
            user_id: ID của user
            user_name: Tên của user (optional)
            
        Returns:
            Dict chứa kết quả gửi email
        """
        try:
            # Tạo OTP code
            otp_code = generate_otp_code()
            expires_at = create_otp_expiry()
            
            # Lưu OTP vào database
            otp_record = OTPTable(
                otp_id=f"otp_{user_id}_{int(datetime.utcnow().timestamp())}",
                email=email,
                otp_code=otp_code,
                user_id=user_id,
                expires_at=expires_at,
                created_at=datetime.utcnow(),
                attempts=0,
                is_used="false"
            )
            otp_record.save()
            
            # Render email template với OTP
            email_content = await self._render_otp_verification_template(
                user_name or "User",
                otp_code
            )
            
            # Gửi email qua SES
            response = await self._send_email(
                to_email=email,
                subject="Mã xác thực tài khoản - AI Resume Analyzer",
                html_content=email_content,
                text_content=self._html_to_text(email_content)
            )
            
            logger.info(f"OTP verification email sent for user_id={user_id}, MessageId={response.get('MessageId')}")
            
            return {
                "success": True,
                "message_id": response.get('MessageId'),
                "otp_id": otp_record.otp_id,
                "expires_at": expires_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send OTP verification email for user_id={user_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_password_reset_email(
        self, 
        email: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Gửi email reset password
        
        Args:
            email: Email của user
            user_id: ID của user
            
        Returns:
            Dict chứa kết quả gửi email
        """
        try:
            # Tạo reset token
            token = await self._generate_password_reset_token(user_id, email)
            
            # Tạo reset URL
            reset_url = f"{settings.frontend_url}/reset-password?token={token}"
            
            # Render email template
            email_content = await self._render_password_reset_template(reset_url)
            
            # Gửi email qua SES
            response = await self._send_email(
                to_email=email,
                subject="Đặt lại mật khẩu - AI Resume Analyzer",
                html_content=email_content,
                text_content=self._html_to_text(email_content)
            )
            
            logger.info(f"Password reset email sent for user_id={user_id}, MessageId={response.get('MessageId')}")
            
            return {
                "success": True,
                "message_id": response.get('MessageId'),
                "token": token,
                "reset_url": reset_url
            }
            
        except Exception as e:
            logger.error(f"Failed to send password reset email for user_id={user_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def verify_email_token(self, token: str) -> Dict[str, Any]:
        """
        Xác thực email token
        
        Args:
            token: Verification token
            
        Returns:
            Dict chứa kết quả verification
        """
        try:
            table = self.dynamodb.Table("email_verification_tokens")
            
            # Tìm token trong database
            response = table.get_item(
                Key={'token': token}
            )
            
            if 'Item' not in response:
                return {
                    "success": False,
                    "error": "Invalid or expired token"
                }
            
            item = response['Item']
            
            # Kiểm tra token đã expire chưa
            if datetime.now() > datetime.fromisoformat(item['expires_at']):
                # Xóa token expired
                table.delete_item(Key={'token': token})
                return {
                    "success": False,
                    "error": "Token has expired"
                }
            
            # Kiểm tra token đã được sử dụng chưa
            if item.get('used', False):
                return {
                    "success": False,
                    "error": "Token has already been used"
                }
            
            # Đánh dấu token đã sử dụng
            table.update_item(
                Key={'token': token},
                UpdateExpression='SET used = :used, verified_at = :verified_at',
                ExpressionAttributeValues={
                    ':used': True,
                    ':verified_at': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Email verified successfully for user {item['user_id']}")
            
            return {
                "success": True,
                "user_id": item['user_id'],
                "email": item['email'],
                "verified_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to verify email token: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def resend_verification_email(
        self, 
        email: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """
        Gửi lại email verification
        
        Args:
            email: Email của user
            user_id: ID của user
            
        Returns:
            Dict chứa kết quả gửi email
        """
        try:
            # Kiểm tra rate limiting (không cho gửi quá nhiều trong thời gian ngắn)
            if await self._check_rate_limit(email):
                return {
                    "success": False,
                    "error": "Too many verification emails sent. Please wait before requesting another."
                }
            
            # Gửi email verification mới
            return await self.send_verification_email(email, user_id)
            
        except Exception as e:
            logger.error(f"Failed to resend verification email to {email}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _generate_verification_token(self, user_id: str, email: str) -> str:
        """Tạo verification token"""
        # Tạo random token
        token = secrets.token_urlsafe(32)
        
        # Tính toán expiry time (24 giờ)
        expires_at = datetime.now() + timedelta(hours=24)
        
        # Lưu token vào DynamoDB table email_verification_tokens
        table = self.dynamodb.Table("email_verification_tokens")
        table.put_item(
            Item={
                'token': token,
                'user_id': user_id,
                'email': email,
                'token_type': 'email_verification',
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat(),
                'used': False
            }
        )
        
        return token
    
    async def _generate_password_reset_token(self, user_id: str, email: str) -> str:
        """Tạo password reset token"""
        # Tạo random token
        token = secrets.token_urlsafe(32)
        
        # Tính toán expiry time (1 giờ)
        expires_at = datetime.now() + timedelta(hours=1)
        
        # Lưu token vào DynamoDB table password_reset_tokens
        table = self.dynamodb.Table("password_reset_tokens")
        table.put_item(
            Item={
                'token': token,
                'user_id': user_id,
                'email': email,
                'token_type': 'password_reset',
                'created_at': datetime.now().isoformat(),
                'expires_at': expires_at.isoformat(),
                'used': False
            }
        )
        
        return token
    
    async def _send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str,
        text_content: str
    ) -> Dict[str, Any]:
        """Gửi email qua AWS SES"""
        
        # Kiểm tra verified email addresses
        verified_emails = self.ses_client.list_verified_email_addresses()
        if settings.ses_from_email not in verified_emails['VerifiedEmailAddresses']:
            raise Exception("Sender email is not verified in SES")
        
        # Gửi email
        response = self.ses_client.send_email(
            Source=settings.ses_from_email,
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Html': {'Data': html_content, 'Charset': 'UTF-8'},
                    'Text': {'Data': text_content, 'Charset': 'UTF-8'}
                }
            }
        )
        
        return response
    
    async def _render_otp_verification_template(
        self, 
        user_name: str, 
        otp_code: str
    ) -> str:
        """Render OTP verification email template"""
        
        template_html = """
        <!DOCTYPE html>
        <html lang="vi">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Mã xác thực tài khoản</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f4f4f4;
                }
                .container {
                    background-color: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                    margin: -30px -30px 30px -30px;
                }
                .header h1 {
                    margin: 0;
                    font-size: 28px;
                    font-weight: 300;
                }
                .otp-code {
                    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                    color: white;
                    font-size: 32px;
                    font-weight: bold;
                    text-align: center;
                    padding: 20px;
                    border-radius: 10px;
                    margin: 30px 0;
                    letter-spacing: 8px;
                    font-family: 'Courier New', monospace;
                }
                .content {
                    font-size: 16px;
                    line-height: 1.8;
                }
                .warning {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    color: #856404;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }
                .footer {
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 14px;
                    color: #666;
                    text-align: center;
                }
                .highlight {
                    color: #667eea;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Chào mừng đến với AI Resume Analyzer!</h1>
                </div>
                
                <div class="content">
                    <p>Xin chào <span class="highlight">{{ user_name }}</span>,</p>
                    
                    <p>Cảm ơn bạn đã đăng ký tài khoản tại AI Resume Analyzer. Để hoàn tất quá trình đăng ký, vui lòng sử dụng mã OTP bên dưới:</p>
                    
                    <div class="otp-code">
                        {{ otp_code }}
                    </div>
                    
                    <div class="warning">
                        <strong>Lưu ý quan trọng:</strong>
                        <ul>
                            <li>Mã OTP này sẽ hết hạn sau <strong>15 phút</strong></li>
                            <li>Không chia sẻ mã này với bất kỳ ai</li>
                            <li>Nếu bạn không đăng ký tài khoản này, vui lòng bỏ qua email này</li>
                        </ul>
                    </div>
                    
                    <p>Sau khi nhập mã OTP, bạn sẽ có thể:</p>
                    <ul>
                        <li>✅ Đăng nhập vào tài khoản</li>
                        <li>✅ Sử dụng đầy đủ tính năng AI Resume Analyzer</li>
                        <li>✅ Phân tích và tối ưu hóa CV của bạn</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>Trân trọng,<br>
                    <strong>Đội ngũ AI Resume Analyzer</strong></p>
                    
                    <p><small>Email này được gửi tự động, vui lòng không trả lời.</small></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(template_html)
        return template.render(
            user_name=user_name,
            otp_code=otp_code
        )
    
    async def _render_password_reset_template(self, reset_url: str) -> str:
        """Render password reset template"""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Đặt lại mật khẩu</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #dc2626; color: white; padding: 20px; text-align: center; }
                .content { padding: 30px; background: #f8fafc; }
                .button { 
                    display: inline-block; 
                    background: #dc2626; 
                    color: white; 
                    padding: 12px 24px; 
                    text-decoration: none; 
                    border-radius: 6px; 
                    margin: 20px 0;
                }
                .footer { text-align: center; padding: 20px; color: #64748b; font-size: 14px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Đặt lại mật khẩu</h1>
                </div>
                <div class="content">
                    <h2>Yêu cầu đặt lại mật khẩu</h2>
                    <p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn. Để tiếp tục, vui lòng nhấp vào nút bên dưới:</p>
                    
                    <div style="text-align: center;">
                        <a href="{{ reset_url }}" class="button">Đặt lại mật khẩu</a>
                    </div>
                    
                    <p>Hoặc copy và paste link này vào trình duyệt:</p>
                    <p style="word-break: break-all; background: #e2e8f0; padding: 10px; border-radius: 4px;">
                        {{ reset_url }}
                    </p>
                    
                    <p><strong>Lưu ý:</strong> Link này sẽ hết hạn sau 1 giờ.</p>
                    
                    <p>Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này. Mật khẩu của bạn sẽ không thay đổi.</p>
                </div>
                <div class="footer">
                    <p>© 2024 AI Resume Analyzer. Tất cả quyền được bảo lưu.</p>
                    <p>Email này được gửi tự động, vui lòng không trả lời.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(template_str)
        return template.render(reset_url=reset_url)
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text"""
        import re
        
        # Remove HTML tags
        text = re.sub('<[^<]+?>', '', html_content)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    async def _check_rate_limit(self, email: str) -> bool:
        """Kiểm tra rate limiting cho email"""
        try:
            table = self.dynamodb.Table(self.table_name)
            
            # Kiểm tra số lượng email đã gửi trong 1 giờ qua
            one_hour_ago = datetime.now() - timedelta(hours=1)
            
            response = table.scan(
                FilterExpression='email = :email AND created_at > :one_hour_ago',
                ExpressionAttributeValues={
                    ':email': email,
                    ':one_hour_ago': one_hour_ago.isoformat()
                }
            )
            
            # Cho phép tối đa 3 email trong 1 giờ
            return len(response['Items']) >= 3
            
        except Exception as e:
            logger.error(f"Failed to check rate limit for {email}: {str(e)}")
            return False


# Singleton instance
email_service = EmailService()
