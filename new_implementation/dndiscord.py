import os
import argparse

from modules.business_simulator.data import business_data_pack
from modules.business_simulator.gui.business_simulator_gui import BusinessSimulatorGUI

# This is a small standalone executable that allows you to either generate a business data pack programmatically or through the GUI
from new_implementation.runtimes.bot_runtime.dndiscord_bot import DNDiscordBot
from new_implementation.data import data


# Parse the runtime arguments
parser = argparse.ArgumentParser()
parser.add_argument("-r", "--runtime", dest="runtime", help="The runtime type of dndiscord. Valid options are: bot, pack_dump, pack_editor", type=str, default="bot", choices=['bot', 'pack_dump', 'pack_editor'])
parser.add_argument("-c", "--config", dest="config", help="The location of the configuration file for the bot", type=str, default="./config.json")
parser.add_argument("-f", "--file", dest="file", help="The location of the python file to load when attempting to dump a programmatically created data pack", type=str)
args = parser.parse_args()

# Runtime as bot
if args.runtime == "bot":

    # Load the configuration file for the bot - this is required!
    if args.config and os.path.isfile(args.config):
        config_data = data.load(args.config)
        if "discord_token" not in config_data:
            print("Invalid configuration file provided.")
            exit(1)

        dnd_bot = DNDiscordBot(config_data)
        dnd_bot.run()

    else:
        print("Please supply a valid configuration file.")

# Dump the default Trollskull manor pack to file
elif args.runtime == "pack_dump":
    if args.file and os.path.isfile(args.file):
        business_data_pack.generate_data_pack_from_python(args.file)
    else:
        print("Please supply a valid python file.")

# Activate the pack editor so you can edit or create data packs
elif args.runtime == "pack_editor":
    business_gui = BusinessSimulatorGUI()
    business_gui.mainloop()
