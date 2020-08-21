import discord
from discord.ext import commands

from new_implementation.core.engine import DnDiscordCog
from new_implementation.data.games import PlayerData, GameData
from new_implementation.handlers.permissions_handler import PermissionLevel
from new_implementation.utils import utils
from new_implementation.utils.message import send_message, LongMessage


class GameCog(DnDiscordCog):
    def __init__(self, bot, engine):
        super().__init__(bot, engine)

    @commands.command(name="purge_memory", hidden=True)
    async def purge_memory_command(self, ctx: commands.Context):
        self.engine.purge_mutex = True

        # Save out all of our guild data

        # Save out all of our user data

        # Save out all of our game data

        # Let other modules know

        self.engine.purge_mutex = False

    @commands.command(name="game")
    async def game_command(self, ctx: commands.Context):
        """
        This function displays whether a guild is running a game currently and who the game master is. If the guild dissalows this information it will not be sent.

        It also shows all of the names of games that a user is involved in

        :param ctx: The context for the command
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        message = LongMessage()

        user = await self.engine.get_user_data_for_context(ctx)
        games = user.get_games()
        if len(games) > 0:
            message.add("You are currently playing in the following games:")
            for game in games:
                message.add("\t" + game)
            message.add("")
        else:
            message.add("You are not currently involved in any games.")
            message.add("")

        # If we are not in a private channel, we could look into the guild data
        if not isinstance(ctx.channel, discord.channel.DMChannel):

            # Check if the guild allows this command
            permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, "game:game_information", permissions_level=PermissionLevel.ANY)
            if not permission and reason != "You cannot do this as there is no game running in your guild.":
                message.add("The currently running game for this guild cannot be displayed due to: " + reason)
                return await send_message(ctx, message, is_dm=True)

            # Is there a game running currently
            game = self.engine.get_active_game_for_context(ctx)
            if game:
                message.add("The game: " + game.get_name() + " is currently running in this guild and is run by: " + game.get_gm())
            else:
                message.add("There is no game currently running in this guild.")
            message.add("")

            # Now get the games that aren't running
            guild_data = await self.engine.get_guild_data_for_context(ctx)
            games = guild_data.get_games()
            if len(games) > 0:
                message.add("The games that are available but not running in your guild right now are:")
                for game in guild_data.get_games():
                    permission, reason = await self.engine.get_permission_handler().check_inactive_game_permissions_for_user(ctx, game, "game:game_information",  permissions_level=PermissionLevel.ANY)
                    if permission:
                        message.add("\t" + game)

        # Reply as DM
        return await send_message(ctx, message, is_dm=True)

    @commands.command(name="game:create")
    async def game_create_command(self, ctx: commands.Context, *, game_name: str):
        """
        This function registers a new game with the caller as the game master for that game. If there is already a game with that name in the guild or the caller does not have permission to run the game it will fail.

        :param ctx: The context of the invocation
        :param game_name: The name of the game to create
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        permission, reason = await self.engine.get_permission_handler().check_guild_permissions_for_user(ctx, "game:create_game", elevated_roles="GameMaster")
        if not permission:
            return await send_message(ctx, reason)

        # Check if there is a game with this name already
        game = await self.engine.get_game(ctx, game_name)
        if game:
            return await send_message(ctx, "There is a game with that name present already.")

        # Register a new game
        game = GameData(utils.get_guild_id_from_context(ctx), game_name, utils.get_user_id_from_context(ctx), ctx.author.name)
        await self.engine.save_game(ctx, game)

        # Add a pointer in our user.
        user = await self.engine.get_user_data_for_context(ctx)
        user.add_game(game_name)
        await self.engine.save_user_data_for_context(ctx)

        # Add a pointer in our guild
        guild = await self.engine.get_guild_data_for_context(ctx)
        guild.add_game(game_name)
        await self.engine.save_guild_data_for_context(ctx)
        await send_message(ctx, "Create the game: " + game.get_name())

    @commands.command(name="game:run")
    async def game_run_command(self, ctx: commands.Context, *, game_name: str):
        """
        This function 'activates' a registered game if there is no other game running. This is necessary to ensure context dependent hints for running games

        :param ctx:
        :param game_name:
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_inactive_game_permissions_for_user(ctx, game_name, "game:run_game", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Check if there is already a game running for context
        if self.engine.get_active_game_for_context(ctx):
            return await send_message(ctx, "There is already a game running in this guild!")

        # Get the game
        game = await self.engine.get_game(ctx, game_name)
        if not game:
            return await send_message(ctx, "There is no game with that name registered for this guild. Please create the game first.")

        # Set the game as our active game
        self.engine.set_active_game_for_context(ctx, game)
        for listener in self.engine.get_game_state_listeners():
            await listener.game_started(ctx, game)

        await send_message(ctx, game_name + " is now running.")

    @commands.command(name="game:end")
    async def game_end_command(self, ctx: commands.Context):
        """
        This function deactivates the currently running game from the guild.

        :param ctx:
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "game:end", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # The game is guaranteed to be present if the above permission check succeeds
        game = self.engine.get_active_game_for_context(ctx)

        # Inform our listeners
        for listener in self.engine.get_game_state_listeners():
            await listener.game_about_to_end(ctx, game)

        # End this game
        await self.engine.end_active_game_for_context(ctx)

        # Inform
        return await send_message(ctx, "Finished playing: " + game.get_name() + " - thanks for playing!")

    @commands.command(name="game:delete")
    async def game_delete_command(self, ctx: commands.Context):
        """
        Delete the active game - this will remove all traces of the game so be careful with this one!

        :param ctx:
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "game:end", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # The game is guaranteed to be present if the above permission check succeeds
        game = self.engine.get_active_game_for_context(ctx)

        # Inform our listeners
        for listener in self.engine.get_game_state_listeners():
            await listener.game_deleting(ctx, game)

        # Go through the players and remove this game
        players = game.get_players()
        for player in players:
            user = await self.engine.get_user_data(ctx, player.get_id())
            user.remove_game(game.get_name())
            await self.engine.save_user_data(ctx, user)
        user = await self.engine.get_user_data(ctx, game.get_gm())
        user.remove_game(game.get_name())
        await self.engine.save_user_data(ctx, user)

        # Remove from our guild
        guild_data = await self.engine.get_guild_data_for_context(ctx)
        guild_data.remove_game(game.get_name())
        await self.engine.save_guild_data_for_context(ctx)

        # Delete this game
        await self.engine.delete_game(ctx, game)
        return await send_message(ctx, "Deleted: " + game.get_name() + " and all of it's data.")

    @commands.command(name="game:player")
    async def players_command(self, ctx: commands.Context):
        """
        List the players in the current game

        :param ctx:
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "game:player:add", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Get the players
        game = self.engine.get_active_game_for_context(ctx)
        players = game.get_players()
        if len(players) == 0:
            return await send_message(ctx, "There are no players in this game yet!")

        # Print out the adventurers
        message = LongMessage()
        for index, player in players.items():
            message.add(player.get_character_name() + " is controlled by: " + player.get_player_name())
        return await send_message(ctx, message)

    @commands.command(name="game:player:add")
    async def player_add_command(self, ctx: commands.Context):
        """
        Add a player. Requires the format: !game:player:add @<mention> <character_name>

        :param ctx:
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "game:player:add", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Check that an identifiable user was mentioned
        if not ctx.message.mentions:
            return await send_message(ctx, "No players were mentioned.")

        # If more than one
        if len(ctx.message.mentions) != 1:
            return await send_message(ctx, "Only one player can be added at a time.")

        # The game is guaranteed to be present if the above permission check succeeds
        game = self.engine.get_active_game_for_context(ctx)

        # Check if the player is already a member
        player = ctx.message.mentions[0]
        if game.is_player(str(player.id)):
            return await send_message(ctx, "The mentioned individual is already a player in this game")

        # Check additional arguments now to derive the player's character name
        remaining_text = ctx.message.clean_content.replace("!" + ctx.invoked_with, "")
        character_name = remaining_text.replace("@" + player.display_name, "").strip()  # TODO This does something weird with nicknames & mentions
        if not character_name or character_name == "":
            return await send_message(ctx, "No character name was provided")

        # Create the player entry and update our records
        player_entry = PlayerData(str(player.id), player.display_name, character_name)
        game.add_player(player_entry)
        await self.engine.save_game(ctx, game)

        # Add this game to the player
        user_data = await self.engine.get_user_data(ctx, str(player.id))
        user_data.add_game(game.get_name())
        await self.engine.save_user_data(ctx, user_data)

        return await send_message(ctx, "Added the player: " + player.display_name + " to the party.")

    @commands.command(name="game:player:add_dummy")
    async def player_add_dummy_command(self, ctx: commands.Context, *, items: str):
        """
        A command to add a player even if they are not available on discord. Format is !game:player:add_dummy <fake_player_name> <character_name>

        :param ctx:
        :param items:
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "game:player:add", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # The game is guaranteed to be present if the above permission check succeeds
        game = self.engine.get_active_game_for_context(ctx)

        # Args
        items = items.split(" ", 1)
        if len(items) != 2:
            return await send_message(ctx, "Incorrect arguments.")
        fake_name = items[0]
        character_name = items[1]
        if fake_name is "" or character_name is "":
            return await send_message(ctx, "Incorrect arguments.")

        # Create the player entry and update our records
        player_entry = PlayerData(fake_name, fake_name, character_name)
        game.add_player(player_entry)
        await self.engine.save_game(ctx, game)
        return await send_message(ctx, "Added the player character " + character_name + " to the party.")

    @commands.command(name="game:player:remove")
    async def player_remove_command(self, ctx: commands.Context):
        """
        Remove a player from the current game. Format is !game:player:remove @<mention>

        :param ctx:
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "game:player:add", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Check that an identifiable user was mentioned
        if not ctx.message.mentions:
            return await send_message(ctx, "No players were mentioned.")

        # If more than one
        if len(ctx.message.mentions) != 1:
            return await send_message(ctx, "Only one player can be added at a time.")

        # Check if the player is a member
        game = self.engine.get_active_game_for_context(ctx)
        player = ctx.message.mentions[0]
        adventurer = game.get_player(str(player.id))
        if not adventurer:
            return await send_message(ctx, "The player is not in this party.")

        # Remove and update
        game.remove_player(str(player.id))
        await self.engine.save_game(ctx, game)

        # Remove the game from the user
        user_data = await self.engine.get_user_data(ctx, str(player.id))
        user_data.remove_game(game.get_name())
        await self.engine.save_user_data(ctx, user_data)

        return await send_message(ctx, "Removed " + adventurer.get_character_name() + " from the party.")

    @commands.command(name="game:player:remove_character")
    async def player_remove_character_command(self, ctx: commands.Context, *, character: str):
        """
        Removes a character from the current game. This is good for removing dummy players too. Format is !game:player:remove_character <character_name>

        :param ctx:
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "game:player:add", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Check if the player is already a member
        game = self.engine.get_active_game_for_context(ctx)

        # Handle if they are not
        player = game.get_character(character)
        if not character or not player:
            return await send_message(ctx, "This adventurer is not in your party.")

        # Remove and update
        game.remove_player(player.get_player_id())
        await self.engine.save_game(ctx, game)

        # Attempt to get the player - but it may not be a real one so don't error if we cannot
        user_data = await self.engine.get_user_data(ctx, player.get_player_id())
        user_data.remove_game(game.get_name())
        await self.engine.save_user_data(ctx, user_data)

        return await send_message(ctx, "Removed the adventurer: " + character + " from the party.")

    @commands.command(name="game:day")
    async def days_command(self, ctx: commands.Context):
        """
        Returns the number of days passed in this game.

        :param ctx:
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "game:player:add", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Get the game and display the day
        game = self.engine.get_active_game_for_context(ctx)
        days = game.get_days_passed()
        return await send_message(ctx, str(days) + " have passed since the start of the adventure.")

    @commands.command(name="game:day:pass")
    async def pass_day_command(self, ctx: commands.Context):
        """
        Passes a day in game.

        :param ctx:
        :return:
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "game:player:add", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Get the game and increment the day
        game = self.engine.get_active_game_for_context(ctx)
        game.increment_day()
        await send_message(ctx, "A new day dawns in: " + game.get_name())

        # Inform our listeners
        for listener in self.engine.get_game_state_listeners():
            await listener.day_passed(ctx, game)

        # Save the game
        return await self.engine.save_game(ctx, game)