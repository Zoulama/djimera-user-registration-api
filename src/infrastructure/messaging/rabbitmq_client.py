import asyncio
import json
import logging
from typing import Dict, Any, Callable, Optional
import aio_pika
from aio_pika import Message, DeliveryMode

from src.domain.exceptions import EmailServiceException

logger = logging.getLogger(__name__)


class RabbitMQClient:
    """RabbitMQ client for async messaging."""

    def __init__(self, connection_url: str):
        self.connection_url = connection_url
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None

    async def connect(self):
        """Establish connection to RabbitMQ."""
        try:
            self.connection = await aio_pika.connect_robust(
                self.connection_url,
                heartbeat=30,
                blocked_connection_timeout=300,
            )
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=10)
            logger.info("Connected to RabbitMQ successfully")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise EmailServiceException()

    async def disconnect(self):
        """Close connection to RabbitMQ."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("RabbitMQ connection closed")

    async def declare_queue(
        self,
        queue_name: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False
    ) -> aio_pika.Queue:
        """
        Declare a queue.
        
        Args:
            queue_name: Name of the queue
            durable: Whether queue survives broker restarts
            exclusive: Whether queue is exclusive to this connection
            auto_delete: Whether queue is deleted when no consumers
            
        Returns:
            Declared queue
        """
        if not self.channel:
            raise EmailServiceException()

        try:
            queue = await self.channel.declare_queue(
                queue_name,
                durable=durable,
                exclusive=exclusive,
                auto_delete=auto_delete
            )
            logger.info(f"Queue declared: {queue_name}")
            return queue
        except Exception as e:
            logger.error(f"Failed to declare queue {queue_name}: {str(e)}")
            raise EmailServiceException()

    async def publish_message(
        self,
        queue_name: str,
        message: Dict[str, Any],
        delivery_mode: DeliveryMode = DeliveryMode.PERSISTENT
    ):
        """
        Publish a message to a queue.
        
        Args:
            queue_name: Name of the target queue
            message: Message payload
            delivery_mode: Message delivery mode
        """
        if not self.channel:
            raise EmailServiceException()

        try:
            # Declare queue if it doesn't exist
            await self.declare_queue(queue_name)

            # Create message
            msg = Message(
                json.dumps(message).encode('utf-8'),
                delivery_mode=delivery_mode,
                content_type='application/json',
                timestamp=asyncio.get_event_loop().time()
            )

            # Publish message
            await self.channel.default_exchange.publish(
                msg,
                routing_key=queue_name
            )
            
            logger.info(f"Message published to queue {queue_name}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish message to {queue_name}: {str(e)}")
            raise EmailServiceException()

    async def consume_messages(
        self,
        queue_name: str,
        callback: Callable[[Dict[str, Any]], None],
        auto_ack: bool = False
    ):
        """
        Consume messages from a queue.
        
        Args:
            queue_name: Name of the queue to consume from
            callback: Function to handle received messages
            auto_ack: Whether to automatically acknowledge messages
        """
        if not self.channel:
            raise EmailServiceException()

        try:
            # Declare queue
            queue = await self.declare_queue(queue_name)

            async def message_handler(message: aio_pika.IncomingMessage):
                async with message.process(ignore_processed=True):
                    try:
                        # Decode message
                        body = json.loads(message.body.decode('utf-8'))
                        
                        # Process message
                        await callback(body)
                        
                        logger.info(f"Message processed from queue {queue_name}")
                        
                        # Acknowledge message if not auto-ack
                        if not auto_ack:
                            message.ack()
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in message: {str(e)}")
                        message.nack(requeue=False)
                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}")
                        message.nack(requeue=True)

            # Start consuming
            await queue.consume(message_handler, no_ack=auto_ack)
            logger.info(f"Started consuming from queue: {queue_name}")
            
        except Exception as e:
            logger.error(f"Failed to consume from queue {queue_name}: {str(e)}")
            raise EmailServiceException()

    async def health_check(self) -> bool:
        """Check RabbitMQ connection health."""
        try:
            if not self.connection or self.connection.is_closed:
                return False
            
            # Try to declare a temporary queue
            if self.channel:
                temp_queue = await self.channel.declare_queue(
                    "health_check",
                    exclusive=True,
                    auto_delete=True
                )
                await temp_queue.delete()
                return True
            return False
        except Exception as e:
            logger.error(f"RabbitMQ health check failed: {str(e)}")
            return False