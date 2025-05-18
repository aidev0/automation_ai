from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId
from .schema import Workflow, Agent, WorkflowDesign, WorkflowNode, AgentDesign
from .mongodb import get_db, WORKFLOWS_COLLECTION, AGENTS_COLLECTION

class WorkflowModel:
    """Model for workflow operations"""
    
    @staticmethod
    def get(workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID"""
        try:
            db = get_db()
            workflow = db[WORKFLOWS_COLLECTION].find_one({"_id": ObjectId(workflow_id)})
            return Workflow(**workflow) if workflow else None
        except PyMongoError as e:
            raise Exception(f"Error getting workflow: {str(e)}")

    @staticmethod
    def get_by_chat(chat_id: str) -> List[Workflow]:
        """Get all workflows for a chat"""
        try:
            db = get_db()
            workflows = db[WORKFLOWS_COLLECTION].find({"chat_id": chat_id})
            return [Workflow(**w) for w in workflows]
        except PyMongoError as e:
            raise Exception(f"Error getting workflows for chat: {str(e)}")

    @staticmethod
    def create(workflow_data: Dict[str, Any]) -> str:
        """Create a new workflow"""
        try:
            workflow = Workflow(**workflow_data)
            db = get_db()
            result = db[WORKFLOWS_COLLECTION].insert_one(workflow.dict())
            return str(result.inserted_id)
        except PyMongoError as e:
            raise Exception(f"Error creating workflow: {str(e)}")

    @staticmethod
    def update(workflow_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a workflow"""
        try:
            db = get_db()
            update_data["updated_at"] = datetime.utcnow()
            result = db[WORKFLOWS_COLLECTION].update_one(
                {"_id": ObjectId(workflow_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except PyMongoError as e:
            raise Exception(f"Error updating workflow: {str(e)}")

    @staticmethod
    def delete(workflow_id: str) -> bool:
        """Delete a workflow and its associated agents"""
        try:
            db = get_db()
            # Delete associated agents first
            db[AGENTS_COLLECTION].delete_many({"workflow_id": workflow_id})
            # Then delete the workflow
            result = db[WORKFLOWS_COLLECTION].delete_one({"_id": ObjectId(workflow_id)})
            return result.deleted_count > 0
        except PyMongoError as e:
            raise Exception(f"Error deleting workflow: {str(e)}")

    @staticmethod
    def push_node(workflow_id: str, node: WorkflowNode) -> bool:
        """Add a new node to workflow design"""
        try:
            db = get_db()
            result = db[WORKFLOWS_COLLECTION].update_one(
                {"_id": ObjectId(workflow_id)},
                {
                    "$push": {"workflow_design.nodes": node.dict()},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except PyMongoError as e:
            raise Exception(f"Error adding node to workflow: {str(e)}")

    @staticmethod
    def push_agent(workflow_id: str, agent: Agent) -> bool:
        """Add a new agent to workflow"""
        try:
            db = get_db()
            result = db[WORKFLOWS_COLLECTION].update_one(
                {"_id": ObjectId(workflow_id)},
                {
                    "$push": {"agents": agent.dict()},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except PyMongoError as e:
            raise Exception(f"Error adding agent to workflow: {str(e)}")

    @staticmethod
    def get_all() -> List[Workflow]:
        """Get all workflows"""
        try:
            db = get_db()
            workflows = db[WORKFLOWS_COLLECTION].find()
            return [Workflow(**w) for w in workflows]
        except PyMongoError as e:
            raise Exception(f"Error getting all workflows: {str(e)}")

    @staticmethod
    def get_all_agents() -> List[Agent]:
        """Get all agents across all workflows"""
        try:
            db = get_db()
            agents = db[AGENTS_COLLECTION].find()
            return [Agent(**a) for a in agents]
        except PyMongoError as e:
            raise Exception(f"Error getting all agents: {str(e)}")

    @staticmethod
    def get_all_workflows() -> List[Dict[str, Any]]:
        """Get all workflows with their agents and nodes"""
        try:
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
        except PyMongoError as e:
            raise Exception(f"Error getting all workflows: {str(e)}")

class AgentModel:
    """Model for agent operations"""
    
    @staticmethod
    def get(agent_id: str) -> Optional[Agent]:
        """Get an agent by ID"""
        try:
            db = get_db()
            agent = db[AGENTS_COLLECTION].find_one({"_id": ObjectId(agent_id)})
            return Agent(**agent) if agent else None
        except PyMongoError as e:
            raise Exception(f"Error getting agent: {str(e)}")

    @staticmethod
    def get_by_workflow(workflow_id: str) -> List[Agent]:
        """Get all agents for a workflow"""
        try:
            db = get_db()
            agents = db[AGENTS_COLLECTION].find({"workflow_id": workflow_id})
            return [Agent(**a) for a in agents]
        except PyMongoError as e:
            raise Exception(f"Error getting agents for workflow: {str(e)}")

    @staticmethod
    def create(agent_data: Dict[str, Any]) -> str:
        """Create a new agent"""
        try:
            agent = Agent(**agent_data)
            db = get_db()
            result = db[AGENTS_COLLECTION].insert_one(agent.dict())
            return str(result.inserted_id)
        except PyMongoError as e:
            raise Exception(f"Error creating agent: {str(e)}")

    @staticmethod
    def update(agent_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an agent"""
        try:
            db = get_db()
            update_data["updated_at"] = datetime.utcnow()
            result = db[AGENTS_COLLECTION].update_one(
                {"_id": ObjectId(agent_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except PyMongoError as e:
            raise Exception(f"Error updating agent: {str(e)}")

    @staticmethod
    def delete(agent_id: str) -> bool:
        """Delete an agent"""
        try:
            db = get_db()
            result = db[AGENTS_COLLECTION].delete_one({"_id": ObjectId(agent_id)})
            return result.deleted_count > 0
        except PyMongoError as e:
            raise Exception(f"Error deleting agent: {str(e)}")

    @staticmethod
    def push_requirement(agent_id: str, requirement: str) -> bool:
        """Add a requirement to agent's requirements.txt"""
        try:
            db = get_db()
            result = db[AGENTS_COLLECTION].update_one(
                {"_id": ObjectId(agent_id)},
                {
                    "$push": {"requirements": requirement},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except PyMongoError as e:
            raise Exception(f"Error adding requirement to agent: {str(e)}")

    @staticmethod
    def get_all() -> List[Agent]:
        """Get all agents"""
        try:
            db = get_db()
            agents = db[AGENTS_COLLECTION].find()
            return [Agent(**a) for a in agents]
        except PyMongoError as e:
            raise Exception(f"Error getting all agents: {str(e)}") 