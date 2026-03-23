import os
import sys

# Add the project root to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(root_dir)

import mongoengine as me
from api.models import Agent, TicketType
from dotenv import load_dotenv
from datetime import datetime

# Try to find .env in various locations
load_dotenv(dotenv_path=os.path.join(root_dir, '.env'))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(root_dir), '.env'))
load_dotenv(dotenv_path=os.path.join(root_dir, 'backend', '.env'))

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/agent_swarm_os')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'agent_swarm_os')

DEFAULT_LLM_CONFIG = {
    "api_key": os.getenv('DEEPSEEK_API_KEY'),
    "api_key_name": "DEEPSEEK_API_KEY",
    "model": os.getenv('DEEPSEEK_MODEL')
}

def seed():
    print(f"Connecting to MongoDB at {MONGO_URI}...")
    me.connect(MONGO_DB_NAME, host=MONGO_URI)

    # 1. Seed Agents (15 total)
    agents_data = [
        {"agent_id": "ceo", "label": "CEO", "department": "Management", "type": "llm", "capabilities": ["decompose_goal", "clarify_requirements", "propose_plan", "create_ticket"]},
        {"agent_id": "coo", "label": "COO", "department": "Orchestration", "type": "llm", "capabilities": ["assign_ticket", "manage_dependencies", "monitor_agents", "reassign_ticket", "orchestrate", "route_to_auditor"]},
        {"agent_id": "gatekeeper", "label": "Gatekeeper", "department": "Governance", "type": "llm", "capabilities": ["check_budget", "reserve_budget", "deduct_budget", "release_budget", "enforce_policy"]},
        {"agent_id": "technical_auditor", "label": "Technical Auditor", "department": "Auditors", "type": "llm", "capabilities": ["review_code", "run_tests", "generate_test_cases", "document_errors", "test_integration", "security_audit"]},
        {"agent_id": "experience_auditor", "label": "Experience Auditor", "department": "Auditors", "type": "llm", "capabilities": ["review_ux", "test_usability", "check_accessibility", "brand_compliance", "provide_feedback"]},
        {"agent_id": "ui_ux", "label": "UI/UX Designer", "department": "Brand & Design", "type": "llm", "capabilities": ["create_wireframes", "design_screens", "build_prototypes", "deliver_assets", "follow_brand_guide"]},
        {"agent_id": "branding", "label": "Branding Expert", "department": "Brand & Design", "type": "llm", "capabilities": ["create_logo", "define_palette", "write_guidelines", "create_templates"]},
        {"agent_id": "antigravity", "label": "Antigravity Engineer", "department": "Engineering", "type": "llm", "capabilities": ["full_stack_dev", "backend_dev", "frontend_dev", "database_design", "api_development", "deploy_code", "write_tests"]},
        {"agent_id": "instagram", "label": "Instagram Agent", "department": "Growth & Marketing", "type": "llm", "capabilities": ["create_post", "schedule_post", "reply_to_comments", "reply_to_direct_messages", "track_metrics", "analyze_engagement", "manage_hashtags"]},
        {"agent_id": "whatsapp", "label": "WhatsApp Agent", "department": "Growth & Marketing", "type": "llm", "capabilities": ["send_message", "send_campaign", "handle_conversation", "track_response", "schedule_message", "onboard_user"]},
        {"agent_id": "seo", "label": "SEO Expert", "department": "Growth & Marketing", "type": "llm", "capabilities": ["keyword_research", "optimize_content", "analyze_rankings", "competitor_analysis", "backlink_strategy", "feedback_to_creator"]},
        {"agent_id": "email", "label": "Email Marketer", "department": "Growth & Marketing", "type": "llm", "capabilities": ["send_email", "create_campaign", "ab_test", "track_metrics", "schedule_meeting", "respond_to_email", "filter_contacts"]},
        {"agent_id": "content_creator", "label": "Content Creator", "department": "Growth & Marketing", "type": "llm", "capabilities": ["generate_text", "generate_image", "create_pdf", "create_presentation", "use_template", "incorporate_feedback"]},
        {"agent_id": "reels_maker", "label": "Reels Maker", "department": "Growth & Marketing", "type": "llm", "capabilities": ["edit_video", "add_captions", "add_music", "produce_reel", "analyze_video_performance"]},
        {"agent_id": "researcher", "label": "Strategic Researcher", "department": "Growth & Marketing", "type": "llm", "capabilities": ["query_companies", "query_people", "find_leads", "monitor_trends", "competitive_intel", "generate_report", "analyze_insights"]}
    ]

    print("Seeding Agents...")
    for a in agents_data:
        agent_fields = a.copy()
        agent_fields["llm_config"] = DEFAULT_LLM_CONFIG
        agent_fields["status"] = "idle"
        agent_fields["version"] = 1
        agent_fields["max_concurrent_tasks"] = 1
        agent_fields["budget_rate_usd_per_hour"] = 1 if a["department"] == "Management" else 0
        agent_fields["heartbeat_schedule"] = "*/5 * * * *"
        agent_fields["last_heartbeat"] = datetime.utcnow()
        
        Agent.objects(agent_id=a["agent_id"]).update_one(upsert=True, **agent_fields)
        print(f" - Registered {a['agent_id']} ({a['label']})")

    # 2. Seed Ticket Types (Specialized blueprints)
    ticket_types_data = [
        # Brand & Design
        {"_id": "ttype_logo", "description": "Create vector logo", "required_capabilities": ["create_logo"], "required_assets": ["brand_guidelines"], "template_parameters": {"brand_name": {"type": "string", "required": True}, "style": {"type": "string", "default": "modern"}}},
        {"_id": "ttype_brand_guidelines", "description": "Create brand guidelines", "required_capabilities": ["write_guidelines"], "template_parameters": {"brand_name": {"type": "string", "required": True}}},
        {"_id": "ttype_wireframe", "description": "Create wireframes", "required_capabilities": ["create_wireframes"], "template_parameters": {"screen": {"type": "string", "required": True}}},
        {"_id": "ttype_high_fidelity_design", "description": "Create high-fidelity mockups", "required_capabilities": ["design_screens"], "required_assets": ["style_guide"], "template_parameters": {"screen": {"type": "string", "required": True}}},

        # Engineering
        {"_id": "ttype_backend_setup", "description": "Set up backend", "required_capabilities": ["backend_dev"], "template_parameters": {"tech": {"type": "string", "default": "python/django"}}},
        {"_id": "ttype_frontend_setup", "description": "Set up frontend", "required_capabilities": ["frontend_dev"], "template_parameters": {"tech": {"type": "string", "default": "react"}}},
        {"_id": "ttype_api_development", "description": "Develop API endpoint", "required_capabilities": ["api_development"], "template_parameters": {"endpoint": {"type": "string", "required": True}}},

        # Growth & Marketing
        {"_id": "ttype_instagram_post", "description": "Create Instagram post", "required_capabilities": ["create_post"], "required_assets": ["logo", "brand_guidelines"], "template_parameters": {"topic": {"type": "string", "required": True}}},
        {"_id": "ttype_email_campaign", "description": "Send email campaign", "required_capabilities": ["create_campaign"], "template_parameters": {"target": {"type": "string", "required": True}}},
        {"_id": "ttype_keyword_research", "description": "Research keywords", "required_capabilities": ["keyword_research"], "template_parameters": {"topic": {"type": "string", "required": True}}},
        {"_id": "ttype_lead_generation", "description": "Find leads", "required_capabilities": ["find_leads"], "template_parameters": {"industry": {"type": "string", "required": True}}},

        # Auditing
        {"_id": "ttype_code_review", "description": "Review code", "required_capabilities": ["review_code"], "template_parameters": {"ticket_id": {"type": "string", "required": True}}},
        {"_id": "ttype_ux_review", "description": "Review UX", "required_capabilities": ["review_ux"], "template_parameters": {"ticket_id": {"type": "string", "required": True}}}
    ]

    print("Seeding Ticket Types...")
    for t in ticket_types_data:
        # Renaming internal _id to id to match refactored models.py
        data = t.copy()
        tid = data.pop("_id")
        TicketType.objects(id=tid).update_one(upsert=True, **data)
        print(f" - Registered {tid} ({t['description']})")

    print("\nSwarm Seeded Successfully!")

if __name__ == "__main__":
    seed()
