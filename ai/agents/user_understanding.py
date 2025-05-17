from typing import List, Dict, Any
import json
from ai.llm.inference import run_inference

# Define the input schema
INPUT_SCHEMA: List[Dict[str, Any]] = []

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
You are the user understanding agent. Your name is VibeFlows User Understanding Agent. 
Your task is to receives messages of VibeFLow users and other AI agents in the chat, we may provide tools and ressouces available. 
Your mission is to find out user's intent, our understaning from user until we know enough details to develop a workflow automation. 

VibeFlows is a platform that allows Non-Technicals to automate their work with AI.
User can describe their workflow in plain English. Our AI translates their needs into production-ready automation.
Get your automation up and running in minutes, not days. Our AI handles the heavy lifting.

A workflow is a list of agents each specialized in taking specific actions on specific tech, these are macro units, e.g. Gmail integration, Slack integration, Vapi MCP, LLM API, etc. 
We obviously don't want to overwhelm users with asking too many  technical questions specially if they are non technical. The goals is to provide Workflow Automation  Services through multi-agent AI for NonTechnicals.

The input will be a list of json messages from user and other AI agents.

The latter messages are more important, as they are more likely to provide details about user's intent and workflow.
You have to find out the context from the earlier messages and use it to understand the user's intent.
But your default is to use the latter messages to understand the user's intent.

We want json with this schema. Avoid any other text. Also no markdown. avoid ```json ``` 
or anything inside ``` ````.

The Output Schema shall be exactly:

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

user_understanding: their technical level, industry, experience,
problem_understanding: what do they want to accomplish? the target audience?, etc
workflow_tech_understanding: do they have tech preference or we should decide on their behalf
user_tech_list: ["str"] tech provided by users for this workflow and problem-> [integrations, MCPs, APIs, Services, etc]
required_tech_list: ["str"] [tech needed for this problem. Integrations. Tools, APIs, Services, etc]
user_last_message_intent: str:  are they providing information and details? did they want specific workflow, have technical question, do they need support, etc
clarification_questions: ["str"] questions to ask user to clarify their needs
is_user_clarification_needed: boolean
is_workflow_design_approved: boolean
is_workflow_build_approved: boolean
do_we_have_enough_information_to_develop_workflow: boolean
do_we_have_enough_information_to_design_workflow: boolean
do_we_have_enough_information_to_run_workflow: boolean

Do not incude any markdown. Do not include any other text. Do not include ```json```. 
The output should be readable by json.loads().
"""

model_name = "gpt-4o"

def get_user_understanding(messages: List[Dict[str, Any]], model_name=model_name) -> str:
    """
    Get user understanding from the input messages.
    Returns a JSON string that can be parsed with json.loads()
    """
    # Add system message at the start
    full_messages = [{"role": "system", "content": SYSTEM}] + messages
    
    # attempt 3 times
    for attempt in range(3):
        try:
            response = run_inference(full_messages, model_name=model_name)
            
            # Create a dictionary with the required structure
            result = {
                "user_understanding": "",
                "problem_understanding": "",
                "workflow_tech_understanding": "",
                "user_tech_list": [],
                "required_tech_list": [],
                "user_last_message_intent": "",
                "clarification_questions": [],
                "is_user_clarification_needed": False,
                "is_workflow_design_approved": False,
                "is_workflow_build_approved": False,
                "do_we_have_enough_information_to_develop_workflow": False,
                "do_we_have_enough_information_to_design_workflow": False,
                "do_we_have_enough_information_to_run_workflow": False
            }
            
            # Try to extract information from the response
            try:
                # First try to parse as JSON
                parsed = json.loads(response)
                result.update(parsed)
            except json.JSONDecodeError:
                # If not JSON, try to extract information from text
                lines = response.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Try to match key-value pairs
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip().lower().replace(' ', '_')
                        value = value.strip()
                        
                        # Map the key to our schema
                        if key in result:
                            if isinstance(result[key], list):
                                # Handle lists
                                if value.startswith('[') and value.endswith(']'):
                                    try:
                                        result[key] = json.loads(value)
                                    except:
                                        result[key] = [v.strip() for v in value[1:-1].split(',')]
                                else:
                                    result[key] = [value]
                            elif isinstance(result[key], bool):
                                # Handle booleans
                                result[key] = value.lower() in ['true', 'yes', '1']
                            else:
                                # Handle strings
                                result[key] = value
            
            # Convert to JSON string
            return json.dumps(result, ensure_ascii=False)
                    
        except Exception as e:
            print(f"Attempt {attempt + 1}: Error: {e}")
            error_message = {
                "role": "assistant",
                "content": f"An error occurred. Please provide your response in a clear format with key-value pairs. Error: {e}"
            }
            messages.append(error_message)
            continue
    
    # If all attempts fail, return default response
    default_response = {
        "user_understanding": "Error: Could not parse user understanding",
        "problem_understanding": "Error: Could not parse problem understanding",
        "workflow_tech_understanding": "Error: Could not parse workflow tech understanding",
        "user_tech_list": [],
        "required_tech_list": [],
        "user_last_message_intent": "Error: Could not parse intent",
        "clarification_questions": ["Could you please rephrase your request?"],
        "is_user_clarification_needed": True,
        "is_workflow_design_approved": False,
        "is_workflow_build_approved": False,
        "do_we_have_enough_information_to_develop_workflow": False,
        "do_we_have_enough_information_to_design_workflow": False,
        "do_we_have_enough_information_to_run_workflow": False
    }
    return json.dumps(default_response, ensure_ascii=False)

