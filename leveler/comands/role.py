from typing import Optional

from redbot.core import commands, checks

from discord.utils import find
from discord import Embed

from ..config import db
from ..permissions import leveler_enabled


@commands.group(pass_context=True)
@leveler_enabled
async def role(ctx):
    """Admin Role Configuration"""
    if ctx.invoked_subcommand is None:
        return


@checks.mod_or_permissions(manage_roles=True)
@role.command(name="link", no_pm=True, pass_context=True)
async def role_link(ctx, role_name: str, level: int, remove_role: Optional[str] = None):
    """Associate a role with a level. Removes previous role if given."""
    guild = ctx.message.guild

    role_obj = find(lambda r: r.name == role_name, guild.roles)
    remove_role_obj = find(lambda r: r.name == remove_role, guild.roles)

    if role_obj is None:
        return await ctx.send("**Please make sure the `{}` role exists!**".format(role_name))
    if remove_role is not None and remove_role_obj is None:
        return await ctx.send("**Please make sure the `{}` role exists!**".format(remove_role))

    role_info = db.role(role_obj)
    await role_info.level.set(level)
    if remove_role_obj is not None:
        await role_info.remove_role.set(remove_role_obj.id)

    remove_role_msg = f"Will also remove `{remove_role}` role." if remove_role is not None else ""
    message = f"**The `{role_name}` role has been linked to level `{level}`. {remove_role_msg}**"
    await ctx.send(message)


@checks.mod_or_permissions(manage_roles=True)
@role.command(name="unlink", no_pm=True, pass_context=True)
async def role_unlink(ctx, role_name: str):
    """Delete a role/level association."""
    guild = ctx.message.guild

    role_obj = find(lambda r: r.name == role_name, guild.roles)
    if role_obj is None:
        return await ctx.send(f"**The `{role_name}` role doesn't exist!**")

    role_info = db.role(role_obj)
    role_level = await role_info.level()

    if role_level is not None:
        await ctx.send(f"**Role/Level association `{role_name}`/`{role_level}` removed.**")
        await role_info.level.set(None)
        await role_info.remove_role.set(None)
    else:
        await ctx.send(f"**The `{role_name}` role is not linked to any levels!**")


@checks.mod_or_permissions(manage_roles=True)
@role.command(name="listlinks", no_pm=True, pass_context=True)
async def role_list(ctx):
    """List level/role associations."""
    guild = ctx.message.guild
    user = ctx.message.author

    embed = Embed(description="", colour=user.colour)
    embed.set_author(
        name=f"Current Role - Level Links for {guild.name}",
        icon_url=guild.icon_url
    )

    role_text = []
    for role in guild.roles:
        role_info = db.role(role)
        role_level = await role_info.level()
        remove_role_id = await role_info.remove_role()
        if role_level is not None:
            if remove_role_id is not None:
                role_name = next(r.name for r in guild.roles if r.id == remove_role_id) or "Deleted Role"
                role_text.append(f"**• {role} →** {role_level} (Removes: {role_name})\n")
            else:
                role_text.append(f"**• {role} →** {role_level}\n")

    if not role_text:
        embed.description = "None"
    else:
        embed.description = "**Role** → Level\n" + "".join(role_text)

    await ctx.send(embed=embed)
