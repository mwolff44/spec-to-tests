---
date: 2026-05-20
context: Concrete application of testing principles (PBT, mutation, multi-agent AI, deterministic)
       to the stack: Pure React frontend + Go backend (Gin + GORM + PostgreSQL)
scope: tools, workflow CI, AI prompts, contract testing between the two sides
prerequisites: have read test-generation-from-spec.md, test-quality-tools-survey.md
---

# Testing Stack — React + Go (Gin/GORM/PostgreSQL)

## TL;DR

For this stack, the testing pyramid that maximizes confidence at reasonable cost:

```
┌─────────────────────────────────────────────────────────────┐
│ CROSS-STACK                                                 │
│  • Contract testing      : Pact (consumer JS / provider Go) │
│  • E2E                   : Playwright against docker stack   │
│  • Gherkin acceptance    : optional via Cucumber.js/godog   │
├─────────────────────────────────────────────────────────────┤
│ FRONTEND (React)                                            │
│  • Unit / component      : Vitest + React Testing Library   │
│  • API mocking           : MSW (Mock Service Worker)        │
│  • PBT                   : fast-check on pure logic         │
│  • Mutation              : StrykerJS (incremental, PR)      │
│  • Smells / forbidden    : ESLint + plugin-vitest/jest      │
├─────────────────────────────────────────────────────────────┤
│ BACKEND (Go : Gin + GORM + PostgreSQL)                      │
│  • Unit                  : testing + testify                │
│  • HTTP handlers         : httptest + gin.Engine            │
│  • DB integration        : testcontainers-go + golang-migrate│
│  • PBT                   : rapid (pure logic, routing)      │
│  • Mutation              : gremlins (per package, PR)       │
│  • Smells                : golangci-lint (thelper, paralleltest, errcheck, testifylint) │
│  • BDD                   : godog (acceptance, optional)     │
└─────────────────────────────────────────────────────────────┘
```

No mocked DB in unit tests: we use **testcontainers-go** (ephemeral PostgreSQL via Docker). This is the most critical element of the backend, and it is the direct defense against "sqlmock theatre" (mocked GORM that does not reproduce real SQL behavior).

---

## 1. Mapping — what to test where

| Layer | Main tool | Speed | What we test |
|---|---|---|---|
| **Front** — pure functions, utils, formatters | Vitest | ms | Isolated business logic |
| **Front** — React components | Vitest + RTL | ms–s | Rendering, user interactions |
| **Front** — views with API | Vitest + RTL + MSW | s | Components with simulated data |
| **Front** — logic invariants | fast-check | s | Pure properties (parsing, calculation, state) |
| **Back** — pure functions (Go) | testing + testify | µs–ms | Pure functions, helpers, utils |
| **Back** — HTTP handlers | httptest + gin | ms | Gin handlers, validation, routing |
| **Back** — repository / GORM | testcontainers-go + Postgres | s | Real SQL, migrations, transactions |
| **Back** — pure logic invariants | rapid | s | Properties (pricing, routing, state) |
| **Cross** — contract API | Pact | s | Front↔back compatibility without full E2E |
| **Cross** — E2E | Playwright | s–min | Complete user journey, prod-like |

The principle: **the higher the test in the stack, the fewer we write** (Mike Cohn's pyramid). PBT short-circuits this by increasing the **strength** of lower-level tests, not their quantity.

---

## 2. React Frontend

### 2.1 Minimal recommended setup

```json
// package.json (excerpt)
{
  "scripts": {
    "test": "vitest",
    "test:ci": "vitest run --coverage",
    "test:mutation": "stryker run",
    "test:e2e": "playwright test"
  },
  "devDependencies": {
    "vitest": "^2",
    "@vitest/coverage-v8": "^2",
    "@vitest/browser": "^2",
    "@testing-library/react": "^16",
    "@testing-library/user-event": "^14",
    "@testing-library/jest-dom": "^6",
    "jsdom": "^25",
    "msw": "^2",
    "fast-check": "^3",
    "@stryker-mutator/core": "^8",
    "@stryker-mutator/vitest-runner": "^8",
    "@playwright/test": "^1.48",
    "eslint-plugin-vitest": "^0.5",
    "eslint-plugin-testing-library": "^7",
    "eslint-plugin-jest-dom": "^5"
  }
}
```

### 2.2 Component tests — Vitest + RTL

**Iron rules** (from 2025 best practices):

1. **Test what the user sees**, not the implementation.
2. **Query priority**: `getByRole` > `getByLabelText` > `getByText` >>> `getByTestId`. The `data-testid` is a last resort.
3. **No manual `act()`** except in extreme cases — `userEvent` handles it.
4. **`userEvent` > `fireEvent`** in 95% of cases (simulates browser better).
5. **AAA pattern**: Arrange / Act / Assert, visible in each test.

Canonical example:

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { LoginForm } from './LoginForm';

describe('LoginForm', () => {
  it('shows an error when submitted without a password', async () => {
    // Arrange
    const user = userEvent.setup();
    render(<LoginForm onSubmit={() => {}} />);

    // Act
    await user.type(screen.getByLabelText(/email/i), 'alice@example.com');
    await user.click(screen.getByRole('button', { name: /log in/i }));

    // Assert
    expect(await screen.findByRole('alert')).toHaveTextContent(/password/i);
  });
});
```

**Anti-patterns to avoid** (detected by ESLint with `eslint-plugin-testing-library`):

- `container.querySelector(...)` — use an RTL query.
- Waiting with `setTimeout` — use `findBy*` or `waitFor`.
- Testing internal CSS classes — test behavior, not style.
- `wrapper.instance()` or `enzyme`-style — RTL no longer permits it, and that is good.

### 2.3 API mocking — MSW

**MSW (Mock Service Worker)** intercepts requests at the network level, not at the application code level. Major advantage: your production code is not aware of the mock, and the same MSW handler works in tests **and** in dev (mode `start()`).

```typescript
// src/test/msw-handlers.ts
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/users/:id', ({ params }) => {
    return HttpResponse.json({ id: params.id, name: 'Alice' });
  }),
  http.post('/api/sessions', async ({ request }) => {
    const body = await request.json();
    if (!body.password) {
      return new HttpResponse(null, { status: 400 });
    }
    return HttpResponse.json({ token: 'fake-jwt' });
  }),
];

// src/test/setup.ts
import { setupServer } from 'msw/node';
import { handlers } from './msw-handlers';

export const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

The `onUnhandledRequest: 'error'` is essential: any unmocked API call fails the test. This prevents "green tests that silently called the real API in dev".

### 2.4 PBT with fast-check on the frontend

Where PBT shines on the React side:

- **Reducers / state machines** (Redux, Zustand, useReducer) — idempotence and invariant properties.
- **Form validation** — round-trip `parse(serialize(x)) === x`.
- **Price calculations, totals, taxes** — commutativity, associativity properties.
- **URL builders / parsers** — round-trip.
- **Sorting, filtering, grouping** — algebraic properties.

Example on a reducer:

```typescript
import * as fc from 'fast-check';

const action = fc.oneof(
  fc.record({ type: fc.constant('add'), item: itemArb }),
  fc.record({ type: fc.constant('remove'), id: fc.uuid() }),
  fc.record({ type: fc.constant('clear') }),
);

it('total is always >= 0 and matches sum(items)', () => {
  fc.assert(
    fc.property(fc.array(action), (actions) => {
      const state = actions.reduce(cartReducer, initialState);
      expect(state.total).toBeGreaterThanOrEqual(0);
      expect(state.total).toEqual(
        state.items.reduce((s, i) => s + i.price * i.qty, 0),
      );
    }),
  );
});
```

This is the equivalent of the `RuleBasedStateMachine` Hypothesis (cf. `pbt-sip/`), but on the React side.

### 2.5 Mutation testing with StrykerJS

Minimal configuration in `stryker.config.json`:

```json
{
  "$schema": "./node_modules/@stryker-mutator/core/schema/stryker-schema.json",
  "packageManager": "pnpm",
  "testRunner": "vitest",
  "reporters": ["progress", "clear-text", "html"],
  "incremental": true,
  "incrementalFile": ".stryker-tmp/incremental.json",
  "mutate": [
    "src/**/*.{ts,tsx}",
    "!src/**/*.{test,spec}.{ts,tsx}",
    "!src/test/**",
    "!src/main.tsx"
  ],
  "thresholds": { "high": 80, "low": 60, "break": 60 }
}
```

**On the frontend, mutation testing often reveals**:
- Ternary conditions on CSS classes never tested (`isError ? 'red' : 'gray'` mutated to `isError ? 'gray' : 'red'` survives if no one checks the color).
- Mocked form validation — `expect(form).toBeInvalid()` without assertion on the message.
- Absence guard-rails (`if (!user) return null`) not covered by tests.

The typical case of "perpetually green" on the frontend: we render a component, verify it renders, without verifying what it renders.

### 2.6 ESLint — test-aware config

```js
// eslint.config.js
import vitest from 'eslint-plugin-vitest';
import testingLibrary from 'eslint-plugin-testing-library';
import jestDom from 'eslint-plugin-jest-dom';

export default [
  {
    files: ['**/*.{test,spec}.{ts,tsx}'],
    plugins: {
      vitest,
      'testing-library': testingLibrary,
      'jest-dom': jestDom,
    },
    rules: {
      ...vitest.configs.recommended.rules,
      ...testingLibrary.configs.react.rules,
      ...jestDom.configs.recommended.rules,
      'vitest/expect-expect': 'error',
      'vitest/no-disabled-tests': 'error',
      'vitest/no-focused-tests': 'error',
      'vitest/no-conditional-expect': 'error',
      'vitest/valid-expect': 'error',
      'testing-library/no-node-access': 'error',      // no querySelector
      'testing-library/prefer-screen-queries': 'error',
      'testing-library/no-wait-for-multiple-assertions': 'error',
      'jest-dom/prefer-checked': 'error',
      'jest-dom/prefer-enabled-disabled': 'error',
      'jest-dom/prefer-in-document': 'error',
    },
  },
];
```

These ESLint rules catch at lint-time a large number of test smells that human review would miss.

---

## 3. Go Backend (Gin + GORM + PostgreSQL)

### 3.1 Minimal setup

```go
// go.mod (excerpt)
require (
    github.com/gin-gonic/gin v1.10.x
    gorm.io/gorm v1.25.x
    gorm.io/driver/postgres v1.5.x
    github.com/stretchr/testify v1.10.x
    github.com/testcontainers/testcontainers-go v0.33.x
    github.com/testcontainers/testcontainers-go/modules/postgres v0.33.x
    github.com/golang-migrate/migrate/v4 v4.18.x
    pgregory.net/rapid v1.1.x
    github.com/cucumber/godog v0.14.x   // optional BDD
    github.com/pact-foundation/pact-go/v2 v2.x  // contract testing
)
```

Linters via `.golangci.yml` (see `tdd-skill/hooks-go.md`).

### 3.2 Unit tests — pure functions

```go
// pricing/discount.go
package pricing

func ApplyDiscount(total int, percent int) int {
    if percent <= 0 { return total }
    if percent >= 100 { return 0 }
    return total - (total * percent / 100)
}

// pricing/discount_test.go
package pricing_test

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "yourapp/pricing"
)

func TestApplyDiscount(t *testing.T) {
    t.Parallel()
    cases := []struct{
        name      string
        total     int
        percent   int
        expected  int
    }{
        {"no discount when percent <= 0", 100, 0,   100},
        {"no discount when percent < 0",  100, -10, 100},
        {"clamp to zero at 100%",         100, 100, 0},
        {"clamp to zero above 100%",      100, 150, 0},
        {"half off",                       100, 50,  50},
    }
    for _, tc := range cases {
        tc := tc
        t.Run(tc.name, func(t *testing.T) {
            t.Parallel()
            assert.Equal(t, tc.expected, pricing.ApplyDiscount(tc.total, tc.percent))
        })
    }
}
```

`t.Parallel()` + `tc := tc` is the correct Go idiom. The `paralleltest` linter from golangci-lint enforces it correctly.

### 3.3 HTTP handler tests — httptest + Gin

Gin exposes a `*gin.Engine` that implements `http.Handler`. `httptest.NewRecorder` captures the response without a real server.

```go
// handlers/users_test.go
package handlers_test

import (
    "encoding/json"
    "net/http"
    "net/http/httptest"
    "strings"
    "testing"

    "github.com/gin-gonic/gin"
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/require"
    "yourapp/handlers"
)

func setupRouter(t *testing.T) *gin.Engine {
    t.Helper()
    gin.SetMode(gin.TestMode)
    r := gin.New()
    handlers.Register(r, fakeUserStore{})
    return r
}

func TestCreateUser_validBody_returns201(t *testing.T) {
    t.Parallel()
    r := setupRouter(t)

    body := strings.NewReader(`{"email":"alice@example.com","name":"Alice"}`)
    req := httptest.NewRequest(http.MethodPost, "/users", body)
    req.Header.Set("Content-Type", "application/json")
    rec := httptest.NewRecorder()

    r.ServeHTTP(rec, req)

    require.Equal(t, http.StatusCreated, rec.Code)
    var got map[string]any
    require.NoError(t, json.NewDecoder(rec.Body).Decode(&got))
    assert.NotEmpty(t, got["id"])
    assert.Equal(t, "alice@example.com", got["email"])
}

func TestCreateUser_invalidEmail_returns400(t *testing.T) {
    t.Parallel()
    r := setupRouter(t)

    req := httptest.NewRequest(http.MethodPost, "/users",
        strings.NewReader(`{"email":"not-an-email"}`))
    req.Header.Set("Content-Type", "application/json")
    rec := httptest.NewRecorder()

    r.ServeHTTP(rec, req)

    assert.Equal(t, http.StatusBadRequest, rec.Code)
}
```

At this level we **fake the store** (not mock — a simple in-memory implementation that implements the interface), not the DB. The goal is to test the **handler**: JSON binding, validation, HTTP codes, routing.

### 3.4 DB integration tests — testcontainers-go

**This is the most important element of the backend for this stack.** Starts a real Postgres in a Docker container, applies migrations, runs tests, tears down. Takes a few seconds per run, but in exchange: **we test real SQL, real GORM, real constraints**.

```go
// repository/users_integration_test.go
//go:build integration

package repository_test

import (
    "context"
    "testing"
    "time"

    "github.com/golang-migrate/migrate/v4"
    _ "github.com/golang-migrate/migrate/v4/database/postgres"
    _ "github.com/golang-migrate/migrate/v4/source/file"
    "github.com/stretchr/testify/require"
    "github.com/testcontainers/testcontainers-go/modules/postgres"
    tcwait "github.com/testcontainers/testcontainers-go/wait"
    "gorm.io/driver/postgres" as gpostgres
    "gorm.io/gorm"

    "yourapp/repository"
)

func setupDB(t *testing.T) (*gorm.DB, func()) {
    t.Helper()
    ctx := context.Background()

    pg, err := postgres.Run(ctx,
        "postgres:16-alpine",
        postgres.WithDatabase("testdb"),
        postgres.WithUsername("test"),
        postgres.WithPassword("test"),
        testcontainers.WithWaitStrategy(
            tcwait.ForLog("database system is ready to accept connections").
                WithOccurrence(2).
                WithStartupTimeout(30*time.Second),
        ),
    )
    require.NoError(t, err)

    dsn, err := pg.ConnectionString(ctx, "sslmode=disable")
    require.NoError(t, err)

    m, err := migrate.New("file://../migrations", dsn)
    require.NoError(t, err)
    require.NoError(t, m.Up())

    db, err := gorm.Open(gpostgres.Open(dsn), &gorm.Config{})
    require.NoError(t, err)

    return db, func() {
        sqlDB, _ := db.DB()
        sqlDB.Close()
        _ = pg.Terminate(ctx)
    }
}

func TestUserRepository_CreateAndFind(t *testing.T) {
    db, cleanup := setupDB(t)
    defer cleanup()

    repo := repository.NewUserRepository(db)

    u, err := repo.Create(repository.User{Email: "alice@example.com", Name: "Alice"})
    require.NoError(t, err)

    found, err := repo.FindByID(u.ID)
    require.NoError(t, err)
    assert.Equal(t, "alice@example.com", found.Email)
}

func TestUserRepository_DuplicateEmail_violatesUnique(t *testing.T) {
    db, cleanup := setupDB(t)
    defer cleanup()

    repo := repository.NewUserRepository(db)

    _, err := repo.Create(repository.User{Email: "dup@example.com"})
    require.NoError(t, err)
    _, err = repo.Create(repository.User{Email: "dup@example.com"})

    require.Error(t, err)
    assert.True(t, repository.IsUniqueViolation(err))   // semantic error
}
```

**Four patterns to observe**:

1. **Build tag `//go:build integration`** separates integration tests. CI: `go test -tags=integration ./...`.
2. **Container shared per package or per test** — depending on isolation needs. Sharing requires reset (TRUNCATE, or rolled-back transactions).
3. **Migrations applied via `golang-migrate`** — exactly the same as in prod.
4. **DB errors classified semantically** (`IsUniqueViolation`) — never compare raw Postgres string in a test.

**Performance tip**: start Postgres once for the entire package with `TestMain` + `t.Parallel()` on tests that use transactions with rollback.

### 3.5 PBT with rapid on pure logic

For calculation, routing, parsing functions: `rapid` is the Go equivalent of Hypothesis.

```go
package routing_test

import (
    "testing"
    "pgregory.net/rapid"
    "yourapp/routing"
)

func TestLookup_MoreSpecificPrefix_neverIncreasesCost(t *testing.T) {
    rapid.Check(t, func(t *rapid.T) {
        table := genRoutingTable().Draw(t, "table")
        number := rapid.StringMatching(`^\+[0-9]{8,15}$`).Draw(t, "number")

        baseCost := routing.Lookup(table, number).Cost

        moreSpecific := routing.AddRoute(table, number, baseCost/2)
        newCost := routing.Lookup(moreSpecific, number).Cost

        if newCost > baseCost {
            t.Fatalf("adding more specific route increased cost: %d > %d",
                newCost, baseCost)
        }
    })
}

func genRoutingTable() *rapid.Generator[routing.Table] { /* ... */ }
```

Identical in spirit to Hypothesis examples from the PBT deep-dive. The shrinking in `rapid` is solid.

**Stateful with rapid** (equivalent `RuleBasedStateMachine`):

```go
type cartMachine struct {
    cart  *Cart
    model map[ItemID]int  // simple oracle
}

func (m *cartMachine) Add(t *rapid.T) {
    id := rapid.UUID().Draw(t, "id")
    qty := rapid.IntRange(1, 10).Draw(t, "qty")
    m.cart.Add(id, qty)
    m.model[id] += qty
}

func (m *cartMachine) Remove(t *rapid.T) {
    if len(m.model) == 0 { t.Skip("empty") }
    var id ItemID
    for k := range m.model { id = k; break }
    m.cart.Remove(id)
    delete(m.model, id)
}

func (m *cartMachine) Check(t *rapid.T) {
    if m.cart.Total() != m.expectedTotal() {
        t.Fatal("invariant violated")
    }
}

func TestCart_stateful(t *testing.T) {
    rapid.Check(t, rapid.Run(&cartMachine{
        cart:  NewCart(),
        model: map[ItemID]int{},
    }))
}
```

### 3.6 Mutation testing — gremlins

Configuration `gremlins.yaml` (see `tdd-skill/hooks-go.md` §4 for the complete CI version). On this stack:

- Target **pure logic packages** first (pricing, routing, validation) — target mutation score ≥ 75%.
- Exclude handlers and repository packages on first pass — their integration tests cover a lot but mutants are expensive.
- Nightly full-suite mutation, PR mutation on changed packages only.

### 3.7 Smells / linters — golangci-lint config for tests

```yaml
# .golangci.yml (excerpt focused on tests)
linters:
  enable:
    - errcheck
    - staticcheck
    - govet
    - revive
    - testifylint     # detects misuse of testify (assert.Nil vs assert.NoError, etc.)
    - thelper         # t.Helper() must be called in helpers
    - tparallel       # t.Parallel correctness
    - paralleltest    # flags Test* without t.Parallel()
    - testpackage     # encourages *_test in separate package
    - errorlint       # detects incorrect error comparisons
    - bodyclose       # http response body close (important in handler tests!)

issues:
  exclude-rules:
    - path: _integration_test\.go
      linters: [errcheck]  # tolerance on integration setup
```

`testifylint` is crucial: it catches `assert.Nil(t, err)` that should be `assert.NoError(t, err)`, `assert.Equal(t, nil, x)` that should be `assert.Nil(t, x)`, etc. Classic source of false positives.

### 3.8 Optional BDD with godog

If you want to write executable Gherkin scenarios on the Go side:

```gherkin
# features/billing.feature
Feature: CDR rating

  Scenario: A standard call is rated at the destination rate
    Given a tariff with rate 0.02 per minute for destination "33"
    When I rate a CDR of 120 seconds to "+33612345678"
    Then the cost should be 0.04
```

```go
// features_test.go
package billing_test

import (
    "testing"
    "github.com/cucumber/godog"
)

func TestFeatures(t *testing.T) {
    suite := godog.TestSuite{
        ScenarioInitializer: InitializeScenario,
        Options: &godog.Options{
            Format:   "pretty",
            Paths:    []string{"features"},
            TestingT: t,
        },
    }
    if suite.Run() != 0 {
        t.Fatal("non-zero status returned, failed to run feature tests")
    }
}

func InitializeScenario(sc *godog.ScenarioContext) {
    var state struct{ tariff Tariff; cost float64 }

    sc.Step(`^a tariff with rate ([\d.]+) per minute for destination "(\w+)"$`,
        func(rate float64, dest string) error {
            state.tariff = Tariff{Rate: rate, Destination: dest}
            return nil
        })
    sc.Step(`^I rate a CDR of (\d+) seconds to "(.+)"$`,
        func(seconds int, number string) error {
            state.cost = Rate(state.tariff, seconds, number)
            return nil
        })
    sc.Step(`^the cost should be ([\d.]+)$`,
        func(expected float64) error {
            if math.Abs(state.cost - expected) > 1e-6 {
                return fmt.Errorf("got %f want %f", state.cost, expected)
            }
            return nil
        })
}
```

**When to use godog instead of plain Go tests**: when the spec has a real non-dev audience (PO, business), when business language must remain readable (pricing, billing rules, SIP dialplan). Otherwise, the overhead is not justified.

Best practices for godog (Cucumber 2024):
- Steps **orthogonal, small, composable**.
- Strict state per scenario via `ScenarioContext` (no package variables).
- Concurrent execution + random order to unmask state leaks.

---

## 4. Cross-stack

### 4.1 Contract testing — Pact (consumer JS / provider Go)

**The most profitable pattern** when front and back evolve independently.

On the **React (consumer)** side — describes what it expects:

```typescript
// pacts/users.consumer.test.ts
import { PactV3, MatchersV3 } from '@pact-foundation/pact';
import { fetchUser } from '../src/api/users';

const provider = new PactV3({
  consumer: 'react-frontend',
  provider: 'go-api',
});

describe('Users API', () => {
  it('returns a user by id', () => {
    provider
      .given('a user with id 42 exists')
      .uponReceiving('a request for user 42')
      .withRequest({ method: 'GET', path: '/api/users/42' })
      .willRespondWith({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: {
          id: MatchersV3.integer(42),
          email: MatchersV3.email('alice@example.com'),
          name: MatchersV3.string('Alice'),
        },
      });

    return provider.executeTest(async (mockServer) => {
      const user = await fetchUser(42, mockServer.url);
      expect(user.id).toBe(42);
    });
  });
});
```

The test generates a **Pact JSON file** published to a broker (Pactflow or self-hosted).

On the **Go (provider)** side — verifies it respects the contract:

```go
// pacts/provider_test.go
package main_test

import (
    "testing"
    "github.com/pact-foundation/pact-go/v2/provider"
)

func TestProvider_satisfiesReactFrontendPact(t *testing.T) {
    err := provider.NewVerifier().VerifyProvider(t, provider.VerifyRequest{
        ProviderBaseURL: "http://localhost:8080",
        Provider:        "go-api",
        PactURL:         "https://pact-broker.example.com/pacts/...",
        StateHandlers: provider.StateHandlers{
            "a user with id 42 exists": func(_ provider.ProviderState) (provider.ProviderStateResponse, error) {
                // setup the DB so the state matches
                seedUser(42, "alice@example.com", "Alice")
                return nil, nil
            },
        },
    })
    if err != nil {
        t.Fatal(err)
    }
}
```

**Why this is better than a full-stack E2E**:
- Temporal decoupling: front and back test their contract **separately**.
- Breaking changes caught at build time, not in integration.
- "Loose matchers": the contract says "an integer", not "exactly 42" → resilient to minor data changes.

**Key best practice**: keep matchers loose. The Pact rule is *"the loosest match that still catches breaking changes"*.

### 4.2 E2E — Playwright

For critical user journeys (login, payment, dialplan editor…). Not for everything — Playwright is expensive and slow.

```typescript
// e2e/login.spec.ts
import { test, expect } from '@playwright/test';

test('user can log in and reaches dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('alice@example.com');
  await page.getByLabel('Password').fill('s3cr3t');
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.getByRole('heading', { name: /welcome, alice/i })).toBeVisible();
});
```

Docker stack for Playwright in CI: `docker compose up -d postgres api frontend && playwright test`. Separate configuration for CI vs local.

**Anti-pattern**: stacking E2E for every feature. Limit: 10–30 critical journeys, never a matrix of combinations.

### 4.3 Type generation from OpenAPI

Key pattern for this stack: generate OpenAPI from Go, and generate TS types from the OpenAPI. Single source of truth for contracts.

Go → OpenAPI:
- **swaggo/swag** (annotations in code) — less clean.
- **kin-openapi** + manual write — cleaner.
- **goa** — full codegen from spec.
- **oapi-codegen** — codegen from hand-written OpenAPI spec.

OpenAPI → TS:
- **openapi-typescript** — generates a TS types file.
- **openapi-fetch** — typed client.
- **orval** — typed client + React Query hooks.

Combined, it means: you change a Go route, the front's `npm run typecheck` explodes if the contract is no longer respected. This is **static contract testing** complementary to Pact.

---

## 5. Workflow with AI — per layer

### 5.1 React Frontend

Good tasks for an AI agent:

| Task | Type | Risk |
|---|---|---|
| Generate an RTL test from an existing component | Low-medium | Insensitive tests, "perpetually green" without mutation gate |
| Generate MSW handlers from an OpenAPI | High | Quasi-deterministic |
| Generate fast-check properties from a reducer | Medium | Good — properties to validate |
| Generate Storybook stories from a component | High | Visual |
| Write Playwright E2E from a description | Low-medium | Fragile selectors, to review |

**Typical prompt for Vitest+RTL** (writer-agent):

```
You write component tests with Vitest + React Testing Library.
RULES:
- Query by role/label/text, NEVER by data-testid unless I tell you to.
- One Arrange, one Act, one Assert block per test, visible.
- Use userEvent, not fireEvent.
- Mock the network via MSW; do NOT vi.mock our own modules.
- Each test must contain at least one expect on a user-visible side effect.
- If the component depends on context (Router, QueryClient, theme), wrap it
  with a render helper, do not mock the context.

For each test, output:
1. The behavior under test in one sentence.
2. The Arrange/Act/Assert code.
Stop after 5 tests. Wait for human review before writing more.
```

Verifier-agent (as a Claude Code sub-agent):

```
Review the following test file against this checklist:
- [ ] No data-testid unless justified
- [ ] No vi.mock on our own modules
- [ ] Each test has an assertion on a user-visible effect
- [ ] No expect.toHaveBeenCalled() without arg matchers (over-mocking smell)
- [ ] No setTimeout / arbitrary waits
- [ ] Each test would fail if the component's behavior changed

For each violation: file:line, rule, suggested fix.
Return a structured report.
```

### 5.2 Go Backend

| Task | Type | Risk |
|---|---|---|
| Table-driven tests on pure function | Low | Quasi-deterministic |
| Gin handler tests from OpenAPI spec | Low-medium | Good |
| Setup testcontainers + repository tests | Medium | Common bug: not cleaning up resources |
| `rapid` properties from docstring | Medium | Good |
| godog steps from Gherkin | Medium | Check step orthogonality |

**Prompt for writer-agent Go**:

```
You write Go tests using the standard testing package + testify (require/assert).
RULES:
- Use table-driven tests for multi-case logic.
- t.Parallel() in every Test*; tc := tc inside the loop.
- require.NoError on setup errors that block the test; assert on outcomes.
- For handlers: httptest.NewRecorder + httptest.NewRequest, no live server.
- For DB: testcontainers-go + golang-migrate; do NOT mock GORM with sqlmock.
- One commit cycle = one test scenario. STOP after each Green.

For integration tests, use the //go:build integration tag.
```

### 5.3 Multi-agent pattern applied to this stack

A concrete workflow with 3 agents (cf. `test-generation-from-spec.md` §2.4):

```
┌──────────────────────────────────────────────────────────┐
│ Writer-Agent       : produces tests (Vitest/Go)          │
│                      from spec + types + Gherkin         │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│ Critic-Agent       : applies tdd-skill/agent-discipline  │
│                      + ESLint testing-library            │
│                      + golangci-lint testifylint         │
│                      → lists violations                  │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────┐
│ Coverage+Mutation  : deterministic                       │
│ Gate               : c8 / go cover + Stryker / gremlins  │
│                      → blocks if thresholds not met      │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼
                  Human review final
```

The **critic-agent** is a Claude Code sub-agent (or a separate OpenAI agent). The **mutation+coverage gate** is deterministic and runs in CI. The human only sees what has passed the two upstream stages.

---

## 6. Suggested CI pipeline

```yaml
# .github/workflows/test.yml — simplified view
on: [pull_request, push]

jobs:
  frontend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: pnpm install --frozen-lockfile
      - run: pnpm typecheck
      - run: pnpm lint
      - run: pnpm test:ci   # vitest + coverage

  frontend-mutation:
    needs: frontend-unit
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: pnpm/action-setup@v4
      - run: pnpm install --frozen-lockfile
      - run: pnpm test:mutation   # stryker incremental

  backend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
      - run: golangci-lint run
      - run: go test -race ./...

  backend-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
      - run: go test -race -tags=integration ./...

  backend-mutation:
    needs: backend-unit
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/setup-go@v5
      - run: |
          go install github.com/go-gremlins/gremlins/cmd/gremlins@latest
          PKGS=$(./scripts/changed-packages.sh)
          [ -n "$PKGS" ] && gremlins unleash $PKGS

  contract:
    needs: [frontend-unit, backend-integration]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pnpm test:pact:consumer && go test -tags=pact ./pacts/...

  e2e:
    needs: contract
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose up -d --wait
      - run: pnpm playwright test
```

Threshold logic:
- `frontend-unit`, `backend-unit`, `backend-integration`: blocking on PR.
- `frontend-mutation`, `backend-mutation`: blocking on PR only, scoped to changes.
- `contract`: blocking if pacts change.
- `e2e`: on main only (too expensive per PR).

---

## 7. PR review checklist (human review)

```
Frontend
[ ] All modified components have at least one RTL test
[ ] No data-testid added without justification
[ ] No vi.mock on internal module without justification
[ ] MSW handlers updated if API changed
[ ] Mutation score >= threshold on modified files
[ ] eslint-plugin-testing-library passes without warnings

Backend
[ ] t.Parallel() + tc := tc in all table-driven tests
[ ] testcontainers used, not sqlmock
[ ] DB errors classified semantically (IsUniqueViolation etc.)
[ ] golangci-lint passes (testifylint, paralleltest, thelper)
[ ] Mutation score >= threshold on modified packages
[ ] No //nolint without justification comment

Cross-stack
[ ] Pact contract updated if API changed
[ ] TS types regenerated from OpenAPI if spec changed
[ ] E2E touched only if critical journey changed
```

---

## 8. Articulation with other documents

| Doc | Contribution for this stack |
|---|---|
| `tdd-skill/SKILL.md` | Roles + spec-first + plan.md applicable to both sides |
| `tdd-skill/agent-discipline.md` | The 10 hard rules the critic-agent must enforce |
| `tdd-skill/hooks-typescript.md` | Pre-commit hooks + Stryker incremental for React |
| `tdd-skill/hooks-go.md` | Pre-commit hooks + gremlins for Go |
| `test-quality-tools-survey.md` | The 4 axes (coverage / mutation / smells / robustness) applied here |
| `property-based-testing-hypothesis-deep-dive.md` | The PBT pattern, transposed to fast-check and rapid |
| `test-generation-from-spec.md` | Multi-agent workflow + deterministic tools (Pact = deterministic) |
| `pbt-sip/` | Runnable demo of stateful pattern, transposable to Zustand store or stateful Go service |

---

## 9. Honest limitations

- **CI cost**: this pipeline with mutation+E2E+contract quickly exceeds 15 min per PR. For teams < 3 devs, that is too much. Start with unit + integration + lint, add mutation and contract as the team grows.
- **testcontainers-go** requires Docker available (CI and local) — true for most contexts, but verify on constrained self-hosted runners.
- **Pact** requires a broker (Pactflow or self-hosted). For a solo team, static contract testing via OpenAPI + generated types often suffices.
- **MSW** works in the browser but also in Node — watch out for different config.
- **godog** is useful only if business wants to read the specs. Otherwise, it is over-engineering.

---

## Sources

### Tools — project pages

- **Vitest** — https://vitest.dev/
- **React Testing Library** — https://testing-library.com/docs/react-testing-library/intro/
- **MSW** — https://mswjs.io/
- **fast-check** — https://fast-check.dev/
- **StrykerJS** — https://stryker-mutator.io/
- **Playwright** — https://playwright.dev/
- **Gin** — https://gin-gonic.com/
- **GORM** — https://gorm.io/
- **testify** — https://github.com/stretchr/testify
- **testcontainers-go** — https://golang.testcontainers.org/
- **golang-migrate** — https://github.com/golang-migrate/migrate
- **rapid** — https://github.com/flyingmutant/rapid
- **gremlins** — https://github.com/go-gremlins/gremlins
- **godog** — https://github.com/cucumber/godog
- **Pact (JS)** — https://github.com/pact-foundation/pact-js
- **Pact (Go)** — https://github.com/pact-foundation/pact-go
- **golangci-lint** — https://golangci-lint.run/
- **eslint-plugin-testing-library** — https://github.com/testing-library/eslint-plugin-testing-library
- **openapi-typescript** — https://openapi-ts.dev/
- **oapi-codegen** — https://github.com/oapi-codegen/oapi-codegen
- **orval** — https://orval.dev/

### Articles and guides

- *Golang Integration Test With Gin, Gorm, Testify, PostgreSQL* (2024). https://dev.to/truongpx396/golang-integration-test-with-gin-gorm-testify-postgresql-1e8m
- *Simplifying Integration Testing in Go with Test Containers — PostgreSQL*. https://medium.com/@radha.kandala/simplifying-integration-testing-in-go-with-test-containers-postgressql-2e3abec35f81
- *PACT Contract Testing — Microsoft ISE Dev Blog*. https://devblogs.microsoft.com/ise/pact-contract-testing-because-not-everything-needs-full-integration-tests/
- *Consumer-Driven Contract Testing in Practice* (Jan 2025). https://noraweisser.com/2025/01/31/consumer-driven-contract-testing-in-practice/
- *Integration Tests in Go with Cucumber, Testcontainers, and HTTPMock*. https://dev.to/joseboretto/integration-tests-in-go-with-cucumber-testcontainers-and-httpmock-5hb9
- *Guide to React Testing Library using Vitest* — Makers' Den. https://makersden.io/blog/guide-to-react-testing-library-vitest
- *Component Testing — Vitest official*. https://vitest.dev/guide/browser/component-testing
- *Intro to Godog — The Dumpster Fire Project*. https://thedumpsterfireproject.com/posts/godog-part-1/
