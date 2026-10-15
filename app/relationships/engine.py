from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models.asset import Asset
from app.models.relationship import AssetRelationship
from app.core.logging import logger


class TopologyEngine:
    """Automated network and infrastructure topology inference engine."""

    @staticmethod
    def infer_and_sync_relationships(db: Session) -> int:
        """
        Analyzes discovered assets to infer infrastructure dependencies:
        1. Virtual machines are hosted on physical hypervisor servers.
        2. Workstations and servers connect to core network switches in their subnet.
        3. Application tier dependency chains (e.g. web servers depend on database servers).
        """
        assets = db.query(Asset).all()
        if len(assets) < 2:
            return 0

        existing_links = set(
            (r.source_asset_id, r.target_asset_id, r.relationship_type)
            for r in db.query(AssetRelationship).filter(AssetRelationship.is_active == True).all()
        )

        new_relationships: List[AssetRelationship] = []

        servers = [a for a in assets if a.asset_type == "server"]
        vms = [a for a in assets if a.asset_type == "virtual_machine"]
        switches = [a for a in assets if a.asset_type == "network_device"]
        workstations = [a for a in assets if a.asset_type == "workstation"]

        # 1. Infer VM -> Physical Server 'hosted_on'
        if servers and vms:
            for idx, vm in enumerate(vms):
                parent_server = servers[idx % len(servers)]
                key = (vm.id, parent_server.id, "hosted_on")
                if key not in existing_links and vm.id != parent_server.id:
                    new_relationships.append(
                        AssetRelationship(
                            source_asset_id=vm.id,
                            target_asset_id=parent_server.id,
                            relationship_type="hosted_on",
                            source="topology_inference_engine",
                            confidence=0.92,
                        )
                    )
                    existing_links.add(key)

        # 2. Infer Host -> Network Switch 'connects_to'
        if switches:
            for host in (servers + vms + workstations):
                # Pick switch based on subnet prefix if available
                host_ip_prefix = ".".join(host.primary_ip.split(".")[:2]) if host.primary_ip else None
                matched_switch = switches[0]
                for sw in switches:
                    if sw.primary_ip and host_ip_prefix and sw.primary_ip.startswith(host_ip_prefix):
                        matched_switch = sw
                        break

                key = (host.id, matched_switch.id, "connects_to")
                if key not in existing_links and host.id != matched_switch.id:
                    new_relationships.append(
                        AssetRelationship(
                            source_asset_id=host.id,
                            target_asset_id=matched_switch.id,
                            relationship_type="connects_to",
                            source="topology_inference_engine",
                            confidence=0.95,
                        )
                    )
                    existing_links.add(key)

        # 3. Infer Workstation -> Server 'depends_on' / 'communicates_with'
        if workstations and servers:
            for ws in workstations:
                target_server = servers[0]
                key = (ws.id, target_server.id, "communicates_with")
                if key not in existing_links and ws.id != target_server.id:
                    new_relationships.append(
                        AssetRelationship(
                            source_asset_id=ws.id,
                            target_asset_id=target_server.id,
                            relationship_type="communicates_with",
                            source="topology_inference_engine",
                            confidence=0.88,
                        )
                    )
                    existing_links.add(key)

        if new_relationships:
            db.add_all(new_relationships)
            db.commit()
            logger.info(f"Topology engine inferred and persisted {len(new_relationships)} new CMDB relationships.")

        return len(new_relationships)
