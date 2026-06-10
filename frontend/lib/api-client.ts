export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api"
).replace(/\/$/, "");


export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}


export async function request<TResponse>(
  path: string,
  options: RequestInit = {},
): Promise<TResponse> {
  const headers = new Headers(options.headers);
  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(apiUrl(path), {
    ...options,
    cache: "no-store",
    credentials: "include",
    headers,
  });

  if (response.status === 204) {
    return undefined as TResponse;
  }

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new Error(detail ?? `Request failed with status ${response.status}.`);
  }

  return (await response.json()) as TResponse;
}


async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
    if (Array.isArray(body.detail)) {
      const messages = body.detail
        .map((item) => {
          if (
            typeof item === "object" &&
            item !== null &&
            "msg" in item &&
            typeof item.msg === "string"
          ) {
            return item.msg;
          }

          return null;
        })
        .filter((message): message is string => message !== null);

      return messages.length > 0 ? messages.join(" ") : null;
    }
  } catch {
    return null;
  }

  return null;
}
