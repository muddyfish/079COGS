from typing import NoReturn, Dict
from redbot.core import commands
import discord
from discord import Embed
from ..config import db
from ..permissions import leveler_enabled


@commands.command(name="backgrounds", pass_context=True, no_pm=True)
@leveler_enabled
async def disp_backgrounds(ctx, type: str = None):
    """Gives a list of backgrounds. [p]backgrounds [profile|rank|levelup]"""

    if type is None:
        await all_catagories(ctx)
    else:
        await single_catagory(ctx, type.lower())


async def all_catagories(ctx) -> NoReturn:
    user = ctx.message.author
    backgrounds = await db.backgrounds()

    em = discord.Embed(description="", colour=user.colour)
    em.set_author(
        name=f"All Backgrounds for {ctx.bot.user.name}",
        icon_url=ctx.bot.user.avatar_url,
    )
    for category, bgs in backgrounds.items():
        await add_category(em, category, bgs)
    await ctx.send(embed=em)


async def single_catagory(ctx, catagory: str) -> NoReturn:
    user = ctx.message.author
    backgrounds = await db.backgrounds()
    if catagory not in backgrounds:
        return await ctx.send(f"**Invalid Background Type. ({', '.join(backgrounds)})**")

    em = discord.Embed(description="", colour=user.colour)
    em.set_author(
        name=f"{catagory.title()} Backgrounds for {ctx.bot.user.name}",
        icon_url=ctx.bot.user.avatar_url,
    )
    await add_category(em, catagory, backgrounds[catagory])
    await ctx.send(embed=em)


async def add_category(embed: Embed, category: str, backgrounds: Dict[str, str]) -> NoReturn:
    max_backgrounds = 18

    bg_urls = [
        f"[{background_name}]({backgrounds[background_name]})"
        for background_name in sorted(backgrounds)
    ]
    bgs = ", ".join(bg_urls[:min(max_backgrounds, len(bg_urls))])
    if len(bg_urls) >= max_backgrounds:
        bgs += "..."
    embed.add_field(name=category.upper(), value=bgs, inline=False)
