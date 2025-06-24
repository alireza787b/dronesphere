# ADR-001: Use Hexagonal Architecture

Date: 2024-01-20

## Status
Accepted

## Context
We need a flexible, testable architecture for our drone control system.

## Decision
We will use Hexagonal Architecture (Ports and Adapters).

## Consequences
- Clear separation of business logic and infrastructure
- Easy to test and mock external dependencies
- More initial complexity but better long-term maintainability
