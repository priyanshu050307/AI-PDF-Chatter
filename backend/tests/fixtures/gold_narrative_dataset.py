"""
Manually Annotated Gold Narrative Benchmark Dataset for Phase 10.5 Quality & Accuracy Testing.
Contains 8 representative test cases across dialogue, alias distinction, coreferences,
relationship temporality, narrative events, timeline order, character knowledge boundaries,
and spoiler safety.
"""

GOLD_NARRATIVE_DATASET = [
    {
        "id": "sample_1_dialogue",
        "title": "Dialogue Heavy & Canonical Alias Test",
        "text_pages": [
            (
                1,
                "Chapter 1: The Gathering\n\n"
                "Lord Edward Sterling entered the drawing room of Sterling Manor. "
                "He smiled at Lady Eleanor Vance. 'Welcome, Eleanor,' said Lord Sterling. "
                "Lady Eleanor Vance bowed gracefully. 'Thank you, Edward,' replied Eleanor. "
                "Lord Sterling trusts Lady Eleanor completely."
            )
        ],
        "expected_entities": [
            {
                "canonical_name": "Lord Edward Sterling",
                "entity_type": "PERSON",
                "aliases": ["Lord Edward Sterling", "Edward", "Sterling", "Lord Sterling"],
                "importance": "major"
            },
            {
                "canonical_name": "Lady Eleanor Vance",
                "entity_type": "PERSON",
                "aliases": ["Lady Eleanor Vance", "Eleanor"],
                "importance": "major"
            },
            {
                "canonical_name": "Sterling Manor",
                "entity_type": "LOCATION",
                "aliases": ["Sterling Manor"],
                "importance": "minor"
            }
        ],
        "expected_relationships": [
            {
                "source": "Lord Edward Sterling",
                "target": "Lady Eleanor Vance",
                "type": "trusts",
                "page": 1
            }
        ],
        "expected_events": [
            {
                "title": "Gathering at Sterling Manor",
                "type": "meeting",
                "page": 1,
                "participants": ["Lord Edward Sterling", "Lady Eleanor Vance"]
            }
        ]
    },
    {
        "id": "sample_2_alias_distinction",
        "title": "Generational Suffix Distinction Test",
        "text_pages": [
            (
                2,
                "The legal testament named two distinct heirs: Edward Sterling and Edward Sterling Jr.\n"
                "Edward Sterling signed the deed first. Later, Edward Sterling Jr. objected to the terms. "
                "Meanwhile, Inspector Thomas Miller observed both men."
            )
        ],
        "expected_entities": [
            {
                "canonical_name": "Edward Sterling",
                "entity_type": "PERSON",
                "aliases": ["Edward Sterling"],
                "importance": "major"
            },
            {
                "canonical_name": "Edward Sterling Jr.",
                "entity_type": "PERSON",
                "aliases": ["Edward Sterling Jr."],
                "importance": "major"
            },
            {
                "canonical_name": "Inspector Thomas Miller",
                "entity_type": "PERSON",
                "aliases": ["Inspector Thomas Miller", "Thomas Miller"],
                "importance": "minor"
            }
        ],
        "must_not_merge": [
            ("Edward Sterling", "Edward Sterling Jr.")
        ]
    },
    {
        "id": "sample_3_coreference",
        "title": "Pronoun Coreference & Ambiguity Fallback Test",
        "text_pages": [
            (
                3,
                "Paragraph 1: Detective Robert Smith picked up the letter. He examined the handwriting carefully.\n"
                "Paragraph 2: Inspector Robert Smith and Captain James Vance stood in the dimly lit hallway. "
                "He walked toward the door silently."
            )
        ],
        "expected_coreferences": [
            {"sentence_idx": 0, "pronoun": "He", "expected_target": "Detective Robert Smith", "confidence": "high"},
            {"sentence_idx": 1, "pronoun": "He", "expected_target": None, "confidence": "ambiguous"}  # Unresolved fallback
        ]
    },
    {
        "id": "sample_4_relationship_temporality",
        "title": "Temporal Relationship Transition Test",
        "text_pages": [
            (
                20,
                "Page 20: Alice Vance trusts Bob Sterling with the secret vault combination. "
                "They shook hands warmly."
            ),
            (
                100,
                "Page 100: Alice Vance discovered the missing documents. "
                "Now Alice Vance distrusts Bob Sterling completely."
            )
        ],
        "expected_temporal_states": [
            {
                "source": "Alice Vance",
                "target": "Bob Sterling",
                "type": "trusts",
                "observed_page": 20,
                "valid_until_page": 99
            },
            {
                "source": "Alice Vance",
                "target": "Bob Sterling",
                "type": "distrusts",
                "observed_page": 100,
                "valid_from_page": 100
            }
        ]
    },
    {
        "id": "sample_5_event_categories",
        "title": "Event Classification Test",
        "text_pages": [
            (
                5,
                "At midnight, Lord Sterling discovered the hidden passage behind the bookcase. "
                "Shortly after, Captain Arthur Pendelton departed from the estate. "
                "Lady Eleanor Vance made the crucial decision to hide the key."
            )
        ],
        "expected_events": [
            {"type": "discovery", "title_keyword": "discovered", "page": 5},
            {"type": "departure", "title_keyword": "departed", "page": 5},
            {"type": "decision", "title_keyword": "decision", "page": 5}
        ]
    },
    {
        "id": "sample_6_timeline_flashback",
        "title": "Flashback & Story-Time vs Document Order Test",
        "text_pages": [
            (
                10,
                "In the present year 1890, Detective Smith examined the crime scene in London."
            ),
            (
                50,
                "Flashback to 1870: Twenty years earlier, young Robert Smith met Henry Vance in Paris."
            )
        ],
        "document_order": [10, 50],
        "story_time_order": [50, 10]
    },
    {
        "id": "sample_7_character_knowledge",
        "title": "Character Knowledge Boundary Test",
        "text_pages": [
            (
                10,
                "Alice Vance secretly stole the gold key from the desk at midnight."
            ),
            (
                30,
                "Robert Sterling searched his study, completely unaware of the missing key. "
                "Robert Sterling still believes the key is safely locked inside the drawer."
            )
        ],
        "query": "What does Robert Sterling know about the gold key on page 30?",
        "expected_knowledge": "Robert Sterling does not know Alice stole the key.",
        "forbidden_knowledge": "Robert knows Alice stole the key."
    },
    {
        "id": "sample_8_spoiler_protection",
        "title": "Spoiler Security & Page Capping Test",
        "text_pages": [
            (
                40,
                "Page 40: Lord Sterling continues his investigation into the missing estate funds."
            ),
            (
                200,
                "Page 200: Critical revelation: Lady Eleanor Vance was the mastermind behind the stolen funds."
            )
        ],
        "active_reading_page": 40,
        "query": "Who took the estate funds?",
        "spoiler_free_expected_answer_constraint": "Must NOT reveal Lady Eleanor Vance on page 200.",
        "full_book_expected_answer_constraint": "May reveal Lady Eleanor Vance from page 200."
    }
]
