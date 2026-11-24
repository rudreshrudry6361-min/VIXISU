"""Translate supported scouting questions into existing archive queries."""
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .cricket import FIT_WEIGHTS, Cohort, FitRequest, decision_lab, players, profile

router = APIRouter(prefix="/api/scouting", tags=["Scouting copilot"])

ROLES = {
    "Opener": r"\b(openers?|opening)\b",
    "Middle Order": r"\bmiddle[ -]order\b",
    "Finisher": r"\b(finishers?|finishing|death[ -]overs?)\b",
    "All-Rounder": r"\ball[ -]rounders?\b",
    "Bowler": r"\bbowlers?\b",
}
PRIORITIES = {
    "strike": r"\b(aggressive|batting strike rate|scoring rate|boundary hitting)\b",
    "batting": r"\b(batting average|average runs)\b",
    "finishing": r"\b(death[ -]overs?|late[ -]overs?)\b",
    "bowling": r"\b(wickets|wicket taking)\b",
    "economy": r"\b(economy|economical)\b",
}


class ScoutQuestion(BaseModel):
    question: str = Field(min_length=2, max_length=300)
    cohort: Cohort
    player_ids: list[str] = Field(default_factory=list, max_length=3)
    roster_ids: list[str] = Field(default_factory=list, max_length=30)


@router.post("/query")
def query(data: ScoutQuestion):
    question = data.question.strip().lower()
    cohort = data.cohort
    if re.search(r"\b(football|soccer|midfielders?)\b", question):
        raise HTTPException(422, "This workspace uses the cricket archive. Choose a cricket scouting question.")
    if years := set(re.findall(r"\b(?:19|20)\d{2}\b", question)):
        selected_years = set(re.findall(r"\b(?:19|20)\d{2}\b", str(cohort.season)))
        if not years <= selected_years:
            raise HTTPException(422, "Select the season mentioned in the question before running it.")
    if formats := set(re.findall(r"\b(t20i?|t10|odi|test)\b", question)):
        selected = cohort.format.lower()
        if formats == {"t20i"}:
            matches_format = cohort.team_type == "international" and selected in {"t20", "it20"}
        else:
            matches_format = formats == {selected}
        if not matches_format:
            raise HTTPException(422, "Select the cricket format mentioned in the question.")
    if re.search(r"\bcompar(e|ison)\b", question):
        distinct = sorted(set(data.player_ids))
        if len(distinct) < 2 or not all(cohort.model_dump().values()):
            raise HTTPException(422, "Select a shared cohort and two or three players from the scouting table.")
        return {"action": "compare", "cohort": cohort,
                "players": [profile(player_id, cohort) for player_id in distinct]}
    if match := re.fullmatch(r"(?:find|search for) player\s+(.+)", question):
        result = players(cohort, q=match[1], offset=0, limit=8, criterion="matches")
        return {"action": "search", **result}
    roles = [key for key, pattern in ROLES.items() if re.search(pattern, question)]
    if len(roles) != 1:
        raise HTTPException(422, "Ask for one cricket role, use ‘find player NAME’, or compare selected players.")
    role = roles[0]
    weights = {key: weight * (2 if re.search(PRIORITIES[key], question) else 1)
               for key, weight in FIT_WEIGHTS[role].items()}
    result = decision_lab(FitRequest(cohort=cohort, role=role, weights=weights, roster_ids=data.roster_ids))
    return {"action": "rank", "role": role, **result}
