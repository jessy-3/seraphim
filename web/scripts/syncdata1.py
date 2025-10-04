'''
This program is to update OHLC data from bitstamp
'''

import requests
import psycopg2
import datetime, time, pytz, math, logging

#from unixtimestampfield.fields import UnixTimeStampField

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
    if end - start < interval:
        cursor.close()
        return
    
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
            database="vanilla", user='postgres', password='2022pass', host='localhost', port= '5432'
        )
    except psycopg2.Error as error:
        print("Error while connecting utils.py to PostgreSQL:", error)
        pass
    else:
        print(f"Cronjob: {time.mktime(datetime.datetime.now().timetuple())} ({datetime.datetime.now()})")
        # update_ohlc(mydb, 'qt_ohlc', 'BTC/USD', 86400)
        # update_ohlc(mydb, 'qt_ohlc', 'ETH/USD', 86400)
        # update_ohlc(mydb, 'qt_ohlc', 'ETH/BTC', 86400)
        # update_ohlc(mydb, 'qt_ohlc', 'LTC/USD', 86400)
        # update_ohlc(mydb, 'qt_ohlc', 'LTC/BTC', 86400)
        # update_ohlc(mydb, 'qt_ohlc', 'XRP/USD', 86400)
        # update_ohlc(mydb, 'qt_ohlc', 'XRP/BTC', 86400)
        # update_ohlc(mydb, 'qt_ohlc', 'BTC/USD', 3600)
        # update_ohlc(mydb, 'qt_ohlc', 'ETH/USD', 3600)
        # update_ohlc(mydb, 'qt_ohlc', 'ETH/BTC', 3600)
        # update_ohlc(mydb, 'qt_ohlc', 'LTC/USD', 3600)
        # update_ohlc(mydb, 'qt_ohlc', 'LTC/BTC', 3600)
        # update_ohlc(mydb, 'qt_ohlc', 'XRP/USD', 3600)
        # update_ohlc(mydb, 'qt_ohlc', 'XRP/BTC', 3600)
        # initial_calc_ohlc(mydb, 'qt_ohlc', 'BTC/USD', 14400, 3600)
        # update_calc_ohlc(mydb, 'qt_ohlc', 'BTC/USD', 14400, 3600)
        initial_calc_ohlc(mydb, 'qt_ohlc', 'BTC/USD', 604800, 86400)
        update_calc_ohlc(mydb, 'qt_ohlc', 'BTC/USD', 604800, 86400)
        print(f"Cronjob: Completed. {datetime.datetime.now()}\n")

if __name__ == '__main__':
    my_cron_job()
