from redbot.core import commands
import random
from ..leveler import db
from ..static_methods import _hex_to_rgb, _is_hex

prefix = "!"


@commands.group(name="lvlset", pass_context=True)
async def lvlset(self, ctx):
    """Profile Configuration Options"""
    if ctx.invoked_subcommand is None:
        return


@lvlset.group(name="profile", pass_context=True)
async def profileset(self, ctx):
    """Profile options"""
    if ctx.invoked_subcommand is None or isinstance(ctx.invoked_subcommand, commands.Group):
        return


@lvlset.group(name="rank", pass_context=True)
async def rankset(self, ctx):
    """Rank options"""
    if ctx.invoked_subcommand is None or isinstance(ctx.invoked_subcommand, commands.Group):
        return


@lvlset.group(name="levelup", pass_context=True)
async def levelupset(self, ctx):
    """Level-Up options"""
    if ctx.invoked_subcommand is None or isinstance(ctx.invoked_subcommand, commands.Group):
        return


@profileset.command(name="color", pass_context=True, no_pm=True)
async def profilecolors(self, ctx, section: str, color: str):
    """Set info color. e.g [p]lvlset profile color [exp|rep|badge|info|all] [default|white|hex|auto]"""
    user = ctx.message.author
    guild = ctx.message.guild
    # creates user if doesn't exist
    await self._create_user(user, guild)
    userinfo = db.users.find_one({"user_id": str(str(user.id))})

    section = section.lower()
    default_info_color = (30, 30, 30, 200)
    white_info_color = (150, 150, 150, 180)
    default_rep = (92, 130, 203, 230)
    default_badge = (128, 151, 165, 230)
    default_exp = (255, 255, 255, 230)
    default_a = 200

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("**Leveler commands for this guild are disabled!**")
        return

    if "text_only" in self.settings and str(guild.id) in self.settings["text_only"]:
        await ctx.send("**Text-only commands allowed.**")
        return

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

        hex_colors = await self._auto_color(userinfo["profile_background"], color_ranks)
        set_color = []
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
        await ctx.send("**Not a valid color. (default, hex, white, auto)**")
        return

    if section == "all":
        if len(set_color) == 1:
            db.users.update_one(
                {"user_id": str(str(user.id))},
                {
                    "$set": {
                        "profile_exp_color": set_color[0],
                        "rep_color": set_color[0],
                        "badge_col_color": set_color[0],
                        "profile_info_color": set_color[0],
                    }
                },
            )
        elif color == "default":
            db.users.update_one(
                {"user_id": str(str(user.id))},
                {
                    "$set": {
                        "profile_exp_color": default_exp,
                        "rep_color": default_rep,
                        "badge_col_color": default_badge,
                        "profile_info_color": default_info_color,
                    }
                },
            )
        elif color == "auto":
            db.users.update_one(
                {"user_id": str(str(user.id))},
                {
                    "$set": {
                        "profile_exp_color": set_color[0],
                        "rep_color": set_color[1],
                        "badge_col_color": set_color[2],
                        "profile_info_color": set_color[3],
                    }
                },
            )
        await ctx.send("**Colors for profile set.**")
    else:
        db.users.update_one(
            {"user_id": str(str(user.id))}, {"$set": {section_name: set_color[0]}}
        )
        await ctx.send("**Color for profile {} set.**".format(section))


@rankset.command(name="color", pass_context=True, no_pm=True)
async def rankcolors(self, ctx, section: str, color: str = None):
    """Set info color. e.g [p]lvlset rank color [exp|info] [default|white|hex|auto]"""
    user = ctx.message.author
    guild = ctx.message.guild
    # creates user if doesn't exist
    await self._create_user(user, guild)
    userinfo = db.users.find_one({"user_id": str(str(user.id))})

    section = section.lower()
    default_info_color = (30, 30, 30, 200)
    white_info_color = (150, 150, 150, 180)
    default_exp = (255, 255, 255, 230)
    default_rep = (92, 130, 203, 230)
    default_badge = (128, 151, 165, 230)
    default_a = 200

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("**Leveler commands for this guild are disabled!**")
        return

    if "text_only" in self.settings and str(guild.id) in self.settings["text_only"]:
        await ctx.send("**Text-only commands allowed.**")
        return

    # get correct section for db query
    if section == "exp":
        section_name = "rank_exp_color"
    elif section == "info":
        section_name = "rank_info_color"
    elif section == "all":
        section_name = "all"
    else:
        await ctx.send("**Not a valid section. (exp, info, all)**")
        return

    # get correct color choice
    if color == "auto":
        if section == "exp":
            color_ranks = [random.randint(2, 3)]
        elif section == "info":
            color_ranks = [random.randint(0, 1)]
        elif section == "all":
            color_ranks = [random.randint(2, 3), random.randint(0, 1)]

        hex_colors = await self._auto_color(userinfo["rank_background"], color_ranks)
        set_color = []
        for hex_color in hex_colors:
            color_temp = _hex_to_rgb(hex_color, default_a)
            set_color.append(color_temp)
    elif color == "white":
        set_color = [white_info_color]
    elif color == "default":
        if section == "exp":
            set_color = [default_exp]
        elif section == "info":
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
            db.users.update_one(
                {"user_id": str(str(user.id))},
                {"$set": {"rank_exp_color": set_color[0], "rank_info_color": set_color[0]}},
            )
        elif color == "default":
            db.users.update_one(
                {"user_id": str(str(user.id))},
                {
                    "$set": {
                        "rank_exp_color": default_exp,
                        "rank_info_color": default_info_color,
                    }
                },
            )
        elif color == "auto":
            db.users.update_one(
                {"user_id": str(str(user.id))},
                {"$set": {"rank_exp_color": set_color[0], "rank_info_color": set_color[1]}},
            )
        await ctx.send("**Colors for rank set.**")
    else:
        db.users.update_one(
            {"user_id": str(str(user.id))}, {"$set": {section_name: set_color[0]}}
        )
        await ctx.send("**Color for rank {} set.**".format(section))


@levelupset.command(name="color", pass_context=True, no_pm=True)
async def levelupcolors(self, ctx, section: str, color: str = None):
    """Set info color. e.g [p]lvlset color [info] [default|white|hex|auto]"""
    user = ctx.message.author
    guild = ctx.message.guild
    # creates user if doesn't exist
    await self._create_user(user, guild)
    userinfo = db.users.find_one({"user_id": str(str(user.id))})

    section = section.lower()
    default_info_color = (30, 30, 30, 200)
    white_info_color = (150, 150, 150, 180)
    default_a = 200

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("**Leveler commands for this guild are disabled!**")
        return

    if "text_only" in self.settings and str(guild.id) in self.settings["text_only"]:
        await ctx.send("**Text-only commands allowed.**")
        return

    # get correct section for db query
    if section == "info":
        section_name = "levelup_info_color"
    else:
        await ctx.send("**Not a valid section. (info)**")
        return

    # get correct color choice
    if color == "auto":
        if section == "info":
            color_ranks = [random.randint(0, 1)]
        hex_colors = await self._auto_color(userinfo["levelup_background"], color_ranks)
        set_color = []
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

    db.users.update_one({"user_id": str(str(user.id))}, {"$set": {section_name: set_color[0]}})
    await ctx.send("**Color for level-up {} set.**".format(section))


@profileset.command(pass_context=True, no_pm=True)
async def info(self, ctx, *, info):
    """Set your user info."""
    user = ctx.message.author
    guild = ctx.message.guild
    # creates user if doesn't exist
    await self._create_user(user, guild)
    max_char = 150

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("Leveler commands for this guild are disabled.")
        return

    if len(info) < max_char:
        db.users.update_one({"user_id": str(str(user.id))}, {"$set": {"info": info}})
        await ctx.send("**Your info section has been succesfully set!**")
    else:
        await ctx.send(
            "**Your description has too many characters! Must be <{}**".format(max_char)
        )


@levelupset.command(name="bg", pass_context=True, no_pm=True)
async def levelbg(self, ctx, *, image_name: str):
    """Set your level background"""
    user = ctx.message.author
    guild = ctx.message.guild
    # creates user if doesn't exist
    await self._create_user(user, guild)

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("Leveler commands for this guild are disabled.")
        return

    if "text_only" in self.settings and str(guild.id) in self.settings["text_only"]:
        await ctx.send("**Text-only commands allowed.**")
        return

    if image_name in self.backgrounds["levelup"].keys():
        if await self._process_purchase(ctx):
            db.users.update_one(
                {"user_id": str(str(user.id))},
                {"$set": {"levelup_background": self.backgrounds["levelup"][image_name]}},
            )
            await ctx.send("**Your new level-up background has been succesfully set!**")
    else:
        await ctx.send(
            "That is not a valid bg. See available bgs at `{}backgrounds levelup`".format(
                prefix[0]
            )
        )


@profileset.command(name="bg", pass_context=True, no_pm=True)
async def profilebg(self, ctx, *, image_name: str):
    """Set your profile background"""
    user = ctx.message.author
    guild = ctx.message.guild
    # creates user if doesn't exist
    await self._create_user(user, guild)

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("Leveler commands for this guild are disabled.")
        return

    if "text_only" in self.settings and str(guild.id) in self.settings["text_only"]:
        await ctx.send("**Text-only commands allowed.**")
        return

    if image_name in self.backgrounds["profile"].keys():
        if await self._process_purchase(ctx):
            db.users.update_one(
                {"user_id": str(str(user.id))},
                {"$set": {"profile_background": self.backgrounds["profile"][image_name]}},
            )
            await ctx.send("**Your new profile background has been succesfully set!**")
    else:
        await ctx.send(
            "That is not a valid bg. See available bgs at `{}backgrounds profile`".format(
                prefix[0]
            )
        )


@rankset.command(name="bg", pass_context=True, no_pm=True)
async def rankbg(self, ctx, *, image_name: str):
    """Set your rank background"""
    user = ctx.message.author
    guild = ctx.message.guild
    # creates user if doesn't exist
    await self._create_user(user, guild)

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("Leveler commands for this guild are disabled.")
        return

    if "text_only" in self.settings and str(guild.id) in self.settings["text_only"]:
        await ctx.send("**Text-only commands allowed.**")
        return

    if image_name in self.backgrounds["rank"].keys():
        if await self._process_purchase(ctx):
            db.users.update_one(
                {"user_id": str(str(user.id))},
                {"$set": {"rank_background": self.backgrounds["rank"][image_name]}},
            )
            await ctx.send("**Your new rank background has been succesfully set!**")
    else:
        await ctx.send(
            "That is not a valid bg. See available bgs at `{}backgrounds rank`".format(
                prefix[0]
            )
        )


@profileset.command(pass_context=True, no_pm=True)
async def title(self, ctx, *, title):
    """Set your title."""
    user = ctx.message.author
    guild = ctx.message.guild
    # creates user if doesn't exist
    await self._create_user(user, guild)
    userinfo = db.users.find_one({"user_id": str(str(user.id))})
    max_char = 20

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("Leveler commands for this guild are disabled.")
        return

    if len(title) < max_char:
        userinfo["title"] = title
        db.users.update_one({"user_id": str(str(user.id))}, {"$set": {"title": title}})
        await ctx.send("**Your title has been succesfully set!**")
    else:
        await ctx.send("**Your title has too many characters! Must be <{}**".format(max_char))
