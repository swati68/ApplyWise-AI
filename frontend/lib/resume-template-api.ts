import { request } from "@/lib/api-client";


export type ResumeTemplate = {
  id: string;
  userId: string;
  name: string;
  latexContent: string;
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
};


export type ResumeTemplateValues = {
  name: string;
  latexContent: string;
  isDefault: boolean;
};


type ResumeTemplateApiRecord = {
  id: string;
  user_id: string;
  name: string;
  latex_content: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};


function toResumeTemplate(record: ResumeTemplateApiRecord): ResumeTemplate {
  return {
    id: record.id,
    userId: record.user_id,
    name: record.name,
    latexContent: record.latex_content,
    isDefault: record.is_default,
    createdAt: record.created_at,
    updatedAt: record.updated_at,
  };
}


function toApiPayload(values: ResumeTemplateValues) {
  return {
    name: values.name,
    latex_content: values.latexContent,
    is_default: values.isDefault,
  };
}


export const resumeTemplateApi = {
  async list(): Promise<ResumeTemplate[]> {
    const records = await request<ResumeTemplateApiRecord[]>("/resume-templates");
    return records.map(toResumeTemplate);
  },

  async create(values: ResumeTemplateValues): Promise<ResumeTemplate> {
    const record = await request<ResumeTemplateApiRecord>("/resume-templates", {
      body: JSON.stringify(toApiPayload(values)),
      method: "POST",
    });
    return toResumeTemplate(record);
  },

  async update(
    templateId: string,
    values: ResumeTemplateValues,
  ): Promise<ResumeTemplate> {
    const record = await request<ResumeTemplateApiRecord>(
      `/resume-templates/${templateId}`,
      {
        body: JSON.stringify(toApiPayload(values)),
        method: "PUT",
      },
    );
    return toResumeTemplate(record);
  },

  async delete(templateId: string): Promise<void> {
    await request<void>(`/resume-templates/${templateId}`, {
      method: "DELETE",
    });
  },

  async setDefault(templateId: string): Promise<ResumeTemplate> {
    const record = await request<ResumeTemplateApiRecord>(
      `/resume-templates/${templateId}/set-default`,
      { method: "POST" },
    );
    return toResumeTemplate(record);
  },
};
