import os
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from datetime import datetime, UTC
from .schema import Workflow, Agent, WORKFLOWS_COLLECTION, AGENTS_COLLECTION

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE")

def get_client() -> MongoClient:
    """Get MongoDB client."""
    return MongoClient(MONGODB_URI)

def get_db():
    """Get database instance."""
    client = get_client()
    return client[MONGODB_DATABASE]

# Workflow operations
def create_workflow(workflow: Workflow) -> str:
    """Create a new workflow."""
    db = get_db()
    result = db[WORKFLOWS_COLLECTION].insert_one(workflow.model_dump())
    return str(result.inserted_id)

def get_workflow(workflow_id: str) -> Optional[Workflow]:
    """Get a workflow by ID."""
    db = get_db()
    workflow = db[WORKFLOWS_COLLECTION].find_one({"_id": workflow_id})
    return Workflow(**workflow) if workflow else None

def get_workflows_by_chat(chat_id: str) -> List[Workflow]:
    """Get all workflows for a chat."""
    db = get_db()
    workflows = db[WORKFLOWS_COLLECTION].find({"chat_id": chat_id})
    return [Workflow(**w) for w in workflows]

def update_workflow(workflow_id: str, update_data: Dict[str, Any]) -> bool:
    """Update a workflow."""
    db = get_db()
    update_data["updated_at"] = datetime.utcnow()
    result = db[WORKFLOWS_COLLECTION].update_one(
        {"_id": workflow_id},
        {"$set": update_data}
    )
    return result.modified_count > 0

def delete_workflow(workflow_id: str) -> bool:
    """Delete a workflow and its associated agents."""
    db = get_db()
    # Delete associated agents first
    db[AGENTS_COLLECTION].delete_many({"workflow_id": workflow_id})
    # Then delete the workflow
    result = db[WORKFLOWS_COLLECTION].delete_one({"_id": workflow_id})
    return result.deleted_count > 0

# Agent operations
def create_agent(agent: Agent) -> str:
    """Create a new agent."""
    db = get_db()
    result = db[AGENTS_COLLECTION].insert_one(agent.model_dump())
    return str(result.inserted_id)

def get_agent(agent_id: str) -> Optional[Agent]:
    """Get an agent by ID."""
    db = get_db()
    agent = db[AGENTS_COLLECTION].find_one({"_id": agent_id})
    return Agent(**agent) if agent else None

def get_agents_by_workflow(workflow_id: str) -> List[Agent]:
    """Get all agents for a workflow."""
    db = get_db()
    agents = db[AGENTS_COLLECTION].find({"workflow_id": workflow_id})
    return [Agent(**a) for a in agents]

def update_agent(agent_id: str, update_data: Dict[str, Any]) -> bool:
    """Update an agent."""
    db = get_db()
    update_data["updated_at"] = datetime.utcnow()
    result = db[AGENTS_COLLECTION].update_one(
        {"_id": agent_id},
        {"$set": update_data}
    )
    return result.modified_count > 0

def delete_agent(agent_id: str) -> bool:
    """Delete an agent."""
    db = get_db()
    result = db[AGENTS_COLLECTION].delete_one({"_id": agent_id})
    return result.deleted_count > 0

def create_agents(workflow_id: str, agent_designs: List[Dict[str, Any]]) -> List[str]:
    """Create multiple agents for a workflow"""
    db = get_db()
    agent_ids = []
    
    for design in agent_designs:
        agent = {
            "workflow_id": workflow_id,
            "agent_design": design,
            "db": {},
            "src": "",
            "cmd": "",
            "readme": "",
            "requirements": "",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }
        result = db[AGENTS_COLLECTION].insert_one(agent)
        agent_ids.append(str(result.inserted_id))
    
    return agent_ids

# Existing functions
def get_all_users() -> List[Dict[str, Any]]:
    """Get all users."""
    db = get_db()
    return list(db.users.find())

def get_all_chats(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all chats, optionally filtered by user_id."""
    db = get_db()
    query = {"user_id": user_id} if user_id else {}
    return list(db.chats.find(query))

def get_all_messages(chat_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all messages, optionally filtered by chatId."""
    db = get_db()
    query = {"chatId": chat_id} if chat_id else {}
    return list(db.messages.find(query))

def get_all_workflows() -> List[Dict[str, Any]]:
    """Get all workflows with their agents and nodes"""
    db = get_db()
    workflows = list(db[WORKFLOWS_COLLECTION].find())
    agents = list(db[AGENTS_COLLECTION].find())
    
    # Group agents by workflow_id
    agents_by_workflow = {}
    for agent in agents:
        workflow_id = agent["workflow_id"]
        if workflow_id not in agents_by_workflow:
            agents_by_workflow[workflow_id] = []
        agents_by_workflow[workflow_id].append(agent)
    
    # Add agents to each workflow
    for workflow in workflows:
        workflow_id = str(workflow["_id"])
        workflow["agents"] = agents_by_workflow.get(workflow_id, [])
    
    return workflows 