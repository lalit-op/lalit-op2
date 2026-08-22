import os
import html
from datetime import datetime

import feedparser
import requests
import yfinance as yf
import google.generativeai as genai


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CONTENT_TYPE = os.getenv("CONTENT_TYPE", "video").lower()


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ============================================================
# US MARKET CONFIGURATION
# ============================================================

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


# ============================================================
# MARKET DATA
# ============================================================

def get_single_ticker_data(symbol):
    """
    Fetch latest available close and previous close
    for a Yahoo Finance ticker.
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

        if previous_close != 0:
            change_percent = (change / previous_close) * 100
        else:
            change_percent = 0

        return {
            "close": round(close, 2),
            "previous_close": round(previous_close, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
        }

    except Exception as e:
        print(f"Error fetching {symbol}: {e}")

        return {
            "close": None,
            "previous_close": None,
            "change": None,
            "change_percent": None,
        }


def get_market_data():
    """
    Fetch major US market indices.
    """

    print("Fetching US market indices...")

    market_data = {}

    for name, symbol in INDEXES.items():
        print(f"Fetching {name} ({symbol})...")

        market_data[name] = get_single_ticker_data(symbol)

    return market_data


def get_major_stocks():
    """
    Fetch major US stocks.
    """

    print("Fetching major US stocks...")

    stocks = {}

    for name, symbol in MAJOR_STOCKS.items():
        print(f"Fetching {name} ({symbol})...")

        stocks[name] = get_single_ticker_data(symbol)

    return stocks


# ============================================================
# FORMAT MARKET DATA
# ============================================================

def format_market_data(market_data, stocks):
    """
    Converts market data into clean text for Gemini.
    """

    lines = []

    lines.append("=== US MARKET INDICES ===")

    for name, data in market_data.items():

        if data["close"] is None:
            lines.append(f"{name}: Unavailable")
            continue

        direction = "UP" if data["change"] >= 0 else "DOWN"

        lines.append(
            f"{name}: "
            f"Close={data['close']}, "
            f"Change={data['change']}, "
            f"Change%={data['change_percent']}%, "
            f"Direction={direction}"
        )

    lines.append("")
    lines.append("=== MAJOR US STOCKS ===")

    for name, data in stocks.items():

        if data["close"] is None:
            lines.append(f"{name}: Unavailable")
            continue

        direction = "UP" if data["change"] >= 0 else "DOWN"

        lines.append(
            f"{name}: "
            f"Close={data['close']}, "
            f"Change={data['change']}, "
            f"Change%={data['change_percent']}%, "
            f"Direction={direction}"
        )

    return "\n".join(lines)


# ============================================================
# US FINANCIAL NEWS
# ============================================================

def fetch_news_headlines():
    """
    Fetch US financial news from RSS feeds.
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

    print("Fetching US financial news...")

    for source in sources:

        try:
            feed = feedparser.parse(source)

            for item in feed.entries[:20]:

                title = getattr(item, "title", "").strip()

                if not title:
                    continue

                if title not in headlines:
                    headlines.append(title)

        except Exception as e:
            print(f"Error reading {source}: {e}")

    print(f"Collected {len(headlines)} unique headlines.")

    return "\n".join(headlines[:100])


# ============================================================
# HTML INDEX
# ============================================================

# def generate_index():
#     """
#     Generates mobile-friendly index.html
#     containing all generated US market reports.
#     """

#     os.makedirs("posts", exist_ok=True)

    files = [
        f
        for f in os.listdir("posts")
        if f.endswith(".html") and f != "index.html"
    ]

    files.sort(reverse=True)

    cards = ""

    for file in files:

        date_str = file.replace(".html", "")

        cards += f"""
        <article class="report-card">

            <a href="{file}">
                US Market Report - {date_str}
            </a>

            <div class="date">
                📅 Published on {date_str}
            </div>

        </article>
        """

    html_content = f"""<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>US Market AI - Daily Reports</title>

<style>

* {{
    box-sizing: border-box;
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
            #1e3a8a55,
            transparent 40%
        ),
        radial-gradient(
            circle at top right,
            #06b6d455,
            transparent 40%
        ),
        #020617;

    color: #e2e8f0;
}}

.container {{
    max-width: 1000px;
    margin: auto;
    padding: 25px;
}}

.header {{
    text-align: center;
    padding: 45px 20px;
    margin-bottom: 25px;

    border-radius: 24px;

    background: rgba(255,255,255,0.05);

    border: 1px solid rgba(255,255,255,0.08);

    backdrop-filter: blur(20px);
}}

.badge {{
    display: inline-block;

    padding: 8px 15px;

    border-radius: 999px;

    color: #38bdf8;

    background: rgba(14,165,233,0.12);

    border: 1px solid rgba(56,189,248,0.25);

    font-size: 14px;
}}

h1 {{
    margin: 18px 0 10px;

    font-size: 46px;

    background:
        linear-gradient(
            90deg,
            #38bdf8,
            #22c55e,
            #facc15
        );

    -webkit-background-clip: text;

    -webkit-text-fill-color: transparent;
}}

.subtitle {{
    color: #94a3b8;

    font-size: 17px;
}}

.report-card {{
    margin-bottom: 15px;

    padding: 22px;

    border-radius: 20px;

    background: rgba(15,23,42,0.85);

    border: 1px solid rgba(255,255,255,0.08);

    transition: 0.2s;
}}

.report-card:hover {{
    transform: translateY(-3px);

    border-color: rgba(56,189,248,0.35);
}}

.report-card a {{
    color: #38bdf8;

    text-decoration: none;

    font-size: 22px;

    font-weight: 700;
}}

.date {{
    margin-top: 8px;

    color: #94a3b8;

    font-size: 14px;
}}

@media (max-width: 768px) {{

    .container {{
        padding: 15px;
    }}

    .header {{
        padding: 30px 15px;
    }}

    h1 {{
        font-size: 32px;
    }}

    .report-card a {{
        font-size: 18px;
    }}

}}

</style>

</head>

<body>

<div class="container">

    <div class="header">

        <div class="badge">
            🇺🇸 AI-Powered US Market Intelligence
        </div>

        <h1>
            US Market AI
        </h1>

        <div class="subtitle">
            Daily S&P 500, Nasdaq & Dow Jones Market Reports
        </div>

    </div>

    {cards}

</div>

</body>

</html>
"""

    with open("posts/index.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print("Updated posts/index.html")


# ============================================================
# SAVE INDIVIDUAL POST
# ============================================================

def save_post(title, content):
    """
    Generates a mobile-friendly HTML page
    for the generated US market script.
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

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>{safe_title}</title>

<link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"
    rel="stylesheet"
>

<style>

:root {{
    --bg: #020617;
    --card: #0f172a;
    --border: #1e293b;
    --text: #e2e8f0;
    --muted: #94a3b8;
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: 'Inter', sans-serif;

    background:
        radial-gradient(
            circle at top left,
            #1e3a8a33,
            transparent 40%
        ),
        radial-gradient(
            circle at top right,
            #06b6d433,
            transparent 40%
        ),
        var(--bg);

    color: var(--text);

    min-height: 100vh;
}}

.container {{
    max-width: 1200px;

    margin: auto;

    padding: 30px;
}}

.header {{
    text-align: center;

    padding: 40px;

    border-radius: 24px;

    margin-bottom: 25px;

    background:
        rgba(255,255,255,0.05);

    backdrop-filter: blur(20px);

    border:
        1px solid rgba(255,255,255,0.08);
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

    background:
        linear-gradient(
            90deg,
            #38bdf8,
            #22c55e,
            #facc15
        );

    -webkit-background-clip: text;

    -webkit-text-fill-color: transparent;

    line-height: 1.2;
}}

.tagline {{
    font-size: 18px;

    color: #38bdf8;

    margin-top: 10px;
}}

.toolbar {{
    display: flex;

    justify-content: flex-end;

    margin-bottom: 20px;
}}

.copy-btn {{
    background:
        linear-gradient(
            135deg,
            #2563eb,
            #06b6d4
        );

    color: white;

    border: none;

    padding: 14px 24px;

    border-radius: 14px;

    cursor: pointer;

    font-weight: 600;
}}

.copy-btn:hover {{
    transform: translateY(-2px);
}}

.card {{
    background:
        rgba(15,23,42,0.85);

    border:
        1px solid rgba(255,255,255,0.08);

    border-radius: 24px;

    overflow: hidden;

    backdrop-filter: blur(20px);

    box-shadow:
        0 25px 60px rgba(0,0,0,0.45);
}}

.card-top {{
    display: flex;

    align-items: center;

    padding: 15px 20px;

    border-bottom:
        1px solid rgba(255,255,255,0.08);
}}

.dots {{
    display: flex;

    gap: 8px;
}}

.dot {{
    width: 14px;

    height: 14px;

    border-radius: 50%;
}}

.red {{
    background: #ff5f57;
}}

.yellow {{
    background: #ffbd2e;
}}

.green {{
    background: #28c840;
}}

.file-name {{
    margin-left: 15px;

    color: #94a3b8;

    font-size: 14px;
}}

pre {{
    white-space: pre-wrap;

    word-wrap: break-word;

    padding: 30px;

    line-height: 1.8;

    font-size: 16px;

    color: #e2e8f0;

    font-family: 'Inter', sans-serif;
}}

.footer {{
    text-align: center;

    margin-top: 30px;

    color: #64748b;

    font-size: 14px;

    padding-bottom: 20px;
}}

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

    .container {{
        padding: 15px;
    }}

    .header {{
        padding: 25px 15px;
    }}

    .header h1 {{
        font-size: 32px;
    }}

    .tagline {{
        font-size: 15px;
    }}

    .toolbar {{
        justify-content: center;
    }}

    .copy-btn {{
        width: 100%;

        padding: 16px;
    }}

    .card {{
        border-radius: 16px;
    }}

    .file-name {{
        margin-left: 10px;

        font-size: 12px;
    }}

    pre {{
        padding: 20px 15px;

        font-size: 15px;
    }}

    .toast {{
        left: 50%;

        right: auto;

        transform: translateX(-50%);

        width: 90%;

        text-align: center;
    }}

}}

</style>

</head>

<body>

<div class="container">

    <div class="header">

        <div class="badge">
            🚀 AI Generated US Market Report
        </div>

        <h1>
            US Market AI
        </h1>

        <p class="tagline">
            Daily US Stock Market Intelligence
        </p>

    </div>

    <div class="toolbar">

        <button
            class="copy-btn"
            onclick="copyScript()"
        >
            📋 Copy Full Script
        </button>

    </div>

    <div class="card">

        <div class="card-top">

            <div class="dots">

                <span class="dot red"></span>

                <span class="dot yellow"></span>

                <span class="dot green"></span>

            </div>

            <div class="file-name">
                US Daily Market Analysis
            </div>

        </div>

        <pre id="script">{safe_content}</pre>

    </div>

    <div class="footer">
        US Market AI |
        Daily US Stock Market Reports |
        Powered by Gemini
    </div>

</div>

<div id="toast" class="toast">
    Script Copied Successfully ✅
</div>

<script>

function copyScript() {{

    const text =
        document
        .getElementById("script")
        .innerText;

    navigator.clipboard
        .writeText(text)
        .then(() => {{

            const toast =
                document.getElementById("toast");

            toast.style.display = "block";

            setTimeout(() => {{
                toast.style.display = "none";
            }}, 2500);

        }})
        .catch(err => {{
            console.error(
                "Failed to copy:",
                err
            );
        }});

}}

</script>

</body>

</html>
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("Saved:", filepath)


# ============================================================
# TELEGRAM
# ============================================================

def send_to_telegram(script):
    """
    Sends generated script to Telegram in chunks.
    """

    if not BOT_TOKEN or not CHAT_ID:

        print(
            "Telegram BOT_TOKEN or CHAT_ID missing. "
            "Skipping Telegram notification."
        )

        return

    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

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

                print(
                    "Telegram error:",
                    response.text
                )

        except Exception as e:

            print(
                f"Error sending to Telegram: {e}"
            )

    print(
        "US market report sent to Telegram."
    )


# ============================================================
# GEMINI PROMPTS
# ============================================================

def get_master_prompt():
    """
    Returns prompt based on CONTENT_TYPE.
    """

    if CONTENT_TYPE == "short":

        return """
You are a professional US financial news anchor
creating a YouTube Short for an American audience.

Create a 45–60 second YouTube Short about today's
US stock market.

The audience is interested in:
- S&P 500
- Nasdaq
- Dow Jones
- Major US stocks
- Federal Reserve
- Inflation
- Jobs data
- Economic news
- Corporate earnings

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
- Do not use Hindi.
- Do not invent prices.
- Do not invent percentages.
- Do not invent news.
- Do not invent earnings.
- Do not invent Federal Reserve decisions.
- Use ONLY the supplied market data and headlines.
- Clearly distinguish facts from analysis.
- Keep the script suitable for a general audience.
- Do not give personalized financial advice.
"""

    return """
You are a professional US financial market analyst
and YouTube financial news anchor.

Create a detailed 8–12 minute YouTube video script
about today's US stock market.

The target audience is interested in US equities
and follows the daily market closely.

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
11. Sector or market themes mentioned in the news
12. Federal Reserve / economic developments if supported
13. Earnings or corporate developments if supported
14. Why the market moved
15. What investors are watching next
16. Tomorrow's potential catalysts
17. Conclusion
18. Financial disclaimer

Also provide:

- SEO YouTube Title
- Thumbnail Text
- YouTube Description
- 20 Hashtags
- Pinned Comment
- Chapter Timestamps

WRITING RULES:

- Write entirely in natural American English.
- Do not use Hindi.
- Sound like a professional financial news channel.
- Make the opening engaging.
- Explain financial terms simply.
- Do not repeat the same information unnecessarily.
- Do not fabricate data.
- Do not fabricate headlines.
- Do not fabricate earnings.
- Do not fabricate Federal Reserve actions.
- Do not fabricate economic data.
- Use ONLY the supplied market data and headlines.
- If information is unavailable, explicitly say it is unavailable.
- Do not provide personalized investment advice.
- Include a clear financial disclaimer.
- Target approximately 1800–2500 words.
"""


# ============================================================
# MAIN EXECUTION
# ============================================================

def main():

    print("=" * 60)
    print("US MARKET AI SCRIPT GENERATOR")
    print("=" * 60)

    # --------------------------------------------------------
    # MARKET DATA
    # --------------------------------------------------------

    print("\n📊 Fetching US market data...")

    market_data = get_market_data()

    stocks = get_major_stocks()

    market_text = format_market_data(
        market_data,
        stocks
    )

    print("\n" + market_text)

    # --------------------------------------------------------
    # NEWS
    # --------------------------------------------------------

    print("\n📰 Fetching US financial news...")

    news_text = fetch_news_headlines()

    # --------------------------------------------------------
    # GEMINI API CHECK
    # --------------------------------------------------------

    if not GEMINI_API_KEY:

        print(
            "❌ GEMINI_API_KEY is missing."
        )

        return

    # --------------------------------------------------------
    # PROMPT
    # --------------------------------------------------------

    master_prompt = get_master_prompt()

    today = datetime.now().strftime(
        "%B %d, %Y"
    )

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

Only use the supplied market data and news.
"""

    # --------------------------------------------------------
    # GEMINI GENERATION
    # --------------------------------------------------------

    print(
        "\n🤖 Generating US market script..."
    )

    try:

        model = genai.GenerativeModel(
            "gemini-3.6-flash"
        )

        response = model.generate_content(
            prompt
        )

        if not response.text:

            print(
                "❌ Gemini returned an empty response."
            )

            return

        script = (
            f"🇺🇸 US MARKET AI\n"
            f"📅 {today}\n"
            f"📊 Content Type: "
            f"{CONTENT_TYPE.upper()}\n\n"
            f"{response.text}\n"
        )

        # ----------------------------------------------------
        # SAVE TXT
        # ----------------------------------------------------

        with open(
            "latest_script.txt",
            "w",
            encoding="utf-8"
        ) as f:

            f.write(script)

        print(
            "✅ Saved latest_script.txt"
        )

        # ----------------------------------------------------
        # SAVE HTML
        # ----------------------------------------------------

        title = (
            f"US Market Report - {today}"
        )

        save_post(
            title,
            script
        )

        # ----------------------------------------------------
        # UPDATE INDEX
        # ----------------------------------------------------

        generate_index()

        # ----------------------------------------------------
        # TELEGRAM
        # ----------------------------------------------------

        send_to_telegram(script)

        print(
            "\n✅ US market workflow completed."
        )

    except Exception as e:

        error_msg = (
            f"❌ Gemini Error\n\n{e}"
        )

        print(error_msg)

        send_to_telegram(
            error_msg
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
