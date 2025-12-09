import { apiClient } from "./client";
import type { SearchRequest, SearchResult } from "../types/video";

export const searchAPI = {
  search: async (request: SearchRequest): Promise<SearchResult[]> => {
    const response = await apiClient.post<SearchResult[]>("/api/search/", request);
    return response.data;
  },
};

