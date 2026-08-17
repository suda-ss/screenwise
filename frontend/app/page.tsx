"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Organization } from "@/lib/api";

export default function Home() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [error, setError] = useState("");

  const load = () => api<Organization[]>("/organizations").then(setOrganizations).catch((e) => setError(e.message));
  useEffect(() => { void load(); }, []);

  return (
    <div className="shell">
      <section className="hero">
        <p className="eyebrow">MULTI-COMPANY RECRUITING</p>
        <h1>Match evidence to requirements,<br />not people to assumptions.</h1>
        <p className="lede">Create a company workspace, define job rubrics, and review transparent CV scores with source evidence.</p>
      </section>
      <div className="grid two">
        <section className="panel">
          <div className="panelHeader"><h2>Company workspaces</h2><span>{organizations.length}</span></div>
          <div className="list">
            {organizations.map((org) => (
              <Link key={org.id} className="row" href={`/companies/${org.id}`}>
                <span className="avatar">{org.name.slice(0, 2).toUpperCase()}</span>
                <span><strong>{org.name}</strong><small>{org.slug}</small></span>
                <span className="arrow">→</span>
              </Link>
            ))}
            {!organizations.length && <p className="empty">Create your first company workspace.</p>}
          </div>
        </section>
        <section className="panel warm companyRule">
          <p className="eyebrow">YOUR COMPANY</p>
          <h2>One focused workspace</h2>
          <p className="muted">Your account belongs to one company. Inside that workspace you can create as many job descriptions and screening pipelines as needed.</p>
          {organizations[0] && <Link className="companyCta" href={`/companies/${organizations[0].id}`}>Open {organizations[0].name} <span>→</span></Link>}
          {error && <p className="error">{error}</p>}
        </section>
      </div>
    </div>
  );
}
