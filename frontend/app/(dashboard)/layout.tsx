"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { UserProvider, useUser } from "@/contexts/UserContext";

function Nav() {
  const router = useRouter();
  const pathname = usePathname();
  const { user } = useUser();

  function handleLogout() {
    localStorage.removeItem("access_token");
    router.replace("/login");
  }

  const navItems = [
    { href: "/dashboard", label: "Overview" },
    { href: "/targets", label: "Targets" },
    { href: "/agent-scans", label: "Agent Scans" },
    { href: "/schedules", label: "Schedules" },
    ...(user?.role === "admin" ? [{ href: "/users", label: "Users" }] : []),
  ];

  return (
    <nav className="border-b border-border bg-card px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <span className="font-semibold text-primary tracking-tight">SentinelAI</span>
        <div className="flex gap-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                pathname === item.href
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-3">
        {user && (
          <span className="text-xs text-muted-foreground">
            {user.email} · <span className="capitalize">{user.role}</span>
          </span>
        )}
        <button
          onClick={handleLogout}
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Sign out
        </button>
      </div>
    </nav>
  );
}

function LayoutInner({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
    }
  }, [router]);

  return (
    <div className="min-h-screen bg-background">
      <Nav />
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <UserProvider>
      <LayoutInner>{children}</LayoutInner>
    </UserProvider>
  );
}
