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
```python
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
    \"\"\"
    Process the workflow step.
    
    Args:
        input_data: Input data matching INPUT_SCHEMA
        
    Returns:
        Output data matching OUTPUT_SCHEMA
    \"\"\"
    try:
        # Validate environment variables
        missing_env = [var for var in REQUIRED_ENV if not os.getenv(var)]
        if missing_env:
            raise ValueError(f"Missing required environment variables: {{', '.join(missing_env)}}")
        
        # Extract input data
        data = input_data.get("data", {{}})
        config = input_data.get("config", {{}})
        
        # TODO: Implement the actual functionality
        
        return {{
            "status": "success",
            "message": "Step completed",
            "data": data
        }}
    except Exception as e:
        return {{
            "status": "error",
            "message": str(e),
            "data": None
        }}
```

Return only the Python code, no explanations.
"""

def generate_agent_code(step: Dict[str, Any], model_name: str = "gpt-4o") -> Dict[str, Any]:
    """
    Generate Python code for a workflow agent.
    Args:
        step: The workflow step to generate code for
        model_name: Name of the model to use for inference
    Returns:
        Dictionary containing the generated code and metadata
    """
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
        
        # Clean up the response to get just the Python code
        if "```python" in response:
            code = response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            code = response.split("```")[1].split("```")[0].strip()
        else:
            code = response.strip()
        
        # If no code was generated or it's too short, create a default implementation
        if not code or len(code) < 50:  # Arbitrary minimum length to ensure meaningful code
            # Get required environment variables based on integrations
            required_env = []
            if "google-sheets" in step.get("integrations", []):
                required_env.extend(["GOOGLE_SHEETS_CREDENTIALS", "GOOGLE_SHEETS_TOKEN"])
            if "gmail" in step.get("integrations", []):
                required_env.extend(["GMAIL_CREDENTIALS", "GMAIL_TOKEN"])
            if "twilio" in step.get("integrations", []):
                required_env.extend(["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"])
            
            # Get required packages based on integrations
            required_packages = []
            if "google-sheets" in step.get("integrations", []):
                required_packages.append("google-api-python-client")
            if "gmail" in step.get("integrations", []):
                required_packages.append("google-api-python-client")
            if "twilio" in step.get("integrations", []):
                required_packages.append("twilio")
            
            code = f'''from typing import Dict, Any, Optional
import json
import os
import requests
from datetime import datetime

# Required packages: {", ".join(required_packages)}

# Input and output schemas
INPUT_SCHEMA = {{
    "data": Dict[str, Any],  # Input data for the step
    "config": Dict[str, Any]  # Configuration data
}}

OUTPUT_SCHEMA = {{
    "status": str,  # "success" or "error"
    "message": str,  # Description of the result
    "data": Optional[Dict[str, Any]]  # Processed data or None if error
}}

# System message
SYSTEM_MESSAGE = """You are the {step['label']} agent. Your task is to {step['description']}"""

# Required environment variables
REQUIRED_ENV = {json.dumps(required_env, indent=4)}

def process_step(input_data: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"
    Process the workflow step: {step['label']}
    
    Args:
        input_data: Input data matching INPUT_SCHEMA
        
    Returns:
        Output data matching OUTPUT_SCHEMA
    \"\"\"
    try:
        # Validate environment variables
        missing_env = [var for var in REQUIRED_ENV if not os.getenv(var)]
        if missing_env:
            raise ValueError(f"Missing required environment variables: {{', '.join(missing_env)}}")
        
        # Extract input data
        data = input_data.get("data", {{}})
        config = input_data.get("config", {{}})
        
        # TODO: Implement the actual functionality
        # This is where you'll add the specific implementation for this step
        
        return {{
            "status": "success",
            "message": "Step {step['label']} completed",
            "data": data
        }}
    except Exception as e:
        return {{
            "status": "error",
            "message": str(e),
            "data": None
        }}

if __name__ == "__main__":
    # Example usage
    test_input = {{
        "data": {{"task": "test"}},
        "config": {{"option": "value"}}
    }}
    result = process_step(test_input)
    print(json.dumps(result, indent=2))
'''
        
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
    """
    Create a workflow agent.
    Args:
        step: The workflow step to create an agent for
        output_path: Path to write the agent file to
        model_name: Name of the model to use for inference
    Returns:
        Dictionary containing the result path and any errors
    """
    steps = []
    errors = []
    
    try:
        print(f"Creating agent at: {os.path.abspath(output_path)}")  # Debug print
        
        # Step 1: Generate agent code
        steps.append("Generating agent code...")
        result = generate_agent_code(step, model_name)
        
        if result["status"] == "error":
            errors.extend(result["errors"])
            steps.extend(result["steps"])
            raise Exception(result["error"])
        
        steps.extend(result["steps"])
        
        # Step 2: Ensure output directory exists
        steps.append("Creating output directory...")
        output_dir = os.path.dirname(output_path)
        print(f"Output directory: {os.path.abspath(output_dir)}")  # Debug print
        os.makedirs(output_dir, exist_ok=True)
        steps.append("✓ Output directory created")
        
        # Step 3: Write agent file
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
        
        # Create a minimal error agent file
        error_code = f'''from typing import Dict, Any, Optional
import json
import os
from datetime import datetime

# Input and output schemas
INPUT_SCHEMA = {{"error": str}}
OUTPUT_SCHEMA = {{"error": str}}

# System message
SYSTEM_MESSAGE = "Error creating agent: {str(e)}"

# Required environment variables
REQUIRED_ENV = []

def process_step(input_data: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"
    Error in agent creation.
    \"\"\"
    return {{
        "status": "error",
        "message": "Failed to create agent: {str(e)}",
        "data": None
    }}
'''
        
        # Write the error agent file
        print(f"Writing error agent file at: {os.path.abspath(output_path)}")  # Debug print
        with open(output_path, 'w') as f:
            f.write(error_code)
        
        return {
            "path": output_path,
            "status": "error",
            "error": error_msg,
            "steps": steps,
            "errors": errors
        } 