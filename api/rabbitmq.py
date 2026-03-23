import json
import logging
import uuid
from datetime import datetime
import pika
from django.conf import settings
from .models import AgentMessage

logger = logging.getLogger(__name__)

class MessagePublisher:
    """
    Thread-safe publisher for sending messages from Django to RabbitMQ.
    """
    def publish(self, sender, recipient, message_type, payload, project_id=None, ticket_id=None):
        message_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()

        # 1. Save to Audit Log (AgentMessage)
        try:
            AgentMessage(
                message_id=message_id,
                timestamp=timestamp,
                message_type=message_type,
                sender=sender,
                recipient=recipient,
                project_id=project_id,
                ticket_id=ticket_id,
                payload=payload,
                processed=False
            ).save()
        except Exception as e:
            logger.error(f"Failed to save AgentMessage audit log: {e}")

        # 2. Publish to RabbitMQ using an ephemeral connection
        try:
            parameters = pika.URLParameters(getattr(settings, 'RABBITMQ_URL', 'amqp://guest:guest@127.0.0.1:5672/'))
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            queue_name = recipient
            
            channel.queue_declare(queue=queue_name, durable=True)
            
            message_body = {
                'message_id': message_id,
                'timestamp': timestamp.isoformat(),
                'message_type': message_type,
                'sender': sender,
                'recipient': recipient,
                'project_id': project_id,
                'ticket_id': ticket_id,
                'payload': payload
            }
            
            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=json.dumps(message_body),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json'
                )
            )
            connection.close()
            logger.info(f"Published {message_type} to {queue_name}")
        except Exception as e:
            logger.error(f"Failed to publish to RabbitMQ: {e}")

publisher = MessagePublisher()
