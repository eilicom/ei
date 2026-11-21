# -*- coding: utf-8 -*-
"""
YANGZI BOT 👽  —  ربات شبیه‌ساز زندگی و اقتصاد (یک فایل، aiogram 3 + aiosqlite)

نصب:      pip install aiogram aiosqlite
اجرا:      BOT_TOKEN=123:ABC ADMIN_IDS=111,222 python bot.py
متغیرها:   BOT_TOKEN | ADMIN_IDS (آیدی عددی ادمین‌ها، با کاما) | DB_PATH (پیش‌فرض yangzi.db)
           FORCE_CHANNEL (کانال جوین اجباری، پیش‌فرض @Swag_Farsi)

نکته ۱: برای کار کردن دستورهای بدون ریپلی در گروه، Privacy Mode ربات را در BotFather خاموش کن
(BotFather ← /mybots ← Bot Settings ← Group Privacy ← Turn off) یا ربات را ادمین گروه کن.
نکته ۲: برای جوین اجباری، ربات باید ادمین کانال باشد.

پنل مدیریت: در چت خصوصی بنویس «پنل مدیریت» یا /admin
(اگر ADMIN_IDS خالی باشد، اولین کسی که /admin بزند ادمین می‌شود).
"""
import asyncio
import html
import json
import logging
import math
import os
import random
import re
import string
import time
from contextlib import asynccontextmanager

import aiosqlite
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.types import (CallbackQuery, ChatMemberUpdated, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("yangzi")

BOT_TOKEN = os.getenv("BOT_TOKEN", "9197926027:AAGJEvRfGm1Skzx35rw4hpSAh5JIWhnFvHQ")
DB_PATH = os.getenv("DB_PATH", "yangzi.db")
ENV_ADMINS = {int(x) for x in re.findall(r"\d+", os.getenv("ADMIN_IDS", "7949818604"))}
FORCE_CHANNEL = os.getenv("FORCE_CHANNEL", "@Swag_Farsi")
BOT_USERNAME = "YangziBot"
MAX_MONEY = 10 ** 15

# ════════════════════════════════════════════════════════════════════════════
#  متن‌ها و دکمه‌ها (همه از پنل مدیریت قابل تغییرند)
# ════════════════════════════════════════════════════════════════════════════
DEFAULTS: dict = {}


def _d(key, label, default):
    DEFAULTS[key] = (label, default)


# ---- متن‌ها
_d("t_menu", "عنوان منوی اصلی", "منوی اصلی یانگزی پسرعمو 👽:")
_d("t_added", "پیام اد شدن ربات به گروه", "اد شدم پسرعمو 👽\nبنویس منو")
_d("t_force_join", "جوین اجباری (پیوی)",
   "پسرعمو برای استفاده از ربات اول باید تو کانال ما عضو بشی 📢\n\nبعد از عضویت روی «عضو شدم» بزن ✅")
_d("t_force_fail", "هنوز عضو نیست", "هنوز تو کانال عضو نشدی پسرعمو ❌")
_d("t_bank", "متن بانک ({cash} {bank} {rate})",
   "بانک مرکزی زی کوین 🏦:\n\nکیف پولت: {cash} زی کوین\nسپرده بانک: {bank} زی کوین\n\n"
   "روزانه {rate}٪ سود خودکار میشینه به حسابت پسرعمو 💯")
_d("t_props", "متن بخش املاک ({ready} {max})",
   "بخش کسب درآمد و املاک 🏠:\n\nسود آماده برداشت (لحظه‌ای)، {ready} زی کوین\n\n"
   "از هر ملک تا {max} تا میتونی بخری. یکی رو انتخاب کن پسرعمو:")
_d("t_prop_confirm", "تأیید خرید ملک ({label} {price} {income} {period} {qty} {max})",
   "{label}\n\nقیمت: {price} زی کوین\nسود هر {period}: {income} زی کوین (لحظه‌ای حساب میشه)\n"
   "تعداد فعلی: {qty} از {max}\n\nمیخوای بخری پسرعمو؟")
_d("t_shop", "عنوان فروشگاه", "فروشگاه مرکزی 🛒:")
_d("t_shop_cat", "عنوان دسته فروشگاه ({cat})", "{cat}:\n\nیکی رو انتخاب کن پسرعمو:")
_d("t_shop_empty", "دسته خالی", "هنوز محصولی اینجا نیست پسرعمو 🚧")
_d("t_daf_menu", "عنوان بخش داف‌ها", "بخش داف ها 💃\n(هر داف رو فقط یکی میشه اجاره کرد)")
_d("t_condom_menu", "عنوان منوی کاندوم", "خرید کاندوم 🛒")
_d("t_toy_menu", "عنوان اسباب بازی", "اسباب بازی جنسی")
_d("t_item_confirm", "تأیید خرید ({name} {price} {cash})",
   "{name}\n\nقیمت: {price} زی کوین\nپول نقدت: {cash} زی کوین\n\nمطمئنی میخوای بخری پسرعمو؟")
_d("t_daf_confirm", "تأیید اجاره داف ({name} {price} {cash} {hours})",
   "{name} 💃\n\nقیمت اجاره: {price} زی کوین\nمدت استفاده: {hours} ساعت\nپول نقدت: {cash} زی کوین\n\n"
   "میخوای اجاره‌ش کنی پسرعمو؟")
_d("t_daf_rented", "اجاره داف ({name} {hours})", "✅ {name} رو برات اجاره کردم پسرعمو، {hours} ساعت مال توئه 💃🔥")
_d("t_daf_have", "داف تکراری ({name} {left})", "{name} رو از قبل اجاره کردی پسرعمو، {left} دیگه وقت داره 💃")
_d("t_stash_have", "مشروب/مخدر فعال ({name} {left} {uses})",
   "هنوز {name} داری پسرعمو ✅\n{left} دیگه اعتبار داره و {uses} بار مصرف مونده. بعد از تموم شدن دوباره بخرش.")
_d("t_stash_have2", "محافظ/رت فعال ({name} {left})", "{name} هنوز فعاله پسرعمو ✅ {left} دیگه اعتبار داره.")
_d("t_inv", "عنوان انبار", "انبار و اوراقی 📦:\nآیتم‌هات و وسایلت رو می‌تونی ببینی و بفروشی پسرعمو 💸")
_d("t_inv_empty", "انبار خالی", "انبارت خالیه پسرعمو 📦")
_d("t_sell_confirm", "تأیید فروش آیتم ({name} {price})",
   "فروش {name}\n\nقیمت فروش: {price} زی کوین\n\nمطمئنی پسرعمو؟")
_d("t_kid_sell_confirm", "تأیید فروش بچه ({name} {price})",
   "فروش بچه {name} 👶\n\nقیمت فروش: {price} زی کوین\n\nمطمئنی میخوای بفروشیش پسرعمو؟")
_d("t_kids_title", "عنوان بچه‌ها", "بچه‌های پسرعمو 👶")
_d("t_no_kids", "بدون بچه", "هنوز بچه‌ای نداری پسرعمو 👶")
_d("t_profile", "قالب پروفایل",
   "پروفایل {link} 👽\n\nپول نقد: {cash} زی کوین\n\nبانک: {bank} زی کوین\n\nترید: {trade} زی کوین\n\n"
   "کل سرمایه: {total} زی کوین 💯\n\nسطح: {level_title} (سطح {level}) {level_emoji}\n\n"
   "مخدرها و مشروبات:\n{drugs}\n\nاملاک:\n{props}\n\nموتور:\n{motos}\n\nماشین:\n{cars}\n\n"
   "وسایل و داف:\n{stuff}\n\nبرادر: {brother}\n\n"
   "بچه‌ها:\nتعداد بچه‌ها: {kids} عدد")
_d("t_help", "راهنما (منوی اصلی راهنما)", "📖 راهنمای یانگزی 👽\n\nپسرعمو کدوم بخش رو میخوای بدونی؟ یکی رو بزن 👇")
_d("t_help_daf", "راهنما: داف",
   "💃 داف\n\nاز فروشگاه > داف، داف اجاره میکنی پسرعمو. از هر داف فقط یدونه میشه گرفت، مدتش که تموم شد باید دوباره اجاره کنی.\n"
   "بعدش بنویس سکس • ساک • تریسام • فورسام • فایوسام (هرچی داف بیشتر پول بیشتر 💰) تا زی کوین بریزه تو جیبت.\n"
   "هرکدوم یه استراحت داره، زود زود نکن کصخل، دافت خسته میشه 💤\n"
   "یه وقتایی هم دافت حامله میشه، یا نگه میداری یا سقط 😈\n"
   "کاندوم و اسباب بازی هم ته همون منوی داف ها هست 🎈")
_d("t_help_mavad", "راهنما: مواد",
   "💊 مواد\n\nنوشیدنی و مشروبات و مخدرها (تریاک، لین، گل، ماشروم و...) رو از فروشگاه میخری، بعد اسمشو تو چت مینویسی "
   "(مثلا: ودکا یا تریاک) تا مصرف شه و سود بریزه 💰\n"
   "هر خرید 10 بار مصرف داره و یه مدت اعتبار، تموم شد دوباره بخرش.\n"
   "مخدرها رو هر نیم ساعت فقط یبار میشه زد، زیادی بکشی میخوری تو سرت پسرعمو 😵‍💫 صبر کن بعد بزن.\n"
   "از انبار > مخدرها و مشروبات هم میتونی مصرفشون کنی 📦")
_d("t_help_rat", "راهنما: رت",
   "🐀 رت\n\nرت همون مخبره پسرعمو. از فروشگاه > رت میخریش و تا وقتی فعاله، هرکی بخواد ازت دزدی کنه پلیس خفتش میکنه و جریمه میشه 🚓\n"
   "یعنی دزده جیبشو میکنی تو کونش و تو راحت میخوابی 😎 فقط اعتبارش تموم نشه.")
_d("t_help_bala", "راهنما: بالاخواه",
   "🛡 بالاخواه\n\nبالاخواه رو از مواد بالاخواه تو فروشگاه میخری. تا وقتی فعاله هرکی بیاد روت مفتبری کنه، بالاخواهت خفتش میکنه و ازش جریمه میگیره 😈\n"
   "نداشته باشی هرکی دلش بخواد میزنه تو سرت و پولتو میبره، پس بخرش پسرعمو 🔥")
_d("t_use_cd", "محدودیت مصرف مخدر ({name} {n})",
   "{name} رو تازه زدی پسرعمو 😵‍💫\n{n} دقیقه دیگه صبر کن تا دوباره بتونی بزنی 💤")
_d("t_mission", "میشن", "میشن‌ها فعلاً غیرفعال هستند.")
_d("t_trade_menu", "منوی ترید",
   "ترید 📈\n\nترید سریع: بنویس «ترید 1000» (هر مبلغی که پول نقد داری)\nترید بلندمدت: فعلاً غیرفعال است.")
_d("t_trade_long", "ترید بلندمدت", "ترید بلندمدت فعلاً غیرفعال است 🔒")
_d("t_not_yours", "منوی کس دیگه", "این منو مال تو نیست پسرعمو 👽")
_d("t_no_cash", "نبود موجودی ({cash})", "پول نقدت به این مبلغ نمی‌رسه پسرعمو 💸\nموجودی نقد: {cash}")
_d("t_ashkra", "اشکرع ({reward})", "اشکرع گفتی و {reward} زی کوین گرفتی پسرعمو 💯 دسخوش")
_d("t_hasbi", "حسبی الله ({reward})", "حسبی الله گفتی پسرعمو 🤲\n{reward} زی کوین نشست به حسابت، اشکرع 💯")
_d("t_bad", "داف من بدکارست ({reward})",
   "پسرعمو دافت حسابی برات کار کرد و {reward} زی کوین درآمد داشت 💃💰 اشکرع")
_d("t_sex", "سکس ({reward} {cd} {daf})",
   "{daf} رو گاییدی و {reward} زی کوین گرفتی پسرعمو 😈🔥\n{cd} دقیقه دیگه صبر کن تا دوباره شارژ شه 💤 اشکرع")
_d("t_tri", "تریسام ({reward} {cd} {daf})",
   "پسرعمو دسخوش دو تا دافتو باهم استفاده کردی 👥\n{reward} زی کوین گرفتی\n"
   "{cd} دقیقه دیگه دوباره میتونی تریسام بزنی 😈")
_d("t_four", "فورسام ({reward} {cd} {daf})",
   "پسرعمو سه تا دافتو باهم بردی بالا 🔥👥\n{reward} زی کوین گرفتی دسخوش 💯\n"
   "{cd} دقیقه دیگه دوباره میتونی فورسام بزنی 😈")
_d("t_five", "فایوسام ({reward} {cd} {daf})",
   "پسرعمو چهارتا دافتو با هم ترکوندی 🔥🔥👥\n{reward} زی کوین گرفتی دسخوش 💯\n"
   "{cd} دقیقه دیگه دوباره میتونی فایوسام بزنی 😈")
_d("t_sak", "ساک ({reward} {cd})",
   "پسرعمو دافت برات یه ساک مشتی و پر تف زد 😈💦\n{reward} زی کوین گرفتی دسخوش 💯")
_d("t_cd_simple", "کولداون عمومی ({n} {cmd})", "صبر کن، {n} دقیقه دیگه مونده تا بتونی دوباره {cmd} بگی 💤")
_d("t_cd_sex", "کولداون سکس ({n})", "پسرعمو دافات هنوز خسته‌ان، {n} دقیقه دیگه برای استفاده دوباره صبر کن 💤")
_d("t_cd_tri", "کولداون تریسام ({n})",
   "پسرعمو مراقب باش توعون کس دافاتو ندی 🤲\nفعلا {n} دقیقه وایسا وگرنه کسشون جز میخوره انقدر که میکنی 🤒")
_d("t_cd_multi", "کولداون فورسام/فایوسام ({n} {cmd})",
   "پسرعمو دافات هنوز خسته‌ان، {n} دقیقه دیگه برای {cmd} صبر کن 💤")
_d("t_cd_sak", "کولداون ساک ({n})", "پسرعمو دافت خسته‌ست، {n} دقیقه دیگه صبر کن 💤")
_d("t_no_daf_sex", "نداشتن داف (سکس)", "اول باید از فروشگاه داف اجاره کنی پسرعمو")
_d("t_no_daf_tri", "نداشتن دو داف (تریسام)", "داف کافی نداری کصخل")
_d("t_no_daf_multi", "نداشتن داف کافی (فورسام/فایوسام) ({need} {cmd})",
   "برای {cmd} باید حداقل {need} تا داف اجاره‌ای فعال داشته باشی پسرعمو")
_d("t_no_daf_sak", "نداشتن داف (ساک)", "اول باید داف اجاره کنی کسخل")
_d("t_gamble_win", "برد قمار ({bet} {cash})",
   "قمارت گرفت و بردی پسرعمو! {bet} زی کوین اضافه شد دسخوش 💯\n\nموجودی جدید: {cash}")
_d("t_gamble_lose", "باخت قمار ({bet} {cash})",
   "شانست رید و {bet} زی کوینت بگا رفت توعون دادی 💀\n\nموجودی جدید: {cash}")
_d("t_trade_win", "سود ترید ({amount} {pct} {cash})",
   "ترید سریع زدی پسرعمو 📈\n\n{amount} زی کوین سود کردی ({pct}٪) اشکرع 💯\n\nموجودی جدید: {cash}")
_d("t_trade_lose", "ضرر ترید ({amount} {pct} {cash})",
   "ترید سریع زدی 📉\n\n{amount} زی کوین ضرر کردی ({pct}٪) توعون دادی 💀\n\nموجودی جدید: {cash}")
_d("t_preg", "بارداری ({n})", "پسرعمو دافت {n} حامله‌ست، بچه‌ها رو نگه می‌داری یا سقط می‌کنی؟")
_d("t_orphan", "یتیم‌خونه", "پسرعمو بچه‌هات 50 تاست، تو خونه جا نداشتیم فرستادیمشون یتیم‌خونه 👶")
_d("t_keep_done", "نگه داشتن ({k})", "✅ {k} تا بچه نگه داشتی پسرعمو 👶")
_d("t_abort_done", "سقط", "🚫 بارداری سقط شد پسرعمو، هیچ بچه‌ای به دارایی‌هات اضافه نشد.")
_d("t_name_prompt", "پیشنهاد اسم ({n})", "پسرعمو برای بچه شماره {n} می‌تونی اسم انتخاب کنی.")
_d("t_name_usage", "راهنمای اسم‌گذاری", "برای اسم‌گذاری بنویس:\nاسم بچه 1 علی")
_d("t_unpriced", "قیمت‌گذاری نشده", "هنوز قیمت‌گذاری نشده 🚫")

# ---- مفتبری / دزدی / برادری / فیت
_d("t_crime_noreply", "بدون ریپلی ({what})", "برای {what} باید روی پیام طرف ریپلی کنی پسرعمو 😈")
_d("t_crime_self", "ریپلی به خود ({what})", "رو خودت که نمیشه {what} کرد پسرعمو 🤦‍♂️")
_d("t_crime_bro", "ریپلی به برادر", "با برادرت که کاری نداری پسرعمو 🤝")
_d("t_crime_empty", "طرف پول نقد ندارد ({what})", "پسرعمو این بدبخت چیزی برای {what} نداره💤")
_d("t_mofte_ok", "موفقیت مفتبری ({a} {v} {n})",
   "پسرعمو {a} زد تو سر {v} و {n} زی کوین بالا کشید.! 😈🔥 دسخوش")
_d("t_mofte_bro", "موفقیت مفتبری با برادر ({a} {b} {v} {n})",
   "پسرعمو {a} به همراه داداشش {b} ریختن رو سر {v} و {n} زی کوین ازش بالاکشیدن! 😈🔥 دسخوش")
_d("t_mofte_guard", "مفتبری روی بالاخواه‌دار ({n})",
   "طرف بالاخواه داشت 🛡!\nبالاخواه خفتت کرد و 5 ٪ پولت ({n} زی) به عنوان توعون رفت تو جیبش")
_d("t_mofte_cd", "کولداون مفتبری ({n})", "هنوز درگیر توعون مفتبری قبلی هستی، {n} دقیقه دیگه صبر کن 💤")
_d("t_dozd_ok", "موفقیت دزدی ({v} {n})", "{n} زی کوین از {v} کش رفتی پسرعمو 😈\nمراقب توعونش باش 💣")
_d("t_dozd_rat", "دزدی روی رت‌دار ({n})", "طرف 'رت' داشت! پلیس خفتت کرد و {n} زی کوین جریمه توعون دادی 🐀🚓")
_d("t_dozd_cd", "کولداون دزدی ({n})", "هنوز درگیر توعون دزدی قبلی هستی، {n} دقیقه دیگه صبر کن 💤")
_d("t_bro_ok", "صیغه برادری موفق ({a} {b})",
   "پسرعمو {a} با {b} صیغه برادری خوندن 🤝\nمبارکتون باشه دسخوش 💯")
_d("t_bro_target_has", "طرف برادر دارد", "طرف خودش برادر داره، نمیشه باهاش صیغه خوند! ⚠️")
_d("t_bro_self_has", "خودت برادر داری", "کسخل تو خودت از قبل برادر داری نمیتونی صیغه برادری بخونی!")
_d("t_bro_noreply", "صیغه بدون ریپلی", "برای صیغه برادری باید روی پیام طرف ریپلی کنی پسرعمو 🤝")
_d("t_bro_broken", "شکستن صیغه ({a} {b})", "💔 صیغه برادری {a} و {b} شکسته شد.")
_d("t_fit_ok", "فیت موفق ({a} {b} {n})",
   "پسرعمو {a} و داداشش {b} فیت زدن و هر کدوم {n} زی کوین گرفتن 🤝🔥 دسخوش")
_d("t_fit_fail", "فیت ناموفق", "فیتتون نگرفت پسرعمو، دست خالی برگشتین 😐")
_d("t_fit_cd", "کولداون فیت ({n})", "برادرا هنوز خسته‌ان، {n} دقیقه دیگه برای فیت صبر کنین 💤")
_d("t_fit_nobro", "فیت بدون برادر", "برادر نداری پسرعمو، اول صیغه برادری بخون 🤝")
_d("t_fit_private", "فیت در پیوی", "فیت فقط تو گروه کار میکنه پسرعمو 😎")

# ---- مشروب و مخدر
_d("t_use_ok", "مصرف موفق ({name} {n} {left})",
   "{emoji} {name} رو زدی پسرعمو 😎\n{n} زی کوین سود کردی 💰\n{left} بار مصرف دیگه مونده")
_d("t_use_none", "مصرف بدون موجودی ({name})", "{name} نداری یا تموم/منقضی شده پسرعمو، از فروشگاه بخرش 🛒")
_d("t_od_warn", "هشدار اوردوز ({name})",
   "⚠️ هشدار اوردوز!\n\nپسرعمو تازه مشروب زدی، روش {name} بزنی ممکنه اوردوز کنی و توعون سنگین بدی 💀\n\nمطمئنی؟")
_d("t_od_dead", "اوردوز شد ({n})", "اوردوز کردی پسرعمو 💀🚑\n{n} زی کوین توعون دادی")
_d("t_od_ok", "اوردوز نشد ({name} {n} {left})",
   "{name} رو زدی و اوردوز نکردی، شانس آوردی 😮‍💨\n{n} زی کوین سود کردی 💰\n{left} بار مصرف دیگه مونده")
_d("t_od_cancel", "انصراف از اوردوز", "آفرین پسرعمو، عاقل شدی 🤲 نزدی.")

# ---- کد هدیه
_d("t_gift_ok", "کد هدیه موفق ({n})", "🎁 کد هدیه ثبت شد! {n} زی کوین به حسابت اضافه شد پسرعمو 💯")
_d("t_gift_bad", "کد هدیه نامعتبر", "این کد هدیه وجود نداره پسرعمو ❌")
_d("t_gift_exp", "کد هدیه منقضی", "این کد هدیه منقضی شده ⌛")
_d("t_gift_full", "کد هدیه پر", "ظرفیت این کد هدیه پر شده 🚫")
_d("t_gift_used", "کد هدیه تکراری", "این کد رو قبلاً استفاده کردی پسرعمو ✋")

# ---- موتور و ماشین
VEH = {
    "moto": {"name": "موتور", "emoji": "🏍", "ok": 85, "pen": 600},
    "car": {"name": "ماشین", "emoji": "🚗", "ok": 86, "pen": 700},
}
ACTS = {"tak": "تک‌چرخ", "lai": "لایی", "drift": "دریفت"}
_d("t_veh_none", "وسیله ندارد ({veh})", "{veh} نداری پسرعمو، اول از فروشگاه بخر 🛒")
_d("t_no_license", "بدون گواهینامه", "اول باید گواهینامه بخری پسرعمو 🪪 بی‌گواهینامه نمیشه ماشین خرید!")
_d("t_have_veh", "وسیله دارد ({veh})", "اول {veh} فعلیتو بفروش پسرعمو، بعد یکی دیگه بخر 🔁")
_d("t_moto_ok", "تک‌چرخ موفق ({name} {reward})",
   "پسرعمو با {name} تک‌چرخ زدی و کل خیابونو ترکوندی 🏍🔥\n{reward} زی کوین نشست به حسابت دسخوش 💯")
_d("t_moto_fail", "تک‌چرخ ناموفق ({name} {pen})", "خوردی زمین پسرعمو، {pen} زی کوین توعون دادی 💀")
_d("t_moto_svc_need", "موتور سرویس می‌خواد ({name} {cost})",
   "پسرعمو، موتورت بعد از تک‌چرخ قبلی سرویس می‌خواد. اول با {cost} زی کوین سرویسش کن بعد دوباره تک‌چرخ بزن 🛠")
_d("t_moto_cool", "محدودیت تک‌چرخ ({n})",
   "هنوز {n} دقیقه مونده تا موتورت خنک شه! داری کیر میکنی تو ناموسش  ⚠️")
_d("t_moto_svc_done", "سرویس موتور ({name} {cost})",
   "موتورت با هزینه کل {cost} زی کوین سرویس شد و مثل ساعت کار میکنه پسرعمو 🛠🔥 دسخوش")
_d("t_moto_sell_confirm", "تأیید فروش موتور ({name} {paid} {price} {loss})",
   "فروش {name} 🏍\n\nقیمت خرید: {paid} زی کوین\nقیمت فروش ({loss}٪ ضرر): {price} زی کوین\n\nمطمئنی میخوای بفروشیش پسرعمو؟")
_d("t_moto_sold", "موتور فروخته شد ({name} {price})", "💵 موتورت ({name}) فروخته شد پسرعمو! {price} زی کوین نشست به حسابت")
_d("t_car_ok", "لایی/دریفت موفق ({name} {reward} {act})",
   "پسرعمو با {name} {act} کشیدی و خیابونو به آتیش کشیدی 🏎🔥\n{reward} زی کوین نشست به حسابت دسخوش 💯")
_d("t_car_fail", "لایی/دریفت ناموفق ({name} {pen} {act})",
   "ای کسشر، {act} کشیدی ولی {name} رو کوبیدی به جدول و خودتم کردی تو فکتو 🤡💥\n{pen} زی کوین توعون دادی")
_d("t_car_svc_need", "ماشین سرویس می‌خواد ({name} {cost})",
   "پسرعمو، ماشینت بعد از لایی/دریفت قبلی سرویس می‌خواد. اول با {cost} زی کوین سرویسش کن بعد دوباره بزن 🛠")
_d("t_car_cool", "محدودیت لایی/دریفت ({n})",
   "هنوز {n} دقیقه مونده تا ماشینت خنک شه! داری کیر میکنی تو ناموسش  ⚠️")
_d("t_car_svc_done", "سرویس ماشین ({name} {cost})",
   "ماشینت با هزینه کل {cost} زی کوین سرویس شد و مثل ساعت کار میکنه پسرعمو 🛠🔥 دسخوش")
_d("t_car_sell_confirm", "تأیید فروش ماشین ({name} {paid} {price} {loss})",
   "فروش {name} 🚗\n\nقیمت خرید: {paid} زی کوین\nقیمت فروش ({loss}٪ ضرر): {price} زی کوین\n\nمطمئنی میخوای بفروشیش پسرعمو؟")
_d("t_car_sold", "ماشین فروخته شد ({name} {price})", "💵 ماشینت ({name}) فروخته شد پسرعمو! {price} زی کوین نشست به حسابت")

# ---- نام سطح‌ها (بر اساس پول نقد)
for _i, _t in enumerate(["پسرعمو", "کفخواب", "بچه زیرنگ", "eظVe", "کاسب", "خلافکار", "تبهکار", "کارباز اصلی"], 1):
    _d(f"t_lvl_{_i}", f"نام سطح {_i}", _t)
LEVEL_EMOJI = {1: "🙂", 2: "😴", 3: "🦊", 4: "😎", 5: "😈", 6: "🔪", 7: "💀", 8: "👑"}

# ---- دکمه‌ها
_d("b_shop", "دکمه فروشگاه", "فروشگاه 🛒")
_d("b_profile", "دکمه پروفایل", "پروفایل 👽")
_d("b_props", "دکمه ملک", "ملک 🏠")
_d("b_bank", "دکمه بانک", "بانک 🏦")
_d("b_inv", "دکمه انبار", "انبار و فروش 📦")
_d("b_trade", "دکمه ترید", "ترید 📈")
_d("b_help", "دکمه راهنما", "راهنما 📖")
_d("b_mission", "دکمه میشن", "میشن 🎯")
_d("b_addgroup", "دکمه افزودن به گروه", "افزودن به گروه ➕")
_d("b_back", "بازگشت به منو", "بازگشت به منو 🔙")
_d("b_back_shop_menu", "بازگشت به منوی فروشگاه", "بازگشت به منوی فروشگاه 🛒")
_d("b_back_store", "بازگشت به فروشگاه", "بازگشت به فروشگاه 🔙")
_d("b_back_prev", "بازگشت به قبل", "بازگشت به قبل ↩️")
_d("b_back_veh", "بازگشت (موتور/ماشین)", "بازگشت 🔙")
_d("b_buy", "تأیید خرید", "تأیید خرید ✅")
_d("b_cancel", "انصراف", "انصراف ❌")
_d("b_help_daf", "دکمه راهنما: داف", "داف 💃")
_d("b_help_mavad", "دکمه راهنما: مواد", "مواد 💊")
_d("b_help_rat", "دکمه راهنما: رت", "رت 🐀")
_d("b_help_bala", "دکمه راهنما: بالاخواه", "بالاخواه 🛡")
_d("b_help_back", "دکمه راهنما: برگشت", "برگشت 🔙")
_d("b_sell_ok", "تأیید فروش", "تأیید فروش ✅")
_d("b_collect", "برداشت درآمد", "برداشت درآمد 💰")
_d("b_refresh", "بروزرسانی", "بروزرسانی سود 🔄")
_d("b_keep", "نگه داشتن بچه‌ها", "نگه داشتن بچه‌ها 👶")
_d("b_abort", "سقط جنین", "سقط جنین 🚫")
_d("b_condom", "خرید کاندوم", "🛒 خرید کاندوم")
_d("b_toy", "اسباب بازی جنسی", "اسباب بازی جنسی 🧸")
_d("b_withdraw", "برداشت درصدی ({p})", "📤 برداشت {p} درصد")
_d("b_deposit", "سپرده درصدی ({p})", "📥 سپرده {p} درصد")
_d("b_long_trade", "ترید بلندمدت", "ترید بلندمدت 🔒")
_d("b_inv_drug", "انبار: مخدرها ({n})", "مخدرها و مشروبات ({n}) 💊")
_d("b_inv_daf", "انبار: داف‌ها ({n})", "داف‌ها ({n}) 💃")
_d("b_inv_gear", "انبار: وسایل جانبی ({n})", "وسایل جانبی ({n}) 🛡️")
_d("b_inv_kids", "انبار: بچه‌ها ({n})", "بچه‌ها ({n}) 👶")
_d("b_inv_props", "انبار: املاک ({n})", "املاک ({n}) 🏠")
_d("b_inv_moto", "انبار: موتور و ماشین ({n})", "موتور و ماشین ({n}) 🏍️")
_d("b_join", "دکمه عضویت کانال", "📢 عضویت در کانال")
_d("b_joined", "دکمه عضو شدم", "✅ عضو شدم")
_d("b_bro_break", "شکستن صیغه برادری", "شکستن صیغه برادری 💔")
_d("b_od_go", "اوردوز: به هرحال بزن", "💀 به هرحال بزن")
_d("b_od_no", "اوردوز: نه نزن", "🚫 نه نزن")
_d("b_force", "تکراری: به هرحال بزن", "به هرحال بزن 😈")
_d("b_moto_sell", "فروش موتور", "فروش موتور 💵")
_d("b_moto_svc", "سرویس موتور", "سرویس موتور 🛠")
_d("b_car_sell", "فروش ماشین", "فروش ماشین 💵")
_d("b_car_svc", "سرویس ماشین", "سرویس ماشین 🛠")
SHOP_CATS = [
    ("drink", "نوشیدنی و مشروبات 🥃"), ("narc", "مخدر ها 💊"), ("drug", "مواد بالاخواه 🛡"), ("daf", "داف 💃"),
    ("rat", "رت (مخبر) 🐀"), ("car", "ماشین و تیونینگ 🚗"), ("moto", "موتور و پیست 🏍"), ("gun", "GUN 🔫"),
    ("gear", "تجهیزات و آرنا 🎽"),
]
for _k, _l in SHOP_CATS:
    _d("c_" + _k, "دسته فروشگاه: " + _l, _l)
HIDDEN_CATS = [("condom", "کاندوم 🎈"), ("toy", "اسباب بازی جنسی 🧸")]
ALL_CATS = dict(SHOP_CATS + HIDDEN_CATS)
GEAR_CATS = ("gun", "gear", "toy")
CAT_GROUP = {"daf": "daf", "drug": "drug", "drink": "drug", "narc": "drug", "rat": "drug", "moto": "moto", "car": "moto",
             "condom": "gear", "gun": "gear", "gear": "gear", "toy": "gear"}

# ════════════════════════════════════════════════════════════════════════════
#  تنظیمات عددی (از پنل مدیریت قابل تغییر)
# ════════════════════════════════════════════════════════════════════════════
NUMS: dict = {}


def _n(key, label, default):
    NUMS[key] = (label, default)


_n("bank_rate", "درصد سود روزانه بانک", 5)
_n("start_cash", "پول اولیه کاربر جدید", 0)
_n("prop_period_minutes", "دوره سود املاک (دقیقه) — پیش‌فرض ۳ ساعت (سود لحظه‌ای حساب میشه)", 180)
_n("prop_max", "حداکثر خرید از هر ملک", 10)
_n("preg_chance", "احتمال بارداری (درصد)", 45)
_n("preg_w1", "وزن یک‌قلو", 40)
_n("preg_w2", "وزن دوقلو", 25)
_n("preg_w3", "وزن سه‌قلو", 20)
_n("preg_w4", "وزن چهارقلو", 15)
_n("max_children", "سقف بچه‌ها", 50)
_n("infant_minutes", "مدت نوزادی (دقیقه)", 40)
_n("job_period_hours", "دوره درآمد بچه‌ها (ساعت)", 6)
_n("gamble_win", "احتمال برد قمار (درصد)", 48)
_n("trade_win", "احتمال سود ترید (درصد)", 51)
_n("trade_gain_min", "حداقل درصد سود ترید", 13)
_n("trade_gain_max", "حداکثر درصد سود ترید", 71)
_n("trade_loss_min", "حداقل درصد ضرر ترید", 5)
_n("trade_loss_max", "حداکثر درصد ضرر ترید", 55)
_n("daf_hours", "مدت اجاره هر داف (ساعت)", 36)
_n("stash_hours", "مدت اعتبار پیش‌فرض مشروب/مخدر/بالاخواه/رت (ساعت)", 24)
_n("stash_uses", "تعداد دفعات مصرف پیش‌فرض مشروب/مخدر", 10)
_n("narc_cd_min", "محدودیت زمانی بین هر مصرف مخدر (دقیقه)", 30)
_n("drug_profit_pct", "سود پیش‌فرض هر مصرف (٪ قیمت) وقتی سود ثبت نشده", 12)
_n("od_chance", "احتمال اوردوز (درصد)", 80)
_n("od_fine", "جریمه اوردوز", 300)
_n("od_window_min", "مدت خطر اوردوز بعد از مشروب (دقیقه)", 60)
_n("mofte_pct", "درصد مفتبری/دزدی از پول نقد طرف", 5)
_n("mofte_cd", "محدودیت مفتبری (دقیقه)", 60)
_n("dozd_cd", "محدودیت دزدی (دقیقه)", 60)
_n("rat_fine", "جریمه دزدی روی رت‌دار", 300)
_n("fit_win", "احتمال موفقیت فیت (درصد)", 90)
_n("fit_reward", "پاداش فیت برای هر برادر", 300)
_n("fit_cd", "محدودیت فیت (دقیقه)", 120)
_n("veh_loss_pct", "درصد ضرر فروش موتور/ماشین", 20)
for _vk, _vc in VEH.items():
    _n(f"{_vk}_ok", f"احتمال موفقیت {_vc['name']} (درصد)", _vc["ok"])
    _n(f"{_vk}_ok_force", f"احتمال موفقیت {_vc['name']} وقتی تکراری میزنه (درصد)", 50)
    _n(f"{_vk}_pen", f"جریمه شکست {_vc['name']}", _vc["pen"])
    _n(f"{_vk}_cd", f"محدودیت {_vc['name']} (دقیقه)", 60)
    _n(f"{_vk}_profit_bp", f"سود {_vc['name']} (صدم درصد قیمت؛ 100 = یک درصد)", 100)
    _n(f"{_vk}_svc_bp", f"هزینه سرویس {_vc['name']} (صدم درصد قیمت؛ 65 = 0.65٪)", 65)
for _i, _m in zip(range(2, 9), (5000, 10000, 20000, 100000, 200000, 400000, 1000000)):
    _n(f"lvl_{_i}_min", f"حداقل پول نقد برای سطح {_i}", _m)

JOBS = {  # کلید: (نام، ایموجی)
    "embezzler": ("اختلاس‌گر", "💼"), "doctor": ("دکتر", "🩺"), "engineer": ("مهندس", "💻"),
    "worker": ("کارگر", "🧱"), "addict": ("معتاد", "💊"),
}
# کلید: (درآمد/هزینه هر دوره، قیمت فروش، وزن انتخاب شغل) — وزن‌ها تقریبا برابر؛ اختلاس‌گر ~۲٪ کمتر
JOB_DEFAULTS = {
    "embezzler": (1500, 1500, 18), "doctor": (1000, 1000, 20), "engineer": (700, 700, 20),
    "worker": (400, 400, 20), "addict": (-200, 100, 20),
}
for _jk, (_inc, _price, _w) in JOB_DEFAULTS.items():
    _n(f"job_{_jk}_income", f"درآمد شغل {JOBS[_jk][0]} (هر دوره، منفی=هزینه)", _inc)
    _n(f"job_{_jk}_price", f"قیمت فروش بچه {JOBS[_jk][0]}", _price)
    _n(f"job_{_jk}_weight", f"وزن احتمال شغل {JOBS[_jk][0]}", _w)

# دستورهای پاداش‌دار: کلید → (عبارت، کلید متن، کلید متن کولداون، حداقل داف، بارداری، (حداقل، حداکثر، کولداون دقیقه))
COMMANDS = {
    "ashkra": ("اشکرع", "t_ashkra", "t_cd_simple", 0, False, (100, 100, 60)),
    "hasbi": ("حسبی الله", "t_hasbi", "t_cd_simple", 0, False, (100, 100, 60)),
    "bad": ("داف من بدکارست", "t_bad", "t_cd_simple", 0, False, (70, 70, 60)),
    "sex": ("سکس", "t_sex", "t_cd_sex", 1, True, (220, 220, 40)),
    "tri": ("تریسام", "t_tri", "t_cd_tri", 2, True, (290, 360, 120)),
    "four": ("فورسام", "t_four", "t_cd_multi", 3, True, (400, 480, 180)),
    "five": ("فایوسام", "t_five", "t_cd_multi", 4, True, (550, 650, 240)),
    "sak": ("ساک", "t_sak", "t_cd_sak", 1, False, (100, 100, 60)),
}
for _ck, _v in COMMANDS.items():
    _n(f"{_ck}_min", f"«{_v[0]}» — حداقل پاداش", _v[5][0])
    _n(f"{_ck}_max", f"«{_v[0]}» — حداکثر پاداش", _v[5][1])
    _n(f"{_ck}_cd", f"«{_v[0]}» — محدودیت (دقیقه)", _v[5][2])

SET: dict = {}      # مقادیر تغییر داده‌شده از پنل
REPLIES: dict = {}  # پاسخ‌های ساده  trigger → response
DB_ADMINS: set = set()

# ---- متغیرهای متن‌ها: نام‌های هم‌معنی (فارسی/انگلیسی) و جاهای خالی ناشناخته خراب نمی‌کنند
_ALIAS = [
    ("n", "cd", "min", "time", "دقیقه", "زمان"), ("reward", "amount", "coin", "مبلغ", "پاداش", "سود"),
    ("name", "اسم", "نام"), ("cash", "نقد", "موجودی"), ("price", "قیمت"), ("cost", "هزینه"),
    ("a", "user", "کاربر", "اسم_کاربر"), ("b", "brother", "برادر"), ("v", "target", "طرف", "قربانی"),
]


class _Safe(dict):
    def __missing__(self, k):
        return "{" + k + "}"


def _with_alias(kw):
    out = dict(kw)
    for grp in _ALIAS:
        val = next((kw[g] for g in grp if g in kw), None)
        if val is not None:
            for g in grp:
                out.setdefault(g, val)
    return out


_BTN_KEYS: dict = {}  # متن دکمه → کلیدهای دکمه (برای مخفی/حذف کردن دکمه‌ها از پنل)


def T(key, **kw):
    out = _T(key, **kw)
    if key[:2] in ("b_", "c_"):
        _BTN_KEYS.setdefault(out[:64], set()).add(key)
    return out


def _T(key, **kw):
    raw = SET.get(key, DEFAULTS[key][1])
    data = _Safe(_with_alias(kw))
    try:
        return raw.format_map(data)
    except Exception:
        try:
            return DEFAULTS[key][1].format_map(data)
        except Exception:
            return DEFAULTS[key][1]

def num(key):
    try:
        return int(SET[key])
    except Exception:
        return NUMS[key][1]


def fmt(x):
    return f"{int(x):,}"


esc = html.escape
NOW = lambda: int(time.time())  # noqa: E731

# ════════════════════════════════════════════════════════════════════════════
#  نرمال‌سازی متن
# ════════════════════════════════════════════════════════════════════════════
_DIG = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_JUNK = dict.fromkeys(map(ord, "\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff"))


def soft(s: str) -> str:
    s = s.translate(_DIG).translate(_JUNK).replace("ي", "ی").replace("ك", "ک").replace("ـ", "")
    return re.sub(r"\s+", " ", s).strip()


def key_of(s: str) -> str:
    return soft(s.replace("\u200c", " "))


# ════════════════════════════════════════════════════════════════════════════
#  دیتابیس
# ════════════════════════════════════════════════════════════════════════════
class Database:
    def __init__(self, path):
        self.path = path
        self.conn = None
        self.lock = asyncio.Lock()

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path, isolation_level=None)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("PRAGMA synchronous=NORMAL")

    @asynccontextmanager
    async def tx(self):
        """تراکنش اتمیک؛ همه‌ی عملیات هم‌زمان پشت یک قفل سریالی می‌شوند."""
        async with self.lock:
            await self.conn.execute("BEGIN IMMEDIATE")
            try:
                yield self.conn
            except BaseException:
                await self.conn.execute("ROLLBACK")
                raise
            else:
                await self.conn.execute("COMMIT")


DB = Database(DB_PATH)


async def q1(c, sql, args=()):
    cur = await c.execute(sql, args)
    row = await cur.fetchone()
    await cur.close()
    return row


async def qall(c, sql, args=()):
    cur = await c.execute(sql, args)
    rows = await cur.fetchall()
    await cur.close()
    return rows


async def run(c, sql, args=()):
    cur = await c.execute(sql, args)
    n = cur.rowcount
    await cur.close()
    return n


async def ins(c, sql, args=()):
    cur = await c.execute(sql, args)
    n = cur.lastrowid
    await cur.close()
    return n


SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT,
    created_at INTEGER NOT NULL, last_seen INTEGER);
CREATE TABLE IF NOT EXISTS balances(user_id INTEGER PRIMARY KEY, cash INTEGER NOT NULL DEFAULT 0 CHECK(cash>=0));
CREATE TABLE IF NOT EXISTS bank(user_id INTEGER PRIMARY KEY, deposit INTEGER NOT NULL DEFAULT 0 CHECK(deposit>=0),
    last_interest_ts INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL, kind TEXT NOT NULL, note TEXT, created_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id, id);
CREATE TABLE IF NOT EXISTS properties(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
    emoji TEXT NOT NULL DEFAULT '', price INTEGER, income INTEGER, enabled INTEGER NOT NULL DEFAULT 1,
    sort_order INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS user_properties(user_id INTEGER NOT NULL, property_id INTEGER NOT NULL,
    bought_at INTEGER NOT NULL, last_collect INTEGER NOT NULL, PRIMARY KEY(user_id, property_id));
CREATE TABLE IF NOT EXISTS shop_items(id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL,
    name TEXT NOT NULL, emoji TEXT NOT NULL DEFAULT '', price INTEGER, sell_price INTEGER,
    enabled INTEGER NOT NULL DEFAULT 1, sort_order INTEGER NOT NULL DEFAULT 0, extra TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS inventory(user_id INTEGER NOT NULL, item_id INTEGER NOT NULL,
    qty INTEGER NOT NULL DEFAULT 0, health INTEGER NOT NULL DEFAULT 100, PRIMARY KEY(user_id, item_id));
CREATE TABLE IF NOT EXISTS davas(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL, bought_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS idx_davas_user ON davas(user_id);
CREATE TABLE IF NOT EXISTS condoms(user_id INTEGER NOT NULL, item_id INTEGER NOT NULL,
    qty INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id, item_id));
CREATE TABLE IF NOT EXISTS cooldowns(user_id INTEGER NOT NULL, cmd TEXT NOT NULL, last_ts INTEGER NOT NULL,
    PRIMARY KEY(user_id, cmd));
CREATE TABLE IF NOT EXISTS trade_history(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL, pct INTEGER NOT NULL, pnl INTEGER NOT NULL, created_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS idx_trade_user ON trade_history(user_id);
CREATE TABLE IF NOT EXISTS gambling_history(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
    bet INTEGER NOT NULL, won INTEGER NOT NULL, created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS user_levels(user_id INTEGER PRIMARY KEY, level INTEGER NOT NULL DEFAULT 5,
    title TEXT NOT NULL DEFAULT 'کاسب', emoji TEXT NOT NULL DEFAULT '😈', xp INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS children(id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL,
    number INTEGER NOT NULL, name TEXT, born_at INTEGER NOT NULL, stage TEXT NOT NULL DEFAULT 'infant',
    job TEXT, work_start INTEGER, last_pay INTEGER, status TEXT NOT NULL DEFAULT 'kept', sold_at INTEGER,
    pregnancy_id INTEGER);
CREATE INDEX IF NOT EXISTS idx_children_owner ON children(owner_id, status);
CREATE TABLE IF NOT EXISTS pregnancies(id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER NOT NULL,
    kind TEXT NOT NULL, count INTEGER NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
    created_at INTEGER NOT NULL, resolved_at INTEGER);
CREATE TABLE IF NOT EXISTS extras(user_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT,
    PRIMARY KEY(user_id, key));
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS simple_replies(id INTEGER PRIMARY KEY AUTOINCREMENT, trigger TEXT NOT NULL UNIQUE,
    response TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS chats(chat_id INTEGER PRIMARY KEY, type TEXT, title TEXT);
"""

SEED_PROPS = [
    ("👕", "بوتیک"), ("🎙", "استودیو"), ("🍾", "عرق فروشی"), ("💊", "داروخونه"), ("🧹", "کارواش لوکس"),
    ("🏭", "کارخونه واک هارت"), ("🎬", "سینما"), ("🏬", "مرکز خرید"), ("🚢", "پایانه باربری"),
    ("🏨", "هتل پنج ستاره"), ("🖥", "دیتاسنتر"), ("", "پالایشگاه"), ("", "فرودگاه بین‌المللی"),
    ("", "مجتمع پتروشیمی"), ("", "برج تجاری"),
]


async def migration_2_seed(conn):
    """ملک‌ها (بدون قیمت)، داف‌ها (قیمت‌های مشخص)، کاندوم‌ها (بدون قیمت)، پاسخ‌های ساده."""
    for i, (emo, name) in enumerate(SEED_PROPS, 1):
        await conn.execute("INSERT INTO properties(name, emoji, price, income, sort_order) VALUES(?,?,NULL,NULL,?)",
                           (name, emo, i))
    for i, (name, price) in enumerate([("داف آماتور", 2000), ("داف کاربلد", 4000), ("شوگر", 5000),
                                       ("داف خوشگل", 10000)], 1):
        await conn.execute("INSERT INTO shop_items(category,name,emoji,price,sort_order) VALUES('daf',?,'💃',?,?)",
                           (name, price, i))
    for i, name in enumerate(["کاندوم خاردار", "کاندوم خاردار هلویی", "کاندوم معمولی"], 1):
        await conn.execute("INSERT INTO shop_items(category,name,emoji,price,sort_order) VALUES('condom',?,'',NULL,?)",
                           (name, i))
    for trig, resp in [("حلالت", "حلالم"), ("توعون", "حلالت"), ("فدای سرش", "توعونشو میدم"),
                       ("موتکر میاد بالا اشکرع", "اشکرع")]:
        await conn.execute("INSERT OR IGNORE INTO simple_replies(trigger,response) VALUES(?,?)", (key_of(trig), resp))


# فهرست مایگریشن‌ها؛ برای تغییر در آینده فقط یک ردیف جدید با شماره بالاتر اضافه کن (داده‌ها پاک نمی‌شوند).
SEED_V3 = [
    # دسته، نام، ایموجی، قیمت، سود هر مصرف، تعداد مصرف، مدت (ساعت)، extra
    ("drink", "عرق کشمش", "🍇", 500, 90, 10, 24, {}),
    ("drink", "ویسکی", "🥃", 1200, 150, 10, 24, {}),
    ("drink", "آبجو", "🍺", 800, 110, 10, 24, {}),
    ("drink", "ودکا", "🍸", 2000, 220, 10, 24, {}),
    ("drink", "هنسی", "🍷", 1200, 140, 10, 24, {}),
    ("drink", "کونیاک", "🥂", 900, 100, 10, 24, {}),
    ("drug", "بالاخواه", "🛡", 5000, None, None, 24, {"kind": "guard"}),
    ("rat", "رت", "🐀", 5000, None, None, 24, {"kind": "rat"}),
    ("car", "گواهینامه", "🪪", 8000, None, None, 120, {"kind": "license"}),
    ("car", "پراید 131", "", 28800, None, None, None, {}),
    ("car", "پژو 206 تیپ 5", "", 56000, None, None, None, {}),
    ("car", "سمند EF7", "", 67200, None, None, None, {}),
    ("car", "Toyota Corolla", "", 144000, None, None, None, {}),
    ("car", "Subaru WRX", "", 288000, None, None, None, {}),
    ("car", "Honda Civic Type R", "", 416000, None, None, None, {}),
    ("car", "Porsche 911 Carrera", "", 672000, None, None, None, {}),
    ("car", "BMW M3 Competition", "", 832000, None, None, None, {}),
    ("car", "Nissan GT-R", "", 960000, None, None, None, {}),
    ("car", "Bugatti Chiron", "", 2880000, None, None, None, {}),
    ("moto", "اسکوتر", "", 2000, None, None, None, {}),
    ("moto", "موتور کلیک", "", 5000, None, None, None, {}),
    ("moto", "هوندا 125", "", 8000, None, None, None, {}),
    ("moto", "تمرین موتورسواری", "🏁", 8000, None, None, 24 * 365 * 10, {"kind": "course"}),
    ("moto", "بنلی", "", 20000, None, None, None, {}),
    ("moto", "کاوازاکی نینجا", "", 40000, None, None, None, {}),
    ("moto", "سی بی 1,300", "", 100000, None, None, None, {}),
    ("moto", "BMW", "", 200000, None, None, None, {}),
]


async def migration_3(conn):
    """نسخه ۲: ملک تا ۱۰ تا + سود لحظه‌ای، داف اجاره‌ای، مشروب/مخدر شمارشی، موتور/ماشین، برادری، کد هدیه."""
    for stmt in (
        "ALTER TABLE user_properties ADD COLUMN qty INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE user_properties ADD COLUMN acc INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE shop_items ADD COLUMN profit INTEGER",
        "ALTER TABLE shop_items ADD COLUMN max_uses INTEGER",
        "ALTER TABLE shop_items ADD COLUMN dur_hours INTEGER",
        "CREATE TABLE IF NOT EXISTS stash(user_id INTEGER NOT NULL, item_id INTEGER NOT NULL, bought_at INTEGER NOT NULL, "
        "expires_at INTEGER NOT NULL, uses_left INTEGER NOT NULL DEFAULT 1, last_use INTEGER, PRIMARY KEY(user_id,item_id))",
        "CREATE TABLE IF NOT EXISTS vehicles(user_id INTEGER NOT NULL, kind TEXT NOT NULL, item_id INTEGER NOT NULL, "
        "paid INTEGER NOT NULL, svc INTEGER NOT NULL DEFAULT 0, bought_at INTEGER NOT NULL, PRIMARY KEY(user_id,kind))",
        "CREATE TABLE IF NOT EXISTS brothers(user_id INTEGER PRIMARY KEY, brother_id INTEGER NOT NULL, since INTEGER NOT NULL)",
        "CREATE TABLE IF NOT EXISTS gift_codes(code TEXT PRIMARY KEY, amount INTEGER NOT NULL, capacity INTEGER NOT NULL, "
        "used INTEGER NOT NULL DEFAULT 0, expires_at INTEGER, created_at INTEGER NOT NULL)",
        "CREATE TABLE IF NOT EXISTS gift_redeems(code TEXT NOT NULL, user_id INTEGER NOT NULL, ts INTEGER NOT NULL, "
        "PRIMARY KEY(code,user_id))",
    ):
        await conn.execute(stmt)
    now = NOW()
    # داف‌ها: از هر نوع فقط یکی، و ۳۶ ساعت از همین لحظه
    await conn.execute("DELETE FROM davas WHERE id NOT IN (SELECT MAX(id) FROM davas GROUP BY user_id,item_id)")
    await conn.execute("UPDATE davas SET bought_at=?", (now,))
    # مشروب/مخدر/رت قدیمی انبار → استش جدید
    rows = await qall(conn, "SELECT i.user_id uid, i.item_id iid, s.category cat FROM inventory i "
                            "JOIN shop_items s ON s.id=i.item_id WHERE i.qty>0 AND s.category IN ('drink','drug','rat')")
    for r in rows:
        await conn.execute("INSERT OR IGNORE INTO stash(user_id,item_id,bought_at,expires_at,uses_left) VALUES(?,?,?,?,?)",
                           (r["uid"], r["iid"], now, now + 24 * 3600, 1 if r["cat"] == "rat" else 10))
    await conn.execute("DELETE FROM inventory WHERE item_id IN (SELECT id FROM shop_items WHERE category IN ('drink','drug','rat'))")
    # موتور/ماشین قدیمی انبار → وسیله فعلی (گران‌ترین)
    rows = await qall(conn, "SELECT i.user_id uid, i.item_id iid, s.category cat, COALESCE(s.price,0) price FROM inventory i "
                            "JOIN shop_items s ON s.id=i.item_id WHERE i.qty>0 AND s.category IN ('moto','car') "
                            "ORDER BY COALESCE(s.price,0) DESC")
    for r in rows:
        await conn.execute("INSERT OR IGNORE INTO vehicles(user_id,kind,item_id,paid,bought_at) VALUES(?,?,?,?,?)",
                           (r["uid"], r["cat"], r["iid"], r["price"], now))
    await conn.execute("DELETE FROM inventory WHERE item_id IN (SELECT id FROM shop_items WHERE category IN ('moto','car'))")
    # محصولات جدید
    for cat, name, emoji, price, profit, mu, hrs, extra in SEED_V3:
        row = await q1(conn, "SELECT id FROM shop_items WHERE category=? AND name=?", (cat, name))
        if row:
            await conn.execute("UPDATE shop_items SET price=?, profit=?, max_uses=?, dur_hours=?, extra=? WHERE id=?",
                               (price, profit, mu, hrs, json.dumps(extra), row["id"]))
        else:
            await conn.execute(
                "INSERT INTO shop_items(category,name,emoji,price,profit,max_uses,dur_hours,extra,sort_order) "
                "VALUES(?,?,?,?,?,?,?,?,(SELECT COALESCE(MAX(sort_order),0)+1 FROM shop_items))",
                (cat, name, emoji, price, profit, mu, hrs, json.dumps(extra)))


SEED_V4 = [
    # دسته، نام، ایموجی، قیمت، سود هر مصرف، تعداد مصرف، مدت (ساعت)، extra
    ("narc", "تریاک", "🟤", 500, 70, 10, 24, {}),
    ("narc", "لین", "🥤", 250, 40, 10, 24, {}),
    ("narc", "ترامادول", "💊", 600, 85, 10, 24, {}),
    ("narc", "زاناکس", "🔵", 800, 100, 10, 24, {}),
    ("narc", "ماشروم", "🍄", 1000, 130, 10, 24, {}),
    ("narc", "سیگار", "🚬", 200, 35, 10, 24, {}),
    ("narc", "پرومتازین", "💉", 500, 75, 10, 24, {}),
    ("narc", "گل", "🌿", 600, 90, 10, 24, {}),
]


async def migration_4(conn):
    """دسته‌ی جدید «مخدر ها» (زیر نوشیدنی و مشروبات) با محصولات مخصوص خودش."""
    for cat, name, emoji, price, profit, mu, hrs, extra in SEED_V4:
        row = await q1(conn, "SELECT id FROM shop_items WHERE category=? AND name=?", (cat, name))
        if row:
            continue
        await conn.execute(
            "INSERT INTO shop_items(category,name,emoji,price,profit,max_uses,dur_hours,extra,sort_order) "
            "VALUES(?,?,?,?,?,?,?,?,(SELECT COALESCE(MAX(sort_order),0)+1 FROM shop_items))",
            (cat, name, emoji, price, profit, mu, hrs, json.dumps(extra)))


MIGRATIONS = [(1, SCHEMA_V1), (2, migration_2_seed), (3, migration_3), (4, migration_4)]


async def migrate():
    conn = DB.conn
    await conn.execute("CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY, applied_at INTEGER)")
    row = await q1(conn, "SELECT COALESCE(MAX(version),0) v FROM schema_version")
    current = row["v"]
    for ver, step in MIGRATIONS:
        if ver <= current:
            continue
        if isinstance(step, str):
            await conn.executescript(step)
        else:
            await conn.execute("BEGIN")
            try:
                await step(conn)
                await conn.execute("COMMIT")
            except BaseException:
                await conn.execute("ROLLBACK")
                raise
        await conn.execute("INSERT INTO schema_version(version, applied_at) VALUES(?,?)", (ver, NOW()))
        log.info("migration %s applied", ver)


async def load_cache():
    global DB_ADMINS
    SET.clear()
    REPLIES.clear()
    async with DB.tx() as c:
        for r in await qall(c, "SELECT key, value FROM settings"):
            SET[r["key"]] = r["value"]
        for r in await qall(c, "SELECT trigger, response FROM simple_replies"):
            REPLIES[r["trigger"]] = r["response"]
    DB_ADMINS = {int(x) for x in re.findall(r"\d+", SET.get("admin_ids", ""))}


async def set_setting(c, key, value):
    if value is None:
        await run(c, "DELETE FROM settings WHERE key=?", (key,))
        SET.pop(key, None)
    else:
        await run(c, "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (key, str(value)))
        SET[key] = str(value)


def is_admin(uid):
    return uid in ENV_ADMINS or uid in DB_ADMINS


# ════════════════════════════════════════════════════════════════════════════
#  هسته‌ی اقتصاد
# ════════════════════════════════════════════════════════════════════════════
async def touch(c, u):
    """ثبت/به‌روزرسانی کاربر + اعمال سود بانک و رشد/درآمد بچه‌ها (حتی برای زمان آفلاین)."""
    now = NOW()
    await run(c, "INSERT OR IGNORE INTO users(user_id,first_name,username,created_at,last_seen) VALUES(?,?,?,?,?)",
              (u.id, u.full_name, u.username, now, now))
    await run(c, "UPDATE users SET first_name=?, username=?, last_seen=? WHERE user_id=?",
              (u.full_name, u.username, now, u.id))
    await run(c, "INSERT OR IGNORE INTO balances(user_id,cash) VALUES(?,?)", (u.id, max(0, num("start_cash"))))
    await run(c, "INSERT OR IGNORE INTO bank(user_id,deposit,last_interest_ts) VALUES(?,0,?)", (u.id, now))
    await run(c, "INSERT OR IGNORE INTO user_levels(user_id) VALUES(?)", (u.id,))
    await accrue_bank(c, u.id, now)
    await process_children(c, u.id, now)


async def get_cash(c, uid):
    return (await q1(c, "SELECT cash FROM balances WHERE user_id=?", (uid,)))["cash"]


async def get_bank(c, uid):
    return (await q1(c, "SELECT deposit FROM bank WHERE user_id=?", (uid,)))["deposit"]


async def add_cash(c, uid, delta, kind, note=""):
    """تغییر اتمیک پول نقد؛ اگر موجودی کافی نباشد False برمی‌گردد."""
    delta = int(delta)
    ok = await run(c, "UPDATE balances SET cash=cash+? WHERE user_id=? AND cash+?>=0", (delta, uid, delta)) == 1
    if ok:
        await run(c, "INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,?,?,?,?)",
                  (uid, delta, kind, note, NOW()))
    return ok


async def accrue_bank(c, uid, now):
    row = await q1(c, "SELECT deposit, last_interest_ts FROM bank WHERE user_id=?", (uid,))
    dep, last = row["deposit"], row["last_interest_ts"]
    if dep <= 0:
        if last != now:
            await run(c, "UPDATE bank SET last_interest_ts=? WHERE user_id=?", (now, uid))
        return
    days = (now - last) // 86400
    if days <= 0:
        return
    rate = max(0, num("bank_rate"))
    start = dep
    for _ in range(min(days, 5000)):
        g = dep * rate // 100
        if g <= 0 or dep >= MAX_MONEY:
            break
        dep = min(MAX_MONEY, dep + g)
    await run(c, "UPDATE bank SET deposit=?, last_interest_ts=? WHERE user_id=?", (dep, last + days * 86400, uid))
    if dep != start:
        await run(c, "INSERT INTO transactions(user_id,amount,kind,note,created_at) VALUES(?,0,'bank_interest',?,?)",
                  (uid, f"+{dep - start} in {days}d", now))


async def bank_op(c, uid, mode, pct):
    cash, dep = await get_cash(c, uid), await get_bank(c, uid)
    if mode == "dep":
        amt = cash * pct // 100
        if amt <= 0:
            return False, "پول نقدی برای سپرده نداری پسرعمو 💸"
        if dep + amt > MAX_MONEY:
            return False, "سقف سپرده پر شده پسرعمو"
        await add_cash(c, uid, -amt, "bank_deposit")
        await run(c, "UPDATE bank SET deposit=deposit+? WHERE user_id=?", (amt, uid))
        return True, f"✅ {fmt(amt)} زی کوین سپرده شد پسرعمو"
    amt = dep * pct // 100
    if amt <= 0:
        return False, "سپرده‌ای برای برداشت نداری پسرعمو 🏦"
    await run(c, "UPDATE bank SET deposit=deposit-? WHERE user_id=?", (amt, uid))
    await add_cash(c, uid, amt, "bank_withdraw")
    return True, f"✅ {fmt(amt)} زی کوین برداشت شد پسرعمو"


async def take_cooldown(c, uid, cmd, seconds):
    """اگر محدودیت باقی باشد ثانیه‌ی باقی‌مانده را برمی‌گرداند، وگرنه زمان را ثبت می‌کند و ۰ می‌دهد."""
    now = NOW()
    row = await q1(c, "SELECT last_ts FROM cooldowns WHERE user_id=? AND cmd=?", (uid, cmd))
    if row and now - row["last_ts"] < seconds:
        return seconds - (now - row["last_ts"])
    await run(c, "INSERT INTO cooldowns(user_id,cmd,last_ts) VALUES(?,?,?) "
                 "ON CONFLICT(user_id,cmd) DO UPDATE SET last_ts=excluded.last_ts", (uid, cmd, now))
    return 0


def minutes_left(sec):
    return max(1, math.ceil(sec / 60))


# ---- املاک (حداکثر ۱۰ تا از هر ملک، سود لحظه‌ای)
def fmt_period(minutes):
    if minutes % 60 == 0:
        return f"{minutes // 60} ساعت"
    return f"{minutes} دقیقه"


_PROP_EMOJI = {"پالایشگاه": "⛽", "فرودگاه بین‌المللی": "✈️", "مجتمع پتروشیمی": "🧪", "برج تجاری": "🏢"}


def prop_label(p):
    emo = p["emoji"] or _PROP_EMOJI.get(p["name"], "🏢")
    return f"{emo} {p['name']}".strip()


def fmt_left(sec):
    mins = max(0, int(sec)) // 60
    h, m = divmod(mins, 60)
    if h and m:
        return f"{h} ساعت و {m} دقیقه"
    if h:
        return f"{h} ساعت"
    return f"{max(1, m)} دقیقه"


def fmt_hours(h):
    h = int(h)
    return f"{h // 24} روز" if h >= 24 and h % 24 == 0 else f"{h} ساعت"


def prop_period():
    return max(1, num("prop_period_minutes")) * 60


async def prop_user_rows(c, uid):
    return await qall(c, "SELECT up.property_id pid, up.last_collect lc, up.qty qty, up.acc acc, p.income inc "
                         "FROM user_properties up JOIN properties p ON p.id=up.property_id WHERE up.user_id=?", (uid,))


async def prop_ready(c, uid, now):
    """سود آماده‌ی برداشت به‌صورت لحظه‌ای: درآمد هر دوره به‌طور یکنواخت در هر ثانیه جمع میشه."""
    period = prop_period()
    rows = await prop_user_rows(c, uid)
    total = 0
    for r in rows:
        rate = max(0, r["inc"] or 0) * r["qty"]
        total += (r["acc"] * period + max(0, now - r["lc"]) * rate) // period
    return total, rows


async def prop_collect(c, uid):
    now = NOW()
    period = prop_period()
    total = 0
    for r in await prop_user_rows(c, uid):
        rate = max(0, r["inc"] or 0) * r["qty"]
        units = r["acc"] * period + max(0, now - r["lc"]) * rate
        pay, rem = divmod(units, period)
        total += pay
        new_lc = now - (rem // rate if rate > 0 else 0)  # باقیمانده‌ی کسری از دست نمیره
        await run(c, "UPDATE user_properties SET acc=0, last_collect=? WHERE user_id=? AND property_id=?",
                  (new_lc, uid, r["pid"]))
    if total <= 0:
        return False, "هنوز سودی آماده برداشت نیست پسرعمو ⏳"
    await add_cash(c, uid, total, "property_income")
    return True, f"💰 {fmt(total)} زی کوین سود برداشت کردی پسرعمو"


async def prop_buy(c, uid, pid):
    p = await q1(c, "SELECT * FROM properties WHERE id=? AND enabled=1", (pid,))
    if not p:
        return False, "این ملک پیدا نشد"
    if p["price"] is None:
        return False, T("t_unpriced")
    mx = max(1, num("prop_max"))
    row = await q1(c, "SELECT qty, acc, last_collect FROM user_properties WHERE user_id=? AND property_id=?", (uid, pid))
    if row and row["qty"] >= mx:
        return False, f"از این ملک {mx} تا داری و بیشتر نمیشه خرید پسرعمو ✅"
    if not await add_cash(c, uid, -p["price"], "property_buy", str(pid)):
        return False, "پول نقدت کافی نیست پسرعمو 💸"
    now = NOW()
    if row:
        pend = row["acc"] + max(0, now - row["last_collect"]) * max(0, p["income"] or 0) * row["qty"] // prop_period()
        await run(c, "UPDATE user_properties SET qty=qty+1, acc=?, last_collect=? WHERE user_id=? AND property_id=?",
                  (pend, now, uid, pid))
        qty = row["qty"] + 1
    else:
        await run(c, "INSERT INTO user_properties(user_id,property_id,bought_at,last_collect,qty,acc) VALUES(?,?,?,?,1,0)",
                  (uid, pid, now, now))
        qty = 1
    return True, f"✅ {prop_label(p)} رو خریدی پسرعمو! ({qty}/{mx}) موجودی: {fmt(await get_cash(c, uid))}"


# ---- سطح (بر اساس پول نقد)
def level_of(cash):
    lv = 1
    for n in range(2, 9):
        if cash >= num(f"lvl_{n}_min"):
            lv = n
    return lv


# ---- محدودیت‌های زمانی (بدون ثبت)
async def cd_peek(c, uid, cmd, seconds):
    r = await q1(c, "SELECT last_ts FROM cooldowns WHERE user_id=? AND cmd=?", (uid, cmd))
    now = NOW()
    if r and now - r["last_ts"] < seconds:
        return seconds - (now - r["last_ts"])
    return 0


async def cd_set(c, uid, cmd):
    await run(c, "INSERT INTO cooldowns(user_id,cmd,last_ts) VALUES(?,?,?) "
                 "ON CONFLICT(user_id,cmd) DO UPDATE SET last_ts=excluded.last_ts", (uid, cmd, NOW()))


# ---- فروشگاه و انبار
_CAT_EMOJI = {"daf": "💃", "drink": "🥃", "narc": "💊", "drug": "🛡", "rat": "🐀", "car": "🚗", "moto": "🏍",
              "gun": "🔫", "gear": "🎽", "condom": "🎈", "toy": "🧸"}


def _row_cat(it):
    try:
        ks = it.keys()
        for k in ("category", "kind"):
            if k in ks:
                return it[k]
    except Exception:
        pass
    return ""


def item_label(it, price=False, owned=False):
    emo = it["emoji"] or _CAT_EMOJI.get(_row_cat(it), "🛍")
    s = f"{emo} {it['name']}".strip()
    if price and it["price"] is not None:
        s += f" — {fmt(it['price'])} زی"
    return ("✅ " if owned else "") + s


def item_extra(it):
    try:
        return json.loads(it["extra"] or "{}")
    except Exception:
        return {}


def item_kind(it):
    """daf | drink | drug | guard(بالاخواه) | rat | license | course | vehicle | condom | gear"""
    k = item_extra(it).get("kind")
    if k:
        return k
    return {"daf": "daf", "drink": "drink", "narc": "drink", "drug": "drug", "rat": "rat", "moto": "vehicle", "car": "vehicle",
            "condom": "condom"}.get(it["category"], "gear")


STASH_KINDS = {"drink", "drug", "guard", "rat", "license", "course"}
USABLE_KINDS = {"drink", "drug"}


def item_hours(it):
    h = it["dur_hours"]
    if h:
        return int(h)
    k = item_kind(it)
    if k == "daf":
        return max(1, num("daf_hours"))
    if k == "license":
        return 120
    if k == "course":
        return 24 * 365 * 10
    return max(1, num("stash_hours"))


def item_uses(it):
    if item_kind(it) in USABLE_KINDS:
        return int(it["max_uses"] or num("stash_uses"))
    return 1


def item_profit(it):
    if it["profit"] is not None:
        return max(0, int(it["profit"]))
    return max(0, (it["price"] or 0) * num("drug_profit_pct") // 100)


async def stash_row(c, uid, iid):
    return await q1(c, "SELECT * FROM stash WHERE user_id=? AND item_id=?", (uid, iid))


def stash_active(r, now=None):
    return r is not None and r["expires_at"] > (now or NOW()) and r["uses_left"] > 0


async def stash_give(c, uid, it):
    now = NOW()
    await run(c, "INSERT INTO stash(user_id,item_id,bought_at,expires_at,uses_left) VALUES(?,?,?,?,?) "
                 "ON CONFLICT(user_id,item_id) DO UPDATE SET bought_at=excluded.bought_at, "
                 "expires_at=excluded.expires_at, uses_left=excluded.uses_left, last_use=NULL",
              (uid, it["id"], now, now + item_hours(it) * 3600, item_uses(it)))


async def stash_rows(c, uid, kinds=None):
    rows = await qall(c, "SELECT st.expires_at, st.uses_left, s.id, s.name, s.emoji, s.category, s.extra, s.price, "
                         "s.profit, s.max_uses, s.dur_hours, s.sell_price FROM stash st JOIN shop_items s ON s.id=st.item_id "
                         "WHERE st.user_id=? AND st.expires_at>? AND st.uses_left>0 ORDER BY s.category, s.id",
                      (uid, NOW()))
    return [r for r in rows if not kinds or item_kind(r) in kinds]


async def has_effect(c, uid, kind):
    return bool(await stash_rows(c, uid, {kind}))


async def has_license(c, uid):
    return await has_effect(c, uid, "license")


async def daf_rows(c, uid):
    """داف‌های اجاره‌ای فعال: [(row, ثانیه‌ی باقی‌مانده)]"""
    now = NOW()
    out = []
    for r in await qall(c, "SELECT d.id did, d.bought_at ba, s.id, s.name, s.emoji, s.dur_hours, s.category, s.extra "
                           "FROM davas d JOIN shop_items s ON s.id=d.item_id WHERE d.user_id=? ORDER BY d.id", (uid,)):
        left = r["ba"] + item_hours(r) * 3600 - now
        if left > 0:
            out.append((r, left))
    return out


async def veh_get(c, uid, kind):
    return await q1(c, "SELECT v.item_id, v.kind, v.paid, v.svc, s.name, s.emoji, s.price FROM vehicles v "
                       "JOIN shop_items s ON s.id=v.item_id WHERE v.user_id=? AND v.kind=?", (uid, kind))


async def owned_qty(c, uid, it):
    kind = item_kind(it)
    if kind == "daf":
        return sum(1 for r, _ in await daf_rows(c, uid) if r["id"] == it["id"])
    if kind in STASH_KINDS:
        return 1 if stash_active(await stash_row(c, uid, it["id"])) else 0
    if kind == "vehicle":
        v = await veh_get(c, uid, it["category"])
        return 1 if v and v["item_id"] == it["id"] else 0
    if kind == "condom":
        r = await q1(c, "SELECT COALESCE(SUM(qty),0) n FROM condoms WHERE user_id=? AND item_id=?", (uid, it["id"]))
    else:
        r = await q1(c, "SELECT COALESCE(SUM(qty),0) n FROM inventory WHERE user_id=? AND item_id=?", (uid, it["id"]))
    return r["n"]


async def give_item(c, uid, it):
    if it["category"] == "condom":
        await run(c, "INSERT INTO condoms(user_id,item_id,qty) VALUES(?,?,1) "
                     "ON CONFLICT(user_id,item_id) DO UPDATE SET qty=qty+1", (uid, it["id"]))
    else:
        await run(c, "INSERT INTO inventory(user_id,item_id,qty) VALUES(?,?,1) "
                     "ON CONFLICT(user_id,item_id) DO UPDATE SET qty=qty+1", (uid, it["id"]))


async def take_item(c, uid, it):
    tbl = "condoms" if it["category"] == "condom" else "inventory"
    return await run(c, f"UPDATE {tbl} SET qty=qty-1 WHERE user_id=? AND item_id=? AND qty>0", (uid, it["id"])) == 1


async def buy_item(c, uid, iid):
    it = await q1(c, "SELECT * FROM shop_items WHERE id=? AND enabled=1", (iid,))
    if not it:
        return False, "این محصول پیدا نشد"
    if it["price"] is None:
        return False, T("t_unpriced")
    kind, now, hours = item_kind(it), NOW(), item_hours(it)
    name = item_label(it)
    if kind == "daf":
        r = await q1(c, "SELECT bought_at FROM davas WHERE user_id=? AND item_id=? ORDER BY id DESC LIMIT 1", (uid, iid))
        if r and r["bought_at"] + hours * 3600 > now:
            return False, T("t_daf_have", name=name, left=fmt_left(r["bought_at"] + hours * 3600 - now))
    elif kind in STASH_KINDS:
        r = await stash_row(c, uid, iid)
        if stash_active(r, now):
            if kind in USABLE_KINDS:
                return False, T("t_stash_have", name=name, left=fmt_left(r["expires_at"] - now), uses=r["uses_left"])
            return False, T("t_stash_have2", name=name, left=fmt_left(r["expires_at"] - now))
    elif kind == "vehicle":
        if await veh_get(c, uid, it["category"]):
            return False, T("t_have_veh", veh=VEH[it["category"]]["name"])
        if it["category"] == "car" and not await has_license(c, uid):
            return False, T("t_no_license")
    if not await add_cash(c, uid, -it["price"], "shop_buy", f"item:{iid}"):
        return False, "پول نقدت کافی نیست پسرعمو 💸"
    if kind == "daf":
        await run(c, "DELETE FROM davas WHERE user_id=? AND item_id=?", (uid, iid))
        await run(c, "INSERT INTO davas(user_id,item_id,bought_at) VALUES(?,?,?)", (uid, iid, now))
        return True, T("t_daf_rented", name=name, hours=hours)
    if kind in STASH_KINDS:
        await stash_give(c, uid, it)
    elif kind == "vehicle":
        await run(c, "INSERT INTO vehicles(user_id,kind,item_id,paid,svc,bought_at) VALUES(?,?,?,?,0,?)",
                  (uid, it["category"], iid, it["price"], now))
    else:
        await give_item(c, uid, it)
    return True, f"✅ {name} رو خریدی پسرعمو! موجودی: {fmt(await get_cash(c, uid))}"


NON_SELLABLE = STASH_KINDS | {"daf", "vehicle"}


async def sell_item(c, uid, iid):
    it = await q1(c, "SELECT * FROM shop_items WHERE id=?", (iid,))
    if not it:
        return False, "آیتم پیدا نشد"
    if item_kind(it) in NON_SELLABLE:
        return False, "این آیتم قابل فروش نیست پسرعمو 🚫"
    if it["sell_price"] is None:
        return False, "قیمت فروش این آیتم هنوز مشخص نشده 🚫"
    if not await take_item(c, uid, it):
        return False, "این آیتم رو نداری پسرعمو"
    await add_cash(c, uid, it["sell_price"], "item_sell", f"item:{iid}")
    return True, f"✅ {item_label(it)} فروخته شد! +{fmt(it['sell_price'])} زی کوین"


async def inv_rows(c, uid, cats):
    ph = ",".join("?" * len(cats))
    return await qall(c, f"SELECT s.id,s.name,s.emoji,s.sell_price,s.category,i.qty,i.health FROM inventory i "
                         f"JOIN shop_items s ON s.id=i.item_id WHERE i.user_id=? AND i.qty>0 AND s.category IN ({ph}) "
                         f"ORDER BY s.id", (uid, *cats))


async def group_rows(c, uid, group):
    """وسایل جانبی (اینونتوری معمولی + کاندوم)."""
    rows = list(await inv_rows(c, uid, GEAR_CATS))
    rows += list(await qall(c, "SELECT s.id,s.name,s.emoji,s.sell_price,s.category,o.qty,100 health FROM condoms o "
                               "JOIN shop_items s ON s.id=o.item_id WHERE o.user_id=? AND o.qty>0 ORDER BY s.id", (uid,)))
    return rows


async def vehicle_rows(c, uid):
    return await qall(c, "SELECT v.kind, v.item_id, v.paid, v.svc, s.name, s.emoji, s.price FROM vehicles v "
                         "JOIN shop_items s ON s.id=v.item_id WHERE v.user_id=? ORDER BY v.kind DESC", (uid,))


async def inv_counts(c, uid):
    out = {"drug": len(await stash_rows(c, uid)), "daf": len(await daf_rows(c, uid)),
           "gear": sum(r["qty"] for r in await group_rows(c, uid, "gear")),
           "moto": len(await vehicle_rows(c, uid))}
    out["kids"] = (await q1(c, "SELECT COUNT(*) n FROM children WHERE owner_id=? AND status='kept'", (uid,)))["n"]
    out["props"] = (await q1(c, "SELECT COALESCE(SUM(qty),0) n FROM user_properties WHERE user_id=?", (uid,)))["n"]
    return out


# ---- مشروب و مخدر (۱۰ بار مصرف، ۲۴ ساعت اعتبار) + اوردوز
async def use_item(c, uid, iid, force=False):
    """خروجی: (وضعیت, داده) — none | warn | od | ok"""
    it = await q1(c, "SELECT * FROM shop_items WHERE id=?", (iid,))
    if not it or item_kind(it) not in USABLE_KINDS:
        return "none", it
    now = NOW()
    st = await stash_row(c, uid, iid)
    if not stash_active(st, now):
        return "none", it
    kind = item_kind(it)
    if it["category"] == "narc" and st["last_use"]:  # مخدرها: هر نیم ساعت فقط یک بار
        wait = st["last_use"] + max(1, num("narc_cd_min")) * 60 - now
        if wait > 0:
            return "cd", (it, wait)
    risky = False
    if kind == "drug":
        r = await q1(c, "SELECT last_ts FROM cooldowns WHERE user_id=? AND cmd='last_drink'", (uid,))
        risky = bool(r and now - r["last_ts"] < max(1, num("od_window_min")) * 60)
    if risky and not force:
        return "warn", it
    await run(c, "UPDATE stash SET uses_left=uses_left-1, last_use=? WHERE user_id=? AND item_id=? AND uses_left>0",
              (now, uid, iid))
    left = st["uses_left"] - 1
    if kind == "drink":
        await cd_set(c, uid, "last_drink")
    if risky and random.randint(1, 100) <= num("od_chance"):
        fine = min(max(0, num("od_fine")), await get_cash(c, uid))
        if fine:
            await add_cash(c, uid, -fine, "overdose")
        return "od", (it, fine, left)
    profit = item_profit(it)
    if profit:
        await add_cash(c, uid, profit, "use_item", f"item:{iid}")
    return "ok", (it, profit, left, risky)


def fmt_use(uid, status, data, back=None):
    """متن و دکمه‌ی نتیجه‌ی مصرف."""
    kb = mk([[btn(T("b_back_prev"), back)]]) if back else None
    if status == "none":
        name = esc(item_label(data)) if data else "این محصول"
        return T("t_use_none", name=name), kb
    if status == "cd":
        it, wait = data
        return T("t_use_cd", name=esc(it["name"]), n=minutes_left(wait)), kb
    if status == "warn":
        it = data
        rows = [[btn(T("b_od_go"), cd(uid, "od", "go", it["id"])), btn(T("b_od_no"), cd(uid, "od", "no"))]]
        return T("t_od_warn", name=esc(it["name"])), mk(rows)
    if status == "od":
        it, fine, left = data
        return T("t_od_dead", n=fmt(fine)), kb
    it, profit, left, risky = data
    key = "t_od_ok" if risky else "t_use_ok"
    return T(key, name=esc(it["name"]), emoji=it["emoji"], n=fmt(profit), left=left), kb


# ---- موتور و ماشین
def veh_price(v):
    return v["price"] or v["paid"]


def svc_cost(v, kind):
    return max(1, veh_price(v) * num(f"{kind}_svc_bp") // 10000)


def sell_price(v):
    return max(0, v["paid"] * (100 - num("veh_loss_pct")) // 100)


async def veh_trick(c, uid, kind, force=False):
    v = await veh_get(c, uid, kind)
    if not v:
        return "none", None
    if v["svc"]:
        return "svc", (v, svc_cost(v, kind))
    left = await cd_peek(c, uid, f"trick_{kind}", max(0, num(f"{kind}_cd")) * 60)
    if left > 0 and not force:
        return "cool", (v, left)
    chance = num(f"{kind}_ok_force") if left > 0 else num(f"{kind}_ok")
    await cd_set(c, uid, f"trick_{kind}")
    await run(c, "UPDATE vehicles SET svc=1 WHERE user_id=? AND kind=?", (uid, kind))
    if random.randint(1, 100) <= chance:
        reward = max(1, veh_price(v) * num(f"{kind}_profit_bp") // 10000)
        await add_cash(c, uid, reward, f"trick_{kind}")
        return "ok", (v, reward)
    pen = min(max(0, num(f"{kind}_pen")), await get_cash(c, uid))
    if pen:
        await add_cash(c, uid, -pen, f"trick_fail_{kind}")
    return "fail", (v, pen)


async def veh_service(c, uid, kind):
    v = await veh_get(c, uid, kind)
    if not v:
        return False, T("t_veh_none", veh=VEH[kind]["name"]), None
    if not v["svc"]:
        return False, f"{VEH[kind]['name']}ت سرویس نمیخواد پسرعمو ✅", v
    cost = svc_cost(v, kind)
    if not await add_cash(c, uid, -cost, f"service_{kind}"):
        return False, f"پول نقدت برای سرویس کافی نیست پسرعمو 💸 (هزینه: {fmt(cost)})", v
    await run(c, "UPDATE vehicles SET svc=0 WHERE user_id=? AND kind=?", (uid, kind))
    return True, cost, v


async def veh_sell(c, uid, kind):
    v = await veh_get(c, uid, kind)
    if not v:
        return False, T("t_veh_none", veh=VEH[kind]["name"]), None
    price = sell_price(v)
    if await run(c, "DELETE FROM vehicles WHERE user_id=? AND kind=?", (uid, kind)) != 1:
        return False, "قبلاً فروخته شده", v
    await add_cash(c, uid, price, f"sell_{kind}")
    return True, price, v


def fmt_trick(uid, kind, act, status, data):
    """متن و دکمه‌ی نتیجه‌ی تک‌چرخ / لایی / دریفت."""
    cfg = VEH[kind]
    if status == "none":
        return T("t_veh_none", veh=cfg["name"]), None
    v = data[0]
    name = esc(v["name"])
    if status == "svc":
        rows = [[btn(T(f"b_{kind}_sell"), cd(uid, "veh", kind, "sell")),
                 btn(T(f"b_{kind}_svc"), cd(uid, "veh", kind, "svc"))]]
        return T(f"t_{kind}_svc_need", name=name, cost=fmt(data[1])), mk(rows)
    if status == "cool":
        rows = [[btn(T("b_force"), cd(uid, "veh", kind, "force", act))]]
        return T(f"t_{kind}_cool", n=minutes_left(data[1]), name=name), mk(rows)
    key = f"t_{kind}_ok" if status == "ok" else f"t_{kind}_fail"
    return T(key, name=name, reward=fmt(data[1]), pen=fmt(data[1]), act=ACTS.get(act, "")), None


# ---- برادری
async def brother_of(c, uid):
    r = await q1(c, "SELECT brother_id FROM brothers WHERE user_id=?", (uid,))
    return r["brother_id"] if r else None


async def make_brothers(c, a, b):
    now = NOW()
    await run(c, "INSERT OR REPLACE INTO brothers(user_id,brother_id,since) VALUES(?,?,?)", (a, b, now))
    await run(c, "INSERT OR REPLACE INTO brothers(user_id,brother_id,since) VALUES(?,?,?)", (b, a, now))


async def break_brothers(c, a, b):
    return await run(c, "DELETE FROM brothers WHERE (user_id=? AND brother_id=?) OR (user_id=? AND brother_id=?)",
                     (a, b, b, a))


async def user_link(c, uid):
    r = await q1(c, "SELECT first_name FROM users WHERE user_id=?", (uid,))
    name = (r["first_name"] if r and r["first_name"] else None) or str(uid)
    return f'<a href="tg://user?id={uid}">{esc(name)}</a>'


# ---- کد هدیه
async def gift_redeem(c, uid, code):
    code = code.strip().upper()
    g = await q1(c, "SELECT * FROM gift_codes WHERE code=?", (code,))
    if not g:
        return False, T("t_gift_bad")
    if g["expires_at"] and g["expires_at"] <= NOW():
        return False, T("t_gift_exp")
    if g["used"] >= g["capacity"]:
        return False, T("t_gift_full")
    if await q1(c, "SELECT 1 FROM gift_redeems WHERE code=? AND user_id=?", (code, uid)):
        return False, T("t_gift_used")
    await run(c, "INSERT INTO gift_redeems(code,user_id,ts) VALUES(?,?,?)", (code, uid, NOW()))
    await run(c, "UPDATE gift_codes SET used=used+1 WHERE code=?", (code,))
    await add_cash(c, uid, g["amount"], "gift_code", code)
    return True, T("t_gift_ok", n=fmt(g["amount"]))


# ---- بچه‌ها
ORD = ["اول", "دوم", "سوم", "چهارم", "پنجم", "ششم", "هفتم", "هشتم", "نهم", "دهم"]
PREG_NAMES = {1: "یک قلو", 2: "دوقلو", 3: "سه قلو", 4: "چهارقلو"}


def child_name(ch):
    if ch["name"]:
        return ch["name"]
    n = ch["number"]
    return f"بچه‌ی {ORD[n - 1]}" if 1 <= n <= 10 else f"بچه‌ی شماره {n}"


def pick_job():
    keys = list(JOBS)
    w = [max(0, num(f"job_{k}_weight")) for k in keys]
    if sum(w) <= 0:
        return "worker"
    return random.choices(keys, weights=w, k=1)[0]


def child_line(ch):
    name = esc(child_name(ch))
    if ch["stage"] == "infant":
        return f"{ch['number']}. {name} - شغل: نوزاد (بی‌شغل) 🍼"
    nm, emo = JOBS[ch["job"]]
    inc = num(f"job_{ch['job']}_income")
    hrs = num("job_period_hours")
    if inc < 0:
        return f"{ch['number']}. {name} - شغل: {nm} {emo} (هر {hrs} ساعت {fmt(-inc)} زی از حسابت کم میشه)"
    return f"{ch['number']}. {name} - شغل: {nm} {emo} (هر {hrs} ساعت {fmt(inc)} زی)"


def child_price(ch):
    return None if ch["stage"] == "infant" else num(f"job_{ch['job']}_price")


async def kids_of(c, uid):
    return await qall(c, "SELECT * FROM children WHERE owner_id=? AND status='kept' ORDER BY number", (uid,))


async def process_children(c, uid, now):
    """رشد نوزادها بعد از مدت نوزادی + پرداخت دوره‌های کامل درآمد (آفلاین هم محاسبه می‌شود)."""
    inf = max(1, num("infant_minutes")) * 60
    for r in await qall(c, "SELECT id, born_at FROM children WHERE owner_id=? AND status='kept' AND stage='infant' "
                           "AND born_at+?<=?", (uid, inf, now)):
        start = r["born_at"] + inf
        await run(c, "UPDATE children SET stage='adult', job=?, work_start=?, last_pay=? WHERE id=? AND stage='infant'",
                  (pick_job(), start, start, r["id"]))
    period = max(1, num("job_period_hours")) * 3600
    total = 0
    for r in await qall(c, "SELECT id, job, last_pay FROM children WHERE owner_id=? AND status='kept' "
                           "AND stage='adult'", (uid,)):
        n = (now - r["last_pay"]) // period
        if n > 0:
            await run(c, "UPDATE children SET last_pay=last_pay+? WHERE id=? AND last_pay=?",
                      (n * period, r["id"], r["last_pay"]))
            total += n * num(f"job_{r['job']}_income")
    if total != 0:
        total = max(total, -(await get_cash(c, uid)))
        if total != 0:
            await add_cash(c, uid, total, "children_income")


async def resolve_pregnancy(c, uid, pid, keep):
    p = await q1(c, "SELECT * FROM pregnancies WHERE id=? AND owner_id=?", (pid, uid))
    if not p:
        return "gone", None
    if p["state"] != "pending":
        return "done", None
    if await run(c, "UPDATE pregnancies SET state=?, resolved_at=? WHERE id=? AND state='pending'",
                 ("kept" if keep else "aborted", NOW(), pid)) != 1:
        return "done", None
    if not keep:
        return "abort", None
    held = await kids_of(c, uid)
    used = {k["number"] for k in held}
    keep_n = max(0, min(p["count"], num("max_children") - len(held)))
    nums, now = [], NOW()
    for _ in range(keep_n):
        n = 1
        while n in used:
            n += 1
        used.add(n)
        nums.append(n)
        await run(c, "INSERT INTO children(owner_id,number,born_at,stage,status,pregnancy_id) "
                     "VALUES(?,?,?,'infant','kept',?)", (uid, n, now, pid))
    return "keep", (nums, p["count"] - keep_n)


# ════════════════════════════════════════════════════════════════════════════
#  ساخت کیبورد و صفحه‌ها (Views)
# ════════════════════════════════════════════════════════════════════════════
def cd(uid, *parts):
    return ":".join(str(p) for p in parts) + f":{uid}"


def btn(text, data):
    return InlineKeyboardButton(text=text[:64], callback_data=data)


def _btn_hidden(b):
    """دکمه‌ای که ادمین از پنل مخفی/حذف کرده نمایش داده نمی‌شود."""
    if (b.callback_data or "").startswith("adm:"):
        return False
    keys = _BTN_KEYS.get(b.text)
    return bool(keys) and all(SET.get("bh_" + k) in ("1", "2") for k in keys)


def mk(rows):
    out = []
    for row in rows:
        keep = [b for b in row if not _btn_hidden(b)]
        if keep:
            out.append(keep)
    return InlineKeyboardMarkup(inline_keyboard=out)


def clip(text, limit=4000):
    return text if len(text) <= limit else text[:limit - 2] + " …"


def back_row(uid):
    return [btn(T("b_back"), cd(uid, "menu"))]


def view_menu(uid):
    rows = [
        [btn(T("b_shop"), cd(uid, "shop", "menu")), btn(T("b_profile"), cd(uid, "prof"))],
        [btn(T("b_props"), cd(uid, "prop", "menu")), btn(T("b_bank"), cd(uid, "bank", "menu"))],
        [btn(T("b_inv"), cd(uid, "inv", "menu")), btn(T("b_trade"), cd(uid, "trade", "menu"))],
        [btn(T("b_help"), cd(uid, "help")), btn(T("b_mission"), cd(uid, "mission"))],
        [InlineKeyboardButton(text=T("b_addgroup")[:64], url=f"https://t.me/{BOT_USERNAME}?startgroup=true")],
    ]
    return T("t_menu"), mk(rows)


async def view_bank(c, uid):
    text = T("t_bank", cash=fmt(await get_cash(c, uid)), bank=fmt(await get_bank(c, uid)), rate=num("bank_rate"))
    rows = [[btn(T("b_withdraw", p=p), cd(uid, "bank", "wd", p)), btn(T("b_deposit", p=p), cd(uid, "bank", "dep", p))]
            for p in range(10, 101, 10)]
    rows.append(back_row(uid))
    return text, mk(rows)


async def view_props(c, uid):
    ready, urows = await prop_ready(c, uid, NOW())
    owned = {r["pid"]: r["qty"] for r in urows}
    mx = max(1, num("prop_max"))
    rows = []
    for p in await qall(c, "SELECT * FROM properties WHERE enabled=1 ORDER BY sort_order, id"):
        label = prop_label(p)
        if p["price"] is not None:
            label += f" — {fmt(p['price'])} زی"
        q = owned.get(p["id"], 0)
        if q:
            label = f"✅ {label} ({q}/{mx})"
        rows.append([btn(label, cd(uid, "prop", "view", p["id"]))])
    rows.append([btn(T("b_collect"), cd(uid, "prop", "collect")), btn(T("b_refresh"), cd(uid, "prop", "menu"))])
    rows.append(back_row(uid))
    return T("t_props", ready=fmt(ready), max=mx), mk(rows)


async def view_prop_confirm(c, uid, pid):
    p = await q1(c, "SELECT * FROM properties WHERE id=? AND enabled=1", (pid,))
    own = await q1(c, "SELECT qty FROM user_properties WHERE user_id=? AND property_id=?", (uid, pid))
    text = T("t_prop_confirm", label=prop_label(p), price=fmt(p["price"]), income=fmt(p["income"] or 0),
             period=fmt_period(num("prop_period_minutes")), qty=own["qty"] if own else 0, max=max(1, num("prop_max")))
    rows = [[btn(T("b_buy"), cd(uid, "prop", "do", pid)), btn(T("b_cancel"), cd(uid, "prop", "menu"))],
            [btn(T("b_back_prev"), cd(uid, "prop", "menu"))]]
    return text, mk(rows)


HELP_SECS = ("daf", "mavad", "rat", "bala")


def view_help(uid, sec=""):
    """راهنمای شیشه‌ای: داف | مواد / رت | بالاخواه / برگشت"""
    if sec in HELP_SECS:
        return T("t_help_" + sec), mk([[btn(T("b_help_back"), cd(uid, "help"))]])
    rows = [[btn(T("b_help_daf"), cd(uid, "help", "daf")), btn(T("b_help_mavad"), cd(uid, "help", "mavad"))],
            [btn(T("b_help_rat"), cd(uid, "help", "rat")), btn(T("b_help_bala"), cd(uid, "help", "bala"))],
            [btn(T("b_help_back"), cd(uid, "menu"))]]
    return T("t_help"), mk(rows)


def view_shop(uid):
    rows = [[btn(T("c_" + k), cd(uid, "shop", "cat", k))] for k, _ in SHOP_CATS]
    rows.append(back_row(uid))
    return T("t_shop"), mk(rows)


async def view_shop_cat(c, uid, cat):
    if cat in VEH:
        return await view_veh_shop(c, uid, cat)
    items = await qall(c, "SELECT * FROM shop_items WHERE category=? AND enabled=1 ORDER BY sort_order, id", (cat,))
    rows = []
    if cat == "daf":
        rented = {r["id"] for r, _ in await daf_rows(c, uid)}
        for it in items:  # فقط اسم، بدون تعداد
            rows.append([btn(item_label(it, owned=it["id"] in rented), cd(uid, "shop", "item", it["id"]))])
        rows.append([btn(T("b_condom"), cd(uid, "shop", "cat", "condom"))])
        rows.append([btn(T("b_toy"), cd(uid, "shop", "cat", "toy"))])
        rows.append([btn(T("b_back_shop_menu"), cd(uid, "shop", "menu"))])
        return T("t_daf_menu"), mk(rows)
    for it in items:
        qty = await owned_qty(c, uid, it) if cat not in ("condom", "toy") else 0
        rows.append([btn(item_label(it, price=True, owned=qty > 0), cd(uid, "shop", "item", it["id"]))])
    if cat in ("condom", "toy"):
        rows.append([btn(T("b_back_prev"), cd(uid, "shop", "cat", "daf"))])
        title = T("t_condom_menu") if cat == "condom" else T("t_toy_menu")
    else:
        rows.append([btn(T("b_back_store"), cd(uid, "shop", "menu"))])
        title = T("t_shop_cat", cat=T("c_" + cat))
    if not items:
        title += "\n\n" + T("t_shop_empty")
    return title, mk(rows)


async def view_veh_shop(c, uid, cat):
    cfg = VEH[cat]
    v = await veh_get(c, uid, cat)
    items = await qall(c, "SELECT * FROM shop_items WHERE category=? AND enabled=1 ORDER BY sort_order, id", (cat,))
    rows, listed = [], False
    for it in items:
        kind = item_kind(it)
        if kind == "vehicle":
            if v and v["item_id"] == it["id"]:
                listed = True
                rows.append([btn(f"{cfg['emoji']} {cfg['name']} فعلی: {v['name']} (مدیریت ⚙️)",
                                 cd(uid, "veh", cat, "manage"))])
                continue
            if cat == "moto":
                label = f"🛒 خرید {it['name']}" + (f" ({fmt(it['price'])} زی)" if it["price"] is not None else "")
            else:
                label = item_label(it, price=True)
        else:
            label = item_label(it, price=True, owned=stash_active(await stash_row(c, uid, it["id"])))
            if cat == "car" and kind == "license":
                label += f" | {fmt_hours(item_hours(it))}"
        rows.append([btn(label, cd(uid, "shop", "item", it["id"]))])
    if v and not listed:
        rows.insert(0, [btn(f"{cfg['emoji']} {cfg['name']} فعلی: {v['name']} (مدیریت ⚙️)", cd(uid, "veh", cat, "manage"))])
    rows.append([btn(T("b_back_store"), cd(uid, "shop", "menu"))])
    title = T("t_shop_cat", cat=T("c_" + cat))
    if not items:
        title += "\n\n" + T("t_shop_empty")
    return title, mk(rows)


async def view_veh_manage(c, uid, kind):
    v = await veh_get(c, uid, kind)
    if not v:
        return await view_veh_shop(c, uid, kind)
    cfg = VEH[kind]
    state = "نیاز به سرویس داره 🛠" if v["svc"] else "سالم و آماده ✅"
    text = (f"{cfg['emoji']} {cfg['name']} فعلی: {esc(item_label(v))}\n\nقیمت خرید: {fmt(v['paid'])} زی کوین\n"
            f"وضعیت: {state}\nهزینه سرویس: {fmt(svc_cost(v, kind))} زی کوین\n"
            f"قیمت فروش: {fmt(sell_price(v))} زی کوین ({num('veh_loss_pct')}٪ ضرر)")
    rows = [[btn(T(f"b_{kind}_sell"), cd(uid, "veh", kind, "sell")), btn(T(f"b_{kind}_svc"), cd(uid, "veh", kind, "svc"))],
            [btn(T("b_back_veh"), cd(uid, "shop", "cat", kind))]]
    return text, mk(rows)


async def view_veh_sell_confirm(c, uid, kind):
    v = await veh_get(c, uid, kind)
    if not v:
        return await view_veh_shop(c, uid, kind)
    text = T(f"t_{kind}_sell_confirm", name=esc(v["name"]), paid=fmt(v["paid"]), price=fmt(sell_price(v)),
             loss=num("veh_loss_pct"))
    back = cd(uid, "veh", kind, "manage")
    return text, mk([[btn(T("b_sell_ok"), cd(uid, "veh", kind, "sellok")), btn(T("b_cancel"), back)]])


def shop_back(cat):
    return cat if cat in ALL_CATS else "daf"


async def view_item_confirm(c, uid, iid):
    it = await q1(c, "SELECT * FROM shop_items WHERE id=?", (iid,))
    kind = item_kind(it)
    cash = fmt(await get_cash(c, uid))
    if kind == "daf":
        text = T("t_daf_confirm", name=esc(item_label(it)), price=fmt(it["price"]), cash=cash, hours=item_hours(it))
    else:
        text = T("t_item_confirm", name=esc(item_label(it)), price=fmt(it["price"]), cash=cash)
        if kind in USABLE_KINDS:
            text += (f"\n\n⏳ مدت اعتبار: {fmt_hours(item_hours(it))} | 🔢 تعداد مصرف: {item_uses(it)}"
                     f"\n💰 سود هر مصرف: {fmt(item_profit(it))} زی کوین")
            if it["category"] == "narc":
                text += f"\n⏱ هر {num('narc_cd_min')} دقیقه فقط یک بار میشه مصرفش کرد"
        elif kind in STASH_KINDS:
            text += f"\n\n⏳ مدت اعتبار: {fmt_hours(item_hours(it))}"
    back = cd(uid, "shop", "cat", it["category"])
    rows = [[btn(T("b_buy"), cd(uid, "shop", "do", iid)), btn(T("b_cancel"), back)], [btn(T("b_back_prev"), back)]]
    return text, mk(rows)


async def view_inventory(c, uid):
    cnt = await inv_counts(c, uid)
    rows = []
    for key, g in (("b_inv_drug", "drug"), ("b_inv_gear", "gear"), ("b_inv_kids", "kids"),
                   ("b_inv_props", "props"), ("b_inv_moto", "moto")):  # داف‌ها اینجا نیستند (قابل فروش نیستند)
        if cnt[g] > 0:
            rows.append([btn(T(key, n=cnt[g]), cd(uid, "inv", "g", g))])
    rows.append(back_row(uid))
    return T("t_inv"), mk(rows)


GROUP_TITLES = {"drug": "مخدرها و مشروبات 💊", "gear": "وسایل جانبی 🛡️", "moto": "موتور و ماشین 🏍️",
                "props": "املاک 🏠", "kids": "بچه‌ها 👶"}


async def view_inv_group(c, uid, group):
    back = [btn(T("b_back_prev"), cd(uid, "inv", "menu"))]
    if group == "kids":
        kids = await kids_of(c, uid)
        if not kids:
            return T("t_no_kids"), mk([back])
        rows = []
        for ch in kids:
            price = child_price(ch)
            if price is None:
                rows.append([btn(f"فروش بچه {child_name(ch)} (غیرقابل فروش) 👶", cd(uid, "inv", "kx", ch["id"]))])
            else:
                rows.append([btn(f"فروش بچه {child_name(ch)} ({price} زی) 👶", cd(uid, "inv", "ks", ch["id"]))])
        rows.append(back)
        return clip(T("t_kids_title") + "\n\n" + "\n".join(child_line(k) for k in kids)), mk(rows)
    if group == "props":
        props = await qall(c, "SELECT p.*, up.qty qty FROM user_properties up JOIN properties p ON p.id=up.property_id "
                              "WHERE up.user_id=? ORDER BY p.sort_order", (uid,))
        if not props:
            return T("t_inv_empty"), mk([back])
        return "املاک 🏠:\n\n" + "\n".join(f"• {esc(prop_label(p))} × {p['qty']}" for p in props), mk([back])
    if group == "drug":
        items = await stash_rows(c, uid)
        if not items:
            return T("t_inv_empty"), mk([back])
        now = NOW()
        lines, rows = [], []
        for r in items:
            left = fmt_left(r["expires_at"] - now)
            if item_kind(r) in USABLE_KINDS:
                lines.append(f"• {esc(item_label(r))} — {r['uses_left']} بار مصرف | {left} اعتبار")
                rows.append([btn(f"مصرف {item_label(r)} 💉", cd(uid, "use", "do", r["id"]))])
            else:
                lines.append(f"• {esc(item_label(r))} — {left} اعتبار")
        rows.append(back)
        return clip(GROUP_TITLES["drug"] + ":\n\n" + "\n".join(lines)), mk(rows)
    if group == "moto":
        vs = await vehicle_rows(c, uid)
        if not vs:
            return T("t_inv_empty"), mk([back])
        lines, rows = [], []
        for v in vs:
            cfg = VEH[v["kind"]]
            lines.append(f"• {cfg['emoji']} {esc(v['name'])}" + (" (نیاز به سرویس 🛠)" if v["svc"] else ""))
            rows.append([btn(f"مدیریت {v['name']} ⚙️", cd(uid, "veh", v["kind"], "manage"))])
        rows.append(back)
        return GROUP_TITLES["moto"] + ":\n\n" + "\n".join(lines), mk(rows)
    items = await group_rows(c, uid, group)
    if not items:
        return T("t_inv_empty"), mk([back])
    lines, rows = [], []
    for it in items:
        lines.append(f"• {esc(item_label(it))} × {it['qty']}")
        sp = f" ({it['sell_price']} زی)" if it["sell_price"] is not None else ""
        rows.append([btn(f"فروش {item_label(it)}{sp}", cd(uid, "inv", "s", it["id"]))])
    rows.append(back)
    return GROUP_TITLES["gear"] + ":\n\n" + "\n".join(lines), mk(rows)


async def view_profile(c, target_id, viewer_id):
    u = await q1(c, "SELECT * FROM users WHERE user_id=?", (target_id,))
    cash, bank = await get_cash(c, target_id), await get_bank(c, target_id)
    trade = (await q1(c, "SELECT COALESCE(SUM(pnl),0) s FROM trade_history WHERE user_id=?", (target_id,)))["s"]
    lv = level_of(cash)
    now = NOW()

    def lines(items, f):
        return "\n".join(f(i) for i in items) if items else "ندارد"

    def stash_line(r):
        left = fmt_left(r["expires_at"] - now)
        if item_kind(r) in USABLE_KINDS:
            return f"{esc(item_label(r))} — {r['uses_left']} بار | {left}"
        return f"{esc(item_label(r))} — {left}"

    stash = await stash_rows(c, target_id)
    vs = {v["kind"]: v for v in await vehicle_rows(c, target_id)}

    def veh_line(k):
        v = vs.get(k)
        return "ندارد" if not v else esc(item_label(v)) + (" (نیاز به سرویس 🛠)" if v["svc"] else "")

    dafs = await daf_rows(c, target_id)
    gear = await group_rows(c, target_id, "gear")
    stuff = [f"{esc(item_label(r))} (اجاره‌ای، {fmt_left(left)} مونده)" for r, left in dafs]
    stuff += [f"{esc(item_label(i))} × {i['qty']}" for i in gear]
    props = await qall(c, "SELECT p.*, up.qty qty FROM user_properties up JOIN properties p ON p.id=up.property_id "
                          "WHERE up.user_id=? ORDER BY p.sort_order", (target_id,))
    kids = (await q1(c, "SELECT COUNT(*) n FROM children WHERE owner_id=? AND status='kept'", (target_id,)))["n"]
    bro = await brother_of(c, target_id)
    link = f'<a href="tg://user?id={target_id}">{esc(u["first_name"] or str(target_id))}</a>'
    text = T("t_profile", link=link, cash=fmt(cash), bank=fmt(bank), trade=f"{trade:,}", total=fmt(cash + bank),
             level_title=esc(T(f"t_lvl_{lv}")), level=lv, level_emoji=LEVEL_EMOJI[lv],
             drugs=lines(stash, stash_line),
             props=lines(props, lambda p: f"{esc(prop_label(p))} × {p['qty']}"),
             motos=veh_line("moto"), cars=veh_line("car"),
             stuff="\n".join(stuff) if stuff else "ندارد", kids=kids,
             brother=(await user_link(c, bro)) if bro else "ندارد")
    return clip(text), mk([back_row(viewer_id)])


async def view_kids(c, uid):
    kids = await kids_of(c, uid)
    if not kids:
        return T("t_no_kids"), mk([back_row(uid)])
    return clip(T("t_kids_title") + "\n\n" + "\n".join(child_line(k) for k in kids)), mk([back_row(uid)])


# ════════════════════════════════════════════════════════════════════════════
#  مسیریاب دکمه‌ها
# ════════════════════════════════════════════════════════════════════════════
async def route(c, uid, a):
    """خروجی: (متن هشدار | None، صفحه‌ی جدید | None)"""
    s = a[0]
    sub = a[1] if len(a) > 1 else ""
    arg = int(a[2]) if len(a) > 2 and a[2].lstrip("-").isdigit() else None
    if s == "menu":
        return None, view_menu(uid)
    if s == "bank":
        alert = None
        if sub in ("dep", "wd") and arg in range(10, 101, 10):
            _, alert = await bank_op(c, uid, sub, arg)
        return alert, await view_bank(c, uid)
    if s == "prop":
        if sub == "menu":
            return None, await view_props(c, uid)
        if sub == "collect":
            _, msg = await prop_collect(c, uid)
            return msg, await view_props(c, uid)
        p = await q1(c, "SELECT * FROM properties WHERE id=? AND enabled=1", (arg,))
        if not p:
            return "این ملک پیدا نشد", await view_props(c, uid)
        if sub == "view":
            own = await q1(c, "SELECT qty FROM user_properties WHERE user_id=? AND property_id=?", (uid, arg))
            mx = max(1, num("prop_max"))
            if own and own["qty"] >= mx:
                return f"از این ملک {mx} تا داری و بیشتر نمیشه خرید پسرعمو ✅", None
            if p["price"] is None:
                return T("t_unpriced"), None
            return None, await view_prop_confirm(c, uid, arg)
        if sub == "do":
            _, msg = await prop_buy(c, uid, arg)
            return msg, await view_props(c, uid)
    if s == "shop":
        if sub == "menu":
            return None, view_shop(uid)
        if sub == "cat":
            return None, await view_shop_cat(c, uid, a[2] if len(a) > 2 and a[2] in ALL_CATS else "daf")
        it = await q1(c, "SELECT * FROM shop_items WHERE id=?", (arg,)) if arg is not None else None
        if not it:
            return "این محصول پیدا نشد", view_shop(uid)
        if sub == "item":
            if it["price"] is None:
                return T("t_unpriced"), None
            return None, await view_item_confirm(c, uid, arg)
        if sub == "do":
            _, msg = await buy_item(c, uid, arg)
            return msg, await view_shop_cat(c, uid, it["category"])
    if s == "veh":
        kind = sub
        if kind not in VEH:
            return None, None
        act = a[2] if len(a) > 2 else "manage"
        if act == "manage":
            return None, await view_veh_manage(c, uid, kind)
        if act == "sell":
            return None, await view_veh_sell_confirm(c, uid, kind)
        if act == "sellok":
            ok, res, v = await veh_sell(c, uid, kind)
            if not ok:
                return res, await view_veh_shop(c, uid, kind)
            return T(f"t_{kind}_sold", name=v["name"], price=fmt(res)), await view_veh_shop(c, uid, kind)
        if act == "svc":
            ok, res, v = await veh_service(c, uid, kind)
            if not ok:
                return res, await view_veh_manage(c, uid, kind)
            back = mk([[btn(T("b_back_veh"), cd(uid, "shop", "cat", kind))]])
            return None, (T(f"t_{kind}_svc_done", name=esc(v["name"]), cost=fmt(res)), back)
        if act == "force":
            code = a[3] if len(a) > 3 and a[3] in ACTS else ("tak" if kind == "moto" else "drift")
            status, data = await veh_trick(c, uid, kind, force=True)
            return None, fmt_trick(uid, kind, code, status, data)
        return None, None
    if s == "use" and sub == "do":
        status, data = await use_item(c, uid, arg)
        return None, fmt_use(uid, status, data, back=cd(uid, "inv", "g", "drug"))
    if s == "od":
        if sub == "no":
            return None, (T("t_od_cancel"), None)
        if sub == "go":
            status, data = await use_item(c, uid, arg, force=True)
            return None, fmt_use(uid, status, data)
    if s == "prof":
        return None, await view_profile(c, uid, uid)
    if s == "help":
        return None, view_help(uid, sub)
    if s == "mission":
        return None, (T("t_mission"), mk([back_row(uid)]))
    if s == "trade":
        if sub == "long":
            return T("t_trade_long"), None
        rows = [[btn(T("b_long_trade"), cd(uid, "trade", "long"))], back_row(uid)]
        return None, (T("t_trade_menu"), mk(rows))
    if s == "inv":
        if sub == "menu":
            return None, await view_inventory(c, uid)
        if sub == "g":
            return None, await view_inv_group(c, uid, a[2] if len(a) > 2 and a[2] in GROUP_TITLES else "gear")
        if sub in ("s", "sc"):
            it = await q1(c, "SELECT * FROM shop_items WHERE id=?", (arg,))
            if not it:
                return "آیتم پیدا نشد", await view_inventory(c, uid)
            if item_kind(it) in NON_SELLABLE:
                return "این آیتم قابل فروش نیست پسرعمو 🚫", None
            grp = CAT_GROUP.get(it["category"], "gear")
            if sub == "s":
                if it["sell_price"] is None:
                    return "قیمت فروش این آیتم هنوز مشخص نشده 🚫", None
                if await owned_qty(c, uid, it) <= 0:
                    return "این آیتم رو نداری پسرعمو", await view_inv_group(c, uid, grp)
                text = T("t_sell_confirm", name=esc(item_label(it)), price=fmt(it["sell_price"]))
                back = cd(uid, "inv", "g", grp)
                return None, (text, mk([[btn(T("b_sell_ok"), cd(uid, "inv", "sc", arg)), btn(T("b_cancel"), back)],
                                        [btn(T("b_back_prev"), back)]]))
            _, msg = await sell_item(c, uid, arg)
            cnt = await inv_counts(c, uid)
            if cnt.get(grp, 0) <= 0:
                return msg, await view_inventory(c, uid)
            return msg, await view_inv_group(c, uid, grp)
        if sub in ("kx", "ks", "kc"):
            ch = await q1(c, "SELECT * FROM children WHERE id=? AND owner_id=? AND status='kept'", (arg, uid))
            if not ch:
                return "این بچه دیگه مال تو نیست پسرعمو", await view_inv_group(c, uid, "kids")
            price = child_price(ch)
            if price is None:
                return "نوزاد فعلاً غیرقابل فروشه پسرعمو 🍼", None
            if sub == "kx":
                return "نوزاد فعلاً غیرقابل فروشه پسرعمو 🍼", None
            if sub == "ks":
                text = T("t_kid_sell_confirm", name=esc(child_name(ch)), price=fmt(price))
                back = cd(uid, "inv", "g", "kids")
                return None, (text, mk([[btn(T("b_sell_ok"), cd(uid, "inv", "kc", arg)), btn(T("b_cancel"), back)],
                                        [btn(T("b_back_prev"), back)]]))
            if await run(c, "UPDATE children SET status='sold', sold_at=? WHERE id=? AND owner_id=? AND status='kept'",
                         (NOW(), arg, uid)) != 1:
                return "این بچه قبلاً فروخته شده", await view_inv_group(c, uid, "kids")
            await add_cash(c, uid, price, "child_sell", f"child:{arg}")
            msg = f"✅ {child_name(ch)} فروخته شد! +{fmt(price)} زی کوین"
            cnt = await inv_counts(c, uid)
            return msg, (await view_inv_group(c, uid, "kids") if cnt["kids"] else await view_inventory(c, uid))
    if s == "preg":
        st, data = await resolve_pregnancy(c, uid, arg, keep=(sub == "keep"))
        if st in ("gone", "done"):
            return "این بارداری قبلاً مشخص شده پسرعمو", ("__clear__", None)
        if st == "abort":
            return None, ("__append__", T("t_abort_done"))
        nums, orphan = data
        parts = []
        if nums:
            parts.append(T("t_keep_done", k=len(nums)))
            parts += [T("t_name_prompt", n=n) for n in nums]
            parts.append(T("t_name_usage"))
        if orphan > 0 or not nums:
            parts.append(T("t_orphan"))
        return None, ("__append__", "\n".join(parts))
    return None, None


async def safe_edit(msg, text, markup):
    try:
        await msg.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "not modified" not in str(e).lower():
            log.warning("edit failed: %s", e)


router = Router()


@router.callback_query(F.data.startswith("adm:"))
async def on_adm(q: CallbackQuery):
    if not is_admin(q.from_user.id):
        return await q.answer("دسترسی نداری 🚫", show_alert=True)
    PENDING.pop(q.from_user.id, None)
    async with DB.tx() as c:
        alert, view = await adm_route(c, q.data.split(":")[1:], q.from_user.id)
    await q.answer(alert, show_alert=bool(alert))
    if view and q.message:
        await safe_edit(q.message, view[0], view[1])


# ---- جوین اجباری (فقط در پیوی)
_MEMBER_OK: dict = {}


async def is_member(bot, uid, fresh=False):
    """عضویت در کانال اجباری. اگر ربات نتواند بررسی کند (ادمین کانال نیست) اجازه می‌دهد تا ربات از کار نیفتد."""
    if not FORCE_CHANNEL:
        return True
    now = NOW()
    if not fresh and _MEMBER_OK.get(uid, 0) > now:
        return True
    try:
        cm = await bot.get_chat_member(FORCE_CHANNEL, uid)
    except Exception as e:
        log.warning("بررسی جوین اجباری ناموفق (ربات باید ادمین %s باشد): %s", FORCE_CHANNEL, e)
        return True
    st = str(getattr(cm.status, "value", cm.status))
    ok = st in ("creator", "administrator", "member") or (st == "restricted" and bool(getattr(cm, "is_member", False)))
    if ok:
        _MEMBER_OK[uid] = now + 600
    return ok


def join_kb(uid):
    rows = [[InlineKeyboardButton(text=T("b_join")[:64], url=f"https://t.me/{FORCE_CHANNEL.lstrip('@')}")],
            [InlineKeyboardButton(text=T("b_joined")[:64], callback_data=f"fj:chk:{uid}")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("fj:"))
async def on_fj(q: CallbackQuery):
    if not await is_member(q.bot, q.from_user.id, fresh=True):
        return await q.answer(T("t_force_fail"), show_alert=True)
    await q.answer("✅")
    if isinstance(q.message, Message):
        text, kb = view_menu(q.from_user.id)
        await safe_edit(q.message, text, kb)


@router.callback_query(F.data.startswith("brk:"))
async def on_brk(q: CallbackQuery):
    """شکستن صیغه برادری (هر کدام از دو برادر می‌توانند بزنند)."""
    try:
        _, x, y = (q.data or "").split(":")
        x, y = int(x), int(y)
    except ValueError:
        return await q.answer()
    if q.from_user.id not in (x, y):
        return await q.answer("این صیغه به تو ربطی نداره پسرعمو 😐", show_alert=True)
    async with DB.tx() as c:
        await touch(c, q.from_user)
        n = await break_brothers(c, x, y)
        la, lb = await user_link(c, x), await user_link(c, y)
    if not n:
        return await q.answer("این صیغه قبلاً شکسته شده 💔", show_alert=True)
    await q.answer("صیغه شکسته شد 💔")
    if isinstance(q.message, Message):
        await safe_edit(q.message, T("t_bro_broken", a=la, b=lb), None)


@router.callback_query()
async def on_cb(q: CallbackQuery):
    parts = (q.data or "").split(":")
    try:
        owner = int(parts[-1])
    except (ValueError, IndexError):
        return await q.answer()
    if q.from_user.id != owner:
        return await q.answer(T("t_not_yours"), show_alert=True)
    if isinstance(q.message, Message) and q.message.chat.type == "private" and not is_admin(owner) \
            and not await is_member(q.bot, owner):
        return await q.answer(T("t_force_fail"), show_alert=True)
    try:
        async with DB.tx() as c:
            await touch(c, q.from_user)
            alert, view = await route(c, owner, parts[:-1])
    except Exception:
        log.exception("callback failed: %s", q.data)
        return await q.answer("خطایی پیش اومد پسرعمو، دوباره امتحان کن", show_alert=True)
    await q.answer((alert or "")[:200] or None, show_alert=bool(alert))
    msg = q.message
    if not view or not isinstance(msg, Message):
        return
    if view[0] == "__clear__":
        try:
            await msg.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
    elif view[0] == "__append__":
        base = (msg.html_text or "").rsplit("\n\n", 1)[0]
        await safe_edit(msg, clip(base + "\n\n" + view[1]), None)
    else:
        await safe_edit(msg, view[0], view[1])


# ════════════════════════════════════════════════════════════════════════════
#  دستورهای متنی
# ════════════════════════════════════════════════════════════════════════════
async def say(m: Message, text, kb=None):
    try:
        return await m.reply(text, reply_markup=kb)
    except TelegramBadRequest as e:
        if "parse" in str(e).lower() or "entit" in str(e).lower():  # متن/متغیر خراب HTML → ساده بفرست
            try:
                return await m.reply(text, reply_markup=kb, parse_mode=None)
            except TelegramBadRequest:
                pass
        try:
            return await m.answer(text, reply_markup=kb)
        except TelegramBadRequest as e2:
            log.warning("send failed: %s", e2)


async def cmd_menu(m: Message):
    text, kb = view_menu(m.from_user.id)
    await say(m, text, kb)


async def open_view(m: Message, builder):
    """باز کردن مستقیم یک منو (بانک، ملک، ...) با پیام جدید."""
    uid = m.from_user.id
    async with DB.tx() as c:
        await touch(c, m.from_user)
        text, kb = await builder(c, uid)
    await say(m, text, kb)


async def _bank(m):
    await open_view(m, view_bank)


async def _props(m):
    await open_view(m, view_props)


async def _shop(m):
    await open_view(m, lambda c, u: _async(view_shop(u)))


async def _daf(m):
    await open_view(m, lambda c, u: view_shop_cat(c, u, "daf"))


async def _inv(m):
    await open_view(m, view_inventory)


async def _kids(m):
    await open_view(m, view_kids)


async def _trade(m):
    uid = m.from_user.id
    await say(m, T("t_trade_menu"), mk([[btn(T("b_long_trade"), cd(uid, "trade", "long"))], back_row(uid)]))


async def _help(m):
    text, kb = view_help(m.from_user.id)
    await say(m, text, kb)


async def _mission(m):
    await say(m, T("t_mission"), mk([back_row(m.from_user.id)]))


async def _long_trade(m):
    await say(m, T("t_trade_long"))


async def _async(v):
    return v


async def cmd_profile(m: Message, username=None):
    viewer = m.from_user
    async with DB.tx() as c:
        await touch(c, viewer)
        target_id = viewer.id
        if username:
            r = await q1(c, "SELECT user_id FROM users WHERE username=? COLLATE NOCASE", (username,))
            if not r:
                return await say(m, "این کاربر رو پیدا نکردم پسرعمو 🤷‍♂️")
            target_id = r["user_id"]
        elif m.reply_to_message and m.reply_to_message.from_user and not m.reply_to_message.from_user.is_bot:
            await touch(c, m.reply_to_message.from_user)
            target_id = m.reply_to_message.from_user.id
        text, kb = await view_profile(c, target_id, viewer.id)
    await say(m, text, kb)


async def cmd_reward(m: Message, cmd):
    phrase, ttext, tcd, need, can_preg, _ = COMMANDS[cmd]
    u = m.from_user
    pid = None
    names = ""
    async with DB.tx() as c:
        await touch(c, u)
        if need:
            dafs = await daf_rows(c, u.id)  # فقط داف‌های اجاره‌ای فعال
            if len(dafs) < need:
                key = {"sex": "t_no_daf_sex", "sak": "t_no_daf_sak", "tri": "t_no_daf_tri"}.get(cmd, "t_no_daf_multi")
                return await say(m, T(key, need=need, cmd=phrase))
            pick = random.sample(dafs, 1 if cmd in ("sex", "sak") else need)
            names = " و ".join(esc(r["name"]) for r, _ in pick)
        cd_min = max(0, num(f"{cmd}_cd"))
        rem = await take_cooldown(c, u.id, cmd, cd_min * 60)
        if rem:
            return await say(m, T(tcd, n=minutes_left(rem), cmd=phrase))
        lo, hi = sorted((max(0, num(f"{cmd}_min")), max(0, num(f"{cmd}_max"))))
        reward = random.randint(lo, hi)
        await add_cash(c, u.id, reward, f"cmd_{cmd}")
        count = 0
        if can_preg and random.randint(1, 100) <= num("preg_chance"):
            w = [max(0, num(f"preg_w{i}")) for i in (1, 2, 3, 4)]
            count = random.choices([1, 2, 3, 4], weights=w if sum(w) > 0 else None, k=1)[0]
            pid = await ins(c, "INSERT INTO pregnancies(owner_id,kind,count,created_at) VALUES(?,?,?,?)",
                            (u.id, cmd, count, NOW()))
    text = T(ttext, reward=fmt(reward), cd=cd_min, daf=names)
    if pid:
        text += "\n\n" + T("t_preg", n=PREG_NAMES[count])
        kb = mk([[btn(T("b_keep"), cd(u.id, "preg", "keep", pid)), btn(T("b_abort"), cd(u.id, "preg", "abort", pid))]])
        return await say(m, text, kb)
    await say(m, text)


async def cmd_crime(m: Message, kind):
    """مفتبری (۵٪ نقد طرف؛ بالاخواه جلوشو می‌گیره) و دزدی (رت جلوشو می‌گیره) — با ریپلی."""
    what = "مفتبری" if kind == "mofte" else "دزدی"
    u = m.from_user
    r = m.reply_to_message
    if not r or not r.from_user or r.from_user.is_bot:
        return await say(m, T("t_crime_noreply", what=what))
    v = r.from_user
    if v.id == u.id:
        return await say(m, T("t_crime_self", what=what))
    pct = max(0, num("mofte_pct"))
    async with DB.tx() as c:
        await touch(c, u)
        await touch(c, v)
        left = await cd_peek(c, u.id, kind, max(0, num(f"{kind}_cd")) * 60)
        if left:
            return await say(m, T(f"t_{kind}_cd", n=minutes_left(left)))
        vcash = await get_cash(c, v.id)
        if vcash <= 0:
            return await say(m, T("t_crime_empty", what=what))
        bro = await brother_of(c, u.id)
        if bro == v.id:
            return await say(m, T("t_crime_bro"))
        await cd_set(c, u.id, kind)
        la, lv = await user_link(c, u.id), await user_link(c, v.id)
        if await has_effect(c, v.id, "guard" if kind == "mofte" else "rat"):
            if kind == "mofte":  # بالاخواه: ۵٪ پول مهاجم میره به قربانی
                pen = await get_cash(c, u.id) * pct // 100
                if pen:
                    await add_cash(c, u.id, -pen, "mofte_fined")
                    await add_cash(c, v.id, pen, "mofte_guard_gain")
                text = T("t_mofte_guard", n=fmt(pen))
            else:  # رت: جریمه‌ی ثابت از دزد
                pen = min(max(0, num("rat_fine")), await get_cash(c, u.id))
                if pen:
                    await add_cash(c, u.id, -pen, "dozd_fined")
                text = T("t_dozd_rat", n=fmt(pen))
        else:
            amt = min(vcash, max(1, vcash * pct // 100))
            await add_cash(c, v.id, -amt, f"{kind}_victim")
            if kind == "mofte" and bro:  # نصف به خودش، نصف به برادرش
                half = amt // 2
                await add_cash(c, bro, half, "mofte_bro")
                await add_cash(c, u.id, amt - half, "mofte_gain")
                text = T("t_mofte_bro", a=la, b=await user_link(c, bro), v=lv, n=fmt(amt))
            else:
                await add_cash(c, u.id, amt, f"{kind}_gain")
                text = T("t_mofte_ok" if kind == "mofte" else "t_dozd_ok", a=la, v=lv, n=fmt(amt))
    await say(m, text)


async def cmd_bro(m: Message):
    """صیغه برادری (با ریپلی)."""
    u = m.from_user
    r = m.reply_to_message
    if not r or not r.from_user or r.from_user.is_bot or r.from_user.id == u.id:
        return await say(m, T("t_bro_noreply"))
    v = r.from_user
    async with DB.tx() as c:
        await touch(c, u)
        await touch(c, v)
        if await brother_of(c, u.id):
            return await say(m, T("t_bro_self_has"))
        if await brother_of(c, v.id):
            return await say(m, T("t_bro_target_has"))
        await make_brothers(c, u.id, v.id)
        text = T("t_bro_ok", a=await user_link(c, u.id), b=await user_link(c, v.id))
    kb = mk([[InlineKeyboardButton(text=T("b_bro_break")[:64], callback_data=f"brk:{u.id}:{v.id}")]])
    await say(m, text, kb)


async def cmd_fit(m: Message):
    """فیت: فقط داخل گروه و فقط وقتی برادر داری؛ ۹۰٪ شانس، ۳۰۰ زی برای هر دو، محدودیت ۲ ساعت."""
    u = m.from_user
    if m.chat.type == "private":
        return await say(m, T("t_fit_private"))
    async with DB.tx() as c:
        await touch(c, u)
        bro = await brother_of(c, u.id)
        if not bro:
            return await say(m, T("t_fit_nobro"))
        secs = max(0, num("fit_cd")) * 60
        left = max(await cd_peek(c, u.id, "fit", secs), await cd_peek(c, bro, "fit", secs))
        if left:
            return await say(m, T("t_fit_cd", n=minutes_left(left)))
        await cd_set(c, u.id, "fit")
        await cd_set(c, bro, "fit")
        if random.randint(1, 100) <= num("fit_win"):
            n = max(0, num("fit_reward"))
            await add_cash(c, u.id, n, "fit")
            await add_cash(c, bro, n, "fit")
            text = T("t_fit_ok", a=await user_link(c, u.id), b=await user_link(c, bro), n=fmt(n))
        else:
            text = T("t_fit_fail")
    await say(m, text)


async def cmd_trick(m: Message, kind, act):
    u = m.from_user
    async with DB.tx() as c:
        await touch(c, u)
        status, data = await veh_trick(c, u.id, kind)
    text, kb = fmt_trick(u.id, kind, act, status, data)
    await say(m, text, kb)


async def cmd_use(m: Message, iid):
    u = m.from_user
    async with DB.tx() as c:
        await touch(c, u)
        status, data = await use_item(c, u.id, iid)
    text, kb = fmt_use(u.id, status, data)
    await say(m, text, kb)


async def cmd_gift(m: Message, code):
    u = m.from_user
    async with DB.tx() as c:
        await touch(c, u)
        _, msg = await gift_redeem(c, u.id, code)
    await say(m, msg)


async def cmd_gamble(m: Message, amount):
    u = m.from_user
    async with DB.tx() as c:
        await touch(c, u)
        cash = await get_cash(c, u.id)
        if amount <= 0 or amount > cash:
            return await say(m, T("t_no_cash", cash=fmt(cash)))
        won = random.randint(1, 100) <= num("gamble_win")
        await add_cash(c, u.id, amount if won else -amount, "gamble_win" if won else "gamble_lose")
        await run(c, "INSERT INTO gambling_history(user_id,bet,won,created_at) VALUES(?,?,?,?)",
                  (u.id, amount, int(won), NOW()))
        cash = await get_cash(c, u.id)
    await say(m, T("t_gamble_win" if won else "t_gamble_lose", bet=fmt(amount), cash=fmt(cash)))


async def cmd_trade(m: Message, amount):
    u = m.from_user
    async with DB.tx() as c:
        await touch(c, u)
        cash = await get_cash(c, u.id)
        if amount <= 0 or amount > cash:
            return await say(m, T("t_no_cash", cash=fmt(cash)))
        win = random.randint(1, 100) <= num("trade_win")
        if win:
            lo, hi = sorted((num("trade_gain_min"), num("trade_gain_max")))
        else:
            lo, hi = sorted((num("trade_loss_min"), num("trade_loss_max")))
        pct = random.randint(max(0, lo), max(0, hi))
        amt = max(1, amount * pct // 100)
        pnl = amt if win else -amt
        await add_cash(c, u.id, pnl, "trade_win" if win else "trade_lose")
        await run(c, "INSERT INTO trade_history(user_id,amount,pct,pnl,created_at) VALUES(?,?,?,?,?)",
                  (u.id, amount, pct, pnl, NOW()))
        cash = await get_cash(c, u.id)
    await say(m, T("t_trade_win" if win else "t_trade_lose", amount=fmt(amt), pct=pct, cash=fmt(cash)))


async def cmd_name_child(m: Message, number, name):
    u = m.from_user
    name = name.strip()
    if len(name) > 25:
        return await say(m, "اسم بچه نباید بیشتر از 25 حرف باشه پسرعمو")
    async with DB.tx() as c:
        await touch(c, u)
        n = await run(c, "UPDATE children SET name=? WHERE owner_id=? AND number=? AND status='kept'",
                      (name, u.id, number))
    if n != 1:
        return await say(m, f"بچه‌ای با شماره {number} نداری پسرعمو 👶")
    await say(m, f"✅ اسم بچه شماره {number} شد {esc(name)} 👶")


def _cat_opener(cat):
    async def f(m):
        await open_view(m, lambda c, u: view_shop_cat(c, u, cat))
    return f


def _trick_opener(kind, act):
    async def f(m):
        await cmd_trick(m, kind, act)
    return f


async def _crime_mofte(m):
    await cmd_crime(m, "mofte")


async def _crime_dozd(m):
    await cmd_crime(m, "dozd")


EXACT = {}
for _keys, _fn in [
    (("منو",), cmd_menu), (("بانک",), _bank), (("ملک", "املاک"), _props), (("فروشگاه",), _shop),
    (("داف ها", "دافها"), _daf), (("انبار", "انبار و فروش", "انبار و اوراقی"), _inv),
    (("بچه ها", "بچهها"), _kids), (("ترید",), _trade), (("راهنما",), _help),
    (("میشن", "میشن ها"), _mission), (("ترید بلندمدت", "ترید بلند مدت"), _long_trade),
    (("موجودی", "پروفایل"), cmd_profile),
    (("گان", "گان ها", "گانها", "اسلحه", "اسلحه ها"), _cat_opener("gun")),
    (("ماشین", "ماشین ها", "ماشینها"), _cat_opener("car")),
    (("موتور", "موتور ها", "موتورها"), _cat_opener("moto")),
    (("مشروب", "مشروبات", "نوشیدنی", "نوشیدنی ها"), _cat_opener("drink")),
    (("مخدر", "مخدرها", "مخدر ها"), _cat_opener("narc")),
    (("بالاخواه", "مواد بالاخواه"), _cat_opener("drug")),
    (("رت", "مخبر"), _cat_opener("rat")),
    (("تجهیزات", "تجهیزات و آرنا"), _cat_opener("gear")),
    (("مفتبری",), _crime_mofte), (("دزدی",), _crime_dozd),
    (("صیغه برادری", "صیغه"), cmd_bro), (("فیت",), cmd_fit),
    (("تک چرخ", "تکچرخ"), _trick_opener("moto", "tak")),
    (("لایی کشی", "لایی"), _trick_opener("car", "lai")),
    (("دریفت کشی", "دریفت", "دیریفت", "دیریفت کشی"), _trick_opener("car", "drift")),
]:
    for _k in _keys:
        EXACT[key_of(_k)] = _fn
REWARD_PHRASES = {key_of(v[0]): k for k, v in COMMANDS.items()}

_CHAT_SEEN = set()
_UMAP = {"ts": 0.0, "map": {}}


async def usable_map():
    """نام مشروب/مخدرهای قابل مصرف → آیدی (کش ۳۰ ثانیه‌ای)."""
    if time.time() - _UMAP["ts"] > 30:
        async with DB.tx() as c:
            rows = await qall(c, "SELECT id,name,category,extra FROM shop_items WHERE category IN ('drink','drug','narc') AND enabled=1")
        _UMAP["map"] = {key_of(r["name"]): r["id"] for r in rows if item_kind(r) in USABLE_KINDS}
        _UMAP["ts"] = time.time()
    return _UMAP["map"]


def _use_key(k):
    k = re.sub(r"^(بزن|مصرف کن|مصرف|بکش|بخور) ", "", k)
    return re.sub(r" (بزن|بکش|مصرف کن|مصرف|بخور)$", "", k)


async def remember_chat(m: Message):
    if m.chat.id in _CHAT_SEEN:
        return
    _CHAT_SEEN.add(m.chat.id)
    async with DB.tx() as c:
        await run(c, "INSERT OR REPLACE INTO chats(chat_id,type,title) VALUES(?,?,?)",
                  (m.chat.id, m.chat.type, m.chat.title or ""))


@router.message(CommandStart())
async def on_start(m: Message):
    if not m.from_user or m.from_user.is_bot:
        return
    await remember_chat(m)
    if m.chat.type == "private" and not is_admin(m.from_user.id) and not await is_member(m.bot, m.from_user.id):
        return await say(m, T("t_force_join"), join_kb(m.from_user.id))
    await cmd_menu(m)


@router.message(Command("admin"))
async def on_admin_cmd(m: Message):
    if not m.from_user or m.chat.type != "private":
        return
    if not ENV_ADMINS and not DB_ADMINS:  # اولین نفر مالک می‌شود
        async with DB.tx() as c:
            await set_setting(c, "admin_ids", str(m.from_user.id))
        DB_ADMINS.add(m.from_user.id)
        await m.answer("✅ تو به عنوان ادمین ثبت شدی.")
    if not is_admin(m.from_user.id):
        return await m.answer("دسترسی نداری 🚫")
    PENDING.pop(m.from_user.id, None)
    text, kb = adm_home()
    await m.answer(text, reply_markup=kb)


@router.my_chat_member()
async def on_added(ev: ChatMemberUpdated):
    if ev.chat.type in ("group", "supergroup") and ev.new_chat_member.status in ("member", "administrator") \
            and ev.old_chat_member.status in ("left", "kicked"):
        async with DB.tx() as c:
            await run(c, "INSERT OR REPLACE INTO chats(chat_id,type,title) VALUES(?,?,?)",
                      (ev.chat.id, ev.chat.type, ev.chat.title or ""))
        _CHAT_SEEN.add(ev.chat.id)
        try:
            await ev.bot.send_message(ev.chat.id, T("t_added"))
        except Exception:
            log.exception("welcome failed")


@router.message(F.text)
async def on_text(m: Message):
    u = m.from_user
    if not u or u.is_bot or not m.text:
        return
    raw = m.text
    if m.chat.type == "private" and is_admin(u.id):
        if u.id in PENDING and not raw.startswith("/"):
            return await admin_input(m)
        if key_of(raw) in ("پنل مدیریت", "پنل"):
            PENDING.pop(u.id, None)
            text, kb = adm_home()
            return await m.answer(text, reply_markup=kb)
    if raw.startswith("/"):
        return
    # جوین اجباری فقط در پیوی
    if m.chat.type == "private" and not is_admin(u.id) and not await is_member(m.bot, u.id):
        return await say(m, T("t_force_join"), join_kb(u.id))
    await remember_chat(m)
    s, k = soft(raw), key_of(raw)
    try:
        fn = EXACT.get(k)
        if fn:
            return await fn(m)
        if k in REWARD_PHRASES:
            return await cmd_reward(m, REWARD_PHRASES[k])
        mt = re.fullmatch(r"پروفایل @?(\w{3,32})", s)
        if mt:
            return await cmd_profile(m, mt.group(1))
        mt = re.fullmatch(r"قمار ([\d,]{1,20})", s)
        if mt:
            return await cmd_gamble(m, int(mt.group(1).replace(",", "") or 0))
        if k == "قمار":
            return await say(m, "فرمت: قمار 10000")
        mt = re.fullmatch(r"ترید ([\d,]{1,20})", s)
        if mt:
            return await cmd_trade(m, int(mt.group(1).replace(",", "") or 0))
        mt = re.fullmatch(r"اسم بچه (\d{1,3}) (.+)", s) or re.fullmatch(r"اسم بچه‌ (\d{1,3}) (.+)", s)
        if mt:
            return await cmd_name_child(m, int(mt.group(1)), mt.group(2))
        mt = re.fullmatch(r"کد(?: هدیه)? ([A-Za-z0-9_]{3,24})", s)
        if mt:
            return await cmd_gift(m, mt.group(1))
        resp = REPLIES.get(k)
        if resp:
            return await say(m, resp)
        umap = await usable_map()
        iid = umap.get(k) or umap.get(_use_key(k))
        if iid:
            return await cmd_use(m, iid)
    except Exception:
        log.exception("text handler failed: %r", raw)


# ════════════════════════════════════════════════════════════════════════════
#  پنل مدیریت
# ════════════════════════════════════════════════════════════════════════════
PENDING: dict = {}  # admin_id → حالت در انتظار ورودی
PAGE = 10


def ab(text, *parts):
    return btn(text, "adm:" + ":".join(str(p) for p in parts))


def adm_home():
    rows = [
        [ab("🏠 مدیریت املاک", "props"), ab("🛒 مدیریت فروشگاه", "shop")],
        [ab("🥃 مشروب و مخدر (سود/قیمت)", "drugs"), ab("🎁 کدهای هدیه", "gifts")],
        [ab("📝 مدیریت متن‌ها", "txt", "t", 0), ab("🔘 مدیریت دکمه‌ها", "txt", "b", 0)],
        [ab("⚙️ تنظیمات عددی", "num", 0), ab("👤 مدیریت کاربران", "users")],
        [ab("💬 پاسخ‌های ساده", "reps"), ab("📢 پیام همگانی", "cast")],
        [ab("📊 آمار", "stats"), ab("👑 ادمین‌ها", "admins")],
    ]
    return "🛠 پنل مدیریت یانگزی 👽\n\nیکی رو انتخاب کن:", mk(rows)


def parse_price(s):
    s = soft(s).replace(",", "")
    if s in ("-", "حذف", "هیچی", "none", "null", "خالی"):
        return True, None
    if re.fullmatch(r"\d{1,15}", s):
        return True, int(s)
    return False, None


def cancel_kb(back):
    return mk([[ab("❌ انصراف", *back)]])


def money_or(v):
    return "—" if v is None else fmt(v)


async def adm_props(c):
    rows = []
    for p in await qall(c, "SELECT * FROM properties ORDER BY sort_order, id"):
        off = "" if p["enabled"] else "🚫 "
        rows.append([ab(f"{off}{p['id']}. {prop_label(p)} | {money_or(p['price'])} | {money_or(p['income'])}",
                        "prop", p["id"])])
    rows.append([ab("➕ افزودن ملک", "padd")])
    rows.append([ab("🔙 بازگشت", "home")])
    period = fmt_period(num("prop_period_minutes"))
    return f"🏠 مدیریت املاک\n(نام | قیمت | سود هر {period})", mk(rows)


async def adm_prop(c, pid):
    p = await q1(c, "SELECT * FROM properties WHERE id=?", (pid,))
    if not p:
        return await adm_props(c)
    owners = (await q1(c, "SELECT COUNT(*) n FROM user_properties WHERE property_id=?", (pid,)))["n"]
    text = (f"🏠 ملک #{pid}\n\nنام: {esc(p['name'])}\nایموجی: {p['emoji'] or '—'}\nقیمت: {money_or(p['price'])}\n"
            f"سود هر {fmt_period(num('prop_period_minutes'))}: {money_or(p['income'])}\n"
            f"وضعیت: {'فعال ✅' if p['enabled'] else 'غیرفعال 🚫'}\nتعداد مالک‌ها: {owners}")
    rows = [[ab("✏️ نام", "pf", pid, "name"), ab("😀 ایموجی", "pf", pid, "emoji")],
            [ab("💰 قیمت", "pf", pid, "price"), ab("📈 سود هر دوره", "pf", pid, "income")],
            [ab("🔁 فعال/غیرفعال", "pt", pid), ab("🗑 حذف", "pd", pid)],
            [ab("🔙 بازگشت", "props")]]
    return text, mk(rows)


async def adm_shop_home():
    rows = [[ab(f"{label}", "sc", k)] for k, label in SHOP_CATS + HIDDEN_CATS]
    rows.append([ab("🔙 بازگشت", "home")])
    return "🛒 مدیریت فروشگاه\nدسته را انتخاب کن:", mk(rows)


async def adm_cat(c, cat):
    rows = []
    for it in await qall(c, "SELECT * FROM shop_items WHERE category=? ORDER BY sort_order, id", (cat,)):
        off = "" if it["enabled"] else "🚫 "
        rows.append([ab(f"{off}{it['id']}. {item_label(it)} | {money_or(it['price'])} | فروش {money_or(it['sell_price'])}"
                        + (f" | سود {money_or(it['profit'])}" if cat in ("drink", "drug", "narc") else ""),
                        "item", it["id"])])
    rows.append([ab("➕ افزودن محصول", "iadd", cat)])
    rows.append([ab("🔙 بازگشت", "shop")])
    return f"🛒 {ALL_CATS[cat]}\n(نام | قیمت خرید | قیمت فروش)", mk(rows)


async def adm_item(c, iid):
    it = await q1(c, "SELECT * FROM shop_items WHERE id=?", (iid,))
    if not it:
        return await adm_shop_home()
    kind = item_kind(it)
    text = (f"📦 محصول #{iid} ({ALL_CATS.get(it['category'], it['category'])})\n\nنام: {esc(it['name'])}\n"
            f"ایموجی: {it['emoji'] or '—'}\nقیمت خرید: {money_or(it['price'])}\nقیمت فروش: {money_or(it['sell_price'])}\n"
            f"وضعیت: {'فعال ✅' if it['enabled'] else 'غیرفعال 🚫'}\nنوع: {kind}")
    if kind in USABLE_KINDS:
        text += (f"\n\n💊 سود هر مصرف: {money_or(it['profit'])} (فعلی: {fmt(item_profit(it))})"
                 f"\n🔢 تعداد دفعات مصرف: {item_uses(it)}")
    if kind in STASH_KINDS or kind == "daf":
        text += f"\n⏳ مدت اعتبار: {fmt_hours(item_hours(it))}"
    rows = [[ab("✏️ نام", "if", iid, "name"), ab("😀 ایموجی", "if", iid, "emoji")],
            [ab("💰 قیمت خرید", "if", iid, "price"), ab("💸 قیمت فروش", "if", iid, "sell_price")]]
    if kind in USABLE_KINDS:
        rows.append([ab("💊 سود هر مصرف", "if", iid, "profit"), ab("🔢 تعداد مصرف", "if", iid, "max_uses")])
    if kind in STASH_KINDS or kind == "daf":
        rows.append([ab("⏳ مدت اعتبار (ساعت)", "if", iid, "dur_hours")])
    rows.append([ab("🔁 فعال/غیرفعال", "it", iid), ab("🗑 حذف", "idl", iid)])
    rows.append([ab("🔙 بازگشت", "sc", it["category"])])
    return text, mk(rows)


async def adm_drugs(c):
    rows = []
    for it in await qall(c, "SELECT * FROM shop_items WHERE category IN ('drink','drug','narc') ORDER BY category, sort_order, id"):
        if item_kind(it) not in USABLE_KINDS:
            continue
        off = "" if it["enabled"] else "🚫 "
        rows.append([ab(f"{off}{item_label(it)} | قیمت {money_or(it['price'])} | سود {fmt(item_profit(it))}", "item", it["id"])])
    rows.append([ab("🔙 بازگشت", "home")])
    return "🥃 مشروب و مخدر\n(نام | قیمت | سود هر مصرف) — برای ویرایش روی هر مورد بزن:", mk(rows)


async def adm_gifts(c):
    rows = []
    for g in await qall(c, "SELECT * FROM gift_codes ORDER BY created_at DESC LIMIT 40"):
        rows.append([ab(f"🎟 {g['code']} | {fmt(g['amount'])} | {g['used']}/{g['capacity']}", "gc", g["code"])])
    rows.append([ab("➕ ساخت کد هدیه", "gadd")])
    rows.append([ab("🔙 بازگشت", "home")])
    return "🎁 کدهای هدیه\n(کد | مبلغ | استفاده‌شده/ظرفیت)", mk(rows)


async def adm_gift(c, code):
    g = await q1(c, "SELECT * FROM gift_codes WHERE code=?", (code,))
    if not g:
        return await adm_gifts(c)
    if g["expires_at"]:
        exp = time.strftime("%Y-%m-%d %H:%M", time.localtime(g["expires_at"]))
        exp += " (منقضی شده ⌛)" if g["expires_at"] <= NOW() else ""
    else:
        exp = "بدون محدودیت زمانی"
    text = (f"🎁 کد هدیه <code>{esc(g['code'])}</code>\n\nموجودی (برای هر نفر): {fmt(g['amount'])} زی کوین\n"
            f"ظرفیت: {g['capacity']} نفر | استفاده‌شده: {g['used']}\nاعتبار تا: {exp}\n\n"
            f"کاربرها در گروه یا پیوی می‌نویسن: کد {esc(g['code'])}")
    return text, mk([[ab("🗑 حذف", "gdel", code)], [ab("🔙 بازگشت", "gifts")]])


def adm_keys(kind):
    pre = ("t_",) if kind == "t" else ("b_", "c_")
    keys = [k for k in DEFAULTS if k.startswith(pre)]
    if kind == "b":  # دکمه‌های حذف‌شده توی لیست اصلی نیستن (از «حذف‌شده‌ها» برمی‌گردن)
        keys = [k for k in keys if SET.get("bh_" + k) != "2"]
    return keys


NO_HIDE = {"b_join", "b_joined"}  # جوین اجباری نباید قابل مخفی شدن باشه
BTN_TEXT_KEY = {
    "b_shop": "t_shop", "b_profile": "t_profile", "b_props": "t_props", "b_bank": "t_bank", "b_inv": "t_inv",
    "b_trade": "t_trade_menu", "b_long_trade": "t_trade_long", "b_help": "t_help", "b_mission": "t_mission",
    "b_back": "t_menu", "b_help_daf": "t_help_daf", "b_help_mavad": "t_help_mavad", "b_help_rat": "t_help_rat",
    "b_help_bala": "t_help_bala", "b_help_back": "t_help", "b_condom": "t_condom_menu", "b_toy": "t_toy_menu",
    "b_keep": "t_keep_done", "b_abort": "t_abort_done", "b_buy": "t_item_confirm", "b_sell_ok": "t_sell_confirm",
    "b_od_go": "t_od_ok", "b_od_no": "t_od_cancel", "b_bro_break": "t_bro_broken", "b_withdraw": "t_bank",
    "b_deposit": "t_bank", "b_collect": "t_props", "b_refresh": "t_props", "b_join": "t_force_join",
    "b_joined": "t_force_fail", "b_inv_kids": "t_kids_title", "b_moto_sell": "t_moto_sell_confirm",
    "b_car_sell": "t_car_sell_confirm", "b_moto_svc": "t_moto_svc_done", "b_car_svc": "t_car_svc_done",
    "b_back_shop_menu": "t_shop", "b_back_store": "t_shop", "b_addgroup": "t_added",
}


def btn_text_key(key):
    """متنی که با زدن این دکمه نشون داده میشه (اگه وجود داشته باشه)."""
    tk = BTN_TEXT_KEY.get(key)
    if not tk and key.startswith("c_"):
        tk = "t_daf_menu" if key == "c_daf" else "t_shop_cat"
    return tk if tk in DEFAULTS else None


def adm_removed_btns():
    keys = [k for k in DEFAULTS if k[:2] in ("b_", "c_") and SET.get("bh_" + k) == "2"]
    rows = [[ab(f"♻️ {DEFAULTS[k][0]}", "bres", k)] for k in keys[:90]]
    if keys:
        rows.append([ab("♻️ بازگردانی همه", "bresall")])
    rows.append([ab("🔙 بازگشت", "txt", "b", 0)])
    return (f"🗑 دکمه‌های حذف‌شده ({len(keys)})\nروی هرکدوم بزنی دوباره برمی‌گرده:" if keys
            else "🗑 هیچ دکمه‌ای حذف نشده 👌"), mk(rows)


def adm_txt_list(kind, page):
    keys = adm_keys(kind)
    pages = max(1, math.ceil(len(keys) / PAGE))
    page = max(0, min(page, pages - 1))
    icon = "📝 " if kind == "t" else "🔘 "
    rows = [[ab(("🙈 " if SET.get("bh_" + k) == "1" else "") + ("✏️ " if k in SET else "") + icon + DEFAULTS[k][0],
                "te", k)] for k in keys[page * PAGE:(page + 1) * PAGE]]
    nav = []
    if page > 0:
        nav.append(ab("⬅️ قبلی", "txt", kind, page - 1))
    if page < pages - 1:
        nav.append(ab("بعدی ➡️", "txt", kind, page + 1))
    if nav:
        rows.append(nav)
    if kind == "b":
        nrm = sum(1 for k in DEFAULTS if k[:2] in ("b_", "c_") and SET.get("bh_" + k) == "2")
        rows.append([ab(f"🗑 حذف‌شده‌ها ({nrm})", "brm")])
    rows.append([ab("🔙 بازگشت", "home")])
    title = "📝 متن‌ها" if kind == "t" else "🔘 دکمه‌ها"
    note = "(✏️ یعنی تغییر داده شده)" if kind == "t" else "(✏️ تغییر نام داده شده | 🙈 مخفی) — روی هر دکمه بزن تا مخفی/حذف/تغییر نام/تغییر متن کنی"
    return f"{title} — صفحه {page + 1}/{pages}\n{note}", mk(rows)


def adm_text(key):
    label, default = DEFAULTS[key]
    cur = SET.get(key, default)
    ph = sorted(set(re.findall(r"\{(\w+)\}", default)))
    text = (f"✏️ {esc(label)}\n\nمتن فعلی:\n<code>{esc(cur)}</code>\n\n"
            f"جاهای خالی مجاز: {' '.join('{' + p + '}' for p in ph) if ph else 'ندارد'}")
    kind = "t" if key.startswith("t_") else "b"
    if kind == "t":
        rows = [[ab("✏️ تغییر", "tset", key), ab("♻️ پیش‌فرض", "trst", key)], [ab("🔙 بازگشت", "txt", kind, 0)]]
        return text, mk(rows)
    hid = SET.get("bh_" + key) == "1"
    text += f"\n\nوضعیت دکمه: {'🙈 مخفی' if hid else '👁 نمایش داده میشه'}"
    rows = []
    if key not in NO_HIDE:
        rows.append([ab("👁 نمایش دادن" if hid else "🙈 مخفی کردن", "bhide", key), ab("🗑 حذف دکمه", "bdel", key)])
    tk = btn_text_key(key)
    if tk:
        rows.append([ab("📝 تغییر متن این بخش", "te", tk)])
    rows.append([ab("✏️ تغییر نام", "tset", key), ab("♻️ پیش‌فرض", "trst", key)])
    rows.append([ab("🔙 بازگشت", "txt", kind, 0)])
    return text, mk(rows)


def adm_num_list(page):
    keys = list(NUMS)
    pages = math.ceil(len(keys) / PAGE)
    page = max(0, min(page, pages - 1))
    rows = [[ab(f"🔢 {NUMS[k][0]}: {num(k)}", "ne", k)] for k in keys[page * PAGE:(page + 1) * PAGE]]
    nav = []
    if page > 0:
        nav.append(ab("⬅️ قبلی", "num", page - 1))
    if page < pages - 1:
        nav.append(ab("بعدی ➡️", "num", page + 1))
    if nav:
        rows.append(nav)
    rows.append([ab("🔙 بازگشت", "home")])
    return f"⚙️ تنظیمات عددی — صفحه {page + 1}/{pages}", mk(rows)


def adm_num(key):
    label, default = NUMS[key]
    text = f"⚙️ {esc(label)}\n\nمقدار فعلی: {num(key)}\nپیش‌فرض: {default}"
    return text, mk([[ab("✏️ تغییر", "nset", key), ab("♻️ پیش‌فرض", "nrst", key)], [ab("🔙 بازگشت", "num", 0)]])


async def adm_user_card(c, uid):
    u = await q1(c, "SELECT * FROM users WHERE user_id=?", (uid,))
    if not u:
        return "کاربری با این آیدی پیدا نشد 🤷‍♂️", mk([[ab("🔙 بازگشت", "home")]])
    cnt = await inv_counts(c, uid)
    text = (f"👤 {esc(u['first_name'] or '')} (@{u['username'] or '—'})\nآیدی: <code>{uid}</code>\n\n"
            f"پول نقد: {fmt(await get_cash(c, uid))}\nبانک: {fmt(await get_bank(c, uid))}\n"
            f"داف‌ها: {cnt['daf']} | بچه‌ها: {cnt['kids']} | املاک: {cnt['props']}")
    rows = [[ab("➕ افزایش نقد", "ua", uid, "add"), ab("➖ کاهش نقد", "ua", uid, "sub")],
            [ab("✏️ تعیین نقد", "ua", uid, "setcash"), ab("🏦 تعیین بانک", "ua", uid, "setbank")],
            [ab("⏱ ریست محدودیت‌ها", "ucd", uid)], [ab("🔙 بازگشت", "home")]]
    return text, mk(rows)


async def adm_reps():
    rows = [[ab(f"🗑 {t} ⟵ {r}"[:60], "rdel", i)] for i, (t, r) in enumerate(REPLIES.items())]
    rows.append([ab("➕ افزودن پاسخ", "radd")])
    rows.append([ab("🔙 بازگشت", "home")])
    return "💬 پاسخ‌های ساده (عبارت ⟵ پاسخ)\nبرای حذف روی هر مورد بزن:", mk(rows)


async def adm_route(c, a, admin_id):
    s = a[0]
    sub = a[1] if len(a) > 1 else ""
    if s == "home":
        return None, adm_home()
    # ---- املاک
    if s == "props":
        return None, await adm_props(c)
    if s == "prop":
        return None, await adm_prop(c, int(sub))
    if s == "pt":
        await run(c, "UPDATE properties SET enabled=1-enabled WHERE id=?", (int(sub),))
        return None, await adm_prop(c, int(sub))
    if s == "pd":
        n = (await q1(c, "SELECT COUNT(*) n FROM user_properties WHERE property_id=?", (int(sub),)))["n"]
        if n:
            return f"این ملک {n} مالک داره؛ به‌جای حذف، غیرفعالش کن.", None
        await run(c, "DELETE FROM properties WHERE id=?", (int(sub),))
        return "🗑 حذف شد", await adm_props(c)
    if s == "pf":
        PENDING[admin_id] = {"act": "prop_field", "id": int(sub), "field": a[2]}
        hint = {"name": "نام جدید", "emoji": "ایموجی جدید (یا - برای حذف)",
                "price": "قیمت جدید (عدد، یا - برای بدون قیمت)", "income": "سود هر دوره (عدد، یا -)"}[a[2]]
        return None, (f"✏️ {hint} را بفرست:", cancel_kb(("prop", sub)))
    if s == "padd":
        PENDING[admin_id] = {"act": "prop_add"}
        return None, ("➕ نام ملک جدید را بفرست (ایموجی را بعداً می‌توانی بگذاری):", cancel_kb(("props",)))
    # ---- فروشگاه
    if s == "shop":
        return None, await adm_shop_home()
    if s == "sc":
        return None, await adm_cat(c, sub if sub in ALL_CATS else "daf")
    if s == "item":
        return None, await adm_item(c, int(sub))
    if s == "it":
        await run(c, "UPDATE shop_items SET enabled=1-enabled WHERE id=?", (int(sub),))
        return None, await adm_item(c, int(sub))
    if s == "idl":
        it = await q1(c, "SELECT * FROM shop_items WHERE id=?", (int(sub),))
        if it and await owned_any(c, it):
            return "کاربرانی این محصول رو دارن؛ به‌جای حذف، غیرفعالش کن.", None
        await run(c, "DELETE FROM shop_items WHERE id=?", (int(sub),))
        return "🗑 حذف شد", await adm_cat(c, it["category"] if it else "daf")
    if s == "if":
        PENDING[admin_id] = {"act": "item_field", "id": int(sub), "field": a[2]}
        hint = {"name": "نام جدید", "emoji": "ایموجی جدید (یا -)", "price": "قیمت خرید (عدد، یا - برای بدون قیمت)",
                "sell_price": "قیمت فروش (عدد، یا - برای غیرقابل فروش)",
                "profit": "سود هر بار مصرف (عدد، یا - برای پیش‌فرض)",
                "max_uses": "تعداد دفعات مصرف (عدد، یا - برای پیش‌فرض)",
                "dur_hours": "مدت اعتبار به ساعت (عدد، یا - برای پیش‌فرض)"}[a[2]]
        return None, (f"✏️ {hint} را بفرست:", cancel_kb(("item", sub)))
    if s == "iadd":
        PENDING[admin_id] = {"act": "item_add", "cat": sub}
        return None, ("➕ نام محصول جدید را بفرست:", cancel_kb(("sc", sub)))
    # ---- متن‌ها و دکمه‌ها
    if s == "txt":
        return None, adm_txt_list(sub, int(a[2]))
    if s == "te":
        return None, adm_text(sub)
    if s == "tset":
        PENDING[admin_id] = {"act": "text_set", "key": sub}
        return None, ("✏️ متن جدید را بفرست (همین‌طور که هست با همان خط‌ها ثبت می‌شود):", cancel_kb(("te", sub)))
    if s in ("bhide", "bdel", "bres") and not (sub in DEFAULTS and sub[:2] in ("b_", "c_")):
        return None, None
    if s == "bhide":
        cur = SET.get("bh_" + sub)
        await set_setting(c, "bh_" + sub, None if cur == "1" else "1")
        return ("👁 دکمه دوباره نمایش داده میشه" if cur == "1" else "🙈 دکمه مخفی شد"), adm_text(sub)
    if s == "bdel":
        await set_setting(c, "bh_" + sub, "2")
        return "🗑 دکمه حذف شد (از «حذف‌شده‌ها» برمی‌گرده)", adm_txt_list("b", 0)
    if s == "bres":
        await set_setting(c, "bh_" + sub, None)
        return "♻️ دکمه برگشت", adm_removed_btns()
    if s == "bresall":
        for k in [k for k in DEFAULTS if k[:2] in ("b_", "c_") and SET.get("bh_" + k) == "2"]:
            await set_setting(c, "bh_" + k, None)
        return "♻️ همه برگشتن", adm_removed_btns()
    if s == "brm":
        return None, adm_removed_btns()
    if s == "trst":
        await set_setting(c, sub, None)
        return "♻️ به حالت پیش‌فرض برگشت", adm_text(sub)
    # ---- اعداد
    if s == "num":
        return None, adm_num_list(int(sub))
    if s == "ne":
        return None, adm_num(sub)
    if s == "nset":
        PENDING[admin_id] = {"act": "num_set", "key": sub}
        return None, ("✏️ عدد جدید را بفرست:", cancel_kb(("ne", sub)))
    if s == "nrst":
        await set_setting(c, sub, None)
        return "♻️ به حالت پیش‌فرض برگشت", adm_num(sub)
    # ---- کاربران
    if s == "users":
        PENDING[admin_id] = {"act": "user_find"}
        return None, ("👤 آیدی عددی یا @یوزرنیم کاربر را بفرست:", cancel_kb(("home",)))
    if s == "ua":
        PENDING[admin_id] = {"act": "user_amt", "uid": int(sub), "op": a[2]}
        return None, ("مبلغ (عدد صحیح) را بفرست:", cancel_kb(("home",)))
    if s == "ucd":
        await run(c, "DELETE FROM cooldowns WHERE user_id=?", (int(sub),))
        return "⏱ محدودیت‌های کاربر ریست شد", await adm_user_card(c, int(sub))
    # ---- پاسخ‌های ساده
    if s == "reps":
        return None, await adm_reps()
    if s == "radd":
        PENDING[admin_id] = {"act": "rep_trigger"}
        return None, ("💬 عبارت محرک را بفرست (مثلاً: حلالت):", cancel_kb(("reps",)))
    if s == "rdel":
        trig = list(REPLIES)[int(sub)] if int(sub) < len(REPLIES) else None
        if trig:
            await run(c, "DELETE FROM simple_replies WHERE trigger=?", (trig,))
            REPLIES.pop(trig, None)
        return "🗑 حذف شد", await adm_reps()
    # ---- همگانی، آمار، ادمین‌ها
    if s == "cast":
        PENDING[admin_id] = {"act": "cast"}
        return None, ("📢 متن پیام همگانی را بفرست (به همه‌ی گروه‌ها و چت‌های ثبت‌شده می‌رود):", cancel_kb(("home",)))
    if s == "stats":
        r = await q1(c, "SELECT (SELECT COUNT(*) FROM users) u, (SELECT COALESCE(SUM(cash),0) FROM balances) cash, "
                        "(SELECT COALESCE(SUM(deposit),0) FROM bank) bank, "
                        "(SELECT COUNT(*) FROM children WHERE status='kept') k, (SELECT COUNT(*) FROM davas) d, "
                        "(SELECT COUNT(*) FROM chats) ch, (SELECT COUNT(*) FROM user_properties) p")
        text = (f"📊 آمار\n\nکاربران: {r['u']}\nچت‌ها: {r['ch']}\nمجموع پول نقد: {fmt(r['cash'])}\n"
                f"مجموع بانک: {fmt(r['bank'])}\nبچه‌ها: {r['k']}\nداف‌ها: {r['d']}\nملک‌های خریداری‌شده: {r['p']}")
        return None, (text, mk([[ab("🔙 بازگشت", "home")]]))
    if s == "admins":
        ids = sorted(ENV_ADMINS | DB_ADMINS)
        text = ("👑 ادمین‌ها\n\n" + "\n".join(f"<code>{i}</code>" for i in ids) +
                "\n\nادمین‌های ثابت از ADMIN_IDS می‌آیند.")
        return None, (text, mk([[ab("➕ افزودن ادمین", "aadd")], [ab("🔙 بازگشت", "home")]]))
    if s == "aadd":
        PENDING[admin_id] = {"act": "admin_add"}
        return None, ("آیدی عددی ادمین جدید را بفرست:", cancel_kb(("admins",)))
    if s == "drugs":
        return None, await adm_drugs(c)
    if s == "gifts":
        return None, await adm_gifts(c)
    if s == "gc":
        return None, await adm_gift(c, sub)
    if s == "gdel":
        await run(c, "DELETE FROM gift_codes WHERE code=?", (sub,))
        await run(c, "DELETE FROM gift_redeems WHERE code=?", (sub,))
        return "🗑 حذف شد", await adm_gifts(c)
    if s == "gadd":
        PENDING[admin_id] = {"act": "gift_code"}
        return None, ("🎁 کد هدیه را بفرست (حروف انگلیسی/عدد، ۳ تا ۲۴ کاراکتر) یا - برای ساخت خودکار:",
                      cancel_kb(("gifts",)))
    return None, None


async def owned_any(c, it):
    return await q1(c, "SELECT 1 FROM davas WHERE item_id=? UNION ALL SELECT 1 FROM condoms WHERE item_id=? AND qty>0 "
                       "UNION ALL SELECT 1 FROM inventory WHERE item_id=? AND qty>0 "
                       "UNION ALL SELECT 1 FROM stash WHERE item_id=? AND expires_at>? "
                       "UNION ALL SELECT 1 FROM vehicles WHERE item_id=? LIMIT 1",
                    (it["id"], it["id"], it["id"], it["id"], NOW(), it["id"])) is not None


async def admin_input(m: Message):
    """پردازش پاسخ ادمین به پرسش‌های پنل."""
    admin_id = m.from_user.id
    st = PENDING.get(admin_id)
    raw = (m.text or "").strip()
    if not st:
        return
    act = st["act"]

    async def reply_view(view, note=None):
        if note:
            await m.answer(note)
        await m.answer(view[0], reply_markup=view[1])

    if act == "cast":
        PENDING.pop(admin_id, None)
        async with DB.tx() as c:
            chats = [r["chat_id"] for r in await qall(c, "SELECT chat_id FROM chats")]
        ok = bad = 0
        for chat_id in chats:
            try:
                await m.bot.send_message(chat_id, raw)
                ok += 1
            except Exception:
                bad += 1
            await asyncio.sleep(0.05)
        return await m.answer(f"📢 ارسال شد: {ok} موفق، {bad} ناموفق")

    async with DB.tx() as c:
        if act == "prop_field":
            pid, field = st["id"], st["field"]
            if field in ("price", "income"):
                ok, val = parse_price(raw)
                if not ok:
                    return await m.answer("عدد صحیح بفرست (یا - برای حذف).")
            elif field == "emoji":
                val = "" if raw in ("-", "حذف") else raw[:8]
            else:
                val = raw[:40]
                if not val:
                    return await m.answer("نام خالی نمی‌شود.")
            await run(c, f"UPDATE properties SET {field}=? WHERE id=?", (val, pid))
            view = await adm_prop(c, pid)
        elif act == "prop_add":
            pid = await ins(c, "INSERT INTO properties(name,emoji,sort_order) VALUES(?,'',"
                               "(SELECT COALESCE(MAX(sort_order),0)+1 FROM properties))", (raw[:40],))
            view = await adm_prop(c, pid)
        elif act == "item_field":
            iid, field = st["id"], st["field"]
            if field in ("price", "sell_price", "profit", "max_uses", "dur_hours"):
                ok, val = parse_price(raw)
                if not ok:
                    return await m.answer("عدد صحیح بفرست (یا - برای حذف).")
            elif field == "emoji":
                val = "" if raw in ("-", "حذف") else raw[:8]
            else:
                val = raw[:50]
                if not val:
                    return await m.answer("نام خالی نمی‌شود.")
            await run(c, f"UPDATE shop_items SET {field}=? WHERE id=?", (val, iid))
            view = await adm_item(c, iid)
        elif act == "item_add":
            iid = await ins(c, "INSERT INTO shop_items(category,name,sort_order) VALUES(?,?,"
                               "(SELECT COALESCE(MAX(sort_order),0)+1 FROM shop_items))", (st["cat"], raw[:50]))
            view = await adm_item(c, iid)
        elif act == "text_set":
            val = raw.replace("\\n", "\n").replace("/n", "\n")
            default = DEFAULTS[st["key"]][1]
            try:
                probe = {p: "x" for p in re.findall(r"\{(\w+)\}", default)}
                val.format_map(_Safe(probe))
            except Exception:
                return await m.answer("⚠️ آکولادها درست نیست؛ فقط از جاهای خالی مجاز استفاده کن و دوباره بفرست.")
            await set_setting(c, st["key"], val)
            view = adm_text(st["key"])
        elif act == "num_set":
            s = soft(raw)
            if not re.fullmatch(r"-?\d{1,12}", s) or (int(s) < 0 and not st["key"].endswith("_income")):
                return await m.answer("یک عدد صحیح معتبر بفرست.")
            await set_setting(c, st["key"], int(s))
            view = adm_num(st["key"])
        elif act == "user_find":
            s = soft(raw)
            if re.fullmatch(r"\d{1,15}", s):
                tid = int(s)
            else:
                r = await q1(c, "SELECT user_id FROM users WHERE username=? COLLATE NOCASE", (s.lstrip("@"),))
                tid = r["user_id"] if r else 0
            view = await adm_user_card(c, tid)
        elif act == "user_amt":
            s = soft(raw).replace(",", "")
            if not re.fullmatch(r"\d{1,15}", s):
                return await m.answer("یک عدد صحیح و مثبت بفرست.")
            amt, tid, op = int(s), st["uid"], st["op"]
            if op in ("add", "sub"):
                ok = await add_cash(c, tid, amt if op == "add" else -amt, "admin_adjust")
                note = "✅ انجام شد" if ok else "⚠️ موجودی کاربر کافی نیست"
            elif op == "setcash":
                cur = await get_cash(c, tid)
                await add_cash(c, tid, amt - cur, "admin_set")
                note = "✅ انجام شد"
            else:
                await run(c, "UPDATE bank SET deposit=?, last_interest_ts=? WHERE user_id=?", (amt, NOW(), tid))
                note = "✅ انجام شد"
            await m.answer(note)
            view = await adm_user_card(c, tid)
        elif act == "rep_trigger":
            PENDING[admin_id] = {"act": "rep_resp", "trigger": key_of(raw)}
            return await m.answer("حالا متن پاسخ را بفرست:")
        elif act == "rep_resp":
            await run(c, "INSERT INTO simple_replies(trigger,response) VALUES(?,?) "
                         "ON CONFLICT(trigger) DO UPDATE SET response=excluded.response", (st["trigger"], raw))
            REPLIES[st["trigger"]] = raw
            view = await adm_reps()
        elif act == "admin_add":
            s = soft(raw)
            if not re.fullmatch(r"\d{1,15}", s):
                return await m.answer("آیدی عددی بفرست.")
            DB_ADMINS.add(int(s))
            await set_setting(c, "admin_ids", ",".join(str(i) for i in sorted(DB_ADMINS)))
            view = ("✅ ادمین اضافه شد.", mk([[ab("🔙 بازگشت", "admins")]]))
        elif act == "gift_code":
            code = soft(raw).upper()
            if code in ("-", ""):
                code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not re.fullmatch(r"[A-Z0-9_]{3,24}", code):
                return await m.answer("کد باید ۳ تا ۲۴ حرف انگلیسی/عدد باشه. دوباره بفرست.")
            if await q1(c, "SELECT 1 FROM gift_codes WHERE code=?", (code,)):
                return await m.answer("این کد قبلاً ساخته شده، یکی دیگه بفرست.")
            PENDING[admin_id] = {"act": "gift_amount", "code": code}
            return await m.answer(f"کد: {code}\nحالا موجودی (مبلغ زی کوین برای هر نفر) را بفرست:")
        elif act == "gift_amount":
            s = soft(raw).replace(",", "")
            if not re.fullmatch(r"\d{1,12}", s) or int(s) <= 0:
                return await m.answer("یک عدد صحیح و مثبت بفرست.")
            PENDING[admin_id] = {"act": "gift_cap", "code": st["code"], "amount": int(s)}
            return await m.answer("ظرفیت (تعداد نفراتی که می‌تونن استفاده کنن) را بفرست:")
        elif act == "gift_cap":
            s = soft(raw).replace(",", "")
            if not re.fullmatch(r"\d{1,9}", s) or int(s) <= 0:
                return await m.answer("یک عدد صحیح و مثبت بفرست.")
            PENDING[admin_id] = {"act": "gift_hours", "code": st["code"], "amount": st["amount"], "cap": int(s)}
            return await m.answer("مدت اعتبار را به ساعت بفرست (0 = بدون محدودیت زمانی):")
        elif act == "gift_hours":
            s = soft(raw)
            if not re.fullmatch(r"\d{1,6}", s):
                return await m.answer("یک عدد صحیح بفرست (0 = بدون محدودیت).")
            hrs = int(s)
            await run(c, "INSERT INTO gift_codes(code,amount,capacity,used,expires_at,created_at) VALUES(?,?,?,0,?,?)",
                      (st["code"], st["amount"], st["cap"], NOW() + hrs * 3600 if hrs else None, NOW()))
            view = await adm_gift(c, st["code"])
        else:
            PENDING.pop(admin_id, None)
            return
    PENDING.pop(admin_id, None)
    await reply_view(view, "✅ ثبت شد" if act not in ("user_amt", "user_find") else None)


@router.errors()
async def on_error(event):
    log.error("unhandled: %s", event.exception, exc_info=event.exception)
    return True


# ════════════════════════════════════════════════════════════════════════════
#  اجرا
# ════════════════════════════════════════════════════════════════════════════
async def main():
    global BOT_USERNAME
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN تنظیم نشده است.")
    await DB.connect()
    await migrate()
    await load_cache()
    if not ENV_ADMINS and not DB_ADMINS:
        log.warning("ADMIN_IDS خالی است؛ اولین نفری که در پیوی /admin بزند ادمین می‌شود.")
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True))
    me = await bot.get_me()
    BOT_USERNAME = me.username or BOT_USERNAME
    if getattr(me, "can_read_all_group_messages", True) is False:
        log.warning("Group Privacy ربات روشنه؛ در گروه فقط ریپلی‌ها/دستورها می‌رسه. در BotFather ← Bot Settings ← "
                    "Group Privacy ← Turn off (یا ربات را ادمین گروه کن) تا دستورها بدون ریپلی هم کار کنن.")
    if FORCE_CHANNEL:
        try:
            cm = await bot.get_chat_member(FORCE_CHANNEL, me.id)
            if str(getattr(cm.status, "value", cm.status)) not in ("administrator", "creator"):
                log.warning("ربات باید ادمین کانال %s باشه تا جوین اجباری کار کنه.", FORCE_CHANNEL)
        except Exception as e:
            log.warning("دسترسی به کانال %s ندارم (ربات را ادمین کانال کن): %s", FORCE_CHANNEL, e)
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=False)
    log.info("YANGZI BOT started as @%s", BOT_USERNAME)
    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "my_chat_member"])


if __name__ == "__main__":
    asyncio.run(main())
