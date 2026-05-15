"""Parse PDF CVs and match candidates to jobs.

We extract text with ``pypdf`` and run a deterministic, dictionary-based
analyzer rather than a heavy ML model — this keeps the project portable
and offline-friendly while giving a solid match score.

The matcher returns:
- a sorted list of matched jobs with score + missing skills
- a list of skill suggestions when no good match is found
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

try:
    from pypdf import PdfReader  # type: ignore
except Exception:  # pragma: no cover - pypdf is required at runtime
    PdfReader = None  # type: ignore


logger = logging.getLogger(__name__)


# Canonical skill keywords. The matcher recognises any of the aliases
# but stores the canonical name.
SKILL_DICTIONARY: dict[str, list[str]] = {
    "python": ["python", "py"],
    "javascript": ["javascript", "js", "ecmascript"],
    "typescript": ["typescript", "ts"],
    "java": ["java"],
    "kotlin": ["kotlin"],
    "swift": ["swift"],
    "c++": ["c++", "cpp"],
    "c#": ["c#", "csharp"],
    "go": ["golang", " go "],
    "rust": ["rust"],
    "php": ["php"],
    "ruby": ["ruby", "rails"],
    "sql": ["sql", "mysql", "postgresql", "postgres", "sqlite", "mssql"],
    "nosql": ["mongodb", "mongo", "redis", "cassandra", "dynamodb"],
    "html": ["html", "html5"],
    "css": ["css", "css3", "scss", "sass", "tailwind"],
    "react": ["react", "reactjs", "react.js", "next.js", "nextjs"],
    "vue": ["vue", "vuejs", "nuxt"],
    "angular": ["angular", "angularjs"],
    "nodejs": ["node", "nodejs", "node.js", "express"],
    "django": ["django"],
    "flask": ["flask", "fastapi"],
    "spring": ["spring", "spring boot"],
    "laravel": ["laravel"],
    "git": ["git", "github", "gitlab", "bitbucket"],
    "docker": ["docker", "container"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services"],
    "gcp": ["gcp", "google cloud"],
    "azure": ["azure"],
    "linux": ["linux", "ubuntu", "debian", "centos"],
    "rest api": ["rest api", "restful", "rest"],
    "graphql": ["graphql"],
    "machine learning": ["machine learning", "ml", "deep learning", "ai", "tensorflow", "pytorch"],
    "data science": ["data science", "pandas", "numpy", "scikit", "data analyst"],
    "excel": ["microsoft excel", "ms excel", "excel", "spreadsheet"],
    "word": ["microsoft word", "ms word"],
    "powerpoint": ["powerpoint", "ppt", "presentation"],
    "english": ["english", "bahasa inggris", "toefl", "ielts"],
    "design": ["ui", "ux", "figma", "photoshop", "illustrator", "design"],
    "accounting": ["accounting", "akuntansi", "pajak", "pembukuan"],
    "marketing": ["marketing", "digital marketing", "seo", "sem", "social media"],
    "sales": ["sales", "penjualan", "b2b", "b2c"],
    "hr": ["hr", "human resource", "recruitment", "recruiter"],
    "customer service": ["customer service", "cs", "customer support"],
    "leadership": ["leadership", "team lead", "manajerial", "management"],
    "communication": ["communication", "komunikasi", "public speaking"],
    "problem solving": ["problem solving", "analytical"],
    "project management": ["project management", "scrum", "agile", "kanban", "jira", "pmp"],
}


@dataclass
class CVData:
    raw_text: str
    skills: list[str]
    age: int | None
    experience_years: int


def extract_text_from_pdf(path: str | Path) -> str:
    if PdfReader is None:  # pragma: no cover
        raise RuntimeError("pypdf is not installed")
    path = Path(path)
    text_parts: list[str] = []
    try:
        reader = PdfReader(str(path))
        for page in reader.pages:
            try:
                text_parts.append(page.extract_text() or "")
            except Exception as exc:  # pragma: no cover - corrupt page
                logger.warning("pypdf page extract failed: %s", exc)
        return "\n".join(text_parts)
    except Exception as exc:
        logger.exception("Failed to read PDF %s: %s", path, exc)
        return ""


def _detect_skills(text_lower: str) -> list[str]:
    found: list[str] = []
    for canonical, aliases in SKILL_DICTIONARY.items():
        for alias in aliases:
            pat = re.compile(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])")
            if pat.search(text_lower):
                found.append(canonical)
                break
    return sorted(set(found))


def _detect_age(text: str) -> int | None:
    # Try to find "umur 24", "age 25", "berusia 28"
    for pat in (
        r"(?:umur|usia|age|berusia)\s*[:\-]?\s*(\d{2})",
        r"(\d{2})\s*(?:tahun|years old|yo)",
    ):
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            age = int(m.group(1))
            if 14 <= age <= 90:
                return age
    # Try to find a date of birth and compute age
    m = re.search(
        r"(?:tanggal lahir|date of birth|dob|tempat[, ]+tanggal lahir)[^\d]*"
        r"(\d{1,2})[\s\-/](\d{1,2}|jan|feb|mar|apr|mei|may|jun|jul|agu|aug|sep|okt|oct|nov|des|dec)"
        r"[\s\-/](\d{4})",
        text,
        re.IGNORECASE,
    )
    if m:
        day = int(m.group(1))
        mon_raw = m.group(2)
        year = int(m.group(3))
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "may": 5,
            "jun": 6, "jul": 7, "agu": 8, "aug": 8, "sep": 9, "okt": 10,
            "oct": 10, "nov": 11, "des": 12, "dec": 12,
        }
        try:
            month = int(mon_raw)
        except ValueError:
            month = months.get(mon_raw.lower()[:3], 1)
        try:
            dob = datetime(year, month, day)
            today = datetime.utcnow()
            age = today.year - dob.year - (
                (today.month, today.day) < (dob.month, dob.day)
            )
            if 14 <= age <= 90:
                return age
        except ValueError:
            return None
    return None


def _detect_experience_years(text: str) -> int:
    """Estimate years of professional experience.

    Combines explicit mentions ("3 tahun pengalaman") with date ranges
    on the CV (e.g. ``2020 - 2023``). Returns the maximum found, capped
    at 50.
    """
    years_found: list[int] = []
    for m in re.finditer(
        r"(\d{1,2})\s*(?:tahun|year[s]?)\s*(?:pengalaman|of experience|experience)",
        text,
        re.IGNORECASE,
    ):
        years_found.append(int(m.group(1)))

    # date ranges like 2018 - 2023 or 2019-Present
    total_from_ranges = 0
    for m in re.finditer(
        r"(19\d{2}|20\d{2})\s*[-–—to]+\s*(19\d{2}|20\d{2}|present|sekarang|now)",
        text,
        re.IGNORECASE,
    ):
        start = int(m.group(1))
        end_raw = m.group(2)
        try:
            end = int(end_raw)
        except ValueError:
            end = datetime.utcnow().year
        if 1970 <= start <= end <= datetime.utcnow().year + 1:
            total_from_ranges += max(0, end - start)
    years_found.append(min(total_from_ranges, 50))
    return max(years_found) if years_found else 0


def parse_cv(file_path: str | Path) -> CVData:
    raw = extract_text_from_pdf(file_path)
    text_lower = raw.lower()
    skills = _detect_skills(text_lower)
    age = _detect_age(raw)
    exp = _detect_experience_years(raw)
    return CVData(raw_text=raw, skills=skills, age=age, experience_years=exp)


# -----------------------------
# Matching
# -----------------------------


@dataclass
class JobMatch:
    job_id: int
    job_title: str
    company_id: int
    company_name: str
    score: int
    matched_skills: list[str]
    missing_skills: list[str]
    age_ok: bool
    experience_ok: bool


def _split_skills(blob: str | None) -> list[str]:
    if not blob:
        return []
    return [s.strip().lower() for s in blob.split(",") if s.strip()]


def match_jobs_for_cv(
    cv: CVData, jobs: Iterable[dict], top_n: int = 20
) -> list[JobMatch]:
    matches: list[JobMatch] = []
    user_skills = set(cv.skills)
    for job in jobs:
        job_skills = set(_split_skills(job.get("skills")))
        if not job_skills:
            continue
        matched = sorted(user_skills & job_skills)
        missing = sorted(job_skills - user_skills)
        skill_score = (len(matched) / len(job_skills)) * 80.0
        exp_ok = cv.experience_years >= int(job.get("min_experience") or 0)
        exp_score = 10.0 if exp_ok else 0.0
        age = cv.age
        min_age = job.get("min_age")
        max_age = job.get("max_age")
        if age is None:
            age_ok = True
        else:
            age_ok = (min_age is None or age >= int(min_age)) and (
                max_age is None or age <= int(max_age)
            )
        age_score = 10.0 if age_ok else 0.0
        score = int(round(skill_score + exp_score + age_score))
        matches.append(
            JobMatch(
                job_id=int(job["id"]),
                job_title=str(job.get("title", "")),
                company_id=int(job.get("company_id", 0)),
                company_name=str(job.get("company_name", "")),
                score=score,
                matched_skills=matched,
                missing_skills=missing,
                age_ok=age_ok,
                experience_ok=exp_ok,
            )
        )
    matches.sort(key=lambda m: m.score, reverse=True)
    return matches[:top_n]


def suggest_skills_to_improve(matches: list[JobMatch], limit: int = 8) -> list[str]:
    """Compile a ranked list of skills the user is missing most often."""
    counts: dict[str, int] = {}
    for m in matches:
        for s in m.missing_skills:
            counts[s] = counts.get(s, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [name for name, _ in ranked[:limit]]
