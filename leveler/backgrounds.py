from redbot.core import commands
from redbot.core.utils.chat_formatting import pagify
import discord


@commands.command(name="backgrounds", pass_context=True, no_pm=True)
async def disp_backgrounds(self, ctx, type: str = None):
    """Gives a list of backgrounds. [p]backgrounds [profile|rank|levelup]"""
    guild = ctx.message.guild
    user = ctx.message.author
    max_all = 18

    if str(guild.id) in self.settings["disabled_guilds"]:
        await ctx.send("**Leveler commands for this guild are disabled!**")
        return

    em = discord.Embed(description="", colour=user.colour)
    if not type:
        em.set_author(
            name="All Backgrounds for {}".format(self.bot.user.name),
            icon_url=self.bot.user.avatar_url,
        )

        for category in self.backgrounds.keys():
            bg_url = []
            for background_name in sorted(self.backgrounds[category].keys()):
                bg_url.append(
                    "[{}]({})".format(
                        background_name, self.backgrounds[category][background_name]
                    )
                )
            max_bg = min(max_all, len(bg_url))
            bgs = ", ".join(bg_url[0:max_bg])
            if len(bg_url) >= max_all:
                bgs += "..."
            em.add_field(name=category.upper(), value=bgs, inline=False)
        await ctx.send(embed=em)
    else:
        if type.lower() == "profile":
            em.set_author(
                name="Profile Backgrounds for {}".format(self.bot.user.name),
                icon_url=self.bot.user.avatar_url,
            )
            bg_key = "profile"
        elif type.lower() == "rank":
            em.set_author(
                name="Rank Backgrounds for {}".format(self.bot.user.name),
                icon_url=self.bot.user.avatar_url,
            )
            bg_key = "rank"
        elif type.lower() == "levelup":
            em.set_author(
                name="Level Up Backgrounds for {}".format(self.bot.user.name),
                icon_url=self.bot.user.avatar_url,
            )
            bg_key = "levelup"
        else:
            bg_key = None

        if bg_key:
            bg_url = []
            for background_name in sorted(self.backgrounds[bg_key].keys()):
                bg_url.append(
                    "[{}]({})".format(
                        background_name, self.backgrounds[bg_key][background_name]
                    )
                )
            bgs = ", ".join(bg_url)

            total_pages = 0
            for _ in pagify(bgs, [" "]):
                total_pages += 1

            counter = 1
            for page in pagify(bgs, [" "]):
                em.description = page
                em.set_footer(text="Page {} of {}".format(counter, total_pages))
                await ctx.send(embed=em)
                counter += 1
        else:
            await ctx.send("**Invalid Background Type. (profile, rank, levelup)**")
