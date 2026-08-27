# ADR-001: Dual-Mode Simulation Architecture

## Status
Accepted

## Context
Sentinel AI is a complex system with many external dependencies: LLM providers, Kubernetes clusters, GitHub, Prometheus, Slack, and more. Running the full system requires API keys, network access, and live infrastructure. This creates barriers for:
- New developers setting up the project
- CI/CD pipelines testing without external dependencies
- Demos and presentations without live infrastructure
- Cost control during development

## Decision
Implement a **dual-mode simulation architecture** where every external integration has a simulation fallback:

1. **LLM Client**: Uses OpenAI/Anthropic when API keys are provided; otherwise generates deterministic, realistic expert-quality output via simulation
2. **Kubernetes**: Uses `K8sSimulator` to generate realistic cluster state (pods, events, logs) without a real cluster
3. **Metrics**: Uses `MetricsCollector` with scenario-based generation (healthy, OOM, connection exhaustion)
4. **Logs**: Uses `LogCollector` with pre-written realistic log sequences
5. **External APIs**: GitHub, Slack, Jira tools return realistic simulated responses

The mode is detected automatically at startup based on whether API keys are present.

## Consequences

### Positive
- Zero-config startup: `pip install -e . && uvicorn services.gateway.main:app` works immediately
- CI/CD can test the full pipeline without any external dependencies
- Demo-able in any environment (airplane mode, conference stage, etc.)
- Simulation output is realistic enough to serve as documentation
- No cost for AI API calls during development

### Negative
- Simulation output is deterministic, so it can't discover truly novel failure modes
- Developers might not realize they're in simulation mode
- Maintaining simulation quality requires updating alongside real integrations

### Mitigations
- The `is_simulation: true` field is included in all API responses
- Logs clearly indicate simulation mode at startup
- Simulation scenarios cover the most common real-world failure patterns
