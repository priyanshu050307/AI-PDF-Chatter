import { apiClient } from '@/lib/api-client';
import {
  EntityItem,
  CharacterProfile,
  NarrativeEventItem,
  NarrativeAskRequest,
  NarrativeAskResponse,
} from '@/types';

export const narrativeApi = {
  getEntities: async (documentId: string, importance?: string): Promise<EntityItem[]> => {
    const query = importance ? `?importance=${encodeURIComponent(importance)}` : '';
    return apiClient.get<EntityItem[]>(`/documents/${documentId}/narrative/entities${query}`);
  },

  getEntityProfile: async (documentId: string, entityId: string, maxPage?: number): Promise<CharacterProfile> => {
    const query = maxPage !== undefined ? `?max_page=${maxPage}` : '';
    return apiClient.get<CharacterProfile>(`/documents/${documentId}/narrative/entities/${entityId}${query}`);
  },

  getTimeline: async (documentId: string, maxPage?: number): Promise<NarrativeEventItem[]> => {
    const query = maxPage !== undefined ? `?max_page=${maxPage}` : '';
    return apiClient.get<NarrativeEventItem[]>(`/documents/${documentId}/narrative/timeline${query}`);
  },

  askQuestion: async (documentId: string, req: NarrativeAskRequest): Promise<NarrativeAskResponse> => {
    return apiClient.post<NarrativeAskResponse>(`/documents/${documentId}/narrative/ask`, req);
  },
};
