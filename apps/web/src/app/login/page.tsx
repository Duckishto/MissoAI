"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ApiError, api, setAccessToken } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSignIn() {
    setBusy(true);
    setError(null);
    try {
      const { access_token } = await api.login(email, password);
      setAccessToken(access_token);
      router.push("/courses");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not reach the server. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-md px-6 py-24">
      <h1 className="reading text-2xl">Sign in</h1>

      <div className="mt-8 space-y-4">
        <label className="block">
          <span className="text-sm text-ink-2">Email</span>
          <input
            type="email"
            value={email}
            autoComplete="email"
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 w-full rounded-sm border bg-paper-raised px-3 py-2"
            style={{ borderColor: "var(--rule)" }}
          />
        </label>

        <label className="block">
          <span className="text-sm text-ink-2">Password</span>
          <input
            type="password"
            value={password}
            autoComplete="current-password"
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSignIn()}
            className="mt-1 w-full rounded-sm border bg-paper-raised px-3 py-2"
            style={{ borderColor: "var(--rule)" }}
          />
        </label>

        {error && (
          <p role="alert" className="text-sm" style={{ color: "var(--attention)" }}>
            {error}
          </p>
        )}

        <button
          onClick={handleSignIn}
          disabled={busy || !email || !password}
          className="w-full rounded-sm px-4 py-2.5 text-sm font-medium text-white disabled:opacity-40"
          style={{ background: "var(--observed)" }}
        >
          {busy ? "Signing in" : "Sign in"}
        </button>
      </div>
    </main>
  );
}
