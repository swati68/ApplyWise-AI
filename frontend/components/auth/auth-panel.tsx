"use client";

import Link from "next/link";
import { AlertCircle, Loader2, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { authApi } from "@/lib/auth-api";


function GoogleMark() {
  return (
    <span className="flex h-5 w-5 items-center justify-center rounded-full border bg-white text-xs font-semibold text-slate-950">
      G
    </span>
  );
}


export function AuthPanel() {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  useEffect(() => {
    let isMounted = true;

    authApi
      .me()
      .then(() => {
        window.location.replace("/dashboard");
      })
      .catch(() => {
        if (isMounted) {
          setIsCheckingSession(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  if (isCheckingSession) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-white text-slate-950">
        <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          Checking session
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-white text-slate-950">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-8">
        <header className="flex items-center justify-between gap-4">
          <Link className="flex items-center gap-3" href="/">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-slate-950 text-sm font-bold text-white">
              AW
            </div>
            <span className="text-lg font-semibold">ApplyWise AI</span>
          </Link>
        </header>

        <section className="grid flex-1 items-center gap-10 py-16 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="text-sm font-semibold uppercase text-slate-400">
              ApplyWise AI
            </p>
            <h1 className="mt-4 max-w-xl text-5xl font-semibold leading-tight tracking-normal">
              Sign in to manage your job pipeline.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-slate-600">
              Keep your profile, job matches, and resume templates in one focused workspace.
            </p>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-[0_24px_80px_rgba(15,23,42,0.10)]">
            <div className="mb-6">
              <h2 className="text-2xl font-semibold tracking-normal">
                Log in
              </h2>
              <p className="mt-2 text-sm leading-6 text-slate-500">
                Use your Google account to continue.
              </p>
            </div>

            {errorMessage ? (
              <div className="mb-4 flex gap-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            ) : null}

            <Button
              asChild
              className="h-11 w-full justify-center"
            >
              <a href={authApi.googleLoginUrl()} onClick={() => setErrorMessage(null)}>
                <GoogleMark />
                Continue with Google
              </a>
            </Button>

            <div className="mt-6 rounded-lg border bg-slate-50 p-4 text-sm leading-6 text-slate-600">
              <div className="flex gap-3">
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                <p>
                  You can connect Drive and Gmail after signing in.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
