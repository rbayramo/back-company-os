import os
import sys
import json
import uuid
import time
import django
from datetime import datetime

if __name__ == "__main__":
    # Setup Django environment (only if run as standalone script)
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from api.models import Project, ConversationMessage, Ticket, AgentMessage
from agents.base_agent import BaseAgent

class CEOAgent(BaseAgent):
    def __init__(self):
        super().__init__('ceo', 'CEO', 'Management')
        self.base_prompt = """
        You are the CEO Agent of an AI-driven Agent Swarm Operating System.
        Your goal is to lead the company, decompose high-level missions into actionable tasks, and communicate with the user.

        AVAILABLE DEPARTMENTS & AGENTS:
        - Management: CEO (You), COO (Orchestration & Delegation)
        - Brand: UI/UX, Branding
        - Engineering: Antigravity (Lead Developer)
        - Growth: Instagram, WhatsApp, SEO, Email, Content Creator, Reels Maker, Researcher

        YOUR RESPONSIBILITIES:
        1. Understand the user's mission or question.
        2. Decompose goals into logical phases and tasks.
        3. Delegate tasks to the COO or specific departments when needed.
        4. Maintain a professional, visionary, and helpful tone.
        
        LANGUAGE NOTES:
        - The user may write in Azerbaijani or English. Respond in the same language.
        - Pay attention to Azerbaijani suffixes (-u, -ü, -ı, -i, -da, -də) to understand context.

        OUTPUT FORMAT (JSON ONLY):
        You must ALWAYS return valid JSON conforming to this schema:
        {
            "is_mission_update": true/false,
            "response_text": "Your direct message (in the same language as user)",
            "suggested_tasks": [
                { "title": "Task name", "department": "Dept", "description": "Details" }
            ],
            "intent": "Brief description of user intent"
        }
        """

    def get_system_prompt(self, company_context=None):
        """Construct the full system prompt with global company context."""
        context_str = ""
        if company_context:
            context_str = f"\n\nGLOBAL COMPANY CONTEXT:\n{company_context}\n\n"
            context_str += "IMPORTANT: Consider the above existing company knowledge/missions when planning. Stay consistent with the overall company vision."
            
        return self.base_prompt + context_str

    @property
    def system_prompt(self):
        # Default property for base class compatibility
        return self.base_prompt

    def handle_message(self, message):
        project_id = message['payload'].get('project_id')
        text = message['payload'].get('text')
        msg_type = message.get('message_type')
        history = message['payload'].get('history', [])
        company_context = message['payload'].get('company_context', '')
        
        full_system_prompt = self.get_system_prompt(company_context)
        
        print(f"[CEO] Handling {msg_type} for project {project_id}")
        
        if msg_type == 'human_message':
            self.log(project_id, 'received_human_mission', {'text': text[:50]})
            
            print(f"[CEO] Calling LLM (JSON Mode) for project {project_id}...", flush=True)
            ai_raw = self.call_llm(full_system_prompt, text, history=history, json_mode=True)
            
            try:
                ai_json = json.loads(ai_raw)
                response_text = ai_json.get('response_text', "I've processed your request.")
                suggested_tasks = ai_json.get('suggested_tasks', [])
            except Exception as e:
                print(f"[CEO] Failed to parse JSON: {e}", flush=True)
                response_text = ai_raw # Fallback
                suggested_tasks = []

            # 3. Save CEO response to chat
            ceo_msg = ConversationMessage(
                project_id=project_id,
                sender='ceo',
                text=response_text,
                processed=True
            )
            ceo_msg.save()
            
            # 4. Notify Frontend
            self._notify_chat(project_id, ceo_msg)
            
            # 5. Draft tickets if suggested
            if suggested_tasks:
                self._draft_tickets(project_id, suggested_tasks)

    def _notify_chat(self, project_id, msg):
        ws_message = {
            'type': 'chat_message_event',
            'message': msg.to_dict()
        }
        if self.channel_layer:
            from asgiref.sync import async_to_sync
            async_to_sync(self.channel_layer.group_send)(f'project_{project_id}', ws_message)
        elif self.redis_client:
            self.redis_client.publish(f'project_{project_id}_chat', json.dumps({'type': 'chat_message', 'message': msg.to_dict()}))

    def _draft_tickets(self, project_id, tasks):
        """Create tickets based on AI suggestions."""
        self.log(project_id, 'drafting_execution_plan', {'count': len(tasks)})
        
        for t_data in tasks:
            title = t_data.get('title', 'New Task')
            dept = t_data.get('department', 'Management').lower()
            desc = t_data.get('description', '')

            ticket = Ticket(
                project_id=project_id,
                title=title,
                description=desc,
                status='assigned',
                priority='medium',
                assigned_to=f'agent:{dept}',
                department=dept
            )
            ticket.save()
            
            # Notify Frontend
            ws_message = {
                'type': 'kanban_update_event',
                'ticket': ticket.to_dict()
            }
            if self.channel_layer:
                from asgiref.sync import async_to_sync
                async_to_sync(self.channel_layer.group_send)(f'project_{project_id}', ws_message)
            elif self.redis_client:
                self.redis_client.publish(f'project_{project_id}_kanban', json.dumps({'type': 'kanban_update', 'ticket': ticket.to_dict()}))
            
            # Log the assignment
            self.log(project_id, 'ticket_assigned', {'ticket': title, 'agent': dept}, ticket_id=str(ticket.id))

if __name__ == "__main__":
    agent = CEOAgent()
    agent.run()
