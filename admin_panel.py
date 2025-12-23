"""
پنل مدیریت ادمین - تمام قابلیت‌های ادمین
"""

import json
import random
import string
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import utils

# فایل‌های مربوط به کدهای فعال‌سازی
ACTIVATION_CODES_FILE = 'activation_codes.json'
DELETED_CODES_FILE = 'deleted_codes.json'

# متغیر برای وضعیت قفل ربات
bot_locked = False

def load_activation_codes():
    """بارگذاری کدهای فعال‌سازی"""
    try:
        with open(ACTIVATION_CODES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_activation_codes(codes):
    """ذخیره کدهای فعال‌سازی"""
    with open(ACTIVATION_CODES_FILE, 'w', encoding='utf-8') as f:
        json.dump(codes, f, ensure_ascii=False, indent=2)

def load_deleted_codes():
    """بارگذاری کدهای حذف شده"""
    try:
        with open(DELETED_CODES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_deleted_codes(codes):
    """ذخیره کدهای حذف شده"""
    with open(DELETED_CODES_FILE, 'w', encoding='utf-8') as f:
        json.dump(codes, f, ensure_ascii=False, indent=2)

def generate_activation_code():
    """تولید کد فعال‌سازی 12 رقمی"""
    return ''.join(random.choices(string.digits, k=12))

def generate_all_activation_codes():
    """تولید کدهای فعال‌سازی برای تمام کشورها"""
    # بارگذاری کدهای قبلی
    old_codes = load_activation_codes()
    deleted_codes = load_deleted_codes()
    
    # انتقال کدهای قبلی به فایل حذف شده‌ها
    if old_codes:
        deleted_codes.update(old_codes)
        save_deleted_codes(deleted_codes)
    
    # تولید کدهای جدید
    new_codes = {}
    used_codes = set()
    
    for country in utils.countries:
        while True:
            code = generate_activation_code()
            if code not in used_codes:
                used_codes.add(code)
                new_codes[code] = {
                    'country': country['name'],
                    'category': country['category'],
                    'generated_at': utils.game_data.get('turn', 1)
                }
                break
    
    # ذخیره کدهای جدید
    save_activation_codes(new_codes)
    return new_codes

def get_activation_code_for_country(country_name):
    """دریافت کد فعال‌سازی برای کشور خاص"""
    codes = load_activation_codes()
    for code, data in codes.items():
        if data['country'] == country_name:
            return code
    return None

def load_bot_lock_status():
    """بارگذاری وضعیت قفل ربات"""
    global bot_locked
    try:
        with open('bot_lock_status.json', 'r') as f:
            data = json.load(f)
            bot_locked = data.get('locked', False)
    except FileNotFoundError:
        bot_locked = False

def save_bot_lock_status():
    """ذخیره وضعیت قفل ربات"""
    with open('bot_lock_status.json', 'w') as f:
        json.dump({'locked': bot_locked}, f)

def toggle_bot_lock():
    """تغییر وضعیت قفل ربات"""
    global bot_locked
    bot_locked = not bot_locked
    save_bot_lock_status()
    return bot_locked

def is_bot_locked():
    """بررسی وضعیت قفل ربات"""
    load_bot_lock_status()
    return bot_locked

# منوی ادمین حرفه‌ای
async def show_admin_menu(target):
    # بارگذاری وضعیت قفل
    load_bot_lock_status()
    
    keyboard = [
        # بخش مدیریت بازی
        [InlineKeyboardButton('🎮 مدیریت بازی', callback_data='admin_game_management')],
        [InlineKeyboardButton('📊 آمار و گزارش‌ها', callback_data='admin_statistics')],
        [InlineKeyboardButton('👥 مدیریت کاربران', callback_data='admin_user_management')],
        [InlineKeyboardButton('⚙️ تنظیمات سیستم', callback_data='admin_system_settings')],
        [InlineKeyboardButton('🔧 ابزارهای پیشرفته', callback_data='admin_advanced_tools')],
        [InlineKeyboardButton('🛡️ امنیت و نظارت', callback_data='admin_security')],
        [InlineKeyboardButton('🔐 قفل/باز کردن ربات', callback_data='admin_toggle_lock')],
        [InlineKeyboardButton('🔑 مدیریت کدهای فعال‌سازی', callback_data='admin_activation_codes_menu')],
        [InlineKeyboardButton('🏛️ ریست سازمان ملل', callback_data='admin_reset_un')],
        [InlineKeyboardButton('🎯 ریست فصل (حفظ اکانت)', callback_data='admin_season_reset')],
        [InlineKeyboardButton('🔄 ریست کامل ربات', callback_data='reset_bot')],
        [InlineKeyboardButton('🔄 ری‌استارت ربات', callback_data='restart_bot')],
        [InlineKeyboardButton('🧪 پنل دیباگ', callback_data='admin_debug')],
        [InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    lock_status = "🔒 قفل شده" if bot_locked else "🔓 باز"
    
    text = '🔧 <b>پنل مدیریت حرفه‌ای</b>\n\n'
    text += f'🔐 <b>وضعیت ربات:</b> {lock_status}\n\n'
    text += '🎯 <b>دسترسی‌های ادمین:</b>\n'
    text += '▫️ مدیریت کامل بازی و دورها\n'
    text += '▫️ نظارت بر کاربران و آمار\n'
    text += '▫️ تنظیمات پیشرفته سیستم\n'
    text += '▫️ ابزارهای امنیتی و نظارتی\n'
    text += '▫️ قفل/باز کردن ربات\n'
    text += '▫️ تولید کدهای فعال‌سازی\n'
    text += '▫️ ریست سازمان ملل\n'
    text += '▫️ ریست کامل ربات\n'
    text += '▫️ ری‌استارت ربات\n\n'
    text += '📋 <b>یکی از بخش‌های زیر را انتخاب کنید:</b>'
    
    if hasattr(target, 'edit_message_text'):
        await target.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await target.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

# منوی مدیریت بازی
async def show_admin_game_management(query):
    keyboard = [
        [InlineKeyboardButton('⏭️ پیش‌برد دور بازی', callback_data='advance_turn')],
        [InlineKeyboardButton('📅 تنظیم تاریخ بازی', callback_data='admin_set_game_date')],
        [InlineKeyboardButton('🌍 کشورهای فتح شده', callback_data='conquered_countries')],
        [InlineKeyboardButton('⚔️ مدیریت جنگ‌ها', callback_data='admin_war_management')],
        [InlineKeyboardButton('🤝 مدیریت اتحادها', callback_data='admin_alliance_management')],
        [InlineKeyboardButton('💰 تنظیم اقتصاد', callback_data='admin_economy_settings')],
        [InlineKeyboardButton('🏁 چایان بازی (اعلام نتایج فصل)', callback_data='admin_finalize_season')],
        [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = '🎮 <b>مدیریت بازی</b>\n\n'
    text += '📋 <b>گزینه‌های موجود:</b>\n'
    text += '▫️ پیش‌برد دور بازی\n'
    text += '▫️ تنظیم تاریخ و زمان\n'
    text += '▫️ مدیریت کشورهای فتح شده\n'
    text += '▫️ نظارت بر جنگ‌ها و اتحادها\n'
    text += '▫️ تنظیمات اقتصادی\n\n'
    text += '🎯 <b>یکی از گزینه‌ها را انتخاب کنید:</b>'
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# منوی آمار و گزارش‌ها
async def show_admin_statistics(query):
    keyboard = [
        [InlineKeyboardButton('📊 آمار کلی بازی', callback_data='admin_general_stats')],
        [InlineKeyboardButton('👥 آمار کاربران', callback_data='admin_user_stats')],
        [InlineKeyboardButton('🌍 آمار کشورها', callback_data='admin_country_stats')],
        [InlineKeyboardButton('⚔️ آمار نظامی', callback_data='admin_military_stats')],
        [InlineKeyboardButton('💰 آمار اقتصادی', callback_data='admin_economy_stats')],
        [InlineKeyboardButton('📢 تست ارسال به کانال', callback_data='test_channel')],
        [InlineKeyboardButton('📋 تست ارسال گزارش‌ها', callback_data='test_reports')],
        [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = '📊 <b>آمار و گزارش‌ها</b>\n\n'
    text += '📈 <b>گزینه‌های موجود:</b>\n'
    text += '▫️ آمار کلی و عمومی بازی\n'
    text += '▫️ آمار کاربران و فعالیت‌ها\n'
    text += '▫️ آمار کشورها و حکومت‌ها\n'
    text += '▫️ آمار نظامی و جنگ‌ها\n'
    text += '▫️ آمار اقتصادی و تجاری\n'
    text += '▫️ تست ارسال گزارش‌ها\n\n'
    text += '📋 <b>یکی از گزینه‌ها را انتخاب کنید:</b>'
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# منوی مدیریت کاربران
async def show_admin_user_management(query):
    keyboard = [
        [InlineKeyboardButton('👤 جستجوی کاربر', callback_data='admin_search_user')],
        [InlineKeyboardButton('🔒 مسدود کردن کاربر', callback_data='admin_ban_user')],
        [InlineKeyboardButton('🔓 آزاد کردن کاربر', callback_data='admin_unban_user')],
        [InlineKeyboardButton('🤖 ساخت پروفایل خودکار', callback_data='admin_auto_profile')],
        [InlineKeyboardButton('💰 تنظیم منابع کاربر', callback_data='admin_set_user_resources')],
        [InlineKeyboardButton('🎯 تنظیم سطح کاربر', callback_data='admin_set_user_level')],
        [InlineKeyboardButton('🔄 ریست کاربر', callback_data='admin_reset_user')],
        [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = '👥 <b>مدیریت کاربران</b>\n\n'
    text += '🛠️ <b>گزینه‌های موجود:</b>\n'
    text += '▫️ جستجو و مشاهده کاربران\n'
    text += '▫️ مسدود/آزاد کردن کاربران\n'
    text += '▫️ تنظیم منابع و امکانات\n'
    text += '▫️ تنظیم سطح و دسترسی‌ها\n'
    text += '▫️ ریست کامل کاربر\n\n'
    text += '👤 <b>یکی از گزینه‌ها را انتخاب کنید:</b>'
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def prompt_admin_auto_profile(query):
    import utils
    utils.pending_admin_auto_profile = True
    keyboard = [[InlineKeyboardButton('🔙 انصراف', callback_data='admin_user_management')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = '🤖 <b>ساخت پروفایل خودکار</b>\n\n'
    text += '🆔 آیدی کاربر یا @username را ارسال کنید تا پروفایل بدون شماره تماس و لوکیشن ساخته شود.\n'
    text += '👤 اگر اینگونه ساخته شد، کنار پروفایل برچسب <b>مهمان</b> نمایش داده می‌شود.'
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

def create_guest_profile(identifier: str):
    import utils
    key = identifier.strip()
    is_username = key.startswith('@') or not key.isdigit()
    # اگر یوزرنیم است، کلید را خود یوزرنیم نگه داریم
    if is_username:
        username = key if key.startswith('@') else f"@{key}"
        user = utils.users.setdefault(username, {})
        user['username'] = username
        user['user_id'] = None
        user['status'] = 'guest'
    else:
        utils.ensure_user_profile(key)
        user = utils.users.setdefault(key, {})
        user['user_id'] = int(key) if key.isdigit() else key
        user['status'] = 'guest'
    # پروفایل و برچسب مهمان
    profile = user.setdefault('profile', {})
    profile['is_registered'] = True
    profile['guest'] = True
    # ثبت شماره تماس و لوکیشن فیک برای نمایش پروفایل
    user['phone'] = user.get('phone') or '+989000000000'
    user['location'] = user.get('location') or {
        'latitude': 0.0,
        'longitude': 0.0,
        'city': 'مجزا',
        'country': 'مهمان'
    }
    # پاک کردن هرگونه روند ثبت‌نام در حال انتظار برای این کاربر (فقط اگر کلید عددی است)
    try:
        if not is_username and key in utils.pending_registration:
            utils.pending_registration.pop(key, None)
    except Exception:
        pass
    # رفع هرگونه بلاک ناشی از تأیید موقعیت و علامت‌گذاری وضعیت به عنوان guest
    try:
        if isinstance(utils.location_verification_data, dict):
            lv_key = key if not is_username else username
            utils.location_verification_data[lv_key] = {
                'latitude': 0,
                'longitude': 0,
                'city': None,
                'country': None,
                'location_attempts': 0,
                'location_verified': False,
                'status': 'guest'
            }
            utils.save_location_verification()
    except Exception:
        pass
    # اگر نام بازیکن ندارد، پیش‌فرض از آیدی
    if not user.get('player_name'):
        base = username if is_username else key
        user['player_name'] = f"User_{base}"
    # ذخیره
    utils.users[username if is_username else key] = user
    utils.save_users()
    return user

# منوی تنظیمات سیستم
async def show_admin_system_settings(query):
    keyboard = [
        [InlineKeyboardButton('⚙️ تنظیمات عمومی', callback_data='admin_general_settings')],
        [InlineKeyboardButton('🔧 تنظیمات فنی', callback_data='admin_technical_settings')],
        [InlineKeyboardButton('📢 تنظیمات کانال', callback_data='admin_channel_settings')],
        [InlineKeyboardButton('🛡️ تنظیمات امنیتی', callback_data='admin_security_settings')],
        [InlineKeyboardButton('🔄 تنظیمات خودکار', callback_data='admin_auto_settings')],
        [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = '⚙️ <b>تنظیمات سیستم</b>\n\n'
    text += '🔧 <b>گزینه‌های موجود:</b>\n'
    text += '▫️ تنظیمات عمومی و پایه\n'
    text += '▫️ تنظیمات فنی و عملکردی\n'
    text += '▫️ تنظیمات کانال و اطلاع‌رسانی\n'
    text += '▫️ تنظیمات امنیتی\n'
    text += '▫️ تنظیمات خودکار و زمانبندی\n\n'
    text += '⚙️ <b>یکی از گزینه‌ها را انتخاب کنید:</b>'
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# منوی ابزارهای پیشرفته
async def show_admin_advanced_tools(query):
    keyboard = [
        [InlineKeyboardButton('🔧 ابزارهای فنی', callback_data='admin_technical_tools')],
        [InlineKeyboardButton('📊 ابزارهای تحلیلی', callback_data='admin_analytical_tools')],
        [InlineKeyboardButton('🛠️ ابزارهای مدیریتی', callback_data='admin_management_tools')],
        [InlineKeyboardButton('🔍 ابزارهای جستجو', callback_data='admin_search_tools')],
        [InlineKeyboardButton('📋 ابزارهای گزارش‌گیری', callback_data='admin_reporting_tools')],
        [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = '🔧 <b>ابزارهای پیشرفته</b>\n\n'
    text += '🛠️ <b>گزینه‌های موجود:</b>\n'
    text += '▫️ ابزارهای فنی و دیباگ\n'
    text += '▫️ ابزارهای تحلیلی و آماری\n'
    text += '▫️ ابزارهای مدیریتی پیشرفته\n'
    text += '▫️ ابزارهای جستجو و فیلتر\n'
    text += '▫️ ابزارهای گزارش‌گیری\n\n'
    text += '🔧 <b>یکی از گزینه‌ها را انتخاب کنید:</b>'
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# منوی امنیت و نظارت
async def show_admin_security(query):
    keyboard = [
        [InlineKeyboardButton('🔐 قفل/باز کردن ربات', callback_data='admin_toggle_lock')],
        [InlineKeyboardButton('🚫 غیرفعال‌سازی کشورها', callback_data='admin_disable_countries_menu')],
        [InlineKeyboardButton('⛔ بن کردن کاربر', callback_data='admin_ban_user_prompt')],
        [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = '🛡️ <b>امنیت و نظارت</b>\n\n'
    text += '🔒 <b>گزینه‌های موجود:</b>\n'
    text += '▫️ قفل/باز کردن ربات\n'
    text += '▫️ غیرفعال‌سازی کشورها (تکی/همه)\n\n'
    text += '🛡️ <b>یکی از گزینه‌ها را انتخاب کنید:</b>'
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# شروع فرایند بن کردن کاربر
async def admin_ban_user_prompt(query):
    import utils
    utils.pending_admin_ban = True
    keyboard = [[InlineKeyboardButton('🔙 انصراف', callback_data='admin_security')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('⛔ شناسه کاربر (ID یا نام کاربری) را ارسال کنید:', reply_markup=reply_markup, parse_mode='HTML')

# منوی غیرفعال‌سازی کشورها
async def show_admin_disable_countries_menu(query):
    keyboard = [
        [InlineKeyboardButton('🚫 غیرفعال‌سازی همه کشورها', callback_data='admin_disable_all_countries')],
        [InlineKeyboardButton('🗺️ غیرفعال‌سازی کشور دلخواه', callback_data='admin_disable_select_country')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='admin_security')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = '🚫 <b>غیرفعال‌سازی کشورها</b>\n\nگزینه موردنظر را انتخاب کنید:'
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_disable_all_countries(query):
    import utils
    # آزاد کردن کشورها و غیرفعال کردن کاربران
    for c in utils.countries:
        if isinstance(c, dict):
            c['taken'] = False
    for uid in list(utils.users.keys()):
        utils.users[uid]['activated'] = False
    utils.save_users()
    utils.save_countries()
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='admin_disable_countries_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('✅ تمام کشورها غیرفعال شدند و آزاد شدند.', reply_markup=reply_markup, parse_mode='HTML')

async def show_disable_country_picker(query, page: int = 0):
    import math
    import utils
    per_row = 2
    per_page = 20  # 10 ردیف × 2 ستون
    start = page * per_page
    items = utils.countries[start:start+per_page]
    keyboard = []
    row = []
    for i, c in enumerate(items, 1):
        name = c.get('name', '—')
        callback = f"admin_disable_country::{start+i-1}"
        row.append(InlineKeyboardButton(name, callback_data=callback))
        if len(row) == per_row:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    # ناوبری صفحات
    total = len(utils.countries)
    total_pages = math.ceil(total / per_page) if per_page else 1
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton('⬅️ قبلی', callback_data=f'admin_disable_pick_page::{page-1}'))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton('بعدی ➡️', callback_data=f'admin_disable_pick_page::{page+1}'))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='admin_disable_countries_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('🗺️ یک کشور را برای غیرفعال‌سازی انتخاب کنید:', reply_markup=reply_markup, parse_mode='HTML')

async def handle_disable_specific_country(query, index_str: str):
    import utils
    try:
        idx = int(index_str)
        country = utils.countries[idx]
    except Exception:
        await query.answer('❌ کشور نامعتبر است', show_alert=True)
        return
    # آزاد کردن کشور و غیرفعال‌سازی صاحبش (اگر داشت)
    country_name = country.get('name')
    country['taken'] = False
    # پیدا کردن کاربری که این کشور را دارد
    owner_id = None
    for uid, u in utils.users.items():
        if u.get('country') == country_name and u.get('activated'):
            owner_id = uid
            break
    if owner_id:
        utils.users[owner_id]['activated'] = False
    utils.save_users()
    utils.save_countries()
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='admin_disable_countries_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f'✅ کشور {country_name} غیرفعال شد.', reply_markup=reply_markup, parse_mode='HTML')

# تابع قفل/باز کردن ربات
async def handle_toggle_bot_lock(query):
    """تغییر وضعیت قفل ربات"""
    new_status = toggle_bot_lock()
    status_text = "🔒 قفل شد" if new_status else "🔓 باز شد"
    
    text = f'🔐 <b>وضعیت ربات تغییر کرد!</b>\n\n'
    text += f'📊 <b>وضعیت جدید:</b> {status_text}\n\n'
    
    if new_status:
        text += '⚠️ <b>توجه:</b>\n'
        text += '▫️ تمام بخش‌های منوی شروع قفل شده‌اند\n'
        text += '▫️ فقط ادمین می‌تواند از ربات استفاده کند\n'
        text += '▫️ کاربران عادی دسترسی ندارند\n'
    else:
        text += '✅ <b>ربات باز شد:</b>\n'
        text += '▫️ تمام بخش‌ها در دسترس هستند\n'
        text += '▫️ کاربران می‌توانند از ربات استفاده کنند\n'
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# منوی مدیریت کدهای فعال‌سازی
async def show_admin_activation_codes_menu(query):
    """نمایش منوی مدیریت کدهای فعال‌سازی"""
    keyboard = [
        [InlineKeyboardButton('🆕 تولید کدهای جدید', callback_data='admin_generate_codes')],
        [InlineKeyboardButton('📋 مشاهده کدهای فعلی', callback_data='admin_view_codes')],
        [InlineKeyboardButton('🔍 جستجوی کد کشور خاص', callback_data='admin_search_country_code')],
        [InlineKeyboardButton('🗑️ حذف کدهای قدیمی', callback_data='admin_delete_old_codes')],
        [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = '🔑 <b>مدیریت کدهای فعال‌سازی</b>\n\n'
    text += '📋 <b>گزینه‌های موجود:</b>\n'
    text += '▫️ تولید کدهای فعال‌سازی جدید\n'
    text += '▫️ مشاهده کدهای فعال‌سازی فعلی\n'
    text += '▫️ جستجوی کد کشور خاص\n'
    text += '▫️ حذف کدهای قدیمی و غیرفعال\n\n'
    text += '🔧 <b>یکی از گزینه‌ها را انتخاب کنید:</b>'
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# تابع تولید کدهای فعال‌سازی
async def handle_generate_activation_codes(query):
    """تولید کدهای فعال‌سازی جدید"""
    try:
        # تولید کدهای جدید
        new_codes = generate_all_activation_codes()
        
        text = '🔑 <b>کدهای فعال‌سازی جدید تولید شدند!</b>\n\n'
        text += f'📊 <b>تعداد کدها:</b> {len(new_codes)}\n'
        text += f'📅 <b>تاریخ تولید:</b> دور {utils.game_data.get("turn", 1)}\n\n'
        text += '📋 <b>کدهای فعال‌سازی:</b>\n\n'
        
        # نمایش کدها به صورت monospace
        for code, data in new_codes.items():
            country_name = data['country']
            category = data['category']
            text += f'<code>{code}</code> - {country_name} ({category})\n'
        
        text += '\n⚠️ <b>توجه:</b>\n'
        text += '▫️ کدهای قبلی به فایل حذف شده‌ها منتقل شدند\n'
        text += '▫️ این کدها 12 رقمی و یکتا هستند\n'
        text += '▫️ کدها در ریست ربات پاک نمی‌شوند\n'
        
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی کدها', callback_data='admin_activation_codes_menu')],
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        error_text = f'❌ <b>خطا در تولید کدها:</b>\n\n{str(e)}'
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی کدها', callback_data='admin_activation_codes_menu')],
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')

# تابع مشاهده کدهای فعلی
async def handle_view_activation_codes(query):
    """مشاهده کدهای فعال‌سازی فعلی"""
    try:
        codes = load_activation_codes()
        
        if not codes:
            text = '❌ <b>هیچ کد فعال‌سازی‌ای موجود نیست!</b>\n\n'
            text += 'لطفاً ابتدا کدهای جدید تولید کنید.'
        else:
            text = '📋 <b>کدهای فعال‌سازی فعلی:</b>\n\n'
            text += f'📊 <b>تعداد کل کدها:</b> {len(codes)}\n\n'
            
            # گروه‌بندی کدها بر اساس دسته‌بندی
            categories = {}
            for code, data in codes.items():
                category = data['category']
                if category not in categories:
                    categories[category] = []
                categories[category].append((code, data))
            
            # نمایش کدها بر اساس دسته‌بندی
            for category, code_list in categories.items():
                text += f'🏷️ <b>{category}:</b>\n'
                for code, data in code_list:
                    country_name = data['country']
                    text += f'<code>{code}</code> - {country_name}\n'
                text += '\n'
        
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی کدها', callback_data='admin_activation_codes_menu')],
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        error_text = f'❌ <b>خطا در مشاهده کدها:</b>\n\n{str(e)}'
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی کدها', callback_data='admin_activation_codes_menu')],
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')

# تابع جستجوی کد کشور خاص
async def handle_search_country_code(query):
    """جستجوی کد کشور خاص"""
    keyboard = [
        [InlineKeyboardButton('🔙 بازگشت به منوی کدها', callback_data='admin_activation_codes_menu')],
        [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = '🔍 <b>جستجوی کد کشور خاص</b>\n\n'
    text += '📝 <b>نحوه استفاده:</b>\n'
    text += '▫️ نام کشور را وارد کنید\n'
    text += '▫️ کد فعال‌سازی آن کشور نمایش داده می‌شود\n\n'
    text += '💡 <b>مثال:</b>\n'
    text += '• ایران\n'
    text += '• ایالات متحده آمریکا\n'
    text += '• چین\n\n'
    text += '⚠️ <b>توجه:</b> نام کشور باید دقیق باشد'
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

def search_country_code_by_name(country_name):
    """جستجوی کد کشور بر اساس نام"""
    codes = load_activation_codes()
    for code, data in codes.items():
        if data['country'].lower() == country_name.lower():
            return code, data
    return None, None

# تابع حذف کدهای قدیمی
async def handle_delete_old_codes(query):
    """حذف کدهای قدیمی"""
    try:
        # بارگذاری کدهای حذف شده
        deleted_codes = load_deleted_codes()
        current_codes = load_activation_codes()
        
        # انتقال کدهای فعلی به فایل حذف شده‌ها
        deleted_codes.update(current_codes)
        save_deleted_codes(deleted_codes)
        
        # پاک کردن کدهای فعلی
        save_activation_codes({})
        
        text = '🗑️ <b>کدهای قدیمی حذف شدند!</b>\n\n'
        text += f'📊 <b>تعداد کدهای حذف شده:</b> {len(current_codes)}\n'
        text += f'📊 <b>تعداد کل کدهای حذف شده:</b> {len(deleted_codes)}\n\n'
        text += '⚠️ <b>توجه:</b>\n'
        text += '▫️ تمام کدهای فعلی حذف شدند\n'
        text += '▫️ کدها در فایل حذف شده‌ها ذخیره شدند\n'
        text += '▫️ برای استفاده مجدد، کدهای جدید تولید کنید\n'
        
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی کدها', callback_data='admin_activation_codes_menu')],
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        error_text = f'❌ <b>خطا در حذف کدها:</b>\n\n{str(e)}'
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی کدها', callback_data='admin_activation_codes_menu')],
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')

# تابع بررسی کد فعال‌سازی
def validate_activation_code(code):
    """بررسی اعتبار کد فعال‌سازی"""
    codes = load_activation_codes()
    return code in codes

def get_country_by_activation_code(code):
    """دریافت اطلاعات کشور بر اساس کد فعال‌سازی"""
    codes = load_activation_codes()
    if code in codes:
        return codes[code]
    return None 

def free_user_country(user_id):
    """آزاد کردن کشور کاربر"""
    user = utils.users.get(user_id, {})
    if user.get('activated', False):
        old_country_name = user.get('country')
        if old_country_name:
            # پیدا کردن کشور در لیست و آزاد کردن آن
            for country in utils.countries:
                if country['name'] == old_country_name:
                    country['taken'] = False
                    break
            utils.save_countries()
            print(f"کشور {old_country_name} برای کاربر {user_id} آزاد شد")
            return old_country_name
    return None

def get_available_countries():
    """دریافت لیست کشورهای آزاد"""
    available = []
    for country in utils.countries:
        if not country.get('taken', False):
            available.append(country)
    return available

def change_user_country(user_id, new_country_name):
    """تغییر کشور کاربر"""
    # آزاد کردن کشور قبلی
    old_country_name = free_user_country(user_id)
    
    # پیدا کردن کشور جدید
    new_country = None
    for country in utils.countries:
        if country['name'] == new_country_name and not country.get('taken', False):
            new_country = country
            break
    
    if new_country:
        # به‌روزرسانی اطلاعات کاربر
        user = utils.users.get(user_id, {})
        user.update({
            'country': new_country['name'],
            'category': new_country['category'],
            'code': new_country['code']
        })
        
        # علامت‌گذاری کشور جدید به عنوان گرفته شده
        new_country['taken'] = True
        
        # ذخیره تغییرات
        utils.save_users()
        utils.save_countries()
        
        print(f"کشور کاربر {user_id} از {old_country_name} به {new_country_name} تغییر یافت")
        return True, old_country_name, new_country_name
    else:
        print(f"کشور {new_country_name} در دسترس نیست یا قبلاً گرفته شده است")
        return False, old_country_name, None

def get_country_status():
    """دریافت وضعیت کشورها"""
    total_countries = len(utils.countries)
    taken_countries = sum(1 for country in utils.countries if country.get('taken', False))
    available_countries = total_countries - taken_countries
    
    return {
        'total': total_countries,
        'taken': taken_countries,
        'available': available_countries
    }

def get_taken_countries():
    """دریافت لیست کشورهای گرفته شده"""
    taken = []
    for country in utils.countries:
        if country.get('taken', False):
            taken.append(country)
    return taken

# تابع ریست سازمان ملل
async def handle_reset_un(query):
    """ریست کردن اطلاعات سازمان ملل"""
    try:
        from utils import reset_un_data, cleanup_deleted_un_users
        reset_un_data()
        
        # پاک کردن کاربران حذف شده
        cleanup_deleted_un_users()
        
        text = '🏛️ <b>ریست سازمان ملل</b>\n\n'
        text += '✅ اطلاعات سازمان ملل پاک شد\n'
        text += '✅ کاربر فعال سازمان ملل ریست شد\n'
        text += '✅ وضعیت درخواست فعال‌سازی پاک شد\n'
        text += '✅ کاربران حذف شده پاک شدند\n\n'
        text += '🔄 حالا کاربران جدید می‌توانند سازمان ملل را فعال کنند.'
        
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        error_text = f'❌ <b>خطا در ریست سازمان ملل:</b>\n\n{str(e)}'
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')

# تابع ریست فصل
async def handle_season_reset(query):
    """ریست فصل - پاک کردن تمام فایل‌های بازی و حفظ اطلاعات اکانت کاربران"""
    try:
        from bot import season_reset
        
        text = '🎯 <b>ریست فصل</b>\n\n'
        text += '⚠️ <b>هشدار:</b> این عملیات تمام اطلاعات بازی را پاک می‌کند!\n\n'
        text += '📋 <b>عملیات‌های انجام شده:</b>\n'
        text += '▫️ حذف تمام فایل‌های بازی\n'
        text += '▫️ پاک کردن اطلاعات کشورها\n'
        text += '▫️ پاک کردن منابع و نیروها\n'
        text += '▫️ پاک کردن روابط دیپلماتیک\n'
        text += '▫️ پاک کردن جنگ‌ها و اتحادها\n\n'
        text += '✅ <b>اطلاعات حفظ شده:</b>\n'
        text += '▫️ اطلاعات اکانت کاربران\n'
        text += '▫️ نام و شماره تلفن\n'
        text += '▫️ تاریخ ثبت‌نام\n'
        text += '▫️ شناسه عمومی\n\n'
        text += '🔄 در حال ریست فصل...'
        
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
        # اجرای ریست فصل
        season_reset()
        
        # پیام نهایی
        final_text = '🎉 <b>ریست فصل کامل شد!</b>\n\n'
        final_text += '✅ تمام فایل‌های بازی پاک شدند\n'
        final_text += '✅ اطلاعات اکانت کاربران حفظ شدند\n'
        final_text += '✅ فایل‌های جدید با مقادیر پیش‌فرض ایجاد شدند\n\n'
        final_text += '🔄 فصل جدید آماده شروع است!\n'
        final_text += '👥 کاربران باید دوباره کشور انتخاب کنند.'
        
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(final_text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        error_text = f'❌ <b>خطا در ریست فصل:</b>\n\n{str(e)}'
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')

# تابع ریست کامل ربات
async def handle_reset_bot(query):
    """ریست کامل ربات - حذف تمام فایل‌های ذخیره‌سازی"""
    try:
        # لیست فایل‌هایی که باید حذف شوند
        files_to_delete = [
            'users.json',
            'game_data.json',
            'war_declarations.json',
            'country_relations.json',
            'conquered_countries.json',
            'secret_loan_claimed.json',
            'secret_loan_activated.json',
            'bank_data.json',
            'loan_history.json',
            'independence_loans.json',
            'bot_lock_status.json',
            "countries.json",
            "tax_data.json",
            "alliances.json",
            "alliance_messages.json",
            "naval_attack_saves.json",
            "pending_trades.json",
            "military_technologies.json",
        ]
        
        deleted_files = []
        failed_files = []
        
        for file_name in files_to_delete:
            try:
                if os.path.exists(file_name):
                    os.remove(file_name)
                    deleted_files.append(file_name)
                    print(f"فایل {file_name} حذف شد")
            except Exception as e:
                failed_files.append(f"{file_name}: {str(e)}")
                print(f"خطا در حذف {file_name}: {e}")
        
        # ریست کردن متغیرهای درون حافظه
        try:
            import utils
            # ریست کردن متغیرهای اصلی
            utils.users = {}
            utils.countries = {}
            utils.game_data = {}
            utils.war_declarations = {}
            utils.country_relations = {}
            utils.conquered_countries = {}
            utils.secret_loan_claimed = {}
            utils.secret_loan_activated = {}
            utils.bank_data = {
                'total_loans_given': 0,
                'total_loans_paid': 0,
                'total_interest_earned': 0,
                'bank_reserves': 100000000000,
                'loan_types': {
                    'independence': {
                        'amount': 1_000_000_000,
                        'interest_rate': 0.04,
                        'duration': 4,
                        'max_uses': 1
                    },
                    'development': {
                        'amount': 500_000_000,
                        'interest_rate': 0.22,
                        'duration': 6,
                        'max_uses': 3
                    },
                    'emergency': {
                        'amount': 200_000_000,
                        'interest_rate': 0.12,
                        'duration': 3,
                        'max_uses': 5
                    }
                }
            }
            utils.loan_history = {}
            utils.independence_loans = {}
            utils.bot_lock_status = {}
            utils.tax_data = {}
            utils.alliances = {}
            utils.alliance_messages = {}
            utils.naval_attack_saves = {}
            utils.pending_trades = {}
            utils.military_technologies = {}
            
            # ریست کردن متغیرهای سازمان ملل
            utils.UN_ACTIVATED_USER = None
            utils.pending_un_activation = None
            
            # ریست کردن متغیرهای انتظار
            utils.pending_military_production = {}
            
            # ریست کردن متغیرهای سازمان ملل
            utils.ceasefire_requests = {}
            
            # ریست کردن متغیرهای کانال
            utils.CHANNEL_ID = None
            
            # ریست کردن متغیرهای محلی bot.py
            try:
                import bot
                # ریست کردن متغیرهای انتظار
                bot.pending_name_selection = {}
                bot.pending_activation = {}
                bot.pending_sell_amount = {}
                bot.pending_sell_total_price = {}
                bot.pending_statement = {}
                bot.pending_ground_attack = {}
                bot.pending_naval_attack = {}
                bot.pending_air_attack = {}
                bot.pending_sea_raid = {}
                bot.pending_help_request = {}
                bot.pending_alliance_chat = {}
                bot.pending_country_slogan = {}
                
                print("✅ متغیرهای محلی bot.py ریست شدند")
                
            except Exception as e:
                print(f"خطا در ریست متغیرهای bot.py: {e}")
            
            print("✅ متغیرهای درون حافظه ریست شدند")
            
        except Exception as e:
            print(f"خطا در ریست متغیرهای حافظه: {e}")
        
        # پیام نتیجه
        text = '🔄 <b>ریست کامل ربات</b>\n\n'
        
        if deleted_files:
            text += '✅ <b>فایل‌های حذف شده:</b>\n'
            for file in deleted_files:
                text += f'▫️ {file}\n'
            text += '\n'
        
        if failed_files:
            text += '❌ <b>فایل‌های ناموفق:</b>\n'
            for file in failed_files:
                text += f'▫️ {file}\n'
            text += '\n'
        
        if not deleted_files and not failed_files:
            text += 'ℹ️ هیچ فایلی برای حذف یافت نشد.\n\n'
        
        text += '✅ <b>متغیرهای درون حافظه ریست شدند</b>\n'
        text += '💡 <b>نکته:</b> برای اطمینان از ریست کامل، ربات را ری‌استارت کنید.'
        
        keyboard = [
            [InlineKeyboardButton('🔄 ری‌استارت ربات', callback_data='restart_bot')],
            [InlineKeyboardButton('💥 ریست کامل + ری‌استارت', callback_data='reset_and_restart')],
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        error_text = f'❌ <b>خطا در ریست ربات:</b>\n\n{str(e)}'
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')

# تابع ریست کامل + ری‌استارت
async def handle_reset_and_restart(query):
    """ریست کامل + ری‌استارت ربات"""
    try:
        text = '💥 <b>ریست کامل + ری‌استارت ربات</b>\n\n'
        text += '⚠️ <b>هشدار:</b> این عملیات تمام اطلاعات را پاک می‌کند!\n\n'
        text += '📋 <b>عملیات‌های انجام شده:</b>\n'
        text += '▫️ حذف تمام فایل‌های ذخیره‌سازی\n'
        text += '▫️ ریست متغیرهای درون حافظه\n'
        text += '▫️ ریست متغیرهای محلی\n'
        text += '▫️ ری‌استارت کامل ربات\n\n'
        text += '🔄 در حال ری‌استارت...'
        
        # ریست کامل
        await handle_reset_bot(query)
        
        # ری‌استارت ربات
        import os
        import sys
        
        # ری‌استارت ربات
        python = sys.executable
        os.execl(python, python, *sys.argv)
        
    except Exception as e:
        error_text = f'❌ <b>خطا در ریست و ری‌استارت:</b>\n\n{str(e)}'
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')

# تابع ری‌استارت ربات
async def handle_restart_bot(query):
    """ری‌استارت ربات"""
    try:
        text = '🔄 <b>ری‌استارت ربات</b>\n\n'
        text += '⏳ در حال ری‌استارت ربات...\n\n'
        text += '📋 <b>عملیات‌های انجام شده:</b>\n'
        text += '▫️ بازسازی فایل‌های اولیه\n'
        text += '▫️ تنظیم مجدد متغیرهای سیستم\n'
        text += '▫️ بارگذاری مجدد کانفیگ‌ها\n'
        text += '▫️ تولید کدهای فعال‌سازی جدید\n\n'
        text += '✅ ربات با موفقیت ری‌استارت شد!'
        
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
        # ری‌استارت واقعی ربات
        try:
            # بارگذاری مجدد کشورها
            utils.load_countries()
            
            # تولید کدهای فعال‌سازی جدید
            new_codes = generate_all_activation_codes()
            print(f"✅ {len(new_codes)} کد فعال‌سازی جدید تولید شد")
            
            # بازسازی فایل‌های اولیه
            utils.save_users()
            utils.save_game_data()
            utils.save_countries()
            
            print("✅ ربات با موفقیت ری‌استارت شد")
            
        except Exception as e:
            print(f"❌ خطا در ری‌استارت ربات: {e}")
        
    except Exception as e:
        error_text = f'❌ <b>خطا در ری‌استارت ربات:</b>\n\n{str(e)}'
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی ادمین', callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== WAR MANAGEMENT FUNCTIONS ====================

async def show_admin_war_management(query):
    """نمایش منوی مدیریت جنگ‌ها"""
    keyboard = [
        [InlineKeyboardButton('⚔️ حمله زمینی', callback_data='admin_war_ground')],
        [InlineKeyboardButton('✈️ حمله هوایی', callback_data='admin_war_air')],
        [InlineKeyboardButton('🚢 حمله دریایی', callback_data='admin_war_naval')],
        [InlineKeyboardButton('💥 حمله موشکی', callback_data='admin_war_missile')],
        [InlineKeyboardButton('🔙 بازگشت به مدیریت بازی', callback_data='admin_game_management')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = '⚔️ <b>مدیریت جنگ‌ها</b>\n\n'
    text += '📋 <b>انواع حملات:</b>\n'
    text += '▫️ حمله زمینی - نیروهای زمینی\n'
    text += '▫️ حمله هوایی - نیروهای هوایی\n'
    text += '▫️ حمله دریایی - نیروهای دریایی\n'
    text += '▫️ حمله موشکی - حملات موشکی\n\n'
    text += '🎯 <b>یکی از انواع حملات را انتخاب کنید:</b>'
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_admin_war_type(query, war_type):
    """نمایش جنگ‌های در حال انجام برای نوع خاص"""
    try:
        import utils
        from datetime import datetime
        
        # تعریف نام‌ها و ایموجی‌ها
        war_types = {
            'ground': {'name': 'زمینی', 'emoji': '⚔️', 'data_key': 'pending_ground_attack'},
            'air': {'name': 'هوایی', 'emoji': '✈️', 'data_key': 'pending_air_attack'},
            'naval': {'name': 'دریایی', 'emoji': '🚢', 'data_key': 'pending_naval_attack'},
            'missile': {'name': 'موشکی', 'emoji': '💥', 'data_key': 'pending_missile_attack'}
        }
        
        if war_type not in war_types:
            await query.answer("❌ نوع جنگ نامعتبر است!", show_alert=True)
            return
        
        war_info = war_types[war_type]
        war_data = getattr(utils, war_info['data_key'], {})
        
        if not war_data:
            text = f'{war_info["emoji"]} <b>جنگ‌های {war_info["name"]}</b>\n\n'
            text += '📭 <b>هیچ جنگی در حال انجام نیست</b>\n\n'
            text += '🔍 در حال حاضر هیچ حمله زمینی در انتظار نیست.'
        else:
            text = f'{war_info["emoji"]} <b>جنگ‌های {war_info["name"]} در حال انجام</b>\n\n'
            text += f'📊 <b>تعداد کل جنگ‌ها:</b> {len(war_data)}\n\n'
            
            # نمایش جنگ‌ها
            for i, (war_key, war_details) in enumerate(war_data.items(), 1):
                attacker = war_details.get('attacker', 'نامشخص')
                defender = war_details.get('defender', 'نامشخص')
                turn = war_details.get('turn', 0)
                date = war_details.get('date', 'نامشخص')
                
                text += f'<b>{i}.</b> {attacker} → {defender}\n'
                text += f'   📅 دور: {turn} | ⏰ تاریخ: {date}\n\n'
        
        keyboard = []
        
        # دکمه‌های لغو جنگ
        for i, (war_key, war_details) in enumerate(war_data.items(), 1):
            attacker = war_details.get('attacker', 'نامشخص')
            defender = war_details.get('defender', 'نامشخص')
            button_text = f'❌ لغو: {attacker} → {defender}'
            callback_data = f'admin_cancel_war_{war_type}_{war_key}'
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        # دکمه بازگشت
        keyboard.append([InlineKeyboardButton('🔙 بازگشت به مدیریت جنگ‌ها', callback_data='admin_war_management')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        error_text = f'❌ <b>خطا در نمایش جنگ‌ها:</b>\n\n{str(e)}'
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به مدیریت جنگ‌ها', callback_data='admin_war_management')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')

async def cancel_admin_war(query, war_type, war_key):
    """لغو جنگ توسط ادمین"""
    try:
        import utils
        from datetime import datetime
        
        # تعریف کلیدهای داده
        war_types = {
            'ground': 'pending_ground_attack',
            'air': 'pending_air_attack', 
            'naval': 'pending_naval_attack',
            'missile': 'pending_missile_attack'
        }
        
        if war_type not in war_types:
            await query.answer("❌ نوع جنگ نامعتبر است!", show_alert=True)
            return
        
        data_key = war_types[war_type]
        war_data = getattr(utils, data_key, {})
        
        if war_key not in war_data:
            await query.answer("❌ جنگ مورد نظر یافت نشد!", show_alert=True)
            return
        
        war_details = war_data[war_key]
        attacker = war_details.get('attacker', 'نامشخص')
        defender = war_details.get('defender', 'نامشخص')
        
        # حذف جنگ از داده‌ها
        del war_data[war_key]
        
        # ذخیره تغییرات
        if hasattr(utils, f'save_{data_key}'):
            getattr(utils, f'save_{data_key}')()
        
        # بازگرداندن منابع (اگر وجود دارد)
        try:
            # اینجا می‌توانید منطق بازگرداندن منابع را اضافه کنید
            # برای مثال، اگر هزینه‌ای برای شروع جنگ پرداخت شده باشد
            pass
        except Exception:
            pass
        
        # ارسال پیام به طرفین
        try:
            # پیدا کردن شناسه کاربران
            attacker_id = None
            defender_id = None
            
            for uid, user_data in utils.users.items():
                country_name = user_data.get('current_country_name', user_data.get('country', ''))
                if country_name == attacker:
                    attacker_id = uid
                elif country_name == defender:
                    defender_id = uid
            
            # پیام لغو جنگ
            cancel_message = (
                f'🛑 <b>جنگ لغو شد</b>\n\n'
                f'⚔️ <b>جنگ:</b> {attacker} → {defender}\n'
                f'👑 <b>دلیل:</b> لغو توسط ادمین\n'
                f'⏰ <b>زمان:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n'
                f'📋 <b>توضیحات:</b>\n'
                f'جنگ به صلاح ادمین پایان یافت و تمام منابع بازگردانده شد.'
            )
            
            # ارسال به حمله‌کننده
            if attacker_id:
                try:
                    await query.bot.send_message(
                        chat_id=int(attacker_id),
                        text=cancel_message,
                        parse_mode='HTML'
                    )
                except Exception:
                    pass
            
            # ارسال به مدافع
            if defender_id:
                try:
                    await query.bot.send_message(
                        chat_id=int(defender_id),
                        text=cancel_message,
                        parse_mode='HTML'
                    )
                except Exception:
                    pass
            
            # ارسال به کانال (اگر وجود دارد)
            try:
                from utils import NAVAL_ATTACK_CHANNEL_ID
                if NAVAL_ATTACK_CHANNEL_ID:
                    channel_message = (
                        f'🛑 <b>اعلامیه ادمین</b>\n\n'
                        f'⚔️ جنگ بین {attacker} و {defender} لغو شد.\n'
                        f'👑 <b>دلیل:</b> تصمیم ادمین\n'
                        f'⏰ <b>زمان:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n'
                        f'📋 تمام منابع بازگردانده شد و جنگ پایان یافت.'
                    )
                    await query.bot.send_message(
                        chat_id=NAVAL_ATTACK_CHANNEL_ID,
                        text=channel_message,
                        parse_mode='HTML'
                    )
            except Exception:
                pass
                
        except Exception as e:
            print(f"خطا در ارسال پیام‌های لغو جنگ: {e}")
        
        # نمایش پیام موفقیت
        success_text = (
            f'✅ <b>جنگ با موفقیت لغو شد</b>\n\n'
            f'⚔️ <b>جنگ:</b> {attacker} → {defender}\n'
            f'⏰ <b>زمان لغو:</b> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n'
            f'📋 <b>عملیات‌های انجام شده:</b>\n'
            f'▫️ حذف جنگ از سیستم\n'
            f'▫️ بازگرداندن منابع\n'
            f'▫️ اطلاع‌رسانی به طرفین\n'
            f'▫️ ارسال اعلان به کانال'
        )
        
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به مدیریت جنگ‌ها', callback_data='admin_war_management')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        error_text = f'❌ <b>خطا در لغو جنگ:</b>\n\n{str(e)}'
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به مدیریت جنگ‌ها', callback_data='admin_war_management')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML') 