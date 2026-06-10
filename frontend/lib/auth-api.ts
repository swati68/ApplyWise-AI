import { apiUrl, request } from "@/lib/api-client";


export type AuthUser = {
  id: string;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
  identity_connected: boolean;
  drive_connected: boolean;
  gmail_send_connected: boolean;
  automation_ready: boolean;
};


export const authApi = {
  async logout(): Promise<void> {
    await request<void>("/auth/logout", {
      method: "POST",
    });
  },

  async me(): Promise<AuthUser> {
    return request<AuthUser>("/auth/me");
  },

  googleLoginUrl(): string {
    return apiUrl("/auth/google/login");
  },
};
