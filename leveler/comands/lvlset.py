from redbot.core import commands
import random
from ..config import db
from ..static_methods import _hex_to_rgb, _is_hex, _auto_color, process_purchase
from ..permissions import leveler_enabled


prefix = "!"


@commands.group(name="lvlset", pass_context=True)
@leveler_enabled
async def lvlset(ctx):
    """Profile Configuration Options"""
    if ctx.invoked_subcommand is None:
        return


@lvlset.group(name="profile", pass_context=True)
async def profileset(ctx):
    """Profile options"""
    if ctx.invoked_subcommand is None or isinstance(ctx.invoked_subcommand, commands.Group):
        return


@lvlset.group(name="rank", pass_context=True)
async def rankset(ctx):
    """Rank options"""
    if ctx.invoked_subcommand is None or isinstance(ctx.invoked_subcommand, commands.Group):
        return


@lvlset.group(name="levelup", pass_context=True)
async def levelupset(ctx):
    """Level-Up options"""
    if ctx.invoked_subcommand is None or isinstance(ctx.invoked_subcommand, commands.Group):
        return


@profileset.command(name="color", pass_context=True, no_pm=True)
async def profilecolors(ctx, section: str, color: str):
    """Set info color. e.g [p]lvlset profile color [exp|rep|badge|info|all] [default|white|hex|auto]"""
    user = ctx.message.author
    user_info = db.user(user)

    section = section.lower()
    default_info_color = (30, 30, 30, 200)
    white_info_color = (150, 150, 150, 180)
    default_rep = (92, 130, 203, 230)
    default_badge = (128, 151, 165, 230)
    default_exp = (255, 255, 255, 230)
    default_a = 200

    all_sections = {
        "rep": "rep_color",
        "exp": "profile_exp_color",
        "badge": "badge_col_color",
        "info": "profile_info_color",
        "all": "all"
    }
    section_name = all_sections.get(section, None)
    if section_name is None:
        return await ctx.send("**Not a valid section. (rep, exp, badge, info, all)**")

    # get correct color choice
    set_color = []
    if color == "auto":
        if section == "exp":
            color_ranks = [random.randint(2, 3)]
        elif section == "rep":
            color_ranks = [random.randint(2, 3)]
        elif section == "badge":
            color_ranks = [0]  # most prominent color
        elif section == "info":
            color_ranks = [random.randint(0, 1)]
        else:
            color_ranks = [random.randint(2, 3), random.randint(2, 3), 0, random.randint(0, 2)]

        hex_colors = await _auto_color(ctx, await user_info.profile_background(), color_ranks)
        for hex_color in hex_colors:
            color_temp = _hex_to_rgb(hex_color, default_a)
            set_color.append(color_temp)

    elif color == "white":
        set_color = [white_info_color]
    elif color == "default":
        if section == "exp":
            set_color = [default_exp]
        elif section == "rep":
            set_color = [default_rep]
        elif section == "badge":
            set_color = [default_badge]
        elif section == "info":
            set_color = [default_info_color]
        elif section == "all":
            set_color = [default_exp, default_rep, default_badge, default_info_color]
    elif _is_hex(color):
        set_color = [_hex_to_rgb(color, default_a)]
    else:
        return await ctx.send("**Not a valid color. (default, hex, white, auto)**")

    if section == "all":
        if len(set_color) == 1:
            await user_info.profile_exp_color.set(set_color[0])
            await user_info.rep_color.set(set_color[0])
            await user_info.badge_col_color.set(set_color[0])
            await user_info.profile_info_color.set(set_color[0])
        elif color == "default":
            await user_info.profile_exp_color.set(default_exp)
            await user_info.rep_color.set(default_rep)
            await user_info.badge_col_color.set(default_badge)
            await user_info.profile_info_color.set(default_info_color)
        elif color == "auto":
            await user_info.profile_exp_color.set(set_color[0])
            await user_info.rep_color.set(set_color[1])
            await user_info.badge_col_color.set(set_color[2])
            await user_info.profile_info_color.set(set_color[3])
        await ctx.send("**Colors for profile set.**")
    else:
        await user_info.get_attr(section_name).set(set_color[0])
        await ctx.send("**Color for profile {} set.**".format(section))


@rankset.command(name="color", pass_context=True, no_pm=True)
async def rankcolors(ctx, section: str, color: str = None):
    """Set info color. e.g [p]lvlset rank color [info] [default|white|hex|auto]"""
    user = ctx.message.author
    user_info = db.user(user)

    section = section.lower()
    default_info_color = (30, 30, 30, 200)
    white_info_color = (150, 150, 150, 180)
    default_exp = (255, 255, 255, 230)
    default_rep = (92, 130, 203, 230)
    default_badge = (128, 151, 165, 230)
    default_a = 200

    # get correct section for db query
    if section == "info":
        section_name = "rank_info_color"
    elif section == "all":
        section_name = "all"
    else:
        await ctx.send("**Not a valid section. (info, all)**")
        return

    # get correct color choice
    set_color = []
    if color == "auto":
        color_ranks = [random.randint(2, 3), random.randint(0, 1)]
        if section == "info":
            color_ranks = [random.randint(0, 1)]

        hex_colors = await _auto_color(await user_info.rank_background, color_ranks)
        for hex_color in hex_colors:
            color_temp = _hex_to_rgb(hex_color, default_a)
            set_color.append(color_temp)
    elif color == "white":
        set_color = [white_info_color]
    elif color == "default":
        if section == "info":
            set_color = [default_info_color]
        elif section == "all":
            set_color = [default_exp, default_rep, default_badge, default_info_color]
    elif _is_hex(color):
        set_color = [_hex_to_rgb(color, default_a)]
    else:
        await ctx.send("**Not a valid color. (default, hex, white, auto)**")
        return

    if section == "all":
        if len(set_color) == 1:
            await user_info.rank_info_color.set(set_color[0])
        elif color == "default":
            await user_info.rank_info_color.set(default_info_color)
        elif color == "auto":
            await user_info.rank_info_color.set(set_color[0])
        await ctx.send("**Colors for rank set.**")
    else:
        await user_info.get_attr(section_name).set(set_color[0])
        await ctx.send("**Color for rank {} set.**".format(section))


@levelupset.command(name="color", pass_context=True, no_pm=True)
async def levelupcolors(ctx, section: str, color: str = None):
    """Set info color. e.g [p]lvlset color [info] [default|white|hex|auto]"""
    user = ctx.message.author
    user_info = db.user(user)

    section = section.lower()
    default_info_color = (30, 30, 30, 200)
    white_info_color = (150, 150, 150, 180)
    default_a = 200

    # get correct section for db query
    if section == "info":
        section_name = "levelup_info_color"
    else:
        await ctx.send("**Not a valid section. (info)**")
        return

    # get correct color choice
    set_color = []
    if color == "auto":
        color_ranks = [random.randint(0, 1)]
        hex_colors = await _auto_color(ctx, await user_info.levelup_background(), color_ranks)
        for hex_color in hex_colors:
            color_temp = _hex_to_rgb(hex_color, default_a)
            set_color.append(color_temp)
    elif color == "white":
        set_color = [white_info_color]
    elif color == "default":
        if section == "info":
            set_color = [default_info_color]
    elif _is_hex(color):
        set_color = [_hex_to_rgb(color, default_a)]
    else:
        await ctx.send("**Not a valid color. (default, hex, white, auto)**")
        return

    await user_info.get_attr(section_name).set(set_color[0])
    await ctx.send("**Color for level-up {} set.**".format(section))


@profileset.command(pass_context=True, no_pm=True)
async def info(ctx, *, info):
    """Set your user info."""
    user = ctx.message.author
    user_info = db.user(user)

    max_char = 150

    if len(info) < max_char:
        await user_info.info.set(info)
        await ctx.send("**Your info section has been succesfully set!**")
    else:
        await ctx.send(
            "**Your description has too many characters! Must be <{}**".format(max_char)
        )


@levelupset.command(name="bg", pass_context=True, no_pm=True)
async def levelbg(ctx, *, image_name: str):
    """Set your level background"""
    user = ctx.message.author
    user_info = db.user(user)
    backgrounds = await db.backgrounds()

    if image_name in backgrounds["levelup"].keys():
        if await process_purchase(ctx):
            await user_info.levelup_background.set(backgrounds["levelup"][image_name])
            await ctx.send("**Your new level-up background has been successfully set!**")
    else:
        await ctx.send(
            "That is not a valid bg. See available bgs at `{}backgrounds levelup`".format(
                prefix[0]
            )
        )


@profileset.command(name="bg", pass_context=True, no_pm=True)
async def profilebg(ctx, *, image_name: str):
    """Set your profile background"""
    user = ctx.message.author
    user_info = db.user(user)
    backgrounds = await db.backgrounds()

    if image_name in backgrounds["profile"].keys():
        if await process_purchase(ctx):
            await user_info.profile_background.set(backgrounds["profile"][image_name])
            await ctx.send("**Your new profile background has been successfully set!**")
    else:
        await ctx.send(
            "That is not a valid bg. See available bgs at `{}backgrounds profile`".format(
                prefix[0]
            )
        )


@rankset.command(name="bg", pass_context=True, no_pm=True)
async def rankbg(ctx, *, image_name: str):
    """Set your rank background"""
    user = ctx.message.author
    user_info = db.user(user)
    backgrounds = await db.backgrounds()

    if image_name in backgrounds["rank"].keys():
        if await process_purchase(ctx):
            await user_info.rank_background.set(backgrounds["rank"][image_name])
            await ctx.send("**Your new rank background has been succesfully set!**")
    else:
        await ctx.send(
            "That is not a valid bg. See available bgs at `{}backgrounds rank`".format(
                prefix[0]
            )
        )


@profileset.command(pass_context=True, no_pm=True)
async def title(ctx, *, title):
    """Set your title."""
    user = ctx.message.author
    user_info = db.user(user)
    max_char = 20

    if len(title) < max_char:
        await user_info.info.set(info)
        await ctx.send("**Your title has been succesfully set!**")
    else:
        await ctx.send("**Your title has too many characters! Must be <{}**".format(max_char))
