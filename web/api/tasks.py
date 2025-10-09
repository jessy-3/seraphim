"""
Celery tasks for automated data updates and calculations
"""
import subprocess
import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='api.tasks.fetch_ohlc_data')
def fetch_ohlc_data(self):
    """
    Fetch OHLC data from Kraken API
    Runs: Every hour at 5 minutes past
    """
    logger.info("Starting OHLC data fetch...")
    try:
        result = subprocess.run(
            ['python', '/app/scripts/fetch_historical_data.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            logger.info(f"OHLC fetch completed successfully")
            logger.debug(result.stdout)
            return {'status': 'success', 'output': result.stdout}
        else:
            logger.error(f"OHLC fetch failed: {result.stderr}")
            return {'status': 'error', 'error': result.stderr}
    
    except subprocess.TimeoutExpired:
        logger.error("OHLC fetch timed out")
        return {'status': 'error', 'error': 'Timeout after 5 minutes'}
    except Exception as e:
        logger.error(f"OHLC fetch exception: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task(bind=True, name='api.tasks.calculate_indicators')
def calculate_indicators(self):
    """
    Calculate technical indicators (RSI, MACD, SMA, EMA, ADX)
    Runs: Every hour at 10 minutes past (after OHLC fetch)
    """
    logger.info("Starting indicator calculations...")
    try:
        result = subprocess.run(
            ['python', '/app/scripts/calculate_indicators.py'],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode == 0:
            logger.info("Indicator calculations completed successfully")
            logger.debug(result.stdout)
            return {'status': 'success', 'output': result.stdout}
        else:
            logger.error(f"Indicator calculation failed: {result.stderr}")
            return {'status': 'error', 'error': result.stderr}
    
    except subprocess.TimeoutExpired:
        logger.error("Indicator calculation timed out")
        return {'status': 'error', 'error': 'Timeout after 10 minutes'}
    except Exception as e:
        logger.error(f"Indicator calculation exception: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task(bind=True, name='api.tasks.calculate_ema_channel')
def calculate_ema_channel(self):
    """
    Calculate EMA Channel (EMA High 33, EMA Low 33)
    Runs: Every hour at 15 minutes past
    """
    logger.info("Starting EMA channel calculations...")
    try:
        result = subprocess.run(
            ['python', '/app/scripts/calculate_ema_channel.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            logger.info("EMA channel calculations completed successfully")
            logger.debug(result.stdout)
            return {'status': 'success', 'output': result.stdout}
        else:
            logger.error(f"EMA channel calculation failed: {result.stderr}")
            return {'status': 'error', 'error': result.stderr}
    
    except subprocess.TimeoutExpired:
        logger.error("EMA channel calculation timed out")
        return {'status': 'error', 'error': 'Timeout after 5 minutes'}
    except Exception as e:
        logger.error(f"EMA channel calculation exception: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task(bind=True, name='api.tasks.calculate_market_regime')
def calculate_market_regime(self):
    """
    Calculate market regime (trending/ranging, ADX, channel metrics)
    Runs: Every hour at 20 minutes past
    """
    logger.info("Starting market regime calculations...")
    try:
        result = subprocess.run(
            ['python', '/app/scripts/calculate_market_regime.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            logger.info("Market regime calculations completed successfully")
            logger.debug(result.stdout)
            return {'status': 'success', 'output': result.stdout}
        else:
            logger.error(f"Market regime calculation failed: {result.stderr}")
            return {'status': 'error', 'error': result.stderr}
    
    except subprocess.TimeoutExpired:
        logger.error("Market regime calculation timed out")
        return {'status': 'error', 'error': 'Timeout after 5 minutes'}
    except Exception as e:
        logger.error(f"Market regime calculation exception: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task(bind=True, name='api.tasks.generate_trading_signals')
def generate_trading_signals(self):
    """
    Generate trading signals based on market regime and indicators
    Runs: Every hour at 25 minutes past
    """
    logger.info("Starting trading signal generation...")
    try:
        result = subprocess.run(
            ['python', '/app/scripts/generate_trading_signals.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            logger.info("Trading signal generation completed successfully")
            logger.debug(result.stdout)
            return {'status': 'success', 'output': result.stdout}
        else:
            logger.error(f"Trading signal generation failed: {result.stderr}")
            return {'status': 'error', 'error': result.stderr}
    
    except subprocess.TimeoutExpired:
        logger.error("Trading signal generation timed out")
        return {'status': 'error', 'error': 'Timeout after 5 minutes'}
    except Exception as e:
        logger.error(f"Trading signal generation exception: {str(e)}")
        return {'status': 'error', 'error': str(e)}


@shared_task(bind=True, name='api.tasks.manual_update_all')
def manual_update_all(self):
    """
    Manual trigger to update all data (OHLC + Indicators + Signals)
    Can be called from Django Admin or API endpoint
    """
    logger.info("Starting manual full data update...")
    
    results = {}
    
    # Step 1: Fetch OHLC
    results['ohlc'] = fetch_ohlc_data()
    
    # Step 2: Calculate Indicators
    results['indicators'] = calculate_indicators()
    
    # Step 3: Calculate EMA Channel
    results['ema_channel'] = calculate_ema_channel()
    
    # Step 4: Calculate Market Regime
    results['market_regime'] = calculate_market_regime()
    
    # Step 5: Generate Trading Signals
    results['signals'] = generate_trading_signals()
    
    logger.info("Manual full data update completed")
    return results

