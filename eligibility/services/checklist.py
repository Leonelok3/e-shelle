from typing import List, Dict
from ..models import ChecklistTemplate, JourneyStepTemplate, Program

def build_checklist(program: Program) -> Dict:
    docs = [{"label": t.label, "required": t.is_required, "code": t.doc_code}
            for t in program.checklist_templates.all()]
    steps = [{"label": s.label, "order": s.order, "eta_days": s.eta_days}
             for s in program.journey_steps.all()]
    return {"documents": docs, "steps": steps}
