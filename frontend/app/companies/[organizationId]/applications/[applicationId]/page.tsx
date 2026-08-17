"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, ApplicationDetail } from "@/lib/api";

export default function CandidateDetail() {
  const { organizationId: orgId, applicationId } = useParams<{ organizationId: string; applicationId: string }>();
  const [data, setData] = useState<ApplicationDetail | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!orgId || !applicationId) return;
    api<ApplicationDetail>(`/organizations/${orgId}/applications/${applicationId}`).then(setData).catch((e) => setError(e.message));
  }, [orgId, applicationId]);
  if (error) return <div className="shell"><p className="error">{error}</p></div>;
  if (!data) return <div className="shell"><p>Loading score details…</p></div>;
  return <div className="shell">
    <Link className="back" href={`/companies/${orgId}/jobs/${data.job.id}`}>← {data.job.title}</Link>
    <div className="candidateHero"><div><p className="eyebrow">CANDIDATE EVIDENCE REPORT</p><h1>{data.candidate.full_name}</h1><p className="muted">{data.candidate.email} · Rubric v{data.rubric.version}</p></div><div className="bigScore"><strong>{data.score_percentage ?? "—"}%</strong><span>{data.aggregate_score ?? "—"} / 5</span></div></div>
    {data.review_reason && <section className="notice amberNotice"><div><strong>Recruiter review needed</strong><p>{data.review_reason}</p></div></section>}
    <section className="scoreList">{data.scores.map((score) => <article className="scoreCard" key={score.id}><div className="scoreTop"><span className="number">{score.requirement.position}</span><div className="grow"><h2>{score.requirement.title}</h2><p>{score.requirement.description}</p></div><div className="reqScore"><strong>{score.score}</strong><span>/ 5 · {score.requirement.weight}%</span></div></div><div className="scoreBody"><div><h3>Assessment</h3><p>{score.rationale}</p><div className="confidence">Confidence {Math.round(score.confidence * 100)}%{score.needs_review && <span>Review</span>}</div>{score.gaps.length > 0 && <><h3>Unverified or missing terms</h3><div className="tags">{score.gaps.map((gap) => <span key={gap}>{gap}</span>)}</div></>}</div><div><h3>CV evidence</h3>{score.evidence.length ? score.evidence.map((evidence, index) => <blockquote key={index}><small>{evidence.location}</small>{evidence.text}</blockquote>) : <p className="muted">No direct evidence retrieved.</p>}</div></div></article>)}</section>
    <p className="disclaimer">This report supports—not replaces—meaningful human review. Verify evidence against the original CV before making an employment decision.</p>
  </div>;
}
