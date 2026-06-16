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
# تنظیمات
# ---------------------------------------------------------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8589038863:AAFBrmmLV5KOcO0Mw8PCGU0F8_KQv32GR_U")
ADMIN_GROUP_ID = int(os.environ.get("ADMIN_GROUP_ID", "-1003966066313"))
ADMIN_ID = int(os.environ.get("ADMIN_ID", "7374971382"))
SUPPORT_USERNAME = os.environ.get("SUPPORT_USERNAME", "Aiireza_1383")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# پلن های اقتصادی
# ---------------------------------------------------------------------------
ECO_PLANS = {
    "eco_10gb":  {"name": "10 GB",   "price": 110_000},
    "eco_20gb":  {"name": "20 GB",   "price": 220_000},
    "eco_30gb":  {"name": "30 GB",   "price": 300_000},
    "eco_50gb":  {"name": "50 GB",   "price": 499_000},
}

# ---------------------------------------------------------------------------
# پلن های VIP
# ---------------------------------------------------------------------------
VIP_PLANS = {
    "vip_10gb":  {"name": "10 GB",    "price": 150_000},
    "vip_20gb":  {"name": "20 GB",    "price": 299_000},
    "vip_unltd": {"name": "نامحدود", "price": 449_000},
}

ALL_PLANS = {**ECO_PLANS, **VIP_PLANS}

CARD = {"number": "6063 7312 6171 9448", "holder": "محمد تمیمی خلف آبادی"}

# ---------------------------------------------------------------------------
# وضعیت های مکالمه
# ---------------------------------------------------------------------------
(
    SELECTING_CATEGORY,
    SELECTING_PLAN,
    TYPING_CONFIG_NAME,
    SELECTING_PAYMENT,
    WAITING_CARD_RECEIPT,
    WALLET_MENU,
    TYPING_TOPUP_AMOUNT,
    WAITING_TOPUP_RECEIPT,
) = range(8)


# ---------------------------------------------------------------------------
# کیبوردها
# ---------------------------------------------------------------------------
def main_menu_keyboard():
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


def category_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 پلن اقتصادی", callback_data="cat_eco")],
        [InlineKeyboardButton("VIP پر سرعت ⚡️", callback_data="cat_vip")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ])


def eco_plans_keyboard():
    buttons = []
    for key, plan in ECO_PLANS.items():
        buttons.append([InlineKeyboardButton(
            f"🔹 {plan['name']}  |  {plan['price']:,} تومان",
            callback_data=f"plan_{key}"
        )])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_category")])
    return InlineKeyboardMarkup(buttons)


def vip_plans_keyboard():
    buttons = []
    for key, plan in VIP_PLANS.items():
        buttons.append([InlineKeyboardButton(
            f"⚡️ {plan['name']}  |  {plan['price']:,} تومان",
            callback_data=f"plan_{key}"
        )])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_category")])
    return InlineKeyboardMarkup(buttons)


def back_keyboard(cb="back_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=cb)]])


def main_menu_button_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_main")]])


# ---------------------------------------------------------------------------
# استارت و منوی اصلی
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username)
    await update.message.reply_text(
        "👋 سلام و خوش آمدید!\n\nاز منوی زیر یکی از گزینه‌ها را انتخاب کنید 👇",
        reply_markup=main_menu_keyboard()
    )


async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "🏠 منوی اصلی\n\nیکی از گزینه‌ها را انتخاب کنید 👇",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# خرید سرویس - انتخاب دسته
# ---------------------------------------------------------------------------
async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "🛒 خرید سرویس\n\nنوع پلن مورد نظر را انتخاب کنید 👇",
        reply_markup=category_keyboard()
    )
    return SELECTING_CATEGORY


async def back_to_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🛒 خرید سرویس\n\nنوع پلن مورد نظر را انتخاب کنید 👇",
        reply_markup=category_keyboard()
    )
    return SELECTING_CATEGORY


# ---------------------------------------------------------------------------
# خرید سرویس - انتخاب پلن
# ---------------------------------------------------------------------------
async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = query.data  # "cat_eco" یا "cat_vip"
    context.user_data["cat"] = cat

    if cat == "cat_eco":
        await query.edit_message_text(
            "💰 پلن اقتصادی\n\nیک پلن را انتخاب کنید 👇",
            reply_markup=eco_plans_keyboard()
        )
    else:
        await query.edit_message_text(
            "VIP پر سرعت ⚡️\n\nیک پلن را انتخاب کنید 👇",
            reply_markup=vip_plans_keyboard()
        )
    return SELECTING_PLAN


async def back_to_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat = context.user_data.get("cat", "cat_eco")

    if cat == "cat_eco":
        await query.edit_message_text(
            "💰 پلن اقتصادی\n\nیک پلن را انتخاب کنید 👇",
            reply_markup=eco_plans_keyboard()
        )
    else:
        await query.edit_message_text(
            "VIP پر سرعت ⚡️\n\nیک پلن را انتخاب کنید 👇",
            reply_markup=vip_plans_keyboard()
        )
    return SELECTING_PLAN


async def select_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_key = query.data[5:]  # حذف "plan_" از ابتدا
    plan = ALL_PLANS[plan_key]
    context.user_data["plan_key"] = plan_key

    await query.edit_message_text(
        f"✅ پلن انتخابی: {plan['name']} - {plan['price']:,} تومان\n\n"
        "✏️ یک نام انگلیسی برای کانفیگ ارسال کنید.\n"
        "مثال: Alireza\n\n"
        "(فقط حروف و اعداد انگلیسی، بدون فاصله)",
        reply_markup=back_keyboard("back_plans")
    )
    return TYPING_CONFIG_NAME


async def receive_config_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()

    if not re.match(r"^[A-Za-z0-9_]{2,32}$", name):
        await update.message.reply_text(
            "❌ نام معتبر نیست.\nفقط از حروف و اعداد انگلیسی استفاده کنید. مثال: Alireza"
        )
        return TYPING_CONFIG_NAME

    plan_key = context.user_data["plan_key"]
    plan = ALL_PLANS[plan_key]
    context.user_data["config_name"] = name

    balance = db.get_wallet_balance(update.effective_user.id)

    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "       🛒  خلاصه سفارش شما\n"
        "╚══════════════════════╝\n\n"
        f"📦  پلن: {plan['name']}\n"
        f"💰  قیمت: {plan['price']:,} تومان\n"
        f"🏷️  نام کانفیگ: {name}\n"
        f"👛  موجودی کیف پول: {balance:,} تومان\n\n"
        "👇 روش پرداخت را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 پرداخت کارت به کارت", callback_data="pay_card")],
            [InlineKeyboardButton("👛 پرداخت با کیف پول", callback_data="pay_wallet")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_plans")],
        ])
    )
    return SELECTING_PAYMENT


# ---------------------------------------------------------------------------
# پرداخت کارت به کارت
# ---------------------------------------------------------------------------
async def pay_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan = ALL_PLANS[context.user_data["plan_key"]]
    order_id = db.create_order(
        user_id=update.effective_user.id,
        order_type="purchase_card",
        plan_name=plan["name"],
        amount=plan["price"],
        config_name=context.user_data["config_name"],
    )
    context.user_data["order_id"] = order_id

    await query.edit_message_text(
        "╔══════════════════════╗\n"
        "     💳  اطلاعات پرداخت\n"
        "╚══════════════════════╝\n\n"
        f"💰 مبلغ: {plan['price']:,} تومان\n\n"
        "شماره کارت:\n"
        f"{CARD['number']}\n"
        f"👤 به نام: {CARD['holder']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📸 پس از واریز، عکس رسید را ارسال کنید:",
        reply_markup=back_keyboard("back_plans")
    )
    return WAITING_CARD_RECEIPT


async def receive_card_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ لطفاً عکس رسید را ارسال کنید.")
        return WAITING_CARD_RECEIPT

    order_id = context.user_data.get("order_id")
    order = db.get_order(order_id)
    user = update.effective_user

    msg = await context.bot.send_photo(
        chat_id=ADMIN_GROUP_ID,
        photo=update.message.photo[-1].file_id,
        caption=(
            "🧾 رسید پرداخت جدید (کارت به کارت)\n\n"
            f"👤 کاربر: {user.mention_html()}\n"
            f"🆔 آیدی: {user.id}\n"
            f"📦 پلن: {order['plan_name']}\n"
            f"💰 مبلغ: {order['amount']:,} تومان\n"
            f"🏷️ نام کانفیگ: {order['config_name']}\n\n"
            "✅ برای تایید، روی این پیام ریپلای کرده و متن کانفیگ را ارسال کنید."
        ),
        parse_mode=ParseMode.HTML,
    )
    db.set_order_group_message(order_id, msg.message_id)

    await update.message.reply_text(
        "✅ رسید شما ارسال شد.\nپس از تایید، کانفیگ به همین چت ارسال می‌شود. 🙏",
        reply_markup=main_menu_button_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# پرداخت با کیف پول
# ---------------------------------------------------------------------------
async def pay_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan = ALL_PLANS[context.user_data["plan_key"]]
    user_id = update.effective_user.id
    balance = db.get_wallet_balance(user_id)

    if balance < plan["price"]:
        shortage = plan["price"] - balance
        await query.edit_message_text(
            "⚠️ موجودی کیف پول کافی نیست.\n\n"
            f"👛 موجودی فعلی: {balance:,} تومان\n"
            f"💰 قیمت سرویس: {plan['price']:,} تومان\n"
            f"❗️ کسری: {shortage:,} تومان\n\n"
            "ابتدا کیف پول خود را شارژ کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="topup_start")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_plans")],
            ])
        )
        return SELECTING_PAYMENT

    order_id = db.create_order(
        user_id=user_id,
        order_type="purchase_wallet",
        plan_name=plan["name"],
        amount=plan["price"],
        config_name=context.user_data["config_name"],
    )

    msg = await context.bot.send_message(
        chat_id=ADMIN_GROUP_ID,
        text=(
            "🆕 درخواست خرید با کیف پول\n\n"
            f"👤 کاربر: {update.effective_user.mention_html()}\n"
            f"🆔 آیدی: {user_id}\n"
            f"📦 پلن: {plan['name']}\n"
            f"💰 مبلغ: {plan['price']:,} تومان\n"
            f"🏷️ نام کانفیگ: {context.user_data['config_name']}\n\n"
            "✅ برای تایید، ریپلای کرده و متن کانفیگ را ارسال کنید."
        ),
        parse_mode=ParseMode.HTML,
    )
    db.set_order_group_message(order_id, msg.message_id)

    await query.edit_message_text(
        "✅ درخواست خرید ثبت شد.\nپس از تایید ادمین، کانفیگ ارسال و هزینه از کیف پول کسر می‌شود. 🙏",
        reply_markup=main_menu_button_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# کیف پول و شارژ
# ---------------------------------------------------------------------------
async def wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()

    balance = db.get_wallet_balance(update.effective_user.id)
    await query.edit_message_text(
        f"👛 کیف پول شما\n\n💰 موجودی: {balance:,} تومان",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 افزایش موجودی", callback_data="topup_start")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
        ])
    )
    return WALLET_MENU


async def topup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💰 افزایش موجودی کیف پول\n\nمبلغ را به تومان وارد کنید:\nمثال: 100000",
        reply_markup=back_keyboard("back_main")
    )
    return TYPING_TOPUP_AMOUNT


async def receive_topup_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip().replace(",", "").replace("،", "")
    if not raw.isdigit() or int(raw) <= 0:
        await update.message.reply_text("❌ لطفاً فقط عدد وارد کنید. مثال: 100000")
        return TYPING_TOPUP_AMOUNT

    amount = int(raw)
    context.user_data["topup_amount"] = amount

    await update.message.reply_text(
        "╔══════════════════════╗\n"
        "     💳  اطلاعات پرداخت\n"
        "╚══════════════════════╝\n\n"
        f"💰 مبلغ: {amount:,} تومان\n\n"
        "شماره کارت:\n"
        f"{CARD['number']}\n"
        f"👤 به نام: {CARD['holder']}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📸 پس از واریز، عکس رسید را ارسال کنید:",
        reply_markup=back_keyboard("back_main")
    )
    return WAITING_TOPUP_RECEIPT


async def receive_topup_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ لطفاً عکس رسید را ارسال کنید.")
        return WAITING_TOPUP_RECEIPT

    amount = context.user_data["topup_amount"]
    user = update.effective_user
    order_id = db.create_order(
        user_id=user.id, order_type="topup",
        plan_name=None, amount=amount, config_name=None,
    )

    msg = await context.bot.send_photo(
        chat_id=ADMIN_GROUP_ID,
        photo=update.message.photo[-1].file_id,
        caption=(
            "💰 درخواست شارژ کیف پول\n\n"
            f"👤 کاربر: {user.mention_html()}\n"
            f"🆔 آیدی: {user.id}\n"
            f"💵 مبلغ: {amount:,} تومان\n\n"
            f"✅ برای تایید، ریپلای کرده و عدد {amount} را ارسال کنید."
        ),
        parse_mode=ParseMode.HTML,
    )
    db.set_order_group_message(order_id, msg.message_id)

    await update.message.reply_text(
        "✅ رسید ارسال شد.\nپس از تایید ادمین، کیف پول شارژ می‌شود. 🙏",
        reply_markup=main_menu_button_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# سرویس های من
# ---------------------------------------------------------------------------
async def my_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    services = db.get_user_services(update.effective_user.id)
    if not services:
        text = "📦 سرویس‌های من\n\nشما هنوز هیچ سرویسی خریداری نکرده‌اید."
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
    await query.edit_message_text(
        "💬 پشتیبانی\n\nبرای ارتباط با تیم پشتیبانی روی دکمه زیر بزنید 👇",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👨‍💻 ارتباط با پشتیبانی", url=f"https://t.me/{SUPPORT_USERNAME}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
        ])
    )


# ---------------------------------------------------------------------------
# پردازش ریپلای ادمین در گروه
# ---------------------------------------------------------------------------
async def admin_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or message.chat_id != ADMIN_GROUP_ID or not message.reply_to_message:
        return

    order = db.get_order_by_group_message(message.reply_to_message.message_id)
    if not order:
        return
    if order["status"] != "pending":
        await message.reply_text("⚠️ این سفارش قبلاً پردازش شده است.")
        return

    if order["type"] == "topup":
        amount_text = (message.text or "").strip().replace(",", "")
        if not amount_text.isdigit():
            await message.reply_text("❌ فقط عدد مبلغ را ارسال کنید.")
            return
        amount = int(amount_text)
        db.change_wallet_balance(order["user_id"], amount)
        db.update_order_status(order["id"], "approved")
        new_balance = db.get_wallet_balance(order["user_id"])
        try:
            await context.bot.send_message(
                chat_id=order["user_id"],
                text=(
                    "✅ کیف پول شما شارژ شد.\n\n"
                    f"💵 مبلغ شارژ: {amount:,} تومان\n"
                    f"👛 موجودی جدید: {new_balance:,} تومان"
                )
            )
        except Exception:
            logger.exception("خطا در ارسال پیام به کاربر %s", order["user_id"])
        await message.reply_text("✅ کیف پول کاربر شارژ شد.")

    else:
        config_text = (message.text or "").strip()
        if not config_text:
            await message.reply_text("❌ متن کانفیگ را ریپلای کنید.")
            return
        if order["type"] == "purchase_wallet":
            db.change_wallet_balance(order["user_id"], -order["amount"])
        db.set_order_config(order["id"], config_text)
        db.update_order_status(order["id"], "approved")
        try:
            await context.bot.send_message(
                chat_id=order["user_id"],
                text=(
                    "🎉 پرداخت شما تایید شد!\n\n"
                    f"📦 پلن: {order['plan_name']}\n"
                    f"🏷️ نام کانفیگ: {order['config_name']}\n\n"
                    f"🔗 کانفیگ شما:\n{config_text}\n\n"
                    "از خرید شما متشکریم 🙏"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛒 خرید سرویس جدید", callback_data="buy_service")]
                ])
            )
        except Exception:
            logger.exception("خطا در ارسال کانفیگ به کاربر %s", order["user_id"])
        await message.reply_text("✅ کانفیگ برای کاربر ارسال شد.")


# ---------------------------------------------------------------------------
# راه اندازی
# ---------------------------------------------------------------------------
def main():
    db.init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(show_category, pattern="^buy_service$"),
            CallbackQueryHandler(wallet_menu, pattern="^wallet$"),
        ],
        states={
            SELECTING_CATEGORY: [
                CallbackQueryHandler(select_category, pattern="^cat_eco$|^cat_vip$"),
                CallbackQueryHandler(back_to_main, pattern="^back_main$"),
            ],
            SELECTING_PLAN: [
                CallbackQueryHandler(select_plan, pattern="^plan_"),
                CallbackQueryHandler(back_to_category, pattern="^back_category$"),
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
    application.add_handler(conv)
    application.add_handler(CallbackQueryHandler(my_services, pattern="^my_services$"))
    application.add_handler(CallbackQueryHandler(support, pattern="^support$"))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_main$"))
    application.add_handler(
        MessageHandler(filters.Chat(chat_id=ADMIN_GROUP_ID) & filters.REPLY, admin_reply_handler)
    )

    logger.info("ربات در حال اجرا است...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
