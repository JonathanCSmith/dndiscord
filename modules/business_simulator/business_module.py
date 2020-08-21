import os

import names
from discord.ext import commands

from module_properties import Module
from modules.business_simulator.data.data_packs_generators import default_data_pack
from modules.business_simulator.model.data_pack import BusinessDataPack
from modules.business_simulator.business_controller import BusinessController
from modules.business_simulator.business_command_view_builder import build_status_view_players, build_purchaseable_view_players
from utils import constants
from utils.errors import CommandRunError
from utils.strings import get_trailing_number

"""
Define a current state view for the business
    
    3) Allow players to change the state of the business over time via the GM
        a) Contract negotiations
        b) Purchase negotiations
        c) Purchase contributions
        
    4) Show business history
    
    5) Simulate a day and show outcomes in a log

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


class BusinessSimulator(Module):
    def __init__(self, engine):
        super().__init__("business_simulator", engine)

        self.active_businesses = dict()
        self.game_master = self.engine.get_module("game_master")
        if self.game_master:
            self.game_master.register_game_state_listener(self)
        else:
            raise RuntimeError("Cannot use the business simulator without the Game Master module.")

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage('This command can\'t be used in DM channels.')

        return True

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, CommandRunError):
            await ctx.send(error.detail)
            return

        await ctx.send('`An error occurred: {}`'.format(str(error)))
        
    def get_businesses_for_context(self, ctx):
        game = self.game_master.get_active_game_for_context(ctx)
        if game.get_name() in self.active_businesses:
            return self.active_businesses[game.get_name()]

        return None

    def get_business_for_context(self, ctx, name):
        game = self.game_master.get_active_game_for_context(ctx)
        if game.get_name() in self.active_businesses and name in self.active_businesses[game.get_name()]:
            return self.active_businesses[game.get_name()][name]

        return None

    async def set_business_for_context(self, ctx, business):
        game = self.game_master.get_active_game_for_context(ctx)

        should_save = False
        if business.get_name() not in self.active_businesses[game.get_name()]:
            should_save = True

        # Save the business specific data
        await business.save(self.game_master, ctx)
        self.active_businesses[game.get_name()][business.get_name()] = business

        # Save our core info too
        if should_save:
            await self.game_master.save_game_data(ctx, "businesses", "businesses.json", [*self.active_businesses[game.get_name()].keys()])

    async def unload_business_for_context(self, ctx):
        game = self.game_master.get_active_game_for_context(ctx)

        if game.get_name() in self.active_businesses:
            await self.game_master.save_game_data(ctx, "businesses", "businesses.json", [*self.active_businesses[game.get_name()].keys()])
            for val in self.active_businesses[game.get_name()].values():
                val.save(self.game_master, ctx)

            del self.active_businesses[game.get_name()]

    async def game_created(self, ctx, game):
        pass

    async def game_started(self, ctx, game):
        businesses = await self.game_master.load_game_data(ctx, "businesses", "businesses.json")
        if businesses is not None:
            real_businesses = dict()
            for business_name in businesses:
                #business = await BusinessController.load_business(self.engine, self.game_master, ctx, business_name)
                business = await BusinessController.load_business(self.engine, self.game_master, ctx, business_name)
                if isinstance(business, str):
                    return await ctx.send(business)

                else:
                    display_name = business.get_name() if business.get_name() != "" else business_name
                    await ctx.send("`Loaded business: " + display_name + "`")

                real_businesses[business_name] = business
            self.active_businesses[game.get_name()] = real_businesses
        else:
            self.active_businesses[game.get_name()] = dict()
            await self.game_master.save_game_data(ctx, "businesses", "businesses.json", [*self.active_businesses[game.get_name()].keys()])

    async def game_about_to_end(self, ctx, game):
        await self.unload_business_for_context(ctx)

    async def game_deleted(self, ctx, game):
        await self.unload_business_for_context(ctx)

    async def day_passed(self, ctx, game):
        businesses = self.active_businesses[game.get_name()]
        for business in businesses:
            business.pass_day(ctx, game)
            # TODO: Some kind of output here

    async def _get_data_pack(self, ctx, pack_name):
        data_pack = None
        data_packs_path = os.path.join(self.name, "data_packs")

        # First check our guild specific dir and our local bot directory
        if pack_name != "" and pack_name != "FORCE":
            await ctx.send("`Attempting to load data pack: " + pack_name + "`")
            data_pack = await BusinessDataPack.load(self.engine, ctx, data_packs_path, data_pack_name=pack_name)

        # Fallback to default_data pack
        if not data_pack and pack_name != "FORCE":
            await ctx.send("`Could not find a data pack named: " + pack_name + " using default instead.`")
            data_pack = await BusinessDataPack.load(self.engine, ctx, data_packs_path, data_pack_name="default_data_pack")

        # If its still not full we can dump our code based one to file and use that
        if data_pack is None or pack_name == "FORCE":
            await ctx.send("`Using the in code data pack.`")
            data_pack = default_data_pack.create_default_data_pack(data_packs_path)
            await data_pack.save(self.engine, ctx)

        return data_pack

    @commands.command(name="business:force_reload_default")
    async def _force_reload_default(self, ctx: commands.Context):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("`Only the administrator can use this command as its for development purposes only.`")

        data_pack = await self._get_data_pack(ctx, "FORCE")

        # Check if we have a business here!
        businesses = self.get_businesses_for_context(ctx)
        for business in businesses:
            if business.get_data_pack().get_name() == data_pack.get_name() and business.get_data_pack().get_path() == data_pack.get_path():
                await business.set_data_pack(data_pack)

        await ctx.send("`Default data pack reloaded`")

    @commands.command(name="business:force_reload")
    async def _force_reload(self, ctx: commands.Context, *, name: str):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "business:force_reload", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Check if we have a business here!
        businesses = self.get_businesses_for_context(ctx)
        if not businesses:
            return await ctx.send("`There are no business initialized for this game!`")

        # If the name was not a business
        if name not in businesses:
            await ctx.send("`Could not find a business with that name - looking through data packs")

            # Arbitrarily look for data packs and reload
            data_pack = await self._get_data_pack(ctx, name)
            if data_pack is not None:
                for business in businesses:
                    if business.get_data_pack().get_name() == data_pack.get_name() and business.get_data_pack().get_path() == data_pack.get_path():
                        await business.set_data_pack(data_pack)

                # Inform
                return await ctx.send("`Data pack identified - all business using it were reloaded.`")

        # Reload the business' data pack specifically
        else:
            business = businesses[name]
            data_pack = await self._get_data_pack(ctx, business.get_data_pack())
            await business.refresh_data_pack(data_pack)
            return await ctx.send("`Default data pack reloaded`")

        return await ctx.send("`Could not identify anything corresponding to the name: " + name + " to reload.`")

    @commands.command(name="business:force_reload_business")
    async def _force_reload_business(self, ctx: commands.Context, *, name: str):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "business:force_reload_business", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Get our businesses
        business = self.get_business_for_context(ctx)
        if not business:
            return await ctx.send("`No business with the name: " + name + "`")

        #business = await BusinessController.load_business(self.manager, self.game_master, ctx, name)
        business = await BusinessController.load_business(self.engine, self.game_master, ctx, name)
        if isinstance(business, str):
            return await ctx.send(business)

        elif business:
            await self.set_business_for_context(ctx, business)
            return await ctx.send("`Reloaded: " + name + "`")

    @commands.command(name="business:initialize")
    async def _initialize(self, ctx: commands.Context, *, pack: str):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "business:initialize", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Split
        parts = pack.split(" ")
        if len(parts) != 2:
            return await ctx.send("`You need to pass the data pack and the business name into this function. Also the data pack and the business nickname must be one word!`")

        # Check if we already have a business here!
        business = self.get_business_for_context(ctx, parts[1])
        if business is not None:
            return await ctx.send("`There is already a business initialized with: " + pack + "`")

        # Try and load the business to make sure that it doesnt exist as a file
        #business = await BusinessController.load_business(self.engine, self.game_master, ctx, parts[1])
        business = await BusinessController.load_business(self.engine, ctx, self.game_master, parts[1])
        if isinstance(business, str):
            return await ctx.send(business)

        elif business:
            await self.set_business_for_context(ctx, business)
            return await ctx.send("`There is already business data present in this game. Loading it instead.`")

        # Look for a data pack base on our input.
        data_pack = await self._get_data_pack(ctx, parts[0])
        if data_pack is None:
            return await ctx.send("`No data pack could be loaded!`")

        # Create a business
        business = await BusinessController.create_business(self.game_master, ctx, data_pack, parts[1])
        await self.set_business_for_context(ctx, business)
        return await ctx.send("`Successfully created a business for your adventuring party!`")

    @commands.command(name="business:rename")
    async def _name(self, ctx: commands.Context, *, name: str = ""):
        # Can the user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "business:rename", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Split for nickname
        parts = name.split(" ", 1)
        if len(parts) != 2:
            return ctx.send("You must provide the nickname of the business that you would like to rename!")

        # Get the business and exit if there is none
        business = self.get_business_for_context(ctx, parts[0])
        if not business:
            return await ctx.send("`There is no business being operated in your game with the name: " + parts[0] + "!`")

        # Set the business and save
        business.set_name(parts[1])
        await self.set_business_for_context(ctx, business)
        return await ctx.send("`Changed the name of your business to: " + name + "`")

    @commands.command(name="business:status")
    async def _status(self, ctx: commands.Context, *, name: str = ""):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "business:status", permissions_level=constants.party_member)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # If name is empty
        if name == "":
            return await ctx.send("`No name was provided.`")

        # Get the business and exit if there is none
        business = self.get_business_for_context(ctx, name)
        if not business:
            return await ctx.send("`There is no business being operated in your game with the nickname: " + name + "!`")

        long_message = await build_status_view_players(business, self.engine, ctx)

        # Output
        async with ctx.typing():
            for message in long_message:
                await ctx.send(message)

    @commands.command(name="business:purchaseables")
    async def _purchaseables(self, ctx: commands, name: str = ""):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "business:purchaseables", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Split for nickname
        parts = name.split(" ", 1)
        if len(parts) != 2:
            return await ctx.send("You must provide the nickname of the business that you would like to rename!")

        # Get the business and exit if there is none
        business = self.get_business_for_context(ctx, parts[0])
        if not business:
            return await ctx.send("`There is no business being operated in your game!`")

        long_message = await build_purchaseable_view_players(business, self.engine, ctx)

        # Output
        async with ctx.typing():
            for message in long_message:
                await ctx.author.send(message)

    @commands.command(name="business:purchase_improvement")
    async def _purchase_improvement(self, ctx: commands.Context, *, name: str):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "business:purchase_improvement", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Split for nickname
        parts = name.split(" ", 1)
        if len(parts) != 2:
            return await ctx.send("You must provide the nickname of the business that you would like to rename!")

        # Get the amount
        amount = get_trailing_number(parts[1])
        item = parts[1].replace(str(amount), "").strip()

        # Get the business and exit if there is none
        business = self.get_business_for_context(ctx, parts[0])
        if not business:
            return await ctx.send("`There is no business being operated in your game!`")

        # TODO: Inventory integration

        # Apply the purchase
        game_days = self.game_master.get_active_game_for_context(ctx).get_days_passed()
        if await business.apply_improvement(item, amount, game_days):
            await self.set_business_for_context(ctx, business)
            return await ctx.send("`The improvement has been purchased!`")

        else:
            return await ctx.send("`The improvement could not be purchased.`")

    @commands.command(name="business:purchase_contract")
    async def _purchase_contract(self, ctx: commands.Context, *, name: str):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "business:purchase_contract", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Split for nickname
        parts = name.split(" ", 1)
        if len(parts) != 2:
            return await ctx.send("You must provide the nickname of the business that you would like to rename!")

        # Get the amount
        amount = get_trailing_number(parts[1])
        item = parts[1].replace(str(amount), "").strip()

        # Get the business and exit if there is none
        business = self.get_business_for_context(ctx, parts[0])
        if not business:
            return await ctx.send("`There is no business being operated in your game!`")

        # TODO: Inventory integration

        # Get the current day
        game = self.game_master.get_active_game_for_context(ctx)
        current_day = game.get_days_passed()

        # Apply the purchase
        if await business.apply_contract(item, amount, current_day):
            await self.set_business_for_context(ctx, business)
            return await ctx.send("`The contract has been purchased!`")

        else:
            return await ctx.send("`The contract could not be purchased.`")

    @commands.command(name="business:hire_staff")
    async def _hire_staff(self, ctx: commands.Context, *, name: str):
        # Can this user initiate the call to this command
        permissions_check, reason = await self.game_master.check_active_game_permissions_for_user(ctx, "business:hire_staff", permissions_level=constants.gm)
        if not permissions_check:
            return await ctx.send("`" + reason + "`")

        # Split for nickname
        parts = name.split(" ", 1)
        if len(parts) != 2:
            return await ctx.send("You must provide the nickname of the business that you would like to rename!")

        # Get the amount
        amount = get_trailing_number(parts[1])
        item = parts[1].replace(str(amount), "").strip()

        # Get the business and exit if there is none
        business = self.get_business_for_context(ctx, parts[0])
        if not business:
            return await ctx.send("`There is no business being operated in your game!`")

        # TODO: Fantasy name generator
        staff_name = names.get_full_name()

        # Apply the purchase
        game_days = self.game_master.get_active_game_for_context(ctx).get_days_passed()
        if await business.hire_employee(item, staff_name, game_days):
            await self.set_business_for_context(ctx, business)
            return await ctx.send("`A new staff member named: " + staff_name + " has been hired!`")

        else:
            return await ctx.send("`That staff type could not be hired.`")
