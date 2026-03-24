import mongoengine as me
from datetime import datetime


class Project(me.Document):
    meta = {'collection': 'projects'}

    title = me.StringField(required=True, max_length=200)
    description = me.StringField(default='')
    status = me.StringField(choices=['active', 'archived', 'completed'], default='active')
    goal = me.StringField(default='')
    created_at = me.DateTimeField(default=datetime.utcnow)
    updated_at = me.DateTimeField(default=datetime.utcnow)
    created_by = me.StringField(default='anonymous')
    tags = me.ListField(me.StringField())
    auto_pilot = me.BooleanField(default=False)

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
            'auto_pilot': self.auto_pilot,
        }


class ConversationMessage(me.Document):
    meta = {'collection': 'conversation_messages', 'indexes': [
        {'fields': ['project_id', 'timestamp']},
    ]}

    project_id = me.StringField(required=True)
    sender = me.StringField(choices=['human', 'agent:ceo'], required=True)
    sender_id = me.StringField()
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

    message_id = me.StringField(required=True, unique=True)
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
            'id': str(self.id),
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

    id = me.StringField(primary_key=True)
    project_id = me.StringField(required=True)
    goal_ancestry = me.ListField(me.StringField())
    title = me.StringField(required=True)
    description = me.StringField(default='')
    department = me.StringField()
    status = me.StringField(
        choices=['draft', 'open', 'assigned', 'in_progress', 'audit_pending', 'completed', 'rejected'],
        default='draft'
    )
    priority = me.StringField(choices=['low', 'medium', 'high', 'critical'], default='medium')
    assigned_to = me.StringField()
    dependencies = me.ListField(me.StringField())
    budget = me.EmbeddedDocumentField(BudgetField, default=BudgetField)
    created_by = me.StringField()
    created_at = me.DateTimeField(default=datetime.utcnow)
    assigned_at = me.DateTimeField()
    completed_at = me.DateTimeField()
    updated_at = me.DateTimeField(default=datetime.utcnow)
    version = me.IntField(default=1)
    logs = me.ListField(me.StringField())
    output = me.DictField()
    tags = me.ListField(me.StringField())
    ticket_type_id = me.StringField()

    def to_dict(self):
        return {
            'id': self.id,
            '_id': self.id,
            'project_id': self.project_id,
            'goal_ancestry': self.goal_ancestry,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'assigned_to': self.assigned_to,
            'dependencies': self.dependencies,
            'budget': {
                'allocated': self.budget.allocated if self.budget else 0,
                'spent': self.budget.spent if self.budget else 0,
                'remaining': self.budget.remaining if self.budget else 0,
            },
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'version': self.version,
            'logs': self.logs,
            'output': self.output,
            'tags': self.tags,
            'ticket_type_id': self.ticket_type_id,
        }


class TicketHistory(me.Document):
    meta = {'collection': 'ticket_history', 'indexes': ['ticket_id']}
    
    ticket_id = me.StringField(required=True)
    version = me.IntField()
    document = me.DictField()
    modified_at = me.DateTimeField(default=datetime.utcnow)
    modified_by = me.StringField()
    change_type = me.StringField(choices=['creation', 'status_update', 'assignment', 'rollback'])


class Agent(me.Document):
    meta = {'collection': 'agents', 'indexes': ['department', 'status']}

    agent_id = me.StringField(primary_key=True)
    label = me.StringField()
    department = me.StringField()
    type = me.StringField(choices=['llm', 'dummy'], default='llm')
    status = me.StringField(choices=['idle', 'busy', 'offline'], default='offline')
    capabilities = me.ListField(me.StringField())
    current_tickets = me.ListField(me.StringField())
    last_heartbeat = me.DateTimeField()
    last_processed_msg_id = me.StringField()
    heartbeat_schedule = me.StringField()
    budget_rate_usd_per_hour = me.FloatField(default=0.0)
    max_concurrent_tasks = me.IntField(default=1)
    is_active = me.BooleanField(default=True)
    llm_config = me.DictField()
    version = me.IntField(default=1)

    def to_dict(self):
        return {
            '_id': self.agent_id,
            'agent_id': self.agent_id,
            'label': self.label,
            'department': self.department,
            'type': self.type,
            'status': self.status,
            'is_active': self.is_active,
            'capabilities': self.capabilities,
            'current_tickets': self.current_tickets,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'budget_rate_usd_per_hour': self.budget_rate_usd_per_hour,
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'llm_config': self.llm_config,
        }


class TicketType(me.Document):
    meta = {'collection': 'ticket_types'}

    id = me.StringField(primary_key=True) # e.g. ttype_logo
    parent_id = me.StringField()
    description = me.StringField()
    required_assets = me.ListField(me.StringField())
    required_capabilities = me.ListField(me.StringField())
    template_parameters = me.DictField() # e.g. {'brand_name': {'type': 'string', 'required': True}}
    system_instructions = me.StringField(default='') # Global 'HOW-TO' for this blueprint
    audit_failure_count = me.IntField(default=0) # Track global failures for self-healing

    def to_dict(self):
        return {
            'id': self.id,
            '_id': self.id,
            'parent_id': self.parent_id,
            'description': self.description,
            'required_assets': self.required_assets,
            'required_capabilities': self.required_capabilities,
            'template_parameters': self.template_parameters,
            'system_instructions': self.system_instructions,
            'audit_failure_count': self.audit_failure_count,
        }


class KnowledgeExperience(me.Document):
    meta = {'collection': 'knowledge_experience', 'indexes': ['ttype_id', 'context_tags']}

    ttype_id = me.StringField(required=True)
    task_goal = me.StringField()
    best_practice_output = me.StringField() # The 'Gold' snippet
    context_tags = me.ListField(me.StringField())
    embedding = me.ListField(me.FloatField()) # For semantic retrieval
    created_at = me.DateTimeField(default=datetime.utcnow)
    success_rating = me.IntField(default=1) # Incremented if reused successfully

    def to_dict(self):
        return {
            'id': str(self.id),
            'ttype_id': self.ttype_id,
            'task_goal': self.task_goal,
            'best_practice_output': self.best_practice_output,
            'context_tags': self.context_tags,
            'success_rating': self.success_rating
        }


class Budget(me.Document):
    meta = {'collection': 'budgets'}
    
    _id = me.StringField(primary_key=True)
    type = me.StringField(choices=['project', 'department'])
    allocated = me.FloatField(default=0.0)
    spent = me.FloatField(default=0.0)
    reserved = me.FloatField(default=0.0)
    currency = me.StringField(default='USD')
    updated_at = me.DateTimeField(default=datetime.utcnow)


class MemoryVector(me.Document):
    meta = {'collection': 'memory_vectors'}
    
    timestamp = me.DateTimeField(default=datetime.utcnow)
    source_type = me.StringField(choices=['ticket', 'conversation', 'audit'])
    source_id = me.StringField()
    embedding = me.ListField(me.FloatField())
    text_summary = me.StringField()
    metadata = me.DictField()


class Resource(me.Document):
    meta = {'collection': 'resources', 'indexes': ['project_id', 'department']}
    
    name = me.StringField(required=True)
    type = me.StringField(choices=['image', 'document', 'code', 'data', 'video', 'audio'])
    format = me.StringField()
    gridfs_id = me.StringField()
    project_id = me.StringField()
    department = me.StringField()
    tags = me.ListField(me.StringField())
    description = me.StringField()
    created_by = me.StringField()
    created_at = me.DateTimeField(default=datetime.utcnow)
    version = me.IntField(default=1)
    checksum = me.StringField()
    access_roles = me.ListField(me.StringField())
    expires_at = me.DateTimeField()
    embedding = me.ListField(me.FloatField())

    def to_dict(self):
        return {
            '_id': str(self.id),
            'name': self.name,
            'type': self.type,
            'format': self.format,
            'gridfs_id': self.gridfs_id,
            'project_id': self.project_id,
            'department': self.department,
            'tags': self.tags,
            'description': self.description,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ResourceRelationship(me.Document):
    meta = {'collection': 'resource_relationships', 'indexes': ['source_id', 'target_id']}
    
    source_id = me.StringField(required=True)
    target_id = me.StringField(required=True)
    target_type = me.StringField(choices=['ticket', 'project', 'resource', 'agent'])
    relation = me.StringField(choices=['used_in', 'derived_from', 'depends_on'])
    created_at = me.DateTimeField(default=datetime.utcnow)


class Company(me.Document):
    meta = {'collection': 'companies'}
    
    name = me.StringField(required=True)
    website = me.StringField()
    email = me.StringField()
    phone = me.StringField()
    size = me.StringField()
    industry = me.StringField()
    location = me.StringField()
    scraped_at = me.DateTimeField()
    source = me.StringField()
    created_at = me.DateTimeField(default=datetime.utcnow)
    stage = me.StringField()
    mission = me.StringField()
    vision = me.StringField()

    def to_dict(self):
        return {
            '_id': str(self.id),
            'name': self.name,
            'website': self.website,
            'industry': self.industry,
        }


class Person(me.Document):
    meta = {'collection': 'people'}
    
    name = me.StringField(required=True)
    email = me.StringField()
    phone = me.StringField()
    title = me.StringField()
    company_id = me.StringField()
    linkedin = me.StringField()
    scraped_at = me.DateTimeField()

    def to_dict(self):
        return {
            '_id': str(self.id),
            'name': self.name,
            'title': self.title,
            'company_id': self.company_id,
        }
