package services

import (
	"context"

	"github.com/go-redis/redis/v8"
)

type RedisClientInterface interface {
	SendMessage(channel, message string) error
	HMSet(key string, values map[string]interface{}) error
	HGetAll(key string) (map[string]string, error)
	PSubscribe(ctx context.Context, pattern string) *redis.PubSub
}
