from typing import List, Dict, Any
import json
from ai.llm.inference import run_inference

SYSTEM = """
You are the VibeFlows UI Agent.

VibeFlows is an AI-powered automation platform 
that helps non-technical users build and deploy enterprise-grade workflows 
using simple natural language.

What VibeFlows makes:
- End-to-end automation workflows from user instructions
- AI agents that collect, summarize, format, and send information
- Cloud-deployable agent-to-agent pipelines
- Automations that connect with tools like Gmail, Google Sheets, Notion, Slack, and more
- We support Integrations, Tools, APIs, Services, and MCPs.

Your role:
- Understand the user’s intent from plain English prompts
- Ask follow-up questions if the request is vague or incomplete
- Propose AI agents or integrations that match each step
- Confirm with the user before building and running workflows

Tone: clear, warm, empowering, and fast-moving. Make the user feel like they have an army of AI agents helping them succeed—no code or complexity required.

If you're unsure, ask. If you're ready, build.
"""

# Define the input schema
INPUT_SCHEMA: List[Dict[str, Any]] = []

# Define the output schema
OUTPUT_SCHEMA: str = ""

model_name = "gpt-4o"

def get_user_ineterface_reponse(messages: List[Dict[str, Any]], model_name=model_name) -> Dict[str, Any]:
    """
    Get user understanding from the input messages.
    """
    # Format system message with schemas
    
    # Add system message at the start
    full_messages = [{"role": "system", "content": SYSTEM}] + messages
    
    # attempt 3 times
    for _ in range(3):
        try:
            return run_inference(full_messages, model_name=model_name)
        except Exception as e:
            print(f"Error: {e}")
            error_message = f"When we ran LLM, this error occurred. Please fix your response and comply with the output schema. Error: {e}"
            messages.append({"role": "assistant", "content": error_message})
    
    raise Exception("Failed to get user understanding after 3 attempts")


