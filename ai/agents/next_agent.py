from typing import List, Dict, Any
import json
from ai.llm.inference import run_inference

# Define the input schema
INPUT_SCHEMA: List[Dict[str, Any]] = []

# Define the output schema
OUTPUT_SCHEMA: Dict[str, Any] = {
    "next_agent": str,
    "state_understanding": str,
    "is_ready_for_design": bool,
    "is_ready_for_development": bool,
    "is_ready_for_test": bool,
    "is_ready_for_execution": bool
}

SYSTEM = """
You are the Next Agent Selector for VibeFlows.
Your role is to:
1. Understand the current state of the workflow
2. Select the next appropriate agent to handle the user's request
3. Determine the readiness state for each phase

We Always want to understand the User and create perosnalized miminimal informative concice response to them.
When ready we create workflows.

User Experience Agents in order:
- user_understanding: For deep analysis of user & user's requirements
- user_interface: For user interaction and user personalized persona.
- workflow_designer: For creating workflow structure
- integration_wizard: For intergration of users' tools & platform integrations
- workflow_validator: For validating workflow requirements
- workflow_developer: For development & testing & deployment of workflows.
- agent_developer: For developing & testing & deployment of agents.
- agent_tester: For testing & debugging & optimization
- workflow_tester: For testing of workflows, debuging & and optimizing.
- workflow_executor: For workflow executions in production.

The input will be a list of json messages from user and other AI agents.
The latter messages are more important, as they are more likely to provide details about the current state.

IMPORTANT: Your response MUST be a valid JSON object with the following structure:
{
    "next_agent": "string",
    "state_understanding": "string",
    "is_ready_for_design": boolean,
    "is_ready_for_development": boolean,
    "is_ready_for_test": boolean,
    "is_ready_for_execution": boolean
}

Do not include any markdown. Do not include any other text. Do not include ```json```. 
The output must be a single valid JSON object that can be parsed by json.loads().
All property names must be enclosed in double quotes.
All boolean values must be true or false (not True or False).
All string values must be enclosed in double quotes.
"""

model_name = "gpt-4o"

def format_response(response: str) -> Dict[str, Any]:
    """Format the response to ensure valid JSON."""
    try:
        # First try to parse as is
        return json.loads(response)
    except json.JSONDecodeError:
        # If that fails, try to clean the response
        # Remove any markdown code blocks
        cleaned = response.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # If still fails, try to extract JSON-like content
            import re
            json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            # If all parsing attempts fail, return a default response
            return {
                "next_agent": "user_interface",
                "state_understanding": "Error parsing response, defaulting to user interface",
                "is_ready_for_design": False,
                "is_ready_for_development": False,
                "is_ready_for_test": False,
                "is_ready_for_execution": False
            }

def get_next_agent(messages: List[Dict[str, Any]], model_name=model_name) -> Dict[str, Any]:
    """
    Get next agent selection based on current state and messages.
    """
    # Add system message at the start
    full_messages = [{"role": "system", "content": SYSTEM}] + messages
    
    # attempt 3 times
    for _ in range(3):
        try:
            response = run_inference(full_messages, model_name=model_name)
            return format_response(response)
        except Exception as e:
            print(f"Error: {e}")
            error_message = f"When we ran LLM, this error occurred. Please fix your response and comply with the output schema. Error: {e}"
            messages.append({"role": "assistant", "content": error_message})
    
    raise Exception("Failed to get next agent after 3 attempts") 