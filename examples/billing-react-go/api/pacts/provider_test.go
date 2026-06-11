//go:build pact

// Package pacts — provider-side verification of the Pact contract.
// Spins up the API, configures DB states, replays the consumer pact.
package pacts_test

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/pact-foundation/pact-go/v2/models"
	"github.com/pact-foundation/pact-go/v2/provider"
	"github.com/stretchr/testify/require"

	"billing/handlers"
	"billing/pricing"
)

const providerPort = 8181

// stateLookup is a TariffLookup whose contents can be reset between Pact states.
type stateLookup struct {
	tariffs []pricing.Tariff
}

func (s *stateLookup) LookupByPrefix(number string) (pricing.Tariff, bool, error) {
	t, ok := pricing.LongestPrefixMatch(s.tariffs, number)
	return t, ok, nil
}

func startProvider(t *testing.T, lookup *stateLookup) {
	t.Helper()
	gin.SetMode(gin.TestMode)
	r := gin.New()
	handlers.Register(r, lookup)

	srv := &http.Server{
		Addr:    fmt.Sprintf(":%d", providerPort),
		Handler: r,
	}
	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Printf("provider stopped: %v", err)
		}
	}()
	// Naive wait — in CI use a /healthz poll.
	time.Sleep(300 * time.Millisecond)
	t.Cleanup(func() { _ = srv.Close() })
}

func TestProvider_satisfiesReactFrontendPact(t *testing.T) {
	pactFile := os.Getenv("PACT_FILE")
	if pactFile == "" {
		pactFile = "../../pacts/react-frontend-go-api.json"
	}
	if _, err := os.Stat(pactFile); err != nil {
		t.Skipf("pact file not found at %s — run the consumer test first", pactFile)
	}

	lookup := &stateLookup{}
	startProvider(t, lookup)

	verifier := provider.NewVerifier()
	err := verifier.VerifyProvider(t, provider.VerifyRequest{
		ProviderBaseURL: fmt.Sprintf("http://localhost:%d", providerPort),
		Provider:        "go-api",
		PactFiles:       []string{pactFile},
		StateHandlers: models.StateHandlers{
			"a tariff for prefix 336 exists at rate 1500": func(setup bool, _ models.ProviderState) (models.ProviderStateResponse, error) {
				if setup {
					lookup.tariffs = []pricing.Tariff{
						{Prefix: "33", RatePerMinute: 2000},
						{Prefix: "336", RatePerMinute: 1500},
					}
				} else {
					lookup.tariffs = nil
				}
				return nil, nil
			},
			"no tariff exists for prefix 999": func(setup bool, _ models.ProviderState) (models.ProviderStateResponse, error) {
				lookup.tariffs = nil
				return nil, nil
			},
		},
	})
	require.NoError(t, err)
}
