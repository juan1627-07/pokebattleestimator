# ============================================
# Tier Engine
# ============================================

TIER_INFO = {

    "AG":{
        "stars":5,"color":"#be123c","description":"Anything Goes: the least restricted singles tier."
    },

    "Uber":{

        "stars":5,

        "color":"#8e44ad",

        "description":"Restricted to the strongest Pokémon."

    },

    "OU":{

        "stars":5,

        "color":"#27ae60",

        "description":"Excellent in standard competitive battles."

    },

    "UUBL":{
        "stars":4,"color":"#16a34a","description":"Banned from UU and usable in OU."
    },

    "UU":{

        "stars":4,

        "color":"#3498db",

        "description":"Strong and reliable competitive choice."

    },

    "RUBL":{
        "stars":4,"color":"#0284c7","description":"Banned from RU and usable in UU."
    },

    "RU":{

        "stars":3,

        "color":"#f39c12",

        "description":"Good Pokémon with niche strengths."

    },

    "NUBL":{
        "stars":3,"color":"#d97706","description":"Banned from NU and usable in RU."
    },

    "NU":{

        "stars":2,

        "color":"#d35400",

        "description":"Limited competitive effectiveness."

    },

    "PUBL":{
        "stars":2,"color":"#ea580c","description":"Banned from PU and usable in NU."
    },

    "PU":{

        "stars":1,

        "color":"#7f8c8d",

        "description":"Rarely used competitively."

    },

    "ZU":{
        "stars":1,"color":"#64748b","description":"ZeroUsed, below PU in the usage hierarchy."
    },

    "NFE":{
        "stars":1,"color":"#78716c","description":"Not Fully Evolved."
    },

    "LC":{
        "stars":1,"color":"#0d9488","description":"Little Cup eligible."
    },

    "Unknown":{

        "stars":3,

        "color":"#95a5a6",

        "description":"Competitive tier not yet available."

    }

}

def get_tier_analysis(tier):

    return TIER_INFO.get(

        tier,

        TIER_INFO["Unknown"]

    )
