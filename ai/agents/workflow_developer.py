from typing import List, Dict, Any
import os
import json
from datetime import datetime
from ai.agents.agent_maker import create_agent
from ai.agents.config_maker import generate_config_file


def generate_project_name(workflow_design: List[Dict[str, Any]]) -> str:
    timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
    label = workflow_design[0].get("label", "workflow").lower().replace(" ", "_")
    techs = "_".join(sorted(workflow_design[0].get("integrations", [])))
    return f"{techs}_{label}_{timestamp}"


def create_workflow_structure(workflow_design: List[Dict[str, Any]], model_name: str = "gpt-4o") -> Dict[str, Any]:
    steps, errors = [], []

    try:
        project_name = generate_project_name(workflow_design)
        base_dir = os.path.join("generated_workflows", project_name)
        os.makedirs(base_dir, exist_ok=True)
        steps.append(f"✓ Created project directory: {base_dir}")

        agent_files = []
        for step in workflow_design:
            filename = step["label"].lower().replace(" ", "_") + ".py"
            filepath = os.path.join(base_dir, filename)
            result = create_agent(step, filepath, model_name)
            agent_files.append(filename)

            if result["status"] == "error":
                errors.append(result["error"])
                steps += result.get("steps", [])
            else:
                steps.append(f"✓ Agent created: {filename}")

        if errors:
            raise Exception("Agent creation failed")

        config_result = generate_config_file(workflow_design, model_name=model_name)
        if config_result["status"] == "error":
            errors.append(config_result["error"])
            steps.append(f"✗ Config generation failed: {config_result['error']}")
        else:
            steps.append(f"✓ Config generated: {config_result['config_path']}")
            steps.append(f"✓ Requirements generated: {config_result['requirements_path']}")

        structure = {
            "workflows": {
                project_name: {
                    "agents": {f: None for f in agent_files},
                    "workflow_config.py": None,
                    "requirements.txt": None
                }
            }
        }

        return {
            "project_name": project_name,
            "project_dir": base_dir,
            "structure": structure,
            "status": "success",
            "error": "",
            "steps": steps,
            "errors": errors
        }

    except Exception as e:
        return {
            "project_name": "",
            "project_dir": "",
            "structure": {},
            "status": "error",
            "error": str(e),
            "steps": steps,
            "errors": errors + [str(e)]
        }


def develop_workflow(workflow_design: List[Dict[str, Any]], model_name: str = "gpt-4o") -> str:
    result = create_workflow_structure(workflow_design, model_name)
    return json.dumps(result, indent=2, ensure_ascii=False)