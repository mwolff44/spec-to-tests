// Default MSW handlers. Individual tests override with server.use(...).
// Keeping the default set small means tests are explicit about what they expect.
import { http, HttpResponse } from 'msw';

export const handlers = [
  // No default — every test must declare what it expects.
  // This forces explicitness and avoids "stale handler" bugs.
  http.all('*', () =>
    HttpResponse.json(
      { error: 'no MSW handler declared for this request' },
      { status: 599 },
    ),
  ),
];
