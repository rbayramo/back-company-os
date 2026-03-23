import json
import logging
import asyncio
import pika
import redis
from django.core.management.base import BaseCommand
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from api.models import AgentMessage
from api.views import format_log_message

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Starts the RabbitMQ consumer listening on queue:django'

    def handle(self, *args, **options):
        self.stdout.write("Starting Django RabbitMQ Consumer...")
        
        # Connect to Redis for idempotency
        try:
            redis_url = getattr(settings, 'REDIS_URL', 'redis://127.0.0.1:6379/0')
            r = redis.from_url(redis_url)
            self.stdout.write("Connected to Redis.")
        except Exception as e:
            self.stderr.write(f"Failed to connect to Redis: {e}")
            return

        # Connect to RabbitMQ
        try:
            rabbitmq_url = getattr(settings, 'RABBITMQ_URL', 'amqp://guest:guest@127.0.0.1:5672/')
            parameters = pika.URLParameters(rabbitmq_url)
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            self.stdout.write("Connected to RabbitMQ.")
        except Exception as e:
            self.stderr.write(f"Failed to connect to RabbitMQ: {e}")
            return

        queue_name = 'queue:django'
        channel.queue_declare(queue=queue_name, durable=True)

        channel_layer = get_channel_layer()

        def callback(ch, method, properties, body):
            try:
                data = json.loads(body)
                msg_id = data.get('message_id')
                msg_type = data.get('message_type')
                payload = data.get('payload', {})
                project_id = data.get('project_id') or payload.get('project_id')

                # Idempotency check
                if msg_id and r.sismember('django_processed_messages', msg_id):
                    self.stdout.write(f"Skipping already processed message: {msg_id}")
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                self.stdout.write(f"Processing message {msg_id}: {msg_type} for project {project_id}")

                # Mark AgentMessage as processed in MongoDB
                if msg_id:
                    AgentMessage.objects.filter(message_id=msg_id).update(processed=True)

                # Broadcast agent status to all active UI clients globally
                if msg_type == 'ui_agent_status':
                    async_to_sync(channel_layer.group_send)(
                        'global_agents',
                        {
                            'type': 'agent_status_event',
                            'agent': payload
                        }
                    )

                # Broadcast via Websockets if project_id exists
                if project_id:
                    room_group_name = f'project_{project_id}'
                    
                    if msg_type == 'ceo_response':
                        async_to_sync(channel_layer.group_send)(
                            room_group_name,
                            {
                                'type': 'chat_message_event',
                                'message': payload
                            }
                        )
                    elif msg_type in ['kanban_update', 'ticket_created', 'ticket_updated']:
                        async_to_sync(channel_layer.group_send)(
                            room_group_name,
                            {
                                'type': 'kanban_update_event',
                                'ticket': payload
                            }
                        )
                    
                    # Always send a generic agent log event (unless it's a high-frequency UI status update)
                    if msg_type != 'ui_agent_status':
                        sender_id = data.get('sender', '').replace('agent:', '')
                        label = sender_id.upper()
                        if sender_id == 'django' or sender_id == 'board':
                            label = 'BOARD'

                        async_to_sync(channel_layer.group_send)(
                            room_group_name,
                            {
                                'type': 'agent_log_event',
                                'log': {
                                    'id': msg_id or str(uuid.uuid4()),
                                    'agent': sender_id,
                                    'agent_label': label,
                                    'message': format_log_message(msg_type, payload),
                                    'timestamp': data.get('timestamp') or datetime.utcnow().isoformat(),
                                    'type': 'info'
                                }
                            }
                        )

                # Mark as processed in Redis
                if msg_id:
                    r.sadd('django_processed_messages', msg_id)
                
                # Acknowledge the message
                ch.basic_ack(delivery_tag=method.delivery_tag)

            except Exception as e:
                self.stderr.write(f"Error processing message: {e}")
                # Depending on error, we might reject or ack. For now, NACK and requeue.
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

        # Set QoS
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=queue_name, on_message_callback=callback)

        self.stdout.write('Waiting for messages. To exit press CTRL+C')
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
        connection.close()
