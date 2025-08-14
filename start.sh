#!/bin/bash
. /home/site/wwwroot/antenv/bin/activate
export PYTHONPATH=$PYTHONPATH:/home/site/wwwroot
gunicorn agent.teams_bot:create_app