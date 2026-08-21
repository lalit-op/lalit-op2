import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


BOT_TOKEN = os.getenv("BOT_TOKEN")


async def script_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("latest_script.txt", "r", encoding="utf-8") as f:
            script = f.read()

        if not script.strip():
            await update.message.reply_text(
                "🇺🇸 Today's US market script is empty."
            )
            return

        # Telegram allows approximately 4096 characters per message.
        # Keep a safety margin.
        for i in range(0, len(script), 4000):
            await update.message.reply_text(script[i:i + 4000])

    except FileNotFoundError:
        await update.message.reply_text(
            "🇺🇸 Today's US market script is not available yet.\n"
            "Please try again after the US market closes."
        )

    except Exception as e:
        print(f"Error sending script: {e}")

        await update.message.reply_text(
            "❌ Unable to load today's US market script."
        )


app = Application.builder().token(BOT_TOKEN).build()


app.add_handler(
    CommandHandler("script", script_command)
)


print("🇺🇸 US Market Bot Started...")


app.run_polling()
