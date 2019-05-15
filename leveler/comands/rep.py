from redbot.core import commands
import discord
import time
from ..config import db
from ..permissions import leveler_enabled
from ..static_methods import get_user_name


@commands.cooldown(2, 10, commands.BucketType.user)
@commands.command(pass_context=True, no_pm=True)
@leveler_enabled
async def rep(self, ctx, user: discord.Member = None):
    """Gives a reputation point to a designated player."""
    author = ctx.message.author
    rep_wait_time = await db.rep_cooldown()

    author_info = db.user(author)
    delta = time.time() - (await author_info.rep_block())
    if not (user and delta >= rep_wait_time and delta > 0):
        return await failure_message(ctx, rep_wait_time - delta)

    if user == author:
        return await ctx.send("**You can't give a rep to yourself!**")
    if user.bot:
        return await ctx.send("**You can't give a rep to a bot!**")

    await author_info.rep_block.set(time.time())

    target_info = db.user(user)
    target_rep = await target_info.rep()
    await target_info.rep.set(target_rep + 1)
    return await ctx.send(f"**You have just given {await get_user_name(user)} a reputation point!**")


async def failure_message(ctx, seconds):
    if seconds < 0:
        return await ctx.send("**You can give a rep!**")

    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    await ctx.send(f"**You need to wait {int(h)} hours, {int(m)} minutes, and {int(s)} seconds "
                   f"until you can give reputation again!**")
