from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.relationship import AssetRelationship
from app.models.asset import Asset
from app.schemas.relationship import RelationshipCreate, RelationshipGraphResponse, RelationshipGraphNode, RelationshipGraphEdge


class RelationshipService:
    @staticmethod
    def create_relationship(db: Session, rel_in: RelationshipCreate, source: str = "manual") -> AssetRelationship:
        if rel_in.source_asset_id == rel_in.target_asset_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Self-referential relationships are not permitted")

        src = db.query(Asset).filter(Asset.id == rel_in.source_asset_id).first()
        tgt = db.query(Asset).filter(Asset.id == rel_in.target_asset_id).first()
        if not src or not tgt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source or target asset not found")

        rel = AssetRelationship(
            source_asset_id=rel_in.source_asset_id,
            target_asset_id=rel_in.target_asset_id,
            relationship_type=rel_in.relationship_type,
            source=source,
            confidence=rel_in.confidence,
        )
        db.add(rel)
        db.commit()
        db.refresh(rel)
        return rel

    @staticmethod
    def list_relationships(db: Session) -> List[AssetRelationship]:
        return db.query(AssetRelationship).filter(AssetRelationship.is_active == True).all()

    @staticmethod
    def infer_topology(db: Session) -> int:
        from app.relationships.engine import TopologyEngine
        return TopologyEngine.infer_and_sync_relationships(db)

    @staticmethod
    def get_relationship_graph(db: Session) -> RelationshipGraphResponse:
        relationships = db.query(AssetRelationship).filter(AssetRelationship.is_active == True).all()
        assets = db.query(Asset).all()

        if not relationships and len(assets) >= 2:
            from app.relationships.engine import TopologyEngine
            TopologyEngine.infer_and_sync_relationships(db)
            relationships = db.query(AssetRelationship).filter(AssetRelationship.is_active == True).all()

        nodes = [
            RelationshipGraphNode(
                id=a.id,
                label=a.display_name,
                type=a.asset_type,
                status=a.status,
                ip=a.primary_ip,
            )
            for a in assets
        ]

        edges = [
            RelationshipGraphEdge(
                id=r.id,
                source=r.source_asset_id,
                target=r.target_asset_id,
                type=r.relationship_type,
                confidence=r.confidence,
            )
            for r in relationships
        ]

        return RelationshipGraphResponse(nodes=nodes, edges=edges)
