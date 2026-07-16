---
date: 2026-05-21
context: Runnable demo of the React + Go (Gin/GORM/Postgres) + Pact stack between the two
purpose: illustrate the workflow described in test-stack-react-go-postgresql.md on a concrete case
---

# test-stack-demo-billing

Mini "billing" application that demonstrates the recommended test stack:

- **Go backend**: a `POST /api/rate` endpoint that calculates the cost of a call from a tariff stored in the database.
- **React frontend**: a form that calls the endpoint and displays the cost.
- **Contract testing**: Pact between the two, with no E2E dependency.

## The domain

Pricing calculation for a phone call:
- Input: duration (seconds) + destination number (E.164).
- Lookup: find in the database the tariff whose prefix matches (longest-prefix match).
- Output: cost (duration rounded up to the next minute × tariff).

Simplistic — but sufficient to demonstrate:
- Pure logic → unit tests + PBT.
- Persistence → testcontainers-go + real Postgres.
- HTTP API → httptest + Gin.
- Frontend → Vitest + RTL + MSW.
- Contract → Pact consumer (JS) + provider (Go).

## Structure

```
test-stack-demo-billing/
├── api/                          # Go backend
│   ├── pricing/                  # pure logic (unit + rapid PBT)
│   ├── repository/               # GORM + tariff (integration testcontainers)
│   ├── handlers/                 # Gin handlers (httptest)
│   ├── pacts/                    # Pact provider verification
│   └── migrations/               # SQL migrations (golang-migrate)
│
├── frontend/                     # React + Vite + TS
│   └── src/
│       ├── api/                  # client + Pact consumer test
│       ├── components/           # RateCalculator + Vitest+RTL test
│       └── test/                 # MSW handlers, setup
│
├── pacts/                        # generated contracts (CI artifact)
└── docker-compose.yml            # Postgres + API + Front for E2E
```

## Prerequisites

- Go ≥ 1.22
- Node ≥ 20 + pnpm (or npm)
- Docker (for testcontainers + docker-compose)

## Local setup (without Docker)

### Backend

```bash
cd api
go mod tidy
# Start Postgres separately (or docker run --rm -d -p 5432:5432 -e POSTGRES_PASSWORD=test postgres:16)
export DATABASE_URL="postgres://test:test@localhost:5432/billing?sslmode=disable"
go run .
```

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Open http://localhost:5173.

## Running the tests

### Go backend

```bash
cd api

# Unit (fast, no Docker)
go test -race ./pricing/...

# Handlers (fast, no Docker)
go test -race ./handlers/...

# DB integration (slow, requires Docker)
go test -race -tags=integration ./repository/...

# Pact provider verification (slow, requires Docker + pact-broker OR local pact file)
PACT_FILE=../pacts/react-frontend-go-api.json go test -race -tags=pact ./pacts/...

# Lint
golangci-lint run

# Mutation (slow, on changed packages)
gremlins unleash ./pricing/...
```

### React frontend

```bash
cd frontend

# Unit + components
pnpm test:ci

# Pact consumer (generates the pact file in ../pacts/)
pnpm test:pact

# Mutation (slow)
pnpm test:mutation

# Lint
pnpm lint
```

### Cross-stack (E2E)

```bash
docker compose up --build --wait
pnpm --dir frontend playwright test
docker compose down
```

## Enforcing the RED→GREEN cycle (§0 gate)

This demo wires the hardened pre-commit gate from
[`tdd-skill/scripts/tdd-verify-cycle.sh`](../../tdd-skill/scripts/tdd-verify-cycle.sh)
via [`lefthook.yml`](lefthook.yml). The gate **proves** the cycle at commit time
(the staged production code is reverted to HEAD, the test must fail; restored, it
must pass) instead of trusting that tests were written first. See
[`tdd-skill/hooks-python.md`](../../tdd-skill/hooks-python.md) §0 for the full
rationale.

Because the project is polyglot, `lefthook.yml` runs the gate twice — once scoped
to Go (`api/`, `*_test.go`), once to TS (`frontend/src/`, `*.{test,spec}.tsx`).
On any commit, only the command whose production files are staged does real work;
the other sees no production files of its language and no-ops. A clean cycle
touches one language.

```bash
# one-time, treating this folder as its own repo:
git init && lefthook install

# Go cycle:
echo './pricing::TestRateCall_RoundsUp' > .tdd-cycle
git add api/pricing/pricing.go api/pricing/pricing_test.go
git commit -m 'test+feat(pricing): round up to the next minute'   # gate proves RED→GREEN
rm .tdd-cycle

# TS cycle:
echo 'RateCalculator shows the cost' > .tdd-cycle
git add frontend/src/components/RateCalculator.tsx frontend/src/components/RateCalculator.test.tsx
git commit -m 'test+feat: show the cost'
rm .tdd-cycle

# behaviour-preserving change (either language):
echo 'refactor' > .tdd-cycle
```

The `run:` path in `lefthook.yml` is monorepo-relative (`../../tdd-skill/…`); in a
standalone project you would vendor the script (e.g. into `scripts/`) and point
`run:` at it. `--no-verify` bypasses the gate, like any pre-commit — the hard
backstop is the mutation-testing CI (see below).

## Pact workflow

The end-to-end pattern:

```
1. The frontend writes a consumer test describing what it expects from the API.
   → pnpm test:pact generates pacts/react-frontend-go-api.json.

2. The pact file is published to a broker (Pactflow / self-hosted) — or for
   this demo, shared via the filesystem (../pacts/).

3. The backend runs its "provider verification" tests:
   it starts the API, sets up states (e.g. "tariff for prefix 33 exists"),
   and plays the pact against it.
   → If the pact is red, the backend PR is blocked.
```

## Intentional bugs (for learning)

As in `pbt-examples-sip/`, a bug is left in place for the tests to demonstrate it:

- `api/pricing/pricing.go` — `RateCall` rounds up to the next minute but has an edge case at 0 seconds. PBT reveals it.

The bug is commented `// BUG:` in the code.

## Relationship with the docs

- Method: `../../docs/test-stack-react-go-postgresql.md`
- PBT: `../../docs/property-based-testing-hypothesis-deep-dive.md`
- Deterministic tools: `../../docs/test-generation-from-spec.md`
- TDD skill: `../../tdd-skill/`

## Limitations of this demo

- No auth, no pagination, no sophisticated error handling — this is intentional.
- The pact is generated locally and shared via filesystem; in production, use Pactflow or a self-hosted broker.
- The frontend is minimal (a single form) — no router or state management.
- Mutation testing CI not included (template in `tdd-skill/hooks-*.md`).
