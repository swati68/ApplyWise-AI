import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import type { AuthUser } from "@/lib/auth-api";
import { API_BASE_URL } from "@/lib/api-client";


const AUTH_COOKIE_NAME = "applywise_session";


export async function getServerAuthUser(): Promise<AuthUser | null> {
  const cookieStore = await cookies();
  const sessionCookie = cookieStore.get(AUTH_COOKIE_NAME);
  if (sessionCookie === undefined) {
    return null;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/auth/me`, {
      cache: "no-store",
      headers: {
        cookie: `${AUTH_COOKIE_NAME}=${sessionCookie.value}`,
      },
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as AuthUser;
  } catch {
    return null;
  }
}


export async function requireServerAuth(): Promise<AuthUser> {
  const user = await getServerAuthUser();
  if (user === null) {
    redirect("/login");
  }

  return user;
}


export async function redirectAuthenticatedUser(): Promise<void> {
  const user = await getServerAuthUser();
  if (user !== null) {
    redirect("/dashboard");
  }
}
