import { DashboardOverview } from "@/components/dashboard/dashboard-overview";
import { PageHeader } from "@/components/page-header";


export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        description="Workspace summary built from saved profile records and resume templates."
        eyebrow="Dashboard"
        title="Workspace overview"
      />

      <DashboardOverview />
    </div>
  );
}
