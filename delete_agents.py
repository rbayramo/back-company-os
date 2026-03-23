import os
import mongoengine as me
from dotenv import load_dotenv

load_dotenv()
try:
    me.connect(
        db=os.environ.get('MONGO_DB_NAME', 'agent_swarm_os'),
        host=os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    )
    from api.models import Agent
    count = Agent.objects.count()
    Agent.objects.delete()
    print(f"Deleted {count} agents from DB natively.")
except Exception as e:
    print("Failed to delete agents:", e)
