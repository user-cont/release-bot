#!/usr/bin/bash

export RELEASE_BOT_HOME=/home/release-bot

exec release-bot -c /home/release-bot/.config/conf.yaml &
exec celery -A release_bot.celery_task worker -l info
