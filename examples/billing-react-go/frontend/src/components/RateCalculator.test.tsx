// Component test with Vitest + RTL + MSW.
// Network is intercepted at the boundary (MSW). No vi.mock on our own modules.
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { server } from '../test/setup';
import { RateCalculator } from './RateCalculator';

describe('<RateCalculator />', () => {
  it('shows the cost when the API returns a tariff', async () => {
    // Arrange
    server.use(
      http.post('/api/rate', async ({ request }) => {
        const body = (await request.json()) as Record<string, unknown>;
        expect(body.destination).toBe('+33612345678');
        return HttpResponse.json({
          cost_millicents: 3000,
          tariff_prefix: '336',
        });
      }),
    );
    const user = userEvent.setup();
    render(<RateCalculator />);

    // Act
    await user.clear(screen.getByLabelText(/duration/i));
    await user.type(screen.getByLabelText(/duration/i), '120');
    await user.click(screen.getByRole('button', { name: /rate/i }));

    // Assert — observable side effect: the cost is displayed to the user.
    const status = await screen.findByRole('status');
    expect(status).toHaveTextContent('0.03 €');
    expect(status).toHaveTextContent('336');
  });

  it('shows an error when the API returns 404', async () => {
    server.use(
      http.post('/api/rate', () =>
        HttpResponse.json(
          { error: 'no tariff for destination' },
          { status: 404 },
        ),
      ),
    );
    const user = userEvent.setup();
    render(<RateCalculator />);

    await user.clear(screen.getByLabelText(/destination/i));
    await user.type(screen.getByLabelText(/destination/i), '+99912345678');
    await user.click(screen.getByRole('button', { name: /rate/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /no tariff for destination/i,
    );
  });

  it('disables the submit button while loading', async () => {
    server.use(
      http.post('/api/rate', async () => {
        await new Promise((r) => setTimeout(r, 50));
        return HttpResponse.json({
          cost_millicents: 100,
          tariff_prefix: '33',
        });
      }),
    );
    const user = userEvent.setup();
    render(<RateCalculator />);

    await user.click(screen.getByRole('button', { name: /rate/i }));

    // Mid-flight: button is disabled and labelled "Rating…"
    expect(screen.getByRole('button')).toBeDisabled();
    expect(screen.getByRole('button')).toHaveTextContent(/rating/i);

    // Resolution: status appears, button re-enabled.
    expect(await screen.findByRole('status')).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeEnabled();
  });
});
