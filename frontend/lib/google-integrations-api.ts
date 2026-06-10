import { apiUrl, request } from "@/lib/api-client";


export type GoogleIntegrationStatus = {
  user_id: string;
  google_sub: string | null;
  email: string | null;
  identity_connected: boolean;
  drive_connected: boolean;
  gmail_send_connected: boolean;
  automation_ready: boolean;
  granted_scopes: string[];
  drive_folder_id: string | null;
  updated_at: string | null;
};


export const googleIntegrationsApi = {
  async status(): Promise<GoogleIntegrationStatus> {
    return request<GoogleIntegrationStatus>("/integrations/google/status");
  },

  async disconnect(): Promise<GoogleIntegrationStatus> {
    return request<GoogleIntegrationStatus>("/integrations/google/disconnect", {
      method: "POST",
    });
  },

  connectUrl(): string {
    return apiUrl("/integrations/google/connect");
  },
};
