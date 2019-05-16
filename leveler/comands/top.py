from typing import Dict, ItemsView, Union

from redbot.core import commands

import discord
import math
import operator

from ..static_methods import _truncate_text, all_rep, all_exp, guild_level, guild_exp
from ..permissions import leveler_enabled


@commands.command(pass_context=True, no_pm=True)
@leveler_enabled
async def top(ctx, *options):
    """Displays leaderboard. Add "global" parameter for global"""

    if "-rep" in options and "-global" in options:
        return await global_rep(ctx, options)
    elif "-global" in options:
        return await global_exp(ctx, options)
    elif "-rep" in options:
        return await local_rep(ctx, options)
    elif "-lvl" in options or "-level" in options:
        return await local_level(ctx, options)
    else:
        return await local_exp(ctx, options)


async def global_rep(ctx, options):
    user = ctx.author
    users = await all_rep()

    user_rep = users.get(user.id, 0)
    user_rank = sum(1 for rep in users.values() if rep > user_rep) + 1

    await send_page(
        ctx,
        users.items(),
        options,
        "Rep",
        f"Your Rank: {user_rank}         Rep: {user_rep}",
        user,
        f"Global Rep Leaderboard for {ctx.bot.user.name}\n",
        ctx.bot.user.avatar_url
    )


async def global_exp(ctx, options):
    user = ctx.author
    users = await all_exp()

    user_exp = users.get(user.id, 0)
    user_rank = sum(1 for rep in users.values() if rep > user_exp) + 1

    await send_page(
        ctx,
        users.items(),
        options,
        "Points",
        f"Your Rank: {user_rank}         Rep: {user_exp}",
        user,
        f"Global Points Leaderboard for {ctx.bot.user.name}\n",
        ctx.bot.user.avatar_url
    )


async def local_rep(ctx, options):
    user = ctx.author
    guild = ctx.guild
    all_users = await all_rep()
    users = {u.id: all_users.get(u.id, 0) for u in guild.members}

    user_rep = users[user.id]
    user_rank = sum(1 for rep in users.values() if rep > user_rep) + 1

    await send_page(
        ctx,
        users.items(),
        options,
        "Rep",
        f"Your Rank: {user_rank}         Rep: {user_rep}",
        user,
        f"Rep Leaderboard for {guild.name}\n",
        guild.icon_url
    )


async def local_level(ctx, options):
    user = ctx.author
    guild = ctx.guild
    users = await guild_level(guild)

    user_level = users.get(user.id, 0)
    user_rank = sum(1 for level in users.values() if level > user_level) + 1

    await send_page(
        ctx,
        users.items(),
        options,
        "Level",
        f"Your Rank: {user_rank}         Level: {user_level}",
        user,
        f"Level Leaderboard for {guild.name}\n",
        guild.icon_url
    )


async def local_exp(ctx, options):
    user = ctx.author
    guild = ctx.guild
    users = await guild_exp(guild)

    user_exp = users.get(user.id, 0)
    user_rank = sum(1 for exp in users.values() if exp > user_exp) + 1

    await send_page(
        ctx,
        users.items(),
        options,
        "Exp",
        f"Your Rank: {user_rank}         Exp: {user_exp}",
        user,
        f"Exp Leaderboard for {guild.name}\n",
        guild.icon_url
    )


async def send_page(ctx, users: Union[Dict[int, int], ItemsView[int, int]], options, board_type, footer_text, user, title, icon_url):

    sorted_list = sorted(users, key=operator.itemgetter(1), reverse=True)

    # multiple page support
    page = 1
    per_page = 15
    pages = math.ceil(len(sorted_list) / per_page)
    for option in options:
        if str(option).isdigit():
            if page >= 1 and int(option) <= pages:
                page = int(str(option))
            else:
                await ctx.send(
                    "**Please enter a valid page number! (1 - {})**".format(str(pages))
                )
                return
            break

    msg = ""
    msg += "**Rank              Name (Page {}/{})**\n".format(page, pages)
    rank = 1 + per_page * (page - 1)
    start_index = per_page * page - per_page
    end_index = per_page * page

    default_label = "   "
    special_labels = ["♔", "♕", "♖", "♗", "♘", "♙"]

    for user_id, rep in sorted_list[start_index:end_index]:
        if rank - 1 < len(special_labels):
            label = special_labels[rank - 1]
        else:
            label = default_label

        user = ctx.bot.get_user(user_id) or "Unknown User"

        msg += u"`{:<2}{:<2}{:<2}   # {:<22}".format(
            rank, label, u"➤", _truncate_text(str(user), 20)
        )
        msg += f"Total {board_type}: {rep}`\n"
        rank += 1
    msg += "----------------------------------------------------\n"
    msg += "`{}`".format(footer_text)

    em = discord.Embed(description="", colour=user.colour)
    em.set_author(name=title, icon_url=icon_url)
    em.description = msg

    await ctx.send(embed=em)
