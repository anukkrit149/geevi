import { LoginForm } from "@/features/session/LoginForm";

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ returnTo?: string }> }) {
  return <LoginForm returnTo={(await searchParams).returnTo} />;
}
