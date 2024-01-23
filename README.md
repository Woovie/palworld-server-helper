# Palworld Discord Bot

## Features


- Custom allowlist solution using rcon to read the player list and compare Steam IDs to the allowed list.
- Execute some RCON commands from Discord.

## Expectations

You have some Python experience, Linux experience, and Discord bot experience. I simply do not have the time to help everyone, I'm sorry.

## How to use

### Prerequisites

Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) and ensure you check the "Desktop development with C++"

![image](https://github.com/Woovie/palworld-server-helper/assets/7304619/5da3a18b-7080-4892-97f9-19eeeb183886)

- Have some form of Python 3.10+ installed (Maybe even 3.12? Not sure how backward compatible my code is honestly, but I used 3.12)
- Copy config.example.ini to config.ini and edit as needed
- Install dependencies from requirements.txt using `pip install -r requirements.txt`
- Run with `python bot.py`

Once running, the default command prefix is ! and the following commands exist:

- players
- kick (Needs Discord kick privileges)
- ban (Needs Discord ban privileges)
- allow (Needs Discord kick privileges)
- disallow (Needs Discord kick privileges)
- allowlist
- shutdown (Needs Discord ban privileges)
- save

Each should be relatively straighforward.

## Configuration help

Example configuration in config.example.ini

### palworld

#### Implemented

- **hostname**: The IP to your server
- **port**: RCON port, default is 25575
- **password**: The administrator password
- **rcon_path**: A path to your RCON binary, expecting and hardcoded for https://github.com/gorcon/rcon-cli right now, might use a library later

#### Still WIP

- **save_path**: A directory to where the save files are located
- **backup_path**: A directory to where a zipped backup will be stored

### discord

- **token**: Your Discord bot's token

These are specific to the announcements of "<SteamID> kicked, not on the allowlist" messages as they do not have a context prior:

- **guild**: Guild ID
- **channel**: Channel ID
- **thread**: Thread ID

## I still need help

Join here and I might be able to help more should time allow: https://discord.gg/ccyGETpetwf
