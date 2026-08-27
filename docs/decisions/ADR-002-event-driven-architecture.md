# ADR-002: Event-Driven Communication via Kafka

## Status
Accepted

## Context
Sentinel AI has multiple services that need to communicate: incident management, deployment tracking, Kubernetes monitoring, AI analysis, and notifications. Synchronous HTTP calls between services would create tight coupling, single points of failure, and make the system difficult to scale independently.

## Decision
Use **Apache Kafka** as the central event bus for all inter-service communication:

- Services communicate exclusively through Kafka topics
- Each service owns its data store (PostgreSQL for incidents/deployments)
- Events carry enough context for consumers to process independently
- Every event has a unique `event_id` for idempotent processing
- Failed messages are routed to dead-letter queues (DLQ)

### Topic Design
- `incidents.created`, `incidents.updated`, `incidents.resolved`
- `deployments.created`, `deployments.failed`
- `ai.analysis.started`, `ai.analysis.completed`
- `ai.remediation.proposed`
- `notifications`

### Consumer Patterns
- Idempotent processing via event ID tracking
- Exponential backoff retry (via `tenacity`)
- DLQ routing for permanently failed messages
- Graceful shutdown with signal handling

## Consequences

### Positive
- Services are decoupled and can scale independently
- System is resilient — if one service is down, events queue up
- Full audit trail of all state changes
- New consumers can subscribe to existing topics without modifying producers
- Natural fit for incident-driven workflows

### Negative
- Increased operational complexity (Kafka cluster management)
- Eventual consistency — state may be temporarily inconsistent across services
- Debugging is harder than synchronous systems
- Requires careful topic partitioning and consumer group management

### Mitigations
- Structured logging with `structlog` for cross-service tracing
- `X-Request-ID` propagated through all events
- OpenTelemetry distributed tracing integration
