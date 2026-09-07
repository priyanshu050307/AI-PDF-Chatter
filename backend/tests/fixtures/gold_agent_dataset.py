"""
Manually Annotated Gold Agent Benchmark Dataset for Phase 11 Evaluation.
Contains 9 evaluation query categories testing tool selection, multi-step investigation,
evidence recall/precision, comparison, annotation analysis, spoiler protection,
unanswerable queries, and conflicting evidence.
"""

GOLD_AGENT_DATASET = [
    {
        "category": "simple_factual",
        "query": "What is the primary encryption standard used?",
        "expected_route": "SIMPLE_FACTUAL",
        "expected_tools": ["search_evidence"],
        "expected_min_evidence": 1,
        "is_agentic": False
    },
    {
        "category": "multi_hop_factual",
        "query": "Investigate how security risk factors evolve across Chapter 1 and Chapter 3.",
        "expected_route": "MULTI_STEP_INVESTIGATION",
        "expected_tools": ["get_document_structure", "search_evidence"],
        "expected_min_evidence": 2,
        "is_agentic": True
    },
    {
        "category": "character_relationship",
        "query": "How did Lord Edward Sterling and Lady Eleanor Vance's relationship evolve?",
        "expected_route": "CHARACTER_NARRATIVE",
        "expected_tools": ["find_entity", "find_relationships", "find_events"],
        "expected_min_evidence": 2,
        "is_agentic": True
    },
    {
        "category": "temporal_narrative",
        "query": "List all plot events involving Captain Pendelton in chronological order.",
        "expected_route": "CHARACTER_NARRATIVE",
        "expected_tools": ["find_events", "get_character_timeline"],
        "expected_min_evidence": 2,
        "is_agentic": True
    },
    {
        "category": "comparison",
        "query": "Compare Lord Sterling and Lady Eleanor Vance.",
        "expected_route": "COMPARISON",
        "expected_tools": ["compare_entities", "search_evidence"],
        "expected_min_evidence": 2,
        "is_agentic": True
    },
    {
        "category": "annotation_analysis",
        "query": "What did I highlight about authentication security in my notes?",
        "expected_route": "ANNOTATION_ANALYSIS",
        "expected_tools": ["get_my_annotations", "search_evidence"],
        "expected_min_evidence": 1,
        "is_agentic": True
    },
    {
        "category": "multimodal_evidence",
        "query": "What does Table 1 show regarding high risk factors?",
        "expected_route": "MULTI_STEP_INVESTIGATION",
        "expected_tools": ["search_evidence"],
        "expected_min_evidence": 1,
        "is_agentic": True
    },
    {
        "category": "unanswerable",
        "query": "What is the average surface temperature on Titan in 2090?",
        "expected_route": "MULTI_STEP_INVESTIGATION",
        "expected_tools": ["search_evidence"],
        "expected_min_evidence": 0,
        "is_agentic": True,
        "expected_grounding_response": "I could not find information addressing your question"
    },
    {
        "category": "conflicting_evidence",
        "query": "Did Alice trust Bob on page 20 versus page 100?",
        "expected_route": "CHARACTER_NARRATIVE",
        "expected_tools": ["find_relationships"],
        "expected_min_evidence": 2,
        "is_agentic": True
    }
]
