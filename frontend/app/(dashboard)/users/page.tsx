"use client";

import { useEffect, useState } from "react";
import {
  listUsers,
  inviteUser,
  updateUserRole,
  removeUser,
  type OrgUser,
  ApiError,
} from "@/lib/api";
import { useUser } from "@/contexts/UserContext";
import { useRouter } from "next/navigation";

const ROLES = ["admin", "analyst", "viewer"] as const;

export default function UsersPage() {
  const { user: currentUser, loading } = useUser();
  const router = useRouter();
  const [users, setUsers] = useState<OrgUser[]>([]);
  const [fetchError, setFetchError] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "analyst" | "viewer">("analyst");
  const [inviteError, setInviteError] = useState("");
  const [inviting, setInviting] = useState(false);

  useEffect(() => {
    if (!loading && currentUser?.role !== "admin") {
      router.replace("/dashboard");
    }
  }, [currentUser, loading, router]);

  useEffect(() => {
    if (currentUser?.role === "admin") {
      listUsers()
        .then(setUsers)
        .catch((e) => setFetchError(e.message));
    }
  }, [currentUser]);

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    setInviteError("");
    setInviting(true);
    try {
      const newUser = await inviteUser(email, password, role);
      setUsers((prev) => [...prev, newUser]);
      setEmail("");
      setPassword("");
      setRole("analyst");
    } catch (e) {
      setInviteError(e instanceof ApiError ? e.message : "Invite failed");
    } finally {
      setInviting(false);
    }
  }

  async function handleRoleChange(userId: string, newRole: "admin" | "analyst" | "viewer") {
    try {
      const updated = await updateUserRole(userId, newRole);
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
    } catch (e) {
      alert(e instanceof ApiError ? e.message : "Role update failed");
    }
  }

  async function handleRemove(userId: string) {
    if (!confirm("Remove this user from the org?")) return;
    try {
      await removeUser(userId);
      setUsers((prev) => prev.filter((u) => u.id !== userId));
    } catch (e) {
      alert(e instanceof ApiError ? e.message : "Remove failed");
    }
  }

  if (loading) return null;
  if (currentUser?.role !== "admin") return null;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">Team Members</h1>

      {fetchError && <p className="text-destructive text-sm">{fetchError}</p>}

      <div className="rounded-lg border border-border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="border-b border-border bg-muted/40">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Email</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Role</th>
              <th className="px-4 py-3 text-left font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3">{u.email}</td>
                <td className="px-4 py-3">
                  {u.id === currentUser.id ? (
                    <span className="capitalize text-muted-foreground">{u.role} (you)</span>
                  ) : (
                    <select
                      value={u.role}
                      onChange={(e) =>
                        handleRoleChange(u.id, e.target.value as "admin" | "analyst" | "viewer")
                      }
                      className="rounded border border-border bg-background px-2 py-1 text-sm capitalize"
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r} className="capitalize">
                          {r}
                        </option>
                      ))}
                    </select>
                  )}
                </td>
                <td className="px-4 py-3">
                  {u.id !== currentUser.id && (
                    <button
                      onClick={() => handleRemove(u.id)}
                      className="text-destructive text-xs hover:underline"
                    >
                      Remove
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-muted-foreground">
                  No team members yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="rounded-lg border border-border bg-card p-6 space-y-4">
        <h2 className="font-semibold">Invite Team Member</h2>
        <form onSubmit={handleInvite} className="flex flex-wrap gap-3 items-end">
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded border border-border bg-background px-3 py-1.5 text-sm w-56"
              placeholder="user@example.com"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Temp Password</label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded border border-border bg-background px-3 py-1.5 text-sm w-40"
              placeholder="min 8 chars"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-muted-foreground">Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as typeof role)}
              className="rounded border border-border bg-background px-3 py-1.5 text-sm"
            >
              {ROLES.map((r) => (
                <option key={r} value={r} className="capitalize">
                  {r}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={inviting}
            className="rounded bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {inviting ? "Inviting…" : "Invite"}
          </button>
        </form>
        {inviteError && <p className="text-destructive text-sm">{inviteError}</p>}
      </div>
    </div>
  );
}
