import { apiClient } from "./client";
import type { User } from "../types/auth";

export interface Organization {
  id: string;
  name: string;
  created_at: string;
}

export const adminAPI = {
  listUsers: async (): Promise<User[]> => {
    const response = await apiClient.get<User[]>("/api/users/");
    return response.data;
  },

  createUser: async (data: {
    email: string;
    password: string;
    full_name: string;
    role: string;
    organization_id?: string;
  }): Promise<User> => {
    const response = await apiClient.post<User>("/api/users/", data);
    return response.data;
  },

  updateUser: async (id: string, data: Partial<User>): Promise<User> => {
    const response = await apiClient.patch<User>(`/api/users/${id}`, data);
    return response.data;
  },

  deleteUser: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/users/${id}`);
  },

  listOrganizations: async (): Promise<Organization[]> => {
    const response = await apiClient.get<Organization[]>("/api/admin/organizations");
    return response.data;
  },
};

