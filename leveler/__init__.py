from .leveler import Leveler
from .profile import profile
from .rank import rank
from .top import top
from .rep import rep
from .lvlinfo import lvlinfo
from .lvlset import lvlset
from .lvladmin import lvladmin
from .badge import badge
from .role import role
from .backgrounds import disp_backgrounds
from .rank import rank
from .on_message import _handle_on_message


def setup(bot):
    Leveler.profile = profile
    Leveler.rank = rank
    Leveler.top = top
    Leveler.rep = rep
    Leveler.lvlinfo = lvlinfo
    Leveler.lvlset = lvlset
    Leveler.lvladmin = lvladmin
    Leveler.badge = badge
    Leveler.role = role
    Leveler.disp_backgrounds = disp_backgrounds
    Leveler.rank = rank
    Leveler._handle_on_message = _handle_on_message

    n = Leveler(bot)
    bot.add_listener(n._handle_on_message, "on_message")
    bot.add_cog(n)
