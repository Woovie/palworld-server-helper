import discord
from discord.ext import commands, tasks
import subprocess
import configparser
import re
import aiohttp
import json

cache = {}
allowlist = []

with open("cache.json", "r") as raw_read:
  cache = json.load(raw_read)

with open("allowlist.json", "r") as raw_read:
  allowlist = json.load(raw_read)

config = configparser.ConfigParser()
config.read("config.ini")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

hostname = f"{config["palworld"]["hostname"]}:{config["palworld"]["port"]}"
password = config["palworld"]["password"]
rcon_command = ["/usr/local/bin/rcon", "-a", f"{hostname}", "-p", f"{password}"]

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")
    player_scanner.start()

@tasks.loop(seconds=10)
async def player_scanner():
    matches = await get_players()
    await kick_unwanted(matches)
    player_count = len(matches)
    await bot.change_presence(activity=discord.Game(name=f"{player_count}/32 players"))

async def get_players():
  result = await perform_rcon_command("ShowPlayers")
  regex = r"([\w ]+),(\d+),(\d+)"
  matches = re.findall(regex, result)
  return matches

async def kick_unwanted(matches):
  for match in matches:
    if not str(match[2]) in allowlist:
      await perform_rcon_command(f"KickPlayer {match[2]}")
      guild = bot.get_guild(105420838487990272)
      channel = guild.get_channel(1019639566765936650)
      thread = channel.get_thread(1197370734096429116)
      await thread.send(f"\n{match[0]} {match[2]} kicked, not on the whitelist")


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

@bot.hybrid_command(name="allowlist", description="Show allowlist")
async def show_allowlist(context: commands.Context):
  steamids = []
  for allowed in allowlist:
    if str(allowed) in cache:
      steamids.append(f"{allowed} {cache[str(allowed)]["steamID"]}")
    else:
      steamids.append(f"{allowed} Unknown User")
  await context.send(f"```c\n{'\n'.join(steamids)}```")



bot.run(config['discord']['token'])
