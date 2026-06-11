// billing — entry point. Wires DB → repository → handler → router.
package main

import (
	"log"
	"os"

	"github.com/gin-gonic/gin"
	gpostgres "gorm.io/driver/postgres"
	"gorm.io/gorm"

	"billing/handlers"
	"billing/repository"
)

func main() {
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		log.Fatal("DATABASE_URL is required")
	}

	db, err := gorm.Open(gpostgres.Open(dsn), &gorm.Config{})
	if err != nil {
		log.Fatalf("db open: %v", err)
	}

	repo := repository.NewTariffRepo(db)

	r := gin.Default()
	r.GET("/healthz", func(c *gin.Context) { c.String(200, "ok") })
	handlers.Register(r, repo)

	if err := r.Run(":8080"); err != nil {
		log.Fatalf("server: %v", err)
	}
}
