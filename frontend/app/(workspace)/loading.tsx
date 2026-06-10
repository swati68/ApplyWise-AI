import { Loader2 } from "lucide-react";


export default function WorkspaceLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background text-foreground">
      <div className="flex items-center gap-3 rounded-lg border bg-card px-4 py-3 text-sm text-muted-foreground shadow-sm">
        <Loader2 className="h-4 w-4 animate-spin" />
        Checking session
      </div>
    </div>
  );
}
