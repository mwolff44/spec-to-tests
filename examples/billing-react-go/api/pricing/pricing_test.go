package pricing_test

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"pgregory.net/rapid"

	"billing/pricing"
)

// --- table-driven unit tests ------------------------------------------------

func TestRateCall_examples(t *testing.T) {
	t.Parallel()
	tariff := pricing.Tariff{Prefix: "33", RatePerMinute: 2000}
	cases := []struct {
		name     string
		duration int
		want     int
	}{
		{"zero seconds is free", 0, 0},
		{"negative seconds is free", -1, 0},
		{"one second bills one minute", 1, 2000},
		{"sixty seconds bills one minute", 60, 2000},
		{"sixty-one seconds bills two minutes", 61, 4000},
		{"two minutes exact", 120, 4000},
	}
	for _, tc := range cases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()
			got := pricing.RateCall(tariff, tc.duration)
			assert.Equal(t, tc.want, got)
		})
	}
}

func TestLongestPrefixMatch_examples(t *testing.T) {
	t.Parallel()
	tariffs := []pricing.Tariff{
		{Prefix: "33", RatePerMinute: 2000},
		{Prefix: "336", RatePerMinute: 1500},  // more specific
		{Prefix: "1", RatePerMinute: 5000},
	}
	t.Run("longest matches", func(t *testing.T) {
		t.Parallel()
		got, ok := pricing.LongestPrefixMatch(tariffs, "33612345678")
		assert.True(t, ok)
		assert.Equal(t, "336", got.Prefix)
	})
	t.Run("falls back to shorter", func(t *testing.T) {
		t.Parallel()
		got, ok := pricing.LongestPrefixMatch(tariffs, "33712345678")
		assert.True(t, ok)
		assert.Equal(t, "33", got.Prefix)
	})
	t.Run("no match", func(t *testing.T) {
		t.Parallel()
		_, ok := pricing.LongestPrefixMatch(tariffs, "44612345678")
		assert.False(t, ok)
	})
}

// --- property-based tests with rapid ----------------------------------------

func TestRateCall_alwaysNonNegative(t *testing.T) {
	rapid.Check(t, func(t *rapid.T) {
		tariff := pricing.Tariff{
			Prefix:        "X",
			RatePerMinute: rapid.IntRange(0, 100000).Draw(t, "rate"),
		}
		duration := rapid.IntRange(-1000, 100000).Draw(t, "duration")
		got := pricing.RateCall(tariff, duration)
		if got < 0 {
			t.Fatalf("cost was negative: %d", got)
		}
	})
}

func TestRateCall_monotonicInDuration(t *testing.T) {
	// Property: cost is non-decreasing in duration.
	// This surfaces the "60s same as 1s due to ceiling" — which is INTENDED
	// (per-minute billing). The property still holds: cost(a) <= cost(b) when a <= b.
	rapid.Check(t, func(t *rapid.T) {
		tariff := pricing.Tariff{
			Prefix:        "X",
			RatePerMinute: rapid.IntRange(1, 100000).Draw(t, "rate"),
		}
		a := rapid.IntRange(0, 10000).Draw(t, "a")
		b := rapid.IntRange(0, 10000).Draw(t, "b")
		if a > b {
			a, b = b, a
		}
		ca := pricing.RateCall(tariff, a)
		cb := pricing.RateCall(tariff, b)
		if ca > cb {
			t.Fatalf("non-monotonic: cost(%d)=%d > cost(%d)=%d", a, ca, b, cb)
		}
	})
}

func TestLongestPrefixMatch_addingMoreSpecificNeverIncreasesCost(t *testing.T) {
	// Metamorphic: adding a more-specific prefix with a *lower* rate must
	// reduce or keep the cost for a number under that prefix.
	rapid.Check(t, func(t *rapid.T) {
		basePrefix := rapid.StringMatching(`[0-9]{1,3}`).Draw(t, "basePrefix")
		extension := rapid.StringMatching(`[0-9]{1,3}`).Draw(t, "extension")
		baseRate := rapid.IntRange(100, 10000).Draw(t, "baseRate")
		moreSpecificRate := rapid.IntRange(1, baseRate).Draw(t, "moreSpecificRate")
		callTail := rapid.StringMatching(`[0-9]{4,8}`).Draw(t, "callTail")

		number := basePrefix + extension + callTail
		duration := rapid.IntRange(1, 600).Draw(t, "duration")

		tariffsBase := []pricing.Tariff{{Prefix: basePrefix, RatePerMinute: baseRate}}
		baseMatch, _ := pricing.LongestPrefixMatch(tariffsBase, number)
		costBase := pricing.RateCall(baseMatch, duration)

		tariffsRefined := append(tariffsBase,
			pricing.Tariff{Prefix: basePrefix + extension, RatePerMinute: moreSpecificRate})
		refinedMatch, _ := pricing.LongestPrefixMatch(tariffsRefined, number)
		costRefined := pricing.RateCall(refinedMatch, duration)

		if costRefined > costBase {
			t.Fatalf("more specific cheaper prefix made cost go up: %d -> %d",
				costBase, costRefined)
		}
	})
}
