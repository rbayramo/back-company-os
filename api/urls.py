from django.urls import path
from . import views

urlpatterns = [
    # Company
    path('company/', views.company_detail, name='company_detail'),

    # Projects
    path('projects/', views.projects_list, name='projects_list'),
    path('projects/<str:project_id>/', views.project_detail, name='project_detail'),

    # Messages (conversation with CEO)
    path('projects/<str:project_id>/messages/', views.messages_list, name='messages_list'),

    # Kanban tickets
    path('projects/<str:project_id>/tickets/', views.tickets_list, name='tickets_list'),
    path('projects/<str:project_id>/tickets/<str:ticket_id>/', views.ticket_detail, name='ticket_detail'),

    # Agents
    path('agents/', views.agents_list, name='agents_list'),

    # Activity Logs
    path('projects/<str:project_id>/logs/', views.logs_list, name='logs_list'),
]
