package indicators

import (
	// "errors"
	"fmt"
	"math"

	"github.com/jessy-3/vanilla/gobackend/models"
	"github.com/jessy-3/vanilla/gobackend/repositories"
	"github.com/markcheno/go-talib"
	// "log"
	// "sort"
	// "strconv"
	// "time"
)

func EMA(prices []float64, period int) []float64 {
	ema := make([]float64, len(prices))
	multiplier := 2.0 / float64(period+1)
	ema[0] = prices[0]

	for i := 1; i < len(prices); i++ {
		ema[i] = (prices[i]-ema[i-1])*multiplier + ema[i-1]
	}

	return ema
}

func MACD(prices []float64) ([]float64, []float64, []float64) {
	macdLine := make([]float64, len(prices))
	signalLine := make([]float64, len(prices))
	histogram := make([]float64, len(prices))

	shortEMA := EMA(prices, 12)
	longEMA := EMA(prices, 26)

	for i := 0; i < len(prices); i++ {
		macdLine[i] = shortEMA[i] - longEMA[i]
	}

	signal := EMA(macdLine, 9)

	for i := 0; i < len(prices); i++ {
		signalLine[i] = signal[i]
		histogram[i] = macdLine[i] - signalLine[i]
	}

	return macdLine, signalLine, histogram
}

func Avg(arr []float64) float64 {
	sum := 0.0
	for _, val := range arr {
		sum += val
	}
	return sum / float64(len(arr))
}

func RSI(prices []float64, n int) []float64 {
	var rsi []float64
	var gains []float64
	var losses []float64
	prevPrice := prices[0]
	for i := 1; i < len(prices); i++ {
		currPrice := prices[i]
		diff := currPrice - prevPrice
		if diff > 0 {
			gains = append(gains, diff)
			losses = append(losses, 0)
		} else {
			gains = append(gains, 0)
			losses = append(losses, -diff)
		}
		prevPrice = currPrice
		if i >= n {
			avgGain := Avg(gains[i-n : i])
			avgLoss := Avg(losses[i-n : i])
			rs := avgGain / avgLoss
			currRsi := 100 - (100 / (1 + rs))
			rsi = append(rsi, currRsi)
		}
	}
	return rsi
}

func CalculateMA(prices []float64, n int) []float64 {
	ma := make([]float64, len(prices))
	for i := n - 1; i < len(prices); i++ {
		sum := 0.0
		for j := i - n + 1; j <= i; j++ {
			sum += prices[j]
		}
		ma[i] = sum / float64(n)
	}
	return ma
}

func CalculateEMA(prices []float64, period int) []float64 {

	ema := talib.Ema(prices, period)

	return ema
}

func CalculateMACD(closePrices []float64) ([]float64, []float64, []float64) {

	macd, signal, hist := talib.Macd(closePrices, 12, 26, 9)

	return macd, signal, hist
}

func CalculateRSI(closePrices []float64) []float64 {

	rsi := talib.Rsi(closePrices, 14)

	return rsi
}

func CalculateStoch(closePrices, highPrices, lowPrices []float64) ([]float64, []float64) {
	fastKPeriod := 14
	slowKPeriod := 3
	slowDPeriod := 3

	// matype: 0=SMA, 1=EMA, 2=WMA, 3=DEMA, 4=TEMA, 5=TRIMA, 6=KAMA, 7=MAMA, 8=T3 (Default=SMA)
	k, d := talib.Stoch(highPrices, lowPrices, closePrices, fastKPeriod, slowKPeriod, talib.SMA, slowDPeriod, talib.SMA)

	// Drop the first (fastKPeriod - 1) elements from k and d
	for i := 0; i < fastKPeriod-1; i++ { // have problem here.
		k[i] = 0
		d[i] = 0
	}
	return k, d
}

func CalculateKDJ(closePrices, highPrices, lowPrices []float64) ([]float64, []float64, []float64) {
	// Calculate RSV
	rsv := make([]float64, len(closePrices))
	for i := 8; i < len(closePrices); i++ {
		var maxHigh, minLow float64
		for n := i - 8; n <= i; n++ {
			if n == i-8 {
				maxHigh, minLow = highPrices[n], lowPrices[n]
			} else {
				maxHigh = math.Max(maxHigh, highPrices[n])
				minLow = math.Min(minLow, lowPrices[n])
			}
		}
		rsv[i] = (closePrices[i] - minLow) / (maxHigh - minLow) * 100
	}
	// Calculate KDJ
	fastK := 9
	kPeriod := 3
	dPeriod := 3

	k := make([]float64, len(closePrices))
	d := make([]float64, len(closePrices))

	k[fastK-1] = rsv[fastK-1]
	d[fastK-1] = k[fastK-1]
	for i := fastK; i < len(closePrices); i++ {
		k[i] = (1-1/float64(kPeriod))*k[i-1] + 1/float64(kPeriod)*rsv[i]
		d[i] = (1-1/float64(dPeriod))*d[i-1] + 1/float64(dPeriod)*k[i]
	}

	j := make([]float64, len(closePrices))
	for i := 0; i < len(closePrices); i++ {
		j[i] = 3*k[i] - 2*d[i]
	}

	return k, d, j
}

func CalculateIndicators(ohlcData []models.OHLCPrice) ([]models.Indicator, error) {

	closePrices, err := repositories.GetOHLCInFloat64(ohlcData, 3)
	if err != nil {
		fmt.Println("Error fetching OHLC column in float 64:", err)
	}
	highPrices, err := repositories.GetOHLCInFloat64(ohlcData, 1)
	if err != nil {
		fmt.Println("Error fetching OHLC column in float 64:", err)
	}
	lowPrices, err := repositories.GetOHLCInFloat64(ohlcData, 2)
	if err != nil {
		fmt.Println("Error fetching OHLC column in float 64:", err)
	}

	ma_20 := CalculateMA(closePrices, 20)
	ma_50 := CalculateMA(closePrices, 50)

	macd, signal, histogram := CalculateMACD(closePrices)
	if len(ohlcData) != len(macd) {
		fmt.Println("Error occured in initial MACD for different length")
	}

	rsi := CalculateRSI(closePrices)

	stoch_k, stoch_d := CalculateStoch(closePrices, highPrices, lowPrices)

	closeEMA := CalculateEMA(closePrices, 33)
	upperEMA := CalculateEMA(highPrices, 33)
	lowerEMA := CalculateEMA(lowPrices, 33)
	if len(ohlcData) != len(upperEMA) {
		fmt.Println("Error occured in initial EMA for different length")
	}

	k, d, j := CalculateKDJ(closePrices, highPrices, lowPrices)

	if err != nil {
		return nil, err
	}

	indicators := make([]models.Indicator, len(ohlcData))
	for i := range ohlcData {
		indicators[i] = models.Indicator{
			Unix:       ohlcData[i].Unix,
			Timestamp:  ohlcData[i].Date,
			Symbol:     ohlcData[i].Symbol,
			Interval:   ohlcData[i].Interval,
			Volume:     &ohlcData[i].Volume,
			MA20:       &ma_20[i],
			MA50:       &ma_50[i],
			MACD:       &macd[i],
			SignalLine: &signal[i],
			Histogram:  &histogram[i],
			RSI:        &rsi[i],
			Stoch_K:    &stoch_k[i],
			Stoch_D:    &stoch_d[i],
			EMA:        &closeEMA[i],
			UpperEMA:   &upperEMA[i],
			LowerEMA:   &lowerEMA[i],
			KDJ_K:      &k[i],
			KDJ_D:      &d[i],
			KDJ_J:      &j[i],
		}
	}

	return indicators, nil
}
