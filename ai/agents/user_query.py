from typing import List, Dict, Any
import json
from datetime import datetime
from ai.db.mongodb import get_db, get_all_messages
from ai.llm.inference import run_inference
from ai.agents.next_agent import get_next_agent
from ai.agents.workflow_designer import design_workflow
from ai.agents.workflow_developer import run_develop_workflow
from ai.agents.user_understanding import get_user_understanding
from ai.agents.user_interface import get_user_ineterface_reponse

def get_chat_messages(chat_id: str) -> List[Dict[str, Any]]:
    """Fetch messages for a given chat_id from the database."""
    messages = get_all_messages(chat_id)
    
    # Format messages for LLM
    llm_messages = []
    for message in messages:
        content = ""
        for key in ["text", "json", "nodeList"]: 
            if key in message and message[key] is not None:
                content += str(message[key])
        if message['sender'] == "user":
            llm_messages.append({"role": "user", "content": str(content)})
        else:
            llm_messages.append({"role": "assistant", "content": str(content)})
    
    return llm_messages

def push_message(chat_id: str, text_content: str = None, json_content: Dict = None, node_list: List = None, message_type: str = "ai") -> None:
    """Push a message to the messages collection in the database."""
    db = get_db()
    
    # Combine text and JSON content
    content = ""
    if text_content:
        content += text_content
    if json_content:
        if content:
            content += "\n"
        content += json.dumps(json_content)
    
    # Get current time in local timezone
    local_time = datetime.now().astimezone()
    
    message = {
        "id": str(int(local_time.timestamp() * 1000)),
        "chatId": chat_id,
        "text": content,
        "json": None,
        "nodeList": node_list,
        "sender": "user" if message_type == "user" else "ai",
        "timestamp": local_time,
        "type": message_type
    }
    db.messages.insert_one(message)

def process_user_query(chat_id: str) -> Dict[str, Any]:
    """Process a user query and coordinate the workflow development process."""
    try:
        # Get chat history
        messages = get_chat_messages(chat_id)
        
        # Get user understanding using GPT-4
        user_understanding = json.loads(get_user_understanding(messages, model_name="gpt-4o"))
        print("\nUser Understanding Response:", json.dumps(user_understanding, indent=2))
        
        # Push user understanding as JSON
        push_message(
            chat_id=chat_id,
            text_content="Our Understanding AI has understood user's query.",
            json_content=user_understanding,
            message_type="json"
        )
        
        # Run next agent in loop until it becomes user_interface or max iterations reached
        iteration_count = 0
        max_iterations = 3
        
        while iteration_count < max_iterations:
            # Determine next agent based on current state
            next_agent_result = json.loads(get_next_agent(messages, model_name="gpt-4o"))
            next_agent = next_agent_result["next_agent"]
            print("\nNext Agent Response:", json.dumps(next_agent_result, indent=2))
            
            # Push next agent decision as JSON
            push_message(
                chat_id=chat_id,
                json_content=next_agent_result,
                message_type="json"
            )
            
            # If next agent is user_interface, break the loop
            if next_agent == "user_interface":
                break
                
            # Process based on next agent
            if next_agent == "workflow_designer":
                # Design workflow using GPT-4
                workflow_design = json.loads(design_workflow(messages, model_name="gpt-4o"))
                print("\nWorkflow Designer Response:", json.dumps(workflow_design, indent=2))
                
                # Store workflow design in database
                db = get_db()
                workflow_design_doc = {
                    "chatId": chat_id,
                    "design": workflow_design,
                    "timestamp": datetime.now(),
                    "status": "pending"
                }
                db.workflow_designs.insert_one(workflow_design_doc)
                
                # Push workflow design as JSON
                push_message(
                    chat_id=chat_id,
                    text_content="Our Workflow Design AI has designed the following workflow for you. Please review it and let us know if you need any changes.",
                    node_list=workflow_design,
                    message_type="workflow_plan"
                )
                
            elif next_agent == "workflow_developer":
                # Get workflow design from database
                db = get_db()
                workflow_design_doc = db.workflow_designs.find_one({"chatId": chat_id, "status": "pending"})
                
                if workflow_design_doc:
                    workflow_design = workflow_design_doc["design"]
                    
                    # Develop workflow using GPT-4
                    workflow_result = run_develop_workflow(workflow_design, model_name="gpt-4o", chat_id=chat_id)
                    workflow_result = json.loads(workflow_result)
                    print("\nWorkflow Developer Response:", json.dumps(workflow_result, indent=2))
                    
                    # Create node list with agent details
                    node_list = []
                    for agent_id, agent_summary in zip(workflow_result["details"]["agent_ids"], workflow_result["details"]["agents_generated"]):
                        node_list.append({
                            "agent_id": agent_id,
                            "label": agent_summary["label"],
                            "description": workflow_design[workflow_result["details"]["agents_generated"].index(agent_summary)]["description"],
                            "integrations": workflow_design[workflow_result["details"]["agents_generated"].index(agent_summary)]["integrations"]
                        })
                    
                    # Delete the workflow design since it's been approved and developed
                    db.workflow_designs.delete_one({"_id": workflow_design_doc["_id"]})
                    
                    # Push workflow development result as JSON
                    push_message(
                        chat_id=chat_id,
                        text_content="Our Workflow Development AI has created the following agents for your workflow. Each agent is specialized in a specific task.",
                        node_list=node_list,
                        json_content=workflow_result,
                        message_type="workflow_agents"
                    )
            
            # Get updated messages after processing
            messages = get_chat_messages(chat_id)
            
            # Increment iteration count
            iteration_count += 1
            
            # If we've reached max iterations, force user_interface
            if iteration_count >= max_iterations:
                next_agent = "user_interface"
                next_agent_result = {
                    "next_agent": "user_interface",
                    "reason": "Maximum iterations reached, switching to user interface",
                    "is_workflow_design_approved": False,
                    "is_workflow_build_approved": False,
                    "do_we_have_enough_information_to_develop_workflow": False,
                    "do_we_have_enough_information_to_design_workflow": False,
                    "do_we_have_enough_information_to_run_workflow": False
                }
                break
        
        # Get user interface response using GPT-4
        user_response = get_user_ineterface_reponse(messages, model_name="gpt-4o")
        print("\nUser Interface Response:", user_response)
        
        # Push user interface response as text
        push_message(
            chat_id=chat_id,
            text_content=user_response,
            message_type="simple_text"
        )
        
        return {
            "status": "success",
            "next_agent": next_agent_result
        }
        
    except Exception as e:
        error_msg = f"Error processing user query: {str(e)}"
        print("\nError:", error_msg)
        push_message(
            chat_id=chat_id,
            text_content=error_msg,
            message_type="simple_text"
        )
        return {
            "status": "error",
            "error": error_msg
        } 