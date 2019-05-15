from redbot.core import commands
import discord
from ..leveler import db
from redbot.core import checks


@commands.group(pass_context=True)
async def role(self, ctx):
    """Admin Background Configuration"""
    if ctx.invoked_subcommand is None:
        return


@checks.mod_or_permissions(manage_roles=True)
@role.command(name="link", no_pm=True, pass_context=True)
async def linkrole(self, ctx, role_name: str, level: int, remove_role=None):
    """Associate a role with a level. Removes previous role if given."""
    guild = ctx.message.guild

    role_obj = discord.utils.find(lambda r: r.name == role_name, guild.roles)
    remove_role_obj = discord.utils.find(lambda r: r.name == remove_role, guild.roles)
    if role_obj == None or (remove_role != None and remove_role_obj == None):
        if remove_role == None:
            await ctx.send("**Please make sure the `{}` role exists!**".format(role_name))
        else:
            await ctx.send(
                "**Please make sure the `{}` and/or `{}` roles exist!**".format(
                    role_name, remove_role
                )
            )
    else:
        guild_roles = db.roles.find_one({"guild_id": str(guild.id)})
        if not guild_roles:
            new_guild = {
                "guild_id": str(guild.id),
                "roles": {role_name: {"level": str(level), "remove_role": remove_role}},
            }
            db.roles.insert_one(new_guild)
        else:
            if role_name not in guild_roles["roles"]:
                guild_roles["roles"][role_name] = {}

            guild_roles["roles"][role_name]["level"] = str(level)
            guild_roles["roles"][role_name]["remove_role"] = remove_role
            db.roles.update_one(
                {"guild_id": str(guild.id)}, {"$set": {"roles": guild_roles["roles"]}}
            )

        if remove_role == None:
            await ctx.send(
                "**The `{}` role has been linked to level `{}`**".format(role_name, level)
            )
        else:
            await ctx.send(
                "**The `{}` role has been linked to level `{}`. Will also remove `{}` role.**".format(
                    role_name, level, remove_role
                )
            )


@checks.mod_or_permissions(manage_roles=True)
@role.command(name="unlink", no_pm=True, pass_context=True)
async def unlinkrole(self, ctx, role_name: str):
    """Delete a role/level association."""
    guild = ctx.message.guild

    guild_roles = db.roles.find_one({"guild_id": str(guild.id)})
    roles = guild_roles["roles"]

    if role_name in roles:
        await ctx.send(
            "**Role/Level association `{}`/`{}` removed.**".format(
                role_name, roles[role_name]["level"]
            )
        )
        del roles[role_name]
        db.roles.update_one({"guild_id": str(guild.id)}, {"$set": {"roles": roles}})
    else:
        await ctx.send("**The `{}` role is not linked to any levels!**".format(role_name))


@checks.mod_or_permissions(manage_roles=True)
@role.command(name="listlinks", no_pm=True, pass_context=True)
async def listrole(self, ctx):
    """List level/role associations."""
    guild = ctx.message.guild
    user = ctx.message.author

    guild_roles = db.roles.find_one({"guild_id": str(guild.id)})

    em = discord.Embed(description="", colour=user.colour)
    em.set_author(
        name="Current Role - Level Links for {}".format(guild.name), icon_url=guild.icon_url
    )

    if guild_roles == None or "roles" not in guild_roles or guild_roles["roles"] == {}:
        msg = "None"
    else:
        roles = guild_roles["roles"]
        msg = "**Role** → Level\n"
        for role in roles:
            if roles[role]["remove_role"] != None:
                msg += "**• {} →** {} (Removes: {})\n".format(
                    role, roles[role]["level"], roles[role]["remove_role"]
                )
            else:
                msg += "**• {} →** {}\n".format(role, roles[role]["level"])

    em.description = msg
    await ctx.send(embed=em)
