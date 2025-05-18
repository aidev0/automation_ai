import os
import json
from typing import List, Dict, Any
from datetime import datetime
import re # For sanitizing filenames
from ai.llm.inference import run_inference
from ai.db.mongodb import create_agent
from ai.db.schema import Agent
import requests

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
    """Creates an agent file using LLM to generate the code and registers it in the database."""
    steps_log = []
    errors_log = []
    
    try:
        # Add default input schema if not provided
        if "input_schema" not in step:
            step["input_schema"] = {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object"
                        }
                    }
                },
                "required": ["items"]
            }
            
        # Generate agent code using LLM
        messages = [
            {"role": "system", "content": """You are an expert Python developer specializing in creating workflow agents.
            Your task is to generate a Python agent file that follows this EXACT structure:

            # Required imports
            import os
            import json
            import logging
            from typing import Dict, Any, List
            import requests

            # Configure logging
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            logger = logging.getLogger(__name__)

            # System Configuration
            AGENT_NAME = "..."  # From step label
            AGENT_DESCRIPTION = "..."  # From step description

            # Required Environment Variables
            REQUIRED_ENV_VARS = [...]  # List of required env vars from integrations

            # Input Schema
            INPUT_SCHEMA = {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                # Define input properties based on step input_schema_description
                            }
                        }
                    }
                },
                "required": ["items"]
            }

            # Output Schema (Standard for all agents)
            OUTPUT_SCHEMA = {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["success", "error"]},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object"
                        }
                    },
                    "error": {"type": "string", "nullable": true}
                },
                "required": ["status", "data"]
            }

            def run_inference(messages: List[Dict[str, str]], model_name: str = "gpt-4o") -> str:
                try:
                    api_key = os.getenv("OPENAI_API_KEY")
                    if not api_key:
                        raise ValueError("OPENAI_API_KEY environment variable not set")

                    headers = {
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    }

                    data = {
                        "model": model_name,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 2000
                    }

                    response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=data
                    )
                    response.raise_for_status()

                    result = response.json()
                    return result["choices"][0]["message"]["content"]

                except Exception as e:
                    logger.error(f"LLM inference failed: {str(e)}")
                    raise

            def run_agent(input_data: Dict[str, Any], model_name: str = "gpt-4o") -> Dict[str, Any]:
                try:
                    logger.info(f"Starting {AGENT_NAME} agent")
                    result = process_step(input_data, model_name)
                    logger.info(f"Completed {AGENT_NAME} agent")
                    return result
                except Exception as e:
                    logger.error(f"Agent failed: {str(e)}")
                    return {
                        "status": "error",
                        "data": [],
                        "error": str(e)
                    }

            def process_step(input_data: Dict[str, Any], model_name: str = "gpt-4o") -> Dict[str, Any]:
                try:
                    # Validate input
                    if not isinstance(input_data, dict) or "items" not in input_data:
                        return {"status": "error", "data": [], "error": "Invalid input format"}
                        
                    items = input_data["items"]
                    if not isinstance(items, list):
                        return {"status": "error", "data": [], "error": "Items must be a list"}
                        
                    # Process each item using LLM
                    processed_items = []
                    for item in items:
                        # Step 1: Use LLM to understand and plan the task
                        system_prompt = f"You are an expert at {AGENT_NAME}. Your task is to {AGENT_DESCRIPTION}. For any external service interactions (like Google Sheets, Gmail, etc.): 1. Use LLM to generate the correct API calls 2. Use LLM to process the API responses 3. Use LLM to handle any data transformations 4. Use LLM to validate the results. Always use LLM for: - Understanding the task requirements - Generating API calls - Processing responses - Data transformations - Error handling - Result validation"
                        
                        messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": json.dumps(item, ensure_ascii=False)}
                        ]
                        
                        task_plan = run_inference(messages, model_name=model_name)
                        
                        # Step 2: Use LLM to execute the task
                        execution_messages = [
                            {"role": "system", "content": "Execute the following task plan:"},
                            {"role": "user", "content": json.dumps({"plan": task_plan, "input": item}, ensure_ascii=False)}
                        ]
                        response = run_inference(execution_messages, model_name=model_name)
                        
                        # Step 3: Use LLM to validate the results
                        validation_messages = [
                            {"role": "system", "content": "Validate the following results:"},
                            {"role": "user", "content": json.dumps({"input": item, "output": response}, ensure_ascii=False)}
                        ]
                        validated_response = run_inference(validation_messages, model_name=model_name)
                        
                        processed_items.append(validated_response)
                        
                    return {
                        "status": "success",
                        "data": processed_items
                    }
                    
                except Exception as e:
                    logger.error(f"Processing failed: {str(e)}")
                    return {
                        "status": "error",
                        "data": [],
                        "error": str(e)
                    }

            # Main execution block
            if __name__ == "__main__":
                # Example usage
                test_input = {"items": [{"test": "data"}]}
                result = run_agent(test_input)
                print(json.dumps(result, indent=2))

            Rules:
            1. Use the step's label for AGENT_NAME
            2. Use the step's description for AGENT_DESCRIPTION
            3. Extract env vars from step's integrations
            4. Parse input_schema_description into proper JSON schema
            5. Include input validation in process_step
            6. No example usage or test code
            7. No explanations or docstrings
            8. No markdown formatting
            9. Use LLM for any processing needed
            10. Return structured output matching OUTPUT_SCHEMA

            The agent must:
            - Include all required imports (os, json, logging, typing, requests)
            - Configure logging
            - Define system config (name, description)
            - List required env vars
            - Define input/output schemas with items array structure
            - Include complete run_inference function
            - Include both run_agent and process_step functions with model_name parameter
            - Use LLM for ALL processing, including:
              - Understanding task requirements
              - Generating API calls
              - Processing responses
              - Data transformations
              - Error handling
              - Result validation
            - Return structured output
            - Include proper error handling
            - Include logging
            - Include main execution block

            LLM Usage Rules:
            1. Include complete run_inference function in each agent
            2. Use gpt-4o for all LLM operations (code generation, API interactions, planning, validation)
            3. Include proper error handling for LLM calls
            4. Use appropriate system prompts for each stage
            5. Process and validate LLM responses
            6. No placeholder comments about LLM usage
            7. Include actual LLM calls with proper parameters
            8. Handle rate limits and retries if needed
            9. Log LLM interactions

            Output only the Python code for the agent file. Do not include any markdown or explanatory text outside the code."""},
            {"role": "user", "content": json.dumps({"step": step}, ensure_ascii=False)}
        ]
        agent_code = run_inference(messages, model_name)
        print("\n=== LLM Agent Code Response ===\n" + agent_code + "\n")
        
        # Clean up any markdown code blocks or extra text
        agent_code = agent_code.replace("```python", "").replace("```", "").strip()
        
        # Write the file
        output_dir = os.path.dirname(agent_file_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        with open(agent_file_path, 'w', encoding="utf-8") as f:
            f.write(agent_code)
            
        steps_log.append(f"✓ Created agent file: {os.path.basename(agent_file_path)}")

        # Register agent in database
        agent = Agent(
            _id=str(datetime.utcnow().timestamp()),  # Use timestamp as ID
            timestamp=datetime.utcnow(),
            name=step["label"],
            description=step["description"],
            task=step["description"],
            integrations=step["integrations"],
            user_id=step.get("user_id", "system"),
            system=step.get("system", ""),
            model_name=model_name,
            input_schema=step["input_schema"],
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["success", "error"]},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object"
                        }
                    },
                    "error": {"type": "string", "nullable": true}
                },
                "required": ["status", "data"]
            },
            readme_md=step.get("readme", ""),
            code=agent_code,
            code_language="python",
            command=f"python {agent_file_path}",
            env_list=step.get("env_list", [])
        )

        # Push to database
        create_agent(agent.dict())
        steps_log.append(f"✓ Registered agent in database: {step['label']}")
            
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

def generate_project_artifacts(
    workflow_design_with_scripts: List[Dict[str, Any]],
    project_dir: str,
    project_name: str,
    model_name: str = "gpt-4o"
) -> Dict[str, Any]:
    """Generates project artifacts using LLM."""
    results = {
        "status": "pending",
        "files_generated": [],
        "files_content": {},
        "errors": []
    }
    
    files_to_generate = {
        "workflow_config.py": """Generate a Python configuration file for the workflow.
        - Only include the actual Python code
        - No explanations or docstrings
        - No markdown formatting or code block markers""",
        "README.md": """Generate a README file for the project.
        - Use markdown formatting
        - No code block markers
        - No explanations about the README itself""",
        "requirements.txt": """Generate a requirements.txt file with necessary dependencies.
        - One package per line
        - No explanations or comments
        - No markdown formatting""",
        ".env.example": """Generate an example .env file with required environment variables.
        - One variable per line
        - No explanations or comments
        - No markdown formatting"""
    }
    
    os.makedirs(project_dir, exist_ok=True)
    
    for filename, prompt in files_to_generate.items():
        try:
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps({"project_name": project_name, "workflow_steps": workflow_design_with_scripts}, ensure_ascii=False)}
            ]
            content = run_inference(messages, model_name)
            
            # Clean up any markdown code blocks or extra text
            content = content.replace("```python", "").replace("```", "").strip()
            
            file_path = os.path.join(project_dir, filename)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            results["files_generated"].append(file_path)
            results["files_content"][filename] = content
            print(f"✓ Generated {filename}")
            
        except Exception as e:
            error_msg = f"Error generating {filename}: {str(e)}"
            print(f"✗ {error_msg}")
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
            "input_schema": {
                "type": "object",
                "properties": {
                    "max_emails": {"type": "integer"},
                    "filter_subject": {"type": "string", "nullable": true},
                    "drive_folder_id": {"type": "string"}
                },
                "required": ["drive_folder_id"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "fetched_emails_count": {"type": "integer"},
                    "attachments_uploaded_count": {"type": "integer"},
                    "processed_email_ids": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["fetched_emails_count", "attachments_uploaded_count", "processed_email_ids"]
            }
        },
        {
            "label": "Content Summarizer & Keyword Extractor",
            "description": "Summarizes the content of the fetched emails and extracts keywords using OpenAI's GPT model. Stores results in a local SQLite database.",
            "integrations": ["openai", "sqlite"],
            "input_schema": {
                "type": "object",
                "properties": {
                    "email_bodies": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "body": {"type": "string"}
                            },
                            "required": ["id", "body"]
                        }
                    }
                },
                "required": ["email_bodies"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "summary": {"type": "string"},
                                "keywords": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            },
                            "required": ["id", "summary", "keywords"]
                        }
                    },
                    "db_path": {"type": "string"}
                },
                "required": ["results", "db_path"]
            }
        },
        {
            "label": "Slack Notifier",
            "description": "Sends notifications with summaries and direct links to Slack for urgent emails.",
            "integrations": ["slack"],
            "input_schema": {
                "type": "object",
                "properties": {
                    "urgent_summaries": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "summary": {"type": "string"},
                                "original_email_link": {"type": "string"}
                            },
                            "required": ["summary", "original_email_link"]
                        }
                    },
                    "slack_channel_id": {"type": "string"}
                },
                "required": ["urgent_summaries", "slack_channel_id"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "notifications_sent_count": {"type": "integer"},
                    "failed_notifications_count": {"type": "integer"}
                },
                "required": ["notifications_sent_count", "failed_notifications_count"]
            }
        },
        {
            "label": "Report Generator",
            "description": "Generates a daily PDF report from the SQLite database data and emails it.",
            "integrations": ["sqlite", "smtp", "pdf-library"],
            "input_schema": {
                "type": "object",
                "properties": {
                    "report_date": {"type": "string"},
                    "recipient_email": {"type": "string"}
                },
                "required": ["report_date", "recipient_email"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "report_path": {"type": "string"},
                    "email_sent_status": {"type": "boolean"}
                },
                "required": ["report_path", "email_sent_status"]
            }
        }
    ]

    print("Starting workflow development process with example design using MOCK LLM...")
    
    # The mock run_inference is defined within project_artifact_generator.py and agent_generator.py
    # If those files are imported correctly, their mocks will be used.
    # No need for further monkey-patching here if imports are successful.

    result_json_output = develop_workflow_entry_point(sample_workflow_design)
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