#!/bin/bash
service cron start
python manage.py crontab add

# Start the listen_for_commands function in the background
python run_listener.py &

# Start the Daphne server
daphne vanilla.asgi:application -b 0.0.0.0 -p 8082 --proxy-headers
