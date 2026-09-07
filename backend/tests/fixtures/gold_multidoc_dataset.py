"""
Gold Multi-Document Evaluation Dataset for Phase 12 Multi-Document Intelligence.
Defines 10 cross-document evaluation scenarios with ground truth evidence expectations,
supporting citations, and contradiction criteria.
"""

GOLD_MULTIDOC_DATASET = [
    {
        "id": "md_01_lookup",
        "category": "simple_cross_document_lookup",
        "query": "Which encryption algorithms are recommended across selected papers?",
        "expected_documents": ["Paper_A.pdf", "Paper_B.pdf"],
        "expected_evidence_keywords": ["AES-256", "ChaCha20"],
        "expected_citations": ["Paper_A.pdf — Page 1", "Paper_B.pdf — Page 2"]
    },
    {
        "id": "md_02_comparison",
        "category": "comparison",
        "query": "Compare the authentication models presented in Paper A and Paper B.",
        "expected_documents": ["Paper_A.pdf", "Paper_B.pdf"],
        "expected_evidence_keywords": ["MFA", "OAuth 2.0"],
        "expected_similarities": ["Both recommend multi-factor authentication for identity verification."],
        "expected_differences": ["Paper A uses SAML 2.0 while Paper B relies on OAuth 2.0 / OIDC."]
    },
    {
        "id": "md_03_agreement",
        "category": "agreement",
        "query": "What do these documents agree on regarding defense in depth?",
        "expected_documents": ["Paper_A.pdf", "Paper_B.pdf", "Paper_C.pdf"],
        "expected_evidence_keywords": ["layered security", "attack surface"],
        "expected_agreed_claims": ["Layered controls significantly reduce successful intrusion rates."]
    },
    {
        "id": "md_04_contradiction",
        "category": "contradiction",
        "query": "Where do Paper A and Paper B disagree on zero trust efficacy?",
        "expected_documents": ["Paper_A.pdf", "Paper_B.pdf"],
        "expected_evidence_keywords": ["latency impact", "network overhead"],
        "expected_conflicts": [
            {
                "doc_a": "Paper_A.pdf",
                "doc_b": "Paper_B.pdf",
                "issue": "Paper A claims zero trust reduces latency by 15%, whereas Paper B reports a 20% latency penalty."
            }
        ]
    },
    {
        "id": "md_05_methodology",
        "category": "methodology_comparison",
        "query": "How does the evaluation methodology differ between these studies?",
        "expected_documents": ["Paper_A.pdf", "Paper_B.pdf"],
        "expected_evidence_keywords": ["synthetic benchmark", "empirical sandbox"],
        "expected_differences": ["Paper A used synthetic microbenchmarks; Paper B conducted a real-world enterprise sandbox trial."]
    },
    {
        "id": "md_06_source_specific",
        "category": "source_specific_question",
        "query": "What conclusions appear only in Paper C?",
        "expected_documents": ["Paper_C.pdf"],
        "expected_evidence_keywords": ["quantum-resistant cryptography"],
        "expected_citations": ["Paper_C.pdf — Page 4"]
    },
    {
        "id": "md_07_unanswerable",
        "category": "unanswerable_across_selected_documents",
        "query": "What is the GPU hardware requirement for processing in Paper A?",
        "expected_documents": ["Paper_A.pdf", "Paper_B.pdf"],
        "expected_evidence_keywords": [],
        "expected_answer_contains": "could not find"
    },
    {
        "id": "md_08_exclusion",
        "category": "document_exclusion",
        "query": "Summarize findings from selected documents (excluding Paper C).",
        "expected_documents": ["Paper_A.pdf", "Paper_B.pdf"],
        "excluded_documents": ["Paper_C.pdf"],
        "expected_evidence_keywords": ["AES-256", "OAuth"]
    },
    {
        "id": "md_09_conflicting_conditions",
        "category": "conflicting_conditions",
        "query": "Do the documents contradict on network throughput performance?",
        "expected_documents": ["Paper_A.pdf", "Paper_B.pdf"],
        "expected_qualifiers": ["10GbE enterprise network vs 1GbE cloud environment"]
    },
    {
        "id": "md_10_character_comparison",
        "category": "multi_document_character_comparison",
        "query": "Compare Lord Sterling's actions across Book 1 and Book 2.",
        "expected_documents": ["Book_1.pdf", "Book_2.pdf"],
        "expected_evidence_keywords": ["Sterling Manor", "Exile"],
        "expected_citations": ["Book_1.pdf — Page 1", "Book_2.pdf — Page 3"]
    }
]
