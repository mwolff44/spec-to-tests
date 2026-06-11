package handlers_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"billing/handlers"
	"billing/pricing"
)

// fakeLookup is an in-memory TariffLookup. No mocking framework — just an impl.
// This is the recommended pattern (see tdd-skill/agent-discipline.md §4).
type fakeLookup struct {
	tariffs []pricing.Tariff
}

func (f *fakeLookup) LookupByPrefix(number string) (pricing.Tariff, bool, error) {
	t, ok := pricing.LongestPrefixMatch(f.tariffs, number)
	return t, ok, nil
}

func setupRouter(t *testing.T, l handlers.TariffLookup) *gin.Engine {
	t.Helper()
	gin.SetMode(gin.TestMode)
	r := gin.New()
	handlers.Register(r, l)
	return r
}

func doPost(t *testing.T, r *gin.Engine, body any) *httptest.ResponseRecorder {
	t.Helper()
	b, err := json.Marshal(body)
	require.NoError(t, err)
	req := httptest.NewRequest(http.MethodPost, "/api/rate", bytes.NewReader(b))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)
	return rec
}

func TestPostRate_validRequest_returns200WithCost(t *testing.T) {
	t.Parallel()
	r := setupRouter(t, &fakeLookup{tariffs: []pricing.Tariff{
		{Prefix: "33", RatePerMinute: 2000},
		{Prefix: "336", RatePerMinute: 1500},
	}})

	rec := doPost(t, r, handlers.RateRequest{
		DurationSeconds: 120,
		Destination:     "+33612345678",
	})

	require.Equal(t, http.StatusOK, rec.Code)
	var got handlers.RateResponse
	require.NoError(t, json.NewDecoder(rec.Body).Decode(&got))
	assert.Equal(t, "336", got.TariffPrefix)
	assert.Equal(t, 3000, got.CostMillicents) // 2 minutes * 1500
}

func TestPostRate_invalidDestination_returns400(t *testing.T) {
	t.Parallel()
	r := setupRouter(t, &fakeLookup{})

	rec := doPost(t, r, handlers.RateRequest{
		DurationSeconds: 60,
		Destination:     "not-a-phone",
	})

	assert.Equal(t, http.StatusBadRequest, rec.Code)
}

func TestPostRate_missingDestination_returns400(t *testing.T) {
	t.Parallel()
	r := setupRouter(t, &fakeLookup{})

	rec := doPost(t, r, map[string]any{"duration_seconds": 60})

	assert.Equal(t, http.StatusBadRequest, rec.Code)
}

func TestPostRate_noMatchingTariff_returns404(t *testing.T) {
	t.Parallel()
	r := setupRouter(t, &fakeLookup{tariffs: []pricing.Tariff{
		{Prefix: "33", RatePerMinute: 2000},
	}})

	rec := doPost(t, r, handlers.RateRequest{
		DurationSeconds: 60,
		Destination:     "+44612345678",
	})

	assert.Equal(t, http.StatusNotFound, rec.Code)
}
