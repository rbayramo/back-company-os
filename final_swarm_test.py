import requests
import time
import json
from pymongo import MongoClient

# Configuration
API_URL = "http://127.0.0.1:8000/api"
MONGO_URI = "mongodb://rashadbayramov815:Rashad1994@62.72.22.62:27017/?authSource=admin"
DB_NAME = "agent_swarm_os"

def test_swarm():
    print("🚀 STARTING TERMINAL SWARM VERIFICATION...")
    
    # 1. Create Project
    proj_payload = {
        "title": "Autonomous Swarm Test-V3",
        "goal": "Build a secure fintech stack with real-time audit logging using autonomous agents. Map out the entire engineering and marketing stack."
    }
    r = requests.post(f"{API_URL}/projects/", json=proj_payload)
    if r.status_code != 201:
        print(f"❌ Failed to create project: {r.text}")
        return
    
    proj_id = r.json()['id']
    print(f"✅ Created Project ID: {proj_id}")

    # 2. Toggle Auto-Pilot ON
    requests.patch(f"{API_URL}/projects/{proj_id}/", json={"auto_pilot": True})
    print("✅ Auto Pilot Toggled ON.")

    # 3. Send Signal Message
    msg_payload = {"sender": "human", "text": "GO! Develop the fintech mission now."}
    requests.post(f"{API_URL}/projects/{proj_id}/messages/", json=msg_payload)
    print("✅ Mission Signal Sent. Swarm is thinking...")

    # 4. Wait for CEO to plan (Wait 45 seconds for LLM + RabbitMQ latency)
    time.sleep(45)

    # 5. Verify Database State
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Check Messages
    messages = list(db.messages.find({"project_id": proj_id}))
    print(f"--- MESSAGES ({len(messages)}) ---")
    for m in messages:
        sender = m.get('sender', 'unknown')
        text = m.get('text', '')[:100]
        print(f"[{sender}] {text}...")

    # Check Tickets
    tickets = list(db.tickets.find({"project_id": proj_id}))
    print(f"\n--- TICKETS ({len(tickets)}) ---")
    if not tickets:
        print("❌ NO TICKETS GENERATED. CEO is likely stuck or RabbitMQ is failing.")
    for t in tickets:
        print(f"- [{t.get('status')}] {t.get('title')} (Type: {t.get('ticket_type_id')})")

    # 6. Conclusion
    if any(t.get('status') == 'draft' for t in tickets):
        print("\n🏆 SUCCESS: CEO successfully generated an autonomous plan with drafted tickets.")
    else:
        print("\n⚠️ SWARM STALLED: Checkout the RabbitMQ / CEO logs for errors.")

if __name__ == "__main__":
    test_swarm()
