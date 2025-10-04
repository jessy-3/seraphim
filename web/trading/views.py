from django.shortcuts import render
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, DeleteView, FormView, UpdateView

from api.models import SymbolInfo, OhlcPrice, TslaPrice
from api.wsclient import ws_client
from datetime import timedelta
from django.conf import settings
# from vanilla.settings import SERVER_IP, SERVER_PORT
import redis
import logging
logger = logging.getLogger('TradingListView')
logger.setLevel(logging.INFO)

REDIS_HOST = "redis"  # Use your Redis host
REDIS_PORT = 6379  # Use your Redis port

# class TradingListView(ListView):
#     template_name = "trading/trading_home.html"

class TradingListView(View):
    template_name = "trading/trading_home.html"

    def get(self, request) :
        ws_client('start')      # start market websocket client
        # Retrieve the latest price for each symbol from Redis
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        symbol_data = {}
        latest_prices = {}

        intervals = ["1m", "5m", "15m", "1H", "4H", "1D", "1W"]
        durationInteger = {
            "1m":  60,
            "5m":  300,
            "15m": 900,
            "1H":  3600,
            "4H":  14400,
            "1D":  86400,
            "1W":  604800,
        }
 
        qs = SymbolInfo.objects.filter(trading="Enabled")
        for instance in qs:
            ws_client('subscribe','live_trades_' + instance.url_symbol)
            symbol = instance.name
            digits = instance.counter_decimals
            if digits < 2:
                digits = 2

            # for symbol in symbols:
            price_data = r.hgetall(f"{symbol}_Price")
            if not price_data:
                # Handle the case when the key is not found in Redis
                latest_prices[symbol] = "N/A"  # or any default value
            else:
                decoded_data = {key.decode(): value.decode() for key, value in price_data.items()}
                latest_prices[symbol] = decoded_data.get("price", "")

            # Retrieve OHLC data from the ORM
            symbol_indicators = {}
            for interval in intervals:
                indicator_data = r.hgetall(f"{symbol}_I{interval}")
                if indicator_data:
                    ohlc_data = OhlcPrice.objects.filter(symbol=symbol, interval=durationInteger[interval]).order_by('-date')[1:2].first()
                    if ohlc_data:
                        logger.info(ohlc_data)
                        decoded_data = {key.decode(): value.decode() for key, value in indicator_data.items()}
                        v_volume = float(decoded_data.get("Volume", 0)) if decoded_data.get("Volume", "") != "" else 0
                        f_volume = "{:.{}f}".format(v_volume, digits)
                        v_ma20 = float(decoded_data.get("MA20", 0)) if decoded_data.get("MA20", "") != "" else 0
                        f_ma20 = "{:.{}f}".format(v_ma20, digits)
                        v_ma50 = float(decoded_data.get("MA50", 0)) if decoded_data.get("MA50", "") != "" else 0
                        f_ma50 = "{:.{}f}".format(v_ma50, digits)
                        v_macd = float(decoded_data.get("MACD", 0)) if decoded_data.get("MACD", "") != "" else 0
                        f_macd = "{:.{}f}".format(v_macd, digits)
                        v_signal = float(decoded_data.get("Signal", 0))  if decoded_data.get("Signal", "") != "" else 0
                        f_signal = "{:.{}f}".format(v_signal, digits)
                        v_histogram = float(decoded_data.get("Histogram", 0)) if decoded_data.get("Histogram", "") != "" else 0
                        f_histogram = "{:.{}f}".format(v_histogram, digits)

                        v_rsi = float(decoded_data.get("RSI", 0)) if decoded_data.get("RSI", "") != "" else 0
                        f_rsi = "{:.{}f}".format(v_rsi, digits)
                        v_stochk = float(decoded_data.get("Stoch_K", 0)) if decoded_data.get("Stoch_K", "") != "" else 0
                        f_stochk = "{:.{}f}".format(v_stochk, digits)
                        v_stochd = float(decoded_data.get("Stoch_D", 0)) if decoded_data.get("Stoch_D", "") != "" else 0
                        f_stochd = "{:.{}f}".format(v_stochd, digits)

                        v_ema = float(decoded_data.get("EMA", 0)) if decoded_data.get("EMA", "") != "" else 0
                        f_ema = "{:.{}f}".format(v_ema, digits)
                        v_upper = float(decoded_data.get("UpperEMA", 0)) if decoded_data.get("UpperEMA", "") != "" else 0
                        f_upper = "{:.{}f}".format(v_upper, digits)
                        v_lower = float(decoded_data.get("LowerEMA", 0)) if decoded_data.get("LowerEMA", "") != "" else 0
                        f_lower = "{:.{}f}".format(v_lower, digits)

                        v_kdj_k = float(decoded_data.get("KDJ_K", 0)) if decoded_data.get("KDJ_K", "") != "" else 0
                        f_kdj_k = "{:.{}f}".format(v_kdj_k, digits)
                        v_kdj_d = float(decoded_data.get("KDJ_D", 0)) if decoded_data.get("KDJ_D", "") != "" else 0
                        f_kdj_d = "{:.{}f}".format(v_kdj_d, digits)
                        v_kdj_j = float(decoded_data.get("KDJ_J", 0)) if decoded_data.get("KDJ_J", "") != "" else 0
                        f_kdj_j = "{:.{}f}".format(v_kdj_j, digits)

                        closetime = ohlc_data.date + timedelta(seconds=durationInteger[interval])

                        symbol_indicators[interval] = {
                            'ohlc_close': "{:.{}f}".format(ohlc_data.close, digits) + " @"+ closetime.strftime('%m-%d %H%MZ'),
                            'change': str(float(latest_prices[symbol]) - float(ohlc_data.close)),
                            'volume': f_volume,
                            'ma20': f_ma20,
                            'ma50': f_ma50,
                            'macd': f_macd,
                            'signal': f_signal,
                            'histogram': f_histogram,
                            'rsi': f_rsi,
                            'stoch_k': f_stochk,
                            'stoch_d': f_stochd,
                            'closeEMA': f_ema,
                            'upperEMA': f_upper,
                            'lowerEMA': f_lower,
                            'kdj_k': f_kdj_k,
                            'kdj_d': f_kdj_d,
                            'kdj_j': f_kdj_j,
                        }
                    else:
                        symbol_indicators[interval] = "N/A"
                else:
                    symbol_indicators[interval] = "N/A"

            symbol_data[symbol] = {
                'price': latest_prices.get(symbol, ""),
                'digits': digits,
                'indicators': symbol_indicators,
            }
            print(symbol_data[symbol])
            logger.info(f"{symbol}, {symbol_data[symbol]}")


        # vanilla websocket server endpoint
        ipport = "wss://"+settings.SERVER_IP+"/ws/tick"

        ctx = {'symbol_data': symbol_data, 'ipport': ipport, 'favorites': "favorites", 'search': "strval"}
        return render(request, self.template_name, ctx)
    
        # try:
        #     r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        #     if not r.ping():
        #         r = True    # not connected
        #         logger.info("Connection to Redis failed.")
        #         print("Connection to Redis failed.")
        # except redis.ConnectionError as e:
        #     r = True        # not connected
        #     logger.info(f"Connection error: {e}")
        #     print(f"Connection error: {e}")
        # if not (r == True):       # redis connected
        #     logger.info("redis connected log for hgetall")
        #     print("redis connected for hgetall")
        #     btc_usd_data = r.hgetall("BTC/USD_Price")
        #     btc_usd_price = {key.decode(): value.decode() for key, value in btc_usd_data.items()}
        #     logger.info(btc_usd_price)
        #     print(btc_usd_price)

class TradingDetailView(DetailView):

        model = OhlcPrice
        template_name = "trading/trading_detail.html"

        def get(self, request, pk):
            x = OhlcPrice.objects.get(id=pk)
            # comments = Comment.objects.filter(ad=x).order_by('-updated_at')
            # comment_form = CommentForm()
            context = {'ctd': x } #, 'comments': comments, 'comment_form': comment_form}
            return render(request, self.template_name, context)

