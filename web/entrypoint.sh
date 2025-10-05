#!/bin/bash

echo "🚀 Starting Seraphim Trading System..."

# Wait for PostgreSQL
echo "⏳ Waiting for postgres..."
while ! nc -z postgres 5432; do
    sleep 0.1
done
echo "✅ PostgreSQL connected"

# Wait for Redis  
echo "⏳ Waiting for redis..."
while ! nc -z redis 6379; do
    sleep 0.1
done
echo "✅ Redis connected"

# Run Django migrations
echo "🔄 Running database migrations..."
python manage.py migrate --no-input

# Start cron service (for existing cron jobs)
service cron start
python manage.py crontab add

# Start the listen_for_commands function in the background (legacy)
# TODO: Migrate to Celery tasks
python run_listener.py &

# Start the server
if [ "$DJANGO_ENV" = "development" ]; then
    echo "🔧 Starting Django development server..."
    python manage.py runserver 0.0.0.0:8082
else
    echo "🚀 Starting Uvicorn ASGI server..."
    # Fallback to Daphne if Uvicorn not available yet
    if command -v uvicorn &> /dev/null; then
            uvicorn seraphim.asgi:application --host 0.0.0.0 --port 8082 --workers 2
    else
        echo "📡 Using Daphne as fallback..."
            daphne seraphim.asgi:application -b 0.0.0.0 -p 8082 --proxy-headers
    fi
fi
