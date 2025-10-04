venv/bin/uwsgi --gevent 50 --socket 127.0.0.1:9022 --chdir /data/www/vanilla/vanilla --wsgi-file vanilla/wsgi.py --master --processes 2 --threads 1
