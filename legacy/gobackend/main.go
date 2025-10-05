package main

import (
	// "context"
	// "errors"
	"fmt"
	"github.com/go-redis/redis/v8"
	"github.com/jessy-3/vanilla/gobackend/config" // Update this import
	"github.com/jessy-3/vanilla/gobackend/messaging"
	"github.com/jessy-3/vanilla/gobackend/repositories"
	"github.com/jessy-3/vanilla/gobackend/services"
	"github.com/jmoiron/sqlx"
	_ "github.com/lib/pq" // Add this import for PostgreSQL support
)

func main() {
	// Load configuration values from environment variables
	cfg := &config.Config{}
	err := config.Load(cfg) // Change this line
	if err != nil {
		panic(fmt.Errorf("failed to load config: %w", err))
	}

	// Initialize Redis client
	client := redis.NewClient(&redis.Options{
		Addr: fmt.Sprintf("%s:%s", cfg.Redis.Host, cfg.Redis.Port),
		// Password: cfg.Redis.Password,
		DB: 0,
	})
	defer client.Close()
	// Create a RedisClient struct instance
	myClient := messaging.NewRedisClient(client)

	// Initialize database connection
	db, err := sqlx.Connect("postgres", cfg.PostgresConnectionString()) // Update this line
	if err != nil {
		panic(fmt.Errorf("failed to initialize database: %w", err))
	}
	// defer db.Close()

	// Initialize repositories with the database connection
	ohlcRepository, err := repositories.NewOHLCRepository(*cfg) // Update this line
	if err != nil {
		panic(fmt.Errorf("failed to initialize OHLCRepository: %w", err))
	}
	// ohlcRepository := repositories.NewOHLCRepository(db)
	indicatorRepository := repositories.NewIndicatorRepository(db)
	symbolInfoRepository := repositories.NewSymbolInfoRepository(db)

	ds := services.NewDataService(myClient, ohlcRepository, indicatorRepository, symbolInfoRepository)

	// services.DoTesting(ds)
	// Use the repositories as needed
	fmt.Println("Go listener starting ...")
	messaging.ListenRedis(ds, client)
}
