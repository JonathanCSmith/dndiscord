def get_guild_id_from_context(context):
    return str(context.guild.id)


def get_user_id_from_context(context):
    return str(context.author.id)
