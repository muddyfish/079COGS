import string
import platform
from io import BytesIO
from aiohttp import ClientSession

from redbot.core import commands, bank
from discord import Member, File
from PIL import ImageFont, Image, ImageDraw

from ..static_methods import _find_guild_rank, _add_corners, _required_exp, _truncate_text, _center, get_user_name, get_user_display_name
from ..config import db
from ..permissions import leveler_enabled
from ..path_munger import font_heavy_file, font_bold_file, font_thin_file, font_unicode_file


@commands.cooldown(1, 10, commands.BucketType.user)
@commands.command(pass_context=True, no_pm=True)
@leveler_enabled
async def rank(ctx, user: Member = None):
    """Displays the rank of a user."""
    if user is None:
        user = ctx.message.author

    async with ClientSession(loop=ctx.bot.loop) as session:
        image = await draw_rank(session, user)

    image_buffer = BytesIO()
    image.save(image_buffer, "png")
    image_buffer.seek(0)

    await ctx.send(
        f"**Ranking & Statistics for {await get_user_name(user)}**",
        file=File(filename="rank.png", fp=image_buffer),
    )


async def draw_rank(session: ClientSession, user: Member) -> Image:
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

    user_info = db.user(user)

    bg_url = await user_info.rank_background()
    profile_url = user.avatar_url

    async with session.get(bg_url) as r:
        bg_image = Image.open(BytesIO(await r.content.read())).convert("RGBA")
    async with session.get(profile_url) as r:
        profile_image = Image.open(BytesIO(await r.content.read())).convert("RGBA")

    member_info = db.member(user)
    user_exp = await member_info.current_exp()
    user_level = await member_info.level()
    exp_color = await user_info.rank_info_color()

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
    exp_width = int(bg_width * (user_exp / _required_exp(user_level)))

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
        _truncate_text(get_user_display_name(user, 20), 20), 100, 0, name_fnt, name_u_fnt, grey_color
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
        _write_unicode(
            local_symbol, 117, v_label_align + 4, label_fnt, symbol_u_fnt, info_text_color
        )  # Symbol
        _write_unicode(
            local_symbol, 195, v_label_align + 4, label_fnt, symbol_u_fnt, info_text_color
        )  # Symbol

    # userinfo
    guild_rank = f"#{await _find_guild_rank(user)}"
    draw.text(
        (_center(100, 200, guild_rank, large_fnt), v_label_align - 30),
        guild_rank,
        font=large_fnt,
        fill=info_text_color,
    )  # Rank
    level_text = str(user_level)
    draw.text(
        (_center(95, 360, level_text, large_fnt), v_label_align - 30),
        level_text,
        font=large_fnt,
        fill=info_text_color,
    )  # Level
    credit_txt = f"${await bank.get_balance(user)}"
    draw.text(
        (_center(260, 360, credit_txt, large_fnt), v_label_align - 30),
        credit_txt,
        font=large_fnt,
        fill=info_text_color,
    )  # Balance
    exp_text = f"{user_exp}/{_required_exp(user_level)}"
    draw.text(
        (_center(80, 360, exp_text, exp_fnt), 19),
        exp_text,
        font=exp_fnt,
        fill=info_text_color,
    )  # Rank

    return Image.alpha_composite(result, process)
