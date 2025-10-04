package services

import (
	// "encoding/csv"

	"context"
	"fmt"
	"strconv"

	"github.com/jessy-3/vanilla/gobackend/indicators"
	"github.com/jessy-3/vanilla/gobackend/models"

	// "github.com/markcheno/go-talib"

	"log"
	"math"

	// "os"
	// "strconv"
	"strings"
	"time"
)

// func ExtractColumnAsFloat64(data [][]interface{}, columnIndex int) []float64 {
// 	result := make([]float64, len(data)-1)

// 	for i := 1; i < len(data); i++ {
// 		if value, ok := data[i][columnIndex].(float64); ok {
// 			result[i-1] = value
// 		} else {
// 			log.Fatal("Non-float value in the expected float column")
// 		}
// 	}
// 	return result
// }

// func readCSV(filename string) ([][]interface{}, error) {
// 	file, err := os.Open(filename)
// 	if err != nil {
// 		return nil, err
// 	}
// 	defer file.Close()

// 	reader := csv.NewReader(file)
// 	reader.Comma = ','

// 	rows, err := reader.ReadAll()
// 	if err != nil {
// 		return nil, err
// 	}

// 	data := make([][]interface{}, len(rows))
// 	for i, row := range rows {
// 		data[i] = make([]interface{}, len(row))
// 		for j, value := range row {
// 			if floatValue, err := strconv.ParseFloat(strings.Replace(value, ",", "", -1), 64); err == nil {
// 				data[i][j] = floatValue
// 			} else {
// 				data[i][j] = value
// 			}
// 		}
// 	}

// 	return data, nil
// }

func (ds *DataService) InitialIndicators(symbol string, interval int, market_id int, limit int) {

	var ohlcData []models.OHLCPrice
	var err error
	_, err = ds.indicatorRepo.GetLatestIndicator(symbol, interval)
	if err == nil {
		fmt.Printf("Initial Indicators STOPPED. Found indicators for: %v (%v)\n", symbol, interval)
		return
	}

	if limit == 0 {
		ohlcData, err = ds.ohlcRepo.GetOHLC(symbol, interval, market_id, true)
	} else { // limit non-zero for testing with recent limit number of ohlc
		ohlcData, err = ds.ohlcRepo.GetLatestOHLCbyNumber(symbol, interval, market_id, true, limit)
	}
	if err != nil {
		fmt.Println("Error fetching OHLC data:", err)
	}
	indicators, err := indicators.CalculateIndicators(ohlcData)
	for _, indicator := range indicators {
		err := ds.indicatorRepo.InsertIndicator(&indicator)
		if err != nil {
			log.Printf("Error inserting indicator: %v\n", err)
		}
	}
}
func formatFloatOrNil(f *float64) string {
	if f == nil {
		return ""
	}
	return strconv.FormatFloat(*f, 'f', -1, 64)
}
func (ds *DataService) RedisTrigger() {

	var ctx = context.Background()

	// Subscribe to keyspace notifications
	pubsub := ds.redisClient.PSubscribe(ctx, "__keyspace@0__:BTC/USD")

	// Process notifications
	for {
		msg, err := pubsub.ReceiveMessage(ctx)
		if err != nil {
			fmt.Println("Error receiving message:", err)
			continue
		}

		if msg.Channel == "__keyspace@0__:BTC/USD" {
			switch msg.Payload {
			case "hset", "hmset", "hdel", "del":
				// Key has been modified, get the latest data
				data, err := ds.redisClient.HGetAll("BTC/USD_Price")
				if err != nil {
					fmt.Println("Error getting data:", err)
					continue
				}

				// Convert keys and values from []byte to string
				stringData := make(map[string]string)
				for key, value := range data {
					stringData[key] = value
				}

				// Print the data
				fmt.Println("BTC/USD_Price Triggered:", stringData)
			}
		}
	}
}
func (ds *DataService) UpdateIndicators(symbol string, interval int, market_id int) {
	ohlc, err := ds.ohlcRepo.GetLatestOHLC(symbol, interval, market_id)
	if err != nil {
		fmt.Println("Update Indicators STOPPED. Error fetching latest OHLC data:", err)
		return
	}

	indicator, err := ds.indicatorRepo.GetLatestIndicator(symbol, interval)
	if err != nil {
		fmt.Println("Update Indicators STOPPED. Error fetching latest Indicator data:", err)
		return
	}

	limitForMACD := 260 // retrieve last 260 ohlc to calculate MACD
	var limit int = int(math.Abs(float64(ohlc.Unix-indicator.Unix))/float64(interval)) + limitForMACD
	latestOhlc, err := ds.ohlcRepo.GetLatestOHLCbyNumber(symbol, interval, market_id, true, limit)
	fmt.Printf("Updating %v(%v) based on %v / %v ohlc.\n", symbol, interval, limitForMACD, limit)
	if err != nil {
		fmt.Println("Error fetching latest OHLC data by number:", err)
	}

	indicators, err := indicators.CalculateIndicators(latestOhlc)

	tenPercentIndex := int(0.9 * float64(limitForMACD))
	for _, indicator := range indicators[tenPercentIndex:] {
		err := ds.indicatorRepo.UpdateIndicator(&indicator)
		if err != nil {
			log.Printf("Error updating indicator: %v\n", err)
		}
	}
	// var ctx = context.Background()
	durationString := map[int]string{
		60:     "1m",
		300:    "5m",
		900:    "15m",
		3600:   "1H",
		14400:  "4H",
		86400:  "1D",
		604800: "1W",
	}
	pair := symbol + "_I" + durationString[interval]

	durationInteger := map[string]int{
		"1m":  60,
		"5m":  300,
		"15m": 900,
		"1H":  3600,
		"4H":  14400,
		"1D":  86400,
		"1W":  604800,
	}
	if durationInteger[durationString[interval]] != interval {
		fmt.Println("error in conversion.")
	}

	indicator_data := map[string]interface{}{
		"Timestamp": strconv.Itoa(indicator.Unix),
		"Volume":    formatFloatOrNil(indicator.Volume),
		"MA20":      formatFloatOrNil(indicator.MA20),
		"MA50":      formatFloatOrNil(indicator.MA50),
		"MACD":      formatFloatOrNil(indicator.MACD),
		"Signal":    formatFloatOrNil(indicator.SignalLine),
		"Histogram": formatFloatOrNil(indicator.Histogram),
		"RSI":       formatFloatOrNil(indicator.RSI),
		"Stoch_K":   formatFloatOrNil(indicator.Stoch_K),
		"Stoch_D":   formatFloatOrNil(indicator.Stoch_D),
		"EMA":       formatFloatOrNil(indicator.EMA),
		"UpperEMA":  formatFloatOrNil(indicator.UpperEMA),
		"LowerEMA":  formatFloatOrNil(indicator.LowerEMA),
		"KDJ_K":     formatFloatOrNil(indicator.KDJ_K),
		"KDJ_D":     formatFloatOrNil(indicator.KDJ_D),
		"KDJ_J":     formatFloatOrNil(indicator.KDJ_J),
	}
	fmt.Println(pair, indicator_data)
	err = ds.redisClient.HMSet(pair, indicator_data)
	if err != nil {
		panic(err)
	}

	// Get data from Redis
	data, err := ds.redisClient.HGetAll("BTC/USD_Price")
	if err != nil {
		panic(err)
	}
	// Convert keys and values from []byte to string
	stringData := make(map[string]string)
	for key, value := range data {
		stringData[key] = value
	}
	// Print the data
	fmt.Println("BTC/USD_Price:", stringData)

}

func (ds *DataService) UpdateAllIndicators(market_id int) {
	ds.UpdateIndicators("BTC/USD", 604800, market_id)
	ds.UpdateIndicators("BTC/USD", 86400, market_id)
	ds.UpdateIndicators("BTC/USD", 14400, market_id)
	ds.UpdateIndicators("BTC/USD", 3600, market_id)
	fmt.Println("All Indicators Updated at:", time.Now())
}

func (ds *DataService) DeleteIndicators(symbol string, interval int) {
	err := ds.indicatorRepo.DeleteIndicator(symbol, interval)
	if err != nil {
		fmt.Printf("Error in deleting Indicator data: %s, interval: %d\n", symbol, interval)
	}
}

func EnableIndicators(ds *DataService, symbol string, interval int, market_id int) {
	indicator, err := ds.indicatorRepo.GetLatestIndicator(symbol, interval)
	if err != nil {
		fmt.Println("Error fetching latest Indicator data:", err)
		ds.InitialIndicators(symbol, interval, market_id, 0)
	} else {
		fmt.Printf("Last daily indicator for %v(%v): %v", symbol, interval, indicator.Timestamp)
		ds.UpdateIndicators(symbol, interval, market_id)
	}
}

func EnableAllIndicators(ds *DataService, market_id int) {
	fmt.Println("Function EnableAllIndicators started at:", time.Now())
	EnableIndicators(ds, "BTC/USD", 604800, 1)
	EnableIndicators(ds, "BTC/USD", 86400, 1)
	EnableIndicators(ds, "BTC/USD", 14400, 1)
	EnableIndicators(ds, "BTC/USD", 3600, 1)
	fmt.Println("Function EnableAllIndicators ended at:", time.Now())
}

func DoTesting(ds *DataService) {
	// startTime := time.Date(2022, 1, 1, 0, 0, 0, 0, time.UTC)
	// endTime := time.Now()

	symbol := "BTC/USD"
	// ds.InitialIndicators(symbol, 86400, 1, 1000)
	ds.UpdateIndicators(symbol, 3600, 1)
	message := strings.ToLower(strings.ReplaceAll(symbol, "/", ""))
	message += " | " + "Go testing running for initial indicators."
	err := ds.redisClient.SendMessage("bot_commands", message)
	if err != nil {
		log.Printf("Error sending message to Redis: %v\n", err)
	}

}
