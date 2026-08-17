"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, Application, Job, Rubric } from "@/lib/api";

type DraftRequirement = { title: string; description: string; weight: number; keywords: string[] };

export default function JobPage() {
  const { organizationId: orgId, jobId } = useParams<{ organizationId: string; jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [candidates, setCandidates] = useState<Application[]>([]);
  const [draft, setDraft] = useState<DraftRequirement[]>([]);
  const [error, setError] = useState("");
  const base = `/organizations/${orgId}/jobs/${jobId}`;

  async function load() {
    if (!orgId || !jobId) return;
    try {
      const [jobData, rubricData, candidateData] = await Promise.all([
        api<Job>(base), api<Rubric[]>(`${base}/rubrics`), api<Application[]>(`${base}/candidates`),
      ]);
      setJob(jobData); setRubrics(rubricData); setCandidates(candidateData);
    } catch (e) { setError((e as Error).message); }
  }
  useEffect(() => { load(); }, [orgId, jobId]);
  const approved = rubrics.find((item) => item.approved);

  async function suggest() {
    setError("");
    try {
      const response = await api<{ requirements: DraftRequirement[] }>(`${base}/rubrics/suggest`, { method: "POST" });
      setDraft(response.requirements);
    } catch (e) { setError((e as Error).message); }
  }

  function updateRequirement(index: number, field: keyof DraftRequirement, value: string | number) {
    setDraft(draft.map((item, i) => i === index ? { ...item, [field]: value } : item));
  }

  async function saveAndApprove() {
    setError("");
    try {
      const rubric = await api<Rubric>(`${base}/rubrics`, { method: "POST", body: JSON.stringify({ requirements: draft }) });
      await api<Rubric>(`${base}/rubrics/${rubric.id}/approve`, { method: "POST" });
      setDraft([]); await load();
    } catch (e) { setError((e as Error).message); }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    const data = new FormData(event.currentTarget);
    try {
      await api<Application>(`${base}/candidates/upload`, { method: "POST", body: data });
      event.currentTarget.reset(); setTimeout(load, 600);
    } catch (e) { setError((e as Error).message); }
  }

  return (
    <div className="shell">
      <Link className="back" href={`/companies/${orgId}`}>← Company jobs</Link>
      <div className="pageTitle"><div><p className="eyebrow">JOB SCREENING</p><h1>{job?.title || "Loading…"}</h1><p className="muted">{job?.location}</p></div><span className={`pill ${approved ? "green" : "amber"}`}>{approved ? `Rubric v${approved.version} locked` : "Rubric required"}</span></div>

      {!approved && !draft.length && <section className="notice"><div><strong>Build the screening rubric</strong><p>The system will propose up to five requirements. Review every requirement and weight before locking it.</p></div><button onClick={suggest}>Suggest requirements</button></section>}

      {!!draft.length && <section className="panel rubricEditor"><div className="panelHeader"><div><p className="eyebrow">RECRUITER APPROVAL REQUIRED</p><h2>Review top requirements</h2></div><span>{draft.reduce((sum, item) => sum + Number(item.weight), 0).toFixed(1)}% total</span></div>
        <div className="requirements">{draft.map((item, index) => <div className="requirementEdit" key={index}><span className="number">{index + 1}</span><div><input className="titleInput" value={item.title} onChange={(e) => updateRequirement(index, "title", e.target.value)} /><textarea rows={2} value={item.description} onChange={(e) => updateRequirement(index, "description", e.target.value)} /></div><label>Weight<input type="number" min="1" max="100" step="0.1" value={item.weight} onChange={(e) => updateRequirement(index, "weight", Number(e.target.value))} /></label></div>)}</div>
        <button onClick={saveAndApprove}>Approve and lock rubric</button>
      </section>}

      {approved && <div className="grid two wideLeft">
        <section className="panel">
          <div className="panelHeader"><h2>Candidates</h2><span>{candidates.length}</span></div>
          <div className="candidateHeader"><span>Candidate</span><span>Status</span><span>Score</span></div>
          {candidates.map((application) => <Link className="candidateRow" key={application.id} href={`/companies/${orgId}/applications/${application.id}`}><span><strong>{application.candidate.full_name}</strong><small>{application.candidate.email || "No email"}</small></span><span className={`status ${application.status}`}>{application.status.replace("_", " ")}</span><strong className="score">{application.score_percentage == null ? "—" : `${application.score_percentage}%`}</strong></Link>)}
          {!candidates.length && <p className="empty">No candidates screened for this JD.</p>}
        </section>
        <div className="stackSection">
          <section className="panel"><p className="eyebrow">ADD CANDIDATE</p><h2>Upload a CV</h2><form className="stack" onSubmit={upload}><label>Candidate name<input name="candidate_name" required /></label><label>Email<input name="candidate_email" type="email" /></label><label>CV (PDF, DOCX, or TXT)<input name="cv" type="file" accept=".pdf,.docx,.txt" required /></label><button>Upload and screen</button></form></section>
          <section className="panel compact"><p className="eyebrow">LOCKED RUBRIC</p>{approved.requirements.map((req) => <div className="miniReq" key={req.id}><span>{req.position}</span><p>{req.title}</p><strong>{req.weight}%</strong></div>)}</section>
        </div>
      </div>}
      {error && <p className="error banner">{error}</p>}
    </div>
  );
}
