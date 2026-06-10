"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  RefreshCw,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  type GoogleIntegrationStatus,
  googleIntegrationsApi,
} from "@/lib/google-integrations-api";


export function GoogleIntegrationSettings() {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
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

  async function handleDisconnect() {
    setIsDisconnecting(true);
    setErrorMessage(null);

    try {
      const nextStatus = await googleIntegrationsApi.disconnect();
      setStatus(nextStatus);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Could not disconnect Google services.",
      );
    } finally {
      setIsDisconnecting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-3 rounded-lg border p-4 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading Google integration
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {errorMessage ? (
        <div className="flex gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-3">
        <StatusTile
          detail={status?.email ?? "No Google identity recorded"}
          isConnected={status?.identity_connected ?? false}
          label="Google account"
        />
        <StatusTile
          detail="Save generated resumes"
          isConnected={status?.drive_connected ?? false}
          label="Google Drive"
        />
        <StatusTile
          detail="Send application updates"
          isConnected={status?.gmail_send_connected ?? false}
          label="Gmail"
        />
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <Button asChild>
          <a href={googleIntegrationsApi.connectUrl()}>
            <RefreshCw />
            {status?.drive_connected && status.gmail_send_connected
              ? "Reconnect"
              : "Connect"}
          </a>
        </Button>
        <Button
          disabled={
            isDisconnecting ||
            !(status?.drive_connected || status?.gmail_send_connected)
          }
          onClick={handleDisconnect}
          type="button"
          variant="outline"
        >
          {isDisconnecting ? <Loader2 className="animate-spin" /> : <Trash2 />}
          Disconnect
        </Button>
      </div>
    </div>
  );
}


function StatusTile({
  detail,
  isConnected,
  label,
}: {
  detail: string;
  isConnected: boolean;
  label: string;
}) {
  return (
    <div className="rounded-lg border p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-medium">{label}</p>
          <p className="mt-1 truncate text-xs text-muted-foreground">{detail}</p>
        </div>
        {isConnected ? (
          <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
        ) : (
          <TriangleAlert className="h-4 w-4 shrink-0 text-amber-500" />
        )}
      </div>
      <Badge className="mt-3" variant={isConnected ? "secondary" : "outline"}>
        {isConnected ? "Connected" : "Not connected"}
      </Badge>
    </div>
  );
}
