if __name__ == "__main__":
    # Setup Django (for standalone execution)
    from pathlib import Path
    import sys
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()

import os
import json
import uuid
import time
import redis
import mongoengine as me
from datetime import datetime
from dotenv import load_dotenv

# Load config
load_dotenv()

class BaseAgent:
    def __init__(self, agent_id, label, department):
        self.agent_id = agent_id
        self.label = label
        self.department = department
        self.redis_client = None
        try:
            self.redis_client = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
            self.redis_client.ping()
        except:
            print(f"[{self.label}] Redis unavailable. Using direct memory layering if applicable.")

        self.queue_name = f'queue:agent:{self.agent_id}'
        
        # Django Channels layer (for in-process live updates)
        try:
            from channels.layers import get_channel_layer
            self.channel_layer = get_channel_layer()
        except:
            self.channel_layer = None
        # Note: Connection is handled globally in settings.py
        self.db_name = os.environ.get('MONGO_DB_NAME', 'agent_swarm_os')
        self.mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
        
        print(f"[{self.label}] Initialized and hooked into Redis/MongoDB.")

    def log(self, project_id, message_type, payload, ticket_id=None):
        """Log agent activity to MongoDB and notify over WebSocket."""
        from api.models import AgentMessage 
        # Note: In a standalone script, we import inside or use direct collection access
        # Since I'm using mongoengine, I'll use the model
        
        log_entry = {
            'message_id': f'log_{uuid.uuid4().hex[:8]}',
            'timestamp': datetime.utcnow(),
            'message_type': message_type,
            'sender': f'agent:{self.agent_id}',
            'project_id': project_id,
            'ticket_id': ticket_id,
            'payload': payload,
        }
        
        # Save to DB (using direct pymongo via mongoengine connection for speed/simplicity in scripts)
        db = me.get_db()
        db.agent_messages.insert_one(log_entry)
        
        # Publish to WebSocket (try Channels Layer first, then Redis PubSub)
        ws_message = {
            'type': 'agent_log_event', # Match expected handler in consumer
            'log': {
                'id': log_entry['message_id'],
                'agent': self.agent_id,
                'agent_label': self.label,
                'message': f"[{message_type}] {json.dumps(payload)[:100]}...",
                'timestamp': log_entry['timestamp'].isoformat() + 'Z',
                'type': 'info'
            }
        }

        if self.channel_layer:
            from asgiref.sync import async_to_sync
            async_to_sync(self.channel_layer.group_send)(f'project_{project_id}', ws_message)
        elif self.redis_client:
            self.redis_client.publish(f'project_{project_id}_logs', json.dumps({'type': 'agent_log', 'log': ws_message['log']}))
        
        print(f"[{self.label}] LOG: {message_type}")

    def run(self):
        print(f"[{self.label}] Listening for messages on {self.queue_name}...")
        while True:
            try:
                # BLPOP blocks until a message is available
                _, message_json = self.redis_client.blpop(self.queue_name)
                message = json.loads(message_json)
                self.handle_message(message)
            except Exception as e:
                print(f"[{self.label}] Error processing message: {e}")
                time.sleep(1)

    def handle_message(self, message):
        raise NotImplementedError("Subclasses must implement handle_message")

    def call_llm(self, system_prompt, user_prompt, history=None, temperature=0.7, json_mode=False):
        """Generic LLM caller (wraps OpenAI/Gemini/DeepSeek based on env)."""
        # Prioritize OpenAI as per user request
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key:
            print(f"\n--- [DEBUG] START OPENAI REQUEST ({self.label}) ---", flush=True)
            print(f"Model: gpt-5.2", flush=True)
            print(f"JSON Mode: {json_mode}", flush=True)
            
            # Construct messages
            messages = [{"role": "system", "content": system_prompt}]
            if history:
                messages.extend(history)
            messages.append({"role": "user", "content": user_prompt})
            
            print(f"Total Context Items: {len(messages)}", flush=True)
            
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                print(f"[{self.label}] OpenAI Client initialized. Sending request...", flush=True)
                
                kwargs = {
                    "model": "gpt-5.2",
                    "messages": messages,
                    "temperature": temperature,
                    "timeout": 35.0
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}
                
                response = client.chat.completions.create(**kwargs)
                
                print(f"--- [DEBUG] OPENAI RESPONSE RECEIVED ---", flush=True)
                content = response.choices[0].message.content
                print(f"Full Response Content: {content}", flush=True)
                print(f"--- [DEBUG] END OPENAI RESPONSE ---", flush=True)
                
                return content
            except Exception as e:
                print(f"!!! [DEBUG] OPENAI ERROR: {e}", flush=True)
                print(f"--- [DEBUG] END OPENAI REQUEST (FAILED) ---\n", flush=True)
                # Fall through to other providers or mock if it fails
        else:
            print(f"[{self.label}] No OPENAI_API_KEY found in environment.", flush=True)

        # Fallback to Gemini
        gemini_key = os.environ.get('GEMINI_API_KEY')
        if gemini_key and gemini_key != 'your-gemini-api-key-here':
            print(f"[{self.label}] Attempting Gemini fallback...")
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel('gemini-pro')
                response = model.generate_content(f"{system_prompt}\n\nUSER: {user_prompt}")
                return response.text
            except Exception as e:
                print(f"[{self.label}] Gemini Error: {e}")
        
        # Mock for now if no keys
        print(f"[{self.label}] Falling back to MOCK response.")
        return f"MOCK RESPONSE from {self.label}: I've received your request about '{user_prompt[:50]}...' and I'm processing it."
