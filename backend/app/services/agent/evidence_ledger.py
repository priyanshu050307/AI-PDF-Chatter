import uuid
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field


@dataclass
class EvidenceRecord:
    evidence_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_type: str = "chunk"  # chunk, page, entity, relationship, event, annotation
    source_id: str = ""
    document_id: str = ""
    page_number: int = 1
    title: Optional[str] = None
    content: str = ""
    provenance: Optional[Dict[str, Any]] = None
    retrieval_method: str = "tool_call"


class EvidenceLedger:
    """
    Structured Evidence Ledger for Agentic Reasoning.
    Collects, deduplicates, and formats evidence records gathered during agentic investigation steps.
    """

    def __init__(self):
        self.records: List[EvidenceRecord] = []
        self._seen_source_ids: Set[str] = set()

    def add_record(self, record: EvidenceRecord) -> bool:
        """Add record with strict source_id deduplication."""
        dedup_key = f"{record.source_type}:{record.source_id or record.evidence_id}"
        if dedup_key in self._seen_source_ids:
            return False
        self._seen_source_ids.add(dedup_key)
        self.records.append(record)
        return True

    def add_from_tool_output(self, tool_name: str, doc_id: str, output: Dict[str, Any]) -> int:
        """Extract evidence records from tool execution output."""
        added_count = 0

        if tool_name == "search_evidence":
            for ev in output.get("evidence", []):
                rec = EvidenceRecord(
                    source_type="chunk",
                    source_id=ev.get("chunk_id", ""),
                    document_id=doc_id,
                    page_number=ev.get("page_start", 1),
                    title=f"Chunk (Page {ev.get('page_start')})",
                    content=ev.get("content", ""),
                    provenance={
                        "chapter": ev.get("chapter_title"),
                        "section": ev.get("section_title"),
                        "element_type": ev.get("element_type", "text"),
                        "score": ev.get("score")
                    },
                    retrieval_method="hybrid_search"
                )
                if self.add_record(rec):
                    added_count += 1

        elif tool_name == "search_document":
            for m in output.get("matches", []):
                rec = EvidenceRecord(
                    source_type="chunk",
                    source_id=m.get("chunk_id", ""),
                    document_id=doc_id,
                    page_number=m.get("page_number", 1),
                    title=f"Direct Search Match (Page {m.get('page_number')})",
                    content=m.get("content_snippet", ""),
                    retrieval_method="keyword_search"
                )
                if self.add_record(rec):
                    added_count += 1

        elif tool_name == "get_page":
            if output.get("found") and output.get("content"):
                rec = EvidenceRecord(
                    source_type="page",
                    source_id=f"page:{output.get('page_number')}",
                    document_id=doc_id,
                    page_number=output.get("page_number", 1),
                    title=f"Page {output.get('page_number')} Content",
                    content=output.get("content", "")[:2000],
                    retrieval_method="get_page"
                )
                if self.add_record(rec):
                    added_count += 1

        elif tool_name in ["find_entity", "get_entity_profile"]:
            profile = output.get("profile")
            if profile and profile.get("entity"):
                e = profile["entity"]
                rec = EvidenceRecord(
                    source_type="entity",
                    source_id=e.get("id", ""),
                    document_id=doc_id,
                    page_number=e.get("first_appeared_page", 1),
                    title=f"Character Profile: {e.get('name')}",
                    content=f"Entity: {e.get('name')} ({e.get('entity_type')}). {e.get('description', '')}",
                    retrieval_method="entity_profile"
                )
                if self.add_record(rec):
                    added_count += 1

        elif tool_name in ["find_relationships", "get_character_timeline", "find_events"]:
            for r in output.get("relationships", []):
                rec = EvidenceRecord(
                    source_type="relationship",
                    source_id=r.get("id", ""),
                    document_id=doc_id,
                    page_number=r.get("observed_page", 1),
                    title=f"Relationship (Page {r.get('observed_page')})",
                    content=f"{r.get('source_entity_name')} {r.get('relationship_type')} {r.get('target_entity_name')}: {r.get('description', '')}",
                    retrieval_method="relationship_graph"
                )
                if self.add_record(rec):
                    added_count += 1

            for ev in output.get("events", []):
                rec = EvidenceRecord(
                    source_type="event",
                    source_id=ev.get("event_id", ev.get("id", "")),
                    document_id=doc_id,
                    page_number=ev.get("page_number", 1),
                    title=f"Event: {ev.get('title')}",
                    content=f"Page {ev.get('page_number')} [{ev.get('event_type')}]: {ev.get('description')}",
                    retrieval_method="event_timeline"
                )
                if self.add_record(rec):
                    added_count += 1

        elif tool_name == "get_my_annotations":
            for ann in output.get("annotations", []):
                rec = EvidenceRecord(
                    source_type="annotation",
                    source_id=ann.get("annotation_id", ""),
                    document_id=doc_id,
                    page_number=ann.get("page_number", 1),
                    title=f"User Note (Page {ann.get('page_number')})",
                    content=f"Highlight: \"{ann.get('selected_text')}\" | Note: \"{ann.get('note_text', '')}\"",
                    retrieval_method="user_annotations"
                )
                if self.add_record(rec):
                    added_count += 1

        elif tool_name == "compare_entities":
            if output.get("entity_a") and output.get("entity_b"):
                ea = output["entity_a"]
                eb = output["entity_b"]
                rec = EvidenceRecord(
                    source_type="entity",
                    source_id=f"compare:{ea.get('id')}:{eb.get('id')}",
                    document_id=doc_id,
                    page_number=ea.get("first_appeared_page", 1),
                    title=f"Comparison: {ea.get('name')} vs {eb.get('name')}",
                    content=f"Entity A: {ea.get('name')} ({ea.get('description')})\nEntity B: {eb.get('name')} ({eb.get('description')})",
                    retrieval_method="entity_comparison"
                )
                if self.add_record(rec):
                    added_count += 1

        return added_count

    def to_chunks_format(self) -> List[Dict[str, Any]]:
        """Format deduplicated evidence records as retrieved_chunks for ContextBuilder."""
        formatted = []
        for r in self.records:
            formatted.append({
                "chunk_id": r.source_id or r.evidence_id,
                "page_start": r.page_number,
                "page_end": r.page_number,
                "content": r.content,
                "chapter_title": (r.provenance or {}).get("chapter"),
                "section_title": (r.provenance or {}).get("section"),
                "score": (r.provenance or {}).get("score", 1.0),
                "metadata_json": {
                    "element_type": (r.provenance or {}).get("element_type", "text"),
                    "source_type": r.source_type,
                    "retrieval_method": r.retrieval_method
                }
            })
        return formatted
