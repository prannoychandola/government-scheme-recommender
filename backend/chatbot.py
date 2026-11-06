from __future__ import annotations

import re
from typing import Any

from backend.recommender import recommend_schemes


FLOW = [
    ("interests", "What would you like help with? Pick a focus area or type your own.", "select", [
        "Education and scholarships", "Employment and skill development", "Agriculture",
        "Women empowerment", "Healthcare", "Housing", "Financial assistance",
        "Social welfare", "Business and entrepreneurship",
    ], False),
    ("age", "What is your age?", "number", [], True),
    ("state", "Which Indian state or union territory do you live in?", "text", [], True),
    ("gender", "Would you like to share your gender? This is optional.", "select", ["Woman", "Man", "Non-binary", "Prefer not to say"], True),
    ("annual_income", "Approximate annual family income in rupees? You can skip this.", "number", [], True),
    ("education", "What is your highest completed education level?", "select", ["No formal schooling", "Primary", "Secondary", "Higher secondary", "Diploma or ITI", "Undergraduate", "Postgraduate", "Other"], True),
    ("employment_status", "What best describes your current employment status?", "select", ["Student", "Employed", "Self-employed", "Unemployed", "Farmer", "Homemaker", "Other"], True),
    ("occupation", "What is your occupation or work area?", "text", [], True),
    ("category", "Any social category you would like us to consider? This is optional.", "select", ["SC", "ST", "OBC", "General", "Prefer not to say"], True),
]

STATES_AND_TERRITORIES = {
    "andhra pradesh": "Andhra Pradesh", "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam", "bihar": "Bihar", "chhattisgarh": "Chhattisgarh", "goa": "Goa",
    "gujarat": "Gujarat", "haryana": "Haryana", "himachal pradesh": "Himachal Pradesh",
    "jharkhand": "Jharkhand", "karnataka": "Karnataka", "kerala": "Kerala",
    "madhya pradesh": "Madhya Pradesh", "maharashtra": "Maharashtra", "manipur": "Manipur",
    "meghalaya": "Meghalaya", "mizoram": "Mizoram", "nagaland": "Nagaland",
    "odisha": "Odisha", "orissa": "Odisha", "punjab": "Punjab", "rajasthan": "Rajasthan",
    "sikkim": "Sikkim", "tamil nadu": "Tamil Nadu", "telangana": "Telangana",
    "tripura": "Tripura", "uttar pradesh": "Uttar Pradesh", "uttarakhand": "Uttarakhand",
    "west bengal": "West Bengal", "andaman and nicobar islands": "Andaman and Nicobar Islands",
    "andaman and nicobar": "Andaman and Nicobar Islands", "chandigarh": "Chandigarh",
    "dadra and nagar haveli and daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "dadra and nagar haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "delhi": "Delhi", "nct delhi": "Delhi", "national capital territory of delhi": "Delhi",
    "jammu and kashmir": "Jammu and Kashmir", "jammu kashmir": "Jammu and Kashmir",
    "ladakh": "Ladakh", "lakshadweep": "Lakshadweep", "puducherry": "Puducherry",
    "pondicherry": "Puducherry",
}

SKIP_ANSWERS = {"skip", "pass", "prefer not to say", "rather not say", "n/a", "na"}
INTEREST_TERMS = {
    "school", "college", "student", "scholarship", "study", "education", "skill", "job",
    "employment", "training", "farm", "farmer", "agriculture", "crop", "women", "woman",
    "girl", "health", "medical", "hospital", "house", "home", "housing", "loan", "money",
    "financial", "assistance", "pension", "welfare", "disability", "disabled", "senior",
    "elderly", "business", "startup", "entrepreneur", "livelihood", "maternity", "child",
    "nutrition", "ration", "tribal", "minority", "insurance", "artisan", "self-employed",
}
NON_INTEREST_ANSWERS = {"hello", "hi", "hey", "thanks", "thank you", "ok", "okay", "yes", "no"}


def _field(stage: str) -> dict[str, Any]:
    index = next((i for i, step in enumerate(FLOW) if step[0] == stage), 0)
    key, question, input_type, options, optional = FLOW[index]
    return {
        "stage": key,
        "question": question,
        "input_type": input_type,
        "options": options,
        "optional": optional,
        "progress": {"current": index + 1, "total": len(FLOW)},
    }


def _parse_value(stage: str, message: str) -> Any:
    if stage in {"age", "annual_income"}:
        number = message.strip()
        number = re.sub(r"^(?:₹|rs\.?|inr)\s*", "", number, flags=re.IGNORECASE)
        if stage == "age":
            number = re.sub(r"\s*years?\s*(?:old)?$", "", number, flags=re.IGNORECASE)
        else:
            number = re.sub(r"\s*(?:rupees?|per year|annually|annual)$", "", number, flags=re.IGNORECASE)
        if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})+,\d{3})", number):
            label = "age" if stage == "age" else "annual family income"
            raise ValueError(f"Enter {label} as a whole number, or choose Skip.")
        value = int(number.replace(",", ""))
        if stage == "age" and not 0 <= value <= 120:
            raise ValueError("Please enter an age between 0 and 120.")
        if stage == "annual_income" and not 0 <= value <= 1_000_000_000:
            raise ValueError("Please enter an annual income between 0 and 1,000,000,000.")
        return value
    if stage == "interests":
        interest = message.strip()
        if len(interest) > 100:
            raise ValueError("Keep your focus area to 100 characters or fewer.")
        normalized = interest.casefold()
        if normalized in NON_INTEREST_ANSWERS or not re.search(r"[a-z]{2}", normalized):
            raise ValueError("Choose a listed focus area or describe a related need, such as a scholarship, farm support, healthcare or housing.")
        if normalized not in {option.casefold() for option in FLOW[0][3]}:
            words = set(re.findall(r"[a-z]+", normalized))
            if not words.intersection(INTEREST_TERMS):
                raise ValueError("I couldn’t match that to a scheme area. Choose one of the listed areas or mention a related need.")
        return [interest]
    if stage == "state":
        state = re.sub(r"^(?:i am from|i'm from|i live in|i am in|from|live in|located in)\s+", "", message.strip(), flags=re.IGNORECASE)
        state = re.sub(r"[.,\s]+$", "", state).casefold()
        if state not in STATES_AND_TERRITORIES:
            raise ValueError("Enter an Indian state or union territory, or choose Skip.")
        return STATES_AND_TERRITORIES[state]
    if stage == "occupation":
        occupation = message.strip()
        if len(occupation) < 2 or len(occupation) > 100 or not re.search(r"[a-zA-Z]{2}", occupation):
            raise ValueError("Enter a short occupation or work area (2 to 100 characters), or choose Skip.")
        return occupation
    _key, _question, input_type, options, _optional = next(step for step in FLOW if step[0] == stage)
    if input_type == "select":
        option = next((choice for choice in options if choice.casefold() == message.strip().casefold()), None)
        if option is None:
            raise ValueError("Please choose one of the listed options, or choose Skip.")
        if option.casefold() == "prefer not to say":
            return None
        return option
    return message.strip()


def handle_chat(message: str, profile: dict[str, Any], stage: str, schemes: list[dict[str, str]]) -> dict[str, Any]:
    clean_profile = dict(profile)
    if stage == "start":
        return {"reply": _field("interests")["question"], "profile": clean_profile, **_field("interests")}
    if stage == "complete":
        text = re.sub(r"[^a-z ]", " ", message.casefold()).strip()
        text = re.sub(r"\s+", " ", text)
        if text in {"restart", "start over", "new search", "reset"}:
            return {"reply": "Let’s start fresh. What would you like help with?", "profile": {}, **_field("interests")}
        results = recommend_schemes(schemes, clean_profile)
        if text in {"why", "why this", "why recommended", "why was this recommended", "explain", "explain ranking"}:
            reply = "Candidates are ranked using the information you shared and any criteria explicitly listed in the dataset. Unknown rules are not assumed to match; they are flagged for verification."
        elif text in {"more", "show more", "more schemes", "more options", "see more"}:
            results = recommend_schemes(schemes, clean_profile, limit=25)
            reply = "Here are more candidates. The score is a relative rule-match score, not a probability of approval."
        elif text:
            reply = "I can explain why these candidates appeared, show more schemes, or start a new search. For scheme-specific rules, open its details and verify with the official department."
        else:
            reply = "Choose a follow-up: ask ‘why’, request ‘more schemes’, or restart."
        return {"reply": reply, "stage": "complete", "profile": clean_profile, "recommendations": results}

    flow_keys = [step[0] for step in FLOW]
    if stage not in flow_keys:
        raise ValueError("Unknown conversation stage. Restart the conversation to continue.")
    index = flow_keys.index(stage)
    if message.strip().casefold() in SKIP_ANSWERS and FLOW[index][4]:
        message = ""
    if message.strip():
        try:
            value = _parse_value(stage, message.strip())
        except ValueError as error:
            return {"reply": str(error), "profile": clean_profile, **_field(stage)}
        if value is not None:
            clean_profile[stage] = value
    elif not FLOW[index][4]:
        return {"reply": "Choose an area or type a short interest so I can focus the search.", "profile": clean_profile, **_field(stage)}

    if index + 1 < len(FLOW):
        next_stage = FLOW[index + 1][0]
        return {"reply": _field(next_stage)["question"], "profile": clean_profile, **_field(next_stage)}

    recommendations = recommend_schemes(schemes, clean_profile)
    return {
        "reply": f"I found {len(recommendations)} candidates. Treat these as a starting point, not confirmation of eligibility.",
        "stage": "complete",
        "profile": clean_profile,
        "recommendations": recommendations,
    }