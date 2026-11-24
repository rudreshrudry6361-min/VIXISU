"""Raw cricket measures shared by archive, local scorecards and normalized imports."""
import re
from typing import Annotated

from pydantic import BaseModel, Field, model_validator

from .ingestion import safe_ratio

Count = Annotated[int, Field(ge=0, le=10_000_000, strict=True)]


def parse_overs(notation):
    match = re.fullmatch(r"(\d+)(?:\.([0-5]))?", notation)
    if not match:
        raise ValueError("Use cricket overs notation, for example 4.2 for four overs and two balls.")
    return int(match[1]) * 6 + int(match[2] or 0)


def cricket_rates(counts):
    def ratio(n, d, factor=1):
        value = safe_ratio(counts.get(n), counts.get(d), factor)
        return round(value, 2) if value is not None else None

    boundaries = None
    if all(counts.get(key) is not None for key in ("fours", "sixes", "runs")):
        boundaries = safe_ratio(4 * counts["fours"] + 6 * counts["sixes"], counts["runs"], 100)
    return {
        "batting_average": ratio("runs", "dismissals"),
        "strike_rate": ratio("runs", "balls_faced", 100),
        "bowling_average": ratio("runs_conceded", "wickets"),
        "economy": ratio("runs_conceded", "balls_bowled", 6),
        "bowling_strike_rate": ratio("balls_bowled", "wickets"),
        "boundary_run_percent": round(boundaries, 2) if boundaries is not None else None,
        "dot_ball_percent": ratio("dot_balls", "balls_bowled", 100),
    }


class CricketCounts(BaseModel):
    matches: Count | None = None
    innings: Count | None = None
    runs: Count | None = None
    balls_faced: Count | None = None
    dismissals: Count | None = None
    highest_score: Count | None = None
    fours: Count | None = None
    sixes: Count | None = None
    wickets: Count | None = None
    balls_bowled: Count | None = None
    overs: str | None = Field(None, max_length=12)
    runs_conceded: Count | None = None
    dot_balls: Count | None = None
    catches: Count | None = None
    stumpings: Count | None = None

    @model_validator(mode="after")
    def validate_totals(self):
        if self.overs is not None:
            converted = parse_overs(self.overs)
            if converted > 10_000_000 or (self.balls_bowled is not None and self.balls_bowled != converted):
                raise ValueError("Overs and legal balls must agree and stay within the supported count range.")
            self.balls_bowled = converted
        for subtotal, total in (("dismissals", "innings"), ("dot_balls", "balls_bowled"), ("highest_score", "runs")):
            a, b = getattr(self, subtotal), getattr(self, total)
            if a is not None and b is not None and a > b:
                raise ValueError(f"{subtotal} cannot exceed {total}.")
        if self.runs is not None and 4 * (self.fours or 0) + 6 * (self.sixes or 0) > self.runs:
            raise ValueError("Boundary runs cannot exceed total runs.")
        if not any(value is not None for value in self.model_dump().values()):
            raise ValueError("Supply at least one cricket count.")
        return self
