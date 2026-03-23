import os
import sys
import uuid
import pika
import json
import time

# Add root to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

import mongoengine as me
from api.models import Ticket, Project, ConversationMessage, Resource
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(root_dir, '.env'))

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/agent_swarm_os')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'agent_swarm_os')

def test_ceo():
    me.connect(MONGO_DB_NAME, host=MONGO_URI)
    
    # 1. Setup Test Project
    project = Project(
        title="Test: Café Volt Branding",
        description="We need a full branding package and an Instagram presence for our new coffee shop, Café Volt."
    )
    project.save()
    project_id = str(project.id)
    print(f"Created Test Project: {project_id}")

    # 2. Publish Message to CEO
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='queue:agent:ceo', durable=True)
    
    payload = {
        "message_type": "human_message",
        "payload": {
            "text": "Please plan the branding and Instagram launch for Café Volt.",
            "project_id": project_id
        },
        "project_id": project_id
    }
    
    channel.basic_publish(
        exchange='',
        routing_key='queue:agent:ceo',
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    print("Sent mission to CEO Agent...")
    connection.close()

    # 3. Wait for CEO to process
    print("Waiting 45 seconds for CEO to think and draft tickets...")
    time.sleep(45)

    # 4. Verify Results
    tickets = Ticket.objects(project_id=project_id)
    print(f"\nFound {len(tickets)} drafted tickets:")
    for t in tickets:
        print(f" - [{t.priority}] {t.title} (Type: {t.ticket_type_id}, Dept: {t.department})")
        print(f"   Desc Len: {len(t.description)} chars")
        if len(t.description) > 50:
             print(f"   Desc snippet: {t.description[:100]}...")

    if len(tickets) > 0:
        print("\nSUCCESS: CEO generated tickets with the new blueprint system!")
        # Check for sequencing (Branding/Guidelines should be first)
        first_ticket = tickets[0]
        if 'guidelines' in first_ticket.title.lower() or 'logo' in first_ticket.title.lower():
             print("VERIFIED: Plan appears to be correctly sequenced.")
    else:
        print("\nFAILURE: No tickets were generated. Check if the CEO Agent process is running.")

if __name__ == "__main__":
    test_ceo()
