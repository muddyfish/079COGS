from redbot.core import commands
import discord
from redbot.core.utils.chat_formatting import pagify
import operator
from .leveler import db
from redbot.core import checks, bank
from .path_munger import fileIO
from .static_methods import _badge_convert_dict, _is_hex

prefix = "!"


@commands.group(pass_context=True)
async def badge(self, ctx):
    """Badge Configuration Options"""
    if ctx.invoked_subcommand is None:
        return


@badge.command(name="available", pass_context=True, no_pm=True)
async def available(self, ctx):
    """Get a list of available badges for guild or 'global'."""
    user = ctx.message.author
    guild = ctx.message.guild

    # get guild stuff
    ids = [
        ("global", "Global", self.bot.user.avatar_url),
        (str(guild.id), guild.name, guild.icon_url),
    ]

    title_text = "**Available Badges**"
    index = 0
    for guildid, guildname, icon_url in ids:
        em = discord.Embed(description="", colour=user.colour)
        em.set_author(name="{}".format(guildname), icon_url=icon_url)
        msg = ""
        guild_badge_info = db.badges.find_one({"guild_id": guildid})
        if guild_badge_info:
            guild_badges = guild_badge_info["badges"]
            for badgename in guild_badges:
                badgeinfo = guild_badges[badgename]
                if badgeinfo["price"] == -1:
                    price = "Non-purchasable"
                elif badgeinfo["price"] == 0:
                    price = "Free"
                else:
                    price = badgeinfo["price"]

                msg += "**• {}** ({}) - {}\n".format(
                    badgename, price, badgeinfo["description"]
                )
        else:
            msg = "None"

        em.description = msg

        total_pages = 0
        for _ in pagify(msg, ["\n"]):
            total_pages += 1

        counter = 1
        for _ in pagify(msg, ["\n"]):
            if index == 0:
                await ctx.send(title_text, embed=em)
            else:
                await ctx.send(embed=em)
            index += 1

            em.set_footer(text="Page {} of {}".format(counter, total_pages))
            counter += 1


@badge.command(name="list", pass_context=True, no_pm=True)
async def listuserbadges(self, ctx, user: discord.Member = None):
    """Get the badges of a user."""
    if user == None:
        user = ctx.message.author
    guild = ctx.message.guild
    await self._create_user(user, guild)
    userinfo = db.users.find_one({"user_id": str(str(user.id))})
    userinfo = _badge_convert_dict(userinfo)

    # sort
    priority_badges = []
    for badgename in userinfo["badges"].keys():
        badge = userinfo["badges"][badgename]
        priority_num = badge["priority_num"]
        if priority_num != -1:
            priority_badges.append((badge, priority_num))
    sorted_badges = sorted(priority_badges, key=operator.itemgetter(1), reverse=True)

    badge_ranks = ""
    counter = 1
    for badge, priority_num in sorted_badges[:12]:
        badge_ranks += "**{}. {}** ({}) [{}] **—** {}\n".format(
            counter,
            badge["badge_name"],
            badge["guild_name"],
            priority_num,
            badge["description"],
        )
        counter += 1
    if not badge_ranks:
        badge_ranks = "None"

    em = discord.Embed(description="", colour=user.colour)

    total_pages = 0
    for page in pagify(badge_ranks, ["\n"]):
        total_pages += 1

    counter = 1
    for page in pagify(badge_ranks, ["\n"]):
        em.description = page
        em.set_author(name="Badges for {}".format(user.name), icon_url=user.avatar_url)
        em.set_footer(text="Page {} of {}".format(counter, total_pages))
        await ctx.send(embed=em)
        counter += 1


@badge.command(name="buy", pass_context=True, no_pm=True)
async def buy(self, ctx, name: str, global_badge: str = None):
    '''Get a badge from repository. optional = "-global"'''
    user = ctx.message.author
    guild = ctx.message.guild
    if global_badge == "-global":
        guildid = "global"
    else:
        guildid = str(guild.id)
    await self._create_user(user, guild)
    userinfo = db.users.find_one({"user_id": str(str(user.id))})
    userinfo = _badge_convert_dict(userinfo)
    guild_badge_info = db.badges.find_one({"guild_id": guildid})

    if guild_badge_info:
        guild_badges = guild_badge_info["badges"]
        if name in guild_badges:

            if "{}_{}".format(name, str(guildid)) not in userinfo["badges"].keys():
                badge_info = guild_badges[name]
                if badge_info["price"] == -1:
                    await ctx.send("**That badge is not purchasable.**".format(name))
                elif badge_info["price"] == 0:
                    userinfo["badges"]["{}_{}".format(name, str(guildid))] = guild_badges[name]
                    db.users.update_one(
                        {"user_id": userinfo["user_id"]},
                        {"$set": {"badges": userinfo["badges"]}},
                    )
                    await ctx.send("**`{}` has been obtained.**".format(name))
                else:
                    # use the economy cog
                    await ctx.send(
                        '**{}, you are about to buy the `{}` badge for `{}`. Confirm by typing "yes"**'.format(
                            self._is_mention(user), name, badge_info["price"]
                        )
                    )
                    answer = await self.bot.wait_for_message(timeout=15, author=user)
                    if answer is None:
                        await ctx.send("**Purchase canceled.**")
                        return
                    elif "yes" not in answer.content.lower():
                        await ctx.send("**Badge not purchased.**")
                        return
                    else:
                        if badge_info["price"] <= await bank.get_balance(user):
                            await bank.withdraw_credits(user, badge_info["price"])
                            userinfo["badges"][
                                "{}_{}".format(name, str(guildid))
                            ] = guild_badges[name]
                            db.users.update_one(
                                {"user_id": userinfo["user_id"]},
                                {"$set": {"badges": userinfo["badges"]}},
                            )
                            await ctx.send(
                                "**You have bought the `{}` badge for `{}`.**".format(
                                    name, badge_info["price"]
                                )
                            )
                        elif bank.get_balance(user) < badge_info["price"]:
                            await ctx.send(
                                "**Not enough money! Need `{}` more.**".format(
                                    badge_info["price"] - bank.get_balance(user)
                                )
                            )
                        else:
                            await ctx.send(
                                "**User does not exist in bank. Do {}bank register**".format(
                                    prefix
                                )
                            )
            else:
                await ctx.send("**{}, you already have this badge!**".format(user.name))
        else:
            await ctx.send(
                "**The badge `{}` does not exist. (try `{}badge available`)**".format(
                    name, prefix[0]
                )
            )
    else:
        await ctx.send(
            "**There are no badges to get! (try `{}badge get [name] -global`).**".format(
                prefix[0]
            )
        )


@badge.command(name="set", pass_context=True, no_pm=True)
async def set(self, ctx, name: str, priority_num: int):
    """Set a badge to profile. -1(invis), 0(not on profile), max: 5000."""
    user = ctx.message.author
    guild = ctx.message.author
    await self._create_user(user, guild)

    userinfo = db.users.find_one({"user_id": str(str(user.id))})
    userinfo = _badge_convert_dict(userinfo)

    if priority_num < -1 or priority_num > 5000:
        await ctx.send("**Invalid priority number! -1-5000**")
        return

    for badge in userinfo["badges"]:
        if userinfo["badges"][badge]["badge_name"] == name:
            userinfo["badges"][badge]["priority_num"] = priority_num
            db.users.update_one(
                {"user_id": userinfo["user_id"]}, {"$set": {"badges": userinfo["badges"]}}
            )
            await ctx.send(
                "**The `{}` badge priority has been set to `{}`!**".format(
                    userinfo["badges"][badge]["badge_name"], priority_num
                )
            )
            break
    else:
        await ctx.send("**You don't have that badge!**")


@checks.mod_or_permissions(manage_roles=True)
@badge.command(name="add", pass_context=True, no_pm=True)
async def addbadge(
        self, ctx, name: str, bg_img: str, border_color: str, price: int, *, description: str
):
    """Add a badge. name = "Use Quotes", Colors = #hex. bg_img = url, price = -1(non-purchasable), 0,..."""

    user = ctx.message.author
    guild = ctx.message.guild

    # check members
    required_members = 35
    members = 0
    for member in guild.members:
        if not member.bot:
            members += 1

    if str(user.id) == self.owner:
        pass
    elif members < required_members:
        await ctx.send(
            "**You may only add badges in guilds with {}+ non-bot members**".format(
                required_members
            )
        )
        return

    if "-global" in description and str(user.id) == self.owner:
        description = description.replace("-global", "")
        guildid = "global"
        guildname = "global"
    else:
        guildid = str(guild.id)
        guildname = guild.name

    if "." in name:
        await ctx.send("**Name cannot contain `.`**")
        return

    if not await self._valid_image_url(bg_img):
        await ctx.send("**Background is not valid. Enter hex or image url!**")
        return

    if not _is_hex(border_color):
        await ctx.send("**Border color is not valid!**")
        return

    if price < -1:
        await ctx.send("**Price is not valid!**")
        return

    if len(description.split(" ")) > 40:
        await ctx.send("**Description is too long! <=40**")
        return

    badges = db.badges.find_one({"guild_id": guildid})
    if not badges:
        db.badges.insert_one({"guild_id": guildid, "badges": {}})
        badges = db.badges.find_one({"guild_id": guildid})

    new_badge = {
        "badge_name": name,
        "bg_img": bg_img,
        "price": price,
        "description": description,
        "border_color": border_color,
        "guild_id": guildid,
        "guild_name": guildname,
        "priority_num": 0,
    }

    if name not in badges["badges"].keys():
        # create the badge regardless
        badges["badges"][name] = new_badge
        db.badges.update_one({"guild_id": guildid}, {"$set": {"badges": badges["badges"]}})
        await ctx.send("**`{}` Badge added in `{}` guild.**".format(name, guildname))
    else:
        # update badge in the guild
        badges["badges"][name] = new_badge
        db.badges.update_one({"guild_id": guildid}, {"$set": {"badges": badges["badges"]}})

        # go though all users and update the badge. Doing it this way because dynamic does more accesses when doing profile
        for user in db.users.find({}):
            try:
                user = _badge_convert_dict(user)
                userbadges = user["badges"]
                badge_name = "{}_{}".format(name, guildid)
                if badge_name in userbadges.keys():
                    user_priority_num = userbadges[badge_name]["priority_num"]
                    new_badge[
                        "priority_num"
                    ] = user_priority_num  # maintain old priority number set by user
                    userbadges[badge_name] = new_badge
                    db.users.update_one(
                        {"user_id": user["user_id"]}, {"$set": {"badges": userbadges}}
                    )
            except:
                pass
        await ctx.send("**The `{}` badge has been updated**".format(name))


@checks.is_owner()
@badge.command(no_pm=True)
async def type(self, ctx, name: str):
    """circles or bars."""
    valid_types = ["circles", "bars"]
    if name.lower() not in valid_types:
        await ctx.send("**That is not a valid badge type!**")
        return

    self.settings["badge_type"] = name.lower()
    await ctx.send("**Badge type set to `{}`**".format(name.lower()))
    fileIO("settings.json", "save", self.settings)


@checks.mod_or_permissions(manage_roles=True)
@badge.command(pass_context=True, no_pm=True)
async def give(self, ctx, user: discord.Member, name: str):
    """Give a user a badge with a certain name"""
    org_user = ctx.message.author
    guild = org_user.guild
    # creates user if doesn't exist
    await self._create_user(user, guild)
    userinfo = db.users.find_one({"user_id": str(str(user.id))})
    userinfo = _badge_convert_dict(userinfo)

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("Leveler commands for this guild are disabled.")
        return

    guildbadges = db.badges.find_one({"guild_id": str(guild.id)})
    badges = guildbadges["badges"]
    badge_name = "{}_{}".format(name, str(guild.id))

    if name not in badges:
        await ctx.send("**That badge doesn't exist in this guild!**")
        return
    elif badge_name in badges.keys():
        await ctx.send("**{} already has that badge!**".format(self._is_mention(user)))
        return
    else:
        userinfo["badges"][badge_name] = badges[name]
        db.users.update_one(
            {"user_id": str(str(user.id))}, {"$set": {"badges": userinfo["badges"]}}
        )
        await ctx.send(
            "**{} has just given `{}` the `{}` badge!**".format(
                self._is_mention(org_user), self._is_mention(user), name
            )
        )


@checks.mod_or_permissions(manage_roles=True)
@badge.command(pass_context=True, no_pm=True)
async def take(self, ctx, user: discord.Member, name: str):
    """Take a user's badge."""
    org_user = ctx.message.author
    guild = org_user.guild
    # creates user if doesn't exist
    await self._create_user(user, guild)
    userinfo = db.users.find_one({"user_id": str(str(user.id))})
    userinfo = _badge_convert_dict(userinfo)

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("Leveler commands for this guild are disabled.")
        return

    guildbadges = db.badges.find_one({"guild_id": str(guild.id)})
    badges = guildbadges["badges"]
    badge_name = "{}_{}".format(name, str(guild.id))

    if name not in badges:
        await ctx.send("**That badge doesn't exist in this guild!**")
    elif badge_name not in userinfo["badges"]:
        await ctx.send("**{} does not have that badge!**".format(self._is_mention(user)))
    else:
        if userinfo["badges"][badge_name]["price"] == -1:
            del userinfo["badges"][badge_name]
            db.users.update_one(
                {"user_id": str(str(user.id))}, {"$set": {"badges": userinfo["badges"]}}
            )
            await ctx.send(
                "**{} has taken the `{}` badge from {}! :upside_down:**".format(
                    self._is_mention(org_user), name, self._is_mention(user)
                )
            )
        else:
            await ctx.send("**You can't take away purchasable badges!**")


@checks.mod_or_permissions(manage_roles=True)
@badge.command(name="link", no_pm=True, pass_context=True)
async def linkbadge(self, ctx, badge_name: str, level: int):
    """Associate a role with a level."""
    guild = ctx.message.guild
    guildbadges = db.badges.find_one({"guild_id": str(guild.id)})

    if guildbadges == None:
        await ctx.send("**This guild does not have any badges!**")
        return

    if badge_name not in guildbadges["badges"].keys():
        await ctx.send("**Please make sure the `{}` badge exists!**".format(badge_name))
        return
    else:
        guild_linked_badges = db.badgelinks.find_one({"guild_id": str(guild.id)})
        if not guild_linked_badges:
            new_guild = {"guild_id": str(guild.id), "badges": {badge_name: str(level)}}
            db.badgelinks.insert_one(new_guild)
        else:
            guild_linked_badges["badges"][badge_name] = str(level)
            db.badgelinks.update_one(
                {"guild_id": str(guild.id)},
                {"$set": {"badges": guild_linked_badges["badges"]}},
            )
        await ctx.send(
            "**The `{}` badge has been linked to level `{}`**".format(badge_name, level)
        )


@checks.admin_or_permissions(manage_roles=True)
@badge.command(name="unlink", no_pm=True, pass_context=True)
async def unlinkbadge(self, ctx, badge_name: str):
    """Delete a role/level association."""
    guild = ctx.message.guild

    guild_linked_badges = db.badgelinks.find_one({"guild_id": str(guild.id)})
    badge_links = guild_linked_badges["badges"]

    if badge_name in badge_links.keys():
        await ctx.send(
            "**Badge/Level association `{}`/`{}` removed.**".format(
                badge_name, badge_links[badge_name]
            )
        )
        del badge_links[badge_name]
        db.badgelinks.update_one(
            {"guild_id": str(guild.id)}, {"$set": {"badges": badge_links}}
        )
    else:
        await ctx.send("**The `{}` badge is not linked to any levels!**".format(badge_name))


@checks.mod_or_permissions(manage_roles=True)
@badge.command(name="listlinks", no_pm=True, pass_context=True)
async def listbadge(self, ctx):
    """List level/role associations."""
    guild = ctx.message.guild
    user = ctx.message.author

    guild_badges = db.badgelinks.find_one({"guild_id": str(guild.id)})

    em = discord.Embed(description="", colour=user.colour)
    em.set_author(
        name="Current Badge - Level Links for {}".format(guild.name), icon_url=guild.icon_url
    )

    if guild_badges == None or "badges" not in guild_badges or guild_badges["badges"] == {}:
        msg = "None"
    else:
        badges = guild_badges["badges"]
        msg = "**Badge** → Level\n"
        for badge in badges.keys():
            msg += "**• {} →** {}\n".format(badge, badges[badge])

    em.description = msg
    await ctx.send(embed=em)
