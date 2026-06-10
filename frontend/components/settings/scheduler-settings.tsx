"use client";

import { AlertTriangle, Clock, Loader2, Save } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  type GoogleIntegrationStatus,
  googleIntegrationsApi,
} from "@/lib/google-integrations-api";
import {
  type SchedulerPreference,
  type SchedulerPreferenceValues,
  schedulerApi,
} from "@/lib/scheduler-api";


const timezoneOptions = [
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "UTC",
];


const defaultValues: SchedulerPreferenceValues = {
  enabled: false,
  timezone: "America/New_York",
  morningEnabled: true,
  morningTime: "08:00",
  eveningEnabled: true,
  eveningTime: "18:00",
  minMatchScore: 50,
};


export function SchedulerSettings() {
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [googleStatus, setGoogleStatus] = useState<GoogleIntegrationStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [savedPreference, setSavedPreference] = useState<SchedulerPreference | null>(
    null,
  );
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [values, setValues] = useState<SchedulerPreferenceValues>(defaultValues);

  useEffect(() => {
    let isMounted = true;

    async function loadSchedulerSettings() {
      try {
        const [preference, nextGoogleStatus] = await Promise.all([
          schedulerApi.preferences(),
          googleIntegrationsApi.status(),
        ]);
        if (isMounted) {
          setSavedPreference(preference);
          setGoogleStatus(nextGoogleStatus);
          setValues({
            enabled: preference.enabled,
            timezone: preference.timezone,
            morningEnabled: preference.morningEnabled,
            morningTime: preference.morningTime,
            eveningEnabled: preference.eveningEnabled,
            eveningTime: preference.eveningTime,
            minMatchScore: preference.minMatchScore,
          });
          setErrorMessage(null);
        }
      } catch (error) {
        if (isMounted) {
          setErrorMessage(getErrorMessage(error));
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    void loadSchedulerSettings();

    return () => {
      isMounted = false;
    };
  }, []);

  const isGoogleReady = Boolean(
    googleStatus?.drive_connected && googleStatus.gmail_send_connected,
  );

  async function handleSave() {
    setErrorMessage(null);
    setSuccessMessage(null);

    if (values.enabled && !isGoogleReady) {
      setErrorMessage("Connect Google Drive and Gmail permissions before enabling automation.");
      return;
    }

    setIsSaving(true);
    try {
      const preference = await schedulerApi.updatePreferences(values);
      setSavedPreference(preference);
      setValues({
        enabled: preference.enabled,
        timezone: preference.timezone,
        morningEnabled: preference.morningEnabled,
        morningTime: preference.morningTime,
        eveningEnabled: preference.eveningEnabled,
        eveningTime: preference.eveningTime,
        minMatchScore: preference.minMatchScore,
      });
      setSuccessMessage("Scheduler preferences saved.");
    } catch (error) {
      setErrorMessage(getErrorMessage(error));
    } finally {
      setIsSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-3 rounded-lg border p-4 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading scheduler preferences
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {!isGoogleReady ? (
        <div className="flex gap-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>Connect Google Drive and Gmail permissions before enabling automation.</span>
        </div>
      ) : null}

      {errorMessage ? (
        <div className="flex gap-3 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      ) : null}

      {successMessage ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-medium text-emerald-800">
          {successMessage}
        </div>
      ) : null}

      <div className="rounded-lg border p-4">
        <label className="flex items-start justify-between gap-4">
          <span>
            <span className="font-medium">Enable automation</span>
            <span className="mt-1 block text-sm text-muted-foreground">
              Run enabled GitHub sources at the configured times.
            </span>
          </span>
          <input
            checked={values.enabled}
            className="mt-1 h-5 w-5 accent-primary"
            disabled={!isGoogleReady}
            onChange={(event) =>
              setValues((currentValues) => ({
                ...currentValues,
                enabled: event.target.checked,
              }))
            }
            type="checkbox"
          />
        </label>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <label className="grid gap-2 text-sm font-medium">
          Timezone
          <select
            className="h-10 rounded-md border bg-background px-3 text-sm"
            onChange={(event) =>
              setValues((currentValues) => ({
                ...currentValues,
                timezone: event.target.value,
              }))
            }
            value={values.timezone}
          >
            {timezoneOptions.map((timezone) => (
              <option key={timezone} value={timezone}>
                {timezone}
              </option>
            ))}
          </select>
        </label>

        <label className="grid gap-2 text-sm font-medium">
          Minimum match score
          <input
            className="h-10 rounded-md border bg-background px-3 text-sm"
            max={100}
            min={0}
            onChange={(event) =>
              setValues((currentValues) => ({
                ...currentValues,
                minMatchScore: Number(event.target.value),
              }))
            }
            type="number"
            value={values.minMatchScore}
          />
        </label>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ScheduleTimeField
          checked={values.morningEnabled}
          label="Morning scan"
          onCheckedChange={(checked) =>
            setValues((currentValues) => ({
              ...currentValues,
              morningEnabled: checked,
            }))
          }
          onTimeChange={(timeValue) =>
            setValues((currentValues) => ({
              ...currentValues,
              morningTime: timeValue,
            }))
          }
          timeValue={values.morningTime}
        />
        <ScheduleTimeField
          checked={values.eveningEnabled}
          label="Evening scan"
          onCheckedChange={(checked) =>
            setValues((currentValues) => ({
              ...currentValues,
              eveningEnabled: checked,
            }))
          }
          onTimeChange={(timeValue) =>
            setValues((currentValues) => ({
              ...currentValues,
              eveningTime: timeValue,
            }))
          }
          timeValue={values.eveningTime}
        />
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Clock className="h-4 w-4" />
          Next run: {savedPreference?.nextRunAt ? formatDateTime(savedPreference.nextRunAt) : "Not scheduled"}
        </div>
        <Button disabled={isSaving} onClick={handleSave} type="button">
          {isSaving ? <Loader2 className="animate-spin" /> : <Save />}
          Save
        </Button>
      </div>
    </div>
  );
}


function ScheduleTimeField({
  checked,
  label,
  onCheckedChange,
  onTimeChange,
  timeValue,
}: {
  checked: boolean;
  label: string;
  onCheckedChange: (checked: boolean) => void;
  onTimeChange: (value: string) => void;
  timeValue: string;
}) {
  return (
    <div className="rounded-lg border p-4">
      <label className="flex items-center justify-between gap-3">
        <span className="font-medium">{label}</span>
        <input
          checked={checked}
          className="h-5 w-5 accent-primary"
          onChange={(event) => onCheckedChange(event.target.checked)}
          type="checkbox"
        />
      </label>
      <input
        className="mt-3 h-10 w-full rounded-md border bg-background px-3 text-sm"
        disabled={!checked}
        onChange={(event) => onTimeChange(event.target.value)}
        type="time"
        value={timeValue}
      />
    </div>
  );
}


function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}


function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong.";
}
