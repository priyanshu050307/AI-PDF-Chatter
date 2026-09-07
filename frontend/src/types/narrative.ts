export interface EntityItem {
  id: string;
  document_id: string;
  name: string;
  entity_type: string; // PERSON, LOCATION, ORGANIZATION, EVENT
  description?: string;
  first_appeared_page: number;
  aliases: string[];
  importance: 'major' | 'minor' | 'background';
  mention_count: number;
}

export interface RelationshipItem {
  id: string;
  source_entity_id: string;
  target_entity_id: string;
  relationship_type: string;
  description?: string;
  observed_page: number;
  source_entity_name?: string;
  target_entity_name?: string;
}

export interface NarrativeEventItem {
  id: string;
  document_id: string;
  title: string;
  event_type: string;
  description?: string;
  page_number: number;
  participants: string[];
  location_name?: string;
}

export interface CharacterProfile {
  entity: EntityItem;
  relationships: RelationshipItem[];
  events: NarrativeEventItem[];
}

export interface NarrativeAskRequest {
  query: string;
  spoiler_mode: 'spoiler_free' | 'current_position' | 'full_book';
  current_page?: number;
}

export interface NarrativeAskResponse {
  query: string;
  answer: string;
  spoiler_mode: string;
  capped_at_page?: number;
  graph_context: {
    target_entity?: EntityItem;
    relationships?: RelationshipItem[];
    connected_entities?: EntityItem[];
    events?: NarrativeEventItem[];
  };
  citations: Array<{
    chunk_id: string;
    page_start: number;
    page_end: number;
    score?: number;
  }>;
}
