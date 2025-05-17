import os
import json
from typing import List, Dict, Any
from datetime import datetime
from ai.llm.inference import run_inference

SYSTEM_MESSAGE = """
You are the config generator for a workflow system. Your job is to write a Python config file called `workflow_config.py`.

Input: a list of steps in a workflow. Each step is a dictionary with:
- `label`: the agent label
- `description`: what the agent does
- Optional fields: `integrations`, `mcps`, `apis`, `tools`, `env_vars`, `packages`

The config file should include:
1. `workflow_env_vars`: a list of all unique env vars used by any agent
2. `workflow_tech`: a list of all unique technologies used (from integrations, mcps, apis, tools)
3. `agents`: a list of dictionaries, each with:
    - `agent_label`: snake_case label of the step
    - `env_vars`: env vars used by this agent
    - `agent_task`: description of the step
    - `agent_tech`: all tech used by the agent (integrations, mcps, apis, tools)

Output only a valid Python file (no markdown, no extra text). The file should be ready to be saved as `workflow_config.py`.
"""

def generate_project_name(workflow_design: List[Dict[str, Any]]) -> str:
    timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
    action = workflow_design[0].get("label", "workflow").lower().replace(" ", "_")
    return f"{action}_{timestamp}"

def generate_config_file(workflow_design: List[Dict[str, Any]], model_name: str = "gpt-4o") -> Dict[str, Any]:
    try:
        base_dir = "generated_workflows"
        os.makedirs(base_dir, exist_ok=True)

        project_name = generate_project_name(workflow_design)
        project_dir = os.path.join(base_dir, project_name)
        os.makedirs(project_dir, exist_ok=True)

        config_path = os.path.join(project_dir, "workflow_config.py")
        requirements_path = os.path.join(project_dir, "requirements.txt")

        # --- LLM-based config file generation ---
        messages = [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": json.dumps(workflow_design, ensure_ascii=False)}
        ]
        response = run_inference(messages, model_name=model_name)

        if "```python" in response:
            response = response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()

        with open(config_path, "w") as f:
            f.write(response)

        # --- Requirements.txt generation ---
        package_map = {}  # integration/tool -> set(packages)

        for step in workflow_design:
            packages = step.get("packages", [])
            integrations = step.get("integrations", []) + step.get("mcps", []) + step.get("apis", []) + step.get("tools", [])
            for tech in integrations:
                if tech not in package_map:
                    package_map[tech] = set()
                package_map[tech].update(packages)

        # Flatten all packages for install command
        requirements_lines = [
            "# Core requirements",
            "requests>=2.31.0",
            "python-dotenv>=1.0.0",
            ""
        ]

        for tech, pkgs in package_map.items():
            if not pkgs:
                continue
            requirements_lines.append(f"# {tech.title()} requirements")
            requirements_lines += [f"{pkg}>=0.0.0" for pkg in sorted(pkgs)]
            requirements_lines.append("")

        with open(requirements_path, "w") as f:
            f.write("\n".join(requirements_lines))

        return {
            "status": "success",
            "project_name": project_name,
            "project_dir": project_dir,
            "config_path": config_path,
            "requirements_path": requirements_path,
            "code_preview": response
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
