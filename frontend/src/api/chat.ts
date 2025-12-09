import { apiClient } from "./client";
import type { ChatRequest, ChatResponse, Conversation, ConversationWithMessages } from "../types/chat";

export const chatAPI = {
  sendMessage: async (request: ChatRequest): Promise<ChatResponse> => {
    const response = await apiClient.post<ChatResponse>("/api/chat/message", request);
    return response.data;
  },

  getConversations: async (): Promise<Conversation[]> => {
    const response = await apiClient.get<Conversation[]>("/api/chat/conversations");
    return response.data;
  },

  getConversation: async (conversationId: string): Promise<ConversationWithMessages> => {
    const response = await apiClient.get<ConversationWithMessages>(
      `/api/chat/${conversationId}/messages`
    );
    return response.data;
  },

  deleteConversation: async (conversationId: string): Promise<void> => {
    await apiClient.delete(`/api/chat/${conversationId}`);
  },

  getDebugSources: async (query: string): Promise<any> => {
    const response = await apiClient.post<any>("/api/chat/debug/sources", { query });
    return response.data;
  },
};

