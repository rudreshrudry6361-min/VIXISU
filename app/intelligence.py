"""Transparent, deterministic team-fit ranking; never compares metrics across sports."""
from .data import FEATURES, ROLE_TEMPLATES

COMPATIBLE = {
    'cricket': {
        'Opener': {'Middle Order': 70, 'All-Rounder': 70, 'Finisher': 65},
        'Middle Order': {'Opener': 78, 'Finisher': 78, 'All-Rounder': 80},
        'Finisher': {'Middle Order': 80, 'All-Rounder': 76, 'Opener': 70},
        'All-Rounder': {'Middle Order': 65, 'Finisher': 65, 'Bowler': 62},
        'Bowler': {'All-Rounder': 72},
    },
    'football': {
        'Midfielder': {'Winger': 70, 'Defender': 65, 'Forward': 55},
        'Forward': {'Winger': 78, 'Midfielder': 60},
        'Winger': {'Forward': 75, 'Midfielder': 73},
        'Defender': {'Midfielder': 65},
    },
}


def clean_weights(sport, role, weights=None):
    if sport not in ROLE_TEMPLATES:
        raise ValueError('Unsupported sport')
    if role not in ROLE_TEMPLATES[sport]:
        raise ValueError('Unsupported role for sport')
    if weights is None:
        weights = ROLE_TEMPLATES[sport][role]
    valid = {name for name, _ in FEATURES[sport]}
    if not isinstance(weights, dict) or not weights:
        raise ValueError('Provide nonempty skill weights')
    out = {}
    for k, v in weights.items():
        if k not in valid:
            raise ValueError(f'Unsupported feature: {k}')
        if isinstance(v, bool) or not isinstance(v, (int,float)) or not (0 <= v <= 1000):
            raise ValueError(f'Invalid weight for {k}')
        if v > 0:
            out[k] = float(v)
    if not out:
        raise ValueError('At least one weight must be positive')
    return out


def score_candidates(players, sport, role, weights=None, roster_ids=None):
    weights = clean_weights(sport, role, weights)
    roster_ids = set(roster_ids or [])
    pool = [p for p in players if p['sport'] == sport]
    roster = [p for p in pool if p['id'] in roster_ids]
    total_w = sum(weights.values())
    output = []
    for p in pool:
        if p['id'] in roster_ids:
            continue
        observed = {k: p['features'][k] for k in weights if k in p['features'] and isinstance(p['features'][k],(int,float))}
        available_w = sum(weights[k] for k in observed)
        coverage = available_w / total_w
        if not observed or coverage < 0.5:
            continue
        skill_fit = sum(weights[k] * observed[k] for k in observed) / total_w
        role_score = 100 if p['role'] == role else COMPATIBLE.get(sport, {}).get(role, {}).get(p['role'], 35)
        # Bonus is bounded and only applied when an existing roster is provided.
        gap_bonus = 0.0
        if roster:
            positive_gap = 0.0
            for key in observed:
                teammates = [r['features'][key] for r in roster if key in r['features']]
                if teammates:
                    avg = sum(teammates) / len(teammates)
                    positive_gap += weights[key] * max(0, observed[key] - avg) / total_w
            gap_bonus = min(8.0, positive_gap * 0.25)
        fit = min(100.0, 0.85 * skill_fit + 0.15 * role_score + gap_bonus)
        strengths = sorted(observed, key=lambda k: weights[k] * observed[k], reverse=True)[:2]
        missing = [k for k in weights if k not in observed]
        labels = dict(FEATURES[sport])
        reasons = [f"{labels[k]} contributes ({observed[k]:.0f}/100)" for k in strengths]
        if p['role'] == role:
            reasons.insert(0, f'Exact role match: {role}')
        else:
            reasons.insert(0, f'Alternative role: {p["role"]} (requested: {role})')
        if gap_bonus > 0:
            reasons.append(f'Addresses existing roster gaps (+{gap_bonus:.1f} points)')
        if missing:
            reasons.append('Limited evidence for: ' + ', '.join(labels[k] for k in missing))
        output.append({
            'player': p, 'score': round(fit,1), 'skill_fit': round(skill_fit,1),
            'role_match': role_score, 'gap_bonus': round(gap_bonus,1),
            'coverage': round(coverage * 100), 'reasons': reasons,
            'missing_features': missing,
            'contributions': {
                key: round(.85 * weights[key] * observed[key] / total_w, 2)
                for key in observed
            },
            'role_points': round(.15 * role_score, 2),
        })
    return sorted(output, key=lambda x: (-x['score'], x['player']['name'], x['player']['id']))
