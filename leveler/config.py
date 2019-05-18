from redbot.core import Config


db = Config.get_conf(None, 228174739, force_registration=True, cog_name="leveler")


backgrounds = {
    "levelup": {
        "default": "http://i.imgur.com/eEFfKqa.jpg"
    },
    "profile": {
        "alice": "http://i.imgur.com/MUSuMao.png",
        "bluestairs": "http://i.imgur.com/EjuvxjT.png",
        "coastline": "http://i.imgur.com/XzUtY47.jpg",
        "default": "http://i.imgur.com/8T1FUP5.jpg",
        "greenery": "http://i.imgur.com/70ZH6LX.png",
        "iceberg": "http://i.imgur.com/8KowiMh.png",
        "lamp": "http://i.imgur.com/0nQSmKX.jpg",
        "miraiglasses": "http://i.imgur.com/2Ak5VG3.png",
        "miraikuriyama": "http://i.imgur.com/jQ4s4jj.png",
        "mountaindawn": "http://i.imgur.com/kJ1yYY6.jpg",
        "redblack": "http://i.imgur.com/74J2zZn.jpg",
        "waterlilies": "http://i.imgur.com/qwdcJjI.jpg"
    },
    "rank": {
        "abstract": "http://i.imgur.com/70ZH6LX.png",
        "aurora": "http://i.imgur.com/gVSbmYj.jpg",
        "city": "http://i.imgur.com/yr2cUM9.jpg",
        "default": "http://i.imgur.com/SorwIrc.jpg",
        "mountain": "http://i.imgur.com/qYqEUYp.jpg",
        "nebula": "http://i.imgur.com/V5zSCmO.jpg"
    }
}

badges = {}

settings = {
    "badge_type": "circles",
    "bg_price": 0,
    "chat_cooldown": 120,
    "mention": False,
    "rep_cooldown": 43200,
}

global_settings = {
    "backgrounds": backgrounds,
    "badges": badges,
    **settings,
}

default_user = {
    "total_exp": 0,
    "profile_background": backgrounds["profile"]["default"],
    "rank_background": backgrounds["rank"]["default"],
    "levelup_background": backgrounds["levelup"]["default"],
    "title": "",
    "info": "I am a mysterious person.",
    "rep": 0,
    "rep_block": 0,
    "badges": {},
    "active_badges": {},
    "rep_color": (92, 130, 203, 230),
    "badge_col_color": (128, 151, 165, 230),
    "profile_info_color": (30, 30, 30, 220),
    "profile_exp_color": (255, 255, 255, 230),
    "levelup_info_color": (30, 30, 30, 150),
    "rank_info_color": (140, 140, 140, 230)
}

default_role = {
    "level": None,
    "remove_role": None
}

default_member = {
    "level": 0,
    "current_exp": 0,
    "chat_block": 0
}

default_guild = {
    "badges": {},
    "badge_links": {},
    "msg_credits": 0,
    "disabled": False,
    "private_lvl_msg": False,
    "lvl_msg": False,
    "lvl_msg_lock": None
}

db.register_global(**global_settings)
db.register_user(**default_user)
db.register_member(**default_member)
db.register_role(**default_role)
db.register_guild(**default_guild)
