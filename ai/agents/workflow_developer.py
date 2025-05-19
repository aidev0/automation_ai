import os
import json
from typing import List, Dict, Any
from datetime import datetime
import re # For sanitizing filenames
from ai.llm.inference import run_inference
import requests
from ai.agents.agent_developer import generate_agent_code
from ai.agents.project_artifact_generator import generate_project_artifacts

def generate_unique_project_name(workflow_design_steps: List[Dict[str, Any]]) -> str:
    """Generates a unique project name based on the first step's label and a timestamp."""
    timestamp = datetime.now().strftime("%y%m%d_%H%M%S")
    if not workflow_design_steps or not workflow_design_steps[0].get("label"):
        action_label = "generic_workflow"
    else:
        action_label = workflow_design_steps[0]["label"].lower()

    action_label = re.sub(r'[^\w-]', '_', action_label)
    action_label = re.sub(r'_+', '_', action_label).strip('_')
    action_label = action_label[:30]

    if not action_label:
        action_label = "workflow"

    return f"{action_label}_{timestamp}"

def create_agent_file(step: Dict[str, Any], agent_file_path: str, model_name: str = "gpt-4o") -> Dict[str, Any]:
    """Creates an agent file using LLM to generate the code."""
    steps_log = []
    errors_log = []
    
    try:
        agent_code = generate_agent_code(step, model_name)
        
        # Write the file
        output_dir = os.path.dirname(agent_file_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(agent_file_path, 'w', encoding="utf-8") as f:
            f.write(agent_code)
            
        steps_log.append(f"✓ Created agent file: {os.path.basename(agent_file_path)}")
        return {
            "path": agent_file_path,
            "status": "success",
            "error": "",
            "steps_log": steps_log,
            "errors_log": errors_log
        }
    except Exception as e:
        error_msg = f"Failed to create agent file {os.path.basename(agent_file_path)}: {str(e)}"
        errors_log.append(error_msg)
        steps_log.append(f"✗ {error_msg}")
        return {
            "path": agent_file_path,
            "status": "error",
            "error": error_msg,
            "steps_log": steps_log,
            "errors_log": errors_log
        }

def create_workflow_project(
    workflow_design_steps: List[Dict[str, Any]],
    base_project_dir: str = "generated_workflows",
    model_name: str = "gpt-4o"
) -> Dict[str, Any]:
    """
    Creates the full workflow project structure, including agent files and project artifacts.
    workflow_design_steps: A list of dictionaries, where each dictionary defines an agent/step.
    """
    overall_status = {
        "project_name": "",
        "project_dir": "",
        "status": "pending",
        "message": "",
        "details": {
            "agents_generated": [],
            "project_artifacts_status": None
        },
        "log": [],
        "errors": []
    }

    try:
        print("\n=== Starting Workflow Project Creation ===")
        if not isinstance(workflow_design_steps, list) or not all(isinstance(step, dict) for step in workflow_design_steps):
             raise ValueError("workflow_design_steps must be a list of dictionaries.")
        if not workflow_design_steps:
            raise ValueError("Workflow design steps list cannot be empty.")

        project_name = generate_unique_project_name(workflow_design_steps)
        overall_status["project_name"] = project_name
        project_dir_path = os.path.join(base_project_dir, project_name)
        overall_status["project_dir"] = project_dir_path
        print(f"\nProject: {project_name}")
        print(f"Directory: {project_dir_path}")

        os.makedirs(project_dir_path, exist_ok=True)

        print("\n=== Generating Agent Files ===")
        agents_generated_summary = overall_status["details"]["agents_generated"]
        workflow_design_with_scripts = []

        has_agent_errors = False
        for i, step_details in enumerate(workflow_design_steps):
            agent_base_label = step_details.get("label", f"agent_{i+1}")
            if not isinstance(agent_base_label, str) or not agent_base_label.strip():
                 agent_base_label = f"agent_{i+1}"
                 print(f"Warning: Step {i+1} has an invalid label. Using default: {agent_base_label}")

            sanitized_label = re.sub(r'[^\w-]', '_', agent_base_label.lower())
            sanitized_label = re.sub(r'_+', '_', sanitized_label).strip('_')
            agent_filename = f"{sanitized_label or f'agent_{i+1}'}.py"
            agent_file_path = os.path.join(project_dir_path, agent_filename)

            print(f"\nCreating agent: {agent_base_label}")
            agent_result = create_agent_file(step_details, agent_file_path, model_name)

            for log_entry in agent_result.get("steps_log", []):
                print(f"  {log_entry}")
            for error_entry in agent_result.get("errors_log", []):
                 overall_status["errors"].append(f"  [Agent Error: {agent_filename}] {error_entry}")

            agent_summary = {
                "label": agent_base_label,
                "script_name": agent_filename,
                "path": agent_result.get("path"),
                "status": agent_result["status"]
            }
            if agent_result["status"] == "error":
                has_agent_errors = True
                agent_summary["error_message"] = agent_result.get("error")
                summary_error_msg = f"Error creating agent '{agent_base_label}': {agent_result.get('error')}"
                if summary_error_msg not in overall_status["errors"]:
                     overall_status["errors"].append(summary_error_msg)

            agents_generated_summary.append(agent_summary)
            current_step_for_config = step_details.copy()
            current_step_for_config['script_name'] = agent_filename
            workflow_design_with_scripts.append(current_step_for_config)

        print("\n=== Generating Project Artifacts ===")
        project_artifacts_result = generate_project_artifacts(
            workflow_design_with_scripts=workflow_design_with_scripts,
            project_dir=project_dir_path,
            project_name=project_name,
            model_name=model_name
        )
        overall_status["details"]["project_artifacts_status"] = project_artifacts_result

        if project_artifacts_result.get("errors"):
            for err_info in project_artifacts_result["errors"]:
                err_msg = f"Error generating project file '{err_info.get('file')}': {err_info.get('error')}"
                overall_status["errors"].append(err_msg)
            print("\n✗ Some project artifacts failed to generate")
        else:
            print("\n✓ All project artifacts generated successfully")

        if overall_status["errors"] or has_agent_errors or project_artifacts_result.get("status") in ["error", "partial_success"]:
            successful_agents = any(a['status'] == 'success' for a in agents_generated_summary)
            successful_artifacts = project_artifacts_result.get("status") == "success" or \
                                   (project_artifacts_result.get("status") == "partial_success" and project_artifacts_result.get("files_generated"))

            if not successful_agents and not project_artifacts_result.get("files_generated"):
                overall_status["status"] = "error"
                overall_status["message"] = f"Workflow project '{project_name}' creation FAILED. No usable files were generated."
                print(f"\n✗ {overall_status['message']}")
            else:
                overall_status["status"] = "partial_success"
                overall_status["message"] = f"Workflow project '{project_name}' created with some errors or partial output."
                print(f"\n⚠ {overall_status['message']}")
        else:
            overall_status["status"] = "success"
            overall_status["message"] = f"Workflow project '{project_name}' created successfully at {project_dir_path}."
            print(f"\n✓ {overall_status['message']}")

        print("\n=== Project Creation Summary ===")
        print(f"Status: {overall_status['status']}")
        print(f"Project: {project_name}")
        print(f"Location: {project_dir_path}")
        if overall_status["errors"]:
            print("\nErrors encountered:")
            for error in overall_status["errors"]:
                print(f"  ✗ {error}")

        return overall_status

    except ValueError as ve:
        overall_status["status"] = "critical_error"
        error_msg = f"Input validation error: {str(ve)}"
        overall_status["message"] = error_msg
        overall_status["errors"].append(error_msg)
        print(f"\n✗ CRITICAL ERROR: {error_msg}")
        return overall_status
    except Exception as e:
        overall_status["status"] = "critical_error"
        error_msg = f"Critical error during workflow project creation: {str(e)}"
        overall_status["message"] = error_msg
        overall_status["errors"].append(error_msg)
        print(f"\n✗ CRITICAL ERROR: {error_msg}")
        return overall_status

def run_develop_workflow(workflow_design: List[Dict[str, Any]], model_name: str = "gpt-4o") -> str:
    """
    Main entry point to develop the workflow.
    Returns a JSON string summarizing the outcome.
    """
    if not workflow_design:
        error_result = {
            "project_name": "",
            "project_dir": "",
            "status": "critical_error",
            "message": "Workflow design input cannot be empty.",
            "details": {},
            "log": ["Workflow design input was empty or null."],
            "errors": ["Workflow design input cannot be empty."]
        }
        return json.dumps(error_result, indent=2, ensure_ascii=False)

    result = create_workflow_project(workflow_design_steps=workflow_design, model_name=model_name)
    return json.dumps(result, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    sample_workflow_design = [
        {
            "label": "Email Fetcher",
            "description": "Fetches new emails from a Gmail account based on specified criteria, then uploads attachments to a designated Google Drive folder.",
            "integrations": ["gmail", "google-drive"],
            "input_schema_description": "{'max_emails': int, 'filter_subject': Optional[str], 'drive_folder_id': str}",
            "output_schema_description": "{'fetched_emails_count': int, 'attachments_uploaded_count': int, 'processed_email_ids': List[str]}"
        },
        {
            "label": "Content Summarizer & Keyword Extractor",
            "description": "Summarizes the content of the fetched emails and extracts keywords using OpenAI's GPT model. Stores results in a local SQLite database.",
            "integrations": ["openai", "sqlite"],
            "input_schema_description": "{'email_bodies': List[Dict{'id':str, 'body':str}]}",
            "output_schema_description": "{'results': List[Dict{'id':str, 'summary':str, 'keywords':List[str]}], 'db_path': str}"
        },
        {
            "label": "Slack Notifier",
            "description": "Sends notifications with summaries and direct links to Slack for urgent emails.",
            "integrations": ["slack"],
            "input_schema_description": "{'urgent_summaries': List[Dict{'summary':str, 'original_email_link':str}], 'slack_channel_id': str}",
            "output_schema_description": "{'notifications_sent_count': int, 'failed_notifications_count': int}"
        },
        {
            "label": "Report Generator",
            "description": "Generates a daily PDF report from the SQLite database data and emails it.",
            "integrations": ["sqlite", "smtp", "pdf-library"],
            "input_schema_description": "{'report_date': str, 'recipient_email': str}",
            "output_schema_description": "{'report_path': str, 'email_sent_status': bool}"
        }
    ]

    print("Starting workflow development process with example design using MOCK LLM...")
    
    # The mock run_inference is defined within project_artifact_generator.py and agent_generator.py
    # If those files are imported correctly, their mocks will be used.
    # No need for further monkey-patching here if imports are successful.

    result_json_output = run_develop_workflow(sample_workflow_design)
    print("\n--- Workflow Development Result (JSON Output) ---")
    print(result_json_output)

    # Optional: Further inspect the detailed JSON output
    # result_data = json.loads(result_json_output)
    # if result_data.get("project_dir"):
    #     print(f"\nProject files would be generated in: {result_data['project_dir']}")
    # if result_data.get("errors"):
    #     print("\n--- Top-Level ERRORS Encountered ---")
    #     for error in result_data["errors"]:
    #         print(f"- {error}")
    # if result_data.get("log"):
    #     print("\n--- DETAILED LOG ---")
    #     for log_entry in result_data["log"]:
    #         print(log_entry)
    print("\nScript finished. Review console output for MOCK LLM interactions and logs.")