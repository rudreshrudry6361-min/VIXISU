"""Conservative feature extraction from aggregated match statistics.

Reference ranges below are demonstration calibration assumptions, NOT learned population
percentiles or validated professional benchmarks. Missing metrics remain missing.
"""
import math


def bounded_score(value, low, high, reverse=False):
    if value is None or not math.isfinite(float(value)) or high <= low:
        return None
    s = max(0.0, min(1.0, (float(value) - low) / (high - low)))
    return round(100 * (1 - s if reverse else s), 1)


def num(row, key):
    raw = row.get(key)
    if raw is None or str(raw).strip() == '':
        return None
    n = float(raw)
    if not math.isfinite(n) or n < 0:
        raise ValueError(f'{key} must be a finite non-negative number')
    return n


def safe_ratio(a,b,multiplier=1):
    if a is None or b is None or b <= 0:
        return None
    return a/b*multiplier


def extract_raw_features(row, sport):
    if sport == 'cricket':
        runs=num(row,'runs'); balls=num(row,'balls_faced'); dismissals=num(row,'dismissals')
        wickets=num(row,'wickets'); matches=num(row,'matches')
        catches=num(row,'catches'); runs_conceded=num(row,'runs_conceded'); balls_bowled=num(row,'balls_bowled')
        metrics={
            'batting':bounded_score(safe_ratio(runs,dismissals),10,60),
            'strike':bounded_score(safe_ratio(runs,balls,100),70,200),
            'fielding':bounded_score(safe_ratio(catches,matches),0,1.2),
            'bowling':bounded_score(safe_ratio(wickets,matches),0,3),
            'economy':bounded_score(safe_ratio(runs_conceded,balls_bowled,6),5,13,reverse=True),
        }
    elif sport == 'football':
        minutes=num(row,'minutes_played'); goals=num(row,'goals')
        passes=num(row,'passes_attempted'); completed=num(row,'passes_completed')
        tackles=num(row,'tackles'); interceptions=num(row,'interceptions')
        dribbles=num(row,'dribbles_completed')
        defense = tackles + interceptions if tackles is not None and interceptions is not None else None
        metrics={
            'passing':bounded_score(safe_ratio(completed,passes,100),50,95),
            'finishing':bounded_score(safe_ratio(goals,minutes,90),0,1.2),
            'defending':bounded_score(safe_ratio(defense,minutes,90),0,8),
            'dribbling':bounded_score(safe_ratio(dribbles,minutes,90),0,5),
        }
    else:
        raise ValueError('Unsupported sport')
    return {k:v for k,v in metrics.items() if v is not None}
