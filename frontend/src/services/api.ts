import { apiClient } from '@/lib/api-client';
import { HighlightItem, HighlightCreateRequest, HighlightUpdateRequest, HighlightListResponse } from '@/types';

export const apiService = {
  getHighlights: async (
    documentId: string,
    params?: { page_number?: number; color?: string; has_note?: boolean; search?: string }
  ): Promise<HighlightListResponse> => {
    const query = new URLSearchParams();
    if (params?.page_number) query.append('page_number', params.page_number.toString());
    if (params?.color) query.append('color', params.color);
    if (params?.has_note !== undefined) query.append('has_note', params.has_note.toString());
    if (params?.search) query.append('search', params.search);

    const queryString = query.toString() ? `?${query.toString()}` : '';
    return apiClient.get<HighlightListResponse>(`/documents/${documentId}/highlights${queryString}`);
  },

  createHighlight: async (documentId: string, payload: HighlightCreateRequest): Promise<HighlightItem> => {
    return apiClient.post<HighlightItem>(`/documents/${documentId}/highlights`, payload);
  },

  updateHighlight: async (highlightId: string, payload: HighlightUpdateRequest): Promise<HighlightItem> => {
    return apiClient.patch<HighlightItem>(`/highlights/${highlightId}`, payload);
  },

  deleteHighlight: async (highlightId: string): Promise<void> => {
    return apiClient.delete<void>(`/highlights/${highlightId}`);
  },
};
