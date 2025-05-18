from typing import List, Dict, Any, Optional, Union
from datetime import datetime, UTC
from pydantic import BaseModel, Field

class AgentDesign(BaseModel):
    """Schema for agent design"""
    label: str
    description: str
    integrations: List[str]
    input_schema_description: str
    output_schema_description: str

class Agent(BaseModel):
    """Schema for an agent"""
    _id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    name: str
    description: str
    task: str
    integrations: List[str]
    user_id: str
    system: str
    model_name: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    readme_md: str
    code: str
    code_language: str
    command: str
    env_list: List[str]

class WorkflowNode(BaseModel):
    """Schema for a workflow node - represents an agent at a specific version"""
    agent_id: str
    order: int

class WorkflowEdge(BaseModel):
    source: str  # agent_id
    target: str  # agent_id

class Workflow(BaseModel):
    """Schema for a workflow"""
    _id: str
    chat_id: str
    name: str
    description: str
    type: str = Field(..., pattern="^(graph|tree)$")
    nodes: Optional[List[WorkflowNode]] = None  # For graph type
    edges: Optional[List[WorkflowEdge]] = None  # For graph type
    nodes_list: Optional[List[str]] = None  # For tree type
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    env_list: List[str]
    integrations: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        validate_assignment = True

    def validate_type_fields(self):
        if self.type == "graph":
            if not self.nodes or not self.edges:
                raise ValueError("Graph workflow must have nodes and edges")
            if self.nodes_list:
                raise ValueError("Graph workflow cannot have nodes_list")
        elif self.type == "tree":
            if not self.nodes_list:
                raise ValueError("Tree workflow must have nodes_list")
            if self.nodes or self.edges:
                raise ValueError("Tree workflow cannot have nodes or edges")

# MongoDB collection names
WORKFLOWS_COLLECTION = "workflows"
AGENTS_COLLECTION = "agents" 