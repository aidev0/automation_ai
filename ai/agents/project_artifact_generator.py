import os
import json
from typing import List, Dict, Any
from ai.llm.inference import run_inference

# System message for workflow_config.py generation
CONFIG_SYSTEM_MESSAGE = """
You are the config generator for a workflow system. Your job is to write a Python config file called `workflow_config.py`.

Input: A dictionary containing 'project_name' (string) and 'workflow_steps' (a list of dictionaries, where each step has 'label', 'description', and optional fields like 'integrations', 'mcps', 'apis', 'tools', 'env_vars', 'packages', 'settings'). The 'workflow_steps' will also include 'script_name' for each agent.

The config file must follow this exact structure:

# Project Configuration
PROJECT_NAME = "..."  # From project_name
WORKFLOW_VERSION = "1.0.0"

# Environment Settings
WORKFLOW_ENVIRONMENT = "development"  # Options: development, production
WORKFLOW_DEBUG = False
WORKFLOW_LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR

# Required Environment Variables
WORKFLOW_ENV_VARS = [
    # Core workflow vars
    "WORKFLOW_ENVIRONMENT",
    "WORKFLOW_DEBUG",
    "WORKFLOW_LOG_LEVEL",
    # Add other required vars from integrations
]

# Workflow Technologies
WORKFLOW_TECH = [
    # List of all unique technologies used (from integrations, mcps, apis, tools)
]

# Workflow Settings
WORKFLOW_SETTINGS = {
    "environment": WORKFLOW_ENVIRONMENT,
    "debug": WORKFLOW_DEBUG,
    "log_level": WORKFLOW_LOG_LEVEL,
    # Add other workflow-level settings
}

# Agent Configurations
AGENTS = [
    {
        "label": "...",  # From step label
        "description": "...",  # From step description
        "script_name": "...",  # From step script_name
        "integrations": [...],  # From step integrations
        "env_vars": [...],  # Required env vars for this agent
        "settings": {...}  # Agent-specific settings
    }
]

# Integration Configurations
INTEGRATIONS = {
    "integration_name": {
        "env_vars": [...],  # Required env vars
        "packages": [...],  # Required packages
        "settings": {...}  # Integration-specific settings
    }
}

Rules:
1. Use the project_name for PROJECT_NAME
2. Extract all unique env vars from agents and integrations
3. Extract all unique technologies from agents' integrations
4. Define proper settings for each integration
5. Include all required packages for each integration
6. No example usage or test code
7. No explanations or docstrings
8. No markdown formatting

Output only the Python code for the config file. Do not include any markdown or explanatory text outside the code.
"""

# System message for README.md generation
README_SYSTEM_MESSAGE = """
You are tasked with generating a user-friendly README.md file for a new workflow automation project.

Input: A dictionary containing 'project_name' (string) and 'workflow_steps' (a list of agent/step dictionaries, each with 'label', 'description', and 'script_name').

The README.md should include the following sections:
1.  Project Title: Use the provided 'project_name'.
2.  Overview: A brief summary of the workflow's purpose and what it automates, based on the collective agent descriptions.
3.  Agents: A list or description of each agent in the workflow (from 'workflow_steps'), mentioning its role and its script file name (e.g., "Email Fetcher (`email_fetcher.py`): Fetches new emails...").
4.  Technologies Used: Briefly mention the key technologies or integrations involved (infer from agent descriptions and the overall workflow context).
5.  Setup and Usage:
    * Prerequisites (e.g., Python 3.x, pip).
    * Installation: Explain how to set up the environment (e.g., `python -m venv venv`, `source venv/bin/activate` or `venv\\Scripts\\activate`, `pip install -r requirements.txt`).
    * Configuration: Detail the need to create a `.env` file from `.env.example` (if you generate one) or list key environment variables. Mention `workflow_config.py` for workflow behavior settings.
    * How to run the workflow (provide a placeholder command if the exact entry point is not known by you, e.g., `python main.py` or `python run_workflow.py`).
6.  Project Structure: Briefly describe the key files and directories (e.g., `/agents` or individual agent scripts, `workflow_config.py`, `requirements.txt`, `.env`).

Make the README clear, concise, and helpful for someone new to the project. Use markdown formatting.
"""

# System message for requirements.txt generation
REQUIREMENTS_SYSTEM_MESSAGE = """
You are tasked with generating a `requirements.txt` file for a Python-based workflow automation project.

Input: A dictionary containing 'project_name' (string) and 'workflow_steps' (a list of agent/step dictionaries, each with 'label', 'description', and potentially 'integrations', 'packages').

Based on the workflow steps and their descriptions/integrations:
1.  Identify all necessary Python packages.
2.  Include core workflow packages often used in such projects (e.g., requests, python-dotenv, pydantic for data validation).
3.  Include packages for any specified or inferred integrations (e.g., `openai` for OpenAI, `google-api-python-client` and `google-auth-httplib2` and `google-auth-oauthlib` for Google services, `slack-sdk` for Slack, `aiohttp` for async HTTP requests if applicable). Refer to common, up-to-date libraries for the integrations mentioned.
4.  List each package on a new line. It's good practice to include versions (e.g., `package_name>=1.2.3,<2.0.0` or `package_name==1.2.3`), but if versions are not known, list only the package name. For this task, aim to provide package names without specific versions unless a common default versioning scheme is standard for a package (e.g. `somepackage>=X.Y`).

Output only the content of a valid `requirements.txt` file (no markdown, no extra text).
"""

# System message for .env file content generation
ENV_SYSTEM_MESSAGE = """
You are tasked with generating the content for a `.env.example` file for a workflow automation project. This file will serve as a template for users.

Input: A dictionary containing 'project_name' (string) and 'workflow_steps' (a list of agent/step dictionaries, each potentially implying necessary environment variables through its 'label', 'description', or 'integrations').

Based on the workflow design:
1.  List all likely required environment variables.
2.  Include common workflow environment variables like `WORKFLOW_ENVIRONMENT=development` (options: development, production), `WORKFLOW_DEBUG=false` (options: true, false), `WORKFLOW_LOG_LEVEL=INFO` (options: DEBUG, INFO, WARNING, ERROR).
3.  For each integration identified in the workflow steps (e.g., OpenAI, Google Sheets, Slack, SMTP), list its corresponding standard environment variables. Examples include:
    "GOOGLE_APPLICATION_CREDENTIALS" (path to JSON key file for Google Cloud services)
    "GOOGLE_SHEET_ID"
    "GMAIL_USER_EMAIL"
    "SLACK_BOT_TOKEN" (for modern Slack apps, usually starts with xoxb-)
    "SLACK_APP_TOKEN" (for specific features like Socket Mode, usually starts with xapp-)
    "DISCORD_BOT_TOKEN"
    "NOTION_API_KEY"
    "AIRTABLE_API_KEY"
    "AIRTABLE_BASE_ID"
    "AIRTABLE_TABLE_NAME"
    "ZAPIER_NLA_API_KEY" (if using Zapier Natural Language Actions)
    "WEBHOOK_URL_EXAMPLE"
    "GENERIC_API_KEY_FOR_XYZ_SERVICE"
    "SMTP_HOST"
    "SMTP_PORT"
    "SMTP_USER"
    "SMTP_PASSWORD"
    "SMTP_USE_TLS" (true/false)
    "OPENAI_API_KEY"
    "ANTHROPIC_API_KEY"
    "VAPI_API_KEY"
    "TWILIO_ACCOUNT_SID"
    "TWILIO_AUTH_TOKEN"
4.  Format each variable as `VARIABLE_NAME= # Optional comment explaining the variable`. The user will fill in the values.
5.  Add comments to group related variables or explain their purpose where helpful.

Output only the content of a valid `.env.example` file (no markdown, no extra text).
Start the file with a comment like:
# This is an example .env file. Copy it to .env and fill in your actual values.
# Do not commit your .env file to version control.
"""

def _call_llm_for_file_content(system_message: str, user_data: Dict[str, Any], model_name: str) -> str:
    """Helper function to call the LLM and parse its response for file content."""
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": json.dumps(user_data, ensure_ascii=False)}
    ]
    response_text = run_inference(messages, model_name=model_name)

    # Standardize LLM response cleaning.
    # If the LLM is expected to return raw code without fences, this might be simplified.
    # However, keeping some fence-stripping logic can be a robust fallback.
    # The user specifically requested *prompts* not to contain ```python.
    # This parsing logic handles what the LLM *returns*.
    content_to_check = response_text.strip()
    
    # Check for common code block fences if LLM still uses them
    if content_to_check.startswith("```") and content_to_check.endswith("```"):
        lines = content_to_check.splitlines()
        if len(lines) > 1:
            # Remove first line (potential language specifier like "python") and last line ("```")
            # Or just first line if it's ```python and last is ```
            if lines[0].startswith("```") and lines[0] != "```": # Handles ```python, ```json etc.
                content = "\n".join(lines[1:-1]).strip()
            else: # Handles simple ``` on first line
                content = "\n".join(lines[1:-1]).strip() if len(lines) > 2 else "" # if only ``` \n ```
            # If content is empty after stripping, it might be just fences around nothing
            if not content and len(lines) == 2 and lines[0].startswith("```") and lines[1] == "```":
                 content = ""
            elif not content and len(lines) > 2 and lines[0].startswith("```") and lines[-1] == "```":
                 # It means the lines between were empty or whitespace
                 content = ""
            elif not content and len(lines) <= 2 : # handles cases like ```\n``` or ``````
                content = ""

        elif len(lines) == 1 : # ```content``` on one line
            content = lines[0][3:-3].strip() if lines[0] != "```" else ""
        else: # Just fences or malformed
            content = content_to_check # Fallback if stripping didn't make sense
    else:
        content = content_to_check # No fences detected, use as is

    return content


def generate_project_artifacts(
    workflow_design_with_scripts: List[Dict[str, Any]], # Expects steps to include 'script_name'
    project_dir: str,
    project_name: str,
    model_name: str = "gpt-4o"
) -> Dict[str, Any]:
    """
    Generates workflow_config.py, README.md, requirements.txt, and .env.example files.
    'workflow_design_with_scripts' is the list of agent steps, augmented with their script names.
    """
    results = {
        "status": "pending",
        "files_generated": [], # List of paths for successfully generated files
        "files_content": {}, # filename: content
        "errors": []
    }
    llm_input_data = {"project_name": project_name, "workflow_steps": workflow_design_with_scripts}


    files_to_generate_info = {
        "workflow_config.py": {"system_message": CONFIG_SYSTEM_MESSAGE},
        "README.md": {"system_message": README_SYSTEM_MESSAGE},
        "requirements.txt": {"system_message": REQUIREMENTS_SYSTEM_MESSAGE},
        ".env.example": {"system_message": ENV_SYSTEM_MESSAGE},
    }

    os.makedirs(project_dir, exist_ok=True)

    for filename, info in files_to_generate_info.items():
        try:
            print(f"Generating {filename}...")
            content = _call_llm_for_file_content(info["system_message"], llm_input_data, model_name)

            if not content and filename not in [".env.example", "README.md", "requirements.txt"]:
                # Config file should not be empty. Others might be minimal.
                raise ValueError(f"LLM returned empty or invalid content for critical file: {filename}")

            file_path = os.path.join(project_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            results["files_generated"].append(file_path)
            results["files_content"][filename] = content
            print(f"Successfully generated {filename} at {file_path}")

        except Exception as e:
            error_msg = f"Error generating {filename}: {str(e)}"
            print(error_msg)
            results["errors"].append({"file": filename, "error": error_msg})
            results["files_content"][filename] = None

    if not results["errors"]:
        results["status"] = "success"
    else:
        if results["files_generated"]:
            results["status"] = "partial_success"
        else:
            results["status"] = "error"

    return results