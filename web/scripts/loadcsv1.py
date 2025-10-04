'''
This program is to load OHLC data from bitstamp downloaded csv
'''
import sqlite3
import pandas as pd
from sqlalchemy import create_engine

def upload_ohlc(pair, filename, interval, tablename):
    # engine = sqlite3.connect('db.sqlite3')
    # engine = create_engine('mysql://root:2022pass@localhost/vanilla') # enter your password and database names here
    engine = create_engine('postgresql://postgres:2022pass@localhost/vanilla')

    df = pd.read_csv(filename,sep=',',quotechar='\'',skiprows=1,encoding='utf8')
    df['date']=pd.to_datetime(df['date'], utc=True)
    df.rename(columns={"Volume "+pair[pair.find("/")+1:] : "volume_base" }, inplace=True)  # / USD
    df.rename(columns={"Volume "+pair[:pair.find("/")] : "volume" }, inplace=True)         # BTC /
    df['interval']=interval
    df['market_id']=1
    df.to_sql(tablename,con=engine,index=False,if_exists='append')


if __name__ == '__main__':
#    upload_ohlc("BTC/USD", '/Users/jessy/Downloads/Bitstamp_BTCUSD_D.csv', 86400, 'qt_ohlc')
    # upload_ohlc("BTC/USD", 'data/Bitstamp_BTCUSD_d.csv', 86400, 'qt_ohlc')
    # upload_ohlc("ETH/USD", 'data/Bitstamp_ETHUSD_d.csv', 86400, 'qt_ohlc')
    # upload_ohlc("ETH/BTC", 'data/Bitstamp_ETHBTC_d.csv', 86400, 'qt_ohlc')
    # upload_ohlc("LTC/USD", 'data/Bitstamp_LTCUSD_d.csv', 86400, 'qt_ohlc')
    # upload_ohlc("LTC/BTC", 'data/Bitstamp_LTCBTC_d.csv', 86400, 'qt_ohlc')
    # upload_ohlc("XRP/USD", 'data/Bitstamp_XRPUSD_d.csv', 86400, 'qt_ohlc')
    # upload_ohlc("XRP/BTC", 'data/Bitstamp_XRPBTC_d.csv', 86400, 'qt_ohlc')
    # upload_ohlc("BTC/USD", 'data/Bitstamp_BTCUSD_1h.csv', 3600, 'qt_ohlc')
    upload_ohlc("ETH/USD", 'data/Bitstamp_ETHUSD_1h.csv', 3600, 'qt_ohlc')
    upload_ohlc("ETH/BTC", 'data/Bitstamp_ETHBTC_1h.csv', 3600, 'qt_ohlc')
    upload_ohlc("LTC/USD", 'data/Bitstamp_LTCUSD_1h.csv', 3600, 'qt_ohlc')
    upload_ohlc("LTC/BTC", 'data/Bitstamp_LTCBTC_1h.csv', 3600, 'qt_ohlc')
    upload_ohlc("XRP/USD", 'data/Bitstamp_XRPUSD_1h.csv', 3600, 'qt_ohlc')
    upload_ohlc("XRP/BTC", 'data/Bitstamp_XRPBTC_1h.csv', 3600, 'qt_ohlc')
