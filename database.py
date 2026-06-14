"""
ماژول مدیریت دیتابیس ربات فروشگاهی تلگرام
از SQLite برای ذخیره‌سازی کاربران، کیف پول و سفارش‌ها استفاده می‌شود.
"""

import os
import sqlite3
from contextlib import closing
from datetime import datetime

# مسیر فایل دیتابیس - در صورت نیاز می‌توانید با متغیر محیطی DB_PATH تغییرش بدید
DB_PATH = os.environ.get("DB_PATH", "bot_database.db")


def init_db():
    """ساخت جدول‌های دیتابیس در صورت عدم وجود"""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                wallet_balance INTEGER NOT NULL DEFAULT 0,
                created_at TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,           -- 'purchase_card' | 'purchase_wallet' | 'topup'
                plan_name TEXT,
                amount INTEGER NOT NULL,
                config_name TEXT,
                config_text TEXT,
                status TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected'
                group_message_id INTEGER,
                created_at TEXT
            )
        """)

        conn.commit()


# ---------------------------------------------------------------------------
# کاربران و کیف پول
# ---------------------------------------------------------------------------

def get_or_create_user(user_id: int, username: str | None):
    """در صورت عدم وجود کاربر، ایجادش می‌کند و در هر صورت اطلاعاتش را برمی‌گرداند"""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id, username, wallet_balance FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row is None:
            cur.execute(
                "INSERT INTO users (user_id, username, wallet_balance, created_at) VALUES (?, ?, 0, ?)",
                (user_id, username, datetime.utcnow().isoformat()),
            )
            conn.commit()
            return {"user_id": user_id, "username": username, "wallet_balance": 0}

        # آپدیت یوزرنیم در صورت تغییر
        if username and row[1] != username:
            cur.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
            conn.commit()

        return {"user_id": row[0], "username": row[1], "wallet_balance": row[2]}


def get_wallet_balance(user_id: int) -> int:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("SELECT wallet_balance FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        return row[0] if row else 0


def change_wallet_balance(user_id: int, delta: int):
    """مقدار delta را به موجودی کیف پول کاربر اضافه می‌کند (می‌تواند منفی باشد)"""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET wallet_balance = wallet_balance + ? WHERE user_id = ?",
            (delta, user_id),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# سفارش‌ها (خریدها و شارژ کیف پول)
# ---------------------------------------------------------------------------

def create_order(user_id: int, order_type: str, plan_name: str | None,
                  amount: int, config_name: str | None) -> int:
    """ساخت یک سفارش جدید و برگرداندن شناسه آن"""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO orders (user_id, type, plan_name, amount, config_name, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (user_id, order_type, plan_name, amount, config_name, datetime.utcnow().isoformat()),
        )
        conn.commit()
        return cur.lastrowid


def set_order_group_message(order_id: int, message_id: int):
    """ذخیره شناسه پیامی که در گروه ادمین برای این سفارش ارسال شده"""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE orders SET group_message_id = ? WHERE id = ?", (message_id, order_id))
        conn.commit()


def get_order(order_id: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_order_by_group_message(message_id: int):
    """پیدا کردن سفارش بر اساس شناسه پیام ریپلای‌شده در گروه ادمین"""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM orders WHERE group_message_id = ?", (message_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_order_status(order_id: int, status: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        conn.commit()


def set_order_config(order_id: int, config_text: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE orders SET config_text = ? WHERE id = ?", (config_text, order_id))
        conn.commit()


def get_user_services(user_id: int):
    """لیست سرویس‌های تاییدشده (خریداری‌شده) یک کاربر"""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            """
            SELECT * FROM orders
            WHERE user_id = ?
              AND type IN ('purchase_card', 'purchase_wallet')
              AND status = 'approved'
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        return [dict(row) for row in cur.fetchall()]
