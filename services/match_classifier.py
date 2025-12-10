# services/match_classifier.py
import random
from typing import List, Tuple, Optional

# You can tweak thresholds here
VIBE_SPECIAL_THRESHOLD = 80  # >= 80 is special
MUTUAL_INTERESTS_SPECIAL = 3   # >= 3 shared interests
FRESHMAN_SENIOR_PAIRS = {("1st Year", "4th Year"), ("1st Year", "5th Year+"),
                         ("2nd Year", "5th Year+")}

def _years_pair_is_freshman_senior(y1: str, y2: str) -> bool:
    pair = (y1, y2)
    pair_rev = (y2, y1)
    return pair in FRESHMAN_SENIOR_PAIRS or pair_rev in FRESHMAN_SENIOR_PAIRS

def _is_cross_campus(c1: Optional[str], c2: Optional[str]) -> bool:
    if not c1 or not c2:
        return False
    return c1.strip().lower() != c2.strip().lower()

def _is_opposite_dept(d1: Optional[str], d2: Optional[str]) -> bool:
    if not d1 or not d2:
        return False
    # simple heuristic — treat different dept as "opposite" only for selected combos
    opposites = {
        ("Business", "Engineering"),
        ("Natural Sciences", "Social Sciences"),
        ("Law", "Business"),
        ("IT", "Health Sciences"),
    }
    pair = (d1, d2)
    pair_rev = (d2, d1)
    return pair in opposites or pair_rev in opposites

def classify_match(
    user1: dict,
    user2: dict,
    interests1: List[str],
    interests2: List[str],
    vibe_score: float
) -> Tuple[Optional[str], List[str], float]:
    """
    Return: (special_type or None, shared_interests, vibe_score)
    special_type one of:
      - "cross-campus"
      - "freshman-senior"
      - "same-department"
      - "opposite-department"
      - "high-vibe"
      - "shared-interests"
    """

    # Normalize fields
    dept1 = (user1.get("department") or "").strip()
    dept2 = (user2.get("department") or "").strip()
    year1 = (user1.get("year") or "").strip()
    year2 = (user2.get("year") or "").strip()
    campus1 = (user1.get("campus") or "").strip()
    campus2 = (user2.get("campus") or "").strip()

    # Shared interests
    s_interests = list({i.strip() for i in (interests1 or [])} & {i.strip() for i in (interests2 or [])})

    # RULES (priority order)
    # 1. High vibe
    if vibe_score is not None and vibe_score >= VIBE_SPECIAL_THRESHOLD:
        return ("high-vibe", s_interests, vibe_score)

    # 2. Freshman-Senior
    if _years_pair_is_freshman_senior(year1, year2):
        return ("freshman-senior", s_interests, vibe_score)

    # 3. Cross-campus
    if _is_cross_campus(campus1, campus2):
        return ("cross-campus", s_interests, vibe_score)

    # 4. Shared interests strong
    if len(s_interests) >= MUTUAL_INTERESTS_SPECIAL:
        return ("shared-interests", s_interests, vibe_score)

    # 5. Same department
    if dept1 and dept2 and dept1.lower() == dept2.lower():
        return ("same-department", s_interests, vibe_score)

    # 6. Opposite department combos
    if _is_opposite_dept(dept1, dept2):
        return ("opposite-department", s_interests, vibe_score)

    # fallback: maybe queue occasionally for variety
    # We'll not mark as special here (return None) — DB code may still queue a small %
    return (None, s_interests, vibe_score)
