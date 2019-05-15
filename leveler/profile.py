from redbot.core import commands
import discord
import time
import os
from .leveler import munge_path, db, bank


@commands.cooldown(1, 10, commands.BucketType.user)
@commands.command(name="profile", pass_context=True, no_pm=True)
async def profile(leveler, ctx, *, user: discord.Member = None):
    """Displays a user profile."""
    if user is None:
        user = ctx.message.author
    channel = ctx.message.channel
    guild = user.guild
    curr_time = time.time()

    # creates user if doesn't exist
    await leveler._create_user(user, guild)
    userinfo = db.users.find_one({"user_id": str(str(user.id))})

    # check if disabled
    if str(guild.id) in leveler.settings["disabled_guilds"]:
        await ctx.send("**Leveler commands for this guild are disabled!**")
        return

    # no cooldown for text only
    if "text_only" in leveler.settings and str(guild.id) in leveler.settings["text_only"]:
        em = await profile_text(leveler, user, guild, userinfo)
        await channel.send("", embed=em)
    else:
        await leveler.draw_profile(user, guild)

        await channel.send(
            "**User profile for {}**".format(leveler._is_mention(user)),
            file=discord.File(munge_path("temp/{}_profile.png".format(str(user.id)))),
        )
        db.users.update_one(
            {"user_id": str(str(user.id))}, {"$set": {"profile_block": curr_time}}, upsert=True
        )
        try:
            os.remove(munge_path("temp/{}_profile.png".format(str(user.id))))
        except:
            pass


async def profile_text(leveler, user, guild, userinfo):
    def test_empty(text):
        if text == "":
            return "None"
        else:
            return text

    em = discord.Embed(description="", colour=user.colour)
    em.add_field(name="Title:", value=test_empty(userinfo["title"]))
    em.add_field(name="Reps:", value=userinfo["rep"])
    em.add_field(name="Global Rank:", value="#{}".format(await leveler._find_global_rank(user)))
    em.add_field(
        name="guild Rank:", value="#{}".format(await leveler._find_guild_rank(user, guild))
    )
    em.add_field(
        name="guild Level:", value=format(userinfo["servers"][str(guild.id)]["level"])
    )
    em.add_field(name="Total Exp:", value=userinfo["total_exp"])
    em.add_field(name="guild Exp:", value=await leveler._find_guild_exp(user, guild))
    try:
        credits = await bank.get_balance(user)
    except:
        credits = 0
    em.add_field(name="Credits: ", value="${}".format(credits))
    em.add_field(name="Info: ", value=test_empty(userinfo["info"]))
    em.add_field(
        name="Badges: ", value=test_empty(", ".join(userinfo["badges"])).replace("_", " ")
    )
    em.set_author(name="Profile for {}".format(user.name), url=user.avatar_url)
    em.set_thumbnail(url=user.avatar_url)
    return em
