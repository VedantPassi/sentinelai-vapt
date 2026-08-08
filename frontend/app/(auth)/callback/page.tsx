"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

export default function AuthCallbackPage() {
  const router = useRouter();
  const params = useSearchParams();

  useEffect(() => {
    const token = params.get("token");
    if (token) {
      localStorage.setItem("access_token", token);
      router.replace("/dashboard");
    } else {
      router.replace("/login?error=sso_failed");
    }
  }, [params, router]);

  return (
    <div className="flex items-center justify-center min-h-screen">
      <p className="text-sm text-muted-foreground">Signing you in…</p>
    </div>
  );
}
