import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ProjectConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.project_id = self.scope['url_route']['kwargs']['project_id']
        self.room_group_name = f'project_{self.project_id}'

        # Join project group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        # Join global agents group
        await self.channel_layer.group_add(
            'global_agents',
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave project group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        await self.channel_layer.group_discard(
            'global_agents',
            self.channel_name
        )

    # Receive message from WebSocket 
    # (Optional: if we want to allow sending via WS instead of REST)
    async def receive(self, text_data):
        pass

    # ─── Event Handlers (Called by channel_layer.group_send) ──────────────────

    async def chat_message_event(self, event):
        """Handler for 'type': 'chat_message_event'"""
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

    async def kanban_update_event(self, event):
        """Handler for 'type': 'kanban_update_event'"""
        await self.send(text_data=json.dumps({
            'type': 'kanban_update',
            'ticket': event['ticket']
        }))

    async def agent_log_event(self, event):
        """Handler for 'type': 'agent_log_event'"""
        await self.send(text_data=json.dumps({
            'type': 'agent_log',
            'log': event['log']
        }))

    async def agent_status_event(self, event):
        """Handler for 'type': 'agent_status_event'"""
        await self.send(text_data=json.dumps({
            'type': 'agent_status',
            'agent': event['agent']
        }))
