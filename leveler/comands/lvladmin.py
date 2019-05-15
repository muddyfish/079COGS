from redbot.core import commands
import discord
import os
from PIL import Image
from redbot.core import checks, bank
from ..leveler import db
from ..path_munger import fileIO
from ..static_methods import _level_exp, _required_exp


prefix = "!"


@checks.admin_or_permissions(manage_guild=True)
@commands.group(pass_context=True)
async def lvladmin(self, ctx):
    """Admin Toggle Features"""
    if ctx.invoked_subcommand is None:
        return


@checks.admin_or_permissions(manage_guild=True)
@lvladmin.group(pass_context=True)
async def overview(self, ctx):
    """A list of settings"""
    user = ctx.message.author

    disabled_guilds = []
    private_levels = []
    disabled_levels = []
    locked_channels = []

    for guild in self.bot.guilds:
        if (
                "disabled_guilds" in self.settings.keys()
                and str(str(guild.id)) in self.settings["disabled_guilds"]
        ):
            disabled_guilds.append(guild.name)
        if (
                "lvl_msg_lock" in self.settings.keys()
                and str(guild.id) in self.settings["lvl_msg_lock"].keys()
        ):
            for channel in guild.channels:
                if self.settings["lvl_msg_lock"][str(guild.id)] == channel.id:
                    locked_channels.append("\n{} → #{}".format(guild.name, channel.name))
        if "lvl_msg" in self.settings.keys() and str(guild.id) in self.settings["lvl_msg"]:
            disabled_levels.append(guild.name)
        if (
                "private_lvl_msg" in self.settings.keys()
                and str(guild.id) in self.settings["private_lvl_msg"]
        ):
            private_levels.append(guild.name)

    num_users = 0
    for i in db.users.find({}):
        num_users += 1

    msg = ""
    msg += "**guilds:** {}\n".format(len(self.bot.guilds))
    msg += "**Unique Users:** {}\n".format(num_users)
    if "mention" in self.settings.keys():
        msg += "**Mentions:** {}\n".format(str(self.settings["mention"]))
    msg += "**Background Price:** {}\n".format(self.settings["bg_price"])
    if "badge_type" in self.settings.keys():
        msg += "**Badge type:** {}\n".format(self.settings["badge_type"])
    msg += "**Disabled guilds:** {}\n".format(", ".join(disabled_guilds))
    msg += "**Enabled Level Messages:** {}\n".format(", ".join(disabled_levels))
    msg += "**Private Level Messages:** {}\n".format(", ".join(private_levels))
    msg += "**Channel Locks:** {}\n".format(", ".join(locked_channels))
    em = discord.Embed(description=msg, colour=user.colour)
    em.set_author(name="Settings Overview for {}".format(self.bot.user.name))
    await ctx.send(embed=em)


@lvladmin.command(pass_context=True, no_pm=True)
async def msgcredits(self, ctx, credits: int = 0):
    """Credits per message logged. Default = 0"""
    channel = ctx.message.channel
    guild = ctx.message.guild

    if credits < 0 or credits > 1000:
        await ctx.send("**Please enter a valid number (0 - 1000)**".format(channel.name))
        return

    if "msg_credits" not in self.settings.keys():
        self.settings["msg_credits"] = {}

    self.settings["msg_credits"][str(guild.id)] = credits
    await ctx.send("**Credits per message logged set to `{}`.**".format(str(credits)))

    fileIO("settings.json", "save", self.settings)


@lvladmin.command(name="lock", pass_context=True, no_pm=True)
async def lvlmsglock(self, ctx):
    """Locks levelup messages to one channel. Disable command via locked channel."""
    channel = ctx.message.channel
    guild = ctx.message.guild

    if "lvl_msg_lock" not in self.settings.keys():
        self.settings["lvl_msg_lock"] = {}

    if str(guild.id) in self.settings["lvl_msg_lock"]:
        if channel.id == self.settings["lvl_msg_lock"][str(guild.id)]:
            del self.settings["lvl_msg_lock"][str(guild.id)]
            await ctx.send("**Level-up message lock disabled.**".format(channel.name))
        else:
            self.settings["lvl_msg_lock"][str(guild.id)] = channel.id
            await ctx.send("**Level-up message lock changed to `#{}`.**".format(channel.name))
    else:
        self.settings["lvl_msg_lock"][str(guild.id)] = channel.id
        await ctx.send("**Level-up messages locked to `#{}`**".format(channel.name))

    fileIO("settings.json", "save", self.settings)


async def _process_purchase(self, ctx):
    user = ctx.message.author

    try:
        if self.settings["bg_price"] != 0:
            if not bank.can_spend(user, self.settings["bg_price"]):
                await ctx.send(
                    "**Insufficient funds. Backgrounds changes cost: ${}**".format(
                        self.settings["bg_price"]
                    )
                )
                return False
            else:
                await ctx.send(
                    "**{}, you are about to buy a background for `{}`. Confirm by typing `yes`.**".format(
                        self._is_mention(user), self.settings["bg_price"]
                    )
                )
                answer = await self.bot.wait_for_message(timeout=15, author=user)
                if answer is None:
                    await ctx.send("**Purchase canceled.**")
                    return False
                elif "yes" not in answer.content.lower():
                    await ctx.send("**Background not purchased.**")
                    return False
                else:
                    new_balance = bank.get_balance(user) - self.settings["bg_price"]
                    await bank.set_balance(user, new_balance)
                    return True
        else:
            if self.settings["bg_price"] == 0:
                return True
            else:
                await ctx.send(
                    "**You don't have an account. Do {}bank register**".format(prefix)
                )
                return False
    except:
        if self.settings["bg_price"] == 0:
            return True
        else:
            await ctx.send(
                "**There was an error with economy cog. Fix to allow purchases or set price to $0. Currently ${}**".format(
                    prefix, self.settings["bg_price"]
                )
            )
            return False


@checks.is_owner()
@lvladmin.command(no_pm=True)
async def setprice(self, ctx, price: int):
    """Set a price for background changes."""
    if price < 0:
        await ctx.send("**That is not a valid background price.**")
    else:
        self.settings["bg_price"] = price
        await ctx.send("**Background price set to: `{}`!**".format(price))
        fileIO("settings.json", "save", self.settings)


@checks.is_owner()
@lvladmin.command(pass_context=True, no_pm=True)
async def setlevel(self, ctx, user: discord.Member, level: int):
    """Set a user's level. (What a cheater C:)."""
    guild = user.guild
    channel = ctx.message.channel
    # creates user if doesn't exist
    await self._create_user(user, guild)
    userinfo = db.users.find_one({"user_id": str(str(user.id))})

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("Leveler commands for this guild are disabled.")
        return

    if level < 0:
        await ctx.send("**Please enter a positive number.**")
        return

    # get rid of old level exp
    old_guild_exp = 0
    for i in range(userinfo["servers"][str(guild.id)]["level"]):
        old_guild_exp += _required_exp(i)
    userinfo["total_exp"] -= old_guild_exp
    userinfo["total_exp"] -= userinfo["servers"][str(guild.id)]["current_exp"]

    # add in new exp
    total_exp = _level_exp(level)
    userinfo["servers"][str(guild.id)]["current_exp"] = 0
    userinfo["servers"][str(guild.id)]["level"] = level
    userinfo["total_exp"] += total_exp

    db.users.update_one(
        {"user_id": str(str(user.id))},
        {
            "$set": {
                "servers.{}.level".format(str(guild.id)): level,
                "servers.{}.current_exp".format(str(guild.id)): 0,
                "total_exp": userinfo["total_exp"],
            }
        },
    )
    await ctx.send(
        "**{}'s Level has been set to `{}`.**".format(self._is_mention(user), level)
    )
    await self._handle_levelup(user, userinfo, guild, channel)


@checks.is_owner()
@lvladmin.command(no_pm=True)
async def mention(self, ctx):
    """Toggle mentions on messages."""
    if "mention" not in self.settings.keys() or self.settings["mention"] is True:
        self.settings["mention"] = False
        await ctx.send("**Mentions disabled.**")
    else:
        self.settings["mention"] = True
        await ctx.send("**Mentions enabled.**")
    fileIO("settings.json", "save", self.settings)


async def _valid_image_url(self, url):
    try:
        async with self.session.get(url) as r:
            image = await r.content.read()
        with open("test.png", "wb") as f:
            f.write(image)
        Image.open("test.png").convert("RGBA")
        os.remove("test.png")
        return True
    except:
        return False


@checks.admin_or_permissions(manage_guild=True)
@lvladmin.command(pass_context=True, no_pm=True)
async def toggle(self, ctx):
    """Toggle most leveler commands on the current guild."""
    guild = ctx.message.guild
    if str(guild.id) in self.settings["disabled_guilds"]:
        self.settings["disabled_guilds"] = list(
            filter(lambda a: a != str(guild.id), self.settings["disabled_guilds"])
        )
        await ctx.send("**Leveler enabled on `{}`.**".format(guild.name))
    else:
        self.settings["disabled_guilds"].append(str(guild.id))
        await ctx.send("**Leveler disabled on `{}`.**".format(guild.name))
    fileIO("settings.json", "save", self.settings)


@checks.admin_or_permissions(manage_guild=True)
@lvladmin.command(pass_context=True, no_pm=True)
async def textonly(self, ctx, all: str = None):
    """Toggle text-based messages on the guild."""
    guild = ctx.message.guild
    user = ctx.message.author
    # deals with enabled array

    if "text_only" not in self.settings.keys():
        self.settings["text_only"] = []

    if all is not None:
        if str(user.id) == self.owner:
            if all == "disableall":
                self.settings["text_only"] = []
                await ctx.send("**Text-only disabled for all guilds.**")
            elif all == "enableall":
                self.settings["lvl_msg"] = []
                for guild in self.bot.guilds:
                    self.settings["text_only"].append(str(guild.id))
                await ctx.send("**Text-only messages enabled for all guilds.**")
        else:
            await ctx.send("**No Permission.**")
    else:
        if str(guild.id) in self.settings["text_only"]:
            self.settings["text_only"].remove(str(guild.id))
            await ctx.send("**Text-only messages disabled for `{}`.**".format(guild.name))
        else:
            self.settings["text_only"].append(str(guild.id))
            await ctx.send("**Text-only messages enabled for `{}`.**".format(guild.name))
    fileIO("settings.json", "save", self.settings)


@checks.admin_or_permissions(manage_guild=True)
@lvladmin.command(name="alerts", pass_context=True, no_pm=True)
async def lvlalert(self, ctx, all: str = None):
    """Toggle level-up messages on the guild."""
    guild = ctx.message.guild
    user = ctx.message.author

    # old version was boolean
    if not isinstance(self.settings["lvl_msg"], list):
        self.settings["lvl_msg"] = []

    if all is not None:
        if str(user.id) == self.owner:
            if all == "disableall":
                self.settings["lvl_msg"] = []
                await ctx.send("**Level-up messages disabled for all guilds.**")
            elif all == "enableall":
                self.settings["lvl_msg"] = []
                for guild in self.bot.guilds:
                    self.settings["lvl_msg"].append(str(guild.id))
                await ctx.send("**Level-up messages enabled for all guilds.**")
        else:
            await ctx.send("**No Permission.**")
    else:
        if str(guild.id) in self.settings["lvl_msg"]:
            self.settings["lvl_msg"].remove(str(guild.id))
            await ctx.send("**Level-up alerts disabled for `{}`.**".format(guild.name))
        else:
            self.settings["lvl_msg"].append(str(guild.id))
            await ctx.send("**Level-up alerts enabled for `{}`.**".format(guild.name))
    fileIO("settings.json", "save", self.settings)


@checks.admin_or_permissions(manage_guild=True)
@lvladmin.command(name="private", pass_context=True, no_pm=True)
async def lvlprivate(self, ctx, all: str = None):
    """Toggles if lvl alert is a private message to the user."""
    guild = ctx.message.guild
    user = ctx.message.author

    # deals with ENABLED array, not disabled

    if "private_lvl_msg" not in self.settings.keys():
        self.settings["private_lvl_msg"] = []

    if all is not None:
        if str(user.id) == self.owner:
            if all == "disableall":
                self.settings["private_lvl_msg"] = []
                await ctx.send("**Private level-up messages disabled for all guilds.**")
            elif all == "enableall":
                self.settings["private_lvl_msg"] = []
                for guild in self.bot.guilds:
                    self.settings["private_lvl_msg"].append(str(guild.id))
                await ctx.send("**Private level-up messages enabled for all guilds.**")
        else:
            await ctx.send("**No Permission.**")
    else:
        if str(guild.id) in self.settings["private_lvl_msg"]:
            self.settings["private_lvl_msg"].remove(str(guild.id))
            await ctx.send("**Private level-up alerts disabled for `{}`.**".format(guild.name))
        else:
            self.settings["private_lvl_msg"].append(str(guild.id))
            await ctx.send("**Private level-up alerts enabled for `{}`.**".format(guild.name))

    fileIO("settings.json", "save", self.settings)


@lvladmin.group(name="bg", pass_context=True)
async def lvladminbg(self, ctx):
    """Admin Background Configuration"""
    if ctx.invoked_subcommand is None or isinstance(ctx.invoked_subcommand, commands.Group):
        return


@checks.is_owner()
@lvladminbg.command(no_pm=True)
async def addprofilebg(self, ctx, name: str, url: str):
    """Add a profile background. Proportions: (290px x 290px)"""
    if name in self.backgrounds["profile"].keys():
        await ctx.send("**That profile background name already exists!**")
    elif not await self._valid_image_url(url):
        await ctx.send("**That is not a valid image url!**")
    else:
        self.backgrounds["profile"][name] = url
        fileIO("backgrounds.json", "save", self.backgrounds)
        await ctx.send("**New profile background(`{}`) added.**".format(name))


@checks.is_owner()
@lvladminbg.command(no_pm=True)
async def addrankbg(self, ctx, name: str, url: str):
    """Add a rank background. Proportions: (360px x 100px)"""
    if name in self.backgrounds["rank"].keys():
        await ctx.send("**That rank background name already exists!**")
    elif not await self._valid_image_url(url):
        await ctx.send("**That is not a valid image url!**")
    else:
        self.backgrounds["rank"][name] = url
        fileIO("backgrounds.json", "save", self.backgrounds)
        await ctx.send("**New rank background(`{}`) added.**".format(name))


@checks.is_owner()
@lvladminbg.command(no_pm=True)
async def addlevelbg(self, ctx, name: str, url: str):
    """Add a level-up background. Proportions: (85px x 105px)"""
    if name in self.backgrounds["levelup"].keys():
        await ctx.send("**That level-up background name already exists!**")
    elif not await self._valid_image_url(url):
        await ctx.send("**That is not a valid image url!**")
    else:
        self.backgrounds["levelup"][name] = url
        fileIO("backgrounds.json", "save", self.backgrounds)
        await ctx.send("**New level-up background(`{}`) added.**".format(name))


@checks.is_owner()
@lvladminbg.command(no_pm=True, pass_context=True)
async def setcustombg(self, ctx, bg_type: str, user_id: str, img_url: str):
    """Set one-time custom background"""
    valid_types = ["profile", "rank", "levelup"]
    type_input = bg_type.lower()

    if type_input not in valid_types:
        await ctx.send("**Please choose a valid type: `profile`, `rank`, `levelup`.")
        return

    # test if valid user_id
    userinfo = db.users.find_one({"user_id": user_id})
    if not userinfo:
        await ctx.send("**That is not a valid user id!**")
        return

    if not await self._valid_image_url(img_url):
        await ctx.send("**That is not a valid image url!**")
        return

    db.users.update_one(
        {"user_id": user_id}, {"$set": {"{}_background".format(type_input): img_url}}
    )
    await ctx.send("**User {} custom {} background set.**".format(user_id, bg_type))


@checks.is_owner()
@lvladminbg.command(no_pm=True)
async def delprofilebg(self, ctx, name: str):
    """Delete a profile background."""
    if name in self.backgrounds["profile"].keys():
        del self.backgrounds["profile"][name]
        fileIO("backgrounds.json", "save", self.backgrounds)
        await ctx.send("**The profile background(`{}`) has been deleted.**".format(name))
    else:
        await ctx.send("**That profile background name doesn't exist.**")


@checks.is_owner()
@lvladminbg.command(no_pm=True)
async def delrankbg(self, ctx, name: str):
    """Delete a rank background."""
    if name in self.backgrounds["rank"].keys():
        del self.backgrounds["rank"][name]
        fileIO("backgrounds.json", "save", self.backgrounds)
        await ctx.send("**The rank background(`{}`) has been deleted.**".format(name))
    else:
        await ctx.send("**That rank background name doesn't exist.**")


@checks.is_owner()
@lvladminbg.command(no_pm=True)
async def dellevelbg(self, ctx, name: str):
    """Delete a level background."""
    if name in self.backgrounds["levelup"].keys():
        del self.backgrounds["levelup"][name]
        fileIO("backgrounds.json", "save", self.backgrounds)
        await ctx.send("**The level-up background(`{}`) has been deleted.**".format(name))
    else:
        await ctx.send("**That level-up background name doesn't exist.**")
