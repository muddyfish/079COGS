from redbot.core import commands
from .config import db


@commands.check
async def leveler_enabled(ctx: commands.Context):
    guild = ctx.message.guild
    if guild is None:
        return True
    settings = await db.settings()
    if str(guild.id) in settings["disabled_guilds"]:
        await ctx.send("**Leveler commands for this guild are disabled!**")
        return False
    return True
