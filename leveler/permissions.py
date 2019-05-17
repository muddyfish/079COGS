from redbot.core import commands
from .config import db


@commands.check
async def leveler_enabled(ctx: commands.Context):
    guild = ctx.message.guild
    if guild is None:
        return True
    if await db.guild(guild).disabled():
        await ctx.send("**Leveler commands for this guild are disabled!**")
        return False
    return True
