from typing import Dict, Any, List
import json
import os
from datetime import datetime
from ai.llm.inference import run_inference

# Define the input schema
INPUT_SCHEMA = {
    "step": Dict[str, Any]
}

# Define the output schema
OUTPUT_SCHEMA = {
    "agent_code": str,
    "status": str,
    "error": str,
    "steps": List[str],
    "errors": List[str]
}

# System message for agent code generation
SYSTEM_MESSAGE = """
You are the agent code generator. Your task is to create Python code for a workflow agent.

The code should:
1. Follow Python best practices
2. Include proper type hints
3. Have clear docstrings
4. Handle errors gracefully
5. Use environment variables for credentials
6. Include necessary imports
7. Have a clear process_step function

Example structure:
from typing import Dict, Any, Optional
import json
import os
import requests
from datetime import datetime

# Input and output schemas
INPUT_SCHEMA = {
    "data": Dict[str, Any],  # Input data for the step
    "config": Dict[str, Any]  # Configuration data
}

OUTPUT_SCHEMA = {
    "status": str,  # "success" or "error"
    "message": str,  # Description of the result
    "data": Optional[Dict[str, Any]]  # Processed data or None if error
}

# System message
SYSTEM_MESSAGE = "You are the {step_label} agent. Your task is to {step_description}"

# Required environment variables
REQUIRED_ENV = ["API_KEY", "API_SECRET"]

def process_step(input_data: Dict[str, Any]) -> Dict[str, Any]:
    Process the workflow step.

    Args:
        input_data: Input data matching INPUT_SCHEMA

    Returns:
        Output data matching OUTPUT_SCHEMA

    Use LLMs like OpenAI, Gemini, Claude, model_name="openai-gpt4o" is the default.
    Always process the Ststem message and data in llm and return the result as required output_schema 
"""

def generate_agent_code(step: Dict[str, Any], model_name: str = "gpt-4o") -> Dict[str, Any]:
    steps = []
    errors = []

    try:
        # Step 1: Validate input
        steps.append("Validating input...")
        if not isinstance(step, dict):
            error_msg = "step must be a dictionary"
            errors.append(error_msg)
            raise ValueError(error_msg)

        if "label" not in step or "description" not in step:
            error_msg = "step must contain 'label' and 'description'"
            errors.append(error_msg)
            raise ValueError(error_msg)

        steps.append("✓ Input validated")

        # Step 2: Prepare messages for code generation
        steps.append("Preparing code generation...")
        messages = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": json.dumps({
                "step": step
            }, ensure_ascii=False)}
        ]
        steps.append("✓ Messages prepared")

        # Step 3: Generate code
        steps.append("Generating code...")
        response = run_inference(messages, model_name=model_name)

        if "```python" in response:
            code = response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            code = response.split("```")[1].split("```")[0].strip()
        else:
            code = response.strip()

        if not code or len(code) < 50:
            raise ValueError("Generated code is invalid or too short")

        steps.append("✓ Code generated")

        return {
            "agent_code": code,
            "status": "success",
            "error": "",
            "steps": steps,
            "errors": errors
        }

    except Exception as e:
        error_msg = f"Failed to generate agent code: {str(e)}"
        errors.append(error_msg)
        steps.append(f"✗ {error_msg}")

        return {
            "agent_code": "",
            "status": "error",
            "error": error_msg,
            "steps": steps,
            "errors": errors
        }

def create_agent(step: Dict[str, Any], output_path: str, model_name: str = "gpt-4o") -> Dict[str, Any]:
    steps = []
    errors = []

    try:
        steps.append(f"Creating agent at: {os.path.abspath(output_path)}")
        result = generate_agent_code(step, model_name)

        if result["status"] == "error":
            errors.extend(result["errors"])
            steps.extend(result["steps"])
            raise Exception(result["error"])

        steps.extend(result["steps"])

        steps.append("Creating output directory...")
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        steps.append("✓ Output directory created")

        steps.append("Writing agent file...")
        with open(output_path, 'w') as f:
            f.write(result["agent_code"])
        steps.append("✓ Agent file written")

        return {
            "path": output_path,
            "status": "success",
            "error": "",
            "steps": steps,
            "errors": errors
        }

    except Exception as e:
        error_msg = f"Failed to create agent: {str(e)}"
        errors.append(error_msg)
        steps.append(f"✗ {error_msg}")

        error_code = f'''from typing import Dict, Any, Optional
import json
import os
from datetime import datetime

INPUT_SCHEMA = {{"error": str}}
OUTPUT_SCHEMA = {{"error": str}}

SYSTEM_MESSAGE = "Error creating agent: {str(e)}"
REQUIRED_ENV = []

def process_step(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {{
        "status": "error",
        "message": "Failed to create agent: {str(e)}",
        "data": None
    }}
'''
        with open(output_path, 'w') as f:
            f.write(error_code)

        return {
            "path": output_path,
            "status": "error",
            "error": error_msg,
            "steps": steps,
            "errors": errors
        }
