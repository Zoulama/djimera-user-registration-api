import logging
import httpx
from typing import Dict, Any
import asyncio

from src.infrastructure.messaging.rabbitmq_client import RabbitMQClient
from src.domain.exceptions import EmailServiceException

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending activation codes via third-party service."""

    def __init__(self, rabbitmq_client: RabbitMQClient, email_service_url: str, queue_name: str):
        self.rabbitmq_client = rabbitmq_client
        self.email_service_url = email_service_url
        self.queue_name = queue_name
        self._is_consuming = False

    async def send_activation_code(self, email: str, activation_code: str, user_id: str):
        """
        Send activation code via RabbitMQ queue.
        
        Args:
            email: Recipient email address
            activation_code: 4-digit activation code
            user_id: User ID for tracking
        """
        message = {
            "type": "activation_code",
            "recipient": email,
            "activation_code": activation_code,
            "user_id": user_id,
            "subject": "Your Dailymotion Activation Code",
            "template": "activation_code",
            "timestamp": asyncio.get_event_loop().time()
        }

        try:
            await self.rabbitmq_client.publish_message(self.queue_name, message)
            logger.info(f"Activation code email queued for {email}")
        except Exception as e:
            logger.error(f"Failed to queue activation code email: {str(e)}")
            raise EmailServiceException()

    async def start_email_consumer(self):
        """Start consuming email messages from RabbitMQ queue."""
        if self._is_consuming:
            logger.warning("Email consumer is already running")
            return

        try:
            await self.rabbitmq_client.consume_messages(
                self.queue_name,
                self._process_email_message
            )
            self._is_consuming = True
            logger.info("Email consumer started successfully")
        except Exception as e:
            logger.error(f"Failed to start email consumer: {str(e)}")
            raise EmailServiceException()

    async def _process_email_message(self, message: Dict[str, Any]):
        """
        Process email message from queue.
        
        Args:
            message: Email message payload
        """
        try:
            message_type = message.get("type")
            if message_type == "activation_code":
                await self._send_activation_code_email(message)
            else:
                logger.warning(f"Unknown message type: {message_type}")
        except Exception as e:
            logger.error(f"Error processing email message: {str(e)}")
            raise

    async def _send_activation_code_email(self, message: Dict[str, Any]):
        """
        Send activation code email via HTTP API or console.
        
        Args:
            message: Email message with activation code details
        """
        recipient = message.get("recipient")
        activation_code = message.get("activation_code")
        user_id = message.get("user_id")

        if not all([recipient, activation_code, user_id]):
            logger.error("Missing required fields in activation code message")
            return

        # Email content
        email_payload = {
            "to": recipient,
            "subject": message.get("subject", "Your Dailymotion Activation Code"),
            "html_content": self._generate_activation_email_html(activation_code),
            "text_content": self._generate_activation_email_text(activation_code)
        }

        try:
            # Try to send via HTTP API first
            success = await self._send_via_http_api(email_payload)
            
            if not success:
                # Fallback to console output for development/testing
                self._send_via_console(recipient, activation_code)
                
        except Exception as e:
            logger.error(f"Failed to send activation code email: {str(e)}")
            # Fallback to console output
            self._send_via_console(recipient, activation_code)

    async def _send_via_http_api(self, email_payload: Dict[str, Any]) -> bool:
        """
        Send email via HTTP API.
        
        Args:
            email_payload: Email data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.email_service_url,
                    json=email_payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    logger.info(f"Email sent successfully via API to {email_payload['to']}")
                    return True
                else:
                    logger.warning(f"Email API returned status {response.status_code}")
                    return False
                    
        except httpx.TimeoutException:
            logger.warning("Email API request timed out")
            return False
        except httpx.ConnectError:
            logger.warning("Could not connect to email API service")
            return False
        except Exception as e:
            logger.error(f"Email API error: {str(e)}")
            return False

    def _send_via_console(self, recipient: str, activation_code: str):
        """
        Send email via console output (for development/testing).
        
        Args:
            recipient: Email recipient
            activation_code: 4-digit code
        """
        print("\n" + "="*60)
        print("📧 EMAIL NOTIFICATION (Console Mode)")
        print("="*60)
        print(f"To: {recipient}")
        print(f"Subject: Your Dailymotion Activation Code")
        print(f"")
        print(f"Your activation code is: {activation_code}")
        print(f"This code will expire in 1 minute.")
        print(f"")
        print(f"Please use this code to activate your Dailymotion account.")
        print("="*60)
        logger.info(f"Activation code sent via console to {recipient}: {activation_code}")

    def _generate_activation_email_html(self, activation_code: str) -> str:
        """Generate HTML email content for activation code."""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Dailymotion Activation Code</title>
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #f8f9fa; padding: 30px; text-align: center; border-radius: 10px;">
                <h1 style="color: #333; margin-bottom: 20px;">Welcome to Dailymotion!</h1>
                <p style="color: #666; font-size: 16px; margin-bottom: 30px;">
                    Please use the following activation code to complete your registration:
                </p>
                <div style="background-color: #007bff; color: white; font-size: 36px; font-weight: bold; 
                           padding: 20px; border-radius: 8px; letter-spacing: 8px; margin: 30px 0;">
                    {activation_code}
                </div>
                <p style="color: #999; font-size: 14px;">
                    This code will expire in 1 minute for security reasons.
                </p>
                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    If you didn't request this code, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """

    def _generate_activation_email_text(self, activation_code: str) -> str:
        """Generate plain text email content for activation code."""
        return f"""
        Welcome to Dailymotion!
        
        Please use the following activation code to complete your registration:
        
        {activation_code}
        
        This code will expire in 1 minute for security reasons.
        
        If you didn't request this code, please ignore this email.
        """

    async def health_check(self) -> bool:
        """Check email service health."""
        try:
            # Check RabbitMQ connection
            rabbitmq_healthy = await self.rabbitmq_client.health_check()
            
            # Check HTTP API availability (optional)
            api_healthy = await self._check_email_api_health()
            
            # Service is healthy if RabbitMQ is working
            # Email API is optional (fallback to console)
            return rabbitmq_healthy
            
        except Exception as e:
            logger.error(f"Email service health check failed: {str(e)}")
            return False

    async def _check_email_api_health(self) -> bool:
        """Check if email API is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Try to ping the email service
                response = await client.get(
                    self.email_service_url.replace("/send-email", "/health")
                )
                return response.status_code == 200
        except Exception:
            # Email API is not available, but that's okay (we have console fallback)
            return False