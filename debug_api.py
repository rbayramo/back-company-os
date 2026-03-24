import requests
import json

url = "http://127.0.0.1:8000/api/projects/"
payload = {
    "title": "Debug Project",
    "goal": "Test if project creation works"
}

try:
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
