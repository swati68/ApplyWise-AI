import { Clock3, Database } from "lucide-react";

import { PageHeader } from "@/components/page-header";
import { GoogleIntegrationSettings } from "@/components/settings/google-integration-settings";
import { SchedulerSettings } from "@/components/settings/scheduler-settings";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";


export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        description="Manage preferences and connected services."
        eyebrow="Settings"
        title="Settings"
      />

      <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
        <Card>
          <CardHeader>
            <CardTitle>Appearance</CardTitle>
            <CardDescription>Choose how the workspace looks.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between rounded-lg border p-4">
              <div>
                <p className="font-medium">Theme</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Switch between light and dark mode.
                </p>
              </div>
              <ThemeToggle />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-primary" />
              <CardTitle>Google Services</CardTitle>
            </div>
            <CardDescription>
              Connect Drive and Gmail when you want generated resumes delivered automatically.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <GoogleIntegrationSettings />
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Clock3 className="h-4 w-4 text-primary" />
            <CardTitle>Automation Scheduler</CardTitle>
          </div>
          <CardDescription>
            Schedule enabled GitHub sources to scan and generate resumes automatically.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <SchedulerSettings />
        </CardContent>
      </Card>
    </div>
  );
}
