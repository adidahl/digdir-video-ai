import { apiClient } from "./client";
import type { LoginRequest, RegisterRequest, TokenResponse, User } from "../types/auth";

export const authAPI = {
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>("/api/auth/login", data);
    return response.data;
  },

  register: async (data: RegisterRequest): Promise<User> => {
    const response = await apiClient.post<User>("/api/auth/register", data);
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>("/api/auth/me");
    return response.data;
  },
};

