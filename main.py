import os
import html
import logging
from datetime import datetime

import feedparser
import requests
import yfinance as yf
import google.generativeai as genai

# Setup logger configuration for clean CLI feedback
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("USMarketAI")

# Load configuration parameters from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CONTENT_TYPE = os.getenv("CONTENT_TYPE", "video").lower()

# Configure Gemini AI client if API key is provided
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY environment variable is missing!")

INDEXES = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Dow Jones": "^DJI",
    "Russell 2000": "^RUT",
    "VIX": "^VIX",
}

MAJOR_STOCKS = {
    "NVIDIA": "NVDA",
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Amazon": "AMZN",
    "Alphabet": "GOOGL",
    "Meta": "META",
    "Tesla": "TSLA",
    "Broadcom": "AVGO",
}

def get_single_ticker_data(symbol: str) -> dict:
    """
    Fetch latest available close and previous close for a Yahoo Finance ticker.
    Returns calculated changes and percentages cleanly.
    """
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period="5d", auto_adjust=False)

        if history.empty or len(history) < 2:
            return {
                "close": None,
                "previous_close": None,
                "change": None,
                "change_percent": None,
            }

        close = float(history["Close"].iloc[-1])
        previous_close = float(history["Close"].iloc[-2])
        change = close - previous_close

        change_percent = (change / previous_close * 100) if previous_close != 0 else 0.0

        return {
            "close": round(close, 2),
            "previous_close": round(previous_close, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
        }

    except Exception as e:
        logger.error(f"Error fetching ticker '{symbol}': {e}")
        return {
            "close": None,
            "previous_close": None,
            "change": None,
            "change_percent": None,
        }

def get_market_data() -> dict:
    """Fetch major US market indices data."""
    logger.info("Fetching US market indices...")
    market_data = {}
    for name, symbol in INDEXES.items():
        logger.info(f"  -> {name} ({symbol})")
        market_data[name] = get_single_ticker_data(symbol)
    return market_data

def get_major_stocks() -> dict:
    """Fetch major US stock data."""
    logger.info("Fetching major US stock data...")
    stocks = {}
    for name, symbol in MAJOR_STOCKS.items():
        logger.info(f"  -> {name} ({symbol})")
        stocks[name] = get_single_ticker_data(symbol)
    return stocks

def format_market_data(market_data: dict, stocks: dict) -> str:
    """
    Converts raw market dictionary data into structured text format for Gemini API prompt input.
    """
    lines = ["=== US MARKET INDICES ==="]

    for name, data in market_data.items():
        if data["close"] is None:
            lines.append(f"{name}: Unavailable")
            continue
        direction = "UP" if data["change"] >= 0 else "DOWN"
        lines.append(
            f"{name}: Close={data['close']}, Change={data['change']}, "
            f"Change%={data['change_percent']}%, Direction={direction}"
        )

    lines.append("\n=== MAJOR US STOCKS ===")

    for name, data in stocks.items():
        if data["close"] is None:
            lines.append(f"{name}: Unavailable")
            continue
        direction = "UP" if data["change"] >= 0 else "DOWN"
        lines.append(
            f"{name}: Close={data['close']}, Change={data['change']}, "
            f"Change%={data['change_percent']}%, Direction={direction}"
        )

    return "\n".join(lines)

def fetch_news_headlines() -> str:
    """
    Fetch financial news headlines from curated RSS feeds.
    """
    sources = [
        "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
        "https://finance.yahoo.com/rss/",
        "https://www.investing.com/rss/news.rss",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "https://www.cnbc.com/id/19854910/device/rss/rss.html",
    ]

    headlines = []
    logger.info("Fetching US financial news RSS feeds...")

    for source in sources:
        try:
            feed = feedparser.parse(source)
            for item in feed.entries[:20]:
                title = getattr(item, "title", "").strip()
                if title and title not in headlines:
                    headlines.append(title)
        except Exception as e:
            logger.error(f"Error parsing RSS source {source}: {e}")

    logger.info(f"Collected {len(headlines)} unique news headlines.")
    return "\n".join(headlines[:100])

def generate_index():
    """
    Builds and updates posts/index.html with a US-only live clock.
    """

    os.makedirs("posts", exist_ok=True)

    # ========================================================
    # FIND REPORTS
    # ========================================================

    files = [
        f
        for f in os.listdir("posts")
        if f.endswith(".html") and f != "index.html"
    ]

    files.sort(reverse=True)

    cards = ""

    for file in files:

        date_str = file.replace(".html", "")

        try:
            date_obj = datetime.strptime(
                date_str,
                "%Y-%m-%d"
            )

            display_date = date_obj.strftime(
                "%B %d, %Y"
            )

            weekday = date_obj.strftime(
                "%A"
            )

        except Exception:
            display_date = date_str
            weekday = ""

        cards += f"""
        <article class="report-card">

            <div class="report-info">

                <a
                    href="{file}"
                    class="report-link"
                >
                    📄 US Market Report - {date_str}
                </a>

                <div class="date">
                    📅 {weekday}, {display_date}
                </div>

                <div class="market-tags">
                    S&amp;P 500 • Nasdaq • Dow Jones • US Stocks
                </div>

            </div>

        </article>
        """

    if not cards:
        cards = """
        <p class="no-reports">
            No reports available yet.
        </p>
        """

    # ========================================================
    # HTML
    # ========================================================

    html_content = f"""<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<meta
    name="theme-color"
    content="#020617"
>

<title>US Market AI - Daily Reports</title>


<style>

/* ==========================================================
   GLOBAL
========================================================== */

* {{
    box-sizing: border-box;
}}

html {{
    scroll-behavior: smooth;
}}

body {{

    margin: 0;

    min-height: 100vh;

    font-family:
        Inter,
        Arial,
        sans-serif;

    background:

        radial-gradient(
            circle at top left,
            #123b6d55,
            transparent 40%
        ),

        radial-gradient(
            circle at top right,
            #07598544,
            transparent 40%
        ),

        #020617;

    color: #e2e8f0;

    -webkit-text-size-adjust: 100%;
}}


/* ==========================================================
   CONTAINER
========================================================== */

.container {{

    width: 100%;

    max-width: 1100px;

    margin: 0 auto;

    padding:
        30px 25px 60px;
}}


/* ==========================================================
   HEADER
========================================================== */

.header {{

    text-align: center;

    padding:
        50px 25px 35px;

    margin-bottom: 25px;

    border-radius: 30px;

    background:
        linear-gradient(
            135deg,
            rgba(15,38,70,0.75),
            rgba(8,47,73,0.55)
        );

    border:
        1px solid
        rgba(56,189,248,0.18);

    box-shadow:
        0 25px 70px
        rgba(0,0,0,0.35);
}}


/* ==========================================================
   BADGE
========================================================== */

.badge {{

    display: inline-flex;

    align-items: center;

    justify-content: center;

    gap: 7px;

    padding:
        10px 20px;

    border-radius: 999px;

    color: #38bdf8;

    background:
        rgba(14,165,233,0.08);

    border:
        1px solid
        rgba(56,189,248,0.25);

    font-size: 14px;
}}


/* ==========================================================
   TITLE
========================================================== */

h1 {{

    margin:
        25px 0 12px;

    font-size:
        clamp(42px, 7vw, 72px);

    line-height: 1.05;

    font-weight: 800;

    background:
        linear-gradient(
            90deg,
            #22d3ee,
            #22c55e,
            #a3e635
        );

    -webkit-background-clip: text;

    -webkit-text-fill-color: transparent;
}}


/* ==========================================================
   SUBTITLE
========================================================== */

.subtitle {{

    color: #94a3b8;

    font-size:
        clamp(16px, 2vw, 21px);

    line-height: 1.5;
}}


/* ==========================================================
   US CLOCK
========================================================== */

.clock-panel {{

    width: 100%;

    margin-top: 35px;

    border-radius: 25px;

    overflow: hidden;

    border:
        1px solid
        rgba(14,165,233,0.5);

    background:
        rgba(2,6,23,0.65);

    box-shadow:
        0 15px 40px
        rgba(0,0,0,0.25);

    text-align: left;
}}


.clock-box {{

    width: 100%;

    padding: 30px;
}}


/* ==========================================================
   US CLOCK TITLE
========================================================== */

.clock-title {{

    display: flex;

    align-items: center;

    gap: 9px;

    font-size: 18px;

    font-weight: 800;

    margin-bottom: 15px;

    letter-spacing: 0.02em;
}}


.us-title {{

    color: #22c55e;
}}


/* LIVE DOT */

.live-dot {{

    width: 11px;

    height: 11px;

    border-radius: 50%;

    background: #22c55e;

    box-shadow:
        0 0 12px
        rgba(34,197,94,0.9);

    flex-shrink: 0;
}}


/* FLAG */

.flag {{

    display: inline-flex;

    align-items: center;

    justify-content: center;

    font-size: 24px;

    line-height: 1;

    flex-shrink: 0;
}}


/* ==========================================================
   CLOCK TIME
========================================================== */

.clock-time {{

    font-size:
        clamp(34px, 5vw, 58px);

    font-weight: 800;

    color: #f8fafc;

    line-height: 1.1;

    margin:
        10px 0 12px;
}}


/* ==========================================================
   CLOCK DATE
========================================================== */

.clock-date {{

    color: #94a3b8;

    font-size:
        clamp(14px, 2vw, 17px);

    line-height: 1.5;

    margin-top: 10px;
}}


/* ==========================================================
   CLOCK LOCATION
========================================================== */

.clock-zone {{

    color: #64748b;

    font-size: 14px;

    margin-top: 9px;

    line-height: 1.5;
}}


/* ==========================================================
   ARCHIVE
========================================================== */

.section-label {{

    color: #38bdf8;

    font-size: 13px;

    font-weight: 800;

    letter-spacing: 0.15em;

    margin:
        35px 0 8px;
}}


.section-title {{

    font-size:
        clamp(30px, 5vw, 42px);

    line-height: 1.2;

    margin:
        0 0 20px;

    color: #f8fafc;
}}


/* ==========================================================
   REPORT CARD
========================================================== */

.report-card {{

    width: 100%;

    margin-bottom: 16px;

    padding: 24px;

    border-radius: 22px;

    background:
        rgba(15,23,42,0.82);

    border:
        1px solid
        rgba(56,189,248,0.15);

    transition:
        transform 0.2s ease,
        border-color 0.2s ease,
        background 0.2s ease;
}}


.report-card:hover {{

    transform:
        translateY(-2px);

    border-color:
        rgba(56,189,248,0.35);

    background:
        rgba(15,23,42,0.95);
}}


/* ==========================================================
   REPORT INFO
========================================================== */

.report-info {{

    width: 100%;

    min-width: 0;
}}


/* ==========================================================
   REPORT LINK
========================================================== */

.report-link {{

    display: block;

    color: #38bdf8;

    text-decoration: none;

    font-size:
        clamp(18px, 3vw, 25px);

    font-weight: 750;

    line-height: 1.35;

    overflow-wrap: anywhere;
}}


.report-link:hover {{

    color: #67e8f9;
}}


/* ==========================================================
   DATE
========================================================== */

.date {{

    margin-top: 9px;

    color: #94a3b8;

    font-size: 14px;

    line-height: 1.5;
}}


/* ==========================================================
   MARKET TAGS
========================================================== */

.market-tags {{

    margin-top: 10px;

    color: #64748b;

    font-size: 13px;

    line-height: 1.5;
}}


/* ==========================================================
   NO REPORTS
========================================================== */

.no-reports {{

    color: #64748b;

    text-align: center;

    padding: 30px;
}}


/* ==========================================================
   MOBILE
========================================================== */

@media (max-width: 700px) {{

    .container {{

        padding:
            15px 12px 40px;
    }}


    .header {{

        padding:
            35px 15px 22px;

        margin-bottom: 20px;

        border-radius: 22px;
    }}


    .badge {{

        max-width: 100%;

        padding:
            8px 13px;

        font-size: 11px;

        line-height: 1.4;
    }}


    h1 {{

        margin-top: 22px;

        font-size: 42px;

        line-height: 1.05;
    }}


    .subtitle {{

        font-size: 15px;

        line-height: 1.45;
    }}


    /* CLOCK */

    .clock-panel {{

        margin-top: 28px;

        border-radius: 20px;
    }}


    .clock-box {{

        padding:
            24px 18px;
    }}


    .clock-title {{

        font-size: 17px;

        gap: 7px;
    }}


    .live-dot {{

        width: 9px;

        height: 9px;
    }}


    .flag {{

        font-size: 21px;
    }}


    .clock-time {{

        font-size: 34px;

        white-space: nowrap;
    }}


    .clock-date {{

        font-size: 14px;

        line-height: 1.45;
    }}


    .clock-zone {{

        font-size: 13px;
    }}


    /* ARCHIVE */

    .section-label {{

        margin-top: 30px;

        font-size: 12px;
    }}


    .section-title {{

        font-size: 32px;

        line-height: 1.15;
    }}


    /* REPORT */

    .report-card {{

        padding:
            19px 18px;

        border-radius: 18px;
    }}


    .report-link {{

        font-size: 18px;

        line-height: 1.35;
    }}


    .date {{

        font-size: 13px;
    }}


    .market-tags {{

        font-size: 12px;
    }}

}}


/* ==========================================================
   SMALL PHONES
========================================================== */

@media (max-width: 380px) {{

    .container {{

        padding-left: 10px;

        padding-right: 10px;
    }}


    h1 {{

        font-size: 36px;
    }}


    .clock-box {{

        padding:
            22px 15px;
    }}


    .clock-time {{

        font-size: 29px;
    }}

}}


/* ==========================================================
   REDUCED MOTION
========================================================== */

@media (prefers-reduced-motion: reduce) {{

    html {{
        scroll-behavior: auto;
    }}

    .report-card {{
        transition: none;
    }}

}}

</style>

</head>


<body>


<div class="container">


    <!-- =====================================================
         HEADER
    ====================================================== -->

    <header class="header">


        <div class="badge">

            🇺🇸 AI-Powered US Market Intelligence

        </div>


        <h1>

            US Market AI

        </h1>


        <div class="subtitle">

            Daily S&amp;P 500, Nasdaq &amp; Dow Jones
            Market Reports

        </div>


        <!-- =================================================
             US TIME ONLY
        ================================================== -->

        <div class="clock-panel">

            <div class="clock-box">

                <div class="clock-title us-title">

                    <span class="live-dot"></span>

                    <span class="flag">🇺🇸</span>

                    <span>US MARKET TIME</span>

                </div>


                <div
                    id="us-time"
                    class="clock-time"
                >
                    --:--:--
                </div>


                <div
                    id="us-date"
                    class="clock-date"
                >
                    Loading...
                </div>


                <div class="clock-zone">

                    New York • Eastern Time

                </div>

            </div>

        </div>


    </header>


    <!-- =====================================================
         ARCHIVE
    ====================================================== -->

    <div class="section-label">

        ARCHIVE

    </div>


    <h2 class="section-title">

        Daily US Market Reports

    </h2>


    {cards}


</div>


<!-- ==========================================================
     US LIVE CLOCK JAVASCRIPT
=========================================================== -->

<script>

function updateUSClock() {{

    const now = new Date();


    const usTime =
        new Intl.DateTimeFormat(
            "en-US",
            {{

                timeZone:
                    "America/New_York",

                hour:
                    "2-digit",

                minute:
                    "2-digit",

                second:
                    "2-digit",

                hour12:
                    true

            }}
        );


    const usDate =
        new Intl.DateTimeFormat(
            "en-US",
            {{

                timeZone:
                    "America/New_York",

                weekday:
                    "long",

                month:
                    "long",

                day:
                    "numeric",

                year:
                    "numeric"

            }}
        );


    const timeElement =
        document.getElementById(
            "us-time"
        );


    const dateElement =
        document.getElementById(
            "us-date"
        );


    if (timeElement) {{

        timeElement.textContent =
            usTime.format(now);

    }}


    if (dateElement) {{

        dateElement.textContent =
            usDate.format(now);

    }}

}}


updateUSClock();


setInterval(
    updateUSClock,
    1000
);

</script>


</body>

</html>
"""


    # ========================================================
    # SAVE
    # ========================================================

    with open(
        "posts/index.html",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(html_content)


    logger.info(
        "Updated posts/index.html successfully."
    )

def save_post(title: str, content: str):
    """
    Generates a mobile-friendly standalone HTML post page for the generated report.
    """
    os.makedirs("posts", exist_ok=True)
    filename = datetime.now().strftime("%Y-%m-%d") + ".html"
    filepath = os.path.join("posts", filename)

    safe_title = html.escape(title)
    safe_content = html.escape(content)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{safe_title}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{
    --bg: #020617;
    --card: #0f172a;
    --border: #1e293b;
    --text: #e2e8f0;
    --muted: #94a3b8;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Inter', sans-serif;
    background: radial-gradient(circle at top left, #1e3a8a33, transparent 40%),
                radial-gradient(circle at top right, #06b6d433, transparent 40%),
                var(--bg);
    color: var(--text);
    min-height: 100vh;
}}
.container {{ max-width: 1200px; margin: auto; padding: 30px; }}
.header {{
    text-align: center;
    padding: 40px;
    border-radius: 24px;
    margin-bottom: 25px;
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.08);
}}
.badge {{
    display: inline-block;
    padding: 8px 16px;
    border-radius: 999px;
    background: #0ea5e920;
    border: 1px solid #38bdf830;
    color: #38bdf8;
    margin-bottom: 15px;
    font-size: 14px;
}}
.header h1 {{
    font-size: 48px;
    font-weight: 700;
    background: linear-gradient(90deg, #38bdf8, #22c55e, #facc15);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.2;
}}
.tagline {{ font-size: 18px; color: #38bdf8; margin-top: 10px; }}
.toolbar {{ display: flex; justify-content: flex-end; margin-bottom: 20px; }}
.copy-btn {{
    background: linear-gradient(135deg, #2563eb, #06b6d4);
    color: white;
    border: none;
    padding: 14px 24px;
    border-radius: 14px;
    cursor: pointer;
    font-weight: 600;
}}
.copy-btn:hover {{ transform: translateY(-2px); }}
.card {{
    background: rgba(15,23,42,0.85);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 24px;
    overflow: hidden;
    backdrop-filter: blur(20px);
    box-shadow: 0 25px 60px rgba(0,0,0,0.45);
}}
.card-top {{
    display: flex;
    align-items: center;
    padding: 15px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
}}
.dots {{ display: flex; gap: 8px; }}
.dot {{ width: 14px; height: 14px; border-radius: 50%; }}
.red {{ background: #ff5f57; }}
.yellow {{ background: #ffbd2e; }}
.green {{ background: #28c840; }}
.file-name {{ margin-left: 15px; color: #94a3b8; font-size: 14px; }}
pre {{
    white-space: pre-wrap;
    word-wrap: break-word;
    padding: 30px;
    line-height: 1.8;
    font-size: 16px;
    color: #e2e8f0;
    font-family: 'Inter', sans-serif;
}}
.footer {{ text-align: center; margin-top: 30px; color: #64748b; font-size: 14px; padding-bottom: 20px; }}
.toast {{
    position: fixed;
    bottom: 25px;
    right: 25px;
    background: #22c55e;
    color: white;
    padding: 12px 20px;
    border-radius: 12px;
    display: none;
}}
@media (max-width: 768px) {{
    .container {{ padding: 15px; }}
    .header {{ padding: 25px 15px; }}
    .header h1 {{ font-size: 32px; }}
    .tagline {{ font-size: 15px; }}
    .toolbar {{ justify-content: center; }}
    .copy-btn {{ width: 100%; padding: 16px; }}
    .card {{ border-radius: 16px; }}
    .file-name {{ margin-left: 10px; font-size: 12px; }}
    pre {{ padding: 20px 15px; font-size: 15px; }}
    .toast {{ left: 50%; right: auto; transform: translateX(-50%); width: 90%; text-align: center; }}
}}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <div class="badge">🚀 AI Generated US Market Report</div>
        <h1>US Market AI</h1>
        <p class="tagline">Daily US Stock Market Intelligence</p>
    </div>
    <div class="toolbar">
        <button class="copy-btn" onclick="copyScript()">📋 Copy Full Script</button>
    </div>
    <div class="card">
        <div class="card-top">
            <div class="dots">
                <span class="dot red"></span>
                <span class="dot yellow"></span>
                <span class="dot green"></span>
            </div>
            <div class="file-name">US Daily Market Analysis</div>
        </div>
        <pre id="script">{safe_content}</pre>
    </div>
    <div class="footer">
        US Market AI | Daily US Stock Market Reports | Powered by Gemini
    </div>
</div>
<div id="toast" class="toast">Script Copied Successfully ✅</div>
<script>
function copyScript() {{
    const text = document.getElementById("script").innerText;
    navigator.clipboard.writeText(text).then(() => {{
        const toast = document.getElementById("toast");
        toast.style.display = "block";
        setTimeout(() => {{ toast.style.display = "none"; }}, 2500);
    }}).catch(err => {{
        console.error("Failed to copy script text:", err);
    }});
}}
</script>
</body>
</html>
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(f"Saved post page: {filepath}")

def send_to_telegram(script: str):
    """
    Sends generated script text to Telegram channel/chat in manageable message chunks.
    """
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("Telegram BOT_TOKEN or CHAT_ID is missing. Skipping Telegram dispatch.")
        return

    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    for i in range(0, len(script), 3500):
        try:
            response = requests.post(
                telegram_url,
                data={
                    "chat_id": CHAT_ID,
                    "text": script[i:i + 3500],
                },
                timeout=30,
            )
            if not response.ok:
                logger.error(f"Telegram API response error: {response.text}")
        except Exception as e:
            logger.error(f"Error sending message chunk to Telegram: {e}")

    logger.info("US market report successfully sent to Telegram.")

def get_master_prompt() -> str:
    """
    Returns AI system prompt dynamically based on CONTENT_TYPE ('short' vs standard 'video').
    """
    if CONTENT_TYPE == "short":
        return """
You are a professional US financial news anchor creating a YouTube Short for an American audience.

Create a 45–60 second YouTube Short about today's US stock market.

The audience is interested in:
- S&P 500
- Nasdaq
- Dow Jones
- Major US stocks
- Federal Reserve
- Inflation & Jobs data
- Economic news & Corporate earnings

FORMAT:
1. Powerful HOOK
2. What happened in today's market
3. Biggest reason behind the move
4. Biggest stock movers
5. What investors should watch next
6. Strong conclusion

Also provide:
- YouTube Shorts Title
- Thumbnail Text
- Description
- 10 Hashtags

IMPORTANT RULES:
- Write entirely in natural American English.
- Do not use non-English terms.
- Do not invent prices, percentages, news, or earnings.
- Use ONLY the supplied market data and headlines.
- Keep script suitable for a general financial audience.
"""

    return """
You are a professional US financial market analyst and YouTube financial news anchor.

Create a detailed 8–12 minute YouTube video script about today's US stock market.

COVER:
1. Powerful opening hook
2. Overall US market summary
3. S&P 500 analysis
4. Nasdaq analysis
5. Dow Jones analysis
6. Russell 2000 analysis
7. VIX / market volatility
8. Biggest US stock movers
9. Magnificent Seven / mega-cap stocks
10. Major financial headlines
11. Sector or market themes mentioned in news
12. Federal Reserve / economic developments
13. Earnings or corporate developments
14. Why the market moved
15. What investors are watching next
16. Tomorrow's potential catalysts
17. Conclusion & Financial disclaimer

Also provide:
- SEO YouTube Title
- Thumbnail Text
- YouTube Description
- 20 Hashtags
- Pinned Comment
- Chapter Timestamps

WRITING RULES:
- Write entirely in natural American English.
- Sound like a professional financial news anchor.
- Do not fabricate data or news headlines.
- Use ONLY supplied data.
- Include a clear financial disclaimer.
- Target approximately 1800–2500 words.
"""

def main():
    logger.info("============================================================")
    logger.info("             US MARKET AI SCRIPT GENERATOR                  ")
    logger.info("============================================================")

    # 1. Fetch Market Data
    logger.info("📊 Step 1: Fetching US market data...")
    market_data = get_market_data()
    stocks = get_major_stocks()
    market_text = format_market_data(market_data, stocks)

    print("\n" + market_text + "\n")

    # 2. Fetch News Headlines
    logger.info("📰 Step 2: Fetching financial news headlines...")
    news_text = fetch_news_headlines()

    # 3. Check Gemini API configuration
    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY is missing. Aborting generation.")
        return

    # 4. Construct AI Prompt
    master_prompt = get_master_prompt()
    today = datetime.now().strftime("%B %d, %Y")

    prompt = f"""
{master_prompt}

============================================================
DATE
============================================================
{today}

============================================================
US MARKET DATA
============================================================
{market_text}

============================================================
US FINANCIAL NEWS HEADLINES
============================================================
{news_text}

============================================================
FINAL INSTRUCTION
============================================================
Generate the final script now.
Do not mention that you are an AI.
Do not make up missing information.
Only use supplied market data and news.
"""

    logger.info("🤖 Step 3: Invoking Gemini AI Model...")
    try:
        # Standard stable model identifier
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)

        if not response.text:
            logger.error("❌ Gemini returned an empty response.")
            return

        script = (
            f"🇺🇸 US MARKET AI\n"
            f"📅 {today}\n"
            f"📊 Content Type: {CONTENT_TYPE.upper()}\n\n"
            f"{response.text}\n"
        )

        # 5. Save output text file
        with open("latest_script.txt", "w", encoding="utf-8") as f:
            f.write(script)
        logger.info("✅ Saved raw script to latest_script.txt")

        # 6. Save individual post HTML
        title = f"US Market Report - {today}"
        save_post(title, script)

        # 7. Update Archive Index HTML
        generate_index()

        # 8. Send via Telegram
        send_to_telegram(script)

        logger.info("✅ US Market AI workflow completed successfully.")

    except Exception as e:
        error_msg = f"❌ Gemini Generation Error:\n\n{e}"
        logger.error(error_msg)
        send_to_telegram(error_msg)

if __name__ == "__main__":
    main()
