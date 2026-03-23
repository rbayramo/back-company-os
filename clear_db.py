import os
import mongoengine
from dotenv import load_dotenv

load_dotenv()
mongoengine.connect(
    db=os.environ.get('MONGO_DB_NAME', 'agent_swarm_os'),
    host=os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
)

from api.models import Agent, AgentMessage, ConversationMessage, Project, Ticket

print(f"Deleted {Agent.objects.all().delete()} agents")
print(f"Deleted {AgentMessage.objects.all().delete()} agent_messages")
print(f"Deleted {ConversationMessage.objects.all().delete()} conversation_messages")
print(f"Deleted {Project.objects.all().delete()} projects")
print(f"Deleted {Ticket.objects.all().delete()} tickets")
print("Database cleared.")
