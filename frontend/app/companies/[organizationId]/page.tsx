"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, Job } from "@/lib/api";

export default function CompanyPage() {
  const { organizationId: orgId } = useParams<{ organizationId: string }>();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [form, setForm] = useState({ title: "", location: "", jd_text: "" });
  const [error, setError] = useState("");
  const load = () => {
    if (!orgId) return Promise.resolve();
    return api<Job[]>(`/organizations/${orgId}/jobs`).then(setJobs).catch((e) => setError(e.message));
  };
  useEffect(() => { void load(); }, [orgId]);

  async function createJob(event: FormEvent) {
    event.preventDefault(); setError("");
    try {
      const job = await api<Job>(`/organizations/${orgId}/jobs`, { method: "POST", body: JSON.stringify(form) });
      window.location.href = `/companies/${orgId}/jobs/${job.id}`;
    } catch (e) { setError((e as Error).message); }
  }

  return (
    <div className="shell">
      <Link href="/" className="back">← All companies</Link>
      <div className="pageTitle"><div><p className="eyebrow">COMPANY WORKSPACE</p><h1>Jobs &amp; screening</h1></div><div className="titleActions"><Link className="architectureLink" href={`/companies/${orgId}/architecture`}>View product architecture</Link><span className="pill">{jobs.length} jobs</span></div></div>
      <div className="grid two wideLeft">
        <section className="panel">
          <div className="panelHeader"><h2>Job descriptions</h2></div>
          <div className="list">
            {jobs.map((job) => <Link className="row" key={job.id} href={`/companies/${orgId}/jobs/${job.id}`}><span><strong>{job.title}</strong><small>{job.location || "Location not specified"}</small></span><span className="arrow">→</span></Link>)}
            {!jobs.length && <p className="empty">No jobs yet. Add the first JD.</p>}
          </div>
        </section>
        <section className="panel">
          <p className="eyebrow">NEW JOB</p><h2>Add a job description</h2>
          <form className="stack" onSubmit={createJob}>
            <label>Job title<input required minLength={2} value={form.title} onChange={(e) => setForm({...form, title: e.target.value})} /></label>
            <label>Location<input value={form.location} onChange={(e) => setForm({...form, location: e.target.value})} placeholder="Remote / New York" /></label>
            <label>Job description<textarea required minLength={30} rows={10} value={form.jd_text} onChange={(e) => setForm({...form, jd_text: e.target.value})} placeholder="Paste the complete JD here…" /></label>
            <button>Create job &amp; build rubric</button>{error && <p className="error">{error}</p>}
          </form>
        </section>
      </div>
    </div>
  );
}
