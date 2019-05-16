from redbot.core import commands
import operator
import random
import aiohttp

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
