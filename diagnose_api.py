import os
import django
from django.conf import settings
from django.test import RequestFactory
from api.views import company_detail, messages_list

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def diagnose():
    factory = RequestFactory()
    
    print("--- Diagnosing /api/company/ ---")
    request = factory.get('/api/company/')
    try:
        response = company_detail(request)
        print(f"Status: {response.status_code}")
        print(f"Content: {response.content}")
    except Exception as e:
        import traceback
        print(f"FAILED with exception: {e}")
        traceback.print_exc()

    print("\n--- Diagnosing /api/projects/proj_001/messages/ ---")
    request = factory.get('/api/projects/proj_001/messages/')
    try:
        response = messages_list(request, project_id='proj_001')
        print(f"Status: {response.status_code}")
        print(f"Content: {response.content}")
    except Exception as e:
        import traceback
        print(f"FAILED with exception: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    diagnose()
