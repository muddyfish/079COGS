from redbot.core import commands
import discord
from .leveler import db
from .static_methods import _required_exp, _rgb_to_hex


@commands.command(pass_context=True, no_pm=True)
async def lvlinfo(self, ctx, user: discord.Member = None):
    """Gives more specific details about user profile image."""

    if not user:
        user = ctx.message.author
    userinfo = db.users.find_one({"user_id": str(str(user.id))})

    guild = ctx.message.guild

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("**Leveler commands for this guild are disabled!**")
        return

    # creates user if doesn't exist
    await self._create_user(user, guild)
    msg = ""
    msg += "Name: {}\n".format(user.name)
    msg += "Title: {}\n".format(userinfo["title"])
    msg += "Reps: {}\n".format(userinfo["rep"])
    msg += "guild Level: {}\n".format(userinfo["servers"][str(guild.id)]["level"])
    total_guild_exp = 0
    for i in range(userinfo["servers"][str(guild.id)]["level"]):
        total_guild_exp += _required_exp(i)
    total_guild_exp += userinfo["servers"][str(guild.id)]["current_exp"]
    msg += "guild Exp: {}\n".format(total_guild_exp)
    msg += "Total Exp: {}\n".format(userinfo["total_exp"])
    msg += "Info: {}\n".format(userinfo["info"])
    msg += "Profile background: {}\n".format(userinfo["profile_background"])
    msg += "Rank background: {}\n".format(userinfo["rank_background"])
    msg += "Levelup background: {}\n".format(userinfo["levelup_background"])
    if "profile_info_color" in userinfo.keys() and userinfo["profile_info_color"]:
        msg += "Profile info color: {}\n".format(
            _rgb_to_hex(userinfo["profile_info_color"])
        )
    if "profile_exp_color" in userinfo.keys() and userinfo["profile_exp_color"]:
        msg += "Profile exp color: {}\n".format(
            _rgb_to_hex(userinfo["profile_exp_color"])
        )
    if "rep_color" in userinfo.keys() and userinfo["rep_color"]:
        msg += "Rep section color: {}\n".format(_rgb_to_hex(userinfo["rep_color"]))
    if "badge_col_color" in userinfo.keys() and userinfo["badge_col_color"]:
        msg += "Badge section color: {}\n".format(
            _rgb_to_hex(userinfo["badge_col_color"])
        )
    if "rank_info_color" in userinfo.keys() and userinfo["rank_info_color"]:
        msg += "Rank info color: {}\n".format(_rgb_to_hex(userinfo["rank_info_color"]))
    if "rank_exp_color" in userinfo.keys() and userinfo["rank_exp_color"]:
        msg += "Rank exp color: {}\n".format(_rgb_to_hex(userinfo["rank_exp_color"]))
    if "levelup_info_color" in userinfo.keys() and userinfo["levelup_info_color"]:
        msg += "Level info color: {}\n".format(
            _rgb_to_hex(userinfo["levelup_info_color"])
        )
    msg += "Badges: "
    msg += ", ".join(userinfo["badges"])

    em = discord.Embed(description=msg, colour=user.colour)
    em.set_author(
        name="Profile Information for {}".format(user.name), icon_url=user.avatar_url
    )
    await ctx.send(embed=em)
