from redbot.core import commands
import discord
from ..config import db
from ..static_methods import _required_exp, _rgb_to_hex


@commands.command(pass_context=True, no_pm=True)
async def lvlinfo(ctx, user: discord.Member = None):
    """Gives more specific details about user profile image."""

    if not user:
        user = ctx.message.author
    user_info = db.user(user)
    member_info = db.member(user)

    level = await member_info.level()
    current_exp = await member_info.current_exp()

    msg = ""
    msg += "Name: {}\n".format(user.name)
    msg += f"Title: {await user_info.title()}\n"
    msg += f"Reps: {await user_info.rep()}\n"
    msg += f"Guild Level: {level}\n"
    total_guild_exp = 0
    for i in range(level):
        total_guild_exp += _required_exp(i)
    total_guild_exp += current_exp
    msg += f"Guild Exp: {total_guild_exp}\n"
    msg += f"Total Exp: {await user_info.total_exp()}\n"
    msg += f"Info: {await user_info.info()}\n"
    msg += f"Profile background: {await user_info.profile_background()}\n"
    msg += f"Rank background: {await user_info.rank_background()}\n"
    msg += f"Levelup background: {await user_info.levelup_background()}\n"

    profile_info_color = await user_info.profile_info_color()
    if profile_info_color:
        msg += f"Profile info color: {_rgb_to_hex(profile_info_color)}\n"

    profile_exp_color = await user_info.profile_exp_color()
    if profile_exp_color:
        msg += f"Profile exp color: {_rgb_to_hex(profile_exp_color)}\n"

    rep_color = await user_info.rep_color()
    if rep_color:
        msg += f"Rep section color: {_rgb_to_hex(rep_color)}\n"

    badge_col_color = await user_info.badge_col_color()
    if badge_col_color:
        msg += f"Badge section color: {_rgb_to_hex(badge_col_color)}\n"

    rank_info_color = await member_info.rank_info_color()
    if rank_info_color:
        msg += f"Rank info color: {_rgb_to_hex(rank_info_color)}\n"

    levelup_info_color = await user_info.levelup_info_color()
    if levelup_info_color:
        msg += f"Level info color: {_rgb_to_hex(levelup_info_color)}\n"
    msg += "Badges: "
    msg += f", ".join(await user_info.badges())

    em = discord.Embed(description=msg, colour=user.colour)
    em.set_author(
        name=f"Profile Information for {user.name}",
        icon_url=user.avatar_url
    )
    await ctx.send(embed=em)
