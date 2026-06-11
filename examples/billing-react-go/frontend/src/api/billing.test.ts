// PBT for the pure formatter. The fetch wrapper is tested via the component
// integration (with MSW) — covering it via PBT here would mean re-mocking.
import { describe, expect, it } from 'vitest';
import * as fc from 'fast-check';

import { formatCost } from './billing';

describe('formatCost (PBT)', () => {
  it('produces a string ending in " €"', () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 100_000_000 }), (m) => {
        expect(formatCost(m)).toMatch(/ €$/);
      }),
    );
  });

  it('is monotonic non-decreasing in millicents', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 50_000_000 }),
        fc.integer({ min: 0, max: 50_000_000 }),
        (a, b) => {
          const [lo, hi] = a <= b ? [a, b] : [b, a];
          // Compare numerically (parse back from the formatted string).
          const valLo = Number(formatCost(lo).replace(' €', ''));
          const valHi = Number(formatCost(hi).replace(' €', ''));
          expect(valLo).toBeLessThanOrEqual(valHi);
        },
      ),
    );
  });

  it('formats zero as "0.00 €"', () => {
    expect(formatCost(0)).toBe('0.00 €');
  });
});
