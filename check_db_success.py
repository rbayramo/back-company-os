import os
import django
from django.conf import settings
from api.models import ConversationMessage, AgentMessage

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def check_success():
    print("--- Checking MongoDB for CEO Response ---")
    
    # 1. Check for any CEO response created in the last 5 minutes
    ceo_responses = ConversationMessage.objects(sender='ceo').order_by('-timestamp')[:5]
    if ceo_responses:
        print(f"Found {len(ceo_responses)} Recent CEO Responses:")
        for r in ceo_responses:
            print(f"- [{r.timestamp}] project={r.project_id}: {r.text[:50]}...")
    else:
        print("No recent CEO responses found.")

    # 2. Check for unprocessed AgentMessages
    unprocessed = AgentMessage.objects(recipient='agent:ceo', processed=False)
    if unprocessed:
        print(f"Found {len(unprocessed)} UNPROCESSED AgentMessages for CEO.")
    else:
        print("All CEO AgentMessages have been processed.")

if __name__ == "__main__":
    check_success()
