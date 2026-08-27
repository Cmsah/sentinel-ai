"""Dual-mode LLM client for AI agent reasoning.

When an API key is configured, uses the real LLM provider.
Otherwise, falls back to deterministic simulation mode that produces
realistic, high-quality output without any external API calls.

This makes the system:
1. Demo-able without API keys (for reviewers, CI/CD)
2. Production-ready with real AI (when keys are provided)
"""

from __future__ import annotations

import json
import random
from typing import Any

import structlog

from services.shared.config import get_settings

logger = structlog.get_logger(__name__)


class LLMClient:
    """Unified LLM client with real + simulation modes."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._mode = self._settings.llm.provider
        self._real_client = None

        if self._mode == "openai":
            self._init_openai()
        elif self._mode == "anthropic":
            self._init_anthropic()

        logger.info("llm_client_initialized", mode=self._mode)

    def _init_openai(self) -> None:
        try:
            from langchain_openai import ChatOpenAI
            self._real_client = ChatOpenAI(
                api_key=self._settings.llm.openai_api_key,
                model=self._settings.llm.model,
                temperature=self._settings.llm.temperature,
                max_tokens=self._settings.llm.max_tokens,
            )
        except ImportError:
            logger.warning("openai_not_installed_falling_back_to_simulation")
            self._mode = "simulation"

    def _init_anthropic(self) -> None:
        try:
            from langchain_anthropic import ChatAnthropic
            self._real_client = ChatAnthropic(
                api_key=self._settings.llm.anthropic_api_key,
                model="claude-sonnet-4-20250514",
                temperature=self._settings.llm.temperature,
                max_tokens=self._settings.llm.max_tokens,
            )
        except ImportError:
            logger.warning("anthropic_not_installed_falling_back_to_simulation")
            self._mode = "simulation"

    async def analyze(self, system_prompt: str, user_prompt: str) -> str:
        """Send an analysis request to the LLM.

        Args:
            system_prompt: System instructions for the agent.
            user_prompt: The specific analysis request.

        Returns:
            LLM response as a string.
        """
        if self._mode == "simulation":
            return await self._simulate(system_prompt, user_prompt)

        return await self._call_real_llm(system_prompt, user_prompt)

    async def analyze_structured(
        self, system_prompt: str, user_prompt: str, response_format: dict
    ) -> dict[str, Any]:
        """Send a request expecting structured JSON output."""
        if self._mode == "simulation":
            return await self._simulate_structured(system_prompt, user_prompt, response_format)

        # Append format instructions to the prompt
        format_instruction = (
            f"\n\nRespond with valid JSON matching this structure:\n"
            f"{json.dumps(response_format, indent=2)}"
        )
        raw = await self._call_real_llm(system_prompt, user_prompt + format_instruction)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            if "{" in raw and "}" in raw:
                start = raw.index("{")
                end = raw.rindex("}") + 1
                return json.loads(raw[start:end])
            raise ValueError(f"Could not parse JSON from LLM response: {raw[:200]}")

    async def _call_real_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call the real LLM provider."""
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await self._real_client.ainvoke(messages)
        return response.content

    # -------------------------------------------------------------------
    # Simulation Mode
    # -------------------------------------------------------------------

    async def _simulate(self, system_prompt: str, user_prompt: str) -> str:
        """Produce deterministic, realistic simulation output.

        The simulation extracts intent from the prompts and returns
        pre-written expert-quality analysis that looks like real LLM output.
        """
        prompt_lower = (system_prompt + user_prompt).lower()

        if "log" in prompt_lower and ("analy" in prompt_lower or "examin" in prompt_lower):
            return self._simulate_log_analysis(user_prompt)
        elif "kubernetes" in prompt_lower or "k8s" in prompt_lower:
            return self._simulate_k8s_analysis(user_prompt)
        elif "metric" in prompt_lower:
            return self._simulate_metrics_analysis(user_prompt)
        elif "root cause" in prompt_lower:
            return self._simulate_root_cause(user_prompt)
        elif "remediat" in prompt_lower or "fix" in prompt_lower:
            return self._simulate_remediation(user_prompt)
        else:
            return "Analysis complete. The system appears to be experiencing configuration-related issues following a recent deployment."

    async def _simulate_structured(
        self, system_prompt: str, user_prompt: str, response_format: dict
    ) -> dict[str, Any]:
        """Produce structured simulation output matching the expected format."""
        prompt_lower = (system_prompt + user_prompt).lower()

        if "log" in prompt_lower:
            return {
                "findings": [
                    "DATABASE_URL environment variable not found in pod environment",
                    "Application crashes within 3 seconds of startup on all 7 restart attempts",
                    "First error at 02:31:15.982 — psycopg2.OperationalError: connection to server timed out",
                    "All errors are identical — no application-level errors (only config missing)",
                    "Sidecar container (fluent-bit) is healthy and running normally",
                ],
                "error_pattern": "repeated_startup_failure",
                "first_error": "DATABASE_URL environment variable not set",
                "error_count": 7,
                "confidence": 0.95,
                "root_cause_hypothesis": "Missing DATABASE_URL environment variable in pod specification",
            }
        elif "kubernetes" in prompt_lower or "k8s" in prompt_lower:
            return {
                "findings": [
                    "Pod sentinel-api-7d4f8b-2x9kp in CrashLoopBackOff state",
                    "Exit code 1 — application-level error, not OOM (exit code 137)",
                    "ConfigMap 'app-config' exists but missing DATABASE_URL key",
                    "Deployment annotation indicates revision #8 — 'Update env vars for database connection'",
                    "MountVolume.SetUp failed for volume 'config-volume'",
                ],
                "pod_status": "CrashLoopBackOff",
                "exit_code": 1,
                "configmap_issue": True,
                "confidence": 0.92,
                "root_cause_hypothesis": "ConfigMap 'app-config' not updated with DATABASE_URL",
            }
        elif "metric" in prompt_lower:
            return {
                "findings": [
                    "CPU usage normal (15-35%) — no processing spike",
                    "Memory usage at 60% — well within limits, no OOM risk",
                    "Request rate dropped to 0 rps — no healthy pods serving traffic",
                    "Error rate elevated but artificial (connection timeouts from load balancer)",
                    "Database connections at 0 — application never connected successfully",
                ],
                "cpu_percent": 25.0,
                "memory_percent": 60.0,
                "request_rate": 0.0,
                "confidence": 0.88,
                "root_cause_hypothesis": "Service outage — all pods unhealthy, zero request capacity",
            }
        elif "root cause" in prompt_lower:
            return {
                "root_cause": (
                    "Deployment #812 updated ConfigMap 'app-config' to add database connection "
                    "configuration, but the DATABASE_URL key was omitted. When pods restarted "
                    "with the new ConfigMap mount, the application failed to find the required "
                    "environment variable and crashed on startup with exit code 1. This caused "
                    "all 3 replicas to enter CrashLoopBackOff, resulting in a complete service outage."
                ),
                "confidence": 0.94,
                "contributing_factors": [
                    "ConfigMap updated without all required keys",
                    "No pre-deployment validation of environment variables",
                    "Application does not fail fast with clear error message",
                    "No health check detected the misconfiguration early enough",
                ],
                "timeline": [
                    {"time": "02:30:00", "event": "Deployment #812 started — rolling update"},
                    {"time": "02:30:45", "event": "First pod terminated — exit code 1"},
                    {"time": "02:31:00", "event": "Pod restarted, crashed again within 3 seconds"},
                    {"time": "02:31:15", "event": "CrashLoopBackOff initiated"},
                    {"time": "02:35:00", "event": "All 3 replicas in CrashLoopBackOff, 0 ready"},
                ],
            }
        elif "remediat" in prompt_lower or "fix" in prompt_lower:
            return {
                "recommended_actions": [
                    {
                        "action": "config_fix",
                        "description": "Add DATABASE_URL to ConfigMap 'app-config' and restart pods",
                        "priority": "immediate",
                        "risk_level": "low",
                        "estimated_time": "2 minutes",
                        "steps": [
                            "kubectl edit configmap app-config -n default",
                            "Add key: DATABASE_URL=postgresql://prod-db:5432/sentinel",
                            "kubectl rollout restart deployment/sentinel-api -n default",
                            "kubectl rollout status deployment/sentinel-api -n default",
                        ],
                    },
                    {
                        "action": "rollback",
                        "description": "Roll back to deployment #811 which had DATABASE_URL inline",
                        "priority": "alternative",
                        "risk_level": "medium",
                        "estimated_time": "1 minute",
                        "steps": [
                            "kubectl rollout undo deployment/sentinel-api -n default",
                            "kubectl rollout status deployment/sentinel-api -n default",
                        ],
                    },
                ],
                "prevention": [
                    "Add ConfigMap key validation to CI/CD deployment pipeline",
                    "Implement application startup probe with clear env var validation",
                    "Add pre-deployment ConfigMap diff to deployment review process",
                ],
            }
        else:
            return {"status": "analysis_complete", "confidence": 0.8}

    # -------------------------------------------------------------------
    # Simulation Helpers (detailed text output)
    # -------------------------------------------------------------------

    def _simulate_log_analysis(self, prompt: str) -> str:
        return (
            "## Log Analysis Report\n\n"
            "**Service:** sentinel-api\n"
            "**Time Window:** Last 10 minutes\n"
            "**Total Log Entries Analyzed:** 47\n\n"
            "### Key Findings\n\n"
            "1. **First Error** (02:31:15.982): `DATABASE_URL environment variable not set`\n"
            "   - This is the initial failure that cascades into all subsequent crashes.\n\n"
            "2. **Recurring Pattern**: The application crashes within 3 seconds of startup on "
            "every attempt. The error is identical across all 7 restart attempts:\n"
            "   ```\n"
            "   psycopg2.OperationalError: connection to server timed out\n"
            "   ```\n\n"
            "3. **No Application Errors**: Once the application fails to connect to the database, "
            "it exits immediately. There are no application-level errors because the app never "
            "reaches a state where it can process requests.\n\n"
            "4. **Sidecar Container**: The fluent-bit sidecar is healthy and logging normally. "
            "This indicates the issue is specific to the main application container.\n\n"
            "### Error Distribution\n"
            "- Exit code 1 (application error): 7 occurrences (100%)\n"
            "- No OOM events (exit code 137): 0\n"
            "- No network timeouts before startup: 0\n\n"
            "### Root Cause Hypothesis\n"
            "The `DATABASE_URL` environment variable is missing from the pod specification. "
            "The application requires this variable to establish a database connection during "
            "startup. Without it, the connection attempt times out and the application exits "
            "with code 1.\n\n"
            "**Confidence:** 95%"
        )

    def _simulate_k8s_analysis(self, prompt: str) -> str:
        return (
            "## Kubernetes Analysis Report\n\n"
            "### Pod Status\n"
            "- **Name:** sentinel-api-7d4f8b-2x9kp\n"
            "- **Phase:** Running (but container is CrashLoopBackOff)\n"
            "- **Restart Count:** 7\n"
            "- **Node:** ip-10-0-1-42.ec2.internal\n\n"
            "### Container Status\n"
            "- **Main Container:** `sentinel-api`\n"
            "  - Ready: ❌ False\n"
            "  - State: Waiting (CrashLoopBackOff)\n"
            "  - Restart Count: 7\n"
            "  - Last State: Terminated (Exit Code 1, Reason: Error)\n\n"
            "- **Sidecar:** `fluent-bit`\n"
            "  - Ready: ✅ True\n"
            "  - State: Running\n\n"
            "### K8s Events (Warning)\n"
            "1. `BackOff` — Back-off restarting failed container sentinel-api (×7)\n"
            "2. `FailedMount` — MountVolume.SetUp failed for volume 'config-volume': "
            "configmap 'app-config' not found\n\n"
            "### ConfigMap Analysis\n"
            "- ConfigMap `app-config` exists\n"
            "- Available keys: `REDIS_HOST`, `LOG_LEVEL`\n"
            "- **Missing key: `DATABASE_URL`**\n"
            "- Last modified: 2 days ago (not recently updated)\n\n"
            "### Deployment Analysis\n"
            "- **Current Revision:** #8\n"
            "- **Annotation:** 'Update env vars for database connection'\n"
            "- **Ready Replicas:** 0/3\n"
            "- **Updated Replicas:** 3 (all updated, none ready)\n\n"
            "### Root Cause Hypothesis\n"
            "The ConfigMap `app-config` was supposed to be updated with the `DATABASE_URL` "
            "key as part of deployment #812, but the key is missing from the ConfigMap data. "
            "The pod spec correctly references the ConfigMap volume mount, but the data it "
            "mounts doesn't contain the required variable.\n\n"
            "**Confidence:** 92%"
        )

    def _simulate_metrics_analysis(self, prompt: str) -> str:
        return (
            "## Metrics Analysis Report\n\n"
            "### Current State\n"
            "- **CPU Usage:** 22% (normal — app crashes before load)\n"
            "- **Memory Usage:** 58MB / 256MB (23% — no memory pressure)\n"
            "- **Request Rate:** 0.0 req/s (⚠️ zero traffic)\n"
            "- **Error Rate:** 0.0 (no requests to fail)\n"
            "- **Active Connections:** 0\n\n"
            "### Database Metrics\n"
            "- **DB Connection Pool:** 0 active / 0 waiting\n"
            "- **DB Query Latency:** N/A (no queries executed)\n\n"
            "### Timeline Analysis\n"
            "Looking at the 10-minute window:\n"
            "- T-10min: Healthy — 150 req/s, 15ms p99 latency, 3/3 pods ready\n"
            "- T-8min: Traffic drops to 0 — deployment started, pods terminating\n"
            "- T-7min: All pods in CrashLoopBackOff, zero capacity\n"
            "- T-7min to now: Flatline — no recovery\n\n"
            "### Key Insight\n"
            "The metrics confirm this is NOT a performance issue. CPU and memory are normal. "
            "The problem is structural — pods are failing to start, so there is zero capacity "
            "to serve traffic. The metrics profile is consistent with a configuration error "
            "that prevents application startup, NOT a resource exhaustion or code performance issue.\n\n"
            "**Confidence:** 88%"
        )

    def _simulate_root_cause(self, prompt: str) -> str:
        return (
            "## Root Cause Analysis\n\n"
            "### Incident Summary\n"
            "A deployment of `sentinel-api` v2.3.1 caused a complete service outage when "
            "all 3 replicas entered CrashLoopBackOff due to a missing environment variable.\n\n"
            "### Root Cause\n"
            "**Deployment #812 introduced a ConfigMap change that omitted the `DATABASE_URL` "
            "environment variable.**\n\n"
            "The deployment workflow updated the `app-config` ConfigMap as part of adding "
            "database connection configuration. However, the `DATABASE_URL` key was not "
            "included in the ConfigMap data — only `REDIS_HOST` and `LOG_LEVEL` were present. "
            "When the rolling update restarted pods with the new ConfigMap mount, the "
            "application could not find `DATABASE_URL` in its environment and crashed on "
            "startup with exit code 1.\n\n"
            "### Evidence Chain\n"
            "1. **Log Evidence:** Repeated `DATABASE_URL not set` error across all 7 restarts\n"
            "2. **K8s Evidence:** ConfigMap exists but is missing the key; deployment annotation "
            "confirms this was an env var update\n"
            "3. **Metrics Evidence:** Zero request rate + normal CPU/memory = structural startup "
            "failure, not performance issue\n"
            "4. **Deployment Evidence:** Revision #8 annotation 'Update env vars for database "
            "connection' directly correlates with the failure\n\n"
            "### Confidence: 94%\n\n"
            "### Contributing Factors\n"
            "- No pre-deployment validation of required environment variables\n"
            "- ConfigMap update was not atomic with the deployment\n"
            "- Application exits immediately on missing config (no graceful degradation)\n"
            "- No startup probe detected the misconfiguration within the rolling update window\n\n"
            "### Timeline\n"
            "| Time | Event |\n"
            "|------|-------|\n"
            "| 02:30:00 | Deployment #812 started (rolling update, 3 replicas) |\n"
            "| 02:30:45 | First pod terminated — exit code 1 |\n"
            "| 02:31:00 | Pod restarted, crashed within 3 seconds |\n"
            "| 02:31:15 | Kubernetes entered CrashLoopBackOff backoff |\n"
            "| 02:35:00 | All 3 replicas in CrashLoopBackOff, 0 ready |"
        )

    def _simulate_remediation(self, prompt: str) -> str:
        return (
            "## Remediation Plan\n\n"
            "### Option 1: Fix ConfigMap (Recommended — Immediate)\n"
            "**Risk Level:** LOW\n"
            "**Estimated Downtime:** 0 minutes (rolling restart)\n\n"
            "```bash\n"
            "# 1. Add DATABASE_URL to the ConfigMap\n"
            "kubectl patch configmap app-config -n default --type merge -p '\n"
            "  data:\n"
            "    DATABASE_URL: \"postgresql://prod-db:5432/sentinel\"\n"
            "'\n\n"
            "# 2. Restart pods to pick up the new ConfigMap\n"
            "kubectl rollout restart deployment/sentinel-api -n default\n\n"
            "# 3. Verify rollout\n"
            "kubectl rollout status deployment/sentinel-api -n default\n"
            "```\n\n"
            "### Option 2: Rollback Deployment (Alternative)\n"
            "**Risk Level:** MEDIUM\n"
            "**Estimated Downtime:** ~30 seconds (rolling update)\n\n"
            "```bash\n"
            "# Roll back to the previous working revision\n"
            "kubectl rollout undo deployment/sentinel-api -n default\n"
            "kubectl rollout status deployment/sentinel-api -n default\n"
            "```\n\n"
            "**Note:** This reverts to deployment #811 which had the env var set inline. "
            "The ConfigMap change from #812 would need to be addressed separately.\n\n"
            "### Prevention Recommendations\n"
            "1. **CI/CD Validation:** Add a pre-deployment step that validates all required "
            "environment variables are present in the target ConfigMap\n"
            "2. **Application Hardening:** Implement a startup check that logs all required "
            "env vars and their presence (not values) before attempting database connection\n"
            "3. **Deployment Review:** Add ConfigMap diff to the deployment approval process\n"
            "4. **Monitoring:** Add an alert for `ready_replicas < desired_replicas` lasting "
            "more than 60 seconds during a deployment"
        )
