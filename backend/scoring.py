from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .models import Requirement


TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9+#.\-]{1,}")
STOP_WORDS = {
    "and", "the", "with", "for", "that", "from", "this", "will", "are", "you",
    "our", "have", "has", "job", "role", "work", "years", "experience", "required",
}


@dataclass
class ScoreResult:
    score: float
    confidence: float
    rationale: str
    evidence: list[dict]
    gaps: list[str]
    needs_review: bool


def tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text) if token.lower() not in STOP_WORDS}


def evidence_segments(cv_text: str, terms: set[str], limit: int = 3) -> list[dict]:
    lines = [line.strip() for line in cv_text.splitlines() if len(line.strip()) >= 15]
    ranked = []
    for index, line in enumerate(lines):
        overlap = terms & tokens(line)
        if overlap:
            ranked.append((len(overlap), index, line, sorted(overlap)))
    ranked.sort(reverse=True)
    return [
        {"location": f"line {index + 1}", "text": line[:500], "matched_terms": matched}
        for _, index, line, matched in ranked[:limit]
    ]


def score_requirement(requirement: Requirement, cv_text: str) -> ScoreResult:
    requirement_terms = tokens(requirement.title + " " + requirement.description)
    requirement_terms.update(item.lower() for item in (requirement.keywords or []))
    evidence = evidence_segments(cv_text, requirement_terms)
    matched = set().union(*(set(item["matched_terms"]) for item in evidence)) if evidence else set()
    coverage = len(matched) / max(len(requirement_terms), 1)
    evidence_depth = min(len(evidence) / 2, 1)
    raw = 5 * (0.75 * min(coverage * 2.5, 1) + 0.25 * evidence_depth)
    score = round(min(5, max(0, raw)) * 2) / 2
    confidence = round(min(0.95, 0.35 + coverage + 0.1 * len(evidence)), 2)
    missing = sorted(requirement_terms - matched)[:8]
    if evidence:
        rationale = (
            f"Found {len(evidence)} relevant CV passage(s) covering "
            f"{len(matched)} rubric term(s). This provisional score requires recruiter review."
        )
    else:
        rationale = "No directly matching evidence was found in the extracted CV text."
    needs_review = confidence < 0.6 or not evidence or math.isclose(score, 0)
    return ScoreResult(score, confidence, rationale, evidence, missing, needs_review)


def default_anchors() -> dict[str, str]:
    return {
        "0": "No relevant evidence found",
        "1": "Minimal or weakly related evidence",
        "2": "Partial evidence with important gaps",
        "3": "Meets the requirement",
        "4": "Strong evidence exceeding the baseline",
        "5": "Exceptional and directly supported evidence",
    }


def suggest_requirements(jd_text: str) -> list[dict]:
    lines = [line.strip(" -•\t") for line in jd_text.splitlines() if len(line.strip()) >= 18]
    candidates = []
    seen: set[str] = set()
    priority_markers = ("must", "required", "minimum", "proficient", "experience", "certification")
    prioritized = sorted(lines, key=lambda line: any(marker in line.lower() for marker in priority_markers), reverse=True)
    for line in prioritized:
        key_terms = sorted(tokens(line), key=len, reverse=True)[:8]
        signature = " ".join(key_terms[:3])
        if not key_terms or signature in seen:
            continue
        seen.add(signature)
        candidates.append({"title": line[:100], "description": line[:500], "keywords": key_terms})
        if len(candidates) == 5:
            break
    if not candidates:
        candidates.append({"title": "Relevant experience", "description": jd_text[:500], "keywords": sorted(tokens(jd_text))[:8]})
    weight = round(100 / len(candidates), 2)
    for item in candidates:
        item["weight"] = weight
    candidates[-1]["weight"] = round(100 - sum(item["weight"] for item in candidates[:-1]), 2)
    return candidates
