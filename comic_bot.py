import os
import pytz
from io import BytesIO
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
import openai
from PIL import Image, ImageDraw, ImageFont

# --- اطلاعات امنیتی ---
TELEGRAM_TOKEN = '7561666851:AAE4RIl0epwq8oQrPVWgQrrpAJss1iUIVHM'
OPENAI_API_KEY = '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'

openai.api_key = OPENAI_API_KEY

CHOOSING_TYPE, WAITING_FOR_PHOTOS, WAITING_FOR_FORMAT = range(3)
user_photos = {}

# --- ساخت کمیک ---
def create_comic(images, story_parts):
    try:
        font = ImageFont.truetype("arial.ttf", size=20)
    except:
        font = ImageFont.load_default()

    comic_images = []
    for img_data, text in zip(images, story_parts):
        img_data.seek(0)
        img = Image.open(img_data).convert("RGB")
        draw = ImageDraw.Draw(img)

        width, height = img.size
        text_bg_height = 60
        draw.rectangle([0, height - text_bg_height, width, height], fill=(0, 0, 0))
        draw.text((10, height - text_bg_height + 10), text, fill=(255, 255, 255), font=font)
        comic_images.append(img)

    final_img = Image.new("RGB", (comic_images[0].width, comic_images[0].height * len(comic_images)))
    for idx, img in enumerate(comic_images):
        final_img.paste(img, (0, idx * img.height))

    output = BytesIO()
    final_img.save(output, format="JPEG")
    output.seek(0)
    return output

# --- تولید داستان از طریق OpenAI ---
def generate_story(prompts):
    stories = []
    for prompt in prompts:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "تو یک نویسنده کمیک هستی."},
                {"role": "user", "content": f"برای این صحنه کمیک بنویس: {prompt}"}
            ]
        )
        stories.append(response['choices'][0]['message']['content'])
    return stories

# --- هندلرها ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! لطفاً سبک داستانت رو انتخاب کن:\n1. کمدی\n2. فانتزی\n3. تاریک")
    return CHOOSING_TYPE

async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("حالا لطفاً عکس‌هات رو بفرست. وقتی تموم شد، دستور /done رو بزن.")
    user_photos[update.message.chat_id] = []
    return WAITING_FOR_PHOTOS

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    image_stream = BytesIO()
    await photo_file.download_to_memory(out=image_stream)
    image_stream.seek(0)
    user_photos[update.message.chat_id].append(image_stream)
    await update.message.reply_text("عکس دریافت شد. عکس بعدی؟ یا دستور /done رو بزن.")
    return WAITING_FOR_PHOTOS

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("در چه فرمتی خروجی بدم؟ jpg یا pdf ؟")
    return WAITING_FOR_FORMAT

async def output_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fmt = update.message.text.lower()
    images = user_photos.get(update.message.chat_id, [])
    prompts = [f"صحنه شماره {i+1}" for i in range(len(images))]
    story_parts = generate_story(prompts)
    comic = create_comic(images, story_parts)

    if fmt == "pdf":
        await update.message.reply_document(document=comic, filename="comic.pdf")
    else:
        await update.message.reply_photo(photo=comic)

    await update.message.reply_text("کمیک آماده شد!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لغو شد.")
    return ConversationHandler.END

# --- اجرای بات ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_type)],
            WAITING_FOR_PHOTOS: [
                MessageHandler(filters.PHOTO, photo_handler),
                CommandHandler("done", done),
            ],
            WAITING_FOR_FORMAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, output_format)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    print("ربات اجرا شد...")
    app.run_polling()
