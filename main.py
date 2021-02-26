import asyncio
import platform
import dataclasses
import pathlib
import json
import re

import discord
import appdirs
if platform.system() == "OpenBSD":
    import openbsd

# todo: add partial paths, fuzzy matching.
# todo: allow single filenames, returns all matching paths.
# todo: consider different data structure for symbols, files.
# One big hashtable with tuples for colliding elements?
# Disparate maps for each type means no collision, searching in all maps is trivial.
# Disperate maps mean elements don't need to carry type information.
# Maps can be iterated over for fuzzy searching and whatnot.

# ==============================================================================
async def process_msg(msg):

    matches = re.findall(r"(?:^|\s)%% ?([\w:\/\.]+)", msg.content)
    if matches != []:
        embed = discord.Embed(color = 0x55FFFF)
        for match in matches:
            if "/" in match:
                # Check against file paths.
                try:
                    normalized = "/" + re.match(r"^(?:[A-Z:]:)?\/(.*?)/?$", match).group(1).lower()
                except AttributeError:
                    embed = embed_append_error(embed, f"Invalid path: {match}`")
                    continue

                path = paths.get(normalized)
                if path is not None:
                    embed = embed_append_path(embed, path)
                else:
                    embed = embed_append_error(embed, f"Path not found: ::{match}")
            else:
                # Check against symbol table.
                symbol = symbols.get(match.lower())
                if symbol is not None:
                    embed = embed_append_symbol(embed, symbol)
                    continue
                else:
                    embed = embed_append_error(embed, f"Symbol not found: {match}")

        await msg.channel.send(embed = embed)


# Embeds =======================================================================
def embed_append_symbol(e: discord.Embed, symbol) -> discord.Embed:
    if "file" not in symbol:
        path_link = "N/A"
    else:
        path = symbol["file"][2:]  # Remove drive letter, ie. "C:"
        if "." in path:
            path = path.split(".")[0] + ".html"
        url = f"https://templeos.holyc.xyz/Wb{path}#l{symbol['line']}"
        path_link = f"[{symbol['file']}, line {symbol['line']}]({url})"

    text = f"Type: {symbol['type']}\nDefinition: {path_link}"

    e.add_field(name=symbol['symbol'], value=text, inline=False)
    return e


def embed_append_path(e: discord.Embed, path) -> discord.Embed:
    file_types = {
        "HC": "HolyC",
        "TXT": "Text",
        "GRA": "Graphics",
        "BMP": "Windows Bitmap",
        "DD": "DolDoc",
        "IN": "Input",
        "BIN": "Binary",
        "CPP": "C++",
    }

    file_name_parts = path.split(".")
    if len(file_name_parts) > 1:
        url_path = file_name_parts[0] + ".html"

        file_type = file_types.get(file_name_parts[1])
        if file_type is None:
            file_type = file_name_parts[1]

        if file_name_parts[-1] == "Z":
            file_type = f"{file_type} (Compressed)"
    
    else:
        url_path = path
        file_type = "Directory"


    url = "https://templeos.holyc.xyz/Wb" + url_path
    text = f"Type: {file_type}\nPath: [::{path}]({url})"

    path_name = path.split("/")[-1] or "/"
    e.add_field(name=path_name, value=text, inline=False)
    return e


def embed_append_error(e: discord.Embed, error_message) -> discord.Embed:
    e.add_field(name="[Error]", value=error_message, inline=False)
    return e


# Client and callbacks =========================================================
client = discord.Client()

@client.event
async def on_ready():
    if platform.system() == "OpenBSD":
        openbsd.pledge("stdio inet dns prot_exec")


@client.event
async def on_message(msg):
    await process_msg(msg)


# ==============================================================================
if __name__ == "__main__":

    # Load token from config. If not available, prompt for token and
    # create config.
    config_dir = pathlib.Path(appdirs.user_config_dir("TTD_bot"))
    config_file = config_dir.joinpath("config.json")

    if config_file.exists():
        with open(config_file, "r") as f:
            config = json.load(f)
    else:
        config = {}
        print("Config doesn't exist. Creating one. [ctrl+c to cancel]")
        config["token"] = input("Bot token: ")
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w+") as f:
            json.dump(config, f)

    with open("symbol.json", "r") as f:
        tos_data = json.load(f)

    # Make map of symbols. Keys are lowercased symbols.
    symbols = {}
    for s in tos_data["symbols"]:
        symbols[s["symbol"].lower()] = s

    # Make map of full paths, for each value, the keys are:
    #   - the lowercased path,
    #   - The lowercased last segment of the path.
    paths = {}
    for p in tos_data["paths"]:
        paths[p.lower()] = p


    client.run(config["token"])

