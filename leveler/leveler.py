import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
import platform
import string
import operator
import random
import textwrap
import os
import aiohttp
from redbot.core import checks, bank

try:
    from pymongo import MongoClient
except:
    raise RuntimeError("Can't load pymongo. Do 'pip3 install pymongo'.")
try:
    client = MongoClient()
    db = client["leveler"]
except:
    print("Can't load database. Follow instructions on Git/online to install MongoDB.")


from .static_methods import pop_database, _rgb_to_hex, _truncate_text, _center, _required_exp, _level_exp, _find_level,\
    _add_corners, _contrast, _is_hex, _find_guild_rank, _find_guild_rep_rank, _find_guild_level_rank, _find_guild_exp, \
    _find_global_rank, _find_global_rep_rank, _badge_convert_dict, _hex_to_rgb
from .path_munger import munge_path, fileIO

try:
    import scipy
    import scipy.misc
    import scipy.cluster
except:
    pass
try:
    from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageOps, ImageFilter
except:
    raise RuntimeError("Can't load pillow. Do 'pip3 install pillow'.")
import time

# fonts
font_file = munge_path("fonts", "font.ttf")
font_bold_file = munge_path("fonts", "font_bold.ttf")
font_unicode_file = munge_path("fonts", "unicode.ttf")

# Credits (None)
bg_credits = {}

# directory

prefix = "!"
default_avatar_url = "http://i.imgur.com/XPDO9VH.jpg"

class Leveler(commands.Cog):
    """A level up thing with image generation!"""

    def __init__(self, bot):
        self.bot = bot
        self.backgrounds = fileIO("backgrounds.json", "load")
        self.badges = fileIO("badges.json", "load")
        self.settings = fileIO("settings.json", "load")
        bot_settings = fileIO("red_settings.json", "load")
        self.owner = bot_settings["OWNER"]
        self.session = aiohttp.ClientSession(loop=self.bot.loop)
        dbs = client.database_names()
        if "leveler" not in dbs:
            pop_database()

    # should the user be mentioned based on settings?
    def _is_mention(self, user):
        if "mention" not in self.settings.keys() or self.settings["mention"]:
            return user.mention
        else:
            return user.name

    # uses k-means algorithm to find color from bg, rank is abundance of color, descending
    async def _auto_color(self, ctx, url: str, ranks):
        phrases = ["Calculating colors..."]  # in case I want more
        # try:
        await ctx.send("**{}**".format(random.choice(phrases)))
        clusters = 10

        async with self.session.get(url) as r:
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
        return colors  # returns array

    async def draw_profile(self, user, guild):
        font_thin_file = munge_path("fonts", "Uni_Sans_Thin.ttf")
        font_heavy_file = munge_path("fonts", "Uni_Sans_Heavy.ttf")
        font_file = munge_path("fonts", "SourceSansPro-Regular.ttf")
        font_bold_file = munge_path("fonts", "SourceSansPro-Semibold.ttf")

        name_fnt = ImageFont.truetype(font_heavy_file, 30)
        name_u_fnt = ImageFont.truetype(font_unicode_file, 30)
        title_fnt = ImageFont.truetype(font_heavy_file, 22)
        title_u_fnt = ImageFont.truetype(font_unicode_file, 23)
        label_fnt = ImageFont.truetype(font_bold_file, 18)
        exp_fnt = ImageFont.truetype(font_bold_file, 13)
        large_fnt = ImageFont.truetype(font_thin_file, 33)
        rep_fnt = ImageFont.truetype(font_heavy_file, 26)
        rep_u_fnt = ImageFont.truetype(font_unicode_file, 30)
        text_fnt = ImageFont.truetype(font_file, 14)
        text_u_fnt = ImageFont.truetype(font_unicode_file, 14)
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

        # get urls
        userinfo = db.users.find_one({"user_id": str(str(user.id))})
        _badge_convert_dict(userinfo)
        userinfo = db.users.find_one(
            {"user_id": str(str(user.id))}
        )  ##############################################
        bg_url = userinfo["profile_background"]
        profile_url = user.avatar_url

        # COLORS
        white_color = (240, 240, 240, 255)
        if "rep_color" not in userinfo.keys() or not userinfo["rep_color"]:
            rep_fill = (92, 130, 203, 230)
        else:
            rep_fill = tuple(userinfo["rep_color"])
        # determines badge section color, should be behind the titlebar
        if "badge_col_color" not in userinfo.keys() or not userinfo["badge_col_color"]:
            badge_fill = (128, 151, 165, 230)
        else:
            badge_fill = tuple(userinfo["badge_col_color"])
        if "profile_info_color" in userinfo.keys():
            info_fill = tuple(userinfo["profile_info_color"])
        else:
            info_fill = (30, 30, 30, 220)
        info_fill_tx = (info_fill[0], info_fill[1], info_fill[2], 150)
        if "profile_exp_color" not in userinfo.keys() or not userinfo["profile_exp_color"]:
            exp_fill = (255, 255, 255, 230)
        else:
            exp_fill = tuple(userinfo["profile_exp_color"])
        if badge_fill == (128, 151, 165, 230):
            level_fill = white_color
        else:
            level_fill = _contrast(exp_fill, rep_fill, badge_fill)

        # create image objects

        async with self.session.get(bg_url) as r:
            image = await r.content.read()
        with open(munge_path("temp/{}_temp_profile_bg.png".format(str(user.id))), "wb") as f:
            f.write(image)
        try:
            async with self.session.get(profile_url) as r:
                image = await r.content.read()
        except:
            async with self.session.get(default_avatar_url) as r:
                image = await r.content.read()
        with open(munge_path("temp/{}_temp_profile_profile.png".format(str(user.id))), "wb") as f:
            f.write(image)

        bg_image = Image.open(
            munge_path("temp/{}_temp_profile_bg.png".format(str(user.id)))
        ).convert("RGBA")
        profile_image = Image.open(
            munge_path("temp/{}_temp_profile_profile.png".format(str(user.id)))
        ).convert("RGBA")

        # set canvas
        bg_color = (255, 255, 255, 0)
        result = Image.new("RGBA", (340, 390), bg_color)
        process = Image.new("RGBA", (340, 390), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # puts in background
        bg_image = bg_image.resize((340, 340), Image.ANTIALIAS)
        bg_image = bg_image.crop((0, 0, 340, 305))
        result.paste(bg_image, (0, 0))

        # draw filter
        draw.rectangle([(0, 0), (340, 340)], fill=(0, 0, 0, 10))

        draw.rectangle([(0, 134), (340, 325)], fill=info_fill_tx)  # general content
        # draw profile circle
        multiplier = 8
        lvl_circle_dia = 116
        circle_left = 14
        circle_top = 48
        raw_length = lvl_circle_dia * multiplier

        # create mask
        mask = Image.new("L", (raw_length, raw_length), 0)
        draw_thumb = ImageDraw.Draw(mask)
        draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill=255, outline=0)

        # border
        lvl_circle = Image.new("RGBA", (raw_length, raw_length))
        draw_lvl_circle = ImageDraw.Draw(lvl_circle)
        draw_lvl_circle.ellipse(
            [0, 0, raw_length, raw_length], fill=(255, 255, 255, 255), outline=(255, 255, 255, 250)
        )
        # put border
        lvl_circle = lvl_circle.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
        lvl_bar_mask = mask.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
        process.paste(lvl_circle, (circle_left, circle_top), lvl_bar_mask)

        # put in profile picture
        total_gap = 6
        border = int(total_gap / 2)
        profile_size = lvl_circle_dia - total_gap
        mask = mask.resize((profile_size, profile_size), Image.ANTIALIAS)
        profile_image = profile_image.resize((profile_size, profile_size), Image.ANTIALIAS)
        process.paste(profile_image, (circle_left + border, circle_top + border), mask)

        # write label text
        white_color = (240, 240, 240, 255)
        light_color = (160, 160, 160, 255)
        dark_color = (35, 35, 35, 255)

        head_align = 140
        # determine info text color
        info_text_color = _contrast(info_fill, white_color, dark_color)
        _write_unicode(
            _truncate_text(user.name, 22).upper(),
            head_align,
            142,
            name_fnt,
            name_u_fnt,
            info_text_color,
        )  # NAME
        _write_unicode(
            userinfo["title"].upper(), head_align, 170, title_fnt, title_u_fnt, info_text_color
        )

        # draw divider
        draw.rectangle([(0, 323), (340, 324)], fill=(0, 0, 0, 255))  # box
        # draw text box
        draw.rectangle(
            [(0, 324), (340, 390)], fill=(info_fill[0], info_fill[1], info_fill[2], 255)
        )  # box

        rep_text = "{}".format(userinfo["rep"])
        _write_unicode("❤", 257, 9, rep_fnt, rep_u_fnt, info_text_color)
        draw.text(
            (_center(278, 340, rep_text, rep_fnt), 10),
            rep_text,
            font=rep_fnt,
            fill=info_text_color,
        )  # Exp Text

        label_align = 362  # vertical
        draw.text(
            (_center(0, 140, "    RANK", label_fnt), label_align),
            "    RANK",
            font=label_fnt,
            fill=info_text_color,
        )  # Rank
        draw.text(
            (_center(0, 340, "    LEVEL", label_fnt), label_align),
            "    LEVEL",
            font=label_fnt,
            fill=info_text_color,
        )  # Exp
        draw.text(
            (_center(200, 340, "BALANCE", label_fnt), label_align),
            "BALANCE",
            font=label_fnt,
            fill=info_text_color,
        )  # Credits

        if "linux" in platform.system().lower():
            global_symbol = u"\U0001F30E "
            fine_adjust = 1
        else:
            global_symbol = "G."
            fine_adjust = 0

        _write_unicode(
            global_symbol, 36, label_align + 5, label_fnt, symbol_u_fnt, info_text_color
        )  # Symbol
        _write_unicode(
            global_symbol, 134, label_align + 5, label_fnt, symbol_u_fnt, info_text_color
        )  # Symbol

        # userinfo
        global_rank = "#{}".format(await _find_global_rank(user))
        global_level = "{}".format(_find_level(userinfo["total_exp"]))
        draw.text(
            (_center(0, 140, global_rank, large_fnt), label_align - 27),
            global_rank,
            font=large_fnt,
            fill=info_text_color,
        )  # Rank
        draw.text(
            (_center(0, 340, global_level, large_fnt), label_align - 27),
            global_level,
            font=large_fnt,
            fill=info_text_color,
        )  # Exp
        # draw level bar
        exp_font_color = _contrast(exp_fill, light_color, dark_color)
        exp_frac = int(userinfo["total_exp"] - _level_exp(int(global_level)))
        exp_total = _required_exp(int(global_level) + 1)
        bar_length = int(exp_frac / exp_total * 340)
        draw.rectangle(
            [(0, 305), (340, 323)], fill=(level_fill[0], level_fill[1], level_fill[2], 245)
        )  # level box
        draw.rectangle(
            [(0, 305), (bar_length, 323)], fill=(exp_fill[0], exp_fill[1], exp_fill[2], 255)
        )  # box
        exp_text = "{}/{}".format(exp_frac, exp_total)  # Exp
        draw.text(
            (_center(0, 340, exp_text, exp_fnt), 305),
            exp_text,
            font=exp_fnt,
            fill=exp_font_color,
        )  # Exp Text

        try:
            credits = await bank.get_balance(user)
        except:
            credits = 0
        credit_txt = "${}".format(credits)
        draw.text(
            (_center(200, 340, credit_txt, large_fnt), label_align - 27),
            _truncate_text(credit_txt, 18),
            font=large_fnt,
            fill=info_text_color,
        )  # Credits

        if userinfo["title"] == "":
            offset = 170
        else:
            offset = 195
        margin = 140
        txt_color = _contrast(info_fill, white_color, dark_color)
        for line in textwrap.wrap(userinfo["info"], width=32):
            _write_unicode(line, margin, offset, text_fnt, text_u_fnt, txt_color)
            offset += text_fnt.getsize(line)[1] + 2

        # sort badges
        priority_badges = []

        for badgename in userinfo["badges"].keys():
            badge = userinfo["badges"][badgename]
            priority_num = badge["priority_num"]
            if priority_num != 0 and priority_num != -1:
                priority_badges.append((badge, priority_num))
        sorted_badges = sorted(priority_badges, key=operator.itemgetter(1), reverse=True)

        # TODO: simplify this. it shouldn't be this complicated... sacrifices conciseness for customizability
        if "badge_type" not in self.settings.keys() or self.settings["badge_type"] == "circles":
            # circles require antialiasing
            vert_pos = 172
            right_shift = 0
            left = 9 + right_shift
            size = 38
            total_gap = 4  # /2
            hor_gap = 6
            vert_gap = 6
            border_width = int(total_gap / 2)
            multiplier = 6  # for antialiasing
            raw_length = size * multiplier
            mult = [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2)]
            for num in range(9):
                coord = (
                    left + int(mult[num][0]) * int(hor_gap + size),
                    vert_pos + int(mult[num][1]) * int(vert_gap + size),
                )
                if num < len(sorted_badges[:9]):
                    pair = sorted_badges[num]
                    badge = pair[0]
                    bg_color = badge["bg_img"]
                    border_color = badge["border_color"]
                    # draw mask circle
                    mask = Image.new("L", (raw_length, raw_length), 0)
                    draw_thumb = ImageDraw.Draw(mask)
                    draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill=255, outline=0)

                    # determine image or color for badge bg
                    if await self._valid_image_url(bg_color):
                        # get image
                        async with self.session.get(bg_color) as r:
                            image = await r.content.read()
                        with open(
                            "temp/{}_temp_badge.png".format(str(user.id)), "wb"
                        ) as f:
                            f.write(image)
                        badge_image = Image.open(
                            "temp/{}_temp_badge.png".format(str(user.id))
                        ).convert("RGBA")
                        badge_image = badge_image.resize((raw_length, raw_length), Image.ANTIALIAS)

                        # structured like this because if border = 0, still leaves outline.
                        if border_color:
                            square = Image.new("RGBA", (raw_length, raw_length), border_color)
                            # put border on ellipse/circle
                            output = ImageOps.fit(
                                square, (raw_length, raw_length), centering=(0.5, 0.5)
                            )
                            output = output.resize((size, size), Image.ANTIALIAS)
                            outer_mask = mask.resize((size, size), Image.ANTIALIAS)
                            process.paste(output, coord, outer_mask)

                            # put on ellipse/circle
                            output = ImageOps.fit(
                                badge_image, (raw_length, raw_length), centering=(0.5, 0.5)
                            )
                            output = output.resize(
                                (size - total_gap, size - total_gap), Image.ANTIALIAS
                            )
                            inner_mask = mask.resize(
                                (size - total_gap, size - total_gap), Image.ANTIALIAS
                            )
                            process.paste(
                                output,
                                (coord[0] + border_width, coord[1] + border_width),
                                inner_mask,
                            )
                        else:
                            # put on ellipse/circle
                            output = ImageOps.fit(
                                badge_image, (raw_length, raw_length), centering=(0.5, 0.5)
                            )
                            output = output.resize((size, size), Image.ANTIALIAS)
                            outer_mask = mask.resize((size, size), Image.ANTIALIAS)
                            process.paste(output, coord, outer_mask)
                else:
                    plus_fill = exp_fill
                    # put on ellipse/circle
                    plus_square = Image.new("RGBA", (raw_length, raw_length))
                    plus_draw = ImageDraw.Draw(plus_square)
                    plus_draw.rectangle(
                        [(0, 0), (raw_length, raw_length)],
                        fill=(info_fill[0], info_fill[1], info_fill[2], 245),
                    )
                    # draw plus signs
                    margin = 60
                    thickness = 40
                    v_left = int(raw_length / 2 - thickness / 2)
                    v_right = v_left + thickness
                    v_top = margin
                    v_bottom = raw_length - margin
                    plus_draw.rectangle(
                        [(v_left, v_top), (v_right, v_bottom)],
                        fill=(plus_fill[0], plus_fill[1], plus_fill[2], 245),
                    )
                    h_left = margin
                    h_right = raw_length - margin
                    h_top = int(raw_length / 2 - thickness / 2)
                    h_bottom = h_top + thickness
                    plus_draw.rectangle(
                        [(h_left, h_top), (h_right, h_bottom)],
                        fill=(plus_fill[0], plus_fill[1], plus_fill[2], 245),
                    )
                    # put border on ellipse/circle
                    output = ImageOps.fit(
                        plus_square, (raw_length, raw_length), centering=(0.5, 0.5)
                    )
                    output = output.resize((size, size), Image.ANTIALIAS)
                    outer_mask = mask.resize((size, size), Image.ANTIALIAS)
                    process.paste(output, coord, outer_mask)

                # attempt to remove badge image
                try:
                    os.remove("temp/{}_temp_badge.png".format(str(user.id)))
                except:
                    pass

        result = Image.alpha_composite(result, process)
        result = _add_corners(result, 25)
        result.save(munge_path("temp/{}_profile.png".format(str(user.id))), "PNG", quality=100)

        # remove images
        try:
            os.remove(munge_path("temp/{}_temp_profile_bg.png".format(str(user.id))))
        except:
            pass
        try:
            os.remove(munge_path("temp/{}_temp_profile_profile.png".format(str(user.id))))
        except:
            pass

    # returns a string with possibly a nickname
    def _name(self, user, max_length):
        if user.name == user.display_name:
            return user.name
        else:
            return "{} ({})".format(
                user.name,
                _truncate_text(user.display_name, max_length - len(user.name) - 3),
                max_length,
            )

    # handles user creation, adding new guild, blocking
    async def _create_user(self, user, guild):
        try:
            userinfo = db.users.find_one({"user_id": str(str(user.id))})
            if not userinfo:
                new_account = {
                    "user_id": str(user.id),
                    "username": user.name,
                    "servers": {},
                    "total_exp": 0,
                    "profile_background": self.backgrounds["profile"]["default"],
                    "rank_background": self.backgrounds["rank"]["default"],
                    "levelup_background": self.backgrounds["levelup"]["default"],
                    "title": "",
                    "info": "I am a mysterious person.",
                    "rep": 0,
                    "badges": {},
                    "active_badges": {},
                    "rep_color": [],
                    "badge_col_color": [],
                    "rep_block": 0,
                    "chat_block": 0,
                    "profile_block": 0,
                    "rank_block": 0,
                }
                db.users.insert_one(new_account)

            userinfo = db.users.find_one({"user_id": str(str(user.id))})

            if "username" not in userinfo or userinfo["username"] != user.name:
                db.users.update_one(
                    {"user_id": str(str(user.id))}, {"$set": {"username": user.name}}, upsert=True
                )

            if "servers" not in userinfo or str(guild.id) not in userinfo["servers"]:
                db.users.update_one(
                    {"user_id": str(str(user.id))},
                    {
                        "$set": {
                            "servers.{}.level".format(str(guild.id)): 0,
                            "servers.{}.current_exp".format(str(guild.id)): 0,
                        }
                    },
                    upsert=True,
                )
        except AttributeError as e:
            pass
