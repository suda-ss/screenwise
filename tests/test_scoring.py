from types import SimpleNamespace

from backend.scoring import score_requirement, suggest_requirements


def requirement(**overrides):
    values = {
        "title": "Python API development",
        "description": "Build production Python APIs using FastAPI",
        "keywords": ["python", "fastapi", "api"],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_score_returns_cited_evidence():
    result = score_requirement(
        requirement(),
        "Senior Engineer\nBuilt Python and FastAPI services for a production API platform.\nLed testing and deployment.",
    )
    assert result.score >= 3
    assert result.evidence
    assert "python" in result.evidence[0]["matched_terms"]


def test_missing_evidence_requires_review():
    result = score_requirement(requirement(), "Account executive focused on enterprise sales and renewals.")
    assert result.score == 0
    assert result.needs_review is True


def test_suggestions_have_at_most_five_requirements_and_total_weight():
    jd = "\n".join(
        [
            "Must have five years of Python development experience.",
            "Required experience building REST APIs with FastAPI.",
            "Strong PostgreSQL database design and optimization skills.",
            "Experience deploying services to AWS infrastructure.",
            "Excellent written communication with technical stakeholders.",
            "Preferred experience with Kubernetes orchestration.",
        ]
    )
    suggestions = suggest_requirements(jd)
    assert 1 <= len(suggestions) <= 5
    assert sum(item["weight"] for item in suggestions) == 100
