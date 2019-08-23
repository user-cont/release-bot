#!/usr/bin/bash

printf "release-bot:x:$(id -u):0:Release bot:/home/release-bot:/bin/bash\n" >> /home/release-bot/passwd

export RELEASE_BOT_HOME=/home/release-bot

exec release-bot -c /home/release-bot/.config/conf.yaml &
exec celery -A release_bot.celery_task worker -l info
