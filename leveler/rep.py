from redbot.core import commands
import discord
import time
from .leveler import db


@commands.cooldown(2, 10, commands.BucketType.user)
@commands.command(pass_context=True, no_pm=True)
async def rep(leveler, ctx, user: discord.Member = None):
    """Gives a reputation point to a designated player."""
    org_user = ctx.message.author
    guild = org_user.guild

    # creates user if doesn't exist
    await leveler._create_user(org_user, guild)
    if user:
        await leveler._create_user(user, guild)

    # Get the time to wait until they can rep
    org_userinfo = db.users.find_one({"user_id": str(org_user.id)})
    curr_time = time.time()
    if "rep_block" not in org_userinfo:
        org_userinfo["rep_block"] = 0
    delta = float(curr_time) - float(org_userinfo["rep_block"])
    if not (user and delta >= 43200.0 and delta > 0):
        return await failure_message(ctx, delta)

    if str(guild.id) in leveler.settings["disabled_guilds"]:
        return await ctx.send("**Leveler commands for this guild are disabled!**")
    if user == org_user:
        return await ctx.send("**You can't give a rep to yourleveler!**")
    if user.bot:
        return await ctx.send("**You can't give a rep to a bot!**")

    userinfo = db.users.find_one({"user_id": str(str(user.id))})
    db.users.update_one({"user_id": str(org_user.id)}, {"$set": {"rep_block": curr_time}})
    db.users.update_one(
        {"user_id": str(str(user.id))}, {"$set": {"rep": userinfo["rep"] + 1}}
    )
    return await ctx.send(f"**You have just given {leveler._is_mention(user)} a reputation point!**")


async def failure_message(ctx, delta):
    seconds = 43200 - delta
    if seconds < 0:
        return await ctx.send("**You can give a rep!**")

    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    await ctx.send(f"**You need to wait {int(h)} hours, {int(m)} minutes, and {int(s)} seconds "
                   f"until you can give reputation again!**")
