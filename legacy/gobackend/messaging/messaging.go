package messaging

import (
	"context"
	// "errors"
	"fmt"

	"github.com/go-redis/redis/v8"
	"github.com/jessy-3/vanilla/gobackend/services"

	// "log"
	// "os"
	// "strconv"
	"strings"
	// "time"
)

type RedisClient struct {
	client *redis.Client
}

func NewRedisClient(client *redis.Client) *RedisClient {
	return &RedisClient{
		client: client,
	}
}

func (r *RedisClient) HMSet(key string, values map[string]interface{}) error {
	ctx := context.Background()
	return r.client.HMSet(ctx, key, values).Err()
}

func (r *RedisClient) HGetAll(key string) (map[string]string, error) {
	ctx := context.Background()
	result, err := r.client.HGetAll(ctx, key).Result()
	if err != nil {
		return nil, err
	}
	return result, nil
}

func (r *RedisClient) PSubscribe(ctx context.Context, pattern string) *redis.PubSub {
	return r.client.PSubscribe(ctx, pattern)
}

func (r *RedisClient) SendMessage(channel, message string) error {
	ctx := context.Background()
	return r.client.Publish(ctx, channel, message).Err()
}

var _ services.RedisClientInterface = &RedisClient{}

// func SendRedis(client *redis.Client, channelName string, message string) error {
// 	ctx := context.Background()

// 	// Publish a message to the Redis channel
// 	pubResult := client.Publish(ctx, channelName, message)

// 	// Check for errors in publishing the message
// 	if err := pubResult.Err(); err != nil {
// 		return err
// 	}

// 	return nil
// }

func ListenRedis(ds *services.DataService, client *redis.Client) {
	// Subscribe to the Redis channel
	ctx := context.Background()
	pubsub := client.Subscribe(ctx, "go_commands")

	// Wait for the subscription to be ready
	_, err := pubsub.Receive(ctx)
	if err != nil {
		panic(err)
	}

	// Create a channel to receive messages
	channel := pubsub.Channel()

	// Process messages from the channel
	for msg := range channel {
		fmt.Println("Go command received: " + msg.Payload)
		splittedPayload := strings.SplitN(msg.Payload, " | ", 2)
		command := strings.ToLower(splittedPayload[0])
		var payload string
		if len(splittedPayload) > 1 {
			payload = splittedPayload[1]
		}
		switch command {
		case "initbtc1w":
			ds.InitialIndicators("BTC/USD", 604800, 1, 0)
		case "initbtc1d":
			ds.InitialIndicators("BTC/USD", 86400, 1, 0)
		case "initbtc4h":
			ds.InitialIndicators("BTC/USD", 14400, 1, 0)
		case "initbtc1h":
			ds.InitialIndicators("BTC/USD", 3600, 1, 0)
		case "updbtc1w":
			ds.UpdateIndicators("BTC/USD", 604800, 1)
		case "updbtc1d":
			ds.UpdateIndicators("BTC/USD", 86400, 1)
		case "updbtc4h":
			ds.UpdateIndicators("BTC/USD", 14400, 1)
		case "updbtc1h":
			ds.UpdateIndicators("BTC/USD", 3600, 1)
		case "delbtc1w":
			ds.DeleteIndicators("BTC/USD", 604800)
		case "delbtc1d":
			ds.DeleteIndicators("BTC/USD", 86400)
		case "delbtc4h":
			ds.DeleteIndicators("BTC/USD", 14400)
		case "delbtc1h":
			ds.DeleteIndicators("BTC/USD", 3600)
		case "upd_all_indicators":
			ds.UpdateAllIndicators(1)
			// Publish the received message to the "bot_commands" channel with "crons" subscription
			err = client.Publish(ctx, "bot_commands", "crons | "+payload).Err()
			if err != nil {
				fmt.Println("Error publishing message to bot_commands:", err)
			} else {
				fmt.Println("Message published to bot_commands:", "crons | "+payload)
			}
		case "echo_web_commands":
			// Publish the received message to the "web_commands" channel
			err := client.Publish(ctx, "web_commands", "Go received | "+payload).Err()
			if err != nil {
				fmt.Println("Error publishing message to web_commands:", err)
			} else {
				fmt.Println("Message published to web_commands:", "Go received | "+payload)
			}
		case "echo_bot_commands":
			// Publish the received message to the "bot_commands" channel
			err := client.Publish(ctx, "bot_commands", "Go received | "+msg.Payload).Err()
			if err != nil {
				fmt.Println("Error publishing message to bot_commands:", err)
			} else {
				fmt.Println("Message published to bot_commands:", "Go received | "+msg.Payload)
			}
		default:
			fmt.Println("Unknown command:", msg.Payload)
		}
	}
}
