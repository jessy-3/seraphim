package repositories

import (
	// "context"
	"database/sql"
	"fmt"
	"time"

	// "github.com/go-redis/redis/v8"
	// "github.com/jackc/pgx/v4/pgxpool"
	"github.com/jessy-3/vanilla/gobackend/config"
	"github.com/jessy-3/vanilla/gobackend/models"
	"github.com/jmoiron/sqlx"
	_ "github.com/lib/pq" // Add this import for PostgreSQL support
)

// RdsConn *redis.Client
// unixTime := time.Unix(int64(OHLCPrice.Unix), 0)

type SymbolInfoRepository struct {
	DbConn *sqlx.DB
}

func NewSymbolInfoRepository(db *sqlx.DB) *SymbolInfoRepository {
	return &SymbolInfoRepository{DbConn: db}
}

// Implement SymbolInfo repository methods here

type OHLCRepository struct {
	DbConn *sqlx.DB
}

func NewOHLCRepository(cfg config.Config) (*OHLCRepository, error) {
	db, err := sqlx.Connect("postgres", cfg.PostgresConnectionString())
	if err != nil {
		return nil, err
	}
	return &OHLCRepository{
		DbConn: db,
	}, nil
}

func (r *OHLCRepository) GetOHLC(symbol string, interval int, market_id int, ascending bool, times ...time.Time) ([]models.OHLCPrice, error) {
	var ohlcData []models.OHLCPrice
	var orderQuery string
	var startTime, endTime time.Time
	if len(times) >= 2 {
		startTime, endTime = times[0], times[1]
	} else if len(times) == 1 {
		startTime = times[0]
	}

	baseQuery := `SELECT * FROM qt_ohlc WHERE symbol = $1 AND interval = $2 AND market_id = $3`
	if ascending {
		orderQuery = `ORDER BY unix ASC`
	} else {
		orderQuery = `ORDER BY unix DESC`
	}

	if !startTime.IsZero() && !endTime.IsZero() {
		query := baseQuery + ` AND unix BETWEEN $4 AND $5 ` + orderQuery
		err := r.DbConn.Select(&ohlcData, query, symbol, interval, market_id, startTime.Unix(), endTime.Unix())
		return ohlcData, err
	} else if !startTime.IsZero() {
		query := baseQuery + ` AND unix >= $4 ` + orderQuery
		err := r.DbConn.Select(&ohlcData, query, symbol, interval, market_id, startTime.Unix())
		return ohlcData, err
	} else {
		query := baseQuery + " " + orderQuery
		err := r.DbConn.Select(&ohlcData, query, symbol, interval, market_id)
		return ohlcData, err
	}
}

func (r *OHLCRepository) GetLatestOHLCbyNumber(symbol string, interval int, market_id int, ascending bool, limit int) ([]models.OHLCPrice, error) {
	var ohlcData []models.OHLCPrice
	query := `SELECT * FROM qt_ohlc WHERE symbol = $1 AND interval = $2 AND market_id = $3 ORDER BY unix DESC LIMIT $4`
	err := r.DbConn.Select(&ohlcData, query, symbol, interval, market_id, limit)
	if err != nil {
		return nil, err
	}
	if ascending {
		for i, j := 0, len(ohlcData)-1; i < j; i, j = i+1, j-1 {
			ohlcData[i], ohlcData[j] = ohlcData[j], ohlcData[i]
		}
	}
	return ohlcData, nil
}

func (r *OHLCRepository) GetLatestOHLC(symbol string, interval int, market_id int) (*models.OHLCPrice, error) {
	ohlc := &models.OHLCPrice{}
	query := `SELECT * FROM qt_ohlc WHERE symbol = $1 AND interval = $2 AND market_id = $3 ORDER BY unix DESC LIMIT 1`
	err := r.DbConn.Get(ohlc, query, symbol, interval, market_id)
	if err != nil {
		return nil, err
	}
	return ohlc, nil
}

func GetOHLCInFloat64(data []models.OHLCPrice, columnIndex int) ([]float64, error) {
	result := make([]float64, len(data))

	for i, ohlc := range data {
		switch columnIndex {
		case 0:
			result[i] = ohlc.Open
		case 1:
			result[i] = ohlc.High
		case 2:
			result[i] = ohlc.Low
		case 3:
			result[i] = ohlc.Close
		case 4:
			result[i] = ohlc.Volume
		case 5:
			result[i] = ohlc.VolumeBase
		default:
			return nil, fmt.Errorf("invalid columnIndex")
		}
	}
	return result, nil
}

type IndicatorRepository struct {
	DbConn *sqlx.DB
}

func NewIndicatorRepository(db *sqlx.DB) *IndicatorRepository {
	return &IndicatorRepository{
		DbConn: db,
	}
}

func (r *IndicatorRepository) GetLatestIndicator(symbol string, interval int) (*models.Indicator, error) {
	indicator := &models.Indicator{}
	query := `SELECT unix, timestamp, symbol, interval, volume, ma_20, ma_50, macd, signal_line, histogram, rsi, stoch_k, stoch_d, ema, upper_ema, lower_ema, kdj_k, kdj_d, kdj_j FROM qt_indicator WHERE symbol = $1 AND interval = $2 ORDER BY unix DESC LIMIT 1`
	err := r.DbConn.Get(indicator, query, symbol, interval)
	if err != nil {
		return nil, err
	}
	return indicator, nil
}

func (r *IndicatorRepository) InsertIndicator(indicator *models.Indicator) error {
	query := `INSERT INTO qt_indicator (unix, timestamp, symbol, interval, volume, ma_20, ma_50, macd, signal_line, histogram, rsi, stoch_k, stoch_d, ema, upper_ema, lower_ema, kdj_k, kdj_d, kdj_j)
	          VALUES (:unix, :timestamp, :symbol, :interval, :volume, :ma_20, :ma_50, :macd, :signal_line, :histogram, :rsi, :stoch_k, :stoch_d, :ema, :upper_ema, :lower_ema, :kdj_k, :kdj_d, :kdj_j)`
	_, err := r.DbConn.NamedExec(query, indicator)
	return err
}

func (r *IndicatorRepository) UpdateIndicator(indicator *models.Indicator) error {
	// First, check if the record exists in the table
	existingIndicator := &models.Indicator{}
	query := `SELECT * FROM qt_indicator WHERE symbol = $1 AND interval = $2 AND unix = $3`
	err := r.DbConn.Get(existingIndicator, query, indicator.Symbol, indicator.Interval, indicator.Unix)

	// If a record is found, update the existing record
	if err == nil {
		updateQuery := `UPDATE qt_indicator
		                SET volume = :volume,
		                    ma_20 = :ma_20,
		                    ma_50 = :ma_50,
		                    macd = :macd,
		                    signal_line = :signal_line,
		                    histogram = :histogram,
		                    rsi = :rsi,
		                    stoch_k = :stoch_k,
		                    stoch_d = :stoch_d,
							ema = :ema,
		                    upper_ema = :upper_ema,
		                    lower_ema = :lower_ema,
		                    kdj_k = :kdj_k,
		                    kdj_d = :kdj_d,
		                    kdj_j = :kdj_j
		                WHERE symbol = :symbol AND interval = :interval AND unix =:unix`

		_, updateErr := r.DbConn.NamedExec(updateQuery, indicator)
		return updateErr
	}

	// If the record is not found, insert a new record
	if err == sql.ErrNoRows {
		return r.InsertIndicator(indicator)
	}

	// If there is any other error, return it
	return err
}

func (r *IndicatorRepository) DeleteIndicator(symbol string, interval int) error {
	query := `DELETE FROM qt_indicator WHERE symbol = $1 AND interval = $2`
	result, err := r.DbConn.Exec(query, symbol, interval)
	if err != nil {
		return err
	}
	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return err
	}
	if rowsAffected == 0 {
		return fmt.Errorf("no indicator found with symbol: %s, interval: %d", symbol, interval)
	}

	return nil
}

// Implement Indicator repository methods here
