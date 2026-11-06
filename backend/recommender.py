from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any


FIELDS = (
    "scheme_id", "scheme_name", "government_department", "category", "description",
    "eligibility_criteria", "minimum_age", "maximum_age", "gender_eligibility",
    "income_limit", "state_eligibility", "education_requirement", "occupation_requirement",
    "benefits", "application_process", "official_website", "required_documents",
    "verification_status", "source_note",
)

PROFILE_LIMITS = {
    "age": (0, 120),
    "annual_income": (0, 1_000_000_000),
}


def load_schemes(csv_path: str | Path) -> list[dict[str, str]]:
    with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = set(FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Scheme data is missing columns: {', '.join(sorted(missing))}")
        return [
            {field: (row.get(field) or "").strip() for field in FIELDS}
            for row in reader
            if row.get("scheme_id") and row.get("scheme_name")
        ]


def _unknown(value: Any) -> bool:
    return value is None or str(value).strip().casefold() in {
        "", "unknown", "unknown - verify", "not catalogued", "not applicable", "n/a"
    }


def _number(value: Any) -> float | None:
    if _unknown(value):
        return None
    found = re.search(r"\d[\d,]*(?:\.\d+)?", str(value))
    return float(found.group(0).replace(",", "")) if found else None


def _normalise_profile(profile: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "interests", "age", "state", "gender", "annual_income", "education",
        "employment_status", "occupation", "category",
    }
    unknown_keys = set(profile) - allowed
    if unknown_keys:
        raise ValueError(f"Unsupported profile field: {sorted(unknown_keys)[0]}")
    clean = {key: value for key, value in profile.items() if value is not None and str(value).strip()}
    for key, (minimum, maximum) in PROFILE_LIMITS.items():
        if key in clean:
            try:
                value = float(clean[key])
            except (TypeError, ValueError) as error:
                raise ValueError(f"{key.replace('_', ' ').title()} must be a number.") from error
            if not minimum <= value <= maximum:
                raise ValueError(f"{key.replace('_', ' ').title()} must be between {minimum:,} and {maximum:,}.")
            clean[key] = value
    for key, value in clean.items():
        if not isinstance(value, (str, int, float, list)):
            raise ValueError(f"{key.replace('_', ' ').title()} has an invalid value.")
        if isinstance(value, str) and len(value) > 120:
            raise ValueError(f"{key.replace('_', ' ').title()} must be 120 characters or fewer.")
    return clean


def _matches_text(user_value: Any, scheme_value: str) -> bool | None:
    if _unknown(scheme_value) or not user_value:
        return None
    value = str(user_value).casefold().strip()
    rule = scheme_value.casefold().strip()
    if rule in {"all india", "all states", "all genders", "any", "open to all"}:
        return True
    return value in rule or rule in value


def _matches_category(user_value: Any, criteria: str) -> bool | None:
    if _unknown(criteria) or not user_value:
        return None
    labels = {
        label for label in ("SC", "ST", "OBC", "EBC", "EWS", "General", "Minority")
        if re.search(rf"\b{re.escape(label)}\b", criteria, re.IGNORECASE)
    }
    if not labels:
        return None
    return str(user_value).casefold() in {label.casefold() for label in labels}


def _score_one(scheme: dict[str, str], profile: dict[str, Any]) -> dict[str, Any] | None:
    points = 0
    reasons: list[str] = []
    unresolved: list[str] = []

    interests = profile.get("interests", [])
    if isinstance(interests, str):
        interests = [part.strip() for part in re.split(r"[,;]", interests) if part.strip()]
    interest_terms = [str(term).casefold() for term in interests]
    category = scheme["category"].casefold()
    name = scheme["scheme_name"].casefold()
    if any(term in category or category in term or term in name for term in interest_terms):
        points += 6
        reasons.append(f"Matches your interest in {scheme['category'].lower()}.")

    age = profile.get("age")
    if age is not None:
        minimum, maximum = _number(scheme["minimum_age"]), _number(scheme["maximum_age"])
        if minimum is not None and age < minimum or maximum is not None and age > maximum:
            return None
        if minimum is not None or maximum is not None:
            points += 2
            reasons.append("Your age is within the listed age range.")
        else:
            unresolved.append("Age criteria are not catalogued.")

    income = profile.get("annual_income")
    if income is not None:
        limit = _number(scheme["income_limit"])
        if limit is not None and income > limit:
            return None
        if limit is not None:
            points += 2
            reasons.append("Your stated income is within the listed limit.")
        else:
            unresolved.append("Income criteria are not catalogued.")

    for profile_key, scheme_key, label, weight in (
        ("state", "state_eligibility", "State", 3),
        ("gender", "gender_eligibility", "Gender", 1),
        ("education", "education_requirement", "Education", 1),
        ("occupation", "occupation_requirement", "Occupation", 2),
    ):
        user_value = profile.get(profile_key)
        if profile_key == "occupation" and not user_value:
            user_value = profile.get("employment_status")
        if not user_value:
            continue
        match = _matches_text(user_value, scheme[scheme_key])
        if match is False:
            return None
        if match is True:
            points += weight
            reasons.append(f"{label} information is consistent with the listed criteria.")
        else:
            unresolved.append(f"{label} criteria are not catalogued.")

    category_match = _matches_category(profile.get("category"), scheme["eligibility_criteria"])
    if category_match is False:
        return None
    if category_match is True:
        points += 1
        reasons.append("Your social category is listed in the eligibility criteria.")
    elif profile.get("category"):
        unresolved.append("Social category criteria are not catalogued.")

    if not reasons:
        reasons.append("Shown as a candidate because no listed rule conflicts with the information provided.")
    score = min(100, 25 + points * 8)
    return {
        **scheme,
        "relevance_score": score,
        "recommendation_reasons": reasons,
        "verification_notes": list(dict.fromkeys(unresolved)),
        "eligibility_status": "Needs verification" if unresolved else "No listed conflicts",
    }


def recommend_schemes(schemes: list[dict[str, str]], profile: dict[str, Any], limit: int = 12) -> list[dict[str, Any]]:
    clean = _normalise_profile(profile)
    ranked = [result for scheme in schemes if (result := _score_one(scheme, clean)) is not None]
    ranked.sort(key=lambda result: (result["relevance_score"], result["scheme_name"].casefold()), reverse=True)
    return ranked[:max(1, min(int(limit), 50))]