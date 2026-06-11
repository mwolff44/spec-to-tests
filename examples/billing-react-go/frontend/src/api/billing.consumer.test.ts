// Pact consumer test for the React frontend.
// Running this test (pnpm test:pact) generates ../pacts/react-frontend-go-api.json
// which the Go provider then verifies.
//
// The contract describes what the frontend EXPECTS — not what the backend HAPPENS to return.
// Use loose matchers: data types > exact values.
import { PactV4, MatchersV3 } from '@pact-foundation/pact';
import path from 'node:path';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import { rateCall, RateError } from './billing';

const { integer, string, regex } = MatchersV3;

const provider = new PactV4({
  consumer: 'react-frontend',
  provider: 'go-api',
  // pacts/ folder is shared with the Go provider via filesystem in this demo.
  dir: path.resolve(__dirname, '../../../pacts'),
  logLevel: 'warn',
});

describe('Pact: react-frontend → go-api', () => {
  it('returns the cost when a tariff exists for the destination', async () => {
    await provider
      .addInteraction()
      .given('a tariff for prefix 336 exists at rate 1500')
      .uponReceiving('a rate request for a French mobile number')
      .withRequest('POST', '/api/rate', (builder) => {
        builder
          .headers({ 'Content-Type': 'application/json' })
          .jsonBody({
            duration_seconds: 120,
            destination: '+33612345678',
          });
      })
      .willRespondWith(200, (builder) => {
        builder
          .headers({ 'Content-Type': regex('application/json.*', 'application/json; charset=utf-8') })
          .jsonBody({
            cost_millicents: integer(3000),
            tariff_prefix: string('336'),
          });
      })
      .executeTest(async (mockServer) => {
        const result = await rateCall(
          { duration_seconds: 120, destination: '+33612345678' },
          mockServer.url,
        );
        expect(result.tariff_prefix).toBe('336');
        expect(typeof result.cost_millicents).toBe('number');
        expect(result.cost_millicents).toBeGreaterThan(0);
      });
  });

  it('returns 404 when no tariff matches', async () => {
    await provider
      .addInteraction()
      .given('no tariff exists for prefix 999')
      .uponReceiving('a rate request for an unsupported destination')
      .withRequest('POST', '/api/rate', (builder) => {
        builder
          .headers({ 'Content-Type': 'application/json' })
          .jsonBody({
            duration_seconds: 60,
            destination: '+99912345678',
          });
      })
      .willRespondWith(404, (builder) => {
        builder
          .headers({ 'Content-Type': regex('application/json.*', 'application/json; charset=utf-8') })
          .jsonBody({ error: string('no tariff for destination') });
      })
      .executeTest(async (mockServer) => {
        await expect(
          rateCall(
            { duration_seconds: 60, destination: '+99912345678' },
            mockServer.url,
          ),
        ).rejects.toBeInstanceOf(RateError);
      });
  });
});
