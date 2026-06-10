import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import { requireServerAuth } from "@/lib/server-auth";


type WorkspaceLayoutProps = Readonly<{
  children: ReactNode;
}>;


export default async function WorkspaceLayout({ children }: WorkspaceLayoutProps) {
  const user = await requireServerAuth();

  return <AppShell user={user}>{children}</AppShell>;
}
