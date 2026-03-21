import mongoengine as me
from datetime import datetime


class Project(me.Document):
    meta = {'collection': 'projects'}

    title = me.StringField(required=True, max_length=200)
    description = me.StringField(default='')
    status = me.StringField(choices=['active', 'paused', 'completed', 'archived'], default='active')
    goal = me.StringField(default='')
    created_at = me.DateTimeField(default=datetime.utcnow)
    updated_at = me.DateTimeField(default=datetime.utcnow)
    created_by = me.StringField(default='user')
    tags = me.ListField(me.StringField())

    def to_dict(self):
        return {
            'id': str(self.id),
            '_id': str(self.id),
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'goal': self.goal,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'created_by': self.created_by,
            'tags': self.tags,
        }


class ConversationMessage(me.Document):
    meta = {'collection': 'conversation_messages', 'indexes': [
        {'fields': ['project_id', 'timestamp']},
    ]}

    project_id = me.StringField(required=True)
    sender = me.StringField(choices=['human', 'ceo'], required=True)
    sender_id = me.StringField(default='user')
    text = me.StringField(required=True)
    timestamp = me.DateTimeField(default=datetime.utcnow)
    attachments = me.ListField(me.StringField())
    structured_data = me.DictField()
    processed = me.BooleanField(default=False)

    def to_dict(self):
        return {
            'id': str(self.id),
            '_id': str(self.id),
            'project_id': self.project_id,
            'sender': self.sender,
            'sender_id': self.sender_id,
            'text': self.text,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'attachments': self.attachments,
            'structured_data': self.structured_data,
            'processed': self.processed,
        }


class AgentMessage(me.Document):
    meta = {'collection': 'agent_messages', 'indexes': ['project_id', 'timestamp', 'sender', 'recipient']}

    message_id = me.StringField()
    timestamp = me.DateTimeField(default=datetime.utcnow)
    message_type = me.StringField()
    sender = me.StringField()
    recipient = me.StringField()
    project_id = me.StringField()
    ticket_id = me.StringField()
    payload = me.DictField()
    processed = me.BooleanField(default=False)

    def to_dict(self):
        return {
            '_id': str(self.id),
            'message_id': self.message_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'message_type': self.message_type,
            'sender': self.sender,
            'recipient': self.recipient,
            'project_id': self.project_id,
            'ticket_id': self.ticket_id,
            'payload': self.payload,
            'processed': self.processed,
        }


class BudgetField(me.EmbeddedDocument):
    allocated = me.FloatField(default=0.0)
    spent = me.FloatField(default=0.0)
    remaining = me.FloatField(default=0.0)


class Ticket(me.Document):
    meta = {'collection': 'tickets', 'indexes': ['project_id', 'status', 'assigned_to', 'priority']}

    project_id = me.StringField(required=True)
    goal_ancestry = me.ListField(me.StringField())
    title = me.StringField(required=True)
    description = me.StringField(default='')
    status = me.StringField(
        choices=['draft', 'assigned', 'in_progress', 'completed', 'failed', 'cancelled'],
        default='draft'
    )
    priority = me.StringField(choices=['low', 'medium', 'high', 'critical'], default='medium')
    assigned_to = me.StringField()
    department = me.StringField()
    dependencies = me.ListField(me.StringField())
    budget = me.EmbeddedDocumentField(BudgetField, default=BudgetField)
    created_by = me.StringField(default='agent:ceo')
    created_at = me.DateTimeField(default=datetime.utcnow)
    assigned_at = me.DateTimeField()
    completed_at = me.DateTimeField()
    updated_at = me.DateTimeField(default=datetime.utcnow)
    version = me.IntField(default=1)
    logs = me.ListField(me.StringField())
    output = me.DictField()
    tags = me.ListField(me.StringField())

    def to_dict(self):
        return {
            'id': str(self.id),
            '_id': str(self.id),
            'project_id': self.project_id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'assigned_to': self.assigned_to,
            'department': self.department,
            'dependencies': self.dependencies,
            'budget': {
                'allocated': self.budget.allocated if self.budget else 0,
                'spent': self.budget.spent if self.budget else 0,
                'remaining': self.budget.remaining if self.budget else 0,
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'version': self.version,
            'tags': self.tags,
            'output': self.output,
        }


class Agent(me.Document):
    meta = {'collection': 'agents', 'indexes': ['department', 'status']}

    agent_id = me.StringField(primary_key=True)
    label = me.StringField()
    department = me.StringField()
    capabilities = me.ListField(me.StringField())
    status = me.StringField(choices=['idle', 'busy', 'offline', 'error'], default='idle')
    current_tickets = me.ListField(me.StringField())
    last_heartbeat = me.DateTimeField()
    budget_rate_usd_per_hour = me.FloatField(default=0.10)
    max_concurrent_tasks = me.IntField(default=2)
    version = me.IntField(default=1)
    llm_config = me.DictField()

    def to_dict(self):
        return {
            '_id': str(self.agent_id),
            'label': self.label,
            'department': self.department,
            'capabilities': self.capabilities,
            'status': self.status,
            'current_tickets': self.current_tickets,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
        }


class Budget(me.Document):
    meta = {'collection': 'budgets'}
    budget_id = me.StringField(primary_key=True)
    type = me.StringField()
    allocated = me.FloatField(default=0.0)
    spent = me.FloatField(default=0.0)
    reserved = me.FloatField(default=0.0)
    currency = me.StringField(default='USD')
    updated_at = me.DateTimeField(default=datetime.utcnow)


class MemoryVector(me.Document):
    meta = {'collection': 'memory_vectors'}
    timestamp = me.DateTimeField(default=datetime.utcnow)
    source_type = me.StringField()
    source_id = me.StringField()
    text_summary = me.StringField()
    metadata = me.DictField()


class Resource(me.Document):
    meta = {'collection': 'resources'}
    name = me.StringField(required=True)
    type = me.StringField()
    format = me.StringField()
    gridfs_id = me.StringField()
    project_id = me.StringField()
    department = me.StringField()
    tags = me.ListField(me.StringField())
    description = me.StringField()
    created_by = me.StringField()
    created_at = me.DateTimeField(default=datetime.utcnow)

    def to_dict(self):
        return {
            '_id': str(self.id),
            'name': self.name,
            'type': self.type,
            'project_id': self.project_id,
            'department': self.department,
            'tags': self.tags,
            'description': self.description,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

class Company(me.Document):
    meta = {'collection': 'companies'}
    name = me.StringField(required=True)
    industry = me.StringField()
    mission = me.StringField()
    vision = me.StringField()
    stage = me.StringField()
    created_at = me.DateTimeField(default=datetime.utcnow)

    def to_dict(self):
        return {
            '_id': str(self.id),
            'name': self.name,
            'industry': self.industry,
            'mission': self.mission,
            'vision': self.vision,
            'stage': self.stage,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
