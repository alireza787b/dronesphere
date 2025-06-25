# DroneSphere Architecture Review & Decisions

## 🏗️ System Architecture (3-Component Model)

Based on your clarification, DroneSphere consists of three distinct components:

### 1. **Frontend Application** (Future Steps)
- **Technology**: React/Next.js
- **Purpose**: User interface for drone control
- **Location**: Web browser
- **Communication**: REST/WebSocket to Server

### 2. **Server Application** (Current Focus)
- **Technology**: FastAPI + LLM integration
- **Purpose**: 
  - Natural language processing
  - Command translation
  - Business logic
  - API for frontend
  - Drone fleet management
- **Location**: Cloud or local server
- **Components**:
  - FastAPI REST/WebSocket endpoints
  - NLP service (spaCy)
  - Domain logic
  - Database integration
  - Message queue (RabbitMQ)

### 3. **Drone Controller** (Raspberry Pi)
- **Technology**: Python + MAVSDK
- **Purpose**: Direct drone control
- **Location**: Raspberry Pi on drone
- **Components**:
  - MAVSDK for Pixhawk communication
  - Command receiver (from server)
  - Telemetry sender
  - Local safety logic

## 📁 Revised Project Structure

```
dronesphere/
├── server/                     # Main server application
│   ├── src/
│   │   ├── core/              # Domain logic (current)
│   │   ├── adapters/          # External adapters
│   │   ├── application/       # Use cases
│   │   └── infrastructure/    # FastAPI, DB, etc.
│   ├── tests/
│   └── pyproject.toml
│
├── drone_controller/          # Raspberry Pi drone controller
│   ├── src/
│   │   ├── mavsdk_adapter/   # MAVSDK integration
│   │   ├── command_receiver/ # Receives from server
│   │   ├── telemetry/        # Sends data to server
│   │   └── safety/           # Local safety checks
│   ├── requirements.txt
│   └── main.py
│
├── frontend/                  # Future React/Next.js app
│   ├── src/
│   └── package.json
│
└── shared/                    # Shared types/contracts
    └── proto/                 # Protocol definitions

## 🔄 Current Status & Issues

### ✅ Completed
- Project structure (Step 1)
- Development environment (Step 2)
- Core domain models (Step 3 - in progress)

### ❌ Issues Found
1. **Duplicate DomainEvent classes** causing import confusion
2. **Dataclass field ordering** in events/commands
3. **Unclear separation** between server and drone components

### 🛠️ Fixes Applied
1. Single canonical DomainEvent in `src/shared/domain/event.py`
2. All event fields have defaults to avoid ordering issues
3. Command classes use properties instead of dataclass fields

## 📦 Poetry vs UV Decision

### Current: Poetry
- **Pros**: Mature, stable, good dependency resolution
- **Cons**: Slower, complex for some operations

### Proposed: UV (by Astral)
- **Pros**: 
  - 10-100x faster than pip/poetry
  - Drop-in pip replacement
  - Better monorepo support
  - Simpler configuration
- **Cons**: 
  - Newer tool (but from makers of Ruff)
  - Less ecosystem integration

### ✅ Recommendation: Switch to UV
- Better fits our multi-component architecture
- Faster development cycles
- Simpler for Raspberry Pi deployment

## 🚀 Migration Plan

### Phase 1: Fix Current Issues
1. Run domain fixes: `python scripts/fix_all_domain_issues.py`
2. Test domain models: `python scripts/test_domain_models.py`
3. Commit fixes

### Phase 2: Restructure for 3-Component Model
1. Move current code to `server/` directory
2. Create `drone_controller/` structure
3. Update imports and paths

### Phase 3: Migrate to UV
1. Install UV
2. Convert pyproject.toml
3. Update development scripts
4. Update CI/CD

## 📝 Next Steps Priority

1. **Fix domain model issues** (immediate)
2. **Complete NLP adapter** (Step 4)
3. **Restructure project** for 3 components
4. **Migrate to UV** (can be done anytime)
5. **Implement drone controller** component

## 🤝 Agreement Points

Before proceeding, confirm:
- [ ] Domain model fixes are working
- [ ] 3-component architecture is correct
- [ ] UV migration is desired
- [ ] Priority order is acceptable