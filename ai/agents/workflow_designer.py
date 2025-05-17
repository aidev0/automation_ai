from typing import List, Dict, Any
import json
from ai.llm.inference import run_inference

# Define the input schema
INPUT_SCHEMA: List[Dict[str, Any]] = []

# Define the output schema for a single workflow step
WORKFLOW_STEP_SCHEMA = {
    "label": str,
    "description": str,
    "integrations": List[str]
}

# Define the system message
SYSTEM = """
You are the workflow designer agent. Your name is VibeFlows Workflow Designer Agent.
Your task is to design workflow steps based on user requirements and available integrations.

Each workflow step should be a JSON object with:
- label: A short, clear label for the step (e.g., "Read Leads Data")
- description: A brief description of what the step does (e.g., "Reads leads data from Google Sheets")
- integrations: A list of required integrations (e.g., ["google-sheets"])

The output should be a JSON array of workflow steps. Each step should be a complete, self-contained unit that can be executed independently.

Example output format:
[
    {
        "label": "Read Leads Data",
        "description": "Reads leads data from Google Sheets",
        "integrations": ["google-sheets"]
    },
    {
        "label": "Process Leads",
        "description": "Processes and validates lead information",
        "integrations": ["openai"]
    }
]

Available integrations - everything that we can connect to including tools, APIs, services, and MCPs:
- google-sheets
- gmail
- slack
- discord
- notion
- airtable
- zapier
- webhook
- http
- smtp
- openai
- anthropic
- vapi
- mcp

Do not include any markdown. Do not include any other text. Do not include ```json```.
The output should be readable by json.loads().
"""

model_name = "gpt-4o"

def design_workflow(messages: List[Dict[str, Any]], model_name=model_name) -> str:
    """
    Design a workflow based on user requirements.
    Returns a JSON string containing an array of workflow steps.
    """
    # Add system message at the start
    full_messages = [{"role": "system", "content": SYSTEM}] + messages
    
    # attempt 3 times
    for attempt in range(3):
        try:
            response = run_inference(full_messages, model_name=model_name)
            
            # Create a default empty workflow
            result = []
            
            # Try to extract information from the response
            try:
                # First try to parse as JSON
                parsed = json.loads(response)
                if isinstance(parsed, list):
                    # Validate each step in the workflow
                    for step in parsed:
                        if all(key in step for key in ["label", "description", "integrations"]):
                            result.append({
                                "label": str(step["label"]),
                                "description": str(step["description"]),
                                "integrations": [str(i) for i in step["integrations"]]
                            })
            except json.JSONDecodeError:
                # If not JSON, try to extract information from text
                lines = response.split('\n')
                current_step = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Look for step indicators
                    if line.lower().startswith(("step", "task", "action")):
                        if current_step:
                            result.append(current_step)
                        current_step = {
                            "label": "",
                            "description": "",
                            "integrations": []
                        }
                        # Extract label from the step line
                        label = line.split(":", 1)[1].strip() if ":" in line else line
                        current_step["label"] = label
                    elif current_step:
                        # Try to match key-value pairs
                        if ':' in line:
                            key, value = line.split(':', 1)
                            key = key.strip().lower()
                            value = value.strip()
                            
                            if key in ["description", "desc"]:
                                current_step["description"] = value
                            elif key in ["integration", "integrations"]:
                                # Handle integrations list
                                if value.startswith('[') and value.endswith(']'):
                                    try:
                                        current_step["integrations"] = json.loads(value)
                                    except:
                                        current_step["integrations"] = [v.strip() for v in value[1:-1].split(',')]
                                else:
                                    current_step["integrations"] = [value]
                
                # Add the last step if exists
                if current_step:
                    result.append(current_step)
            
            # Convert to JSON string
            return json.dumps(result, ensure_ascii=False)
                    
        except Exception as e:
            print(f"Attempt {attempt + 1}: Error: {e}")
            error_message = {
                "role": "assistant",
                "content": f"An error occurred. Please provide your response in a clear format with workflow steps. Error: {e}"
            }
            messages.append(error_message)
            continue
    
    # If all attempts fail, return empty workflow
    return json.dumps([], ensure_ascii=False) 