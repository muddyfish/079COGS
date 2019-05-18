from redbot.core import commands
import discord
from redbot.core import checks
from ..config import db
from ..path_munger import fileIO
from ..static_methods import _valid_image_url
from ..permissions import leveler_enabled


prefix = "!"


@checks.admin_or_permissions(manage_guild=True)
@commands.group(pass_context=True)
@leveler_enabled
async def lvladmin(ctx):
    """Admin Toggle Features"""
    if ctx.invoked_subcommand is None:
        return


@checks.is_owner()
@lvladmin.group(pass_context=True)
async def overview(ctx):
    """A list of settings"""
    user = ctx.message.author

    disabled_guilds = []
    level_messages = []
    private_levels = []
    locked_channels = []

    for guild in ctx.bot.guilds:
        guild_info = db.guild(guild)
        if await guild_info.disabled():
            disabled_guilds.append(guild.name)
        msg_lock = await guild_info.lvl_msg_lock()
        if msg_lock:
            for channel in guild.channels:
                if msg_lock == channel.id:
                    locked_channels.append(f"\n{guild.name} → #{channel.name}")
        if await guild_info.lvl_msg():
            level_messages.append(guild.name)
        if await guild_info.private_lvl_msg():
            private_levels.append(guild.name)

    msg = \
        f"**Guilds:** {len(ctx.bot.guilds)}\n"\
        f"**Unique Users:** {len(ctx.bot.users)}\n"\
        f"**Mentions:** {await db.mention()}\n"\
        f"**Background Price:** {await db.bg_price()}\n"\
        f"**Badge type:** {await db.badge_type()}\n"\
        f"**Disabled guilds:** {', '.join(disabled_guilds)}\n"\
        f"**Enabled Level Messages:** {', '.join(level_messages)}\n"\
        f"**Private Level Messages:** {', '.join(private_levels)}\n"\
        f"**Channel Locks:** {', '.join(locked_channels)}\n"
    em = discord.Embed(
        description=msg,
        colour=user.colour
    )
    em.set_author(name=f"Settings Overview for {ctx.bot.user.name}")
    await ctx.send(embed=em)


@lvladmin.command(pass_context=True, no_pm=True)
async def msgcredits(ctx, credits: int = 0):
    """Credits per message logged. Default = 0"""
    channel = ctx.message.channel
    guild = ctx.message.guild

    if credits < 0 or credits > 1000:
        return await ctx.send("**Please enter a valid number (0 - 1000)**".format(channel.name))

    await db.guild(guild).msg_credits.set(credits)
    await ctx.send(f"**Credits per message logged set to `{credits}`.**")


@lvladmin.command(name="lock", pass_context=True, no_pm=True)
async def lvlmsglock(ctx):
    """Locks levelup messages to one channel. Disable command via locked channel."""
    channel = ctx.message.channel
    guild = ctx.message.guild

    guild_info = db.guild(guild)
    lvl_msg_lock = await guild_info.lvl_msg_lock()

    if lvl_msg_lock == channel.id:
        await guild_info.lvl_msg_lock.unset()
        return await ctx.send("**Level-up message lock disabled.**")

    await guild_info.lvl_msg_lock.set(channel.id)

    if lvl_msg_lock is None:
        await ctx.send(f"**Level-up messages locked to `#{channel.name}`**")
    else:
        await ctx.send(f"**Level-up message lock changed to `#{channel.name}`.**")


@checks.is_owner()
@lvladmin.command(no_pm=True)
async def setprice(ctx, price: int):
    """Set a price for background changes."""
    if price < 0:
        return await ctx.send("**That is not a valid background price.**")
    await db.bg_price.set(price)
    await ctx.send(f"**Background price set to: `{price}`!**")


@checks.is_owner()
@lvladmin.command(no_pm=True)
async def mention(ctx):
    """Toggle mentions on messages."""
    await db.mention.set(not await db.mention())


@checks.admin_or_permissions(manage_guild=True)
@lvladmin.command(pass_context=True, no_pm=True)
async def toggle(ctx):
    """Toggle most leveler commands on the current guild."""
    guild = ctx.message.guild
    guild_info = db.guild(guild)
    disabled = await guild_info.disabled()

    if disabled:
        await guild_info.disabled.set(False)
        await ctx.send(f"**Leveler enabled on `{guild.name}`.**")
    else:
        await guild_info.disabled.set(True)
        await ctx.send(f"**Leveler disabled on `{guild.name}`.**")


@checks.admin_or_permissions(manage_guild=True)
@lvladmin.command(name="alerts", pass_context=True, no_pm=True)
async def lvlalert(ctx):
    """Toggle level-up messages on the guild."""
    guild = ctx.message.guild
    guild_info = db.guild(guild)
    lvl_msg = await guild_info.lvl_msg()

    if lvl_msg:
        await guild_info.lvl_msg.set(False)
        await ctx.send(f"**Level-up alerts disabled for `{guild.name}`.**")
    else:
        await guild_info.lvl_msg.set(True)
        await ctx.send(f"**Level-up alerts enabled for `{guild.name}`.**")


@checks.admin_or_permissions(manage_guild=True)
@lvladmin.command(name="private", pass_context=True, no_pm=True)
async def lvlprivate(ctx):
    """Toggles if lvl alert is a private message to the user."""
    guild = ctx.message.guild
    guild_info = db.guild(guild)
    private_lvl_msg = await guild_info.lvl_msg()

    if private_lvl_msg:
        await guild_info.private_lvl_msg.set(False)
        await ctx.send(f"**Private level-up alerts disabled for `{guild.name}`.**")
    else:
        await guild_info.private_lvl_msg.set(True)
        await ctx.send(f"**Private level-up alerts enabled for `{guild.name}`.**")


@lvladmin.group(name="bg", pass_context=True)
async def lvladminbg(ctx):
    """Admin Background Configuration"""
    if ctx.invoked_subcommand is None or isinstance(ctx.invoked_subcommand, commands.Group):
        return


@checks.is_owner()
@lvladminbg.command(no_pm=True)
async def addprofilebg(ctx, name: str, url: str):
    """Add a profile background. Proportions: (290px x 290px)"""
    backgrounds = await db.backgrounds()
    if name in backgrounds["profile"]:
        await ctx.send("**That profile background name already exists!**")
    elif not await _valid_image_url(url):
        await ctx.send("**That is not a valid image url!**")
    else:
        await db.backgrounds.set(backgrounds)
        await ctx.send(f"**New profile background(`{name}`) added.**")


@checks.is_owner()
@lvladminbg.command(no_pm=True)
async def addrankbg(ctx, name: str, url: str):
    """Add a rank background. Proportions: (360px x 100px)"""
    backgrounds = await db.backgrounds()
    if name in backgrounds["rank"]:
        await ctx.send("**That rank background name already exists!**")
    elif not await _valid_image_url(url):
        await ctx.send("**That is not a valid image url!**")
    else:
        await db.backgrounds.set(backgrounds)
        await ctx.send(f"**New rank background(`{name}`) added.**")


@checks.is_owner()
@lvladminbg.command(no_pm=True)
async def addlevelbg(ctx, name: str, url: str):
    """Add a level-up background. Proportions: (85px x 105px)"""
    backgrounds = await db.backgrounds()
    if name in backgrounds["levelup"]:
        await ctx.send("**That level-up background name already exists!**")
    elif not await _valid_image_url(url):
        await ctx.send("**That is not a valid image url!**")
    else:
        await db.backgrounds.set(backgrounds)
        await ctx.send(f"**New level-up background(`{name}`) added.**")


@checks.is_owner()
@lvladminbg.command(no_pm=True, pass_context=True)
async def setcustombg(ctx, bg_type: str, user_id: int, img_url: str):
    """Set one-time custom background"""
    valid_types = ["profile", "rank", "levelup"]
    type_input = bg_type.lower()

    if type_input not in valid_types:
        return await ctx.send("**Please choose a valid type: `profile`, `rank`, `levelup`.")
    if not user_id:
        return await ctx.send("**That is not a valid user id!**")
    if not await _valid_image_url(img_url):
        return await ctx.send("**That is not a valid image url!**")

    user_info = db.user(user_id)
    await user_info.get_attr(f"{type_input}_background").set(img_url)

    await ctx.send(f"**User {user_id} custom {bg_type} background set.**")


@checks.is_owner()
@lvladminbg.command(no_pm=True)
async def delprofilebg(ctx, name: str):
    """Delete a profile background."""
    backgrounds = await db.backgrounds()

    if name in backgrounds["profile"]:
        del backgrounds["profile"][name]
        await db.backgrounds.set(backgrounds)
        await ctx.send(f"**The profile background(`{name}`) has been deleted.**")
    else:
        await ctx.send("**That profile background name doesn't exist.**")


@checks.is_owner()
@lvladminbg.command(no_pm=True)
async def delrankbg(ctx, name: str):
    """Delete a rank background."""
    backgrounds = await db.backgrounds()

    if name in backgrounds["rank"]:
        del backgrounds["rank"][name]
        await db.backgrounds.set(backgrounds)
        await ctx.send(f"**The rank background(`{name}`) has been deleted.**")
    else:
        await ctx.send("**That rank background name doesn't exist.**")


@checks.is_owner()
@lvladminbg.command(no_pm=True)
async def dellevelbg(ctx, name: str):
    """Delete a level background."""
    backgrounds = await db.backgrounds()

    if name in backgrounds["levelup"]:
        del backgrounds["levelup"][name]
        await db.backgrounds.set(backgrounds)
        await ctx.send(f"**The level-up background(`{name}`) has been deleted.**")
    else:
        await ctx.send("**That level-up background name doesn't exist.**")
