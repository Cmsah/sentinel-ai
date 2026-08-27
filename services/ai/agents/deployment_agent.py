"""Deployment Agent — analyzes recent deployments for the incident.

Responsibilities:
- Identify what changed in the failing deployment
- Compare before/after configurations
- Check CI/CD pipeline results
- Analyze Helm/Terraform changes
"""

from __future__ import annotations

import structlog

from services.ai.llm import LLMClient
from services.ai.state import AgentAnalysisResult, AgentState

logger = structlog.get_logger(__name__)

DEPLOYMENT_ANALYSIS_SYSTEM_PROMPT = """You are an expert deployment analysis agent for a Site Reliability Engineering (SRE) platform.

Your job is to analyze deployment changes to identify:
1. What changed in the failing deployment
2. Configuration drift between environments
3. Infrastructure changes (Terraform, Helm, K8s manifests)
4. Code changes that might have caused the failure
5. Rollback eligibility and risk

Focus on:
- Git commits and their associated changes
- Configuration diffs (env vars, configmaps, secrets)
- Infrastructure-as-code changes
- Deployment timing relative to failure onset"""


async def deployment_analysis_agent(state: AgentState) -> AgentState:
    """Analyze deployment changes for the incident."""
    logger.info("deployment_agent_starting", incident_id=state.incident_id)

    llm = LLMClient()

    user_prompt = f"""Analyze the deployment history for this incident:

**Incident:** {state.title}
**Service:** {state.service_name}
**Scenario:** {state.scenario}

The incident occurred shortly after a deployment. Analyze:
1. What changed in the deployment
2. Whether the deployment is the likely cause
3. What specifically in the deployment triggered the failure
4. Whether a rollback would resolve the issue
5. Confidence level (0-1)"""

    try:
        raw_response = await llm.analyze(DEPLOYMENT_ANALYSIS_SYSTEM_PROMPT, user_prompt)

        structured = await llm.analyze_structured(
            DEPLOYMENT_ANALYSIS_SYSTEM_PROMPT,
            user_prompt,
            response_format={
                "findings": ["string"],
                "deployment_cause": True,
                "change_type": "string",
                "confidence": 0.0,
                "root_cause_hypothesis": "string",
            },
        )

        result = AgentAnalysisResult(
            agent_name="deployment_agent",
            findings=structured.get("findings", []),
            root_cause_hypothesis=structured.get("root_cause_hypothesis", ""),
            confidence=structured.get("confidence", 0.8),
            raw_output=raw_response,
        )

        state.deployment_analysis = result
        state.agents_used.append("deployment_agent")

        logger.info("deployment_agent_complete", confidence=result.confidence)

    except Exception as exc:
        logger.error("deployment_agent_failed", error=str(exc))
        state.errors.append(f"deployment_agent: {exc}")

    return state
