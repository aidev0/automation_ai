from typing import List, Dict, Any
import json
import os
import random
import traceback
from datetime import datetime
from ai.llm.inference import run_inference
from ai.agents.agent_maker import create_agent

# Define the input schema
INPUT_SCHEMA = {
    "workflow_design": List[Dict[str, Any]]
}

# Define the output schema
OUTPUT_SCHEMA = {
    "project_name": str,
    "project_dir": str,
    "structure": Dict[str, Any],
    "status": str,
    "error": str,
    "steps": List[str],
    "errors": List[str]
}

# System message for workflow development
SYSTEM_MESSAGE = """
You are the workflow developer. Your task is to create a well-organized workflow project structure.

The structure should follow these rules:
1. One directory per workflow
2. One file per agent
3. Clear separation of concerns
4. Proper configuration files
5. Documentation files

Example structure:
{
    "workflows": {
        "gmail_google-sheets_retrieve_240315_143022": {
            "retrieve_leads_data.py": null,
            "call_lead_via_twilio.py": null,
            "workflow_config.json": null,
            "README.md": null,
            "requirements.txt": null
        }
    }
}

Return only the JSON structure, no explanations.
"""

def generate_project_name(workflow_design: List[Dict[str, Any]]) -> str:
    """Generate a project name based on the workflow design."""
    # Get timestamp in format YYMMDD_HHMMSS
    timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
    
    # Get first step's label as the action
    action = workflow_design[0]["label"].lower().replace(" ", "_")
    
    # Get integrations from first step
    integrations = "_".join(sorted(workflow_design[0].get("integrations", [])))
    
    # Format: integrations_action_YYMMDD_HHMMSS
    return f"{integrations}_{action}_{timestamp}"

def create_workflow_structure(workflow_design: List[Dict[str, Any]], model_name: str = "gpt-4o") -> Dict[str, Any]:
    """
    Create the workflow project structure.
    Args:
        workflow_design: List of workflow steps
        model_name: Name of the model to use for inference
    Returns:
        Dictionary containing the project structure and metadata
    """
    steps = []
    errors = []
    
    try:
        # Step 1: Generate project name
        steps.append("Generating project name...")
        project_name = generate_project_name(workflow_design)
        project_dir = os.path.join("workflows", project_name)
        print(f"Project directory: {os.path.abspath(project_dir)}")  # Debug print
        steps.append(f"✓ Project name generated: {project_name}")
        
        # Step 2: Create project directory
        steps.append(f"Creating project directory: {project_dir}")
        os.makedirs(project_dir, exist_ok=True)
        steps.append("✓ Project directory created")
        
        # Step 3: Generate agent files
        steps.append("Generating agent files...")
        agent_files = []
        for step in workflow_design:
            agent_name = f"{step['label'].lower().replace(' ', '_')}.py"
            agent_files.append(agent_name)
            
            # Create agent file using agent_maker
            agent_path = os.path.join(project_dir, agent_name)
            print(f"Creating agent file at: {os.path.abspath(agent_path)}")  # Debug print
            agent_result = create_agent(step, agent_path, model_name)
            
            if agent_result.get("status") == "error":
                error_msg = f"Failed to create agent {agent_name}: {agent_result.get('error', 'Unknown error')}"
                errors.append(error_msg)
                steps.append(f"✗ {error_msg}")
            else:
                steps.append(f"✓ Created agent file: {agent_name}")
        
        if errors:
            raise Exception("Failed to create one or more agent files")
        
        steps.append(f"✓ Created {len(agent_files)} agent files")
        
        # Step 4: Create workflow configuration file
        steps.append("Creating workflow configuration...")
        config_path = os.path.join(project_dir, "workflow_config.json")
        print(f"Creating config file at: {os.path.abspath(config_path)}")  # Debug print
        
        # Collect all integrations and their requirements from workflow design
        integrations = {}
        for step in workflow_design:
            if "integrations" in step:
                for integration in step["integrations"]:
                    if integration not in integrations:
                        integrations[integration] = {
                            "steps": [],
                            "env_vars": step.get("env_vars", []),
                            "packages": step.get("packages", [])
                        }
                    integrations[integration]["steps"].append(step["label"])
        
        workflow_config = {
            "name": project_name,
            "description": "Automated workflow for processing leads and communications",
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "workflow_design": workflow_design,
            "agents": agent_files,
            "integrations": integrations,
            "requirements": {
                "python": ">=3.8",
                "packages": list(set([pkg for intg in integrations.values() for pkg in intg["packages"]]))
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(workflow_config, f, indent=2)
        steps.append("✓ Created workflow configuration")
        
        # Step 5: Create README
        steps.append("Creating README...")
        readme_path = os.path.join(project_dir, "README.md")
        print(f"Creating README at: {os.path.abspath(readme_path)}")  # Debug print
        
        # Generate integration setup instructions
        integration_setup = []
        for integration, details in integrations.items():
            setup = f"""### {integration.title()}
1. Install required packages:
   ```bash
   pip install {' '.join(details['packages'])}
   ```
2. Set up environment variables:
   ```bash
   {chr(10).join(f'export {var}=your_value' for var in details['env_vars'])}
   ```
3. Used in steps: {', '.join(details['steps'])}
"""
            integration_setup.append(setup)
        
        readme_content = f"""# {project_name}

## Description
Automated workflow for processing leads and communications. This workflow {', '.join(step['label'].lower() for step in workflow_design)}.

## Workflow Steps
{chr(10).join(f'1. {step["label"]}: {step["description"]}' for step in workflow_design)}

## Setup

### Prerequisites
- Python {workflow_config['requirements']['python']}
- pip (Python package manager)

### Installation
1. Clone this repository
2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

### Environment Variables
Create a `.env` file in the project root with the following variables:
```bash
{chr(10).join(f'# {intg.title()} variables{chr(10)}{chr(10).join(f"{var}=your_value" for var in details["env_vars"])}{chr(10)}' for intg, details in integrations.items())}
```

## Integration Setup
{chr(10).join(integration_setup)}

## Usage
1. Ensure all environment variables are set
2. Run individual steps:
   ```bash
   {chr(10).join(f'   python {agent}' for agent in agent_files)}
   ```

## Configuration
See `workflow_config.json` for detailed workflow configuration.

## Error Handling
Each step includes error handling and will return a JSON response with:
- `status`: "success" or "error"
- `message`: Description of the result or error
- `data`: The processed data or null if error

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
"""
        
        with open(readme_path, 'w') as f:
            f.write(readme_content)
        steps.append("✓ Created README")
        
        # Step 6: Create requirements.txt
        steps.append("Creating requirements.txt...")
        requirements_path = os.path.join(project_dir, "requirements.txt")
        print(f"Creating requirements at: {os.path.abspath(requirements_path)}")  # Debug print
        
        requirements_content = f"""# Core requirements
requests>=2.31.0
python-dotenv>=1.0.0

# Integration requirements
{chr(10).join(f'# {intg.title()} requirements{chr(10)}{chr(10).join(f"{pkg}>=0.0.0" for pkg in details["packages"])}{chr(10)}' for intg, details in integrations.items())}
"""
        with open(requirements_path, 'w') as f:
            f.write(requirements_content)
        steps.append("✓ Created requirements.txt")
        
        # Step 7: Prepare success response
        structure = {
            "workflows": {
                project_name: {
                    "agents": {f: None for f in agent_files},
                    "workflow_config.json": None,
                    "README.md": None,
                    "requirements.txt": None
                }
            }
        }
        
        result = {
            "project_name": project_name,
            "project_dir": project_dir,
            "structure": structure,
            "status": "success",
            "error": "",
            "steps": steps,
            "errors": errors
        }
        
        return result
        
    except Exception as e:
        # Return error response
        error_msg = f"Failed to create workflow structure: {str(e)}"
        errors.append(error_msg)
        steps.append(f"✗ {error_msg}")
        
        error_response = {
            "project_name": "",
            "project_dir": "",
            "structure": {},
            "status": "error",
            "error": error_msg,
            "steps": steps,
            "errors": errors
        }
        return error_response

def develop_workflow(workflow_design: List[Dict[str, Any]], model_name: str = "gpt-4o") -> str:
    """
    Develop a workflow project.
    Args:
        workflow_design: List of workflow steps
        model_name: Name of the model to use for inference
    Returns:
        JSON string with the workflow structure and metadata
    """
    result = create_workflow_structure(workflow_design, model_name)
    return json.dumps(result, ensure_ascii=False) 