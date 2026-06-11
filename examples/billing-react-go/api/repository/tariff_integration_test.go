//go:build integration

package repository_test

import (
	"context"
	"path/filepath"
	"runtime"
	"testing"
	"time"

	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/postgres"
	_ "github.com/golang-migrate/migrate/v4/source/file"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	tcpostgres "github.com/testcontainers/testcontainers-go/modules/postgres"
	tcwait "github.com/testcontainers/testcontainers-go/wait"
	gpostgres "gorm.io/driver/postgres"
	"gorm.io/gorm"

	"billing/repository"
)

func setupDB(t *testing.T) (*gorm.DB, func()) {
	t.Helper()
	ctx := context.Background()

	pg, err := tcpostgres.Run(ctx,
		"postgres:16-alpine",
		tcpostgres.WithDatabase("billing"),
		tcpostgres.WithUsername("test"),
		tcpostgres.WithPassword("test"),
		tcpostgres.BasicWaitStrategies(),
		tcpostgres.WithSQLDriver("postgres"),
		tcpostgres.WithLogger(nil),
		tcpostgres.WithInitScripts(),
		tcpostgres.WithStartupTimeout(60*time.Second),
		tcwait.ForLog("database system is ready to accept connections").WithOccurrence(2),
	)
	require.NoError(t, err)

	dsn, err := pg.ConnectionString(ctx, "sslmode=disable")
	require.NoError(t, err)

	_, thisFile, _, _ := runtime.Caller(0)
	migrationsDir := filepath.Join(filepath.Dir(thisFile), "..", "migrations")

	m, err := migrate.New("file://"+migrationsDir, dsn)
	require.NoError(t, err)
	require.NoError(t, m.Up())

	db, err := gorm.Open(gpostgres.Open(dsn), &gorm.Config{})
	require.NoError(t, err)

	return db, func() {
		sqlDB, _ := db.DB()
		_ = sqlDB.Close()
		_ = pg.Terminate(ctx)
	}
}

func TestTariffRepo_CreateAndLookup(t *testing.T) {
	db, cleanup := setupDB(t)
	defer cleanup()

	repo := repository.NewTariffRepo(db)

	_, err := repo.Create(repository.Tariff{Prefix: "33", RatePerMinute: 2000})
	require.NoError(t, err)
	_, err = repo.Create(repository.Tariff{Prefix: "336", RatePerMinute: 1500})
	require.NoError(t, err)

	t.Run("longest prefix wins", func(t *testing.T) {
		got, ok, err := repo.LookupByPrefix("33612345678")
		require.NoError(t, err)
		require.True(t, ok)
		assert.Equal(t, "336", got.Prefix)
		assert.Equal(t, 1500, got.RatePerMinute)
	})

	t.Run("falls back to shorter prefix", func(t *testing.T) {
		got, ok, err := repo.LookupByPrefix("33712345678")
		require.NoError(t, err)
		require.True(t, ok)
		assert.Equal(t, "33", got.Prefix)
	})

	t.Run("no match returns ok=false", func(t *testing.T) {
		_, ok, err := repo.LookupByPrefix("44712345678")
		require.NoError(t, err)
		assert.False(t, ok)
	})
}

func TestTariffRepo_DuplicatePrefixViolatesUnique(t *testing.T) {
	db, cleanup := setupDB(t)
	defer cleanup()

	repo := repository.NewTariffRepo(db)

	_, err := repo.Create(repository.Tariff{Prefix: "44", RatePerMinute: 3000})
	require.NoError(t, err)

	_, err = repo.Create(repository.Tariff{Prefix: "44", RatePerMinute: 4000})
	require.Error(t, err)
	assert.True(t, repository.IsUniqueViolation(err),
		"expected unique violation, got %v", err)
}
