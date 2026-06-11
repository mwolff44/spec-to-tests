// Package handlers — Gin HTTP handlers. Thin layer: bind → call domain → respond.
package handlers

import (
	"net/http"
	"regexp"

	"github.com/gin-gonic/gin"

	"billing/pricing"
)

// TariffLookup is the contract the handler needs. Implemented by repository.TariffRepo
// in prod, by fakes in tests. Keeps the handler free of GORM/DB knowledge.
type TariffLookup interface {
	LookupByPrefix(number string) (pricing.Tariff, bool, error)
}

// RateRequest is the JSON body for POST /api/rate.
type RateRequest struct {
	DurationSeconds int    `json:"duration_seconds" binding:"required,min=0"`
	Destination     string `json:"destination"      binding:"required"`
}

// RateResponse is the JSON returned by POST /api/rate. Cost is in millicents.
type RateResponse struct {
	CostMillicents int    `json:"cost_millicents"`
	TariffPrefix   string `json:"tariff_prefix"`
}

// e164Re — minimal E.164 validation: + followed by 8..15 digits.
var e164Re = regexp.MustCompile(`^\+[0-9]{8,15}$`)

// PostRate is the handler factory. It captures the TariffLookup and returns the gin.HandlerFunc.
func PostRate(lookup TariffLookup) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req RateRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid body: " + err.Error()})
			return
		}
		if !e164Re.MatchString(req.Destination) {
			c.JSON(http.StatusBadRequest, gin.H{"error": "destination must be E.164 (+digits)"})
			return
		}

		// Drop the leading + before prefix matching.
		number := req.Destination[1:]
		tariff, ok, err := lookup.LookupByPrefix(number)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": "lookup failed"})
			return
		}
		if !ok {
			c.JSON(http.StatusNotFound, gin.H{"error": "no tariff for destination"})
			return
		}

		cost := pricing.RateCall(tariff, req.DurationSeconds)
		c.JSON(http.StatusOK, RateResponse{
			CostMillicents: cost,
			TariffPrefix:   tariff.Prefix,
		})
	}
}

// Register mounts the handlers on the engine.
func Register(r *gin.Engine, lookup TariffLookup) {
	api := r.Group("/api")
	api.POST("/rate", PostRate(lookup))
}
