import datetime, time
import math

# Get the current time
now = datetime.datetime.now()

# Get the starting time of the current minute, hour, and day
minute_start = now.replace(second=0, microsecond=0)
hour_start = now.replace(minute=0, second=0, microsecond=0)
day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

# Get the starting time of the current week (assuming Monday is the first day of the week)
week_start = day_start - datetime.timedelta(days=now.weekday())

# Get the starting time of the current month
month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

# Custom intervals
interval_4h_start = now - datetime.timedelta(hours=(now.hour % 4), minutes=now.minute, seconds=now.second, microseconds=now.microsecond)
interval_5m_start = now - datetime.timedelta(minutes=(now.minute % 5), seconds=now.second, microseconds=now.microsecond)
interval_15m_start = now - datetime.timedelta(minutes=(now.minute % 15), seconds=now.second, microseconds=now.microsecond)

# Convert datetime objects to Unix timestamps
minute_start_unix = int(minute_start.timestamp())
hour_start_unix = int(hour_start.timestamp())
day_start_unix = int(day_start.timestamp())
week_start_unix = int(week_start.timestamp())
month_start_unix = int(month_start.timestamp())
interval_4h_start_unix = int(interval_4h_start.timestamp())
interval_5m_start_unix = int(interval_5m_start.timestamp())
interval_15m_start_unix = int(interval_15m_start.timestamp())

print("Now:", time.mktime(datetime.datetime.now().timetuple()))
print("Current minute start:", minute_start_unix)
print("Current hour start:", hour_start_unix)
print("Current day start:", day_start_unix)
print("Current week start:", week_start_unix)
print("Current month start:", month_start_unix)
print("Current 4-hour interval start:", interval_4h_start_unix)
print("Current 5-minute interval start:", interval_5m_start_unix)
print("Current 15-minute interval start:", interval_15m_start_unix)
