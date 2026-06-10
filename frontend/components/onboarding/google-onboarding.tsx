"use client";

import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Mail,
  RefreshCw,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type GoogleIntegrationStatus,
  googleIntegrationsApi,
} from "@/lib/google-integrations-api";


type OnboardingItem = {
  description: string;
  isConnected: boolean;
  label: string;
};


export function GoogleOnboarding() {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [status, setStatus] = useState<GoogleIntegrationStatus | null>(null);

  useEffect(() => {
    let isMounted = true;

    async function loadStatus() {
      try {
        const nextStatus = await googleIntegrationsApi.status();
        if (isMounted) {
          setStatus(nextStatus);
          setErrorMessage(null);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(
            error instanceof Error
              ? error.message
              : "Could not load Google integration status.",
          );
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadStatus();

    return () => {
      isMounted = false;
    };
  }, []);

  const items: OnboardingItem[] = [
    {
      description: status?.email ?? "Signed in with your Google account.",
      isConnected: status?.identity_connected ?? false,
      label: "Google Login",
    },
    {
      description: "Save generated resume PDFs.",
      isConnected: status?.drive_connected ?? false,
      label: "Google Drive",
    },
    {
      description: "Send job and resume updates.",
      isConnected: status?.gmail_send_connected ?? false,
      label: "Gmail",
    },
  ];
  const isAutomationReady = status?.automation_ready ?? false;

  return (
    <div className="space-y-6">
      <PageHeader
        description="Connect Drive and Gmail when you want generated resumes saved and sent automatically."
        eyebrow="Onboarding"
        title="Finish setup"
      />

      {isLoading ? (
        <Card>
          <CardContent className="flex items-center gap-3 py-8 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Checking Google connection status
          </CardContent>
        </Card>
      ) : null}

      {errorMessage ? (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="flex gap-3 py-5 text-sm text-destructive">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </CardContent>
        </Card>
      ) : null}

      {!isLoading ? (
        <>
          <section className="grid gap-4 md:grid-cols-3">
            {items.map((item) => (
              <Card key={item.label}>
                <CardHeader>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <CardTitle>{item.label}</CardTitle>
                      <CardDescription className="mt-2 leading-6">
                        {item.description}
                      </CardDescription>
                    </div>
                    {item.isConnected ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                    ) : (
                      <TriangleAlert className="h-5 w-5 text-amber-500" />
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <Badge variant={item.isConnected ? "secondary" : "outline"}>
                    {item.isConnected ? "Connected" : "Not connected"}
                  </Badge>
                </CardContent>
              </Card>
            ))}
          </section>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                {isAutomationReady ? (
                  <ShieldCheck className="h-4 w-4 text-emerald-500" />
                ) : (
                  <Mail className="h-4 w-4 text-primary" />
                )}
                <CardTitle>
                  {isAutomationReady ? "Ready" : "Connect services"}
                </CardTitle>
              </div>
              <CardDescription className="leading-6">
                {isAutomationReady
                  ? "Your account is ready for automated resume generation and email delivery."
                  : "Drive upload and email delivery will not work until these services are connected."}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 sm:flex-row">
              <Button asChild>
                <a href={googleIntegrationsApi.connectUrl()}>
                  <RefreshCw />
                  {isAutomationReady ? "Reconnect" : "Connect"}
                </a>
              </Button>
              <Button asChild variant="outline">
                <Link href="/dashboard">Continue to Dashboard</Link>
              </Button>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
