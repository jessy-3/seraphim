'''
This program is to locd OHLC data from yahoo downloaded csv
'''
import pandas as pd
import time
import datetime
from sqlalchemy import create_engine

#engine = sqlite3.connect('db.sqlite3')
#engine = create_engine('mysql://root:2022pass@localhost/vanilla') # enter your password and database names here
engine = create_engine('postgresql://postgres:2022pass@localhost/vanilla')

df = pd.read_csv("/Users/jessy/Downloads/DOGE-USD.csv",sep=',',quotechar='\'',encoding='utf8')
df.rename(columns={"Date" : "date" }, inplace=True)
df['date']=pd.to_datetime(df['date'], utc=True)
#df.rename(columns={"Volume USD" : "volume_base" }, inplace=True)
df.rename(columns={"Volume" : "volume" }, inplace=True)
df.rename(columns={"Open" : "open" }, inplace=True)
df.rename(columns={"High" : "high" }, inplace=True)
df.rename(columns={"Low" : "low" }, inplace=True)
df.rename(columns={"Close" : "close" }, inplace=True)

df.insert(1,"symbol","DOGE/USD")
df.drop("Adj Close", axis='columns', inplace=True)
df.insert(0,"unix",0)
df.insert(8,"volume_base",0)
df.insert(9,"interval",86400)
for x in df.index:
    df.loc[x, "unix"] = time.mktime((df.loc[x, "date"]-datetime.timedelta(hours=5)).timetuple())

df.to_sql('qt_ohlc',con=engine,index=False,if_exists='append') 
