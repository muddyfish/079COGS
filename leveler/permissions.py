from redbot.core import commands
from .config import db


@commands.check
async def leveler_enabled(ctx: commands.Context):
    guild = ctx.message.guild
    if guild is None:
        return True
    disabled_guilds = await db.disabled_guilds()
    if str(guild.id) in disabled_guilds:
        await ctx.send("**Leveler commands for this guild are disabled!**")
        return False
    return True
