import discord
from discord.ext import commands, tasks
import subprocess
import configparser
import re
import aiohttp
import json
import requests
from pathlib import Path
import datetime
import zipfile
import os
import shutil

cache = {}
allowlist = []
config = configparser.ConfigParser()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

hostname = ""
password = ""
rcon_command = []

@bot.event
async def on_ready():
    print(f"We have logged in to Discord as {bot.user}")
    player_scanner.start()

@tasks.loop(seconds=10)
async def player_scanner():
    matches = await get_players()
    await kick_unwanted(matches)
    player_count = len(matches)
    await bot.change_presence(activity=discord.Game(name=f"{player_count}/32 players"))

# TODO WIP add backup functionality
# @tasks.loop(minutes=5)
# async def backup_saves():
#   await perform_rcon_command("Save")
#   # Zip the save folder into a file with a date and time stamp in the name
#   zip_folder_name = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
#   backup_path = f"{config['palworld']['backup_path']}/{zip_folder_name}.zip"
#   print(backup_path)
#   subprocess.run(["zip", "-r", backup_path, config["palworld"]["save_path"]])
#   # The path of the folder is config["palworld"]["save_path"]


async def get_players():
  result = await perform_rcon_command("ShowPlayers")
  regex = r"([\w ]+),(\d+),(\d+)"
  matches = re.findall(regex, result)
  return matches

async def kick_unwanted(matches):
  for match in matches:
    if not str(match[2]) in allowlist:
      await perform_rcon_command(f"KickPlayer {match[2]}")
      await send_discord_message(f"\n{match[0]} {match[2]} kicked, not on the allowlist")

async def send_discord_message(message):
  guild = bot.get_guild(int(config['discord']['guild']))
  channel = guild.get_channel(int(config['discord']['channel']))
  announce_to = channel

  if config['discord']['thread']:
    thread = channel.get_thread(int(config['discord']['thread']))
    announce_to = thread
  
  await announce_to.send(message)

def cache_write():
  with open("cache.json", "w") as raw_write:
    json.dump(cache, raw_write)

async def fetch_steam_username(steam_id):
  async with aiohttp.ClientSession() as session:
    url = f"https://steamid.co/php/api.php?action=steamID64&id={steam_id}"
    async with session.get(url) as response:
      if response.status == 200:
        data = await response.text()
        return json.loads(data)

async def perform_rcon_command(command):
  process = subprocess.Popen(rcon_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  process.stdin.write(f"{command}\n".encode("utf-8"))
  process.stdin.write(b":q\n")
  process.stdin.close()
  output = process.stdout.read()
  return output.decode("utf-8")

@bot.hybrid_command(name="players", description="Show current players")
async def show_players(context: commands.Context):
  matches = await get_players()
  if len(matches) == 0:
    await context.send("No players online")
    return

  longest_name = max(len(match[0]) for match in matches)
  players = [f"Steam ID          {'Ingame Name'.ljust(longest_name)} Steam Username", ""]
  for match in matches:
    formatted_name = match[0].ljust(longest_name)
    if not str(match[2]) in cache:
      steam_payload = await fetch_steam_username(match[2])
      print(f'added cache for {match[2]}')
      cache[match[2]] = steam_payload
      cache_write()
    players.append(f"{match[2]} {formatted_name} {cache[match[2]]['steamID']}")
  await context.send(f"```c\n{'\n'.join(players)}```")

@bot.hybrid_command(name="kick", description="Kick a player")
async def kick_player(context: commands.Context, steamid: str):
  if context.channel.permissions_for(context.author).kick_members:
    result = perform_rcon_command(f"KickPlayer {steamid}")
    await context.send(f"```c\n{result}```")

@bot.hybrid_command(name="ban", description="Ban a player")
async def ban_player(context: commands.Context, steamid: str):
  if context.channel.permissions_for(context.author).ban_members:
    result = perform_rcon_command(f"BanPlayer {steamid}")
    await context.send(f"```c\n{result}```")

@bot.hybrid_command(name="allow", description="Allow a player to join")
async def allow_player(context: commands.Context, steamid: str):
  if context.channel.permissions_for(context.author).kick_members:
    if not steamid in allowlist:
      allowlist.append(steamid)
      with open("allowlist.json", "w") as raw_write:
        json.dump(allowlist, raw_write)
      await context.send(f"{steamid} added to allowlist")
    else:
      await context.send(f"{steamid} already in allowlist")

@bot.hybrid_command(name="disallow", description="Disallow a player to join")
async def disallow_player(context: commands.Context, steamid: str):
  if context.channel.permissions_for(context.author).kick_members:
    if steamid in allowlist:
      allowlist.remove(steamid)
      with open("allowlist.json", "w") as raw_write:
        json.dump(allowlist, raw_write)
      await context.send(f"{steamid} removed from allowlist")
    else:
      await context.send(f"{steamid} not in allowlist")

@bot.hybrid_command(name="allowlist", description="Show allowed players")
async def show_allowlist(context: commands.Context):
  steamids = []
  for allowed in allowlist:
    if str(allowed) in cache:
      steamids.append(f"{allowed} {cache[str(allowed)]["steamID"]}")
    else:
      steamids.append(f"{allowed} Unknown User")
  await context.send(f"```c\n{'\n'.join(steamids)}```")

@bot.hybrid_command(name="shutdown", description="Shutdown the server")
async def shutdown_server(context: commands.Context, seconds: str, *, reason: str):
  if context.channel.permissions_for(context.author).ban_members:
    # await send_discord_message(f"Shutdown seconds: {seconds} reason: {reason}")
    result = await perform_rcon_command(f"Shutdown {seconds} {reason}")
    await context.send(f"```c\n{result}```")

# TODO Presently broken, awaiting Palworld devs
# @bot.hybrid_command(name="broadcast", description="Send a server announcement")
# async def broadcast_message(context: commands.Context, *, message: str):
#   if context.channel.permissions_for(context.author).kick_members:
#     # await send_discord_message(f"Broadcast {message}")
#     result = await perform_rcon_command(f"Broadcast {message}")
#     await context.send(f"```c\n{result}```")

@bot.hybrid_command(name="save", description="Save the server")
async def save(context: commands.Context):
    # await send_discord_message(f"Broadcast {message}")
    result = await perform_rcon_command(f"Save")
    await context.send(f"```c\n{result}```")

if __name__ == "__main__":
  if not Path('config.ini').is_file():
    print("config.ini not found, please copy config.example.ini to config.ini and fill in the values.")
    exit()

  config.read("config.ini")

  rcon_path = Path('rcon')
  if not rcon_path.is_dir():
    rcon_path.mkdir()
    print("rcon folder not found, downloading gorcon/rcon-cli from GitHub. Assuming Win64 and downloading latest release.")
    github_api_results = requests.get("https://api.github.com/repos/gorcon/rcon-cli/releases/latest")
    github_api_json = github_api_results.json()
    github_api_assets = github_api_json["assets"]
    for asset in github_api_assets:
      if asset["name"].endswith("win64.zip"):
        rcon_download_url = asset["browser_download_url"]
        rcon_download = requests.get(rcon_download_url)
        with open(asset["name"], "wb") as rcon_file:
          rcon_file.write(rcon_download.content)
        with zipfile.ZipFile(asset["name"]) as zip_file:
          for member in zip_file.namelist():
            filename = os.path.basename(member)
            if not filename:
              continue

            source = zip_file.open(member)
            target = open(os.path.join("rcon", filename), "wb")
            with source, target:
              shutil.copyfileobj(source, target)
          break

  backup_dir = Path(config['palworld']['backup_path'])
  if not backup_dir.is_dir() and not backup_dir.exists():
    backup_dir.mkdir()
  elif not backup_dir.is_dir():
    print("backup_path is not a directory, please check the path in config.ini")
    exit()

  if not Path('cache.json').is_file():
    print("cache.json not found, creating empty cache.")
    with open("cache.json", "w") as raw_write:
      json.dump({}, raw_write)

  with open("cache.json", "r") as raw_read:
    cache = json.load(raw_read)

  if not Path('allowlist.json').is_file():
    print("allowlist.json not found, creating empty allowlist.")
    with open("allowlist.json", "w") as raw_write:
      json.dump([], raw_write)

  with open("allowlist.json", "r") as raw_read:
    allowlist = json.load(raw_read)

  hostname = f"{config["palworld"]["hostname"]}:{config["palworld"]["port"]}"
  password = config["palworld"]["password"]
  rcon_command = [config["palworld"]["rcon_path"], "-a", f"{hostname}", "-p", f"{password}"]

  bot.run(config['discord']['token']) 