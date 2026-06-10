import { AuthPanel } from "@/components/auth/auth-panel";
import { redirectAuthenticatedUser } from "@/lib/server-auth";


export default async function LoginPage() {
  await redirectAuthenticatedUser();

  return <AuthPanel />;
}
