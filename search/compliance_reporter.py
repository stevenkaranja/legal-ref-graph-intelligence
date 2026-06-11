"""Auto-generate compliance reports from graph + RAG pipeline."""
from search.vector_search import HybridSearchEngine
from datetime import datetime


REPORT_TEMPLATE = """
COMPLIANCE REPORT
Generated: {timestamp}
Jurisdiction: {jurisdiction}

REGULATORY COVERAGE
{reg_section}

GAPS IDENTIFIED
{gaps_section}

RECOMMENDED ACTIONS
{actions_section}
"""


class ComplianceReporter:
    def __init__(self):
        self.engine = HybridSearchEngine()

    def generate(self, jurisdiction: str, doc_ids: list) -> str:
        regs = self._get_applicable_regs(doc_ids)
        gaps = self._identify_gaps(doc_ids, regs)
        actions = self._recommend_actions(gaps, jurisdiction)
        return REPORT_TEMPLATE.format(
            timestamp=datetime.utcnow().isoformat(),
            jurisdiction=jurisdiction,
            reg_section="\n".join(f"  • {r['code']}: {r['title']}" for r in regs),
            gaps_section="\n".join(f"  ⚠ {g}" for g in gaps) or "  None identified",
            actions_section="\n".join(f"  {i+1}. {a}" for i, a in enumerate(actions)),
        )

    def _get_applicable_regs(self, doc_ids):
        with self.engine.neo4j.session() as s:
            result = s.run(
                "MATCH (d:Document)-[:GOVERNED_BY]->(r:Regulation) "
                "WHERE d.id IN $ids AND r.status='ACTIVE' "
                "RETURN DISTINCT r.code AS code, r.title AS title",
                ids=doc_ids,
            )
            return [r.data() for r in result]

    def _identify_gaps(self, doc_ids, regs):
        known = {r["code"] for r in regs}
        gaps = []
        # Ask LLM to identify missing regulatory coverage
        qa = self.engine.compliance_qa(
            f"What regulations might be missing for documents involving: {', '.join(doc_ids[:3])}?"
        )
        return [qa] if qa else []

    def _recommend_actions(self, gaps, jurisdiction):
        if not gaps:
            return ["Continue periodic compliance review — no gaps detected."]
        return [
            f"Review and update documentation to align with {jurisdiction} requirements.",
            "Schedule legal team review of identified regulatory gaps.",
            "Update document registry with missing regulatory mappings.",
        ]
