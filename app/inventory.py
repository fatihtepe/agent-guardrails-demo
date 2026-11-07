"""Tiny service inventory: the 'product code' the agent is allowed to change."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Service:
    name: str
    replicas: int
    env: str  # dev | staging | prod


VALID_ENVS = {"dev", "staging", "prod"}


def validate(service: Service) -> list[str]:
    """Return a list of problems; empty list means the service is valid."""
    problems = []
    if not service.name:
        problems.append("name is required")
    if service.env not in VALID_ENVS:
        problems.append(f"env must be one of {sorted(VALID_ENVS)}")
    if service.replicas < 1:
        problems.append("replicas must be >= 1")
    if service.env == "prod" and service.replicas < 2:
        problems.append("prod services need at least 2 replicas")
    if service.env == "staging" and service.replicas > 3:
        problems.append("staging services may not exceed 3 replicas")
    return problems


def total_replicas(services: list[Service], env: str) -> int:
    return sum(s.replicas for s in services if s.env == env)
