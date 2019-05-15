from redbot.core import commands, bank
import discord
import time
import os
from PIL import ImageFont, Image, ImageDraw
import string
import platform
from ..leveler import munge_path, db, default_avatar_url, font_unicode_file
from ..static_methods import _find_guild_rank, _find_guild_exp, _add_corners, _required_exp, _truncate_text, _center


@commands.cooldown(1, 10, commands.BucketType.user)
@commands.command(pass_context=True, no_pm=True)
async def rank(leveler, ctx, user: discord.Member = None):
    """Displays the rank of a user."""
    if user is None:
        user = ctx.message.author
    channel = ctx.message.channel
    guild = user.guild
    curr_time = time.time()

    # creates user if doesn't exist
    await leveler._create_user(user, guild)
    userinfo = db.users.find_one({"user_id": str(str(user.id))})

    # check if disabled
    if str(guild.id) in leveler.settings["disabled_guilds"]:
        await ctx.send("**Leveler commands for this guild are disabled!**")
        return

    # no cooldown for text only
    if "text_only" in leveler.settings and str(guild.id) in leveler.settings["text_only"]:
        em = await rank_text(user, guild, userinfo)
        await channel.send("", embed=em)
    else:
        await draw_rank(leveler, user, guild)

        await channel.send(
            "**Ranking & Statistics for {}**".format(leveler._is_mention(user)),
            file=discord.File(munge_path("temp/{}_rank.png".format(str(user.id)))),
        )
        db.users.update_one(
            {"user_id": str(str(user.id))},
            {"$set": {"rank_block".format(str(guild.id)): curr_time}},
            upsert=True,
        )
        try:
            os.remove("temp/{}_rank.png".format(str(user.id)))
        except:
            pass


async def rank_text(user, guild, userinfo):
    em = discord.Embed(description="", colour=user.colour)
    em.add_field(
        name="guild Rank", value="#{}".format(await _find_guild_rank(user, guild))
    )
    em.add_field(name="Reps", value=userinfo["rep"])
    em.add_field(name="guild Level", value=userinfo["servers"][str(guild.id)]["level"])
    em.add_field(name="guild Exp", value=await _find_guild_exp(user, guild))
    em.set_author(name="Rank and Statistics for {}".format(user.name), url=user.avatar_url)
    em.set_thumbnail(url=user.avatar_url)
    return em


async def draw_rank(self, user, guild):
    # fonts
    font_thin_file = munge_path("fonts/Uni_Sans_Thin.ttf")
    font_heavy_file = munge_path("fonts/Uni_Sans_Heavy.ttf")
    font_bold_file = munge_path("fonts/SourceSansPro-Semibold.ttf")

    name_fnt = ImageFont.truetype(font_heavy_file, 24)
    name_u_fnt = ImageFont.truetype(font_unicode_file, 24)
    label_fnt = ImageFont.truetype(font_bold_file, 16)
    exp_fnt = ImageFont.truetype(font_bold_file, 9)
    large_fnt = ImageFont.truetype(font_thin_file, 24)
    symbol_u_fnt = ImageFont.truetype(font_unicode_file, 15)

    def _write_unicode(text, init_x, y, font, unicode_font, fill):
        write_pos = init_x

        for char in text:
            if char.isalnum() or char in string.punctuation or char in string.whitespace:
                draw.text((write_pos, y), char, font=font, fill=fill)
                write_pos += font.getsize(char)[0]
            else:
                draw.text((write_pos, y), u"{}".format(char), font=unicode_font, fill=fill)
                write_pos += unicode_font.getsize(char)[0]

    userinfo = db.users.find_one({"user_id": str(str(user.id))})
    # get urls
    bg_url = userinfo["rank_background"]
    profile_url = user.avatar_url
    guild_icon_url = guild.icon_url

    # create image objects

    async with self.session.get(bg_url) as r:
        image = await r.content.read()
    with open(munge_path("temp/test_temp_rank_bg.png".format(str(user.id))), "wb") as f:
        f.write(image)
    try:
        async with self.session.get(profile_url) as r:
            image = await r.content.read()
    except:
        async with self.session.get(default_avatar_url) as r:
            image = await r.content.read()
    with open(munge_path("temp/test_temp_rank_profile.png".format(str(user.id))), "wb") as f:
        f.write(image)
    try:
        async with self.session.get(guild_icon_url) as r:
            image = await r.content.read()
    except:
        async with self.session.get(default_avatar_url) as r:
            image = await r.content.read()
    with open(munge_path("temp/test_temp_guild_icon.png".format(str(user.id))), "wb") as f:
        f.write(image)

    bg_image = Image.open(
        munge_path("temp/test_temp_rank_bg.png".format(str(user.id)))
    ).convert("RGBA")
    profile_image = Image.open(
        munge_path("temp/test_temp_rank_profile.png".format(str(user.id)))
    ).convert("RGBA")

    # set canvas
    width = 390
    height = 100
    bg_color = (255, 255, 255, 0)
    bg_width = width - 50
    result = Image.new("RGBA", (width, height), bg_color)
    process = Image.new("RGBA", (width, height), bg_color)
    draw = ImageDraw.Draw(process)

    # info section
    info_section = Image.new("RGBA", (bg_width, height), bg_color)
    info_section_process = Image.new("RGBA", (bg_width, height), bg_color)
    # puts in background
    bg_image = bg_image.resize((width, height), Image.ANTIALIAS)
    bg_image = bg_image.crop((0, 0, width, height))
    info_section.paste(bg_image, (0, 0))

    # draw transparent overlays
    draw_overlay = ImageDraw.Draw(info_section_process)
    draw_overlay.rectangle([(0, 0), (bg_width, 20)], fill=(230, 230, 230, 200))
    draw_overlay.rectangle([(0, 20), (bg_width, 30)], fill=(120, 120, 120, 180))  # Level bar
    exp_frac = int(userinfo["servers"][str(guild.id)]["current_exp"])
    exp_total = _required_exp(userinfo["servers"][str(guild.id)]["level"])
    exp_width = int(bg_width * (exp_frac / exp_total))
    if "rank_info_color" in userinfo.keys():
        exp_color = tuple(userinfo["rank_info_color"])
        exp_color = (exp_color[0], exp_color[1], exp_color[2], 180)  # increase transparency
    else:
        exp_color = (140, 140, 140, 230)
    draw_overlay.rectangle([(0, 20), (exp_width, 30)], fill=exp_color)  # Exp bar
    draw_overlay.rectangle([(0, 30), (bg_width, 31)], fill=(0, 0, 0, 255))  # Divider
    for i in range(0, 70):
        draw_overlay.rectangle(
            [(0, height - i), (bg_width, height - i)], fill=(20, 20, 20, 255 - i * 3)
        )  # title overlay

    # draw corners and finalize
    info_section = Image.alpha_composite(info_section, info_section_process)
    info_section = _add_corners(info_section, 25)
    process.paste(info_section, (35, 0))

    # draw level circle
    multiplier = 6
    lvl_circle_dia = 100
    circle_left = 0
    circle_top = int((height - lvl_circle_dia) / 2)
    raw_length = lvl_circle_dia * multiplier

    # create mask
    mask = Image.new("L", (raw_length, raw_length), 0)
    draw_thumb = ImageDraw.Draw(mask)
    draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill=255, outline=0)

    # drawing level border
    lvl_circle = Image.new("RGBA", (raw_length, raw_length))
    draw_lvl_circle = ImageDraw.Draw(lvl_circle)
    draw_lvl_circle.ellipse([0, 0, raw_length, raw_length], fill=(250, 250, 250, 250))

    # put on profile circle background
    lvl_circle = lvl_circle.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
    lvl_bar_mask = mask.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
    process.paste(lvl_circle, (circle_left, circle_top), lvl_bar_mask)

    # draws mask
    total_gap = 6
    border = int(total_gap / 2)
    profile_size = lvl_circle_dia - total_gap
    # put in profile picture
    mask = mask.resize((profile_size, profile_size), Image.ANTIALIAS)
    profile_image = profile_image.resize((profile_size, profile_size), Image.ANTIALIAS)
    process.paste(profile_image, (circle_left + border, circle_top + border), mask)

    # draw text
    grey_color = (100, 100, 100, 255)
    white_color = (220, 220, 220, 255)

    # name
    _write_unicode(
        _truncate_text(self._name(user, 20), 20), 100, 0, name_fnt, name_u_fnt, grey_color
    )  # Name

    # labels
    v_label_align = 75
    info_text_color = white_color
    draw.text(
        (_center(100, 200, "  RANK", label_fnt), v_label_align),
        "  RANK",
        font=label_fnt,
        fill=info_text_color,
    )  # Rank
    draw.text(
        (_center(100, 360, "  LEVEL", label_fnt), v_label_align),
        "  LEVEL",
        font=label_fnt,
        fill=info_text_color,
    )  # Rank
    draw.text(
        (_center(260, 360, "BALANCE", label_fnt), v_label_align),
        "BALANCE",
        font=label_fnt,
        fill=info_text_color,
    )  # Rank
    if "linux" in platform.system().lower():
        local_symbol = u"\U0001F3E0 "
    else:
        local_symbol = "S. "
    _write_unicode(
        local_symbol, 117, v_label_align + 4, label_fnt, symbol_u_fnt, info_text_color
    )  # Symbol
    _write_unicode(
        local_symbol, 195, v_label_align + 4, label_fnt, symbol_u_fnt, info_text_color
    )  # Symbol

    # userinfo
    guild_rank = "#{}".format(await _find_guild_rank(user, guild))
    draw.text(
        (_center(100, 200, guild_rank, large_fnt), v_label_align - 30),
        guild_rank,
        font=large_fnt,
        fill=info_text_color,
    )  # Rank
    level_text = "{}".format(userinfo["servers"][str(guild.id)]["level"])
    draw.text(
        (_center(95, 360, level_text, large_fnt), v_label_align - 30),
        level_text,
        font=large_fnt,
        fill=info_text_color,
    )  # Level
    try:
        credits = await bank.get_balance(user)
    except:
        credits = 0
    credit_txt = "${}".format(credits)
    draw.text(
        (_center(260, 360, credit_txt, large_fnt), v_label_align - 30),
        credit_txt,
        font=large_fnt,
        fill=info_text_color,
    )  # Balance
    exp_text = "{}/{}".format(exp_frac, exp_total)
    draw.text(
        (_center(80, 360, exp_text, exp_fnt), 19),
        exp_text,
        font=exp_fnt,
        fill=info_text_color,
    )  # Rank

    result = Image.alpha_composite(result, process)
    result.save(munge_path("temp/{}_rank.png".format(str(user.id))), "PNG", quality=100)
