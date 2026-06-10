import { request } from "@/lib/api-client";


export type CustomJobStatus = {
  id: string;
  userId: string;
  name: string;
  color: string;
  sortOrder: number;
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
};


export type CustomJobStatusValues = {
  name: string;
  color: string;
  sortOrder: number;
  isDefault: boolean;
};


type CustomJobStatusApiRecord = {
  id: string;
  user_id: string;
  name: string;
  color: string | null;
  sort_order: number;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};


export const jobStatusesApi = {
  async list(): Promise<CustomJobStatus[]> {
    const records = await request<CustomJobStatusApiRecord[]>("/job-statuses");
    return records.map(jobStatusFromApi);
  },

  async create(values: CustomJobStatusValues): Promise<CustomJobStatus> {
    const record = await request<CustomJobStatusApiRecord>("/job-statuses", {
      body: JSON.stringify(jobStatusToApi(values)),
      method: "POST",
    });
    return jobStatusFromApi(record);
  },

  async update(
    statusId: string,
    values: Partial<CustomJobStatusValues>,
  ): Promise<CustomJobStatus> {
    const record = await request<CustomJobStatusApiRecord>(
      `/job-statuses/${statusId}`,
      {
        body: JSON.stringify(partialJobStatusToApi(values)),
        method: "PUT",
      },
    );
    return jobStatusFromApi(record);
  },

  async delete(statusId: string): Promise<void> {
    await request<void>(`/job-statuses/${statusId}`, {
      method: "DELETE",
    });
  },
};


function jobStatusFromApi(record: CustomJobStatusApiRecord): CustomJobStatus {
  return {
    id: record.id,
    userId: record.user_id,
    name: record.name,
    color: record.color ?? "",
    sortOrder: record.sort_order,
    isDefault: record.is_default,
    createdAt: record.created_at,
    updatedAt: record.updated_at,
  };
}


function jobStatusToApi(values: CustomJobStatusValues) {
  return {
    name: values.name,
    color: optionalApiString(values.color),
    sort_order: values.sortOrder,
    is_default: values.isDefault,
  };
}


function partialJobStatusToApi(values: Partial<CustomJobStatusValues>) {
  return {
    ...(values.name !== undefined ? { name: values.name } : {}),
    ...(values.color !== undefined ? { color: optionalApiString(values.color) } : {}),
    ...(values.sortOrder !== undefined ? { sort_order: values.sortOrder } : {}),
    ...(values.isDefault !== undefined ? { is_default: values.isDefault } : {}),
  };
}


function optionalApiString(value: string): string | null {
  const cleanedValue = value.trim();
  return cleanedValue === "" ? null : cleanedValue;
}
