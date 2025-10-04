package services

import (
	// "github.com/go-redis/redis/v8"
	"github.com/jessy-3/vanilla/gobackend/repositories"
)

type DataService struct {
	// redisClient    *redis.Client
	redisClient    RedisClientInterface
	ohlcRepo       *repositories.OHLCRepository
	indicatorRepo  *repositories.IndicatorRepository
	symbolInfoRepo *repositories.SymbolInfoRepository
}

func NewDataService(redisClient RedisClientInterface, ohlcRepo *repositories.OHLCRepository, indicatorRepo *repositories.IndicatorRepository, symbolInfoRepo *repositories.SymbolInfoRepository) *DataService {
	return &DataService{
		redisClient:    redisClient,
		ohlcRepo:       ohlcRepo,
		indicatorRepo:  indicatorRepo,
		symbolInfoRepo: symbolInfoRepo,
	}
}

// Other methods for the DataService that depend on the repositories
