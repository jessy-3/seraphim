package config

import (
	"fmt"
	"os"
)

type Config struct {
	Redis struct {
		Host     string
		Port     string
		Password string
	}
	Postgres struct {
		Host     string
		Port     string
		User     string
		Password string
		DbName   string
	}
}

// getEnvWithDefault returns the value of the environment variable if set,
// otherwise it returns the provided default value.
func getEnvWithDefault(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}

func Load(cfg *Config) error {
	cfg.Redis.Host = getEnvWithDefault("REDIS_HOST", "127.0.0.1")
	cfg.Redis.Port = getEnvWithDefault("REDIS_PORT", "6379")
	// cfg.Redis.Password = getEnvWithDefault("REDIS_PASSWORD", "")

	cfg.Postgres.Host = getEnvWithDefault("PG_HOST", "localhost")
	cfg.Postgres.Port = getEnvWithDefault("PG_PORT", "5432")
	cfg.Postgres.User = getEnvWithDefault("PG_USER", "postgres")
	cfg.Postgres.Password = getEnvWithDefault("PG_PASSWORD", "2022pass")
	cfg.Postgres.DbName = getEnvWithDefault("PG_DATABASE", "vanilla")

	return nil
}

func (c *Config) PostgresConnectionString() string {
	return fmt.Sprintf("postgres://%s:%s@%s:%s/%s?sslmode=disable",
		c.Postgres.User,
		c.Postgres.Password,
		c.Postgres.Host,
		c.Postgres.Port,
		c.Postgres.DbName,
	)
}
