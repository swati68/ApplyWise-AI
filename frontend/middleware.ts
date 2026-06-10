import { NextResponse, type NextRequest } from "next/server";


const protectedPrefixes = [
  "/dashboard",
  "/profile",
  "/jobs",
  "/onboarding",
  "/resumes",
  "/settings",
];


const authRoutes = ["/login", "/signup"];
const authCookieName = "applywise_session";
const apiBaseUrl = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api"
).replace(/\/$/, "");


export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtectedRoute = protectedPrefixes.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
  const isAuthRoute = authRoutes.includes(pathname);

  if (!isProtectedRoute && !isAuthRoute) {
    return NextResponse.next();
  }

  const sessionCookie = request.cookies.get(authCookieName);
  const isAuthenticated = sessionCookie
    ? await hasValidSession(request)
    : false;

  if (isProtectedRoute && !isAuthenticated) {
    return redirectToLogin(request);
  }

  if (isAuthRoute && isAuthenticated) {
    const dashboardUrl = request.nextUrl.clone();
    dashboardUrl.pathname = "/dashboard";
    dashboardUrl.search = "";
    return NextResponse.redirect(dashboardUrl);
  }

  const response = NextResponse.next();
  if (sessionCookie !== undefined && !isAuthenticated) {
    response.cookies.delete(authCookieName);
  }

  return response;
}


async function hasValidSession(request: NextRequest): Promise<boolean> {
  const authCheckUrl = `${apiBaseUrl}/auth/me`;

  try {
    const response = await fetch(authCheckUrl, {
      cache: "no-store",
      headers: {
        cookie: request.headers.get("cookie") ?? "",
      },
    });

    return response.ok;
  } catch {
    return false;
  }
}


function redirectToLogin(request: NextRequest) {
  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.searchParams.set("next", `${request.nextUrl.pathname}${request.nextUrl.search}`);
  return NextResponse.redirect(loginUrl);
}


export const config = {
  matcher: [
    "/dashboard/:path*",
    "/profile/:path*",
    "/jobs/:path*",
    "/onboarding/:path*",
    "/resumes/:path*",
    "/settings/:path*",
    "/login",
    "/signup",
  ],
};
