import uuid
from typing import List, Dict, Any, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity_graph import Entity, EntityRelationship, NarrativeEvent
from app.core.logging import logger


class EntityRetriever:
    """
    Bounded Relational Graph Retriever for Narrative Intelligence.
    Executes 1-hop, 2-hop, 3-hop entity & event graph traversals with Spoiler Protection.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_matching_entities(
        self,
        document_id: uuid.UUID,
        query: str,
        max_page: Optional[int] = None
    ) -> List[Entity]:
        """Match query terms against canonical entity names and aliases with spoiler safety."""
        q_lower = query.lower()
        stmt = select(Entity).where(Entity.document_id == document_id)
        if max_page is not None:
            stmt = stmt.where((Entity.first_appeared_page == None) | (Entity.first_appeared_page <= max_page))
        res = await self.db.execute(stmt)
        entities = list(res.scalars().all())

        matched = []
        q_tokens = [t for t in q_lower.split() if len(t) >= 3]
        for e in entities:
            c_name = e.name.lower()
            aliases = [a.lower() for a in e.attributes.get("aliases", [])] if e.attributes else []
            
            # Exact or substring match (either direction) or token overlap match
            is_match = (
                c_name in q_lower or q_lower in c_name
                or any(t in c_name for t in q_tokens)
                or any(a in q_lower or q_lower in a for a in aliases if len(a) > 2)
            )
            if is_match:
                matched.append(e)

        return matched

    async def get_bounded_subgraph(
        self,
        document_id: uuid.UUID,
        query: str,
        max_hops: int = 2,
        max_page: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Perform bounded 1-hop / 2-hop graph traversal starting from matched query entities.
        Applies Spoiler Protection if max_page is specified.
        """
        matched_entities = await self.find_matching_entities(document_id, query, max_page=max_page)
        if not matched_entities:
            return {"entities": [], "relationships": [], "events": []}

        visited_entity_ids: Set[uuid.UUID] = {e.id for e in matched_entities}
        visited_entity_names: Set[str] = {e.name for e in matched_entities}
        frontier_ids = set(visited_entity_ids)

        relationships_found: List[Dict[str, Any]] = []
        seen_relationship_ids: Set[str] = set()

        # 1-hop and 2-hop relationship expansion
        for hop in range(min(max_hops, 3)):
            if not frontier_ids:
                break

            rel_query = select(EntityRelationship).where(
                EntityRelationship.document_id == document_id,
                (EntityRelationship.source_entity_id.in_(frontier_ids)) | (EntityRelationship.target_entity_id.in_(frontier_ids))
            )
            if max_page is not None:
                rel_query = rel_query.where(
                    (EntityRelationship.observed_page == None) | (EntityRelationship.observed_page <= max_page)
                )

            res = await self.db.execute(rel_query)
            rels = list(res.scalars().all())

            next_frontier = set()
            for r in rels:
                r_id_str = str(r.id)
                src_id = r.source_entity_id
                tgt_id = r.target_entity_id

                if r_id_str not in seen_relationship_ids:
                    seen_relationship_ids.add(r_id_str)
                    relationships_found.append({
                        "id": r_id_str,
                        "source_entity_id": str(src_id),
                        "target_entity_id": str(tgt_id),
                        "relationship_type": r.relationship_type,
                        "description": r.description,
                        "observed_page": r.observed_page
                    })

                if src_id not in visited_entity_ids:
                    next_frontier.add(src_id)
                    visited_entity_ids.add(src_id)
                if tgt_id not in visited_entity_ids:
                    next_frontier.add(tgt_id)
                    visited_entity_ids.add(tgt_id)

            frontier_ids = next_frontier

        # Fetch full Entity objects for all visited entity IDs
        ent_res = await self.db.execute(
            select(Entity).where(Entity.id.in_(visited_entity_ids))
        )
        all_entities = list(ent_res.scalars().all())
        entity_map = {e.id: e for e in all_entities}
        visited_entity_names = {e.name for e in all_entities}

        # Enrich relationship records with canonical entity names
        enriched_relationships = []
        for r in relationships_found:
            src_entity = entity_map.get(uuid.UUID(r["source_entity_id"]))
            tgt_entity = entity_map.get(uuid.UUID(r["target_entity_id"]))
            r["source_entity_name"] = src_entity.name if src_entity else "Entity"
            r["target_entity_name"] = tgt_entity.name if tgt_entity else "Entity"
            enriched_relationships.append(r)

        # Fetch Narrative Events involving visited entities
        evt_query = select(NarrativeEvent).where(NarrativeEvent.document_id == document_id)
        if max_page is not None:
            evt_query = evt_query.where(NarrativeEvent.page_number <= max_page)
        evt_query = evt_query.order_by(NarrativeEvent.page_number.asc())

        evt_res = await self.db.execute(evt_query)
        all_events = list(evt_res.scalars().all())

        matching_events = []
        for ev in all_events:
            parts = ev.participants_json.get("participants", []) if ev.participants_json else []
            if any(p in visited_entity_names for p in parts):
                matching_events.append({
                    "id": str(ev.id),
                    "title": ev.title,
                    "event_type": ev.event_type,
                    "description": ev.description,
                    "page_number": ev.page_number,
                    "participants": parts,
                    "location_name": ev.location_name
                })

        return {
            "entities": [
                {
                    "id": str(e.id),
                    "name": e.name,
                    "entity_type": e.entity_type,
                    "description": e.description,
                    "first_appeared_page": e.first_appeared_page,
                    "aliases": e.attributes.get("aliases", []) if e.attributes else [],
                    "importance": e.attributes.get("importance", "minor") if e.attributes else "minor"
                }
                for e in all_entities
            ],
            "relationships": enriched_relationships,
            "events": matching_events
        }

    async def get_character_profile(
        self,
        document_id: uuid.UUID,
        entity_id_or_name: str,
        max_page: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Build detailed character profile, aliases, relationship web, and event timeline."""
        query = select(Entity).where(Entity.document_id == document_id)
        try:
            e_uuid = uuid.UUID(entity_id_or_name)
            query = query.where(Entity.id == e_uuid)
        except ValueError:
            query = query.where(Entity.name.ilike(entity_id_or_name))

        res = await self.db.execute(query)
        entity = res.scalars().first()
        if not entity:
            return None

        subgraph = await self.get_bounded_subgraph(
            document_id=document_id,
            query=entity.name,
            max_hops=2,
            max_page=max_page
        )

        return {
            "entity": {
                "id": str(entity.id),
                "name": entity.name,
                "entity_type": entity.entity_type,
                "description": entity.description,
                "first_appeared_page": entity.first_appeared_page,
                "attributes": entity.attributes
            },
            "relationships": subgraph["relationships"],
            "events": subgraph["events"],
            "subgraph_entities": subgraph["entities"]
        }
