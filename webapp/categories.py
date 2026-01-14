"""Subreddit to category mapping."""

# Map subreddits to categories
CATEGORIES = {
    "Self-Hosting & Homelab": [
        "selfhosted", "homelab", "truenas", "PleX", "sonarr", "radarr",
        "DataHoarder", "Kometa", "LunaSeaApp", "HomeServer", "HomeDataCenter",
        "minilab", "Cloudbox", "homebox", "supermicro",
    ],
    "AI & LLMs": [
        "ClaudeAI", "ChatGPTCoding", "RooCode", "LocalLLaMA", "ChatGPT",
        "OpenAI", "ollama", "modelcontextprotocol", "ChatGPTPromptGenius",
        "aipromptprogramming", "Codeium", "cursor",
    ],
    "Home Automation": [
        "homeassistant", "smarthome", "homebridge", "homeautomation",
        "EufyCam", "Ring", "elgato",
    ],
    "Networking & Security": [
        "opnsense", "OPNsenseFirewall", "PFSENSE", "Tailscale", "CloudFlare",
        "nextdns", "networking", "cybersecurity", "yubikey", "Bitwarden",
        "netsec", "HomeNetworking", "GlInet", "RuckusWiFi", "Ubiquiti",
        "tmobileisp", "VirginMedia", "1Password", "PrivacyGuides", "privacytoolsIO",
    ],
    "Microsoft & Sysadmin": [
        "Intune", "AZURE", "PowerShell", "sysadmin", "msp", "macsysadmin",
        "Office365", "MicrosoftTeams", "devops", "kubernetes", "vmware",
        "DefenderATP", "AzureSentinel", "sharepoint", "Veeam", "MDT",
        "azuredevops", "ITProTuesday", "SysAdminBlogs", "usefulscripts",
    ],
    "Mechanical Keyboards": [
        "MechanicalKeyboards", "mechmarket", "CustomKeyboards",
        "MechanicalKeyboardsUK", "KBDfans",
    ],
    "3D Printing": [
        "prusa3d", "3Dprinting", "functionalprint", "BambuLab",
        "gridfinity", "PrintedWarhammer",
    ],
    "PC Building & Hardware": [
        "sffpc", "watercooling", "pcmasterrace", "buildapc", "hardware",
        "Monitors", "OLED_Gaming", "nvidia", "Amd", "thinkpad", "MiniPCs",
        "battlestations", "CableManagement", "Louqe", "ncasedesign",
        "Phanteks", "PCSleeving", "LGOLED", "MouseReview", "headphones",
        "UsbCHardware", "computerhelp", "pcgaming", "SteamDeck",
    ],
    "Gaming & Retro": [
        "AnalogueInc", "AnaloguePocket", "SBCGaming", "retroid", "nintendo",
        "NintendoSwitch", "SwitchPirates", "gaming", "Games", "n64",
        "Overwatch", "riskofrain", "Borderlands", "playrust", "pokemon",
        "SatisfactoryGame", "ReadyOrNotGame", "duneawakening",
    ],
    "Anime & Japanese Media": [
        "evangelion", "AnimationCels", "ghibli", "anime", "FullmetalAlchemist",
        "OnePunchMan", "mildlyevangelion", "dbz", "TheLastAirbender",
        "csmanime", "Tenkinoko",
    ],
    "Movies & TV": [
        "movies", "TrueDetective", "StarWars", "bladerunner", "FinalFantasy",
        "metalgearsolid", "ThePittTVShow", "lesmiserables", "television",
        "Documentaries", "ShieldAndroidTV", "OSMC",
    ],
    "Food & Health": [
        "ninjacreami", "CICO", "fitmeals", "Cooking", "Testosterone",
        "tressless", "HairTransplants", "EatCheapAndHealthy", "mounjarouk",
        "Asthma", "mountaindew", "HydroHomies", "LoseitApp",
    ],
    "Fashion & Sneakers": [
        "Repsneakers", "malefashionadvice", "FashionReps", "Sneakers",
        "sneakerreps", "wicked_edge", "hermanmiller", "onebag", "backpacks",
        "shoebots",
    ],
    "Apple & Mac": [
        "MacOS", "apple", "apolloapp", "apollosideloaded", "iphone",
        "appletv", "macapps", "mac", "macbookpro", "AppleWatch", "airpods",
        "CarPlay", "narwhalapp", "webos",
    ],
    "Productivity & Dev Tools": [
        "ObsidianMD", "raycastapp", "vscode", "thingsapp", "gohugo",
        "github", "git", "programming", "n8n", "productivity", "actualbudgeting",
        "ynab", "datacurator", "Papermerge",
    ],
    "Finance & Career": [
        "UKPersonalFinance", "ContractorUK", "overemployed", "HousingUK",
        "Resume", "slavelabour", "monzo", "starlingbankuk",
    ],
    "Piracy & Media": [
        "trackers", "seedboxes", "torrents", "usenet", "Piracy", "UsenetTalk",
        "OpenSignups", "uBlockOrigin", "Annas_Archive", "Softwarr", "crboxes",
    ],
    "Feel Good & Animals": [
        "Eyebleach", "aww", "Awww", "MadeMeSmile", "rarepuppers", "FunnyAnimals",
        "AnimalsBeingDerps", "AnimalsBeingBros", "HumansBeingBros", "Zoomies",
        "NatureIsFuckingLit", "BeAmazed", "oddlysatisfying", "WatchPeopleDieInside",
        "Damnthatsinteresting", "interestingasfuck", "nextfuckinglevel", "Amazing",
        "blackmagicfuckery", "UpliftingNews", "funny", "gifs",
    ],
    "UK Life": [
        "CasualUK", "AskUK", "ukpolitics", "GreatBritishMemes", "Airsoft_UK",
        "reading", "asda", "BuyFromEU",
    ],
    "Sports": [
        "LiverpoolFC", "soccer", "nba",
    ],
    "Cars": [
        "VolvoXC90", "Volvo", "teslamotors", "dashcams",
    ],
    "Other Tech": [
        "technology", "gadgets", "AirTags", "IKEA", "Traefik", "firefox",
        "youtube", "lifehacks", "FuckTAA",
    ],
}


def categorize_subreddit(subreddit: str) -> str:
    """Find the category for a subreddit."""
    for category, subs in CATEGORIES.items():
        if subreddit in subs:
            return category
    return "Uncategorized"


def get_all_categories() -> list[str]:
    """Get all category names."""
    return list(CATEGORIES.keys()) + ["Uncategorized"]
