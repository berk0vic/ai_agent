#!/bin/bash
export PYTHONPATH=$PYTHONPATH:/home/site/wwwroot
gunicorn agent.teams_bot:create_app