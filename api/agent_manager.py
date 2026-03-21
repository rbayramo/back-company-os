import threading
import time
import os
import json
from django.conf import settings
from api.models import AgentMessage, ConversationMessage
from agents.ceo_agent import CEOAgent

class InProcessAgentManager(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="AgentManager")
        self.ceo = CEOAgent()
        self.is_running = True

    def run(self):
        print("[AgentManager] Started in-process background thread.")
        
        while self.is_running:
            try:
                # 1. Check for new Human Messages in AgentMessage collection (or just poll ConversationMessage)
                # For simplicity, we'll check AgentMessage for recipient='agent:ceo' and processed=False
                unprocessed = AgentMessage.objects(recipient='agent:ceo', processed=False).order_by('timestamp')
                if unprocessed:
                    print(f"[AgentManager] Found {len(unprocessed)} unprocessed messages for CEO.", flush=True)
                
                for msg in unprocessed:
                    # Handle message via CEO Agent
                    print(f"[AgentManager] CEO processing message: {msg.message_id}", flush=True)
                    self.ceo.handle_message(msg.to_dict())
                    
                    # Mark as processed
                    msg.processed = True
                    msg.save()
                
                # 2. Check for human messages in chat directly that might have been missed by the view logic
                # (Optional safety check)
                
            except Exception as e:
                # Handle MongoDB connection issues gracefully
                from pymongo.errors import AutoReconnect, ServerSelectionTimeoutError
                # Check message for WinError 10053 or similar if e is typical Exception
                error_str = str(e)
                if isinstance(e, (AutoReconnect, ServerSelectionTimeoutError)) or "10053" in error_str:
                    print(f"[AgentManager] MongoDB Connection Error: {e}. Waiting 5s before retry...", flush=True)
                    time.sleep(5)
                else:
                    print(f"[AgentManager] Error: {e}", flush=True)
            
            time.sleep(2) # Poll every 2 seconds

    def stop(self):
        self.is_running = False

# Global instance
manager = None

def start_agents():
    global manager
    if getattr(settings, 'START_AGENTS_IN_PROCESS', False) and manager is None:
        manager = InProcessAgentManager()
        manager.start()
