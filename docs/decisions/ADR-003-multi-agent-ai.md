# ADR-003: Multi-Agent AI Architecture with LangGraph

## Status
Accepted

## Context
Incident analysis requires examining multiple data sources: logs, Kubernetes state, metrics, and deployment history. A single LLM prompt analyzing all data at once would:
- Lose detail (context window limits)
- Miss cross-domain correlations
- Be difficult to debug and iterate on
- Not parallelize well

## Decision
Use **LangGraph** to orchestrate a pipeline of specialized AI agents:

### Agent Architecture
```
Start → [Log Agent, K8s Agent, Metrics Agent, Deployment Agent] (parallel)
       → Root Cause Agent (synthesis)
       → Remediation Agent (actionable fixes)
       → End
```

### Agent Responsibilities
1. **Log Agent**: Parse and analyze application logs for error patterns
2. **K8s Agent**: Examine pod states, events, ConfigMaps, and deployment rollout
3. **Metrics Agent**: Analyze time-series metrics (CPU, memory, latency, connections)
4. **Deployment Agent**: Identify what changed in the failing deployment
5. **Root Cause Agent**: Synthesize all findings into a coherent root cause narrative
6. **Remediation Agent**: Propose specific, actionable fixes with risk assessment

### State Management
- Shared `AgentState` flows through the graph
- Each agent reads relevant fields and writes its analysis results
- The root cause agent receives all prior agent outputs

## Consequences

### Positive
- Parallel execution of independent analyses reduces total analysis time
- Specialized prompts produce higher-quality analysis per domain
- Graph structure is visual and auditable
- Adding new agents is non-disruptive
- Each agent can be tested and improved independently
- The root cause agent sees a comprehensive picture

### Negative
- More complex than a single-prompt approach
- Requires managing state across multiple agent invocations
- Agent prompt tuning is needed for each domain
- Higher latency than a single LLM call (but compensated by parallelism)

### Alternatives Considered
- **Single prompt**: Rejected due to context window limits and quality
- **Sequential agents**: Rejected due to latency (parallel is faster)
- **AutoGen/CrewAI**: Rejected in favor of LangGraph for its graph-based control flow
