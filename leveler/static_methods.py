from math import sqrt
import os
from .path_munger import fileIO
from PIL import Image, ImageDraw
import operator
import re
import random
from aiohttp import ClientSession

import scipy
import scipy.misc
import scipy.cluster

from io import BytesIO

from .config import db

from typing import Dict
from discord import Member, Guild
from redbot.core import bank

user_directory = "users"
prefix = "!"


async def get_user_name(user: Member) -> str:
    if await db.mention():
        return user.mention
    else:
        return user.name


def get_user_display_name(user: Member, max_length: int) -> str:
    if user.name == user.display_name:
        return user.name
    else:
        return "{} ({})".format(
            user.name,
            _truncate_text(user.display_name, max_length - len(user.name) - 3),
            max_length,
        )


def pop_database():
    if os.path.exists("users"):
        for userid in os.listdir(user_directory):
            userinfo = fileIO("users/{}/info.json".format(str(userid)), "load")
            userinfo["user_id"] = str(userid)
            db.users.insert_one(userinfo)


def _rgb_to_hex(rgb):
    rgb = tuple(rgb[:3])
    return "#%02x%02x%02x" % rgb


def _truncate_text(text, max_length):
    if len(text) > max_length:
        if text.strip("$").isdigit():
            text = int(text.strip("$"))
            return "${:.2E}".format(text)
        return text[: max_length - 3] + "..."
    return text


# finds the the pixel to center the text
def _center(start, end, text, font):
    dist = end - start
    width = font.getsize(text)[0]
    start_pos = start + ((dist - width) / 2)
    return int(start_pos)


# calculates required exp for next level
def _required_exp(level: int):
    if level < 0:
        return 0
    return 139 * level + 65


def _level_exp(level: int):
    return level * 65 + 139 * level * (level - 1) // 2


def _find_level(total_exp):
    # this is specific to the function above
    return int((1 / 278) * (9 + sqrt(81 + 1112 * total_exp)))


def _add_corners(im, rad, multiplier=6):
    raw_length = rad * 2 * multiplier
    circle = Image.new("L", (raw_length, raw_length), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, raw_length, raw_length), fill=255)
    circle = circle.resize((rad * 2, rad * 2), Image.ANTIALIAS)

    alpha = Image.new("L", im.size, 255)
    w, h = im.size
    alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
    alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
    alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
    alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
    im.putalpha(alpha)
    return im


# returns color that contrasts better in background
def _contrast(bg_color, color1, color2):
    color1_ratio = _contrast_ratio(bg_color, color1)
    color2_ratio = _contrast_ratio(bg_color, color2)
    if color1_ratio >= color2_ratio:
        return color1
    else:
        return color2


def _luminance(color):
    # convert to greyscale
    luminance = float((0.2126 * color[0]) + (0.7152 * color[1]) + (0.0722 * color[2]))
    return luminance


def _contrast_ratio(bgcolor, foreground):
    f_lum = float(_luminance(foreground) + 0.05)
    bg_lum = float(_luminance(bgcolor) + 0.05)

    if bg_lum > f_lum:
        return bg_lum / f_lum
    else:
        return f_lum / bg_lum


def _is_hex(color: str):
    if color is not None and len(color) != 4 and len(color) != 7:
        return False
    reg_ex = r"^#(?:[0-9a-fA-F]{3}){1,2}$"
    return re.search(reg_ex, str(color))


async def guild_exp(guild: Guild) -> Dict[int, int]:
    users = {}
    for member_id, member_info in (await db.all_members(guild)).items():
        guild_exp = 0
        for i in range(member_info["level"]):
            guild_exp += _required_exp(i)
        guild_exp += member_info["current_exp"]
        users[member_id] = guild_exp
    return users


async def guild_level(guild: Guild) -> Dict[int, int]:
    users = {}
    for member_id, member_info in await db.all_members(guild):
        users[member_id] = member_info["level"]
    return users


async def all_rep() -> Dict[int, int]:
    return {member_id: member_info["rep"] for member_id, member_info in (await db.all_users()).items()}


async def all_exp() -> Dict[int, int]:
    return {member_id: member_info["total_exp"] for member_id, member_info in (await db.all_users()).items()}


async def _find_guild_rank(user: Member) -> int:
    users = await guild_exp(user.guild)
    user_exp = users.get(user.id, 0)
    return sum(1 for xp in users.values() if xp > user_exp)


async def _find_guild_rep_rank(user, guild):
    targetid = str(user.id)
    users = []
    for userinfo in db.users.find({}):
        if "servers" in userinfo and str(guild.id) in userinfo["servers"]:
            users.append((userinfo["user_id"], userinfo["rep"]))

    sorted_list = sorted(users, key=operator.itemgetter(1), reverse=True)

    rank = 1
    for a_user in sorted_list:
        if a_user[0] == targetid:
            return rank
        rank += 1


async def _find_guild_level_rank(user, guild):
    targetid = str(user.id)
    users = []
    for userinfo in db.users.find({}):
        if "servers" in userinfo and str(guild.id) in userinfo["servers"]:
            users.append((userinfo["user_id"], userinfo["servers"][str(guild.id)]["level"]))
        sorted_list = sorted(users, key=operator.itemgetter(1), reverse=True)

        rank = 1
        for a_user in sorted_list:
            if a_user[0] == targetid:
                return rank
            rank += 1


async def _find_guild_exp(user, guild):
    guild_exp = 0
    userinfo = db.users.find_one({"user_id": str(str(user.id))})

    try:
        for i in range(userinfo["servers"][str(guild.id)]["level"]):
            guild_exp += _required_exp(i)
        guild_exp += userinfo["servers"][str(guild.id)]["current_exp"]
        return guild_exp
    except:
        return guild_exp


async def _find_global_rank(user):
    users = await all_exp()
    user_exp = users.get(user.id, 0)
    return sum(1 for xp in users.values() if xp > user_exp)


async def _find_global_rep_rank(user):
    users = await all_rep()
    user_rep = users.get(user.id, 0)
    return sum(1 for rep in users.values() if rep > user_rep)


def _badge_convert_dict(userinfo):
    if "badges" not in userinfo or not isinstance(userinfo["badges"], dict):
        db.users.update_one({"user_id": userinfo["user_id"]}, {"$set": {"badges": {}}})
    return db.users.find_one({"user_id": userinfo["user_id"]})


# converts hex to rgb
def _hex_to_rgb(hex_num: str, a: int):
    h = hex_num.lstrip("#")

    # if only 3 characters are given
    if len(str(h)) == 3:
        expand = "".join([x * 2 for x in str(h)])
        h = expand

    colors = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    colors.append(a)
    return tuple(colors)


# uses k-means algorithm to find color from bg, rank is abundance of color, descending
async def _auto_color(ctx, url: str, ranks):
    phrases = ["Calculating colors..."]  # in case I want more
    # try:
    await ctx.send("**{}**".format(random.choice(phrases)))
    clusters = 10

    async with ClientSession(loop=ctx.bot.loop) as session:
        async with session.get(url) as r:
            image = await r.content.read()
    with open("temp_auto.png", "wb") as f:
        f.write(image)

    im = Image.open("temp_auto.png").convert("RGBA")
    im = im.resize((290, 290))  # resized to reduce time
    ar = scipy.misc.fromimage(im)
    shape = ar.shape
    ar = ar.reshape(scipy.product(shape[:2]), shape[2])

    codes, dist = scipy.cluster.vq.kmeans(ar.astype(float), clusters)
    vecs, dist = scipy.cluster.vq.vq(ar, codes)  # assign codes
    counts, bins = scipy.histogram(vecs, len(codes))  # count occurrences

    # sort counts
    freq_index = []
    index = 0
    for count in counts:
        freq_index.append((index, count))
        index += 1
    sorted_list = sorted(freq_index, key=operator.itemgetter(1), reverse=True)

    colors = []
    for rank in ranks:
        color_index = min(rank, len(codes))
        peak = codes[sorted_list[color_index][0]]  # gets the original index
        peak = peak.astype(int)

        colors.append("".join(format(c, "02x") for c in peak))
    return colors


async def process_purchase(ctx):
    user = ctx.message.author
    price = await db.bg_price()

    try:
        if price != 0:
            if not bank.can_spend(user, price):
                await ctx.send(
                    "**Insufficient funds. Backgrounds changes cost: ${}**".format(
                        price
                    )
                )
                return False
            else:
                await ctx.send(
                    "**{}, you are about to buy a background for `{}`. Confirm by typing `yes`.**".format(
                        get_user_name(user), price
                    )
                )
                answer = await ctx.bot.wait_for_message(timeout=15, author=user)
                if answer is None:
                    await ctx.send("**Purchase canceled.**")
                    return False
                elif "yes" not in answer.content.lower():
                    await ctx.send("**Background not purchased.**")
                    return False
                else:
                    new_balance = (await bank.get_balance(user)) - price
                    await bank.set_balance(user, new_balance)
                    return True
        else:
            return True
    except:
        await ctx.send(
            "**There was an error with economy cog. Fix to allow purchases or set price to $0. Currently ${}**".format(
                prefix, price
            )
        )
        return False


async def _valid_image_url(ctx, url):
    try:
        async with ClientSession(loop=ctx.bot.loop) as session:
            async with session.get(url) as r:
                Image.open(BytesIO(await r.content.read())).convert("RGBA")
        return True
    except:
        return False
