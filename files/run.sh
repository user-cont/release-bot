#!/usr/bin/bash

printf "release-bot:x:$(id -u):0:Release bot:/home/release-bot:/bin/bash\n" >>/home/release-bot/passwd

export RELEASE_BOT_HOME=/home/release-bot

exec release-bot -c /secrets/prod/conf.yaml
