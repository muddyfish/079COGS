from redbot.core import commands
import discord
import time
from .leveler import db


@commands.cooldown(2, 10, commands.BucketType.user)
@commands.command(pass_context=True, no_pm=True)
async def rep(self, ctx, user: discord.Member = None):
    """Gives a reputation point to a designated player."""
    org_user = ctx.message.author
    guild = org_user.guild
    # creates user if doesn't exist
    await self._create_user(org_user, guild)
    if user:
        await self._create_user(user, guild)
    org_userinfo = db.users.find_one({"user_id": str(org_user.id)})
    curr_time = time.time()

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("**Leveler commands for this guild are disabled!**")
        return
    if user and str(user.id) == str(org_user.id):
        await ctx.send("**You can't give a rep to yourself!**")
        return
    if user and user.bot:
        await ctx.send("**You can't give a rep to a bot!**")
        return
    if "rep_block" not in org_userinfo:
        org_userinfo["rep_block"] = 0

    delta = float(curr_time) - float(org_userinfo["rep_block"])
    if user and delta >= 43200.0 and delta > 0:
        userinfo = db.users.find_one({"user_id": str(str(user.id))})
        db.users.update_one({"user_id": str(org_user.id)}, {"$set": {"rep_block": curr_time}})
        db.users.update_one(
            {"user_id": str(str(user.id))}, {"$set": {"rep": userinfo["rep"] + 1}}
        )
        await ctx.send(
            "**You have just given {} a reputation point!**".format(self._is_mention(user))
        )
    else:
        # calulate time left
        seconds = 43200 - delta
        if seconds < 0:
            await ctx.send("**You can give a rep!**")
            return

        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        await ctx.send(
            "**You need to wait {} hours, {} minutes, and {} seconds until you can give reputation again!**".format(
                int(h), int(m), int(s)
            )
        )
