"""Standardized Benchmark Datasets & Versioning for AI PDF Chatter Evaluation."""

from typing import Dict, List, Any, Optional
from tests.fixtures.gold_agent_dataset import GOLD_AGENT_DATASET
from tests.fixtures.gold_multidoc_dataset import GOLD_MULTIDOC_DATASET
from tests.fixtures.gold_narrative_dataset import GOLD_NARRATIVE_DATASET


# 1. Retrieval Benchmark Dataset (retrieval-v1)
RETRIEVAL_V1_DATASET = [
    {
        "case_id": "ret_01",
        "category": "exact_keyword_lookup",
        "difficulty": "easy",
        "question": "What is the primary AES encryption key length specified?",
        "expected_evidence": [{"keywords": ["AES-256", "key length"], "page": 1}],
        "expected_answer_properties": {"required_terms": ["AES-256", "256-bit"]},
    },
    {
        "case_id": "ret_02",
        "category": "semantic_synonym_retrieval",
        "difficulty": "medium",
        "question": "How does the system prevent unauthorized identity access?",
        "expected_evidence": [{"keywords": ["multi-factor authentication", "MFA", "OAuth 2.0"], "page": 1}],
        "expected_answer_properties": {"required_terms": ["multi-factor", "authentication"]},
    },
    {
        "case_id": "ret_03",
        "category": "multi_page_aggregation",
        "difficulty": "hard",
        "question": "Summarize the network security vulnerability mitigation strategy across pages 1 and 3.",
        "expected_evidence": [{"keywords": ["firewall", "zero trust", "network segmentation"], "page": 1}, {"keywords": ["patch management"], "page": 3}],
        "expected_answer_properties": {"required_terms": ["segmentation", "patch"]},
    },
    {
        "case_id": "ret_04",
        "category": "unanswerable_query",
        "difficulty": "medium",
        "question": "What is the quantum computer qubit threshold mentioned in section 4?",
        "expected_evidence": [],
        "expected_answer_properties": {"must_refuse": True, "required_terms": ["could not find"]},
    }
]


# 2. Agent Benchmark Dataset (agent-v1)
AGENT_V1_DATASET = [
    {
        "case_id": f"agent_{i+1:02d}",
        "category": item["category"],
        "difficulty": "medium" if not item.get("is_agentic") else "hard",
        "question": item["query"],
        "expected_route": item.get("expected_route"),
        "expected_tools": item.get("expected_tools", []),
        "expected_evidence": [{"keywords": [item["query"].split()[0]]}],
        "expected_answer_properties": {"must_refuse": item.get("category") == "unanswerable"},
        "metadata": item
    }
    for i, item in enumerate(GOLD_AGENT_DATASET)
]


# 3. Narrative Intelligence Benchmark Dataset (narrative-v1)
NARRATIVE_V1_DATASET = [
    {
        "case_id": f"narrative_{i+1:02d}",
        "category": item.get("category", "entity_extraction"),
        "difficulty": "medium",
        "question": item.get("query", f"Tell me about {item.get('entity_name', 'characters')}"),
        "expected_entities": item.get("expected_entities", []),
        "expected_relationships": item.get("expected_relationships", []),
        "expected_events": item.get("expected_events", []),
        "expected_evidence": [{"page": item.get("page", 1)}],
        "metadata": item
    }
    for i, item in enumerate(GOLD_NARRATIVE_DATASET)
]


# 4. Multi-Document Intelligence Benchmark Dataset (multidoc-v1)
MULTIDOC_V1_DATASET = [
    {
        "case_id": item["id"],
        "category": item["category"],
        "difficulty": "hard",
        "question": item["query"],
        "expected_documents": item.get("expected_documents", []),
        "expected_evidence": [{"keywords": item.get("expected_evidence_keywords", [])}],
        "expected_citations": item.get("expected_citations", []),
        "expected_answer_properties": {
            "must_refuse": item.get("category") == "unanswerable_across_selected_documents",
            "conflicts_expected": "expected_conflicts" in item
        },
        "metadata": item
    }
    for item in GOLD_MULTIDOC_DATASET
]


# 5. Multimodal PDF Intelligence Benchmark Dataset (multimodal-v1)
MULTIMODAL_V1_DATASET = [
    {
        "case_id": "mm_01_ocr",
        "category": "scanned_ocr_extraction",
        "difficulty": "medium",
        "question": "What is the document title extracted via OCR on page 1 of the scanned archive?",
        "expected_evidence": [{"element_type": "ocr_text", "page": 1, "keywords": ["CONFIDENTIAL SECURITY AUDIT"]}],
        "expected_answer_properties": {"required_terms": ["CONFIDENTIAL SECURITY AUDIT"]}
    },
    {
        "case_id": "mm_02_table",
        "category": "structured_table_reasoning",
        "difficulty": "medium",
        "question": "What is the high-severity vulnerability count listed in Table 1?",
        "expected_evidence": [{"element_type": "table", "page": 2, "keywords": ["Table 1", "High Severity", "14"]}],
        "expected_answer_properties": {"required_terms": ["14", "Table 1"]}
    },
    {
        "case_id": "mm_03_visual",
        "category": "visual_figure_understanding",
        "difficulty": "hard",
        "question": "Describe the architecture topology depicted in Figure 3.",
        "expected_evidence": [{"element_type": "image", "page": 3, "keywords": ["Figure 3", "Load Balancer", "Worker Pool"]}],
        "expected_answer_properties": {"required_terms": ["Figure 3", "Load Balancer"]}
    }
]


# 6. AI Tutor Mode Benchmark Dataset (tutor-v1)
TUTOR_V1_DATASET = [
    {
        "case_id": "tutor_01_diagnostic",
        "category": "diagnostic_assessment",
        "difficulty": "easy",
        "question": "Initiate diagnostic assessment for asymmetric encryption.",
        "expected_evidence": [{"keywords": ["public key", "private key"]}],
        "expected_answer_properties": {"tutor_action": "ASSESSING"}
    },
    {
        "case_id": "tutor_02_hint",
        "category": "progressive_hint_utility",
        "difficulty": "medium",
        "question": "Provide a Level 1 progressive hint for modular exponentiation.",
        "expected_evidence": [{"keywords": ["modular arithmetic"]}],
        "expected_answer_properties": {"hint_level": 1}
    },
    {
        "case_id": "tutor_03_quiz",
        "category": "comprehension_quiz_grading",
        "difficulty": "medium",
        "question": "Evaluate student answer 'AES uses asymmetric keys' for MCQ 1.",
        "expected_evidence": [{"keywords": ["AES uses symmetric secret keys"]}],
        "expected_answer_properties": {"correct": False}
    }
]


# 7. Hallucination & Unsupported Answer Dataset (hallucination-v1)
HALLUCINATION_V1_DATASET = [
    {
        "case_id": "hal_01_fully_supported",
        "category": "fully_supported",
        "difficulty": "easy",
        "question": "What key size is specified for AES encryption in the document?",
        "expected_evidence": [{"keywords": ["256-bit AES"]}],
        "expected_answer_properties": {"must_refuse": False, "required_terms": ["256-bit"]}
    },
    {
        "case_id": "hal_02_partially_supported",
        "category": "partially_supported",
        "difficulty": "medium",
        "question": "Explain the AES 256-bit key size and its performance impact on ARM Cortex M0 processors.",
        "expected_evidence": [{"keywords": ["256-bit AES"]}], # Document mentions AES 256-bit but not ARM Cortex M0
        "expected_answer_properties": {"must_refuse": False, "must_qualify": True, "required_terms": ["AES 256"]}
    },
    {
        "case_id": "hal_03_unsupported",
        "category": "completely_unsupported",
        "difficulty": "medium",
        "question": "What was the stock price of Apple Inc. on January 5, 2026 according to the document?",
        "expected_evidence": [],
        "expected_answer_properties": {"must_refuse": True, "required_terms": ["could not find"]}
    },
    {
        "case_id": "hal_04_conflicting_prompt",
        "category": "deliberately_conflicting_prompt",
        "difficulty": "hard",
        "question": "The document claims that AES-256 uses 128-bit keys. Confirm this.",
        "expected_evidence": [{"keywords": ["AES-256 uses 256-bit keys"]}],
        "expected_answer_properties": {"must_refuse": False, "must_correct_premise": True, "required_terms": ["256-bit"]}
    }
]


# Registry map
DATASET_REGISTRY: Dict[str, Dict[str, Any]] = {
    "retrieval-v1": {
        "dataset_name": "retrieval",
        "dataset_version": "retrieval-v1",
        "description": "Standardized vector & lexical retrieval quality evaluation dataset.",
        "cases": RETRIEVAL_V1_DATASET
    },
    "agent-v1": {
        "dataset_name": "agent",
        "dataset_version": "agent-v1",
        "description": "Agentic multi-step tool selection and reasoning evaluation dataset.",
        "cases": AGENT_V1_DATASET
    },
    "narrative-v1": {
        "dataset_name": "narrative",
        "dataset_version": "narrative-v1",
        "description": "Character, relationship, timeline event, and spoiler leakage evaluation dataset.",
        "cases": NARRATIVE_V1_DATASET
    },
    "multidoc-v1": {
        "dataset_name": "multidoc",
        "dataset_version": "multidoc-v1",
        "description": "Cross-document comparison, consensus, and contradiction evaluation dataset.",
        "cases": MULTIDOC_V1_DATASET
    },
    "multimodal-v1": {
        "dataset_name": "multimodal",
        "dataset_version": "multimodal-v1",
        "description": "Scanned page OCR, table parsing, and figure vision evaluation dataset.",
        "cases": MULTIMODAL_V1_DATASET
    },
    "tutor-v1": {
        "dataset_name": "tutor",
        "dataset_version": "tutor-v1",
        "description": "AI Tutor state machine, difficulty alignment, hint, and quiz evaluation dataset.",
        "cases": TUTOR_V1_DATASET
    },
    "hallucination-v1": {
        "dataset_name": "hallucination",
        "dataset_version": "hallucination-v1",
        "description": "Hallucination, premise correction, and unsupported claim refusal evaluation dataset.",
        "cases": HALLUCINATION_V1_DATASET
    }
}


def list_datasets() -> List[Dict[str, str]]:
    return [
        {
            "dataset_name": info["dataset_name"],
            "dataset_version": info["dataset_version"],
            "description": info["description"],
            "case_count": len(info["cases"])
        }
        for info in DATASET_REGISTRY.values()
    ]


def get_dataset(dataset_version: str) -> Optional[Dict[str, Any]]:
    return DATASET_REGISTRY.get(dataset_version)
