import os

import names
from discord.ext import commands

from module_properties import Module
from modules.tavern_simulator.data_packs import default_data_pack
from modules.tavern_simulator.model.new_data_pack import DataPack
from modules.tavern_simulator.tavern_controller import Tavern
from utils import constants
from utils.errors import CommandRunError
from utils.messages import LongMessage
from utils.strings import get_trailing_number

"""
Define a current state view for the tavern
        
    2) Allow the players to determine what is available now
        a) List next services <implement a tier>
        b) List missing prerequisites and options to obtain
        c) Easily identify the costs and people to speak to.
    
    3) Allow players to change the state of the tavern over time via the GM
        a) Contract negotiations
        b) Purchase negotiations
        c) Purchase contributions
        
    4) Show tavern history
    
    5) Simulate a week and show outcomes in a log

# TODO: Centralize keywords / constants
# TODO: Find a way of mapping tag keys and tag values to translation packs. Namely:
    default_language_pack:
        key: "Human readable representation of this key"
        key.value: "Human readable representation of this value of this key" 
TODO: Document
TODO: Game end listener (THIS IS IMPORTANT)
TODO: We could make this a purchaseable module - if so I would need to reevaluate the load checks for data packs
TODO: Employee names
TODO: Employee, Contract, Customer_History, Sales_History need custom data 
"""


class TavernSimulator(Module):
    def __init__(self, manager):
        super().__init__("tavern_simulator", manager)

        self.taverns = dict()
        self.game_master = self.manager.get_module("game_master")
        if self.game_master:
            self.game_master.register_game_state_listener(self)
        else:
            raise RuntimeError("Cannot use the tavern simulator without the Game Master module.")

        # TODO: We should load taverns here

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('`An error occurred: {}`'.format(str(error)))

    async def get_tavern_for_context(self, ctx):
        game = self.game_master.get_active_game_for_context(ctx)
        if game.get_name() in self.taverns:
            return self.taverns[game.get_name()]

        return None

    async def set_tavern_for_context(self, ctx, tavern):
        game = self.game_master.get_active_game_for_context(ctx)
        self.taverns[game.get_name()] = tavern
        await tavern.save(self.game_master, ctx, "tavern")

    async def unload_tavern_for_context(self, ctx, tavern):
        game = self.game_master.get_active_game_for_context(ctx)
        if game.get_name() in self.taverns:
            tavern = self.taverns[game.get_name()]
            await tavern.save(self.game_master, ctx, "tavern")
            del self.taverns[game.get_name()]

    async def game_created(self, ctx, game):
        pass

    async def game_started(self, ctx, game):
        tavern = await Tavern.load_tavern(self.manager, self.game_master, ctx, "tavern")
        if isinstance(tavern, str):
            return await ctx.send(tavern)

        elif tavern:
            await self.set_tavern_for_context(ctx, tavern)
            return await ctx.send("`Loaded a tavern for your game!`")

    async def game_about_to_end(self, ctx, game):
        await self.unload_tavern_for_context(ctx, game)

    async def game_deleted(self, ctx, game):
        # TODO DELETE DATA
        await self.unload_tavern_for_context(ctx, game)

    async def _get_data_pack(self, ctx, pack_name):
        data_pack = None
        data_packs_path = os.path.join(self.name, "data_packs")

        # First check our guild specific dir and our local bot directory
        if pack_name != "" and pack_name != "FORCE":
            await ctx.send("`Attempting to load data pack: " + pack_name + "`")
            data_pack = await DataPack.load_data_pack(self.manager, ctx, data_packs_path, pack_name)

        # Fallback to default_data pack
        if not data_pack and pack_name != "FORCE":
            await ctx.send("`Could not find a data pack named: " + pack_name + " using default instead.`")
            data_pack = await DataPack.load_data_pack(self.manager, ctx, data_packs_path, "default_data_pack")

        # If its still not full we can dump our code based one to file and use that
        if data_pack is None or pack_name == "FORCE":
            await ctx.send("`Using the in code data pack.`")
            data_pack = default_data_pack.create_default_data_pack(data_packs_path)
            await data_pack.save(self.manager, ctx)

        return data_pack

    @commands.command(name="tavern:force_reload_default")
    async def _force_reload_default(self, ctx: commands.Context):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("`Only the administrator can use this command as its for development purposes only.`")

        data_pack = await self._get_data_pack(ctx, "FORCE")

        # Check if we have a tavern here!
        tavern = await self.get_tavern_for_context(ctx)
        if tavern:
            old_data_pack = tavern.get_data_pack()
            if old_data_pack.get_name() == data_pack.get_name() and old_data_pack.get_path() == data_pack.get_path():
                await tavern.set_data_pack(data_pack)

        await ctx.send("`Default data pack reloaded`")

    @commands.command(name="tavern:force_reload")
    async def _force_reload(self, ctx: commands.Context):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:force_reload", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Check if we have a tavern here!
        tavern = await self.get_tavern_for_context(ctx)
        if not tavern:
            return await ctx.send("`There is no tavern initialized for this game!`")

        data_packs_path = os.path.join(self.name, "data_packs")
        data_pack = await DataPack.load_data_pack(self.manager, ctx, data_packs_path, tavern.get_data_pack().get_name())
        await tavern.refresh_data_pack(data_pack)
        await ctx.send("`Default data pack reloaded`")

    @commands.command(name="tavern:force_reload_tavern")
    async def _force_reload_tavern(self, ctx: commands.Context):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:force_reload_tavern", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        tavern = await Tavern.load_tavern(self.manager, self.game_master, ctx, "tavern")
        if isinstance(tavern, str):
            return await ctx.send(tavern)

        elif tavern:
            await self.set_tavern_for_context(ctx, tavern)
            return await ctx.send("`Loaded a tavern for your game!`")

    @commands.command(name="tavern:initialize")
    async def _initialize(self, ctx: commands.Context, *, pack: str = ""):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:initialize", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Check if we have a tavern here!
        tavern = await self.get_tavern_for_context(ctx)
        if tavern:
            return await ctx.send("`There is already a tavern operating in your current game!`")

        # Try and load the tavern to make sure that it doesnt exist as a file
        tavern = await Tavern.load_tavern(self.manager, self.game_master, ctx, "tavern")
        if isinstance(tavern, str):
            return ctx.send(tavern)

        elif tavern:
            await self.set_tavern_for_context(ctx, tavern)
            return ctx.send("`There is already tavern data present in this game. Loading it instead.`")

        # Look for a data pack base on our input.
        data_pack = await self._get_data_pack(ctx, pack)

        # Check that we actually have data
        if data_pack is None:
            return await ctx.send("`No data pack could be loaded!`")

        # Create a tavern
        tavern = await Tavern.create_tavern(self.manager, self.game_master, ctx, "tavern", data_pack)
        await self.set_tavern_for_context(ctx, tavern)
        return await ctx.send("`Successfully created a tavern for your adventuring party!`")

    @commands.command(name="tavern:name")
    async def _name(self, ctx: commands.Context, *, name: str = ""):
        # Can the user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:name", permissions_level=constants.party_member)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the tavern and exit if there is none
        tavern = await self.get_tavern_for_context(ctx)
        if not tavern:
            return await ctx.send("`There is no tavern being operated in your game!`")

        # Set the tavern and save
        tavern.set_name(name)
        await self.set_tavern_for_context(ctx, tavern)
        return await ctx.send("`Changed the name of your tavern to: " + name + "`")

    @commands.command(name="tavern:status")
    async def _status(self, ctx: commands.Context):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:status", permissions_level=constants.party_member)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the tavern and exit if there is none
        tavern = await self.get_tavern_for_context(ctx)
        if not tavern:
            return await ctx.send("`There is no tavern being operated in your game!`")

        # Create our status representation in long message form
        long_message = LongMessage()

        # Gather our business status
        long_message.add("===================================")  # Fake new line
        long_message.add("Your business: " + tavern.get_name() + " has the following properties: ")
        long_message.add("===================================")  # Fake new line
        for property, value in tavern.get_properties().items():
            key = "tavern." + tavern.data_pack.name + "." + property

            if value is not None or value is not "":
                detail_key = key + "." + str(value)
                translation = await self.manager.get_translation_for_current_localization(ctx, detail_key)

                if translation != detail_key:
                    long_message.add(translation)
                    continue

            translation = await self.manager.get_translation_for_current_localization(ctx, key)
            long_message.add(str(translation) + (" " + str(value) if value is not None else ""))

        # Gather our staff
        staff = tavern.get_staff()
        count = len(staff)
        long_message.add(None)
        long_message.add("===================================")  # Fake new line
        long_message.add("You currently have " + str(count) + " employees." + (" They are:" if count > 0 else ""))
        for staff_member in staff:
            long_message.add(str(staff_member))

        # Active contracts
        contracts = tavern.get_contracts()
        long_message.add(None)
        long_message.add("===================================")  # Fake new line
        long_message.add("You currently have " + str(len(contracts)) + " contracts ongoing.")
        for contract in contracts:
            long_message.add(str(contract))

        # Customers
        customers = tavern.get_most_recent_customer_history()
        long_message.add(None)
        long_message.add("===================================")  # Fake new line
        if customers:
            long_message.add("Last tenday you had the following customers:")
            for customer_entry in customers:
                long_message.add(str(customer_entry))
        else:
            long_message.add("You have had no customers over the last week.")

        # Offering
        services = tavern.get_most_recent_sales_history()
        long_message.add(None)
        long_message.add("===================================")  # Fake new line
        if services:
            long_message.add("Last tenday you served the following: ")
            for service in services:
                long_message.add(str(service))
        else:
            long_message.add("You have had no sales over the last week.")

        # Output
        async with ctx.typing():
            for message in long_message:
                await ctx.send(message)

    @commands.command(name="tavern:purchaseable_upgrades")
    async def _purchaseable_upgrades(self, ctx: commands):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:purchaseable_upgrades", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the tavern and exit if there is none
        tavern = await self.get_tavern_for_context(ctx)
        if not tavern:
            return await ctx.send("`There is no tavern being operated in your game!`")

        # Get the results to post
        purchaseable = tavern.get_upgradeable()

        # Create an output message
        long_message = LongMessage()
        long_message.add("The business can apply the following upgrades: ")

        # Gather our business status
        long_message.add(" ")  # Fake new line
        for purchaseable in purchaseable:
            long_message.add("===================================")
            purchaseable_name = await self.manager.get_translation_for_current_localization(ctx, purchaseable.get_key())
            long_message.add("Upgrade: " + purchaseable.get_key())
            long_message.add(" ")
            long_message.add(purchaseable_name + " can be purchased for " + str(float(purchaseable.cost) / 100.0) + " gold and will take " + str(purchaseable.duration) + " days to construct")
            long_message.add(" ")

        # Output
        async with ctx.typing():
            for message in long_message:
                await ctx.author.send(message)

    @commands.command(name="tavern:purchase_upgrade")
    async def _purchase_upgrade(self, ctx: commands.Context, *, item: str):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:purchase_upgrade", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the amount
        amount = get_trailing_number(item)
        item = item.replace(str(amount), "").strip()

        # Get the tavern and exit if there is none
        tavern = await self.get_tavern_for_context(ctx)
        if not tavern:
            return await ctx.send("`There is no tavern being operated in your game!`")

        # TODO: Inventory integration

        # Apply the purchase
        if await tavern.apply_upgrade(item, amount):
            await self.set_tavern_for_context(ctx, tavern)
            return await ctx.send("`The upgrade has been purchased!`")

        else:
            return await ctx.send("`The upgrade could not be purchased.`")

    @commands.command(name="tavern:purchaseable_contracts")
    async def _purchaseable_contracts(self, ctx: commands):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:purchaseable_contracts", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the tavern and exit if there is none
        tavern = await self.get_tavern_for_context(ctx)
        if not tavern:
            return await ctx.send("`There is no tavern being operated in your game!`")

        # Get the results to post
        contractables = tavern.get_contractable()

        # Create an output message
        long_message = LongMessage()
        long_message.add("The business can apply the following contracts: ")

        # Gather our business status
        long_message.add(" ")  # Fake new line
        for contract in contractables:
            long_message.add("===================================")
            purchaseable_name = await self.manager.get_translation_for_current_localization(ctx, contract.get_key())
            long_message.add("Contract: " + contract.get_key())
            long_message.add(" ")
            long_message.add(purchaseable_name + " can be purchased for " + str(float(contract.cost) / 100.0) + " gold and will last for  " + str(contract.duration) + " days.")
            long_message.add(" ")

        # Output
        async with ctx.typing():
            for message in long_message:
                await ctx.author.send(message)

    @commands.command(name="tavern:purchase_contract")
    async def _purchase_contract(self, ctx: commands.Context, *, item: str):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:purchase_contract", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the amount
        amount = get_trailing_number(item)
        item = item.replace(str(amount), "").strip()

        # Get the tavern and exit if there is none
        tavern = await self.get_tavern_for_context(ctx)
        if not tavern:
            return await ctx.send("`There is no tavern being operated in your game!`")

        # TODO: Inventory integration

        # Get the current day
        game = self.game_master.get_active_game_for_context(ctx)
        current_day = game.get_days_passed()

        # Apply the purchase
        if await tavern.apply_contract(item, amount, current_day):
            await self.set_tavern_for_context(ctx, tavern)
            return await ctx.send("`The upgrade has been applied!`")

        else:
            return await ctx.send("`The upgrade could not be applied.`")

    @commands.command(name="tavern:available_staff")
    async def _available_staff(self, ctx: commands):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:available_staff", permissions_level=constants.party_member)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the tavern and exit if there is none
        tavern = await self.get_tavern_for_context(ctx)
        if not tavern:
            return await ctx.send("`There is no tavern being operated in your game!`")

        # Get the results to post
        hireables = tavern.get_hireable()

        # Create an output message
        long_message = LongMessage()
        long_message.add("The business can apply the following upgrades: ")

        # Gather our business status
        long_message.add(" ")  # Fake new line
        for hireable in hireables:
            long_message.add("===================================")
            purchaseable_name = await self.manager.get_translation_for_current_localization(ctx, hireable.get_key())
            long_message.add("Employee Type: " + hireable.get_key())
            long_message.add(" ")
            long_message.add(purchaseable_name + " can be hired for " + str(hireable.cost_per_day) + " copper pieces a day.")
            long_message.add(" ")

        # Output
        async with ctx.typing():
            for message in long_message:
                await ctx.author.send(message)

    @commands.command(name="tavern:hire_staff")
    async def _hire_staff(self, ctx: commands.Context, *, item: str):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "tavern:hire_staff", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get the amount
        amount = get_trailing_number(item)
        item = item.replace(str(amount), "").strip()

        # Get the tavern and exit if there is none
        tavern = await self.get_tavern_for_context(ctx)
        if not tavern:
            return await ctx.send("`There is no tavern being operated in your game!`")

        # TODO: Fantasy name generator
        staff_name = names.get_full_name()

        # Apply the purchase
        if await tavern.hire_staff(item, amount, staff_name):
            await self.set_tavern_for_context(ctx, tavern)
            return await ctx.send("`A new staff member named: " + staff_name + " has been hired!`")

        else:
            return await ctx.send("`That staff type could not be hired.`")
