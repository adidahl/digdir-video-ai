export enum Role {
  SUPER_ADMIN = "super_admin",
  ORG_ADMIN = "org_admin",
  USER = "user",
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  organization_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

