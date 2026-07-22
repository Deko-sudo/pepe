# Architecture Decisions

## ADR-001: Monorepo Structure

**Status**: Accepted

**Context**: Pepe consists of multiple services (Mini App, API, Bot, Worker) that share common types and configurations.

**Decision**: Use a monorepo structure with separate apps and shared packages.

**Consequences**:
- Easier code sharing between services
- Unified CI/CD pipeline
- Single source of truth for shared types
- Potential for larger repository size

## ADR-002: FastAPI over Express

**Status**: Accepted

**Context**: Need a high-performance async backend for real-time market data.

**Decision**: Use FastAPI with Python 3.12 instead of Express.js.

**Consequences**:
- Native async support
- Better type safety with Pydantic
- Faster development with auto-generated docs
- Requires Python expertise in team

## ADR-003: PostgreSQL over SQLite

**Status**: Accepted

**Context**: Need a production-ready database for user data and market history.

**Decision**: Use PostgreSQL with async SQLAlchemy.

**Consequences**:
- Better scalability
- JSON support for complex data
- Requires separate database service
- More complex local development setup
