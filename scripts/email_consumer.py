import asyncio
import json
import logging
import sys
from pathlib import Path

# Add the app directory to the path so we can import our modules
app_dir = Path(__file__).parent.parent
sys.path.insert(0, str(app_dir))

from config import settings
from infrastructure.messaging.rabbitmq_client import RabbitMQClient
from infrastructure.email.email_service import EmailService


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmailConsumer:
    """Consumes email messages from RabbitMQ and sends them."""
    
    def __init__(self):
        self.rabbitmq_client = RabbitMQClient()
        self.email_service = EmailService()
        self.running = False
    
    async def start(self):
        """Start the email consumer."""
        logger.info("Starting Email Consumer...")
        
        try:
            # Connect to RabbitMQ
            await self.rabbitmq_client.connect()
            logger.info("Connected to RabbitMQ")
            
            # Declare the email queue
            await self.rabbitmq_client.declare_queue(settings.email_queue_name)
            logger.info(f"Declared queue: {settings.email_queue_name}")
            
            # Start consuming messages
            self.running = True
            await self.rabbitmq_client.consume_messages(
                queue_name=settings.email_queue_name,
                callback=self._handle_email_message
            )
            
        except Exception as e:
            logger.error(f"Failed to start email consumer: {e}")
            raise
    
    async def stop(self):
        """Stop the email consumer."""
        logger.info("Stopping Email Consumer...")
        self.running = False
        if self.rabbitmq_client:
            await self.rabbitmq_client.close()
        logger.info("Email Consumer stopped")
    
    async def _handle_email_message(self, message_body: bytes):
        """Handle incoming email message."""
        try:
            # Parse the message
            message_data = json.loads(message_body.decode('utf-8'))
            logger.info(f"Received email message: {message_data}")
            
            # Extract email data
            to_email = message_data.get('to_email')
            subject = message_data.get('subject')
            body = message_data.get('body')
            
            if not all([to_email, subject, body]):
                logger.error(f"Invalid email message format: {message_data}")
                return
            
            # Send the email
            success = await self.email_service.send_email(
                to_email=to_email,
                subject=subject,
                body=body
            )
            
            if success:
                logger.info(f"Successfully sent email to {to_email}")
            else:
                logger.error(f"Failed to send email to {to_email}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse email message: {e}")
        except Exception as e:
            logger.error(f"Error handling email message: {e}")


async def main():
    """Main entry point."""
    consumer = EmailConsumer()
    
    try:
        # Start the consumer
        await consumer.start()
        
        # Keep running until interrupted
        logger.info("Email Consumer is running. Press Ctrl+C to stop.")
        while consumer.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Email consumer error: {e}")
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(main())