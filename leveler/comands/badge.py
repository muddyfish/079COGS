from redbot.core import commands
import discord
from redbot.core.utils.chat_formatting import pagify
import operator
from leveler.leveler import db
from redbot.core import checks, bank
from ..static_methods import _badge_convert_dict, _is_hex, get_user_name, _valid_image_url, get_user_display_name


from ..config import db
from ..permissions import leveler_enabled

prefix = "!"


@commands.group(pass_context=True)
@leveler_enabled
async def badge(ctx):
    """Badge Configuration Options"""
    if ctx.invoked_subcommand is None:
        return


@badge.command(name="available", pass_context=True, no_pm=True)
async def available(ctx):
    """Get a list of available badges for guild or 'global'."""
    user = ctx.message.author
    guild = ctx.message.guild

    ids = [
        (await db.badges(), "Global", ctx.bot.user.avatar_url),
        (await db.guild(guild).badges(), guild.name, guild.icon_url),
    ]

    title_text = "**Available Badges**"
    for i, (badges, guild_name, icon_url) in enumerate(ids):
        em = discord.Embed(description="", colour=user.colour)
        em.set_author(name=guild_name, icon_url=icon_url)
        msg = ""
        if badges:
            for badge_name, badge_info in badges.items():
                if badge_info["price"] == -1:
                    price = "Non-purchasable"
                elif badge_info["price"] == 0:
                    price = "Free"
                else:
                    price = badge_info["price"]

                msg += f"**• {badge_name}** ({price}) - {badge_info['description']}\n"
        else:
            msg = "None"

        em.description = msg
        if i == 0:
            await ctx.send(title_text, embed=em)
        else:
            await ctx.send(embed=em)


@badge.command(name="list", pass_context=True, no_pm=True)
async def listuserbadges(ctx, user: discord.Member = None):
    """Get the badges of a user."""
    if user is None:
        user = ctx.message.author
    badges = await db.user(user).badges()

    # sort
    priority_badges = []
    for badge_name, badge in badges.items():
        priority_num = badge["priority_num"]
        if priority_num != -1:
            priority_badges.append((badge, priority_num))
    sorted_badges = sorted(priority_badges, key=operator.itemgetter(1), reverse=True)

    badge_ranks = []
    for i, (badge, priority_num) in enumerate(sorted_badges[:12], 1):
        badge_ranks.append(f"**{i}. {badge['badge_name']}** ({badge['guild_name']}) [{priority_num}] **—** {badge['description']}")
    badge_ranks = "\n".join(badge_ranks) or "None"

    em = discord.Embed(description="", colour=user.colour)

    total_pages = 0
    for _ in pagify(badge_ranks, ["\n"]):
        total_pages += 1

    for i, page in enumerate(pagify(badge_ranks, ["\n"]), 1):
        em.description = page
        em.set_author(name=f"Badges for {user.name}", icon_url=user.avatar_url)
        em.set_footer(text=f"Page {i} of {total_pages}")
        await ctx.send(embed=em)


@badge.command(name="buy", pass_context=True, no_pm=True)
async def buy(ctx, name: str, global_badge: str = None):
    '''Get a badge from repository. optional = "-global"'''
    user = ctx.message.author
    guild = ctx.message.guild
    if global_badge == "-global":
        badges = await db.badges()
        guild_id = "global"
    else:
        badges = await db.guild(guild).badges()
        guild_id = guild.id

    user_info = db.user(user)
    user_badges = await user_info.badges()

    if not badges:
        return await ctx.send(f"**There are no badges to get! (try `{prefix[0]}badge get [name]`).**")
    if name not in badges:
        return await ctx.send("**The badge `{name}` does not exist. (try `{prefix[0]}badge available`)**")
    if f"{name}_{guild_id}" in user_badges:
        return await ctx.send(f"**{user.name}, you already have this badge!**")

    badge_info = badges[name]
    if badge_info["price"] == -1:
        return await ctx.send("**That badge is not purchasable.**")
    if badge_info["price"] == 0:
        user_badges[f"{name}_{guild_id}"] = badges[name]
        await user_info.badges.set(user_badges)
        return await ctx.send(f"**`{name}` has been obtained.**")

    await ctx.send(f'**{get_user_name(user)}, you are about to buy the `{name}` badge for `{badge_info["price"]}`. Confirm by typing "yes"**')
    answer = await ctx.bot.wait_for_message(timeout=15, author=user)
    if answer is None:
        return await ctx.send("**Purchase canceled.**")
    if "yes" not in answer.content.lower():
        return await ctx.send("**Badge not purchased.**")
    if badge_info["price"] <= await bank.get_balance(user):
        await bank.withdraw_credits(user, badge_info["price"])

        user_badges[f"{name}_{guild_id}"] = badges[name]
        await user_info.badges.set(user_badges)

        await ctx.send(f"**You have bought the `{name}` badge for `{badge_info['price']}`.**")
    elif bank.get_balance(user) < badge_info["price"]:
        return await ctx.send(f"**Not enough money! Need `{badge_info['price'] - bank.get_balance(user)}` more.**")
    else:
        return await ctx.send(f"**User does not exist in bank. Do {prefix[0]}bank register**")


@badge.command(name="set", pass_context=True, no_pm=True)
async def set(ctx, name: str, priority_num: int):
    """Set a badge to profile. -1(invis), 0(not on profile), max: 5000."""
    user = ctx.message.author

    user_info = db.user(user)
    user_badges = await user_info.badges()

    if priority_num < -1 or priority_num > 5000:
        await ctx.send("**Invalid priority number! -1-5000**")
        return

    badge = next((badge for badge in user_badges if badge["badge_name"] == name), None)
    if badge is None:
        return await ctx.send("**You don't have that badge!**")

    badge["priority_num"] = priority_num
    await user_info.badges.set(user_badges)
    await ctx.send(
        "**The `{}` badge priority has been set to `{}`!**".format(
            badge["badge_name"], priority_num
        )
    )


@checks.mod_or_permissions(manage_roles=True)
@badge.command(name="add", pass_context=True, no_pm=True)
async def addbadge(ctx, name: str, bg_img: str, border_color: str, price: int, *, description: str):
    """Add a badge. name = "Use Quotes", Colors = #hex. bg_img = url, price = -1(non-purchasable), 0,..."""

    user = ctx.message.author
    guild = ctx.message.guild

    # check members
    required_members = 35
    members = sum(1 for member in guild.members if not member.bot)

    guildid = str(guild.id)
    guildname = guild.name

    if user == ctx.bot.owner:
        if "-global" in description:
            guildid = "global"
            guildname = "global"
    elif members < required_members:
        return await ctx.send(f"**You may only add badges in guilds with {required_members}+ non-bot members**")

    if "." in name:
        return await ctx.send("**Name cannot contain `.`**")

    if not await _valid_image_url(ctx, bg_img):
        return await ctx.send("**Background is not valid. Enter hex or image url!**")

    if not _is_hex(border_color):
        return await ctx.send("**Border color is not valid!**")

    if price < -1:
        return await ctx.send("**Price is not valid!**")

    if len(description.split(" ")) > 40:
        return await ctx.send("**Description is too long! <=40**")

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

    badge_id = f"{name}_{guildid}"

    badges = await db.badges()
    badges[name] = new_badge
    await db.badges.set(badges)

    if badge_id not in badges:
        # create the badge regardless
        await ctx.send(f"**`{name}` Badge added in `{guildname}` guild.**")
    else:
        for user_id, user_info in (await db.all_users()).items():
            if badge_id in user_info["badges"]:
                user_priority_num = user_info["badges"][badge_id]["priority_num"]
                new_badge[
                    "priority_num"
                ] = user_priority_num  # maintain old priority number set by user
                user_info["badges"][badge_id] = new_badge
                await db.user(user_id).badges.set(user_info["badges"])
        await ctx.send(f"**The `{name}` badge has been updated**")


@checks.is_owner()
@badge.command(no_pm=True)
async def type(ctx, name: str):
    """circles or bars."""
    valid_types = ["circles"]
    if name.lower() not in valid_types:
        await ctx.send("**That is not a valid badge type!**")
        return
    await db.badge_type.set(name.lower())
    await ctx.send(f"**Badge type set to `{name.lower()}`**")


@checks.mod_or_permissions(manage_roles=True)
@badge.command(pass_context=True, no_pm=True)
async def give(ctx, user: discord.Member, name: str):
    """Give a user a badge with a certain name"""
    org_user = ctx.message.author
    guild = org_user.guild

    user_info = db.user(user)
    user_badges = await user_info.badges()
    badges = await db.guild(guild).badges()

    badge_id = f"{name}_{guild.id}"

    if name not in badges:
        return await ctx.send("**That badge doesn't exist in this guild!**")
    if badge_id in user_badges:
        return await ctx.send(f"**{get_user_name(user)} already has that badge!**")

    user_badges[badge_id] = badges[name]
    await user_badges.badges.set(user_badges)
    await ctx.send(f"**{get_user_name(org_user)} has just given `{get_user_name(user)}` the `{name}` badge!**")


@checks.mod_or_permissions(manage_roles=True)
@badge.command(pass_context=True, no_pm=True)
async def take(ctx, user: discord.Member, name: str):
    """Take a user's badge."""
    org_user = ctx.message.author
    guild = org_user.guild

    user_info = db.user(user)
    user_badges = await user_info.badges()
    badge_id = f"{name}_{guild.id}"

    if badge_id not in user_badges:
        return await ctx.send(f"**{get_user_name(user)} does not have that badge!**")
    if user_badges[badge_id]["price"] != -1:
        return await ctx.send("**You can't take away purchasable badges!**")
    del user_badges[badge_id]
    await user_badges.badges.set(user_badges)
    await ctx.send(f"**{get_user_name(org_user)} has taken the `{name}` badge from {get_user_name(user)}! :upside_down:**")


@checks.mod_or_permissions(manage_roles=True)
@badge.command(name="link", no_pm=True, pass_context=True)
async def linkbadge(ctx, badge_name: str, level: int):
    """Associate a role with a level."""
    guild = ctx.message.guild
    badges = await db.guild(guild).badges()
    badge_links = await db.guild(guild).badge_links()

    if not badges:
        return await ctx.send("**This guild does not have any badges!**")

    if badge_name not in badges:
        return await ctx.send(f"**Please make sure the `{badge_name}` badge exists!**")
    badge_links[badge_name] = level
    await db.guild(guild).badge_links.set(badge_links)
    await ctx.send(f"**The `{badge_name}` badge has been linked to level `{level}`**")


@checks.admin_or_permissions(manage_roles=True)
@badge.command(name="unlink", no_pm=True, pass_context=True)
async def unlinkbadge(ctx, badge_name: str):
    """Delete a role/level association."""
    guild = ctx.message.guild

    badge_links = await db.guild(guild).badge_links()

    if badge_name not in badge_links:
        await ctx.send(f"**The `{badge_name}` badge is not linked to any levels!**")

    del badge_links[badge_name]
    await db.guild(guild).badge_links.set(badge_links)
    await ctx.send(f"**Badge/Level association `{badge_name}`/`{badge_links[badge_name]}` removed.**")


@checks.mod_or_permissions(manage_roles=True)
@badge.command(name="listlinks", no_pm=True, pass_context=True)
async def listbadge(ctx):
    """List level/role associations."""
    guild = ctx.message.guild
    user = ctx.message.author

    badge_links = await db.guild(guild).badge_links()

    em = discord.Embed(description="", colour=user.colour)
    em.set_author(
        name=f"Current Badge - Level Links for {guild.name}",
        icon_url=guild.icon_url
    )

    if not badge_links:
        msg = "None"
    else:
        msg = "**Badge** → Level\n"
        for badge, level in badge_links.items():
            msg += f"**• {badge} →** {level}\n"

    em.description = msg
    await ctx.send(embed=em)
