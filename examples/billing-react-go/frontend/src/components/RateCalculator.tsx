import { useState } from 'react';
import { formatCost, rateCall, RateError } from '../api/billing';

type State =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ok'; cost: number; prefix: string }
  | { status: 'error'; message: string };

export function RateCalculator() {
  const [duration, setDuration] = useState('60');
  const [destination, setDestination] = useState('+33612345678');
  const [state, setState] = useState<State>({ status: 'idle' });

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setState({ status: 'loading' });
    try {
      const result = await rateCall({
        duration_seconds: Number(duration),
        destination,
      });
      setState({
        status: 'ok',
        cost: result.cost_millicents,
        prefix: result.tariff_prefix,
      });
    } catch (err) {
      const message =
        err instanceof RateError ? err.message : 'unexpected error';
      setState({ status: 'error', message });
    }
  }

  return (
    <main>
      <h1>Rate a call</h1>
      <form onSubmit={onSubmit} aria-label="rate-form">
        <label>
          Duration (seconds)
          <input
            type="number"
            min="0"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            required
          />
        </label>
        <label>
          Destination (E.164)
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            required
          />
        </label>
        <button type="submit" disabled={state.status === 'loading'}>
          {state.status === 'loading' ? 'Rating…' : 'Rate'}
        </button>
      </form>

      {state.status === 'ok' && (
        <p role="status">
          Cost: <strong>{formatCost(state.cost)}</strong> (prefix{' '}
          {state.prefix})
        </p>
      )}
      {state.status === 'error' && (
        <p role="alert">Error: {state.message}</p>
      )}
    </main>
  );
}
