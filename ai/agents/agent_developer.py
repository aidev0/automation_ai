import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
import requests
from ai.db.mongodb import get_db
from ai.llm.inference import run_inference

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_agent_code(step: Dict[str, Any], model_name: str = "gpt-4o") -> str:
    """
    Generates agent code from a workflow step.
    """
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

            # Output Schema
            OUTPUT_SCHEMA = {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["success", "error"]},
                    "data": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                # Define output properties based on step output_schema_description
                            }
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
            4. Parse input_schema_description and output_schema_description into proper JSON schemas
            5. Include input/output validation in process_step
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
    # Clean up any markdown code blocks or extra text
    agent_code = agent_code.replace("```python", "").replace("```", "").strip()
    return agent_code

def push_agent(
    step: Dict[str, Any],
    code: str
) -> str:
    """
    Pushes agent to database.
    First generates agent's response using LLM, then extracts schemas and env vars from code.
    """

    code = code.replace("```python", "").replace("```", "").strip()
        
    # Extract schemas and env vars from code
    # extract_messages = [
    #     {"role": "system", "content": "Extract INPUT_SCHEMA, OUTPUT_SCHEMA, and REQUIRED_ENV_VARS from the code. Return as JSON with input_schema, output_schema, and env_list fields."},
    #     {"role": "user", "content": code}
    # ]
    # # extract_response = run_inference(extract_messages, model_name="gpt-4o")
    # extracted = json.loads(extract_response)
    
    # Create agent object with the response
    agent = {
        "timestamp": datetime.utcnow(),
        "name": step["label"],
        "description": step["description"],
        "task": step["description"],
        "integrations": step["integrations"],
        # "system": "",
        "model_name": "gpt-4o",
        # "input_schema": extracted["input_schema"],
        # "output_schema": extracted["output_schema"],
        "code": code,
        "code_language": "python",
        "command": f"python {step['label'].lower().replace(' ', '_')}.py",
        # "env_list": extracted["env_list"]
    }
    
    db = get_db()
    result = db.agents.insert_one(agent)
    return str(result.inserted_id)

