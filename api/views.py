import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Project, ConversationMessage, Ticket, Agent, AgentMessage, Company
from .rabbitmq import publisher

def format_log_message(msg_type, payload):
    if not payload: return msg_type
    if msg_type == 'human_message':
        t = payload.get('text', '')
        return f"Message sent to CEO: {t[:60]}..." if len(t) > 60 else f"Message sent to CEO: {t}"
    if msg_type == 'ceo_response':
        t = payload.get('text', '')
        return f"{t[:60]}..." if len(t) > 60 else f"{t}"
    if msg_type == 'ticket_approved': return "Project plan approved by user."
    if msg_type == 'execute_task': return f"Working on ticket {payload.get('ticket_id')}"
    if msg_type == 'budget_check_request': return f"Verifying budget for {payload.get('ticket_id')}"
    if msg_type == 'budget_check_response': 
        return f"Gatekeeper {'APPROVED' if payload.get('approved') else 'DENIED'} {payload.get('ticket_id')}"
    if msg_type == 'audit_request': return f"Reviewing ticket {payload.get('ticket_id')}"
    if msg_type == 'audit_result':
        return f"Auditor {'APPROVED' if payload.get('approved') else 'REJECTED'} ticket {payload.get('ticket_id')}"
    if msg_type == 'complete_ticket': return f"Worker successfully executed {payload.get('ticket_id')}"
    if msg_type == 'register_agent': return f"Agent {payload.get('label', '')} booted into Swarm."
    if msg_type == 'status_update': return f"Switched to {payload.get('status', 'idle').upper()} state."
    if msg_type == 'agent_action': return payload.get('action', 'Agent performing action.')
    if msg_type == 'ui_agent_status': return None
    return f"Processed {msg_type}"

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


# ─── Projects ────────────────────────────────────────────────────────────────
@csrf_exempt
def projects_list(request):
    """GET /api/projects/ – list all projects
       POST /api/projects/ – create new project"""
    if request.method == 'GET':
        projects = Project.objects.order_by('-created_at')
        return JsonResponse([p.to_dict() for p in projects], safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            project = Project(
                title=data.get('title', 'Untitled Project'),
                description=data.get('description', ''),
                goal=data.get('goal', ''),
                tags=data.get('tags', []),
            )
            project.save()
            print(f"DEBUG: Saved project {project.id}")
            
            init_text = f"I have created a new startup mission: '{project.goal}'. Please review this and ask me questions to clarify the requirements."
            human_msg = ConversationMessage(
                project_id=str(project.id),
                sender='human',
                sender_id='board',
                text=init_text,
                processed=False,
            )
            human_msg.save()

            payload = {
                'project_id': str(project.id),
                'conversation_message_id': str(human_msg.id),
                'text': init_text,
            }

            try:
                publisher.publish(
                    sender='board',
                    recipient='queue:agent:ceo',
                    message_type='new_project_mission',
                    payload=payload,
                    project_id=str(project.id)
                )
            except Exception as pe:
                print(f"DEBUG: Publisher failed but project saved: {pe}")

            return JsonResponse(project.to_dict(), status=201)
        except Exception as e:
            print(f"ERROR creating project: {e}")
            return JsonResponse({'error': str(e)}, status=500)

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
        for field in ['title', 'description', 'status', 'goal', 'tags', 'auto_pilot']:
            if field in data:
                setattr(project, field, data[field])
        project.updated_at = datetime.utcnow()
        project.save()

        # If Auto Pilot was just turned ON, wake up the CEO to start planning
        if data.get('auto_pilot') is True:
            try:
                from .publisher import Publisher
                pub = Publisher()
                pub.publish(
                    sender='board',
                    recipient='queue:agent:ceo',
                    message_type='auto_pilot_enabled',
                    payload={'text': 'Auto pilot enabled. Start mission execution.'},
                    project_id=str(project.id)
                )
            except Exception as e:
                print(f"[API] Failed to wake up CEO: {e}")

        return JsonResponse(project.to_dict())

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ─── Messages ────────────────────────────────────────────────────────────────
@csrf_exempt
def messages_list(request, project_id):
    """GET /api/projects/<id>/messages/ – get conversation"""
    if request.method == 'GET':
        msgs = ConversationMessage.objects.filter(project_id=str(project_id)).order_by('timestamp')
        return JsonResponse([m.to_dict() for m in msgs], safe=False)
    elif request.method == 'POST':
        return send_message(request, project_id)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def send_message(request, project_id):
    """POST /api/projects/<id>/send_message/ – send human message → queue to CEO"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        text = data.get('text', '').strip()
        if not text:
            return JsonResponse({'error': 'text is required'}, status=400)

        # 1. Save human message
        human_msg = ConversationMessage(
            project_id=str(project_id),
            sender='human',
            sender_id=data.get('sender_id', 'user'),
            text=text,
            processed=False,
        )
        human_msg.save()

        # 2. Publish to RabbitMQ -> CEO
        payload = {
            'project_id': str(project_id),
            'conversation_message_id': str(human_msg.id),
            'text': text,
        }
        publisher.publish(
            sender='board',
            recipient='queue:agent:ceo',
            message_type='human_message',
            payload=payload,
            project_id=str(project_id)
        )

        # 3. Broadcast instant live log visually to right sidebar
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{project_id}',
            {
                'type': 'agent_log_event',
                'log': {
                    'id': str(human_msg.id),
                    'agent': 'board',
                    'agent_label': 'BOARD',
                    'message': format_log_message('human_message', payload),
                    'timestamp': human_msg.timestamp.isoformat(),
                    'type': 'info'
                }
            }
        )

        return JsonResponse({'message': 'Message queued successfully', 'data': human_msg.to_dict()}, status=201)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def approve_plan(request, project_id):
    """POST /api/projects/<id>/approve_plan/ – triggered by UI button to approve drafted tickets"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        approved_tickets = data.get('approved_tickets', [])
        message_id = data.get('message_id')
        
        # 1. Update the explicit tickets in DB instantly and send WebSocket + COO events
        updated_count = 0
        for tid in approved_tickets:
            try:
                ticket = Ticket.objects.get(id=tid)
                # Only update if draft exactly
                if ticket.status == 'draft':
                    ticket.status = 'open'
                    ticket.save()
                    updated_count += 1
                
                # We need async_to_sync and channel_layer
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'project_{project_id}',
                    {
                        'type': 'kanban_update_event',
                        'ticket': ticket.to_dict()
                    }
                )
                
                # Signal the COO directly to begin work
                publisher.publish(
                    sender='board',
                    recipient='queue:agent:coo',
                    message_type='create_ticket',
                    payload={'ticket_id': tid},
                    project_id=str(project_id),
                    ticket_id=tid
                )
            except Exception as e:
                print(f"Error updating ticket {tid} in DB / WebSockets:", e)

        # 2. Mark the explicit ConversationMessage as approved so UI freezes on refresh
        if message_id:
            try:
                msg = ConversationMessage.objects.get(id=message_id)
                if msg.structured_data:
                    msg.structured_data['is_approved'] = True
                    msg.save()
            except Exception as e:
                print("Error stamping message approval state:", e)

        # 3. Save a human message indicating approval, just for context history
        human_msg = ConversationMessage(
            project_id=str(project_id),
            sender='human',
            text='I approve this plan. Please proceed.',
            processed=False,
        )
        human_msg.save()

        # Let the CEO know it was approved for context, but do NOT wait for it to process the tickets
        payload = {
            'project_id': str(project_id),
            'approved_tickets': approved_tickets,
            'conversation_message_id': str(human_msg.id)
        }
        publisher.publish(
            sender='board',
            recipient='queue:agent:ceo',
            message_type='ticket_approved',
            payload=payload,
            project_id=str(project_id)
        )

        return JsonResponse({'message': 'Plan approved effectively', 'updated': updated_count})

        return JsonResponse({'message': 'Plan approved and queued.'}, status=200)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ─── Tickets / Kanban ─────────────────────────────────────────────────────────
def tickets_list(request, project_id):
    """GET /api/projects/<id>/tickets/"""
    tickets = Ticket.objects.filter(project_id=project_id).order_by('-created_at')
    return JsonResponse([t.to_dict() for t in tickets], safe=False)


@csrf_exempt
def ticket_detail(request, project_id, ticket_id):
    """GET/PATCH/DELETE /api/projects/<id>/tickets/<tid>/"""
    try:
        ticket = Ticket.objects.get(id=ticket_id, project_id=project_id)
    except Exception:
        return JsonResponse({'error': 'Not found'}, status=404)

    if request.method == 'GET':
        return JsonResponse(ticket.to_dict())

    elif request.method == 'PATCH' or request.method == 'PUT':
        data = json.loads(request.body)
        for field in ['title', 'status', 'priority', 'assigned_to', 'description', 'tags']:
            if field in data:
                setattr(ticket, field, data[field])
        ticket.updated_at = datetime.utcnow()
        ticket.version += 1
        ticket.save()
        
        # Broadcast update
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{project_id}',
            {
                'type': 'kanban_update_event',
                'ticket': ticket.to_dict()
            }
        )
        return JsonResponse(ticket.to_dict())

    elif request.method == 'DELETE':
        # 1. Prune from ConversationMessage drafts if it exists
        try:
            msgs = ConversationMessage.objects(project_id=project_id, structured_data__drafted_ticket_ids=ticket_id)
            for m in msgs:
                if m.structured_data and 'drafted_ticket_ids' in m.structured_data:
                    m.structured_data['drafted_ticket_ids'] = [tid for tid in m.structured_data['drafted_ticket_ids'] if tid != ticket_id]
                    m.save()
        except Exception as e:
            print(f"Error pruning ticket {ticket_id} from messages: {e}")

        # 2. Delete the ticket
        ticket_data = ticket.to_dict()
        ticket_data['status'] = 'deleted' # Signal deletion to frontend
        ticket.delete()

        # 3. Broadcast deletion
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'project_{project_id}',
            {
                'type': 'kanban_update_event',
                'ticket': ticket_data
            }
        )
        return JsonResponse({'message': 'Deleted successfully'})

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
        sender_raw = m.sender or 'system'
        agent_id = sender_raw.replace('agent:', '')
        label = agent_id.upper()
        if agent_id in ['django', 'board', 'user', 'human']:
            label = 'BOARD'
        
        result.append({
            'id': str(m.id),
            'agent': agent_id,
            'agent_label': label,
            'message': format_log_message(m.message_type, m.payload),
            'timestamp': m.timestamp.isoformat() if m.timestamp else None,
            'type': 'info',
        })
    return JsonResponse(list(reversed(result)), safe=False)
