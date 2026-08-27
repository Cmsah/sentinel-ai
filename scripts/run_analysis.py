#!/usr/bin/env python3
"""Run AI analysis directly on a simulated incident.

Standalone script — no database or Kafka needed.
Just runs the multi-agent pipeline in simulation mode.

Usage:
    python -m scripts.run_analysis
    python -m scripts.run_analysis --scenario out_of_memory
    python -m scripts.run_analysis --scenario image_pull_error
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time

from services.ai.orchestrator import SentinelOrchestrator


SCENARIOS = {
    "missing_env_var": {
        "title": "Deployment failure — sentinel-api",
        "description": "Deployment v2.3.1 caused CrashLoopBackOff due to missing DATABASE_URL environment variable in ConfigMap",
        "severity": "critical",
    },
    "out_of_memory": {
        "title": "OOMKilled — sentinel-api",
        "description": "Container exceeded 256Mi memory limit due to connection pool exhaustion causing memory spike",
        "severity": "critical",
    },
    "image_pull_error": {
        "title": "ImagePullBackOff — sentinel-api",
        "description": "Failed to pull image registry.internal/sentinel-api:v2.3.2-INVALID — tag does not exist",
        "severity": "high",
    },
}


async def run(scenario: str, verbose: bool = False) -> None:
    """Run analysis on a given scenario."""
    config = SCENARIOS.get(scenario, SCENARIOS["missing_env_var"])

    print(f"\n🤖 Sentinel AI — Multi-Agent Analysis Pipeline")
    print(f"   Scenario: {scenario}")
    print(f"   Title: {config['title']}")
    print(f"   Severity: {config['severity']}")
    print(f"\n   Running 6 specialized agents...")
    print(f"   Agents: log → k8s → metrics → deployment → root_cause → remediation\n")

    orchestrator = SentinelOrchestrator()
    start = time.perf_counter()

    result = await orchestrator.analyze(
        incident_id=f"cli-{int(time.time())}",
        service_name="sentinel-api",
        title=config["title"],
        description=config["description"],
        severity=config["severity"],
        scenario=scenario,
    )

    duration = time.perf_counter() - start

    if verbose:
        print(json.dumps(result, indent=2, default=str))
    else:
        _print_summary(result, duration)


def _print_summary(result: dict, duration: float) -> None:
    """Print a human-readable summary of the analysis."""
    status = result.get("status", "unknown")

    if status == "failed":
        print(f"\n❌ Analysis failed: {result.get('error')}")
        return

    print(f"\n{'━'*60}")
    print(f"  ✅ Analysis Complete ({duration:.2f}s)")
    print(f"{'━'*60}\n")

    # Root cause
    rc = result.get("root_cause", {})
    confidence = rc.get("confidence", 0)
    analysis = rc.get("analysis", "")

    bar_len = int(confidence * 30)
    bar = "█" * bar_len + "░" * (30 - bar_len)
    print(f"  🔍 ROOT CAUSE  [{bar}] {confidence:.0%}")
    print(f"     {analysis[:300]}")
    if len(analysis) > 300:
        print(f"     ...")
    print()

    # Contributing factors
    factors = rc.get("contributing_factors", [])
    if factors:
        print(f"  📋 Contributing Factors ({len(factors)})")
        for i, f in enumerate(factors, 1):
            print(f"     {i}. {f}")
        print()

    # Timeline
    timeline = rc.get("timeline", [])
    if timeline:
        print(f"  📅 Timeline ({len(timeline)} events)")
        for event in timeline:
            print(f"     [{event.get('time', '?')}] {event.get('event', '?')}")
        print()

    # Agent results
    agents = result.get("agent_results", {})
    print(f"  🤖 Agent Confidence Scores")
    for name, data in agents.items():
        conf = data.get("confidence", 0)
        bar_len = int(conf * 20)
        bar = "█" * bar_len + "░" * (20 - bar_len)
        print(f"     {name:25s} [{bar}] {conf:.0%}")
    print()

    # Remediation
    rem = result.get("remediation", {})
    actions = rem.get("actions", [])
    if actions:
        print(f"  🔧 Remediation Actions ({len(actions)})")
        for action in actions:
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(
                action.get("risk_level", ""), "⚪"
            )
            print(f"     {risk_emoji} [{action.get('priority', '?').upper()}] {action.get('description', '')}")
        print()

    prevention = rem.get("prevention", [])
    if prevention:
        print(f"  🛡️  Prevention ({len(prevention)})")
        for i, p in enumerate(prevention, 1):
            print(f"     {i}. {p}")
        print()

    # Meta
    used = result.get("agents_used", [])
    print(f"  📊 Summary")
    print(f"     Agents: {', '.join(used)}")
    print(f"     Duration: {result.get('duration_seconds', duration):.2f}s")
    print(f"     Simulation: {result.get('is_simulation', True)}")
    print(f"\n{'━'*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Run AI incident analysis")
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        default="missing_env_var",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.scenario, args.verbose))


if __name__ == "__main__":
    main()
