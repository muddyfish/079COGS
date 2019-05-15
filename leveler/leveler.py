from redbot.core import commands
import operator
import random
import aiohttp


try:
    import scipy
    import scipy.misc
    import scipy.cluster
except:
    pass

from PIL import Image

from pymongo import MongoClient
client = MongoClient()
db = client["leveler"]


from .static_methods import pop_database, _truncate_text
from .path_munger import munge_path, fileIO

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
        except AttributeError:
            pass
