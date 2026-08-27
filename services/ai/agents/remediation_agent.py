"""Remediation Agent — proposes specific fixes based on root cause analysis.

Responsibilities:
- Recommend rollback, restart, scale, or config fixes
- Estimate risk level for each action
- Provide step-by-step remediation instructions
- Suggest prevention measures
"""

from __future__ import annotations

import structlog

from services.ai.llm import LLMClient
from services.ai.state import AgentAnalysisResult, AgentState, RemediationAction

logger = structlog.get_logger(__name__)

REMEDIATION_SYSTEM_PROMPT = """You are the Remediation Agent for a Site Reliability Engineering (SRE) platform.

Given a root cause analysis, you propose specific, actionable remediation steps.

Your recommendations should:
1. Address the root cause directly (not just symptoms)
2. Include both immediate fixes and long-term prevention
3. Estimate risk level (low, medium, high) for each action
4. Provide step-by-step instructions where possible
5. Consider rollback as an option when the fix is uncertain

Always prioritize:
- Safety: low-risk fixes first
- Speed: faster resolution for critical incidents
- Completeness: address both the immediate issue and prevent recurrence"""


async def remediation_agent(state: AgentState) -> AgentState:
    """Propose remediation actions based on root cause analysis."""
    logger.info("remediation_agent_starting", incident_id=state.incident_id)

    llm = LLMClient()

    user_prompt = f"""Based on the following root cause analysis, propose remediation actions:

**Incident:** {state.title}
**Service:** {state.service_name}
**Severity:** {state.severity}
**Root Cause:** {state.root_cause}
**Confidence:** {state.root_cause_confidence:.0%}
**Contributing Factors:** {', '.join(state.contributing_factors)}

Provide:
1. **Immediate Actions**: What to do RIGHT NOW to restore service
2. **Short-term Fixes**: Changes to prevent recurrence in the next deployment
3. **Long-term Prevention**: Systemic improvements to prevent this class of incident
4. For each action, specify:
   - Action type (rollback, config_fix, restart, scale, code_patch)
   - Risk level (low, medium, high)
   - Estimated time
   - Step-by-step instructions"""

    try:
        raw_response = await llm.analyze(REMEDIATION_SYSTEM_PROMPT, user_prompt)

        structured = await llm.analyze_structured(
            REMEDIATION_SYSTEM_PROMPT,
            user_prompt,
            response_format={
                "recommended_actions": [
                    {
                        "action_type": "string",
                        "description": "string",
                        "priority": "string",
                        "risk_level": "string",
                        "estimated_time": "string",
                        "steps": ["string"],
                    }
                ],
                "prevention": ["string"],
            },
        )

        actions = [
            RemediationAction(
                action_type=a.get("action_type", "unknown"),
                description=a.get("description", ""),
                priority=a.get("priority", "short_term"),
                risk_level=a.get("risk_level", "medium"),
                estimated_time=a.get("estimated_time", "unknown"),
                steps=a.get("steps", []),
            )
            for a in structured.get("recommended_actions", [])
        ]

        state.remediation_actions = actions
        state.prevention_suggestions = structured.get("prevention", [])
        state.agents_used.append("remediation_agent")

        logger.info(
            "remediation_agent_complete",
            actions_count=len(actions),
            prevention_count=len(state.prevention_suggestions),
        )

    except Exception as exc:
        logger.error("remediation_agent_failed", error=str(exc))
        state.errors.append(f"remediation_agent: {exc}")

    return state
