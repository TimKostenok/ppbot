# ppbot

The bot for true priorities, that can make your life easier. To try - [@priority_helper_bot](https://t.me/priority_helper_bot) in Telegram.

# Install and run

***!!** You need python and pip installed.*

First get this repo onto your local computer.

## Install and run without docker

Then install requirements: `python3 -m pip install requirements.txt`.

And type `python main.py` to run the bot.

## Install and run with docker

***!!** You need docker installed.*

First build an image: `docker build -t ppbot-image /path/to/folder/where/Dockerfile/is`, so if you are in directory where **Dockerfile is located**, you can just do `docker build -t ppbot-image .`

Then run the image as container: `docker run ppbot-image --name ppbot-container` or run it in the **detached mode**: `docker run -d ppbot-image --name ppbot-container`.

So now if you run `docker ps -a` you can see your container running.

To stop it use `docker stop ppbot-container` and to restart a stopped container use `docker start ppbot-container`.

To remove the **stopped** container use `docker rm ppbot-container` or you can remove the **running** container by force remove: `docker rm -f ppbot-container`.

## Architecture

- **main.py** -- the main file of the bot.
- **config.py** -- file that contains the bot's settings.
- **users.txt** -- file with info about users'.
- **admins.txt** -- file with list of admins.
- **requirements.txt** -- file with requirements for the bot.
- **Dockerfile** -- file that uses for running bot using docker.

### I hope if you look carefully, you will find how this bad code works)

# That's all. Thanks!
