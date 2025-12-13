import discord
from discord.ext import tasks
from free_games import get_new_free_games, get_steam_game_description, get_steam_game_image
import os
import logging
import json
import shutil
from time import sleep
import datetime
import pytz
import asyncio
from datetime import timedelta
import traceback

log_filename="free_games_bot.log"
if(os.path.isfile(log_filename)):
    shutil.copy(log_filename,f"old_{log_filename}")
logging.basicConfig(filename=log_filename,filemode="w",format="%(asctime)s %(levelname)s: %(message)s",level=logging.DEBUG)

logging.info("loading config")
try:
    with open("config.json","r") as f:
        config = json.load(f)
except OSError:
    json.dump({
        "discord_token":"your_token_here",
        "discord_channel_id": "your_channel_id_here"
    },open("config.json","w"),indent=4)
    logging.critical("failed to load config, created config.json, please edit it and restart")
    SystemExit(1)

TOKEN = config["discord_token"]
CHANNEL_ID = int(config["discord_channel_id"])
CHANNEL = None


intents = discord.Intents.default()
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    global CHANNEL
    logging.info("bot is ready")
    logging.info(f"Current time: {datetime.datetime.now(pytz.timezone('Europe/Berlin'))}")
    CHANNEL = client.get_channel(CHANNEL_ID)
    if CHANNEL is None:
        logging.critical(f"failed to get channel with id {CHANNEL_ID}, check your config")
        SystemExit(2)
    logging.info(f"Using channel {CHANNEL.name} with id {CHANNEL.id} for updates")
    await check_for_games()
    wait_for_loop_start_task = asyncio.create_task(wait_for_loop_start())
    await wait_for_loop_start_task
    

async def wait_for_loop_start():
    tz = pytz.timezone('Europe/Berlin')
    now = datetime.datetime.now(tz)
    target = now.replace(hour=19, minute=30, second=0, microsecond=0)
    if target <= now:
        target = target + timedelta(days=1)
    wait_seconds = (target - now).total_seconds()
    logging.info(f"sleeping for {wait_seconds} seconds until {target}")
    await asyncio.sleep(wait_seconds)
    await check_for_games.start()


@tasks.loop(hours=24)
async def check_for_games():
    await client.wait_until_ready()
    try:
        logging.info("checking for new free games")
        new_games = get_new_free_games()
        if new_games:
            logging.info(f"found {len(new_games)} new free games, sending messages")
            for title, link, platform in new_games:
                if platform == "steam":
                    message = f"{link}"
                    embed = discord.Embed(title=title, url=link, description=get_steam_game_description(link))
                    embed.set_author(name="Steam",url="https://store.steampowered.com")
                    embed.set_image(url=get_steam_game_image(link))
                    try:
                        await CHANNEL.send(content=message,embed=embed,suppress_embeds=False)
                        logging.info(f"sent message for {title}")
                    except Exception as e:
                        logging.error(f"failed to send message for {title}: {e}")
                await asyncio.sleep(1)  # avoid hitting rate limits
        else:
            logging.info("no new free games found")
    except Exception as e:
        logging.error(f"error while checking for new free games: {e}")
        for line in traceback.format_exception(e):
            logging.error(line)



client.run(TOKEN)