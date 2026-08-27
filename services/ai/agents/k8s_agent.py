"""Kubernetes Agent — analyzes cluster state for the incident.

Responsibilities:
- Read pod status, events, and container states
- Analyze deployment rollout status
- Check ConfigMaps, Secrets, and Volume mounts
- Identify K8s-level failure modes (CrashLoopBackOff, OOMKilled, etc.)
"""

from __future__ import annotations

import structlog

from services.ai.llm import LLMClient
from services.ai.state import AgentAnalysisResult, AgentState
from services.kubernetes.simulator import K8sSimulator

logger = structlog.get_logger(__name__)

K8S_ANALYSIS_SYSTEM_PROMPT = """You are an expert Kubernetes analysis agent for a Site Reliability Engineering (SRE) platform.

Your job is to analyze Kubernetes cluster state to identify:
1. Pod health and failure modes
2. Deployment rollout issues
3. ConfigMap, Secret, or Volume mount problems
4. Resource limits and OOM conditions
5. Network policies and service mesh issues

Kubernetes-specific failure modes you should check:
- CrashLoopBackOff (exit code 1, 137, 139, 143)
- OOMKilled (exit code 137 with SIGKILL)
- ImagePullBackOff / ErrImagePull
- CreateContainerConfigError
- Unschedulable (insufficient resources)
- Readiness/Liveness probe failures

Be precise about pod names, container names, exit codes, and event sequences."""


async def k8s_analysis_agent(state: AgentState) -> AgentState:
    """Analyze Kubernetes cluster state for the incident."""
    logger.info("k8s_agent_starting", incident_id=state.incident_id)

    llm = LLMClient()

    # Get K8s state (simulated or real)
    k8s = K8sSimulator()
    k8s_state = k8s.simulate_crashloop_backoff(
        service_name=state.service_name,
        failure_reason=state.scenario or "missing_env_var",
    )

    user_prompt = f"""Analyze the Kubernetes cluster state for this incident:

**Incident:** {state.title}
**Service:** {state.service_name}
**Scenario:** {state.scenario}

### Pod State
```json
{__import__('json').dumps(k8s_state['pod'], indent=2, default=str)[:2000]}
```

### Deployment State
```json
{__import__('json').dumps(k8s_state['deployment'], indent=2)[:1500]}
```

### Cluster Events
```json
{__import__('json').dumps(k8s_state['cluster_events'], indent=2)[:1000]}
```

Please analyze the Kubernetes state and identify:
1. Pod failure mode and root cause at the K8s level
2. Deployment status and rollout progress
3. Any ConfigMap/Secret/Volume issues
4. Your root cause hypothesis
5. Confidence level (0-1)"""

    try:
        raw_response = await llm.analyze(K8S_ANALYSIS_SYSTEM_PROMPT, user_prompt)

        structured = await llm.analyze_structured(
            K8S_ANALYSIS_SYSTEM_PROMPT,
            user_prompt,
            response_format={
                "findings": ["string"],
                "pod_status": "string",
                "exit_code": 0,
                "configmap_issue": False,
                "confidence": 0.0,
                "root_cause_hypothesis": "string",
            },
        )

        result = AgentAnalysisResult(
            agent_name="k8s_agent",
            findings=structured.get("findings", []),
            root_cause_hypothesis=structured.get("root_cause_hypothesis", ""),
            confidence=structured.get("confidence", 0.8),
            raw_output=raw_response,
        )

        state.k8s_analysis = result
        state.agents_used.append("k8s_agent")

        logger.info(
            "k8s_agent_complete",
            findings_count=len(result.findings),
            confidence=result.confidence,
        )

    except Exception as exc:
        logger.error("k8s_agent_failed", error=str(exc))
        state.errors.append(f"k8s_agent: {exc}")

    return state
