package models

import (
	"time"
)

type SymbolInfo struct {
	ID              int    `db:"id"`
	Name            string `db:"name"`
	URLSymbol       string `db:"url_symbol"`
	BaseDecimals    int    `db:"base_decimals"`
	CounterDecimals int    `db:"counter_decimals"`
	MarketID        int    `db:"market_id"`
	Trading         string `db:"trading"`
	Description     string `db:"description"`
}

type OHLCPrice struct {
	ID         int64     `db:"id"`
	Unix       int       `db:"unix"`
	Date       time.Time `db:"date"`
	Symbol     string    `db:"symbol"`
	Open       float64   `db:"open"`
	High       float64   `db:"high"`
	Low        float64   `db:"low"`
	Close      float64   `db:"close"`
	Volume     float64   `db:"volume"`
	VolumeBase float64   `db:"volume_base"`
	MarketID   int       `db:"market_id"`
	Interval   int       `db:"interval"`
}

type Indicator struct {
	ID         int64     `db:"id"`
	Unix       int       `db:"unix"`
	Timestamp  time.Time `db:"timestamp"`
	Symbol     string    `db:"symbol"`
	Interval   int       `db:"interval"`
	Volume     *float64  `db:"volume"`
	MA20       *float64  `db:"ma_20"`
	MA50       *float64  `db:"ma_50"`
	MACD       *float64  `db:"macd"`
	SignalLine *float64  `db:"signal_line"`
	Histogram  *float64  `db:"histogram"`
	RSI        *float64  `db:"rsi"`
	Stoch_K    *float64  `db:"stoch_k"`
	Stoch_D    *float64  `db:"stoch_d"`
	EMA        *float64  `db:"ema"`
	UpperEMA   *float64  `db:"upper_ema"`
	LowerEMA   *float64  `db:"lower_ema"`
	KDJ_K      *float64  `db:"kdj_k"`
	KDJ_D      *float64  `db:"kdj_d"`
	KDJ_J      *float64  `db:"kdj_j"`
}
