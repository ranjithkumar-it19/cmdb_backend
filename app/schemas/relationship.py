from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class RelationshipCreate(BaseModel):
    source_asset_id: str
    target_asset_id: str
    relationship_type: str = Field(description="runs_on, hosted_on, connects_to, depends_on, managed_by, member_of, communicates_with")
    confidence: float = 1.0


class RelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_asset_id: str
    target_asset_id: str
    relationship_type: str
    source: str
    confidence: float
    is_active: bool
    valid_from: datetime
    valid_to: Optional[datetime] = None
    created_at: datetime


class RelationshipGraphNode(BaseModel):
    id: str
    label: str
    type: str
    status: str
    ip: Optional[str] = None


class RelationshipGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str
    confidence: float


class RelationshipGraphResponse(BaseModel):
    nodes: List[RelationshipGraphNode]
    edges: List[RelationshipGraphEdge]
