import re
import uuid
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass, field

from app.core.logging import logger


@dataclass
class ExtractedEntityData:
    canonical_name: str
    entity_type: str  # PERSON, ORGANIZATION, LOCATION, EVENT, CONCEPT
    aliases: List[str] = field(default_factory=list)
    description: Optional[str] = None
    first_appeared_page: int = 1
    last_appeared_page: int = 1
    mention_count: int = 1
    importance: str = "minor"  # major, minor, background


@dataclass
class ExtractedRelationshipData:
    source_name: str
    target_name: str
    relationship_type: str  # trusts, distrusts, knows, enemy_of, friend_of, works_for, family_with
    description: str
    observed_page: int
    evidence_text: Optional[str] = None


@dataclass
class ExtractedEventData:
    title: str
    event_type: str  # meeting, conflict, discovery, betrayal, revelation, decision, departure, death, major_interaction
    description: str
    page_number: int
    participants: List[str]
    location_name: Optional[str] = None
    evidence_text: Optional[str] = None


class NarrativeExtractor:
    """
    High-performance, deterministic NLP Narrative Extractor.
    Extracts Characters, Entities, Aliases, Coreferences, Relationships, and Narrative Events
    with zero LLM overhead during document ingestion.
    """

    RELATIONSHIP_KEYWORDS = {
        "trusts": ["trusted", "trusts", "relied on", "confided in"],
        "distrusts": ["distrusted", "distrusts", "suspected", "doubted", "feared"],
        "enemy_of": ["enemy", "hated", "fought against", "opposed", "rival"],
        "friend_of": ["friend", "befriended", "ally", "companions"],
        "works_for": ["worked for", "employed by", "served", "assistant to"],
        "family_with": ["brother", "sister", "father", "mother", "son", "daughter", "husband", "wife", "married"],
        "knows": ["met", "knew", "introduced to", "spoke with", "encountered", "confronted"]
    }

    EVENT_KEYWORDS = {
        "meeting": ["met", "encountered", "gathered", "assembled", "conference", "dialogue", "talk"],
        "conflict": ["fought", "attacked", "argued", "confronted", "clashed", "objected"],
        "discovery": ["discovered", "found", "uncovered", "revealed", "noticed", "searched"],
        "betrayal": ["betrayed", "deceived", "double-crossed", "tricked", "stole"],
        "decision": ["decided", "resolved", "agreed", "chose", "determined", "decision"],
        "departure": ["departed", "left", "fled", "escaped", "embarked", "sailed"],
        "revelation": ["disclosed", "confessed", "announced", "admitted", "exposed"],
        "death": ["died", "killed", "murdered", "passed away", "slain", "perished"],
        "major_interaction": ["confronted", "negotiated", "signed", "warned", "demanded"]
    }

    TITLES = {"mr.", "mrs.", "ms.", "dr.", "prof.", "inspector", "detective", "lord", "lady", "sir", "captain"}
    GENERATIONAL_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v", "esq", "esq."}

    PRONOUNS_MALE = {"he", "him", "his", "himself"}
    PRONOUNS_FEMALE = {"she", "her", "hers", "herself"}

    FEMALE_INDICATORS = {"lady", "mrs.", "ms.", "eleanor", "alice", "mary", "elizabeth", "sarah", "jane", "clara"}
    MALE_INDICATORS = {"lord", "mr.", "sir", "captain", "inspector", "detective", "edward", "robert", "john", "thomas", "bob", "arthur", "henry", "james"}

    NON_NAME_STOPWORDS = {
        "welcome", "thank", "thanks", "chapter", "section", "paragraph", "table", "figure",
        "page", "note", "author", "flashback", "meanwhile", "suddenly", "shortly", "later",
        "finally", "first", "second", "third", "fourth", "fifth", "however", "therefore",
        "gathering", "beginning", "suspicions", "conflict", "climax", "revelation", "discovery",
        "decision", "departure", "death", "present", "twenty", "critical", "secretly",
        "the", "in", "at", "on", "he", "she", "it", "they", "we", "you", "i", "his", "her",
        "my", "your", "their", "our", "this", "that", "these", "those", "when", "where",
        "why", "how", "what", "who", "whom", "whose", "which", "there", "here", "now", "then"
    }

    def _infer_gender(self, name: str) -> str:
        """Infer gender category for coreference resolution."""
        tokens = [t.lower() for t in name.split()]
        if any(t in self.FEMALE_INDICATORS for t in tokens):
            return "female"
        if any(t in self.MALE_INDICATORS for t in tokens):
            return "male"
        return "unknown"

    def extract_entities_and_relationships(
        self,
        pages_content: List[Tuple[int, str]]  # List of (page_number, text)
    ) -> Tuple[List[ExtractedEntityData], List[ExtractedRelationshipData], List[ExtractedEventData]]:
        
        name_mentions: Dict[str, List[int]] = {}
        alias_map: Dict[str, str] = {}
        relationships: List[ExtractedRelationshipData] = []
        events: List[ExtractedEventData] = []

        person_pattern = re.compile(
            r"\b(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.|Inspector|Detective|Lord|Lady|Sir|Captain)?\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Jr\.|Sr\.|II|III|IV|esq)\.?)?"
        )
        location_keywords = {"london", "paris", "castle", "library", "manor", "city", "river", "house", "room", "station", "office", "docks", "estate"}

        detected_locations: Set[str] = set()

        for page_num, text in pages_content:
            lines = text.splitlines()

            # Active context window for coreference tracking: stores recent (name, gender)
            recent_context_entities: List[Tuple[str, str]] = []

            for line in lines:
                clean_line = line.strip()
                if not clean_line:
                    continue

                sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', clean_line) if s.strip()]

                for sent in sentences:
                    # Scan for Location Mentions
                    for word in sent.split():
                        w_clean = re.sub(r"[^\w]", "", word)
                        if w_clean.lower() in location_keywords and w_clean.istitle():
                            detected_locations.add(w_clean)

                    # Scan for Person Names in sentence
                    sent_persons = []
                    for match in person_pattern.finditer(sent):
                        name = match.group(0).strip()
                        tokens = [t.strip(",.:;!?'\"").lower() for t in name.split()]
                        non_title_tokens = [t for t in tokens if t not in self.TITLES]
                        if not non_title_tokens:
                            continue
                        if any(t in self.NON_NAME_STOPWORDS for t in non_title_tokens):
                            continue
                        if len(name) < 3:
                            continue

                        if name not in name_mentions:
                            name_mentions[name] = []
                        name_mentions[name].append(page_num)
                        sent_persons.append(name)

                        gender = self._infer_gender(name)
                        # Add/update in recent context stack
                        recent_context_entities = [(n, g) for n, g in recent_context_entities if n != name]
                        recent_context_entities.append((name, gender))
                        if len(recent_context_entities) > 5:
                            recent_context_entities.pop(0)

                    # Robust Coreference Resolution with Ambiguity Fallback
                    words_in_sent = sent.lower().split()
                    for w in words_in_sent:
                        w_sub = re.sub(r"[^\w]", "", w)
                        target_gender = None
                        if w_sub in self.PRONOUNS_MALE:
                            target_gender = "male"
                        elif w_sub in self.PRONOUNS_FEMALE:
                            target_gender = "female"

                        if target_gender:
                            # Filter recent entities matching target gender
                            matching_candidates = [n for n, g in recent_context_entities if g == target_gender or g == "unknown"]
                            if len(matching_candidates) == 1:
                                # High confidence resolution
                                resolved_name = matching_candidates[0]
                                name_mentions[resolved_name].append(page_num)
                            # Else: Ambiguous (0 or >1 candidates), safely skip without inventing identity!

                    # Relationship Extraction
                    sent_lower = sent.lower()
                    for rel_type, kw_list in self.RELATIONSHIP_KEYWORDS.items():
                        for kw in kw_list:
                            if kw in sent_lower:
                                found_persons = [p for p in sent_persons if p in name_mentions]
                                if len(found_persons) >= 2:
                                    src, tgt = found_persons[0], found_persons[1]
                                    if src != tgt:
                                        relationships.append(
                                            ExtractedRelationshipData(
                                                source_name=src,
                                                target_name=tgt,
                                                relationship_type=rel_type,
                                                description=f"{src} {kw} {tgt}",
                                                observed_page=page_num,
                                                evidence_text=sent[:200]
                                            )
                                        )
                                        break
                                elif len(found_persons) == 1 and recent_context_entities:
                                    # Relate to most recent contextual entity if distinct
                                    last_name = recent_context_entities[-1][0]
                                    if last_name != found_persons[0]:
                                        relationships.append(
                                            ExtractedRelationshipData(
                                                source_name=last_name,
                                                target_name=found_persons[0],
                                                relationship_type=rel_type,
                                                description=f"{last_name} {kw} {found_persons[0]}",
                                                observed_page=page_num,
                                                evidence_text=sent[:200]
                                            )
                                        )
                                        break

                    # Event Extraction
                    for evt_type, kw_list in self.EVENT_KEYWORDS.items():
                        for kw in kw_list:
                            if kw in sent_lower:
                                found_persons = [p for p in sent_persons if p in name_mentions]
                                if found_persons:
                                    loc_name = next((l for l in detected_locations if l.lower() in sent_lower), None)
                                    events.append(
                                        ExtractedEventData(
                                            title=f"{evt_type.capitalize()}: {sent[:40]}...",
                                            event_type=evt_type,
                                            description=sent[:250],
                                            page_number=page_num,
                                            participants=found_persons,
                                            location_name=loc_name,
                                            evidence_text=sent[:200]
                                        )
                                    )
                                    break

        # 2. Strict Alias Normalization Pass
        canonical_entities: Dict[str, ExtractedEntityData] = {}

        # Helper to extract generational suffix if present
        def get_suffix(n: str) -> Optional[str]:
            parts = n.lower().split()
            if parts and parts[-1] in self.GENERATIONAL_SUFFIXES:
                return parts[-1]
            return None

        sorted_names = sorted(name_mentions.keys(), key=lambda x: len(x), reverse=True)
        for name in sorted_names:
            pages = name_mentions[name]
            count = len(pages)
            first_p = min(pages)
            last_p = max(pages)

            name_suffix = get_suffix(name)

            # Check if this name is an alias of an existing canonical name
            assigned_canonical = None
            for c_name in canonical_entities.keys():
                c_suffix = get_suffix(c_name)

                # Rule 1: Never merge entities with conflicting generational suffixes (e.g. Jr. vs Sr. vs None)
                if name_suffix != c_suffix:
                    continue

                # Rule 2: Check token containment after stripping title words
                c_tokens = set(c_name.lower().split()) - self.TITLES
                n_tokens = set(name.lower().split()) - self.TITLES

                if n_tokens and (n_tokens.issubset(c_tokens) or c_tokens.issubset(n_tokens)):
                    assigned_canonical = c_name
                    break

            if assigned_canonical:
                if name not in canonical_entities[assigned_canonical].aliases:
                    canonical_entities[assigned_canonical].aliases.append(name)
                canonical_entities[assigned_canonical].mention_count += count
                canonical_entities[assigned_canonical].last_appeared_page = max(
                    canonical_entities[assigned_canonical].last_appeared_page, last_p
                )
                alias_map[name] = assigned_canonical
            else:
                c_name = name
                sfx = get_suffix(name)
                if sfx in {"jr", "sr", "esq"} and not c_name.endswith("."):
                    c_name = c_name + "."
                importance = "major" if count >= 4 else ("minor" if count >= 2 else "background")
                canonical_entities[c_name] = ExtractedEntityData(
                    canonical_name=c_name,
                    entity_type="PERSON",
                    aliases=[name, c_name],
                    description=f"Character appearing on pages {first_p}–{last_p}.",
                    first_appeared_page=first_p,
                    last_appeared_page=last_p,
                    mention_count=count,
                    importance=importance
                )
                alias_map[name] = c_name

        # Add Location Entities (deduplicated against existing canonical entity names)
        existing_names_lower = {c.lower() for c in canonical_entities.keys()}
        for loc in detected_locations:
            loc_lower = loc.lower()
            if any(loc_lower in ex for ex in existing_names_lower if len(ex) > len(loc_lower)):
                continue
            if loc not in canonical_entities:
                canonical_entities[loc] = ExtractedEntityData(
                    canonical_name=loc,
                    entity_type="LOCATION",
                    aliases=[loc],
                    description=f"Location mentioned in document.",
                    first_appeared_page=1,
                    last_appeared_page=1,
                    mention_count=1,
                    importance="minor"
                )
                alias_map[loc] = loc

        # Normalize relationships with canonical entity names
        normalized_rels: List[ExtractedRelationshipData] = []
        for rel in relationships:
            c_src = alias_map.get(rel.source_name, rel.source_name)
            c_tgt = alias_map.get(rel.target_name, rel.target_name)
            if c_src != c_tgt:
                normalized_rels.append(
                    ExtractedRelationshipData(
                        source_name=c_src,
                        target_name=c_tgt,
                        relationship_type=rel.relationship_type,
                        description=rel.description,
                        observed_page=rel.observed_page,
                        evidence_text=rel.evidence_text
                    )
                )

        # Normalize events with canonical entity names
        normalized_events: List[ExtractedEventData] = []
        for evt in events:
            c_parts = list({alias_map.get(p, p) for p in evt.participants})
            normalized_events.append(
                ExtractedEventData(
                    title=evt.title,
                    event_type=evt.event_type,
                    description=evt.description,
                    page_number=evt.page_number,
                    participants=c_parts,
                    location_name=evt.location_name,
                    evidence_text=evt.evidence_text
                )
            )

        return list(canonical_entities.values()), normalized_rels, normalized_events
