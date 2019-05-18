from .leveler import Leveler
from leveler.comands.profile import profile
from leveler.comands.top import top
from leveler.comands.rep import rep
from leveler.comands.lvlinfo import lvlinfo
from leveler.comands.lvlset import lvlset
from leveler.comands.lvladmin import lvladmin
from leveler.comands.badge import badge
from leveler.comands.role import role
from leveler.comands.backgrounds import disp_backgrounds
from leveler.comands.rank import rank
from .on_message import _handle_on_message


def setup(bot):
    n = Leveler(bot)

    n.disp_backgrounds = disp_backgrounds
    n.rep = rep
    n.role = role
    n.rank = rank
    n.top = top
    n.profile = profile
    n.lvlset = lvlset
    n.lvlinfo = lvlinfo
    n.badge = badge
    n.lvladmin = lvladmin

    async def on_message(message):
        return await _handle_on_message(bot, message)
    n._handle_on_message = on_message

    bot.add_listener(on_message, "on_message")
    bot.add_cog(n)
