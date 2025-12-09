import { apiClient } from "./client";
import type { Video, VideoSegment } from "../types/video";

export const videosAPI = {
  list: async (): Promise<Video[]> => {
    const response = await apiClient.get<Video[]>("/api/videos/");
    return response.data;
  },

  get: async (id: string): Promise<Video> => {
    const response = await apiClient.get<Video>(`/api/videos/${id}`);
    return response.data;
  },

  getSegments: async (id: string): Promise<VideoSegment[]> => {
    const response = await apiClient.get<VideoSegment[]>(`/api/videos/${id}/segments`);
    return response.data;
  },

  upload: async (
    file: File,
    title: string,
    description?: string,
    security_level?: string
  ): Promise<Video> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);
    if (description) formData.append("description", description);
    if (security_level) formData.append("security_level", security_level);

    const response = await apiClient.post<Video>("/api/videos/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return response.data;
  },

  update: async (id: string, data: Partial<Video>): Promise<Video> => {
    const response = await apiClient.patch<Video>(`/api/videos/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/videos/${id}`);
  },

  reprocess: async (id: string): Promise<Video> => {
    const response = await apiClient.post<Video>(`/api/videos/${id}/reprocess`);
    return response.data;
  },
};

