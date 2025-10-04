# Original version of loading ohlc data. Kept for reference only.

import csv
import MySQLdb

#import pymysql
#db = pymysql.connect("localhost","root","12345678","data" )

mydb = MySQLdb.connect(host='localhost',
    user='root',
    passwd='2022pass',
    db='vanilla')
cursor = mydb.cursor()

csv_data = csv.reader(file('Bitstamp_BTCUSD_d.csv'))
#csv_data = csv.reader(open('test.csv'))
#next(csv_data)

for row in csv_data:
    cursor.execute('INSERT INTO price_btc(unix, date, \
        symbol, open, high, low, close, volume, volume_base, interval)' \
    'VALUES( %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
    row)
#    cursor.execute('INSERT INTO PM(col1,col2) VALUES(%s, %s)',row)

#close the connection to the database.
mydb.commit()
cursor.close()
print("Done")
