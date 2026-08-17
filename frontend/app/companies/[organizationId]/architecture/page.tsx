import Link from "next/link";

const pipeline = [
  ["01", "Company access", "The owner registers one company workspace. Sessions and membership checks isolate every job, candidate, document, and score."],
  ["02", "JD knowledge", "The company creates a job, supplies its JD, and the system normalizes it into retrievable job knowledge."],
  ["03", "Rubric approval", "Agents propose up to five key requirements. The recruiter reviews weights and scoring anchors, then locks a version."],
  ["04", "Candidate intake", "CVs arrive through protected PDF, DOCX, or text upload—or through an idempotent ATS webhook."],
  ["05", "Evidence retrieval", "CV content becomes traceable passages. Retrieval finds evidence independently for each locked requirement."],
  ["06", "Scoring & validation", "Each requirement receives a 0–5 score, confidence, rationale, evidence, and gaps. Unsupported results are flagged."],
  ["07", "Deterministic result", "Application code calculates the weighted average. Low-confidence cases go to review, never silent rejection."],
  ["08", "Human decision", "Recruiters inspect every score and source passage before making an employment decision."],
];

const agents = [
  ["JD Analyst", "Extracts atomic requirements with JD citations."],
  ["Rubric Builder", "Creates anchored criteria and detects overlap."],
  ["CV Parser", "Builds a profile while excluding sensitive traits."],
  ["Evidence Retriever", "Finds CV evidence for each requirement."],
  ["Requirement Scorer", "Scores only cited evidence against the rubric."],
  ["Validator", "Checks citations, consistency, and confidence."],
  ["Report Agent", "Creates the recruiter summary without new claims."],
];

export default async function ArchitecturePage({ params }: { params: Promise<{ organizationId: string }> }) {
  const { organizationId } = await params;
  return <div className="shell architecturePage">
    <Link className="back" href={`/companies/${organizationId}`}>← Company dashboard</Link>
    <section className="architectureHero"><div><p className="eyebrow">OWNER VIEW · PRODUCT ARCHITECTURE</p><h1>From job description<br />to defensible review.</h1><p>Screenwise combines tenant isolation, a versioned rubric, traceable CV evidence, specialized agents, and mandatory human review.</p></div><div className="architectureLegend"><span><i className="dot greenDot" /> Automated workflow</span><span><i className="dot limeDot" /> Human approval gate</span><span><i className="dot amberDot" /> Review required</span></div></section>
    <section className="architectureFlow">{pipeline.map(([number, title, detail], index) => <article className="flowStage" key={number}><div className="flowNumber">{number}</div><h2>{title}</h2><p>{detail}</p>{index < pipeline.length - 1 && <span className="flowArrow">↓</span>}</article>)}</section>
    <div className="architectureGrid"><section className="panel"><p className="eyebrow">MULTI-AGENT LAYER</p><h2>Specialists with narrow authority</h2><div className="agentGrid">{agents.map(([name, description], index) => <div className="agentCard" key={name}><span>A{index + 1}</span><div><strong>{name}</strong><p>{description}</p></div></div>)}</div></section><section className="panel darkPanel"><p className="eyebrow">SYSTEM BOUNDARIES</p><h2>What stays deterministic</h2><ul className="boundaryList"><li><strong>Authentication</strong><span>PBKDF2 passwords and opaque HttpOnly sessions</span></li><li><strong>Authorization</strong><span>Server-side company membership on every query</span></li><li><strong>Rubric version</strong><span>Locked before candidates enter scoring</span></li><li><strong>Aggregate score</strong><span>Weighted in application code, never by a model</span></li><li><strong>Hiring decision</strong><span>Always owned by a human reviewer</span></li></ul></section></div>
    <section className="dataFlow"><p className="eyebrow">DATA &amp; INFRASTRUCTURE</p><div className="dataNodes"><span>Next.js<small>Recruiter UI</small></span><b>→</b><span>FastAPI<small>Auth &amp; workflow</small></span><b>→</b><span>PostgreSQL<small>Jobs &amp; scores</small></span><b>+</b><span>Object storage<small>Private CVs</small></span><b>+</b><span>Agent adapters<small>Reasoning</small></span></div></section>
    <p className="disclaimer">CV text is untrusted input. Protected traits are excluded from scoring where feasible, and every recommendation remains subject to meaningful human review.</p>
  </div>;
}
