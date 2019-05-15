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
    Leveler.profile = profile
    Leveler.rank = rank
    Leveler.lvlinfo = lvlinfo
    Leveler.lvlset = lvlset
    Leveler.lvladmin = lvladmin
    Leveler.badge = badge
    Leveler._handle_on_message = _handle_on_message

    n = Leveler(bot)

    n.disp_backgrounds = disp_backgrounds
    n.rep = rep
    n.role = role
    n.rank = rank
    n.top = top

    bot.add_listener(n._handle_on_message, "on_message")
    bot.add_cog(n)
