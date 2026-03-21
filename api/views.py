import json
import uuid
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import Project, ConversationMessage, Ticket, Agent, AgentMessage, Company

# ─── Company ─────────────────────────────────────────────────────────────────

@csrf_exempt
def company_detail(request):
    """GET /api/company/ – get current company
       POST /api/company/ – set up company"""
    if request.method == 'GET':
        company = Company.objects.first()
        if not company:
            return JsonResponse(None, safe=False)
        return JsonResponse(company.to_dict())

    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Remove existing if any (since we only support ONE company)
        Company.objects.all().delete()

        company = Company(
            name=data.get('name'),
            industry=data.get('industry'),
            mission=data.get('mission'),
            vision=data.get('vision'),
            stage=data.get('stage'),
        )
        company.save()
        return JsonResponse(company.to_dict(), status=201)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def _get_company_context():
    """Aggregate company and all missions into a single context string for the CEO."""
    try:
        from .models import Company, Project
        company = Company.objects.first()
        projects = Project.objects.all()
        
        ctx = ""
        if company:
            ctx += f"COMPANY: {company.name} ({company.industry})\n"
            ctx += f"MISSION: {company.mission}\n"
            ctx += f"VISION: {company.vision}\n\n"
        
        if projects:
            ctx += "ALL MISSIONS/PROJECTS IN THIS COMPANY:\n"
            for p in projects:
                ctx += f"- {p.title} (Status: {p.status}): {p.goal or 'No goal set'}\n"
        
        return ctx
    except Exception as e:
        print(f"[_get_company_context] Error: {e}", flush=True)
        return ""


# ─── Projects ────────────────────────────────────────────────────────────────

@csrf_exempt
def projects_list(request):
    """GET /api/projects/ – list all projects
       POST /api/projects/ – create new project"""
    try:
        if request.method == 'GET':
            projects = Project.objects.order_by('-created_at')
            return JsonResponse([p.to_dict() for p in projects], safe=False)
        
        elif request.method == 'POST':
            try:
                data = json.loads(request.body)
            except Exception:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            
            project = Project(
                title=data.get('title', 'Untitled Project'),
                description=data.get('description', ''),
                goal=data.get('goal', ''),
                tags=data.get('tags', []),
            )
            project.save()
            
            # Note: Initial CEO welcome is now handled synchronously in messages_list (GET)
            # when the frontend first fetches the conversation for this project.
            
            return JsonResponse(project.to_dict(), status=201)
    except Exception as e:
        import traceback
        print(f"[Views ERROR] projects_list: {traceback.format_exc()}", flush=True)
        return JsonResponse({'error': str(e), 'traceback': traceback.format_exc()}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def project_detail(request, project_id):
    """GET/PATCH /api/projects/<id>/"""
    try:
        project = Project.objects.get(id=project_id)
    except Exception:
        return JsonResponse({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        return JsonResponse(project.to_dict())

    elif request.method == 'PATCH':
        data = json.loads(request.body)
        for field in ['title', 'description', 'status', 'goal', 'tags']:
            if field in data:
                setattr(project, field, data[field])
        project.updated_at = datetime.utcnow()
        project.save()
        return JsonResponse(project.to_dict())

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ─── Messages ────────────────────────────────────────────────────────────────

@csrf_exempt
def messages_list(request, project_id):
    """GET /api/projects/<id>/messages/ – get conversation
       POST – send human message → queue to CEO"""
    try:
        if request.method == 'GET':
            msgs = ConversationMessage.objects.filter(project_id=str(project_id)).order_by('timestamp')
            
            # Initial CEO trigger if no messages and project has goal
            if not msgs:
                try:
                    # Handle possible missing project or invalid ID
                    project = Project.objects.filter(id=project_id).first()
                    if project and project.goal:
                        print(f"[Views] First access to project {project_id}. Generating synchronous structured CEO response...", flush=True)
                        from agents.ceo_agent import CEOAgent
                        ceo = CEOAgent()
                        
                        # Get Global Context
                        company_context = _get_company_context()
                        full_prompt = ceo.get_system_prompt(company_context)
                        
                        user_prompt = f"Initial Project Setup Goal: {project.goal}"
                        ai_raw = ceo.call_llm(full_prompt, user_prompt, json_mode=True)
                        
                        try:
                            ai_json = json.loads(ai_raw)
                            response_text = ai_json.get('response_text', f"Welcome! Let's work on: {project.goal}")
                            suggested_tasks = ai_json.get('suggested_tasks', [])
                        except Exception as e:
                            print(f"[Views] Initial JSON parse failed: {e}", flush=True)
                            response_text = ai_raw
                            suggested_tasks = []

                        ceo_msg = ConversationMessage(
                            project_id=str(project_id),
                            sender='ceo',
                            text=response_text,
                            processed=True,
                        )
                        ceo_msg.save()
                        
                        if suggested_tasks:
                            ceo._draft_tickets(str(project_id), suggested_tasks)
                            
                        msgs = [ceo_msg]
                except Exception as e:
                    print(f"[Views] Error triggering initial CEO: {e}", flush=True)

            return JsonResponse([m.to_dict() for m in msgs], safe=False)

        elif request.method == 'POST':
            try:
                data = json.loads(request.body)
            except Exception:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)

            text = data.get('text', '').strip()
            if not text:
                return JsonResponse({'error': 'text is required'}, status=400)

            # 1. Fetch History for Context
            history_msgs = ConversationMessage.objects.filter(project_id=str(project_id)).order_by('-timestamp')[:15]
            formatted_history = []
            for m in reversed(history_msgs):
                role = "user" if m.sender == 'human' else "assistant"
                formatted_history.append({"role": role, "content": m.text or ""})

            # 2. Save human message
            human_msg = ConversationMessage(
                project_id=str(project_id),
                sender='human',
                text=text,
                processed=True,
            )
            human_msg.save()

            # 3. Get CEO Agent and call synchronously
            from agents.ceo_agent import CEOAgent
            ceo = CEOAgent()
            
            # Get Global Context
            company_context = _get_company_context()
            full_prompt = ceo.get_system_prompt(company_context)
            
            try:
                print(f"[Views] Calling CEOAgent (JSON Mode + History + Global Context) for project {project_id}...", flush=True)
                ai_raw = ceo.call_llm(full_prompt, text, history=formatted_history, json_mode=True)
                
                try:
                    ai_json = json.loads(ai_raw)
                    ceo_response_text = ai_json.get('response_text', "I've processed your message.")
                    suggested_tasks = ai_json.get('suggested_tasks', [])
                except Exception as e:
                    print(f"[Views] Failed to parse CEO JSON: {e}", flush=True)
                    ceo_response_text = ai_raw
                    suggested_tasks = []

                # 4. Save CEO response
                ceo_msg = ConversationMessage(
                    project_id=str(project_id),
                    sender='ceo',
                    text=ceo_response_text,
                    processed=True,
                )
                ceo_msg.save()

                # 5. Handle Suggested Tasks (create tickets)
                if suggested_tasks:
                    ceo._draft_tickets(str(project_id), suggested_tasks)

                # 6. Return both
                return JsonResponse({
                    'human_message': human_msg.to_dict(),
                    'ceo_message': ceo_msg.to_dict()
                }, status=201)
            except Exception as e:
                print(f"[Views] Error in CEO processing: {e}", flush=True)
                return JsonResponse(human_msg.to_dict(), status=201)
    except Exception as e:
        import traceback
        print(f"[Views ERROR] messages_list: {traceback.format_exc()}", flush=True)
        return JsonResponse({'error': str(e), 'traceback': traceback.format_exc()}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ─── Tickets / Kanban ─────────────────────────────────────────────────────────

def tickets_list(request, project_id):
    """GET /api/projects/<id>/tickets/"""
    tickets = Ticket.objects.filter(project_id=project_id).order_by('-created_at')
    return JsonResponse([t.to_dict() for t in tickets], safe=False)


@csrf_exempt
def ticket_detail(request, project_id, ticket_id):
    """PATCH /api/projects/<id>/tickets/<tid>/"""
    try:
        ticket = Ticket.objects.get(id=ticket_id, project_id=project_id)
    except Exception:
        return JsonResponse({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        return JsonResponse(ticket.to_dict())

    elif request.method == 'PATCH':
        data = json.loads(request.body)
        for field in ['status', 'priority', 'assigned_to', 'description', 'tags']:
            if field in data:
                setattr(ticket, field, data[field])
        ticket.updated_at = datetime.utcnow()
        ticket.version += 1
        ticket.save()
        return JsonResponse(ticket.to_dict())

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ─── Agents ──────────────────────────────────────────────────────────────────

def agents_list(request):
    """GET /api/agents/"""
    agents = Agent.objects.all()
    return JsonResponse([a.to_dict() for a in agents], safe=False)


# ─── Logs ────────────────────────────────────────────────────────────────────

def logs_list(request, project_id):
    """GET /api/projects/<id>/logs/"""
    msgs = AgentMessage.objects.filter(project_id=project_id).order_by('-timestamp')[:200]
    result = []
    for m in msgs:
        result.append({
            'id': str(m.id),
            'agent': m.sender.replace('agent:', '') if m.sender else 'system',
            'agent_label': m.sender.replace('agent:', '').upper() if m.sender else 'System',
            'message': f"[{m.message_type}] {json.dumps(m.payload)[:120]}" if m.payload else m.message_type,
            'timestamp': m.timestamp.isoformat() if m.timestamp else None,
            'type': 'info',
        })
    return JsonResponse(list(reversed(result)), safe=False)


# ─── CEO Queue Publisher ──────────────────────────────────────────────────────

def _publish_to_ceo(project, text, msg_id=None):
    """Publish a human_message to the CEO agent task queue."""
    print(f"[Views] Queuing message for CEO: {text[:50]}...", flush=True)
    # 1. Create AgentMessage in MongoDB (Acts as the queue)
    msg = AgentMessage(
        message_id=f'task_{uuid.uuid4().hex[:8]}',
        timestamp=datetime.utcnow(),
        message_type='human_message',
        sender='human',
        recipient='agent:ceo',
        project_id=str(project.id),
        payload={
            'project_id': str(project.id),
            'conversation_message_id': msg_id or '',
            'text': text,
        },
        processed=False
    )
    msg.save()

    # 2. Optionally notify via Redis (as a speed-up if available)
    try:
        import redis
        import os
        r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        r.rpush('queue:agent:ceo', json.dumps(msg.to_dict()))
    except:
        pass
