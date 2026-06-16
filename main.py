"""
ربات فروشگاهی تلگرام
امکانات: خرید سرویس، کیف پول، سرویس‌های من، پشتیبانی
تایید پرداخت و ارسال کانفیگ از طریق گروه ادمین انجام می‌شود.
"""

import logging
import os
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import database as db

# ---------------------------------------------------------------------------
# تنظیمات کلی
# پیشنهاد می‌شود این مقادیر را به صورت Environment Variable در Railway تنظیم کنید
# تا اطلاعات حساس داخل کد قرار نگیرد.
# ---------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8589038863:AAFBrmmLV5KOcO0Mw8PCGU0F8_KQv32GR_U")
ADMIN_GROUP_ID = int(os.environ.get("ADMIN_GROUP_ID", "-1003966066313"))
ADMIN_ID = int(os.environ.get("ADMIN_ID", "8589038863"))
SUPPORT_USERNAME = os.environ.get("SUPPORT_USERNAME", "Aiireza_1383")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# پلن‌ها و اطلاعات کارت‌ها
# ---------------------------------------------------------------------------

PLANS = {
    "10gb": {"name": "10 GB", "price": 110_000, "icon": "🔹", "desc": "مناسب برای استفاده روزمره و سبک"},
    "20gb": {"name": "20 GB", "price": 220_000, "icon": "🔷", "desc": "پرفروش‌ترین پلن، مناسب اکثر کاربران"},
    "30gb": {"name": "30 GB", "price": 300_000, "icon": "🔶", "desc": "مناسب کاربران پرمصرف"},
    "50gb": {"name": "50 GB", "price": 499_000, "icon": "💎", "desc": "حجم بالا، بدون نگرانی برای اتمام حجم"},
}

# اطلاعات کارت برای پرداخت کارت‌به‌کارت
CARD = {"number": "6063 7312 6171 9448", "holder": "محمد تمیمی خلف آبادی"}

# ---------------------------------------------------------------------------
# وضعیت‌های مکالمه (ConversationHandler states)
# ---------------------------------------------------------------------------

(
    SELECTING_PLAN,
    TYPING_CONFIG_NAME,
    SELECTING_PAYMENT,
    WAITING_CARD_RECEIPT,
    WALLET_MENU,
    TYPING_TOPUP_AMOUNT,
    WAITING_TOPUP_RECEIPT,
) = range(7)


# ---------------------------------------------------------------------------
# کیبوردها
# ---------------------------------------------------------------------------

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛒 خرید سرویس", callback_data="buy_service"),
            InlineKeyboardButton("📦 سرویس های من", callback_data="my_services"),
        ],
        [
            InlineKeyboardButton("💬 پشتیبانی", callback_data="support"),
            InlineKeyboardButton("👛 کیف پول", callback_data="wallet"),
        ],
    ])


def plans_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for key, plan in PLANS.items():
        label = f"{plan['icon']} {plan['name']}  |  {plan['price']:,} تومان"
        buttons.append([InlineKeyboardButton(label, callback_data=f"plan_{key}")])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def plans_intro_text() -> str:
    return "⚡️ از سرویس‌های پرسرعت زیر یک مورد را انتخاب کنید 👇"


def back_keyboard(callback_data: str = "back_main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=callback_data)]])


def main_menu_button_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_main")]])


# ---------------------------------------------------------------------------
# دستورات و منوی اصلی
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username)

    text = (
        "👋 سلام و خوش آمدید!\n\n"
        "به ربات فروشگاه ما خوش آمدید. از منوی زیر یکی از گزینه‌ها را انتخاب کنید 👇"
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()

    text = "🏠 منوی اصلی\n\nیکی از گزینه‌ها را انتخاب کنید 👇"
    await query.edit_message_text(text, reply_markup=main_menu_keyboard())
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# بخش خرید سرویس
# ---------------------------------------------------------------------------

async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()

    await query.edit_message_text(
        plans_intro_text(),
        reply_markup=plans_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return SELECTING_PLAN


async def select_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_key = query.data.split("_", 1)[1]
    plan = PLANS[plan_key]
    context.user_data["plan_key"] = plan_key

    text = (
        f"✅ پلن انتخابی شما: {plan['name']} - {plan['price']:,} تومان\n\n"
        "✏️ لطفاً یک نام انگلیسی برای کانفیگ خود ارسال کنید.\n"
        "مثال: Alireza\n\n"
        "(فقط حروف و اعداد انگلیسی، بدون فاصله و کاراکتر خاص)"
    )
    await query.edit_message_text(text, reply_markup=back_keyboard("back_plans"))
    return TYPING_CONFIG_NAME


async def back_to_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        plans_intro_text(),
        reply_markup=plans_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )
    return SELECTING_PLAN


async def receive_config_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()

    if not re.match(r"^[A-Za-z0-9_]{2,32}$", name):
        await update.message.reply_text(
            "❌ نام وارد شده معتبر نیست.\n"
            "لطفاً فقط از حروف و اعداد انگلیسی استفاده کنید (مثال: Alireza)"
        )
        return TYPING_CONFIG_NAME

    plan_key = context.user_data["plan_key"]
    plan = PLANS[plan_key]
    context.user_data["config_name"] = name

    user_id = update.effective_user.id
    balance = db.get_wallet_balance(user_id)

    text = (
        "╔══════════════════════╗\n"
        "       🛒  خلاصه سفارش شما\n"
        "╚══════════════════════╝\n\n"
        f"📦  پلن: {plan['name']}\n"
        f"💰  قیمت اصلی: {plan['price']:,} تومان\n"
        f"✅  مبلغ نهایی: {plan['price']:,} تومان\n"
        f"🏷️  نام کانفیگ: {name}\n"
        f"👛  موجودی کیف پول: {balance:,} تومان\n\n"
        "👇 روش پرداخت را انتخاب کنید:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 پرداخت کارت به کارت", callback_data="pay_card")],
        [InlineKeyboardButton("👛 پرداخت با کیف پول", callback_data="pay_wallet")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_plans")],
    ])
    await update.message.reply_text(text, reply_markup=keyboard)
    return SELECTING_PAYMENT


async def pay_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan = PLANS[context.user_data["plan_key"]]

    order_id = db.create_order(
        user_id=update.effective_user.id,
        order_type="purchase_card",
        plan_name=plan["name"],
        amount=plan["price"],
        config_name=context.user_data["config_name"],
    )
    context.user_data["order_id"] = order_id

    text = (
        "╔══════════════════════╗\n"
        "     💳  اطلاعات پرداخت\n"
        "╚══════════════════════╝\n\n"
        f"💰 مبلغ: {plan['price']:,} تومان\n\n"
        "شماره کارت:\n"
        f"{CARD['number']}\n"
        f"👤 به نام: {CARD['holder']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📸 پس از واریز، عکس رسید را در همین چت ارسال کنید:"
    )
    await query.edit_message_text(text, reply_markup=back_keyboard("back_plans"))
    return WAITING_CARD_RECEIPT


async def receive_card_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ لطفاً عکس رسید پرداخت را ارسال کنید.")
        return WAITING_CARD_RECEIPT

    order_id = context.user_data.get("order_id")
    order = db.get_order(order_id)
    user = update.effective_user

    caption = (
        "🧾 رسید پرداخت جدید (کارت به کارت)\n\n"
        f"👤 کاربر: {user.mention_html()}\n"
        f"🆔 آیدی عددی: {user.id}\n"
        f"📦 پلن: {order['plan_name']}\n"
        f"💰 مبلغ: {order['amount']:,} تومان\n"
        f"🏷️ نام کانفیگ: {order['config_name']}\n\n"
        "✅ برای تایید، روی این پیام ریپلای کرده و متن کانفیگ را ارسال کنید."
    )
    photo_file_id = update.message.photo[-1].file_id

    msg = await context.bot.send_photo(
        chat_id=ADMIN_GROUP_ID,
        photo=photo_file_id,
        caption=caption,
        parse_mode=ParseMode.HTML,
    )
    db.set_order_group_message(order_id, msg.message_id)

    text = (
        "✅ رسید شما برای ادمین ارسال شد.\n"
        "پس از بررسی و تایید، کانفیگ به همین چت ارسال خواهد شد. 🙏"
    )
    await update.message.reply_text(text, reply_markup=main_menu_button_keyboard())
    context.user_data.clear()
    return ConversationHandler.END


async def pay_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan = PLANS[context.user_data["plan_key"]]
    user_id = update.effective_user.id
    balance = db.get_wallet_balance(user_id)

    if balance < plan["price"]:
        shortage = plan["price"] - balance
        text = (
            "⚠️ موجودی کیف پول شما کافی نیست.\n\n"
            f"👛 موجودی فعلی: {balance:,} تومان\n"
            f"💰 قیمت سرویس: {plan['price']:,} تومان\n"
            f"❗️ مقدار کسری: {shortage:,} تومان\n\n"
            "لطفاً ابتدا کیف پول خود را شارژ کنید، سپس دوباره برای خرید این سرویس اقدام کنید."
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="topup_start")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_plans")],
        ])
        await query.edit_message_text(text, reply_markup=keyboard)
        return SELECTING_PAYMENT

    # موجودی کافی است -> ثبت سفارش و اطلاع به گروه ادمین
    order_id = db.create_order(
        user_id=user_id,
        order_type="purchase_wallet",
        plan_name=plan["name"],
        amount=plan["price"],
        config_name=context.user_data["config_name"],
    )

    admin_text = (
        "🆕 درخواست خرید با کیف پول\n\n"
        f"👤 کاربر: {update.effective_user.mention_html()}\n"
        f"🆔 آیدی عددی: {user_id}\n"
        f"📦 پلن: {plan['name']}\n"
        f"💰 مبلغ کسر شده از کیف پول: {plan['price']:,} تومان\n"
        f"🏷️ نام کانفیگ: {context.user_data['config_name']}\n\n"
        "✅ برای تایید، روی این پیام ریپلای کرده و متن کانفیگ را ارسال کنید.\n"
        "(پس از تایید، مبلغ از کیف پول کاربر کسر می‌شود)"
    )
    msg = await context.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=admin_text,
        parse_mode=ParseMode.HTML,
    )
    db.set_order_group_message(order_id, msg.message_id)

    text = (
        "✅ درخواست خرید شما ثبت شد.\n"
        "پس از تایید توسط ادمین، کانفیگ برای شما ارسال و هزینه از کیف پول شما کسر می‌شود.\n\n"
        "🙏 لطفاً منتظر بمانید."
    )
    await query.edit_message_text(text, reply_markup=main_menu_button_keyboard())
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# بخش کیف پول و شارژ
# ---------------------------------------------------------------------------

async def wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()

    user_id = update.effective_user.id
    balance = db.get_wallet_balance(user_id)

    text = (
        "👛 کیف پول شما\n\n"
        f"💰 موجودی فعلی: {balance:,} تومان\n\n"
        "برای افزایش موجودی روی دکمه زیر کلیک کنید:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 افزایش موجودی", callback_data="topup_start")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ])
    await query.edit_message_text(text, reply_markup=keyboard)
    return WALLET_MENU


async def topup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "💰 افزایش موجودی کیف پول\n\n"
        "لطفاً مبلغی که می‌خواهید شارژ کنید را به تومان و فقط به عدد ارسال کنید.\n"
        "مثال: 100000"
    )
    await query.edit_message_text(text, reply_markup=back_keyboard("back_main"))
    return TYPING_TOPUP_AMOUNT


async def receive_topup_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip().replace(",", "").replace("،", "")

    if not raw.isdigit() or int(raw) <= 0:
        await update.message.reply_text(
            "❌ لطفاً فقط یک عدد صحیح و مثبت ارسال کنید.\nمثال: 100000"
        )
        return TYPING_TOPUP_AMOUNT

    amount = int(raw)
    context.user_data["topup_amount"] = amount

    text = (
        "╔══════════════════════╗\n"
        "     💳  اطلاعات پرداخت\n"
        "╚══════════════════════╝\n\n"
        f"💰 مبلغ: {amount:,} تومان\n\n"
        "شماره کارت:\n"
        f"{CARD['number']}\n"
        f"👤 به نام: {CARD['holder']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📸 پس از واریز، عکس رسید را در همین چت ارسال کنید:"
    )
    await update.message.reply_text(text, reply_markup=back_keyboard("back_main"))
    return WAITING_TOPUP_RECEIPT


async def receive_topup_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ لطفاً عکس رسید پرداخت را ارسال کنید.")
        return WAITING_TOPUP_RECEIPT

    amount = context.user_data["topup_amount"]
    user = update.effective_user

    order_id = db.create_order(
        user_id=user.id,
        order_type="topup",
        plan_name=None,
        amount=amount,
        config_name=None,
    )

    caption = (
        "💰 درخواست شارژ کیف پول\n\n"
        f"👤 کاربر: {user.mention_html()}\n"
        f"🆔 آیدی عددی: {user.id}\n"
        f"💵 مبلغ واریزی: {amount:,} تومان\n\n"
        "✅ برای تایید، روی این پیام ریپلای کرده و دقیقاً همین مبلغ را به تومان ارسال کنید.\n"
        f"(مثال: {amount})"
    )
    photo_file_id = update.message.photo[-1].file_id

    msg = await context.bot.send_photo(
        chat_id=ADMIN_GROUP_ID,
        photo=photo_file_id,
        caption=caption,
        parse_mode=ParseMode.HTML,
    )
    db.set_order_group_message(order_id, msg.message_id)

    text = (
        "✅ رسید شما ارسال شد.\n"
        "پس از تایید ادمین، کیف پول شما شارژ خواهد شد. 🙏"
    )
    await update.message.reply_text(text, reply_markup=main_menu_button_keyboard())
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# سرویس‌های من
# ---------------------------------------------------------------------------

async def my_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    services = db.get_user_services(user_id)

    if not services:
        text = (
            "📦 سرویس‌های من\n\n"
            "شما تا کنون هیچ سرویسی خریداری نکرده‌اید.\n"
            "برای خرید به منوی «خرید سرویس» مراجعه کنید."
        )
    else:
        lines = ["📦 سرویس‌های خریداری‌شده شما:\n"]
        for s in services:
            lines.append(
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 پلن: {s['plan_name']}\n"
                f"🏷️ نام کانفیگ: {s['config_name']}\n"
                f"🔗 کانفیگ:\n{s['config_text']}"
            )
        text = "\n\n".join(lines)

    await query.edit_message_text(text, reply_markup=back_keyboard("back_main"))


# ---------------------------------------------------------------------------
# پشتیبانی
# ---------------------------------------------------------------------------

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "💬 پشتیبانی\n\n"
        "برای ارتباط با تیم پشتیبانی روی دکمه زیر کلیک کنید 👇"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👨‍💻 ارتباط با پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ])
    await query.edit_message_text(text, reply_markup=keyboard)


# ---------------------------------------------------------------------------
# پردازش پاسخ ادمین در گروه (ریپلای روی رسید / درخواست)
# ---------------------------------------------------------------------------

async def admin_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message is None or message.chat_id != ADMIN_GROUP_ID:
        return
    if message.reply_to_message is None:
        return

    order = db.get_order_by_group_message(message.reply_to_message.message_id)
    if order is None:
        return

    if order["status"] != "pending":
        await message.reply_text("⚠️ این سفارش قبلاً پردازش شده است.")
        return

    if order["type"] == "topup":
        await _handle_topup_approval(message, context, order)
    elif order["type"] in ("purchase_card", "purchase_wallet"):
        await _handle_purchase_approval(message, context, order)


async def _handle_topup_approval(message, context: ContextTypes.DEFAULT_TYPE, order):
    amount_text = (message.text or "").strip().replace(",", "").replace("،", "")
    if not amount_text.isdigit():
        await message.reply_text(
            "❌ لطفاً برای تایید شارژ کیف پول، فقط مبلغ را به تومان و به صورت عدد ارسال کنید."
        )
        return

    amount = int(amount_text)
    db.change_wallet_balance(order["user_id"], amount)
    db.update_order_status(order["id"], "approved")
    new_balance = db.get_wallet_balance(order["user_id"])

    try:
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                "✅ کیف پول شما با موفقیت شارژ شد.\n\n"
                f"💵 مبلغ شارژ شده: {amount:,} تومان\n"
                f"👛 موجودی جدید: {new_balance:,} تومان"
            ),
        )
    except Exception:
        logger.exception("ارسال پیام شارژ به کاربر %s ناموفق بود", order["user_id"])

    await message.reply_text("✅ کیف پول کاربر با موفقیت شارژ شد.")


async def _handle_purchase_approval(message, context: ContextTypes.DEFAULT_TYPE, order):
    config_text = (message.text or "").strip()
    if not config_text:
        await message.reply_text(
            "❌ لطفاً برای تایید سفارش، متن کانفیگ را به صورت پیام ریپلای ارسال کنید."
        )
        return

    if order["type"] == "purchase_wallet":
        db.change_wallet_balance(order["user_id"], -order["amount"])

    db.set_order_config(order["id"], config_text)
    db.update_order_status(order["id"], "approved")

    delivery_text = (
        "🎉 پرداخت شما تایید شد!\n\n"
        f"📦 پلن: {order['plan_name']}\n"
        f"🏷️ نام کانفیگ: {order['config_name']}\n\n"
        f"🔗 کانفیگ شما:\n{config_text}\n\n"
        "از خرید شما متشکریم 🙏"
    )

    delivery_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 خرید سرویس جدید", callback_data="buy_service")]
    ])

    try:
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=delivery_text,
            reply_markup=delivery_keyboard,
        )
    except Exception:
        logger.exception("ارسال کانفیگ به کاربر %s ناموفق بود", order["user_id"])

    await message.reply_text("✅ کانفیگ برای کاربر ارسال شد و سفارش تایید گردید.")


# ---------------------------------------------------------------------------
# راه‌اندازی اپلیکیشن
# ---------------------------------------------------------------------------

def main():
    db.init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    purchase_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(show_plans, pattern="^buy_service$"),
            CallbackQueryHandler(wallet_menu, pattern="^wallet$"),
        ],
        states={
            SELECTING_PLAN: [
                CallbackQueryHandler(select_plan, pattern="^plan_"),
                CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            ],
            TYPING_CONFIG_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_config_name),
                CallbackQueryHandler(back_to_plans, pattern="^back_plans$"),
            ],
            SELECTING_PAYMENT: [
                CallbackQueryHandler(pay_card, pattern="^pay_card$"),
                CallbackQueryHandler(pay_wallet, pattern="^pay_wallet$"),
                CallbackQueryHandler(topup_start, pattern="^topup_start$"),
                CallbackQueryHandler(back_to_plans, pattern="^back_plans$"),
            ],
            WAITING_CARD_RECEIPT: [
                MessageHandler(filters.PHOTO, receive_card_receipt),
                CallbackQueryHandler(back_to_plans, pattern="^back_plans$"),
            ],
            WALLET_MENU: [
                CallbackQueryHandler(topup_start, pattern="^topup_start$"),
                CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            ],
            TYPING_TOPUP_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_topup_amount),
                CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            ],
            WAITING_TOPUP_RECEIPT: [
                MessageHandler(filters.PHOTO, receive_topup_receipt),
                CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            CommandHandler("start", start),
        ],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(purchase_conversation)
    application.add_handler(CallbackQueryHandler(my_services, pattern="^my_services$"))
    application.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_main$"))

    # پردازش پاسخ‌های ادمین در گروه (ریپلای روی رسید‌ها)
    application.add_handler(
        MessageHandler(filters.Chat(chat_id=ADMIN_GROUP_ID) & filters.REPLY, admin_reply_handler)
    )

    logger.info("ربات در حال اجرا است...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
