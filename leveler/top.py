from redbot.core import commands
import discord
import math
import operator
from .leveler import db
from .static_methods import _find_guild_rank, _find_guild_exp, _find_global_rank, _find_global_rep_rank, _find_guild_rep_rank, _find_guild_level_rank, _required_exp, _truncate_text


@commands.command(pass_context=True, no_pm=True)
async def top(self, ctx, *options):
    """Displays leaderboard. Add "global" parameter for global"""
    guild = ctx.message.guild
    user = ctx.message.author

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("**Leveler commands for this guild are disabled!**")
        return

    users = []
    user_stat = None
    if "-rep" in options and "-global" in options:
        title = "Global Rep Leaderboard for {}\n".format(self.bot.user.name)
        for userinfo in db.users.find({}):
            try:
                users.append((userinfo["username"], userinfo["rep"]))
            except:
                users.append((userinfo["user_id"], userinfo["rep"]))

            if str(user.id) == userinfo["user_id"]:
                user_stat = userinfo["rep"]

        board_type = "Rep"
        footer_text = "Your Rank: {}         {}: {}".format(
            await _find_global_rep_rank(user), board_type, user_stat
        )
        icon_url = self.bot.user.avatar_url
    elif "-global" in options:
        title = "Global Exp Leaderboard for {}\n".format(self.bot.user.name)
        for userinfo in db.users.find({}):
            try:
                users.append((userinfo["username"], userinfo["total_exp"]))
            except:
                users.append((userinfo["user_id"], userinfo["total_exp"]))

            if str(user.id) == userinfo["user_id"]:
                user_stat = userinfo["total_exp"]

        board_type = "Points"
        footer_text = "Your Rank: {}         {}: {}".format(
            await _find_global_rank(user), board_type, user_stat
        )
        icon_url = self.bot.user.avatar_url
    elif "-rep" in options:
        title = "Rep Leaderboard for {}\n".format(guild.name)
        for userinfo in db.users.find({}):
            if "servers" in userinfo and str(guild.id) in userinfo["servers"]:
                try:
                    users.append((userinfo["username"], userinfo["rep"]))
                except:
                    users.append((userinfo["user_id"], userinfo["rep"]))

            if str(user.id) == userinfo["user_id"]:
                user_stat = userinfo["rep"]

        board_type = "Rep"
        footer_text = "Your Rank: {}         {}: {}".format(
            await _find_guild_rep_rank(user, guild), board_type, user_stat
        )
        icon_url = guild.icon_url
    elif "-lvl" in options or "-level" in options:
        title = "Level Leaderboard for {}\n".format(guild.name)
        for userinfo in db.users.find({}):
            if "servers" in userinfo and str(guild.id) in userinfo["servers"]:
                level = userinfo["servers"][str(guild.id)]["level"]
                try:
                    users.append((userinfo["username"], level))
                except:
                    users.append((userinfo["user_id"], level))

            if str(user.id) == userinfo["user_id"]:
                user_stat = userinfo["servers"][str(guild.id)]["level"]

        board_type = "Level"
        footer_text = "Your Rank: {}         {}: {}".format(
            await _find_guild_level_rank(user, guild), board_type, user_stat
        )
        icon_url = guild.icon_url
    else:
        title = "Exp Leaderboard for {}\n".format(guild.name)
        for userinfo in db.users.find({}):
            try:
                if "servers" in userinfo and str(guild.id) in userinfo["servers"]:
                    guild_exp = 0
                    for i in range(userinfo["servers"][str(guild.id)]["level"]):
                        guild_exp += _required_exp(i)
                    guild_exp += userinfo["servers"][str(guild.id)]["current_exp"]
                    try:
                        users.append((userinfo["username"], guild_exp))
                    except:
                        users.append((userinfo["user_id"], guild_exp))
            except:
                pass
        board_type = "Points"
        footer_text = "Your Rank: {}         {}: {}".format(
            await _find_guild_rank(user, guild),
            board_type,
            await _find_guild_exp(user, guild),
        )
        icon_url = guild.icon_url
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

    for single_user in sorted_list[start_index:end_index]:
        if rank - 1 < len(special_labels):
            label = special_labels[rank - 1]
        else:
            label = default_label

        msg += u"`{:<2}{:<2}{:<2}   # {:<22}".format(
            rank, label, u"➤", _truncate_text(single_user[0], 20)
        )
        msg += u"{:>5}{:<2}{:<2}{:<5}`\n".format(
            " ", " ", " ", "Total {}: ".format(board_type) + str(single_user[1])
        )
        rank += 1
    msg += "----------------------------------------------------\n"
    msg += "`{}`".format(footer_text)

    em = discord.Embed(description="", colour=user.colour)
    em.set_author(name=title, icon_url=icon_url)
    em.description = msg

    await ctx.send(embed=em)
