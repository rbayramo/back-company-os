import requests
import json
import pika
import time
from pymongo import MongoClient

# Configuration
API_URL = "http://127.0.0.1:8000/api"
MONGO_URI = "mongodb://rashadbayramov815:Rashad1994@62.72.22.62:27017/?authSource=admin"

def test_manual_mode():
    print("🚀 STARTING MANUAL MODE VERIFICATION...")
    
    # 1. Create Project (Manual Mode by default)
    proj_payload = {
        "title": "Manual Strategy Test-V4",
        "goal": "Explain how to build a decentralized identity platform. Don't plan yet, just ask questions."
    }
    r = requests.post(f"{API_URL}/projects/", json=proj_payload)
    if r.status_code != 201:
        print(f"❌ Failed: {r.text}")
        return
    
    p = r.json()
    proj_id = p['id']
    print(f"✅ Project Created: {proj_id}")

    # 2. Wait for CEO to respond to 'new_project_mission'
    print("⏳ Waiting 30s for CEO response...")
    time.sleep(30)

    # 3. Check Messages
    client = MongoClient(MONGO_URI)
    db = client['agent_swarm_os']
    msgs = list(db.conversation_messages.find({"project_id": proj_id}))
    
    print(f"--- MESSAGES ({len(msgs)}) ---")
    ceo_responded = False
    for m in msgs:
        print(f"[{m.get('sender')}] {m.get('text')[:60]}...")
        if m.get('sender') == 'agent:ceo':
            ceo_responded = True

    if ceo_responded:
        print("\n🏆 SUCCESS: CEO responded in manual mode.")
    else:
        print("\n⚠️ STALLED: CEO did not respond to the mission signal.")

if __name__ == "__main__":
    test_manual_mode()
