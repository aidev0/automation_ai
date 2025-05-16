from typing import List, Dict, Any
import json
from ai.llm.inference import run_inference

# Define the input schema
INPUT_SCHEMA: List[Dict[str, Any]] = [
    {
        "role": "system",
        "content": "You are a user understanding agent. Your task is to analyze user messages and understand their workflow automation needs."
    },
    {
        "role": "user",
        "content": "I want to automate my email workflow"
    }
]

# Define the output schema
OUTPUT_SCHEMA: Dict[str, Any] = {
    "user_understanding": str,
    "problem_understanding": str,
    "workflow_tech_understanding": str,
    "user_tech_list": List[str],
    "required_tech_list": List[str],
    "user_last_message_intent": str,
    "clarification_questions": List[str],
    "is_user_clarification_needed": bool,
    "is_workflow_design_approved": bool,
    "is_workflow_build_approved": bool,
    "do_we_have_enough_information_to_develop_workflow": bool,
    "do_we_have_enough_information_to_design_workflow": bool,
    "do_we_have_enough_information_to_run_workflow": bool
}

# Define the system message
SYSTEM = """
You are VibeFlows User Understanding Agent. Your task is to analyze user messages and understand their workflow automation needs.

About VibeFlows:
- Platform for non-technical users to automate work using AI
- Users describe workflows in plain English
- AI translates needs into production-ready automation
- Workflows are composed of specialized agents (e.g., Gmail, Slack, LLM APIs)

Your Analysis Should Include:
1. User Profile:
   - Technical level
   - Industry/experience
   - Workflow preferences

2. Workflow Requirements:
   - User's goal
   - Target audience
   - Technical constraints
   - Required integrations

3. Current State:
   - User's provided tech stack
   - Missing information
   - Approval status for design/build

Input: List of messages from user and AI agents
Output: JSON with the following fields:
- user_understanding: string
- problem_understanding: string
- workflow_tech_understanding: string
- user_tech_list: array of strings
- required_tech_list: array of strings
- user_last_message_intent: string
- clarification_questions: array of strings
- is_user_clarification_needed: boolean
- is_workflow_design_approved: boolean
- is_workflow_build_approved: boolean
- do_we_have_enough_information_to_develop_workflow: boolean
- do_we_have_enough_information_to_design_workflow: boolean
- do_we_have_enough_information_to_run_workflow: boolean

Focus on recent messages for intent, but use earlier context for full understanding.
"""

model_name = "gpt-4o"  # Specify the model name

def get_user_understanding(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get user understanding from the input messages.
    """
    # Add system message at the start
    full_messages = [{"role": "system", "content": SYSTEM}] + messages
    
    # attempt 3 times
    for _ in range(3):
        try:
            return run_inference(full_messages, model_name="gpt-4o")
        except Exception as e:
            print(f"Error: {e}")
            error_message = f"When we ran LLM, this error occurred. Please fix your response and comply with the output schema. Error: {e}"
            messages.append({"role": "assistant", "content": error_message})
    
    raise Exception("Failed to get user understanding after 3 attempts") 