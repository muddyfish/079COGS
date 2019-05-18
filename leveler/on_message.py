import discord
from discord.utils import find
from redbot.core import bank
import random
import time
from PIL import ImageFont, Image, ImageDraw
from .path_munger import font_thin_file
from .config import db
from .static_methods import _add_corners, _required_exp, _center, _contrast, get_user_name
from io import BytesIO
from aiohttp import ClientSession

prefix = "!"


async def draw_levelup(bot, user):
    # fonts
    level_fnt = ImageFont.truetype(font_thin_file, 23)

    user_info = db.user(user)
    member_info = db.member(user)

    # get urls
    bg_url = await user_info.levelup_background()

    async with ClientSession(loop=bot.loop) as session:
        async with session.get(bg_url) as r:
            bg_image = Image.open(BytesIO(await r.content.read())).convert("RGBA")

        async with session.get(user.avatar_url) as r:
            profile_image = Image.open(BytesIO(await r.content.read())).convert("RGBA")

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
    info_color = await user_info.levelup_info_color()
    info_color = (
        info_color[0],
        info_color[1],
        info_color[2],
        150,
    )

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
    lvl_text = f"LEVEL {await member_info.level()}"
    draw.text(
        (_center(60, 170, lvl_text, level_fnt), 23),
        lvl_text,
        font=level_fnt,
        fill=level_up_text,
    )  # Level Number

    result = Image.alpha_composite(result, process)
    result = _add_corners(result, int(height / 2))
    return result


async def _handle_on_message(bot, message):
    # try:
    text = message.content
    guild = message.guild
    user = message.author
    # creates user if doesn't exist, bots are not logged.
    curr_time = time.time()

    if not guild or await db.guild(guild).disabled():
        return
    if user.bot:
        return

    member_info = db.member(user)

    if float(curr_time) - float(await member_info.chat_block()) >= await db.chat_cooldown() and not any(
        text.startswith(x) for x in prefix
    ):
        await _process_exp(bot, message, random.randint(15, 20))
        await _give_chat_credit(user)


async def _give_chat_credit(user):
    await bank.deposit_credits(user, await db.guild(user.guild).msg_credits())


async def _process_exp(bot, message, exp: int):
    channel = message.channel
    user = message.author

    user_info = db.user(user)
    total_exp = await user_info.total_exp()
    await user_info.total_exp.set(total_exp + exp)

    member_info = db.member(user)
    level = await member_info.level()
    required = _required_exp(level)
    current_exp = await member_info.current_exp()

    if current_exp + exp >= required:
        await member_info.level.set(level + 1)
        await member_info.current_exp.set(current_exp + exp - required)
        await _handle_levelup(bot, user, channel)
    else:
        await member_info.current_exp.set(current_exp + exp)
    await member_info.chat_block.set(time.time())


async def _handle_levelup(bot, user, channel):
    guild = user.guild

    guild_info = db.guild(guild)
    user_info = db.user(user)
    member_info = db.member(user)
    name = await get_user_name(user)
    level = await member_info.level()

    if await db.guild(guild).lvl_msg():  # if lvl msg is enabled
        lock_channel = await db.guild(guild).lvl_msg_lock()
        if lock_channel:
            channel = find(lambda m: m.id == lock_channel, guild.channels)

        guild_identifier = guild.name
        # private message takes precedent, of course
        if await db.guild(guild).private_lvl_msg():
            guild_identifier = "on {}".format(guild.name)
            channel = user
            name = "You"

        image = await draw_levelup(bot, user)
        image_buffer = BytesIO()
        image.save(image_buffer, "png")
        image_buffer.seek(0)

        await channel.send(
            f"**{name} just gained a level {guild_identifier}!**",
            file=discord.File(filename="levelup.png", fp=image_buffer),
        )

    # add to appropriate role if necessary
    for role in guild.roles:
        role_info = db.role(role)
        if await role_info.level() == level:
            await user.add_roles(role)

            remove_role = await role_info.remove_role()
            if remove_role is not None:
                remove_role_obj = discord.utils.find(
                    lambda r: r.id == remove_role,
                    guild.roles,
                )
                if remove_role_obj is not None:
                    await user.remove_roles(remove_role_obj)
            else:
                await channel.send("Error. Could not find role to remove")

    # add appropriate badge if necessary
    try:
        linked_badges = await guild_info.badge_links()
        for badge_name, badge_level in linked_badges.items():
            if badge_level == level:
                guild_badges = await guild_info.badges()
                user_badges = await user_info.badges()
                badge_id = f"{badge_name}_{guild.id}"

                user_badges[badge_id] = guild_badges[badge_name]
                await user_info.badges.set(user_badges)
    except:
        await channel.send("Error. Badge was not given!")
