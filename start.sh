#!/bin/bash
# Sanal ortamı etkinleştir
source /home/site/wwwroot/antenv/bin/activate
# Gunicorn ile uygulamayı başlat
gunicorn teams_bot:create_app