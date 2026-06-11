// Typed API client. Single function — easy to mock at boundary.
export interface RateRequest {
  duration_seconds: number;
  destination: string;
}

export interface RateResponse {
  cost_millicents: number;
  tariff_prefix: string;
}

export class RateError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'RateError';
  }
}

export async function rateCall(
  req: RateRequest,
  baseUrl: string = '',
): Promise<RateResponse> {
  const res = await fetch(`${baseUrl}/api/rate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { error?: string };
    throw new RateError(res.status, body.error ?? `HTTP ${res.status}`);
  }
  return (await res.json()) as RateResponse;
}

// Display helper — millicents → € string. Pure, easy to PBT.
export function formatCost(millicents: number): string {
  const euros = millicents / 100_000;
  return `${euros.toFixed(2)} €`;
}
