import discord

open = discord.PermissionOverwrite(read_messages=True, send_messages=True, create_instant_invite=True, manage_channels=True, manage_permissions=True, manage_webhooks=True, send_tts_messages=True, manage_messages=True, embed_links=True, attach_files=True, read_message_history=True, mention_everyone=True, external_emojis=True, add_reactions=True)
partial = discord.PermissionOverwrite(read_messages=True, send_messages=True, create_instant_invite=True, manage_channels=True, manage_permissions=True, manage_webhooks=True, send_tts_messages=True, manage_messages=True, embed_links=True, attach_files=True, read_message_history=True, mention_everyone=True, external_emojis=True, add_reactions=True)
closed = discord.PermissionOverwrite(read_messages=False, send_messages=False, create_instant_invite=False, manage_channels=False, manage_permissions=False, manage_webhooks=False, send_tts_messages=False, manage_messages=False, embed_links=False, attach_files=False, read_message_history=False, mention_everyone=False, external_emojis=False, add_reactions=False)

# Permission levels
admin = 3
gm = 2
party_member = 1
any = 0
