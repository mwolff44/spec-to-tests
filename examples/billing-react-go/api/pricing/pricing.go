// Package pricing — pure rating logic. No I/O, fully unit-testable.
package pricing

import "math"

// Tariff is the data required to rate a call. RatePerMinute is in millicents
// (i.e. 0.020 €/min → 2000) to avoid floating-point drift in money math.
type Tariff struct {
	Prefix        string
	RatePerMinute int
}

// RateCall computes the cost of a call of `durationSeconds` to `destination`
// using `tariff`. Cost is in millicents.
//
// Convention: any partially-used minute is billed in full (ceiling).
//
// Returns 0 if duration is non-positive.
func RateCall(tariff Tariff, durationSeconds int) int {
	// BUG: the `<= 0` branch returns 0, but a zero-second call should arguably
	// return 0 *only* when the tariff has no setup fee. A PBT property
	// ("two calls cost at least as much as one") can hide this — but a more
	// specific property ("cost is monotonic non-decreasing in duration")
	// surfaces a related issue: 60s costs the same as 1s due to ceiling.
	// This is a deliberate teaching example, not a real billing bug.
	if durationSeconds <= 0 {
		return 0
	}
	minutes := int(math.Ceil(float64(durationSeconds) / 60.0))
	return minutes * tariff.RatePerMinute
}

// LongestPrefixMatch returns the tariff whose Prefix is the longest one that
// is a prefix of `number`. Returns (Tariff{}, false) if no match.
func LongestPrefixMatch(tariffs []Tariff, number string) (Tariff, bool) {
	var best Tariff
	found := false
	for _, t := range tariffs {
		if len(t.Prefix) <= len(number) && number[:len(t.Prefix)] == t.Prefix {
			if !found || len(t.Prefix) > len(best.Prefix) {
				best = t
				found = true
			}
		}
	}
	return best, found
}
