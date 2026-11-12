# When to Use a Double

> Adapted from Matt Pocock, `mattpocock/skills`. The original boundary guidance
> is preserved; the internal-double rule is revised for the risk-based doctrine.
> See `agent-discipline.md` §4 and `references/test-design.md` §6.

A **double** is a test substitute for a collaborator. Use one when the real
collaborator is an external boundary or is impractical, and use the real
collaborator when it is fast, deterministic and practical.

## Prefer real collaborators

If the real collaborator is quick and deterministic, use it. Real wiring catches
integration mistakes that a double silently removes.

## Double at system boundaries

- External APIs (payment, email, etc.)
- Network services that are unavailable or non-deterministic in the test
- Time / randomness
- File system when a real temporary directory is impractical
- Database: prefer a real test database or testcontainers; a double is a
  fallback, not the default

## Internal doubles are allowed with a reason

- A slow or non-deterministic dependency inside the module can justify a fake.
- State the reason in the test or the PR.
- Prefer a small fake with a faithful contract over call-count mocking.
- **Never double the subject under test.** The behavior the test claims to
  verify must be real.
- Do not assert internal call counts or ordering as the behavior.

## Designing for mockability (at boundaries)

At system boundaries, design interfaces that are easy to substitute:

**1. Use dependency injection**

Pass external dependencies in rather than creating them internally:

```typescript
// Easy to substitute
function processPayment(order, paymentClient) {
  return paymentClient.charge(order.total);
}

// Hard to substitute
function processPayment(order) {
  const client = new StripeClient(process.env.STRIPE_KEY);
  return client.charge(order.total);
}
```

**2. Prefer SDK-style interfaces over generic fetchers**

Create specific functions for each external operation instead of one generic
function with conditional logic:

```typescript
// GOOD: Each function is independently substitutable
const api = {
  getUser: (id) => fetch(`/users/${id}`),
  getOrders: (userId) => fetch(`/users/${userId}/orders`),
  createOrder: (data) => fetch('/orders', { method: 'POST', body: data }),
};

// BAD: Substituting requires conditional logic inside the double
const api = {
  fetch: (endpoint, options) => fetch(endpoint, options),
};
```

The SDK approach means:
- Each double returns one specific shape
- No conditional logic in test setup
- Easier to see which endpoints a test exercises
- Type safety per endpoint
