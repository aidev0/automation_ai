from typing import List, Dict, Any
import json
from ai.llm.inference import run_inference

# Define the input schema
INPUT_SCHEMA = {
    "user_understanding": Dict[str, Any]
}

# Define the output schema
OUTPUT_SCHEMA = {
    "next_agent": str,
    "reason": str,
    "is_workflow_design_approved": bool,
    "is_workflow_build_approved": bool,
    "do_we_have_enough_information_to_develop_workflow": bool,
    "do_we_have_enough_information_to_design_workflow": bool,
    "do_we_have_enough_information_to_run_workflow": bool
}

# Define the system message
SYSTEM = """
You are the next agent selector. Your name is VibeFlows Next Agent Selector.
Your task is to determine which agent should handle the next step in the workflow development process.

Available agents:
1. workflow_designer - For designing the workflow steps
2. workflow_developer - For developing the workflow implementation
3. user_interface - For getting the user's approval

The workflow development process follows this sequence:
1. User Understanding -> Workflow Design -> User Interface for approval.
2. Workflow Design -> Workflow Development -> User Interface for approval
3. Workflow Development approved -> User Interface for integrations.

IMPORTANT TRANSITION RULES:
- If workflow_designer has completed its work (you can see workflow steps in the messages), AND
- The workflow design is approved (is_workflow_design_approved is true), AND
- We have enough information to develop (do_we_have_enough_information_to_develop_workflow is true)
THEN you MUST select workflow_developer as the next agent.

You will receive messages that may contain:
- User understanding and requirements
- Workflow design steps and status
- Various state flags about workflow readiness

You must return a JSON object with:
- next_agent: If we have enough information and this is the last step in the workflow, the name of the next agent to handle the request (must be either workflow_designer or workflow_developer).
- After the workflow_designer is done, the next_agent should be user_interface because we need to get the user's approval.
- After the user_interface is done and user has approved the workflow design, the next_agent should be workflow_developer.
- After the workflow_developer is done, the next_agent should be user_interface because we need to get the user's approval.
- next_agent: If we don't have enough information to do the task, next_agent should be user_interface because we need to get more information from the user.
- reason: A brief explanation of why this agent was chosen
- is_workflow_design_approved: Whether the workflow design is approved
- is_workflow_build_approved: Whether the workflow build is approved
- do_we_have_enough_information_to_develop_workflow: Whether we have enough information to develop the workflow
- do_we_have_enough_information_to_design_workflow: Whether we have enough information to design the workflow
- do_we_have_enough_information_to_run_workflow: Whether we have enough information to run the workflow

Example output when workflow design is complete:
{
    "next_agent": "workflow_developer",
    "reason": "Workflow design is complete and approved, ready for development",
    "is_workflow_design_approved": true,
    "is_workflow_build_approved": false,
    "do_we_have_enough_information_to_develop_workflow": true,
    "do_we_have_enough_information_to_design_workflow": true,
    "do_we_have_enough_information_to_run_workflow": false
}

Do not include any markdown. Do not include any other text. Do not include ```json```.
The output should be readable by json.loads().
"""

model_name = "gpt-4"

def get_next_agent(messages, model_name=model_name) -> str:
    """
    Determine the next agent to handle the request based on current state.
    Returns a JSON string with the next agent and state information.
    """
    # Prepare the input message
    messages = [{"role": "system", "content": SYSTEM}] + messages
    
    # attempt 3 times
    for attempt in range(3):
        try:
            response = run_inference(messages, model_name=model_name)
            
            # Create a default response
            result = {
                "next_agent": "user_understanding",
                "reason": "Default fallback to user understanding",
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
                if isinstance(parsed, dict):
                    # Update result with parsed values
                    for key in result:
                        if key in parsed:
                            result[key] = parsed[key]
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
                        
                        if key in result:
                            if isinstance(result[key], bool):
                                # Handle booleans
                                result[key] = value.lower() in ['true', 'yes', '1']
                            else:
                                # Handle strings
                                result[key] = value
            
            # Validate next_agent
            valid_agents = ["user_understanding", "user_interface", "workflow_designer", "workflow_developer", "workflow_runner"]
            if result["next_agent"] not in valid_agents:
                result["next_agent"] = "user_understanding"
                result["reason"] = f"Invalid agent specified, defaulting to user_understanding. Valid agents are: {', '.join(valid_agents)}"
            
            # Convert to JSON string
            return json.dumps(result, ensure_ascii=False)
                    
        except Exception as e:
            print(f"Attempt {attempt + 1}: Error: {e}")
            error_message = {
                "role": "assistant",
                "content": f"An error occurred. Please provide your response in a clear format with the next agent and state information. Error: {e}"
            }
            messages.append(error_message)
            continue
    
    # If all attempts fail, return default response
    default_response = {
        "next_agent": "user_understanding",
        "reason": "Error occurred, defaulting to user understanding",
        "is_workflow_design_approved": False,
        "is_workflow_build_approved": False,
        "do_we_have_enough_information_to_develop_workflow": False,
        "do_we_have_enough_information_to_design_workflow": False,
        "do_we_have_enough_information_to_run_workflow": False
    }
    return json.dumps(default_response, ensure_ascii=False) 