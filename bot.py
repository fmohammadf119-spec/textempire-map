import json
import time
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import os
from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from datetime import datetime, timedelta
import random
from telegram.error import TelegramError
from uuid import uuid4
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, JobQueue
import utils
from utils import (
    ADMIN_ID,
    ADMIN_USERNAME,
    NEWS_CHANNEL_ID,
    NAVAL_ATTACK_CHANNEL_ID,
    user_alliances,
    format_price_short, 
    alliance_leave_turn,
    alliances,
    save_alliances,
    save_users,
    save_country_relations,
    save_countries,
    LAND_BORDERS,
    SEA_BORDER_COUNTRIES,
    save_game_data,
    pending_alliance_chat,
    pending_help_request,
    pending_ground_attack,
    pending_air_attack,
    pending_naval_attack,
    pending_create_alliance,
    countries,
    # users,  # حذف شد چون از utils.users استفاده می‌کنیم
    game_data, 
    update_prices, 
    global_market_inventory, 
    save_global_market,
    BUILDINGS,
    PRODUCTION_RECIPES,
    initialize_user_resources,
    calculate_total_economy,
    get_user_activated,
    check_message_ownership,
    pending_activation,
    pending_sell_amount,
    pending_sell_total_price,
    MILITARY_PRODUCTION_RECIPES,
    load_game_data,
    load_alliances,
    load_country_relations,
    load_global_market,
    war_declarations,
    pending_trades,
    pending_payments,
    country_relations,
    pending_military_production,
    add_missiles_per_turn,
    player_sell_ads,
    save_player_sell_ads,
    load_military_technologies,
    military_technologies,
    give_all_techs_level_one,
    calculate_military_power_with_tech,
    save_naval_attack_saves,
    load_naval_attack_saves,
    save_war_declarations,
    load_war_declarations,
    relation_improvement_requests,
    pending_statement,
    independence_loans,
    save_independence_loans,
    conquered_countries_data,
    save_conquered_countries_data,
    load_independence_loans,
    load_conquered_countries_data,
    pending_sea_raid,
    pending_government_selection,
    pending_name_selection,
pending_country_slogan,
    pending_minister_selection,
    pending_general_selection,
    pending_foreign_selection,
    pending_finance_selection,
    MILITARY_PACKAGES,
    military_package_purchases,
    military_package_cooldowns,
    military_package_approvals,
    save_military_package_data,
    ECONOMIC_PACKAGES,
    economic_package_purchases,
    economic_package_cooldowns,
    economic_package_approvals,
    save_economic_package_data,
    RESOURCE_PACKAGES,
    resource_package_purchases,
    resource_package_cooldowns,
    resource_package_approvals,
    save_resource_package_data,
    save_pending_payments,
    get_user_capital
)
from utils import pending_assassination, pending_assassination_respawn

from government import GOVERNMENT_TYPES, OFFICIAL_TITLES, get_country_officials, create_government_selection_keyboard, create_name_selection_keyboard, generate_name_suggestions, get_short_government_title, format_government_info
from united_nations import is_un_user

# Import پنل ادمین
import admin_panel


# Bot instance exported for other modules (e.g., diplomaci.py announcements)
bot: Bot = Bot(token=utils.BOT_TOKEN)





# ==================== Ground Attack UI (New) ====================
GROUND_UNITS_ORDER = [
    ('soldiers', '🪖 سربازان'),
    ('special_forces', '⚔️ نیروی ویژه'),
    ('tanks', '🛡️ تانک'),
    ('armored_vehicles', '🚛 نفربر'),
    ('war_robots', '🤖 ربات جنگی'),
]

def get_ground_unit_label(unit_key: str) -> str:
    """تبدیل کلید واحد به نام فارسی"""
    unit_dict = dict(GROUND_UNITS_ORDER)
    return unit_dict.get(unit_key, unit_key)

def _is_active_war_between(c1: str, c2: str) -> bool:
    try:
        for _, w in utils.war_declarations.items():
            if not isinstance(w, dict):
                continue
            if w.get('status', 'active') == 'ended':
                continue
            a = w.get('attacker'); d = w.get('defender')
            if (a == c1 and d == c2) or (a == c2 and d == c1):
                return True
    except Exception:
        pass
    return False

async def show_ground_attack_menu(query):
    user_id = str(query.from_user.id)
    # بررسی دسترسی نظامی
    try:
        access_allowed, error_message = check_military_access(user_id)
        if not access_allowed:
            await query.edit_message_text(error_message)
            return
    except Exception:
        pass
    text = 'استراتژی > حمله زمینی\n\nیک کشور هدف انتخاب کنید.'
    keyboard = [[InlineKeyboardButton('لیست کشورها', callback_data='ground_targets')],
                [InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_ground_targets(query):
    user_id = str(query.from_user.id)
    user_country = utils.users.get(user_id, {}).get('country', '')
    borders = utils.get_effective_land_borders(user_id)
    eligible = []
    for uid, u in utils.users.items():
        if uid == user_id:
            continue
        target_country = u.get('country', '')
        if not target_country or target_country not in borders:
            continue
        try:
            if is_user_peace_protected(uid):
                continue
        except Exception:
            pass
        if not _is_active_war_between(user_country, target_country):
            continue
        eligible.append((uid, target_country))
    if not eligible:
        await query.edit_message_text('هیچ کشور واجد شرایطی برای حمله زمینی وجود ندارد.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='ground_attack')]]))
        return
    text = 'کشور هدف را انتخاب کنید:'
    keyboard = []
    row = []
    for tid, name in eligible:
        row.append(InlineKeyboardButton(name, callback_data=f'ground_target_{tid}'))
        if len(row) == 2:
            keyboard.append(row); row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='ground_attack')])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_ground_force_picker(query, target_id: str):
    user_id = str(query.from_user.id)
    if user_id not in utils.pending_ground_attack:
        utils.pending_ground_attack[user_id] = {'target': utils.users.get(target_id, {}).get('country', ''), 'target_id': target_id, 'forces': {}, 'await_unit': None}
    st = utils.pending_ground_attack[user_id]
    inv = utils.users[user_id].get('resources', {})
    lines = [f"🎯 هدف: {utils.users.get(target_id, {}).get('country', '')}", '', 'موجودی شما:']
    for key, label in GROUND_UNITS_ORDER:
        lines.append(f"- {label.split(' ',1)[-1]}: {int(inv.get(key, 0)):,}")
    lines.append('')
    lines.append('نیروهای انتخاب‌شده:')
    for key, label in GROUND_UNITS_ORDER:
        sel = int(st.get('forces', {}).get(key, 0))
        lines.append(f"{label}:\n {sel:,}")
    keyboard = []
    row = []
    for key, label in GROUND_UNITS_ORDER:
        row.append(InlineKeyboardButton(label, callback_data=f'ground_unit_{key}_{target_id}'))
        if len(row) == 2:
            keyboard.append(row); row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton('✅ تایید حمله', callback_data=f'ground_confirm_{target_id}'), InlineKeyboardButton('❌ لغو', callback_data='cancel_ground_attack')])
    await query.edit_message_text('\n'.join(lines), reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_ground_unit_click(query, unit_key: str, target_id: str):
    user_id = str(query.from_user.id)
    if user_id not in utils.pending_ground_attack:
        utils.pending_ground_attack[user_id] = {'target': utils.users.get(target_id, {}).get('country', ''), 'target_id': target_id, 'forces': {}, 'await_unit': None}
    utils.pending_ground_attack[user_id]['await_unit'] = unit_key
    unit_label = get_ground_unit_label(unit_key)
    await query.edit_message_text(f'تعداد {unit_label} را وارد کنید (فقط عدد).\n\nبرای لغو، "لغو" را بفرستید.')

async def handle_ground_confirm(query, target_id: str, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(query.from_user.id)
    st = utils.pending_ground_attack.get(user_id)
    if not st or st.get('target_id') != target_id:
        await query.answer('درخواست نامعتبر است.', show_alert=True)
        return
    forces = {k: int(v) for k, v in (st.get('forces') or {}).items() if int(v) > 0}
    if not forces:
        await query.answer('هیچ نیرویی انتخاب نشده است.', show_alert=True)
        return
    inv = utils.users[user_id].get('resources', {})
    lacking = []
    for k, v in forces.items():
        if int(inv.get(k, 0)) < v:
            lacking.append(f"{get_ground_unit_label(k)}: {int(inv.get(k,0)):,}/{v:,}")
    if lacking:
        await query.edit_message_text('❌ نیروهای کافی ندارید:\n' + '\n'.join(lacking), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data=f'ground_target_{target_id}')]]))
        return
    for k, v in forces.items():
        utils.users[user_id]['resources'][k] = int(utils.users[user_id]['resources'].get(k, 0)) - v
    try:
        utils.save_users()
    except Exception:
        pass
    st['forces'] = forces
    utils.pending_ground_attack[user_id] = st
    from battle import start_ground_battle
    class _Msg:
        def __init__(self, uid): self.from_user = type('U', (), {'id': int(uid)})
        async def reply_text(self, t, **kw):
            try:
                await query.message.reply_text(t, **kw)
            except Exception:
                pass
    await start_ground_battle(_Msg(user_id), st, context)

async def process_ground_unit_amount(message, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(message.from_user.id)
    st = utils.pending_ground_attack.get(user_id)
    if not st or not st.get('await_unit'):
        return False
    unit = st['await_unit']
    text = (message.text or '').strip()
    
    # بررسی لغو
    if text.lower() in ['لغو', 'cancel', 'انصراف', 'بازگشت', 'stop', 'خروج', 'exit']:
        st['await_unit'] = None
        utils.pending_ground_attack[user_id] = st
        class _Q:
            def __init__(self, msg): self.from_user = msg.from_user
            async def edit_message_text(self, t, **kw):
                await message.reply_text(t, **kw)
        await show_ground_force_picker(_Q(message), st['target_id'])
        return True
    
    try:
        amount_text = text.replace(',', '')
        amount = int(amount_text)
        if amount < 0:
            raise ValueError()
    except Exception:
        await message.reply_text('❌ مقدار نامعتبر است. یک عدد صحیح وارد کنید یا "لغو" بفرستید.')
        return True
    st.setdefault('forces', {})
    st['forces'][unit] = amount
    print(f"[DEBUG] Saved force: {unit} = {amount}, all forces: {st['forces']}")
    st['await_unit'] = None
    utils.pending_ground_attack[user_id] = st
    class _Q:
        def __init__(self, msg): self.from_user = msg.from_user
        async def edit_message_text(self, t, **kw):
            await message.reply_text(t, **kw)
    await show_ground_force_picker(_Q(message), st['target_id'])
    return True

# ==================== NEW REFUGEE SYSTEM ====================

# ذخیره درخواست‌های پناهندگی فعال
ACTIVE_REFUGEE_REQUESTS = {}

# توابع persist کردن درخواست‌های پناهندگی
def save_refugee_requests():
    """ذخیره درخواست‌های پناهندگی در فایل"""
    try:
        with open('refugee_requests.json', 'w', encoding='utf-8') as f:
            json.dump(ACTIVE_REFUGEE_REQUESTS, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG][REFUGEE_SAVE] Saved {len(ACTIVE_REFUGEE_REQUESTS)} requests to file")
    except Exception as e:
        print(f"[ERROR][REFUGEE_SAVE] خطا در ذخیره refugee_requests: {e}")
        import traceback
        traceback.print_exc()

def load_refugee_requests():
    """بارگذاری درخواست‌های پناهندگی از فایل"""
    global ACTIVE_REFUGEE_REQUESTS
    try:
        with open('refugee_requests.json', 'r', encoding='utf-8') as f:
            loaded = json.load(f)
            print(f"[DEBUG][REFUGEE_LOAD] Loaded {len(loaded)} requests from file")
            # پاک کردن درخواست‌های منقضی شده (بیشتر از 7 روز - زمان کافی برای پاسخ)
            current_time = time.time()
            expired_count = 0
            ACTIVE_REFUGEE_REQUESTS = {}
            for req_id, req_data in loaded.items():
                req_timestamp = req_data.get('timestamp', 0)
                age_seconds = current_time - req_timestamp
                if age_seconds < 604800:  # 7 روز (604800 ثانیه)
                    ACTIVE_REFUGEE_REQUESTS[req_id] = req_data
                else:
                    expired_count += 1
                    print(f"[DEBUG][REFUGEE_LOAD] Request {req_id} expired (age: {age_seconds/3600:.1f} hours)")
            
            print(f"[DEBUG][REFUGEE_LOAD] Active requests: {len(ACTIVE_REFUGEE_REQUESTS)}, Expired: {expired_count}")
            # اگر درخواست‌هایی پاک شدند، فایل رو آپدیت کن
            if expired_count > 0:
                save_refugee_requests()
    except FileNotFoundError:
        print("[DEBUG][REFUGEE_LOAD] File not found, starting with empty dict")
        ACTIVE_REFUGEE_REQUESTS = {}
    except Exception as e:
        print(f"[ERROR][REFUGEE_LOAD] خطا در بارگذاری refugee_requests: {e}")
        import traceback
        traceback.print_exc()
        ACTIVE_REFUGEE_REQUESTS = {}

async def broadcast_refugee_offers(war_id, attacker_country, defender_country):
    """ارسال پیشنهاد پناهندگی به کشورها پس از اعلان جنگ"""
    try:
        # پیدا کردن کشورهای فعال (به جز طرفین جنگ)
        available_countries = []
        for uid, user in utils.users.items():
            if (user.get('profile', {}).get('is_registered', False) or 
                user.get('profile', {}).get('guest', False) or 
                user.get('activated', False)):
                country = user.get('country', '')
                if country and country not in [attacker_country, defender_country]:
                    available_countries.append((uid, country))
        
        # انتخاب 5 کشور تصادفی
        if len(available_countries) > 5:
            selected_countries = random.sample(available_countries, 5)
        else:
            selected_countries = available_countries
        
        # ارسال درخواست به هر کشور
        for uid, country in selected_countries:
            refugee_count = random.randint(1000000, 10000000)  # 1-10 میلیون
            request_id = f"{attacker_country}_{defender_country}_{uid}_{int(time.time())}"
            
            # ذخیره درخواست
            ACTIVE_REFUGEE_REQUESTS[request_id] = {
                'attacker_country': attacker_country,
                'defender_country': defender_country,
                'target_uid': uid,
                'target_country': country,
                'refugee_count': refugee_count,
                'timestamp': time.time()
            }
            
            # ایجاد دکمه‌ها
            keyboard = [
                [InlineKeyboardButton('✅ بپذیر', callback_data=f'new_refugee_accept_{request_id}')],
                [InlineKeyboardButton('❌ رد کن', callback_data=f'new_refugee_reject_{request_id}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # پیام درخواست
            refugee_text = (
                f"🛂 <b>درخواست پناهندگی</b>\n\n"
                f"در پی درگیری نظامی بین {attacker_country} و {defender_country}\n"
                f"حدود {refugee_count:,} نفر درخواست پناهندگی به کشور شما داده‌اند.\n\n"
                f"آیا می‌خواهید این مهاجران را بپذیرید؟"
            )
            
            # ارسال پیام (بدون context، فقط ذخیره درخواست)
            # پیام‌ها در نوبت بعدی ارسال خواهند شد
            print(f"Refugee request created for {country}: {refugee_count:,} refugees")
            
    except Exception as e:
        print(f"Error in broadcast_refugee_offers: {e}")

async def send_refugee_requests_to_random_countries(attacker_country, defender_country, context):
    """ارسال درخواست پناهندگی به 5 کشور تصادفی"""
    try:
        # پیدا کردن کشورهای فعال (به جز طرفین جنگ)
        available_countries = []
        for uid, user in utils.users.items():
            if (user.get('profile', {}).get('is_registered', False) or 
                user.get('profile', {}).get('guest', False) or 
                user.get('activated', False)):
                country = user.get('country', '')
                if country and country not in [attacker_country, defender_country]:
                    available_countries.append((uid, country))
        
        # انتخاب 5 کشور تصادفی
        if len(available_countries) > 5:
            selected_countries = random.sample(available_countries, 5)
        else:
            selected_countries = available_countries
        
        # ارسال درخواست به هر کشور
        for uid, country in selected_countries:
            refugee_count = random.randint(1000000, 10000000)  # 1-10 میلیون
            # ساخت یک شناسه کوتاه و ایمن برای callback_data (زیر 64 بایت)
            raw_id = f"{attacker_country}|{defender_country}|{uid}|{int(time.time())}"
            try:
                import hashlib
                short_id = 'rr_' + hashlib.sha256(raw_id.encode('utf-8')).hexdigest()[:16]
            except Exception:
                # در صورت بروز مشکل در hashlib، از timestamp ساده استفاده می‌کنیم
                short_id = f"rr_{int(time.time())}_{random.randint(1000,9999)}"
            
            # ذخیره درخواست
            ACTIVE_REFUGEE_REQUESTS[short_id] = {
                'attacker_country': attacker_country,
                'defender_country': defender_country,
                'target_uid': uid,
                'target_country': country,
                'refugee_count': refugee_count,
                'timestamp': time.time(),
                'raw_id': raw_id
            }
            print(f"[DEBUG][REFUGEE_CREATE] Created request {short_id} for {country} ({uid})")
            save_refugee_requests()  # ذخیره فوری
            
            # ایجاد دکمه‌ها
            keyboard = [
                [InlineKeyboardButton('✅ بپذیر', callback_data=f'new_refugee_accept_{short_id}')],
                [InlineKeyboardButton('❌ رد کن', callback_data=f'new_refugee_reject_{short_id}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # پیام درخواست
            refugee_text = (
                f"🛂 <b>درخواست پناهندگی</b>\n\n"
                f"در پی درگیری نظامی بین {attacker_country} و {defender_country}\n"
                f"حدود {refugee_count:,} نفر درخواست پناهندگی به کشور شما داده‌اند.\n\n"
                f"آیا می‌خواهید این مهاجران را بپذیرید؟"
            )
            
            # ارسال پیام
            await context.bot.send_message(
                chat_id=int(uid),
                text=refugee_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            
            print(f"درخواست پناهندگی {refugee_count:,} نفر از {attacker_country} به {country} ارسال شد")
        
    except Exception as e:
        print(f"خطا در ارسال درخواست‌های پناهندگی: {e}")

async def handle_refugee_acceptance(request_id, query, context):
    """پردازش پذیرش پناهندگان"""
    try:
        print(f"[DEBUG][REFUGEE_ACCEPT] Starting with request_id: {request_id}")
        print(f"[DEBUG][REFUGEE_ACCEPT] ACTIVE_REFUGEE_REQUESTS keys: {list(ACTIVE_REFUGEE_REQUESTS.keys())}")
        print(f"[DEBUG][REFUGEE_ACCEPT] Total active requests: {len(ACTIVE_REFUGEE_REQUESTS)}")
        
        # تلاش برای لود مجدد درخواست‌ها از فایل (در صورت نیاز)
        if not ACTIVE_REFUGEE_REQUESTS:
            print("[DEBUG][REFUGEE_ACCEPT] ACTIVE_REFUGEE_REQUESTS is empty, trying to reload from file...")
            load_refugee_requests()
            print(f"[DEBUG][REFUGEE_ACCEPT] After reload: {len(ACTIVE_REFUGEE_REQUESTS)} requests")
        
        # پاسخ فوری به کاربر
        await query.answer('در حال پردازش...', show_alert=False)
        
        if not request_id:
            print(f"[DEBUG][REFUGEE_ACCEPT] request_id is empty!")
            await query.answer('❌ شناسه درخواست نامعتبر است.', show_alert=True)
            return
            
        if request_id not in ACTIVE_REFUGEE_REQUESTS:
            print(f"[DEBUG][REFUGEE_ACCEPT] request_id {request_id} not found in ACTIVE_REFUGEE_REQUESTS!")
            print(f"[DEBUG][REFUGEE_ACCEPT] Available requests: {list(ACTIVE_REFUGEE_REQUESTS.keys())}")
            # بررسی فایل مستقیم
            try:
                with open('refugee_requests.json', 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    if request_id in file_data:
                        print(f"[DEBUG][REFUGEE_ACCEPT] Request found in file but not in memory! Restoring...")
                        ACTIVE_REFUGEE_REQUESTS[request_id] = file_data[request_id]
                        save_refugee_requests()
                    else:
                        print(f"[DEBUG][REFUGEE_ACCEPT] Request not found in file either")
            except Exception as e:
                print(f"[DEBUG][REFUGEE_ACCEPT] Error checking file: {e}")
            
            if request_id not in ACTIVE_REFUGEE_REQUESTS:
                await query.answer('❌ درخواست منقضی شده است.', show_alert=True)
                return
        
        request_data = ACTIVE_REFUGEE_REQUESTS[request_id]
        target_uid = str(query.from_user.id)
        
        # بررسی مالکیت درخواست
        if request_data.get('target_uid') != target_uid:
            await query.answer('❌ این درخواست برای شما نیست.', show_alert=True)
            return
        
        # اضافه کردن مهاجران
        if 'immigrants' not in utils.users[target_uid]:
            utils.users[target_uid]['immigrants'] = 0
        utils.users[target_uid]['immigrants'] += request_data['refugee_count']
        utils.save_users()
        
        # پیام موفقیت
        success_text = (
            f"✅ <b>پناهندگان پذیرفته شدند</b>\n\n"
            f"کشور {request_data['target_country']} {request_data['refugee_count']:,} پناهنده از "
            f"{request_data['attacker_country']} و {request_data['defender_country']} را پذیرفت.\n\n"
            f"📈 مهاجران {request_data['target_country']}: +{request_data['refugee_count']:,}"
        )
        
        # ارسال گیف موفقیت
        try:
            success_gif = "https://t.me/TextEmpire_IR/132"
            await context.bot.send_animation(
                chat_id=int(target_uid), 
                animation=success_gif, 
                caption=success_text, 
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"خطا در ارسال گیف پذیرش: {e}")
            await context.bot.send_message(chat_id=int(target_uid), text=success_text, parse_mode='HTML')
        
        # ارسال به کانال خبری
        try:
            news_text = (
                f"✅ <b>پناهندگان پذیرفته شدند</b>\n\n"
                f"کشور {request_data['target_country']} {request_data['refugee_count']:,} پناهنده از "
                f"{request_data['attacker_country']} و {request_data['defender_country']} را پذیرفت."
            )
            await context.bot.send_animation(
                chat_id=NEWS_CHANNEL_ID, 
                animation=success_gif, 
                caption=news_text, 
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"خطا در ارسال به کانال: {e}")
        
        # حذف درخواست
        del ACTIVE_REFUGEE_REQUESTS[request_id]
        save_refugee_requests()  # ذخیره تغییرات
        
        await query.answer('✅ مهاجران پذیرفته شدند.', show_alert=True)
        print(f"پناهندگی {request_data['refugee_count']:,} نفر به {request_data['target_country']} پذیرفته شد")
        
        # نمایش فوری وضعیت جمعیت به‌روزرسانی‌شده
        try:
            from jame import show_population_status
            await show_population_status(query)
        except Exception as _e:
            print(f"refugee accept: failed to show population status: {_e}")
        
    except Exception as e:
        print(f"خطا در پردازش پذیرش پناهندگی: {e}")
        import traceback
        traceback.print_exc()
        try:
            await query.answer('❌ خطا در پردازش درخواست. لطفاً دوباره تلاش کنید.', show_alert=True)
        except:
            pass

async def handle_refugee_rejection(request_id, query, context):
    """پردازش رد پناهندگان"""
    try:
        # پاسخ فوری به کاربر
        await query.answer('در حال پردازش...', show_alert=False)
        
        if not request_id or request_id not in ACTIVE_REFUGEE_REQUESTS:
            await query.answer('❌ درخواست منقضی شده است.', show_alert=True)
            return
        
        request_data = ACTIVE_REFUGEE_REQUESTS[request_id]
        target_uid = str(query.from_user.id)
        
        # بررسی مالکیت درخواست
        if request_data.get('target_uid') != target_uid:
            await query.answer('❌ این درخواست برای شما نیست.', show_alert=True)
            return
        
        # پیام رد
        rejection_text = (
            f"❌ <b>درخواست پناهندگی رد شد</b>\n\n"
            f"کشور {request_data['target_country']} درخواست پناهندگی {request_data['refugee_count']:,} نفر از "
            f"{request_data['attacker_country']} و {request_data['defender_country']} را رد کرد.\n\n"
            f"این افراد مجبور به بازگشت به کشور خود شدند."
        )
        
        # ارسال پیام رد
        await context.bot.send_message(chat_id=int(target_uid), text=rejection_text, parse_mode='HTML')
        
        # ارسال به کانال خبری
        try:
            news_text = (
                f"❌ <b>درخواست پناهندگی رد شد</b>\n\n"
                f"کشور {request_data['target_country']} درخواست پناهندگی {request_data['refugee_count']:,} نفر از "
                f"{request_data['attacker_country']} و {request_data['defender_country']} را رد کرد."
            )
            await context.bot.send_message(chat_id=NEWS_CHANNEL_ID, text=news_text, parse_mode='HTML')
        except Exception as e:
            print(f"خطا در ارسال به کانال: {e}")
        
        # حذف درخواست
        del ACTIVE_REFUGEE_REQUESTS[request_id]
        save_refugee_requests()  # ذخیره تغییرات
        
        await query.answer('❌ درخواست پناهندگی رد شد.', show_alert=True)
        print(f"درخواست پناهندگی {request_data['refugee_count']:,} نفر از {request_data['target_country']} رد شد")
        
    except Exception as e:
        print(f"خطا در پردازش رد پناهندگی: {e}")
        import traceback
        traceback.print_exc()
        try:
            await query.answer('❌ خطا در پردازش درخواست. لطفاً دوباره تلاش کنید.', show_alert=True)
        except:
            pass

from bank import (
    show_international_bank_menu,
    show_loans_menu,
    show_independence_loan_info,
    show_development_loan_info,
    show_emergency_loan_info,
    request_independence_loan,
    request_development_loan,
    request_emergency_loan,
    show_my_loans,
    process_loan_payments,
    load_bank_data,
    load_loan_history,
    pay_loan_early,
    show_bank_account_menu,
    show_transfer_money_menu,
    start_transfer_process,
    handle_transfer_account_number,
    handle_transfer_amount,
    confirm_transfer,
    cancel_transfer,
    show_transaction_history,
    show_deposit_menu,
    handle_deposit_amount,
    show_withdraw_menu,
    handle_withdraw_amount,
    show_overdue_debts_menu,
    pay_installment,
    pay_full_debt,
    request_installment_loan,
    show_chat_with_morgan,
    handle_morgan_chat
)
import sys
print("[DEBUG] UTILS ID:", id(sys.modules['utils']))
from matts import (
    show_military_tech_menu, upgrade_military_tech, 

)
from diplomaci import (
   
    handle_accept_peace,
    handle_reject_peace,
    show_alliance_menu,
    handle_alliance_urgent_meeting,
    show_alliance_chat,
    handle_alliance_message,
    handle_create_alliance,
    show_alliance_list,
    join_alliance,
    edit_alliance_desc_start,
    edit_alliance_rules_start,
    edit_alliance_logo_start,
    edit_alliance_entry_fee_start,
    set_alliance_deputy_start,
    set_alliance_deputy_confirm,
    show_alliance_members,
    handle_alliance_kick_member,
    handle_kick_member_confirm,
    show_alliance_advertisement_menu,
    handle_alliance_ad_normal,
    handle_alliance_ad_pinned,
    confirm_alliance_ad_normal,
    confirm_alliance_ad_pinned,
    show_alliance_help_menu,
    show_alliance_help_request_menu,
    start_statement,
    handle_help_request_resource,
    handle_help_request_amount,
    show_alliance_help_give_menu,
    show_alliance_trades_list,
    handle_help_give_confirm,
    handle_statement,
    pending_create_alliance,
    show_country_relations_menu,
    get_relation_text,
    show_view_relations,
    show_improve_relations_menu,
    show_damage_relations_menu,
    handle_relation_action,
    show_embassy_menu,
    show_close_embassy_menu,
    show_reopen_embassy_menu,
    handle_close_embassy,
    handle_reopen_embassy_request,
    handle_accept_reopen_embassy,
    handle_embassy_request,
    handle_embassy_accept,
    show_alliance_chat_history,
    handle_foreign_minister_suggestions,

)
from economy import (
    show_trade_menu,
    show_global_market_resources,
    buy_from_market_start,
    sell_to_market_start,
    buy_market_show_inventory,
    sell_market_ask_amount,
    handle_global_market_amount,
    show_prices_menu,
    sell_to_player_start,
    sell_to_player_ask_amount,
    handle_sell_amount,
    handle_sell_total_price,
    manage_sell_ads_menu,
    delete_sell_ad,
    format_price_short,
    buy_from_player_start,
    buy_from_player_ads,
    buy_from_player_confirm,
    finalize_trade_after_delay,



)
import asyncio
from battle import (
      process_attack_forces, start_ground_battle, simulate_ground_battle, schedule_battle_result,
      start_naval_battle, schedule_naval_battle_phases, naval_battle_phase_1, naval_battle_phase_2,
      naval_battle_phase_3, naval_battle_conquest, naval_battle_defeat, naval_battle_draw, ask_sea_raid_forces,
      show_attackable_countries, show_ground_forces_inventory,
      show_loot_menu, show_sea_raid_menu, show_naval_attackable_countries, show_naval_forces_inventory, process_naval_attack_forces,
      ground_battle_phase_1, ground_battle_phase_2, ground_battle_phase_3, ground_battle_conquest, ground_battle_defeat, ground_battle_draw, schedule_ground_battle_phases,
      show_air_attackable_countries, show_air_forces_inventory, process_air_attack_forces, start_air_battle, schedule_air_battle_phases_new,
      show_ground_attack_analysis, show_air_attack_analysis, show_naval_attack_analysis,
      show_missile_attack_menu,
      start_missile_attack_phases,
      missile_attack_phase_1,
      missile_attack_phase_2,
      missile_attack_phase_3,
      missile_attack_result,
      show_missile_target_selection,
      missile_attack_auto_phases
  )
from united_nations import handle_un_callback, is_un_user
# شناسه ادمین (توکن ربات را اینجا قرار دهید)
  # شناسه کانال حمله دریایی (همان کانال اخبار)
# قیمت‌های پایه هر منبع (مستقل از طلا)


# لیست اولیه کشورها (قبل از بارگذاری از فایل)

def get_country_leader_display_name(user_id: str) -> str:
    try:
        import utils
        u = utils.users.get(str(user_id), {})
        name = u.get('country_leader_name')
        if isinstance(name, str) and name.strip():
            return name.strip()
    except Exception:
        pass
    return 'رهبر'

def get_used_official_names(role_key=None):
    """Return a set of already chosen official names across all users.
    If role_key provided (e.g., 'minister'|'general'|'foreign'|'finance'), filter to that role.
    """
    used = set()
    try:
        import utils as _utils
        for _uid, _u in _utils.users.items():
            sel = _u.get('selected_officials', {}) or {}
            if role_key:
                if role_key in sel and isinstance(sel[role_key], dict):
                    name = sel[role_key].get('name')
                    if name:
                        used.add(name)
            else:
                for _rk, _info in sel.items():
                    if isinstance(_info, dict):
                        name = _info.get('name')
                        if name:
                            used.add(name)
    except Exception:
        pass
    return used

# ساخت منوی استارت با دکمه بازگشت (در صورت نیاز)
def get_start_menu(activated):
    keyboard = []
    
    # ردیف اول: شروع بازی و کشورها
    row1 = [
        InlineKeyboardButton('شروع بازی 🚀', callback_data='start_game' if activated else 'inactive_start'),
            InlineKeyboardButton('کشورها 🌍', callback_data='countries')
    ]
    keyboard.append(row1)
    
    # ردیف دوم: فروشگاه و فعالسازی
    row2 = [
        InlineKeyboardButton('🛒 فروشگاه', callback_data='shop_menu'),
            InlineKeyboardButton('فعالسازی کشور 🔑', callback_data='activate_country')
    ]
    keyboard.append(row2)
    
    # ردیف سوم: آموزش و پشتیبانی
    row3 = [
        InlineKeyboardButton('آموزش 📖', callback_data='help'),
            InlineKeyboardButton('پشتیبانی 🛠', callback_data='support')
        ]
    keyboard.append(row3)
    
    # اضافه کردن دکمه ادمین فقط برای ادمین (تک ستونی)
    try:
        from utils import ADMIN_ID
        if ADMIN_ID == '6602925597':
            keyboard.append([InlineKeyboardButton('منوی ادمین 👑', callback_data='admin_menu')])
    except Exception:
        pass
    
    return InlineKeyboardMarkup(keyboard)

def get_start_menu_reply(user_id=None):
    keyboard = []
    
    # ردیف اول: شروع بازی و کشورها
    row1 = [
        KeyboardButton('شروع بازی 🚀'),
        KeyboardButton('کشورها 🌍')
    ]
    keyboard.append(row1)
    
    # ردیف دوم: فروشگاه و فعالسازی
    row2 = [
        KeyboardButton('🛒 فروشگاه'),
        KeyboardButton('فعالسازی کشور 🔑')
    ]
    keyboard.append(row2)
    
    # ردیف سوم: آموزش و پشتیبانی
    row3 = [
        KeyboardButton('آموزش 📖'),
        KeyboardButton('پشتیبانی 🛠')
    ]
    keyboard.append(row3)
    
    # ردیف چهارم: پروفایل یا ثبت‌نام
    if user_id:
        try:
            import utils
            u = utils.users.get(str(user_id), {})
            prof = u.get('profile', {})
            if prof.get('is_registered') or prof.get('guest'):
                keyboard.append([KeyboardButton('👤 پروفایل')])
            else:
                keyboard.append([KeyboardButton('ثبت‌نام 📱')])
        except Exception:
            pass
    
    # اگر ادمین هست (تک ستونی)
    try:
        from utils import ADMIN_ID
        if ADMIN_ID != 'YOUR_ADMIN_ID_HERE':
            keyboard.append([KeyboardButton('منوی ادمین 👑')])
    except Exception:
        pass
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def show_user_profile(update, context):
    """Display user profile information"""
    user_id = str(update.effective_user.id)
    
    try:
        import utils
        u = utils.users.get(str(user_id), {})
        
        prof = u.get('profile', {})
        if not (prof.get('is_registered') or prof.get('guest')):
            await update.message.reply_text('❌ شما هنوز ثبت‌نام نکرده‌اید.')
            return
        
        # اطمینان از وجود شناسه عمومی
        utils.update_user_identifier_if_needed(user_id)
        
        # Get user data
        # Player Name must always be Telegram account name
        player_name = u.get('player_name', 'نامشخص')
        phone = u.get('phone', '')
        country = (u.get('current_country_name') or u.get('country') or 'کشور انتخاب نشده')
        location = u.get('location', {})
        credits = u.get('inventory', {}).get('credits', 0)
        # Compute global rank from Hall of Fame scoring (titles)
        title_points = {
            'امپراتور جهانی': 50,
            'سلطان اقتصاد': 30,
            'دیپلمات اعظم': 20,
            'فرمانده آهنین': 20,
            'محبوب ملت‌ها': 10,
            'سلطان صاحبقِران': 20,
            'پیشکسوت جهان': 25,
            'امپراتور حقیقی': 100
        }
        try:
            leaderboard = []
            for uid, usr in utils.users.items():
                prof2 = usr.get('profile', {})
                if not (prof2.get('is_registered') or prof2.get('guest')):
                    continue
                user_titles = usr.get('titles', []) or []
                score = 0
                for t in user_titles:
                    score += title_points.get(t.get('name', ''), 0)
                leaderboard.append({
                    'uid': uid,
                    'score': score
                })
            leaderboard.sort(key=lambda x: x['score'], reverse=True)
            global_rank = next((idx for idx, row in enumerate(leaderboard, start=1) if row['uid'] == user_id), None)
        except Exception:
            global_rank = None
        titles = u.get('titles', [])
        public_identifier = u.get('public_identifier', '')
        
        # Format phone number
        masked_phone = utils.mask_phone_number(phone) if phone else 'ثبت نشده'
        
        # Format location
        location_display = utils.get_location_display(location)
        province_display = utils.get_location_province(location) if location else '-'
        
        # Build profile text
        guest_badge = ' (مهمان)' if u.get('profile', {}).get('guest') else ''
        profile_text = f"👤 <b>پروفایل کاربری{guest_badge}</b>\n\n"
        profile_text += f"👤 <b>Player Name:</b> {player_name}\n"
        profile_text += f"🆔 <b>شناسه عمومی:</b> /{public_identifier}\n" if public_identifier else ""
        profile_text += f"📞 <b>شماره تماس:</b> {masked_phone}\n"
        profile_text += f"🌍 <b>کشور فعلی:</b> {country}\n"
        profile_text += f"📍 <b>موقعیت ثبت‌نام:</b> {location_display}\n"
        profile_text += f"🗺️ <b>استان:</b> {province_display}\n"
        profile_text += f"💠 <b>اعتبار جهانی:</b> {credits:,}\n"
        profile_text += f"🏅 <b>رتبه جهانی:</b> {global_rank if global_rank is not None else '-'}\n\n"
        
        # Add titles section
        if titles:
            profile_text += "🏆 <b>عناوین کسب‌شده:</b>\n"
            for title in titles:
                title_name = title.get('name', '')
                season = title.get('season', 0)
                profile_text += f"• {title_name} (فصل {season})\n"
        else:
            profile_text += "🏆 <b>عناوین کسب‌شده:</b> هیچ عنوانی کسب نشده\n"
        
        # Inline buttons under profile
        profile_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('🏛 تالار افتخارات', callback_data='hall_of_fame')]
        ])
        await update.message.reply_text(profile_text, parse_mode='HTML', reply_markup=profile_keyboard)
        
    except Exception as e:
        print(f"Profile display error: {e}")
        await update.message.reply_text('❌ خطا در نمایش پروفایل. لطفاً دوباره تلاش کنید.')

async def show_public_profile(update, context, target_user_id=None, target_user_data=None):
    """نمایش پروفایل عمومی کاربر"""
    try:
        import utils
        
        if not target_user_id or not target_user_data:
            await update.message.reply_text('❌ اطلاعات کاربر یافت نشد.')
            return
        
        # Get user data
        # Player Name remains Telegram account name
        player_name = target_user_data.get('player_name', 'نامشخص')
        country = (target_user_data.get('current_country_name') or target_user_data.get('country') or 'کشور انتخاب نشده')
        titles = target_user_data.get('titles', [])
        public_identifier = target_user_data.get('public_identifier', '')
        phone = target_user_data.get('phone', '')
        location = target_user_data.get('location', {})
        
        # Masked fields
        # Public view: fully hide phone and precise location
        masked_phone = 'خصوصی' if phone else '-'
        # Hide coordinates; show only province/city level if available (no exact coords)
        if isinstance(location, dict):
            try:
                province = utils.get_location_province(location)
            except Exception:
                province = '-'
            city = location.get('city') or None
        else:
            province = '-'
            city = None
        if province and province != '-':
            location_display = f"{province}"
        elif city:
            location_display = f"{city}"
        else:
            location_display = '-'
        province_display = province if province else '-'
        
        # Build public profile text as requested
        profile_text = "👤 <b>پروفایل کاربری</b>\n\n"
        profile_text += f"👤 <b>Player Name:</b> {player_name}\n"
        profile_text += (f"🆔 <b>شناسه عمومی:</b> /{public_identifier}\n" if public_identifier else "")
        profile_text += f"📞 <b>شماره تماس:</b> {masked_phone}\n"
        profile_text += f"🌍 <b>کشور فعلی:</b> {country}\n"
        profile_text += f"📍 <b>موقعیت ثبت‌نام:</b> {location_display}\n"
        profile_text += f"🗺️ <b>استان:</b> {province_display}\n"
        # Compute target user's rank similarly
        title_points = {
            'امپراتور جهانی': 50,
            'سلطان اقتصاد': 30,
            'دیپلمات اعظم': 20,
            'فرمانده آهنین': 20,
            'محبوب ملت‌ها': 10,
            'سلطان صاحبقِران': 20,
            'پیشکسوت جهان': 25,
            'امپراتور حقیقی': 100
        }
        try:
            leaderboard = []
            for uid, usr in utils.users.items():
                prof2 = usr.get('profile', {})
                if not (prof2.get('is_registered') or prof2.get('guest')):
                    continue
                user_titles = usr.get('titles', []) or []
                score = 0
                for t in user_titles:
                    score += title_points.get(t.get('name', ''), 0)
                leaderboard.append({'uid': uid, 'score': score})
            leaderboard.sort(key=lambda x: x['score'], reverse=True)
            target_rank = next((idx for idx, row in enumerate(leaderboard, start=1) if row['uid'] == target_user_id), None)
        except Exception:
            target_rank = None
        profile_text += f"💠 <b>اعتبار جهانی:</b> -\n"
        profile_text += f"🏅 <b>رتبه جهانی:</b> {target_rank if target_rank is not None else '-'}\n"
        profile_text += "🏆 <b>عناوین کسب‌شده:</b>\n"
        
        if titles:
            for title in titles[:5]:
                title_name = title.get('name', '')
                season = title.get('season', 0)
                profile_text += f"• {title_name} (فصل {season})\n"
            if len(titles) > 5:
                profile_text += f"... و {len(titles) - 5} عنوان دیگر\n"
        else:
            profile_text += "• -\n"
        
        # Create keyboard with title hall button if user has many titles
        keyboard = []
        if titles and len(titles) > 5:
            keyboard.append([InlineKeyboardButton('🏆 تالار عناوین این کاربر', callback_data=f'user_title_hall_{target_user_id}')])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        await update.message.reply_text(profile_text, parse_mode='HTML', reply_markup=reply_markup)
        
    except Exception as e:
        print(f"Public profile display error: {e}")
        await update.message.reply_text('❌ خطا در نمایش پروفایل عمومی. لطفاً دوباره تلاش کنید.')

async def show_user_title_hall(query, target_user_id):
    """نمایش تالار عناوین کاربر خاص"""
    try:
        import utils
        
        if not target_user_id:
            await query.edit_message_text('❌ شناسه کاربر نامعتبر است.')
            return
        
        target_user_data = utils.users.get(target_user_id, {})
        if not target_user_data:
            await query.edit_message_text('❌ کاربر یافت نشد.')
            return
        
        player_name = target_user_data.get('player_name', 'نامشخص')
        titles = target_user_data.get('titles', [])
        
        if not titles:
            await query.edit_message_text(
                f'🏆 <b>تالار عناوین {player_name}</b>\n\n'
                f'این کاربر هنوز هیچ عنوانی کسب نکرده است.',
                parse_mode='HTML'
            )
            return
        
        # Sort titles by season (newest first)
        sorted_titles = sorted(titles, key=lambda x: x.get('season', 0), reverse=True)
        
        text = f'🏆 <b>تالار عناوین {player_name}</b>\n\n'
        text += f'📊 <b>تعداد کل عناوین:</b> {len(titles)}\n\n'
        
        # Group titles by season
        titles_by_season = {}
        for title in sorted_titles:
            season = title.get('season', 0)
            if season not in titles_by_season:
                titles_by_season[season] = []
            titles_by_season[season].append(title.get('name', ''))
        
        # Display titles grouped by season
        for season in sorted(titles_by_season.keys(), reverse=True):
            text += f'📅 <b>فصل {season}:</b>\n'
            for title_name in titles_by_season[season]:
                text += f'• {title_name}\n'
            text += '\n'
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data=f'back_to_profile_{target_user_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
        
    except Exception as e:
        print(f"User title hall display error: {e}")
        await query.edit_message_text('❌ خطا در نمایش تالار عناوین. لطفاً دوباره تلاش کنید.')

async def handle_public_profile_command(update, context):
    """Handler برای دستورات شناسه عمومی (با /name یا بدون آن)"""
    try:
        import utils
        
        # دریافت متن پیام
        message_text = update.message.text.strip()
        
        # استخراج شناسه از دستور
        if message_text.startswith('/name'):
            identifier = message_text[5:]  # حذف '/name' از ابتدا
            if not identifier:  # اگر فقط '/name' باشد
                return
        elif message_text.startswith('/') and len(message_text) > 1:
            identifier = message_text[1:]  # حذف '/' از ابتدا
        else:
            return
        
        if not identifier:
            await update.message.reply_text('❌ لطفاً شناسه کاربر را وارد کنید.\nمثال: /zvz5si2a')
            return
        
        # جستجوی کاربر
        result = utils.get_user_by_public_identifier(identifier)
        
        if not result:
            await update.message.reply_text(f'❌ کاربری با شناسه /{identifier} یافت نشد.')
            return
        
        target_user_id, target_user_data = result
        
        # نمایش پروفایل عمومی
        await show_public_profile(update, context, target_user_id, target_user_data)
        
    except Exception as e:
        print(f"Public profile command error: {e}")
        await update.message.reply_text('❌ خطا در جستجوی پروفایل. لطفاً دوباره تلاش کنید.')

async def handle_location_approval(query, context, target_user_id):
    """Handle admin approval of user location"""
    try:
        import utils
        
        # Approve the location
        if utils.approve_location(target_user_id):
            # Complete user registration
            u = utils.users.setdefault(target_user_id, {})
            u.setdefault('profile', {})['is_registered'] = True
            
            # Set Player Name from Telegram data (always Telegram account name)
            try:
                # Get user info from Telegram
                user_info = await context.bot.get_chat(target_user_id)
                # prefer full name if available
                fn = getattr(user_info, 'first_name', '') or ''
                ln = getattr(user_info, 'last_name', '') or ''
                full_name = (f"{fn} {ln}".strip()) if (fn or ln) else ''
                uname = f"@{user_info.username}" if hasattr(user_info, 'username') and user_info.username else ''
                player_name = full_name or uname
                
                # Fallback to username if first_name is not available
                if not player_name and hasattr(user_info, 'username') and user_info.username:
                    player_name = f"@{user_info.username}"
                
                # Fallback to user_id if nothing else is available
                if not player_name:
                    player_name = f"User_{target_user_id}"
                
                u['player_name'] = player_name
                print(f"✅ Set player_name for user {target_user_id}: {player_name}")
                
            except Exception as e:
                print(f"Error getting user info: {e}")
                # Fallback to user_id
                u['player_name'] = f"User_{target_user_id}"
            
            # Save location to user profile
            loc_data = utils.location_verification_data.get(target_user_id, {})
            u['location'] = {
                'latitude': loc_data.get('latitude', 0),
                'longitude': loc_data.get('longitude', 0),
                'city': None,
                'country': None
            }
            
            # تولید شناسه عمومی منحصر به فرد
            public_identifier = utils.assign_public_identifier(target_user_id, u.get('player_name', ''))
            if public_identifier:
                print(f"✅ Generated public identifier for user {target_user_id}: {public_identifier}")
            
            utils.save_users()
            utils.pending_registration.pop(target_user_id, None)
            
            # Send success message to user
            try:
                success_text = "🎉 <b>تأییدیه موقعیت</b>\n\n"
                success_text += "✅ موقعیت شما توسط ادمین تأیید شد!\n"
                success_text += "✅ حساب کاربری شما با موفقیت ایجاد شد!\n\n"
                if public_identifier:
                    success_text += f"🆔 <b>شناسه عمومی شما:</b> /{public_identifier}\n\n"
                success_text += "🚀 حالا می‌توانید از تمام امکانات ربات استفاده کنید!\n"
                success_text += "📱 برای شروع، /start را بزنید."
                
                await context.bot.send_message(
                    chat_id=int(target_user_id),
                    text=success_text,
                    parse_mode='HTML'
                )
                print(f"✅ Approval message sent to user {target_user_id}")
            except Exception as e:
                print(f"❌ Error sending approval message to user {target_user_id}: {e}")
            
            # Update admin message (include approver)
            try:
                approver_uname = f"@{query.from_user.username}" if getattr(query.from_user, 'username', None) else ''
                approver_name = (query.from_user.full_name if hasattr(query.from_user, 'full_name') and query.from_user.full_name else '').strip()
                approver_display = approver_uname or approver_name or str(query.from_user.id)
            except Exception:
                approver_display = str(query.from_user.id)
            try:
                await query.edit_message_text(
                    f"✅ <b>موقعیت تأیید شد</b>\n\n"
                    f"👤 کاربر: {target_user_id}\n"
                    f"🆔 شناسه عمومی: /{public_identifier if public_identifier else 'نامشخص'}\n"
                    f"📱 پیام تأییدیه به کاربر ارسال شد\n"
                    f"🛡️ تاییدکننده: {approver_display}\n"
                    f"✅ ثبت‌نام کامل شد",
                    parse_mode='HTML'
                )
            except Exception as _e:
                # اگر امکان ویرایش پیام نبود، پیام جدید برای ادمین ارسال کن
                try:
                    admin_chat_id = query.message.chat.id if getattr(query, 'message', None) else int(utils.ADMIN_ID)
                except Exception:
                    admin_chat_id = int(utils.ADMIN_ID)
                await context.bot.send_message(
                    chat_id=admin_chat_id,
                    text=(
                        f"✅ <b>موقعیت تأیید شد</b>\n\n"
                        f"👤 کاربر: {target_user_id}\n"
                        f"🆔 شناسه عمومی: /{public_identifier if public_identifier else 'نامشخص'}\n"
                        f"📱 پیام تأییدیه به کاربر ارسال شد\n"
                        f"🛡️ تاییدکننده: {approver_display}\n"
                        f"✅ ثبت‌نام کامل شد"
                    ),
                    parse_mode='HTML'
                )
        else:
            await query.edit_message_text("❌ Error: User not found in verification data.")
            
    except Exception as e:
        print(f"Location approval error: {e}")
        await query.edit_message_text("❌ Error processing location approval.")

async def handle_location_rejection(query, context, target_user_id):
    """Handle admin rejection of user location"""
    try:
        import utils
        
        # Reject the location and get attempt count
        attempts = utils.reject_location(target_user_id)
        
        if attempts < 3:
            # User can try again
            try:
                rejection_text = "❌ <b>موقعیت رد شد</b>\n\n"
                rejection_text += f"📍 موقعیت شما توسط ادمین رد شد\n"
                rejection_text += f"🔄 تلاش {attempts}/3\n\n"
                rejection_text += "💡 لطفاً موقعیت دقیق‌تر و معتبرتری ارسال کنید\n"
                rejection_text += "📱 برای تلاش مجدد، /start را بزنید"
                
                await context.bot.send_message(
                    chat_id=int(target_user_id),
                    text=rejection_text,
                    parse_mode='HTML'
                )
                print(f"✅ Rejection message sent to user {target_user_id}")
            except Exception as e:
                print(f"❌ Error sending rejection message to user {target_user_id}: {e}")
            
            await query.edit_message_text(
                f"❌ <b>موقعیت رد شد</b>\n\n"
                f"👤 کاربر: {target_user_id}\n"
                f"🔄 تلاش: {attempts}/3\n"
                f"📱 پیام رد کردن به کاربر ارسال شد",
                parse_mode='HTML'
            )
        else:
            # User is blocked
            try:
                block_text = "🚫 <b>حساب کاربری مسدود شد</b>\n\n"
                block_text += "❌ شما پس از 3 تلاش ناموفق برای تأیید موقعیت مسدود شدید\n\n"
                block_text += "📞 برای رفع مسدودیت با پشتیبانی تماس بگیرید\n"
                block_text += "🆔 شناسه کاربری: " + str(target_user_id)
                
                await context.bot.send_message(
                    chat_id=int(target_user_id),
                    text=block_text,
                    parse_mode='HTML'
                )
                print(f"✅ Block message sent to user {target_user_id}")
            except Exception as e:
                print(f"❌ Error sending block message to user {target_user_id}: {e}")
            
            await query.edit_message_text(
                f"🚫 <b>کاربر مسدود شد</b>\n\n"
                f"👤 کاربر: {target_user_id}\n"
                f"❌ پس از 3 تلاش ناموفق مسدود شد\n"
                f"📱 پیام مسدودیت به کاربر ارسال شد",
                parse_mode='HTML'
            )
            
    except Exception as e:
        print(f"Location rejection error: {e}")
        await query.edit_message_text("❌ Error processing location rejection.")

# ==================== SHOP SYSTEM ====================

def initialize_user_inventory(user_id):
    """Initialize inventory and game stats for new users"""
    if user_id not in utils.users:
        return
    
    # Initialize inventory for credits only
    if 'inventory' not in utils.users[user_id]:
        utils.users[user_id]['inventory'] = {
            'credits': 0,
            'special_packages': []  # list of {id, key, name, price, season, expires_in, activated}
        }
    
    # Initialize military stats
    if 'military' not in utils.users[user_id]:
        utils.users[user_id]['military'] = {
            'defense_power': 1.0,
            'defense_buff_turns': 0,
            'war_success_bonus': 0.0,
            'soldiers': 0,
            'tanks': 0,
            'jets': 0,
            'bombers': 0,
            'carriers': 0,
            'submarines': 0,
            'ballistic_missiles': 0,
            'defense_missiles': 0
        }
    
    # Initialize economy stats
    if 'economy' not in utils.users[user_id]:
        utils.users[user_id]['economy'] = {
            'resources_production': 1.0,
            'production_buff_turns': 0,
            'base_production': 1000,
            'satisfaction': 70,
            'money': 0,
            'loan_turns': 0,
            'loan_interest': 0.0
        }
    
    # Initialize diplomacy stats
    if 'diplomacy' not in utils.users[user_id]:
        utils.users[user_id]['diplomacy'] = {
            'sanction_immunity': False,
            'forced_peace_turns': 0,
            'forced_peace_country': None
        }
    
    # Initialize domestic stats
    if 'domestic' not in utils.users[user_id]:
        utils.users[user_id]['domestic'] = {
            'riot_suppression': False,
            'revolution': 20
        }
    
    # Initialize resources (main game stats)
    if 'resources' not in utils.users[user_id]:
        utils.users[user_id]['resources'] = {
            'soldiers': 0,
            'tanks': 0,
            'fighter_jets': 0,
            'bombers': 0,
            'aircraft_carriers': 0,
            'submarines': 0,
            'ballistic_missiles': 0,
            'defense_missiles': 0,
            'armored_vehicles': 0
        }
    
    # Initialize production tech levels
    if 'production_tech_levels' not in utils.users[user_id]:
        utils.users[user_id]['production_tech_levels'] = {}
    
    utils.save_users()

# ===== Special Packages Config =====
SPECIAL_PACKAGES = {
    'iron_dome': {
        'name': '🛡 گنبد آهنین',
        'price': 1000,
        'description': 'اثر: تمام دفاع‌های زمینی، دریایی و هوایی شما در نبردها ×2 می‌شود.\nمدت: تا پایان فصل جاری.',
    },
    'prod_tech': {
        'name': '⚙️ تکنولوژی تولید',
        'price': 500,
        'description': 'اثر: تولید تمام معادن/پالایشگاه‌ها/مزارع/نیروگاه‌ها ×2 می‌شود.\nتوجه: با ارتقاها جمع‌پذیر است (خروجی نهایی همیشه ×2).',
    },
    'satisfaction_lock': {
        'name': '🔒 امنیت یک نعمت',
        'price': 250,
        'description': 'اثر: رضایت مردم روی 100% قفل می‌شود و کاهش نمی‌یابد.\nمدت: دائمی (تا پایان بازی یا ریست).',
    },
    'robin_hood': {
        'name': '🏹 رابین هود',
        'price': 500,
        'description': 'اثر: +2.5% نرخ رشد ثابت جمعیت تا پایان فصل.\nمستقل از سیستم غذا.',
    },
    'friendship': {
        'name': '🤝 دوری و دوستی',
        'price': 500,
        'description': 'اثر: همه کشورها از اعلان جنگ علیه شما منع می‌شوند.\nروابط با همه کشورها روی +10 قفل می‌شود.\nمدت: 20 نوبت از لحظه فعال‌سازی.',
    },
}

def has_active_country(user_id: str) -> bool:
    try:
        u = utils.users.get(user_id, {})
        return bool(u.get('activated') and u.get('country'))
    except Exception:
        return False

def get_user_defense_power(user_id: str) -> float:
    try:
        return float(utils.users.get(user_id, {}).get('military', {}).get('defense_power', 1.0))
    except Exception:
        return 1.0

def get_user_special_prod_multiplier(user_id: str) -> float:
    try:
        return float(utils.users.get(user_id, {}).get('economy', {}).get('special_prod_multiplier', 1.0))
    except Exception:
        return 1.0

def get_user_robin_hood_bonus(user_id: str) -> float:
    try:
        return float(utils.users.get(user_id, {}).get('diplomacy', {}).get('robin_hood_growth_bonus', 0.0))
    except Exception:
        return 0.0

def get_shop_main_menu():
    """Create main shop menu"""
    keyboard = [
        [InlineKeyboardButton('💠 خرید اعتبار جهانی', callback_data='shop_credits')],
        [InlineKeyboardButton('⚔️ پکیج‌های نظامی', callback_data='shop_military_packages')],
        [InlineKeyboardButton('📈 پکیج‌های اقتصادی', callback_data='shop_economy')],
        [InlineKeyboardButton('📦 پکیج‌های منابع', callback_data='shop_resource_packages')],
        [InlineKeyboardButton('🎁 پکیج‌های ویژه', callback_data='shop_special')],
        [InlineKeyboardButton('🎒 پکیج‌های ویژه من', callback_data='shop_special_inventory')],
        [InlineKeyboardButton('📊 موجودی من', callback_data='shop_inventory')],
        [InlineKeyboardButton('🔙 بازگشت به منوی اصلی', callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_credits_menu():
    """Create credits purchase menu"""
    keyboard = [
        [InlineKeyboardButton('🛒 100💠 اعتبار جهانی - 20 T', callback_data='buy_credits_100')],
        [InlineKeyboardButton('🛒 250💠 اعتبار جهانی - 40 T', callback_data='buy_credits_250')],
        [InlineKeyboardButton('🛒 500💠 اعتبار جهانی - 100 T', callback_data='buy_credits_500')],
        [InlineKeyboardButton('🛒 1000💠 اعتبار جهانی - 200 T', callback_data='buy_credits_1000')],
        [InlineKeyboardButton('🛒 10000💠 اعتبار جهانی - 1499 T', callback_data='buy_credits_10000')],
        [InlineKeyboardButton('🔙 بازگشت به فروشگاه', callback_data='shop_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_military_packages_menu():
    """Create military packages menu"""
    keyboard = [
        [InlineKeyboardButton('♟ پکیج چشم‌های پنهان — 50 💠', callback_data='military_package_hidden_eyes')],
        [InlineKeyboardButton('⚓️ پکیج ناوگان تندر — 150 💠', callback_data='military_package_thunder_fleet')],
        [InlineKeyboardButton('🪖 پکیج لشکر آهنین — 400 💠', callback_data='military_package_iron_legion')],
        [InlineKeyboardButton('✈️ پکیج عقاب‌های آسمان — 1000 💠', callback_data='military_package_sky_eagles')],
        [InlineKeyboardButton('🎖 پکیج ارتش‌های متحد — 2500 💠', callback_data='military_package_united_armies')],
        [InlineKeyboardButton('🔙 بازگشت به فروشگاه', callback_data='shop_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_resource_packages_menu():
    """Create resource packages menu"""
    keyboard = [
        [InlineKeyboardButton('⚡ پکیج فوری — 50 💠', callback_data='resource_package_urgent')],
        [InlineKeyboardButton('🚀 پکیج قدرت نوظهور — 150 💠', callback_data='resource_package_emerging_power')],
        [InlineKeyboardButton('🌍 پکیج قدرت منطقه‌ای — 400 💠', callback_data='resource_package_regional_power')],
        [InlineKeyboardButton('👑 پکیج ابرقدرت — 1000 💠', callback_data='resource_package_superpower')],
        [InlineKeyboardButton('🏛️ پکیج امپراطور — 4999 💠', callback_data='resource_package_emperor')],
        [InlineKeyboardButton('🔙 بازگشت به فروشگاه', callback_data='shop_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_economic_packages_menu():
    """Create economic packages menu"""
    keyboard = [
        [InlineKeyboardButton('🆘 پکیج نیازمند — 50 💠', callback_data='economic_package_needy')],
        [InlineKeyboardButton('👨‍🌾 پکیج رعیت — 200 💠', callback_data='economic_package_peasant')],
        [InlineKeyboardButton('👨‍💼 پکیج تاجر — 500 💠', callback_data='economic_package_merchant')],
        [InlineKeyboardButton('👨‍💻 پکیج وزیر رعیا — 1000 💠', callback_data='economic_package_minister')],
        [InlineKeyboardButton('👑 پکیج پادشاه — 4999 💠', callback_data='economic_package_king')],
        [InlineKeyboardButton('🔙 بازگشت به فروشگاه', callback_data='shop_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_diplomatic_menu():
    """Create diplomatic packages menu"""
    keyboard = [
        [InlineKeyboardButton('🛒 خرید توافق پشت پرده - 800 💠', callback_data='buy_diplomatic_sanction')],
        [InlineKeyboardButton('🛒 خرید دوستی اجباری - 900 💠', callback_data='buy_diplomatic_peace')],
        [InlineKeyboardButton('🔙 بازگشت به فروشگاه', callback_data='shop_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_special_menu():
    """Create special packages menu (new system)"""
    keyboard = [
        [InlineKeyboardButton('🛡 گنبد آهنین — 1000 💠', callback_data='special_pkg_iron_dome')],
        [InlineKeyboardButton('⚙️ تکنولوژی تولید — 500 💠', callback_data='special_pkg_prod_tech')],
        [InlineKeyboardButton('🔒 امنیت یک نعمت — 250 💠', callback_data='special_pkg_satisfaction_lock')],
        [InlineKeyboardButton('🏹 رابین هود — 500 💠', callback_data='special_pkg_robin_hood')],
        [InlineKeyboardButton('🤝 دوری و دوستی — 500 💠', callback_data='special_pkg_friendship')],
        [InlineKeyboardButton('🔙 بازگشت به فروشگاه', callback_data='shop_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_purchase_confirmation(item_key, cost):
    """Create purchase confirmation menu"""
    keyboard = [
        [InlineKeyboardButton('✅ بله', callback_data=f'confirm_purchase_{item_key}_{cost}')],
        [InlineKeyboardButton('❌ خیر', callback_data='cancel_purchase')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_special_purchase_confirmation(key: str):
    pkg = SPECIAL_PACKAGES[key]
    price = pkg['price']
    keyboard = [
        [InlineKeyboardButton('✅ تایید خرید', callback_data=f'confirm_buy_special_{key}_{price}')],
        [InlineKeyboardButton('❌ لغو', callback_data='shop_special')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def show_shop_menu(query):
    """Show main shop menu"""
    user_id = str(query.from_user.id)
    
    # Check if user exists
    if user_id not in utils.users:
        await query.edit_message_text(
            "❌ شما در بازی ثبت‌نام نکرده‌اید! لطفاً ابتدا کشور خود را فعال‌سازی کنید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='back_to_main')]])
        )
        return
    
    initialize_user_inventory(user_id)
    credits = utils.users[user_id]['inventory']['credits']
    
    message = (
        "🛒 <b>فروشگاه</b>\n\n"
        f"💠 اعتبار جهانی شما: <b>{credits:,}</b>\n\n"
        "لطفاً دسته‌بندی مورد نظر خود را انتخاب کنید:"
    )
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=get_shop_main_menu())

async def show_special_package_details(query, key: str):
    user_id = str(query.from_user.id)
    initialize_user_inventory(user_id)
    if key not in SPECIAL_PACKAGES:
        await query.answer('پکیج نامعتبر است.', show_alert=True)
        return
    pkg = SPECIAL_PACKAGES[key]
    message = (
        f"{pkg['name']} — {pkg['price']} 💠\n\n"
        f"<code>{pkg['description']}</code>\n\n"
        "آیا خرید را تایید می‌کنید؟"
    )
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=get_special_purchase_confirmation(key))

async def execute_special_purchase(query, key: str, price: int):
    user_id = str(query.from_user.id)
    initialize_user_inventory(user_id)
    if not has_active_country(user_id):
        await query.answer('❌ شما هیچ کشوری فعال ندارید. ابتدا کشور خود را فعال کنید.', show_alert=True)
        return
    inv = utils.users[user_id]['inventory']
    if inv['credits'] < price:
        await query.answer('❌ موجودی اعتبار جهانی کافی نیست.', show_alert=True)
        return
    inv['credits'] -= price
    # add to special inventory
    from uuid import uuid4
    pkg_id = str(uuid4())
    season = utils.game_data.get('season', 1)
    inv.setdefault('special_packages', []).append({
        'id': pkg_id,
        'key': key,
        'name': SPECIAL_PACKAGES[key]['name'],
        'price': price,
        'purchase_season': season,
        'expires_after_seasons': 3,
        'activated': False
    })
    utils.save_users()
    await query.answer('✅ خرید انجام شد و به موجودی ویژه شما اضافه شد.', show_alert=True)
    await show_special_inventory(query)

async def show_special_inventory(query):
    user_id = str(query.from_user.id)
    initialize_user_inventory(user_id)
    inv = utils.users[user_id]['inventory']
    pkgs = inv.get('special_packages', [])
    season = utils.game_data.get('season', 1)
    lines = ["🎒 <b>پکیج‌های ویژه من</b>", "", "برای فعال‌سازی روی دکمه مربوطه بزنید."]
    keyboard = []
    for p in pkgs:
        status = 'فعال' if p.get('activated') else 'غیرفعال'
        expires_in = max(0, p.get('expires_after_seasons', 3) - (season - p.get('purchase_season', season))) if not p.get('activated') else '-'
        lines.append(f"• {p['name']} — وضعیت: {status} — انقضا: {expires_in} فصل")
        if not p.get('activated'):
            keyboard.append([InlineKeyboardButton(f"فعال‌سازی: {p['name']}", callback_data=f"activate_special_{p['id']}")])
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='shop_menu')])
    await query.edit_message_text('\n'.join(lines), parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def activate_special_package(query, pkg_id: str):
    user_id = str(query.from_user.id)
    if not has_active_country(user_id):
        await query.answer('❌ شما هیچ کشوری فعال ندارید. ابتدا کشور خود را فعال کنید.', show_alert=True)
        return
    inv = utils.users[user_id]['inventory']
    pkgs = inv.get('special_packages', [])
    target = None
    for p in pkgs:
        if p.get('id') == pkg_id:
            target = p
            break
    if not target:
        await query.answer('این پکیج یافت نشد.', show_alert=True)
        return
    if target.get('activated'):
        await query.answer('این پکیج قبلاً فعال شده است.', show_alert=True)
        return
    key = target.get('key')
    # apply effect
    if key == 'iron_dome':
        utils.users[user_id]['military']['defense_power'] = 2.0
        # we rely on season end to reset via season reset; no per-turn turns needed
    elif key == 'prod_tech':
        utils.users[user_id]['economy']['special_prod_multiplier'] = 2.0
    elif key == 'satisfaction_lock':
        utils.users[user_id]['satisfaction'] = 100
        utils.users[user_id]['satisfaction_locked'] = True
    elif key == 'robin_hood':
        utils.users[user_id]['diplomacy']['robin_hood_growth_bonus'] = 2.5
        utils.users[user_id]['diplomacy']['robin_hood_until_season'] = utils.game_data.get('season', 1)
    elif key == 'friendship':
        utils.users[user_id]['diplomacy']['forced_peace_turns'] = max(20, int(utils.users[user_id]['diplomacy'].get('forced_peace_turns', 0)))
        # Note: global +10 relations is simplified; war checks will block via forced_peace_turns
    target['activated'] = True
    utils.save_users()
    await query.answer('✅ پکیج فعال شد.', show_alert=True)
    await show_special_inventory(query)

async def show_credits_menu(query):
    """Show credits purchase menu"""
    user_id = str(query.from_user.id)
    credits = utils.users[user_id]['inventory']['credits']
    
    message = (
        "💠 <b>خرید اعتبار جهانی</b>\n\n"
        f"💠 اعتبار فعلی شما: <b>{credits:,}</b>\n\n"
        "📦 <b>پکیج‌های موجود:</b>\n\n"
        "🔹 <b>100💠 اعتبار جهانی</b> - 20 T\n"
        "🔹 <b>250💠 اعتبار جهانی</b> - 40 T\n"
        "🔹 <b>500💠 اعتبار جهانی</b> - 100 T\n"
        "🔹 <b>1000💠 اعتبار جهانی</b> - 200 T\n"
        "🔹 <b>10000💠 اعتبار جهانی</b> - 1499 T\n\n"
        "💡 <i>اعتبارهای جهانی برای خرید پکیج‌های مختلف استفاده می‌شوند.</i>"
    )
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=get_credits_menu())

async def show_payment_info(query, credits_amount, price):
    """Show payment information for credit purchase"""
    user_id = str(query.from_user.id)
    
    message = (
        f"💳 <b>اطلاعات پرداخت</b>\n\n"
        f"📋 <b>شماره کارت:</b>\n"
        f"<code>6219861825751208</code>\n\n"
        f"👤 <b>به نام:</b> محمدحسین فصیحی\n\n"
        f"💰 <b>مبلغ پرداخت:</b> {price * 1000:,} تومان\n"
        f"💠 <b>تعداد دریافتی:</b> {credits_amount} اعتبار جهانی\n\n"
        f"📝 <b>در صورت تایید خرید و پرداخت؛ رسید را ارسال فرمایید</b>"
    )
    
    keyboard = [
        [InlineKeyboardButton('📤 ارسال رسید پرداخت', callback_data=f'confirm_payment_{credits_amount}_{price}')],
        [InlineKeyboardButton('❌ لغو پرداخت', callback_data='cancel_payment')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)

async def handle_payment_confirmation(query):
    """Handle payment confirmation and wait for receipt"""
    import utils
    print(f"[DEBUG] handle_payment_confirmation received object type: {type(query)}")
    print(f"[DEBUG] Object attributes: {dir(query)}")
    
    # Handle both Update and CallbackQuery objects
    if hasattr(query, 'callback_query'):
        # If it's an Update object, get the callback query
        print(f"[DEBUG] Detected Update object, extracting callback_query")
        callback_query = query.callback_query
        user_id = str(callback_query.from_user.id)
        query = callback_query  # Use the callback query for the rest of the function
    elif hasattr(query, 'from_user'):
        # If it's already a CallbackQuery object
        print(f"[DEBUG] Detected CallbackQuery object")
        user_id = str(query.from_user.id)
    else:
        print(f"[ERROR] Invalid query object: {type(query)}")
        return
    
    # Parse payment info from callback data
    callback_data = query.data.replace('confirm_payment_', '')
    parts = callback_data.split('_')
    credits_amount = int(parts[0])
    price = int(parts[1])
    
    # Store payment info for this user
    utils.pending_payments[user_id] = {
        'credits_amount': credits_amount,
        'price': price,
        'status': 'waiting_receipt'
    }
    save_pending_payments()
    
    message = (
        f"📤 <b>ارسال رسید پرداخت</b>\n\n"
        f"💰 <b>مبلغ:</b> {price * 1000:,} تومان\n"
        f"💠 <b>اعتبار دریافتی:</b> {credits_amount}\n\n"
        f"📷 <b>لطفاً عکس رسید پرداخت را ارسال کنید</b>\n"
        f"⚠️ <b>توجه:</b> حتماً عکس باشد، نه فایل دیگر\n\n"
        f"⏳ در حال انتظار برای دریافت رسید..."
    )
    
    keyboard = [
        [InlineKeyboardButton('❌ لغو', callback_data='cancel_payment')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)

async def handle_receipt_photo(update, context):
    """Handle receipt photo from user"""
    # Import utils at the top to avoid scope issues
    import utils
    user_id = str(update.effective_user.id)
    
    # Check if user has pending payment
    if user_id not in utils.pending_payments:
        await update.message.reply_text("❌ درخواست پرداخت یافت نشد!")
        return
    
    payment_info = utils.pending_payments[user_id]
    
    # If payment was previously rejected, update status to waiting for new receipt
    if payment_info.get('status') == 'rejected':
        utils.pending_payments[user_id]['status'] = 'waiting_receipt'
        save_pending_payments()
        await update.message.reply_text(
            "📷 <b>رسید جدید دریافت شد!</b>\n\n"
            "⏳ در حال بررسی مجدد توسط ادمین...\n"
            "💠 اعتبار جهانی شما پس از تایید رسید پرداخت شارژ خواهد شد"
        )
    
    # Get user info
    user = utils.users.get(user_id, {})
    username = update.effective_user.username or "بدون نام کاربری"
    first_name = update.effective_user.first_name or "نامشخص"
    last_name = update.effective_user.last_name or ""
    full_name = f"{first_name} {last_name}".strip()
    
    # Get phone number from user profile if available
    phone = user.get('phone', 'ثبت نشده')
    
    # Send receipt to admin
    admin_message = (
        f"📋 <b>رسید پرداخت جدید</b>\n\n"
        f"👤 <b>اطلاعات کاربر:</b>\n"
        f"• ID: <code>{user_id}</code>\n"
        f"• نام کاربری: @{username}\n"
        f"• نام: {full_name}\n"
        f"• شماره تماس: {phone}\n\n"
        f"💰 <b>اطلاعات پرداخت:</b>\n"
        f"• مبلغ: {payment_info['price'] * 1000:,} تومان\n"
        f"• اعتبار دریافتی: {payment_info['credits_amount']} 💠\n\n"
        f"📷 <b>رسید پرداخت:</b>"
    )
    
    keyboard = [
        [
            InlineKeyboardButton('✅ تایید پرداخت', callback_data=f'approve_payment_{user_id}'),
            InlineKeyboardButton('❌ رد پرداخت', callback_data=f'reject_payment_{user_id}')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send photo to admin
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=admin_message,
        parse_mode='HTML',
        reply_markup=reply_markup
    )
    
    # Update payment status
    utils.pending_payments[user_id]['status'] = 'pending_admin_approval'
    save_pending_payments()
    
    # Send confirmation to user
    await update.message.reply_text(
        "✅ رسید پرداخت دریافت شد!\n\n"
        "⏳ در حال بررسی توسط ادمین...\n"
        "💠 اعتبار جهانی شما پس از تایید رسید پرداخت شارژ خواهد شد"
    )

async def handle_admin_payment_approval(query):
    """Handle admin approval of payment"""
    import utils
    user_id = query.data.replace('approve_payment_', '')
    print(f"[DEBUG] Admin approval for user {user_id}")
    
    # Check if payment exists
    if user_id not in utils.pending_payments:
        print(f"[DEBUG] Payment not found for user {user_id}")
        await query.answer("❌ درخواست پرداخت یافت نشد!", show_alert=True)
        return
    
    # Check if payment is in correct status
    payment_status = utils.pending_payments[user_id].get('status', 'waiting_receipt')
    print(f"[DEBUG] Payment status: {payment_status}")
    if payment_status not in ['waiting_receipt', 'rejected', 'pending_admin_approval']:
        print(f"[DEBUG] Invalid payment status: {payment_status}")
        await query.answer("❌ وضعیت پرداخت نامناسب است!", show_alert=True)
        return
    
    payment_info = utils.pending_payments[user_id]
    credits_amount = payment_info['credits_amount']
    
    # Add credits to user
    if user_id not in utils.users:
        utils.users[user_id] = {}
    if 'inventory' not in utils.users[user_id]:
        utils.users[user_id]['inventory'] = {}
    if 'credits' not in utils.users[user_id]['inventory']:
        utils.users[user_id]['inventory']['credits'] = 0
    
    utils.users[user_id]['inventory']['credits'] += credits_amount
    utils.save_users()
    
    # Remove from pending payments
    del utils.pending_payments[user_id]
    save_pending_payments()
    print(f"[DEBUG] Payment approved and removed for user {user_id}")
    
    # Send confirmation to user
    try:
        from telegram import Bot
        bot = Bot(token='7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I')
        await bot.send_message(
            chat_id=int(user_id),
            text=f"✅ <b>پرداخت تایید شد!</b>\n\n"
                 f"💠 <b>{credits_amount} اعتبار جهانی</b> به حساب شما اضافه شد\n"
                 f"🎉 رسید پرداخت شما تایید شد",
            parse_mode='HTML'
        )
    except Exception:
        pass
    
    # Update admin message (remove buttons after approval)
    try:
        await query.edit_message_caption(
            caption=f"✅ <b>پرداخت تایید شد</b>\n\n"
                   f"👤 کاربر: {user_id}\n"
                   f"💠 اعتبار اضافه شده: {credits_amount}\n"
                   f"⏰ زمان تایید: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            parse_mode='HTML'
        )
    except Exception:
        # If caption edit fails, try to edit the text
        try:
            await query.edit_message_text(
                f"✅ <b>پرداخت تایید شد</b>\n\n"
                f"👤 کاربر: {user_id}\n"
                f"💠 اعتبار اضافه شده: {credits_amount}\n"
                f"⏰ زمان تایید: {time.strftime('%Y-%m-%d %H:%M:%S')}",
                parse_mode='HTML'
            )
        except Exception:
            pass

async def handle_admin_payment_rejection(query):
    """Handle admin rejection of payment"""
    import utils
    user_id = query.data.replace('reject_payment_', '')
    
    # Check if payment exists
    if user_id not in utils.pending_payments:
        await query.answer("❌ درخواست پرداخت یافت نشد!", show_alert=True)
        return
    
    # Update payment status to rejected (but keep in pending_payments)
    utils.pending_payments[user_id]['status'] = 'rejected'
    save_pending_payments()
    
    # Send rejection message to user
    try:
        from telegram import Bot
        bot = Bot(token='7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I')
        await bot.send_message(
            chat_id=int(user_id),
            text="❌ <b>رسید پرداخت رد شد</b>\n\n"
                 "🔍 <b>دلایل احتمالی:</b>\n"
                 "• عکس رسید واضح نیست\n"
                 "• مبلغ پرداخت مطابقت ندارد\n"
                 "• شماره کارت اشتباه است\n"
                 "• رسید مربوط به تراکنش دیگری است\n\n"
                 "💡 <b>راه حل:</b>\n"
                 "لطفاً رسید جدید و واضح ارسال کنید\n"
                 "یا با پشتیبانی تماس بگیرید\n\n"
                 f"👤 ادمین: @{ADMIN_USERNAME or 'https://t.me/Rylotm'}",
            parse_mode='HTML'
        )
    except Exception:
        pass
    
    # Update admin message with only approve button
    keyboard = [
        [InlineKeyboardButton('✅ تایید پرداخت', callback_data=f'approve_payment_{user_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_caption(
            caption=f"❌ <b>پرداخت رد شد - در انتظار رسید جدید</b>\n\n"
                   f"👤 کاربر: {user_id}\n"
                   f"⏰ زمان رد: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                   f"💡 کاربر می‌تواند رسید جدید ارسال کند",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    except Exception:
        # If caption edit fails, try to edit the text
        try:
            await query.edit_message_text(
                f"❌ <b>پرداخت رد شد - در انتظار رسید جدید</b>\n\n"
                f"👤 کاربر: {user_id}\n"
                f"⏰ زمان رد: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"💡 کاربر می‌تواند رسید جدید ارسال کند",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        except Exception:
            pass

async def show_military_packages_menu(query):
    """Show military packages menu"""
    user_id = str(query.from_user.id)
    credits = utils.users[user_id]['inventory']['credits']
    
    message = (
        "⚔️ <b>پکیج‌های نظامی</b>\n\n"
        f"💠 اعتبار شما: <b>{credits:,}</b>\n\n"
        "📦 <b>پکیج‌های موجود:</b>\n\n"
        "♟ <b>پکیج چشم‌های پنهان</b> — 50 💠\n"
        "⚓️ <b>پکیج ناوگان تندر</b> — 150 💠\n"
        "🪖 <b>پکیج لشکر آهنین</b> — 400 💠\n"
        "✈️ <b>پکیج عقاب‌های آسمان</b> — 1000 💠\n"
        "🎖 <b>پکیج ارتش‌های متحد</b> — 2500 💠\n\n"
        "لطفاً پکیج مورد نظر خود را انتخاب کنید:"
    )
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=get_military_packages_menu())

async def show_military_package_details(query, package_key):
    """Show detailed information about a military package"""
    user_id = str(query.from_user.id)
    credits = utils.users[user_id]['inventory']['credits']
    
    if package_key not in MILITARY_PACKAGES:
        await query.answer("❌ پکیج مورد نظر یافت نشد!", show_alert=True)
        return
    
    package = MILITARY_PACKAGES[package_key]
    
    # Check purchase limits and cooldowns
    current_turn = game_data.get('turn', 1)
    user_purchases = military_package_purchases.get(user_id, {}).get(package_key, [])
    current_season_purchases = [p for p in user_purchases if p.get('turn', 0) >= current_turn - 10]  # Last 10 turns = season
    
    # Check cooldown
    cooldown_end = military_package_cooldowns.get(user_id, {}).get(package_key, 0)
    current_time = time.time()
    cooldown_remaining = max(0, cooldown_end - current_time)
    
    # Build unit list in monospace format
    unit_emojis = {
        'soldiers': '🪖',
        'special_forces': '⚔️',
        'tanks': '🛡',
        'armored_vehicles': '🚛',
        'artillery': '🎯',
        'combat_robots': '🤖',
        'transport_planes': '✈️',
        'helicopters': '🚁',
        'fighter_jets': '🛩',
        'bombers': '💣',
        'drones': '🛸',
        'air_defense': '🛡',
        'coastal_artillery': '🏖',
        'speedboats': '🚤',
        'frigates': '🚢',
        'submarines': '🌊',
        'aircraft_carriers': '⚓️'
    }
    
    unit_names = {
        'soldiers': 'سرباز',
        'special_forces': 'نیرو ویژه',
        'tanks': 'تانک',
        'armored_vehicles': 'نفربر زرهی',
        'artillery': 'توپخانه',
        'combat_robots': 'ربات جنگی',
        'transport_planes': 'هواپیمای ترابری',
        'helicopters': 'بالگرد',
        'fighter_jets': 'جنگنده',
        'bombers': 'بمب‌افکن',
        'drones': 'پهپاد',
        'air_defense': 'پدافند هوایی',
        'coastal_artillery': 'توپ ساحلی',
        'speedboats': 'قایق تندرو',
        'frigates': 'ناوچه',
        'submarines': 'زیردریایی',
        'aircraft_carriers': 'ناو هواپیمابر'
    }
    
    units_text = "```\n"
    for unit_key, count in package['units'].items():
        if count > 0:
            emoji = unit_emojis.get(unit_key, '🔹')
            name = unit_names.get(unit_key, unit_key)
            units_text += f"{emoji} {count:,} {name}\n"
    units_text += "```"
    
    # Status messages
    status_messages = []
    
    if len(current_season_purchases) >= package['max_per_season']:
        status_messages.append(f"❌ حداکثر {package['max_per_season']} بار در هر فصل")
    elif cooldown_remaining > 0:
        hours = int(cooldown_remaining // 3600)
        minutes = int((cooldown_remaining % 3600) // 60)
        status_messages.append(f"⏰ کولداون: {hours}h {minutes}m")
    elif credits < package['price']:
        status_messages.append("❌ موجودی اعتبار کافی نیست")
    elif package['requires_admin_approval']:
        status_messages.append("⚠️ نیاز به تأیید ادمین")
    else:
        status_messages.append("✅ قابل خرید")
    
    status_text = "\n".join(status_messages)
    
    message = (
        f"{package['emoji']} <b>{package['name']}</b>\n\n"
        f"💠 <b>قیمت:</b> {package['price']:,} اعتبار جهانی\n"
        f"📊 <b>موجودی شما:</b> {credits:,} 💠\n"
        f"🔄 <b>حداکثر در فصل:</b> {package['max_per_season']} بار\n"
        f"⏰ <b>کولداون:</b> {package['cooldown_hours']} ساعت\n\n"
        f"<b>محتوای پکیج:</b>\n{units_text}\n\n"
        f"<b>وضعیت:</b>\n{status_text}"
    )
    
    # Create keyboard based on status
    keyboard = []
    
    if len(current_season_purchases) < package['max_per_season'] and cooldown_remaining <= 0 and credits >= package['price']:
        if package['requires_admin_approval']:
            keyboard.append([InlineKeyboardButton('📝 درخواست تأیید ادمین', callback_data=f'request_military_approval_{package_key}')])
        else:
            keyboard.append([InlineKeyboardButton('✅ تأیید خرید', callback_data=f'confirm_military_purchase_{package_key}')])
    
    keyboard.append([InlineKeyboardButton('❌ لغو', callback_data='shop_military_packages')])
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def execute_military_package_purchase(query, package_key):
    """Execute military package purchase"""
    user_id = str(query.from_user.id)
    
    # Check if user has an active country first
    if not has_active_country(user_id):
        await query.answer('❌ شما هیچ کشوری فعال ندارید. ابتدا کشور خود را فعال کنید.', show_alert=True)
        return
    
    if package_key not in MILITARY_PACKAGES:
        await query.answer("❌ پکیج مورد نظر یافت نشد!", show_alert=True)
        return
    
    package = MILITARY_PACKAGES[package_key]
    
    # Check if user exists and is activated
    if user_id not in utils.users:
        await query.answer("❌ شما در بازی ثبت‌نام نکرده‌اید!", show_alert=True)
        return
    
    if not utils.users[user_id].get('activated', False):
        await query.answer("❌ کشور شما فعال نشده است!", show_alert=True)
        return
    
    # Check purchase limits and cooldowns
    current_turn = game_data.get('turn', 1)
    user_purchases = military_package_purchases.get(user_id, {}).get(package_key, [])
    current_season_purchases = [p for p in user_purchases if p.get('turn', 0) >= current_turn - 10]
    
    if len(current_season_purchases) >= package['max_per_season']:
        await query.answer(f"❌ حداکثر {package['max_per_season']} بار در هر فصل!", show_alert=True)
        return
    
    # Check cooldown
    cooldown_end = military_package_cooldowns.get(user_id, {}).get(package_key, 0)
    current_time = time.time()
    if cooldown_end > current_time:
        remaining = int((cooldown_end - current_time) // 3600)
        await query.answer(f"❌ کولداون: {remaining} ساعت باقی مانده!", show_alert=True)
        return
    
    # Check credits
    credits = utils.users[user_id]['inventory']['credits']
    if credits < package['price']:
        await query.answer("❌ موجودی اعتبار جهانی کافی نیست!", show_alert=True)
        return
    
    # Execute purchase
    try:
        # Deduct credits
        utils.users[user_id]['inventory']['credits'] -= package['price']
        
        # Add units to resources
        if 'resources' not in utils.users[user_id]:
            utils.users[user_id]['resources'] = {}
        
        resources = utils.users[user_id]['resources']
        for unit_key, count in package['units'].items():
            if count > 0:
                resources[unit_key] = resources.get(unit_key, 0) + count
        
        # Record purchase
        if user_id not in military_package_purchases:
            military_package_purchases[user_id] = {}
        if package_key not in military_package_purchases[user_id]:
            military_package_purchases[user_id][package_key] = []
        
        military_package_purchases[user_id][package_key].append({
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'turn': current_turn,
            'cost': package['price']
        })
        
        # Set cooldown
        if user_id not in military_package_cooldowns:
            military_package_cooldowns[user_id] = {}
        military_package_cooldowns[user_id][package_key] = current_time + (package['cooldown_hours'] * 3600)
        
        # Save data
        utils.save_users()
        save_military_package_data()
        
        # Send success message to user
        country_name = utils.users[user_id].get('country', 'کشور ناشناس')
        success_message = (
            f"✅ <b>خرید موفق!</b>\n\n"
            f"🎖 <b>{package['name']}</b> با موفقیت خریداری شد!\n"
            f"💠 <b>هزینه:</b> {package['price']:,} اعتبار جهانی\n"
            f"📊 <b>موجودی جدید:</b> {utils.users[user_id]['inventory']['credits']:,} 💠\n\n"
            f"🔍 برای مشاهده نیروهای خود از دستور <code>/myforces</code> استفاده کنید."
        )
        
        await query.edit_message_text(success_message, parse_mode='HTML')
        
        # Send news channel announcement
        await send_military_package_news_announcement(country_name, package['name'])
        
    except Exception as e:
        print(f"[ERROR] خطا در خرید پکیج نظامی: {e}")
        await query.answer("❌ خطا در خرید! لطفاً دوباره تلاش کنید.", show_alert=True)

async def request_military_package_approval(query, package_key):
    """Request admin approval for military package purchase"""
    user_id = str(query.from_user.id)
    
    # Check if user has an active country first
    if not has_active_country(user_id):
        await query.answer('❌ شما هیچ کشوری فعال ندارید. ابتدا کشور خود را فعال کنید.', show_alert=True)
        return
    
    if package_key not in MILITARY_PACKAGES:
        await query.answer("❌ پکیج مورد نظر یافت نشد!", show_alert=True)
        return
    
    package = MILITARY_PACKAGES[package_key]
    
    if not package['requires_admin_approval']:
        await query.answer("❌ این پکیج نیازی به تأیید ادمین ندارد!", show_alert=True)
        return
    
    # Check if already requested
    if user_id in military_package_approvals and package_key in military_package_approvals[user_id]:
        approval = military_package_approvals[user_id][package_key]
        if approval['status'] == 'pending':
            await query.answer("❌ درخواست شما در انتظار تأیید است!", show_alert=True)
            return
        elif approval['status'] == 'approved':
            await query.answer("✅ درخواست شما تأیید شده است! می‌توانید خرید کنید.", show_alert=True)
            return
    
    # Create approval request
    if user_id not in military_package_approvals:
        military_package_approvals[user_id] = {}
    
    military_package_approvals[user_id][package_key] = {
        'status': 'pending',
        'admin_id': None,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'package_name': package['name'],
        'package_price': package['price']
    }
    
    save_military_package_data()
    
    # Notify admin
    country_name = utils.users[user_id].get('country', 'کشور ناشناس')
    admin_message = (
        f"📝 <b>درخواست تأیید پکیج نظامی</b>\n\n"
        f"👤 <b>کشور:</b> {country_name}\n"
        f"🎖 <b>پکیج:</b> {package['name']}\n"
        f"💠 <b>قیمت:</b> {package['price']:,} اعتبار جهانی\n"
        f"⏰ <b>زمان:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"لطفاً تصمیم خود را اتخاذ کنید:"
    )
    
    keyboard = [
        [InlineKeyboardButton('✅ تأیید', callback_data=f'admin_approve_military_{user_id}_{package_key}')],
        [InlineKeyboardButton('❌ رد', callback_data=f'admin_reject_military_{user_id}_{package_key}')]
    ]
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        print(f"[ERROR] خطا در ارسال پیام به ادمین: {e}")
    
    # Confirm to user
    await query.edit_message_text(
        f"📝 <b>درخواست ارسال شد!</b>\n\n"
        f"درخواست تأیید {package['name']} به ادمین ارسال شد.\n"
        f"لطفاً منتظر تأیید باشید.",
        parse_mode='HTML'
    )

async def send_military_package_news_announcement(country_name, package_name):
    """Send news channel announcement for military package purchase"""
    try:
        # Create a generic announcement without revealing exact numbers
        if package_name == "پکیج ارتش‌های متحد":
            caption = f"📰 کشور {country_name} توان نظامی خود را با یک بسته جدید تقویت کرد. این خرید نشان‌دهنده تغییرات مهم در توازن قدرت منطقه‌ای است."
        else:
            caption = f"📰 کشور {country_name} توان نظامی خود را با یک بسته جدید تقویت کرد."
        
        # Send as image with caption
        await bot.send_photo(
            chat_id=NEWS_CHANNEL_ID,
            photo="https://t.me/TextEmpire_IR/178",
            caption=caption,
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"[ERROR] خطا در ارسال اعلان خبری: {e}")

async def handle_admin_military_approval(query, user_id, package_key, approved):
    """Handle admin approval/rejection of military package purchase"""
    if package_key not in MILITARY_PACKAGES:
        await query.answer("❌ پکیج مورد نظر یافت نشد!", show_alert=True)
        return
    
    package = MILITARY_PACKAGES[package_key]
    
    # Update approval status
    if user_id not in military_package_approvals:
        military_package_approvals[user_id] = {}
    
    military_package_approvals[user_id][package_key] = {
        'status': 'approved' if approved else 'rejected',
        'admin_id': str(query.from_user.id),
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'package_name': package['name'],
        'package_price': package['price']
    }
    
    save_military_package_data()
    
    # Notify user
    country_name = utils.users.get(user_id, {}).get('country', 'کشور ناشناس')
    
    if approved:
        user_message = (
            f"✅ <b>درخواست تأیید شد!</b>\n\n"
            f"🎖 درخواست شما برای {package['name']} توسط ادمین تأیید شد.\n"
            f"اکنون می‌توانید این پکیج را خریداری کنید."
        )
        
        # Send news announcement for approved high-tier package
        if package_key == 'united_armies':
            try:
                caption = f"📰 کشور {country_name} توان نظامی خود را با یک بسته جدید تقویت کرد. این خرید نشان‌دهنده تغییرات مهم در توازن قدرت منطقه‌ای است."
                await bot.send_photo(
                    chat_id=NEWS_CHANNEL_ID,
                    photo="https://t.me/TextEmpire_IR/178",
                    caption=caption,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"[ERROR] خطا در ارسال اعلان خبری: {e}")
    else:
        user_message = (
            f"❌ <b>درخواست رد شد!</b>\n\n"
            f"🎖 درخواست شما برای {package['name']} توسط ادمین رد شد.\n"
            f"لطفاً درخواست جدیدی ارسال کنید یا پکیج دیگری انتخاب کنید."
        )
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=user_message,
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"[ERROR] خطا در ارسال پیام به کاربر: {e}")
    
    # Update admin message
    admin_message = (
        f"✅ <b>تصمیم اتخاذ شد!</b>\n\n"
        f"👤 <b>کشور:</b> {country_name}\n"
        f"🎖 <b>پکیج:</b> {package['name']}\n"
        f"📊 <b>وضعیت:</b> {'تأیید شد' if approved else 'رد شد'}\n"
        f"⏰ <b>زمان:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    await query.edit_message_text(admin_message, parse_mode='HTML')

async def show_resource_packages_menu(query):
    """Show resource packages menu"""
    text = "📦 <b>پکیج‌های منابع</b>\n\nانتخاب کنید:"
    reply_markup = get_resource_packages_menu()
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_economic_packages_menu(query):
    """Show economic packages menu"""
    user_id = str(query.from_user.id)
    credits = utils.users[user_id]['inventory']['credits']
    
    message = (
        "📈 <b>پکیج‌های اقتصادی</b>\n\n"
        f"💠 اعتبار شما: <b>{credits:,}</b>\n\n"
        "📦 <b>پکیج‌های موجود:</b>\n\n"
        "🆘 <b>پکیج نیازمند</b> — 50 💠\n"
        "👨‍🌾 <b>پکیج رعیت</b> — 200 💠\n"
        "👨‍💼 <b>پکیج تاجر</b> — 500 💠\n"
        "👨‍💻 <b>پکیج وزیر رعیا</b> — 1000 💠\n"
        "👑 <b>پکیج پادشاه</b> — 4999 💠\n\n"
        "لطفاً پکیج مورد نظر خود را انتخاب کنید:"
    )
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=get_economic_packages_menu())

async def show_resource_package_details(query, package_key):
    """Show detailed information about a resource package"""
    user_id = str(query.from_user.id)
    credits = utils.users[user_id]['inventory']['credits']
    
    if package_key not in RESOURCE_PACKAGES:
        await query.answer("❌ پکیج یافت نشد!", show_alert=True)
        return
    
    package = RESOURCE_PACKAGES[package_key]
    
    # Resource emoji mapping
    resource_emojis = {
        'gold': '🥇',
        'steel': '🔩',
        'iron': '⛓️',
        'copper': '🔧',
        'diamond': '💎',
        'aluminum': '🔧',
        'titanium': '🔩',
        'oil': '🛢️',
        'gas': '⛽',
        'electricity': '⚡',
        'uranium': '☢️',
        'uranium_ore': '🪨',
        'centrifuge': '🔄',
        'yellow_cake': '🍰',
        'wheat': '🌾',
        'rice': '🍚',
        'fruits': '🍎',
        'electronics': '🔌',
        'space_parts': '🚀',
        'pride_cars': '🚗',
        'benz_cars': '🚙'
    }
    
    # Build resources list
    resources_text = "📦 <b>محتوای پکیج:</b>\n"
    for resource, amount in package['resources'].items():
        emoji = resource_emojis.get(resource, '📦')
        resources_text += f"<code>{emoji} {amount:,}</code>\n"
    
    # Check purchase limits
    current_season = utils.game_data.get('season', 1)
    user_purchases = resource_package_purchases.get(user_id, {}).get(package_key, [])
    season_purchases = [p for p in user_purchases if p.get('season') == current_season]
    remaining_purchases = package['season_limit'] - len(season_purchases)
    
    # Check cooldown
    cooldown_info = ""
    if user_id in resource_package_cooldowns and package_key in resource_package_cooldowns[user_id]:
        last_purchase = resource_package_cooldowns[user_id][package_key]
        cooldown_hours = package['cooldown_hours']
        time_passed = (time.time() - last_purchase) / 3600
        if time_passed < cooldown_hours:
            remaining_hours = cooldown_hours - time_passed
            cooldown_info = f"\n⏰ <b>کولداون:</b> {remaining_hours:.1f} ساعت باقی مانده"
    
    # Check admin approval status
    approval_info = ""
    if package['requires_admin_approval']:
        if user_id in resource_package_approvals and package_key in resource_package_approvals[user_id]:
            approval = resource_package_approvals[user_id][package_key]
            if approval['status'] == 'pending':
                approval_info = "\n⏳ <b>وضعیت:</b> در انتظار تأیید ادمین"
            elif approval['status'] == 'approved':
                approval_info = "\n✅ <b>وضعیت:</b> تأیید شده - آماده خرید"
            elif approval['status'] == 'rejected':
                approval_info = "\n❌ <b>وضعیت:</b> رد شده"
        else:
            approval_info = "\n⚠️ <b>نیاز به تأیید ادمین</b>"
    
    message = (
        f"📦 <b>{package['name']}</b>\n\n"
        f"{resources_text}\n"
        f"💰 <b>قیمت:</b> {package['cost']} 💠\n"
        f"📊 <b>موجودی شما:</b> {credits} 💠\n"
        f"📈 <b>محدودیت فصل:</b> {remaining_purchases}/{package['season_limit']}\n"
        f"{cooldown_info}{approval_info}\n\n"
        f"⏰ <b>زمان:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    # Create buttons
    keyboard = []
    if package['requires_admin_approval']:
        if user_id not in resource_package_approvals or package_key not in resource_package_approvals[user_id]:
            keyboard.append([InlineKeyboardButton('📝 درخواست تأیید ادمین', callback_data=f'request_resource_approval_{package_key}')])
        elif resource_package_approvals[user_id][package_key]['status'] == 'approved':
            keyboard.append([InlineKeyboardButton('✅ تأیید خرید', callback_data=f'confirm_resource_purchase_{package_key}')])
    else:
        keyboard.append([InlineKeyboardButton('✅ تأیید خرید', callback_data=f'confirm_resource_purchase_{package_key}')])
    
    keyboard.append([InlineKeyboardButton('❌ لغو', callback_data='shop_resource_packages')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

async def show_economic_package_details(query, package_key):
    """Show detailed information about an economic package"""
    user_id = str(query.from_user.id)
    credits = utils.users[user_id]['inventory']['credits']
    
    if package_key not in ECONOMIC_PACKAGES:
        await query.answer("❌ پکیج مورد نظر یافت نشد!", show_alert=True)
        return
    
    package = ECONOMIC_PACKAGES[package_key]
    
    # Check purchase limits and cooldowns
    current_turn = game_data.get('turn', 1)
    user_purchases = economic_package_purchases.get(user_id, {}).get(package_key, [])
    current_season_purchases = [p for p in user_purchases if p.get('turn', 0) >= current_turn - 10]  # Last 10 turns = season
    
    # Check cooldown
    cooldown_end = economic_package_cooldowns.get(user_id, {}).get(package_key, 0)
    current_time = time.time()
    cooldown_remaining = max(0, cooldown_end - current_time)
    
    # Format money amount
    money_amount = package['money_amount']
    if money_amount >= 1_000_000_000:
        money_display = f"{money_amount // 1_000_000_000}B"
    else:
        money_display = f"{money_amount // 1_000_000}M"
    
    # Status messages
    status_messages = []
    
    if len(current_season_purchases) >= package['max_per_season']:
        status_messages.append(f"❌ حداکثر {package['max_per_season']} بار در هر فصل")
    elif cooldown_remaining > 0:
        hours = int(cooldown_remaining // 3600)
        minutes = int((cooldown_remaining % 3600) // 60)
        status_messages.append(f"⏰ کولداون: {hours}h {minutes}m")
    elif credits < package['price']:
        status_messages.append("❌ موجودی اعتبار کافی نیست")
    elif package['requires_admin_approval']:
        status_messages.append("⚠️ نیاز به تأیید ادمین")
    else:
        status_messages.append("✅ قابل خرید")
    
    status_text = "\n".join(status_messages)
    
    message = (
        f"{package['emoji']} <b>{package['name']}</b>\n\n"
        f"💠 <b>قیمت:</b> {package['price']:,} اعتبار جهانی\n"
        f"💵 <b>مبلغ:</b> {money_display}\n"
        f"📊 <b>موجودی شما:</b> {credits:,} 💠\n"
        f"🔄 <b>حداکثر در فصل:</b> {package['max_per_season']} بار\n"
        f"⏰ <b>کولداون:</b> {package['cooldown_hours']} ساعت\n\n"
        f"<b>وضعیت:</b>\n{status_text}"
    )
    
    # Create keyboard based on status
    keyboard = []
    
    if len(current_season_purchases) < package['max_per_season'] and cooldown_remaining <= 0 and credits >= package['price']:
        if package['requires_admin_approval']:
            keyboard.append([InlineKeyboardButton('📝 درخواست تأیید ادمین', callback_data=f'request_economic_approval_{package_key}')])
        else:
            keyboard.append([InlineKeyboardButton('✅ تأیید خرید', callback_data=f'confirm_economic_purchase_{package_key}')])
    
    keyboard.append([InlineKeyboardButton('❌ لغو', callback_data='shop_economy')])
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def execute_resource_package_purchase(query, package_key):
    """Execute resource package purchase"""
    user_id = str(query.from_user.id)
    # نیاز به کشور فعال
    if not has_active_country(user_id):
        await query.answer('❌ شما هیچ کشوری فعال ندارید. ابتدا کشور خود را فعال کنید.', show_alert=True)
        return
    user_id = str(query.from_user.id)
    
    if package_key not in RESOURCE_PACKAGES:
        await query.answer("❌ پکیج یافت نشد!", show_alert=True)
        return
    
    package = RESOURCE_PACKAGES[package_key]
    
    # Check if user has enough credits
    credits = utils.users[user_id]['inventory']['credits']
    if credits < package['cost']:
        await query.answer("❌ اعتبار کافی ندارید!", show_alert=True)
        return
    
    # Check admin approval if required
    if package['requires_admin_approval']:
        if user_id not in resource_package_approvals or package_key not in resource_package_approvals[user_id]:
            await query.answer("❌ ابتدا باید درخواست تأیید ادمین ارسال کنید!", show_alert=True)
            return
        
        approval = resource_package_approvals[user_id][package_key]
        if approval['status'] != 'approved':
            await query.answer("❌ درخواست شما هنوز تأیید نشده است!", show_alert=True)
            return
    
    # Check purchase limits
    current_season = utils.game_data.get('season', 1)
    user_purchases = resource_package_purchases.get(user_id, {}).get(package_key, [])
    season_purchases = [p for p in user_purchases if p.get('season') == current_season]
    if len(season_purchases) >= package['season_limit']:
        await query.answer(f"❌ شما در این فصل {package['season_limit']} بار این پکیج را خریداری کرده‌اید!", show_alert=True)
        return
    
    # Check cooldown
    if user_id in resource_package_cooldowns and package_key in resource_package_cooldowns[user_id]:
        last_purchase = resource_package_cooldowns[user_id][package_key]
        cooldown_hours = package['cooldown_hours']
        time_passed = (time.time() - last_purchase) / 3600
        if time_passed < cooldown_hours:
            remaining_hours = cooldown_hours - time_passed
            await query.answer(f"❌ باید {remaining_hours:.1f} ساعت دیگر صبر کنید!", show_alert=True)
            return
    
    # Deduct credits
    utils.users[user_id]['inventory']['credits'] -= package['cost']
    
    # Add resources to user's treasury (ensure structure exists)
    if 'resources' not in utils.users[user_id] or not isinstance(utils.users[user_id]['resources'], dict):
        utils.users[user_id]['resources'] = {}
    resources = utils.users[user_id]['resources']
    for resource, amount in package['resources'].items():
        resources[resource] = resources.get(resource, 0) + amount
    
    # Log purchase
    if user_id not in resource_package_purchases:
        resource_package_purchases[user_id] = {}
    if package_key not in resource_package_purchases[user_id]:
        resource_package_purchases[user_id][package_key] = []
    
    resource_package_purchases[user_id][package_key].append({
        'date': datetime.now().isoformat(),
        'season': current_season,
        'amount': package['cost']
    })
    
    # Set cooldown
    if user_id not in resource_package_cooldowns:
        resource_package_cooldowns[user_id] = {}
    resource_package_cooldowns[user_id][package_key] = time.time()
    
    # Save data
    utils.save_users()
    save_resource_package_data()
    
    # Send success message to user
    country_name = utils.users[user_id]['country']
    success_message = (
        f"✅ خرید موفق!\n\n"
        f"پکیج {package['name']} به خزانه کشور شما اضافه شد.\n\n"
        f"💰 هزینه: {package['cost']} 💠\n"
        f"📦 منابع اضافه شده به خزانه کشور"
    )
    
    try:
        await query.edit_message_text(success_message, parse_mode='HTML')
    except Exception:
        pass
    
    # Send news announcement using global bot instance
    await send_resource_package_news_announcement(country_name, package['name'], bot)

async def request_resource_package_approval(query, package_key):
    """Request admin approval for resource package"""
    user_id = str(query.from_user.id)
    
    # Check if user has an active country first
    if not has_active_country(user_id):
        await query.answer('❌ شما هیچ کشوری فعال ندارید. ابتدا کشور خود را فعال کنید.', show_alert=True)
        return
    
    if package_key not in RESOURCE_PACKAGES:
        await query.answer("❌ پکیج یافت نشد!", show_alert=True)
        return
    
    package = RESOURCE_PACKAGES[package_key]
    
    # Check if already requested
    if user_id in resource_package_approvals and package_key in resource_package_approvals[user_id]:
        approval = resource_package_approvals[user_id][package_key]
        if approval['status'] == 'pending':
            await query.answer("❌ درخواست شما قبلاً ارسال شده و در انتظار تأیید است!", show_alert=True)
            return
        elif approval['status'] == 'approved':
            await query.answer("✅ درخواست شما قبلاً تأیید شده است!", show_alert=True)
            return
    
    # Create approval request
    if user_id not in resource_package_approvals:
        resource_package_approvals[user_id] = {}
    
    resource_package_approvals[user_id][package_key] = {
        'status': 'pending',
        'admin_id': '',
        'date': datetime.now().isoformat()
    }
    
    save_resource_package_data()
    
    # Notify admin
    country_name = utils.users[user_id]['country']
    admin_message = (
        f"📦 <b>درخواست تأیید پکیج منابع</b>\n\n"
        f"👤 <b>کاربر:</b> {country_name} ({get_user_capital(user_id)})\n"
        f"📦 <b>پکیج:</b> {package['name']}\n"
        f"💰 <b>قیمت:</b> {package['cost']} 💠\n"
        f"📊 <b>اعتبار کاربر:</b> {utils.users[user_id]['inventory']['credits']} 💠\n\n"
        f"⏰ <b>زمان:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    keyboard = [
        [
            InlineKeyboardButton('✅ تأیید', callback_data=f'approve_resource_{user_id}_{package_key}'),
            InlineKeyboardButton('❌ رد', callback_data=f'reject_resource_{user_id}_{package_key}')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Use global bot instance to avoid context-bound issues
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception as e:
        # Log error for diagnostics if admin notification fails
        print(f"[ERROR] Failed to notify admin for resource package approval: {e}")
    
    await query.edit_message_text(f'درخواست تأیید پکیج {package["name"]} ارسال شد و منتظر تایید ادمین است.')

async def handle_admin_resource_approval(query, user_id, package_key, approved):
    """Handle admin approval/rejection of resource package request"""
    if user_id not in resource_package_approvals or package_key not in resource_package_approvals[user_id]:
        await query.answer("❌ درخواست یافت نشد!", show_alert=True)
        return
    
    package = RESOURCE_PACKAGES[package_key]
    country_name = utils.users[user_id]['country']
    
    if approved:
        resource_package_approvals[user_id][package_key]['status'] = 'approved'
        resource_package_approvals[user_id][package_key]['admin_id'] = str(query.from_user.id)
        
        # Send approval message to user
        try:
            await query.bot.send_message(
                chat_id=int(user_id),
                text=f"✅ درخواست تأیید شد!\n\n💰 درخواست شما برای {package['name']} توسط ادمین تأیید شد.\nاکنون می‌توانید این پکیج را خریداری کنید.",
                parse_mode='HTML'
            )
        except Exception:
            pass
        
        # Update admin message
        keyboard = [
            [InlineKeyboardButton('✅ تأیید شده', callback_data='noop')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                text=f"✅ <b>درخواست تأیید شد</b>\n\n👤 کاربر: {country_name} ({get_user_capital(user_id)})\n📦 پکیج: {package['name']}\n⏰ زمان تأیید: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception:
            pass

        # Send news to channel (resource-focused wording)
        try:
            caption = f"📰 کشور {country_name} منابع خود را با یک بسته جدید تقویت کرد."
            if package['name'] == 'پکیج امپراطور':
                caption = (
                    f"📢 تغییر بزرگ در منابع جهانی!\n\n"
                    f"کشور {country_name} منابع خود را با {package['name']} تقویت کرد."
                )
            await bot.send_photo(
                chat_id=NEWS_CHANNEL_ID, 
                photo="https://t.me/TextEmpire_IR/178",
                caption=caption, 
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"[ERROR] Failed to send resource approval news: {e}")
    else:
        resource_package_approvals[user_id][package_key]['status'] = 'rejected'
        resource_package_approvals[user_id][package_key]['admin_id'] = str(query.from_user.id)
        
        # Send rejection message to user
        try:
            await query.bot.send_message(
                chat_id=int(user_id),
                text=f"❌ درخواست رد شد!\n\nدرخواست شما برای {package['name']} توسط ادمین رد شد.\nلطفاً با پشتیبانی تماس بگیرید.",
                parse_mode='HTML'
            )
        except Exception:
            pass
        
        # Update admin message
        keyboard = [
            [InlineKeyboardButton('❌ رد شده', callback_data='noop')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                text=f"❌ <b>درخواست رد شد</b>\n\n👤 کاربر: {country_name} ({get_user_capital(user_id)})\n📦 پکیج: {package['name']}\n⏰ زمان رد: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception:
            pass
    
    save_resource_package_data()

async def send_resource_package_news_announcement(country_name, package_name, bot):
    """Send news channel announcement for resource package purchase"""
    try:
        caption = f"📰 کشور {country_name} منابع خود را با یک بسته جدید تقویت کرد."
        
        # Special announcement for emperor package
        if package_name == 'پکیج امپراطور':
            caption = f"📢 تغییر بزرگ در منابع جهانی!\n\nکشور {country_name} با خرید {package_name} منابع خود را به طور چشمگیری تقویت کرد!"
        
        # Send as image with caption
        await bot.send_photo(
            chat_id=NEWS_CHANNEL_ID,
            photo="https://t.me/TextEmpire_IR/178",
            caption=caption,
            parse_mode='HTML'
        )
    except Exception:
        pass

async def execute_economic_package_purchase(query, package_key):
    """Execute economic package purchase"""
    user_id = str(query.from_user.id)
    # نیاز به کشور فعال
    if not has_active_country(user_id):
        await query.answer('❌ شما هیچ کشوری فعال ندارید. ابتدا کشور خود را فعال کنید.', show_alert=True)
        return
    
    if package_key not in ECONOMIC_PACKAGES:
        await query.answer("❌ پکیج مورد نظر یافت نشد!", show_alert=True)
        return
    
    package = ECONOMIC_PACKAGES[package_key]
    
    # Check if user exists and is activated
    if user_id not in utils.users:
        await query.answer("❌ شما در بازی ثبت‌نام نکرده‌اید!", show_alert=True)
        return
    
    if not utils.users[user_id].get('activated', False):
        await query.answer("❌ کشور شما فعال نشده است!", show_alert=True)
        return
    
    # Check purchase limits and cooldowns
    current_turn = game_data.get('turn', 1)
    user_purchases = economic_package_purchases.get(user_id, {}).get(package_key, [])
    current_season_purchases = [p for p in user_purchases if p.get('turn', 0) >= current_turn - 10]
    
    if len(current_season_purchases) >= package['max_per_season']:
        await query.answer(f"❌ حداکثر {package['max_per_season']} بار در هر فصل!", show_alert=True)
        return
    
    # Check cooldown
    cooldown_end = economic_package_cooldowns.get(user_id, {}).get(package_key, 0)
    current_time = time.time()
    if cooldown_end > current_time:
        remaining = int((cooldown_end - current_time) // 3600)
        await query.answer(f"❌ کولداون: {remaining} ساعت باقی مانده!", show_alert=True)
        return
    
    # Check credits
    credits = utils.users[user_id]['inventory']['credits']
    if credits < package['price']:
        await query.answer("❌ موجودی اعتبار جهانی کافی نیست!", show_alert=True)
        return
    
    # Check admin approval for packages that require it
    if package['requires_admin_approval']:
        if user_id not in economic_package_approvals or package_key not in economic_package_approvals[user_id]:
            await query.answer("❌ ابتدا باید درخواست تأیید ادمین ارسال کنید!", show_alert=True)
            return
        
        approval = economic_package_approvals[user_id][package_key]
        if approval['status'] != 'approved':
            await query.answer("❌ درخواست شما هنوز تأیید نشده است!", show_alert=True)
            return
    
    # Execute purchase
    try:
        # Deduct credits
        utils.users[user_id]['inventory']['credits'] -= package['price']
        
        # Add money to resources (cash)
        if 'resources' not in utils.users[user_id]:
            utils.users[user_id]['resources'] = {}
        
        resources = utils.users[user_id]['resources']
        resources['cash'] = resources.get('cash', 0) + package['money_amount']
        
        # Record purchase
        if user_id not in economic_package_purchases:
            economic_package_purchases[user_id] = {}
        if package_key not in economic_package_purchases[user_id]:
            economic_package_purchases[user_id][package_key] = []
        
        economic_package_purchases[user_id][package_key].append({
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'turn': current_turn,
            'cost': package['price'],
            'amount': package['money_amount']
        })
        
        # Set cooldown
        if user_id not in economic_package_cooldowns:
            economic_package_cooldowns[user_id] = {}
        economic_package_cooldowns[user_id][package_key] = current_time + (package['cooldown_hours'] * 3600)
        
        # Save data
        utils.save_users()
        save_economic_package_data()
        
        # Send success message to user
        country_name = utils.users[user_id].get('country', 'کشور ناشناس')
        money_display = f"{package['money_amount'] // 1_000_000_000}B" if package['money_amount'] >= 1_000_000_000 else f"{package['money_amount'] // 1_000_000}M"
        
        success_message = (
            f"✅ <b>خرید موفق!</b>\n\n"
            f"💰 <b>{package['name']}</b> با موفقیت خریداری شد!\n"
            f"💠 <b>هزینه:</b> {package['price']:,} اعتبار جهانی\n"
            f"💵 <b>مبلغ اضافه شده:</b> {money_display}\n"
            f"📊 <b>موجودی جدید:</b> {utils.users[user_id]['inventory']['credits']:,} 💠\n"
            f"🏦 <b>خزانه جدید:</b> {resources['cash']:,} 💵"
        )
        
        await query.edit_message_text(success_message, parse_mode='HTML')
        
        # Send news channel announcement
        await send_economic_package_news_announcement(country_name, package['name'])
        
    except Exception as e:
        print(f"[ERROR] خطا در خرید پکیج اقتصادی: {e}")
        await query.answer("❌ خطا در خرید! لطفاً دوباره تلاش کنید.", show_alert=True)

async def request_economic_package_approval(query, package_key):
    """Request admin approval for economic package purchase"""
    user_id = str(query.from_user.id)
    
    # Check if user has an active country first
    if not has_active_country(user_id):
        await query.answer('❌ شما هیچ کشوری فعال ندارید. ابتدا کشور خود را فعال کنید.', show_alert=True)
        return
    
    if package_key not in ECONOMIC_PACKAGES:
        await query.answer("❌ پکیج مورد نظر یافت نشد!", show_alert=True)
        return
    
    package = ECONOMIC_PACKAGES[package_key]
    
    if not package['requires_admin_approval']:
        await query.answer("❌ این پکیج نیازی به تأیید ادمین ندارد!", show_alert=True)
        return
    
    # Check if already requested
    if user_id in economic_package_approvals and package_key in economic_package_approvals[user_id]:
        approval = economic_package_approvals[user_id][package_key]
        if approval['status'] == 'pending':
            await query.answer("❌ درخواست شما در انتظار تأیید است!", show_alert=True)
            return
        elif approval['status'] == 'approved':
            await query.answer("✅ درخواست شما تأیید شده است! می‌توانید خرید کنید.", show_alert=True)
            return
    
    # Create approval request
    if user_id not in economic_package_approvals:
        economic_package_approvals[user_id] = {}
    
    economic_package_approvals[user_id][package_key] = {
        'status': 'pending',
        'admin_id': None,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'package_name': package['name'],
        'package_price': package['price'],
        'money_amount': package['money_amount']
    }
    
    save_economic_package_data()
    
    # Notify admin
    country_name = utils.users[user_id].get('country', 'کشور ناشناس')
    money_display = f"{package['money_amount'] // 1_000_000_000}B" if package['money_amount'] >= 1_000_000_000 else f"{package['money_amount'] // 1_000_000}M"
    
    admin_message = (
        f"📝 <b>درخواست تأیید پکیج اقتصادی</b>\n\n"
        f"👤 <b>کشور:</b> {country_name}\n"
        f"💰 <b>پکیج:</b> {package['name']}\n"
        f"💠 <b>قیمت:</b> {package['price']:,} اعتبار جهانی\n"
        f"💵 <b>مبلغ:</b> {money_display}\n"
        f"⏰ <b>زمان:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"لطفاً تصمیم خود را اتخاذ کنید:"
    )
    
    keyboard = [
        [InlineKeyboardButton('✅ تأیید', callback_data=f'admin_approve_economic_{user_id}_{package_key}')],
        [InlineKeyboardButton('❌ رد', callback_data=f'admin_reject_economic_{user_id}_{package_key}')]
    ]
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        print(f"[ERROR] خطا در ارسال پیام به ادمین: {e}")
    
    # Confirm to user
    await query.edit_message_text(
        f"📝 <b>درخواست ارسال شد!</b>\n\n"
        f"درخواست تأیید {package['name']} به ادمین ارسال شد.\n"
        f"لطفاً منتظر تأیید باشید.",
        parse_mode='HTML'
    )

async def send_economic_package_news_announcement(country_name, package_name):
    """Send news channel announcement for economic package purchase"""
    try:
        # Create a generic announcement without revealing exact amounts
        if package_name == "پکیج پادشاه":
            caption = f"📢 تغییر بزرگ در اقتصاد جهانی! کشور {country_name} اقتصاد خود را با یک بسته جدید تقویت کرد."
        else:
            caption = f"📰 کشور {country_name} اقتصاد خود را با یک بسته جدید تقویت کرد."
        
        # Send as image with caption
        await bot.send_photo(
            chat_id=NEWS_CHANNEL_ID,
            photo="https://t.me/TextEmpire_IR/178",
            caption=caption,
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"[ERROR] خطا در ارسال اعلان خبری: {e}")

async def handle_admin_economic_approval(query, user_id, package_key, approved):
    """Handle admin approval/rejection of economic package purchase"""
    if package_key not in ECONOMIC_PACKAGES:
        await query.answer("❌ پکیج مورد نظر یافت نشد!", show_alert=True)
        return
    
    package = ECONOMIC_PACKAGES[package_key]
    
    # Update approval status
    if user_id not in economic_package_approvals:
        economic_package_approvals[user_id] = {}
    
    economic_package_approvals[user_id][package_key] = {
        'status': 'approved' if approved else 'rejected',
        'admin_id': str(query.from_user.id),
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'package_name': package['name'],
        'package_price': package['price'],
        'money_amount': package['money_amount']
    }
    
    save_economic_package_data()
    
    # Notify user
    country_name = utils.users.get(user_id, {}).get('country', 'کشور ناشناس')
    
    if approved:
        user_message = (
            f"✅ <b>درخواست تأیید شد!</b>\n\n"
            f"💰 درخواست شما برای {package['name']} توسط ادمین تأیید شد.\n"
            f"اکنون می‌توانید این پکیج را خریداری کنید."
        )
        
        # Send special news announcement for approved king package
        if package_key == 'king':
            try:
                caption = f"📢 تغییر بزرگ در اقتصاد جهانی! کشور {country_name} اقتصاد خود را با یک بسته جدید تقویت کرد."
                await bot.send_photo(
                    chat_id=NEWS_CHANNEL_ID,
                    photo="https://t.me/TextEmpire_IR/178",
                    caption=caption,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"[ERROR] خطا در ارسال اعلان خبری: {e}")
    else:
        user_message = (
            f"❌ <b>درخواست رد شد!</b>\n\n"
            f"💰 درخواست شما برای {package['name']} توسط ادمین رد شد.\n"
            f"لطفاً درخواست جدیدی ارسال کنید یا پکیج دیگری انتخاب کنید."
        )
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=user_message,
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"[ERROR] خطا در ارسال پیام به کاربر: {e}")
    
    # Update admin message
    admin_message = (
        f"✅ <b>تصمیم اتخاذ شد!</b>\n\n"
        f"👤 <b>کشور:</b> {country_name}\n"
        f"💰 <b>پکیج:</b> {package['name']}\n"
        f"📊 <b>وضعیت:</b> {'تأیید شد' if approved else 'رد شد'}\n"
        f"⏰ <b>زمان:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    await query.edit_message_text(admin_message, parse_mode='HTML')

async def show_diplomatic_menu(query):
    """Show diplomatic packages menu"""
    user_id = str(query.from_user.id)
    credits = utils.users[user_id]['inventory']['credits']
    
    message = (
        "🤝 <b>پکیج‌های دیپلماتیک</b>\n\n"
        f"💠 اعتبار شما: <b>{credits:,}</b>\n\n"
        "📦 <b>پکیج‌های موجود:</b>\n\n"
        "🔹 <b>توافق پشت پرده</b> - 800 💠\n"
        "• بی‌اثر شدن تحریم‌ها علیه کشور شما\n\n"
        "🔹 <b>دوستی اجباری</b> - 900 💠\n"
        "• برقراری صلح برای 12 دور"
    )
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=get_diplomatic_menu())

async def show_special_menu(query):
    """Show special packages menu"""
    user_id = str(query.from_user.id)
    credits = utils.users[user_id]['inventory']['credits']
    
    message = (
        "🎁 <b>پکیج‌های ویژه</b>\n\n"
        f"💠 اعتبار شما: <b>{credits:,}</b>\n\n"
        "📦 <b>پکیج‌های موجود:</b>\n\n"
        "🔹 <b>🛡 گنبد آهنین</b> — 1000 💠\n"
        "• تمام دفاع‌ها ×2 تا پایان فصل\n\n"
        "🔹 <b>⚙️ تکنولوژی تولید</b> — 500 💠\n"
        "• تولید معادن/مزارع/نیروگاه‌ها ×2\n\n"
        "🔹 <b>🔒 امنیت یک نعمت</b> — 250 💠\n"
        "• رضایت روی 100% قفل می‌شود\n\n"
        "🔹 <b>🏹 رابین هود</b> — 500 💠\n"
        "• +2.5% نرخ رشد ثابت تا پایان فصل\n\n"
        "🔹 <b>🤝 دوری و دوستی</b> — 500 💠\n"
        "• جلوگیری از اعلان جنگ؛ روابط +10 برای 20 نوبت"
    )
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=get_special_menu())

async def show_inventory_menu(query):
    """Show user's inventory and shop effects"""
    user_id = str(query.from_user.id)
    initialize_user_inventory(user_id)
    inventory = utils.users[user_id]['inventory']
    military = utils.users[user_id]['military']
    economy = utils.users[user_id]['economy']
    diplomacy = utils.users[user_id]['diplomacy']
    domestic = utils.users[user_id]['domestic']
    
    message = (
        "📊 <b>موجودی و اثرات فروشگاه</b>\n\n"
        f"💠 <b>اعتبار جهانی:</b> {inventory['credits']:,}\n\n"
        f"⚔️ <b>نظامی:</b>\n"
        f"• ضریب قدرت دفاعی: {military['defense_power']:.2f}x\n"
        f"• نوبت‌های باقی‌مانده: {military['defense_buff_turns']}\n"
        f"• بونوس موفقیت جنگ: +{military['war_success_bonus']*100:.0f}%\n\n"
        f"📈 <b>اقتصادی:</b>\n"
        f"• ضریب تولید: {economy['resources_production']:.2f}x\n"
        f"• نوبت‌های باقی‌مانده: {economy['production_buff_turns']}\n"
        f"• وام فعال: {economy['loan_turns']} نوبت\n"
        f"• بهره وام: {economy['loan_interest']*100:.0f}%\n\n"
        f"🤝 <b>دیپلماتیک:</b>\n"
        f"• مصونیت تحریم: {'✅' if diplomacy['sanction_immunity'] else '❌'}\n"
        f"• صلح اجباری: {diplomacy['forced_peace_turns']} نوبت\n"
        f"• کشور صلح: {diplomacy['forced_peace_country'] or 'هیچ'}\n\n"
        f"🎁 <b>ویژه:</b>\n"
        f"• سرکوب شورش: {'✅' if domestic['riot_suppression'] else '❌'}\n\n"
        f"📊 <b>وضعیت فعلی:</b>\n"
        f"• رضایت: {utils.users[user_id].get('satisfaction', 0)}%\n"
        f"• انقلاب: {utils.users[user_id].get('revolution', 0)}%"
    )
    
    keyboard = [
        [InlineKeyboardButton('🎒 پکیج‌های ویژه من', callback_data='shop_special_inventory')],
        [InlineKeyboardButton('🔙 بازگشت به فروشگاه', callback_data='shop_menu')]
    ]
    
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

# Mapping from internal item keys to Persian display names
SHOP_ITEM_DISPLAY = {
    'credits_1000': '۱۰۰۰ اعتبار جهانی',
    'credits_5000': '۵۰۰۰ اعتبار جهانی',
    'credits_10000': '۱۰۰۰۰ اعتبار جهانی',
    # Old military packages removed - replaced with new military packages system
    # Old economic packages removed - replaced with new economic packages system
    'diplomatic_sanction': 'توافق پشت پرده',
    'diplomatic_peace': 'دوستی اجباری',
    'special_guard': 'گارد ویژه',
    'special_media': 'رسانه ملی',
}

async def handle_purchase_confirmation(query, item_key, cost):
    """Handle purchase confirmation"""
    user_id = str(query.from_user.id)
    credits = utils.users[user_id]['inventory']['credits']
    
    if credits < cost:
        await query.answer("❌ موجودی اعتبار جهانی کافی نیست.", show_alert=True)
        return
    
    # Show confirmation message
    display_name = SHOP_ITEM_DISPLAY.get(item_key, item_key)
    message = f"آیا مطمئنید که می‌خواهید {display_name} را با {cost:,} اعتبار جهانی بخرید؟"
    await query.edit_message_text(message, reply_markup=get_purchase_confirmation(item_key, cost))

async def execute_purchase(query, item_name, cost):
    """Execute the actual purchase and apply effects to game stats"""
    user_id = str(query.from_user.id)
    message = "✅ خرید با موفقیت انجام شد!"  # Default message
    
    # Check if user exists
    if user_id not in utils.users:
        await query.answer("❌ شما در بازی ثبت‌نام نکرده‌اید!", show_alert=True)
        return
    
    initialize_user_inventory(user_id)
    inventory = utils.users[user_id]['inventory']
    
    # Check if user has enough credits (only if cost > 0)
    if cost > 0 and inventory['credits'] < cost:
        await query.answer("❌ موجودی اعتبار جهانی کافی نیست!", show_alert=True)
        return
    
    # Deduct credits (only if cost > 0)
    if cost > 0:
        inventory['credits'] -= cost
    
    # Apply item effects to main game stats
    if item_name == 'credits_1000':
        inventory['credits'] += 1000
        message = "✅ 1000 اعتبار جهانی به حساب شما اضافه شد!"
    elif item_name == 'credits_5000':
        inventory['credits'] += 5000
        message = "✅ 5000 اعتبار جهانی به حساب شما اضافه شد!"
    elif item_name == 'credits_10000':
        inventory['credits'] += 10000
        message = "✅ 10000 اعتبار جهانی به حساب شما اضافه شد!"
    
    # Old military packages removed - replaced with new military packages system
    
    # Old economic packages removed - replaced with new economic packages system
    
    elif item_name == 'diplomatic_sanction':
        # Update diplomacy stats
        diplomacy = utils.users[user_id]['diplomacy']
        diplomacy['sanction_immunity'] = True
        message = "✅ توافق پشت پرده منعقد شد! شما از تحریم‌ها مصون شدید."
    
    elif item_name == 'diplomatic_peace':
        # Update diplomacy stats with random enemy country
        diplomacy = utils.users[user_id]['diplomacy']
        diplomacy['forced_peace_turns'] = 12
        # Find a random enemy country for peace
        user_country = utils.users[user_id].get('country', '')
        enemy_countries = []
        for uid, user_data in utils.users.items():
            if uid != user_id and user_data.get('activated', False):
                country = user_data.get('country', '')
                if country and country != user_country:
                    # Check if they have negative relations
                    relations = utils.country_relations.get(user_id, {}).get(uid, 0)
                    if relations < 0:
                        enemy_countries.append(country)
        
        if enemy_countries:
            import random
            diplomacy['forced_peace_country'] = random.choice(enemy_countries)
            message = f"✅ دوستی اجباری برقرار شد! صلح 12 نوبته با {diplomacy['forced_peace_country']} ایجاد شد."
        else:
            message = "✅ دوستی اجباری برقرار شد! صلح 12 نوبته با یک کشور دشمن ایجاد شد."
    
    elif item_name == 'special_guard':
        # Update domestic stats
        domestic = utils.users[user_id]['domestic']
        domestic['riot_suppression'] = True
        message = "✅ گارد ویژه استخدام شد! شورش‌ها سرکوب خواهند شد."
    
    elif item_name == 'special_media':
        # Update domestic and satisfaction stats
        domestic = utils.users[user_id]['domestic']
        economy = utils.users[user_id]['economy']
        domestic['revolution'] *= 0.5
        economy['satisfaction'] = min(100, economy['satisfaction'] * 1.5)
        # Mark media as used for revolution calculation
        if 'inventory' not in utils.users[user_id]:
            utils.users[user_id]['inventory'] = {}
        utils.users[user_id]['inventory']['media_used'] = True
        message = "✅ رسانه ملی فعال شد! انقلاب 50% کاهش و رضایت 50% افزایش یافت."
    
    # Save changes
    utils.save_users()
    
    # Show success message and return to shop
    keyboard = [
        [InlineKeyboardButton('🔙 بازگشت به فروشگاه', callback_data='shop_menu')]
    ]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== SHOP EFFECTS INTEGRATION ====================

# ==================== CALCULATION FUNCTIONS ====================

def calculate_defense(user):
    """Calculate user's defense power including shop bonuses"""
    resources = user.get('resources', {})
    base = (
        resources.get('soldiers', 0) * 1
        + resources.get('tanks', 0) * 5
        + resources.get('fighter_jets', 0) * 10
        + resources.get('bombers', 0) * 20
        + resources.get('aircraft_carriers', 0) * 50
        + resources.get('submarines', 0) * 25
        + resources.get('ballistic_missiles', 0) * 100
        + resources.get('defense_missiles', 0) * 80
    )
    # ضریب تجهیزات ویژه
    multiplier = user.get('military', {}).get('defense_power', 1.0)
    return base * multiplier

def calculate_attack_success(user):
    """Calculate user's attack success chance including shop bonuses"""
    base_chance = 0.5  # 50% default
    bonus = user.get('military', {}).get('war_success_bonus', 0.0)
    return min(1.0, base_chance + bonus)  # capped at 100%

def calculate_production(user):
    """Calculate user's resource production including shop bonuses"""
    base = user.get('economy', {}).get('base_production', 1000)  # default base production
    multiplier = user.get('economy', {}).get('resources_production', 1.0)
    special_mult = user.get('economy', {}).get('special_prod_multiplier', 1.0)
    return base * multiplier * special_mult

def calculate_satisfaction(user):
    """Calculate user's satisfaction including shop bonuses"""
    # اگر قفل رضایت فعال است
    if user.get('satisfaction_locked'):
        return 100
    base = user.get('economy', {}).get('satisfaction', 70)
    return min(100, base)

def apply_sanctions(user):
    """Check if sanctions should be applied to user"""
    if user.get('diplomacy', {}).get('sanction_immunity', False):
        return False  # تحریم بی‌اثر
    return True

def check_peace(user, target):
    """Check if user has forced peace with target"""
    if user.get('diplomacy', {}).get('forced_peace_turns', 0) > 0:
        return True  # نمی‌تونه جنگ کنه
    return False

def is_user_peace_protected(user_id: str) -> bool:
    """Return True if the given user currently has forced peace protection active."""
    if user_id not in utils.users:
        return False
    diplomacy = utils.users[user_id].get('diplomacy', {})
    return diplomacy.get('forced_peace_turns', 0) > 0

def calculate_revolution(user):
    """Calculate user's revolution risk including shop bonuses"""
    base = user.get('domestic', {}).get('revolution', 20)  # default revolution risk

    # رسانه ملی نصف می‌کنه
    if 'media_used' in user.get('inventory', {}):
        base *= 0.5

    # گارد ویژه → اگر شورش سرکوب شد انقلاب افزایش پیدا نکنه
    if user.get('domestic', {}).get('riot_suppression', False):
        pass  # یعنی افزایش انقلاب از سرکوب حذف بشه

    return base

def process_loans(user):
    """Process loan payments for user"""
    if user.get('economy', {}).get('loan_turns', 0) > 0:
        # هر دور باید قسط پرداخت کنه
        interest = user.get('economy', {}).get('loan_interest', 0.12)
        payment = (10000000000 * interest) / 24
        user['economy']['money'] -= payment
        user['economy']['loan_turns'] -= 1

# ==================== SHOP EFFECTS INTEGRATION ====================

def get_user_defense_power(user_id):
    """Get user's defense power including shop bonuses"""
    if user_id not in utils.users:
        return 1.0
    
    initialize_user_inventory(user_id)
    # اگر کاربر هم‌اکنون در نبرد دریایی است، بوف‌های جدید اعمال نشوند (به جنگ بعدی موکول شوند)
    try:
        # تشخیص مشارکت در نبرد دریایی جاری
        for aid, ad in getattr(utils, 'naval_attacks', {}).items():
            if ad.get('attacker_id') == user_id or ad.get('target_id') == user_id:
                # حین نبرد: مقدار فعلی را بدون تغییرات «همین دور» برگردان
                military = utils.users[user_id]['military']
                return military.get('defense_power', 1.0)
    except Exception:
        pass
    military = utils.users[user_id]['military']
    return military.get('defense_power', 1.0)

def get_user_war_success_bonus(user_id):
    """Get user's war success bonus including shop bonuses"""
    if user_id not in utils.users:
        return 0.0
    
    initialize_user_inventory(user_id)
    # اگر کاربر در یک نبرد دریایی جاری است، بوف‌های جدید موفقیت جنگ در همین نبرد اعمال نشود
    try:
        for aid, ad in getattr(utils, 'naval_attacks', {}).items():
            if ad.get('attacker_id') == user_id or ad.get('target_id') == user_id:
                military = utils.users[user_id]['military']
                return military.get('war_success_bonus', 0.0)
    except Exception:
        pass
    military = utils.users[user_id]['military']
    return military.get('war_success_bonus', 0.0)

def get_user_production_bonus(user_id):
    """Get user's production bonus including shop bonuses"""
    if user_id not in utils.users:
        return 1.0
    
    initialize_user_inventory(user_id)
    economy = utils.users[user_id]['economy']
    return economy.get('resources_production', 1.0)

def is_user_sanction_immune(user_id):
    """Check if user has sanction immunity from shop"""
    if user_id not in utils.users:
        return False
    
    initialize_user_inventory(user_id)
    # اگر کاربر در نبرد جاری است، مصونیت تازه خریداری‌شده در همین نبرد اعمال نشود
    try:
        for aid, ad in getattr(utils, 'naval_attacks', {}).items():
            if ad.get('attacker_id') == user_id or ad.get('target_id') == user_id:
                diplomacy = utils.users[user_id]['diplomacy']
                return diplomacy.get('sanction_immunity', False)
    except Exception:
        pass
    diplomacy = utils.users[user_id]['diplomacy']
    return diplomacy.get('sanction_immunity', False)

def get_user_forced_peace_info(user_id):
    """Get user's forced peace information from shop"""
    if user_id not in utils.users:
        return None, 0
    
    initialize_user_inventory(user_id)
    diplomacy = utils.users[user_id]['diplomacy']
    return diplomacy.get('forced_peace_country'), diplomacy.get('forced_peace_turns', 0)

def has_user_riot_suppression(user_id):
    """Check if user has riot suppression from shop"""
    if user_id not in utils.users:
        return False
    
    initialize_user_inventory(user_id)
    domestic = utils.users[user_id]['domestic']
    return domestic.get('riot_suppression', False)

def process_shop_effects_turn(user_id):
    """Process shop effects that have turn-based durations"""
    import utils
    if user_id not in utils.users:
        return
    
    initialize_user_inventory(user_id)
    military = utils.users[user_id]['military']
    economy = utils.users[user_id]['economy']
    diplomacy = utils.users[user_id]['diplomacy']
    
    # Process military effects
    if military.get('defense_buff_turns', 0) > 0:
        military['defense_buff_turns'] -= 1
        if military['defense_buff_turns'] <= 0:
            military['defense_power'] = 1.0  # Reset to normal
    
    # Process economy effects
    if economy.get('production_buff_turns', 0) > 0:
        economy['production_buff_turns'] -= 1
        if economy['production_buff_turns'] <= 0:
            economy['resources_production'] = 1.0  # Reset to normal
    
    # Process diplomacy effects
    if diplomacy.get('forced_peace_turns', 0) > 0:
        diplomacy['forced_peace_turns'] -= 1
        if diplomacy['forced_peace_turns'] <= 0:
            diplomacy['forced_peace_country'] = None

    # Cleanup expired special packages (unused >3 seasons)
    try:
        inv = utils.users[user_id].get('inventory', {})
        pkgs = inv.get('special_packages', [])
        season = utils.game_data.get('season', 1)
        kept = []
        for p in pkgs:
            if p.get('activated'):
                kept.append(p)
                continue
            purchase_season = int(p.get('purchase_season', season))
            expires_after = int(p.get('expires_after_seasons', 3))
            if (season - purchase_season) >= expires_after:
                # drop expired
                continue
            kept.append(p)
        if kept != pkgs:
            inv['special_packages'] = kept
    except Exception:
        pass
    
    # Process loan effects
    if economy.get('loan_turns', 0) > 0:
        economy['loan_turns'] -= 1
        if economy['loan_turns'] <= 0:
            # Loan expired, could add interest payment logic here
            pass
    
    utils.save_users()

async def main_message_handler(update, context):
    import utils
    user_id = str(update.effective_user.id)
    
    # Handle receipt photos
    if update.message.photo:
        # Check if user has pending payment
        if user_id in utils.pending_payments:
            payment_info = utils.pending_payments[user_id]
            if payment_info.get('status') == 'waiting_receipt':
                await handle_receipt_photo(update, context)
                return
    
    # بررسی دستورات شناسه عمومی (با /name یا بدون آن)
    message_text = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
    if message_text.startswith('/name') or (message_text.startswith('/') and len(message_text) > 1 and message_text[1:].isalnum()):
        await handle_public_profile_command(update, context)
        return
    
    # جلوگیری از تعامل کاربر بن شده
    try:
        from utils import is_user_banned
        if is_user_banned(user_id):
            return
    except Exception:
        pass
    
    # جلوگیری از تعامل کاربر مسدود شده به دلیل تأیید موقعیت
    try:
        from utils import is_user_blocked
        if is_user_blocked(user_id):
            await update.message.reply_text(
                '🚫 شما به دلیل عدم تأیید موقعیت مسدود شده‌اید.\n\n'
                'لطفاً با پشتیبانی تماس بگیرید.'
            )
            return
    except Exception:
        pass
    
    text = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
    
    # Migration username->id
    try:
        import utils
        tg_username = ''
        try:
            tg_username = update.effective_user.username or ''
        except Exception:
            tg_username = ''
        utils.migrate_user_identifier(user_id, tg_username)
        # شمارش تعامل مهمان و انقضا
        guest_expired = utils.increment_guest_interaction_and_maybe_expire(user_id)
        if guest_expired:
            await update.message.reply_text('❌ فرصت شما به پایان رسید. برای ادامه باید ثبت‌نام کنید.')
            return
    except Exception:
        pass

    # بررسی قفل ربات
    if admin_panel.is_bot_locked() and user_id != ADMIN_ID:
        await update.message.reply_text('🔒 ربات در حال حاضر قفل شده است. لطفاً بعداً تلاش کنید.')
        return
    
    # اگر ادمین در حالت وارد کردن آیدی بن باشد
    try:
        import utils
        if utils.pending_admin_ban and user_id == ADMIN_ID:
            target_id_raw = text.strip()
            utils.ban_user(target_id_raw)
            utils.pending_admin_ban = False
            await update.message.reply_text(f'⛔ کاربر {target_id_raw} با موفقیت بن شد.')
            return
        # اگر ادمین در حالت ساخت پروفایل خودکار است
        if utils.pending_admin_auto_profile and user_id == ADMIN_ID:
            target_id_raw = text.strip()
            try:
                # ساخت پروفایل مهمان
                created = admin_panel.create_guest_profile(target_id_raw)
                utils.pending_admin_auto_profile = False
                await update.message.reply_text(
                    f"✅ پروفایل کاربر {target_id_raw} به‌صورت مهمان ساخته شد.\n"
                    f"👤 نام: {created.get('player_name', '—')}\n"
                    f"🏷️ وضعیت: مهمان"
                )
            except Exception as e:
                utils.pending_admin_auto_profile = False
                await update.message.reply_text(f'❌ خطا در ساخت پروفایل: {e}')
            return
    except Exception:
        pass
    
    # ثبت‌نام: دریافت contact
    try:
        import utils
        if user_id in utils.pending_registration:
            reg = utils.pending_registration[user_id]
            if reg.get('step') == 'phone':
                # امکان لغو روند ثبت‌نام در مرحله شماره تماس
                try:
                    msg_text = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
                except Exception:
                    msg_text = ''
                cancel_words = {'لغو', 'انصراف', 'cancel', 'لغو ثبت‌نام', 'لغو پروسه'}
                if msg_text in cancel_words:
                    utils.pending_registration.pop(user_id, None)
                    await update.message.reply_text('✅ روند ثبت‌نام لغو شد.')
                    reply_markup = get_start_menu_reply(user_id)
                    await update.message.reply_text('منوی اصلی:', reply_markup=reply_markup)
                    return
                if update.message.contact and update.message.contact.phone_number:
                    phone = update.message.contact.phone_number
                    utils.users.setdefault(user_id, {})['phone'] = phone
                    utils.save_users()
                    utils.pending_registration[user_id] = {'step': 'location', 'phone': phone}
                    kb = ReplyKeyboardMarkup(
                        [[KeyboardButton('📍 ارسال موقعیت', request_location=True)], [KeyboardButton('لغو')]], 
                        resize_keyboard=True, 
                        one_time_keyboard=True
                    )
                    await update.message.reply_text('شماره تماس ثبت شد. حالا لطفاً موقعیت خود را ارسال کنید.', reply_markup=kb)
                    return
                else:
                    # فقط contact معتبر پذیرفته می‌شود
                    kb = ReplyKeyboardMarkup(
                        [[KeyboardButton('📞 ارسال شماره تماس', request_contact=True)], [KeyboardButton('لغو')]], 
                        resize_keyboard=True, 
                        one_time_keyboard=True
                    )
                    await update.message.reply_text('فقط با دکمه ارسال شماره تماس ادامه دهید.', reply_markup=kb)
                    return
            elif reg.get('step') == 'location':
                if update.message.location:
                    lat = update.message.location.latitude
                    lon = update.message.location.longitude
                    
                    # Save raw location and infer province
                    try:
                        utils.set_user_location_with_province(user_id, lat, lon)
                    except Exception:
                        pass
                    # Add location verification request
                    utils.add_location_verification(user_id, lat, lon)
                    
                    # Send location to admin for verification
                    try:
                        keyboard = [
                            [InlineKeyboardButton('✅ Approve', callback_data=f'admin_approve_location:{user_id}')],
                            [InlineKeyboardButton('❌ Reject', callback_data=f'admin_reject_location:{user_id}')]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await context.bot.send_location(
                            chat_id=int(utils.ADMIN_ID), 
                            latitude=lat, 
                            longitude=lon,
                            reply_markup=reply_markup
                        )
                        # Get user info for better identification
                        try:
                            user_info = await context.bot.get_chat(user_id)
                            username = f"@{user_info.username}" if hasattr(user_info, 'username') and user_info.username else "بدون نام کاربری"
                            first_name = getattr(user_info, 'first_name', '') or ''
                            last_name = getattr(user_info, 'last_name', '') or ''
                            full_name = f"{first_name} {last_name}".strip() if (first_name or last_name) else "نامشخص"
                        except Exception as e:
                            print(f"Error getting user info: {e}")
                            username = "نامشخص"
                            full_name = "نامشخص"
                        
                        await context.bot.send_message(
                            chat_id=int(utils.ADMIN_ID),
                            text=f"📍 <b>درخواست تأیید موقعیت</b>\n\n"
                                 f"👤 <b>شناسه کاربر:</b> {user_id}\n"
                                 f"👤 <b>نام کاربری:</b> {username}\n"
                                 f"👤 <b>نام کامل:</b> {full_name}\n"
                                 f"📞 <b>شماره تماس:</b> <code>{utils.users.get(str(user_id), {}).get('phone', 'ثبت نشده')}</code>\n\n"
                                 f"لطفاً موقعیت را بررسی و تأیید/رد کنید.",
                            parse_mode='HTML'
                        )
                    except Exception as e:
                        print(f"Error sending location to admin: {e}")
                    
                    await update.message.reply_text(
                        '📍 موقعیت شما دریافت شد و برای تأیید به ادمین ارسال شد.\n\n'
                        'لطفاً منتظر تأیید ادمین باشید. پس از تأیید، ثبت‌نام شما کامل خواهد شد.',
                        reply_markup=ReplyKeyboardRemove()
                    )
                    return
                else:
                    kb = ReplyKeyboardMarkup(
                        [[KeyboardButton('📍 ارسال موقعیت', request_location=True)]], 
                        resize_keyboard=True, 
                        one_time_keyboard=True
                    )
                    await update.message.reply_text('لطفاً موقعیت خود را با دکمه زیر ارسال کنید.', reply_markup=kb)
                    return
    except Exception as e:
        print(f"registration flow error: {e}")
    
    # بررسی دکمه پروفایل
    if text == "👤 پروفایل":
        await show_user_profile(update, context)
        return
    
    # بررسی کلمه کلیدی سازمان ملل
    if text == "منو":
        # موقتاً غیرفعال کردن پاک‌سازی خودکار
        # utils.cleanup_deleted_un_users()
        
        # Debug: نمایش وضعیت فعلی
        print(f"[DEBUG] UN_ACTIVATED_USER: {utils.UN_ACTIVATED_USER}")
        print(f"[DEBUG] Current user_id: {user_id}")
        print(f"[DEBUG] Type comparison: {type(utils.UN_ACTIVATED_USER)} vs {type(user_id)}")
        print(f"[DEBUG] Equality check: {utils.UN_ACTIVATED_USER == user_id}")
        
        if utils.UN_ACTIVATED_USER is None:
            # اولین بار - درخواست کد فعالسازی
            keyboard = [
                [InlineKeyboardButton('❌ لغو فعال‌سازی', callback_data='cancel_un_activation')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🏛️ <b>فعال‌سازی پنل سازمان ملل</b>\n\n"
                "برای فعال‌سازی پنل سازمان ملل، لطفاً کد فعال‌سازی خود را وارد کنید:\n\n"
                "💡 <b>نکته:</b> برای لغو فعال‌سازی، روی دکمه 'لغو فعال‌سازی' کلیک کنید.",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
            # ذخیره وضعیت درخواست کد
            utils.pending_un_activation = user_id
            utils.save_un_data()  # ذخیره وضعیت
            return
        elif str(utils.UN_ACTIVATED_USER) == str(user_id):
            # کاربر فعال - نمایش پنل سازمان ملل
            from united_nations import show_un_panel
            
            class FakeQuery:
                def __init__(self, message):
                    self.from_user = message.from_user
                    self.message = message
                    self.data = "un_main"
                
                async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                    await self.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            
            fake_query = FakeQuery(update.message)
            await show_un_panel(fake_query)
            return
        else:
            # کاربر غیرفعال - خطا
            await update.message.reply_text(
                "❌ <b>دسترسی غیرمجاز!</b>\n\n"
                "پنل سازمان ملل قبلاً توسط کاربر دیگری فعال شده است.",
                parse_mode='HTML'
            )
            return
    # پردازش کد فعال‌سازی سازمان ملل
    if utils.pending_un_activation == user_id:
        # بررسی کلمات کلیدی لغو
        if text.lower() in ['لغو', 'cancel', 'انصراف', 'بازگشت', 'stop', 'خروج', 'exit']:
            utils.pending_un_activation = None
            utils.save_un_data()
            await update.message.reply_text(
                "❌ <b>فعال‌سازی سازمان ملل لغو شد!</b>\n\n"
                "حالا می‌توانید از منوی اصلی استفاده کنید.",
                parse_mode='HTML'
            )
            return
        
        activation_code = text.strip()
        
        # بررسی کد فعال‌سازی از سیستم اصلی
        from admin_panel import load_activation_codes, get_activation_code_for_country
        codes = load_activation_codes()
        
        # بررسی اینکه آیا کد برای سازمان ملل هست
        if activation_code in codes and codes[activation_code]['country'] == "سازمان ملل 🇺🇳":
            print(f"[DEBUG] کد فعال‌سازی صحیح برای سازمان ملل")
            print(f"[DEBUG] قبل از تغییر - UN_ACTIVATED_USER: {utils.UN_ACTIVATED_USER}")
            print(f"[DEBUG] قبل از تغییر - pending_un_activation: {utils.pending_un_activation}")
            
            utils.UN_ACTIVATED_USER = user_id
            utils.pending_un_activation = None
            
            print(f"[DEBUG] بعد از تغییر - UN_ACTIVATED_USER: {utils.UN_ACTIVATED_USER}")
            print(f"[DEBUG] بعد از تغییر - pending_un_activation: {utils.pending_un_activation}")
            
            # ذخیره اطلاعات سازمان ملل
            utils.save_un_data()
            print(f"[DEBUG] save_un_data() فراخوانی شد")
            
            # حذف کد استفاده شده
            del codes[activation_code]
            from admin_panel import save_activation_codes
            save_activation_codes(codes)
            
            await update.message.reply_text(
                "✅ <b>پنل سازمان ملل فعال شد!</b>\n\n"
                "حالا می‌توانید با تایپ کردن 'منو' از پنل سازمان ملل استفاده کنید.",
                parse_mode='HTML'
            )
            # پیام الهام‌بخش همراه با گیف
            try:
                caption = (
                    "🌍 <b>سازمان ملل فعال شد</b>\n\n"
                    "«بنی آدم اعضای یکدیگرند که در آفرینش ز یک گوهرند»\n"
                    "از این لحظه، شما نگهبان صلح و عدالت جهانی هستید.\n"
                    "✨ مسئولیت شما: حل منازعات، صدور قطعنامه و پاسداری از انسانیت."
                )
                await update.message.reply_animation(
                    animation="https://t.me/TextEmpire_IR/192",
                    caption=caption,
                    parse_mode='HTML'
                )
            except Exception:
                pass
            return
        else:
            await update.message.reply_text(
                "❌ <b>کد فعال‌سازی اشتباه است!</b>\n\n"
                "لطفاً کد صحیح سازمان ملل را وارد کنید.",
                parse_mode='HTML'
            )
            return
    
    # ==================== مراحل متنی پیش‌نویس قطعنامه‌های سازمان ملل ====================
    # اگر کاربر در ویزارد پیش‌نویس است، ورودی متنی را به united_nations تحویل بده
    draft = utils.pending_un_resolution_draft.get(user_id) if hasattr(utils, 'pending_un_resolution_draft') else None
    if draft and isinstance(draft, dict) and draft.get('step') in ['reason', 'concern', 'necessity', 'duration', 'confirm']:
        print(f"[DEBUG] Processing UN resolution draft for user {user_id}, step: {draft.get('step')}")
        from united_nations import handle_resolution_draft_message
        await handle_resolution_draft_message(update, context)
        return

    # ورودی متن برای شکایت‌نامه سازمان ملل (ویزارد چندمرحله‌ای)
    pending_complaint = utils.pending_un_complaint.get(user_id) if hasattr(utils, 'pending_un_complaint') else None
    if pending_complaint and pending_complaint.get('step') in ['def_custom', 'short', 'details', 'remedy_other', 'attach']:
        from diplomaci import handle_un_complaint_message
        await handle_un_complaint_message(update, context)
        return
    
    # ورودی متن برای برگزاری دادگاه سازمان ملل (ویزارد چندمرحله‌ای)
    pending_court = utils.pending_un_court.get(user_id) if hasattr(utils, 'pending_un_court') else None
    if pending_court and pending_court.get('step') in ['topic', 'plaintiff', 'defendant', 'witnesses', 'time', 'location']:
        from united_nations import handle_un_court_message
        await handle_un_court_message(update, context)
        return
    
    # ورودی متن برای ویرایش اتحاد
    if user_id in utils.pending_edit_alliance:
        from diplomaci import handle_edit_alliance
        await handle_edit_alliance(update, context)
        return
    
    if user_id in utils.pending_court_edit:
        from united_nations import handle_court_edit
        await handle_court_edit(update, context)
        return

    if user_id in pending_alliance_chat:
        await handle_alliance_message(update, context)
        return
    if user_id in utils.pending_create_alliance:
        await handle_create_alliance(update, context)
        return
    if text == 'شروع بازی 🚀':
        # سازمان ملل نمی‌تونه بازی شروع کنه
        if is_un_user(user_id):
            await update.message.reply_text(
                "❌ <b>دسترسی غیرمجاز!</b>\n\n"
                "کاربران سازمان ملل نمی‌توانند بازی شروع کنند.",
                parse_mode='HTML'
            )
            return
        await show_game_menu(update.message)
        return
    elif text == 'کشورها 🌍':
        await show_countries_menu(update.message)
        return
    elif text == '👤 پروفایل':
        await show_user_profile(update, context)
        return
    elif text == 'ثبت‌نام 📱':
        # آغاز روند ثبت‌نام دستی از منو
        try:
            import utils
            utils.pending_registration[user_id] = {'step': 'phone', 'phone': None}
            kb = ReplyKeyboardMarkup(
                [[KeyboardButton('📞 ارسال شماره تماس', request_contact=True)], [KeyboardButton('لغو')]], 
                resize_keyboard=True, 
                one_time_keyboard=True
            )
            await update.message.reply_text(
                'برای ثبت‌نام، لطفاً شماره تماس خود را با دکمه زیر ارسال کنید:',
                reply_markup=kb
            )
            return
        except Exception:
            pass
    elif text == '🛒 فروشگاه':
        # Create a fake query object for the shop menu
        class FakeQuery:
            def __init__(self, message):
                self.from_user = message.from_user
                self.edit_message_text = message.reply_text
        
        fake_query = FakeQuery(update.message)
        await show_shop_menu(fake_query)
        return
    # بررسی مرحله انتخاب تعداد موشک
    elif user_id in utils.pending_military_production and utils.pending_military_production[user_id].get('step') == 'missile_count':
        print(f"[DEBUG] Processing missile count for user {user_id}")
        print(f"[DEBUG] pending_military_production: {utils.pending_military_production}")
        print(f"[DEBUG] User text: {update.message.text if hasattr(update.message, 'text') else 'No text'}")
        print(f"[DEBUG] User step: {utils.pending_military_production[user_id].get('step')}")
        print(f"[DEBUG] About to call process_missile_count_input")
        from battle import process_missile_count_input
        await process_missile_count_input(update.message, context)
        print(f"[DEBUG] process_missile_count_input completed")
        return
    elif text == 'فعالسازی کشور 🔑':
        await activate_country_prompt(update.message, user_id)
        return
    elif text == 'آموزش 📖':
        from tutorial import show_tutorial_menu
        await show_tutorial_menu(update.message)
        return
    elif text == 'پشتیبانی 🛠':
        await show_simple_section(update.message, 'برای پشتیبانی با ادمین به <a href="https://t.me/Rylotm">@Rylotm</a> پیام دهید.', parse_mode='HTML', back_to='main')
        return
    elif text == 'منوی ادمین 👑' and user_id == ADMIN_ID:
        await show_admin_menu(update.message)
        return
    # انتخاب شعار کشور
    if pending_country_slogan.get(user_id):
        await handle_activation_code(update, context)
        return
    
    # انتخاب نام کاربر
    if pending_name_selection.get(user_id):
        await handle_activation_code(update, context)
        return
    
    # فعال‌سازی کشور
    if pending_activation.get(user_id):
        await handle_activation_code(update, context)
        return
    # فروش مرحله مقدار
    if user_id in pending_sell_amount:
        await handle_sell_amount(update, context)
        return
    # فروش مرحله قیمت کل
    if user_id in pending_sell_total_price:
        await handle_sell_total_price(update, context)
        return
    if pending_statement.get(user_id):
        await handle_statement(update, context)
        return
    
    # بررسی پیام‌های چت با جی پی مورگان
    from bank import secret_event_user
    if secret_event_user and secret_event_user == user_id:
        await handle_morgan_chat(update, context)
        return
    # حمله زمینی
    if user_id in pending_ground_attack:
        # ابتدا ورودی عددی برای واحد انتخاب‌شده را پردازش کن
        try:
            handled = await process_ground_unit_amount(update.message, context)
        except Exception:
            handled = False
        if handled:
            return
        # اگر await_unit تنظیم نشده است، از قالب چندخطی قدیمی استفاده کن
        st = utils.pending_ground_attack.get(user_id)
        if st and not st.get('await_unit'):
            await process_attack_forces(update.message, context)
        return
    
    # حمله دریایی
    if user_id in pending_naval_attack:
        await process_naval_attack_forces(update.message, context)
        return
    
    # حمله هوایی
    if user_id in pending_air_attack:
        await process_air_attack_forces(update.message, context)
        return
    
    # حمله به کشتی تجاری
    if user_id in pending_sea_raid:
        from battle import handle_sea_raid_forces
        await handle_sea_raid_forces(update, context)
        return
    
    # اگر کاربر "لغو" تایپ کند، تمام حالت‌های انتظار را لغو کن
    if hasattr(update.message, 'text') and update.message.text and update.message.text.lower() in ['لغو', 'cancel', 'انصراف', 'بازگشت', 'stop', 'خروج', 'exit']:
        # لغو تمام حالت‌های انتظار
        cancelled_operations = []
        
        if user_id in pending_naval_attack:
            # بازگرداندن نیروها در صورت لغو
            try:
                data = pending_naval_attack.get(user_id, {})
                if data.get('already_deducted'):
                    forces = data.get('forces', {}) or {}
                    user_resources = utils.users[user_id].get('resources', {})
                    for key, amount in forces.items():
                        try:
                            amt = int(amount)
                            if amt > 0:
                                user_resources[key] = int(user_resources.get(key, 0)) + amt
                        except Exception:
                            pass
                    utils.save_users()
            except Exception as restore_error:
                print(f"خطا در بازگرداندن نیروها هنگام لغو: {restore_error}")
            del pending_naval_attack[user_id]
            cancelled_operations.append("حمله دریایی")
        
        if user_id in pending_air_attack:
            del pending_air_attack[user_id]
            cancelled_operations.append("حمله هوایی")
        
        if user_id in pending_ground_attack:
            del pending_ground_attack[user_id]
            cancelled_operations.append("حمله زمینی")
        
        if user_id in pending_sea_raid:
            del pending_sea_raid[user_id]
            cancelled_operations.append("حمله به کشتی تجاری")
        
        if user_id in utils.pending_military_production:
            del utils.pending_military_production[user_id]
            cancelled_operations.append("تولید تسلیحات")
        
        if user_id in pending_help_request:
            del pending_help_request[user_id]
            cancelled_operations.append("درخواست کمک")
        
        # لغو حالت‌های بانکی
        from bank import pending_transfers
        if user_id in pending_transfers:
            del pending_transfers[user_id]
            cancelled_operations.append("عملیات بانکی")
        
        # لغو حالت‌های دیپلماتیک
        if user_id in pending_statement:
            del pending_statement[user_id]
            cancelled_operations.append("اظهارنامه")
        
        # لغو حالت‌های اتحاد
        if user_id in pending_alliance_chat:
            del pending_alliance_chat[user_id]
            cancelled_operations.append("چت اتحاد")
        
        # پیام مناسب بر اساس عملیات لغو شده
        if cancelled_operations:
            operations_text = "، ".join(cancelled_operations)
            await update.message.reply_text(f"✅ عملیات لغو شد:\n{operations_text}\n\nحالا می‌توانید نیرو تولید کنید یا کارهای دیگر انجام دهید.")
        else:
            await update.message.reply_text("✅ هیچ عملیات در حال انتظاری یافت نشد!\n\nمی‌توانید نیرو تولید کنید یا کارهای دیگر انجام دهید.")
        return
    
    # ==================== ورودی خرید/فروش سهام (اولویت بالاتر) ====================
    user = utils.users.get(str(user_id), {})
    if user.get('pending_stock_purchase'):
        try:
            symbol = next(iter(user['pending_stock_purchase'].keys()))
            amount_text = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip().replace(',', '')
            amount = int(amount_text)
        except Exception:
            await update.message.reply_text('❌ مقدار نامعتبر است. یک عدد صحیح وارد کنید.')
            return
        from economy import handle_stock_purchase
        ok, msg = await handle_stock_purchase(user_id, symbol, amount)
        await update.message.reply_text(msg)
        return
    if user.get('pending_stock_sale'):
        try:
            symbol = next(iter(user['pending_stock_sale'].keys()))
            amount_text = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip().replace(',', '')
            amount = int(amount_text)
        except Exception:
            await update.message.reply_text('❌ مقدار نامعتبر است. یک عدد صحیح وارد کنید.')
            return
        from economy import handle_stock_sale
        ok, msg = await handle_stock_sale(user_id, symbol, amount)
        await update.message.reply_text(msg)
        return

    # امنیت ملی: مراحل نام/توضیح/لوگو
    try:
        handled = await handle_national_security_photo(update) if update.message and update.message.photo else False
    except Exception:
        handled = False
    if not handled:
        try:
            if update.message and (update.message.text or ''):
                if await handle_national_security_text(update):
                    return
        except Exception:
            pass
    
    # Assassination respawn: handle new name input
    try:
        if update.message and (update.message.text or ''):
            if await handle_assassination_respawn_text(update):
                return
    except Exception:
        pass
    
    # Private messaging: handle message text
    try:
        if update.message and (update.message.text or ''):
            from diplomaci import handle_private_message_text
            if await handle_private_message_text(update, context):
                return
    except Exception:
        pass

    # تولید تسلیحات نظامی / خط تولید (پس از سهام)
    if user_id in utils.pending_military_production:
        await process_military_production_amount(update.message, context)
        return
    if user_id in pending_production_line_production:
        await process_production_line_amount(update.message, context)
        return
    # درخواست کمک اتحاد
    if user_id in pending_help_request:
        await handle_help_request_amount(update, context)
        return
    
    # پردازش انتقال پول - شماره حساب
    from bank import pending_transfers
    if user_id in pending_transfers and pending_transfers[user_id]['step'] == 'account_number':
        await handle_transfer_account_number(update, context)
        return
    
    # پردازش انتقال پول - مبلغ
    if user_id in pending_transfers and pending_transfers[user_id]['step'] == 'amount':
        await handle_transfer_amount(update, context)
        return
    
    # پردازش شارژ حساب
    if user_id in pending_transfers and pending_transfers[user_id]['step'] == 'deposit_amount':
        await handle_deposit_amount(update, context)
        return
    
    # پردازش برداشت از حساب
    if user_id in pending_transfers and pending_transfers[user_id]['step'] == 'withdraw_amount':
        await handle_withdraw_amount(update, context)
        return
    
    # پردازش خرید/فروش بازار جهانی
    from economy import pending_global_trade, handle_global_market_amount
    if user_id in pending_global_trade:
        await handle_global_market_amount(update, context)
        return

    # ==================== پایان ورودی سهام ====================
    
    # سایر پیام‌ها
    await update.message.reply_text("دستور نامعتبر است یا باید از منوها استفاده کنید.")

# ویرایش تابع start برای استفاده از get_start_menu


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    # مسدودسازی: اگر کاربر بن شده باشد، هیچ کاری انجام نشود
    try:
        from utils import is_user_banned
        if is_user_banned(user_id):
            return
    except Exception:
        pass
    
    # مسدودسازی: اگر کاربر به دلیل تأیید موقعیت مسدود شده باشد (به‌جز مهمان)
    try:
        from utils import is_user_blocked
        if is_user_blocked(user_id):
            await update.message.reply_text(
                '🚫 شما به دلیل عدم تأیید موقعیت مسدود شده‌اید.\n\n'
                'لطفاً با پشتیبانی تماس بگیرید.'
            )
            return
    except Exception:
        pass
    
    # Migration: اگر کاربر با @username ذخیره شده، به آیدی عددی منتقل شود
    try:
        import utils
        tg_username = ''
        try:
            tg_username = update.effective_user.username or ''
        except Exception:
            tg_username = ''
        utils.migrate_user_identifier(user_id, tg_username)
        # شمارش تعامل مهمان و انقضا پس از 3 بار
        guest_expired = utils.increment_guest_interaction_and_maybe_expire(user_id)
        if guest_expired:
            await update.message.reply_text('❌ فرصت شما به پایان رسید. برای ادامه باید ثبت‌نام کنید.')
            return
        utils.ensure_user_profile(user_id)
    except Exception as e:
        print(f"Registration check error: {e}")
    
    # بررسی deep link برای هدایت مستقیم به بخش‌های مختلف
    if context.args:
        command = context.args[0].lower()
        if command == 'trade':
            # هدایت مستقیم به پنل تجارت
            activated = get_user_activated(user_id)
            if activated:
                # ایجاد fake query برای نمایش منوی تجارت
                class FakeQuery:
                    def __init__(self, message):
                        self.from_user = message.from_user
                        self.message = message
                        
                    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                        await self.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
                
                fake_query = FakeQuery(update.message)
                from economy import show_trade_menu
                await show_trade_menu(fake_query)
                return
            else:
                await update.message.reply_text('❌ برای دسترسی به پنل تجارت، ابتدا کشور خود را فعال‌سازی کنید!')
                return
    
    activated = get_user_activated(user_id)
    reply_markup = get_start_menu_reply(user_id)
    await update.message.reply_text('به بازی استراتژی خوش آمدید! لطفاً یک گزینه را انتخاب کنید:', reply_markup=reply_markup)

async def show_game_menu(target):
    user_id = None
    if hasattr(target, 'from_user'):
        user_id = str(target.from_user.id)
    elif hasattr(target, 'effective_user'):
        user_id = str(target.effective_user.id)
    
    # چک کردن اینکه آیا کاربر کشور فعال دارد
    user_activated = False
    if user_id:
        user_activated = utils.users.get(str(user_id), {}).get('activated', False)
    
    if not user_activated:
        # اگر کاربر کشور فعال ندارد، پیام مناسب نمایش دهید
        keyboard = [
            [InlineKeyboardButton('فعالسازی کشور 🔑', callback_data='activate_country')],
            [InlineKeyboardButton('کشورها 🌍', callback_data='countries')],
            [InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_main')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        menu_text = "برای شروع بازی ابتدا باید یک کشور فعال کنید.\n\nلطفاً یکی از گزینه‌ها را انتخاب کنید:"
        
        if hasattr(target, 'edit_message_text'):
            await target.edit_message_text(menu_text, reply_markup=reply_markup)
        else:
            await target.reply_text(menu_text, reply_markup=reply_markup)
        return
    
    # منوی کامل برای کاربران فعال (دو ستونی)
    keyboard = []
    
    # ردیف اول: وضعیت کشور و استراتژی
    row1 = [
        InlineKeyboardButton('🏛 وضعیت کشور 🏛', callback_data='country_status'),
        InlineKeyboardButton('🎯 استراتژی 🎯', callback_data='strategy')
    ]
    keyboard.append(row1)
    
    # ردیف دوم: دیپلماسی و تجارت
    row2 = [
        InlineKeyboardButton('🤝 دیپلماسی 🤝', callback_data='diplomacy'),
        InlineKeyboardButton('💰 تجارت 💰', callback_data='trade')
    ]
    keyboard.append(row2)
    
    # ردیف سوم: ساخت و ساز و وضعیت جمعیت
    row3 = [
        InlineKeyboardButton('🏗️ ساخت و ساز 🏗️', callback_data='build'),
        InlineKeyboardButton('⚖️ وضعیت جمعیت ⚖️', callback_data='population')
    ]
    keyboard.append(row3)
    
    # ردیف چهارم: فضا و فناوری
    row4 = [
        InlineKeyboardButton('🚀 فضا و سیارات 🚀', callback_data='space'),
        InlineKeyboardButton('👨‍💻 توسعه فناوری 👨‍💻', callback_data='technology')
    ]
    keyboard.append(row4)
    
    # ردیف پنجم: بازگشت (تک ستونی)
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    gold_price = game_data['prices']['gold']
    try:
        from utils import get_current_weather, get_weather_fa_title
        weather_title = get_weather_fa_title(get_current_weather())
        weather_line = f"🌤 هوا: {weather_title}"
    except Exception:
        weather_line = ""
    menu_text = f"📅 تاریخ: {game_data['game_date']} 🪙 قیمت طلا: {gold_price:,} دلار\n{weather_line}\n\nمنوی بازی:\nیکی از گزینه‌ها را انتخاب کنید:"



    if hasattr(target, 'edit_message_text'):
        await target.edit_message_text(menu_text, reply_markup=reply_markup)
    else:
        await target.reply_text(menu_text, reply_markup=reply_markup)


# گروه‌بندی کشورها بر اساس دسته
from collections import defaultdict

def get_countries_by_category():
    grouped = defaultdict(list)
    for c in countries:
        grouped[c["category"]].append(c)
    return grouped

# نمایش لیست کشورها
async def show_countries_menu(target):
    grouped = get_countries_by_category()
    text = ''
    for category in ["🎖ابرقدرت🎖", "🥇قدرت منطقه‌ای🥇", "🥈قدرت نوظهور🥈", "🥉عادی🥉"]:
        if category in grouped:
            text += f'\n<b>{category}:</b>\n'
            for c in grouped[category]:
                status = "(آزاد)" if not c["taken"] else "(گرفته شده)"
                text += f'{c["name"]} {status}\n'
    keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if hasattr(target, 'edit_message_text'):
        await target.edit_message_text(text or 'کشوری یافت نشد.', reply_markup=reply_markup, parse_mode='HTML')
    else:
        await target.reply_text(text or 'کشوری یافت نشد.', reply_markup=reply_markup, parse_mode='HTML')

# وضعیت انتظار فعال‌سازی برای هر کاربر


# افزودن دکمه بازگشت به سایر بخش‌ها
async def show_simple_section(target, text, parse_mode=None, back_to='game_menu'):
    if back_to == 'game_menu':
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_game_menu')]]
    elif back_to == 'main':
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_main')]]
    elif back_to == 'build':
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_build')]]
    else:  # default to game_menu
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_game_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if hasattr(target, 'edit_message_text'):
        await target.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    else:
        await target.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

# منوی ادمین - استفاده از فایل admin_panel
async def show_admin_menu(target):
    await admin_panel.show_admin_menu(target)

# منوی ساخت و ساز با دو گزینه
async def show_build_menu(query, user_id):
    keyboard = [
        [InlineKeyboardButton('سازه‌ها 🏭', callback_data='build_structures')],
        [InlineKeyboardButton('تولید ⚙️', callback_data='production_menu')],
        [InlineKeyboardButton('تولید تسلیحات نظامی 🛡️', callback_data='military_production')],
        [InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_game_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('منوی ساخت و ساز:\nیکی از گزینه‌ها را انتخاب کنید:', reply_markup=reply_markup)

async def activate_country_prompt(target, user_id):
    # Ensure user is registered before allowing activation
    try:
        import utils
        u = utils.users.get(str(user_id), {})
        prof = u.get('profile', {})
        if not prof.get('is_registered') and not prof.get('guest'):
            msg = '❌ برای فعال‌سازی کشور، ابتدا باید ثبت‌نام کنید. از منوی اصلی گزینه «ثبت‌نام 📱» را بزنید.'
            if hasattr(target, 'edit_message_text'):
                await target.edit_message_text(msg, parse_mode='HTML')
            else:
                await target.reply_text(msg, parse_mode='HTML')
            return
    except Exception:
        pass
    # اگر کاربر در وضعیت مستعمره و داخل مهلت استقلال است، فعال‌سازی قفل است
    try:
        u = utils.users.get(str(user_id), {})
        if u.get('conquered_by') and u.get('independence_deadline_turn'):
            current_turn = utils.game_data.get('turn', 1)
            if current_turn <= int(u['independence_deadline_turn']):
                msg = (
                    '⏳ کشور شما تحت سلطه است و در دوره انتظار استقلال قرار دارد.\n\n'
                    'پس از گذشت مهلت استقلال (۶ نوبت) و در صورت عدم آزادی، می‌توانید مجدداً فعال‌سازی انجام دهید.'
                )
                if hasattr(target, 'edit_message_text'):
                    await target.edit_message_text(msg, parse_mode='HTML')
                else:
                    await target.reply_text(msg, parse_mode='HTML')
                return
    except Exception:
        pass

    # ابتدا نوع حکومت را انتخاب کنید
    text = '🎭 <b>انتخاب نوع حکومت</b>\n\n'
    text += '🏛️ <b>لطفاً نوع حکومت کشور خود را انتخاب کنید:</b>\n\n'
    text += '💡 <b>راهنمایی:</b>\n'
    text += '▫️ هر نوع حکومت مزایا و معایب خاص خود را دارد\n'
    text += '▫️ انتخاب شما بر روی روابط دیپلماتیک تأثیر می‌گذارد\n'
    text += '▫️ برخی حکومت‌ها برای جنگ و برخی برای صلح مناسب‌تر هستند\n\n'
    text += '🎯 <b>حکومت مورد نظر خود را انتخاب کنید:</b>'
    
    keyboard = create_government_selection_keyboard()
    if hasattr(target, 'edit_message_text'):
        await target.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
    else:
        await target.reply_text(text, reply_markup=keyboard, parse_mode='HTML')

async def handle_activation_code(update, context):
    user_id = str(update.effective_user.id)
    
    # اگر کاربر در حال انتخاب شعار کشور است
    if pending_country_slogan.get(user_id):
        country_slogan = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
        if len(country_slogan) < 10:
            await update.message.reply_text('شعار کشور باید حداقل 10 کاراکتر باشد. لطفاً دوباره وارد کنید:')
            return
        
        # ذخیره شعار کشور
        utils.users[user_id]['country_slogan'] = country_slogan
        
        # پاک کردن حالت موقت
        pending_country_slogan.pop(user_id, None)
        
        # شروع انتخاب مسئولین
        pending_minister_selection[user_id] = True
        # پیشنهاد اسامی که قبلاً توسط هیچ بازیکنی انتخاب نشده‌اند
        try:
            used_global = get_used_official_names('minister')
        except Exception:
            used_global = set()
        names_suggestions = generate_name_suggestions(10, exclude_names=list(used_global))
        utils.users[user_id]['current_names_suggestions'] = names_suggestions
        keyboard = create_name_selection_keyboard(names_suggestions, 'minister')
        await update.message.reply_text(
            f'🎭 <b>{utils.users[user_id]["government_title"]} {get_country_leader_display_name(user_id)}</b>\n\n'
            f'🏛️ <b>شعار کشور شما:</b>\n'
            f'<i>"{country_slogan}"</i>\n\n'
            f'حالا لطفاً وزیر کشور خود را انتخاب کنید:',
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        return
    
    # اگر کاربر در حال انتخاب نام است
    if pending_name_selection.get(user_id):
        country_leader_name = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
        if len(country_leader_name) < 2:
            await update.message.reply_text('نام باید حداقل 2 کاراکتر باشد. لطفاً دوباره وارد کنید:')
            return
        
        gov_type = pending_government_selection.get(user_id, 'presidency')
        gov_title = GOVERNMENT_TYPES[gov_type]
        
        # ذخیره اطلاعات حکومت (هنوز فعال نشده) بدون بازنویسی کامل پروفایل کاربر
        current_user = utils.users.get(str(user_id), {})
        current_user['activated'] = False  # هنوز فعال نشده
        current_user['government_type'] = gov_type
        current_user['government_title'] = gov_title
        # Store leader name separately for country
        current_user['country_leader_name'] = country_leader_name
        
        # شناسه عمومی از نام پروفایل تولید می‌شود و در این مرحله تغییر نمی‌کند
        
        # حفظ سایر فیلدهای کاربر و تنظیم مقادیر پیش‌فرض در صورت نبود
        if 'country' not in current_user:
            current_user['country'] = None
        if 'category' not in current_user:
            current_user['category'] = None
        if 'code' not in current_user:
            current_user['code'] = None
        utils.users[user_id] = current_user
        utils.save_users()
        
        # پاک کردن حالت‌های موقت
        pending_name_selection.pop(user_id, None)
        pending_government_selection.pop(user_id, None)
        
        # شروع انتخاب شعار کشور
        pending_country_slogan[user_id] = True
        await update.message.reply_text(
            f'🎭 <b>{gov_title} {country_leader_name}</b>\n\n'
            f'🏛️ <b>حالا شعار کشور خود را انتخاب کنید:</b>\n\n'
            f'💡 <b>راهنمایی:</b>\n'
            f'▫️ شعار کشور شما در خبر خوش‌آمدگویی نمایش داده می‌شود\n'
            f'▫️ می‌توانید شعار خود را بنویسید یا از نمونه‌های زیر استفاده کنید\n\n'
            f'📝 <b>نمونه شعارها:</b>\n'
            f'▫️ "امیدوارم بتوانم کشورم را به اوج قدرت و شکوه برسانم!"\n'
            f'▫️ "برای صلح، پیشرفت و عظمت کشورم تلاش خواهم کرد!"\n'
            f'▫️ "با قدرت و حکمت، کشورم را به سوی آینده‌ای روشن هدایت می‌کنم!"\n\n'
            f'🎯 <b>شعار کشور خود را بنویسید:</b>',
            parse_mode='HTML'
        )
        return
    
    # پردازش کد فعال‌سازی
    if (user_id in pending_sell_amount) or (user_id in pending_sell_total_price):
        return
    # بررسی اینکه آیا کاربر قبلاً کشور فعالی دارد
    current_user = utils.users.get(str(user_id), {})
    if current_user.get('activated', False):
        # آزاد کردن کشور قبلی با استفاده از تابع admin_panel
        old_country_name = admin_panel.free_user_country(user_id)
        if old_country_name:
            print(f"کشور {old_country_name} برای کاربر {user_id} آزاد شد")
        
        # پاک کردن اطلاعات کشور قبلی از کاربر
        current_user.pop('country', None)
        current_user.pop('category', None)
        current_user.pop('code', None)
        utils.save_users()
    if not pending_activation.get(user_id):
        return
    
    code = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
    
    # بررسی کد فعال‌سازی با سیستم جدید
    country_data = admin_panel.get_country_by_activation_code(code)
    if country_data:
        # پیدا کردن کشور در لیست کشورها
        selected_country = None
        for c in utils.countries:
            if c['name'] == country_data['country'] and not c['taken']:
                selected_country = c
                break
    else:
        selected_country = None
    
    if selected_country:
        # به‌روزرسانی اطلاعات کاربر
        utils.users[user_id].update({
            'activated': True,  # حالا فعال شد
            'country': selected_country['name'],
            'current_country_name': selected_country['name'],
            'category': selected_country['category'],
            'code': selected_country['code']
        })
        # Mark profile has_country
        try:
            utils.users[user_id].setdefault('profile', {})['has_country'] = True
        except Exception:
            pass
        
        # مسئولین قبلاً توسط کاربر انتخاب شده‌اند
        # get_country_officials(selected_country['name'])  # این خط را حذف کردیم
        
        # اعمال تأثیرات حکومت
        utils.apply_government_effects(user_id)
        
        # ریست منابع کاربر به دیفالت فصل جدید (هیچ موجودی از فصل قبل منتقل نشود)
        try:
            # پاک کردن هرگونه منابع قبلی قبل از مقداردهی
            utils.users[user_id]['resources'] = {}
        except Exception:
            pass
        # مقداردهی اولیه منابع کاربر بر اساس دسته کشور
        utils.force_initialize_user_resources(user_id)
        
        # ذخیره کاربر با مسئولین انتخاب شده
        utils.save_users()
        selected_country['taken'] = True
        utils.save_countries()
        pending_activation.pop(user_id, None)

        # مقداردهی اولیه جمعیت کشور فعال‌شده اگر 0 است
        try:
            from jame import COUNTRY_POPULATIONS as JAM_POP, save_population_data, get_country_population
            from utils import COUNTRY_POPULATIONS as U_POP
            cname = utils.users[user_id]['country']
            if int(get_country_population(cname)) <= 0:
                # تلاش برای یافتن کلید دارای ایموجی متناظر
                target_key = None
                base = cname.strip()
                for key in list(JAM_POP.keys()):
                    if key.startswith(base + ' ') or key == base:
                        target_key = key
                        break
                if target_key:
                    # اگر هنوز 0 است، یک مقدار پیش‌فرض معقول بده
                    if int(JAM_POP.get(target_key, 0)) <= 0:
                        JAM_POP[target_key] = 330_000_000  # پیش‌فرض برای USA
                        try:
                            save_population_data()
                        except Exception:
                            pass
                    # همگام‌سازی با utils
                    try:
                        U_POP.clear()
                        U_POP.update(JAM_POP)
                    except Exception:
                        pass
        except Exception as e:
            print(f"activation population init error: {e}")
        
        gov_title = utils.users[user_id]['government_title']
        # Use country-specific leader name in gameplay UI
        player_name = get_country_leader_display_name(user_id)
        
        # تبدیل لقب به فرمت مختصر
        short_title = get_short_government_title(gov_title)
        
        await update.message.reply_text(
            f'🎉 <b>کشور شما با موفقیت فعال شد!</b>\n\n'
            f'🏛️ <b>نوع حکومت:</b> {gov_title}\n'
            f'👑 <b>رهبر:</b> {short_title} {player_name}\n'
            f'🌍 <b>کشور:</b> {selected_country["name"]}\n\n'
            f'حالا می‌توانید وارد بازی شوید!',
            parse_mode='HTML'
        )
        
        # ارسال پیام خوش‌آمدگویی در کانال اخبار
        try:
            from utils import NEWS_CHANNEL_ID
            from datetime import datetime
            
            # محاسبه تعداد کل بازیکن‌های فعال
            active_players = len([u for u in utils.users.values() if u.get('activated', False)])
            
            # پیام خوش‌آمدگویی زیبا
            welcome_news = (
                f"🎉 خبر جدید!\n\n"
                f"🏛️  در خاک و خون انقلابی جدید شکل گرفت و دولت نوپای  {selected_country['name']} به قدرت رسید !\n\n"
                f"👑 رهبر: {short_title} {player_name}\n"
                f"🏛️ نوع حکومت: {gov_title}\n"
                f"🌍 کشور: {selected_country['name']}\n\n"
                f"👥 اعضای کابینه:\n"
            )
            
            # اضافه کردن اعضای کابینه
            selected_officials = utils.users[user_id].get('selected_officials', {})
            
            if 'minister' in selected_officials:
                minister_name = selected_officials['minister']['name']
                welcome_news += f"▫️ 🏗️ وزیر کشور: {minister_name}\n"
            
            if 'general' in selected_officials:
                general_name = selected_officials['general']['name']
                welcome_news += f"▫️ ⚔️ ژنرال ارتش: {general_name}\n"
            
            if 'foreign' in selected_officials:
                foreign_name = selected_officials['foreign']['name']
                welcome_news += f"▫️ 🌍 وزیر خارجه: {foreign_name}\n"
            
            if 'finance' in selected_officials:
                finance_name = selected_officials['finance']['name']
                welcome_news += f"▫️ 💰 وزیر دارایی: {finance_name}\n"
            
            # ادامه پیام
            welcome_news += (
                f"\n🎯 به بازی خوش آمدید!\n\n"
                f"💬 شعار کشور:\n"
            )
            
            # اضافه کردن شعار کشور (اگر وجود داشته باشد)
            country_slogan = utils.users[user_id].get('country_slogan', 'امیدوارم بتوانم کشورم را به اوج قدرت و شکوه برسانم!')
            welcome_news += f"\"{country_slogan}\"\n\n"
            
            welcome_news += (
                f"📊 آمار بازی:\n"
                f"▫️ تعداد کل بازیکن‌ها: {active_players}\n"
                f"▫️ کشور شما: {active_players}مین بازیکن\n"
                f"▫️ تاریخ فعال‌سازی: {datetime.now().strftime('%Y/%m/%d %H:%M')}\n\n"
                f"🌟 نکات مهم:\n"
                f"▫️ از منوی اصلی برای شروع بازی استفاده کنید\n"
                f"▫️ منابع خود را مدیریت کنید\n"
                f"▫️ با سایر کشورها روابط برقرار کنید\n"
                f"▫️ اتحاد تشکیل دهید و جنگ کنید\n\n"
                f"🎮 موفق باشید! 🚀"
            )
            
            await context.bot.send_photo(
                chat_id=NEWS_CHANNEL_ID,
                photo="https://t.me/TextEmpire_IR/179",
                caption=welcome_news,
                parse_mode='HTML'
            )
            print(f"✅ پیام خوش‌آمدگویی برای {selected_country['name']} در کانال اخبار ارسال شد")
            
        except Exception as e:
            print(f"❌ خطا در ارسال پیام خوش‌آمدگویی به کانال اخبار: {e}")
        
        # ارسال پیام‌های خوش‌آمدگویی مسئولین
        selected_officials = utils.users[user_id].get('selected_officials', {})
        
        # پیام وزیر کشور
        if 'minister' in selected_officials:
            minister_name = selected_officials['minister']['name']
            await update.message.reply_text(
                f'👨‍💼 <b>خوش آمدید قربان!</b>\n\n'
                f'من {minister_name} وزیر کشور شما هستم و مسئول مدیریت امور داخلی و توسعه زیرساخت‌های کشور.\n'
                f'امیدوارم با همکاری شما به سطح بالای توسعه و پیشرفت دست یابیم! 🏗️',
                parse_mode='HTML'
            )
        
        # پیام ژنرال
        if 'general' in selected_officials:
            general_name = selected_officials['general']['name']
            await update.message.reply_text(
                f'🎖️ <b> درود {short_title} !</b>\n\n'
                f'من {general_name} ژنرال ارتش شما هستم و مسئول دفاع از مرزها و تقویت قدرت نظامی کشور.\n'
                f'امیدوارم با همکاری شما به سطح بالای نظامی دست یابیم! ⚔️',
                parse_mode='HTML'
            )
        
        # پیام وزیر خارجه
        if 'foreign' in selected_officials:
            foreign_name = selected_officials['foreign']['name']
            await update.message.reply_text(
                f'🌍 <b>خوش آمدید قربان!</b>\n\n'
                f'من {foreign_name} وزیر خارجه شما هستم و مسئول روابط دیپلماتیک و اتحادهای استراتژیک.\n'
                f'امیدوارم با همکاری شما به سطح بالای دیپلماتیک دست یابیم! 🤝',
                parse_mode='HTML'
            )
        
        # پیام وزیر دارایی
        if 'finance' in selected_officials:
            finance_name = selected_officials['finance']['name']
            await update.message.reply_text(
                f'💰 <b>خوش آمدید قربان!</b>\n\n'
                f'من {finance_name} وزیر دارایی شما هستم و مسئول مدیریت اقتصاد و سرمایه‌گذاری‌های کلان.\n'
                f'امیدوارم با همکاری شما به سطح بالای اقتصادی دست یابیم! 📈',
                parse_mode='HTML'
            )
    else:
        await update.message.reply_text('کد فعال‌سازی نامعتبر است یا این کشور قبلاً گرفته شده است. لطفاً دوباره تلاش کنید.')

# منوی انتخاب دسته‌بندی سازه‌ها
async def show_build_structures_menu(query):
    # دو ستونی
    keys = list(BUILDINGS.keys())
    keyboard = []
    for i in range(0, len(keys), 2):
        row = []
        for j in range(2):
            if i + j < len(keys):
                key = keys[i + j]
                section = BUILDINGS[key]
                row.append(InlineKeyboardButton(f"{section['title']}", callback_data=f"build_section_{key}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_build')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('دسته‌بندی سازه‌ها را انتخاب کنید:', reply_markup=reply_markup)

async def show_build_section(query, section_key):
    section = BUILDINGS[section_key]
    items = section['items']
    keyboard = []
    for i in range(0, len(items), 2):
        row = []
        for j in range(2):
            if i + j < len(items):
                item = items[i + j]
                row.append(InlineKeyboardButton(f"{item['name']}", callback_data=f"build_item_{item['key']}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_build')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"منابع {section['title']}:\nیکی از منابع را انتخاب کنید:", reply_markup=reply_markup)

async def show_build_item(query, item_key):
    for section_key, section in BUILDINGS.items():
        for item in section['items']:
            if item['key'] == item_key:
                user_id = str(query.from_user.id)
                user = utils.users.get(str(user_id), {})
                economy = user.get('economy', {})
                built = economy.get(section_key, [])
                is_production = item_key in PRODUCTION_RECIPES
                max_count = 1 if is_production else 5
                count = built.count(item_key)
                text = f"<b>{item['name']}</b>\nنوع سازه: {item['name']}\nقیمت ساخت: {item['price']}\nتعداد فعلی: {count}/{max_count}"
                keyboard = []
                if count < max_count:
                    keyboard.append([InlineKeyboardButton('ساخت', callback_data=f'build_confirm_{item_key}')])
                else:
                    text += '\n🚫 حداکثر تعداد این سازه را ساخته‌اید.'
                keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data=f'build_section_{section_key}')])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
                return
    await show_simple_section(query, 'سازه مورد نظر یافت نشد.', back_to='build')

# تولید
async def show_production_menu(query, user_id):
    user = utils.users.get(str(user_id), {})
    economy = user.get('economy', {})
    # فقط سازه‌هایی که کاربر ساخته
    all_built = []
    for section, items in economy.items():
        if isinstance(items, list):
            for key in items:
                all_built.append(key)
    # فقط سازه‌هایی که قابلیت تولید دارند
    built_producers = [k for k in all_built if k in PRODUCTION_RECIPES]
    if not built_producers:
        await show_simple_section(query, 'شما هیچ سازه تولیدی ندارید.', back_to='game_menu')
        return
    # دو ستونی
    keyboard = []
    names = []
    for key in built_producers:
        name = None
        for section in BUILDINGS.values():
            for item in section['items']:
                if item['key'] == key:
                    name = item['name']
        if name:
            names.append((name, key))
    for i in range(0, len(names), 2):
        row = []
        for j in range(2):
            if i + j < len(names):
                name, key = names[i + j]
                row.append(InlineKeyboardButton(name, callback_data=f'production_item_{key}'))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_build')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('منوی تولید:\nیکی از سازه‌های تولیدی خود را انتخاب کنید:', reply_markup=reply_markup)

async def show_production_item(query, user_id, item_key):
    # فقط اگر کاربر این سازه را دارد
    user = utils.users.get(str(user_id), {})
    economy = user.get('economy', {})
    found = False
    for section, items in economy.items():
        if isinstance(items, list) and item_key in items:
             found = True
    if not found:
        await show_simple_section(query, 'شما این سازه را ندارید.', back_to='game_menu')
        return
    # اطلاعات تولید
    recipe = PRODUCTION_RECIPES.get(item_key)
    if not recipe:
        await show_simple_section(query, 'فرمول تولید یافت نشد.', back_to='game_menu')
        return
    inputs = recipe['inputs']
    output = recipe['output']
    amount = recipe['amount']
    # نام‌های فارسی منابع
    resource_names = {
        'steel': 'فولاد', 'oil': 'نفت', 'electricity': 'برق', 'electronics': 'الکترونیک',
        'iron': 'آهن', 'aluminum': 'آلومینیوم', 'titanium': 'تیتانیوم', 'copper': 'مس',
        'gold': 'طلا', 'diamond': 'الماس', 'uranium_ore': 'سنگ اورانیوم', 'yellowcake': 'کیک زرد',
        'space_parts': 'قطعات فضایی', 'centrifuge': 'سانتریفیوژ', 'uranium': 'اورانیوم',
        'gas': 'گاز', 'pride_cars': 'پراید', 'benz_cars': 'بنز'
    }
    
    inputs_text = '\n'.join([f"▫️ {resource_names.get(res, res)}: {val}" for res, val in inputs.items()])
    output_name = resource_names.get(output, output)
    text = f"<b>تولید {output_name}</b>\n<b>منابع مورد نیاز:</b>\n{inputs_text}\n<b>مقدار تولید هر بار:</b> {amount} واحد {output_name}"
    keyboard = [
        [InlineKeyboardButton('تایید ✅', callback_data=f'produce_confirm_{item_key}'), InlineKeyboardButton('لغو ❌', callback_data='production_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# منوی تولید تسلیحات نظامی
async def show_military_production_menu(query, user_id):
    # نام‌های فارسی تسلیحات نظامی
    military_names = {
        'soldiers': 'سربازان 👥',
        'special_forces': 'نیروهای ویژه 🎖️',
        'tanks': 'تانک 🛡️',
        'armored_vehicles': 'نفربر ⚔️',
        'transport_planes': 'هواپیمای ترابری ✈️',
        'helicopters': 'بالگرد 🚁',
        'fighter_jets': 'جنگنده 🛩️',
        'bombers': 'بمب‌افکن 💣',
        'artillery': 'توپخانه 🎯',
        'drones': 'پهپاد 🛸',
        'air_defense': 'پدافند هوایی 🛡️',
        'coastal_artillery': 'توپخانه ساحلی 🏖️',
        'speedboats': 'قایق تندرو 🚤',
        'naval_ship': 'ناو جنگی ⚓',
        'submarines': 'زیردریایی 🚢',
        'aircraft_carriers': 'ناو هواپیمابر 🚢'
    }
    
    # ایجاد دکمه‌ها به صورت دو ستونی
    keyboard = []
    military_items = list(MILITARY_PRODUCTION_RECIPES.keys())
    
    for i in range(0, len(military_items), 2):
        row = []
        for j in range(2):
            if i + j < len(military_items):
                item_key = military_items[i + j]
                name = military_names.get(item_key, item_key)
                row.append(InlineKeyboardButton(name, callback_data=f'military_production_{item_key}'))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_build')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('🛡️ منوی تولید تسلیحات نظامی:\nیکی از تسلیحات را انتخاب کنید:', reply_markup=reply_markup)

# نمایش جزئیات تولید تسلیحات نظامی
async def show_military_production_item(query, user_id, item_key):
    recipe = MILITARY_PRODUCTION_RECIPES.get(item_key)
    if not recipe:
        await show_simple_section(query, 'فرمول تولید یافت نشد.', back_to='military_production')
        return
    
    inputs = recipe['inputs']
    output = recipe['output']
    amount = recipe['amount']
    
    # نام‌های فارسی منابع
    resource_names = {
        'steel': 'فولاد', 'oil': 'نفت', 'electricity': 'برق', 'electronics': 'الکترونیک',
        'iron': 'آهن', 'aluminum': 'آلومینیوم', 'titanium': 'تیتانیوم'
    }
    
    inputs_text = '\n'.join([f"▫️ {resource_names.get(res, res)}: {val}" for res, val in inputs.items()])
    
    # نام فارسی تسلیحات
    military_names = {
        'soldiers': 'سربازان', 'special_forces': 'نیروهای ویژه', 'tanks': 'تانک',
        'armored_vehicles': 'نفربر', 'transport_planes': 'هواپیمای ترابری',
        'helicopters': 'بالگرد', 'fighter_jets': 'جنگنده', 'bombers': 'بمب‌افکن',
        'artillery': 'توپخانه', 'drones': 'پهپاد', 'air_defense': 'پدافند هوایی',
        'coastal_artillery': 'توپخانه ساحلی', 'speedboats': 'قایق تندرو',
        'naval_ship': 'ناو جنگی', 'submarines': 'زیردریایی', 'aircraft_carriers': 'ناو هواپیمابر'
    }
    
    output_name = military_names.get(output, output)
    
    text = f"🛡️ <b>تولید {output_name}</b>\n\n<b>منابع مورد نیاز:</b>\n{inputs_text}\n\n<b>مقدار تولید هر بار:</b> {amount} واحد {output_name}"
    
    keyboard = [
        [InlineKeyboardButton('تایید ✅', callback_data=f'military_produce_confirm_{item_key}'), 
         InlineKeyboardButton('لغو ❌', callback_data='military_production')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
# درخواست تعداد تولید تسلیحات نظامی
async def ask_military_production_amount(query, user_id, item_key):
    recipe = MILITARY_PRODUCTION_RECIPES.get(item_key)
    if not recipe:
        await show_simple_section(query, 'فرمول تولید یافت نشد.', back_to='military_production')
        return
    
    # نام فارسی تسلیحات
    military_names = {
        'soldiers': 'سربازان', 'special_forces': 'نیروهای ویژه', 'tanks': 'تانک',
        'armored_vehicles': 'نفربر', 'transport_planes': 'هواپیمای ترابری',
        'helicopters': 'بالگرد', 'fighter_jets': 'جنگنده', 'bombers': 'بمب‌افکن',
        'artillery': 'توپخانه', 'drones': 'پهپاد', 'air_defense': 'پدافند هوایی',
        'coastal_artillery': 'توپخانه ساحلی', 'speedboats': 'قایق تندرو',
        'naval_ship': 'ناو جنگی', 'submarines': 'زیردریایی', 'aircraft_carriers': 'ناو هواپیمابر'
    }
    
    output_name = military_names.get(recipe['output'], recipe['output'])
    
    utils.pending_military_production[user_id] = {
        'item_key': item_key,
        'step': 'amount'
    }
    
    await query.edit_message_text(f"🛡️ چند واحد {output_name} می‌خواهید تولید کنید؟\n\nلطفاً تعداد را وارد کنید:")

# درخواست تعداد تولید خط تولید
async def ask_production_line_amount(query, user_id, item_key):
    recipe = PRODUCTION_RECIPES.get(item_key)
    if not recipe:
        await show_simple_section(query, 'فرمول تولید یافت نشد.', back_to='production_menu')
        return
    
    # نام فارسی محصولات خط تولید
    production_names = {
        'pride_cars': 'پراید', 'benz_cars': 'بنز', 'electronics': 'الکترونیک'
    }
    
    output_name = production_names.get(recipe['output'], recipe['output'])
    
    pending_production_line_production[user_id] = {
        'item_key': item_key,
        'step': 'amount'
    }
    
    await query.edit_message_text(f"🏗️ چند واحد {output_name} می‌خواهید تولید کنید؟\n\nلطفاً تعداد را وارد کنید:")

# تابع پایان فصل (ارسال نتایج و ریست)
async def finalize_season(context):
    try:
        from utils import (
            users,
            game_data as gd,
            calculate_total_wealth,
            get_positive_relations_count,
            un_peace_prize_winners,
            get_military_wins,
            count_conquests_per_attacker,
            save_game_data,
            NEWS_CHANNEL_ID
        )
        # امپراتور (بیشترین فتح)
        conquests = count_conquests_per_attacker()
        emperor_id = None
        emperor_count = -1
        for uid, cnt in conquests.items():
            if cnt > emperor_count:
                emperor_id, emperor_count = uid, cnt
        # سلطان اقتصاد (بزرگ‌ترین ثروت)
        sultan_id = None
        sultan_wealth = -1
        for uid in users.keys():
            if not users[uid].get('activated'):
                continue
            w = calculate_total_wealth(uid)
            if w > sultan_wealth:
                sultan_id, sultan_wealth = uid, w
        # دیپلمات اعظم: دارنده بیشترین روابط مثبت؛ اگر جایزه صلح دارد، بدون قید
        diplomat_id = None
        if isinstance(un_peace_prize_winners, list) and un_peace_prize_winners:
            last = un_peace_prize_winners[-1]
            country = last.get('country')
            from utils import get_country_to_user_map
            mapping = get_country_to_user_map()
            diplomat_id = mapping.get(country)
        if not diplomat_id:
            best_rel = -1
            for uid in users.keys():
                if not users[uid].get('activated'):
                    continue
                pr = get_positive_relations_count(uid)
                if pr > best_rel:
                    diplomat_id, best_rel = uid, pr
        # فرمانده آهنین: بیشترین برد نظامی
        iron_id = None
        iron_wins = -1
        for uid in users.keys():
            if not users[uid].get('activated'):
                continue
            wins = get_military_wins(uid)
            if wins > iron_wins:
                iron_id, iron_wins = uid, wins
        # محبوب ملت‌ها: بیشترین رضایت و کمترین درصد انقلاب
        popular_id = None
        best_score = None
        for uid, u in users.items():
            if not u.get('activated'):
                continue
            satisfaction = u.get('satisfaction')
            if satisfaction is None:
                satisfaction = u.get('economy', {}).get('satisfaction', 70)
            revolution = u.get('revolution')
            if revolution is None:
                revolution = u.get('domestic', {}).get('revolution', 20)
            score = (int(satisfaction), -int(revolution))
            if best_score is None or score > best_score:
                best_score = score
                popular_id = uid
        def name_of(uid):
            if not uid:
                return '—'
            u = users.get(uid, {})
            return u.get('player_name') or u.get('country') or str(uid)
        def country_of(uid):
            if not uid:
                return '—'
            return users.get(uid, {}).get('country', '—')
        def slogan_of(uid):
            if not uid:
                return '—'
            return users.get(uid, {}).get('country_slogan', '—')
        season_no = gd.get('season', 1)
        # نام پیشکسوت جهان (اکانت فعال سازمان ملل)
        try:
            from utils import UN_ACTIVATED_USER
            un_uid = str(UN_ACTIVATED_USER) if UN_ACTIVATED_USER is not None else None
        except Exception:
            un_uid = None
        def un_veteran_name():
            if un_uid and un_uid in users:
                u = users.get(un_uid, {})
                return u.get('player_name') or u.get('country') or str(un_uid)
            return '—'
        text = (
            f"🎉 فصل [{season_no}] به پایان رسید! 🎉\n\n"
            f"🏆 نتایج نهایی و برندگان:\n\n"
            f"👑 امپراتور جهان: {name_of(emperor_id)}\n"
            f"جایزه: ۵۰٪ مجموع خریدها نقد + 500اعتبار جهانی 💠 + حق رزرو کشور دلخواه\n"
            f"پرچم: {country_of(emperor_id)}\n"
            f"شعار: \"{slogan_of(emperor_id)}\"\n\n"
            f"💰 سلطان اقتصاد: {name_of(sultan_id)}\n"
            f"جایزه: 250اعتبار جهانی 💠 + حق رزرو یک کشور قدرت منطقه ای\n"
            f"پرچم: {country_of(sultan_id)}\n"
            f"شعار: \"{slogan_of(sultan_id)}\"\n\n"
            f"🤝 دیپلمات اعظم: {name_of(diplomat_id)}\n"
            f"جایزه: 100اعتبار جهانی 💠  + حق رزرو یک کشور قدرت نوظهور\n"
            f"پرچم: {country_of(diplomat_id)}\n"
            f"شعار: \"{slogan_of(diplomat_id)}\"\n\n"
            f"⚔️ فرمانده آهنین: {name_of(iron_id)}\n"
            f"جایزه: 100اعتبار جهانی 💠  + حق رزرو یک کشور قدرت منطقه ای\n"
            f"پرچم: {country_of(iron_id)}\n"
            f"شعار: \"{slogan_of(iron_id)}\"\n\n"
            f"🪙 محبوب ملت‌ها: {name_of(popular_id)}\n"
            f"جایزه: 50 اعتبار جهانی 💠  \n"
            f"پرچم: {country_of(popular_id)}\n"
            f"شعار: \"{slogan_of(popular_id)}\"\n\n"
            f"🏛️ پیشکسوت جهان: {un_veteran_name()}\n"
            f"جایزه: 250 اعتبار جهانی 💠 + حق رزرو کشور دلخواه\n"
            f"پرچم: سازمان ملل 🇺🇳\n"
            f"شعار: \"برای صلح، کرامت و برابری.\"\n\n"
            f"---\n\n"
            f"🌍 از همه شما رهبران جهانی برای شرکت در این فصل سپاسگزاریم.\n"
            f"🕊️ فصل بعدی به‌زودی آغاز خواهد شد... آماده باشید!"
        )
        try:
            from utils import SEASON_END_PHOTO_ID
            if SEASON_END_PHOTO_ID:
                msg = await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=SEASON_END_PHOTO_ID, caption=text, parse_mode='HTML')
            else:
                msg = await context.bot.send_message(chat_id=NEWS_CHANNEL_ID, text=text, parse_mode='HTML')
            try:
                await context.bot.pin_chat_message(chat_id=NEWS_CHANNEL_ID, message_id=msg.message_id, disable_notification=True)
            except Exception as pe:
                print(f"pin error: {pe}")
        except Exception as se:
            print(f"season announce error: {se}")
        
        # توزیع جوایز فصل
        try:
            from utils import end_season_rewards
            winners = {
                "emperor": emperor_id,
                "economy": sultan_id,
                "diplomat": diplomat_id,
                "commander": iron_id,
                "popular": popular_id,
                "veteran": un_uid
            }
            end_season_rewards(winners, season_no)
        except Exception as re:
            print(f"rewards distribution error: {re}")
        
        # (حذف ارسال عکس جداگانه؛ متن اصلی همراه عکس بالا ارسال شد)
        # رتبه‌بندی کلی کشورها بر اساس: (کل منابع) × (پول نقد) × (قدرت نظامی)
        # فقط کشورهایی که کشور فعال دارند در رتبه‌بندی می‌آیند
        try:
            from utils import calculate_military_power_with_tech
            rankings = []
            for uid, u in users.items():
                # فقط کاربرانی که کشور دارند در رتبه‌بندی لحاظ شوند
                country_name = u.get('country')
                if not country_name:
                    continue
                res = u.get('resources', {}) or {}
                # کل منابع (بدون پول)
                total_resources_units = 0
                for k, v in res.items():
                    if k == 'cash':
                        continue
                    if isinstance(v, (int, float)):
                        total_resources_units += max(0, int(v))
                # پول نقد + legacy
                cash_val = int(res.get('cash', 0) or 0) + int(u.get('money', 0) or 0)
                # قدرت نظامی واقعی با تکنولوژی
                try:
                    power_val = int(calculate_military_power_with_tech(uid))
                except Exception:
                    power_val = 0
                score = total_resources_units * max(1, cash_val) * max(1, power_val)
                rankings.append({
                    'uid': uid,
                    'country': country_name,
                    'resources': total_resources_units,
                    'cash': cash_val,
                    'power': power_val,
                    'score': score
                })
            rankings.sort(key=lambda x: x['score'], reverse=True)
            # ساخت پیام رتبه‌بندی (ارسال پس از پیام پایان فصل)
            rank_lines = []
            SCALE = 10**18
            for i, r in enumerate(rankings[:20], 1):
                scaled_score = r['score'] / SCALE if r['score'] else 0
                rank_lines.append(
                    f"{i}. {r['country']} — امتیاز: {scaled_score:.3f} (منابع: {r['resources']:,} | پول: {r['cash']:,} | قدرت: {r['power']:,})"
                )
            ranking_text = "📊 رتبه‌بندی نهایی کشورها (Top 20)\n\n" + "\n".join(rank_lines)
            try:
                await context.bot.send_message(chat_id=NEWS_CHANNEL_ID, text=ranking_text)
            except Exception as re:
                print(f"send ranking error: {re}")
        except Exception as e:
            print(f"ranking compute error: {e}")

        # پاکسازی لاگ‌ها و محدودیت‌های خرید پکیج‌های فصل قبل (منابع/اقتصادی/نظامی) و اثرات ویژه
        try:
            from utils import (
                economic_package_purchases,
                economic_package_cooldowns,
                economic_package_approvals,
                resource_package_purchases,
                resource_package_cooldowns,
                resource_package_approvals,
                military_package_purchases,
                military_package_cooldowns,
                military_package_approvals,
                save_users
            )
            economic_package_purchases.clear()
            economic_package_cooldowns.clear()
            economic_package_approvals.clear()
            resource_package_purchases.clear()
            resource_package_cooldowns.clear()
            resource_package_approvals.clear()
            # نظامی
            try:
                military_package_purchases.clear()
                military_package_cooldowns.clear()
                military_package_approvals.clear()
            except Exception:
                pass

            # ریست اثرات پکیج‌های ویژه و موقتی برای همه کاربران
            try:
                for _uid, _u in users.items():
                    # نظامی
                    try:
                        _u.setdefault('military', {})
                        _u['military']['defense_power'] = 1.0
                        _u['military']['defense_buff_turns'] = 0
                    except Exception:
                        pass
                    # اقتصاد
                    try:
                        _u.setdefault('economy', {})
                        _u['economy']['production_buff_turns'] = 0
                        _u['economy']['resources_production'] = 1.0
                        # اثر ویژه تکنولوژی تولید
                        if 'special_prod_multiplier' in _u['economy']:
                            _u['economy']['special_prod_multiplier'] = 1.0
                        # ریست ساختمان‌ها (معادن، مزارع، کارخانه‌ها، نیروگاه‌ها)
                        _u['economy']['mines'] = []
                        _u['economy']['farms'] = []
                        _u['economy']['factories'] = []
                        _u['economy']['power_plants'] = []
                    except Exception:
                        pass
                    # رضایت قفل‌شده
                    try:
                        if _u.get('satisfaction_locked'):
                            _u['satisfaction_locked'] = False
                    except Exception:
                        pass
                    # دیپلماسی
                    try:
                        _u.setdefault('diplomacy', {})
                        _u['diplomacy']['forced_peace_turns'] = 0
                        _u['diplomacy']['forced_peace_country'] = None
                        _u['diplomacy']['robin_hood_growth_bonus'] = 0.0
                        if 'robin_hood_until_season' in _u['diplomacy']:
                            del _u['diplomacy']['robin_hood_until_season']
                    except Exception:
                        pass
                    # پاکسازی پکیج‌های ویژه که فعال شده‌اند (اثرشان به فصل بعد حمل نمی‌شود)
                    try:
                        inv = _u.get('inventory', {})
                        pkgs = inv.get('special_packages', []) or []
                        if pkgs:
                            inv['special_packages'] = [p for p in pkgs if not p.get('activated')]
                    except Exception:
                        pass
            except Exception as _e:
                print(f"special effects reset error: {_e}")
            save_users()
        except Exception as e:
            print(f"season package cleanup error: {e}")

        # غیرفعال کردن تمام کشورها و آزاد کردن کشورها پس از پایان فصل
        try:
            from utils import save_users, save_countries, countries
            # آزاد کردن کشورها در لیست countries
            for c in countries:
                if isinstance(c, dict):
                    c['taken'] = False
            # غیرفعال کردن کاربران
            for uid in list(users.keys()):
                users[uid]['activated'] = False
                try:
                    users[uid].setdefault('profile', {})['has_country'] = False
                    # پاک کردن نام کشورهای باقی‌مانده از فصل قبل
                    if 'country' in users[uid]:
                        users[uid]['country'] = ''
                    if 'current_country_name' in users[uid]:
                        users[uid]['current_country_name'] = ''
                except Exception:
                    pass
            save_users()
            save_countries()
        except Exception as de:
            print(f"deactivate/free countries error: {de}")
        # ریست فصل
        gd['turn'] = 0
        gd['season'] = int(gd.get('season', 1)) + 1
        save_game_data()
        
        # اجرای ریست کامل فصل
        season_reset()
        
        # ارسال پیام شروع فصل جدید
        try:
            new_season_no = gd.get('season', 1)
            new_season_text = (
                f"🎉 <b>فصل جدید شروع شد!</b> 🎉\n\n"
                f"🌍 <b>فصل {new_season_no}</b> آغاز شد!\n\n"
                f"📋 <b>وضعیت جدید:</b>\n"
                f"▫️ تمام کشورها آزاد شدند\n"
                f"▫️ منابع و نیروها ریست شدند\n"
                f"▫️ روابط دیپلماتیک پاک شدند\n"
                f"▫️ جنگ‌ها و اتحادها پایان یافتند\n\n"
                f"👥 <b>برای کاربران:</b>\n"
                f"▫️ اطلاعات اکانت شما حفظ شده است\n"
                f"▫️ می‌توانید دوباره کشور انتخاب کنید\n"
                f"▫️ فصل جدید آماده شروع است!\n\n"
                f"🚀 <b>به فصل جدید خوش آمدید!</b>"
            )
            
            from utils import NEWS_CHANNEL_ID
            await context.bot.send_message(
                chat_id=NEWS_CHANNEL_ID,
                text=new_season_text,
                parse_mode='HTML'
            )
            print(f"✅ پیام شروع فصل جدید {new_season_no} ارسال شد")
        except Exception as e:
            print(f"❌ خطا در ارسال پیام شروع فصل جدید: {e}")
    except Exception as e:
        print(f"finalize_season error: {e}")

# تابع پیش‌برد دور بازی
async def advance_game_turn(context):
    global game_data
    from debug_utils import debug_print, debug_error, debug_success, debug_function_entry, debug_function_exit
    
    debug_function_entry("advance_game_turn", context_type=type(context))
    
    # دیباگ: چک کردن نوع utils.users
    debug_print("advance_game_turn", "CHECK_USERS", f"نوع utils.users = {type(utils.users)}")
    if not isinstance(utils.users, dict):
        debug_error("advance_game_turn", "USERS_TYPE_ERROR", f"utils.users باید dict باشد، اما {type(utils.users)} است!", utils.users)
        return "خطا: utils.users باید dict باشد!"
    
    # لودینگ قبل از شروع محاسبات دور برای تمام کاربران فعال + ادمین/کانال
    debug_print("advance_game_turn", "LOADING_START", "شروع لودینگ برای کاربران")
    try:
        from bot import show_loading_animation
        from utils import NEWS_CHANNEL_ID, ADMIN_ID
        tasks = []
        # کاربران فعال
        debug_print("advance_game_turn", "BEFORE_USER_LOOP", f"نوع utils.users = {type(utils.users)}, تعداد کاربران = {len(utils.users)}")
        for uid, u in utils.users.items():
            if u.get('activated'):
                try:
                    debug_print("advance_game_turn", "ADD_LOADING_TASK", f"اضافه کردن لودینگ برای کاربر {uid}")
                    tasks.append(show_loading_animation(chat_id=int(uid), context=context, duration_seconds=3))
                except Exception as e:
                    debug_error("advance_game_turn", "LOADING_TASK_ERROR", f"خطا در اضافه کردن لودینگ برای کاربر {uid}", str(e))
                    continue
        # ادمین
        try:
            debug_print("advance_game_turn", "ADD_ADMIN_LOADING", f"اضافه کردن لودینگ برای ادمین {ADMIN_ID}")
            tasks.append(show_loading_animation(chat_id=int(ADMIN_ID), context=context, duration_seconds=3))
        except Exception as e:
            debug_error("advance_game_turn", "ADMIN_LOADING_ERROR", f"خطا در اضافه کردن لودینگ برای ادمین", str(e))
        # کانال اخبار
        try:
            debug_print("advance_game_turn", "ADD_NEWS_LOADING", f"اضافه کردن لودینگ برای کانال اخبار {NEWS_CHANNEL_ID}")
            tasks.append(show_loading_animation(chat_id=NEWS_CHANNEL_ID, context=context, duration_seconds=3))
        except Exception as e:
            debug_error("advance_game_turn", "NEWS_LOADING_ERROR", f"خطا در اضافه کردن لودینگ برای کانال اخبار", str(e))
        if tasks:
            debug_print("advance_game_turn", "EXECUTE_LOADING", f"اجرای {len(tasks)} لودینگ")
            await asyncio.gather(*tasks, return_exceptions=True)
            debug_success("advance_game_turn", "LOADING_COMPLETE", "لودینگ تکمیل شد")
    except Exception as e:
        debug_error("advance_game_turn", "LOADING_ERROR", f"خطای کلی در لودینگ", str(e))
    # پیش‌برد دور
    debug_print("advance_game_turn", "TURN_UPDATE", f"دور از {game_data['turn']} به {game_data['turn'] + 1}")
    game_data['turn'] += 1
    game_data['last_turn_time'] = str(datetime.now())
    
    # پیش‌برد تاریخ بازی (1 ماه)
    debug_print("advance_game_turn", "DATE_UPDATE", f"تاریخ فعلی: {game_data['game_date']}")
    current_date = datetime.strptime(game_data['game_date'], '%d/%m/%Y')
    if current_date.month == 12:
        new_date = current_date.replace(year=current_date.year + 1, month=1)
    else:
        new_date = current_date.replace(month=current_date.month + 1)
    game_data['game_date'] = new_date.strftime('%d/%m/%Y')
    debug_success("advance_game_turn", "DATE_UPDATED", f"تاریخ جدید: {game_data['game_date']}")
    
    # به‌روزرسانی قیمت‌ها
    update_prices()
    
    # به‌روزرسانی بازار سهام بین‌المللی
    from economy import update_stock_prices_per_turn
    update_stock_prices_per_turn()
    
    # انتخاب تصادفی آب‌وهوا و اعلام در کانال
    try:
        import random
        from utils import WEATHER_FILE_IDS, format_weather_effects_text
        from utils import NEWS_CHANNEL_ID
        weather_choice = random.choice(['sunny', 'normal', 'rainy', 'snowy'])
        game_data['weather'] = weather_choice
        caption = format_weather_effects_text(weather_choice)
        media_ref = WEATHER_FILE_IDS.get(weather_choice)
        try:
            if media_ref:
                # ابتدا تلاش برای ارسال به عنوان انیمیشن (GIF)
                try:
                    await context.bot.send_animation(chat_id=NEWS_CHANNEL_ID, animation=media_ref, caption=caption)
                except Exception:
                    # تلاش دوم: ارسال به عنوان عکس
                    try:
                        await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=media_ref, caption=caption)
                    except Exception:
                        # در صورت شکست، فقط متن را ارسال کن
                        await context.bot.send_message(chat_id=NEWS_CHANNEL_ID, text=caption)
            else:
                await context.bot.send_message(chat_id=NEWS_CHANNEL_ID, text=caption)
        except Exception:
            # لاگ سبک و ادامه فرآیند دور
            print("[weather] ارسال پیام کانال ناموفق بود.")
    except Exception as e:
        print(f"[weather] خطای انتخاب/اعلام آب‌وهوا: {e}")
    # تولید خودکار معادن و کشاورزی برای هر کاربر (بهبود یافته)
    # تولید متعادل بر اساس قیمت و استفاده
    # محاسبه: تولید = (قیمت سازه / قیمت واحد منبع) / ضریب استفاده
    MINE_PRODUCTION = {
        'iron_mine': ('iron', 75),        # قیمت پایین (200K)، استفاده زیاد → تولید بالا
        'uranium_ore_mine': ('uranium_ore', 20),  # قیمت متوسط (150K)، استفاده متوسط → تولید متوسط
        'copper_mine': ('copper', 50),    # قیمت متوسط (400K)، استفاده متوسط → تولید متوسط
        'gold_mine': ('gold', 3),         # قیمت بالا (5M)، استفاده کم → تولید کم
        'diamond_mine': ('diamond', 1),   # قیمت خیلی بالا (12M)، استفاده خیلی کم → تولید خیلی کم
        'aluminum_mine': ('aluminum', 30), # قیمت بالا (1M)، استفاده متوسط → تولید متوسط
        'titanium_mine': ('titanium', 6), # قیمت بالا (2M)، استفاده در تسلیحات پیشرفته → تولید کم
    }
    FARM_PRODUCTION = {
        'wheat_farm': ('wheat', 25),      # قیمت پایین (100K)، استفاده متوسط → تولید متوسط
        'rice_farm': ('rice', 25),        # قیمت پایین (80K)، استفاده متوسط → تولید متوسط
        'fruit_farm': ('fruits', 20),     # قیمت پایین (60K)، استفاده متوسط → تولید متوسط
    }
    # تولید خودکار معادن و کشاورزی
    debug_print("advance_game_turn", "PRODUCTION_START", "شروع تولید خودکار")
    debug_print("advance_game_turn", "BEFORE_PRODUCTION_LOOP", f"نوع utils.users = {type(utils.users)}, تعداد کاربران = {len(utils.users)}")
    for user_id, user in utils.users.items():
        debug_print("advance_game_turn", "PROCESSING_USER", f"پردازش کاربر {user_id}")
        resources = user.get('resources', {})
        economy = user.get('economy', {})
        # Immigrants dynamic effects per turn
        try:
            immigrants = int(user.get('immigrants', 0))
        except Exception as e:
            debug_error("advance_game_turn", "IMMIGRANTS_ERROR", f"خطا در پردازش مهاجران برای کاربر {user_id}", str(e))
            immigrants = 0
        imm_units = immigrants // 1_000_000
        # production/farm bonus: apply as extra output multiplier to both mines/farms below
        immigrants_prod_multiplier = 1 + (imm_units * 5) / 100.0 if imm_units > 0 else 1.0
        debug_print("advance_game_turn", "IMMIGRANTS_MULTIPLIER", f"کاربر {user_id}: مهاجران = {immigrants}, ضریب = {immigrants_prod_multiplier}")
        # اعمال تأثیرات حکومت بر تولید
        try:
            production_bonus = utils.calculate_government_production_bonus(user_id)
            production_multiplier = 1 + (production_bonus / 100)  # تبدیل درصد به ضریب
            debug_print("advance_game_turn", "PRODUCTION_MULTIPLIER", f"کاربر {user_id}: بونوس حکومت = {production_bonus}%, ضریب = {production_multiplier}")
        except Exception as e:
            debug_error("advance_game_turn", "PRODUCTION_BONUS_ERROR", f"خطا در محاسبه بونوس تولید برای کاربر {user_id}", str(e))
            production_multiplier = 1.0
        
        # معادن
        debug_print("advance_game_turn", "PROCESSING_MINES", f"کاربر {user_id}: پردازش {len(economy.get('mines', []))} معدن")
        for mine in economy.get('mines', []):
            if mine in MINE_PRODUCTION:
                res, amount = MINE_PRODUCTION[mine]
                # اعمال بونوس فناوری تولید معدن
                try:
                    tech_amount = calculate_production_with_tech(user_id, mine, amount)
                    # اعمال بونوس تولید حکومت
                    special_mult = float(utils.users[user_id].get('economy', {}).get('special_prod_multiplier', 1.0))
                    adjusted_amount = int(tech_amount * production_multiplier * immigrants_prod_multiplier * special_mult)
                    resources[res] = resources.get(res, 0) + adjusted_amount
                    debug_print("advance_game_turn", "MINE_PRODUCTION", f"کاربر {user_id}: {mine} -> {res} +{adjusted_amount}")
                except Exception as e:
                    debug_error("advance_game_turn", "MINE_PRODUCTION_ERROR", f"خطا در تولید معدن {mine} برای کاربر {user_id}", str(e))
        
        # کشاورزی
        debug_print("advance_game_turn", "PROCESSING_FARMS", f"کاربر {user_id}: پردازش {len(economy.get('farms', []))} مزرعه")
        for farm in economy.get('farms', []):
            if farm in FARM_PRODUCTION:
                res, amount = FARM_PRODUCTION[farm]
                # اعمال بونوس فناوری تولید مزرعه
                try:
                    tech_amount = calculate_production_with_tech(user_id, farm, amount)
                    # اعمال بونوس تولید حکومت
                    special_mult = float(utils.users[user_id].get('economy', {}).get('special_prod_multiplier', 1.0))
                    adjusted_amount = int(tech_amount * production_multiplier * immigrants_prod_multiplier * special_mult)
                    resources[res] = resources.get(res, 0) + adjusted_amount
                    debug_print("advance_game_turn", "FARM_PRODUCTION", f"کاربر {user_id}: {farm} -> {res} +{adjusted_amount}")
                except Exception as e:
                    debug_error("advance_game_turn", "FARM_PRODUCTION_ERROR", f"خطا در تولید مزرعه {farm} برای کاربر {user_id}", str(e))
        # انرژی (تولید متعادل بر اساس قیمت و استفاده)
        debug_print("advance_game_turn", "PROCESSING_ENERGY", f"کاربر {user_id}: پردازش {len(economy.get('energy', []))} نیروگاه")
        for plant in economy.get('energy', []):
            try:
                if plant in AUTO_PRODUCING_RESOURCES:
                    res, base_amount, _, _, _ = AUTO_PRODUCING_RESOURCES[plant]
                    # اعمال بونوس فناوری تولید انرژی
                    tech_amount = calculate_production_with_tech(user_id, plant, base_amount)
                    # اعمال بونوس تولید حکومت
                    special_mult = float(utils.users[user_id].get('economy', {}).get('special_prod_multiplier', 1.0))
                    adjusted_amount = int(tech_amount * production_multiplier * immigrants_prod_multiplier * special_mult)
                    resources[res] = resources.get(res, 0) + adjusted_amount
                    debug_print("advance_game_turn", "ENERGY_PRODUCTION", f"کاربر {user_id}: {plant} -> {res} +{adjusted_amount}")
            except Exception as e:
                debug_error("advance_game_turn", "ENERGY_PRODUCTION_ERROR", f"خطا در تولید انرژی {plant} برای کاربر {user_id}", str(e))
        
        # خط تولید (تولید متعادل بر اساس قیمت و استفاده)
        debug_print("advance_game_turn", "PROCESSING_PRODUCTION_LINES", f"کاربر {user_id}: پردازش {len(economy.get('production_lines', []))} خط تولید")
        for production_line in economy.get('production_lines', []):
            try:
                if production_line in AUTO_PRODUCING_RESOURCES:
                    res, base_amount, _, _, _ = AUTO_PRODUCING_RESOURCES[production_line]
                    # اعمال بونوس فناوری تولید خط تولید
                    tech_amount = calculate_production_with_tech(user_id, production_line, base_amount)
                    # اعمال بونوس تولید حکومت
                    special_mult = float(utils.users[user_id].get('economy', {}).get('special_prod_multiplier', 1.0))
                    adjusted_amount = int(tech_amount * production_multiplier * immigrants_prod_multiplier * special_mult)
                    resources[res] = resources.get(res, 0) + adjusted_amount
                    debug_print("advance_game_turn", "PRODUCTION_LINE", f"کاربر {user_id}: {production_line} -> {res} +{adjusted_amount}")
            except Exception as e:
                debug_error("advance_game_turn", "PRODUCTION_LINE_ERROR", f"خطا در خط تولید {production_line} برای کاربر {user_id}", str(e))
    
    # بررسی وام‌های بانک
    debug_print("advance_game_turn", "LOAN_PAYMENTS", "شروع بررسی وام‌های بانک")
    try:
        await process_loan_payments(game_data['turn'])
        debug_success("advance_game_turn", "LOAN_PAYMENTS_COMPLETE", "بررسی وام‌های بانک تکمیل شد")
    except Exception as e:
        debug_error("advance_game_turn", "LOAN_PAYMENTS_ERROR", f"خطا در بررسی وام‌های بانک", str(e))
    
    # بررسی respawn های ترور
    debug_print("advance_game_turn", "ASSASSINATION_RESPAWN", "شروع بررسی respawn های ترور")
    try:
        await check_assassination_respawns()
        debug_success("advance_game_turn", "ASSASSINATION_RESPAWN_COMPLETE", "بررسی respawn های ترور تکمیل شد")
    except Exception as e:
        debug_error("advance_game_turn", "ASSASSINATION_RESPAWN_ERROR", f"خطا در بررسی respawn های ترور", str(e))
    
    # پردازش اثرات شنود و ضد شنود
    debug_print("advance_game_turn", "ESPIONAGE_EFFECTS", "شروع پردازش اثرات شنود و ضد شنود")
    try:
        await process_espionage_effects()
        debug_success("advance_game_turn", "ESPIONAGE_EFFECTS_COMPLETE", "پردازش اثرات شنود و ضد شنود تکمیل شد")
    except Exception as e:
        debug_error("advance_game_turn", "ESPIONAGE_EFFECTS_ERROR", f"خطا در پردازش اثرات شنود و ضد شنود", str(e))
    
    # پاک‌سازی آگهی‌های حذف‌شده پس از هر دور
    debug_print("advance_game_turn", "CLEANUP_ADS", "شروع پاک‌سازی آگهی‌های حذف‌شده")
    global player_sell_ads
    player_sell_ads = [ad for ad in player_sell_ads if ad.get('status') != 'deleted']
    try:
        save_player_sell_ads()
    except Exception:
        pass
    debug_success("advance_game_turn", "CLEANUP_ADS_COMPLETE", f"پاک‌سازی آگهی‌ها تکمیل شد، {len(player_sell_ads)} آگهی باقی ماند")
    
    # ریست درخواست‌های بهبود روابط هر دور
    debug_print("advance_game_turn", "RESET_RELATIONS", "ریست درخواست‌های بهبود روابط")
    global relation_improvement_requests
    relation_improvement_requests = {}
    debug_success("advance_game_turn", "RESET_RELATIONS_COMPLETE", "ریست درخواست‌های بهبود روابط تکمیل شد")
    
    # اضافه کردن موشک‌ها برای همه کاربران در هر دور
    debug_print("advance_game_turn", "ADD_MISSILES", f"شروع اضافه کردن موشک‌ها برای {len(utils.users)} کاربر")
    for user_id in utils.users:
        try:
            add_missiles_per_turn(user_id)
            debug_print("advance_game_turn", "MISSILES_ADDED", f"موشک‌ها برای کاربر {user_id} اضافه شدند")
        except Exception as e:
            debug_error("advance_game_turn", "MISSILES_ERROR", f"خطا در اضافه کردن موشک‌ها برای کاربر {user_id}", str(e))
        
        # اعمال تأثیرات حکومت بر نوآوری (افزایش فناوری)
        try:
            innovation_bonus = utils.calculate_government_innovation_bonus(user_id)
            if innovation_bonus > 0:
                debug_print("advance_game_turn", "INNOVATION_BONUS", f"کاربر {user_id}: بونوس نوآوری = {innovation_bonus}%")
                # شانس افزایش خودکار فناوری بر اساس بونوس نوآوری
                innovation_chance = innovation_bonus / 100  # هر 1% بونوس = 1% شانس
                if random.random() < innovation_chance:
                    debug_print("advance_game_turn", "INNOVATION_SUCCESS", f"کاربر {user_id}: شانس نوآوری موفق شد")
                    # انتخاب تصادفی یک فناوری برای افزایش
                    from utils import military_technologies
                    user_techs = military_technologies.get(str(user_id), {})
                    if user_techs:
                        tech_keys = list(user_techs.keys())
                        random_tech = random.choice(tech_keys)
                        current_level = user_techs[random_tech]
                        if current_level < 10:  # حداکثر لول 10
                            user_techs[random_tech] = current_level + 1
                            utils.save_military_technologies()
                        
                        # ارسال پیام به کاربر
                        try:
                            tech_names = {
                                'soldiers': 'سربازان',
                                'special_forces': 'نیروهای ویژه',
                                'tanks': 'تانک‌ها',
                                'armored_vehicles': 'خودروهای زرهی',
                                'transport_planes': 'هواپیماهای ترابری',
                                'helicopters': 'هلیکوپترها',
                                'fighter_jets': 'جت‌های جنگنده',
                                'bombers': 'بمب‌افکن‌ها',
                                'artillery': 'توپخانه',
                                'drones': 'پهپادها',
                                'air_defense': 'پدافند هوایی',
                                'coastal_artillery': 'توپخانه ساحلی',
                                'speedboats': 'قایق‌های تندرو',
                                'naval_ship': 'کشتی‌های جنگی',
                                'submarines': 'زیردریایی‌ها',
                                'aircraft_carriers': 'ناوهای هواپیمابر',
                                'war_robots': 'ربات‌های جنگی',
                                'ballistic_missiles': 'موشک‌های بالستیک',
                                'defense_missiles': 'موشک‌های دفاعی'
                            }
                            
                            tech_name = tech_names.get(random_tech, random_tech)
                            message = f"🔬 <b>پیشرفت فناوری!</b>\n\n"
                            message += f"🎯 فناوری {tech_name} شما به لول {current_level + 1} ارتقا یافت!\n\n"
                            message += f"💡 این پیشرفت به دلیل بونوس نوآوری حکومت شما ({innovation_bonus}%) رخ داده است."
                            
                            await context.bot.send_message(
                                chat_id=int(user_id),
                                text=message,
                                parse_mode='HTML'
                            )
                        except Exception as e:
                            debug_error("advance_game_turn", "TECH_MESSAGE_ERROR", f"خطا در ارسال پیام پیشرفت فناوری برای کاربر {user_id}", str(e))
                    else:
                        debug_print("advance_game_turn", "NO_TECHS", f"کاربر {user_id}: هیچ فناوری‌ای برای افزایش وجود ندارد")
        except Exception as e:
            debug_error("advance_game_turn", "INNOVATION_ERROR", f"خطا در پردازش نوآوری برای کاربر {user_id}", str(e))

    # ادغام مهاجران در جمعیت بعد از 8 دور ماندگاری
    try:
        current_turn = game_data.get('turn', 1)
        from jame import COUNTRY_POPULATIONS, get_country_population, save_population_data
        for uid, u in utils.users.items():
            try:
                immigrants = int(u.get('immigrants', 0) or 0)
            except Exception:
                immigrants = 0
            if immigrants > 0:
                u['immigrants_stay_turns'] = int(u.get('immigrants_stay_turns', 0) or 0) + 1
                if u['immigrants_stay_turns'] >= 8:
                    country = u.get('country', '')
                    if country:
                        try:
                            base_pop = int(get_country_population(country))
                            COUNTRY_POPULATIONS[country] = base_pop + immigrants
                            save_population_data()
                        except Exception as e:
                            print(f"assimilation pop update error: {e}")
                    # reset immigrants after assimilation
                    u['immigrants'] = 0
                    u['immigrants_stay_turns'] = 0
            else:
                if u.get('immigrants_stay_turns'):
                    u['immigrants_stay_turns'] = 0
        utils.save_users()
    except Exception as e:
        print(f"immigrants assimilation error: {e}")
    
    # ارسال پیام ماه جدید به همه کاربران و کانال (فقط یک بار)
    # بررسی مهلت استقلال مستعمرات: اگر 6 دور گذشت و استقلال داده نشد، کشورِ فتح‌شده غیرفعال باقی می‌ماند
    try:
        current_turn = game_data.get('turn', 1)
        for uid, u in utils.users.items():
            try:
                if u.get('conquered_by') and u.get('independence_deadline_turn'):
                    if current_turn >= int(u.get('independence_deadline_turn')):
                        # اطمینان از غیرفعالی کامل
                        u['activated'] = False
            except Exception:
                continue
        utils.save_users()
    except Exception as e:
        print(f"independence deadline check error: {e}")
    global last_month_greeting_date
    if not hasattr(globals(), 'last_month_greeting_date'):
        last_month_greeting_date = None
    
    current_date = game_data['game_date']
    if last_month_greeting_date != current_date:
        try:
            print(f"🔄 در حال ارسال پیام ماه جدید برای تاریخ: {current_date}")
            await send_new_month_greetings(context.bot, current_date)
            print(f"✅ پیام ماه جدید با موفقیت ارسال شد")
            last_month_greeting_date = current_date
        except Exception as e:
            print(f"❌ خطا در ارسال پیام ماه جدید: {e}")
    else:
        print(f"⚠️ پیام ماه جدید برای تاریخ {current_date} قبلاً ارسال شده است")
    
    # اعمال تأثیرات حکومت بر ثبات و شورش
    
    # اعمال تأثیرات حکومت بر ثبات و شورش
    for user_id in utils.users:
        # بروزرسانی رضایت مردم (با اثر مهاجران در utils)
        utils.update_satisfaction(user_id)
        
        # پردازش اثرات فروشگاه
        process_shop_effects_turn(user_id)
        # کاهش مدت بونوس رشد ناشی از اخراج مهاجران
        try:
            buffs = utils.users[user_id].get('temporary_buffs', {})
            if buffs.get('growth_buff_turns', 0) > 0:
                buffs['growth_buff_turns'] -= 1
                if buffs['growth_buff_turns'] <= 0:
                    # پاکسازی نرخ افزوده
                    buffs['growth_buff_rate'] = 0.0
                utils.users[user_id]['temporary_buffs'] = buffs
        except Exception:
            pass
        
        rebellion_risk = utils.get_government_rebellion_risk(user_id)
        stability_bonus = utils.calculate_government_stability_bonus(user_id)
        
        # محاسبه شانس شورش
        base_rebellion_chance = rebellion_risk / 100  # هر 1% ریسک = 1% شانس
        stability_reduction = stability_bonus / 100  # کاهش شانس شورش بر اساس ثبات
        
        # تأثیر رضایت مردم بر شورش
        user = utils.users.get(str(user_id), {})
        satisfaction = user.get('satisfaction', 70)
        satisfaction_modifier = (50 - satisfaction) / 100  # رضایت پایین = شورش بیشتر
        
        # تأثیر گارد ویژه از فروشگاه
        riot_suppression_bonus = 0
        if has_user_riot_suppression(user_id):
            riot_suppression_bonus = 0.3  # 30% کاهش شانس شورش
        
        # اثر مهاجران: +2% انقلاب به ازای هر 1M
        try:
            imm_units = int(utils.users.get(user_id, {}).get('immigrants', 0)) // 1_000_000
        except Exception:
            imm_units = 0
        immigrants_revolution_bonus = (imm_units * 2) / 100.0
        final_rebellion_chance = max(0, base_rebellion_chance - stability_reduction + satisfaction_modifier - riot_suppression_bonus + immigrants_revolution_bonus)
        
        # بررسی وقوع شورش
        if final_rebellion_chance > 0 and random.random() < final_rebellion_chance:
            user = utils.users.get(str(user_id), {})
            resources = user.get('resources', {})
            
            # تأثیرات شورش: از دست دادن منابع
            rebellion_effects = {
                'cash': 0.1,  # 10% کاهش پول
                'iron': 0.15,  # 15% کاهش آهن
                'steel': 0.15,  # 15% کاهش فولاد
                'oil': 0.2,  # 20% کاهش نفت
                'electricity': 0.1,  # 10% کاهش برق
            }
            
            rebellion_message = f"🔥 <b>شورش داخلی!</b>\n\n"
            rebellion_message += f"⚔️ شورش‌گران در کشور شما قیام کرده‌اند!\n\n"
            rebellion_message += "📉 <b>تأثیرات شورش:</b>\n"
            
            for resource, reduction_rate in rebellion_effects.items():
                if resource in resources and resources[resource] > 0:
                    reduction = int(resources[resource] * reduction_rate)
                    resources[resource] = max(0, resources[resource] - reduction)
                    rebellion_message += f"▫️ {resource}: -{reduction:,}\n"
            
            rebellion_message += f"\n💡 <b>راهنمایی:</b> برای کاهش ریسک شورش، حکومت با ثبات بالاتر انتخاب کنید."
            
            # ارسال پیام شورش با تصویر به کاربر و خبر در کانال
            try:
                rebellion_photo = "https://t.me/TextEmpire_IR/95"
                await context.bot.send_photo(
                    chat_id=int(user_id),
                    photo=rebellion_photo,
                    caption=rebellion_message,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"خطا در ارسال پیام شورش به کاربر: {e}")

            # خبر شورش در کانال اخبار با لحن خبری
            try:
                from utils import NEWS_CHANNEL_ID
                country = utils.users.get(user_id, {}).get('country', 'کشور ناشناس')
                news_text = "🛑 خبر فوری: شورش داخلی\n\n"
                news_text += f"در {country} شورش‌های گسترده‌ای گزارش شده است. منابع کلیدی کاهش یافتند و دولت برای بازگشت ثبات تلاش می‌کند.\n\n"
                news_text += "📉 خلاصه خسارات:\n"
                for resource, reduction_rate in rebellion_effects.items():
                    # محاسبه همان کاهش برای گزارش (از reduction که بالا اعمال شد استفاده نکردیم چون تغییر داده شده)
                    # لذا یک برآورد متنی روی درصد ارائه می‌دهیم
                    percent = int(reduction_rate * 100)
                    news_text += f"▫️ {resource}: -{percent}% تقریبی\n"
                news_text += "\n💡 راهنما: حکومت با ثبات بالاتر می‌تواند ریسک شورش را کاهش دهد."
                await context.bot.send_photo(
                    chat_id=NEWS_CHANNEL_ID,
                    photo=rebellion_photo,
                    caption=news_text,
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"خطا در ارسال خبر شورش به کانال: {e}")
    

    

    
    # ارسال گزارش جمعیت به گروه
    try:
        from jame import send_population_report_to_channel
        await send_population_report_to_channel(context.bot)
    except Exception as e:
        print(f"خطا در ارسال گزارش جمعیت: {e}")
    
    # ارسال گزارش اقتصادی به گروه
    try:
        from jame import send_economy_report_to_channel
        await send_economy_report_to_channel(context.bot)
    except Exception as e:
        print(f"خطا در ارسال گزارش اقتصادی: {e}")
    
    # ارسال رتبه‌بندی نظامی جهانی به کانال
    try:
        from analysis import send_global_military_ranking
        await send_global_military_ranking()
    except Exception as e:
        print(f"خطا در ارسال رتبه‌بندی نظامی: {e}")
    
    # ارسال آمار منابع جهانی به کانال
    try:
        from analysis import send_global_resources_ranking
        await send_global_resources_ranking()
    except Exception as e:
        print(f"خطا در ارسال آمار منابع جهانی: {e}")
    
    # به‌روزرسانی جمعیت کشورها
    try:
        from jame import update_population
        for user_id in utils.users:
            if utils.users[user_id].get('activated', False):
                population_growth = update_population(user_id)
                if population_growth > 0:
                    print(f"جمعیت کشور {utils.users[user_id]['country']} {population_growth:,} نفر افزایش یافت")
    except Exception as e:
        print(f"خطا در به‌روزرسانی جمعیت: {e}")
    
    # ارسال گزارش‌های مسئولین به کاربران
    try:
        from reports import send_official_reports, send_economic_growth_report_to_channel
        await send_official_reports(context.bot, game_data['turn'])
        print(f"گزارش‌های مسئولین برای دور {game_data['turn']} ارسال شد")
        
        # ارسال گزارش رشد اقتصادی به کانال
        await send_economic_growth_report_to_channel(context.bot, game_data['turn'])
        print(f"گزارش رشد اقتصادی برای دور {game_data['turn']} به کانال ارسال شد")
    except Exception as e:
        print(f"خطا در ارسال گزارش‌های مسئولین: {e}")
    
    # بررسی پایان فصل در پایان دور 40
    if int(game_data.get('turn', 0)) >= 40:
        await finalize_season(context)
    
    return f"دور {game_data['turn']} با موفقیت پیش‌برد یافت!\nتاریخ جدید: {game_data['game_date']}\nقیمت طلا: {game_data['prices']['gold']:,} دلار"


# پردازش تعداد تولید تسلیحات نظامی
async def process_military_production_amount(message, context):
    user_id = str(message.from_user.id)
    print(f"[DEBUG] process_military_production_amount called: user_id={user_id}")
    if user_id not in utils.pending_military_production:
        print(f"[DEBUG] user_id {user_id} not in utils.pending_military_production")
        return
    data = utils.pending_military_production[user_id]
    item_key = data['item_key']
    print(f"[DEBUG] item_key={item_key}")
    recipe = MILITARY_PRODUCTION_RECIPES.get(item_key)
    print(f"[DEBUG] recipe={recipe}")
    if not recipe:
        print(f"[DEBUG] No recipe found for item_key={item_key}")
        await message.reply_text('❌ خطا در پردازش اطلاعات. لطفاً دوباره تلاش کنید.')
        utils.pending_military_production.pop(user_id, None)
        return
    try:
        amount = int(message.text.replace(',', ''))
        if amount <= 0:
            print(f"[DEBUG] Invalid amount: {amount}")
            await message.reply_text('❌ تعداد باید بیشتر از صفر باشد.')
            return
    except ValueError:
        print(f"[DEBUG] ValueError for amount: {message.text}")
        await message.reply_text('❌ لطفاً یک عدد معتبر وارد کنید.')
        return
    inputs = recipe['inputs']
    recipe_amount = recipe['amount']
    required_resources = {}
    for resource, base_amount in inputs.items():
        required_resources[resource] = (base_amount / recipe_amount) * amount
    print(f"[DEBUG] required_resources={required_resources}")
    user = utils.users.get(str(user_id), {})
    user_resources = user.get('resources', {})
    print(f"[DEBUG] user_resources={user_resources}")
    missing_resources = []
    for resource, required_amount in required_resources.items():
        available = user_resources.get(resource, 0)
        if available < required_amount:
            missing_resources.append(f"{resource}: {available}/{required_amount}")
    if missing_resources:
        print(f"[DEBUG] missing_resources: {missing_resources}")
        
        # نام فارسی منابع
        resource_names = {
            'steel': 'فولاد', 'oil': 'نفت', 'electricity': 'برق', 'electronics': 'الکترونیک',
            'iron': 'آهن', 'aluminum': 'آلومینیوم', 'titanium': 'تیتانیوم', 'copper': 'مس',
            'gold': 'طلا', 'diamond': 'الماس', 'uranium': 'اورانیوم', 'wheat': 'گندم',
            'rice': 'برنج', 'fruits': 'میوه', 'gas': 'گاز', 'pride_cars': 'خودرو پراید',
            'benz_cars': 'خودرو بنز'
        }
        
        # تبدیل نام‌های منابع به فارسی
        persian_missing = []
        for item in missing_resources:
            resource, amount = item.split(': ')
            persian_name = resource_names.get(resource, resource)
            persian_missing.append(f"▫️ {persian_name}: {amount}")
        
        missing_text = '\n'.join(persian_missing)
        await message.reply_text(f"❌ منابع کافی ندارید:\n\n{missing_text}")
        utils.pending_military_production.pop(user_id, None)
        return
    
    # نمایش تایید نهایی
    # نام فارسی تسلیحات
    military_names = {
        'soldiers': 'سربازان', 'special_forces': 'نیروهای ویژه', 'tanks': 'تانک',
        'armored_vehicles': 'نفربر', 'transport_planes': 'هواپیمای ترابری',
        'helicopters': 'بالگرد', 'fighter_jets': 'جنگنده', 'bombers': 'بمب‌افکن',
        'artillery': 'توپخانه', 'drones': 'پهپاد', 'air_defense': 'پدافند هوایی',
        'coastal_artillery': 'توپخانه ساحلی', 'speedboats': 'قایق تندرو',
        'naval_ship': 'ناو جنگی', 'submarines': 'زیردریایی', 'aircraft_carriers': 'ناو هواپیمابر'
    }
    
    output_name = military_names.get(recipe['output'], recipe['output'])
    
    # نام فارسی منابع
    resource_names = {
        'steel': 'فولاد', 'oil': 'نفت', 'electricity': 'برق', 'electronics': 'الکترونیک',
        'iron': 'آهن', 'aluminum': 'آلومینیوم', 'titanium': 'تیتانیوم'
    }
    
    resources_text = '\n'.join([f"▫️ {resource_names.get(res, res)}: {req_amount:,}" for res, req_amount in required_resources.items()])
    
    text = f"🛡️ <b>تایید تولید {output_name}</b>\n\n<b>تعداد:</b> {amount:,} واحد\n\n<b>منابع مصرفی:</b>\n{resources_text}\n\nآیا تایید می‌کنید؟"
    
    keyboard = [
        [InlineKeyboardButton('تایید ✅', callback_data=f'military_produce_final_{item_key}_{amount}'), 
         InlineKeyboardButton('لغو ❌', callback_data='military_production')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    # ذخیره اطلاعات برای تایید نهایی
    utils.pending_military_production[user_id] = {
        'item_key': item_key,
        'amount': amount,
        'required_resources': required_resources,
        'step': 'confirm'
    }

# پردازش تعداد تولید خط تولید
async def process_production_line_amount(message, context):
    user_id = str(message.from_user.id)
    print(f"[DEBUG] process_production_line_amount called: user_id={user_id}")
    if user_id not in pending_production_line_production:
        print(f"[DEBUG] user_id {user_id} not in pending_production_line_production")
        return
    data = pending_production_line_production[user_id]
    item_key = data['item_key']
    print(f"[DEBUG] item_key={item_key}")
    recipe = PRODUCTION_RECIPES.get(item_key)
    print(f"[DEBUG] recipe={recipe}")
    if not recipe:
        print(f"[DEBUG] No recipe found for item_key={item_key}")
        await message.reply_text('❌ خطا در پردازش اطلاعات. لطفاً دوباره تلاش کنید.')
        pending_production_line_production.pop(user_id, None)
        return
    try:
        amount = int(message.text.replace(',', ''))
        if amount <= 0:
            print(f"[DEBUG] Invalid amount: {amount}")
            await message.reply_text('❌ تعداد باید بیشتر از صفر باشد.')
            return
    except ValueError:
        print(f"[DEBUG] ValueError for amount: {message.text}")
        await message.reply_text('❌ لطفاً یک عدد معتبر وارد کنید.')
        return
    inputs = recipe['inputs']
    recipe_amount = recipe['amount']
    required_resources = {}
    for resource, base_amount in inputs.items():
        required_resources[resource] = (base_amount / recipe_amount) * amount
    print(f"[DEBUG] required_resources={required_resources}")
    user = utils.users.get(str(user_id), {})
    user_resources = user.get('resources', {})
    print(f"[DEBUG] user_resources={user_resources}")
    missing_resources = []
    for resource, required_amount in required_resources.items():
        available = user_resources.get(resource, 0)
        if available < required_amount:
            missing_resources.append(f"{resource}: {available}/{required_amount}")
    if missing_resources:
        print(f"[DEBUG] missing_resources: {missing_resources}")
        
        # نام فارسی منابع
        resource_names = {
            'steel': 'فولاد', 'oil': 'نفت', 'electricity': 'برق', 'electronics': 'الکترونیک',
            'iron': 'آهن', 'aluminum': 'آلومینیوم', 'titanium': 'تیتانیوم', 'copper': 'مس',
            'gold': 'طلا', 'diamond': 'الماس', 'uranium': 'اورانیوم', 'wheat': 'گندم',
            'rice': 'برنج', 'fruits': 'میوه', 'gas': 'گاز', 'pride_cars': 'خودرو پراید',
            'benz_cars': 'خودرو بنز'
        }
        
        # تبدیل نام‌های منابع به فارسی
        persian_missing = []
        for item in missing_resources:
            resource, amount = item.split(': ')
            persian_name = resource_names.get(resource, resource)
            persian_missing.append(f"▫️ {persian_name}: {amount}")
        
        missing_text = '\n'.join(persian_missing)
        await message.reply_text(f"❌ منابع کافی ندارید:\n\n{missing_text}")
        pending_production_line_production.pop(user_id, None)
        return
    
    # نمایش تایید نهایی
    # نام فارسی محصولات خط تولید
    production_names = {
        'pride_cars': 'پراید', 'benz_cars': 'بنز', 'electronics': 'الکترونیک'
    }
    
    output_name = production_names.get(recipe['output'], recipe['output'])
    
    # نام فارسی منابع
    resource_names = {
        'steel': 'فولاد', 'oil': 'نفت', 'electricity': 'برق', 'electronics': 'الکترونیک',
        'iron': 'آهن', 'aluminum': 'آلومینیوم', 'titanium': 'تیتانیوم'
    }
    
    resources_text = '\n'.join([f"▫️ {resource_names.get(res, res)}: {req_amount:,}" for res, req_amount in required_resources.items()])
    
    text = f"🏗️ <b>تایید تولید {output_name}</b>\n\n<b>تعداد:</b> {amount:,} واحد\n\n<b>منابع مصرفی:</b>\n{resources_text}\n\nآیا تایید می‌کنید؟"
    
    keyboard = [
        [InlineKeyboardButton('تایید ✅', callback_data=f'production_line_final_{item_key}_{amount}'), 
         InlineKeyboardButton('لغو ❌', callback_data='production_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    # ذخیره اطلاعات برای تایید نهایی
    pending_production_line_production[user_id] = {
        'item_key': item_key,
        'amount': amount,
        'required_resources': required_resources,
        'step': 'confirm'
    }

# تایید نهایی و تولید تسلیحات نظامی
async def confirm_military_production(query, user_id, item_key, amount):
    print(f"[DEBUG] confirm_military_production called: user_id={user_id}, item_key={item_key}, amount={amount}")
    if user_id not in utils.pending_military_production:
        print(f"[DEBUG] user_id {user_id} not in utils.pending_military_production")
        await query.edit_message_text('❌ اطلاعات تولید یافت نشد. لطفاً دوباره تلاش کنید.')
        return
    data = utils.pending_military_production[user_id]
    if data.get('item_key') != item_key or data.get('amount') != amount:
        print(f"[DEBUG] Data mismatch: data={data}")
        await query.edit_message_text('❌ اطلاعات تولید مطابقت ندارد. لطفاً دوباره تلاش کنید.')
        utils.pending_military_production.pop(user_id, None)
        return
    recipe = MILITARY_PRODUCTION_RECIPES.get(item_key)
    print(f"[DEBUG] recipe={recipe}")
    if not recipe:
        print(f"[DEBUG] No recipe found for item_key={item_key}")
        await query.edit_message_text('❌ فرمول تولید یافت نشد.')
        utils.pending_military_production.pop(user_id, None)
        return
    user = utils.users.get(str(user_id), {})
    user_resources = user.get('resources', {})
    required_resources = data['required_resources']
    print(f"[DEBUG] required_resources={required_resources}")
    print(f"[DEBUG] user_resources={user_resources}")
    for resource, required_amount in required_resources.items():
        available = user_resources.get(resource, 0)
        if available < required_amount:
            print(f"[DEBUG] Not enough resource: {resource}: {available}/{required_amount}")
            # نام فارسی منابع
            resource_names = {
                'steel': 'فولاد', 'oil': 'نفت', 'electricity': 'برق', 'electronics': 'الکترونیک',
                'iron': 'آهن', 'aluminum': 'آلومینیوم', 'titanium': 'تیتانیوم', 'copper': 'مس',
                'gold': 'طلا', 'diamond': 'الماس', 'uranium': 'اورانیوم', 'wheat': 'گندم',
                'rice': 'برنج', 'fruits': 'میوه', 'gas': 'گاز', 'pride_cars': 'خودرو پراید',
                'benz_cars': 'خودرو بنز'
            }
            persian_name = resource_names.get(resource, resource)
            await query.edit_message_text(f'❌ منابع کافی ندارید. {persian_name}: {available}/{required_amount}')
            utils.pending_military_production.pop(user_id, None)
            return
    # کسر منابع و اضافه کردن تسلیحات
    for resource, required_amount in required_resources.items():
        user_resources[resource] -= required_amount
    
    # اضافه کردن تسلیحات تولید شده
    output = recipe['output']
    user_resources[output] = user_resources.get(output, 0) + amount
    
    save_users()
    
    # نام فارسی تسلیحات
    military_names = {
        'soldiers': 'سربازان', 'special_forces': 'نیروهای ویژه', 'tanks': 'تانک',
        'armored_vehicles': 'نفربر', 'transport_planes': 'هواپیمای ترابری',
        'helicopters': 'بالگرد', 'fighter_jets': 'جنگنده', 'bombers': 'بمب‌افکن',
        'artillery': 'توپخانه', 'drones': 'پهپاد', 'air_defense': 'پدافند هوایی',
        'coastal_artillery': 'توپخانه ساحلی', 'speedboats': 'قایق تندرو',
        'naval_ship': 'ناو جنگی', 'submarines': 'زیردریایی', 'aircraft_carriers': 'ناو هواپیمابر'
    }
    
    output_name = military_names.get(output, output)
    
    await query.edit_message_text(f"✅ {amount:,} واحد {output_name} با موفقیت تولید شد!")
    utils.pending_military_production.pop(user_id, None)
async def confirm_production_line(query, user_id, item_key, amount):
    print(f"[DEBUG] confirm_production_line called: user_id={user_id}, item_key={item_key}, amount={amount}")
    if user_id not in pending_production_line_production:
        print(f"[DEBUG] user_id {user_id} not in pending_production_line_production")
        return
    
    data = pending_production_line_production[user_id]
    if data['step'] != 'confirm':
        print(f"[DEBUG] step is not confirm: {data['step']}")
        return
    
    pending_production_line_production.pop(user_id, None)
    
    recipe = PRODUCTION_RECIPES.get(item_key)
    if not recipe:
        print(f"[DEBUG] No recipe found for item_key={item_key}")
        await query.edit_message_text('❌ خطا در پردازش اطلاعات.')
        return
    
    # بررسی منابع
    user = utils.users.get(str(user_id), {})
    resources = user.get('resources', {})
    inputs = recipe['inputs']
    recipe_amount = recipe['amount']
    
    # محاسبه منابع مورد نیاز
    required_resources = {}
    for resource, base_amount in inputs.items():
        required_resources[resource] = (base_amount / recipe_amount) * amount
    
    # بررسی کافی بودن منابع
    for resource, required_amount in required_resources.items():
        if resources.get(resource, 0) < required_amount:
            await query.edit_message_text(f'❌ منبع کافی برای تولید ندارید: {resource}')
            return
    
    # مصرف منابع
    for resource, required_amount in required_resources.items():
        resources[resource] -= required_amount
    
    # اضافه کردن محصول تولید شده
    output = recipe['output']
    total_output = amount * recipe_amount
    resources[output] = resources.get(output, 0) + total_output
    
    # ذخیره تغییرات
    utils.save_users()
    
    # نام فارسی محصولات خط تولید
    production_names = {
        'pride_cars': 'پراید', 'benz_cars': 'بنز', 'electronics': 'الکترونیک'
    }
    
    output_name = production_names.get(output, output)
    
    await query.edit_message_text(f"✅ {total_output:,} واحد {output_name} با موفقیت تولید شد!")
    pending_production_line_production.pop(user_id, None)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    
    # Skip auto-answer for refugee handlers (they handle it themselves)
    skip_auto_answer = False
    if query.data:
        if query.data.startswith('new_refugee_accept_') or query.data.startswith('new_refugee_reject_'):
            skip_auto_answer = True
    
    if not skip_auto_answer:
        try:
            await query.answer()
        except Exception:
            pass
        try:
            print(f"[DEBUG][CB] user={query.from_user.id} data={query.data}")
        except Exception:
            pass
    else:
        try:
            print(f"[DEBUG][CB] user={query.from_user.id} data={query.data} (refugee handler)")
        except Exception:
            pass
    user_id = str(query.from_user.id)
    # جلوگیری از تعامل کاربر بن شده
    try:
        from utils import is_user_banned
        if is_user_banned(user_id):
            return
    except Exception:
        pass
    
    # Migration username->id
    try:
        import utils
        tg_username = ''
        try:
            tg_username = query.from_user.username or ''
        except Exception:
            tg_username = ''
        utils.migrate_user_identifier(user_id, tg_username)
        # شمارش تعامل مهمان و انقضا
        guest_expired = utils.increment_guest_interaction_and_maybe_expire(user_id)
        if guest_expired:
            await query.edit_message_text('❌ فرصت شما به پایان رسید. برای ادامه باید ثبت‌نام کنید.')
            return
    except Exception:
        pass

    # چک کردن ثبت‌نام
    try:
        import utils
        u = utils.users.get(str(user_id), {})
        prof = u.get('profile', {})
        if not (prof.get('is_registered') or prof.get('guest')):
            await query.edit_message_text('❌ برای استفاده از منوها ابتدا باید ثبت‌نام کنید. /start را بزنید.')
            return
    except Exception:
        pass
    
    # چک کردن مسدودیت به دلیل تأیید موقعیت
    try:
        from utils import is_user_blocked
        if is_user_blocked(user_id):
            await query.edit_message_text(
                '🚫 شما به دلیل عدم تأیید موقعیت مسدود شده‌اید.\n\n'
                'لطفاً با پشتیبانی تماس بگیرید.'
            )
            return
    except Exception:
        pass
    activated = get_user_activated(user_id)

    if query and query.data == 'start_game':
        await show_game_menu(query)
    elif query and query.data == 'inactive_start':
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
    elif query and query.data == 'countries':
        await show_countries_menu(query)
    elif query and query.data == 'activate_country':
        await activate_country_prompt(query, user_id)
    elif query and query.data == 'hall_of_fame':
        try:
            import utils
            title_points = {
                'امپراتور جهانی': 50,
                'سلطان اقتصاد': 30,
                'دیپلمات اعظم': 20,
                'فرمانده آهنین': 20,
                'محبوب ملت‌ها': 10,
                'سلطان صاحبقِران': 20,
                'پیشکسوت جهان': 25,
                'امپراتور حقیقی': 100
            }
            leaderboard = []
            for uid, usr in utils.users.items():
                prof2 = usr.get('profile', {})
                if not (prof2.get('is_registered') or prof2.get('guest')):
                    continue
                user_titles = usr.get('titles', []) or []
                score = 0
                for t in user_titles:
                    score += title_points.get(t.get('name', ''), 0)
                leaderboard.append({
                    'player_name': usr.get('player_name', 'نامشخص'),
                    'identifier': usr.get('public_identifier', ''),
                    'score': score
                })
            leaderboard.sort(key=lambda x: x['score'], reverse=True)
            text = '🏛 <b>تالار افتخارات</b>\n\n'
            if not leaderboard:
                text += 'هیچ کاربر ثبت‌نام‌شده‌ای یافت نشد.'
            else:
                for idx, row in enumerate(leaderboard[:50], start=1):
                    id_disp = f"/name{row['identifier']}" if row['identifier'] else '-'
                    text += f"{idx}. {row['player_name']} — {id_disp} | امتیاز: {row['score']}\n"
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='back_to_profile')]])
            await query.edit_message_text(text, parse_mode='HTML', reply_markup=keyboard)
        except Exception as e:
            print(f"hall_of_fame error: {e}")
            await query.answer('خطا در نمایش تالار افتخارات', show_alert=True)
        return
    elif query and query.data == 'back_to_profile':
        await query.edit_message_text('برای مشاهده پروفایل، از منوی اصلی گزینه پروفایل را انتخاب کنید.')
        return
    elif query and query.data.startswith('user_title_hall_'):
        target_user_id = query.data.replace('user_title_hall_', '')
        await show_user_title_hall(query, target_user_id)
        return
    elif query and query.data.startswith('back_to_profile_'):
        target_user_id = query.data.replace('back_to_profile_', '')
        # Show the public profile again
        try:
            import utils
            target_user_data = utils.users.get(target_user_id, {})
            if target_user_data:
                await show_public_profile(query, None, target_user_id, target_user_data)
            else:
                await query.edit_message_text('❌ کاربر یافت نشد.')
        except Exception as e:
            print(f"Error showing profile: {e}")
            await query.edit_message_text('❌ خطا در نمایش پروفایل.')
        return
    elif query and query.data == 'gov_info':
        # نمایش اطلاعات حکومت‌ها
        text = "🏛️ <b>اطلاعات انواع حکومت‌ها</b>\n\n"
        text += "هر نوع حکومت مزایا و معایب خاص خود را دارد:\n\n"
        
        # نمایش خلاصه حکومت‌ها
        gov_summaries = {
            'monarchy': '👑 شاهنشاهی: ثبات بالا، روابط دیپلماتیک قوی',
            'dictatorship': '⚡ رهبری: قدرت نظامی بالا، تصمیم‌گیری سریع',
            'presidency': '⚖️ ریاست جمهوری: متعادل در همه زمینه‌ها',
            'parliament': '🏛️ پارلمانی: نوآوری بالا، تجارت قوی',
            'federation': '🌐 فدراسیون: منابع فراوان، تجارت گسترده',
            'empire': '👑 امپراتوری: قدرت نظامی فوق‌العاده، قلمرو وسیع',
            'republic': '🏛️ جمهوری: روابط دیپلماتیک قوی، مردمی',
            'democracy': '🗽 دموکراسی: نوآوری بالا، آموزش پیشرفته',
            'oligarchy': '💰 الیگارشی: اقتصاد قوی، تولید بالا',
            'theocracy': '⛪ تئوکراسی: ثبات بالا، روحیه قوی',
            'military': '⚔️ نظامی: قدرت جنگی فوق‌العاده',
            'socialist': '🏭 سوسیالیستی: برابری اجتماعی، عدالت',
            'capitalist': '💼 کاپیتالیستی: اقتصاد قوی، نوآوری',
            'communist': '🏭 کمونیستی: تولید بالا، برابری',
            'anarchist': '🆓 آنارشیستی: نوآوری فوق‌العاده، آزادی'
        }
        
        for gov_key, summary in gov_summaries.items():
            text += f"{summary}\n"
        
        text += "\n💡 <b>برای مشاهده جزئیات کامل، حکومت مورد نظر را انتخاب کنید.</b>"
        
        keyboard = create_government_selection_keyboard()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='HTML')
        
    elif query and query.data.startswith('gov_type_'):
        gov_type = query.data.replace('gov_type_', '')
        
        pending_government_selection[user_id] = gov_type
        
        # نمایش اطلاعات کامل حکومت انتخاب شده
        gov_info = format_government_info(gov_type)
        
        # اضافه کردن دکمه تأیید
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton('✅ تأیید انتخاب', callback_data=f'confirm_gov_{gov_type}')],
            [InlineKeyboardButton('🔙 بازگشت', callback_data='gov_info')]
        ])
        
        await query.edit_message_text(gov_info, reply_markup=keyboard, parse_mode='HTML')
    elif query and query.data.startswith('confirm_gov_'):
        gov_type = query.data.replace('confirm_gov_', '')
        
        pending_government_selection[user_id] = gov_type
        text = f'🎭 <b>انتخاب نوع حکومت</b>\n\nشما {GOVERNMENT_TYPES[gov_type]} را انتخاب کردید.\n\nحالا لطفاً نام خود را وارد کنید:'
        await query.edit_message_text(text, parse_mode='HTML')
        pending_name_selection[user_id] = True
    elif query and query.data.startswith('select_name_'):
        if pending_minister_selection.get(user_id):
            # انتخاب وزیر کشور
            name_index = int(query.data.replace('select_name_', ''))
            # استفاده از اسامی ذخیره شده
            names_suggestions = utils.users[user_id].get('current_names_suggestions', [])
            if not names_suggestions:
                try:
                    used_global = get_used_official_names('minister')
                except Exception:
                    used_global = set()
                names_suggestions = generate_name_suggestions(10, exclude_names=list(used_global))
            selected_minister = names_suggestions[name_index]
            
            # ذخیره وزیر کشور
            if 'selected_officials' not in utils.users[user_id]:
                utils.users[user_id]['selected_officials'] = {}
            utils.users[user_id]['selected_officials']['minister'] = {
                'name': selected_minister,
                'title': 'وزیر کشور'
            }
            utils.save_users()
            
            # شروع انتخاب ژنرال
            pending_minister_selection.pop(user_id, None)
            pending_general_selection[user_id] = True
            
            # تولید اسامی جدید برای ژنرال (جهانی)
            selected_minister_name = selected_minister
            try:
                used_global = get_used_official_names('general')
            except Exception:
                used_global = set()
            names_suggestions = generate_name_suggestions(10, exclude_names=[selected_minister_name, *list(used_global)])
            utils.users[user_id]['current_names_suggestions'] = names_suggestions
            keyboard = create_name_selection_keyboard(names_suggestions, 'general')
            await query.edit_message_text(
                f'✅ وزیر کشور شما: <b>{selected_minister}</b>\n\n'
                f'حالا لطفاً ژنرال خود را انتخاب کنید:',
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        elif pending_general_selection.get(user_id):
            # انتخاب ژنرال
            name_index = int(query.data.replace('select_name_', ''))
            # استفاده از اسامی ذخیره شده
            names_suggestions = utils.users[user_id].get('current_names_suggestions', [])
            if not names_suggestions:
                selected_minister_name = utils.users[user_id]['selected_officials']['minister']['name']
                names_suggestions = generate_name_suggestions(10, exclude_names=[selected_minister_name])
            selected_general = names_suggestions[name_index]
            
            # ذخیره ژنرال
            utils.users[user_id]['selected_officials']['general'] = {
                'name': selected_general,
                'title': 'ژنرال'
            }
            utils.save_users()
            
            # شروع انتخاب وزیر خارجه
            pending_general_selection.pop(user_id, None)
            pending_foreign_selection[user_id] = True
            
            # تولید اسامی جدید برای وزیر خارجه
            selected_minister_name = utils.users[user_id]['selected_officials']['minister']['name']
            selected_general_name = selected_general
            try:
                used_global = get_used_official_names('foreign')
            except Exception:
                used_global = set()
            names_suggestions = generate_name_suggestions(10, exclude_names=[selected_minister_name, selected_general_name, *list(used_global)])
            utils.users[user_id]['current_names_suggestions'] = names_suggestions
            keyboard = create_name_selection_keyboard(names_suggestions, 'foreign')
            
            await query.edit_message_text(
                f'✅ وزیر کشور: <b>{utils.users[user_id]["selected_officials"]["minister"]["name"]}</b>\n'
                f'✅ ژنرال: <b>{selected_general}</b>\n\n'
                f'حالا لطفاً وزیر خارجه خود را انتخاب کنید:',
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        elif pending_foreign_selection.get(user_id):
            # انتخاب وزیر خارجه
            name_index = int(query.data.replace('select_name_', ''))
            # استفاده از اسامی ذخیره شده
            names_suggestions = utils.users[user_id].get('current_names_suggestions', [])
            if not names_suggestions:
                selected_minister_name = utils.users[user_id]['selected_officials']['minister']['name']
                selected_general_name = utils.users[user_id]['selected_officials']['general']['name']
                names_suggestions = generate_name_suggestions(10, exclude_names=[selected_minister_name, selected_general_name])
            selected_foreign = names_suggestions[name_index]
            
            # ذخیره وزیر خارجه
            utils.users[user_id]['selected_officials']['foreign'] = {
                'name': selected_foreign,
                'title': 'وزیر خارجه'
            }
            utils.save_users()
            
            # شروع انتخاب وزیر دارایی
            pending_foreign_selection.pop(user_id, None)
            pending_finance_selection[user_id] = True
            
            # تولید اسامی جدید برای وزیر دارایی
            selected_minister_name = utils.users[user_id]['selected_officials']['minister']['name']
            selected_general_name = utils.users[user_id]['selected_officials']['general']['name']
            selected_foreign_name = selected_foreign
            try:
                used_global = get_used_official_names('finance')
            except Exception:
                used_global = set()
            names_suggestions = generate_name_suggestions(10, exclude_names=[selected_minister_name, selected_general_name, selected_foreign_name, *list(used_global)])
            utils.users[user_id]['current_names_suggestions'] = names_suggestions
            keyboard = create_name_selection_keyboard(names_suggestions, 'finance')
            
            await query.edit_message_text(
                f'✅ وزیر کشور: <b>{utils.users[user_id]["selected_officials"]["minister"]["name"]}</b>\n'
                f'✅ ژنرال: <b>{utils.users[user_id]["selected_officials"]["general"]["name"]}</b>\n'
                f'✅ وزیر خارجه: <b>{selected_foreign}</b>\n\n'
                f'حالا لطفاً وزیر دارایی خود را انتخاب کنید:',
                reply_markup=keyboard,
                parse_mode='HTML'
            )
        elif pending_finance_selection.get(user_id):
            # انتخاب وزیر دارایی
            name_index = int(query.data.replace('select_name_', ''))
            # استفاده از اسامی ذخیره شده
            names_suggestions = utils.users[user_id].get('current_names_suggestions', [])
            if not names_suggestions:
                selected_minister_name = utils.users[user_id]['selected_officials']['minister']['name']
                selected_general_name = utils.users[user_id]['selected_officials']['general']['name']
                selected_foreign_name = utils.users[user_id]['selected_officials']['foreign']['name']
                names_suggestions = generate_name_suggestions(10, exclude_names=[selected_minister_name, selected_general_name, selected_foreign_name])
            selected_finance = names_suggestions[name_index]
            
            # ذخیره وزیر دارایی
            utils.users[user_id]['selected_officials']['finance'] = {
                'name': selected_finance,
                'title': 'وزیر دارایی'
            }
            utils.save_users()
            
            # پایان انتخاب مسئولین و درخواست کد فعال‌سازی
            pending_finance_selection.pop(user_id, None)
            pending_activation[user_id] = True
            
            gov_title = utils.users[user_id]['government_title']
            player_name = get_country_leader_display_name(user_id)
            
            await query.edit_message_text(
                f'✅ وزیر کشور: <b>{utils.users[user_id]["selected_officials"]["minister"]["name"]}</b>\n'
                f'✅ ژنرال: <b>{utils.users[user_id]["selected_officials"]["general"]["name"]}</b>\n'
                f'✅ وزیر خارجه: <b>{utils.users[user_id]["selected_officials"]["foreign"]["name"]}</b>\n'
                f'✅ وزیر دارایی: <b>{selected_finance}</b>\n\n'
                f'🎭 <b>{gov_title} {player_name}</b>\n\n'
                f'حالا لطفاً کد فعال‌سازی کشور را وارد کنید:',
                parse_mode='HTML'
            )
    elif query and query.data == 'help':
        await show_simple_section(query, 'آموزش بازی به زودی اضافه می‌شود.', back_to='main')
    elif query and query.data == 'support':
        await show_simple_section(query, 'برای پشتیبانی با ادمین به <a href="https://t.me/Rylotm">@Rylotm</a> پیام دهید.', parse_mode='HTML', back_to='main')
    elif query and query.data == 'admin_menu':
        if user_id == ADMIN_ID:
            await show_admin_menu(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_game_management':
        if user_id == ADMIN_ID:
            await admin_panel.show_admin_game_management(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_finalize_season':
        if user_id == ADMIN_ID:
            # تنظیم دور به 50 و اعلام نتایج فصل
            game_data['turn'] = 50
            await finalize_season(context)
            try:
                await query.answer('✅ فصل به پایان رسید و نتایج ارسال شد.', show_alert=True)
            except Exception:
                pass
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_statistics':
        if user_id == ADMIN_ID:
            await admin_panel.show_admin_statistics(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_user_management':
        if user_id == ADMIN_ID:
            await admin_panel.show_admin_user_management(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_auto_profile':
        if user_id == ADMIN_ID:
            await admin_panel.prompt_admin_auto_profile(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_system_settings':
        if user_id == ADMIN_ID:
            await admin_panel.show_admin_system_settings(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_advanced_tools':
        if user_id == ADMIN_ID:
            await admin_panel.show_admin_advanced_tools(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_war_management':
        if user_id == ADMIN_ID:
            await admin_panel.show_admin_war_management(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_war_ground':
        if user_id == ADMIN_ID:
            await admin_panel.show_admin_war_type(query, 'ground')
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_war_air':
        if user_id == ADMIN_ID:
            await admin_panel.show_admin_war_type(query, 'air')
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_war_naval':
        if user_id == ADMIN_ID:
            await admin_panel.show_admin_war_type(query, 'naval')
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_war_missile':
        if user_id == ADMIN_ID:
            await admin_panel.show_admin_war_type(query, 'missile')
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data.startswith('admin_cancel_war_'):
        if user_id == ADMIN_ID:
            # Parse callback data: admin_cancel_war_{war_type}_{war_key}
            parts = query.data.replace('admin_cancel_war_', '').split('_', 1)
            if len(parts) == 2:
                war_type, war_key = parts
                await admin_panel.cancel_admin_war(query, war_type, war_key)
            else:
                await query.answer("❌ خطا در پردازش درخواست!", show_alert=True)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'national_security_menu':
        await show_national_security_menu(query)
    elif query and query.data == 'national_security_create':
        await start_national_security_creation(query)
    elif query and query.data == 'national_security_org':
        await open_national_security_org(query)
    elif query and query.data == 'national_security_skip_logo':
        uid = str(query.from_user.id)
        if uid in utils.pending_national_security and utils.pending_national_security[uid].get('step') == 'ask_logo':
            utils.pending_national_security[uid]['logo_file_id'] = None
            await show_national_security_features(query, uid)
        else:
            await show_national_security_menu(query)
    elif query and query.data == 'cancel_national_security':
        uid = str(query.from_user.id)
        utils.pending_national_security.pop(uid, None)
        await show_national_security_menu(query)
    elif query and query.data.startswith('toggle_ns_'):
        key = query.data.replace('toggle_ns_', '')
        await toggle_national_security_feature(query, key)
    elif query and query.data == 'ns_summary':
        await show_national_security_summary(query)
    elif query and query.data == 'ns_confirm':
        await confirm_national_security(query)
    elif query and query.data == 'ns_action_assassination':
        await ns_pick_assassination_target(query)
    elif query and query.data.startswith('ns_assassinate_'):
        target_uid = query.data.replace('ns_assassinate_', '')
        await ns_confirm_assassination(query, target_uid)
    elif query and query.data.startswith('ns_confirm_assassination_'):
        target_uid = query.data.replace('ns_confirm_assassination_', '')
        await ns_execute_assassination(query, target_uid)
    elif query and query.data == 'ns_recharge_counter':
        await ns_recharge_counter_assassination(query)
    elif query and query.data == 'ns_counter_info':
        await ns_show_counter_info(query)
    elif query and query.data == 'ns_buy_features':
        await ns_buy_features_menu(query)
    elif query and query.data and query.data.startswith('ns_buy_feature_'):
        key = query.data.replace('ns_buy_feature_', '')
        await ns_buy_feature_execute(query, key)
    elif query and query.data == 'private_message':
        from diplomaci import show_private_message_targets
        await show_private_message_targets(query)
    elif query and query.data.startswith('pm_target_'):
        target_uid = query.data.replace('pm_target_', '')
        from diplomaci import confirm_private_message
        await confirm_private_message(query, target_uid)
    elif query and query.data.startswith('pm_confirm_'):
        target_uid = query.data.replace('pm_confirm_', '')
        from diplomaci import start_private_message
        await start_private_message(query, target_uid)
    elif query and query.data == 'ns_espionage_menu':
        await show_espionage_menu(query)
    elif query and query.data == 'ns_spy_alliance':
        await show_alliance_spy_targets(query)
    elif query and query.data == 'ns_spy_country':
        await show_country_spy_targets(query)
    elif query and query.data.startswith('ns_spy_alliance_'):
        alliance_id = query.data.replace('ns_spy_alliance_', '')
        await confirm_alliance_spy(query, alliance_id)
    elif query and query.data.startswith('ns_spy_country_'):
        target_uid = query.data.replace('ns_spy_country_', '')
        await confirm_country_spy(query, target_uid)
    elif query and query.data.startswith('ns_confirm_alliance_spy_'):
        alliance_id = query.data.replace('ns_confirm_alliance_spy_', '')
        await execute_alliance_spy(query, alliance_id)
    elif query and query.data.startswith('ns_confirm_country_spy_'):
        target_uid = query.data.replace('ns_confirm_country_spy_', '')
        await execute_country_spy(query, target_uid)
    elif query and query.data == 'ns_anti_spy':
        await execute_anti_spy(query)
    elif query and query.data == 'ns_intelligence_menu':
        await show_intelligence_menu(query)
    elif query and query.data == 'ns_intel_gather':
        await show_intelligence_categories(query)
    elif query and query.data == 'ns_intel_military':
        await show_intelligence_targets(query, 'military')
    elif query and query.data == 'ns_intel_resources':
        await show_intelligence_targets(query, 'resources')
    elif query and query.data == 'ns_intel_technology':
        await show_intelligence_targets(query, 'technology')
    elif query and query.data.startswith('ns_intel_target_'):
        parts = query.data.replace('ns_intel_target_', '').split('_')
        if len(parts) == 2:
            category, target_uid = parts
            await confirm_intelligence_gathering(query, category, target_uid)
    elif query and query.data.startswith('ns_confirm_intel_'):
        parts = query.data.replace('ns_confirm_intel_', '').split('_')
        if len(parts) == 2:
            category, target_uid = parts
            await execute_intelligence_gathering(query, category, target_uid)
    elif query and query.data == 'ns_anti_intel':
        await execute_anti_intelligence(query)
    elif query and query.data == 'ns_sabotage_menu':
        await show_sabotage_menu(query)
    elif query and query.data == 'ns_sabotage_execute':
        await show_sabotage_targets(query)
    elif query and query.data.startswith('ns_sabotage_target_'):
        target_uid = query.data.replace('ns_sabotage_target_', '')
        await show_sabotage_quantity(query, target_uid)
    elif query and query.data.startswith('ns_sabotage_qty_'):
        parts = query.data.replace('ns_sabotage_qty_', '').split('_')
        if len(parts) == 2:
            quantity, target_uid = parts
            await confirm_sabotage(query, target_uid, int(quantity))
    elif query and query.data.startswith('ns_confirm_sabotage_'):
        parts = query.data.replace('ns_confirm_sabotage_', '').split('_')
        if len(parts) == 2:
            quantity, target_uid = parts
            await execute_sabotage(query, target_uid, int(quantity))
    elif query and query.data == 'ns_anti_sabotage':
        await execute_anti_sabotage(query)
    elif query and query.data == 'ns_noop':
        # No operation - just for display purposes
        await query.answer('این قابلیت فعال است', show_alert=False)
    elif query and query.data == 'admin_security':
        if user_id == ADMIN_ID:
            await admin_panel.show_admin_security(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_ban_user_prompt':
        if user_id == ADMIN_ID:
            await admin_panel.admin_ban_user_prompt(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_disable_countries_menu':
        if user_id == ADMIN_ID:
            await admin_panel.show_admin_disable_countries_menu(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_disable_all_countries':
        if user_id == ADMIN_ID:
            await admin_panel.handle_disable_all_countries(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_disable_select_country':
        if user_id == ADMIN_ID:
            await admin_panel.show_disable_country_picker(query, 0)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data and query.data.startswith('admin_disable_country::'):
        if user_id == ADMIN_ID:
            idx = query.data.split('::', 1)[1]
            await admin_panel.handle_disable_specific_country(query, idx)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data and query.data.startswith('admin_disable_pick_page::'):
        if user_id == ADMIN_ID:
            page = int(query.data.split('::', 1)[1])
            await admin_panel.show_disable_country_picker(query, page)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    
    # Location verification handlers
    elif query and query.data and query.data.startswith('admin_approve_location:'):
        if user_id == ADMIN_ID:
            target_user_id = query.data.split(':', 1)[1]
            await handle_location_approval(query, context, target_user_id)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    
    elif query and query.data and query.data.startswith('admin_reject_location:'):
        if user_id == ADMIN_ID:
            target_user_id = query.data.split(':', 1)[1]
            await handle_location_rejection(query, context, target_user_id)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    
    # پایان هندلر
    elif query and query.data == 'admin_toggle_lock':
        if user_id == ADMIN_ID:
            await admin_panel.handle_toggle_bot_lock(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_activation_codes_menu':
        if user_id == ADMIN_ID:
            await admin_panel.show_admin_activation_codes_menu(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_generate_codes':
        if user_id == ADMIN_ID:
            await admin_panel.handle_generate_activation_codes(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_view_codes':
        if user_id == ADMIN_ID:
            await admin_panel.handle_view_activation_codes(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_search_country_code':
        if user_id == ADMIN_ID:
            await admin_panel.handle_search_country_code(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'admin_delete_old_codes':
        if user_id == ADMIN_ID:
            await admin_panel.handle_delete_old_codes(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'advance_turn':
        if user_id == ADMIN_ID:
            result = await advance_game_turn(context)
            await show_simple_section(query, f'✅ {result}', back_to='main')
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')

    elif query and query.data == 'game_status':
        if user_id == ADMIN_ID:
            status_text = f"وضعیت بازی:\nدور فعلی: {game_data['turn']}\nتاریخ فعلی: {game_data['game_date']}\nآخرین بروزرسانی: {game_data.get('last_turn_time', 'نامشخص')}"
            await show_simple_section(query, status_text, back_to='main')
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'conquered_countries':
        if user_id == ADMIN_ID:
            from battle import show_conquered_countries
            await show_conquered_countries(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'test_reports':
        if user_id == ADMIN_ID:
            from analysis import test_send_reports
            result = await test_send_reports()
            if result:
                await query.answer("✅ تمام گزارش‌ها با موفقیت ارسال شدند!", show_alert=True)
            else:
                await query.answer("❌ خطا در ارسال گزارش‌ها", show_alert=True)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'cancel_un_activation':
        # لغو فعال‌سازی سازمان ملل
        if utils.pending_un_activation == user_id:
            utils.pending_un_activation = None
            utils.save_un_data()
            await query.edit_message_text(
                "❌ <b>فعال‌سازی سازمان ملل لغو شد!</b>\n\n"
                "حالا می‌توانید از منوی اصلی استفاده کنید.",
                parse_mode='HTML'
            )
        else:
            await query.answer("❌ شما در حال فعال‌سازی سازمان ملل نیستید!", show_alert=True)
    elif query and query.data == 'united_nations_access':
        # دسترسی به سازمان ملل برای بازیکن‌های عادی
        from diplomaci import show_united_nations_access_menu
        await show_united_nations_access_menu(query)
    elif query and query.data == 'un_file_complaint':
        # شروع ویزارد شکایت‌نامه سازمان ملل
        from diplomaci import start_un_complaint
        await start_un_complaint(query)
    elif query and query.data == 'un_voting_booth':
        # صندوق رای سازمان ملل
        from diplomaci import show_united_nations_voting_booth
        await show_united_nations_voting_booth(query)
    elif query and query.data == 'diplomacy_menu':
        # بازگشت به منوی دیپلماسی
        from diplomaci import show_diplomacy_menu
        await show_diplomacy_menu(query)
    elif query and query.data == 'covert_ops':
        from diplomaci import show_covert_ops_menu
        await show_covert_ops_menu(query)
    elif query and query.data == 'assassination_pick_country':
        from diplomaci import assassination_pick_country
        await assassination_pick_country(query)
    elif query and query.data.startswith('assassination_country_'):
        country_hash = query.data.replace('assassination_country_', '')
        from diplomaci import assassination_pick_role_from_hash
        await assassination_pick_role_from_hash(query, country_hash)
    elif query and query.data.startswith('assassination_role_'):
        role_key = query.data.replace('assassination_role_', '')
        from diplomaci import assassination_confirm
        await assassination_confirm(query, role_key)
    elif query and query.data.startswith('assassination_do_'):
        role_key = query.data.replace('assassination_do_', '')
        from diplomaci import assassination_execute
        await assassination_execute(query, role_key, context)
    elif query and query.data.startswith('assassination_defend_'):
        from diplomaci import assassination_defend
        await assassination_defend(query)
    elif query and (query.data.startswith('ass_input_') or query.data.startswith('ass_back_') or query.data.startswith('ass_submit_')):
        from diplomaci import assassination_input_handler
        await assassination_input_handler(query)
    elif query and query.data == 'un_view_resolutions':
        # مشاهده قطعنامه‌های سازمان ملل
        await query.answer("📜 این قابلیت به زودی اضافه می‌شود!", show_alert=True)
    # پیش‌نمایش یک قطعنامه برای رای‌گیری (برای همه کاربران)
    elif query and query.data.startswith('un_vote_view_'):
        try:
            number = int(query.data.replace('un_vote_view_', ''))
        except Exception:
            await query.answer('شماره قطعنامه نامعتبر است.', show_alert=True)
            return
        from diplomaci import show_resolution_preview_for_voting
        await show_resolution_preview_for_voting(query, number)
    # رای‌گیری عمومی سازمان ملل (برای همه کاربران آزاد است) — باید قبل از چک کلی un_ باشد
    elif query and (query.data.startswith('un_vote_yes_') or query.data.startswith('un_vote_no_') or query.data.startswith('un_vote_abstain_')):
        from diplomaci import handle_vote_action
        data = query.data
        if data.startswith('un_vote_yes_'):
            number = int(data.replace('un_vote_yes_', ''))
            await handle_vote_action(query, 'yes', number, context)
        elif data.startswith('un_vote_no_'):
            number = int(data.replace('un_vote_no_', ''))
            await handle_vote_action(query, 'no', number, context)
        elif data.startswith('un_vote_abstain_'):
            number = int(data.replace('un_vote_abstain_', ''))
            await handle_vote_action(query, 'abstain', number, context)
    elif query and query.data == 'un_view_sanctions':
        # مشاهده تحریم‌های سازمان ملل
        await query.answer("🚫 این قابلیت به زودی اضافه می‌شود!", show_alert=True)
    elif query and query.data == 'un_view_courts':
        # مشاهده دادگاه‌های سازمان ملل (فقط مشاهده برای کاربران عادی)
        from diplomaci import show_courts_list_for_public
        await show_courts_list_for_public(query)
    elif query and (query.data == 'un_send_president' or query.data.startswith('un_sp_')):
        from diplomaci import handle_send_president_callback
        await handle_send_president_callback(query)

    elif query and query.data == 'un_view_monitoring':
        # مشاهده نظارت سازمان ملل
        await query.answer("👮‍♀️ این قابلیت به زودی اضافه می‌شود!", show_alert=True)
    elif query and query.data == 'un_view_peace_prizes':
        # مشاهده جوایز صلح سازمان ملل
        await query.answer("🏆 این قابلیت به زودی اضافه می‌شود!", show_alert=True)
    
    # مدیریت callback های سازمان ملل
    elif query and (query.data.startswith('un_comp_')):
        # ادامه مراحل ویزارد شکایت‌نامه (برای همه کاربران)
        from diplomaci import handle_un_complaint_callback
        await handle_un_complaint_callback(query)
    elif query and query.data.startswith('un_'):
        # بررسی اینکه آیا کاربر سازمان ملل هست
        if not is_un_user(user_id):
            await query.answer("❌ فقط کاربران سازمان ملل می‌توانند به این بخش دسترسی داشته باشند!", show_alert=True)
            return
        
        # فراخوانی تابع مدیریت سازمان ملل
        from united_nations import handle_un_callback
        await handle_un_callback(query, context)
    elif query and query.data == 'no_action':
        # دکمه بدون عمل (برای نمایش وضعیت رای داده شده)
        try:
            await query.answer('✅')
        except Exception:
            pass

    
    elif query and query.data == 'admin_reset_un':
        if user_id == ADMIN_ID:
            from admin_panel import handle_reset_un
            await handle_reset_un(query)
    elif query and query.data == 'admin_season_reset':
        if user_id == ADMIN_ID:
            from admin_panel import handle_season_reset
            await handle_season_reset(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'reset_bot':
        if user_id == ADMIN_ID:
            from admin_panel import handle_reset_bot
            await handle_reset_bot(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'reset_and_restart':
        if user_id == ADMIN_ID:
            from admin_panel import handle_reset_and_restart
            await handle_reset_and_restart(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'restart_bot':
        if user_id == ADMIN_ID:
            from admin_panel import handle_restart_bot
            await handle_restart_bot(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'reset_and_restart':
        if user_id == ADMIN_ID:
            from admin_panel import handle_reset_and_restart
            await handle_reset_and_restart(query)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data.startswith('free_country_'):
        if user_id == ADMIN_ID:
            target_id = query.data.replace('free_country_', '')
            from battle import free_conquered_country
            await free_conquered_country(query, target_id)
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    elif query and query.data == 'back_to_main':
        activated = get_user_activated(user_id)
        reply_markup = get_start_menu(activated)
        await query.edit_message_text('به بازی استراتژی خوش آمدید! لطفاً یک گزینه را انتخاب کنید:', reply_markup=reply_markup)
    
    # ==================== SHOP CALLBACK HANDLERS ====================
    elif query and query.data == 'shop_menu':
        await show_shop_menu(query)
    elif query and query.data == 'shop_credits':
        await show_credits_menu(query)
    elif query and query.data == 'shop_military_packages':
        await show_military_packages_menu(query)
    
    # Military package handlers
    elif query and query.data.startswith('military_package_'):
        package_key = query.data.replace('military_package_', '')
        await show_military_package_details(query, package_key)
    
    elif query and query.data.startswith('confirm_military_purchase_'):
        package_key = query.data.replace('confirm_military_purchase_', '')
        await execute_military_package_purchase(query, package_key)
    
    elif query and query.data.startswith('request_military_approval_'):
        package_key = query.data.replace('request_military_approval_', '')
        await request_military_package_approval(query, package_key)
    
    # Admin approval handlers
    elif query and query.data.startswith('admin_approve_military_'):
        if str(query.from_user.id) == ADMIN_ID:
            parts = query.data.replace('admin_approve_military_', '').split('_')
            if len(parts) >= 2:
                user_id = parts[0]
                package_key = '_'.join(parts[1:])
                await handle_admin_military_approval(query, user_id, package_key, True)
        else:
            await query.answer("❌ شما دسترسی ادمین ندارید!", show_alert=True)
    
    elif query and query.data.startswith('admin_reject_military_'):
        if str(query.from_user.id) == ADMIN_ID:
            parts = query.data.replace('admin_reject_military_', '').split('_')
            if len(parts) >= 2:
                user_id = parts[0]
                package_key = '_'.join(parts[1:])
                await handle_admin_military_approval(query, user_id, package_key, False)
        else:
            await query.answer("❌ شما دسترسی ادمین ندارید!", show_alert=True)
    elif query and query.data == 'shop_economy':
        await show_economic_packages_menu(query)
    
    # Resource package handlers
    elif query and query.data == 'shop_resource_packages':
        await show_resource_packages_menu(query)
    
    elif query and query.data.startswith('resource_package_'):
        package_key = query.data.replace('resource_package_', '')
        await show_resource_package_details(query, package_key)
    
    elif query and query.data.startswith('confirm_resource_purchase_'):
        package_key = query.data.replace('confirm_resource_purchase_', '')
        await execute_resource_package_purchase(query, package_key)
    
    elif query and query.data.startswith('request_resource_approval_'):
        package_key = query.data.replace('request_resource_approval_', '')
        await request_resource_package_approval(query, package_key)
    
    elif query and query.data.startswith('approve_resource_'):
        if str(query.from_user.id) == ADMIN_ID:
            parts = query.data.replace('approve_resource_', '').split('_')
            user_id = parts[0]
            package_key = parts[1]
            await handle_admin_resource_approval(query, user_id, package_key, True)
        else:
            await query.answer("❌ شما دسترسی ادمین ندارید!", show_alert=True)
    
    elif query and query.data.startswith('reject_resource_'):
        if str(query.from_user.id) == ADMIN_ID:
            parts = query.data.replace('reject_resource_', '').split('_')
            user_id = parts[0]
            package_key = parts[1]
            await handle_admin_resource_approval(query, user_id, package_key, False)
        else:
            await query.answer("❌ شما دسترسی ادمین ندارید!", show_alert=True)
    
    # Economic package handlers
    elif query and query.data.startswith('economic_package_'):
        package_key = query.data.replace('economic_package_', '')
        await show_economic_package_details(query, package_key)
    
    elif query and query.data.startswith('confirm_economic_purchase_'):
        package_key = query.data.replace('confirm_economic_purchase_', '')
        await execute_economic_package_purchase(query, package_key)
    
    elif query and query.data.startswith('request_economic_approval_'):
        package_key = query.data.replace('request_economic_approval_', '')
        await request_economic_package_approval(query, package_key)
    
    # Admin economic approval handlers
    elif query and query.data.startswith('admin_approve_economic_'):
        if str(query.from_user.id) == ADMIN_ID:
            parts = query.data.replace('admin_approve_economic_', '').split('_')
            if len(parts) >= 2:
                user_id = parts[0]
                package_key = '_'.join(parts[1:])
                await handle_admin_economic_approval(query, user_id, package_key, True)
        else:
            await query.answer("❌ شما دسترسی ادمین ندارید!", show_alert=True)
    
    elif query and query.data.startswith('admin_reject_economic_'):
        if str(query.from_user.id) == ADMIN_ID:
            parts = query.data.replace('admin_reject_economic_', '').split('_')
            if len(parts) >= 2:
                user_id = parts[0]
                package_key = '_'.join(parts[1:])
                await handle_admin_economic_approval(query, user_id, package_key, False)
        else:
            await query.answer("❌ شما دسترسی ادمین ندارید!", show_alert=True)
    elif query and query.data == 'shop_diplomatic':
        await show_diplomatic_menu(query)
    elif query and query.data == 'shop_special':
        await show_special_menu(query)
    elif query and query.data == 'shop_inventory':
        await show_inventory_menu(query)
    
    # Credit purchases (paid)
    elif query and query.data == 'buy_credits_100':
        await show_payment_info(query, 100, 20)
    elif query and query.data == 'buy_credits_250':
        await show_payment_info(query, 250, 40)
    elif query and query.data == 'buy_credits_500':
        await show_payment_info(query, 500, 100)
    elif query and query.data == 'buy_credits_1000':
        await show_payment_info(query, 1000, 200)
    elif query and query.data == 'buy_credits_10000':
        await show_payment_info(query, 10000, 1499)
    
    # Payment confirmation
    elif query and query.data.startswith('confirm_payment_'):
        print(f"[DEBUG] Calling handle_payment_confirmation with object type: {type(query)}")
        await handle_payment_confirmation(query)
    elif query and query.data == 'cancel_payment':
        await show_credits_menu(query)
    
    # Admin payment approval
    elif query and query.data.startswith('approve_payment_'):
        await handle_admin_payment_approval(query)
    elif query and query.data.startswith('reject_payment_'):
        await handle_admin_payment_rejection(query)
    
    # Old military purchases removed - replaced with new military packages system
    
    # Old economic purchases removed - replaced with new economic packages system
    
    # Diplomatic purchases
    elif query and query.data == 'buy_diplomatic_sanction':
        await handle_purchase_confirmation(query, 'diplomatic_sanction', 800)
    elif query and query.data == 'buy_diplomatic_peace':
        await handle_purchase_confirmation(query, 'diplomatic_peace', 900)
    
    # Special purchases
    elif query and query.data == 'buy_special_guard':
        await handle_purchase_confirmation(query, 'special_guard', 300)
    elif query and query.data == 'buy_special_media':
        await handle_purchase_confirmation(query, 'special_media', 200)
    
    # Purchase confirmations
    elif query and query.data.startswith('confirm_purchase_'):
        data_parts = query.data.replace('confirm_purchase_', '').split('_')
        if len(data_parts) >= 2:
            item_key = '_'.join(data_parts[:-1])
            cost = int(data_parts[-1])
            await execute_purchase(query, item_key, cost)
    
    elif query and query.data == 'cancel_purchase':
        await show_shop_menu(query)
    elif query and query.data == 'back_to_game_menu':
        await show_game_menu(query)
    elif query and query.data and query.data.startswith('build_section_'):
        section_key = query.data.replace('build_section_', '')
        await show_build_section(query, section_key)
    elif query and query.data and query.data.startswith('build_item_'):
        item_key = query.data.replace('build_item_', '')
        await show_build_item(query, item_key)
    elif query and query.data and query.data in [
        'country_status', 'strategy', 'diplomacy', 'trade', 'population', 'space', 'technology']:
        if query.data == 'country_status':
            await show_country_status(query)
        elif query.data == 'strategy':
            await show_strategy_menu(query)
        elif query.data == 'trade':
            from economy import show_trade_menu
            await show_trade_menu(query)
        elif query.data == 'diplomacy':
            from diplomaci import show_diplomacy_menu
            await show_diplomacy_menu(query)
        elif query.data == 'population':
            from jame import show_population_status
            await show_population_status(query)
        elif query.data == 'my_country_population':
            from jame import show_my_country_population
            await show_my_country_population(query)
    elif query and query.data in ('deport_immigrants', 'collect_tax', 'tax_waiting', 'my_country_population'):
        try:
            from jame import handle_population_callbacks
            await handle_population_callbacks(query)
        except Exception as e:
            print(f"population callbacks error: {e}")
    
    # New Refugee System Handlers
    elif query and query.data and query.data.startswith('new_refugee_accept_'):
        try:
            request_id = query.data.replace('new_refugee_accept_', '')
            print(f"[DEBUG][REFUGEE] request_id extracted: {request_id}")
            if not request_id:
                print("[DEBUG][REFUGEE] request_id is empty!")
                await query.answer('❌ شناسه درخواست نامعتبر است.', show_alert=True)
                return
            print(f"[DEBUG][REFUGEE] Calling handle_refugee_acceptance with request_id: {request_id}")
            await handle_refugee_acceptance(request_id, query, context)
        except Exception as e:
            print(f"[ERROR][REFUGEE] خطا در پردازش پذیرش پناهندگی: {e}")
            import traceback
            traceback.print_exc()
            try:
                await query.answer('❌ خطا در پردازش درخواست.', show_alert=True)
            except:
                pass
    
    elif query and query.data and query.data.startswith('new_refugee_reject_'):
        try:
            request_id = query.data.replace('new_refugee_reject_', '')
            if not request_id:
                await query.answer('❌ شناسه درخواست نامعتبر است.', show_alert=True)
                return
            await handle_refugee_rejection(request_id, query, context)
        except Exception as e:
            print(f"خطا در پردازش رد پناهندگی: {e}")
            import traceback
            traceback.print_exc()
            try:
                await query.answer('❌ خطا در پردازش درخواست.', show_alert=True)
            except:
                pass
    elif query and query.data == 'admin_debug':
        from debug_tools import show_debug_menu
        await show_debug_menu(query)
    elif query and query.data == 'dbg_summary':
        from debug_tools import dbg_summary
        await dbg_summary(query)
    elif query and query.data == 'dbg_ensure_two':
        from debug_tools import dbg_ensure_two
        await dbg_ensure_two(query)
    elif query and query.data == 'dbg_make_war':
        from debug_tools import dbg_make_war
        await dbg_make_war(query, user_id)
    elif query and query.data == 'dbg_revolution_100':
        from debug_tools import dbg_revolution_100
        await dbg_revolution_100(query, user_id)
    elif query and query.data == 'dbg_kill_general':
        from debug_tools import dbg_toggle_official
        await dbg_toggle_official(query, user_id, 'general', False)
    elif query and query.data == 'dbg_kill_minister':
        from debug_tools import dbg_toggle_official
        await dbg_toggle_official(query, user_id, 'minister', False)
    elif query and query.data == 'dbg_revive_general':
        from debug_tools import dbg_toggle_official
        await dbg_toggle_official(query, user_id, 'general', True)
    elif query and query.data == 'dbg_revive_minister':
        from debug_tools import dbg_toggle_official
        await dbg_toggle_official(query, user_id, 'minister', True)
    elif query and query.data == 'tutorial_menu':
        from tutorial import show_tutorial_menu
        await show_tutorial_menu(query)
    elif query and query.data.startswith('tut_'):
        from tutorial import show_tutorial_section
        await show_tutorial_section(query, query.data)


    elif query.data == 'collect_tax':
        print(f"[DEBUG] collect_tax callback received for user_id: {user_id}")
        from jame import collect_tax
        success, message = collect_tax(user_id)
        print(f"[DEBUG] collect_tax result: success={success}, message={message}")
        if success:
            await query.answer(message, show_alert=True)
            # بازگشت به وضعیت جمعیت برای نمایش اطلاعات به‌روز شده
            from jame import show_population_status
            await show_population_status(query)
        else:
            await query.answer(message, show_alert=True)
    elif query.data == 'tax_waiting':
        current_turn = utils.game_data['turn']
        last_tax_collection = utils.users[user_id].get('last_tax_collection', 0)
        remaining_turns = 2 - (current_turn - last_tax_collection)
        await query.answer(f"شما باید {remaining_turns} دور دیگر صبر کنید تا بتوانید مالیات دریافت کنید.", show_alert=True)
    elif query.data == 'suppress_revolution':
        from utils import suppress_revolution, check_revolution_status, handle_country_collapse
        success, message = suppress_revolution(user_id)
        await query.answer(message, show_alert=True)
        
        # بررسی وضعیت انقلاب
        is_collapsed, collapse_message = check_revolution_status(user_id)
        if is_collapsed:
            await handle_country_collapse(user_id)
            # نمایش منوی انتخاب (فرار یا محاکمه)
            keyboard = [
                [InlineKeyboardButton('🏃‍♂️ فرار از کشور', callback_data='escape_country')],
                [InlineKeyboardButton('⚖️ ماندن و محاکمه', callback_data='start_trial')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"🔥 <b>کشور سقوط کرد!</b>\n\n"
                f"کشور شما به دلیل انقلاب مردم سقوط کرده است.\n\n"
                f"شما دو گزینه دارید:\n"
                f"1️⃣ فرار از کشور (کشور غیرفعال می‌شود)\n"
                f"2️⃣ ماندن و محاکمه شدن (5 دقیقه فرصت دفاع)",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            # بازگشت به وضعیت جمعیت برای نمایش اطلاعات به‌روز شده
            from jame import show_population_status
            await show_population_status(query)
    elif query.data == 'escape_country':
        from utils import escape_from_country
        success, message = await escape_from_country(user_id)
        await query.edit_message_text(
            f"{message}\n\n"
            f"🔙 برای شروع مجدد، از منوی اصلی استفاده کنید.",
            parse_mode='HTML'
        )
    elif query.data == 'start_trial':
        from utils import start_trial, get_trial_question
        success, message = start_trial(user_id)
        
        if success:
            # نمایش سؤال اول
            question, keyboard = get_trial_question(user_id)
            if question:
                # تبدیل ساختار ساده به دکمه‌های تلگرام در سمت ربات
                try:
                    buttons = [[InlineKeyboardButton(btn['text'], callback_data=btn['callback_data']) for btn in row] for row in keyboard]
                except Exception:
                    buttons = []
                reply_markup = InlineKeyboardMarkup(buttons)
                await query.edit_message_text(
                    f"⚖️ <b>محاکمه شروع شد!</b>\n\n"
                    f"{message}\n\n"
                    f"📝 <b>سؤال 1 از 3:</b>\n"
                    f"{question}\n\n"
                    f"🔽 یکی از گزینه‌های زیر را انتخاب کنید:",
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
            else:
                await query.edit_message_text(
                    f"❌ خطا در شروع محاکمه",
                    parse_mode='HTML'
                )
        else:
            await query.edit_message_text(
                f"❌ {message}",
                parse_mode='HTML'
            )
    elif query.data.startswith('trial_answer_'):
        from utils import process_trial_answer, get_trial_question
        answer_type = query.data.replace('trial_answer_', '')
        
        success, message = await process_trial_answer(user_id, answer_type)
        
        if success:
            if "سؤال بعدی" in message:
                # نمایش سؤال بعدی
                question, keyboard = get_trial_question(user_id)
                if question:
                    try:
                        buttons = [[InlineKeyboardButton(btn['text'], callback_data=btn['callback_data']) for btn in row] for row in keyboard]
                    except Exception:
                        buttons = []
                    reply_markup = InlineKeyboardMarkup(buttons)
                    current_question = utils.users[user_id].get('trial_current_question', 1)
                    await query.edit_message_text(
                        f"✅ {message}\n\n"
                        f"📝 <b>سؤال {current_question} از 3:</b>\n"
                        f"{question}\n\n"
                        f"🔽 یکی از گزینه‌های زیر را انتخاب کنید:",
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                else:
                    await query.edit_message_text(
                        f"❌ خطا در نمایش سؤال بعدی",
                        parse_mode='HTML'
                    )
            else:
                # محاکمه تمام شده
                await query.edit_message_text(
                    f"{message}\n\n"
                    f"🔙 برای شروع مجدد، از منوی اصلی استفاده کنید.",
                    parse_mode='HTML'
                )
        else:
            await query.answer(message, show_alert=True)
    elif query.data == 'colonies_menu':
        await show_colonies_menu(query)
    elif query.data == 'view_colonies_details':
        await show_colonies_details(query)
    elif query.data == 'grant_independence':
        await show_grant_independence_menu(query)
    elif query.data == 'military_status':
        await show_military_status(query)
    elif query.data == 'global_military_ranking':
        from analysis import show_global_military_ranking
        await show_global_military_ranking(query)
    elif query.data == 'global_resources_ranking':
        from analysis import show_global_resources_ranking
        await show_global_resources_ranking(query)
    elif query.data.startswith('grant_independence_'):
        target_id = query.data.replace('grant_independence_', '')
        await execute_grant_independence(query, target_id)
    elif query.data.startswith('ceasefire_accept_'):
        war_key = query.data.replace('ceasefire_accept_', '')
        await handle_ceasefire_response(query, war_key, 'accept')
    elif query.data.startswith('ceasefire_reject_'):
        war_key = query.data.replace('ceasefire_reject_', '')
        await handle_ceasefire_response(query, war_key, 'reject')
    elif query.data == 'international_bank':
        await show_international_bank_menu(query)
    elif query.data == 'loans_menu':
        from bank import show_loans_menu
        await show_loans_menu(query)
    elif query.data == 'independence_loan':
        await show_independence_loan_info(query)
    elif query.data == 'development_loan':
        await show_development_loan_info(query)
    elif query.data == 'emergency_loan':
        await show_emergency_loan_info(query)
    elif query.data == 'secret_loan':
        from bank import show_secret_loan_info
        await show_secret_loan_info(query)
    elif query.data == 'my_loans':
        await show_my_loans(query)
    elif query.data == 'overdue_debts':
        await show_overdue_debts_menu(query)
    elif query.data == 'chat_with_morgan':
        await show_chat_with_morgan(query)
    elif query.data == 'pay_installment':
        await pay_installment(query)
    elif query.data == 'pay_full_debt':
        await pay_full_debt(query)
    elif query.data == 'request_installment_loan':
        await request_installment_loan(query)
    elif query.data == 'pay_loan_early':
        from bank import pay_loan_early # Re-import to ensure it's available
        await pay_loan_early(query)
    elif query.data == 'bank_account':
        await show_bank_account_menu(query)
    elif query.data == 'transfer_money':
        await show_transfer_money_menu(query)
    elif query.data == 'start_transfer':
        await start_transfer_process(query)
    elif query.data == 'confirm_transfer':
        await confirm_transfer(query)
    elif query.data == 'cancel_transfer':
        await cancel_transfer(query)
    elif query.data == 'transaction_history':
        await show_transaction_history(query)
    elif query.data == 'deposit_to_account':
        await show_deposit_menu(query)
    elif query.data == 'withdraw_from_account':
        await show_withdraw_menu(query)
    elif query.data == 'test_channel':
        from bank import test_channel_sending
        success = await test_channel_sending()
        if success:
            await query.edit_message_text('✅ پیام تست با موفقیت به کانال ارسال شد!')
        else:
            await query.edit_message_text('❌ خطا در ارسال پیام تست به کانال!')
    elif query.data == 'request_independence_loan':
        await request_independence_loan(query)
    elif query.data == 'request_development_loan':
        await request_development_loan(query)
    elif query.data == 'request_emergency_loan':
        await request_emergency_loan(query)
    elif query.data == 'request_secret_loan':
        from bank import request_secret_loan
        await request_secret_loan(query)
    elif query.data == 'pay_loan_early':
        from bank import pay_loan_early
        await pay_loan_early(query)
    elif query.data == 'build':
        await show_build_menu(query, user_id)
    elif query and query.data == 'production':
        await show_production_menu(query, user_id)
    elif query and query.data == 'military_production':
        await show_military_production_menu(query, user_id)
    elif query and query.data == 'statement':
        await start_statement(query, user_id)
    elif query and query.data == 'show_prices':
        await show_prices_menu(query)
    elif query and query.data == 'back_to_trade':
        from economy import show_trade_menu
        await show_trade_menu(query)
    # ==================== بازار سهام خارجی ====================
    elif query and query.data == 'foreign_exchange_market':
        from economy import show_foreign_exchange_market
        try:
            await show_loading_animation(chat_id=query.message.chat.id, context=context, duration_seconds=2)
        except Exception:
            pass
        await show_foreign_exchange_market(query)
    elif query and query.data == 'stock_wallet':
        from economy import show_stock_wallet
        await show_stock_wallet(query)
    elif query and query.data == 'company_stocks':
        from economy import show_company_stocks
        try:
            await show_loading_animation(chat_id=query.message.chat.id, context=context, duration_seconds=2)
        except Exception:
            pass
        await show_company_stocks(query, 0)
    elif query and query.data.startswith('company_stocks_'):
        try:
            page = int(query.data.replace('company_stocks_', ''))
        except Exception:
            page = 0
        from economy import show_company_stocks
        try:
            await show_loading_animation(chat_id=query.message.chat.id, context=context, duration_seconds=1)
        except Exception:
            pass
        await show_company_stocks(query, page)
    elif query and query.data.startswith('stock_details_'):
        symbol = query.data.replace('stock_details_', '')
        try:
            await show_loading_animation(chat_id=query.message.chat.id, context=context, duration_seconds=2)
        except Exception:
            pass
        from economy import show_stock_details
        await show_stock_details(query, symbol)
    elif query and query.data.startswith('buy_stock_'):
        symbol = query.data.replace('buy_stock_', '')
        try:
            await show_loading_animation(chat_id=query.message.chat.id, context=context, duration_seconds=2)
        except Exception:
            pass
        from economy import show_buy_stock_menu
        await show_buy_stock_menu(query, symbol)
    elif query and query.data.startswith('sell_stock_'):
        symbol = query.data.replace('sell_stock_', '')
        try:
            await show_loading_animation(chat_id=query.message.chat.id, context=context, duration_seconds=2)
        except Exception:
            pass
        from economy import show_sell_stock_menu
        await show_sell_stock_menu(query, symbol)
    elif query.data == 'other_diplomacy':
        await show_simple_section(query, 'سایر بخش‌های دیپلماسی به زودی فعال می‌شود.', back_to='game_menu')
    elif query.data in ['buy_sell', 'international_market']:
        await show_simple_section(query, 'این بخش به زودی فعال می‌شود.', back_to='game_menu')
    # ==================== سیستم تحریم ====================
    elif query and query.data == 'sanctions_menu':
        from diplomaci import show_sanctions_menu
        await show_sanctions_menu(query)
    elif query and query.data == 'sanction_countries':
        from diplomaci import show_sanction_countries_menu
        await show_sanction_countries_menu(query)
    elif query and query.data.startswith('sanction_target_'):
        from diplomaci import show_sanction_confirmation
        target_country = query.data.replace('sanction_target_', '')
        await show_sanction_confirmation(query, target_country)
    elif query and query.data.startswith('sanction_confirm_'):
        from diplomaci import execute_sanction
        target_country = query.data.replace('sanction_confirm_', '')
        await execute_sanction(query, target_country)
    elif query and query.data == 'remove_sanctions':
        from diplomaci import show_remove_sanctions_menu
        await show_remove_sanctions_menu(query)
    elif query and query.data.startswith('remove_sanction_'):
        from diplomaci import remove_sanction
        target_country = query.data.replace('remove_sanction_', '')
        await remove_sanction(query, target_country)
    elif query.data.startswith('produce_confirm_'):
        item_key = query.data.replace('produce_confirm_', '')
        user = utils.users.get(str(user_id), {})
        economy = user.get('economy', {})
        found = False
        for section, items in economy.items():
            if isinstance(items, list) and item_key in items:
                found = True
        if not found:
            await show_simple_section(query, 'شما این سازه را ندارید.', back_to='game_menu')
            return
        recipe = PRODUCTION_RECIPES.get(item_key)
        if not recipe:
            await show_simple_section(query, 'فرمول تولید یافت نشد.', back_to='game_menu')
            return
        inputs = recipe['inputs']
        output = recipe['output']
        amount = recipe['amount']
        resources = user.get('resources', {})
        # نام‌های فارسی منابع
        resource_names = {
            'steel': 'فولاد', 'oil': 'نفت', 'electricity': 'برق', 'electronics': 'الکترونیک',
            'iron': 'آهن', 'aluminum': 'آلومینیوم', 'titanium': 'تیتانیوم', 'copper': 'مس',
            'gold': 'طلا', 'diamond': 'الماس', 'uranium_ore': 'سنگ اورانیوم', 'yellowcake': 'کیک زرد',
            'space_parts': 'قطعات فضایی', 'centrifuge': 'سانتریفیوژ', 'uranium': 'اورانیوم',
            'gas': 'گاز', 'pride_cars': 'پراید', 'benz_cars': 'بنز'
        }
        for res, val in inputs.items():
            if resources.get(res, 0) < val:
                res_name = resource_names.get(res, res)
                await show_simple_section(query, f'منبع کافی برای تولید ندارید: {res_name}', back_to='production_menu')
                return
        for res, val in inputs.items():
            resources[res] -= val
        resources[output] = resources.get(output, 0) + amount
        save_users()
        output_name = resource_names.get(output, output)
        await show_simple_section(query, f'✅ تولید {amount} واحد {output_name} با موفقیت انجام شد!', back_to='production_menu')
    elif query.data.startswith('military_production_'):
        item_key = query.data.replace('military_production_', '')
        await show_military_production_item(query, user_id, item_key)
    elif query.data.startswith('military_produce_confirm_'):
        item_key = query.data.replace('military_produce_confirm_', '')
        await ask_military_production_amount(query, user_id, item_key)
    elif query.data.startswith('military_produce_final_'):
        # استخراج item_key و amount از callback_data
        parts = query.data.replace('military_produce_final_', '').rsplit('_', 1)
        if len(parts) == 2:
            item_key = parts[0]
            try:
                amount = int(parts[1])
                await confirm_military_production(query, user_id, item_key, amount)
            except ValueError:
                await query.edit_message_text('❌ خطا در پردازش اطلاعات.')
        else:
            await query.edit_message_text('❌ خطا در پردازش اطلاعات.')
    elif query.data == 'build_structures':
        await show_build_structures_menu(query)
    elif query.data == 'production_menu':
        await show_production_menu(query, user_id)
    elif query.data == 'back_to_build':
        await show_build_menu(query, user_id)
    elif query.data.startswith('build_confirm_'):
        item_key = query.data.replace('build_confirm_', '')
        # پیدا کردن اطلاعات سازه
        found = False
        section_key = None
        item_info = None
        for section_key, section in BUILDINGS.items():
            for item in section['items']:
                if item['key'] == item_key:
                    found = True
                    item_info = item
                    break
            if found:
                break
        if not found:
            await show_simple_section(query, 'سازه مورد نظر یافت نشد.', back_to='build')
            return
        # بررسی پول کاربر
        user = utils.users.get(str(user_id), {})
        resources = user.get('resources', {})
        cash = resources.get('cash', 0)
        # محدودیت تعداد سازه
        economy = user.setdefault('economy', {})
        section_list = economy.setdefault(section_key, [])
        is_production = item_key in PRODUCTION_RECIPES
        max_count = 1 if is_production else 5
        if section_list.count(item_key) >= max_count:
            await show_simple_section(query, '🚫 حداکثر تعداد این سازه را ساخته‌اید.', back_to='build')
            return
        # تبدیل قیمت به عدد
        price_str = item_info['price'].replace('m', '000000').replace('M', '000000').replace(',', '').strip()
        try:
            price = int(price_str)
        except Exception:
            await show_simple_section(query, 'قیمت سازه نامعتبر است.', back_to='build')
            return
        if cash < price:
            await show_simple_section(query, 'موجودی نقد شما برای ساخت این سازه کافی نیست.', back_to='build')
            return
        # کم کردن پول و اضافه کردن سازه
        resources['cash'] = cash - price
        # اضافه کردن سازه به اقتصاد کاربر
        if item_key not in section_list or section_list.count(item_key) < max_count:
            section_list.append(item_key)
        # اطمینان از ثبت در users قبل از ذخیره
        utils.users[str(user_id)] = user
        print(f"[DEBUG] بعد از ساخت معدن - اقتصاد کاربر: {economy}")
        print(f"[DEBUG] لیست معادن: {section_list}")
        print(f"[DEBUG] قبل از save_users - utils.users[{user_id}]: {utils.users.get(str(user_id), {}).get('economy', {})}")
        save_users()
        await show_simple_section(query, f'✅ سازه {item_info["name"]} با موفقیت ساخته شد!', back_to='build')
    elif query.data.startswith('production_item_'):
        item_key = query.data.replace('production_item_', '')
        await show_production_item(query, user_id, item_key)
    elif query.data == 'sell_to_player':
        await sell_to_player_start(query, user_id)
    elif query.data.startswith('sell_choose_'):
        resource = query.data.replace('sell_choose_', '')
        await sell_to_player_ask_amount(query, user_id, resource)
    if query.data == 'manage_sell_ads':
        await manage_sell_ads_menu(query, user_id)
    elif query.data.startswith('delete_sell_ad_'):
        ad_id = query.data.replace('delete_sell_ad_', '')
        await delete_sell_ad(query, user_id, ad_id)
    if query.data == 'buy_from_player':
        await buy_from_player_start(query, user_id)

    elif query.data.startswith('buy_choose_'):
        resource = query.data.replace('buy_choose_', '')
        await buy_from_player_ads(query, user_id, resource)
    elif query.data.startswith('buy_ad_'):
        ad_id = query.data.replace('buy_ad_', '')
        await buy_from_player_confirm(query, user_id, ad_id, context)    
    elif query.data.startswith('escort_yes_'):
        ad_id = query.data.replace('escort_yes_', '')
        from economy import process_escort_yes
        await process_escort_yes(query, user_id, ad_id, context)
    elif query.data.startswith('escort_no_'):
        ad_id = query.data.replace('escort_no_', '')
        from economy import process_escort_no
        await process_escort_no(query, user_id, ad_id, context)    
        
    elif query.data == 'buy_from_market':
        await buy_from_market_start(query, user_id)
    elif query.data == 'sell_to_market':
        await sell_to_market_start(query, user_id)
    elif query.data.startswith('buy_market_choose_'):
        resource = query.data.replace('buy_market_choose_', '')
        await buy_market_show_inventory(query, user_id, resource)
    elif query.data.startswith('sell_market_choose_'):
        resource = query.data.replace('sell_market_choose_', '')
        await sell_market_ask_amount(query, user_id, resource)
    elif query.data == 'strategy':
        # بررسی دسترسی نظامی
        access_allowed, error_message = check_military_access(user_id)
        if not access_allowed:
            await query.edit_message_text(error_message)
            return
        await show_strategy_menu(query)
    elif query.data == 'military_status':
        await show_military_status(query)
    elif query.data == 'air_attack':
        try:
            # بررسی دسترسی نظامی
            access_allowed, error_message = check_military_access(user_id)
            if not access_allowed:
                await query.edit_message_text(error_message)
                return
            await show_air_attackable_countries(query)
        except Exception as e:
            print(f"[ERROR][air_attack] {e}")
            try:
                await query.edit_message_text('❌ خطا در باز کردن حمله هوایی. دوباره تلاش کنید.')
            except Exception:
                pass
    elif query.data == 'naval_attack':
        try:
            # دکمه همیشه باز شود؛ فیلترها در لیست کشورها اعمال می‌شوند
            await show_naval_attackable_countries(query)
        except Exception as e:
            print(f"[ERROR][naval_attack] {e}")
            try:
                await query.edit_message_text('❌ خطا در باز کردن حمله دریایی. دوباره تلاش کنید.')
            except Exception:
                pass
    elif query.data == 'confirm_naval_attack':
        # تایید حمله دریایی و شروع سیستم جدید دو مرحله‌ای
        from battle import pending_naval_attack, start_naval_battle_custom
        data = pending_naval_attack.get(user_id)
        if not data or data.get('step') != 'confirm':
            await query.answer('درخواستی برای تایید یافت نشد.', show_alert=True)
            return
        target_id = data.get('target_id')
        await query.edit_message_text('✅ حمله دریایی تایید شد. زمان‌بندی انجام می‌شود...')
        await start_naval_battle_custom(user_id, context, target_id)
    elif query.data == 'naval_attack_locked':
        try:
            u = utils.users.get(user_id, {})
            country = u.get('country', '')
            extra = bool(u.get('extra_sea_access'))
            try:
                from utils import has_sea_border
                nat = bool(has_sea_border(country))
            except Exception:
                nat = country in SEA_BORDER_COUNTRIES
            print(f"[DEBUG][naval_locked] user={user_id} country='{country}' native_sea={nat} extra_sea={extra}")
        except Exception:
            pass
        await query.answer("کشور شما مرز دریایی ندارد!", show_alert=True)
    elif query.data == 'cancel_naval_attack':
        # لغو حمله دریایی + بازپرداخت در صورت کسر قبلی
        try:
            import utils as _u
            _pna = _u.pending_naval_attack
            data = _pna.get(user_id)
            if not data:
                await query.edit_message_text("✅ چیزی برای لغو یافت نشد.")
                return
            forces = data.get('forces', {}) or {}
            if data.get('already_deducted') and isinstance(forces, dict):
                for key, amount in forces.items():
                    try:
                        amt = int(amount)
                    except Exception:
                        amt = 0
                    if amt > 0:
                        _u.users[user_id]['resources'][key] = int(_u.users[user_id]['resources'].get(key, 0)) + amt
                _u.save_users()
            # پاک کردن ذخیره موقت تایید
            try:
                from utils import naval_attack_saves, save_naval_attack_saves
                if user_id in naval_attack_saves:
                    naval_attack_saves.pop(user_id, None)
                    save_naval_attack_saves()
            except Exception:
                pass
            _pna.pop(user_id, None)
            await query.edit_message_text("✅ حمله دریایی لغو شد و نیروهای رزرو شده بازگردانده شد.")
        except Exception as e:
            print(f"[ERROR][cancel_naval_attack] {e}")
            try:
                await query.edit_message_text("❌ خطا در لغو حمله دریایی. دوباره تلاش کنید.")
            except Exception:
                pass
    elif query.data == 'cancel_ground_attack':
        # لغو حمله زمینی
        if user_id in pending_ground_attack:
            del pending_ground_attack[user_id]
        await query.edit_message_text("✅ حمله زمینی لغو شد!\n\nحالا می‌توانید نیرو تولید کنید یا کارهای دیگر انجام دهید.")
    elif query.data.startswith('naval_attack_'):
        target_id = query.data.replace('naval_attack_', '')
        await show_naval_forces_inventory(query, target_id)
    elif query.data == 'declare_war':
        # بررسی دسترسی نظامی
        access_allowed, error_message = check_military_access(user_id)
        if not access_allowed:
            await query.edit_message_text(error_message)
            return
        from battle import show_countries_for_war_declaration
        await show_countries_for_war_declaration(query)
    elif query.data == 'peace_menu':
        await show_peace_menu(query)
    elif query.data.startswith('peace_request_'):
        country = query.data.replace('peace_request_', '')
        await handle_peace_request(query, user_id, country, context)
    elif query.data.startswith('accept_peace_'):
        from_id = query.data.replace('accept_peace_', '')
        await handle_accept_peace(query, user_id, from_id, context)
    elif query.data.startswith('declare_war_'):
        target_country = query.data.replace('declare_war_', '')
        await confirm_war_declaration(query, target_country)
    # ===== Special Packages: purchase details and inventory =====
    elif query.data == 'shop_special_inventory':
        await show_special_inventory(query)
    elif query.data.startswith('special_pkg_'):
        await show_special_package_details(query, query.data.replace('special_pkg_', ''))
    elif query.data.startswith('confirm_buy_special_'):
        payload = query.data.replace('confirm_buy_special_', '')
        # key may contain underscores; split from right to extract price
        key, price_str = payload.rsplit('_', 1)
        price = int(price_str)
        await execute_special_purchase(query, key, price)
    elif query.data.startswith('activate_special_'):
        pkg_id = query.data.replace('activate_special_', '')
        await activate_special_package(query, pkg_id)
    elif query.data.startswith('confirm_war_'):
        target_country = query.data.replace('confirm_war_', '')
        await execute_war_declaration(query, target_country)
    elif query.data.startswith('air_target_'):
        target_country = query.data.replace('air_target_', '')
        from analysis import generate_air_attack_analysis
        user_id = str(query.from_user.id)
        # Prevent counter-attack if target currently has an active attack against this user
        try:
            user_country = utils.users.get(user_id, {}).get('country')
            blocked = False
            for wid, w in utils.war_declarations.items():
                if w.get('status') == 'active' and w.get('attacker') == target_country and w.get('defender') == user_country:
                    blocked = True
                    break
            if blocked:
                await query.answer('⛔ کشور شما زیر آتش جنگ با این کشور است و امکان حمله وجود ندارد.', show_alert=True)
                try:
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='air_attack')]])
                    await query.edit_message_text('⛔ کشور شما زیر آتش جنگ با این کشور است و امکان حمله وجود ندارد.', reply_markup=kb)
                except Exception:
                    pass
                return
        except Exception:
            pass
        try:
            analysis = generate_air_attack_analysis(user_id, target_country)
        except Exception as e:
            analysis = 'خطا در تحلیل حمله هوایی.'
            print(f'air analysis error: {e}')
        keyboard = [
            [InlineKeyboardButton('ادامه و انتخاب نیروها ➡️', callback_data=f'air_attack_{target_country}')],
            [InlineKeyboardButton('🔙 بازگشت', callback_data='air_attack')]
        ]
        await query.edit_message_text(f"📊 تحلیل حمله هوایی به {target_country}:\n\n<blockquote>{analysis}</blockquote>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    elif query.data.startswith('air_attack_'):
        target_country = query.data.replace('air_attack_', '')
        await show_air_forces_inventory(query, target_country)
    elif query.data == 'cancel_air_attack':
        # لغو حمله هوایی
        if user_id in pending_air_attack:
            del pending_air_attack[user_id]
        await query.edit_message_text("✅ حمله هوایی لغو شد!\n\nحالا می‌توانید نیرو تولید کنید یا کارهای دیگر انجام دهید.")
    elif query.data == 'ground_attack_analysis':
        await show_ground_attack_analysis(query)
    elif query.data == 'air_attack_analysis':
        await show_air_attack_analysis(query)
    elif query.data.startswith('naval_target_'):
        target_id = query.data.replace('naval_target_', '')
        target_country = utils.users.get(target_id, {}).get('country', 'کشور')
        from analysis import generate_naval_attack_analysis
        user_id = str(query.from_user.id)
        # Prevent counter-attack if target currently has an active attack against this user
        try:
            user_country = utils.users.get(user_id, {}).get('country')
            blocked = False
            for wid, w in utils.war_declarations.items():
                if w.get('status') == 'active' and w.get('attacker') == target_country and w.get('defender') == user_country:
                    blocked = True
                    break
            if blocked:
                await query.answer('⛔ کشور شما زیر آتش جنگ با این کشور است و امکان حمله وجود ندارد.', show_alert=True)
                try:
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='naval_attack')]])
                    await query.edit_message_text('⛔ کشور شما زیر آتش جنگ با این کشور است و امکان حمله وجود ندارد.', reply_markup=kb)
                except Exception:
                    pass
                return
        except Exception:
            pass
        try:
            analysis = generate_naval_attack_analysis(user_id, target_country)
        except Exception as e:
            analysis = 'خطا در تحلیل حمله دریایی.'
            print(f'naval analysis error: {e}')
        keyboard = [
            [InlineKeyboardButton('ادامه و انتخاب نیروها ➡️', callback_data=f'naval_attack_{target_id}')],
            [InlineKeyboardButton('🔙 بازگشت', callback_data='naval_attack')]
        ]
        await query.edit_message_text(f"📊 تحلیل حمله دریایی به {target_country}:\n\n<blockquote>{analysis}</blockquote>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    elif query.data == 'real_military_power':
        from analysis import get_real_military_power_message
        user_id = str(query.from_user.id)
        message = get_real_military_power_message(user_id)
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')

    elif query.data == 'loot':
        await show_loot_menu(query)
    elif query.data.startswith('loot_caravan_'):
        caravan_id = query.data.replace('loot_caravan_', '')
        user_id = str(query.from_user.id)
        from battle import execute_loot
        success, message = await execute_loot(user_id, caravan_id, context)
        if success:
            await query.edit_message_text(f"✅ {message}")
        else:
            await query.edit_message_text(f"❌ {message}")
    elif query.data == 'edit_alliance_desc':
        await edit_alliance_desc_start(query, user_id)
    elif query.data == 'edit_alliance_rules':
        await edit_alliance_rules_start(query, user_id)
    elif query.data == 'edit_alliance_logo':
        await edit_alliance_logo_start(query, user_id)
    elif query.data == 'edit_alliance_entry_fee':
        await edit_alliance_entry_fee_start(query, user_id)    
    elif query.data == 'sea_raid_locked':
        await query.answer("کشور شما مرز دریایی ندارد و نمی‌تواند به کشتی تجاری حمله کند.", show_alert=True)
    elif query.data == 'sea_raid':
        await show_sea_raid_menu(query)
    elif query.data.startswith('sea_raid_'):
        trade_id = query.data.replace('sea_raid_', '')
        if trade_id.startswith('alliance_'):
            # حمله به محموله کمک اتحاد
            alliance_trade_id = trade_id.replace('alliance_', '')
            await ask_sea_raid_forces(query, f'alliance_{alliance_trade_id}')
        else:
            # حمله به کشتی تجاری معمولی
            await ask_sea_raid_forces(query, trade_id)

    elif query.data == 'set_alliance_deputy':
        await set_alliance_deputy_start(query, user_id)
    elif query.data.startswith('set_deputy_'):
        deputy_id = query.data.replace('set_deputy_', '')
        await set_alliance_deputy_confirm(query, user_id, deputy_id)
    elif query.data.startswith('accept_peace_'):
        from_id = query.data.replace('accept_peace_', '')
        await handle_accept_peace(query, user_id, from_id, context)
    elif query.data.startswith('reject_peace_'):
        from_id = query.data.replace('reject_peace_', '')
        await handle_reject_peace(query, user_id, from_id, context)
    elif query.data == 'close_embassy_menu':
        await show_close_embassy_menu(query)
    elif query.data.startswith('close_embassy_'):
        target_id = query.data.replace('close_embassy_', '')
        await handle_close_embassy(query, user_id, target_id, context)
    
    
    elif query.data == 'alliance_menu':
        if user_id in pending_alliance_chat:
            del pending_alliance_chat[user_id]
        await show_alliance_menu(query)
    elif query.data == 'alliance_chat':
        await show_alliance_chat(query)
    elif query.data == 'alliance_chat_history':
        from diplomaci import show_alliance_chat_history
        await show_alliance_chat_history(query)
    elif query.data == 'create_alliance':
        user_id = str(query.from_user.id)
        user = utils.users.get(str(user_id), {})
        if user.get('resources', {}).get('cash', 0) < 100_000_000:
            await query.edit_message_text('موجودی نقد شما برای ساخت اتحاد کافی نیست (۱۰۰ میلیون دلار).')
            return
        # مرحله تایید هزینه قبل از شروع ویزارد
        utils.pending_create_alliance[user_id] = {'step': 'confirm'}
        keyboard = [
            [InlineKeyboardButton('✅ تایید و ادامه', callback_data='confirm_create_alliance')],
            [InlineKeyboardButton('لغو ❌', callback_data='alliance_menu')]
        ]
        await query.edit_message_text(
            'هزینه ساخت اتحاد ۱۰۰ میلیون دلار است.\nآیا تایید می‌کنید؟',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == 'confirm_create_alliance':
        user_id = str(query.from_user.id)
        user = utils.users.get(str(user_id), {})
        if user.get('resources', {}).get('cash', 0) < 100_000_000:
            await query.edit_message_text('موجودی نقد شما برای ساخت اتحاد کافی نیست (۱۰۰ میلیون دلار).')
            return
        utils.pending_create_alliance[user_id] = {'step': 'name'}
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='alliance_menu')]]
        await query.edit_message_text('نام اتحاد را ارسال کنید:', reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data == 'alliance_list':
        await show_alliance_list(query, str(query.from_user.id))
    elif query.data == 'alliance_advertisement':
        from diplomaci import show_alliance_advertisement_menu
        await show_alliance_advertisement_menu(query)
    elif query.data == 'alliance_ad_normal':
        from diplomaci import handle_alliance_ad_normal
        await handle_alliance_ad_normal(query)
    elif query.data == 'alliance_ad_pinned':
        from diplomaci import handle_alliance_ad_pinned
        await handle_alliance_ad_pinned(query)
    elif query.data == 'confirm_alliance_ad_normal':
        from diplomaci import confirm_alliance_ad_normal
        await confirm_alliance_ad_normal(query, context)
    elif query.data == 'confirm_alliance_ad_pinned':
        from diplomaci import confirm_alliance_ad_pinned
        await confirm_alliance_ad_pinned(query, context)
    elif query.data.startswith('join_alliance_'):
        alliance_id = query.data.replace('join_alliance_', '')
        await join_alliance(query, str(query.from_user.id), alliance_id)
    elif query.data == 'leave_alliance':
        # نمایش پیام تاییدیه با دکمه تایید و لغو
        keyboard = [
            [InlineKeyboardButton('بله، خارج می‌شوم', callback_data='بلهconfirm_leave_alliance')],
            [InlineKeyboardButton('لغو ❌', callback_data='alliance_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('آیا مطمئن هستید که می‌خواهید از اتحاد خارج شوید؟', reply_markup=reply_markup)
    elif query.data == 'بلهconfirm_leave_alliance':
        # حذف کاربر از اتحاد و ثبت زمان خروج
        alliance_id = utils.user_alliances.get(user_id)
        if alliance_id and alliance_id in utils.alliances:
            alliance = utils.alliances[alliance_id]
            is_leader = (alliance.get('leader') == user_id)
            # اگر کاربر رهبر است، انتقال رهبری و پیام به رهبر جدید
            if is_leader:
                from utils import transfer_alliance_on_leader_loss
                transfer_result = transfer_alliance_on_leader_loss(user_id)
                if transfer_result:
                    if transfer_result.get('deleted'):
                        await query.edit_message_text('اتحاد به دلیل خالی شدن اعضا حذف شد.')
                        return
                    new_leader = transfer_result.get('new_leader')
                    if new_leader:
                        try:
                            await context.bot.send_message(
                                chat_id=int(new_leader),
                                text=f"👑 شما رهبر جدید اتحاد {transfer_result.get('alliance_name', '')} شدید. رهبری اتحاد بر عهده شماست."
                            )
                        except Exception:
                            pass
                # در صورت انتقال، alliance ممکن است به‌روز شده باشد
                alliance = utils.alliances.get(alliance_id, alliance)
            # حذف کاربر از اعضا برای سایر حالات
            if alliance and user_id in alliance.get('members', []):
                alliance['members'].remove(user_id)
            utils.user_alliances.pop(user_id, None)
            # ثبت شماره دور فعلی برای محدودیت عضویت مجدد
            alliance_leave_turn[user_id] = utils.game_data['turn']
            # اگر اتحاد خالی شد، حذف شود
            if not alliance['members']:
                del utils.alliances[alliance_id]
                utils.save_alliances()
                await query.edit_message_text('اتحاد به دلیل خالی شدن اعضا حذف شد.')
                return
            utils.save_alliances()
            await query.edit_message_text('شما با موفقیت از اتحاد خارج شدید. تا ۱ دور نمی‌توانید عضو اتحاد جدید شوید.')
        else:
            await query.edit_message_text('شما در هیچ اتحادی عضو نیستید.')
    elif query.data == 'set_alliance_deputy':
        await set_alliance_deputy_start(query, user_id)
    elif query.data.startswith('set_deputy_'):
        deputy_id = query.data.replace('set_deputy_', '')
        await set_alliance_deputy_confirm(query, user_id, deputy_id)
    elif query.data == 'alliance_members':
        await show_alliance_members(query)
    elif query.data == 'alliance_urgent_meeting':
        await handle_alliance_urgent_meeting(query, context)
    elif query.data == 'alliance_kick_member':
        await handle_alliance_kick_member(query, context)
    elif query.data.startswith('kick_member_'):
        member_id = query.data.replace('kick_member_', '')
        await handle_kick_member_confirm(query, context, member_id)
    elif query.data == 'alliance_help':
        await show_alliance_help_menu(query)
    elif query.data == 'alliance_help_request':
        await show_alliance_help_request_menu(query, user_id)
    elif query.data.startswith('help_request_resource_'):
        resource = query.data.replace('help_request_resource_', '')
        pending_help_request[user_id] = {'resource': resource}
        await query.edit_message_text(f'چه تعداد {resource} نیاز دارید؟ عدد را وارد کنید:')
    elif query.data == 'alliance_help_give':
        await show_alliance_help_give_menu(query, user_id)
    elif query.data == 'alliance_trades_list':
        await show_alliance_trades_list(query)
    elif query.data.startswith('help_give_'):
        # فرمت: help_give_target_id_resource_amount
        parts = query.data.replace('help_give_', '').split('_')
        if len(parts) >= 3:
            target_id = parts[0]
            resource = parts[1]
            amount = int(parts[2])
            await handle_help_give_confirm(query, user_id, target_id, resource, amount, context)
    # هندلرهای روابط کشورها
    elif query.data == 'country_relations':
        await show_country_relations_menu(query)
    elif query.data == 'view_relations':
        await show_view_relations(query)
    elif query.data == 'improve_relations':
        await show_improve_relations_menu(query)
    elif query.data == 'damage_relations':
        await show_damage_relations_menu(query)
    elif query.data.startswith('improve_relation_'):
        target_id = query.data.replace('improve_relation_', '')
        await handle_relation_action(query, user_id, target_id, 'improve', context)
    elif query.data.startswith('damage_relation_'):
        target_id = query.data.replace('damage_relation_', '')
        await handle_relation_action(query, user_id, target_id, 'damage', context)
    elif query.data.startswith('accept_improve_'):
        from_id = query.data.replace('accept_improve_', '')
        await handle_relation_action(query, user_id, from_id, 'accept_improve', context)
    elif query.data.startswith('decline_improve_'):
        from_id = query.data.replace('decline_improve_', '')
        await handle_relation_action(query, user_id, from_id, 'decline_improve', context)
    elif query.data.startswith('embassy_menu'):
        await show_embassy_menu(query)
    elif query.data.startswith('request_embassy_'):
        target_id = query.data.replace('request_embassy_', '')
        await handle_embassy_request(query, user_id, target_id, context)
    elif query.data.startswith('accept_embassy_'):
        from_id = query.data.replace('accept_embassy_', '')
        await handle_embassy_accept(query, user_id, from_id, context)
    elif query.data == 'foreign_minister_suggestions':
        await handle_foreign_minister_suggestions(query, context)
    
    elif query.data == 'ground_attack':
        await show_ground_attack_menu(query)
    elif query.data == 'ground_targets':
        await show_ground_targets(query)
    elif query.data.startswith('ground_target_'):
        tid = query.data.replace('ground_target_', '')
        await show_ground_force_picker(query, tid)
    elif query.data.startswith('ground_unit_'):
        # استفاده از rsplit برای جدا کردن فقط target_id (آخرین بخش بعد از _)
        remaining = query.data.replace('ground_unit_', '')
        parts = remaining.rsplit('_', 1)
        if len(parts) == 2:
            unit_key = parts[0]
            tid = parts[1]
        else:
            unit_key = remaining
            tid = ''
        await handle_ground_unit_click(query, unit_key, tid)
    elif query.data.startswith('ground_confirm_'):
        tid = query.data.replace('ground_confirm_', '')
        await handle_ground_confirm(query, tid, context)
    elif query.data == 'cancel_ground_attack':
        if user_id in utils.pending_ground_attack:
            del utils.pending_ground_attack[user_id]
        await query.edit_message_text('عملیات حمله زمینی لغو شد.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]))

    elif query and query.data == 'technology':
        await show_technology_menu(query)
    elif query and query.data == 'military_tech':
        await show_military_tech_menu(query, user_id)
    elif query and query.data.startswith('upgrade_tech_'):
        tech_key = query.data.replace('upgrade_tech_', '')
        await upgrade_military_tech(query, user_id, tech_key)
    elif query and query.data == 'maxed_tech':
        await query.answer('این فناوری به حداکثر لول رسیده است!', show_alert=True)
    elif query and query.data == 'mine_production_tech':
        await show_mine_production_tech_menu(query)
    elif query and query.data.startswith('production_tech_upgrade_'):
        resource_key = query.data.replace('production_tech_upgrade_', '')
        await confirm_production_tech_upgrade(query, resource_key)
    elif query and query.data.startswith('production_tech_confirm_'):
        resource_key = query.data.replace('production_tech_confirm_', '')
        await execute_production_tech_upgrade(query, resource_key)
    elif query and query.data == 'production_tech_maxed':
        await query.answer('این منبع به حداکثر لول (20) رسیده است!', show_alert=True)
    elif query and query.data == 'give_all_techs_level_one_all':
        if user_id == ADMIN_ID:
            from utils import users, give_all_techs_level_one
            print('[DEBUG] فراخوانی give_all_techs_level_one_all توسط ادمین')
            for uid in utils.users:
                print(f'[DEBUG] فراخوانی give_all_techs_level_one برای کاربر {uid}')
                give_all_techs_level_one(uid)
            print('[DEBUG] ذخیره همه فناوری‌ها برای همه کاربران انجام شد')
            await query.edit_message_text('به همه کاربران لول 1 برای همه فناوری‌های نظامی داده شد و فایل ذخیره شد.')
        else:
            await query.edit_message_text('شما دسترسی ادمین ندارید.')
    
    # مدیریت callback های سازمان ملل (یک مسیر واحد بالاتر موجود است)
    
    elif query.data == 'missile_attack':
        await show_missile_attack_menu(query)
    elif query.data and query.data.startswith('missile_type_'):
        missile_type = query.data.replace('missile_type_', '')
        await start_missile_attack_phases(query, missile_type)
    elif query.data and query.data.startswith('missile_target_'):
        parts = query.data.replace('missile_target_', '').split('_')
        missile_type = parts[0]
        target_country = parts[1]
        count = int(parts[2]) if len(parts) > 2 else 1
        # اجرای خودکار حمله موشکی با job_queue
        from battle import missile_attack_auto_phases
        context.job_queue.run_once(lambda ctx: asyncio.create_task(missile_attack_auto_phases(str(query.from_user.id), missile_type, target_country, count, ctx)), 0)
        await query.edit_message_text('حمله موشکی شما در حال اجراست و مراحل به صورت خودکار پیش خواهد رفت.')
    elif query.data and query.data.startswith('missile_phase2_'):
        parts = query.data.replace('missile_phase2_', '').split('_')
        missile_type = parts[0]
        target_country = parts[1]
        count = int(parts[2]) if len(parts) > 2 else 1
        await missile_attack_phase_2(query, missile_type, target_country, count)
    elif query.data and query.data.startswith('missile_phase3_'):
        parts = query.data.replace('missile_phase3_', '').split('_')
        missile_type = parts[0]
        target_country = parts[1]
        count = int(parts[2]) if len(parts) > 2 else 1
        await missile_attack_phase_3(query, missile_type, target_country, count)
    elif query.data and query.data.startswith('missile_result_'):
        parts = query.data.replace('missile_result_', '').split('_')
        missile_type = parts[0]
        target_country = parts[1]
        count = int(parts[2]) if len(parts) > 2 else 1
        await missile_attack_result(query, missile_type, target_country, count)
    elif query.data and query.data.startswith('select_missile_count_'):
        count = int(query.data.replace('select_missile_count_', ''))
        await show_missile_target_selection(query, 'ballistic', count)
def season_reset():
    """پایان فصل - پاک کردن تمام فایل‌های بازی و حفظ اطلاعات اکانت کاربران"""
    import os
    import json
    import utils as _utils
    
    print("🔄 شروع ریست فصل...")
    
    # ابتدا اطلاعات اکانت کاربران را بخوان و نگه دار
    preserved_users = {}
    if os.path.exists('users.json'):
        try:
            with open('users.json', 'r', encoding='utf-8') as f:
                all_users = json.load(f)
                for uid, udata in all_users.items():
                    # فقط اطلاعات اکانت را نگه دار (بدون اطلاعات کشور)
                    preserved_users[uid] = {
                        'user_id': udata.get('user_id'),
                        'name': udata.get('name', ''),
                        'nickname': udata.get('nickname', ''),
                        'player_name': udata.get('player_name', ''),
                        'phone': udata.get('phone', ''),
                        'location': udata.get('location', {}),
                        'profile': {
                            'is_registered': udata.get('profile', {}).get('is_registered', False),
                            'has_country': False  # کشور پاک می‌شود
                        },
                        'inventory': udata.get('inventory', {'credits': 0, 'items': []}),
                        'titles': udata.get('titles', []),
                        'public_identifier': udata.get('public_identifier'),
                        'aliases': udata.get('aliases', []),
                        'activated': False,  # غیرفعال می‌شود
                        'government_type': '',
                        'government_title': '',
                        'country_leader_name': '',
                        'category': '',
                        'code': 0,
                        'country_slogan': '',
                        'current_names_suggestions': udata.get('current_names_suggestions', []),
                        'selected_officials': udata.get('selected_officials', {}),
                        'resources': {},  # منابع پاک می‌شود
                        # پاک‌سازی کامل وضعیت فتح/استقلال/مهلت
                        'conquered_by': None,
                        'conquered_at': None,
                        'conquered_captured_cash': 0,
                        'independence_deadline_turn': None,
                        'independence_requested': False,
                        'independence_granted': False,
                        'was_conquered': False,
                        'forced_peace_turns': 0,
                        'last_activity': udata.get('last_activity'),
                        'registration_date': udata.get('registration_date'),
                        'last_login': udata.get('last_login')
                    }
        except Exception as e:
            print(f'❌ خطا در خواندن کاربران: {e}')
    
    # لیست کامل فایل‌های بازی که باید پاک شوند
    files_to_delete = [
        'users.json',
        'countries.json', 
        'game_data.json',
        'country_relations.json',
        'war_declarations.json',
        'conquered_countries.json',
        'independence_loans.json',
        'alliances.json',
        'military_technologies.json',
        'pending_trades.json',
        'bank_data.json',
        'loan_history.json',
        'bank_accounts.json',
        'transfer_history.json',
        'alliance_messages.json',
        'naval_attack_saves.json',
        'secret_loan_claimed.json',
        'economy_secret_claimed.json',
        'active_loans.json',
        'overdue_debts.json',
        'population_data.json',
        'united_nations_data.json',
        'banned_users.json',
        'location_verification.json',
        'global_market.json',
        'activation_codes.json',
        'tax_data.json',
        'bot_lock_status.json',
        'secret_loan_activated.json'
    ]
    
    deleted_count = 0
    for file_name in files_to_delete:
        if os.path.exists(file_name):
            try:
                os.remove(file_name)
                deleted_count += 1
                print(f"✅ {file_name} حذف شد")
            except Exception as e:
                print(f"❌ خطا در حذف {file_name}: {e}")
    
    # ایجاد فایل‌های جدید با مقادیر پیش‌فرض
    try:
        # ذخیره کاربران با اطلاعات اکانت
        with open('users.json', 'w', encoding='utf-8') as f:
            json.dump(preserved_users, f, ensure_ascii=False, indent=2)
        print("✅ users.json با اطلاعات اکانت بازسازی شد")
        
        # ایجاد فایل‌های خالی جدید
        empty_files = {
            'countries.json': [],
            'game_data.json': {
                'turn': 1,
                'last_turn_time': None,
                'game_date': '01/01/2025',
                'resources': {},
                'prices': {
                    'gold': 5000000, 'steel': 600000, 'iron': 200000, 'copper': 400000,
                    'diamond': 12000000, 'uranium': 8000000, 'wheat': 100000, 'rice': 80000,
                    'fruits': 60000, 'oil': 600000, 'gas': 300000, 'electronics': 55,
                    'pride_cars': 700, 'benz_cars': 4000, 'electricity': 800000,
                    'uranium_ore': 150000, 'centrifuge': 2000000, 'yellowcake': 1500000,
                    'space_parts': 4000000, 'aluminum': 1000000, 'titanium': 2000000,
                    'soldiers': 5000, 'special_forces': 15000, 'tanks': 500000,
                    'armored_vehicles': 300000, 'transport_planes': 2000000, 'helicopters': 800000,
                    'fighter_jets': 3000000, 'bombers': 5000000, 'artillery': 400000,
                    'drones': 200000, 'air_defense': 600000, 'coastal_artillery': 500000,
                    'speedboats': 300000, 'naval_ship': 2000000, 'submarines': 3000000,
                    'aircraft_carriers': 10000000, 'war_robots': 100000, 'defense_missiles': 50000,
                    'ballistic_missiles': 200000
                },
                'season': int(_utils.game_data.get('season', 1))
            },
            'country_relations.json': {'country_relations': {}, 'embassies': {}},
            'war_declarations.json': {},
            'conquered_countries.json': {},
            'independence_loans.json': {},
            'alliances.json': {
                'alliances': {}, 'user_alliances': {}, 'alliance_messages': {},
                'alliance_help_requests': {}, 'alliance_trades': {}, 'country_relations': {}
            },
            'military_technologies.json': {},
            'pending_trades.json': [],
            'bank_data.json': {
                'total_loans_given': 0,
                'total_loans_paid': 0,
                'total_interest_earned': 0,
                'bank_reserves': 100000000000,
                'loan_types': {
                    'independence': {
                        'amount': 1000000000,
                        'interest_rate': 0.04,
                        'duration': 4,
                        'max_uses': 1
                    },
                    'development': {
                        'amount': 500000000,
                        'interest_rate': 0.22,
                        'duration': 6,
                        'max_uses': 3
                    },
                    'emergency': {
                        'amount': 200000000,
                        'interest_rate': 0.12,
                        'duration': 3,
                        'max_uses': 5
                    },
                    'secret': {
                        'amount': 1000000000,
                        'interest_rate': 0.0,
                        'duration': 24,
                        'max_uses': 1
                    }
                }
            },
            'loan_history.json': {},
            'bank_accounts.json': {},
            'transfer_history.json': {},
            'alliance_messages.json': [],
            'naval_attack_saves.json': {},
            'secret_loan_claimed.json': False,
            'economy_secret_claimed.json': False,
            'active_loans.json': {},
            'overdue_debts.json': {},
            'population_data.json': {},
            'united_nations_data.json': {
                'un_activated_user': None, 'pending_un_activation': {},
                'ceasefire_requests': {}, 'un_peace_scores': {}, 'un_peace_prize_winners': [],
                'last_peace_prize_award_turn': 0, 'un_resolutions': [], 'sanctions': {},
                'pending_sanction': {}, 'un_complaints': [], 'pending_un_complaint': {},
                'un_courts': [], 'pending_un_court': {}, 'pending_court_edit': {}
            },
            'banned_users.json': [],
            'location_verification.json': {},
            'global_market.json': {
                'gold': 100, 'steel': 500, 'iron': 1000, 'copper': 1000, 'diamond': 50,
                'uranium': 100, 'wheat': 1000, 'rice': 1000, 'fruits': 1000, 'oil': 10000,
                'gas': 10000, 'electronics': 10000000, 'pride_cars': 100000, 'benz_cars': 100000,
                'electricity': 1000, 'uranium_ore': 1000, 'centrifuge': 100, 'yellowcake': 1000,
                'space_parts': 100, 'aluminum': 500, 'titanium': 200
            },
            'activation_codes.json': {},
            'tax_data.json': {},
            'bot_lock_status.json': {'locked': False, 'reason': ''},
            'secret_loan_activated.json': False,
            'pending_payments.json': {}
        }
        
        for file_name, content in empty_files.items():
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            print(f"✅ {file_name} بازسازی شد")
        
        # همگام‌سازی وضعیت در حافظه با فایل‌های جدید
        try:
            # به‌روزرسانی users در حافظه بر اساس preserved_users (بدون منابع و کشور)
            _utils.users = preserved_users
            _utils.save_users()
            
            # بارگذاری مجدد داده‌های اصلی بازی
            try:
                _utils.load_game_data()
            except Exception as e:
                print(f"[season_reset] load_game_data error: {e}")
            try:
                _utils.load_countries()
            except Exception as e:
                print(f"[season_reset] load_countries error: {e}")
        except Exception as sync_err:
            print(f"❌ خطا در همگام‌سازی داده‌ها پس از ریست فصل: {sync_err}")
        
        print(f"\n🎉 ریست فصل کامل شد!")
        print(f"📊 آمار: {deleted_count} فایل حذف شد")
        print(f"👥 {len(preserved_users)} اکانت کاربر حفظ شد")
        print("🔄 فصل جدید آماده شروع است!")
        
    except Exception as e:
        print(f"❌ خطا در بازسازی فایل‌ها: {e}")

def force_reset_files():
    """پاک کردن اجباری تمام فایل‌های JSON"""
    import os
    import time
    import json
    
    # ابتدا اطلاعات کاربران فعال را بخوان
    active_users = {}
    if os.path.exists('users.json'):
        try:
            with open('users.json', 'r', encoding='utf-8') as f:
                all_users = json.load(f)
                for uid, udata in all_users.items():
                    if udata.get('activated'):
                        # فقط اطلاعات فعال‌سازی و کشور و حکومت و نام را نگه دار
                        active_users[uid] = {
                            'activated': True,
                            'country': udata.get('country'),
                            'category': udata.get('category'),
                            'code': udata.get('code'),
                            'government_type': udata.get('government_type'),
                            'government_title': udata.get('government_title'),
                            'player_name': udata.get('player_name')
                        }
        except Exception as e:
            print(f'خطا در خواندن کاربران فعال: {e}')
    
    files_to_delete = [
        'users.json',
        'countries.json', 
        'game_data.json',
        'country_relations.json',
        'war_declarations.json',
        'conquered_countries.json',
        'independence_loans.json',
        'alliances.json',
        'military_technologies.json',
        'pending_trades.json',
        'bank_data.json',
        'loan_history.json',
        'bank_accounts.json',
        'transfer_history.json',
        'alliance_messages.json',
        'naval_attack_saves.json',
        'secret_loan_claimed.json',
        'economy_secret_claimed.json',
        'active_loans.json',
        'overdue_debts.json',
        'population_data.json'
    ]
    deleted_count = 0
    for file_name in files_to_delete:
        if os.path.exists(file_name):
            try:
                os.remove(file_name)
                deleted_count += 1
                print(f"✅ {file_name} حذف شد")
            except Exception as e:
                print(f"❌ خطا در حذف {file_name}: {e}")
    
    # ایجاد فایل‌های خالی جدید
    empty_files = {
        'users.json': active_users,  # کاربران فعال را نگه دار
        'countries.json': [],
        'game_data.json': {'turn': 1, 'game_date': '01/01/2024', 'prices': {'gold': 5000000}},
        'country_relations.json': {},
        'war_declarations.json': {},
        'conquered_countries.json': {},
        'independence_loans.json': {},
        'alliances.json': {},
        'global_market.json': {
            'gold': 100,
            'steel': 500,
            'iron': 1000,
            'copper': 1000,
            'diamond': 50,
            'uranium': 100,
            'wheat': 1000,
            'rice': 1000,
            'fruits': 1000,
            'oil': 10000,
            'gas': 10000,
            'electronics': 10000000,
            'pride_cars': 100000,
            'benz_cars': 100000,
            'electricity': 1000,
            'uranium_ore': 1000,
            'centrifuge': 100,
            'yellowcake': 1000,
            'space_parts': 100,
            'aluminum': 500,
            'titanium': 200
        },
        'military_technologies.json': {},
        'pending_trades.json': [],
        'secret_loan_claimed.json': False,
        'economy_secret_claimed.json': False,
        'active_loans.json': {},
        'overdue_debts.json': {},
        'activation_codes.json': {}
    }
    
    for file_name, default_content in empty_files.items():
        try:
            with open(file_name, 'w', encoding='utf-8') as f:
                json.dump(default_content, f, ensure_ascii=False, indent=2)
            print(f"✅ {file_name} با داده‌های خالی ایجاد شد")
        except Exception as e:
            print(f"❌ خطا در ایجاد {file_name}: {e}")
    
    print(f"📊 تعداد فایل‌های حذف شده: {deleted_count}")
    return deleted_count

# تابع ریست کامل ربات
async def reset_bot_completely():
    """ریست کامل تمام اطلاعات ربات به حالت اول"""
    global countries, game_data, pending_trades, country_relations, war_declarations, conquered_countries_data, independence_loans, alliances, user_alliances, player_sell_ads, global_market_inventory, military_technologies
    
    print("🔄 شروع ریست کامل ربات...")
    
    # پاک کردن اجباری فایل‌ها اول
    deleted_count = force_reset_files()
    print(f"📊 {deleted_count} فایل حذف شد")
    
    # اطمینان از اینکه تمام متغیرهای سراسری ریست شوند
    global countries, game_data, pending_trades, country_relations, war_declarations, conquered_countries_data, independence_loans, alliances, user_alliances, player_sell_ads, global_market_inventory, military_technologies
    
    # ریست کردن تمام متغیرهای سراسری
    # users را در utils نگه می‌داریم
    countries = []
    game_data = {'turn': 1, 'game_date': '01/01/2024', 'prices': {'gold': 5000000}}
    pending_trades = []
    country_relations = {}
    war_declarations = {}
    conquered_countries_data = {}
    independence_loans = {}
    alliances = {}
    user_alliances = {}
    player_sell_ads = []
    global_market_inventory = {
        'gold': 10,
        'steel': 500,
        'iron': 1000,
        'copper': 1000,
        'diamond': 50,
        'uranium': 100,
        'wheat': 1000,
        'rice': 1000,
        'fruits': 1000,
        'oil': 10000,
        'gas': 10000,
        'electronics': 1000000,
        'pride_cars': 100000,
        'benz_cars': 100000,
        'electricity': 1000,
        'uranium_ore': 1000,
        'centrifuge': 100,
        'yellowcake': 1000,
        'space_parts': 100,
        'aluminum': 50,
        'titanium': 20
    }
    military_technologies = {}
    
    # ریست کردن تمام متغیرهای pending
    pending_activation.clear()
    pending_sell_amount.clear()
    pending_sell_total_price.clear()
    pending_military_production.clear()
    pending_help_request.clear()
    utils.pending_create_alliance.clear()
    pending_statement.clear()
    pending_alliance_chat.clear()
    pending_government_selection.clear()
    pending_name_selection.clear()
    pending_minister_selection.clear()
    pending_general_selection.clear()
    pending_foreign_selection.clear()
    pending_ground_attack.clear()
    pending_air_attack.clear()
    pending_naval_attack.clear()
    pending_sea_raid.clear()
    
    # ریست کردن متغیرهای مخفی
    utils.secret_loan_claimed = False
    utils.economy_secret_claimed = False
    
    # اطمینان از اینکه تمام متغیرهای سراسری در utils هم ریست شوند
    # utils.users را ریست نمی‌کنیم تا کاربران فعال حفظ شوند
    utils.countries = []
    utils.game_data = {'turn': 1, 'game_date': '01/01/2024', 'prices': {'gold': 5000000}}
    utils.pending_trades = []
    utils.country_relations = {}
    utils.war_declarations = {}
    utils.conquered_countries_data = {}
    utils.independence_loans = {}
    utils.alliances = {}
    utils.user_alliances = {}
    utils.player_sell_ads = []
    utils.global_market_inventory = {}
    utils.military_technologies = {}
    
    print("✅ متغیرهای سراسری ریست شدند")
    
    # تولید کدهای فعال‌سازی جدید
    try:
        from admin_panel import generate_all_activation_codes
        utils.load_countries()  # بارگذاری کشورها برای تولید کدها
        new_codes = generate_all_activation_codes()
        print(f"✅ {len(new_codes)} کد فعال‌سازی جدید تولید شد")
    except Exception as e:
        print(f"❌ خطا در تولید کدهای فعال‌سازی: {e}")
    
    print("✅ فایل‌های جدید با داده‌های خالی ذخیره شدند")
    
    # اطمینان از ریست کامل با بررسی فایل‌ها
    import os
    import json
    
    # بررسی اینکه فایل‌ها واقعاً خالی هستند
    files_to_check = ['users.json', 'countries.json', 'game_data.json']
    for file_name in files_to_check:
        if os.path.exists(file_name):
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    if file_name == 'users.json' and content:
                        print(f"⚠️ {file_name} هنوز حاوی داده است!")
                        # پاک کردن اجباری
                        with open(file_name, 'w', encoding='utf-8') as f:
                            json.dump({}, f, ensure_ascii=False, indent=2)
                        print(f"✅ {file_name} اجباری پاک شد")
                    elif file_name == 'countries.json' and content:
                        print(f"⚠️ {file_name} هنوز حاوی داده است!")
                        # پاک کردن اجباری
                        with open(file_name, 'w', encoding='utf-8') as f:
                            json.dump([], f, ensure_ascii=False, indent=2)
                        print(f"✅ {file_name} اجباری پاک شد")
            except Exception as e:
                print(f"❌ خطا در بررسی {file_name}: {e}")
    
    print("🎉 ریست کامل ربات با موفقیت انجام شد!")

# تابع امن برای ویرایش پیام‌ها (با مدیریت پیام‌های طولانی و عدم تغییر)
async def safe_edit_message(query, text, reply_markup=None, parse_mode=None):
    def split_chunks(s: str, max_len: int = 3800):
        if len(s) <= max_len:
            return [s]
        parts = []
        rest = s
        while len(rest) > max_len:
            cut = rest.rfind('\n\n', 0, max_len)
            if cut == -1:
                cut = rest.rfind('\n', 0, max_len)
            if cut == -1:
                cut = max_len
            parts.append(rest[:cut])
            rest = rest[cut:]
        if rest:
            parts.append(rest)
        return parts

    chunks = split_chunks(text)
    try:
        await query.edit_message_text(chunks[0], reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        msg = str(e)
        if "Message is not modified" in msg:
            return
        if "Message_too_long" in msg:
            # بخش‌بندی بیشتر
            chunks = split_chunks(chunks[0], 3500)
            await query.edit_message_text(chunks[0], reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            print(f"خطا در ویرایش پیام: {e}")
            return

    # ارسال باقی بخش‌ها به صورت پیام جدید
    if len(chunks) > 1:
        try:
            from telegram import Bot
            import utils as _utils
            bot = Bot(token=utils.BOT_TOKEN)
            chat_id = query.message.chat_id if hasattr(query, 'message') else None
            if chat_id is None and hasattr(query, 'message') and hasattr(query.message, 'chat'):
                chat_id = query.message.chat.id
            for idx in range(1, len(chunks)):
                part = chunks[idx]
                for sub in split_chunks(part, 3500):
                    await bot.send_message(chat_id=chat_id, text=sub, parse_mode=parse_mode)
        except Exception as e:
            print(f"خطا در ارسال بخش‌های تکمیلی: {e}")

async def safe_send_message(bot, chat_id, text, reply_markup=None, parse_mode=None):
    """ارسال ایمن پیام با مدیریت خطا و تقسیم متن‌های طولانی"""
    def split_chunks(s: str, max_len: int = 3800):
        if len(s) <= max_len:
            return [s]
        parts = []
        rest = s
        while len(rest) > max_len:
            cut = rest.rfind('\n\n', 0, max_len)
            if cut == -1:
                cut = rest.rfind('\n', 0, max_len)
            if cut == -1:
                cut = max_len
            parts.append(rest[:cut])
            rest = rest[cut:]
        if rest:
            parts.append(rest)
        return parts

    chunks = split_chunks(text)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=chunks[0],
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        for part in chunks[1:]:
            for sub in split_chunks(part, 3500):
                await bot.send_message(chat_id=chat_id, text=sub, parse_mode=parse_mode)
    except Exception as e:
        print(f"Error sending message: {e}")
        if "Too Many Requests" in str(e) or "Flood control" in str(e):
            import asyncio
            await asyncio.sleep(2)
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text="⚠️ به دلیل ارسال پیام‌های زیاد، لطفاً کمی صبر کنید.",
                    parse_mode=parse_mode
                )
            except Exception as e2:
                print(f"Retry failed: {e2}")

# تابع محاسبه ارزش کل اقتصاد

# ==================== افکت لودینگ متحرک ====================
async def show_loading_animation(chat_id: int, context: ContextTypes.DEFAULT_TYPE, duration_seconds: int = 8):
    """نمایش لودینگ ساده با یک ایموجی ⏳ و تبدیل به «✅ آماده» پس از پایان.
    قابل لغو با تغییر فلگ utils.loading_flags[str(message_id)] به False.
    """
    try:
        msg = await context.bot.send_message(chat_id=chat_id, text="⏳")
        message_id = msg.message_id
        utils.loading_flags[str(message_id)] = True
        import time
        start = time.time()
        # حلقه انتظار برای امکان توقف زودتر
        while time.time() - start < duration_seconds and utils.loading_flags.get(str(message_id), True):
            await asyncio.sleep(0.3)
        # پاکسازی فلگ
        utils.loading_flags.pop(str(message_id), None)
        # جمع‌بندی: تبدیل به تیک
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="✅ آماده")
        except Exception:
            pass
    except Exception as e:
        print(f"[LOADING] error: {e}")

def stop_loading_animation(message_id: int):
    utils.loading_flags[str(message_id)] = False


# نمایش وضعیت کشور
async def show_country_status(query):
    user_id = str(query.from_user.id)
    if user_id not in utils.users or not utils.users[user_id].get('activated', False):
        await show_simple_section(query, 'شما هنوز کشور فعال نکرده‌اید.')
        return
    # تعلیق ۲ دوری وضعیت کشور در صورت ترور وزیر کشور
    current_turn = utils.game_data.get('turn', 1)
    panel_suspensions = utils.users[user_id].get('panel_suspensions', {})
    if current_turn < panel_suspensions.get('country_status', 0):
        await query.edit_message_text(
            '⚫️ <b>دوره سوگواری داخلی</b>\n\nبه دلیل ترور وزیر کشور، این بخش تا دو دور آینده در دسترس نیست.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_game_menu')]]),
            parse_mode='HTML'
        )
        return
    
    initialize_user_resources(user_id)
    country_name = utils.users[user_id]['country']
    category = utils.users[user_id]['category']
    cash = utils.users[user_id]['resources'].get('cash', 0)
    total_economy = calculate_total_economy(user_id)
    resources = utils.users[user_id]['resources']
    # نمایش داینامیک تلفات در حال نبرد دریایی برای حمله‌کننده
    try:
        effective_resources = dict(resources)
        # اگر کاربر در حال حاضر مهاجم یک نبرد دریایی فعال است، باقیمانده نیروهای در نبرد را هم به نمایش اضافه کنیم
        naval_keys = ['soldiers', 'speedboats', 'naval_ship', 'submarines', 'aircraft_carriers']
        # پیدا کردن یکی از نبردهای فعال کاربر (در صورت تعدد، جدیدترین بر اساس start_time)
        active_my_naval = []
        for aid, ad in getattr(utils, 'naval_attacks', {}).items():
            if str(ad.get('attacker_id')) == str(user_id):
                active_my_naval.append(ad)
        if active_my_naval:
            active_my_naval.sort(key=lambda x: float(x.get('start_time', 0)), reverse=True)
            ad = active_my_naval[0]
            att_forces = ad.get('attacker_forces', {}) or {}
            for k in naval_keys:
                try:
                    effective_resources[k] = int(effective_resources.get(k, 0)) + int(att_forces.get(k, 0))
                except Exception:
                    pass
        resources = effective_resources
    except Exception:
        pass
    
    # دریافت اطلاعات حکومت و مسئولین
    gov_title = utils.users[user_id].get('government_title', 'رهبر')
    # Use the in-game chosen leader name, not Telegram account name
    player_name = get_country_leader_display_name(user_id)
    
    # استفاده از مسئولین انتخاب شده
    selected_officials = utils.users[user_id].get('selected_officials', {})
    if 'minister' in selected_officials:
        minister = selected_officials['minister']
    else:
        # اگر وزیر انتخاب نشده، از اسامی پیش‌فرض استفاده کن
        minister = {'name': 'وزیر کشور', 'title': 'وزیر کشور'}
    
    # بررسی اینکه آیا مسئولین انتخاب شده وجود دارند
    if not selected_officials:
        print(f"Warning: No selected officials for user {user_id}")
    
    # پیام خوشامدگویی
    from government import get_short_government_title
    
    # تبدیل لقب به فرمت مختصر
    short_title = get_short_government_title(gov_title)
    
    welcome_text = f'🏛️ <b>خوش آمدید {short_title} {player_name}!</b>\n\n'
    welcome_text += f'👨‍💼 من {minister["name"]}، {minister["title"]} شما هستم.\n'
    welcome_text += f'🌍 <b>وضعیت کشور {country_name}</b> در تاریخ {game_data["game_date"]} خدمت شما:\n\n'
    # نمایش منابع به صورت لیست (فقط منابع اقتصادی)
    resources_text = ''
    resource_names = {
        'gold': '🥇 طلا', 'steel': '🔩 فولاد', 'iron': '⛓️ آهن', 'copper': '🔧 مس', 'diamond': '💎 الماس', 'uranium': '☢️ اورانیوم',
        'wheat': '🌾 گندم', 'rice': '🍚 برنج', 'fruits': '🍎 میوه', 'oil': '🛢️ نفت', 'gas': '⛽ گاز', 'electronics': '🔌 الکترونیک',
        'pride_cars': '🚗 پراید', 'benz_cars': '🚙 بنز', 'electricity': '⚡ برق',
        'uranium_ore': '🪨 سنگ اورانیوم', 'centrifuge': '🔄 سانتریفیوژ', 'yellowcake': '🍰 کیک زرد', 'space_parts': '🚀 قطعات فضایی', 'aluminum': '🔧 آلومینیوم', 'titanium': '🔩 تیتانیوم'
    }
    # دسته‌بندی منابع
    minerals = ['gold', 'steel', 'iron', 'copper', 'diamond', 'aluminum', 'titanium']
    energy = ['oil', 'gas', 'electricity', 'uranium', 'uranium_ore', 'centrifuge', 'yellowcake']
    food = ['wheat', 'rice', 'fruits']
    technology = ['electronics', 'space_parts']
    vehicles = ['pride_cars', 'benz_cars']
    
    # فقط منابع اقتصادی را نمایش بده
    resources_text = ''
    
    # مواد معدنی
    minerals_text = ''
    for res in minerals:
        if res in resources:
            val = resources[res]
            name = resource_names.get(res, res)
            minerals_text += f'  {name}: {val:,}\n'
    
    # انرژی
    energy_text = ''
    for res in energy:
        if res in resources:
            val = resources[res]
            name = resource_names.get(res, res)
            energy_text += f'  {name}: {val:,}\n'
    
    # غذا
    food_text = ''
    for res in food:
        if res in resources:
            val = resources[res]
            name = resource_names.get(res, res)
            food_text += f'  {name}: {val:,}\n'
    
    # فناوری
    tech_text = ''
    for res in technology:
        if res in resources:
            val = resources[res]
            name = resource_names.get(res, res)
            tech_text += f'  {name}: {val:,}\n'
    
    # وسایل نقلیه
    vehicles_text = ''
    for res in vehicles:
        if res in resources:
            val = resources[res]
            name = resource_names.get(res, res)
            vehicles_text += f'  {name}: {val:,}\n'
    
    # نمایش سازه‌های ساخته‌شده
    economy = utils.users[user_id].setdefault('economy', {})
    # مهاجرت کلیدهای قدیمی به جدید (مثلاً power_plants -> energy) تا در نمایش سازه‌ها دیده شود
    legacy_mappings = {
        'power_plants': 'energy',
    }
    migrated = False
    for old_key, new_key in legacy_mappings.items():
        if economy.get(old_key):
            economy.setdefault(new_key, [])
            economy[new_key].extend(economy[old_key])
            economy[old_key] = []
            migrated = True
    if migrated:
        save_users()
    buildings_text = ''
    for section_key, section in BUILDINGS.items():
        built = economy.get(section_key, [])
        if built:
            names = []
            for item in section['items']:
                # محدودیت: اگر سازه تولیدی است فقط ۱، وگرنه ۵
                is_production = item['key'] in PRODUCTION_RECIPES
                max_count = 1 if is_production else 5
                count = built.count(item['key'])
                if count > 0:
                    suffix = f' {count}/{max_count}'
                    names.append(item['name'] + suffix)
            if names:
                buildings_text += f"<b>{section['title']}:</b> " + '، '.join(names) + '\n'
    if not buildings_text:
        buildings_text = 'هیچ سازه‌ای ندارید.'

    # تحلیل هوشمند وضعیت کشور
    from analysis import generate_country_status_analysis
    # اگر وزیر کشور ترور شده، تحلیل را نمایش نده
    try:
        is_alive = utils.users[user_id].get('selected_officials', {}).get('minister', {}).get('alive', True)
        if is_alive:
            analysis = generate_country_status_analysis(user_id, resources, economy, total_economy, cash)
        else:
            analysis = 'این مقام ترور شده و تحلیلی ارائه نمی‌شود.'
    except Exception:
        analysis = 'خطا در تحلیل وضعیت کشور.'
    
    # دریافت نوع حکومت
    gov_title = utils.users[user_id].get('government_title', 'رهبر')
    
    status_text = welcome_text + f"""
🇺🇳 <b>{country_name}</b>
📊 <b>لقب:</b> {category}
🏛️ <b>نوع حکومت:</b> {gov_title}

💰 <b>موجودی نقد:</b> {cash:,} دلار

💎 <b>اقتصاد کل کشور:</b> {total_economy:,} دلار

<b>منابع:</b>

🪨 <b>مواد معدنی:</b>
{minerals_text}
⚡ <b>انرژی:</b>
{energy_text}
🌾 <b>مواد غذایی:</b>
{food_text}
🔌 <b>فناوری:</b>
{tech_text}
🚗 <b>وسایل نقلیه:</b>
{vehicles_text}

🏗️ <b>سازه‌های ساخته‌شده:</b>
{buildings_text}

<b>پیشنهاد {minister["title"]} {minister["name"]}:</b>
<blockquote>{analysis}</blockquote>
"""
    
    keyboard = [
        [InlineKeyboardButton('🗺️ نقشه جهان', callback_data='world_map')],
        [InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_game_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(status_text, reply_markup=reply_markup, parse_mode='HTML')

# نمایش وضعیت جمعیت


async def show_technology_menu(query):
    keyboard = [
        [InlineKeyboardButton('توسعه فناوری نظامی', callback_data='military_tech')],
        [InlineKeyboardButton('توسعه فناوری ساخت وساز', callback_data='build_tech')],
        [InlineKeyboardButton('⛏️ فناوری تولید', callback_data='mine_production_tech')],
        # اینجا می‌توانی دکمه‌های دیگر فناوری را اضافه کنی
        [InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_game_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('منوی توسعه فناوری:', reply_markup=reply_markup)

# وضعیت انتظار تولید تسلیحات نظامی برای هر کاربر
pending_military_production = {}
pending_production_line_production = {}




async def send_new_month_greetings(bot, new_date):
    text = f"🎉 ماه جدید مبارک!\n📅 تاریخ جدید: {new_date}\nبه بازی استراتژی خوش آمدید!"
    photo_file_id = "https://t.me/TextEmpire_IR/84"
    
    # ارسال به همه کاربران فعال
    for user_id, user in utils.users.items():
        if user.get('activated', False):
            try:
                await bot.send_photo(chat_id=int(user_id), photo=photo_file_id, caption=text, parse_mode='HTML')
                print(f"✅ پیام ماه جدید به کاربر {user_id} ارسال شد")
            except Exception as e:
                print(f"خطا در ارسال به کاربر {user_id}: {e}")
    
    # ارسال به کانال اخبار
    try:
        await bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=photo_file_id, caption=text, parse_mode='HTML')
        print(f"✅ پیام ماه جدید به کانال اخبار ارسال شد")
    except Exception as e:
        print(f"خطا در ارسال به کانال اخبار: {e}")
# راه‌اندازی ربات


async def check_internet_connection():
    """بررسی اتصال اینترنت"""
    import socket
    try:
        # تلاش برای اتصال به DNS گوگل
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

async def monitor_connection(app):
    """مانیتورینگ اتصال اینترنت در حین اجرای ربات"""
    while True:
        try:
            await asyncio.sleep(60)  # بررسی هر دقیقه
            if not await check_internet_connection():
                print("⚠️ اتصال اینترنت قطع شد. منتظر اتصال مجدد...")
                # متوقف کردن ربات
                await app.stop()
                break
        except Exception as e:
            print(f"خطا در مانیتورینگ اتصال: {e}")
            break

async def setup_bot():
    """راه‌اندازی اولیه ربات"""
    # بارگذاری داده‌های بازی اول
    load_military_technologies()
    load_naval_attack_saves()
    load_war_declarations()
    load_game_data()
    load_global_market()
    load_alliances()
    load_country_relations()
    load_independence_loans()
    load_conquered_countries_data()
    load_bank_data()
    load_loan_history()
    load_refugee_requests()  # بارگذاری درخواست‌های پناهندگی
    
    # بارگذاری کاربران
    from utils import load_users
    load_users()
    
    # اطمینان از اینکه همه کاربران شناسه عمومی دارند
    from utils import ensure_all_users_have_public_identifiers
    ensure_all_users_have_public_identifiers()
    
    # همسان‌سازی حالت جهان پس از بارگذاری
    try:
        import utils as _utils_mod
        _utils_mod.load_countries()
        _utils_mod.load_country_relations()
        _utils_mod.reconcile_world_state()
    except Exception as e:
        print(f"[bootstrap] reconcile on setup error: {e}")
    # بارگذاری و همگام‌سازی جمعیت کشورها
    try:
        from jame import load_population_data, save_population_data, COUNTRY_POPULATIONS as JAM_POP
        load_population_data()
        # اگر داده‌های فایل خالی است، از پیش‌فرض utils پر کن
        try:
            from utils import COUNTRY_POPULATIONS as U_POP
            if not isinstance(JAM_POP, dict) or len(JAM_POP) <= 1:
                # بازیابی از پیش‌فرض utils
                JAM_POP.clear()
                JAM_POP.update(U_POP)
                try:
                    save_population_data()
                except Exception:
                    pass
            # آینه‌سازی در utils برای سازگاری ماژول‌ها
            U_POP.clear()
            U_POP.update(JAM_POP)
        except Exception as e:
            print(f"[bootstrap] sync population to utils failed: {e}")
    except Exception as e:
        print(f"[bootstrap] population data load error: {e}")
    
    # بارگذاری داده‌های تأیید موقعیت
    from utils import load_location_verification
    load_location_verification()
    
    # بارگذاری داده‌های سازمان ملل بعد از بارگذاری کاربران
    from utils import load_un_data, validate_un_user_after_load
    load_un_data()
    
    # بررسی اعتبار کاربر سازمان ملل بعد از بارگذاری کامل
    validate_un_user_after_load()

    TOKEN = '7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I'

    # تنظیم timeoutها و connection pool برای جلوگیری از خطاهای httpx.ConnectError
    app = ApplicationBuilder().token(TOKEN)\
        .connect_timeout(30.0)\
        .read_timeout(30.0)\
        .write_timeout(30.0)\
        .pool_timeout(60.0)\
        .connection_pool_size(512)\
        .build()
    app.add_handler(CommandHandler('start', start))
    # ثبت‌نام دستی با کامند
    async def register_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        try:
            import utils
            utils.pending_registration[user_id] = {'step': 'phone', 'phone': None}
            kb = ReplyKeyboardMarkup(
                [[KeyboardButton('📞 ارسال شماره تماس', request_contact=True)], [KeyboardButton('لغو')]], 
                resize_keyboard=True, 
                one_time_keyboard=True
            )
            await update.message.reply_text('برای ثبت‌نام، لطفاً شماره تماس خود را با دکمه زیر ارسال کنید:', reply_markup=kb)
        except Exception as e:
            await update.message.reply_text(f'خطا در شروع ثبت‌نام: {e}')

    app.add_handler(CommandHandler('register', register_cmd))
    
    # Handler برای دستورات شناسه عمومی (با /name یا بدون آن)
    app.add_handler(MessageHandler(filters.Regex(r'^/(name[A-Za-z0-9\u0600-\u06FF]+|[A-Za-z0-9]{1,})$'), handle_public_profile_command))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.CONTACT | filters.LOCATION) & (~filters.COMMAND), main_message_handler))
   
    app.add_error_handler(error_handler)
    # زمان‌بندی پردازش نتایج ترورها
    try:
        from diplomaci import process_assassination_jobs, process_assassination_games, check_and_unpin_messages
        job_queue = app.job_queue
        if job_queue is not None:
            job_queue.run_repeating(lambda ctx: asyncio.create_task(process_assassination_jobs(ctx)), interval=30, first=30)
            job_queue.run_repeating(lambda ctx: asyncio.create_task(process_assassination_games(ctx)), interval=1, first=60)
            # بررسی سنجاق پیام‌ها هر ساعت
            job_queue.run_repeating(lambda ctx: asyncio.create_task(check_and_unpin_messages(ctx)), interval=3600, first=3600)
        else:
            print("[ASSASSINATION JOB] JobQueue is not available")
    except Exception as e:
        print(f"[ASSASSINATION JOB] schedule error: {e}")
    
    # بازیابی تایمرهای تجارت در زمان startup
    from economy import restore_trade_timers
    await restore_trade_timers(app.bot)
    
    # نمایش پرداخت‌های در انتظار به ادمین
    await show_pending_payments_to_admin(app.bot)
    
    return app

async def show_pending_payments_to_admin(bot):
    """نمایش پرداخت‌های در انتظار به ادمین در startup"""
    try:
        pending_count = 0
        for user_id, payment_info in pending_payments.items():
            if payment_info.get('status') in ['waiting_receipt', 'pending_admin_approval']:
                pending_count += 1

        # شمارش پکیج‌های ویژه خریداری‌شده اما فعال‌نشده (به‌عنوان آیتم‌های معلق برای اقدام کاربر)
        try:
            unactivated_special = 0
            from utils import users as _users
            from utils import game_data as _gd
            season_now = int(_gd.get('season', 1))
            for uid, u in _users.items():
                inv = u.get('inventory', {})
                for p in inv.get('special_packages', []) or []:
                    if p.get('activated'):
                        continue
                    # اگر منقضی نشده باشد
                    purchase_season = int(p.get('purchase_season', season_now))
                    expires_after = int(p.get('expires_after_seasons', 3))
                    if (season_now - purchase_season) < expires_after:
                        unactivated_special += 1
        except Exception:
            unactivated_special = 0

        if pending_count > 0 or unactivated_special > 0:
            message = (
                f"🔄 <b>ربات راه‌اندازی شد</b>\n\n"
                f"📋 <b>پرداخت‌های در انتظار:</b> {pending_count} مورد\n"
                f"🎁 <b>پکیج‌های ویژه غیر فعال:</b> {unactivated_special} مورد\n\n"
                f"💡 برای مشاهده و مدیریت پرداخت‌ها از دستور <code>/admin</code> استفاده کنید."
            )
            
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=message,
                parse_mode='HTML'
            )
        else:
            message = (
                f"✅ <b>ربات راه‌اندازی شد</b>\n\n"
                f"📋 هیچ پرداخت یا پکیج ویژه در انتظاری وجود ندارد."
            )
            
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=message,
                parse_mode='HTML'
            )
    except Exception as e:
        print(f"[ERROR] خطا در نمایش پرداخت‌های در انتظار: {e}")

async def main():
    """تابع اصلی با قابلیت auto-reconnect"""
    max_retries = 10
    retry_delay = 30  # ثانیه
    connection_lost_time = None
    
    while True:
        try:
            # بررسی اتصال اینترنت قبل از شروع
            if not await check_internet_connection():
                if connection_lost_time is None:
                    connection_lost_time = time.time()
                    print("❌ اتصال اینترنت قطع است. منتظر اتصال مجدد...")
                else:
                    elapsed = int(time.time() - connection_lost_time)
                    print(f"❌ اتصال اینترنت قطع است. ({elapsed} ثانیه گذشته)")
                await asyncio.sleep(retry_delay)
                continue
            
            # اگر اتصال برقرار شد
            if connection_lost_time is not None:
                elapsed = int(time.time() - connection_lost_time)
                print(f"✅ اتصال اینترنت برقرار شد! (پس از {elapsed} ثانیه)")
                connection_lost_time = None
            
            print("🚀 راه‌اندازی ربات...")
            
            # راه‌اندازی ربات
            app = await setup_bot()
            
            print('🤖 ربات در حال اجرا...')
            
            # شروع مانیتورینگ اتصال در پس‌زمینه
            monitor_task = asyncio.create_task(monitor_connection(app))
            
            try:
                await app.run_polling(drop_pending_updates=True)
            finally:
                # متوقف کردن مانیتورینگ
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
            
        except Exception as e:
            print(f"❌ خطا در اجرای ربات: {e}")
            
            # بررسی نوع خطا
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in ['network', 'connection', 'timeout', 'unreachable', 'refused']):
                print("🌐 خطای شبکه تشخیص داده شد. تلاش برای اتصال مجدد...")
                connection_lost_time = time.time()
            else:
                print("⚠️ خطای غیرشبکه‌ای. تلاش مجدد...")
            
            # انتظار قبل از تلاش مجدد
            await asyncio.sleep(retry_delay)
            
            # اگر بیش از حد تلاش کردیم، مدت انتظار را افزایش دهیم
            if max_retries > 0:
                max_retries -= 1
                if max_retries == 0:
                    print("🔄 افزایش مدت انتظار به 5 دقیقه...")
                    retry_delay = 300
                    max_retries = 10
async def error_handler(update, context):
    try:
        error = context.error
        msg = str(error)
        if "Timed out" in msg:
            print(f"Timeout error occurred: {error}")
            return
        elif "'CallbackQuery' object has no attribute 'bot'" in msg:
            print(f"CallbackQuery bot attribute error: {error}")
            return
        elif "Message is not modified" in msg:
            # این خطا بی‌ضرر است؛ وقتی متن/کیبورد دقیقاً مثل قبل باشد رخ می‌دهد
            return
    except Exception as e:
        print(f"Error in error handler: {e}")
    print(f"Exception while handling an update: {error}")


# اضافه کردن منوی استراتژی با دکمه وضعیت تسلیحات
async def show_strategy_menu(query):
    user_id = str(query.from_user.id)
    user_country = utils.users.get(user_id, {}).get('country', '')
    try:
        from utils import user_has_sea_access
        has_sea = user_has_sea_access(user_id)
    except Exception:
        has_sea = user_country in SEA_BORDER_COUNTRIES
    current_turn = utils.game_data.get('turn', 1)
    user_record = utils.users.get(user_id, {})
    panel_suspensions = user_record.get('panel_suspensions', {})
    suspended_until = panel_suspensions.get('strategy', 0)
    if current_turn < suspended_until:
        # پنل استراتژی تا 2 دور پس از ترور ژنرال غیرفعال است
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_game_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = (
            "⚫️ <b>دوره سوگواری نظامی</b>\n\n"
            "در پی ترور ژنرال کشور، بخش استراتژی تا پایان دو دور آینده در دسترس نخواهد بود.\n"
            "پس از اتمام مدت سوگواری، دسترسی باز می‌گردد (بدون تحلیل ژنرال)."
        )
        await safe_edit_message(query, text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    # استفاده از ژنرال انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'general' in selected_officials:
        general = selected_officials['general']
    else:
        general = {'name': 'ژنرال', 'title': 'ژنرال'}
    
    keyboard = [
        [InlineKeyboardButton('وضعیت تسلیحات 🪖', callback_data='military_status')],
        [InlineKeyboardButton('حمله زمینی ⚔️', callback_data='ground_attack')],
        [InlineKeyboardButton('حمله هوایی 🛩️', callback_data='air_attack')],
        [InlineKeyboardButton('حمله دریایی 🌊', callback_data='naval_attack' if has_sea else 'naval_attack_locked')],
        [InlineKeyboardButton('حمله موشکی 🚀', callback_data='missile_attack')],
        [InlineKeyboardButton('اعلان جنگ 🚨', callback_data='declare_war'), InlineKeyboardButton('آتش‌بس 🤝', callback_data='peace_menu')],
        # دو ستونی کردن غارت و حمله به کشتی تجاری
        [
            InlineKeyboardButton('غارت 💰', callback_data='loot'),
            InlineKeyboardButton('حمله به کشتی تجاری 🚢', callback_data='sea_raid' if has_sea else 'sea_raid_locked')
        ],
        [InlineKeyboardButton('🎖️ قدرت واقعی نظامی', callback_data='real_military_power')],
        [InlineKeyboardButton('🛡️ امنیت ملی', callback_data='national_security_menu')],
        [InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_game_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"🎯 <b>منوی استراتژی نظامی</b>\n\n"
    text += f"⚔️ {general['name']}، {general['title']} شما آماده خدمت است.\n\n"
    
    # اضافه کردن تحلیل استراتژیک (فقط اگر ژنرال زنده باشد)
    is_alive = selected_officials.get('general', {}).get('alive', True)
    if is_alive:
        try:
            from analysis import generate_strategy_analysis
            strategy_analysis = generate_strategy_analysis(user_id)
            text += f"<b>📊 تحلیل استراتژیک {general['name']}:</b>\n"
            text += f"<blockquote>{strategy_analysis}</blockquote>\n\n"
        except Exception as e:
            text += "<b>📊 تحلیل استراتژیک:</b>\n<blockquote>خطا در تحلیل استراتژیک.</blockquote>\n\n"
            print(f"خطا در تحلیل استراتژیک: {e}")
    else:
        text += "<b>📊 تحلیل استراتژیک:</b>\n<blockquote>این مقام ترور شده و تحلیلی ارائه نمی‌شود.</blockquote>\n\n"
    
    text += "یکی از گزینه‌های زیر را انتخاب کنید:"
    
    await safe_edit_message(query, text, reply_markup=reply_markup, parse_mode='HTML')

# نمایش وضعیت نظامی کشور
async def show_military_status(query):
    user_id = str(query.from_user.id)
    if user_id not in utils.users or not utils.users[user_id].get('activated', False):
        await show_simple_section(query, 'شما هنوز کشور فعال نکرده‌اید.')
        return
    
    # Ensure user's resources are initialized before reading
    initialize_user_resources(user_id)
    
    country_name = utils.users[user_id]['country']
    
    # استفاده از مسئولین انتخاب شده
    selected_officials = utils.users[user_id].get('selected_officials', {})
    if 'general' in selected_officials:
        general = selected_officials['general']
    else:
        # اگر ژنرال انتخاب نشده، از اسامی پیش‌فرض استفاده کن
        general = {'name': 'ژنرال', 'title': 'ژنرال'}
    
    # بررسی اینکه آیا مسئولین انتخاب شده وجود دارند
    if not selected_officials:
        print(f"Warning: No selected officials for user {user_id}")
    
    # پیام خوشامدگویی نظامی
    welcome_text = f'🎖️ <b>خوش آمدید!</b>\n\n'
    welcome_text += f'⚔️ من {general["name"]}، {general["title"]} شما هستم.\n'
    welcome_text += f'🛡️ <b>وضعیت تسلیحات و نیروی نظامی کشور شما:</b>\n\n'
    
    resources = utils.users[user_id]['resources']
    military_keys = [
        "soldiers", 'special_forces', "tanks", "armored_vehicles", 'transport_planes', "helicopters", "fighter_jets", 'bombers', 'artillery', 'drones', "air_defense", 'coastal_artillery', 'speedboats', "naval_ship", "submarines", "aircraft_carriers", "war_robots", "defense_missiles", "ballistic_missiles"
    ]
    military_names = {
        "soldiers": "🪖 سربازان",
        'special_forces': '⚔️ نیروهای ویژه',
        "tanks": "🛡️ تانک",
        "armored_vehicles": "🚛 نفربر زرهی",
        'transport_planes': '✈️ هواپیمای ترابری',
        "helicopters": "🚁 بالگرد",
        "fighter_jets": "🛩️ جنگنده",
        'bombers': '💣 بمب‌افکن',
        'artillery': '🎯 توپخانه',
        'drones': '🛸 پهپاد',
        "air_defense": "🛡️ پدافند هوایی",
        'coastal_artillery': '🏖️ توپ ساحلی',
        'speedboats': '🚤 قایق تندرو',
        "naval_ship": "🚢 ناوچه",
        "submarines": "🌊 زیردریایی",
        "aircraft_carriers": "⚓ ناو هواپیمابر",
        "war_robots": "🤖 ربات جنگی",
        "defense_missiles": "🚀 موشک دفاعی",
        "ballistic_missiles": "💥 موشک بالستیک"
    }
    
    # دسته‌بندی تسلیحات
    ground_forces = ["soldiers", "special_forces", "tanks", "armored_vehicles", "artillery", "war_robots"]
    air_forces = ["transport_planes", "helicopters", "fighter_jets", "bombers", "drones", "air_defense"]
    naval_forces = ["coastal_artillery", "speedboats", "naval_ship", "submarines", "aircraft_carriers"]
    missile_forces = ["defense_missiles", "ballistic_missiles"]
    
    text = welcome_text
    
    # نیروهای زمینی
    text += '🦶 <b>نیروهای زمینی:</b>\n'
    for key in ground_forces:
        val = resources.get(key, 0)
        name = military_names.get(key, key)
        text += f'  {name}: {val:,}\n'
    
    # نیروهای هوایی
    text += '\n🛩️ <b>نیروهای هوایی:</b>\n'
    for key in air_forces:
        val = resources.get(key, 0)
        name = military_names.get(key, key)
        text += f'  {name}: {val:,}\n'
    
    # نیروهای دریایی
    text += '\n🌊 <b>نیروهای دریایی:</b>\n'
    for key in naval_forces:
        val = resources.get(key, 0)
        name = military_names.get(key, key)
        text += f'  {name}: {val:,}\n'
    
    # نیروهای موشکی
    text += '\n🚀 <b>نیروهای موشکی:</b>\n'
    for key in missile_forces:
        val = resources.get(key, 0)
        name = military_names.get(key, key)
        text += f'  {name}: {val:,}\n'
    
    # تحلیل هوشمند نظامی (فقط اگر ژنرال زنده باشد)
    is_alive = selected_officials.get('general', {}).get('alive', True)
    if is_alive:
        try:
            from analysis import generate_military_analysis
            analysis = generate_military_analysis(user_id, resources)
            text += f'\n<b>پیشنهاد {general["title"]} {general["name"]}:</b>\n<blockquote>{analysis}</blockquote>'
        except Exception as e:
            text += f'\n<b>پیشنهاد {general["title"]} {general["name"]}:</b>\n<blockquote>خطا در تحلیل نظامی.</blockquote>'
            print(f"خطا در تحلیل نظامی: {e}")
    else:
        text += f'\n<b>پیشنهاد {general["title"]} {general["name"]}:</b>\n<blockquote>این مقام ترور شده و پیشنهادی ارائه نمی‌شود.</blockquote>'
    
    keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await safe_edit_message(query, text, reply_markup=reply_markup, parse_mode='HTML')





# ==================== National Security (امنیت ملی) ====================
NATIONAL_SECURITY_BASE_COST = 250_000_000
NATIONAL_SECURITY_FEATURES = [
    ('assassination', 'ترور', 150_000_000),
    ('counter_assassination', 'ضد ترور', 100_000_000),
    ('surveillance', 'شنود', 100_000_000),
    ('counter_surveillance', 'ضد شنود', 120_000_000),
    ('intelligence', 'جمع‌آوری اطلاعات', 200_000_000),
    ('counter_intelligence', 'ضد جمع‌آوری اطلاعات', 130_000_000),
    ('sabotage', 'خرابکاری', 250_000_000),
    ('counter_sabotage', 'ضد خرابکاری', 300_000_000),
]

async def show_national_security_menu(query):
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    org = u.get('national_security_org')
    keyboard = []
    if org:
        keyboard.append([InlineKeyboardButton(f"🏢 {org.get('name','سازمان امنیتی')}", callback_data='national_security_org')])
    else:
        keyboard.append([InlineKeyboardButton('➕ ایجاد سازمان امنیتی و اطلاعاتی', callback_data='national_security_create')])
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='strategy')])
    await query.edit_message_text('🛡️ امنیت ملی', reply_markup=InlineKeyboardMarkup(keyboard))

async def start_national_security_creation(query):
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    cash = u.get('resources', {}).get('cash', 0)
    if cash < NATIONAL_SECURITY_BASE_COST:
        kb = [[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')]]
        await query.edit_message_text(f'❌ برای ایجاد سازمان امنیتی حداقل {NATIONAL_SECURITY_BASE_COST:,} دلار نیاز دارید.\nموجودی: {cash:,} دلار', reply_markup=InlineKeyboardMarkup(kb))
        return
    utils.pending_national_security[user_id] = {
        'step': 'ask_name',
        'name': None,
        'description': None,
        'logo_file_id': None,
        'features': {key: False for key, _, _ in NATIONAL_SECURITY_FEATURES}
    }
    await query.edit_message_text('🛡️ نام سازمان امنیتی و اطلاعاتی خود را وارد کنید:\nمثال: «سازمان اطلاعات ملی ...»', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('لغو ❌', callback_data='cancel_national_security')]]))

async def handle_national_security_text(update):
    user_id = str(update.effective_user.id)
    if user_id not in utils.pending_national_security:
        return False
    data = utils.pending_national_security[user_id]
    if data.get('step') == 'ask_name':
        data['name'] = (update.message.text or '').strip()[:100]
        data['step'] = 'ask_description'
        await update.message.reply_text('📝 یک توضیح کوتاه درباره سازمان ارسال کنید (حداکثر 200 کاراکتر).')
        return True
    elif data.get('step') == 'ask_description':
        data['description'] = (update.message.text or '').strip()[:200]
        data['step'] = 'ask_logo'
        kb = [[InlineKeyboardButton('⏭️ رد شدن از لوگو', callback_data='national_security_skip_logo')]]
        await update.message.reply_text('🖼️ لوگوی سازمان را ارسال کنید (یک عکس بفرستید)، یا روی «⏭️ رد شدن از لوگو» بزنید.', reply_markup=InlineKeyboardMarkup(kb))
        return True
    return False

async def handle_national_security_photo(update):
    user_id = str(update.effective_user.id)
    if user_id not in utils.pending_national_security:
        return False
    data = utils.pending_national_security[user_id]
    if data.get('step') == 'ask_logo' and update.message.photo:
        file_id = update.message.photo[-1].file_id
        data['logo_file_id'] = file_id
        await show_national_security_features(update, user_id)
        return True
    return False

def _format_features_keyboard(features_state):
    keyboard = []
    for key, fa_name, price in NATIONAL_SECURITY_FEATURES:
        state_on = bool(features_state.get(key))
        state = 'ON' if state_on else 'OFF'
        emoji = '🟢' if state_on else '⚪'
        keyboard.append([InlineKeyboardButton(f"{emoji} {fa_name} – {int(price/1_000_000)}M [{state}]", callback_data=f'toggle_ns_{key}')])
    keyboard.append([InlineKeyboardButton('🧮 مشاهده جمع کل و ادامه ➡️', callback_data='ns_summary')])
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')])
    return InlineKeyboardMarkup(keyboard)

async def show_national_security_features(message_or_update, user_id):
    data = utils.pending_national_security[user_id]
    data['step'] = 'choose_features'
    text = '⚙️ قابلیت‌ها را فعال/غیرفعال کنید.\nقیمت پایه: 250M'
    reply_markup = _format_features_keyboard(data['features'])
    try:
        # message_or_update can be Update (message) or CallbackQuery
        if hasattr(message_or_update, 'message'):
            await message_or_update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await message_or_update.edit_message_text(text, reply_markup=reply_markup)
    except Exception:
        # fallback
        if hasattr(message_or_update, 'message'):
            await message_or_update.message.reply_text(text, reply_markup=reply_markup)

def _calc_total_cost(features_state):
    total = NATIONAL_SECURITY_BASE_COST
    for key, _, price in NATIONAL_SECURITY_FEATURES:
        if features_state.get(key):
            total += price
    return total

async def toggle_national_security_feature(query, key):
    user_id = str(query.from_user.id)
    data = utils.pending_national_security.get(user_id)
    if not data or data.get('step') != 'choose_features':
        try:
            await query.answer('روند نامعتبر است.', show_alert=True)
        except Exception:
            pass
        return
    cur = bool(data['features'].get(key))
    data['features'][key] = not cur
    total = _calc_total_cost(data['features'])
    text = f'⚙️ قابلیت‌ها را فعال/غیرفعال کنید.\nقیمت پایه: 250M\n💰 هزینه کل تا این لحظه: {total:,} دلار'
    await query.edit_message_text(text, reply_markup=_format_features_keyboard(data['features']))

async def show_national_security_summary(query):
    user_id = str(query.from_user.id)
    data = utils.pending_national_security.get(user_id)
    if not data:
        try:
            await query.answer('روند نامعتبر است.', show_alert=True)
        except Exception:
            pass
        return
    total = _calc_total_cost(data['features'])
    name = data.get('name') or '—'
    desc = data.get('description') or '—'
    enabled = [fa for (k, fa, _price) in NATIONAL_SECURITY_FEATURES if data['features'].get(k)]
    enabled_text = '، '.join(enabled) if enabled else '—'
    text = (
        f"✅ خلاصه سازمان امنیتی:\n\n"
        f"🏷️ نام: {name}\n"
        f"📝 توضیحات: {desc}\n"
        f"⚙️ قابلیت‌های فعال: {enabled_text}\n"
        f"💰 هزینه کل: {total:,} دلار"
    )
    kb = [[InlineKeyboardButton('✅ تایید نهایی', callback_data='ns_confirm')], [InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def confirm_national_security(query):
    user_id = str(query.from_user.id)
    data = utils.pending_national_security.get(user_id)
    if not data:
        try:
            await query.answer('روند نامعتبر است.', show_alert=True)
        except Exception:
            pass
        return
    u = utils.users.setdefault(user_id, {})
    res = u.setdefault('resources', {})
    total = _calc_total_cost(data['features'])
    if res.get('cash', 0) < total:
        await query.edit_message_text(f'❌ موجودی کافی نیست. نیاز: {total:,} دلار\nموجودی: {res.get("cash",0):,} دلار', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')]]))
        return
    res['cash'] = res.get('cash', 0) - total
    u['national_security_org'] = {
        'name': data.get('name'),
        'description': data.get('description'),
        'logo_file_id': data.get('logo_file_id'),
        'features': data.get('features'),
        'total_cost': total,
        # initialize counter-assassination charges if feature ON
        'counter_assassination_charges': 3 if data.get('features', {}).get('counter_assassination') else 0
    }
    utils.save_users()
    utils.pending_national_security.pop(user_id, None)
    await show_national_security_menu(query)

async def open_national_security_org(query):
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    org = u.get('national_security_org')
    if not org:
        await show_national_security_menu(query)
        return
    kb = []
    features = org.get('features', {})
    
    # Primary actions: Assassination and Counter-Assassination management
    if features.get('assassination'):
        kb.append([InlineKeyboardButton('🗡️ ترور (150M)', callback_data='ns_action_assassination')])
    
    # Show counter-assassination management only if feature is enabled
    if features.get('counter_assassination'):
        charges = org.get('counter_assassination_charges', 0)
        if charges <= 0:
            kb.append([InlineKeyboardButton('🔄 شارژ ضدترور (75M)', callback_data='ns_recharge_counter')])
        else:
            kb.append([InlineKeyboardButton(f'🛡️ ضدترور فعال ({charges}/3)', callback_data='ns_counter_info')])
    
    # Espionage actions - only if feature is enabled
    if features.get('surveillance'):
        kb.append([InlineKeyboardButton('🎧 شنود', callback_data='ns_espionage_menu')])
    
    # Intelligence gathering actions - only if feature is enabled
    if features.get('intelligence'):
        kb.append([InlineKeyboardButton('📡 جمع‌آوری اطلاعات', callback_data='ns_intelligence_menu')])
    
    # Sabotage actions - only if feature is enabled
    if features.get('sabotage'):
        kb.append([InlineKeyboardButton('💣 خرابکاری', callback_data='ns_sabotage_menu')])
    
    # Also list active features as info
    for key, fa_name, _price in NATIONAL_SECURITY_FEATURES:
        if org.get('features', {}).get(key):
            kb.append([InlineKeyboardButton(f'✅ {fa_name}', callback_data='ns_noop')])
    # Entry to buy more features
    kb.append([InlineKeyboardButton('🧩 خرید قابلیت‌ها', callback_data='ns_buy_features')])
    kb.append([InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')])
    text = f"🏢 {org.get('name','سازمان امنیتی')}\n📝 {org.get('description','—')}"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def ns_pick_assassination_target(query):
    user_id = str(query.from_user.id)
    # list all active users with countries
    keyboard = []
    for uid, u in utils.users.items():
        try:
            if not u.get('activated'):
                continue
            if uid == user_id:
                continue
            country = u.get('country')
            if not country:
                continue
            keyboard.append([InlineKeyboardButton(country, callback_data=f'ns_assassinate_{uid}')])
        except Exception:
            continue
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')])
    await query.edit_message_text('🎯 هدف ترور را انتخاب کنید:', reply_markup=InlineKeyboardMarkup(keyboard))

async def ns_confirm_assassination(query, target_uid):
    user_id = str(query.from_user.id)
    attacker_country = utils.users.get(user_id, {}).get('country', '—')
    target_country = utils.users.get(target_uid, {}).get('country', '—')
    text = (
        f"⚠️ آیا از اقدام به ترور علیه {target_country} مطمئن هستید؟\n"
        f"💰 هزینه: 150M"
    )
    kb = [
        [InlineKeyboardButton('✅ تایید', callback_data=f'ns_confirm_assassination_{target_uid}')],
        [InlineKeyboardButton('❌ انصراف', callback_data='national_security_menu')]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def ns_execute_assassination(query, target_uid):
    user_id = str(query.from_user.id)
    attacker = utils.users.get(user_id, {})
    target = utils.users.get(target_uid, {})
    if not attacker.get('activated') or not target.get('activated'):
        await query.edit_message_text('❌ هدف معتبر نیست.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')]]))
        return
    # cost check
    if attacker.get('resources', {}).get('cash', 0) < 150_000_000:
        await query.edit_message_text('❌ موجودی کافی نیست.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')]]))
        return
    attacker['resources']['cash'] -= 150_000_000
    # determine defense
    defense_used = False
    success_chance = 0.6  # default when no counter
    t_org = target.get('national_security_org') or {}
    if t_org.get('counter_assassination_charges', 0) > 0:
        # consume one charge and apply 80% defense
        t_org['counter_assassination_charges'] = max(0, int(t_org.get('counter_assassination_charges')) - 1)
        defense_used = True
        success_chance = 0.2
    import random
    success = random.random() < success_chance
    # logs
    attacker.setdefault('security_logs', []).append({'type': 'assassination', 'target': target.get('country'), 'cost': 150_000_000, 'success': success})
    target.setdefault('security_logs', []).append({'type': 'assassination_targeted', 'by': attacker.get('country'), 'defense_used': defense_used, 'success': success})
    utils.save_users()
    # messaging with new rules
    attacker_country = attacker.get('country', '—')
    target_country = target.get('country', '—')
    try:
        if success:
            # SUCCESS: Hide attacker identity in public news
            news = f"🚨 خبر فوری! رهبر {target_country} در عملیات ترور به قتل رسید. کشور وارد دوران بی‌ثباتی شد."
            await send_assassination_news(news, image_url="https://t.me/TextEmpire_IR/136")
            await query.edit_message_text(f'✅ عملیات ترور علیه {target_country} با موفقیت انجام شد. هویت شما مخفی ماند.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')]]))
            
            # Lock victim for 6 turns
            current_turn = utils.game_data.get('turn', 1)
            target['assassination_lock'] = {
                'locked_until_turn': current_turn + 6,
                'locked_at_turn': current_turn,
                'original_name': target.get('player_name', ''),
                'original_title': target.get('government_title', '')
            }
            target['activated'] = False  # deactivate temporarily
            try:
                target.setdefault('profile', {})['has_country'] = False
            except Exception:
                pass
            
            try:
                await send_private_message(target_uid, '  ثبتنام جدید نکنید و صبوری فرمایید 🚨 رهبر شما ترور شد! کشور برای 6 دور قفل خواهد شد.', image_url="https://t.me/TextEmpire_IR/136")
            except Exception:
                pass
        else:
            # FAILURE: Reveal attacker identity in public news
            news = f"🚨 عملیات ترور شکست خورد! کشور {attacker_country} تلاش کرد رهبر {target_country} را ترور کند اما ناکام ماند."
            await send_assassination_news(news, image_url="https://t.me/TextEmpire_IR/136")
            await query.edit_message_text(f'❌ عملیات ترور شما علیه {target_country} شکست خورد. 150M از حساب شما کسر شد.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')]]))
            try:
                await send_private_message(target_uid, f'🛡️ کشور {attacker_country} قصد داشت شما را ترور کند اما ناکام ماند.', image_url="https://t.me/TextEmpire_IR/136")
            except Exception:
                pass
    except Exception as e:
        print(f"Error sending news/DM: {e}")

async def ns_recharge_counter_assassination(query):
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    org = u.get('national_security_org') or {}
    if u.get('resources', {}).get('cash', 0) < 75_000_000:
        await query.edit_message_text('❌ موجودی کافی برای شارژ ندارید. هزینه: 75M', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')]]))
        return
    u['resources']['cash'] -= 75_000_000
    org['counter_assassination_charges'] = 3
    u['national_security_org'] = org
    utils.save_users()
    await query.edit_message_text('✅ ضدترور با موفقیت برای 3 بار شارژ شد.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')]]))

async def ns_show_counter_info(query):
    user_id = str(query.from_user.id)
    charges = utils.users.get(user_id, {}).get('national_security_org', {}).get('counter_assassination_charges', 0)
    await query.edit_message_text(f'🛡️ ضدترور فعال: {charges}/3', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')]]))

async def ns_buy_features_menu(query):
    """Show menu to buy and enable features not enabled during creation."""
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    org = u.get('national_security_org') or {}
    if not org:
        await query.edit_message_text('❌ ابتدا باید سازمان امنیتی ایجاد کنید.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')]]))
        return
    features_state = org.get('features', {})
    keyboard = []
    text_lines = ['🧩 خرید و فعال‌سازی قابلیت‌ها', '', 'قابلیت‌های غیرفعال قابل خرید:']
    any_option = False
    for key, fa_name, price in NATIONAL_SECURITY_FEATURES:
        if not features_state.get(key):
            any_option = True
            keyboard.append([InlineKeyboardButton(f"🧩 {fa_name} – {int(price/1_000_000)}M", callback_data=f'ns_buy_feature_{key}')])
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_org')])
    if not any_option:
        await query.edit_message_text('✅ همه قابلیت‌ها فعال هستند.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_org')]]))
        return
    await query.edit_message_text('\n'.join(text_lines), reply_markup=InlineKeyboardMarkup(keyboard))

async def ns_buy_feature_execute(query, key):
    """Deduct cost and enable a single feature permanently."""
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    org = u.get('national_security_org') or {}
    if not org:
        await query.edit_message_text('❌ ابتدا باید سازمان امنیتی ایجاد کنید.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_menu')]]))
        return
    # Find feature meta
    meta = next(((k, name, price) for (k, name, price) in NATIONAL_SECURITY_FEATURES if k == key), None)
    if not meta:
        await query.edit_message_text('❌ قابلیت نامعتبر است.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_org')]]))
        return
    _k, fa_name, price = meta
    if org.get('features', {}).get(key):
        await query.edit_message_text('ℹ️ این قابلیت هم‌اکنون فعال است.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_org')]]))
        return
    cash = u.get('resources', {}).get('cash', 0)
    if cash < price:
        await query.edit_message_text(f'❌ موجودی کافی نیست. نیاز: {price:,} دلار\nموجودی: {cash:,} دلار', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_buy_features')]]))
        return
    # Deduct and enable
    u.setdefault('resources', {})
    u['resources']['cash'] = cash - price
    org.setdefault('features', {})
    org['features'][key] = True
    # One-time side-effects for specific features
    if key == 'counter_assassination':
        # grant starting charges if buying later
        org['counter_assassination_charges'] = 3
    u['national_security_org'] = org
    utils.save_users()
    await query.edit_message_text(f'✅ {fa_name} با موفقیت فعال شد.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_buy_features')]]))

# ==================== Assassination Respawn System ====================

async def check_assassination_respawns():
    """Check for users who need to respawn after assassination lock expires"""
    current_turn = utils.game_data.get('turn', 1)
    for user_id, user in utils.users.items():
        assassination_lock = user.get('assassination_lock')
        if assassination_lock and assassination_lock.get('locked_until_turn', 0) <= current_turn:
            if not user.get('activated', False):  # still locked
                # Time to respawn
                pending_assassination_respawn[user_id] = {
                    'original_name': assassination_lock.get('original_name', ''),
                    'original_title': assassination_lock.get('original_title', ''),
                    'country': user.get('country', '')
                }
                try:
                    await bot.send_message(chat_id=int(user_id), text='مردم کشور شما رهبر جدیدی می‌خواهند. لطفاً نام جدید خود را وارد کنید.')
                except Exception as e:
                    print(f"Error sending respawn message to {user_id}: {e}")

async def handle_assassination_respawn_text(update):
    """Handle new name input for assassination respawn"""
    user_id = str(update.effective_user.id)
    if user_id not in pending_assassination_respawn:
        return False
    
    new_name = (update.message.text or '').strip()
    if not new_name or len(new_name) < 2:
        await update.message.reply_text('لطفاً نام معتبری وارد کنید (حداقل 2 کاراکتر).')
        return True
    
    respawn_data = pending_assassination_respawn[user_id]
    user = utils.users.get(str(user_id), {})
    
    # Restore user with new leader name (country display only)
    utils.users[user_id]['government_title'] = respawn_data.get('original_title', 'رهبر')
    # ذخیره نام جدید فقط برای نمایش کشوری
    utils.users[user_id]['country_leader_name'] = new_name
    utils.users[user_id]['activated'] = True
    # همگام‌سازی وضعیت کشورها با users تا taken درست تنظیم شود
    try:
        from utils import reconcile_world_state
        reconcile_world_state()
    except Exception:
        pass
    utils.users[user_id].pop('assassination_lock', None)
    
    # شناسه عمومی و player_name تغییر نمی‌کنند
    
    # Send ceremonial news
    country = respawn_data.get('country', 'کشور')
    title = respawn_data.get('original_title', 'رهبر')
    news = (
        f"📢 خبر فوری از خبرگزاری جهانی امپایر\n\n"
        f"پس از شش دور آشوب و سردرگمی، مردم {country} رهبر جدیدی را برگزیدند.\n"
        f"«{title} {new_name}» با تشریفات رسمی و استقبال گسترده به قدرت رسید."
    )
    
    try:
        await bot.send_photo(
            chat_id=utils.NEWS_CHANNEL_ID,
            photo="https://t.me/TextEmpire_IR/181",
            caption=news
        )
    except Exception as e:
        print(f"Error sending ceremonial news: {e}")
    
    # Send welcome message to user
    welcome_msg = f"🎉 تبریک! شما با نام جدید '{new_name}' دوباره به رهبری {country} بازگشتید."
    await update.message.reply_text(welcome_msg)
    
    # Clean up
    pending_assassination_respawn.pop(user_id, None)
    utils.save_users()
    
    return True

# ==================== end Assassination Respawn System ====================

# ==================== Espionage System ====================

async def show_espionage_menu(query):
    """Show espionage options menu"""
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    org = u.get('national_security_org', {})
    
    # Check if user has surveillance feature
    if not org.get('features', {}).get('surveillance'):
        await query.edit_message_text(
            '❌ برای استفاده از شنود، ابتدا باید قابلیت "شنود" را در سازمان امنیتی خود فعال کنید.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_org')]])
        )
        return
    
    keyboard = [
        [InlineKeyboardButton('🎧 شنود اتحاد (100M)', callback_data='ns_spy_alliance')],
        [InlineKeyboardButton('🎧 شنود کشور (50M)', callback_data='ns_spy_country')],
        [InlineKeyboardButton('🔒 ضد شنود (150M)', callback_data='ns_anti_spy')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_org')]
    ]
    
    await query.edit_message_text(
        '🎧 <b>منوی شنود و ضد شنود</b>\n\n'
        'یکی از گزینه‌های زیر را انتخاب کنید:',
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_alliance_spy_targets(query):
    """Show alliance targets for spying"""
    user_id = str(query.from_user.id)
    
    # Get all active alliances
    active_alliances = []
    for alliance_id, alliance in utils.alliances.items():
        if alliance.get('active', True) and len(alliance.get('members', [])) > 0:
            active_alliances.append((alliance_id, alliance['name']))
    
    if not active_alliances:
        await query.edit_message_text(
            '❌ هیچ اتحاد فعالی برای شنود یافت نشد.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_espionage_menu')]])
        )
        return
    
    keyboard = []
    for alliance_id, alliance_name in active_alliances:
        keyboard.append([InlineKeyboardButton(f'🤝 {alliance_name}', callback_data=f'ns_spy_alliance_{alliance_id}')])
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='ns_espionage_menu')])
    
    await query.edit_message_text(
        '🎧 اتحاد مورد نظر برای شنود را انتخاب کنید:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_country_spy_targets(query):
    """Show country targets for spying"""
    user_id = str(query.from_user.id)
    sender_country = utils.users.get(user_id, {}).get('country', '')
    
    # Get all active countries except sender
    active_countries = []
    for uid, user in utils.users.items():
        if (user.get('activated', False) and 
            uid != user_id and 
            user.get('country') and 
            user.get('country') != sender_country):
            active_countries.append((uid, user.get('country')))
    
    if not active_countries:
        await query.edit_message_text(
            '❌ هیچ کشور فعالی برای شنود یافت نشد.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_espionage_menu')]])
        )
        return
    
    # Create 2-column layout
    keyboard = []
    for i in range(0, len(active_countries), 2):
        row = []
        # First country in row
        uid, country = active_countries[i]
        row.append(InlineKeyboardButton(f"🇺🇳 {country}", callback_data=f'ns_spy_country_{uid}'))
        
        # Second country in row (if exists)
        if i + 1 < len(active_countries):
            uid2, country2 = active_countries[i + 1]
            row.append(InlineKeyboardButton(f"🇺🇳 {country2}", callback_data=f'ns_spy_country_{uid2}'))
        
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='ns_espionage_menu')])
    
    await query.edit_message_text(
        '🎧 کشور مورد نظر برای شنود را انتخاب کنید:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_alliance_spy(query, alliance_id):
    """Confirm alliance spying"""
    alliance = utils.alliances.get(alliance_id, {})
    alliance_name = alliance.get('name', 'اتحاد ناشناس')
    
    text = f"⚠️ آیا می‌خواهید اتحاد {alliance_name} را برای 1 دور شنود کنید؟\n💰 هزینه: 100M"
    keyboard = [
        [InlineKeyboardButton('✅ بله', callback_data=f'ns_confirm_alliance_spy_{alliance_id}')],
        [InlineKeyboardButton('❌ خیر', callback_data='ns_spy_alliance')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def confirm_country_spy(query, target_uid):
    """Confirm country spying"""
    target_country = utils.users.get(target_uid, {}).get('country', 'کشور ناشناس')
    
    text = f"⚠️ آیا می‌خواهید کشور {target_country} را برای 3 دور شنود کنید؟\n💰 هزینه: 50M"
    keyboard = [
        [InlineKeyboardButton('✅ بله', callback_data=f'ns_confirm_country_spy_{target_uid}')],
        [InlineKeyboardButton('❌ خیر', callback_data='ns_spy_country')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def execute_alliance_spy(query, alliance_id):
    """Execute alliance spying"""
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    
    # Check cost
    if u.get('resources', {}).get('cash', 0) < 100_000_000:
        await query.edit_message_text(
            '❌ موجودی کافی نیست. نیاز: 100M',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_espionage_menu')]])
        )
        return
    
    # Deduct cost
    u['resources']['cash'] -= 100_000_000
    
    # Set spying effect
    current_turn = utils.game_data.get('turn', 1)
    if 'espionage_effects' not in u:
        u['espionage_effects'] = {}
    
    u['espionage_effects']['alliance_spy'] = {
        'alliance_id': alliance_id,
        'expires_at_turn': current_turn + 1,
        'type': 'alliance_spy'
    }
    
    utils.save_users()
    
    alliance_name = utils.alliances.get(alliance_id, {}).get('name', 'اتحاد')
    await query.edit_message_text(
        f'✅ شنود اتحاد {alliance_name} فعال شد. تا پایان دور بعدی تمام پیام‌های اتحاد به شما ارسال می‌شود.',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_espionage_menu')]])
    )

async def execute_country_spy(query, target_uid):
    """Execute country spying"""
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    target = utils.users.get(target_uid, {})
    
    # Check if target has anti-spy protection
    target_org = target.get('national_security_org', {})
    if target_org.get('anti_spy_active', False):
        await query.edit_message_text(
            '❌ کشور هدف دارای حفاظت ضد شنود است. شنود ناموفق بود.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_espionage_menu')]])
        )
        return
    
    # Check cost
    if u.get('resources', {}).get('cash', 0) < 50_000_000:
        await query.edit_message_text(
            '❌ موجودی کافی نیست. نیاز: 50M',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_espionage_menu')]])
        )
        return
    
    # Deduct cost
    u['resources']['cash'] -= 50_000_000
    
    # Set spying effect
    current_turn = utils.game_data.get('turn', 1)
    if 'espionage_effects' not in u:
        u['espionage_effects'] = {}
    
    u['espionage_effects']['country_spy'] = {
        'target_uid': target_uid,
        'expires_at_turn': current_turn + 3,
        'type': 'country_spy'
    }
    
    utils.save_users()
    
    target_country = target.get('country', 'کشور')
    await query.edit_message_text(
        f'✅ شنود کشور {target_country} فعال شد. تا 3 دور آینده تمام پیام‌های خصوصی به شما ارسال می‌شود.',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_espionage_menu')]])
    )

async def execute_anti_spy(query):
    """Execute anti-spy protection"""
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    
    # Check cost
    if u.get('resources', {}).get('cash', 0) < 150_000_000:
        await query.edit_message_text(
            '❌ موجودی کافی نیست. نیاز: 150M',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_espionage_menu')]])
        )
        return
    
    # Deduct cost
    u['resources']['cash'] -= 150_000_000
    
    # Set anti-spy protection
    current_turn = utils.game_data.get('turn', 1)
    org = u.get('national_security_org', {})
    org['anti_spy_active'] = True
    org['anti_spy_expires_at'] = current_turn + 10
    u['national_security_org'] = org
    
    utils.save_users()
    
    await query.edit_message_text(
        f'✅ حفاظت ضد شنود فعال شد. تا 10 دور آینده از شنود محافظت می‌شوید.',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_espionage_menu')]])
    )

async def process_espionage_effects():
    """Process espionage effects and clean up expired ones"""
    current_turn = utils.game_data.get('turn', 1)
    
    for user_id, user in utils.users.items():
        espionage_effects = user.get('espionage_effects', {})
        
        # Clean up expired effects
        for effect_type, effect_data in list(espionage_effects.items()):
            if effect_data.get('expires_at_turn', 0) <= current_turn:
                del espionage_effects[effect_type]
        
        # Clean up expired anti-spy
        org = user.get('national_security_org', {})
        if org.get('anti_spy_expires_at', 0) <= current_turn:
            org['anti_spy_active'] = False
            org.pop('anti_spy_expires_at', None)
            user['national_security_org'] = org
    
    utils.save_users()

# ==================== end Espionage System ====================

# ==================== Intelligence Gathering System ====================

async def show_intelligence_menu(query):
    """Show intelligence gathering options menu"""
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    org = u.get('national_security_org', {})
    
    # Check if user has intelligence feature
    if not org.get('features', {}).get('intelligence'):
        await query.edit_message_text(
            '❌ برای استفاده از جمع‌آوری اطلاعات، ابتدا باید قابلیت "جمع‌آوری اطلاعات" را در سازمان امنیتی خود فعال کنید.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_org')]])
        )
        return
    
    keyboard = [
        [InlineKeyboardButton('📡 جمع‌آوری اطلاعات (50M)', callback_data='ns_intel_gather')],
        [InlineKeyboardButton('🛰 ضد جمع‌آوری اطلاعات (150M)', callback_data='ns_anti_intel')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_org')]
    ]
    
    await query.edit_message_text(
        '📡 <b>منوی جمع‌آوری اطلاعات</b>\n\n'
        'یکی از گزینه‌های زیر را انتخاب کنید:',
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_intelligence_categories(query):
    """Show intelligence gathering categories"""
    keyboard = [
        [InlineKeyboardButton('⚔️ نظامی', callback_data='ns_intel_military')],
        [InlineKeyboardButton('💰 منابع', callback_data='ns_intel_resources')],
        [InlineKeyboardButton('🔬 فناوری', callback_data='ns_intel_technology')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='ns_intelligence_menu')]
    ]
    
    await query.edit_message_text(
        '📡 <b>انتخاب نوع اطلاعات</b>\n\n'
        'کدام نوع اطلاعات را می‌خواهید جمع‌آوری کنید؟\n'
        '💰 هزینه: 50M برای هر تلاش',
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_intelligence_targets(query, category):
    """Show targets for intelligence gathering"""
    user_id = str(query.from_user.id)
    sender_country = utils.users.get(user_id, {}).get('country', '')
    
    # Get all active countries except sender
    active_countries = []
    for uid, user in utils.users.items():
        if (user.get('activated', False) and 
            uid != user_id and 
            user.get('country') and 
            user.get('country') != sender_country):
            active_countries.append((uid, user.get('country')))
    
    if not active_countries:
        await query.edit_message_text(
            '❌ هیچ کشور فعالی برای جمع‌آوری اطلاعات یافت نشد.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_intel_gather')]])
        )
        return
    
    # Create 2-column layout
    keyboard = []
    for i in range(0, len(active_countries), 2):
        row = []
        # First country in row
        uid, country = active_countries[i]
        row.append(InlineKeyboardButton(f"🇺🇳 {country}", callback_data=f'ns_intel_target_{category}_{uid}'))
        
        # Second country in row (if exists)
        if i + 1 < len(active_countries):
            uid2, country2 = active_countries[i + 1]
            row.append(InlineKeyboardButton(f"🇺🇳 {country2}", callback_data=f'ns_intel_target_{category}_{uid2}'))
        
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='ns_intel_gather')])
    
    category_names = {
        'military': 'نظامی',
        'resources': 'منابع', 
        'technology': 'فناوری'
    }
    
    await query.edit_message_text(
        f'📡 کشور مورد نظر برای جمع‌آوری اطلاعات {category_names.get(category, category)} را انتخاب کنید:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_intelligence_gathering(query, category, target_uid):
    """Confirm intelligence gathering operation"""
    target_country = utils.users.get(target_uid, {}).get('country', 'کشور ناشناس')
    
    category_names = {
        'military': 'نظامی',
        'resources': 'منابع',
        'technology': 'فناوری'
    }
    
    text = f"⚠️ آیا می‌خواهید اطلاعات {category_names.get(category, category)} کشور {target_country} را جمع‌آوری کنید؟\n💰 هزینه: 50M\n🎯 شانس موفقیت: 70%"
    keyboard = [
        [InlineKeyboardButton('✅ بله', callback_data=f'ns_confirm_intel_{category}_{target_uid}')],
        [InlineKeyboardButton('❌ خیر', callback_data=f'ns_intel_{category}')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def execute_intelligence_gathering(query, category, target_uid):
    """Execute intelligence gathering operation"""
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    target = utils.users.get(target_uid, {})
    
    # Check if target has anti-intelligence protection
    target_org = target.get('national_security_org', {})
    anti_intel_charges = target_org.get('anti_intelligence_charges', 0)
    
    if anti_intel_charges > 0:
        # Consume one charge
        target_org['anti_intelligence_charges'] -= 1
        target['national_security_org'] = target_org
        utils.save_users()
        
        # Send messages for failed attempt due to protection
        await send_intelligence_news(
            f"🛰 عملیات جاسوسی علیه کشور {target.get('country', 'ناشناس')} با شکست مواجه شد.",
            reveal_attacker=False,
            image_url="https://t.me/TextEmpire_IR/137"
        )
        
        await send_private_message(user_id, "عملیات شما ناموفق بود. هدف تحت حفاظت امنیتی بود.", image_url="https://t.me/TextEmpire_IR/137")
        await send_private_message(target_uid, "کشور شما تحت حفاظت ضدجاسوسی قرار داشت و امنیت حفظ شد.", image_url="https://t.me/TextEmpire_IR/137")
        
        await query.edit_message_text(
            '❌ عملیات ناموفق بود. کشور هدف تحت حفاظت ضدجاسوسی قرار دارد.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_intelligence_menu')]])
        )
        return
    
    # Check cost
    if u.get('resources', {}).get('cash', 0) < 50_000_000:
        await query.edit_message_text(
            '❌ موجودی کافی نیست. نیاز: 50M',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_intelligence_menu')]])
        )
        return
    
    # Deduct cost
    u['resources']['cash'] -= 50_000_000
    
    # Determine success (70% chance)
    success = random.random() < 0.7
    
    if success:
        # Success - gather information
        info = gather_target_information(target, category)
        
        # Send success messages
        await send_intelligence_news(
            f"🛰 عملیات جاسوسی در کشور {target.get('country', 'ناشناس')} موفقیت‌آمیز بود.\nبخشی از اطلاعات حساس این کشور لو رفت.",
            reveal_attacker=False,
            image_url="https://t.me/TextEmpire_IR/137"
        )
        
        category_names = {
            'military': 'نظامی',
            'resources': 'منابع',
            'technology': 'فناوری'
        }
        
        await send_private_message(user_id, f"عملیات جاسوسی موفق بود. اطلاعات بخش {category_names.get(category, category)} دریافت شد:\n\n{info}", image_url="https://t.me/TextEmpire_IR/137")
        await send_private_message(target_uid, f"🚨 کشور شما هدف جاسوسی قرار گرفت. اطلاعات بخش {category_names.get(category, category)} لو رفت.", image_url="https://t.me/TextEmpire_IR/137")
        
        await query.edit_message_text(
            f'✅ عملیات جاسوسی موفق بود! اطلاعات {category_names.get(category, category)} دریافت شد.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_intelligence_menu')]])
        )
    else:
        # Failure - reveal attacker
        await send_intelligence_news(
            f"🛰 عملیات جاسوسی کشور {u.get('country', 'ناشناس')} علیه {target.get('country', 'ناشناس')} شکست خورد و لو رفت.",
            reveal_attacker=True,
            image_url="https://t.me/TextEmpire_IR/137"
        )
        
        await send_private_message(user_id, "عملیات جاسوسی شکست خورد. 50M از حساب شما کسر شد.", image_url="https://t.me/TextEmpire_IR/137")
        await send_private_message(target_uid, f"کشور {u.get('country', 'ناشناس')} قصد جاسوسی از شما داشت اما ناکام ماند.", image_url="https://t.me/TextEmpire_IR/137")
        
        await query.edit_message_text(
            '❌ عملیات جاسوسی شکست خورد و لو رفت.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_intelligence_menu')]])
        )
    
    utils.save_users()

def gather_target_information(target, category):
    """Gather specific information about target based on category"""
    # منابع و نیروها همگی در target['resources'] ذخیره می‌شوند
    resources = target.get('resources', {}) or {}
    user_id = str(target.get('user_id', target.get('userId', '')))

    # نگاشت نام فارسی نیروهای نظامی
    military_map = [
        ('soldiers', 'سربازان'),
        ('special_forces', 'نیروی ویژه'),
        ('tanks', 'تانک'),
        ('armored_vehicles', 'نفربر'),
        ('artillery', 'توپخانه'),
        ('war_robots', 'ربات جنگی'),
        ('transport_planes', 'هواپیمای ترابری'),
        ('helicopters', 'بالگرد'),
        ('fighter_jets', 'جنگنده'),
        ('bombers', 'بمب‌افکن'),
        ('drones', 'پهپاد'),
        ('air_defense', 'پدافند هوایی'),
        ('coastal_artillery', 'توپخانه ساحلی'),
        ('speedboats', 'قایق تندرو'),
        ('naval_ship', 'ناو جنگی'),
        ('submarines', 'زیردریایی'),
        ('aircraft_carriers', 'ناو هواپیمابر'),
        ('defense_missiles', 'موشک دفاعی'),
        ('ballistic_missiles', 'موشک بالستیک'),
    ]

    # کلیدهای منابع غیرنظامی (نمایش در بخش منابع)
    resource_keys = [
        ('cash', 'نقدینگی'),
        ('gold', 'طلا'), ('steel', 'فولاد'), ('iron', 'آهن'), ('copper', 'مس'), ('diamond', 'الماس'),
        ('uranium', 'اورانیوم'), ('uranium_ore', 'سنگ اورانیوم'), ('yellowcake', 'کیک زرد'),
        ('wheat', 'گندم'), ('rice', 'برنج'), ('fruits', 'میوه'),
        ('oil', 'نفت'), ('gas', 'گاز'), ('electricity', 'برق'),
        ('electronics', 'الکترونیک'), ('space_parts', 'قطعات فضایی'),
        ('aluminum', 'آلومینیوم'), ('titanium', 'تیتانیوم'),
        ('pride_cars', 'خودرو پراید'), ('benz_cars', 'خودرو بنز'),
        ('centrifuge', 'سانتریفیوژ'),
    ]

    if category == 'military':
        info = "📊 اطلاعات نظامی:\n"
        for key, fa in military_map:
            val = int(resources.get(key, 0) or 0)
            if val > 0:
                info += f"• {fa}: {val:,}\n"
        return info if info.strip() != "📊 اطلاعات نظامی:" else "اطلاعات نظامی قابل‌نمایش یافت نشد."

    elif category == 'resources':
        info = "💰 اطلاعات منابع:\n"
        for key, fa in resource_keys:
            val = resources.get(key, 0)
            try:
                val = int(val)
            except Exception:
                continue
            if val > 0:
                info += f"• {fa}: {val:,}\n"
        return info if info.strip() != "💰 اطلاعات منابع:" else "اطلاعات منابع قابل‌نمایش یافت نشد."

    elif category == 'technology':
        info = "🔬 اطلاعات فناوری:\n"
        # فناوری نظامی
        try:
            from utils import military_technologies
            techs = military_technologies.get(str(target.get('user_id', '')), {})
            if not techs and user_id:
                techs = military_technologies.get(user_id, {})
            tech_names = {
                'soldiers': 'سربازان', 'special_forces': 'نیروهای ویژه', 'tanks': 'تانک‌ها',
                'armored_vehicles': 'خودروهای زرهی', 'transport_planes': 'هواپیماهای ترابری',
                'helicopters': 'هلیکوپترها', 'fighter_jets': 'جت‌های جنگنده', 'bombers': 'بمب‌افکن‌ها',
                'artillery': 'توپخانه', 'drones': 'پهپادها', 'air_defense': 'پدافند هوایی',
                'coastal_artillery': 'توپخانه ساحلی', 'speedboats': 'قایق‌های تندرو', 'naval_ship': 'کشتی‌های جنگی',
                'submarines': 'زیردریایی‌ها', 'aircraft_carriers': 'ناوهای هواپیمابر',
                'war_robots': 'ربات‌های جنگی', 'ballistic_missiles': 'موشک‌های بالستیک',
                'defense_missiles': 'موشک‌های دفاعی'
            }
            info += "\n⚔️ فناوری‌های نظامی:\n"
            any_mil = False
            for k, lvl in techs.items():
                try:
                    lvl = int(lvl)
                except Exception:
                    continue
                if lvl > 0:
                    any_mil = True
                    fa = tech_names.get(k, k)
                    info += f"• {fa}: لول {lvl}\n"
            if not any_mil:
                info += "• موردی ثبت نشده\n"
        except Exception:
            pass

        # فناوری تولید (اقتصادی)
        prod = target.get('production_tech_levels', {}) or {}
        prod_names = {
            # نمونه نام‌ها؛ بر اساس کلیدهای واقعی شما قابل گسترش است
            'iron_mine': 'تولید معدن آهن',
            'uranium_ore_mine': 'تولید معدن سنگ اورانیوم',
            'copper_mine': 'تولید معدن مس',
            'gold_mine': 'تولید معدن طلا',
            'diamond_mine': 'تولید معدن الماس',
            'aluminum_mine': 'تولید معدن آلومینیوم',
            'titanium_mine': 'تولید معدن تیتانیوم',
            'wheat_farm': 'تولید مزرعه گندم',
            'rice_farm': 'تولید مزرعه برنج',
            'fruit_farm': 'تولید مزرعه میوه',
            'steel_factory': 'تولید کارخانه فولاد',
            'yellowcake_factory': 'تولید کارخانه کیک زرد',
            'space_parts_factory': 'تولید کارخانه قطعات فضایی',
            'pride_line': 'خط تولید پراید',
            'benz_line': 'خط تولید بنز',
            'electronics_line': 'خط تولید الکترونیک',
        }
        info += "\n🏭 فناوری‌های تولید:\n"
        any_prod = False
        for k, lvl in prod.items():
            try:
                lvl = int(lvl)
            except Exception:
                continue
            if lvl > 0:
                any_prod = True
                fa = prod_names.get(k, k)
                info += f"• {fa}: لول {lvl}\n"
        if not any_prod:
            info += "• موردی ثبت نشده\n"

        return info

    return "اطلاعات یافت نشد."

async def execute_anti_intelligence(query):
    """Execute anti-intelligence protection"""
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    
    # Check cost
    if u.get('resources', {}).get('cash', 0) < 150_000_000:
        await query.edit_message_text(
            '❌ موجودی کافی نیست. نیاز: 150M',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_intelligence_menu')]])
        )
        return
    
    # Deduct cost
    u['resources']['cash'] -= 150_000_000
    
    # Set anti-intelligence protection
    org = u.get('national_security_org', {})
    org['anti_intelligence_charges'] = 3
    u['national_security_org'] = org
    
    utils.save_users()
    
    await query.edit_message_text(
        f'✅ حفاظت ضدجاسوسی فعال شد. 3 بار محافظت در برابر جمع‌آوری اطلاعات دریافت کردید.',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_intelligence_menu')]])
    )

async def send_intelligence_news(message, reveal_attacker=False, image_url=None):
    """Send intelligence news to channel"""
    try:
        from telegram import Bot
        bot = Bot(token=utils.BOT_TOKEN)
        
        if image_url:
            # Send image with caption
            await bot.send_photo(
                chat_id=utils.NEWS_CHANNEL_ID, 
                photo=image_url,
                caption=message
            )
        else:
            # Send text message
            await bot.send_message(chat_id=utils.NEWS_CHANNEL_ID, text=message)
    except Exception as e:
        print(f"Error sending intelligence news: {e}")

async def send_private_message(user_id, message, image_url=None):
    """Send private message to user"""
    try:
        from telegram import Bot
        bot = Bot(token=utils.BOT_TOKEN)
        
        if image_url:
            # Send image with caption
            await bot.send_photo(
                chat_id=int(user_id), 
                photo=image_url,
                caption=message
            )
        else:
            # Send text message
            await bot.send_message(chat_id=int(user_id), text=message)
    except Exception as e:
        print(f"Error sending private message: {e}")

# ==================== end Intelligence Gathering System ====================

# ==================== Sabotage System ====================

async def show_sabotage_menu(query):
    """Show sabotage options menu"""
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    org = u.get('national_security_org', {})
    
    # Check if user has sabotage feature
    if not org.get('features', {}).get('sabotage'):
        await query.edit_message_text(
            '❌ برای استفاده از خرابکاری، ابتدا باید قابلیت "خرابکاری" را در سازمان امنیتی خود فعال کنید.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_org')]])
        )
        return
    
    keyboard = [
        [InlineKeyboardButton('💣 خرابکاری (50M per mine)', callback_data='ns_sabotage_execute')],
        [InlineKeyboardButton('🛡 ضد خرابکاری (200M)', callback_data='ns_anti_sabotage')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='national_security_org')]
    ]
    
    await query.edit_message_text(
        '💣 <b>منوی خرابکاری</b>\n\n'
        'یکی از گزینه‌های زیر را انتخاب کنید:',
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def show_sabotage_targets(query):
    """Show targets for sabotage operations"""
    user_id = str(query.from_user.id)
    sender_country = utils.users.get(user_id, {}).get('country', '')
    
    # Get all active countries except sender
    active_countries = []
    for uid, user in utils.users.items():
        if (user.get('activated', False) and 
            uid != user_id and 
            user.get('country') and 
            user.get('country') != sender_country):
            active_countries.append((uid, user.get('country')))
    
    if not active_countries:
        await query.edit_message_text(
            '❌ هیچ کشور فعالی برای خرابکاری یافت نشد.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_sabotage_menu')]])
        )
        return
    
    # Create 2-column layout
    keyboard = []
    for i in range(0, len(active_countries), 2):
        row = []
        # First country in row
        uid, country = active_countries[i]
        row.append(InlineKeyboardButton(f"🇺🇳 {country}", callback_data=f'ns_sabotage_target_{uid}'))
        
        # Second country in row (if exists)
        if i + 1 < len(active_countries):
            uid2, country2 = active_countries[i + 1]
            row.append(InlineKeyboardButton(f"🇺🇳 {country2}", callback_data=f'ns_sabotage_target_{uid2}'))
        
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='ns_sabotage_menu')])
    
    await query.edit_message_text(
        '💣 کشور مورد نظر برای خرابکاری را انتخاب کنید:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_sabotage_quantity(query, target_uid):
    """Show quantity selection for sabotage"""
    target_country = utils.users.get(target_uid, {}).get('country', 'کشور ناشناس')
    
    keyboard = [
        [InlineKeyboardButton('1 معدن (50M)', callback_data=f'ns_sabotage_qty_1_{target_uid}')],
        [InlineKeyboardButton('2 معدن (100M)', callback_data=f'ns_sabotage_qty_2_{target_uid}')],
        [InlineKeyboardButton('3 معدن (150M)', callback_data=f'ns_sabotage_qty_3_{target_uid}')],
        [InlineKeyboardButton('4 معدن (200M)', callback_data=f'ns_sabotage_qty_4_{target_uid}')],
        [InlineKeyboardButton('5 معدن (250M)', callback_data=f'ns_sabotage_qty_5_{target_uid}')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='ns_sabotage_execute')]
    ]
    
    await query.edit_message_text(
        f'💣 <b>انتخاب تعداد معادن برای خرابکاری</b>\n\n'
        f'کشور هدف: {target_country}\n'
        f'چند معدن را می‌خواهید خراب کنید؟',
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def confirm_sabotage(query, target_uid, quantity):
    """Confirm sabotage operation"""
    target_country = utils.users.get(target_uid, {}).get('country', 'کشور ناشناس')
    cost = quantity * 50_000_000
    
    text = f"⚠️ آیا می‌خواهید {quantity} معدن در کشور {target_country} را خراب کنید؟\n💰 هزینه: {cost:,} تومان\n🎯 شانس موفقیت: 50% برای هر معدن"
    keyboard = [
        [InlineKeyboardButton('✅ بله', callback_data=f'ns_confirm_sabotage_{quantity}_{target_uid}')],
        [InlineKeyboardButton('❌ خیر', callback_data=f'ns_sabotage_target_{target_uid}')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def execute_sabotage(query, target_uid, quantity):
    """Execute sabotage operation"""
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    target = utils.users.get(target_uid, {})
    
    # Check if target has anti-sabotage protection
    target_org = target.get('national_security_org', {})
    anti_sabotage_charges = target_org.get('anti_sabotage_charges', 0)
    
    if anti_sabotage_charges > 0:
        # Check if protection blocks the attempt (90% chance)
        if random.random() < 0.9:
            # Consume one charge
            target_org['anti_sabotage_charges'] -= 1
            target['national_security_org'] = target_org
            utils.save_users()
            
            # Send messages for blocked attempt
            await send_sabotage_news(
                f"💣 تلاش برای خرابکاری در کشور {target.get('country', 'ناشناس')} با شکست مواجه شد.",
                reveal_attacker=False
            )
            
            await send_private_message(user_id, "عملیات شما ناموفق بود. هدف تحت حفاظت امنیتی بود.")
            await send_private_message(target_uid, "کشور شما تحت حفاظت ضد خرابکاری قرار داشت و امنیت حفظ شد.")
            
            await query.edit_message_text(
                '❌ عملیات ناموفق بود. کشور هدف تحت حفاظت ضد خرابکاری قرار دارد.',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_sabotage_menu')]])
            )
            return
    
    # Check cost
    cost = quantity * 50_000_000
    if u.get('resources', {}).get('cash', 0) < cost:
        await query.edit_message_text(
            f'❌ موجودی کافی نیست. نیاز: {cost:,} تومان',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_sabotage_menu')]])
        )
        return
    
    # Check how many mines target actually has
    target_mines = count_target_mines(target)
    
    if target_mines == 0:
        # No mines to destroy
        await query.edit_message_text(
            f'❌ کشور هدف هیچ معدنی ندارد.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_sabotage_menu')]])
        )
        return
    
    # Deduct full cost upfront (user pays for all requested mines regardless of success)
    u['resources']['cash'] -= cost
    
    # Execute sabotage on each mine (limited by target's actual mines)
    actual_quantity = min(quantity, target_mines)
    destroyed_mines = []
    success_count = 0
    
    for i in range(actual_quantity):
        if random.random() < 0.5:  # 50% success chance
            mine_type = destroy_random_mine(target)
            if mine_type:
                destroyed_mines.append(mine_type)
                success_count += 1
    
    if success_count > 0:
        # Success - send messages
        mine_list = ", ".join(destroyed_mines)
        
        # Send sabotage news with image for all countries
        country_name = target.get('country', 'ناشناس')
        
        await send_sabotage_news(
            f" 📰امپایر نیوز :💣افراد نامعلوم با خرابکاری در کشور {country_name} توانستند. معادن زیر را نابود کنند:  {mine_list} ٍ 📿 مقامات و پلیس امنیت در سردرگمی فرو رفتند",
            reveal_attacker=False,
            image_url="https://t.me/TextEmpire_IR/129"
        )
        
        await send_private_message(user_id, f"عملیات خرابکاری شما موفق بود. {success_count} معدن نابود شد: {mine_list}", image_url="https://t.me/TextEmpire_IR/129")
        await send_private_message(target_uid, f"🚨 خرابکاری در کشور شما موفق بود. {success_count} معدن نابود شد: {mine_list}   ژنرال شما: هرچه سریع تر ضد خرابکاری را فعال کنید ", image_url="https://t.me/TextEmpire_IR/129")
        
        # Prepare success message and handle refund
        success_message = f'✅ عملیات خرابکاری موفق بود! {success_count} معدن نابود شد: {mine_list}'
        if actual_quantity < quantity:
            # Refund excess cost only on success
            refund = (quantity - actual_quantity) * 50_000_000
            u['resources']['cash'] += refund
            success_message += f'\n💰 هزینه اضافی ({refund:,} تومان) برگشت داده شد.'
        
        await query.edit_message_text(
            success_message,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_sabotage_menu')]])
        )
    else:
        # Failure - reveal attacker
        await send_sabotage_news(
            f"💣 خرابکاری کشور {u.get('country', 'ناشناس')} علیه {target.get('country', 'ناشناس')} ناکام ماند و افشا شد.",
            reveal_attacker=True
        )
        
        await send_private_message(user_id, f"عملیات خرابکاری شما علیه {target.get('country', 'ناشناس')} شکست خورد. هزینه از حساب شما کسر شد.")
        await send_private_message(target_uid, f"کشور {u.get('country', 'ناشناس')} قصد خرابکاری در معادن شما داشت اما ناکام ماند.")
        
        await query.edit_message_text(
            '❌ عملیات خرابکاری شکست خورد و لو رفت.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_sabotage_menu')]])
        )
    
    utils.save_users()

def count_target_mines(target):
    """Count total number of mines in target's economy"""
    economy = target.get('economy', {})
    mines_list = economy.get('mines', [])
    return len(mines_list)

def destroy_random_mine(target):
    """Destroy a random mine from target and return its type"""
    economy = target.get('economy', {})
    mines_list = economy.get('mines', [])
    
    if not mines_list:
        return None
    
    # Mine names mapping
    mine_names = {
        'gold_mine': 'معدن طلا',
        'iron_mine': 'معدن آهن', 
        'oil_well': 'چاه نفت',
        'coal_mine': 'معدن زغال',
        'uranium_mine': 'معدن اورانیوم',
        'uranium_ore_mine': 'معدن اورانیوم',
        'copper_mine': 'معدن مس',
        'diamond_mine': 'معدن الماس',
        'aluminum_mine': 'معدن آلومینیوم',
        'titanium_mine': 'معدن تیتانیوم'
    }
    
    # Select random mine to destroy
    selected_mine = random.choice(mines_list)
    mines_list.remove(selected_mine)
    
    return mine_names.get(selected_mine, selected_mine)

async def execute_anti_sabotage(query):
    """Execute anti-sabotage protection"""
    user_id = str(query.from_user.id)
    u = utils.users.get(user_id, {})
    
    # Check cost
    if u.get('resources', {}).get('cash', 0) < 200_000_000:
        await query.edit_message_text(
            '❌ موجودی کافی نیست. نیاز: 200M',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_sabotage_menu')]])
        )
        return
    
    # Deduct cost
    u['resources']['cash'] -= 200_000_000
    
    # Set anti-sabotage protection
    org = u.get('national_security_org', {})
    org['anti_sabotage_charges'] = 2
    u['national_security_org'] = org
    
    utils.save_users()
    
    await query.edit_message_text(
        f'✅ حفاظت ضد خرابکاری فعال شد. 2 بار محافظت در برابر خرابکاری دریافت کردید.',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='ns_sabotage_menu')]])
    )

async def send_sabotage_news(message, reveal_attacker=False, image_url=None):
    """Send sabotage news to channel"""
    try:
        from telegram import Bot
        bot = Bot(token=utils.BOT_TOKEN)
        
        if image_url:
            # Send image with caption
            await bot.send_photo(
                chat_id=utils.NEWS_CHANNEL_ID, 
                photo=image_url,
                caption=message
            )
        else:
            # Send text message
            await bot.send_message(chat_id=utils.NEWS_CHANNEL_ID, text=message)
    except Exception as e:
        print(f"Error sending sabotage news: {e}")

async def send_assassination_news(message, image_url=None):
    """Send assassination news to channel"""
    try:
        from telegram import Bot
        bot = Bot(token=utils.BOT_TOKEN)
        
        if image_url:
            # Send image with caption
            await bot.send_photo(
                chat_id=utils.NEWS_CHANNEL_ID, 
                photo=image_url,
                caption=message
            )
        else:
            # Send text message
            await bot.send_message(chat_id=utils.NEWS_CHANNEL_ID, text=message)
    except Exception as e:
        print(f"Error sending assassination news: {e}")

async def send_independence_news(message, image_url=None):
    """Send independence news to channel"""
    try:
        from telegram import Bot
        bot = Bot(token=utils.BOT_TOKEN)
        
        if image_url:
            # Send image with caption
            await bot.send_photo(
                chat_id=utils.NEWS_CHANNEL_ID, 
                photo=image_url,
                caption=message
            )
        else:
            # Send text message
            await bot.send_message(chat_id=utils.NEWS_CHANNEL_ID, text=message)
    except Exception as e:
        print(f"Error sending independence news: {e}")

# ==================== end Sabotage System ====================

# ==================== end National Security ====================

# ==================== Mine Production Technology System ====================

# Define auto-producing mines and farms based on existing code (متعادل شده)
AUTO_PRODUCING_RESOURCES = {
    # Mines
    'iron_mine': ('iron', 75, 'معدن آهن', 15_000_000, '⛏'),
    'uranium_ore_mine': ('uranium_ore', 20, 'معدن اورانیوم', 25_000_000, '⛏'),
    'copper_mine': ('copper', 50, 'معدن مس', 20_000_000, '⛏'),
    'gold_mine': ('gold', 3, 'معدن طلا', 45_000_000, '⛏'),
    'diamond_mine': ('diamond', 1, 'معدن الماس', 80_000_000, '⛏'),
    'aluminum_mine': ('aluminum', 30, 'معدن آلومینیوم', 30_000_000, '⛏'),
    'titanium_mine': ('titanium', 6, 'معدن تیتانیوم', 60_000_000, '⛏'),
    # Farms
    'wheat_farm': ('wheat', 25, 'مزرعه گندم', 25_000_000, '🌾'),
    'rice_farm': ('rice', 25, 'مزرعه برنج', 20_000_000, '🌾'),
    'fruit_farm': ('fruits', 20, 'مزرعه میوه', 15_000_000, '🌾'),
    # Energy
    'power_plant': ('electricity', 6, 'نیروگاه برق', 50_000_000, '⚡'),
    'oil_refinery': ('oil', 250, 'پالایشگاه نفت', 60_000_000, '🛢️'),
    'gas_refinery': ('gas', 200, 'پالایشگاه گاز', 30_000_000, '⛽'),
    # Production Lines
    'pride_line': ('pride_cars', 1500, 'خط تولید پراید', 60_000_000, '🚗'),
    'benz_line': ('benz_cars', 600, 'خط تولید بنز', 150_000_000, '🚙'),
    'electronics_line': ('electronics', 8000, 'خط تولید الکترونیک', 35_000_000, '🔌'),
}

async def show_mine_production_tech_menu(query):
    """Show production technology menu for mines and farms"""
    user_id = str(query.from_user.id)
    user = utils.users.get(str(user_id), {})
    economy = user.get('economy', {})
    
    # Get user's mines, farms, energy, and production lines
    user_mines = economy.get('mines', [])
    user_farms = economy.get('farms', [])
    user_energy = economy.get('energy', [])
    user_production_lines = economy.get('production_lines', [])
    
    # Filter only auto-producing resources
    auto_mines = [mine for mine in user_mines if mine in AUTO_PRODUCING_RESOURCES]
    auto_farms = [farm for farm in user_farms if farm in AUTO_PRODUCING_RESOURCES]
    auto_energy = [plant for plant in user_energy if plant in AUTO_PRODUCING_RESOURCES]
    auto_production_lines = [line for line in user_production_lines if line in AUTO_PRODUCING_RESOURCES]
    
    all_resources_list = auto_mines + auto_farms + auto_energy + auto_production_lines
    
    if not all_resources_list:
        await query.edit_message_text(
            '❌ شما هیچ سازه خودکار تولیدی ندارید.\n\nابتدا معادن، مزارع، نیروگاه‌ها یا خطوط تولید را از منوی ساخت و ساز بسازید.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='technology')]])
        )
        return
    
    # Initialize tech levels if not exists
    ensure_production_tech_levels(user_id)
    
    # Display resources with their tech levels and production rates
    text = "⛏️ <b>فناوری تولید</b>\n\n"
    keyboard = []
    
    # Show all resources: farms, mines, energy, production lines
    all_resources = auto_farms + auto_mines
    
    for resource_key in all_resources:
        resource, base_amount, resource_name, upgrade_cost, icon = AUTO_PRODUCING_RESOURCES[resource_key]
        tech_levels = utils.get_production_tech_levels(user_id)
        tech_level = tech_levels.get(resource_key, 1)
        
        # Calculate production with tech bonus
        production_bonus = (tech_level - 1) * 0.05  # 5% per level
        current_production = base_amount * (1 + production_bonus)
        
        text += f"{icon} {resource_name} | لول: {tech_level} | تولید: {current_production:.1f} واحد/دور\n"
        
        # Add upgrade button if not at max level
        if tech_level < 20:
            keyboard.append([InlineKeyboardButton(
                f'➕ ارتقا {resource_name} (لول {tech_level} → {tech_level + 1}) - {upgrade_cost:,} تومان',
                callback_data=f'production_tech_upgrade_{resource_key}'
            )])
        else:
            keyboard.append([InlineKeyboardButton(
                f'✅ {resource_name} - حداکثر لول (20)',
                callback_data='production_tech_maxed'
            )])
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='technology')])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def confirm_production_tech_upgrade(query, resource_key):
    """Confirm production technology upgrade"""
    user_id = str(query.from_user.id)
    user = utils.users.get(str(user_id), {})
    
    if resource_key not in AUTO_PRODUCING_RESOURCES:
        await query.edit_message_text('❌ منبع نامعتبر است.')
        return
    
    resource, base_amount, resource_name, upgrade_cost, icon = AUTO_PRODUCING_RESOURCES[resource_key]
    tech_levels = utils.get_production_tech_levels(user_id)
    tech_level = tech_levels.get(resource_key, 1)
    
    if tech_level >= 20:
        await query.edit_message_text(f'⚠️ {resource_name} به حداکثر لول (20) رسیده است.')
        return
    
    # Calculate new production rate
    new_tech_level = tech_level + 1
    production_bonus = (new_tech_level - 1) * 0.05
    new_production = base_amount * (1 + production_bonus)
    
    text = f"⚠️ آیا می‌خواهید {resource_name} را به لول {new_tech_level} ارتقا دهید؟\n\n"
    text += f"💰 هزینه: {upgrade_cost:,} تومان\n"
    text += f"📈 تولید جدید: {new_production:.1f} واحد/دور\n"
    text += f"📊 افزایش: +{production_bonus*100:.0f}%"
    
    keyboard = [
        [InlineKeyboardButton('✅ بله', callback_data=f'production_tech_confirm_{resource_key}')],
        [InlineKeyboardButton('❌ خیر', callback_data='mine_production_tech')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def execute_production_tech_upgrade(query, resource_key):
    """Execute production technology upgrade"""
    user_id = str(query.from_user.id)
    user = utils.users.get(str(user_id), {})
    
    if resource_key not in AUTO_PRODUCING_RESOURCES:
        await query.edit_message_text('❌ منبع نامعتبر است.')
        return
    
    resource, base_amount, resource_name, upgrade_cost, icon = AUTO_PRODUCING_RESOURCES[resource_key]
    
    # Check if user has enough money
    if user.get('resources', {}).get('cash', 0) < upgrade_cost:
        await query.edit_message_text(
            f'❌ موجودی کافی برای ارتقا {resource_name} ندارید.\nنیاز: {upgrade_cost:,} تومان',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='mine_production_tech')]])
        )
        return
    
    # Check current level
    tech_levels = utils.get_production_tech_levels(user_id)
    tech_level = tech_levels.get(resource_key, 1)
    if tech_level >= 20:
        await query.edit_message_text(
            f'⚠️ {resource_name} به حداکثر لول (20) رسیده است.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='mine_production_tech')]])
        )
        return
    
    # Deduct cost and upgrade
    user['resources']['cash'] -= upgrade_cost
    utils.set_production_tech_level(user_id, resource_key, tech_level + 1)
    
    # Calculate new production rate
    new_tech_level = tech_level + 1
    production_bonus = (new_tech_level - 1) * 0.05
    new_production = base_amount * (1 + production_bonus)
    
    await query.edit_message_text(
        f'✅ {resource_name} به لول {new_tech_level} ارتقا یافت.\nتولید آن اکنون {new_production:.1f} در هر دور است.',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='mine_production_tech')]])
    )

def calculate_production_with_tech(user_id, resource_key, base_amount):
    """Calculate production with technology bonus for mines and farms"""
    tech_levels = utils.get_production_tech_levels(user_id)
    tech_level = tech_levels.get(resource_key, 1)
    production_bonus = (tech_level - 1) * 0.05  # 5% per level
    return base_amount * (1 + production_bonus)

def ensure_production_tech_levels(user_id):
    """اطمینان از وجود production_tech_levels برای کاربر"""
    return utils.get_production_tech_levels(user_id) is not None

# ==================== end Mine Production Technology System ====================

# تابع نمایش لیست کشورها برای اعلان جنگ
async def show_countries_for_war_declaration(query):
    user_id = str(query.from_user.id)
    if user_id not in utils.users:
        await query.answer("شما در بازی ثبت‌نام نکرده‌اید!")
        return
    initialize_user_resources(user_id)
    user_country = utils.users[user_id]['country']
    all_countries = [country['name'] for country in countries]
    available_countries = []
    # محاسبه لیست طرف‌های جنگ فعلی کاربر بر اساس ساختار جدید utils.war_declarations
    def get_active_war_opponents(uid: str):
        opponents = []
        my_country = utils.users.get(uid, {}).get('country', '')
        for wid, w in utils.war_declarations.items():
            status = w.get('status', 'active')
            attacker = w.get('attacker')
            defender = w.get('defender')
            if status == 'active' and (attacker == my_country or defender == my_country):
                other = defender if attacker == my_country else attacker
                if other and other not in opponents:
                    opponents.append(other)
        return opponents

    current_opponents = set(get_active_war_opponents(user_id))

    for country in all_countries:
        if country == user_country:
            continue
        # پیدا کردن user_id کشور مقابل
        target_id = None
        for uid, u in utils.users.items():
            if u.get('country') == country:
                target_id = uid
                break
        if not target_id:
            continue
        # فقط کشورهایی که روابط کمتر از صفر دارند و قبلاً در جنگ فعال نیستند
        if country_relations.get(user_id, {}).get(target_id, 0) < 0:
            if country not in current_opponents:
                available_countries.append(country)
    # ایجاد دکمه‌ها به صورت دو ستونی
    keyboard = []
    for i in range(0, len(available_countries), 2):
        row = []
        row.append(InlineKeyboardButton(available_countries[i], callback_data=f'declare_war_{available_countries[i]}'))
        if i + 1 < len(available_countries):
            row.append(InlineKeyboardButton(available_countries[i + 1], callback_data=f'declare_war_{available_countries[i + 1]}'))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('کشور مورد نظر برای اعلان جنگ را انتخاب کنید:', reply_markup=reply_markup)

# تابع تایید اعلان جنگ
async def confirm_war_declaration(query, target_country):
    user_id = str(query.from_user.id)
    user_country = utils.users[user_id]['country']
    
    keyboard = [
        [InlineKeyboardButton('تایید ✅', callback_data=f'confirm_war_{target_country}')],
        [InlineKeyboardButton('لغو ❌', callback_data='declare_war')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f'آیا مطمئن هستید که می‌خواهید به کشور {target_country} اعلان جنگ کنید؟'
    await query.edit_message_text(text, reply_markup=reply_markup)

# تابع اجرای اعلان جنگ
pending_peace_requests = {}  # {target_id: user_id}

# --- 2. اصلاح اعلان جنگ دوطرفه (دستی و خودکار) ---
async def execute_war_declaration(query, target_country):
    user_id = str(query.from_user.id)
    user_country = utils.users[user_id]['country']
    
    # جلوگیری از اعلان جنگ علیه کشوری که صلح اجباری فعال دارد
    try:
        # یافتن target_id بر اساس نام کشور هدف
        target_id = None
        for uid, u in utils.users.items():
            if u.get('country') == target_country:
                target_id = uid
                break
        if target_id and is_user_peace_protected(target_id):
            turns = utils.users[target_id].get('diplomacy', {}).get('forced_peace_turns', 0)
            text = (
                "❌ <b>اعلان جنگ ناموفق!</b>\n\n"
                f"🤝 کشور {target_country} تحت صلح اجباری است.\n"
                f"⏰ {turns} نوبت باقی‌مانده\n\n"
                "شما نمی‌توانید تا پایان این مدت به این کشور اعلان جنگ کنید."
            )
            keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='strategy')]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            return
        # جلوگیری از اعلان جنگ توسط کاربری که بسته "دوری و دوستی" فعال دارد
        try:
            if utils.users[user_id].get('diplomacy', {}).get('forced_peace_turns', 0) > 0:
                text = (
                    "❌ <b>اعلان جنگ ناموفق!</b>\n\n"
                    "در حال حاضر اثر صلح اجباری برای کشور شما فعال است و نمی‌توانید اعلان جنگ کنید."
                )
                keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='strategy')]]
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
                return
        except Exception:
            pass
    except Exception:
        pass
    
    # استفاده از وزیر خارجه انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'foreign' in selected_officials:
        foreign_minister = selected_officials['foreign']
    else:
        foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
    
    # پیدا کردن target_id
    target_id = None
    for uid, u in utils.users.items():
        if u.get('country') == target_country:
            target_id = uid
            break
    if not target_id:
        await query.edit_message_text('کشور مورد نظر یافت نشد.')
        return
    # ثبت اعلان جنگ در ساختار جدید utils.war_declarations
    war_id = f"{user_country}->{target_country}"
    utils.war_declarations[war_id] = {
        'attacker': user_country,
        'defender': target_country,
        'type': 'war_declaration',
        'status': 'active',
        'turn_declared': game_data.get('turn', 1)
    }
    # ذخیره اعلان‌های جنگ
    save_war_declarations()
    # پس از شروع جنگ: ارسال پیشنهاد پناهندگی به کشورها
    try:
        await broadcast_refugee_offers(war_id, user_country, target_country)
    except Exception as e:
        print(f"refugee broadcast error: {e}")
    
    # فایل ایدی مشترک برای همه پیام‌های اعلان جنگ
    war_photo = "https://t.me/TextEmpire_IR/63"
    
    # پیام وزیر خارجه
    minister_message = f"🚨 {foreign_minister['name']}: اعلان جنگ با {target_country} ارسال شد. این تصمیم عواقب جدی برای روابط دیپلماتیک ما خواهد داشت."
    
    # ارسال پیام به کانال اخبار
    news_message = f"🚨 <b>اعلان جنگ!</b>\n\nکشور {user_country} به کشور {target_country} اعلان جنگ کرد!\n\n🌍 جهان در حالت آماده‌باش قرار گرفت!"
    try:
        from telegram import Bot
        bot = Bot(token='7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I')
        await bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=war_photo, caption=news_message, parse_mode='HTML')
    except Exception as e:
        print(f"خطا در ارسال پیام به کانال اخبار: {e}")
    
    # ارسال پیام به کشور اعلان‌کننده
    declarer_message = f"🚨 <b>اعلان جنگ ارسال شد!</b>\n\nشما به کشور {target_country} اعلان جنگ کردید!\n\n⚔️ حالا می‌توانید حمله کنید یا منتظر پاسخ بمانید.\n\n<blockquote>{minister_message}</blockquote>"
    try:
        from telegram import Bot
        bot = Bot(token='7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I')
        await bot.send_photo(chat_id=int(user_id), photo=war_photo, caption=declarer_message, parse_mode='HTML')
    except Exception as e:
        print(f"خطا در ارسال پیام به اعلان‌کننده: {e}")
    
    # ارسال پیام به کشور هدف
    target_message = f"🚨 <b>اعلان جنگ دریافت شد!</b>\n\nکشور {user_country} به شما اعلان جنگ کرد!\n\n⚔️ حالا می‌توانید حمله کنید یا درخواست صلح دهید."
    try:
        await bot.send_photo(chat_id=int(target_id), photo=war_photo, caption=target_message, parse_mode='HTML')
    except Exception as e:
        print(f"خطا در ارسال پیام به کشور هدف: {e}")
    
    await show_strategy_menu(query)



# --- 4. نمایش لیست کشورها برای آتش‌بس ---
async def show_peace_menu(query):
    user_id = str(query.from_user.id)
    user_country = utils.users.get(user_id, {}).get('country', '')
    # کشورهایی که با آن‌ها در جنگ است
    # محاسبه لیست طرف‌های جنگ از ساختار جدید
    my_country = utils.users.get(user_id, {}).get('country', '')
    war_list = []
    for wid, w in utils.war_declarations.items():
        if w.get('status') == 'active' and (w.get('attacker') == my_country or w.get('defender') == my_country):
            other = w.get('defender') if w.get('attacker') == my_country else w.get('attacker')
            if other and other not in war_list:
                war_list.append(other)
    if not war_list:
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('شما با هیچ کشوری در جنگ نیستید.', reply_markup=reply_markup)
        return
    keyboard = []
    for country in war_list:
        keyboard.append([InlineKeyboardButton(f'درخواست آتش‌بس با {country}', callback_data=f'peace_request_{country}')])
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('کشوری که می‌خواهید درخواست آتش‌بس بدهید را انتخاب کنید:', reply_markup=reply_markup)

# --- 5. ارسال درخواست آتش‌بس ---
async def handle_peace_request(query, user_id, target_country, context):
    # پیدا کردن target_id
    target_id = None
    for uid, u in utils.users.items():
        if u.get('country') == target_country:
            target_id = uid
            break
    if not target_id:
        await query.edit_message_text('کشور مورد نظر یافت نشد.')
        return
    
    # استفاده از وزیر خارجه انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'foreign' in selected_officials:
        foreign_minister = selected_officials['foreign']
    else:
        foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
    
    # ثبت درخواست آتش‌بس
    pending_peace_requests[user_id] = target_id
    
    # پیام وزیر خارجه
    minister_message = f"🤝 {foreign_minister['name']}: درخواست آتش‌بس با {target_country} ارسال شد. امیدواریم صلح برقرار شود."
    
    keyboard = [
        [InlineKeyboardButton('قبول آتش‌بس 🤝', callback_data=f'accept_peace_{user_id}'),
        InlineKeyboardButton('رد آتش‌بس ❌', callback_data=f'reject_peace_{user_id}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=int(target_id),
        text=f'کشور {utils.users[user_id]["country"]} درخواست آتش‌بس داده است. آیا قبول می‌کنید؟',
        reply_markup=reply_markup
    )
    
    # پیام تایید به درخواست‌دهنده
    await safe_edit_message(query, f'درخواست آتش‌بس به {target_country} ارسال شد. منتظر پاسخ باشید.\n\n<blockquote>{minister_message}</blockquote>', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]))
# --- 6. تایید آتش‌بس و حذف اعلان جنگ ---

# تابع بررسی وضعیت فتح کاربر
def is_user_conquered(user_id):
    user = utils.users.get(str(user_id), {})
    return bool(user.get('conquered_by'))

# تابع بررسی دسترسی نظامی
def check_military_access(user_id):
    if is_user_conquered(user_id):
        return False, "💀 کشور شما تحت سلطه است و نمی‌توانید عملیات نظامی انجام دهید."
    return True, None

# تابع نمایش منوی مستعمرات
async def show_colonies_menu(query):
    user_id = str(query.from_user.id)
    user = utils.users.get(str(user_id), {})
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return
    
    country_name = user.get('country', 'کشور ناشناس')
    
    # استفاده از وزیر خارجه انتخاب شده
    selected_officials = user.get('selected_officials', {})
    if 'foreign' in selected_officials:
        foreign_minister = selected_officials['foreign']
    else:
        # اگر وزیر خارجه انتخاب نشده، از اسامی پیش‌فرض استفاده کن
        foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
    
    # پیام خوشامدگویی
    text = f"🏛️ <b>خوش آمدید!</b>\n\n"
    text += f"🤝 من {foreign_minister['name']}، {foreign_minister['title']} شما هستم.\n"
    text += f"🏛️ <b>مستعمرات کشور {country_name}</b>\n\n"
    
    # بررسی اینکه آیا کاربر مستعمره‌ای دارد
    user_colonies = []
    for uid, user_data in utils.users.items():
        if user_data.get('conquered_by') == user.get('country'):
            user_colonies.append({
                'user_id': uid,
                'country': user_data.get('country', 'نامشخص'),
                'conquered_at': user_data.get('conquered_at', 0)
            })
    
    if not user_colonies:
        text += "شما هیچ مستعمره‌ای ندارید.\n"
        text += "برای کسب مستعمره، کشورهای دیگر را فتح کنید!"
    else:
        text += f"<b>مستعمرات شما ({len(user_colonies)} کشور):</b>\n"
        for i, colony in enumerate(user_colonies, 1):
            from datetime import datetime
            conquered_time = datetime.fromtimestamp(colony['conquered_at']).strftime('%Y-%m-%d %H:%M') if colony['conquered_at'] else 'نامشخص'
            text += f"{i}. {colony['country']}\n"
            text += f"   📅 تاریخ فتح: {conquered_time}\n\n"
    
    # تحلیل هوشمند مستعمرات
    from analysis import generate_colonies_analysis
    analysis = generate_colonies_analysis(user_id)
    
    text += f"\n<b>پیشنهاد {foreign_minister['title']} {foreign_minister['name']}:</b>\n<blockquote>{analysis}</blockquote>"
    
    keyboard = []
    if user_colonies:
        keyboard.append([InlineKeyboardButton('📋 مشاهده جزئیات مستعمرات', callback_data='view_colonies_details')])
        keyboard.append([InlineKeyboardButton('🏳️ اجازه استقلال', callback_data='grant_independence')])
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='diplomacy')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# تابع نمایش جزئیات مستعمرات
async def show_colonies_details(query):
    user_id = str(query.from_user.id)
    user = utils.users.get(str(user_id), {})
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return
    
    # پیدا کردن مستعمرات کاربر
    user_colonies = []
    for uid, user_data in utils.users.items():
        if user_data.get('conquered_by') == user.get('country'):
            user_colonies.append({
                'user_id': uid,
                'country': user_data.get('country', 'نامشخص'),
                'conquered_at': user_data.get('conquered_at', 0),
                'resources': user_data.get('resources', {}),
                'money': user_data.get('money', 0)
            })
    
    if not user_colonies:
        await query.edit_message_text("شما هیچ مستعمره‌ای ندارید.")
        return
    
    text = f"📋 <b>جزئیات مستعمرات شما</b>\n\n"
    
    for i, colony in enumerate(user_colonies, 1):
        from datetime import datetime
        conquered_time = datetime.fromtimestamp(colony['conquered_at']).strftime('%Y-%m-%d %H:%M') if colony['conquered_at'] else 'نامشخص'
        
        text += f"🏛️ <b>{colony['country']}</b>\n"
        text += f"   📅 تاریخ فتح: {conquered_time}\n"
        # نمایش مبلغ نقدی دریافت‌شده در لحظه فتح، اگر ثبت شده باشد
        try:
            captured_cash = utils.users.get(colony['user_id'], {}).get('conquered_captured_cash', None)
        except Exception:
            captured_cash = None
        if captured_cash is not None:
            text += f"   💰 پول دریافتی هنگام فتح: {format_price_short(captured_cash)}\n"
        else:
            text += f"   💰 پول: {format_price_short(colony['money'])}\n"
        
        # نمایش منابع مهم
        resources = colony['resources']
        important_resources = ['soldiers', 'special_forces', 'tanks', 'speedboats', 'naval_ship']
        resource_text = []
        for resource in important_resources:
            if resources.get(resource, 0) > 0:
                resource_text.append(f"{resource}: {resources[resource]:,}")
        
        if resource_text:
            text += f"   🛡️ نیروهای نظامی: {', '.join(resource_text)}\n"
        
        text += "\n"
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='colonies_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# تابع نمایش لیست مستعمرات برای اجازه استقلال
async def show_grant_independence_menu(query):
    user_id = str(query.from_user.id)
    user = utils.users.get(str(user_id), {})
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return

    # پیدا کردن مستعمرات کاربر
    user_colonies = []
    for uid, user_data in utils.users.items():
        if user_data.get('conquered_by') == user.get('country'):
            user_colonies.append({
                'user_id': uid,
                'country': user_data.get('country', 'نامشخص'),
                'conquered_at': user_data.get('conquered_at', 0)
            })
    
    if not user_colonies:
        await query.edit_message_text("شما هیچ مستعمره‌ای برای آزادسازی ندارید.")
        return
    
    text = "🏳️ <b>اجازه استقلال</b>\n\n"
    text += "کدام مستعمره را می‌خواهید آزاد کنید؟\n\n"
    text += "⚠️ <b>توجه:</b> پس از آزادسازی، تمام منابع و پول مستعمره به شما منتقل می‌شود.\n\n"
    
    keyboard = []
    for colony in user_colonies:
        keyboard.append([InlineKeyboardButton(
            f"🏳️ آزادسازی {colony['country']}", 
            callback_data=f'grant_independence_{colony["user_id"]}'
        )])
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='colonies_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
# تابع اجرای اجازه استقلال
async def execute_grant_independence(query, target_id):
    global users
    user_id = str(query.from_user.id)
    user = utils.users.get(str(user_id), {})
    target_user = utils.users.get(target_id, {})
    
    # استفاده از وزیر خارجه انتخاب شده
    selected_officials = user.get('selected_officials', {})
    if 'foreign' in selected_officials:
        foreign_minister = selected_officials['foreign']
    else:
        foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return
    
    if target_user.get('conquered_by') != user.get('country'):
        await query.edit_message_text('این کشور مستعمره شما نیست!')
        return
    
    colony_country = target_user.get('country', 'نامشخص')
    
    # منابع نزد استعمارگر باقی می‌ماند؛ بر اساس «مقادیر پیش‌فرض دسته» 20% منابع اقتصادی و 20% پول و 50% نیروهای نظامی به کشور آزادشده داده می‌شود
    try:
        # تعیین مقادیر پیش‌فرض بر اساس دسته کشور
        cat = utils.users.get(target_id, {}).get('category', '') or target_user.get('category', '')
        def _defaults_by_category(category: str):
            # مقادیر هم‌راستا با initialize_user_resources
            if 'ابرقدرت' in category:
                start_cash = 1_000_000_000
                mil = {"soldiers":1000000,'special_forces':25000,"tanks":450,"armored_vehicles":1050,'transport_planes':40,"helicopters":540,"fighter_jets":460,'bombers':25,'artillery':60,'drones':180,"air_defense":35,'coastal_artillery':51,'speedboats':140,"naval_ship":46,"submarines":23,"aircraft_carriers":11,"war_robots":1000,"defense_missiles":400,"ballistic_missiles":300}
                res = {'gold':60,'steel':500,'iron':600,'copper':250,'diamond':25,'uranium':20,'wheat':400,'rice':400,'fruits':400,'oil':2000,'gas':2000,'electronics':500000,'pride_cars':50000,'benz_cars':20000,'electricity':800,'uranium_ore':200,'centrifuge':30,'yellowcake':100,'space_parts':10,'aluminum':500,'titanium':150}
            elif 'قدرت منطقه‌ای' in category:
                start_cash = 550_000_000
                mil = {"soldiers":500000,'special_forces':12000,"tanks":250,"armored_vehicles":600,'transport_planes':19,"helicopters":300,"fighter_jets":250,'bombers':6,'artillery':28,'drones':100,"air_defense":18,'coastal_artillery':24,'speedboats':90,"naval_ship":21,"submarines":9,"aircraft_carriers":4,"war_robots":500,"defense_missiles":250,"ballistic_missiles":150}
                res = {'gold':40,'steel':350,'iron':400,'copper':150,'diamond':15,'uranium':10,'wheat':200,'rice':200,'fruits':200,'oil':1000,'gas':1000,'electronics':200000,'pride_cars':30000,'benz_cars':10000,'electricity':400,'uranium_ore':100,'centrifuge':15,'yellowcake':50,'space_parts':5,'aluminum':300,'titanium':75}
            elif 'قدرت نوظهور' in category:
                start_cash = 300_000_000
                mil = {"soldiers":250000,'special_forces':6000,"tanks":120,"armored_vehicles":300,'transport_planes':8,"helicopters":150,"fighter_jets":120,'bombers':2,'artillery':14,'drones':60,"air_defense":9,'coastal_artillery':12,'speedboats':60,"naval_ship":10,"submarines":4,"aircraft_carriers":1,"war_robots":250,"defense_missiles":120,"ballistic_missiles":80}
                res = {'gold':25,'steel':220,'iron':260,'copper':90,'diamond':8,'uranium':6,'wheat':140,'rice':140,'fruits':140,'oil':550,'gas':550,'electronics':120000,'pride_cars':20000,'benz_cars':6000,'electricity':250,'uranium_ore':60,'centrifuge':8,'yellowcake':28,'space_parts':3,'aluminum':180,'titanium':45}
            else:
                start_cash = 150_000_000
                mil = {"soldiers":120000,'special_forces':2500,"tanks":45,"armored_vehicles":90,'transport_planes':3,"helicopters":60,"fighter_jets":40,'bombers':0,'artillery':6,'drones':25,"air_defense":3,'coastal_artillery':4,'speedboats':20,"naval_ship":3,"submarines":1,"aircraft_carriers":0,"war_robots":120,"defense_missiles":40,"ballistic_missiles":25}
                res = {'gold':10,'steel':120,'iron':140,'copper':50,'diamond':3,'uranium':2,'wheat':90,'rice':90,'fruits':90,'oil':220,'gas':220,'electronics':50000,'pride_cars':10000,'benz_cars':2000,'electricity':120,'uranium_ore':25,'centrifuge':2,'yellowcake':10,'space_parts':1,'aluminum':80,'titanium':20}
            return start_cash, mil, res

        start_cash, default_mil, default_res = _defaults_by_category(cat)
        # 20% از منابع اقتصادی پیش‌فرض + 20% پول نقد پیش‌فرض
        give_back_res = {k: int(v * 0.20) for k, v in default_res.items()}
        cash_back = int(start_cash * 0.20)
        # 50% از نیروهای نظامی پیش‌فرض
        give_back_mil = {k: int(v * 0.50) for k, v in default_mil.items()}
        # اعمال به کشور آزادشده
        tgt_res = utils.users[target_id].setdefault('resources', {})
        for k, v in give_back_res.items():
            if v > 0:
                tgt_res[k] = tgt_res.get(k, 0) + v
        for k, v in give_back_mil.items():
            if v > 0:
                tgt_res[k] = tgt_res.get(k, 0) + v
        tgt_res['cash'] = int(tgt_res.get('cash', 0)) + cash_back
    except Exception as _e:
        # اگر محاسبه پیش‌فرض‌ها شکست خورد، حداقل نیرو و پولی پایه برگردانده شود
        utils.users[target_id].setdefault('resources', {})
        utils.users[target_id]['resources']['soldiers'] = utils.users[target_id]['resources'].get('soldiers', 0) + 10000
        utils.users[target_id]['resources']['cash'] = int(utils.users[target_id]['resources'].get('cash', 0)) + 10_000_000
    
    # بازگردانی مرزها و دسترسی دریایی اخذ شده از این مستعمره
    try:
        from utils import revoke_conquest_borders
        revoke_conquest_borders(user_id, target_id)
    except Exception:
        pass

    # بازگردانی مهاجران به کشور مستقل (انتخابی: کل جمعیت یا بخشی)
    try:
        from jame import get_country_population_by_user_id
        pop = int(get_country_population_by_user_id(target_id))
        current_imms = int(utils.users[user_id].get('immigrants', 0))
        utils.users[user_id]['immigrants'] = max(0, current_imms - max(0, pop))
    except Exception:
        pass

    # آزادسازی کشور
    utils.users[target_id].pop('conquered_by', None)
    utils.users[target_id].pop('conquered_at', None)
    utils.users[target_id]['activated'] = True
    # همگام‌سازی وضعیت کشورها با users تا taken درست تنظیم شود
    try:
        from utils import reconcile_world_state
        reconcile_world_state()
    except Exception:
        pass
    utils.users[target_id].pop('independence_deadline_turn', None)
    # علامت‌گذاری به عنوان کشورِ آزادشده برای واجدشرایط شدن وام استقلال
    utils.users[target_id]['was_conquered'] = True
    
    # تنظیم روابط بین فاتح و کشور مستقل شده به 100+ (روابط مثبت پس از استقلال)
    try:
        from utils import country_relations, save_country_relations
        if user_id not in country_relations:
            country_relations[user_id] = {}
        if target_id not in country_relations:
            country_relations[target_id] = {}
        country_relations[user_id][target_id] = 100
        country_relations[target_id][user_id] = 100
        save_country_relations()
    except Exception:
        pass
    
    # حذف از conquered_countries_data برای وام استقلال
    try:
        from utils import conquered_countries_data, save_conquered_countries_data
        if str(target_id) in conquered_countries_data:
            del conquered_countries_data[str(target_id)]
            save_conquered_countries_data()
    except Exception:
        pass
    
    # ذخیره تغییرات
    from utils import save_users
    save_users()
    try:
        from utils import save_conquered_countries_data
        save_conquered_countries_data()
    except Exception:
        pass
    
    # پیام وزیر خارجه
    minister_message = f"🏳️ {foreign_minister['name']}: استقلال {colony_country} اعطا شد. این تصمیم نشان‌دهنده عظمت و بخشندگی کشور ما است."
    
    # ارسال پیام خصوصی به استعمارگر
    await send_private_message(
        user_id,
        f"🏳️ کشور {colony_country} از سلطه شما آزاد شد!\n\n💰 پول منتقل شده: {format_price_short(cash_back)}\n📦 20٪ منابع اقتصادی + 50٪ نیروهای پیش‌فرض به کشور آزادشده بازگردانده شد.\n\n🏦 کشور {colony_country} می‌تواند از بانک بین‌المللی وام استقلال دریافت کند.\n\n{minister_message}",
        image_url="https://t.me/TextEmpire_IR/133"
    )
    
    # ارسال پیام‌ها
    text = f"🏳️ <b>استقلال اعطا شد!</b>\n\n"
    text += f"کشور {colony_country} از سلطه شما آزاد شد!\n\n"
    text += f"💰 پول منتقل شده: {format_price_short(cash_back)}\n"
    text += f"📦 20٪ منابع اقتصادی + 50٪ نیروهای پیش‌فرض به کشور آزادشده بازگردانده شد.\n\n"
    text += f"🏦 کشور {colony_country} می‌تواند از بانک بین‌المللی وام استقلال دریافت کند.\n\n"
    text += f"<blockquote>{minister_message}</blockquote>"
    
    # ارسال پیام به کانال خبری
    await send_independence_news(
        f"🏳️ کشور {colony_country} توسط {user.get('country')} آزاد شد و استقلال خود را بازپس گرفت!",
        image_url="https://t.me/TextEmpire_IR/133"
    )
    
    # ارسال پیام به مستعمره سابق
    try:
        await send_private_message(
            target_id, 
            f"🎉 کشور شما توسط {user.get('country')} آزاد شد! شما دوباره مستقل هستید.\n\n🏦 برای بازسازی کشور خود، می‌توانید از بانک بین‌المللی وام استقلال دریافت کنید.",
            image_url="https://t.me/TextEmpire_IR/133"
        )
    except Exception:
        pass
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='colonies_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
# توابع بانک به فایل bank.py منتقل شدند
# تابع مدیریت پاسخ طرفین به درخواست آتش بس
async def handle_ceasefire_response(query, war_key, response):
    """
    مدیریت پاسخ طرفین به درخواست آتش بس
    """
    try:
        # نگاشت war_key (ممکن است war_id یا هش کوتاه آن باشد) به war_id واقعی
        war_id = None
        if hasattr(utils, 'ceasefire_requests'):
            if war_key in utils.ceasefire_requests:
                war_id = war_key
            else:
                import hashlib
                for wid in utils.ceasefire_requests.keys():
                    h = hashlib.sha1(wid.encode('utf-8')).hexdigest()
                    if h == war_key or h.startswith(war_key):
                        war_id = wid
                        break
        if not war_id:
            await query.answer("❌ درخواست آتش بس یافت نشد!", show_alert=True)
            return

        user_id = str(query.from_user.id)
        user = utils.users.get(str(user_id), {})
        user_country = user.get('country', 'نامشخص')
        
        # بررسی اینکه آیا کاربر در این جنگ شرکت دارد
        if not hasattr(utils, 'ceasefire_requests') or war_id not in utils.ceasefire_requests:
            await query.answer("❌ درخواست آتش بس یافت نشد!", show_alert=True)
            return
        
        ceasefire_data = utils.ceasefire_requests[war_id]
        attacker = ceasefire_data.get('attacker', 'نامشخص')
        defender = ceasefire_data.get('defender', 'نامشخص')
        
        if user_country not in [attacker, defender]:
            await query.answer("❌ شما در این جنگ شرکت ندارید!", show_alert=True)
            return
        
        # ثبت پاسخ کاربر
        if user_country == attacker:
            ceasefire_data['attacker_response'] = response
        else:
            ceasefire_data['defender_response'] = response
        
        utils.ceasefire_requests[war_id] = ceasefire_data
        
        # پیام پاسخ
        if response == 'accept':
            response_text = "✅ موافقت با آتش بس"
            response_emoji = "🕊️"
        else:
            response_text = "❌ مخالفت با آتش بس"
            response_emoji = "⚔️"
        
        # پیام تایید
        confirm_text = (
            f"{response_emoji} <b>پاسخ شما ثبت شد!</b>\n\n"
            f"⚔️ <b>جنگ:</b> {attacker} vs {defender}\n"
            f"🏛️ <b>کشور شما:</b> {user_country}\n"
            f"🔘 <b>پاسخ:</b> {response_text}\n\n"
        )
        
        if response == 'accept':
            confirm_text += "🕊️ <b>امیدواریم طرف مقابل نیز موافقت کند!</b>"
        else:
            confirm_text += "⚔️ <b>جنگ ادامه خواهد داشت.</b>"
        
        # بررسی وضعیت کلی
        attacker_response = ceasefire_data.get('attacker_response')
        defender_response = ceasefire_data.get('defender_response')
        
        if attacker_response == 'accept' and defender_response == 'accept':
            confirm_text += "\n\n🎉 <b>هر دو طرف موافقت کردند!</b>\n"
            confirm_text += "آتش بس اعمال می‌شود و جنگ پایان می‌یابد."
            
            # اعمال آتش بس
            from united_nations import apply_ceasefire
            await apply_ceasefire(war_id)
            # امتیاز صلح برای هر دو کشور موافق (تنها یک‌بار)
            try:
                if not ceasefire_data.get('scored'):
                    import utils as _utils
                    utils.un_peace_scores[attacker] = utils.un_peace_scores.get(attacker, 0) + 1
                    utils.un_peace_scores[defender] = utils.un_peace_scores.get(defender, 0) + 1
                    ceasefire_data['scored'] = True
                    utils.ceasefire_requests[war_id] = ceasefire_data
                    if hasattr(_utils, 'save_un_data'):
                        utils.save_un_data()
            except Exception:
                pass
            
        elif attacker_response == 'reject' or defender_response == 'reject':
            confirm_text += "\n\n❌ <b>یکی از طرفین مخالفت کرد!</b>\n"
            confirm_text += "درخواست آتش بس رد شد."
            
            # لغو درخواست
            ceasefire_data['status'] = 'rejected'
            utils.ceasefire_requests[war_id] = ceasefire_data
            # امتیاز منفی برای طرفی که رد کرده (تنها یک‌بار)
            try:
                if not ceasefire_data.get('scored'):
                    import utils as _utils
                    if attacker_response == 'reject':
                        utils.un_peace_scores[attacker] = utils.un_peace_scores.get(attacker, 0) - 1
                    elif defender_response == 'reject':
                        utils.un_peace_scores[defender] = utils.un_peace_scores.get(defender, 0) - 1
                    else:
                        # اگر فقط کاربر فعلی مخالفت کرده باشد
                        utils.un_peace_scores[user_country] = utils.un_peace_scores.get(user_country, 0) - 1
                    ceasefire_data['scored'] = True
                    utils.ceasefire_requests[war_id] = ceasefire_data
                    if hasattr(_utils, 'save_un_data'):
                        utils.save_un_data()
            except Exception:
                pass
        
        await query.edit_message_text(confirm_text, parse_mode='HTML')
        
    except Exception as e:
        error_text = f"❌ <b>خطا در ثبت پاسخ:</b>\n\n{str(e)}"
        await query.edit_message_text(error_text, parse_mode='HTML')


def season_reset():
    """ریست کامل تمام فایل‌های بازی برای شروع فصل جدید"""
    import utils as _utils
    
    try:
        # ریست game_data.json با حفظ شماره فصل افزایش‌یافته
        current_season = int(_utils.game_data.get('season', 1))
        game_data_content = {
            "turn": 1,
            "season": current_season,
            "game_date": "01/01/2024",
            "prices": {
                "gold": 5000000,
                "steel": 2000000,
                "oil": 1500000,
                "electricity": 1000000
            }
        }
        
        with open('game_data.json', 'w', encoding='utf-8') as f:
            json.dump(game_data_content, f, ensure_ascii=False, indent=2)
        
        # ریست bank_data.json با ساختار کامل
        bank_data_content = {
            "total_loans_given": 0,
            "total_loans_paid": 0,
            "total_interest_earned": 0,
            "bank_reserves": 100000000000,
            "loan_types": {
                "independence": {
                    "amount": 1000000000,
                    "interest_rate": 0.04,
                    "duration": 4,
                    "max_uses": 1
                },
                "development": {
                    "amount": 500000000,
                    "interest_rate": 0.22,
                    "duration": 6,
                    "max_uses": 3
                },
                "emergency": {
                    "amount": 200000000,
                    "interest_rate": 0.12,
                    "duration": 3,
                    "max_uses": 5
                },
                "secret": {
                    "amount": 300000000,
                    "interest_rate": 0.08,
                    "duration": 5,
                    "max_uses": 2
                }
            }
        }
        
        with open('bank_data.json', 'w', encoding='utf-8') as f:
            json.dump(bank_data_content, f, ensure_ascii=False, indent=2)
        
        # ریست military_packages.json
        military_packages_content = {
            "military_package_purchases": {},
            "military_package_cooldowns": {},
            "military_package_approvals": {}
        }
        
        with open('military_packages.json', 'w', encoding='utf-8') as f:
            json.dump(military_packages_content, f, ensure_ascii=False, indent=2)
        
        # ریست economic_packages.json
        economic_packages_content = {
            "economic_package_purchases": {},
            "economic_package_cooldowns": {},
            "economic_package_approvals": {}
        }
        
        with open('economic_packages.json', 'w', encoding='utf-8') as f:
            json.dump(economic_packages_content, f, ensure_ascii=False, indent=2)
        
        # ریست resource_packages.json
        resource_packages_content = {
            "resource_package_purchases": {},
            "resource_package_cooldowns": {},
            "resource_package_approvals": {}
        }
        
        with open('resource_packages.json', 'w', encoding='utf-8') as f:
            json.dump(resource_packages_content, f, ensure_ascii=False, indent=2)
        
        # ریست فایل‌های دیگر به حالت خالی
        empty_dict_files = [
            'loan_history.json',
            'transfer_history.json',
            'pending_trades.json',
            'pending_payments.json',
            'bank_accounts.json',
            'overdue_debts.json',
            'country_relations.json',
            'war_declarations.json',
            'alliances.json',
            'alliance_messages.json'
        ]
        
        for filename in empty_dict_files:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
        
        # ریست فایل‌هایی که باید لیست خالی باشند
        empty_list_files = [
            'active_loans.json',
            'ground_attacks.json',
            'naval_attack_saves.json',
            'naval_attacks_active.json'
        ]
        
        for filename in empty_list_files:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        
        print("✅ تمام فایل‌های بازی با موفقیت ریست شدند")
        
    except Exception as e:
        print(f"❌ خطا در ریست فایل‌های بازی: {e}")


if __name__ == '__main__':
    import asyncio
    import sys

    if sys.platform.startswith('win') and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    import nest_asyncio
    nest_asyncio.apply()

    import asyncio
    asyncio.run(main())