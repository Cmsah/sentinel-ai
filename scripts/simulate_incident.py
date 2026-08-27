#!/usr/bin/env python3
"""Simulate a full incident lifecycle.

Usage:
    python -m scripts.simulate_incident
    python -m scripts.simulate_incident --scenario out_of_memory
    python -m scripts.simulate_incident --service api-gateway --scenario image_pull_error
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import datetime, timezone

from services.ai.orchestrator import SentinelOrchestrator
from services.kubernetes.simulator import K8sSimulator


SCENARIOS = {
    "missing_env_var": "ConfigMap DATABASE_URL missing — CrashLoopBackOff",
    "out_of_memory": "Container OOMKilled — memory limit exceeded",
    "image_pull_error": "Invalid image tag — ImagePullBackOff",
    "application_error": "Application crash on startup",
}


async def run_simulation(
    service_name: str = "sentinel-api",
    scenario: str = "missing_env_var",
) -> None:
    """Run a full incident simulation."""
    print(f"\n{'='*70}")
    print(f"  Sentinel AI — Incident Simulation")
    print(f"  Service: {service_name}")
    print(f"  Scenario: {scenario}")
    print(f"  Description: {SCENARIOS.get(scenario, 'Unknown')}")
    print(f"{'='*70}\n")

    # Step 1: Simulate K8s state
    print("📡 Step 1: Simulating Kubernetes cluster state...")
    k8s = K8sSimulator()
    k8s_state = k8s.simulate_crashloop_backoff(
        service_name=service_name,
        failure_reason=scenario,
    )
    print(f"   ✅ Pod: {k8s_state['pod']['metadata']['name']}")
    print(f"   ✅ Namespace: {k8s_state['pod']['metadata']['namespace']}")
    print(f"   ✅ Scenario: {k8s_state['scenario']}")
    print(f"   ✅ Description: {k8s_state['description']}")
    print()

    # Step 2: Run AI analysis
    print("🤖 Step 2: Running AI multi-agent analysis pipeline...")
    print("   Agents: log_agent → k8s_agent → metrics_agent → root_cause → remediation")
    print()

    orchestrator = SentinelOrchestrator()
    start_time = time.perf_counter()

    result = await orchestrator.analyze(
        incident_id=f"sim-{int(time.time())}",
        service_name=service_name,
        title=f"[SIMULATED] {scenario.replace('_', ' ').title()} — {service_name}",
        description=k8s_state["description"],
        severity="critical",
        scenario=scenario,
    )

    duration = time.perf_counter() - start_time

    # Step 3: Print results
    print(f"\n{'─'*70}")
    print(f"  Analysis Complete — {duration:.2f}s")
    print(f"{'─'*70}\n")

    if result.get("status") == "failed":
        print(f"  ❌ Analysis failed: {result.get('error', 'Unknown error')}")
        return

    # Root cause
    root_cause = result.get("root_cause", {})
    print("🔍 ROOT CAUSE ANALYSIS")
    print(f"   Confidence: {root_cause.get('confidence', 0):.0%}")
    print(f"   Analysis: {root_cause.get('analysis', 'N/A')[:200]}...")
    print()

    # Contributing factors
    factors = root_cause.get("contributing_factors", [])
    if factors:
        print("📋 CONTRIBUTING FACTORS")
        for i, factor in enumerate(factors, 1):
            print(f"   {i}. {factor}")
        print()

    # Timeline
    timeline = root_cause.get("timeline", [])
    if timeline:
        print("📅 TIMELINE")
        for event in timeline:
            time_str = event.get("time", "?")
            event_str = event.get("event", "?")
            print(f"   [{time_str}] {event_str}")
        print()

    # Remediation
    remediation = result.get("remediation", {})
    actions = remediation.get("actions", [])
    if actions:
        print("🔧 REMEDIATION ACTIONS")
        for action in actions:
            print(f"   [{action.get('priority', '?').upper()}] {action.get('description', '')}")
            print(f"     Risk: {action.get('risk_level', '?')} | Type: {action.get('type', '?')}")
            steps = action.get("steps", [])
            for i, step in enumerate(steps, 1):
                print(f"     {i}. {step}")
            print()

    # Prevention
    prevention = remediation.get("prevention", [])
    if prevention:
        print("🛡️  PREVENTION RECOMMENDATIONS")
        for i, item in enumerate(prevention, 1):
            print(f"   {i}. {item}")
        print()

    # Agent summary
    agents = result.get("agents_used", [])
    print(f"🤖 AGENTS USED: {', '.join(agents)}")
    print(f"⏱️  DURATION: {result.get('duration_seconds', duration):.2f}s")
    print(f"\n{'='*70}")
    print(f"  Simulation complete. No real external systems were affected.")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Simulate an incident with Sentinel AI")
    parser.add_argument(
        "--service",
        default="sentinel-api",
        help="Service name to simulate (default: sentinel-api)",
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        default="missing_env_var",
        help="Failure scenario to simulate",
    )
    args = parser.parse_args()

    asyncio.run(run_simulation(args.service, args.scenario))


if __name__ == "__main__":
    main()
