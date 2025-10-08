from django.db import models
from django.conf import settings
from django_unixdatetimefield import UnixDateTimeField
from django.contrib.auth.models import User


# Create your models here.
class SymbolInfo(models.Model):
    name = models.CharField(max_length=10)
    url_symbol = models.CharField(max_length=10)
    base_decimals = models.IntegerField()
    counter_decimals = models.IntegerField()
    market_id = models.IntegerField()  # 1 for Bitstamp
    trading = models.CharField(max_length=8)
    description = models.CharField(max_length=100, null=True)

    class Meta:
        managed = True
        db_table = 'qt_symbol_info'

    def __str__(self):
        return self.name

class OhlcPrice(models.Model):
    unix = UnixDateTimeField()
    date = models.DateTimeField()  # This field type is a guess.
    symbol = models.CharField(max_length=10)
    open = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    high = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    low = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    close = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    volume = models.DecimalField(max_digits=20, decimal_places=8, null=True)  # This field type is a guess.
    volume_base = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    market_id = models.IntegerField()  # 1 for Bitstamp
    interval = models.IntegerField()

    class Meta:
        managed = True
        db_table = 'qt_ohlc'

class OhlcPriceMinute(models.Model):
    unix = UnixDateTimeField()
    date = models.DateTimeField()  # This field type is a guess.
    symbol = models.CharField(max_length=10)
    open = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    high = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    low = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    close = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    volume = models.DecimalField(max_digits=20, decimal_places=8, null=True)  # This field type is a guess.
    volume_base = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    market_id = models.IntegerField()  # 1 for Bitstamp
    interval = models.IntegerField()

    class Meta:
        managed = True
        db_table = 'qt_ohlc_m'

    def __str__(self):
        return self.symbol

class TslaPrice(models.Model):
    unix = UnixDateTimeField()
    date = models.DateTimeField()  # This field type is a guess.
    symbol = models.CharField(max_length=10)
    open = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    high = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    low = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    close = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    volume = models.DecimalField(max_digits=20, decimal_places=8, null=True)  # This field type is a guess.
    volume_base = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # This field type is a guess.
    market_id = models.IntegerField()  # 1 for Bitstamp
    interval = models.IntegerField()

    class Meta:
        managed = True
        db_table = 'qt_tsla'


class Indicator(models.Model):
    unix = UnixDateTimeField()
    timestamp = models.DateTimeField()
    symbol = models.CharField(max_length=10)
    interval = models.IntegerField()
    volume = models.DecimalField(max_digits=20, decimal_places=8, null=True)  # This field type is a guess.
    ma_20 = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    ma_50 = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    macd = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    signal_line = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    histogram = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    rsi = models.DecimalField(max_digits=18, decimal_places=8, null=True)    #relative_strength_index
    stoch_k = models.DecimalField(max_digits=18, decimal_places=8, null=True)   #stochastic_oscillator_k
    stoch_d = models.DecimalField(max_digits=18, decimal_places=8, null=True)   #stochastic_oscillator_d
    ema = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    upper_ema = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    lower_ema = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    kdj_k = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    kdj_d = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    kdj_j = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    # EMA Channel (轨道当值) indicators
    ema_high_33 = models.DecimalField(max_digits=18, decimal_places=8, null=True)  # 上轨当值 (EMA of High prices, 33 periods)
    ema_low_33 = models.DecimalField(max_digits=18, decimal_places=8, null=True)   # 下轨当值 (EMA of Low prices, 33 periods)

    class Meta:
        db_table = 'qt_indicator'
        unique_together = ('symbol', 'interval', 'unix')

class IndicatorMinute(models.Model):
    unix = UnixDateTimeField()
    timestamp = models.DateTimeField()
    symbol = models.CharField(max_length=10)
    interval = models.IntegerField()
    volume = models.DecimalField(max_digits=20, decimal_places=8, null=True)  # This field type is a guess.
    ma_20 = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    ma_50 = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    macd = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    signal_line = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    histogram = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    rsi = models.DecimalField(max_digits=18, decimal_places=8, null=True)    #relative_strength_index
    stoch_k = models.DecimalField(max_digits=18, decimal_places=8, null=True)   #stochastic_oscillator_k
    stoch_d = models.DecimalField(max_digits=18, decimal_places=8, null=True)   #stochastic_oscillator_d
    ema = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    upper_ema = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    lower_ema = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    kdj_k = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    kdj_d = models.DecimalField(max_digits=18, decimal_places=8, null=True)
    kdj_j = models.DecimalField(max_digits=18, decimal_places=8, null=True)


    class Meta:
        db_table = 'qt_indicator_m'
        unique_together = ('symbol', 'interval', 'unix')


class TradeData(models.Model):
    unix = UnixDateTimeField()
    symbol = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=18, decimal_places=8)
    volume = models.DecimalField(max_digits=18, decimal_places=8)
    tid = models.CharField(max_length=10)
    trade_type = models.CharField(max_length=10)

    class Meta:
        db_table = 'qt_tradedata'

    def __str__(self):
        return f"{self.symbol} {self.trade_type} {self.price} {self.volume}"


class UserProfile(models.Model):
#    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    trading_user_id = models.CharField(max_length=30)  # userid in trading market
    market_id = models.IntegerField()  # 1 for Bitstamp, 2 for Kraken
    # Add additional fields later

    class Meta:
        db_table = 'tu_user'

    def __str__(self):
        return f"{self.user.username} ({self.market_id}): {self.trading_user_id}"

class UserOrder(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)
    order_type = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=18, decimal_places=8)
    quantity = models.DecimalField(max_digits=18, decimal_places=8)
    status = models.CharField(max_length=10)
    market_id = models.IntegerField()  # 1 for Bitstamp, 2 for Kraken
    class Meta:
        db_table = 'tu_order'

class UserTrade(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=18, decimal_places=8)
    quantity = models.DecimalField(max_digits=18, decimal_places=8)
    unix = UnixDateTimeField()
    timestamp = models.DateTimeField()
    market_id = models.IntegerField()  # 1 for Bitstamp, 2 for Kraken
    class Meta:
        db_table = 'tu_trade'

class Transaction(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    transaction_type = models.CharField(max_length=10)
    timestamp = models.DateTimeField()
    market_id = models.IntegerField()  # 1 for Bitstamp, 2 for Kraken
    class Meta:
        db_table = 'tu_transaction'

class Portfolio(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)
    quantity = models.DecimalField(max_digits=18, decimal_places=8)
    average_price = models.DecimalField(max_digits=18, decimal_places=8)
    balance = models.DecimalField(max_digits=18, decimal_places=8)
    market_id = models.IntegerField()  # 1 for Bitstamp, 2 for Kraken
    class Meta:
        db_table = 'tu_portfolio'
