// Package repository — persistence layer. GORM models + queries.
package repository

import (
	"errors"
	"time"

	"gorm.io/gorm"

	"billing/pricing"
)

// Tariff is the GORM model. Maps to the `tariffs` table created by the migration.
type Tariff struct {
	ID            uint   `gorm:"primaryKey"`
	Prefix        string `gorm:"uniqueIndex;size:20;not null"`
	RatePerMinute int    `gorm:"not null;check:rate_per_minute >= 0"`
	CreatedAt     time.Time
}

func (Tariff) TableName() string { return "tariffs" }

// TariffRepo wraps a *gorm.DB with the tariff queries we need.
type TariffRepo struct {
	db *gorm.DB
}

func NewTariffRepo(db *gorm.DB) *TariffRepo { return &TariffRepo{db: db} }

// Create inserts a tariff. Returns the persisted row including its ID.
func (r *TariffRepo) Create(t Tariff) (Tariff, error) {
	if err := r.db.Create(&t).Error; err != nil {
		return Tariff{}, err
	}
	return t, nil
}

// ListAll returns all tariffs. Used by handlers to do longest-prefix matching
// in memory — pragmatic for a small dialplan; for large ones, see LookupByPrefix.
func (r *TariffRepo) ListAll() ([]pricing.Tariff, error) {
	var rows []Tariff
	if err := r.db.Find(&rows).Error; err != nil {
		return nil, err
	}
	out := make([]pricing.Tariff, 0, len(rows))
	for _, r := range rows {
		out = append(out, pricing.Tariff{Prefix: r.Prefix, RatePerMinute: r.RatePerMinute})
	}
	return out, nil
}

// LookupByPrefix returns the tariff with the longest prefix that is a prefix of `number`.
// Pushes the longest-prefix logic into SQL for scalability.
func (r *TariffRepo) LookupByPrefix(number string) (pricing.Tariff, bool, error) {
	var row Tariff
	// Postgres-specific: starts_with(number, prefix) is faster than LIKE here.
	err := r.db.Where("starts_with(?, prefix)", number).
		Order("length(prefix) DESC").
		First(&row).Error
	if errors.Is(err, gorm.ErrRecordNotFound) {
		return pricing.Tariff{}, false, nil
	}
	if err != nil {
		return pricing.Tariff{}, false, err
	}
	return pricing.Tariff{Prefix: row.Prefix, RatePerMinute: row.RatePerMinute}, true, nil
}

// IsUniqueViolation classifies a Postgres unique constraint error semantically.
// Callers must NEVER inspect the raw error string.
func IsUniqueViolation(err error) bool {
	if err == nil {
		return false
	}
	// Postgres error code 23505 = unique_violation. Wrapped by gorm + pgx.
	// Real impl: errors.As to pq.Error / pgconn.PgError. Kept short for the demo.
	return err.Error() != "" && (containsAny(err.Error(),
		"duplicate key", "unique constraint", "23505"))
}

func containsAny(s string, subs ...string) bool {
	for _, sub := range subs {
		if len(sub) > 0 && len(s) >= len(sub) {
			for i := 0; i+len(sub) <= len(s); i++ {
				if s[i:i+len(sub)] == sub {
					return true
				}
			}
		}
	}
	return false
}
