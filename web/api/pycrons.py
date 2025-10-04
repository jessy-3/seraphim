import asyncio
import requests
import psycopg2
# import sqlite3
import datetime, time, pytz, math, logging
from asgiref.sync import async_to_sync
import json
import redis
import channels.layers

from .utils import send_command_to_go, send_command_to_bot

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# logger = logging.getLogger('main')
# cron_logger = logging.getLogger('my_cron_job')
min_logger = logging.getLogger('min_cron_job')

REDIS_HOST = "redis"  # Use your Redis host
REDIS_PORT = 6379  # Use your Redis port

def get_starting_unix():
    now = datetime.datetime.now()

    # Calculate starting times
    time_starts = {
        'minute': now.replace(second=0, microsecond=0),
        'hour': now.replace(minute=0, second=0, microsecond=0),
        'day': now.replace(hour=0, minute=0, second=0, microsecond=0),
        'week': now.replace(hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(days=now.weekday()),
        'month': now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
        '4hours': now - datetime.timedelta(hours=(now.hour % 4), minutes=now.minute, seconds=now.second, microseconds=now.microsecond),
        '5minutes': now - datetime.timedelta(minutes=(now.minute % 5), seconds=now.second, microseconds=now.microsecond),
        '15minutes': now - datetime.timedelta(minutes=(now.minute % 15), seconds=now.second, microseconds=now.microsecond),
    }
    # Convert datetime objects to Unix timestamps
    unixtimestamps = {key: int(value.timestamp()) for key, value in time_starts.items()}
    
    return unixtimestamps

def initial_calc_ohlc(mydb, tablename, pair, interval, interval_base):
    timezone = pytz.timezone("UTC")
    cursor = mydb.cursor()

    cursor.execute("SELECT * from " + tablename + " \
        where unix = (Select min(unix) from " + tablename + " where interval = " + str(interval_base) + " and symbol = '" + pair + "' ) \
        and interval = "+str(interval_base)+" and symbol = '" + pair + "';")
    res_cur = list(cursor.fetchone())
    start = res_cur[1] - res_cur[1] % interval
    print(f'Ealiest { pair } @ { interval_base } is at { start } ({ res_cur[2]}).')
    grplimit = int(interval / interval_base) 
    if res_cur[1] > start:
        start += interval
    cursor.execute("SELECT unix, date, open, high, low, close, volume, volume_base from " + tablename + " \
        where unix >= " + str(start) + " and interval = "+str(interval_base)+" and symbol = '" + pair + f"' order by unix asc limit { grplimit + 1};")

    print(f'Starting { pair } @ { interval_base } is at { start }.')
    res_all= list(cursor.fetchall())
    count = 0
    for item in res_all:
        if count == 0:
            ts = item[0]
            tsdate = item[1]
            popen = item[2]
            phigh = item[3]
            plow = item[4]
            pclose = item[5]
            pvolume = item[6]
            pvolbase = item[7]
            pass
        else:
            if item[3] > phigh:
                phigh = item[3]
            if item[4] < plow:
                plow = item[4]
            pvolume += item[6]
            pvolbase += item[7]
        count += 1
        # print(item)
        if count == grplimit:
            pclose = item[5]
            sqlstatement = 'INSERT INTO ' + tablename + '(unix, date, symbol, open, high, low, close, volume, volume_base, market_id, interval) ' 
            sqlstatement += 'VALUES(' + \
            f'{ts}, \'{tsdate}\', \'{pair}\', {popen}, {phigh}, {plow}, {pclose}, {pvolume}, {pvolbase}, 1, {interval})'
            print(sqlstatement)
            cursor.execute(sqlstatement)
            count = 0
            ts = 0
        
    if ts != 0:
        sqlstatement = 'INSERT INTO ' + tablename + '(unix, date, symbol, open, high, low, close, volume, volume_base, market_id, interval) ' 
        sqlstatement += 'VALUES(' + \
        f'{ts}, \'{tsdate}\', \'{pair}\', {popen}, {phigh}, {plow}, {pclose}, {pvolume}, {pvolbase}, 1, {interval})'
        print(sqlstatement)
        cursor.execute(sqlstatement)
    
    mydb.commit()
    cursor.close()

def update_calc_ohlc(mydb, tablename, pair, interval, interval_base):
    timezone = pytz.timezone("UTC")
    cursor = mydb.cursor()

    # Find the latest record in DB and calculate number of records to fetch
    cursor.execute("SELECT * from " + tablename + " \
        where unix = (Select max(unix) from " + tablename + " where interval = " + str(interval) + " and symbol = '" + pair + "' ) \
        and interval = "+str(interval)+" and symbol = '" + pair + "';")
    res_cur = list(cursor.fetchone())
    start = res_cur[1] - res_cur[1] % interval
    print(f'Latest { pair } @ { interval } is at { start } ({ res_cur[2]}).')
    end = int(time.time())
    grplimit = int(interval / interval_base) 
    cursor.execute("SELECT unix, date, open, high, low, close, volume, volume_base from " + tablename + " \
        where unix >= " + str(start) + " and interval = "+str(interval_base)+" and symbol = '" + pair + "' order by unix asc;")

    res_all= list(cursor.fetchall())
    count = 0
    for item in res_all:
        if count == 0:
            ts = item[0]
            tsdate = item[1]
            popen = item[2]
            phigh = item[3]
            plow = item[4]
            pclose = item[5]
            pvolume = item[6]
            pvolbase = item[7]
            pass
        else:
            if item[3] > phigh:
                phigh = item[3]
            if item[4] < plow:
                plow = item[4]
            pvolume += item[6]
            pvolbase += item[7]
        count += 1
        # print(item)
        if count == grplimit:
            pclose = item[5]
            if ts == start:     # have grplimit of interval_base and have existing interval
                print(f"Update {pair}@{interval} at {start} - {tsdate}")
        #         # print(f"Update {pair}@{interval}: {rec}")
                sqlstatement = 'UPDATE ' + tablename + f' SET open = {popen}, high = {phigh}, low = {plow}, close = {pclose}, volume = {pvolume}, volume_base = {pvolbase}' + \
                f' WHERE unix = {start} AND symbol = \'{pair}\' AND interval = {interval};'
                print(sqlstatement)
            else:               # have grplimit of interval_base and need to insert new interval
                sqlstatement = 'INSERT INTO ' + tablename + '(unix, date, symbol, open, high, low, close, volume, volume_base, market_id, interval) ' 
                sqlstatement += 'VALUES(' + \
                f'{ts}, \'{tsdate}\', \'{pair}\', {popen}, {phigh}, {plow}, {pclose}, {pvolume}, {pvolbase}, 1, {interval})'
                # print(sqlstatement)
            cursor.execute(sqlstatement)
            count = 0
            ts = 0

    if ts != 0:    
        if ts != start:     # less than grplimit of interval_base and need to insert new intereval
            sqlstatement = 'INSERT INTO ' + tablename + '(unix, date, symbol, open, high, low, close, volume, volume_base, market_id, interval) ' 
            sqlstatement += 'VALUES(' + \
            f'{ts}, \'{tsdate}\', \'{pair}\', {popen}, {phigh}, {plow}, {pclose}, {pvolume}, {pvolbase}, 1, {interval})'
        else:               # less than grplimit of interval_base and have existing interval
            sqlstatement = 'UPDATE ' + tablename + f' SET open = {popen}, high = {phigh}, low = {plow}, close = {pclose}, volume = {pvolume}, volume_base = {pvolbase}' + \
            f' WHERE unix = {start} AND symbol = \'{pair}\' AND interval = {interval};'
        print(sqlstatement)
        cursor.execute(sqlstatement)

    mydb.commit()
    cursor.close()

def update_ohlc(mydb, tablename, pair, interval):
    timezone = pytz.timezone("UTC")
    cursor = mydb.cursor()

    # Find the latest record in DB and calculate number of records to fetch
    cursor.execute("SELECT * from " + tablename + " \
        where unix = (Select max(unix) from " + tablename + " where interval = " + str(interval) + " and symbol = '" + pair + "' ) \
        and interval = "+str(interval)+" and symbol = '" + pair + "';")
    res_cur = list(cursor.fetchone())
    start = res_cur[1]
    end = int(time.time())
    limit = int(( end - start ) / interval ) + 1
    limit = 1000  if (limit > 1000) else limit
    symboluri = pair.lower().replace('/','')
    print(f'Latest { pair } @ { interval } is at { start } ({ res_cur[2]}).')

    # Fetch data from bitstamp and insert into DB
    ohlc_base = "https://www.bitstamp.net/api/v2/ohlc/"
    ohlc_url = f"{ ohlc_base }{ symboluri }?start={ start }&step={ interval }&limit={ limit }"
    # print(ohlc_url)
    resp = requests.get(ohlc_url)
    if resp.status_code == 200:
        for rec in resp.json()['data']['ohlc']:
            ts = int(float(rec['timestamp']))
            rec['timestamp']=ts
            rec['tsdate']= timezone.localize(datetime.datetime.utcfromtimestamp(ts))
            if ts == start:
                print(f"Update {pair}@{interval} at {start} - {rec['tsdate']}")
                # print(f"Update {pair}@{interval}: {rec}")
                sqlstatement = 'UPDATE ' + tablename + f' SET open = {rec["open"]}, high = {rec["high"]}, low = {rec["low"]}, close = {rec["close"]}, volume = {rec["volume"]}' + \
                    f' WHERE unix = {start} AND symbol = \'{pair}\' AND interval = {interval};'
            else:
                print(f"Insert {pair}@{interval}: {rec}")
                sqlstatement = 'INSERT INTO ' + tablename + '(unix, date, symbol, open, high, low, close, volume, volume_base, market_id, interval) ' 
                sqlstatement += 'VALUES(' + \
                f'{rec["timestamp"]}, \'{rec["tsdate"]}\', \'{pair}\', {rec["open"]}, {rec["high"]}, {rec["low"]}, {rec["close"]}, {rec["volume"]}, 0, 1, {interval})'
            # print(sqlstatement)
            cursor.execute(sqlstatement)

    mydb.commit()
    cursor.close()

def my_cron_job():
    try:
        # mydb = sqlite3.connect('sqlite/vanilla.db')
        mydb = psycopg2.connect(
            database="vanilla", user='postgres', password='2022pass', host='postgres', port= '5432'
        )
    except psycopg2.Error as error:
        print("Error while connecting utils.py to PostgreSQL:", error)
        pass
    else:
        print(f"Cronjob: {time.mktime(datetime.datetime.now().timetuple())} ({datetime.datetime.now()})")
        update_ohlc(mydb, 'qt_ohlc', 'BTC/USD', 86400)
        update_ohlc(mydb, 'qt_ohlc', 'ETH/USD', 86400)
        update_ohlc(mydb, 'qt_ohlc', 'ETH/BTC', 86400)
        update_ohlc(mydb, 'qt_ohlc', 'LTC/USD', 86400)
        update_ohlc(mydb, 'qt_ohlc', 'LTC/BTC', 86400)
        update_ohlc(mydb, 'qt_ohlc', 'XRP/USD', 86400)
        update_ohlc(mydb, 'qt_ohlc', 'XRP/BTC', 86400)
        update_ohlc(mydb, 'qt_ohlc', 'BTC/USD', 3600)
        update_ohlc(mydb, 'qt_ohlc', 'ETH/USD', 3600)
        update_ohlc(mydb, 'qt_ohlc', 'ETH/BTC', 3600)
        update_ohlc(mydb, 'qt_ohlc', 'LTC/USD', 3600)
        update_ohlc(mydb, 'qt_ohlc', 'LTC/BTC', 3600)
        update_ohlc(mydb, 'qt_ohlc', 'XRP/USD', 3600)
        update_ohlc(mydb, 'qt_ohlc', 'XRP/BTC', 3600)
        # initial_calc_ohlc(mydb, 'qt_ohlc', 'BTC/USD', 14400, 3600)
        update_calc_ohlc(mydb, 'qt_ohlc', 'BTC/USD', 14400, 3600)
        # initial_calc_ohlc(mydb, 'qt_ohlc', 'BTC/USD', 604800, 86400)
        update_calc_ohlc(mydb, 'qt_ohlc', 'BTC/USD', 604800, 86400)
        asyncio.run(send_command_to_go(f"upd_all_indicators | cronjob updated @ {datetime.datetime.now()}\n"))
        asyncio.run(send_command_to_bot(f"Bot: cronjob @ {datetime.datetime.now()}\n"))
        print(f"Cronjob: Completed. {datetime.datetime.now()}\n")

def send_ws_data(r, tick_data):
    channel_layer = channels.layers.get_channel_layer()
    grp_name= "ticker_price"
    # sending data to vanilla websocket channel
    pair = tick_data["pair"]
    message = json.dumps({
        "data": tick_data, 
        "channel":"timer_tick_"+pair.lower().replace('/',''), 
        "event":"timer",
    })
    async_to_sync(channel_layer.group_send)(
        grp_name, {
        "type": 'timer_ticks',
        "content": message,
    })
    pair += "_Price"
    if not (r == True):       # redis connected
        min_logger.info(f"redis connected log for timer hmset: {pair}")
        # print(f"redis connected for timer hmset: {pair}")
        r.hmset(pair, {"price": tick_data["last"], "timestamp": tick_data["timestamp"], "source": "timer"})

def min_cron_job():
    min_logger.info(f"Cron Min: Started. {datetime.datetime.now()}\n")
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
        if not r.ping():
            r = True    # not connected
            print("Connection to Redis failed.")
    except redis.ConnectionError as e:
        r = True        # not connected
        print(f"Connection error: {e}")
    ticker_base = "https://www.bitstamp.net/api/v2/ticker/"
    resp = requests.get(ticker_base)
    if resp.status_code == 200:
        respdata = resp.json()
        send_ws_data(r, respdata[7])       # xrp/usd  
        send_ws_data(r, respdata[9])       # xrp/btc
        send_ws_data(r, respdata[12])      # ltc/usd
        send_ws_data(r, respdata[11])      # ltc/btc
        send_ws_data(r, respdata[16])      # eth/usd
        send_ws_data(r, respdata[15])      # eth/btc
        send_ws_data(r, respdata[0])       # btc/usd
    # send_command_to_bot(f"hello - {datetime.datetime.now()}")
    # send_command_to_go(f"hello - {datetime.datetime.now()}")
    print(f"Cron Min: Completed. {datetime.datetime.now()}\n")


if __name__ == '__main__':
    min_cron_job()
