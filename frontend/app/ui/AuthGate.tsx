"use client";

import Link from "next/link";
import { FormEvent, ReactNode, useEffect, useState } from "react";
import { api, Auth } from "@/lib/api";

type Mode = "login" | "register";

export default function AuthGate({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<Auth | null>(null);
  const [checking, setChecking] = useState(true);
  const [mode, setMode] = useState<Mode>("login");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", company_name: "", company_slug: "" });

  useEffect(() => {
    api<Auth>("/auth/me")
      .then(setAuth)
      .catch(() => setAuth(null))
      .finally(() => setChecking(false));
  }, []);

  function update(field: keyof typeof form, value: string) {
    if (field === "company_name") {
      const slug = value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      setForm({ ...form, company_name: value, company_slug: slug });
    } else {
      setForm({ ...form, [field]: value });
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setBusy(true);
    try {
      const normalizedSlug = form.company_slug.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      if (mode === "register" && !normalizedSlug) throw new Error("Enter a company name to create its workspace URL.");
      const payload = mode === "register"
        ? { ...form, email: form.email.trim().toLowerCase(), company_slug: normalizedSlug }
        : { email: form.email, password: form.password };
      const result = await api<Auth>(`/auth/${mode}`, { method: "POST", body: JSON.stringify(payload) });
      setAuth(result);
      window.location.href = result.organizations.length === 1 ? `/companies/${result.organizations[0].id}` : "/";
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }

  async function logout() {
    await api<never>("/auth/logout", { method: "POST" }).catch(() => undefined);
    setAuth(null); window.location.href = "/";
  }

  if (checking) return <div className="authPage"><div className="authCard"><p>Checking your secure session…</p></div></div>;

  if (!auth) return <div className="authPage">
    <section className="authStory"><Link href="/" className="brand"><span className="brandMark">S</span> Screenwise</Link><div><p className="eyebrow">EVIDENCE-LED HIRING</p><h1>Every requirement.<br />Every candidate.<br />Clearly scored.</h1><p>Private company workspaces for consistent, human-reviewed resume screening.</p></div><small>Candidate evidence stays isolated inside your company workspace.</small></section>
    <section className="authCard"><div className="authTabs"><button className={mode === "login" ? "active" : ""} onClick={() => { setMode("login"); setError(""); }}>Log in</button><button className={mode === "register" ? "active" : ""} onClick={() => { setMode("register"); setError(""); }}>Create company account</button></div><h2>{mode === "login" ? "Welcome back" : "Create your workspace"}</h2><p className="muted">{mode === "login" ? "Access your company screening dashboard." : "Your first account becomes the company owner."}</p>
      <form className="stack" onSubmit={submit}>
        {mode === "register" && <><label>Your name<input autoComplete="name" value={form.name} onChange={(e) => update("name", e.target.value)} required minLength={2} /></label><label>Company name<input autoComplete="organization" value={form.company_name} onChange={(e) => update("company_name", e.target.value)} required minLength={2} /></label><label>Company URL<input value={form.company_slug} onChange={(e) => update("company_slug", e.target.value)} required minLength={1} pattern="[A-Za-z0-9][A-Za-z0-9 -]*" title="Use letters, numbers, spaces, or hyphens" /><small>screenwise.local/{form.company_slug || "your-company"}</small></label></>}
        <label>Work email<input type="email" autoComplete="email" value={form.email} onChange={(e) => update("email", e.target.value)} required /></label>
        <label>Password<input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} value={form.password} onChange={(e) => update("password", e.target.value)} required minLength={mode === "register" ? 8 : undefined} /></label>
        <button disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Log in securely" : "Create company account"}</button>
        {error && <p className="error">{error}</p>}
      </form>
    </section>
  </div>;

  return <><header className="topbar"><Link href="/" className="brand"><span className="brandMark">S</span> Screenwise</Link><div className="accountNav"><span>{auth.user.display_name}<small>{auth.user.email}</small></span><button onClick={logout}>Log out</button></div></header><main>{children}</main></>;
}
