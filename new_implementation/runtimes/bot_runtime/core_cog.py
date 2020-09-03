import discord
import typing

from discord import Role
from discord.ext import commands

from new_implementation.runtimes.bot_runtime.commands import DnDiscordCommand
from new_implementation.runtimes.bot_runtime.game_state_listener import GameStateListener
from new_implementation.bots.cogs import DnDiscordCog
from new_implementation.data.games import GameData
from new_implementation.core.permissions_handler import PermissionLevel, PermissionContext
from new_implementation.utils import utils, strings
from new_implementation.utils.message import send_message, LongMessage, log


class CoreCog(DnDiscordCog):
    GM_ROLE_NAME = "GameMaster"

    def __init__(self, engine):
        super().__init__(engine)

        self.engine.register_event_class(GameStateListener)

    @commands.command(cls=DnDiscordCommand, name="purge_memory", hidden=True)
    async def purge_memory_command(self, invocation_context: commands.Context):
        """
        Function to force purge all of the memory caches in the DnDiscord Application.
        """
        # Standard check for whether we can run this or not
        outcome, message = await invocation_context.command.check_can_run(self.engine, invocation_context)
        if not outcome:
            await log(self.engine, invocation_context, "User: " + invocation_context.author.name + " failed to invoke a command due to: " + message)
            return await send_message(invocation_context, message)

        # Purge the memory
        outcome = await self.engine.purge_memory()
        if outcome:
            return await send_message(invocation_context, "Memory successfully purged.")
        else:
            await log(self.engine, invocation_context, "Failed a memory purge - application may be unstable.")
            return await send_message(invocation_context, "Memory unsuccessfully purged.")

    @commands.command(cls=DnDiscordCommand, name="minimum_access_level_to_execute_command", aliases=["set_command_access", "set_access"])
    async def set_minimum_access_level_to_execute_command_command(self, invocation_context: commands.Context, command_name: str, permission_level: int, permission_holder_identifier: typing.Optional[str] = None):
        """
        A command to change some of the permission levels for commands at the permission holder level.
        Please note, only a small subset of commands support this feature. If a command does not support it, you will be notified.

        :param command_name: the full command name as given by the help command without the prefix. For example this command would be permissions_change

        :param permission_level: a numeric representation of the minimum permission level required in order to call this command.
                0 = ANY
                1 = SPECIALIST ROLE (as fixed by the commands themselves)
                2 = MEMBER (a member of this permission holding object)
                3 = OWNER (the permission holding 'owner')
                4 = ADMINISTRATOR (@admin role or another supported moderator role type)

        :param permission_holder_identifier: This permission_holder_identifier is used to look up the specific permission holder in the invocation context.
                For example, if you wish to edit the command permissions associated with a command when invoked in a specific 'game', this would be your game name
        """
        # Standard check for whether we can run this or not
        outcome, message = await invocation_context.command.check_can_run(self.engine, invocation_context, permission_holder_identifier=permission_holder_identifier)
        if not outcome:
            await log(self.engine, invocation_context, "User: " + invocation_context.author.name + " failed to invoke a command due to: " + message)
            return await send_message(invocation_context, message)

        # Get the command - this loop assumes that command names are unique
        for command in self.engine.walk_commands():
            if command.name == command_name:
                if not isinstance(command, DnDiscordCommand):
                    return await send_message(invocation_context, "The command you wish to edit the permissions for is not compatible with this yet.")

            # Adjust the permissions
            outcome = await command.change_permission_minimum_execution_level(self.engine, invocation_context, permission_level, permission_holder_identifier=permission_holder_identifier)

            # Inform
            if outcome:
                await log(self.engine, invocation_context, "Minimum execute permissions for command: " + command_name + " have been set to: " + str(PermissionLevel(permission_level)) + "" if permission_holder_identifier is None else " with context: " + permission_holder_identifier)
                return await send_message(invocation_context, "Successfully changed the permissions for: " + command_name)
            else:
                return await send_message(invocation_context, "Could not change the permissions for: " + command_name)

        # Could not find the command
        return send_message(invocation_context, "Could not find the command with the name: " + command_name + ". This command may not be available in our permissions model.")

    @commands.command(cls=DnDiscordCommand, name="add_admin_role")
    async def add_admin_role_command(self, invocation_context: commands.Context, role: Role):
        """
         Add a role to the DnDiscord administrators

        :param role: string name or mention of role
        """
        # Standard check for whether we can run this or not
        outcome, message = await invocation_context.command.check_can_run(self.engine, invocation_context)
        if not outcome:
            await log(self.engine, invocation_context, "User: " + invocation_context.author.name + " failed to invoke a command due to: " + message)
            return await send_message(invocation_context, message)

        # Edit our guild data
        guild_data = await self.engine.get_guild_data_for_context(invocation_context)
        guild_data.add_administrative_role(role)
        await self.engine.save_guild_data_for_context(invocation_context)

        # Inform
        return await send_message(invocation_context, "Administrator role: " + role.name + " added.")

    @commands.command(cls=DnDiscordCommand, name="remove_admin_role")
    async def remove_admin_role_command(self, invocation_context: commands.Context, role: Role):
        """
        Remove a role by name or mention to the DnDiscord administrators

        :param role: string name or mention of role
        """
        # Standard check for whether we can run this or not
        outcome, message = await invocation_context.command.check_can_run(self.engine, invocation_context)
        if not outcome:
            await log(self.engine, invocation_context, "User: " + invocation_context.author.name + " failed to invoke a command due to: " + message)
            return await send_message(invocation_context, message)

        # Edit our guild data
        guild_data = await self.engine.get_guild_data_for_context(invocation_context)
        guild_data.remove_administrative_role(role)
        await self.engine.save_guild_data_for_context(invocation_context)

        # Inform
        return await send_message(invocation_context, "Administrator role: " + role.name + " added.")

    @commands.command(cls=DnDiscordCommand, name="add_permitted_role")
    async def add_permitted_role_command(self, invocation_context: commands.Context, role: Role, command_name: str, permission_holder_identifier: typing.Optional[str] = None):
        """
         Add role permitted to execute the referenced function

        :param role: string name or mention of role

        :param command_name: the full command name as given by the help command without the prefix. For example this command would be permissions_change

        :param permission_holder_identifier: This permission_holder_identifier is used to look up the specific permission holder in the invocation context.
                For example, if you wish to edit the command permissions associated with a command when invoked in a specific 'game', this would be your game name
        """
        # Standard check for whether we can run this or not
        outcome, message = await invocation_context.command.check_can_run(self.engine, invocation_context)
        if not outcome:
            await log(self.engine, invocation_context, "User: " + invocation_context.author.name + " failed to invoke a command due to: " + message)
            return await send_message(invocation_context, message)

        # Get the command - this loop assumes that command names are unique
        for command in self.engine.walk_commands():
            if command.name == command_name:
                if not isinstance(command, DnDiscordCommand):
                    return await send_message(invocation_context, "The command you wish to edit the permissions for is not compatible with this yet.")

            # Adjust the permissions
            outcome = await command.add_permitted_role(self.engine, invocation_context, role, permission_holder_identifier=permission_holder_identifier)

            # Inform
            if outcome:
                await log(self.engine, invocation_context, "Role added for command: " + command_name + " - role name: " + role.name + "" if permission_holder_identifier is None else " with context: " + permission_holder_identifier)
                return await send_message(invocation_context, "Successfully added a role for: " + command_name)
            else:
                return await send_message(invocation_context, "Could not change the permissions for: " + command_name)

        # Could not find the command
        return send_message(invocation_context, "Could not find the command with the name: " + command_name + ". This command may not be available in our permissions model.")

    @commands.command(cls=DnDiscordCommand, name="remove_permitted_role")
    async def remove_permitted_role_command(self, invocation_context: commands.Context, role: Role, command_name: str, permission_holder_identifier: typing.Optional[str] = None):
        """
        Remove role permitted to execute the referenced function

        :param role: string name or mention of role

        :param command_name: the full command name as given by the help command without the prefix. For example this command would be permissions_change

        :param permission_holder_identifier: This permission_holder_identifier is used to look up the specific permission holder in the invocation context.
                For example, if you wish to edit the command permissions associated with a command when invoked in a specific 'game', this would be your game name
        """
        # Standard check for whether we can run this or not
        outcome, message = await invocation_context.command.check_can_run(self.engine, invocation_context)
        if not outcome:
            await log(self.engine, invocation_context, "User: " + invocation_context.author.name + " failed to invoke a command due to: " + message)
            return await send_message(invocation_context, message)

        # Get the command - this loop assumes that command names are unique
        for command in self.engine.walk_commands():
            if command.name == command_name:
                if not isinstance(command, DnDiscordCommand):
                    return await send_message(invocation_context, "The command you wish to edit the permissions for is not compatible with this yet.")

            # Adjust the permissions
            outcome = await command.remove_permitted_role(self.engine, invocation_context, role, permission_holder_identifier=permission_holder_identifier)

            # Inform
            if outcome:
                await log(self.engine, invocation_context, "Role removed for command: " + command_name + " - role name: " + role.name + "" if permission_holder_identifier is None else " with context: " + permission_holder_identifier)
                return await send_message(invocation_context, "Successfully added a role for: " + command_name)
            else:
                return await send_message(invocation_context, "Could not change the permissions for: " + command_name)

        # Could not find the command
        return send_message(invocation_context, "Could not find the command with the name: " + command_name + ". This command may not be available in our permissions model.")

    @commands.command(cls=DnDiscordCommand, name="modify_default_minimum_execution_permissions")
    async def modify_default_minimum_execution_permissions_command(self, invocation_context: commands.Context, command_name: str, permission_level: int):
        """
        A command to change some of the default permission levels for commands.
        Please note, only a small subset of commands support this feature. If a command does not support it, you will be notified.

        :param command_name: the full command name as given by the help command without the prefix. For example this command would be permissions_change

        :param permission_level: a numeric representation of the minimum permission level required in order to call this command.
                0 = ANY
                1 = SPECIALIST ROLE (as fixed by the commands themselves)
                2 = MEMBER (a member of this permission holding object)
                3 = OWNER (the permission holding 'owner')
                4 = ADMINISTRATOR (@admin role or another supported moderator role type)
        """
        # Standard check for whether we can run this or not
        outcome, message = await invocation_context.command.check_can_run(self.engine, invocation_context)
        if not outcome:
            await log(self.engine, invocation_context, "User: " + invocation_context.author.name + " failed to invoke a command due to: " + message)
            return await send_message(invocation_context, message)

        # Get the command - this loop assumes that command names are unique
        for command in self.engine.walk_commands():
            if command.name == command_name:
                if not isinstance(command, DnDiscordCommand):
                    return await send_message(invocation_context, "The command you wish to edit the permissions for is not compatible with this yet.")

            # Adjust the permissions
            command.set_default_minimum_level_to_execute(self.engine, invocation_context, permission_level)
            await log(self.engine, invocation_context, "Minimum execute permissions for command: " + command_name + " have been set to: " + str(PermissionLevel(permission_level)))
            return await send_message(invocation_context, "Successfully changed the permissions for: " + command_name)

        # Could not find the command
        return send_message(invocation_context, "Could not find the command with the name: " + command_name + ". This command may not be available in our permissions model.")

    @commands.command(cls=DnDiscordCommand, name="add_default_permitted_role")
    async def add_default_permitted_role(self, invocation_context: commands.Context, role: Role, command_name: str):
        """
         Add default role permitted to execute the referenced function

        :param role: string name or mention of role

        :param command_name: the full command name as given by the help command without the prefix. For example this command would be permissions_change
        """
        # Standard check for whether we can run this or not
        outcome, message = await invocation_context.command.check_can_run(self.engine, invocation_context)
        if not outcome:
            await log(self.engine, invocation_context, "User: " + invocation_context.author.name + " failed to invoke a command due to: " + message)
            return await send_message(invocation_context, message)

        # Get the command - this loop assumes that command names are unique
        for command in self.engine.walk_commands():
            if command.name == command_name:
                if not isinstance(command, DnDiscordCommand):
                    return await send_message(invocation_context, "The command you wish to edit the permissions for is not compatible with this yet.")

            # Adjust the permissions
            command.add_default_role(self.engine, invocation_context, role)
            await log(self.engine, invocation_context, "Role added for command: " + command_name + " - role name: " + role.name)
            return await send_message(invocation_context, "Successfully added a role for: " + command_name)

        # Could not find the command
        return send_message(invocation_context, "Could not find the command with the name: " + command_name + ". This command may not be available in our permissions model.")

    @commands.command(cls=DnDiscordCommand, name="remove_default_permitted_role")
    async def remove_default_permitted_role(self, invocation_context: commands.Context, role: Role, command_name: str):
        """
         Remove role permitted to execute the referenced function

        :param role: string name or mention of role

        :param command_name: the full command name as given by the help command without the prefix. For example this command would be permissions_change
        """
        # Standard check for whether we can run this or not
        outcome, message = await invocation_context.command.check_can_run(self.engine, invocation_context)
        if not outcome:
            await log(self.engine, invocation_context, "User: " + invocation_context.author.name + " failed to invoke a command due to: " + message)
            return await send_message(invocation_context, message)

        # Get the command - this loop assumes that command names are unique
        for command in self.engine.walk_commands():
            if command.name == command_name:
                if not isinstance(command, DnDiscordCommand):
                    return await send_message(invocation_context, "The command you wish to edit the permissions for is not compatible with this yet.")

            # Adjust the permissions
            command.add_default_role(self.engine, invocation_context, role)
            await log(self.engine, invocation_context, "Role added for command: " + command_name + " - role name: " + role.name)
            return await send_message(invocation_context, "Successfully added a role for: " + command_name)

        # Could not find the command
        return send_message(invocation_context, "Could not find the command with the name: " + command_name + ". This command may not be available in our permissions model.")

    @commands.command(cls=DnDiscordCommand, name="logging_channel", hidden=False)
    async def logging_channel_command(self, invocation_context: commands.Context, *, channel_name: str):
        """
        Command to change the default logging channel's name.

        :param channel_name: the name to change it to.

        Default permissions: Only @admin can perform this
        """
        # Standard check for whether we can run this or not
        outcome, message = await invocation_context.command.check_can_run(self.engine, invocation_context)
        if not outcome:
            await log(self.engine, invocation_context, "User: " + invocation_context.author.name + " failed to invoke a command due to: " + message)
            return await send_message(invocation_context, message)

        # Get the current config
        guild_data = self.engine.get_guild_data_for_context(invocation_context)
        old_channel_name = guild_data.get_log_channel_name()

        # Check if a channel exists for this name
        existing_channel = discord.utils.get(invocation_context.guild.text_channels, name=channel_name)
        if existing_channel:
            return await send_message(invocation_context, "Unfortunately a channel with that name exists already.")

        # Get the channel
        channel = discord.utils.get(invocation_context.guild.text_channels, name=old_channel_name)
        if channel is None:
            await invocation_context.guild.create_text_channel(channel_name)
        else:
            await channel.edit(name=channel_name)

        # Inform
        await log(self.engine, invocation_context, "The logging channel has been changed to: " + channel_name)

        # Save the update
        guild_data.set_logging_channel(channel_name)
        return await self.engine.save_guild_data_for_context(invocation_context)


    @commands.command(cls=DnDiscordCommand, name="list_games", default_minimum_access=PermissionLevel.ANY)
    async def game_command(self, invocation_context: commands.Context):
        """
        This function displays whether a guild is running a game currently and who the game master is. If the guild disallows this information it will not be sent.

        It also shows all of the names of games that a user is involved in
        """
        # Standard check for whether we can run this or not
        outcome, message = await invocation_context.command.check_can_run(self.engine, invocation_context)
        if not outcome:
            await log(self.engine, invocation_context, "User: " + invocation_context.author.name + " failed to invoke a command due to: " + message)
            return await send_message(invocation_context, message)

        # Message holder
        message = LongMessage()

        # DM the user all of the games they are currently in
        user = await self.engine.get_user_data_for_context(invocation_context)
        participating_in = user.get_games()
        if len(participating_in) > 0:
            message.add("You are currently playing in the following games:")
            for game in participating_in:
                message.add("\t" + game.get_name())

        # Inform and nope out if we aren't in a guild
        await send_message(invocation_context, message, is_dm=True)
        if isinstance(invocation_context.channel, discord.channel.DMChannel):
            return

        # If the source of the info was at a guild, list those games unless the game is hidden and the user is not in it.
        guild_data = self.engine.get_guild_data_for_context(invocation_context)
        current_game = self.engine.get_active_game_for_context(invocation_context)
        available_games = guild_data.get_games()
        if len(available_games) > 0:
            added_header = False
            for game in available_games:

                # If anyone can view the game or the caller is already in the game
                if game.is_public() or game.is_player(utils.get_user_id_from_context(invocation_context)):

                    # Add a header to make it legable
                    if not added_header:
                        message.add("The games that are running in your guild right now include:")

                    # Check if the game is the current game
                    if game.get_name() == current_game.get_name():
                        message.add("\t" + game.get_name() + " is currently running.")
                    else:
                        message.add("\t" + game.get_name())

        # Inform the call point
        return await send_message(invocation_context, message)

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
                    permission, reason = await self.engine.get_permission_handler().check_inactive_game_permissions_for_user(ctx, game, "game:game_information", permissions_level=PermissionLevel.ANY)
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

        # Check if there is a game with this name already and load our other data sets
        game = await self.engine.get_game(ctx, game_name)
        if game:
            return await send_message(ctx, "There is a game with that name present already.")
        guild = await self.engine.get_guild_data_for_context(ctx)
        user = await self.engine.get_user_data_for_context(ctx)

        # Register a new game
        game = GameData(utils.get_guild_id_from_context(ctx), game_name, utils.get_user_id_from_context(ctx), ctx.author.name)
        for listener in self.engine.get_event_class_listeners(GameStateListener):
            await listener.game.created(ctx, game)

        # Check if a channel exists for this name
        game_channel_name = guild.get_game_channel_prefix() + game_name + guild.get_game_channel_suffix()
        existing_channel = discord.utils.get(ctx.guild.text_channels, name=game_channel_name)
        if existing_channel:
            return await send_message(ctx, "Unfortunately a channel with that name exists already. Please choose a different name for your game")
        game_gm_channel_name = guild.get_game_gm_channel_prefix() + game_name + guild.get_game_gm_channel_suffix()
        existing_channel = discord.utils.get(ctx.guild.text_channels, name=game_gm_channel_name)
        if existing_channel:
            return await send_message(ctx, "Unfortunately a channel with that name exists already. Please choose a different name for your game")

        # Add a pointer in our guild and user
        guild.add_game(game_name)
        user.add_game(game_name)

        # Admin role
        admin_role = discord.utils.get(ctx.guild.roles, name="@admin")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Create our game channels
        await ctx.guild.create_text_channel(game_channel_name, overwrites=overwrites)
        await ctx.guild.create_text_channel(game_gm_channel_name, overwrites=overwrites)
        game.set_game_channel(game_channel_name)
        game.set_gm_channel(game_gm_channel_name)

        # Save the new data
        await self.engine.save_guild_data_for_context(ctx)
        await self.engine.save_user_data_for_context(ctx)
        await self.engine.save_game(ctx, game)

        # Inform
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
        for listener in self.engine.get_event_class_listeners(GameStateListener):
            await listener.game_started(ctx, game)

        await send_message(ctx, game_name + " is now running.")

    @commands.command(name="game:channel")
    async def game_channel_command(self, ctx: commands.Context, *, channel_name: str):
        """
        Change the current game's text channel

        :param channel_name: the name of the channel to change to
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "game:channel", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Check if a channel exists for this name
        existing_channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
        if existing_channel:
            return await send_message(ctx, "Unfortunately a channel with that name exists already.")

        # The game is guaranteed to be present if the above permission check succeeds
        game = self.engine.get_active_game_for_context(ctx)
        game_channel_name = game.get_game_channel()
        existing_channel = discord.utils.get(ctx.guild.text_channels, name=game_channel_name)
        await existing_channel.edit(name=channel_name)

        # Inform
        return await send_message(ctx, "Channel successfully renamed to: " + channel_name)

    @commands.command(name="game:gm_channel")
    async def game_gm_channel_command(self, ctx: commands.Context, *, channel_name: str):
        """
        Change the current game's gm text channel

        :param channel_name: the name of the channel to change to
        """
        if self.engine.purge_mutex:
            return await send_message(ctx, "Unfortunately we cannot currently process this command as a background purge is being performed of all memory.")

        # Check if the user is the gm (or an admin) for the game they want to activate. Note it will also fail if the game does not exist
        permission, reason = await self.engine.get_permission_handler().check_active_game_permissions_for_user(ctx, "game:gm_channel", permissions_level=PermissionLevel.GAME_MASTER)
        if not permission:
            return await send_message(ctx, reason)

        # Check if a channel exists for this name
        existing_channel = discord.utils.get(ctx.guild.text_channels, name=channel_name)
        if existing_channel:
            return await send_message(ctx, "Unfortunately a channel with that name exists already.")

        # The game is guaranteed to be present if the above permission check succeeds
        game = self.engine.get_active_game_for_context(ctx)
        gm_channel_name = game.get_gm_channel()
        existing_channel = discord.utils.get(ctx.guild.text_channels, name=gm_channel_name)
        await existing_channel.edit(name=channel_name)

        # Inform
        return await send_message(ctx, "Channel successfully renamed to: " + channel_name)

    @commands.command(name="game:end")
    async def game_end_command(self, ctx: commands.Context):
        """
        This function deactivates the currently running game from the guild.
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
        for listener in self.engine.get_event_class_listeners(GameStateListener):
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
        for listener in self.engine.get_event_class_listeners(GameStateListener):
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
            return await send_message(ctx, "The mentioned individual is already a player in this game.")

        # Create the player entry and update our records
        game.add_player(str(player.id))
        await self.engine.save_game(ctx, game)

        # Add this game to the player
        user_data = await self.engine.get_user_data(ctx, str(player.id))
        user_data.add_game(game.get_name())
        await self.engine.save_user_data(ctx, user_data)

        # Update the permissions
        channel = discord.utils.get(ctx.guild.text_channels, name=game.get_game_channel())
        await channel.set_permissions(player, read_messages=True, send_messages=True)

        return await send_message(ctx, "Added the player: " + player.nickname + " to the game.")

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
        if not game.is_player(player.id):
            return await send_message(ctx, "The player is not in this game.")

        # Remove and update
        game.remove_player(str(player.id))
        await self.engine.save_game(ctx, game)

        # Remove the game from the user
        user_data = await self.engine.get_user_data(ctx, str(player.id))
        user_data.remove_game(game.get_name())
        await self.engine.save_user_data(ctx, user_data)

        # Update the permissions
        channel = discord.utils.get(ctx.guild.text_channels, name=game.get_game_channel())
        await channel.set_permissions(player, None)

        return await send_message(ctx, "Removed " + player.nickname + " from the game.")
