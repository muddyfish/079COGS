import discord
from discord.utils import find
from redbot.core import bank
import random
import time
from PIL import ImageFont, Image, ImageDraw
from .path_munger import fileIO
from .leveler import db, default_avatar_url
from .static_methods import _add_corners, _required_exp, _center, _contrast

prefix = "!"


async def draw_levelup(leveler, user, guild):
    # fonts
    font_thin_file = "fonts/Uni_Sans_Thin.ttf"
    level_fnt = ImageFont.truetype(font_thin_file, 23)

    userinfo = db.users.find_one({"user_id": str(str(user.id))})

    # get urls
    bg_url = userinfo["levelup_background"]
    profile_url = user.avatar_url

    async with leveler.session.get(bg_url) as r:
        image = await r.content.read()
    with open("temp/{}_temp_level_bg.png".format(str(user.id)), "wb") as f:
        f.write(image)
    try:
        async with leveler.session.get(profile_url) as r:
            image = await r.content.read()
    except:
        async with leveler.session.get(default_avatar_url) as r:
            image = await r.content.read()
    with open("temp/{}_temp_level_profile.png".format(str(user.id)), "wb") as f:
        f.write(image)

    bg_image = Image.open(
        "temp/{}_temp_level_bg.png".format(str(user.id))
    ).convert("RGBA")
    profile_image = Image.open(
        "temp/{}_temp_level_profile.png".format(str(user.id))
    ).convert("RGBA")

    # set canvas
    width = 176
    height = 67
    bg_color = (255, 255, 255, 0)
    result = Image.new("RGBA", (width, height), bg_color)
    process = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(process)

    # puts in background
    bg_image = bg_image.resize((width, height), Image.ANTIALIAS)
    bg_image = bg_image.crop((0, 0, width, height))
    result.paste(bg_image, (0, 0))

    # info section
    lvl_circle_dia = 60
    total_gap = 2
    border = int(total_gap / 2)
    info_section = Image.new("RGBA", (165, 55), (230, 230, 230, 20))
    info_section = _add_corners(info_section, int(lvl_circle_dia / 2))
    process.paste(info_section, (border, border))

    # draw transparent overlay
    if "levelup_info_color" in userinfo.keys():
        info_color = tuple(userinfo["levelup_info_color"])
        info_color = (
            info_color[0],
            info_color[1],
            info_color[2],
            150,
        )  # increase transparency
    else:
        info_color = (30, 30, 30, 150)

    for i in range(0, height):
        draw.rectangle(
            [(0, height - i), (width, height - i)],
            fill=(info_color[0], info_color[1], info_color[2], 255 - i * 3),
        )  # title overlay

    # draw circle
    multiplier = 6
    circle_left = 4
    circle_top = int((height - lvl_circle_dia) / 2)
    raw_length = lvl_circle_dia * multiplier
    # create mask
    mask = Image.new("L", (raw_length, raw_length), 0)
    draw_thumb = ImageDraw.Draw(mask)
    draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill=255, outline=0)

    # border
    lvl_circle = Image.new("RGBA", (raw_length, raw_length))
    draw_lvl_circle = ImageDraw.Draw(lvl_circle)
    draw_lvl_circle.ellipse([0, 0, raw_length, raw_length], fill=(250, 250, 250, 180))
    lvl_circle = lvl_circle.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
    lvl_bar_mask = mask.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
    process.paste(lvl_circle, (circle_left, circle_top), lvl_bar_mask)

    profile_size = lvl_circle_dia - total_gap
    # put in profile picture
    mask = mask.resize((profile_size, profile_size), Image.ANTIALIAS)
    profile_image = profile_image.resize((profile_size, profile_size), Image.ANTIALIAS)
    process.paste(profile_image, (circle_left + border, circle_top + border), mask)

    # write label text
    white_text = (250, 250, 250, 255)
    dark_text = (35, 35, 35, 230)
    level_up_text = _contrast(info_color, white_text, dark_text)
    lvl_text = "LEVEL {}".format(userinfo["servers"][str(guild.id)]["level"])
    draw.text(
        (_center(60, 170, lvl_text, level_fnt), 23),
        lvl_text,
        font=level_fnt,
        fill=level_up_text,
    )  # Level Number

    result = Image.alpha_composite(result, process)
    result = _add_corners(result, int(height / 2))
    filename = "temp/{}_level.png".format(str(user.id))
    result.save(filename, "PNG", quality=100)


async def _handle_on_message(leveler, message):
    # try:
    text = message.content
    guild = message.guild
    user = message.author
    # creates user if doesn't exist, bots are not logged.
    await leveler._create_user(user, guild)
    curr_time = time.time()
    userinfo = db.users.find_one({"user_id": str(str(user.id))})

    if not guild or str(guild.id) in leveler.settings["disabled_guilds"]:
        return
    if user.bot:
        return

    # check if chat_block exists
    if "chat_block" not in userinfo:
        userinfo["chat_block"] = 0

    if float(curr_time) - float(userinfo["chat_block"]) >= 120 and not any(
            text.startswith(x) for x in prefix
    ):
        await _process_exp(leveler, message, userinfo, random.randint(15, 20))
        await _give_chat_credit(leveler, user, guild)


async def _give_chat_credit(leveler, user, guild):
    try:
        if "msg_credits" in leveler.settings:
            await bank.deposit_credits(user, leveler.settings["msg_credits"][str(guild.id)])
    except:
        pass


async def _process_exp(leveler, message, userinfo, exp: int):
    guild = message.author.guild
    channel = message.channel
    user = message.author

    # add to total exp
    required = _required_exp(userinfo["servers"][str(guild.id)]["level"])
    try:
        db.users.update_one(
            {"user_id": str(str(user.id))},
            {"$set": {"total_exp": userinfo["total_exp"] + exp}},
        )
    except:
        pass
    if userinfo["servers"][str(guild.id)]["current_exp"] + exp >= required:
        userinfo["servers"][str(guild.id)]["level"] += 1
        db.users.update_one(
            {"user_id": str(str(user.id))},
            {
                "$set": {
                    "servers.{}.level".format(str(guild.id)): userinfo["servers"][
                        str(guild.id)
                    ]["level"],
                    "servers.{}.current_exp".format(str(guild.id)): userinfo["servers"][
                                                                        str(guild.id)
                                                                    ]["current_exp"]
                                                                    + exp
                                                                    - required,
                    "chat_block": time.time(),
                }
            },
        )
        await _handle_levelup(leveler, user, userinfo, guild, channel)
    else:
        db.users.update_one(
            {"user_id": str(str(user.id))},
            {
                "$set": {
                    "servers.{}.current_exp".format(str(guild.id)): userinfo["servers"][
                                                                        str(guild.id)
                                                                    ]["current_exp"]
                                                                    + exp,
                    "chat_block": time.time(),
                }
            },
        )


async def _handle_levelup(leveler, user, userinfo, guild, channel):
    if not isinstance(leveler.settings["lvl_msg"], list):
        leveler.settings["lvl_msg"] = []
        fileIO("settings.json", "save", leveler.settings)
    guild_identifier = ""  # super hacky
    name = leveler._is_mention(user)  # also super hacky
    new_level = str(userinfo["servers"][str(guild.id)]["level"])
    if str(guild.id) in leveler.settings["lvl_msg"]:  # if lvl msg is enabled
        # channel lock implementation
        if (
                "lvl_msg_lock" in leveler.settings.keys()
                and str(guild.id) in leveler.settings["lvl_msg_lock"].keys()
        ):
            channel_id = leveler.settings["lvl_msg_lock"][str(guild.id)]
            channel = find(lambda m: m.id == channel_id, guild.channels)

        # private message takes precedent, of course
        if (
                "private_lvl_msg" in leveler.settings
                and str(guild.id) in leveler.settings["private_lvl_msg"]
        ):
            guild_identifier = " on {}".format(guild.name)
            channel = user
            name = "You"

        if "text_only" in leveler.settings and str(guild.id) in leveler.settings["text_only"]:

            em = discord.Embed(
                description="**{} just gained a level{}! (LEVEL {})**".format(
                    name, guild_identifier, new_level
                ),
                colour=user.colour,
            )
            await channel.send("", embed=em)
        else:
            await leveler.draw_levelup(user, guild)

            await channel.send(
                "**{} just gained a level{}!**".format(name, guild_identifier),
                file=discord.File("temp/{}_level.png".format(str(user.id))),
            )

    # add to appropriate role if necessary
    try:
        guild_roles = db.roles.find_one({"guild_id": str(guild.id)})
        if guild_roles != None:
            for role in guild_roles["roles"].keys():
                if int(guild_roles["roles"][role]["level"]) == int(new_level):
                    role_obj = discord.utils.find(lambda r: r.name == role, guild.roles)
                    await user.add_roles(role_obj)

                    if guild_roles["roles"][role]["remove_role"] != None:
                        remove_role_obj = discord.utils.find(
                            lambda r: r.name == guild_roles["roles"][role]["remove_role"],
                            guild.roles,
                        )
                        if remove_role_obj != None:
                            await user.remove_roles(remove_role_obj)
    except:
        await channel.send("Role was not set. Missing Permissions!")

    # add appropriate badge if necessary
    try:
        guild_linked_badges = db.badgelinks.find_one({"guild_id": str(guild.id)})
        if guild_linked_badges != None:
            for badge_name in guild_linked_badges["badges"]:
                if int(guild_linked_badges["badges"][badge_name]) == int(new_level):
                    guild_badges = db.badges.find_one({"guild_id": str(guild.id)})
                    if guild_badges != None and badge_name in guild_badges["badges"].keys():
                        userinfo_db = db.users.find_one({"user_id": str(str(user.id))})
                        new_badge_name = "{}_{}".format(badge_name, str(guild.id))
                        userinfo_db["badges"][new_badge_name] = guild_badges["badges"][
                            badge_name
                        ]
                        db.users.update_one(
                            {"user_id": str(str(user.id))},
                            {"$set": {"badges": userinfo_db["badges"]}},
                        )
    except:
        await channel.send("Error. Badge was not given!")
