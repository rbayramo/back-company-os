import os
from dotenv import load_dotenv
from agents.base_agent import BaseAgent

# Load .env
load_dotenv()

def verify_live():
    print("--- Verifying OpenAI Key Live via BaseAgent ---")
    key = os.environ.get('OPENAI_API_KEY')
    print(f"Key found: {key[:10]}...{key[-5:] if key else 'None'}")
    
    agent = BaseAgent('ceo', 'CEO', 'Management')
    
    print("Calling OpenAI...")
    try:
        response = agent.call_llm("You are a test agent.", "Say 'Verification Success'.")
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error during call: {e}")

if __name__ == "__main__":
    verify_live()
