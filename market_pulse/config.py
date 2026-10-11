"""Static configuration: feeds, quotes, ticker/sector keyword maps."""

FEEDS = {
    "CNBC Top News": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "CNBC Markets": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
    "CNBC Economy": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147",
    "MarketWatch Top": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "MarketWatch Pulse": "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
    "Yahoo Finance": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=SPY,QQQ,AAPL,NVDA,TSLA,MSFT,AMZN&region=US&lang=en-US",
    "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Reuters (via Google News)": "https://news.google.com/rss/search?q=site:reuters.com+markets&hl=en-US&gl=US&ceid=US:en",
    "AP Business (via Google News)": "https://news.google.com/rss/search?q=site:apnews.com+business&hl=en-US&gl=US&ceid=US:en",
    "Shipping & Postage (via Google News)": "https://news.google.com/rss/search?q=(USPS+OR+UPS+OR+FedEx)+(rates+OR+surcharge+OR+postage+OR+shipping)+when:2d&hl=en-US&gl=US&ceid=US:en",
    "Retail & E-commerce (via Google News)": "https://news.google.com/rss/search?q=(retail+sales+OR+e-commerce+OR+retailers)+stocks+when:2d&hl=en-US&gl=US&ceid=US:en",
    "Fed Press Releases": "https://www.federalreserve.gov/feeds/press_all.xml",
    "Nasdaq Markets": "https://www.nasdaq.com/feed/rssoutbound?category=Markets",
}

# symbol -> (label, group)
QUOTES = {
    "ES=F": ("S&P 500 Fut", "Futures"), "NQ=F": ("Nasdaq 100 Fut", "Futures"),
    "YM=F": ("Dow Fut", "Futures"), "RTY=F": ("Russell 2000 Fut", "Futures"),
    "SPY": ("SPY", "Index ETFs"), "QQQ": ("QQQ", "Index ETFs"),
    "DIA": ("DIA", "Index ETFs"), "IWM": ("IWM", "Index ETFs"),
    "^VIX": ("VIX", "Volatility"),
    "CL=F": ("WTI Crude", "Macro"), "GC=F": ("Gold", "Macro"),
    "DX-Y.NYB": ("Dollar Index", "Macro"), "^TNX": ("10Y Yield", "Macro"),
    "BTC-USD": ("Bitcoin", "Macro"),
}

SECTOR_ETFS = {
    "XLK": "Technology", "XLF": "Financials", "XLE": "Energy", "XLV": "Health Care",
    "XLY": "Cons. Discretionary", "XLP": "Cons. Staples", "XLI": "Industrials",
    "XLB": "Materials", "XLU": "Utilities", "XLRE": "Real Estate", "XLC": "Communication",
    "SMH": "Semiconductors",
}

# keyword (lowercase) -> tickers
TICKER_KEYWORDS = {
    "apple": ["AAPL"], "iphone": ["AAPL"], "microsoft": ["MSFT"], "nvidia": ["NVDA"],
    "amazon": ["AMZN"], "alphabet": ["GOOGL"], "google": ["GOOGL"], "meta": ["META"],
    "facebook": ["META"], "tesla": ["TSLA"], "musk": ["TSLA"], "netflix": ["NFLX"],
    "amd": ["AMD"], "intel": ["INTC"], "broadcom": ["AVGO"], "tsmc": ["TSM"],
    "micron": ["MU"], "qualcomm": ["QCOM"], "oracle": ["ORCL"], "salesforce": ["CRM"],
    "palantir": ["PLTR"], "jpmorgan": ["JPM"], "goldman": ["GS"], "morgan stanley": ["MS"],
    "bank of america": ["BAC"], "wells fargo": ["WFC"], "citigroup": ["C"], "citi ": ["C"],
    "berkshire": ["BRK-B"], "exxon": ["XOM"], "chevron": ["CVX"], "boeing": ["BA"],
    "walmart": ["WMT"], "costco": ["COST"], "target": ["TGT"], "disney": ["DIS"],
    "pfizer": ["PFE"], "eli lilly": ["LLY"], "lilly": ["LLY"], "novo nordisk": ["NVO"],
    "unitedhealth": ["UNH"], "coinbase": ["COIN"], "bitcoin": ["BTC-USD", "COIN"],
    "crypto": ["BTC-USD", "COIN"], "openai": ["MSFT"], "uber": ["UBER"], "nike": ["NKE"],
    "starbucks": ["SBUX"], "mcdonald": ["MCD"], "ford": ["F"], "general motors": ["GM"],
    "caterpillar": ["CAT"], "visa": ["V"], "mastercard": ["MA"], "paypal": ["PYPL"],
    "s&p 500": ["SPY"], "s&p": ["SPY"], "nasdaq": ["QQQ"], "dow": ["DIA"],
    "russell": ["IWM"], "small cap": ["IWM"], "small-cap": ["IWM"],
    "oil": ["CL=F", "XLE"], "crude": ["CL=F", "XLE"], "opec": ["CL=F", "XLE"],
    "gold": ["GC=F"], "treasury": ["^TNX"], "yields": ["^TNX"], "bond": ["^TNX"],
    "dollar index": ["DX-Y.NYB"], "u.s. dollar": ["DX-Y.NYB"], "greenback": ["DX-Y.NYB"], "fed": ["^TNX", "SPY"], "powell": ["^TNX", "SPY"],
    "volatility": ["^VIX"],
    "ups": ["UPS"], "united parcel": ["UPS"], "fedex": ["FDX"], "shopify": ["SHOP"], "etsy": ["ETSY"],
    "ebay": ["EBAY"], "wayfair": ["W"], "chewy": ["CHWY"], "temu": ["PDD"], "pdd holdings": ["PDD"],
    "alibaba": ["BABA"], "mercadolibre": ["MELI"], "home depot": ["HD"], "lowe's": ["LOW"], "best buy": ["BBY"],
    "macy's": ["M"], "gap inc": ["GAP"], "lululemon": ["LULU"], "dollar general": ["DG"], "dollar tree": ["DLTR"],
    "kroger": ["KR"], "booking holdings": ["BKNG"], "airbnb": ["ABNB"], "doordash": ["DASH"],
}

SECTOR_KEYWORDS = {
    "Technology": ["tech", "software", "ai ", "artificial intelligence", "cloud", "apple", "microsoft", "chip", "semiconductor", "nvidia"],
    "Semiconductors": ["chip", "semiconductor", "nvidia", "amd", "tsmc", "intel", "micron", "broadcom"],
    "Financials": ["bank", "lender", "jpmorgan", "goldman", "credit", "loan", "insurer", "fintech"],
    "Energy": ["oil", "crude", "opec", "gas", "energy", "exxon", "chevron", "refin"],
    "Health Care": ["drug", "pharma", "fda", "biotech", "health", "vaccine", "lilly", "pfizer"],
    "Cons. Discretionary": ["retail", "consumer", "tesla", "amazon", "automaker", "travel", "restaurant", "housing"],
    "Cons. Staples": ["grocery", "walmart", "costco", "food", "beverage", "staples"],
    "Industrials": ["boeing", "airline", "industrial", "defense", "manufactur", "rail", "freight", "tariff"],
    "Materials": ["copper", "steel", "mining", "gold", "lithium", "chemical"],
    "Utilities": ["utility", "utilities", "power grid", "electricity"],
    "Real Estate": ["real estate", "reit", "mortgage", "home sales", "housing"],
    "E-commerce": ["e-commerce", "ecommerce", "online retail", "online sales", "shopify", "etsy", "ebay", "temu", "shein",
                   "amazon", "marketplace", "prime day", "cyber monday", "online shopping", "direct-to-consumer"],
    "Shipping & Logistics": ["usps", "postal service", "postage", "stamp price", "ups", "fedex", "parcel", "shipping rate",
                             "shipping cost", "shipping surcharge", "freight", "logistics", "de minimis", "delivery fee",
                             "peak surcharge", "dhl", "container ship", "supply chain"],
    "Communication": ["meta", "google", "alphabet", "netflix", "disney", "media", "telecom", "streaming"],
}

HIGH_IMPACT = {
    "fed": 3, "fomc": 4, "powell": 3, "rate cut": 4, "rate hike": 4, "interest rate": 3,
    "inflation": 3, "cpi": 4, "ppi": 3, "jobs report": 4, "payrolls": 4, "unemployment": 3,
    "gdp": 3, "recession": 3, "tariff": 3, "earnings": 2, "guidance": 2, "downgrade": 2,
    "upgrade": 2, "bankruptcy": 3, "merger": 2, "acquire": 2, "acquisition": 2, "deal": 1,
    "lawsuit": 1, "sec ": 2, "plunge": 2, "soar": 2, "surge": 2, "tumble": 2, "record": 1,
    "crash": 3, "sell-off": 2, "selloff": 2, "rally": 1, "war": 2, "sanction": 2,
    "opec": 2, "shutdown": 3, "default": 3, "treasury": 1, "yields": 2, "breaking": 2,
}

THEME_RULES = [
    ("Fed & Rates", ["fed", "fomc", "powell", "rate", "yield", "treasury", "bond"]),
    ("Inflation & Macro Data", ["inflation", "cpi", "ppi", "gdp", "jobs", "payroll", "unemployment", "retail sales", "economy"]),
    ("Earnings & Guidance", ["earnings", "revenue", "profit", "guidance", "quarter", "results", "outlook"]),
    ("AI & Semiconductors", ["ai ", "artificial intelligence", "chip", "semiconductor", "nvidia", "openai", "data center"]),
    ("Energy & Commodities", ["oil", "crude", "opec", "gas", "gold", "copper", "commodit"]),
    ("Trade, Tariffs & Geopolitics", ["tariff", "trade", "china", "sanction", "war", "ukraine", "russia", "israel", "iran", "election", "white house", "trump"]),
    ("Crypto", ["bitcoin", "crypto", "ether", "coinbase", "stablecoin"]),
    ("M&A & Deals", ["merger", "acquire", "acquisition", "deal", "buyout", "ipo"]),
    ("Banks & Credit", ["bank", "credit", "lender", "loan", "debt"]),
    ("Shipping, Postage & Logistics", ["usps", "postal", "postage", "ups ", "fedex", "parcel", "shipping rate",
                                       "shipping cost", "surcharge", "freight", "de minimis", "logistics"]),
    ("E-commerce", ["e-commerce", "ecommerce", "online retail", "online sales", "shopify", "temu", "shein", "etsy", "ebay"]),
    ("Consumer & Retail", ["consumer", "retail", "shopper", "spending", "walmart", "amazon"]),
]

CONSUMER_LENS = {"Cons. Discretionary", "E-commerce", "Shipping & Logistics"}
