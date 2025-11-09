from typing import Dict, Any, List, Tuple
from ..models import Program, ProgramCriterion

def _get(path: str, data: Dict[str, Any]):
    cur = data
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur

def _match(op: str, lhs, rhs) -> bool:
    if lhs is None:
        return False
    if op == "gte": return float(lhs) >= float(rhs)
    if op == "lte": return float(lhs) <= float(rhs)
    if op == "eq":  return lhs == rhs
    if op == "in":  return lhs in rhs
    if op == "bool": return bool(lhs) is bool(rhs)
    return False

def score_program(program: Program, answers: Dict[str, Any]) -> Dict[str, Any]:
    total = 0.0
    max_total = 0.0
    missing: List[str] = []
    hard_fail = False
    details: List[Dict[str, Any]] = []

    for c in program.criteria.all():
        lhs = _get(c.key, answers)
        ok = _match(c.op, lhs, c.value_json)
        max_total += c.weight
        if ok:
            total += c.weight
        else:
            details.append({"key": c.key, "expected": c.value_json, "op": c.op, "got": lhs})
            if c.required:
                hard_fail = True
                missing.append(c.key)
    norm = 0 if max_total == 0 else round((total / max_total) * 100, 2)
    eligible = (not hard_fail) and (norm >= program.min_score)
    return {
        "program": program.code,
        "score": norm,
        "eligible": eligible,
        "hard_fail": hard_fail,
        "missing_keys": missing,
        "explain": details,
        "url_official": program.url_official,
        "country": program.country,
        "title": program.title,
    }
