#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sqlite3
from datetime import datetime, timedelta
from functools import wraps

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from woocommerce import API
import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

wcapi = API(
    url=config.WC_URL,
    consumer_key=config.WC_CONSUMER_KEY,
    consumer_secret=config.WC_CONSUMER_SECRET,
    version="wc/v3",
    timeout=30,
)

def init_db():
    conn = sqlite3.connect(config.DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            phone TEXT,
            registered_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in config.ADMINS:
            await update.message.reply_text("⛔ دسترسی به این دستور فقط برای مدیر است.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def get_order_by_id(order_id):
    try:
        order = wcapi.get(f"orders/{order_id}").json()
        if "code" in order:
            return None
        return order
    except Exception as e:
        logger.error(f"خطا در دریافت سفارش {order_id}: {e}")
        return None

def search_orders_by_phone(phone):
    try:
        orders = wcapi.get("orders", params={"search": phone, "per_page": 10}).json()
        if isinstance(orders, dict):
            return []
        return orders
    except Exception as e:
        logger.error(f"خطا در جستجوی تلفن {phone}: {e}")
        return []

def format_order_for_user(order):
    items = "\n".join([
        f"• {item['name']} x{item['quantity']} — {item['total']} ₽"
        for item in order.get("line_items", [])
    ])
    status_map = {
        "pending": "⏳ در انتظار پرداخت",
        "processing": "🔄 در حال پردازش",
        "completed": "✅ تکمیل شده",
        "cancelled": "❌ لغو شده",
        "refunded": "↩️ برگشت داده شده",
    }
    status = status_map.get(order.get("status"), order.get("status"))
    billing = order.get("billing", {})
    return f"""📋 **سفارش #{order.get('id')}**
👤 {billing.get('first_name', '')} {billing.get('last_name', '')}
📞 {billing.get('phone', '—')}
📅 {order.get('date_created', '—')[:10]}

**محصولات:**
{items if items else '—'}

**وضعیت:** {status}
**مبلغ کل:** {order.get('total', '0')} ₽
"""

def get_status_keyboard(order_id, current_status):
    statuses = [
        ("pending", "⏳ در انتظار"),
        ("processing", "🔄 در حال پردازش"),
        ("completed", "✅ تکمیل"),
        ("cancelled", "❌ لغو"),
    ]
    keyboard = []
    row = []
    for key, label in statuses:
        if key != current_status:
            row.append(InlineKeyboardButton(label, callback_data=f"status_{order_id}_{key}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

# ---------- دستورات مدیر ----------
@admin_only
async def today_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        orders = wcapi.get("orders", params={"after": f"{today}T00:00:00", "per_page": 50}).json()
        if not orders:
            await update.message.reply_text(f"📭 امروز ({today}) سفارشی ثبت نشده است.")
            return
        total = sum(float(o.get("total", 0)) for o in orders)
        await update.message.reply_text(
            f"📊 **سفارشات امروز {today}:**\nتعداد: {len(orders)}\nمجموع: {total:.2f} ₽",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"خطا در today_orders: {e}")
        await update.message.reply_text("❌ خطا در دریافت سفارشات.")

@admin_only
async def week_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    try:
        orders = wcapi.get("orders", params={"after": f"{week_ago}T00:00:00", "per_page": 100}).json()
        if not orders:
            await update.message.reply_text(f"📭 در ۷ روز گذشته سفارشی وجود ندارد.")
            return
        total = sum(float(o.get("total", 0)) for o in orders)
        await update.message.reply_text(
            f"📊 **گزارش هفتگی (از {week_ago}):**\nتعداد: {len(orders)}\nمجموع: {total:.2f} ₽",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"خطا در week_orders: {e}")
        await update.message.reply_text("❌ خطا در دریافت گزارش هفتگی.")

@admin_only
async def last_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = 5
    if context.args and context.args[0].isdigit():
        count = min(int(context.args[0]), 20)
    try:
        orders = wcapi.get("orders", params={"per_page": count, "orderby": "date", "order": "desc"}).json()
        if not orders:
            await update.message.reply_text("📭 سفارشی یافت نشد.")
            return
        for order in orders:
            text = format_order_for_user(order)
            kb = get_status_keyboard(order['id'], order['status'])
            await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)
    except Exception as e:
        logger.error(f"خطا در last_orders: {e}")
        await update.message.reply_text("❌ خطا در دریافت سفارشات.")

@admin_only
async def order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("ℹ️ روش استفاده: `/order 123`", parse_mode="Markdown")
        return
    order_id = int(context.args[0])
    order = get_order_by_id(order_id)
    if not order:
        await update.message.reply_text("❌ سفارش یافت نشد.")
        return
    text = format_order_for_user(order)
    kb = get_status_keyboard(order['id'], order['status'])
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

@admin_only
async def search_by_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("ℹ️ روش استفاده: `/search 09123456789`", parse_mode="Markdown")
        return
    phone = " ".join(context.args)
    orders = search_orders_by_phone(phone)
    if not orders:
        await update.message.reply_text(f"❌ سفارشی با شماره {phone} یافت نشد.")
        return
    msg = f"🔍 {len(orders)} سفارش برای {phone}:\n"
    for o in orders:
        msg += f"#{o['id']} - {o['total']} ₽ - {o['status']}\n"
    await update.message.reply_text(msg)

@admin_only
async def update_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text(
            "ℹ️ روش استفاده: `/update 123 completed`\nوضعیت‌ها: pending, processing, completed, cancelled",
            parse_mode="Markdown"
        )
        return
    order_id = int(context.args[0])
    new_status = context.args[1]
    try:
        res = wcapi.put(f"orders/{order_id}", {"status": new_status}).json()
        if "code" in res:
            await update.message.reply_text(f"❌ خطا: {res.get('message')}")
            return
        await update.message.reply_text(f"✅ وضعیت سفارش #{order_id} به {new_status} تغییر کرد.")
    except Exception as e:
        logger.error(f"خطا در update_status: {e}")
        await update.message.reply_text("❌ خطا در ارتباط با API.")

@admin_only
async def monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    try:
        orders = wcapi.get("orders", params={"after": f"{month_ago}T00:00:00", "per_page": 100}).json()
        if not orders:
            await update.message.reply_text("📭 در ۳۰ روز گذشته سفارشی نداشتیم.")
            return
        total = sum(float(o.get("total", 0)) for o in orders)
        await update.message.reply_text(
            f"📈 **گزارش ۳۰ روزه:**\nتعداد سفارش: {len(orders)}\nمجموع فروش: {total:.2f} ₽",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"خطا در monthly_report: {e}")
        await update.message.reply_text("❌ خطا در گزارش.")

# ---------- دستورات کاربر عادی ----------
async def track_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("ℹ️ روش استفاده: `/track 123`", parse_mode="Markdown")
        return
    order_id = int(context.args[0])
    order = get_order_by_id(order_id)
    if not order:
        await update.message.reply_text("❌ سفارش مورد نظر یافت نشد.")
        return
    text = format_order_for_user(order)
    await update.message.reply_text(text, parse_mode="Markdown")

async def my_orders_by_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("ℹ️ روش استفاده: `/myorders 09123456789`", parse_mode="Markdown")
        return
    phone = " ".join(context.args)
    orders = search_orders_by_phone(phone)
    if not orders:
        await update.message.reply_text(f"❌ سفارشی برای شماره {phone} یافت نشد.")
        return
    msg = f"📋 **سفارشات شما ({phone}):**\n"
    for o in orders:
        msg += f"#{o['id']} - {o['total']} ₽ - {o['status']}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in config.ADMINS
    text = """🎫 **به ربات فروشگاه بلیت کنسرت خوش آمدید!**

من به شما کمک می‌کنم سفارشات را پیگیری کنید.
"""
    if is_admin:
        text += """
**دستورات مدیر:**
/today - سفارشات امروز
/week - سفارشات این هفته
/last <تعداد> - آخرین سفارشات
/order <شماره> - جزییات سفارش
/search <تلفن> - جستجوی سفارش با تلفن
/report - گزارش فروش ۳۰ روزه
/update <شماره> <وضعیت> - تغییر وضعیت سفارش
"""
    else:
        text += """
**دستورات مشتری:**
/track <شماره سفارش> - وضعیت سفارش خود را ببینید
/myorders <تلفن> - همه سفارشات خود را با تلفن جستجو کنید
"""
    await update.message.reply_text(text, parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("status_"):
        parts = data.split("_")
        if len(parts) >= 3:
            order_id = int(parts[1])
            new_status = parts[2]
            try:
                wcapi.put(f"orders/{order_id}", {"status": new_status})
                order = get_order_by_id(order_id)
                if order:
                    text = format_order_for_user(order)
                    kb = get_status_keyboard(order['id'], order['status'])
                    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
                    await query.message.reply_text(f"✅ وضعیت سفارش #{order_id} به {new_status} تغییر یافت.")
            except Exception as e:
                logger.error(f"خطا در دکمه: {e}")
                await query.message.reply_text("❌ خطا در تغییر وضعیت.")

def build_application():
    """ساخت اپلیکیشن ربات (بدون شروع polling)"""
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("today", today_orders))
    app.add_handler(CommandHandler("week", week_orders))
    app.add_handler(CommandHandler("last", last_orders))
    app.add_handler(CommandHandler("order", order_detail))
    app.add_handler(CommandHandler("search", search_by_phone))
    app.add_handler(CommandHandler("update", update_status))
    app.add_handler(CommandHandler("report", monthly_report))
    app.add_handler(CommandHandler("track", track_order))
    app.add_handler(CommandHandler("myorders", my_orders_by_phone))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    return app
