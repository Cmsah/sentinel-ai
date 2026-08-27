"""Root Cause Agent — synthesizes findings from all analysis agents.

This agent runs after the parallel analysis agents and combines their
findings into a unified root cause analysis with confidence scoring.
"""

from __future__ import annotations

import structlog

from services.ai.llm import LLMClient
from services.ai.state import AgentAnalysisResult, AgentState

logger = structlog.get_logger(__name__)

ROOT_CAUSE_SYSTEM_PROMPT = """You are the Root Cause Analysis (RCA) agent for a Site Reliability Engineering (SRE) platform.

You receive findings from multiple specialized analysis agents:
- Log Analysis Agent
- Kubernetes Agent
- Metrics Agent
- Deployment Agent

Your job is to:
1. **Synthesize** all agent findings into a coherent root cause narrative
2. **Rank** the evidence by strength and relevance
3. **Identify** the definitive root cause (not just symptoms)
4. **Construct** a timeline of events leading to the incident
5. **Assess** your overall confidence based on evidence quality

Key principles:
- The root cause is the earliest action that, if prevented, would have avoided the incident
- Distinguish between the trigger (e.g., deployment), the root cause (e.g., missing config), and symptoms (e.g., CrashLoopBackOff)
- Higher confidence requires multiple independent evidence sources agreeing
- If evidence is contradictory, lower your confidence and note the ambiguity"""


async def root_cause_agent(state: AgentState) -> AgentState:
    """Synthesize all analysis results into a root cause determination."""
    logger.info("root_cause_agent_starting", incident_id=state.incident_id)

    llm = LLMClient()

    # Compile agent findings
    findings_sections = []

    if state.log_analysis:
        findings_sections.append(
            f"### Log Analysis (confidence: {state.log_analysis.confidence:.0%})\n"
            + "\n".join(f"- {f}" for f in state.log_analysis.findings)
            + f"\n\nHypothesis: {state.log_analysis.root_cause_hypothesis}"
        )

    if state.k8s_analysis:
        findings_sections.append(
            f"### Kubernetes Analysis (confidence: {state.k8s_analysis.confidence:.0%})\n"
            + "\n".join(f"- {f}" for f in state.k8s_analysis.findings)
            + f"\n\nHypothesis: {state.k8s_analysis.root_cause_hypothesis}"
        )

    if state.metrics_analysis:
        findings_sections.append(
            f"### Metrics Analysis (confidence: {state.metrics_analysis.confidence:.0%})\n"
            + "\n".join(f"- {f}" for f in state.metrics_analysis.findings)
            + f"\n\nHypothesis: {state.metrics_analysis.root_cause_hypothesis}"
        )

    if state.deployment_analysis:
        findings_sections.append(
            f"### Deployment Analysis (confidence: {state.deployment_analysis.confidence:.0%})\n"
            + "\n".join(f"- {f}" for f in state.deployment_analysis.findings)
            + f"\n\nHypothesis: {state.deployment_analysis.root_cause_hypothesis}"
        )

    user_prompt = f"""Synthesize the following agent findings into a root cause analysis:

**Incident:** {state.title}
**Service:** {state.service_name}
**Description:** {state.description}
**Severity:** {state.severity}

---

{chr(10).join(findings_sections)}

---

Based on ALL of the above agent findings, provide:
1. **Root Cause**: A clear, concise statement of what caused the incident
2. **Confidence**: Overall confidence (0-1) based on evidence agreement
3. **Contributing Factors**: Factors that made the incident possible or worse
4. **Timeline**: Ordered sequence of events from trigger to impact
5. **Evidence Strength**: Rate each agent's contribution (strong, moderate, weak)"""

    try:
        raw_response = await llm.analyze(ROOT_CAUSE_SYSTEM_PROMPT, user_prompt)

        structured = await llm.analyze_structured(
            ROOT_CAUSE_SYSTEM_PROMPT,
            user_prompt,
            response_format={
                "root_cause": "string",
                "confidence": 0.0,
                "contributing_factors": ["string"],
                "timeline": [{"time": "string", "event": "string"}],
                "evidence_assessment": {"agent": "strength"},
            },
        )

        state.root_cause = structured.get("root_cause", "")
        state.root_cause_confidence = structured.get("confidence", 0.8)
        state.contributing_factors = structured.get("contributing_factors", [])
        state.timeline = structured.get("timeline", [])
        state.agents_used.append("root_cause_agent")

        logger.info(
            "root_cause_agent_complete",
            confidence=state.root_cause_confidence,
            factors_count=len(state.contributing_factors),
        )

    except Exception as exc:
        logger.error("root_cause_agent_failed", error=str(exc))
        state.errors.append(f"root_cause_agent: {exc}")

    return state
