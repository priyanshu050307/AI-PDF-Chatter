export interface User {
  id: string;
  email: string;
  full_name?: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: any;
  };
}

export type DocumentStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';

export type ChatIntent = 'QUESTION' | 'EXPLAIN' | 'SIMPLIFY' | 'EXAMPLE';

export interface SelectionContext {
  selected_text: string;
  page_number: number;
  selection_start?: number;
  selection_end?: number;
  bounding_box?: BoundingBoxData;
}

export interface ContextSnapshot {
  document_id: string;
  page_number: number;
  chapter_title?: string;
  section_title?: string;
  selection?: SelectionContext;
  intent?: ChatIntent;
}

export interface SendMessageRequest {
  content: string;
  context_snapshot?: ContextSnapshot;
  intent?: ChatIntent;
  stream?: boolean;
}

export interface ReadingProgress {
  id: string;
  user_id: string;
  document_id: string;
  current_page: number;
  scroll_position_pct: number;
  last_opened_at: string;
}

export interface DocumentItem {
  id: string;
  user_id: string;
  title: string;
  original_filename: string;
  file_size_bytes: number;
  page_count: number;
  processing_status: DocumentStatus;
  error_message?: string;
  created_at: string;
  progress?: ReadingProgress;
}

export interface CitationItem {
  chunk_id: string;
  page_start: number;
  page_end: number;
  chapter_title?: string;
  section_title?: string;
  score?: number;
}

export interface ChatMessageItem {
  id: string;
  conversation_id: string;
  sender: 'user' | 'assistant' | 'system';
  content: string;
  citations: CitationItem[];
  context_snapshot?: Record<string, any>;
  token_usage?: Record<string, any>;
  created_at: string;
}

export interface ConversationItem {
  id: string;
  user_id: string;
  document_id: string;
  title: string;
  mode: string;
  summary?: string;
  summary_updated_at?: string;
  summary_message_count?: number;
  created_at: string;
  updated_at: string;
  messages: ChatMessageItem[];
}

export interface PaginatedMessagesResponse {
  items: ChatMessageItem[];
  total: number;
  has_more: boolean;
  next_cursor?: string;
}

export type HighlightColor = 'yellow' | 'green' | 'blue' | 'pink' | 'purple';

export interface BoundingBoxRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface BoundingBoxData {
  x: number;
  y: number;
  width: number;
  height: number;
  page_width?: number;
  page_height?: number;
  rects?: BoundingBoxRect[];
}

export interface HighlightItem {
  id: string;
  user_id: string;
  document_id: string;
  page_number: number;
  selected_text: string;
  start_offset: number;
  end_offset: number;
  color: HighlightColor;
  note_text?: string;
  bounding_box?: BoundingBoxData;
  chapter_title?: string;
  section_title?: string;
  created_at: string;
  updated_at: string;
}

export interface HighlightCreateRequest {
  page_number: number;
  selected_text: string;
  start_offset?: number;
  end_offset?: number;
  color: HighlightColor;
  note_text?: string;
  bounding_box?: BoundingBoxData;
  chapter_title?: string;
  section_title?: string;
}

export interface HighlightUpdateRequest {
  color?: HighlightColor;
  note_text?: string;
}

export interface HighlightListResponse {
  items: HighlightItem[];
  total: number;
}

export * from './tutor';
export * from './narrative';

