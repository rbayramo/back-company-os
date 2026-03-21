import os
from dotenv import load_dotenv
from agents.base_agent import BaseAgent

# Load config
load_dotenv()

def test_gpt52():
    print("--- [TEST] Starting gpt-5.2 Verification ---")
    agent = BaseAgent('test', 'TestAgent', 'TestDept')
    
    system_prompt = "You are a helpful assistant."
    user_prompt = "Say 'Hello from GPT-5.2' if you are working."
    
    # This will use the gpt-5.2 model I just set in BaseAgent.py
    try:
        response = agent.call_llm(system_prompt, user_prompt)
        print(f"\n[RESULT] Final Response Content: {response}")
    except Exception as e:
        print(f"\n[RESULT] Failed with outer exception: {e}")

if __name__ == "__main__":
    test_gpt52()
