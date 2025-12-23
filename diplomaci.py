from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from datetime import datetime
from uuid import uuid4
import json
import time
import utils
from utils import (
    ADMIN_ID,
    NEWS_CHANNEL_ID,
    pending_create_alliance,
    pending_peace_requests,
    save_alliances,
    pending_alliance_chat,
    pending_help_request,
    pending_help_give,
    game_data,
    user_alliances,
    alliances,
    pending_statement,
    alliance_messages,
    war_declarations,
    alliance_leave_turn,
    pending_edit_alliance,
    pending_set_deputy,
    alliance_help_requests,
    get_relation_text,
    embassy_requests,
    relation_improvement_requests,
    save_users,
    country_relations,
    save_country_relations,
    users,
    pending_private_message,
)
import asyncio
import random
from telegram.ext import ContextTypes

"""
همسان‌سازی دسترسی به کاربران: از این پس هر ارجاع به users به utils.users اشاره می‌کند
تا از NameError جلوگیری شود و در عین حال با ساختار فعلی فایل سازگار بماند.
توجه: اگر utils.users به‌طور کامل جایگزین شود، بهتر است ارجاعات به utils.users به‌صورت مستقیم
بازنویسی شوند. این خط صرفاً برای حفظ سازگاری فوری است.
"""
users = utils.users

async def show_simple_section(query, message):
    """نمایش پیام ساده"""
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(message, reply_markup=reply_markup)

async def show_alliance_menu(query):
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    country_name = user.get('country', 'کشور ناشناس')
    
    # استفاده از وزیر خارجه انتخاب شده
    selected_officials = user.get('selected_officials', {})
    if 'foreign' in selected_officials:
        foreign_minister = selected_officials['foreign']
    else:
        # اگر وزیر خارجه انتخاب نشده، از اسامی پیش‌فرض استفاده کن
        foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
    
    # پیام خوشامدگویی
    text = f"🤝 <b>خوش آمدید!</b>\n\n"
    text += f"🤝 من {foreign_minister['name']}، {foreign_minister['title']} شما هستم.\n"
    text += f"🤝 <b>منوی اتحاد کشور {country_name}</b>\n\n"
    
    user_alliance_id = utils.user_alliances.get(user_id)
    
    if user_alliance_id and user_alliance_id in utils.alliances:
        # کاربر در اتحاد است
        alliance = utils.alliances[user_alliance_id]
        is_leader = (alliance.get('leader') == user_id)
        is_deputy = (alliance.get('deputy') == user_id)
        
        # متن اصلی
        text += f"🤝 <b>اتحاد شما: {alliance['name']}</b>\n"
        text += f"👥 تعداد اعضا: {len(alliance['members'])}\n"
        text += f"💵 هزینه عضویت: {alliance['entry_fee']:,} دلار\n\n"
        
        if is_leader:
            text += "👑 <b>شما رهبر این اتحاد هستید</b>"
        elif is_deputy:
            text += "👑 <b>شما جانشین رهبر این اتحاد هستید</b>"
        else:
            text += "👤 <b>شما عضو این اتحاد هستید</b>"
        
        # تحلیل هوشمند اتحاد
        from analysis import generate_alliance_analysis
        analysis = generate_alliance_analysis(user_id)
        
        text += f"\n<b>پیشنهاد {foreign_minister['title']} {foreign_minister['name']}:</b>\n<blockquote>{analysis}</blockquote>"
        
        keyboard = []
        
        # دکمه‌های عمومی برای همه اعضا
        keyboard.append([InlineKeyboardButton('💬 چت اتحاد', callback_data='alliance_chat'), InlineKeyboardButton('👥 اعضای اتحاد', callback_data='alliance_members')])
        keyboard.append([InlineKeyboardButton('🤲 درخواست کمک', callback_data='alliance_help_request'), InlineKeyboardButton('🤝 کمک به اعضا', callback_data='alliance_help_give')])
        
        # دکمه اعلام جلسه فوری فقط برای رهبر و جانشین
        if is_leader or is_deputy:
            keyboard.append([InlineKeyboardButton('📢 اعلام جلسه فوری', callback_data='alliance_urgent_meeting')])
        
        # دکمه‌های ویژه رهبر (دو ستونی)
        if is_leader:
            keyboard.append([InlineKeyboardButton('✏️ ویرایش توضیحات', callback_data='edit_alliance_desc'), InlineKeyboardButton('📜 ویرایش قوانین', callback_data='edit_alliance_rules')])
            keyboard.append([InlineKeyboardButton('🖼️ ویرایش لوگو', callback_data='edit_alliance_logo'), InlineKeyboardButton('💵 ویرایش هزینه عضویت', callback_data='edit_alliance_entry_fee')])
            keyboard.append([InlineKeyboardButton('👑 تعیین جانشین', callback_data='set_alliance_deputy'), InlineKeyboardButton('❌ اخراج اعضا', callback_data='alliance_kick_member')])
            keyboard.append([InlineKeyboardButton('📢 تبلیغ اتحاد', callback_data='alliance_advertisement')])
        
        # دکمه خروج از اتحاد
        keyboard.append([InlineKeyboardButton('🚪 خروج از اتحاد', callback_data='leave_alliance')])
        
        # دکمه‌های پایین
        keyboard.append([InlineKeyboardButton('📋 لیست اتحادها', callback_data='alliance_list')])
        keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='diplomacy')])
        
    else:
        # کاربر در اتحاد نیست
        text += "شما در هیچ اتحادی عضو نیستید.\n"
        text += "می‌توانید اتحاد جدید ایجاد کنید یا به اتحاد موجود بپیوندید."
        
        # تحلیل هوشمند برای کاربران بدون اتحاد
        from analysis import generate_no_alliance_analysis
        analysis = generate_no_alliance_analysis(user_id)
        
        text += f"\n<b>پیشنهاد {foreign_minister['title']} {foreign_minister['name']}:</b>\n<blockquote>{analysis}</blockquote>"
        
        keyboard = [
            [InlineKeyboardButton('📋 لیست اتحادها', callback_data='alliance_list')],
            [InlineKeyboardButton('➕ ایجاد اتحاد جدید', callback_data='create_alliance')],
            [InlineKeyboardButton('🔍 جستجوی اتحاد', callback_data='search_alliance')],
            [InlineKeyboardButton('بازگشت ⬅️', callback_data='diplomacy')]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# --- منوی تبلیغ اتحاد ---
async def show_alliance_advertisement_menu(query):
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    country_name = user.get('country', 'کشور ناشناس')
    
    user_alliance_id = utils.user_alliances.get(user_id)
    if not user_alliance_id or user_alliance_id not in utils.alliances:
        await query.answer('شما در هیچ اتحادی عضو نیستید!')
        return
    
    alliance = utils.alliances[user_alliance_id]
    is_leader = (alliance.get('leader') == user_id)
    if not is_leader:
        await query.answer('فقط رهبر اتحاد می‌تواند تبلیغ کند!', show_alert=True)
        return
    
    text = f"📢 <b>تبلیغ اتحاد {alliance['name']}</b>\n\n"
    text += f"🌍 کشور: {country_name}\n"
    text += f"👥 تعداد اعضا: {len(alliance['members'])}\n"
    text += f"💵 هزینه عضویت: {alliance['entry_fee']:,} دلار\n\n"
    text += "انتخاب کنید که چگونه می‌خواهید اتحاد خود را تبلیغ کنید:\n\n"
    text += "1️⃣ <b>ارسال اگهی عادی:</b> 50 میلیون دلار\n"
    text += "   • ارسال یکبار در کانال اخبار\n\n"
    text += "2️⃣ <b>ارسال اگهی و سنجاق:</b> 200 میلیون دلار\n"
    text += "   • ارسال در کانال اخبار + سنجاق 2 روزه\n"
    
    keyboard = [
        [InlineKeyboardButton('📢 اگهی عادی (50M)', callback_data='alliance_ad_normal')],
        [InlineKeyboardButton('📌 اگهی + سنجاق (200M)', callback_data='alliance_ad_pinned')],
        [InlineKeyboardButton('بازگشت ⬅️', callback_data='alliance_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# --- هندلر تبلیغ عادی اتحاد ---
async def handle_alliance_ad_normal(query):
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    user_alliance_id = utils.user_alliances.get(user_id)
    
    if not user_alliance_id or user_alliance_id not in utils.alliances:
        await query.answer('شما در هیچ اتحادی عضو نیستید!')
        return
    
    alliance = utils.alliances[user_alliance_id]
    is_leader = (alliance.get('leader') == user_id)
    if not is_leader:
        await query.answer('فقط رهبر اتحاد می‌تواند تبلیغ کند!', show_alert=True)
        return
    
    cost = 50_000_000
    user_cash = user.get('resources', {}).get('cash', 0)
    
    if user_cash < cost:
        await query.answer(f'موجودی نقد شما کافی نیست! نیاز: {cost:,} دلار', show_alert=True)
        return
    
    text = f"📢 <b>تایید تبلیغ عادی اتحاد</b>\n\n"
    text += f"🏛 نام اتحاد: {alliance['name']}\n"
    text += f"💰 هزینه: {cost:,} دلار\n"
    text += f"💵 موجودی شما: {user_cash:,} دلار\n\n"
    text += "آیا مطمئن هستید که می‌خواهید این تبلیغ را انجام دهید؟"
    
    keyboard = [
        [InlineKeyboardButton('✅ تایید و پرداخت', callback_data='confirm_alliance_ad_normal')],
        [InlineKeyboardButton('❌ لغو', callback_data='alliance_advertisement')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# --- هندلر تبلیغ سنجاق شده اتحاد ---
async def handle_alliance_ad_pinned(query):
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    user_alliance_id = utils.user_alliances.get(user_id)
    
    if not user_alliance_id or user_alliance_id not in utils.alliances:
        await query.answer('شما در هیچ اتحادی عضو نیستید!')
        return
    
    alliance = utils.alliances[user_alliance_id]
    is_leader = (alliance.get('leader') == user_id)
    if not is_leader:
        await query.answer('فقط رهبر اتحاد می‌تواند تبلیغ کند!', show_alert=True)
        return
    
    cost = 200_000_000
    user_cash = user.get('resources', {}).get('cash', 0)
    
    if user_cash < cost:
        await query.answer(f'موجودی نقد شما کافی نیست! نیاز: {cost:,} دلار', show_alert=True)
        return
    
    text = f"📌 <b>تایید تبلیغ سنجاق شده اتحاد</b>\n\n"
    text += f"🏛 نام اتحاد: {alliance['name']}\n"
    text += f"💰 هزینه: {cost:,} دلار\n"
    text += f"💵 موجودی شما: {user_cash:,} دلار\n\n"
    text += "آیا مطمئن هستید که می‌خواهید این تبلیغ را انجام دهید؟\n"
    text += "(پیام 2 روز سنجاق خواهد شد)"
    
    keyboard = [
        [InlineKeyboardButton('✅ تایید و پرداخت', callback_data='confirm_alliance_ad_pinned')],
        [InlineKeyboardButton('❌ لغو', callback_data='alliance_advertisement')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# --- تایید نهایی تبلیغ عادی ---
async def confirm_alliance_ad_normal(query, context):
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    user_alliance_id = utils.user_alliances.get(user_id)
    
    if not user_alliance_id or user_alliance_id not in utils.alliances:
        await query.answer('شما در هیچ اتحادی عضو نیستید!')
        return
    
    alliance = utils.alliances[user_alliance_id]
    is_leader = (alliance.get('leader') == user_id)
    if not is_leader:
        await query.answer('فقط رهبر اتحاد می‌تواند تبلیغ کند!', show_alert=True)
        return
    
    cost = 50_000_000
    user_cash = user.get('resources', {}).get('cash', 0)
    
    if user_cash < cost:
        await query.answer(f'موجودی نقد شما کافی نیست! نیاز: {cost:,} دلار', show_alert=True)
        return
    
    # کسر پول
    utils.users[user_id]['resources']['cash'] -= cost
    utils.save_users()
    
    # ایجاد متن اگهی
    country_name = user.get('country', 'کشور ناشناس')
    ad_text = f"📢 <b>تبلیغ اتحاد</b>\n\n"
    ad_text += f"🏛 <b>نام اتحاد:</b> {alliance['name']}\n"
    ad_text += f"🌍 <b>کشور رهبر:</b> {country_name}\n"
    ad_text += f"👥 <b>تعداد اعضا:</b> {len(alliance['members'])}\n"
    ad_text += f"💵 <b>هزینه عضویت:</b> {alliance['entry_fee']:,} دلار\n"
    
    if alliance.get('desc'):
        ad_text += f"📝 <b>توضیحات:</b> {alliance['desc']}\n"
    
    ad_text += f"\n🔗 برای عضویت در این اتحاد، از منوی دیپلماسی استفاده کنید."
    
    # ارسال به کانال اخبار
    try:
        from utils import NEWS_CHANNEL_ID
        
        # اگر اتحاد لوگو دارد، با عکس ارسال کن
        if alliance.get('logo'):
            await context.bot.send_photo(
                chat_id=NEWS_CHANNEL_ID,
                photo=alliance['logo'],
                caption=ad_text,
                parse_mode='HTML'
            )
        else:
            await context.bot.send_message(
                chat_id=NEWS_CHANNEL_ID,
                text=ad_text,
                parse_mode='HTML'
            )
        
        # پیام موفقیت به کاربر
        success_text = f"✅ <b>تبلیغ با موفقیت ارسال شد!</b>\n\n"
        success_text += f"💰 هزینه پرداخت شده: {cost:,} دلار\n"
        success_text += f"💵 موجودی باقی‌مانده: {utils.users[user_id]['resources']['cash']:,} دلار\n\n"
        success_text += "📢 اگهی اتحاد شما در کانال اخبار منتشر شد."
        
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='alliance_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        # در صورت خطا، پول را برگردان
        utils.users[user_id]['resources']['cash'] += cost
        utils.save_users()
        await query.answer(f'خطا در ارسال اگهی: {str(e)}', show_alert=True)

# --- تایید نهایی تبلیغ سنجاق شده ---
async def confirm_alliance_ad_pinned(query, context):
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    user_alliance_id = utils.user_alliances.get(user_id)
    
    if not user_alliance_id or user_alliance_id not in utils.alliances:
        await query.answer('شما در هیچ اتحادی عضو نیستید!')
        return
    
    alliance = utils.alliances[user_alliance_id]
    is_leader = (alliance.get('leader') == user_id)
    if not is_leader:
        await query.answer('فقط رهبر اتحاد می‌تواند تبلیغ کند!', show_alert=True)
        return
    
    cost = 200_000_000
    user_cash = user.get('resources', {}).get('cash', 0)
    
    if user_cash < cost:
        await query.answer(f'موجودی نقد شما کافی نیست! نیاز: {cost:,} دلار', show_alert=True)
        return
    
    # کسر پول
    utils.users[user_id]['resources']['cash'] -= cost
    utils.save_users()
    
    # ایجاد متن اگهی
    country_name = user.get('country', 'کشور ناشناس')
    ad_text = f"📌 <b>تبلیغ ویژه اتحاد</b>\n\n"
    ad_text += f"🏛 <b>نام اتحاد:</b> {alliance['name']}\n"
    ad_text += f"🌍 <b>کشور رهبر:</b> {country_name}\n"
    ad_text += f"👥 <b>تعداد اعضا:</b> {len(alliance['members'])}\n"
    ad_text += f"💵 <b>هزینه عضویت:</b> {alliance['entry_fee']:,} دلار\n"
    
    if alliance.get('desc'):
        ad_text += f"📝 <b>توضیحات:</b> {alliance['desc']}\n"
    
    ad_text += f"\n🔗 برای عضویت در این اتحاد، از منوی دیپلماسی استفاده کنید.\n"
    ad_text += f"⏰ این پیام 2 روز سنجاق خواهد بود."
    
    # ارسال به کانال اخبار و سنجاق کردن
    try:
        from utils import NEWS_CHANNEL_ID
        
        # اگر اتحاد لوگو دارد، با عکس ارسال کن
        if alliance.get('logo'):
            message = await context.bot.send_photo(
                chat_id=NEWS_CHANNEL_ID,
                photo=alliance['logo'],
                caption=ad_text,
                parse_mode='HTML'
            )
        else:
            message = await context.bot.send_message(
                chat_id=NEWS_CHANNEL_ID,
                text=ad_text,
                parse_mode='HTML'
            )
        
        # سنجاق کردن پیام برای 2 روز
        await context.bot.pin_chat_message(
            chat_id=NEWS_CHANNEL_ID,
            message_id=message.message_id,
            disable_notification=True
        )
        
        # برنامه‌ریزی برای برداشتن سنجاق بعد از 2 روز
        from datetime import datetime, timedelta
        unpin_time = datetime.now() + timedelta(days=2)
        
        # ذخیره اطلاعات برای برداشتن سنجاق
        if not hasattr(utils, 'pinned_messages'):
            utils.pinned_messages = {}
        
        utils.pinned_messages[message.message_id] = {
            'chat_id': NEWS_CHANNEL_ID,
            'unpin_time': unpin_time.isoformat()
        }
        
        # پیام موفقیت به کاربر
        success_text = f"✅ <b>تبلیغ سنجاق شده با موفقیت ارسال شد!</b>\n\n"
        success_text += f"💰 هزینه پرداخت شده: {cost:,} دلار\n"
        success_text += f"💵 موجودی باقی‌مانده: {utils.users[user_id]['resources']['cash']:,} دلار\n\n"
        success_text += "📌 اگهی اتحاد شما در کانال اخبار منتشر و سنجاق شد.\n"
        success_text += "⏰ سنجاق بعد از 2 روز برداشته خواهد شد."
        
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='alliance_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        # در صورت خطا، پول را برگردان
        utils.users[user_id]['resources']['cash'] += cost
        utils.save_users()
        await query.answer(f'خطا در ارسال اگهی: {str(e)}', show_alert=True)

# --- مدیریت سنجاق پیام‌ها ---
async def check_and_unpin_messages(context):
    """بررسی و برداشتن سنجاق پیام‌هایی که زمانشان تمام شده"""
    if not hasattr(utils, 'pinned_messages'):
        return
    
    from datetime import datetime
    current_time = datetime.now()
    messages_to_remove = []
    
    for message_id, data in utils.pinned_messages.items():
        unpin_time = datetime.fromisoformat(data['unpin_time'])
        if current_time >= unpin_time:
            try:
                await context.bot.unpin_chat_message(
                    chat_id=data['chat_id'],
                    message_id=message_id
                )
                messages_to_remove.append(message_id)
            except Exception as e:
                print(f"خطا در برداشتن سنجاق پیام {message_id}: {e}")
    
    # حذف پیام‌های پردازش شده از لیست
    for message_id in messages_to_remove:
        del utils.pinned_messages[message_id]

# --- هندلر اعلام جلسه فوری ---
async def handle_alliance_urgent_meeting(query, context):
    user_id = str(query.from_user.id)
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id or alliance_id not in alliances:
        await query.answer('شما در هیچ اتحادی عضو نیستید!')
        return
    alliance = utils.alliances[alliance_id]
    is_leader = (alliance.get('leader') == user_id)
    is_deputy = (alliance.get('deputy') == user_id)
    if not (is_leader or is_deputy):
        await query.answer('فقط رهبر یا جانشین اتحاد می‌تواند جلسه فوری اعلام کند!', show_alert=True)
        return
    # ارسال پیام به همه اعضا
    for member_id in alliance['members']:
        try:
            await context.bot.send_message(
                chat_id=int(member_id),
                text=f'📢 <b>جلسه فوری اتحاد {alliance["name"]}!</b>\n\nلطفاً هرچه سریع‌تر در چت اتحاد حضور پیدا کنید.',
                parse_mode='HTML'
            )
        except Exception as e:
            print(f'خطا در ارسال پیام جلسه فوری به کاربر {member_id}: {e}')
    await query.answer('جلسه فوری به همه اعضا ارسال شد!', show_alert=True)
    await query.edit_message_text('📢 جلسه فوری به همه اعضای اتحاد ارسال شد.')
  # user_id: {'step': 'target', 'target_id': ...}

async def show_alliance_chat(query):
    """نمایش چت اتحاد"""
    user_id = str(query.from_user.id)
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await query.answer('شما در هیچ اتحادی نیستید!')
        return
    alliance = utils.alliances.get(alliance_id)
    if not alliance:
        await query.answer('اتحاد یافت نشد!')
        return
    
    # دریافت پیام‌های اتحاد
    messages = alliance_messages.get(alliance_id, [])
    
    if not messages:
        text = f"💬 <b>چت اتحاد {alliance['name']}</b>\n\nهنوز پیامی ارسال نشده است."
    else:
        # نمایش آخرین 10 پیام
        recent_messages = messages[-10:]
        text = f"💬 <b>چت اتحاد {alliance['name']}</b>\n\n"
        for msg in recent_messages:
            timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M')
            text += f"<b>{msg['country']}</b> ({timestamp}):\n{msg['message']}\n\n"
    
    text += "\n📝 برای ارسال پیام، متن خود را بنویسید:"
    
    # تنظیم برای دریافت پیام
    pending_alliance_chat[user_id] = alliance_id
    
    keyboard = [
        [InlineKeyboardButton('📜 تاریخچه کامل', callback_data='alliance_chat_history')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='alliance_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_alliance_chat_history(query):
    """نمایش تاریخچه کامل چت اتحاد"""
    user_id = str(query.from_user.id)
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await query.answer('شما در هیچ اتحادی نیستید!')
        return
    alliance = utils.alliances.get(alliance_id)
    if not alliance:
        await query.answer('اتحاد یافت نشد!')
        return
    
    # دریافت تمام پیام‌های اتحاد
    messages = alliance_messages.get(alliance_id, [])
    
    if not messages:
        text = f"📜 <b>تاریخچه چت اتحاد {alliance['name']}</b>\n\nهنوز پیامی ارسال نشده است."
    else:
        text = f"📜 <b>تاریخچه چت اتحاد {alliance['name']}</b>\n\n"
        for i, msg in enumerate(messages, 1):
            timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%Y/%m/%d %H:%M')
            text += f"<b>{i}. {msg['country']}</b> ({timestamp}):\n{msg['message']}\n\n"
    
    keyboard = [
        [InlineKeyboardButton('🔙 بازگشت به چت', callback_data='alliance_chat')],
        [InlineKeyboardButton('🔙 بازگشت به منو', callback_data='alliance_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_alliance_message(update, context):
    user_id = str(update.effective_user.id)
    alliance_id = pending_alliance_chat.get(user_id)
    # اگر کاربر دیگر عضو اتحاد نیست یا آی‌دی او در user_alliances نیست یا اتحادش تغییر کرده، اجازه ارسال پیام نده
    if not alliance_id or user_id not in utils.user_alliances or utils.user_alliances[user_id] != alliance_id:
        if user_id in pending_alliance_chat:
            del pending_alliance_chat[user_id]
        await update.message.reply_text('شما دیگر عضو این اتحاد نیستید و نمی‌توانید پیام ارسال کنید.')
        return
    message_text = update.message.text if hasattr(update.message, 'text') and update.message.text else ""
    user_country = utils.users.get(user_id, {}).get('country', 'کشور ناشناس')
    # ذخیره پیام
    if alliance_id not in alliance_messages:
        alliance_messages[alliance_id] = []
    new_message = {
        'user_id': user_id,
        'country': f"{user_country} ({utils.get_user_capital(user_id)})",
        'message': message_text,
        'timestamp': datetime.now().isoformat()
    }
    alliance_messages[alliance_id].append(new_message)
    
    # ذخیره تاریخچه چت در فایل
    utils.save_alliance_messages()
    
    # ارسال پیام به همه اعضای اتحاد
    alliance = alliances.get(alliance_id, {})
    for member_id in alliance.get('members', []):
        if member_id != user_id:
            if utils.user_alliances.get(member_id) == alliance_id:
                try:
                    await context.bot.send_message(
                        chat_id=int(member_id),
                        text=f"💬 <b>پیام جدید در اتحاد {alliance['name']}</b>\n\n<b>{user_country}:</b>\n{message_text}",
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"خطا در ارسال پیام به کاربر {member_id}: {e}")
    
    # Check for alliance spying
    await check_and_forward_alliance_spied_message(alliance_id, f"💬 {user_country}: {message_text}", context)
    await update.message.reply_text("✅ پیام شما در چت اتحاد ارسال شد.")



 # user_id: {'step': ..., ...}

async def handle_create_alliance(update, context):
    user_id = str(update.effective_user.id)
    data = pending_create_alliance.get(user_id, {})
    step = data.get('step')

    if step == 'name':
        name = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
        data['name'] = name
        data['step'] = 'desc'
        await update.message.reply_text('توضیحات اتحاد را ارسال کنید (حداکثر ۴ خط):')
    elif step == 'desc':
        desc = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
        if desc.count('\n') > 3:
            await update.message.reply_text('توضیحات نباید بیشتر از ۴ خط باشد. لطفاً دوباره ارسال کنید.')
            return
        data['desc'] = desc
        data['step'] = 'rules'
        await update.message.reply_text('قوانین اتحاد را ارسال کنید (حداکثر ۸ خط):')
    elif step == 'rules':
        rules = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
        if rules.count('\n') > 7:
            await update.message.reply_text('قوانین نباید بیشتر از ۸ خط باشد. لطفاً دوباره ارسال کنید.')
            return
        data['rules'] = rules
        data['step'] = 'logo'
        await update.message.reply_text('لطفاً یک تصویر یا لوگوی اتحاد را ارسال کنید:')
    elif step == 'logo':
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            data['logo'] = file_id
            data['step'] = 'entry_fee'
            await update.message.reply_text('هزینه ورودی اتحاد (برای هر کشور) را به دلار وارد کنید:')
        else:
            await update.message.reply_text('لطفاً یک عکس ارسال کنید.')
    elif step == 'entry_fee':
        try:
            entry_fee = int((update.message.text if hasattr(update.message, 'text') and update.message.text else '').replace(',', ''))
            if entry_fee < 0:
                raise ValueError
        except:
            await update.message.reply_text('عدد معتبر وارد کنید.')
            return
        data['entry_fee'] = entry_fee
        # ذخیره اتحاد
        alliance_id = str(uuid4())
        utils.alliances[alliance_id] = {
            'name': data['name'],
            'desc': data['desc'],
            'rules': data['rules'],
            'logo': data['logo'],
            'entry_fee': data['entry_fee'],
            'members': [user_id],
            'leader': user_id,
            'deputy': None
        }
        utils.user_alliances[user_id] = alliance_id
        utils.users[user_id]['resources']['cash'] -= 100_000_000
        print(f"[DEBUG] Creating alliance: {alliance_id} for user: {user_id}")
        print(f"[DEBUG] Alliances before save: {utils.alliances}")
        print(f"[DEBUG] User alliances before save: {utils.user_alliances}")
        utils.save_alliances()
        utils.save_users()
        del pending_create_alliance[user_id]
        
        # ارسال پیام موفقیت و سپس نمایش منوی اتحاد
        await update.message.reply_text(f'🎉 اتحاد "{data["name"]}" با موفقیت ساخته شد!')
        
        # نمایش منوی اتحاد برای کاربر جدید
        user_alliance_id = utils.user_alliances.get(user_id)
        
        if user_alliance_id:
            # کاربر در اتحاد است
            alliance = utils.alliances[user_alliance_id]
            is_leader = (alliance.get('leader') == user_id)
            is_deputy = (alliance.get('deputy') == user_id)
            keyboard = [
                [InlineKeyboardButton('💬 چت اتحاد', callback_data='alliance_chat'), InlineKeyboardButton('👥 اعضای اتحاد', callback_data='alliance_members')],
                [InlineKeyboardButton('🤲 کمک', callback_data='alliance_help')],
            ]
            # دکمه اعلام جلسه فوری فقط برای رهبر و جانشین
            if is_leader or is_deputy:
                keyboard.append([InlineKeyboardButton('📢 اعلام جلسه فوری', callback_data='alliance_urgent_meeting')])
            # دکمه‌های ویژه رهبر (دو ستونی)
            if is_leader:
                keyboard += [
                    [InlineKeyboardButton('✏️ ویرایش توضیحات', callback_data='edit_alliance_desc'), InlineKeyboardButton('📜 ویرایش قوانین', callback_data='edit_alliance_rules')],
                    [InlineKeyboardButton('🖼️ ویرایش لوگو', callback_data='edit_alliance_logo'), InlineKeyboardButton('💵 ویرایش هزینه عضویت', callback_data='edit_alliance_entry_fee')],
                    [InlineKeyboardButton('👑 تعیین جانشین', callback_data='set_alliance_deputy'), InlineKeyboardButton('❌ اخراج اعضا', callback_data='alliance_kick_member')],
                ]
            keyboard.append([InlineKeyboardButton('❌ خروج از اتحاد', callback_data='leave_alliance')])
            keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='diplomacy')])
            keyboard.append([InlineKeyboardButton('اتحادها 📜', callback_data='alliance_list')])
            text = f"🤝 اتحاد شما: {alliance['name']}\nتعداد اعضا: {len(alliance['members'])}"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup)

        # ارسال اطلاعات اتحاد به کانال اخبار
        NEWS_CHANNEL_ID = '@TextEmpire_News'  # کانال اخبار جدید

        alliance_info = (
            f"🎉 <b>اتحاد جدید ساخته شد!</b>\n\n"
            f"<b>نام اتحاد:</b> {data['name']}\n"
            f"📝 <b>توضیحات:</b>\n{data['desc']}\n\n"
            f"📜 <b>قوانین:</b>\n{data['rules']}\n\n"
            f"💵 <b>هزینه عضویت:</b> {data['entry_fee']:,} دلار"
        )

        try:
            await context.bot.send_photo(
                chat_id=NEWS_CHANNEL_ID,
                photo=data['logo'],
                caption=alliance_info,
                parse_mode='HTML'
            )
        except Exception as e:
            print(f"خطا در ارسال اتحاد جدید به کانال اخبار: {e}")

async def show_alliance_list(query, user_id):
    if not utils.alliances:
        await query.edit_message_text('هیچ اتحادی وجود ندارد.')
        return

    for alliance_id, data in utils.alliances.items():
        text = f"<b>{data['name']}</b>\n\n"
        text += f"📝 <b>توضیحات:</b>\n{data['desc']}\n\n"
        text += f"📜 <b>قوانین:</b>\n{data['rules']}\n\n"
        text += f"💵 <b>هزینه عضویت:</b> {data['entry_fee']:,} دلار"
        # دکمه عضویت فقط اگر کاربر عضو نیست
        is_member = utils.user_alliances.get(user_id) == alliance_id
        keyboard = []
        if not is_member:
            keyboard.append([InlineKeyboardButton(f"عضویت ({data['entry_fee']:,}💵)", callback_data=f'join_alliance_{alliance_id}')])
        else:
            keyboard.append([InlineKeyboardButton("شما عضو این اتحاد هستید", callback_data='alliance_menu')])
        keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='alliance_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        # ارسال عکس و متن
        try:
            await query.message.reply_photo(
                photo=data['logo'],
                caption=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        except Exception as e:
            # اگر عکس مشکل داشت فقط متن بفرست
            await query.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    # پیام اولیه را حذف کن تا فقط پیام‌های اتحادها بماند
    try:
        await query.delete_message()
    except:
        pass

async def join_alliance(query, user_id, alliance_id):
    # محدودیت عضویت مجدد بعد از خروج
    if user_id in alliance_leave_turn:
        last_turn = alliance_leave_turn[user_id]
        if game_data['turn'] - last_turn < 1:
            await query.answer('شما به تازگی از یک اتحاد خارج شده‌اید و تا ۱ دور نمی‌توانید عضو اتحاد جدید شوید.', show_alert=True)
            return
    data = utils.alliances.get(alliance_id)
    if not data:
        await query.answer('اتحاد مورد نظر یافت نشد.', show_alert=True)
        return
    # محدودیت حداکثر اعضا
    if len(data['members']) >= 10:
        await query.answer('ظرفیت این اتحاد تکمیل است و نمی‌توانید عضو شوید.', show_alert=True)
        return
    # چک کردن اینکه آیا کاربر قبلاً در این اتحاد عضو است
    if user_id in data['members']:
        await query.answer('شما قبلاً در این اتحاد عضو هستید.', show_alert=True)
        return
    
    # چک کردن اینکه آیا کاربر در اتحاد دیگری عضو است
    if utils.user_alliances.get(user_id):
        await query.answer('شما هم‌اکنون عضو یک اتحاد هستید و نمی‌توانید عضو اتحاد دیگری شوید.', show_alert=True)
        return
    user = utils.users.get(user_id, {})
    if user.get('resources', {}).get('cash', 0) < data['entry_fee']:
        await query.answer('موجودی نقد شما برای عضویت کافی نیست.', show_alert=True)
        return
    # کم کردن پول و عضویت
    utils.users[user_id]['resources']['cash'] -= data['entry_fee']
    # واریز پول به رهبر اتحاد
    leader_id = data.get('leader')
    if leader_id and leader_id in utils.users:
        utils.users[leader_id]['resources']['cash'] = utils.users[leader_id]['resources'].get('cash', 0) + data['entry_fee']
    # اضافه کردن کاربر به لیست اعضا (فقط اگر قبلاً نباشد)
    if user_id not in data['members']:
        data['members'].append(user_id)
    utils.user_alliances[user_id] = alliance_id
    if user_id in alliance_leave_turn:
        del alliance_leave_turn[user_id]
    utils.save_alliances()
    utils.save_users()
    await query.answer('عضویت شما با موفقیت انجام شد!', show_alert=True)
    try:
        await query.edit_message_text('شما با موفقیت عضو این اتحاد شدید.')
    except Exception:
        await query.message.reply_text('شما با موفقیت عضو این اتحاد شدید.')

  # user_id: {'field': ..., 'alliance_id': ...}

# --- ویرایش توضیحات ---
async def edit_alliance_desc_start(query, user_id):
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await query.answer('شما در هیچ اتحادی نیستید!')
        return
    alliance = utils.alliances[alliance_id]
    if alliance.get('leader') != user_id:
        await query.answer('فقط رهبر اتحاد می‌تواند توضیحات را ویرایش کند!', show_alert=True)
        return
    pending_edit_alliance[user_id] = {'field': 'desc', 'alliance_id': alliance_id}
    await query.edit_message_text('لطفاً توضیحات جدید اتحاد را ارسال کنید (حداکثر ۴ خط):')

# --- ویرایش قوانین ---
async def edit_alliance_rules_start(query, user_id):
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await query.answer('شما در هیچ اتحادی نیستید!')
        return
    alliance = utils.alliances[alliance_id]
    if alliance.get('leader') != user_id:
        await query.answer('فقط رهبر اتحاد می‌تواند قوانین را ویرایش کند!', show_alert=True)
        return
    pending_edit_alliance[user_id] = {'field': 'rules', 'alliance_id': alliance_id}
    await query.edit_message_text('لطفاً قوانین جدید اتحاد را ارسال کنید (حداکثر ۸ خط):')

# --- ویرایش لوگو ---
async def edit_alliance_logo_start(query, user_id):
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await query.answer('شما در هیچ اتحادی نیستید!')
        return
    alliance = utils.alliances[alliance_id]
    if alliance.get('leader') != user_id:
        await query.answer('فقط رهبر اتحاد می‌تواند لوگو را ویرایش کند!', show_alert=True)
        return
    pending_edit_alliance[user_id] = {'field': 'logo', 'alliance_id': alliance_id}
    await query.edit_message_text('لطفاً عکس جدید لوگوی اتحاد را ارسال کنید:')

# --- ویرایش هزینه عضویت ---
async def edit_alliance_entry_fee_start(query, user_id):
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await query.answer('شما در هیچ اتحادی نیستید!')
        return
    alliance = utils.alliances[alliance_id]
    if alliance.get('leader') != user_id:
        await query.answer('فقط رهبر اتحاد می‌تواند هزینه عضویت را ویرایش کند!', show_alert=True)
        return
    pending_edit_alliance[user_id] = {'field': 'entry_fee', 'alliance_id': alliance_id}
    await query.edit_message_text('لطفاً هزینه جدید عضویت را به دلار وارد کنید:')

# --- هندلر دریافت پیام و ذخیره ویرایش ---
async def handle_edit_alliance(update, context):
    user_id = str(update.effective_user.id)
    if user_id not in pending_edit_alliance:
        return
    edit_info = pending_edit_alliance[user_id]
    alliance_id = edit_info['alliance_id']
    field = edit_info['field']
    alliance = utils.alliances.get(alliance_id)
    if not alliance or alliance.get('leader') != user_id:
        await update.message.reply_text('شما اجازه ویرایش ندارید.')
        del pending_edit_alliance[user_id]
        return
    if field == 'desc':
        desc = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
        if desc.count('\n') > 3:
            await update.message.reply_text('توضیحات نباید بیشتر از ۴ خط باشد. لطفاً دوباره ارسال کنید.')
            return
        alliance['desc'] = desc
        await update.message.reply_text('توضیحات اتحاد با موفقیت ویرایش شد.')
    elif field == 'rules':
        rules = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
        if rules.count('\n') > 7:
            await update.message.reply_text('قوانین نباید بیشتر از ۸ خط باشد. لطفاً دوباره ارسال کنید.')
            return
        alliance['rules'] = rules
        await update.message.reply_text('قوانین اتحاد با موفقیت ویرایش شد.')
    elif field == 'logo':
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            alliance['logo'] = file_id
            await update.message.reply_text('لوگوی اتحاد با موفقیت ویرایش شد.')
        else:
            await update.message.reply_text('لطفاً یک عکس ارسال کنید.')
            return
    elif field == 'entry_fee':
        try:
            entry_fee = int((update.message.text if hasattr(update.message, 'text') and update.message.text else '').replace(',', ''))
            if entry_fee < 0:
                raise ValueError
        except:
            await update.message.reply_text('عدد معتبر وارد کنید.')
            return
        alliance['entry_fee'] = entry_fee
        await update.message.reply_text('هزینه عضویت اتحاد با موفقیت ویرایش شد.')
    utils.save_alliances()
    del pending_edit_alliance[user_id]

# --- اضافه کردن هندلرها به button_handler ---
# ... existing code ...

# ... existing code ...

# --- اضافه کردن هندلر پیام به main_message_handler ---
# ... existing code ...

# ... existing code ...

# --- متغیر وضعیت انتخاب جانشین ---
  # user_id: alliance_id

# --- شروع انتخاب جانشین ---
async def set_alliance_deputy_start(query, user_id):
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await query.answer('شما در هیچ اتحادی نیستید!')
        return
    alliance = utils.alliances[alliance_id]
    if alliance.get('leader') != user_id:
        await query.answer('فقط رهبر اتحاد می‌تواند جانشین تعیین کند!', show_alert=True)
        return
    # لیست اعضا به جز رهبر
    members = [uid for uid in alliance['members'] if uid != user_id]
    if not members:
        await query.edit_message_text('هیچ عضوی برای تعیین جانشین وجود ندارد.')
        return
    keyboard = []
    for m in members:
        country = utils.users.get(m, {}).get('country', f'کاربر {m}')
        keyboard.append([InlineKeyboardButton(country, callback_data=f'set_deputy_{m}')])
    keyboard.append([InlineKeyboardButton('لغو ❌', callback_data='alliance_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('یک عضو را به عنوان جانشین انتخاب کنید:', reply_markup=reply_markup)
    pending_set_deputy[user_id] = alliance_id

# --- ثبت جانشین ---
async def set_alliance_deputy_confirm(query, user_id, deputy_id):
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id or alliance_id != pending_set_deputy.get(user_id):
        await query.answer('درخواست معتبر نیست!')
        return
    alliance = utils.alliances[alliance_id]
    if alliance.get('leader') != user_id:
        await query.answer('فقط رهبر اتحاد می‌تواند جانشین تعیین کند!', show_alert=True)
        return
    if deputy_id not in alliance['members'] or deputy_id == user_id:
        await query.answer('عضو انتخابی معتبر نیست!')
        return
    alliance['deputy'] = deputy_id
    utils.save_alliances()
    del pending_set_deputy[user_id]
    country = utils.users.get(deputy_id, {}).get('country', f'کاربر {deputy_id}')
    await query.edit_message_text(f'جانشین اتحاد با موفقیت انتخاب شد: {country}')
    # اطلاع‌رسانی به جانشین
    try:
        await query.bot.send_message(
            chat_id=int(deputy_id),
            text=f"👑 شما به عنوان جانشین اتحاد {alliance.get('name','')} منصوب شدید. در صورت غیبت رهبر، رهبری به شما می‌رسد."
        )
    except Exception:
        pass

# --- منطق انتقال رهبری هنگام خروج رهبر ---
# در بخش خروج از اتحاد (confirm_leave_alliance):
  
async def show_alliance_members(query):
    user_id = str(query.from_user.id)
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id or alliance_id not in utils.alliances:
        await query.edit_message_text('شما در هیچ اتحادی عضو نیستید.')
        return
    alliance = utils.alliances[alliance_id]
    leader_id = alliance.get('leader')
    deputy_id = alliance.get('deputy')
    
    # پاک کردن اعضای تکراری
    unique_members = list(dict.fromkeys(alliance['members']))
    alliance['members'] = unique_members
    
    text = '👥 <b>لیست اعضای اتحاد:</b>\n\n'
    for uid in alliance['members']:
        country = utils.users.get(uid, {}).get('country', f'کاربر {uid}')
        role = ''
        if uid == leader_id:
            role = ' <b>(رهبر)</b>'
        elif deputy_id and uid == deputy_id:
            role = ' <b>(جانشین)</b>'
        text += f'- {country}{role}\n'
    keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='alliance_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_alliance_kick_member(query, context):
    user_id = str(query.from_user.id)
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id or alliance_id not in utils.alliances:
        await query.answer('شما در هیچ اتحادی عضو نیستید!')
        return
    alliance = utils.alliances[alliance_id]
    if alliance.get('leader') != user_id:
        await query.answer('فقط رهبر اتحاد می‌تواند اعضا را اخراج کند!', show_alert=True)
        return
    # لیست اعضا به جز رهبر
    members = [uid for uid in alliance['members'] if uid != user_id]
    if not members:
        await query.edit_message_text('هیچ عضوی برای اخراج وجود ندارد.')
        return
    keyboard = []
    for m in members:
        country = utils.users.get(m, {}).get('country', f'کاربر {m}')
        keyboard.append([InlineKeyboardButton(country, callback_data=f'kick_member_{m}')])
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='alliance_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('یک عضو را برای اخراج انتخاب کنید:', reply_markup=reply_markup)

async def handle_kick_member_confirm(query, context, member_id):
    user_id = str(query.from_user.id)
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id or alliance_id not in utils.alliances:
        await query.answer('شما در هیچ اتحادی عضو نیستید!')
        return
    alliance = utils.alliances[alliance_id]
    if alliance.get('leader') != user_id:
        await query.answer('فقط رهبر اتحاد می‌تواند اعضا را اخراج کند!', show_alert=True)
        return
    if member_id not in alliance['members'] or member_id == user_id:
        await query.answer('عضو انتخابی معتبر نیست!')
        return
    alliance['members'].remove(member_id)
    if member_id in utils.user_alliances:
        del utils.user_alliances[member_id]
    utils.save_alliances()
    try:
        await context.bot.send_message(
            chat_id=int(member_id),
            text=f'شما توسط رهبر از اتحاد {alliance["name"]} اخراج شدید.'
        )
    except Exception as e:
        print(f'خطا در ارسال پیام اخراج به کاربر {member_id}: {e}')
    await query.edit_message_text('عضو با موفقیت اخراج شد.')

# در ابتدای فایل اضافه کن
      # user_id: {'request_id': ..., 'alliance_id': ...}

# سیستم کمک اتحاد - شبیه تجارت
alliance_trades = {}  # {trade_id: {'from_id': user_id, 'to_id': user_id, 'resource': resource, 'amount': amount, 'status': 'sending', 'start_time': timestamp}}

async def show_alliance_help_menu(query):
    user_id = str(query.from_user.id)
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await query.edit_message_text('شما در هیچ اتحادی عضو نیستید.')
        return
    
    keyboard = [
        [InlineKeyboardButton('🤲 درخواست کمک', callback_data='alliance_help_request')],
        [InlineKeyboardButton('💝 ارسال کمک', callback_data='alliance_help_give')],
        [InlineKeyboardButton('📦 محموله‌های در حال ارسال', callback_data='alliance_trades_list')],
        [InlineKeyboardButton('بازگشت ⬅️', callback_data='alliance_menu')]
    ]
    await query.edit_message_text('🤝 منوی کمک اتحاد\n\nدر اینجا می‌توانید از اعضای اتحاد کمک درخواست کنید یا به آنها کمک کنید.', reply_markup=InlineKeyboardMarkup(keyboard))

async def show_alliance_help_request_menu(query, user_id):
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await query.edit_message_text('شما در هیچ اتحادی عضو نیستید.')
        return
    resource_names = {
        'gold': 'طلا', 'steel': 'فولاد', 'iron': 'آهن', 'copper': 'مس', 'diamond': 'الماس', 'uranium': 'اورانیوم',
        'wheat': 'گندم', 'rice': 'برنج', 'fruits': 'میوه', 'oil': 'نفت', 'gas': 'گاز', 'electronics': 'الکترونیک',
        'pride_cars': 'پراید', 'benz_cars': 'بنز', 'electricity': 'برق',
        'uranium_ore': 'سنگ اورانیوم', 'centrifuge': 'سانتریفیوژ', 'yellowcake': 'کیک زرد', 'space_parts': 'قطعات فضایی'
    }
    keys = list(resource_names.keys())
    keyboard = []
    for i in range(0, len(keys), 2):
        row = []
        for j in range(2):
            if i + j < len(keys):
                res = keys[i + j]
                name = resource_names[res]
                row.append(InlineKeyboardButton(name, callback_data=f'help_request_resource_{res}'))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='alliance_help')])
    await query.edit_message_text('کدام منبع را می‌خواهید درخواست کنید؟', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_help_request_resource(query, user_id, resource):
    """هندل کردن انتخاب منبع برای درخواست کمک"""
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await query.answer('شما در هیچ اتحادی عضو نیستید.')
        return
    
    pending_help_request[user_id] = {'resource': resource}
    await query.edit_message_text(f'چه تعداد {resource} نیاز دارید؟ عدد را وارد کنید:')

async def handle_help_request_amount(update, context):
    user_id = str(update.effective_user.id)
    try:
        amount = int((update.message.text if hasattr(update.message, 'text') and update.message.text else '').replace(',', ''))
        if amount <= 0:
            raise ValueError
    except:
        await update.message.reply_text('عدد معتبر وارد کنید.')
        return
    
    if user_id not in pending_help_request:
        await update.message.reply_text('درخواست نامعتبر است.')
        return
        
    resource = pending_help_request[user_id]['resource']
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await update.message.reply_text('شما در هیچ اتحادی عضو نیستید.')
        del pending_help_request[user_id]
        return
    
    # نمایش درخواست به اعضای اتحاد
    alliance = utils.alliances.get(alliance_id, {})
    request_text = f"🤲 <b>درخواست کمک جدید</b>\n\n"
    request_text += f"کشور: {utils.users.get(user_id, {}).get('country', 'نامشخص')}\n"
    request_text += f"منبع: {resource}\n"
    request_text += f"مقدار: {amount:,}\n\n"
    request_text += "اعضای اتحاد می‌توانند به این درخواست پاسخ دهند."
    
    # ارسال به همه اعضای اتحاد
    for member_id in alliance.get('members', []):
        if member_id != user_id:
            try:
                keyboard = [[InlineKeyboardButton('💝 ارسال کمک', callback_data=f'help_give_{user_id}_{resource}_{amount}')]]
                await context.bot.send_message(
                    chat_id=int(member_id),
                    text=request_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"خطا در ارسال درخواست کمک به {member_id}: {e}")
    
    await update.message.reply_text('درخواست کمک شما به اعضای اتحاد ارسال شد.')
    del pending_help_request[user_id]

async def show_alliance_help_give_menu(query, user_id):
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await query.edit_message_text('شما در هیچ اتحادی عضو نیستید.')
        return
    
    # نمایش درخواست‌های کمک موجود
    alliance = utils.alliances.get(alliance_id, {})
    text = "🤲 <b>درخواست‌های کمک موجود:</b>\n\n"
    
    # اینجا می‌توانیم درخواست‌های اخیر را نمایش دهیم
    # فعلاً فقط پیام کلی می‌فرستیم
    text += "برای ارسال کمک، از دکمه‌های موجود در پیام‌های درخواست کمک استفاده کنید."
    
    keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='alliance_help')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def handle_help_give_confirm(query, user_id, target_id, resource, amount, context):
    """هندل کردن تایید ارسال کمک"""
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await query.answer('شما در هیچ اتحادی عضو نیستید.')
        return
    
    # چک کردن موجودی
    user = utils.users.get(user_id, {})
    if user.get('resources', {}).get(resource, 0) < amount:
        await query.answer('موجودی شما کافی نیست!', show_alert=True)
        return
    
    # ایجاد معامله
    trade_id = str(uuid4())
    alliance_trades[trade_id] = {
        'from_id': user_id,
        'to_id': target_id,
        'resource': resource,
        'amount': amount,
        'status': 'sending',
        'start_time': datetime.now().isoformat(),
        'alliance_id': alliance_id
    }
    
    # کم کردن منابع از ارسال‌کننده
    user['resources'][resource] -= amount
    save_users()
    
    # پیام به ارسال‌کننده
    await query.edit_message_text(f'کمک شما در حال ارسال است و پس از ۲۰ دقیقه به مقصد می‌رسد.')
    
    # پیام به دریافت‌کننده
    try:
        await context.bot.send_message(
            chat_id=int(target_id),
            text=f'یک عضو اتحاد ({utils.users.get(user_id, {}).get("country", "")}) در حال ارسال {amount:,} {resource} به شماست. محموله تا ۲۰ دقیقه دیگر می‌رسد.'
        )
    except Exception:
        pass
    
    # پیام به کانال اخبار
    try:
        await context.bot.send_message(
            chat_id=NEWS_CHANNEL_ID,
            text=f'🤲 محموله کمک از کشور {utils.users.get(user_id, {}).get("country", "")} به کشور {utils.users.get(target_id, {}).get("country", "")} در حال ارسال است.'
        )
    except Exception:
        pass
    
    # زمان‌بندی تحویل
    asyncio.create_task(finalize_alliance_trade_delivery(trade_id, context))

async def show_alliance_trades_list(query):
    """نمایش لیست محموله‌های در حال ارسال"""
    user_id = str(query.from_user.id)
    alliance_id = utils.user_alliances.get(user_id)
    if not alliance_id:
        await query.edit_message_text('شما در هیچ اتحادی عضو نیستید.')
        return
    
    # پیدا کردن محموله‌های مربوط به این اتحاد
    user_trades = []
    for trade_id, trade in alliance_trades.items():
        if trade.get('alliance_id') == alliance_id and trade['status'] == 'sending':
            if trade['from_id'] == user_id or trade['to_id'] == user_id:
                user_trades.append((trade_id, trade))
    
    if not user_trades:
        await query.edit_message_text('هیچ محموله‌ای در حال ارسال نیست.')
        return
    
    text = "📦 <b>محموله‌های در حال ارسال:</b>\n\n"
    for trade_id, trade in user_trades:
        from_country = utils.users.get(trade['from_id'], {}).get('country', 'نامشخص')
        to_country = utils.users.get(trade['to_id'], {}).get('country', 'نامشخص')
        text += f"▫️ {from_country} → {to_country}\n"
        text += f"   {trade['amount']:,} {trade['resource']}\n\n"
    
    keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='alliance_help')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def finalize_alliance_trade_delivery(trade_id, context):
    """تحویل محموله کمک اتحاد"""
    await asyncio.sleep(20 * 60)  # 20 دقیقه
    
    if trade_id not in alliance_trades:
        return
    
    trade = alliance_trades[trade_id]
    if trade['status'] != 'sending':
        return
    
    # اضافه کردن منابع به دریافت‌کننده
    receiver = utils.users.get(trade['to_id'], {})
    if receiver:
        receiver['resources'][trade['resource']] = receiver['resources'].get(trade['resource'], 0) + trade['amount']
        save_users()
        
        # پیام به دریافت‌کننده
        try:
            await context.bot.send_message(
                chat_id=int(trade['to_id']),
                text=f'کمک {trade["amount"]:,} {trade["resource"]} به حساب شما واریز شد!'
            )
        except Exception:
            pass
        
        # پیام به ارسال‌کننده
        try:
            await context.bot.send_message(
                chat_id=int(trade['from_id']),
                text=f'کمک شما به {utils.users.get(trade["to_id"], {}).get("country", "")} با موفقیت تحویل شد.'
            )
        except Exception:
            pass
        
        # پیام به کانال اخبار
        try:
            await context.bot.send_message(
                chat_id=NEWS_CHANNEL_ID,
                text=f'🤲 محموله کمک از کشور {utils.users.get(trade["from_id"], {}).get("country", "")} به کشور {utils.users.get(trade["to_id"], {}).get("country", "")} با موفقیت تحویل شد.'
            )
        except Exception:
            pass
    
    trade['status'] = 'completed'

# تابع امن برای ویرایش پیام‌ها
async def safe_edit_message(query, text, reply_markup=None, parse_mode=None):
    """ویرایش امن پیام با مدیریت خطای Message is not modified"""
    try:
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception as e:
        if "Message is not modified" in str(e):
            # پیام تغییر نکرده، فقط پاسخ کوتاه بده
            await query.answer("✅")
        else:
            # خطای دیگر، دوباره تلاش کن
            try:
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            except Exception as e2:
                print(f"خطا در ویرایش پیام: {e2}")

# سیستم روابط کشورها
async def show_country_relations_menu(query):
    user_id = str(query.from_user.id)
    user_country = utils.users.get(user_id, {}).get('country', '')
    user_relations = utils.country_relations.get(user_id, {})
    
    # استفاده از وزیر خارجه انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'foreign' in selected_officials:
        foreign_minister = selected_officials['foreign']
    else:
        # اگر وزیر خارجه انتخاب نشده، از اسامی پیش‌فرض استفاده کن
        foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
    
    # پیام خوشامدگویی
    text = f"🌍 <b>خوش آمدید!</b>\n\n"
    text += f"🤝 من {foreign_minister['name']}، {foreign_minister['title']} شما هستم.\n"
    text += f"🏛️ <b>روابط کشور {user_country}</b>\n\n"
    
    if not user_relations:
        text += "شما هنوز با هیچ کشوری رابطه برقرار نکرده‌اید.\n"
    else:
        text += "<b>روابط فعلی:</b>\n"
        for target_id, relation_level in user_relations.items():
            target_country = utils.users.get(target_id, {}).get('country', f'کاربر {target_id}')
            relation_text = get_relation_text(relation_level)
            text += f"▫️ {target_country}: {relation_text}\n"
    
    # تحلیل هوشمند روابط
    from analysis import generate_relations_analysis
    analysis = generate_relations_analysis(user_id)
    
    text += f"\n<b>پیشنهاد {foreign_minister['title']} {foreign_minister['name']}:</b>\n<blockquote>{analysis}</blockquote>"
    
    keyboard = [
        [InlineKeyboardButton('مشاهده روابط', callback_data='view_relations')],
        [InlineKeyboardButton('بهبود روابط', callback_data='improve_relations')],
        [InlineKeyboardButton('تخریب روابط', callback_data='damage_relations')],
        [InlineKeyboardButton('سفارتخانه 🏛️', callback_data='embassy_menu')],
        [InlineKeyboardButton('💡 پیشنهاد وزیر خارجه', callback_data='foreign_minister_suggestions')],
        [InlineKeyboardButton('بازگشت ⬅️', callback_data='diplomacy')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await safe_edit_message(query, text, reply_markup=reply_markup, parse_mode='HTML')


async def show_view_relations(query):
    user_id = str(query.from_user.id)
    user_country = utils.users.get(user_id, {}).get('country', '')
    user_relations = utils.country_relations.get(user_id, {})
    
    text = f"🌍 <b>روابط کشور {user_country}</b>\n\n"
    
    if not user_relations:
        text += "شما هنوز با هیچ کشوری رابطه برقرار نکرده‌اید."
    else:
        # مرتب کردن بر اساس سطح رابطه
        sorted_relations = sorted(user_relations.items(), key=lambda x: x[1], reverse=True)
        
        for target_id, relation_level in sorted_relations:
            target_country = utils.users.get(target_id, {}).get('country', f'کاربر {target_id}')
            relation_text = get_relation_text(relation_level)
            emoji = "🟢" if relation_level > 0 else "🔴" if relation_level < 0 else "🟡"
            text += f"{emoji} <b>{target_country}</b>: {relation_text} ({relation_level:+.1f})\n"
    
    keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='country_relations')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await safe_edit_message(query, text, reply_markup=reply_markup, parse_mode='HTML')

async def show_improve_relations_menu(query):
    user_id = str(query.from_user.id)
    # اطمینان از لود بودن کاربران و همسان‌سازی وضعیت
    try:
        utils.load_users()
        utils.reconcile_world_state()
    except Exception:
        pass
    user_country = utils.users.get(user_id, {}).get('current_country_name', utils.users.get(user_id, {}).get('country', ''))
    
    # لیست کشورهای فعال به جز خود کاربر (مستقیماً از users)
    available_countries = []
    total_users = 0
    activated_users = 0
    try:
        from utils import is_user_banned
    except Exception:
        def is_user_banned(_):
            return False
    
    # استخراج مستقیم از users: فقط کشورهایی که واقعاً فعال شده‌اند در فصل جاری
    for uid, user_data in utils.users.items():
            total_users += 1
            profile = user_data.get('profile', {})
            # فعال بودن فقط بر اساس activated
            is_active = user_data.get('activated', False)
            # داشتن کشور فقط اگر هم نام کشور هست و هم profile.has_country True باشد
            cname = user_data.get('current_country_name', user_data.get('country', ''))
            has_country = profile.get('has_country', False) and bool(cname)
            if is_active and has_country and not is_user_banned(uid):
                activated_users += 1
                if uid != user_id:
                    available_countries.append((uid, cname))
    
    print(f"[DEBUG] Total users: {total_users}, Activated users: {activated_users}, Available for relations: {len(available_countries)}")
    current_user = utils.users.get(user_id, {})
    current_profile = current_user.get('profile', {})
    current_activated = current_user.get('activated', False) or current_profile.get('is_registered', False) or current_profile.get('guest', False)
    print(f"[DEBUG] Current user_id: {user_id}, Current user activated: {current_activated}")
    print(f"[DEBUG] Current user profile: {current_profile}")
    
    if not available_countries:
        # آمار کمکی برای عیب‌یابی
        taken_countries = [c for c in getattr(utils, 'countries', []) if isinstance(c, dict) and c.get('taken')]
        debug_text = f"هیچ کشور فعال دیگری برای بهبود روابط وجود ندارد.\n\n"
        debug_text += f"📊 اطلاعات دیباگ:\n"
        debug_text += f"• کل کاربران: {total_users}\n"
        debug_text += f"• کاربران فعال: {activated_users}\n"
        debug_text += f"• کاربران قابل دسترس: {len(available_countries)}\n"
        debug_text += f"• شما فعال هستید: {current_activated}\n"
        debug_text += f"• کشورهای اشغال‌شده: {len(taken_countries)}\n"
        debug_text += f"• پروفایل شما: {current_profile}"
        await query.edit_message_text(debug_text)
        return
    
    text = f"🤝 <b>بهبود روابط کشور {user_country}</b>\n\n"
    text += f"📊 {len(available_countries)} کشور فعال برای انتخاب:\n\n"
    
    keyboard = []
    for i in range(0, len(available_countries), 2):
        row = []
        for j in range(2):
            if i + j < len(available_countries):
                uid, country_name = available_countries[i + j]
                current_relation = utils.country_relations.get(user_id, {}).get(uid, 0)
                relation_text = get_relation_text(current_relation)
                btn_text = f"{country_name}\n{relation_text}"
                row.append(InlineKeyboardButton(btn_text, callback_data=f'improve_relation_{uid}'))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='country_relations')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await safe_edit_message(query, text, reply_markup=reply_markup, parse_mode='HTML')

async def show_damage_relations_menu(query):
    user_id = str(query.from_user.id)
    # اطمینان از لود بودن کاربران و همسان‌سازی وضعیت
    try:
        utils.load_users()
        utils.reconcile_world_state()
    except Exception:
        pass
    user_country = utils.users.get(user_id, {}).get('current_country_name', utils.users.get(user_id, {}).get('country', ''))
    
    # لیست کشورهای فعال به جز خود کاربر (مستقیماً از users)
    available_countries = []
    total_users = 0
    activated_users = 0
    try:
        from utils import is_user_banned
    except Exception:
        def is_user_banned(_):
            return False
    
    # استخراج مستقیم از users: فقط کشورهایی که واقعاً فعال شده‌اند در فصل جاری
    for uid, user_data in utils.users.items():
            total_users += 1
            profile = user_data.get('profile', {})
            is_active = user_data.get('activated', False)
            cname = user_data.get('current_country_name', user_data.get('country', ''))
            has_country = profile.get('has_country', False) and bool(cname)
            if is_active and has_country and not is_user_banned(uid):
                activated_users += 1
                if uid != user_id:
                    available_countries.append((uid, cname))
    
    print(f"[DEBUG] Total users: {total_users}, Activated users: {activated_users}, Available for damage: {len(available_countries)}")
    current_user = utils.users.get(user_id, {})
    current_profile = current_user.get('profile', {})
    current_activated = current_user.get('activated', False) or current_profile.get('is_registered', False) or current_profile.get('guest', False)
    print(f"[DEBUG] Current user_id: {user_id}, Current user activated: {current_activated}")
    print(f"[DEBUG] Current user profile: {current_profile}")
    
    if not available_countries:
        taken_countries = [c for c in getattr(utils, 'countries', []) if isinstance(c, dict) and c.get('taken')]
        debug_text = f"هیچ کشور فعال دیگری برای تخریب روابط وجود ندارد.\n\n"
        debug_text += f"📊 اطلاعات دیباگ:\n"
        debug_text += f"• کل کاربران: {total_users}\n"
        debug_text += f"• کاربران فعال: {activated_users}\n"
        debug_text += f"• کاربران قابل دسترس: {len(available_countries)}\n"
        debug_text += f"• شما فعال هستید: {current_activated}\n"
        debug_text += f"• کشورهای اشغال‌شده: {len(taken_countries)}\n"
        debug_text += f"• پروفایل شما: {current_profile}"
        await query.edit_message_text(debug_text)
        return
    
    text = f"💥 <b>تخریب روابط کشور {user_country}</b>\n\n"
    text += f"📊 {len(available_countries)} کشور فعال برای انتخاب:\n\n"
    
    keyboard = []
    for i in range(0, len(available_countries), 2):
        row = []
        for j in range(2):
            if i + j < len(available_countries):
                uid, country_name = available_countries[i + j]
                current_relation = utils.country_relations.get(user_id, {}).get(uid, 0)
                relation_text = get_relation_text(current_relation)
                btn_text = f"{country_name}\n{relation_text}"
                row.append(InlineKeyboardButton(btn_text, callback_data=f'damage_relation_{uid}'))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='country_relations')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_relation_action(query, user_id, target_id, action_type, context):
    user_country = utils.users.get(user_id, {}).get('country', '')
    target_country = utils.users.get(target_id, {}).get('country', '')
    global relation_improvement_requests
    # دریافت روابط فعلی (دوطرفه)
    if user_id not in utils.country_relations:
        utils.country_relations[user_id] = {}
    if target_id not in utils.country_relations:
        utils.country_relations[target_id] = {}
    if target_id not in utils.country_relations[user_id]:
        utils.country_relations[user_id][target_id] = 0
    if user_id not in utils.country_relations[target_id]:
        utils.country_relations[target_id][user_id] = 0
    current_relation_user = utils.country_relations[user_id][target_id]
    current_relation_target = utils.country_relations[target_id][user_id]
    if action_type == 'improve':
        # محدودیت هر دور: فقط یکبار در هر دور
        turn = game_data['turn']
        if user_id not in relation_improvement_requests:
            relation_improvement_requests[user_id] = {}
        if relation_improvement_requests[user_id].get(target_id) == turn:
            await query.edit_message_text('شما در این دور قبلاً به این کشور درخواست بهبود روابط داده‌اید.')
            return
        # ارسال درخواست بهبود روابط به طرف مقابل
        relation_improvement_requests[user_id][target_id] = turn
        keyboard = [
            [InlineKeyboardButton('قبول ✅', callback_data=f'accept_improve_{user_id}')],
            [InlineKeyboardButton('رد ❌', callback_data=f'decline_improve_{user_id}')]
        ]
        print(f"در حال ارسال درخواست بهبود روابط به {target_id} (کشور: {target_country})")
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=f'کشور {user_country} درخواست بهبود روابط با کشور شما را دارد. آیا قبول می‌کنید؟',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            print(f"پیام درخواست بهبود روابط با موفقیت به {target_id} ارسال شد")
        except Exception as e:
            print(f"خطا در ارسال پیام درخواست بهبود روابط به {target_id}: {e}")
            print(f"نوع خطا: {type(e).__name__}")
        await query.edit_message_text('درخواست بهبود روابط ارسال شد و منتظر تایید طرف مقابل است.')
        return
    elif action_type == 'accept_improve':
        # اعمال تأثیرات حکومت بر روابط دیپلماتیک
        diplomatic_bonus_user = utils.calculate_government_diplomatic_bonus(user_id)
        diplomatic_bonus_target = utils.calculate_government_diplomatic_bonus(target_id)
        
        # محاسبه بهبود روابط با در نظر گرفتن بونوس حکومت
        base_improvement = 5
        user_improvement = base_improvement + (diplomatic_bonus_user / 20)  # هر 20% بونوس = +1 واحد
        target_improvement = base_improvement + (diplomatic_bonus_target / 20)
        
        # افزایش روابط دوطرفه
        if target_id not in utils.country_relations:
            utils.country_relations[target_id] = {}
        if user_id not in utils.country_relations:
            utils.country_relations[user_id] = {}
        
        # در این سناریو user_id تاییدکننده است و target_id درخواست‌دهنده اولیه
        requester_id = target_id
        approver_id = user_id
        current_user_relation = utils.country_relations[approver_id].get(requester_id, 0)
        current_target_relation = utils.country_relations[requester_id].get(approver_id, 0)
        
        utils.country_relations[approver_id][requester_id] = min(100, current_user_relation + user_improvement)
        utils.country_relations[requester_id][approver_id] = min(100, current_target_relation + target_improvement)
        utils.save_country_relations()  # ذخیره روابط
        
        # بررسی جایزه وزیر خارجه برای هر دو طرف
        from utils import check_foreign_minister_reward
        check_foreign_minister_reward(user_id, target_id)
        check_foreign_minister_reward(target_id, user_id)
        
        new_user_relation = utils.country_relations[approver_id][requester_id]
        new_target_relation = utils.country_relations[requester_id][approver_id]
        text = (
            f'✅ بهبود روابط بین {utils.users.get(approver_id, {}).get("country", "")} و '
            f'{utils.users.get(requester_id, {}).get("country", "")} با موفقیت انجام شد!\n'
            f'🔢 وضعیت فعلی روابط: شما→او: {new_user_relation:+.1f} | او→شما: {new_target_relation:+.1f}'
        )
        # اطلاع به درخواست‌دهنده (فرستنده اولیه)
        try:
            await context.bot.send_message(
                chat_id=int(requester_id),
                text=(
                    '✅ درخواست بهبود روابط شما پذیرفته شد.\n'
                    f'🔢 وضعیت فعلی روابط با {utils.users.get(approver_id, {}).get("country", "")}: '
                    f'{new_target_relation:+.1f}'
                )
            )
        except Exception as e:
            print(f"[relations] notify requester accept failed: {e}")
        # اطلاع به تاییدکننده
        try:
            await context.bot.send_message(
                chat_id=int(approver_id),
                text=(
                    '✅ شما درخواست بهبود روابط را پذیرفتید.\n'
                    f'🔢 وضعیت فعلی روابط با {utils.users.get(requester_id, {}).get("country", "")}: '
                    f'{new_user_relation:+.1f}'
                )
            )
        except Exception as e:
            print(f"[relations] notify approver accept failed: {e}")
        await query.edit_message_text(text)
        return
    elif action_type == 'decline_improve':
        # اطلاع‌رسانی رد شدن درخواست به هر دو طرف + نمایش مقدار فعلی
        current_user_relation = utils.country_relations[user_id].get(target_id, 0)
        current_target_relation = utils.country_relations[target_id].get(user_id, 0)
        try:
            await context.bot.send_message(
                chat_id=int(target_id),
                text=(
                    f'❌ کشور {utils.users.get(user_id, {}).get("country", "")} درخواست بهبود روابط شما را رد کرد.\n'
                    f'🔢 وضعیت فعلی روابط شما با او: {current_target_relation:+.1f}'
                )
            )
        except Exception as e:
            print(f"[relations] notify requester decline failed: {e}")
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=(
                    f'❌ شما درخواست بهبود روابط کشور {utils.users.get(target_id, {}).get("country", "")} را رد کردید.\n'
                    f'🔢 وضعیت فعلی روابط شما با او: {current_user_relation:+.1f}'
                )
            )
        except Exception as e:
            print(f"[relations] notify approver decline failed: {e}")
        await query.edit_message_text('درخواست بهبود روابط رد شد.')
        return
    # ... منطق قبلی تخریب روابط ...
    if action_type == 'damage':
        # تخریب روابط: -15 تا -35 (دوطرفه)
        damage = random.randint(15, 35)
        new_relation_user = max(-100, current_relation_user - damage)
        new_relation_target = max(-100, current_relation_target - damage)
        utils.country_relations[user_id][target_id] = new_relation_user
        utils.country_relations[target_id][user_id] = new_relation_target
        utils.save_country_relations()  # ذخیره روابط
        
        # استفاده از وزیر خارجه انتخاب شده
        selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
        if 'foreign' in selected_officials:
            foreign_minister = selected_officials['foreign']
        else:
            foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
        
        # پیام اصلی با حضور وزیر خارجه
        text = f"💥 <b>تخریب روابط</b>\n\n"
        text += f"🤝 {foreign_minister['name']}، {foreign_minister['title']} شما گزارش می‌دهد:\n\n"
        text += f"روابط {user_country} با {target_country} تخریب شد!\n"
        text += f"تغییر: {current_relation_user:+.1f} → {new_relation_user:+.1f} (-{damage})\n\n"
        text += f"وضعیت جدید: {get_relation_text(new_relation_user)}"
        
        # پیام هشدار وزیر خارجه
        warning_messages = [
            f"⚠️ {foreign_minister['name']}: این اقدام می‌تواند عواقب جدی برای روابط دیپلماتیک ما داشته باشد.",
            f"🚨 {foreign_minister['name']}: تخریب روابط می‌تواند منجر به تنش‌های بیشتر شود.",
            f"💬 {foreign_minister['name']}: پیشنهاد می‌کنم در آینده از روش‌های دیپلماتیک‌تر استفاده کنیم.",
            f"📢 {foreign_minister['name']}: این تصمیم بر روابط تجاری و سیاسی ما تأثیر خواهد گذاشت."
        ]
        warning = random.choice(warning_messages)
        text += f"\n\n<blockquote>{warning}</blockquote>"
        
        if utils.country_relations[user_id][target_id] <= -81:
            # بررسی پکیج "دوری و دوستی" کشور هدف
            target_diplomacy = utils.users.get(target_id, {}).get('diplomacy', {})
            target_forced_peace = target_diplomacy.get('forced_peace_turns', 0)
            
            if target_forced_peace > 0:
                # کشور هدف تحت صلح اجباری است، جنگ اعلان نمی‌شود
                peace_warning = (
                    f"🛡️ {foreign_minister['name']}: کشور {target_country} تحت صلح اجباری است.\n"
                    f"⏰ {target_forced_peace} نوبت باقی‌مانده\n\n"
                    f"به دلیل فعال بودن پکیج «دوری و دوستی»، جنگ خودکار اعلان نشد."
                )
                text += f"\n\n<blockquote>{peace_warning}</blockquote>"
            else:
            # ثبت جنگ خودکار در ساختار جدید
                wid = f"{user_country}->{target_country}"
                utils.war_declarations[wid] = {
                    'attacker': user_country,
                    'defender': target_country,
                    'type': 'auto_war',
                    'status': 'active',
                    'turn_declared': game_data.get('turn', 1)
            }
            
            # پیام هشدار جنگ از وزیر خارجه
            war_warning = f"🚨 {foreign_minister['name']}: هشدار! روابط به حد بحرانی رسیده و احتمال اعلان جنگ وجود دارد!"
            text += f"\n\n<blockquote>{war_warning}</blockquote>"
            
            # پیام به کانال اخبار
            war_photo_id = "https://t.me/TextEmpire_IR/47"  # file_id عکس اعلان جنگ
            news_text = f"🚨 <b>اعلان جنگ خودکار!</b>\n\nبه دلیل تخریب روابط، جنگ بین کشور {user_country} و {target_country} به طور خودکار اعلان شد!"
            try:
                await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=war_photo_id, caption=news_text, parse_mode='HTML')
            except Exception:
                pass
            
            # پیام به هر دو طرف
            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=f"🚨 {foreign_minister['name']}: به دلیل تخریب روابط، جنگ با {target_country} به طور خودکار اعلام شد!"
                )
            except Exception:
                pass
            try:
                await context.bot.send_message(
                chat_id=int(target_id),
                    text=f"🚨 به دلیل تخریب روابط، جنگ با {user_country} به طور خودکار اعلام شد!"
            )
            except Exception:
                pass
            
            # ذخیره اعلان‌های جنگ
            from utils import save_war_declarations
            save_war_declarations()
        
        # پیام به طرف مقابل با حضور وزیر خارجه
        try:
            target_selected_officials = utils.users.get(target_id, {}).get('selected_officials', {})
            if 'foreign' in target_selected_officials:
                target_foreign_minister = target_selected_officials['foreign']
            else:
                target_foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
            
            target_warning_messages = [
                f"💥 {target_foreign_minister['name']}: کشور {user_country} روابط خود با ما را تخریب کرده است.",
                f"⚠️ {target_foreign_minister['name']}: این اقدام خصمانه نیاز به پاسخ مناسب دارد.",
                f"🚨 {target_foreign_minister['name']}: روابط دیپلماتیک ما با {user_country} به شدت آسیب دیده است."
            ]
            target_warning = random.choice(target_warning_messages)
            
            await query.bot.send_message(
                chat_id=int(target_id),
                text=f"{target_warning}\n🔢 وضعیت جدید روابط: {new_relation_target:+.1f} ({get_relation_text(new_relation_target)})"
            )
        except Exception:
            pass

        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='country_relations')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return

        # اعلان جنگ خودکار اگر روابط به -81 یا کمتر رسید

    # ... existing code ...

# --- اضافه کردن هندلر تایید درخواست بهبود روابط در button_handler ---
# ... existing code ...

# ... existing code ...

# متغیرهای سیستم روابط کشورها
  # {user_id: [target_id]} - سفارتخانه‌های موجود

# سیستم سفارتخانه
async def show_embassy_menu(query):
    global users
    user_id = str(query.from_user.id)
    user_country = utils.users.get(user_id, {}).get('country', '')
    user_relations = utils.country_relations.get(user_id, {})
    user_embassies = utils.embassies.get(user_id, [])
    existing_embassies = []
    for embassy_id in user_embassies:
        embassy_country = utils.users.get(embassy_id, {}).get('country', '')
        existing_embassies.append((embassy_id, embassy_country))
    text = f"🏛️ <b>سفارتخانه کشور {user_country}</b>\n\n"
    if existing_embassies:
        text += "<b>سفارتخانه‌های موجود:</b>\n"
        for embassy_id, embassy_country in existing_embassies:
            text += f"🏛️ {embassy_country}\n"
        text += "\n"
    # کشورهای واجد شرایط (روابط > ۲۰ و هنوز سفارتخانه ندارند و در تاریخچه نیستند)
    eligible_countries = []
    for target_id, relation_level in user_relations.items():
        # چک کردن اینکه آیا در تاریخچه سفارتخانه وجود دارد
        in_history = 'embassy_history' in utils.users[user_id] and target_id in utils.users[user_id]['embassy_history']
        if relation_level > 20 and target_id not in user_embassies and target_id in users and not in_history:
            target_country = utils.users.get(target_id, {}).get('country', '')
            eligible_countries.append((target_id, target_country, relation_level))
    if eligible_countries:
        text += "<b>کشورهای واجد شرایط برای سفارتخانه (روابط > ۲۰):</b>\n"
    else:
        text += "هیچ کشوری با روابط بالای ۲۰ برای ساخت سفارتخانه وجود ندارد."
    # دکمه‌ها
    keyboard = []
    for i in range(0, len(eligible_countries), 2):
        row = []
        for j in range(2):
            if i + j < len(eligible_countries):
                target_id, target_country, relation_level = eligible_countries[i + j]
                btn_text = f"{target_country} (روابط: {relation_level:+.1f})"
                row.append(InlineKeyboardButton(btn_text, callback_data=f'request_embassy_{target_id}'))
        if row:
            keyboard.append(row)
    # دکمه‌های جدید
    keyboard.append([InlineKeyboardButton('بستن سفارتخانه', callback_data='close_embassy_menu')])
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='country_relations')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# --- منوی بستن سفارتخانه ---
async def show_close_embassy_menu(query):
    user_id = str(query.from_user.id)
    user_embassies = utils.embassies.get(user_id, [])
    if not user_embassies:
        await query.edit_message_text('شما هیچ سفارتخانه فعالی ندارید.')
        return
    text = 'برای بستن سفارتخانه، کشور مورد نظر را انتخاب کنید:'
    keyboard = []
    for eid in user_embassies:
        country_name = utils.users.get(eid, {}).get('country', eid)
        keyboard.append([InlineKeyboardButton(country_name, callback_data=f'close_embassy_{eid}')])
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='embassy_menu')])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# --- منوی باز کردن سفارتخانه ---
async def show_reopen_embassy_menu(query):
    user_id = str(query.from_user.id)
    closed_embassies = []
    # سفارتخانه‌هایی که قبلاً وجود داشته و الان بسته شده‌اند (در روابط منفی یا حذف شده)
    for uid in users:
        if uid == user_id:
            continue
        # اگر قبلاً سفارتخانه بوده و الان نیست
        if 'embassy_history' in utils.users[user_id] and uid in utils.users[user_id]['embassy_history'] and uid not in utils.embassies.get(user_id, []):
            closed_embassies.append(uid)
    if not closed_embassies:
        await query.edit_message_text('هیچ سفارتخانه بسته‌ای برای باز کردن وجود ندارد.')
        return
    text = 'برای باز کردن سفارتخانه، کشور مورد نظر را انتخاب کنید:'
    keyboard = []
    for eid in closed_embassies:
        country_name = utils.users.get(eid, {}).get('country', eid)
        keyboard.append([InlineKeyboardButton(country_name, callback_data=f'reopen_embassy_request_{eid}')])
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='embassy_menu')])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# --- بستن سفارتخانه ---
async def handle_close_embassy(query, user_id, target_id, context):
    if user_id not in utils.embassies or target_id not in utils.embassies[user_id]:
        await query.edit_message_text('سفارتخانه‌ای با این کشور ندارید.')
        return
    utils.embassies[user_id].remove(target_id)
    if target_id in utils.embassies and user_id in utils.embassies[target_id]:
        utils.embassies[target_id].remove(user_id)
    # ثبت در تاریخچه
    if 'embassy_history' not in utils.users[user_id]:
        utils.users[user_id]['embassy_history'] = set()
    utils.users[user_id]['embassy_history'].add(target_id)
    if 'embassy_history' not in utils.users[target_id]:
        utils.users[target_id]['embassy_history'] = set()
    utils.users[target_id]['embassy_history'].add(user_id)
    # کاهش روابط
    utils.country_relations[user_id][target_id] = max(-100, utils.country_relations[user_id].get(target_id, 0) - 20)
    utils.country_relations[target_id][user_id] = max(-100, utils.country_relations[target_id].get(user_id, 0) - 20)
    utils.save_country_relations()
    # اعلان به هر دو طرف با نمایش مقدار فعلی روابط
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                f'🏛️ شما سفارتخانه با {utils.users[target_id]["country"]} را بستید.\n'
                f'🔢 وضعیت فعلی روابط: {utils.country_relations[user_id].get(target_id, 0):+.1f}'
            )
        )
    except Exception:
        pass
    try:
        await context.bot.send_message(
            chat_id=int(target_id),
            text=(
                f'🏛️ کشور {utils.users[user_id]["country"]} سفارتخانه با شما را بست.\n'
                f'🔢 وضعیت فعلی روابط: {utils.country_relations[target_id].get(user_id, 0):+.1f}'
            )
        )
    except Exception:
        pass
    # پیام به کانال اخبار (خلاصه)
    try:
        await context.bot.send_message(
            chat_id=NEWS_CHANNEL_ID,
            text=f'🏛️ سفارتخانه بین کشور {utils.users[user_id]["country"]} و {utils.users[target_id]["country"]} بسته شد و روابط ۲۰ واحد کاهش یافت.'
        )
    except Exception:
        pass
    await query.edit_message_text('سفارتخانه بسته شد و روابط ۲۰ واحد کاهش یافت.')

# --- درخواست باز کردن سفارتخانه ---
async def handle_reopen_embassy_request(query, user_id, target_id, context):
    # فقط اگر سفارتخانه بسته است
    if user_id in utils.embassies and target_id in utils.embassies[user_id]:
        await query.edit_message_text('سفارتخانه با این کشور فعال است.')
        return
    # ارسال درخواست به کشور مقابل
    keyboard = [
        [InlineKeyboardButton('تایید باز کردن سفارتخانه', callback_data=f'accept_reopen_embassy_{user_id}')],
        [InlineKeyboardButton('رد ❌', callback_data='embassy_menu')]
    ]
    try:
        await context.bot.send_message(
            chat_id=int(target_id),
            text=f'کشور {utils.users[user_id]["country"]} درخواست باز کردن سفارتخانه را دارد. آیا تایید می‌کنید؟',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        pass
    await query.edit_message_text('درخواست باز کردن سفارتخانه ارسال شد و منتظر تایید طرف مقابل است.')

# --- تایید باز کردن سفارتخانه ---
async def handle_accept_reopen_embassy(query, user_id, from_id, context):
    # فقط اگر سفارتخانه بسته است
    if user_id in utils.embassies and from_id in utils.embassies[user_id]:
        await query.edit_message_text('سفارتخانه با این کشور فعال است.')
        return
    # باز کردن سفارتخانه
    if user_id not in utils.embassies:
        utils.embassies[user_id] = []
    if from_id not in utils.embassies:
        utils.embassies[from_id] = []
    utils.embassies[user_id].append(from_id)
    utils.embassies[from_id].append(user_id)
    # افزایش روابط
    utils.country_relations[user_id][from_id] = min(100, utils.country_relations[user_id].get(from_id, 0) + 20)
    utils.country_relations[from_id][user_id] = min(100, utils.country_relations[from_id].get(user_id, 0) + 20)
    utils.save_country_relations()
    # پیام به کانال اخبار
    try:
        await context.bot.send_message(
            chat_id=NEWS_CHANNEL_ID,
            text=f'🏛️ سفارتخانه بین کشور {utils.users[user_id]["country"]} و {utils.users[from_id]["country"]} مجدداً باز شد و روابط ۲۰ واحد افزایش یافت.'
        )
    except Exception:
        pass
    # پیام به هر دو طرف
    try:
        await context.bot.send_message(
            chat_id=int(from_id),
            text=f'سفارتخانه شما با {utils.users[user_id]["country"]} مجدداً باز شد و روابط ۲۰ واحد افزایش یافت!'
        )
    except Exception:
        pass
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f'سفارتخانه شما با {utils.users[from_id]["country"]} مجدداً باز شد و روابط ۲۰ واحد افزایش یافت!'
        )
    except Exception:
        pass
    await query.edit_message_text('سفارتخانه با موفقیت باز شد و روابط ۲۰ واحد افزایش یافت!')

async def handle_embassy_request(query, user_id, target_id, context):
    user_country = utils.users.get(user_id, {}).get('country', '')
    target_country = utils.users.get(target_id, {}).get('country', '')
    
    # استفاده از وزیر خارجه انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'foreign' in selected_officials:
        foreign_minister = selected_officials['foreign']
    else:
        foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
    
    turn = game_data['turn']
    if user_id not in embassy_requests:
        embassy_requests[user_id] = {}
    if embassy_requests[user_id].get(target_id) == turn:
        await query.edit_message_text('شما در این دور قبلاً به این کشور درخواست سفارتخانه داده‌اید.')
        return
    user_relations = utils.country_relations.get(user_id, {})
    if user_relations.get(target_id, 0) <= 20:
        await query.edit_message_text('روابط شما با این کشور برای ساخت سفارتخانه کافی نیست (حداقل ۲۰).')
        return
    # چک کردن اینکه آیا سفارتخانه در تاریخچه وجود دارد
    in_history = 'embassy_history' in utils.users[user_id] and target_id in utils.users[user_id]['embassy_history']
    if in_history:
        await query.edit_message_text('شما قبلاً با این کشور سفارتخانه داشته‌اید و نمی‌توانید دوباره بسازید. از بخش "باز کردن سفارتخانه" استفاده کنید.')
        return
    # چک کردن اینکه آیا سفارتخانه فعال وجود دارد
    user_embassies = utils.embassies.get(user_id, [])
    if target_id in user_embassies:
        await query.edit_message_text('شما قبلاً با این کشور سفارتخانه فعال دارید.')
        return
    embassy_requests[user_id][target_id] = turn
    
    # پیام وزیر خارجه (بدون تکرار متن وضعیت اصلی)
    minister_message = f"🤝 {foreign_minister['name']}: درخواست سفارتخانه با {target_country} ارسال شد. منتظر پاسخ آن‌ها هستیم."
    
    keyboard = [
        [InlineKeyboardButton('قبول ✅', callback_data=f'accept_embassy_{user_id}')],
        [InlineKeyboardButton('رد ❌', callback_data='embassy_menu')]
    ]
    try:
        await context.bot.send_message(
            chat_id=int(target_id),
            text=f'🏛️ کشور {user_country} درخواست ساخت سفارتخانه با کشور شما را دارد. آیا قبول می‌کنید؟',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception:
        pass
    # پیام تایید به کاربر (بدون تکرار عبارت «منتظر...» در هر دو قسمت)
    await query.edit_message_text(
        f'🏛️ درخواست سفارتخانه ارسال شد.\n\n{minister_message}'
    )

async def handle_embassy_accept(query, user_id, from_id, context):
    user_country = utils.users.get(user_id, {}).get('country', '')
    from_country = utils.users.get(from_id, {}).get('country', '')
    
    # استفاده از وزیر خارجه انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'foreign' in selected_officials:
        foreign_minister = selected_officials['foreign']
    else:
        foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
    
    user_relations = utils.country_relations.get(user_id, {})
    if user_relations.get(from_id, 0) <= 20:
        await query.edit_message_text('روابط شما با این کشور برای ساخت سفارتخانه کافی نیست.')
        return
    # چک کردن اینکه آیا سفارتخانه در تاریخچه وجود دارد
    in_history = 'embassy_history' in utils.users[user_id] and from_id in utils.users[user_id]['embassy_history']
    if in_history:
        await query.edit_message_text('شما قبلاً با این کشور سفارتخانه داشته‌اید و نمی‌توانید دوباره بسازید. از بخش "باز کردن سفارتخانه" استفاده کنید.')
        return
    # چک کردن اینکه آیا سفارتخانه فعال وجود دارد
    user_embassies = utils.embassies.get(user_id, [])
    if from_id in user_embassies:
        await query.edit_message_text('شما قبلاً با این کشور سفارتخانه فعال دارید.')
        return
    if user_id not in utils.embassies:
        utils.embassies[user_id] = []
    if from_id not in utils.embassies:
        utils.embassies[from_id] = []
    if from_id not in utils.embassies[user_id]:
        utils.embassies[user_id].append(from_id)
    if user_id not in utils.embassies[from_id]:
        utils.embassies[from_id].append(user_id)
    if user_id not in utils.country_relations:
        utils.country_relations[user_id] = {}
    if from_id not in utils.country_relations:
        utils.country_relations[from_id] = {}
    utils.country_relations[user_id][from_id] = min(100, utils.country_relations[user_id].get(from_id, 0) + 20)
    utils.country_relations[from_id][user_id] = min(100, utils.country_relations[from_id].get(user_id, 0) + 20)
    utils.save_country_relations()
    
    # پیام وزیر خارجه
    minister_message = f"🏛️ {foreign_minister['name']}: سفارتخانه با {from_country} ({utils.get_user_capital(from_id)}) با موفقیت تاسیس شد! این گام مهمی در بهبود روابط دیپلماتیک ما است."
    
    # پیام به کانال اخبار با file_id مناسب
    embassy_photo_id = "https://t.me/TextEmpire_IR/40" # این را با file_id واقعی عکس سفارت جایگزین کن
    try:
        await context.bot.send_photo(
            chat_id=NEWS_CHANNEL_ID,
            photo=embassy_photo_id,
            caption=f"🏛️ سفارتخانه بین کشور {user_country} ({utils.get_user_capital(user_id)}) و {from_country} ({utils.get_user_capital(from_id)}) با موفقیت تاسیس شد و روابط آن‌ها بهبود یافت!",
            parse_mode='HTML'
        )
    except Exception:
        pass
    # پیام به هر دو طرف
    try:
        await context.bot.send_message(
            chat_id=int(from_id),
            text=f"🏛️ درخواست سفارتخانه شما توسط {user_country} ({utils.get_user_capital(user_id)}) پذیرفته شد و ۲۰ واحد روابط افزایش یافت!"
        )
    except Exception:
        pass
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"🏛️ شما درخواست سفارتخانه {from_country} ({utils.get_user_capital(from_id)}) را پذیرفتید و ۲۰ واحد روابط افزایش یافت!"
        )
    except Exception:
        pass
    await query.edit_message_text(f"🏛️ سفارتخانه بین {user_country} ({utils.get_user_capital(user_id)}) و {from_country} ({utils.get_user_capital(from_id)}) با موفقیت تاسیس شد!\n\n{minister_message}")

async def handle_accept_peace(query, user_id, from_id, context):
    user_country = utils.users[user_id]['country']
    from_country = utils.users[from_id]['country']
    
    # استفاده از وزیر خارجه انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'foreign' in selected_officials:
        foreign_minister = selected_officials['foreign']
    else:
        foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
    
    # حذف اعلان جنگ برای هر دو طرف
    # پایان دادن جنگ در ساختار جدید
    for wid, w in list(utils.war_declarations.items()):
        if w.get('status') == 'active':
            a = w.get('attacker')
            d = w.get('defender')
            if (a == user_country and d == from_country) or (a == from_country and d == user_country):
                utils.war_declarations[wid]['status'] = 'ended'
                utils.war_declarations[wid]['end_turn'] = game_data.get('turn', 1)
                utils.war_declarations[wid]['end_reason'] = 'peace'
    if user_id in pending_peace_requests:
        del pending_peace_requests[user_id]
    
    # ذخیره تغییرات اعلان‌های جنگ
    from utils import save_war_declarations
    save_war_declarations()
    
    # افزایش روابط 50 واحدی برای هر دو طرف
    if user_id not in utils.country_relations:
        utils.country_relations[user_id] = {}
    if from_id not in utils.country_relations:
        utils.country_relations[from_id] = {}
    utils.country_relations[user_id][from_id] = min(100, utils.country_relations[user_id].get(from_id, 0) + 50)
    utils.country_relations[from_id][user_id] = min(100, utils.country_relations[from_id].get(user_id, 0) + 50)
    utils.save_country_relations()  # ذخیره روابط
    
    # پیام وزیر خارجه
    minister_message = f"🤝 {foreign_minister['name']}: آتش‌بس با {from_country} برقرار شد! این گام مهمی در تثبیت صلح و بهبود روابط دیپلماتیک است."
    
    # پیام به کانال اخبار
    file_id = 'https://t.me/TextEmpire_IR/46'  # file_id عکس آتش‌بس (تغییر بده به file_id واقعی)
    news_text = f"🤝 <b>آتش‌بس برقرار شد!</b>\n\nبین کشور {user_country} و {from_country} آتش‌بس برقرار شد و روابط ۵۰ واحد بهبود یافت."
    await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=file_id, caption=news_text, parse_mode='HTML')
    # پیام به هر دو طرف
    await context.bot.send_message(chat_id=int(user_id), text=f'آتش‌بس با {from_country} برقرار شد و جنگ متوقف شد. روابط ۵۰ واحد بهبود یافت.')
    await context.bot.send_message(chat_id=int(from_id), text=f'درخواست آتش‌بس شما توسط {user_country} پذیرفته شد و جنگ متوقف شد. روابط ۵۰ واحد بهبود یافت.')
    await safe_edit_message(query, f'آتش‌بس برقرار شد و جنگ متوقف شد. روابط ۵۰ واحد بهبود یافت.\n\n<blockquote>{minister_message}</blockquote>', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]))

async def handle_reject_peace(query, user_id, from_id, context):
    user_country = utils.users[user_id]['country']
    from_country = utils.users[from_id]['country']
    
    # استفاده از وزیر خارجه انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'foreign' in selected_officials:
        foreign_minister = selected_officials['foreign']
    else:
        foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
    
    if user_id in pending_peace_requests:
        del pending_peace_requests[user_id]
    
    # پیام وزیر خارجه
    minister_message = f"🚨 {foreign_minister['name']}: درخواست آتش‌بس از {from_country} رد شد. جنگ ادامه خواهد داشت."
    
    await context.bot.send_message(chat_id=int(from_id), text=f'درخواست آتش‌بس شما توسط {user_country} رد شد و جنگ ادامه دارد.')
    await safe_edit_message(query, f'درخواست آتش‌بس رد شد و جنگ ادامه دارد.\n\n<blockquote>{minister_message}</blockquote>', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]))
# تابع نمایش کشورهای قابل حمله زمینی

# تابع تست برای بررسی ذخیره اطلاعات اتحاد
def test_alliance_saving():
    print(f"[DEBUG] Alliances: {utils.alliances}")
    print(f"[DEBUG] User alliances: {utils.user_alliances}")
    print(f"[DEBUG] Alliance trades: {alliance_trades}")
    save_alliances()
    print("[DEBUG] Alliances saved!")

# تابع پیشنهاد وزیر خارجه به رهبر کشور
async def foreign_minister_suggestions(user_id, context):
    """وزیر خارجه به رهبر کشور پیشنهاد می‌دهد که با کدام کشور درخواست بهبود روابط بفرستد"""
    user = utils.users.get(user_id, {})
    if not user.get('activated'):
        return
    
    # استفاده از وزیر خارجه انتخاب شده
    selected_officials = user.get('selected_officials', {})
    if 'foreign' in selected_officials:
        foreign_minister = selected_officials['foreign']
    else:
        foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
    
    user_country = user.get('country', 'کشور ناشناس')
    user_relations = utils.country_relations.get(user_id, {})
    
    # کشورهای واجد شرایط برای پیشنهاد
    eligible_countries = []
    for target_id, target_user in users.items():
        if target_id == user_id or not target_user.get('activated'):
            continue
        
        # بررسی اینکه آیا قبلاً در این دور درخواست شده
        if user_id in relation_improvement_requests and target_id in relation_improvement_requests[user_id]:
            continue
        
        target_country = target_user.get('country', 'کشور ناشناس')
        current_relation = user_relations.get(target_id, 0)
        
        # پیشنهاد برای کشورهایی که روابط متوسط یا پایین دارند
        if current_relation < 50:
            eligible_countries.append({
                'id': target_id,
                'country': target_country,
                'relation': current_relation,
                'priority': 'high' if current_relation < 20 else 'medium'
            })
    
    if not eligible_countries:
        return
    
    # انتخاب فقط 1 کشور برای پیشنهاد
    import random
    suggestion = random.choice(eligible_countries)
    
    # ذخیره پیشنهاد وزیر خارجه برای بررسی بعدی
    if 'foreign_minister_suggestions' not in user:
        user['foreign_minister_suggestions'] = {}
    
    suggestion_data = {
        'target_id': suggestion['id'],
        'target_country': suggestion['country'],
        'suggested_at': utils.game_data.get('turn', 1),
        'followed': False
    }
    
    user['foreign_minister_suggestions'][suggestion['id']] = suggestion_data
    save_users()
    
    # پیام وزیر خارجه
    relation_text = get_relation_text(suggestion['relation'])
    priority_emoji = "🔴" if suggestion['priority'] == 'high' else "🟡"
    
    minister_message = f"🤝 {foreign_minister['name']}: رهبر محترم، پیشنهاد می‌کنم با کشور {suggestion['country']} درخواست بهبود روابط بفرستید.\n\n"
    minister_message += f"{priority_emoji} {suggestion['country']} (روابط فعلی: {relation_text})\n"
    minister_message += f"\n💡 این کشور برای بهبود روابط دیپلماتیک مناسب است."
    
    # ارسال پیام به رهبر کشور
    try:
        keyboard = [
            [InlineKeyboardButton('مشاهده روابط', callback_data='country_relations')],
            [InlineKeyboardButton('بهبود روابط', callback_data='improve_relations')],
            [InlineKeyboardButton('بستن', callback_data='diplomacy')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"📢 <b>پیشنهاد {foreign_minister['title']}</b>\n\n{minister_message}",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"خطا در ارسال پیشنهاد وزیر خارجه: {e}")



# ... existing code ...

async def handle_foreign_minister_suggestions(query, context):
    """هندل کردن درخواست پیشنهاد وزیر خارجه"""
    user_id = str(query.from_user.id)
    await foreign_minister_suggestions(user_id, context)
    
    # پیام تایید
    await query.edit_message_text(
        "💡 پیشنهاد وزیر خارجه ارسال شد. لطفاً پیام‌های دریافتی را بررسی کنید.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='country_relations')]])
    )

# ... existing code ...

# منوی دیپلماسی
async def show_diplomacy_menu(query):
    user_id = str(query.from_user.id)
    if user_id not in utils.users or not utils.users[user_id].get('activated', False):
        await show_simple_section(query, 'شما هنوز کشور فعال نکرده‌اید.')
        return
    
    # تعلیق ۲ دوری دیپلماسی در صورت ترور وزیر خارجه
    current_turn = utils.game_data.get('turn', 1)
    panel_suspensions = utils.users[user_id].get('panel_suspensions', {})
    if current_turn < panel_suspensions.get('diplomacy', 0):
        await query.edit_message_text(
            '⚫️ <b>دوره سوگواری دیپلماتیک</b>\n\nبه دلیل ترور وزیر خارجه، این بخش تا دو دور آینده در دسترس نیست.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_game_menu')]]),
            parse_mode='HTML'
        )
        return
    
    country_name = utils.users[user_id]['country']
    gov_title = utils.users[user_id].get('government_title', 'رهبر')
    player_name = utils.users[user_id].get('player_name', 'نامشخص')
    
    # استفاده از وزیر خارجه انتخاب شده
    selected_officials = utils.users[user_id].get('selected_officials', {})
    if 'foreign' in selected_officials:
        foreign_minister = selected_officials['foreign']
    else:
        # اگر وزیر خارجه انتخاب نشده، از اسامی پیش‌فرض استفاده کن
        foreign_minister = {'name': 'وزیر خارجه', 'title': 'وزیر خارجه'}
    
    # پیام خوشامدگویی دیپلماتیک
    welcome_text = f'🌍 <b>خوش آمدید!</b>\n\n'
    welcome_text += f'🤝 من {foreign_minister["name"]}، {foreign_minister["title"]} شما هستم.\n'
    welcome_text += f'🏛️ <b>منوی دیپلماسی کشور {country_name}</b>\n\n'
    
    # تحلیل هوشمند دیپلماتیک (اگر وزیر خارجه زنده است)
    is_alive_foreign = utils.users[user_id].get('selected_officials', {}).get('foreign', {}).get('alive', True)
    if is_alive_foreign:
        try:
            from analysis import generate_diplomatic_analysis
            analysis = generate_diplomatic_analysis(user_id)
            welcome_text += f'<b>پیشنهاد {foreign_minister["title"]} {foreign_minister["name"]}:</b>\n<blockquote>{analysis}</blockquote>\n\n'
        except Exception:
            # اگر تحلیل خطا داد، فقط متن خطا را نمایش نده و از کنار آن بگذر
            pass
    else:
        welcome_text += '<b>پیشنهاد وزیر خارجه:</b>\n<blockquote>این مقام ترور شده و پیشنهادی ارائه نمی‌شود.</blockquote>\n\n'
    welcome_text += 'یکی از گزینه‌ها را انتخاب کنید:'
    
    keyboard = [
        [InlineKeyboardButton('روابط با کشورها 🌍', callback_data='country_relations'), InlineKeyboardButton('مستعمرات 🏛️', callback_data='colonies_menu')],
        [InlineKeyboardButton('بانک بین‌المللی 🏦', callback_data='international_bank'), InlineKeyboardButton('بیانیه 📝', callback_data='statement')],
        [InlineKeyboardButton('اتحاد 🤝', callback_data='alliance_menu'), InlineKeyboardButton('🏛️ سازمان ملل', callback_data='united_nations_access')],
        [InlineKeyboardButton('تحریم 🚫', callback_data='sanctions_menu'), InlineKeyboardButton('سایر بخش‌ها', callback_data='other_diplomacy')],
        [InlineKeyboardButton('عملیات مخفی 🔪', callback_data='covert_ops')],
        [InlineKeyboardButton('📨 مکالمه خصوصی', callback_data='private_message')],
        [InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_game_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')

# ==================== Private Messaging System ====================

async def show_private_message_targets(query):
    """Show list of active countries for private messaging"""
    user_id = str(query.from_user.id)
    sender_country = utils.users.get(user_id, {}).get('country', '')
    
    # Get all active countries except sender
    active_countries = []
    for uid, user in users.items():
        if (user.get('activated', False) and 
            uid != user_id and 
            user.get('country') and 
            user.get('country') != sender_country):
            active_countries.append((uid, user.get('country')))
    
    if not active_countries:
        await query.edit_message_text(
            '❌ هیچ کشور فعالی برای مکالمه خصوصی یافت نشد.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='diplomacy_menu')]])
        )
        return
    
    # Create 2-column layout
    keyboard = []
    for i in range(0, len(active_countries), 2):
        row = []
        # First country in row
        uid, country = active_countries[i]
        row.append(InlineKeyboardButton(f"🇺🇳 {country}", callback_data=f'pm_target_{uid}'))
        
        # Second country in row (if exists)
        if i + 1 < len(active_countries):
            uid2, country2 = active_countries[i + 1]
            row.append(InlineKeyboardButton(f"🇺🇳 {country2}", callback_data=f'pm_target_{uid2}'))
        
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='diplomacy_menu')])
    
    await query.edit_message_text(
        '📨 کشور مورد نظر برای مکالمه خصوصی را انتخاب کنید:',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_private_message(query, target_uid):
    """Show confirmation dialog for private messaging"""
    user_id = str(query.from_user.id)
    sender_country = utils.users.get(user_id, {}).get('country', '')
    target_country = utils.users.get(target_uid, {}).get('country', '')
    
    text = f"⚠️ آیا می‌خواهید مکالمه خصوصی با {target_country} آغاز کنید؟"
    keyboard = [
        [InlineKeyboardButton('✅ بله', callback_data=f'pm_confirm_{target_uid}')],
        [InlineKeyboardButton('❌ خیر', callback_data='private_message')]
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def start_private_message(query, target_uid):
    """Start private messaging session"""
    user_id = str(query.from_user.id)
    sender_country = utils.users.get(user_id, {}).get('country', '')
    target_country = utils.users.get(target_uid, {}).get('country', '')
    
    # Set pending state
    pending_private_message[user_id] = {
        'target_uid': target_uid,
        'target_country': target_country,
        'sender_country': sender_country
    }
    
    await query.edit_message_text(
        f'📨 پیام خود را برای {target_country} تایپ کنید:\n\n'
        f'💡 پیام شما با فرمت زیر ارسال خواهد شد:\n'
        f'🔊 {sender_country}: [پیام شما]',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('❌ لغو', callback_data='diplomacy_menu')]])
    )

async def handle_private_message_text(update, context=None):
    """Handle private message text input"""
    user_id = str(update.effective_user.id)
    if user_id not in pending_private_message:
        return False
    
    message_text = (update.message.text or '').strip()
    if not message_text:
        await update.message.reply_text('لطفاً پیام معتبری وارد کنید.')
        return True
    
    pm_data = pending_private_message[user_id]
    target_uid = pm_data['target_uid']
    sender_country = pm_data['sender_country']
    
    # Format message for receiver
    formatted_message = f"🔊 {sender_country} ({utils.get_user_capital(user_id)}): {message_text}"
    
    try:
        # Send to target user using context.bot
        if context and context.bot:
            await context.bot.send_message(chat_id=int(target_uid), text=formatted_message)
        else:
            # Fallback: create bot instance
            from telegram import Bot
            bot = Bot(token=utils.BOT_TOKEN)
            await bot.send_message(chat_id=int(target_uid), text=formatted_message)
        
        # Check for country spying on target (incoming to target)
        await check_and_forward_spied_message(target_uid, formatted_message, context)
        # Check for country spying on sender (outgoing from sender)
        await check_and_forward_spied_message(user_id, formatted_message, context)
        
        # Confirm to sender
        await update.message.reply_text(
            f'✅ پیام شما به {pm_data["target_country"]} ارسال شد.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت به دیپلماسی', callback_data='diplomacy_menu')]])
        )
        
    except Exception as e:
        print(f"Error sending private message: {e}")
        await update.message.reply_text(
            f'❌ خطا در ارسال پیام: {str(e)}. لطفاً دوباره تلاش کنید.',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت به دیپلماسی', callback_data='diplomacy_menu')]])
        )
    
    # Clean up
    pending_private_message.pop(user_id, None)
    return True

async def check_and_forward_spied_message(target_uid, message, context):
    """Check if target is being spied on and forward message to spy"""
    try:
        # If target has active anti-spy, do not forward
        target_user = utils.users.get(str(target_uid), {})
        target_org = target_user.get('national_security_org', {})
        if target_org.get('anti_spy_active', False):
            return
        # Find users who are spying on this target
        for user_id, user in utils.users.items():
            espionage_effects = user.get('espionage_effects', {})
            country_spy = espionage_effects.get('country_spy', {})
            
            if (country_spy.get('target_uid') == target_uid and 
                country_spy.get('type') == 'country_spy'):
                
                # Forward message to spy
                spy_message = f"🎧 [شنود] {message}"
                
                if context and context.bot:
                    await context.bot.send_message(chat_id=int(user_id), text=spy_message)
                else:
                    from telegram import Bot
                    bot = Bot(token=utils.BOT_TOKEN)
                    await bot.send_message(chat_id=int(user_id), text=spy_message)
                    
    except Exception as e:
        print(f"Error forwarding spied message: {e}")

async def check_and_forward_alliance_spied_message(alliance_id, message, context):
    """Check if alliance is being spied on and forward message to spy"""
    try:
        # Find users who are spying on this alliance
        for user_id, user in utils.users.items():
            espionage_effects = user.get('espionage_effects', {})
            alliance_spy = espionage_effects.get('alliance_spy', {})
            
            if (alliance_spy.get('alliance_id') == alliance_id and 
                alliance_spy.get('type') == 'alliance_spy'):
                
                # Forward message to spy
                spy_message = f"🎧 [شنود اتحاد] {message}"
                
                if context and context.bot:
                    await context.bot.send_message(chat_id=int(user_id), text=spy_message)
                else:
                    from telegram import Bot
                    bot = Bot(token=utils.BOT_TOKEN)
                    await bot.send_message(chat_id=int(user_id), text=spy_message)
                    
    except Exception as e:
        print(f"Error forwarding alliance spied message: {e}")

# ==================== end Private Messaging System ====================

# ==================== عملیات مخفی: ترور ====================
async def show_covert_ops_menu(query):
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    if not user.get('activated'):
        await query.answer('❌ ابتدا کشور خود را فعال کنید.', show_alert=True)
        return
    current_turn = utils.game_data.get('turn', 1)
    last_turn = user.get('last_assassination_turn', -10**9)
    remaining = max(0, 12 - (current_turn - last_turn))
    text = '🔪 <b>عملیات مخفی</b>\n\n'
    text += 'می‌توانید یکی از مقامات کشور هدف را ترور کنید.\n'
    text += f'⏱️ کول‌داون: هر ۱۲ دور یک‌بار. '
    text += (f"(باقیمانده: {remaining} دور)\n\n" if remaining>0 else "(در دسترس)\n\n")
    keyboard = [[InlineKeyboardButton('🎯 شروع ترور', callback_data='assassination_pick_country')],
                [InlineKeyboardButton('🔙 بازگشت', callback_data='diplomacy_menu')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def assassination_pick_country(query):
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    current_turn = utils.game_data.get('turn', 1)
    last_turn = user.get('last_assassination_turn', -10**9)
    if current_turn - last_turn < 12:
        await query.answer('⏱️ هنوز کول‌داون ۱۲ دوری تمام نشده.', show_alert=True)
        return
    my_country = user.get('country', '')
    countries = [ud.get('country') for uid, ud in utils.users.items() if ud.get('activated') and ud.get('country') and ud.get('country')!=my_country]
    if not countries:
        await query.answer('هیچ کشور فعالی برای هدف وجود ندارد.', show_alert=True)
        return
    utils.pending_assassination[user_id] = {'step': 'pick_country'}
    utils.save_users()
    # ساخت دکمه‌ها به شکل دو ستونی و استفاده از هش کوتاه برای جلوگیری از Button_data_invalid
    import hashlib
    country_to_hash = {}
    keyboard = []
    row = []
    for c in countries:
        h = hashlib.sha1(c.encode('utf-8')).hexdigest()[:10]
        country_to_hash[h] = c
        row.append(InlineKeyboardButton(c, callback_data=f'assassination_country_{h}'))
        if len(row)==2:
            keyboard.append(row); row=[]
    if row:
        keyboard.append(row)
    # ذخیره نگاشت برای این کاربر
    utils.pending_assassination[user_id] = {'step': 'pick_country', 'map': country_to_hash}
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='covert_ops')])
    await query.edit_message_text('🎯 کشور هدف را انتخاب کنید:', reply_markup=InlineKeyboardMarkup(keyboard))

async def assassination_pick_role_from_hash(query, country_hash: str):
    user_id = str(query.from_user.id)
    mapping = utils.pending_assassination.get(user_id, {}).get('map', {})
    target_country = mapping.get(country_hash)
    if not target_country:
        await query.answer('کشور هدف نامعتبر است.', show_alert=True)
        return
    utils.pending_assassination[user_id] = {'step': 'pick_role', 'selected_country': target_country}
    utils.save_users()
    keyboard = [
        [InlineKeyboardButton('🪖 ژنرال', callback_data='assassination_role_general')],
        [InlineKeyboardButton('🏛 وزیر کشور', callback_data='assassination_role_minister')],
        [InlineKeyboardButton('🤝 وزیر خارجه', callback_data='assassination_role_foreign')],
        [InlineKeyboardButton('💼 وزیر دارایی', callback_data='assassination_role_finance')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='assassination_pick_country')]
    ]
    await query.edit_message_text(f'🎯 کشور هدف: {target_country}\nنقش مورد نظر را انتخاب کنید:', reply_markup=InlineKeyboardMarkup(keyboard))

async def assassination_confirm(query, role_key: str):
    user_id = str(query.from_user.id)
    draft = utils.pending_assassination.get(user_id)
    if not draft or draft.get('step')!='pick_role':
        await query.answer('درخواست نامعتبر.', show_alert=True); return
    target_country = draft.get('selected_country')
    # یافتن target_id
    target_id = None
    for uid, ud in utils.users.items():
        if ud.get('activated') and ud.get('country')==target_country:
            target_id = uid; break
    if not target_id:
        await query.answer('کشور هدف یافت نشد.', show_alert=True); return
    # هزینه: 2000 نیرو ویژه + 50 میلیون پول
    attacker = utils.users.get(user_id, {})
    resources = attacker.get('resources', {})
    cash = resources.get('cash', 0)
    special_forces = resources.get('special_forces', 0)
    role_fa = {'general':'ژنرال','minister':'وزیر کشور','foreign':'وزیر خارجه','finance':'وزیر دارایی'}.get(role_key, role_key)
    text = (
        f"⚠️ تایید عملیات ترور\n\n"
        f"🎯 کشور هدف: {target_country}\n"
        f"🎭 مقام هدف: {role_fa}\n\n"
        f"💵 هزینه: 50,000,000 دلار\n"
        f"🪖 هزینه: 2,000 نیروی ویژه\n\n"
        f"موافقید عملیات انجام شود؟"
    )
    keyboard = [
        [InlineKeyboardButton('✅ بله، انجام بده', callback_data=f'assassination_do_{role_key}')],
        [InlineKeyboardButton('❌ خیر، انصراف', callback_data='covert_ops')]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def assassination_execute(query, role_key: str, context):
    user_id = str(query.from_user.id)
    draft = utils.pending_assassination.get(user_id)
    if not draft or draft.get('step')!='pick_role':
        await query.answer('درخواست نامعتبر.', show_alert=True); return
    target_country = draft.get('selected_country')
    target_id = None
    for uid, ud in utils.users.items():
        if ud.get('activated') and ud.get('country')==target_country:
            target_id = uid; break
    if not target_id:
        await query.answer('کشور هدف یافت نشد.', show_alert=True); return
    # جلوگیری از ترور مجدد همان مقام
    target_officials = utils.users.get(target_id, {}).get('selected_officials', {})
    target_official = target_officials.get(role_key, {})
    if target_official and target_official.get('alive') is False:
        await query.answer('❌ این مقام قبلاً ترور شده و دیگر قابل هدف قرار دادن نیست.', show_alert=True)
        return
    # چک و کسر هزینه
    attacker = utils.users.get(user_id, {})
    resources = attacker.setdefault('resources', {})
    if resources.get('cash', 0) < 50_000_000 or resources.get('special_forces', 0) < 2000:
        await query.answer('❌ منابع کافی ندارید (50M پول و 2000 نیروی ویژه لازم است).', show_alert=True)
        return
    resources['cash'] -= 50_000_000
    resources['special_forces'] -= 2000
    utils.save_users()
    # ایجاد مینی‌گیم
    from uuid import uuid4
    game_id = str(uuid4())[:8]
    utils.assassination_games[game_id] = {
        'id': game_id,
        'attacker_id': user_id,
        'target_id': target_id,
        'role': role_key,
        'status': 'await_defender',
        'created_at': int(datetime.now().timestamp()),
        'defender_deadline': int(datetime.now().timestamp()) + 300,
        'attacker_paid': True,
        'defender_paid': False,
        'round': 0,
        'rounds_total': 3,
        'shared_sequences': [],
        'attacker_inputs': {},
        'defender_inputs': {},
        'attacker_scores': [],
        'defender_scores': [],
        'prep_start': None,
        'prep_deadline': None,
        'result_announce_at': None
    }
    # پیام برای مهاجم
    role_fa = {'general':'ژنرال','minister':'وزیر کشور','foreign':'وزیر خارجه','finance':'وزیر دارایی'}.get(role_key, role_key)
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"⏳ عملیات ترور ثبت شد.\nشناسه: {game_id}\n🎯 هدف: {target_country} - {role_fa}\n🕒 تا 5 دقیقه به طرف مقابل فرصت داده می‌شود برای مقابله."
        )
    except Exception:
        pass
    # دعوت مخفی برای مدافع
    try:
        defend_text = (
            f"⚠️ تلاش برای ترور {role_fa} در کشور شما گزارش شده است.\n\n"
            f"برای مقابله، باید 50,000,000 دلار و 2,000 نیروی ویژه بپردازید.\n"
            f"⏳ شما 5 دقیقه فرصت دارید."
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton('🛡️ مقابله با ترور', callback_data=f'assassination_defend_{game_id}')]])
        await context.bot.send_message(chat_id=int(target_id), text=defend_text, reply_markup=kb)
    except Exception:
        pass
    # ویرایش پیام جاری
    try:
        await query.edit_message_text('⏳ عملیات ثبت شد. منتظر واکنش کشور هدف تا 5 دقیقه آینده می‌مانیم.', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='covert_ops')]]))
    except Exception:
        pass

async def process_assassination_jobs(context):
    now = int(datetime.now().timestamp())
    remain = []
    for job in utils.pending_assassination_jobs:
        started_at = job.get('started_at') or now
        eta_sec = job.get('eta_sec') or 300
        if now - started_at >= eta_sec:
            # ارزیابی نتیجه
            attacker_id = job['attacker_id']
            target_id = job['target_id']
            role_key = job['role']
            target_country = utils.users.get(target_id, {}).get('country', 'نامشخص')
            attacker_country = utils.users.get(attacker_id, {}).get('country', 'نامشخص')
            import random
            success = random.random() < 0.5
            exposed = (not success) and (random.random() < 0.5)
            role_storage_key = {'general':'general','minister':'minister','foreign':'foreign','finance':'finance'}.get(role_key, role_key)
            role_fa = {'general':'ژنرال','minister':'وزیر کشور','foreign':'وزیر خارجه','finance':'وزیر دارایی'}.get(role_storage_key, role_storage_key)
            if success:
                sel = utils.users.get(target_id, {}).setdefault('selected_officials', {})
                official = sel.get(role_storage_key, {'name': role_storage_key, 'title': role_storage_key})
                official['alive'] = False
                official['assassinated_at_turn'] = utils.game_data.get('turn', 1)
                sel[role_storage_key] = official
                susp = utils.users[target_id].setdefault('panel_suspensions', {})
                cur = utils.game_data.get('turn', 1)
                key_map = {'general':'strategy','minister':'country_status','foreign':'diplomacy','finance':'trade'}
                panel_key = key_map.get(role_storage_key)
                if panel_key:
                    susp[panel_key] = max(susp.get(panel_key, 0), cur+2)
                utils.save_users()
                # اعلان‌ها
                try:
                    await context.bot.send_message(chat_id=int(target_id), text=f'🔪 عملیات ترور موفق بود. {role_fa} شما ترور شد.')
                except Exception:
                    pass
                try:
                    await context.bot.send_message(chat_id=int(attacker_id), text='✅ نتیجه ترور: موفق.')
                except Exception:
                    pass
                try:
                    await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo='https://t.me/TextEmpire_IR/95', caption=f'🗞️ خبر فوری: گزارش‌ها حاکی از ترور {role_fa} در {target_country} است.', parse_mode='HTML')
                except Exception:
                    pass
            else:
                try:
                    await context.bot.send_message(chat_id=int(attacker_id), text='❌ نتیجه ترور: شکست.')
                except Exception:
                    pass
                if exposed:
                    try:
                        await context.bot.send_message(chat_id=int(target_id), text=f'⚠️ تلاش برای ترور {role_fa} شما توسط {attacker_country} شناسایی شد!')
                    except Exception:
                        pass
                    try:
                        await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo='https://t.me/TextEmpire_IR/95', caption=f'📰 گزارش اطلاعاتی: تلاش ناکام {attacker_country} برای ترور {role_fa} در {target_country} افشا شد.', parse_mode='HTML')
                    except Exception:
                        pass
                    try:
                        ar = utils.country_relations.setdefault(attacker_id, {})
                        tr = utils.country_relations.setdefault(target_id, {})
                        ar[target_id] = ar.get(target_id, 0) - 30
                        tr[attacker_id] = tr.get(attacker_id, 0) - 30
                        utils.save_country_relations()
                    except Exception:
                        pass
        else:
            remain.append(job)
    utils.pending_assassination_jobs = remain

# ==================== مینی‌گیم ترور ====================
def _generate_sequence():
    import random
    length = random.randint(4, 6)
    dirs = ['⬆️','⬅️','⬇️','➡️']
    return [random.choice(dirs) for _ in range(length)]

def _transform_sequence(seq, variant):
    print(f"[DEBUG] Transform: variant={variant}, seq={seq}")
    if variant == 'normal':
        result = list(seq)
    elif variant == 'reverse':
        result = list(reversed(seq))
    elif variant == 'mirror_h':
        swap = {'⬅️':'➡️','➡️':'⬅️','⬆️':'⬆️','⬇️':'⬇️'}
        result = [swap.get(x, x) for x in seq]
    elif variant == 'mirror_v':
        swap = {'⬆️':'⬇️','⬇️':'⬆️','⬅️':'⬅️','➡️':'➡️'}
        result = [swap.get(x, x) for x in seq]
    else:
        result = list(seq)
    print(f"[DEBUG] Transform result: {result}")
    return result

def _variant_title(variant):
    return {
        'normal': 'عادی',
        'reverse': 'برعکس',
        'mirror_h': 'آینه افقی (چپ/راست جابجا)',
        'mirror_v': 'آینه عمودی (بالا/پایین جابجا)'
    }.get(variant, 'عادی')

def _pick_variant():
    # همه معماها «عادی» باشد
    return 'normal'

def _calc_accuracy(seq, inputs, variant):
    expected = _transform_sequence(seq, variant)
    correct = 0
    for i, ch in enumerate(inputs[:len(expected)]):
        if ch == expected[i]:
            correct += 1
    total = len(expected)
    accuracy = (correct / total) if total else 0.0
    return correct, total, accuracy

def _score_sequence(seq, inputs, elapsed_sec, variant):
    if not seq:
        return 0.0
    expected = _transform_sequence(seq, variant)
    print(f"[DEBUG] Original seq: {seq}")
    print(f"[DEBUG] Variant: {variant}")
    print(f"[DEBUG] Expected: {expected}")
    print(f"[DEBUG] Inputs: {inputs}")
    print(f"[DEBUG] Elapsed: {elapsed_sec}s")

    correct, total, accuracy = _calc_accuracy(seq, inputs, variant)
    # زمان مهم‌تر باشد: 10 ثانیه ایده‌آل، اما هرگز صفر نشود
    # تابع نرم: 1 / (1 + t/10) با کف 0.3
    time_factor = max(0.3, 1.0 / (1.0 + (elapsed_sec / 10.0)))
    score = round(100.0 * accuracy * time_factor, 2)
    print(f"[DEBUG] Correct: {correct}/{total}, Accuracy: {accuracy}, TimeFactor: {time_factor}, Score: {score}")
    return score

def _build_input_keyboard(game_id, current):
    # نمایش ورودی از راست به چپ
    disp = ''.join(reversed(current)) if current else '—'
    row_arrows1 = [InlineKeyboardButton('⬆️', callback_data=f'ass_input_{game_id}_U'), InlineKeyboardButton('⬅️', callback_data=f'ass_input_{game_id}_L')]
    row_arrows2 = [InlineKeyboardButton('⬇️', callback_data=f'ass_input_{game_id}_D'), InlineKeyboardButton('➡️', callback_data=f'ass_input_{game_id}_R')]
    row_ops = [InlineKeyboardButton('⌫ حذف آخری', callback_data=f'ass_back_{game_id}'), InlineKeyboardButton('📤 ارسال', callback_data=f'ass_submit_{game_id}')]
    return InlineKeyboardMarkup([row_arrows1, row_arrows2, row_ops, [InlineKeyboardButton(f'ورودی: {disp}', callback_data='no_action')]])

async def _start_prep_and_rounds(bot, game):
    # ارسال پیام آمادگی 1 دقیقه‌ای
    attacker_id = game['attacker_id']
    target_id = game['target_id']
    try:
        await bot.send_message(chat_id=int(attacker_id), text='⏳ مینی‌گیم تا 1 دقیقه دیگر شروع می‌شود. آماده باشید!')
    except Exception:
        pass
    try:
        await bot.send_message(chat_id=int(target_id), text='⏳ مینی‌گیم تا 1 دقیقه دیگر شروع می‌شود. آماده باشید!')
    except Exception:
        pass
    game['prep_start'] = int(datetime.now().timestamp())
    game['prep_deadline'] = game['prep_start'] + 60

async def _send_round(bot, game):
    # تولید سکانس مشترک و ارسال
    seq = _generate_sequence()
    game['shared_sequences'].append(seq)
    game['round'] += 1
    round_no = game['round']
    variant = _pick_variant()
    game.setdefault('round_variants', []).append(variant)
    seq_text = ''.join(seq)
    # نمایش سکانس
    try:
        await bot.send_message(chat_id=int(game['attacker_id']), text=f'🎯 دور {round_no} — سکانس: {seq_text}\n🔁 نوع معما: {_variant_title(variant)}\nپس از آماده شدن، با دکمه‌ها وارد کنید و «ارسال» را بزنید.')
        await bot.send_message(chat_id=int(game['target_id']), text=f'🎯 دور {round_no} — سکانس: {seq_text}\n🔁 نوع معما: {_variant_title(variant)}\nپس از آماده شدن، با دکمه‌ها وارد کنید و «ارسال» را بزنید.')
    except Exception:
        pass
    # صفر کردن ورودی‌ها و ارسال کیبورد ورودی
    game['attacker_inputs'][round_no] = {'list': [], 'start': int(datetime.now().timestamp())}
    game['defender_inputs'][round_no] = {'list': [], 'start': int(datetime.now().timestamp())}
    game['round_start_time'] = int(datetime.now().timestamp())  # زمان شروع دور برای تایم‌اوت
    kb = _build_input_keyboard(game['id'], [])
    try:
        await bot.send_message(chat_id=int(game['attacker_id']), text='◀️ وارد کنید: (30 ثانیه فرصت دارید)', reply_markup=kb)
        await bot.send_message(chat_id=int(game['target_id']), text='◀️ وارد کنید: (30 ثانیه فرصت دارید)', reply_markup=kb)
    except Exception:
        pass

async def process_assassination_games(context):
    now = int(datetime.now().timestamp())
    to_delete = []
    for gid, game in list(utils.assassination_games.items()):
        status = game.get('status')
        if status == 'await_defender':
            defender_deadline = game.get('defender_deadline') or 0
            if now >= defender_deadline:
                # مدافع وارد نشد: پیروزی مهاجم
                game['status'] = 'final'
                game['winner'] = 'attacker'
                game['result_announce_at'] = now + 30
        elif status == 'prep':
            prep_deadline = game.get('prep_deadline') or 0
            if now >= prep_deadline:
                # شروع شمارش معکوس 5 ثانیه‌ای
                game['status'] = 'countdown'
                game['countdown_value'] = 5
                game['countdown_next_at'] = now
                try:
                    await context.bot.send_message(chat_id=int(game['attacker_id']), text='⏳ شروع بازی در 5')
                    await context.bot.send_message(chat_id=int(game['target_id']), text='⏳ شروع بازی در 5')
                except Exception:
                    pass
        elif status == 'countdown':
            next_at = game.get('countdown_next_at') or now
            val = game.get('countdown_value') or 0
            if now >= next_at:
                if val > 1:
                    val -= 1
                    game['countdown_value'] = val
                    game['countdown_next_at'] = next_at + 1
                    try:
                        await context.bot.send_message(chat_id=int(game['attacker_id']), text=str(val))
                        await context.bot.send_message(chat_id=int(game['target_id']), text=str(val))
                    except Exception:
                        pass
                else:
                    # پایان شمارش و شروع دور
                    game['status'] = 'round'
                    try:
                        await _send_round(context.bot, game)
                    except Exception:
                        pass
        elif status == 'round':
            r = game.get('round') or 0
            round_start = game.get('round_start_time') or now
            
            # بررسی تایم‌اوت 30 ثانیه‌ای برای هر دور
            if now >= round_start + 30:
                # اگر یکی از طرفین هنوز امتیاز نداده، امتیاز 0 بده
                if len(game['attacker_scores']) < r:
                    game['attacker_scores'].append(0.0)
                    try:
                        await context.bot.send_message(chat_id=int(game['attacker_id']), text='⏰ زمان تمام شد! امتیاز شما: 0')
                    except Exception:
                        pass
                if len(game['defender_scores']) < r:
                    game['defender_scores'].append(0.0)
                    try:
                        await context.bot.send_message(chat_id=int(game['target_id']), text='⏰ زمان تمام شد! امتیاز شما: 0')
                    except Exception:
                        pass
            
            # اگر هردو نمره این دور ثبت شده، دور بعد یا پایان
            if len(game['attacker_scores']) == r and len(game['defender_scores']) == r:
                if r < game.get('rounds_total', 3):
                    try:
                        await _send_round(context.bot, game)
                    except Exception:
                        pass
                else:
                    # محاسبه جمع و تعیین برنده، سپس اعلان با تاخیر
                    a_sum = sum(game['attacker_scores'])
                    d_sum = sum(game['defender_scores'])
                    game['winner'] = 'attacker' if a_sum > d_sum else 'defender' if d_sum > a_sum else 'tie_attacker'  # مساوی: برتری مهاجم
                    game['status'] = 'final'
                    game['result_announce_at'] = now + 30
                    game['final_attacker_sum'] = round(a_sum, 2)
                    game['final_defender_sum'] = round(d_sum, 2)
                    print(f"[DEBUG] Game {gid} finished, winner: {game['winner']}, scores: A={a_sum}, D={d_sum}, announce at: {game['result_announce_at']}")
        elif status == 'final':
            announce_at = game.get('result_announce_at') or 0
            if now >= announce_at:
                # اعلام نتیجه و اعمال اثر
                print(f"[DEBUG] Finalizing game {gid}, winner: {game.get('winner')}")
                try:
                    await _finalize_assassination_result(context, game)
                    print(f"[DEBUG] Game {gid} finalized successfully")
                except Exception as e:
                    print(f"[DEBUG] Error finalizing game {gid}: {e}")
                to_delete.append(gid)
    for gid in to_delete:
        utils.assassination_games.pop(gid, None)

async def _finalize_assassination_result(context, game):
    attacker_id = game['attacker_id']
    target_id = game['target_id']
    role_key = game['role']
    role_fa = {'general':'ژنرال','minister':'وزیر کشور','foreign':'وزیر خارجه','finance':'وزیر دارایی'}.get(role_key, role_key)
    target_country = utils.users.get(target_id, {}).get('country', 'نامشخص')
    attacker_country = utils.users.get(attacker_id, {}).get('country', 'نامشخص')
    winner = game.get('winner')
    # خلاصه امتیازها برای نمایش
    a_scores = game.get('attacker_scores', [])
    d_scores = game.get('defender_scores', [])
    a_sum = game.get('final_attacker_sum', sum(a_scores))
    d_sum = game.get('final_defender_sum', sum(d_scores))
    rounds_summary = '\n'.join([f"دور {i+1}: مهاجم {a_scores[i] if i < len(a_scores) else 0} - مدافع {d_scores[i] if i < len(d_scores) else 0}" for i in range(max(len(a_scores), len(d_scores)))])

    if winner in ['attacker', 'tie_attacker']:
        # موفقیت مهاجم
        sel = utils.users.get(target_id, {}).setdefault('selected_officials', {})
        official = sel.get(role_key, {'name': role_key, 'title': role_key})
        official_name = official.get('name', role_fa)
        official['alive'] = False
        official['assassinated_at_turn'] = utils.game_data.get('turn', 1)
        sel[role_key] = official
        susp = utils.users[target_id].setdefault('panel_suspensions', {})
        cur = utils.game_data.get('turn', 1)
        key_map = {'general':'strategy','minister':'country_status','foreign':'diplomacy','finance':'trade'}
        panel_key = key_map.get(role_key)
        if panel_key:
            susp[panel_key] = max(susp.get(panel_key, 0), cur+2)
        utils.save_users()
        try:
            await context.bot.send_message(chat_id=int(attacker_id), text=f'✅ نتیجه نهایی ترور: موفق.\n\n<blockquote>📈 امتیازها:\n{rounds_summary}\n\nمجموع مهاجم: {a_sum}\nمجموع مدافع: {d_sum}</blockquote>', parse_mode='HTML')
        except Exception:
            pass
        try:
            await context.bot.send_message(chat_id=int(target_id), text=f'🔪 عملیات ترور موفق بود. {role_fa} شما ترور شد.\n\n<blockquote>📈 امتیازها:\n{rounds_summary}\n\nمجموع مهاجم: {a_sum}\nمجموع مدافع: {d_sum}</blockquote>', parse_mode='HTML')
        except Exception:
            pass
        
        # ارسال خبر به کانال
        news_text = (
            f'🗞️ خبر فوری: گزارش‌ها حاکی از ترور {official_name}، {role_fa} {target_country} است.'
            f'\n\n🌍 جامعه جهانی به ابراز تاسف و تعزیت تسلیت می‌گوید به ملت شریف {target_country}.'
            f'\n\n<blockquote>📈 نتیجه مینی‌گیم (۳ دور):\n{rounds_summary}\n\nمجموع مهاجم: {a_sum}\nمجموع مدافع: {d_sum}</blockquote>'
        )
        try:
            await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo='https://t.me/TextEmpire_IR/95', caption=news_text, parse_mode='HTML')
        except Exception as e:
            print(f"[assassination] send_photo news failed: {e}")
            try:
                await context.bot.send_message(chat_id=NEWS_CHANNEL_ID, text=news_text, parse_mode='HTML')
            except Exception as e2:
                print(f"[assassination] send_message news fallback failed: {e2}")
    else:
        # شکست مهاجم و لو رفتن + روابط −50
        try:
            await context.bot.send_message(chat_id=int(attacker_id), text=f'❌ نتیجه نهایی ترور: شکست.\n\n<blockquote>📈 امتیازها:\n{rounds_summary}\n\nمجموع مهاجم: {a_sum}\nمجموع مدافع: {d_sum}</blockquote>', parse_mode='HTML')
        except Exception:
            pass
        try:
            await context.bot.send_message(chat_id=int(target_id), text=f'🛡️ تلاش برای ترور {role_fa} شما دفع شد.\n\n<blockquote>📈 امتیازها:\n{rounds_summary}\n\nمجموع مهاجم: {a_sum}\nمجموع مدافع: {d_sum}</blockquote>', parse_mode='HTML')
        except Exception:
            pass
        try:
            news_text = (
                f'📰 گزارش اطلاعاتی: تلاش ناکام {attacker_country} برای ترور {role_fa} در {target_country} افشا شد.'
                f'\n\n<blockquote>📈 نتیجه مینی‌گیم (۳ دور):\n{rounds_summary}\n\nمجموع مهاجم: {a_sum}\nمجموع مدافع: {d_sum}</blockquote>'
            )
            try:
                await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo='https://t.me/TextEmpire_IR/95', caption=news_text, parse_mode='HTML')
            except Exception as e:
                print(f"[assassination] send_photo news failed: {e}")
                try:
                    await context.bot.send_message(chat_id=NEWS_CHANNEL_ID, text=news_text, parse_mode='HTML')
                except Exception as e2:
                    print(f"[assassination] send_message news fallback failed: {e2}")
        except Exception as e:
            print(f"[assassination] news branch error: {e}")
        try:
            ar = utils.country_relations.setdefault(attacker_id, {})
            tr = utils.country_relations.setdefault(target_id, {})
            ar[target_id] = ar.get(target_id, 0) - 50
            tr[attacker_id] = tr.get(attacker_id, 0) - 50
            utils.save_country_relations()
            # اگر روابط دوطرفه به آستانه بسیار خصمانه رسید، جنگ خودکار اعلام شود
            if ar[target_id] <= -100 and tr[attacker_id] <= -100:
                user_country = attacker_country
                target_country_name = target_country
                wid = f"{user_country}->{target_country_name}"
                utils.war_declarations[wid] = {
                    'attacker': user_country,
                    'defender': target_country_name,
                    'type': 'auto_war',
                    'status': 'active',
                    'turn_declared': utils.game_data.get('turn', 1)
                }
                try:
                    from utils import save_war_declarations
                    save_war_declarations()
                except Exception:
                    pass
                # ارسال درخواست پناهندگی به 5 کشور تصادفی
                try:
                    from bot import send_refugee_requests_to_random_countries
                    await send_refugee_requests_to_random_countries(user_country, target_country_name, context)
                except Exception as e:
                    print(f"خطا در ارسال درخواست‌های پناهندگی: {e}")
                # پیام به کانال و طرفین
                try:
                    war_photo_id = "https://t.me/TextEmpire_IR/47"
                    news_text = (
                        f"🚨 <b>اعلان جنگ خودکار!</b>\n\nبه دلیل اقدامات خصمانه و لو رفتن عملیات، جنگ بین کشور {user_country} و {target_country_name} اعلام شد!"
                    )
                    await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=war_photo_id, caption=news_text, parse_mode='HTML')
                except Exception:
                    pass
                try:
                    await context.bot.send_message(chat_id=int(attacker_id), text=f"🚨 به دلیل لو رفتن عملیات و روابط بسیار خصمانه، جنگ با {target_country_name} به طور خودکار اعلام شد!")
                except Exception:
                    pass
                try:
                    await context.bot.send_message(chat_id=int(target_id), text=f"🚨 به دلیل لو رفتن عملیات و روابط بسیار خصمانه، جنگ با {user_country} به طور خودکار اعلام شد!")
                except Exception:
                    pass
        except Exception:
            pass

async def assassination_defend(query):
    user_id = str(query.from_user.id)
    game_id = query.data.replace('assassination_defend_', '')
    game = utils.assassination_games.get(game_id)
    if not game or game.get('status') != 'await_defender' or game.get('target_id') != user_id:
        await query.answer('درخواست نامعتبر یا منقضی.', show_alert=True)
        return
    # کسر هزینه از مدافع
    defender = utils.users.get(user_id, {})
    res = defender.setdefault('resources', {})
    if res.get('cash', 0) < 50_000_000 or res.get('special_forces', 0) < 2000:
        await query.answer('❌ منابع کافی برای مقابله ندارید (50M و 2000 نیروی ویژه).', show_alert=True)
        return
    res['cash'] -= 50_000_000
    res['special_forces'] -= 2000
    utils.save_users()
    game['defender_paid'] = True
    game['status'] = 'prep'
    await query.answer('✅ مقابله تایید شد. مینی‌گیم به‌زودی آغاز می‌شود.', show_alert=True)
    try:
        await query.edit_message_text('✅ مقابله تایید شد. آماده باشید؛ مینی‌گیم تا 1 دقیقه دیگر شروع می‌شود.')
    except Exception:
        pass
    await _start_prep_and_rounds(query.get_bot() if hasattr(query, 'get_bot') else query.bot, game)

def _dir_from_token(tok):
    return {'U':'⬆️','L':'⬅️','D':'⬇️','R':'➡️'}.get(tok)

async def assassination_input_handler(query):
    user_id = str(query.from_user.id)
    data = query.data
    print(f"[DEBUG] Input handler called: {data} by user {user_id}")
    
    # ass_input_{game_id}_{tok} یا ass_back_{game_id} یا ass_submit_{game_id}
    if data.startswith('ass_input_'):
        parts = data.split('_')
        if len(parts) != 4:
            await query.answer('داده نامعتبر.', show_alert=True)
            return
        _, gid, tok = parts[1], parts[2], parts[3]
        print(f"[DEBUG] Parsed: game_id={gid}, token={tok}")
        
        game = utils.assassination_games.get(gid)
        if not game:
            await query.answer('بازی یافت نشد.', show_alert=True)
            return
        if game.get('status') != 'round':
            await query.answer('بازی فعال نیست.', show_alert=True)
            return
            
        round_no = game.get('round', 0)
        key = 'attacker' if user_id == game['attacker_id'] else 'defender' if user_id == game['target_id'] else None
        if not key:
            await query.answer('مجوز ندارید.', show_alert=True)
            return
            
        entry = game[f'{key}_inputs'].setdefault(round_no, {'list': [], 'start': int(datetime.now().timestamp())})
        current = entry.get('list', [])
        if len(current) >= len(game['shared_sequences'][round_no-1]):
            await query.answer('به اندازه کافی وارد کرده‌اید. ارسال کنید.', show_alert=True)
            return
            
        ch = _dir_from_token(tok)
        if not ch:
            await query.answer('توکن نامعتبر.', show_alert=True)
            return
            
        current.append(ch)
        entry['list'] = current  # ذخیره تغییرات
        print(f"[DEBUG] Added {ch}, current list: {current}")
        
        kb = _build_input_keyboard(gid, current)
        await query.edit_message_text('◀️ وارد کنید: (30 ثانیه فرصت دارید)', reply_markup=kb)
        await query.answer(f'✅ {ch} اضافه شد')
    elif data.startswith('ass_back_'):
        gid = data.replace('ass_back_', '')
        game = utils.assassination_games.get(gid)
        if not game or game.get('status') != 'round':
            return
        round_no = game.get('round', 0)
        key = 'attacker' if user_id == game['attacker_id'] else 'defender' if user_id == game['target_id'] else None
        if not key:
            return
        entry = game[f'{key}_inputs'].setdefault(round_no, {'list': [], 'start': int(datetime.now().timestamp())})
        lst = entry.get('list', [])
        if lst:
            lst.pop()
        kb = _build_input_keyboard(gid, lst)
        await query.edit_message_text('◀️ وارد کنید:', reply_markup=kb)
    elif data.startswith('ass_submit_'):
        gid = data.replace('ass_submit_', '')
        game = utils.assassination_games.get(gid)
        if not game or game.get('status') != 'round':
            await query.answer('بازی فعال نیست.', show_alert=True)
            return
        round_no = game.get('round', 0)
        key = 'attacker' if user_id == game['attacker_id'] else 'defender' if user_id == game['target_id'] else None
        if not key:
            await query.answer('مجوز ندارید.', show_alert=True)
            return
        # محاسبه امتیاز
        entry = game[f'{key}_inputs'].get(round_no)
        if not entry:
            await query.answer('ورودی‌ای ثبت نشده.', show_alert=True)
            return
        inputs = entry.get('list', [])
        elapsed = max(0, int(datetime.now().timestamp()) - entry.get('start', int(datetime.now().timestamp())))
        seq = game['shared_sequences'][round_no-1]
        variant = game.get('round_variants', ['normal'])[round_no-1]
        correct, total, accuracy = _calc_accuracy(seq, inputs, variant)
        score = _score_sequence(seq, inputs, elapsed, variant)
        game[f'{key}_scores'].append(score)
        await query.edit_message_text(
            f'📊 امتیاز این دور شما: {score}\n'
            f'✅ درست‌ها: {correct}/{total} (دقت: {round(accuracy*100)}%)\n'
            f'⏱️ زمان: {elapsed} ثانیه'
        )
        # اگر هر دو طرف امتیاز این دور را دادند، جلو برو
        a_done = len(game['attacker_scores']) == round_no
        d_done = len(game['defender_scores']) == round_no
        if a_done and d_done:
            # اگر دور باقیست، دور بعد
            if round_no < game.get('rounds_total', 3):
                # استفاده از bot از خود query
                try:
                    bot_inst = query.get_bot() if hasattr(query, 'get_bot') else query.bot
                except Exception:
                    bot_inst = None
                if bot_inst:
                    await _send_round(bot_inst, game)
            else:
                # پایان بازی و زمان‌بندی اعلام نتیجه
                a_sum = sum(game['attacker_scores'])
                d_sum = sum(game['defender_scores'])
                game['winner'] = 'attacker' if a_sum > d_sum else 'defender' if d_sum > a_sum else 'tie_attacker'
                game['status'] = 'final'
                game['result_announce_at'] = int(datetime.now().timestamp()) + 30

# هندلر شروع بیانیه
async def start_statement(query, user_id):
    pending_statement[user_id] = True
    await query.edit_message_text('متن یا عکس بیانیه خود را ارسال کنید (می‌توانید فقط عکس یا فقط متن یا هر دو را ارسال کنید):')

# هندلر دریافت پیام بیانیه
async def handle_statement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = str(update.effective_user.id)
        if not pending_statement.get(user_id):
            return
        country = utils.users.get(user_id, {}).get('country', 'کشور ناشناس')
        has_photo = bool(update.message.photo)
        has_text = bool(hasattr(update.message, 'text') and update.message.text and update.message.text.strip())
        has_caption = bool(update.message.caption and update.message.caption.strip())

        # اگر هیچ عکس و هیچ متنی نبود
        if not has_photo and not has_text:
            await update.message.reply_text('لطفاً یک متن یا عکس به عنوان بیانیه ارسال کنید.')
            return

        # اگر عکس ارسال شده
        if has_photo:
            # اگر کپشن هم دارد، کپشن را به عنوان متن بیانیه استفاده کن
            caption = update.message.caption or ''
            text = f"📢 بیانیه از کشور: <b>{country}</b>\n\n{caption}"
            try:
                await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=update.message.photo[-1].file_id, caption=text, parse_mode='HTML')
                await update.message.reply_text('✅ بیانیه شما با موفقیت به کانال اخبار ارسال شد.\nhttps://t.me/TextEmpire_News')
            except Exception as e:
                print(f"خطا در ارسال عکس به کانال: {e}")
                await update.message.reply_text(f'❌ خطا در ارسال بیانیه: {str(e)}')
        # اگر فقط متن ارسال شده
        elif has_text:
            text = f"📢 بیانیه از کشور: <b>{country}</b>\n\n{(update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()}"
            try:
                await context.bot.send_message(chat_id=NEWS_CHANNEL_ID, text=text, parse_mode='HTML')
                await update.message.reply_text('✅ بیانیه شما با موفقیت به کانال اخبار ارسال شد.\nhttps://t.me/TextEmpire_News')
            except Exception as e:
                print(f"خطا در ارسال متن به کانال: {e}")
                await update.message.reply_text(f'❌ خطا در ارسال بیانیه: {str(e)}')
        
        pending_statement.pop(user_id, None)
    except Exception as e:
        print(f"خطا در handle_statement: {e}")
        await update.message.reply_text(f'❌ خطا در پردازش بیانیه: {str(e)}')
        pending_statement.pop(user_id, None)

async def show_courts_list_for_public(query):
    """نمایش لیست دادگاه‌های سازمان ملل برای کاربران عادی"""
    if not utils.un_courts:
        text = "📋 <b>لیست دادگاه‌های سازمان ملل</b>\n\n"
        text += "❌ <b>هیچ دادگاهی برنامه‌ریزی نشده است.</b>\n\n"
        text += "🏛️ دادگاه‌های جدید به محض برنامه‌ریزی در اینجا نمایش داده می‌شوند."
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='united_nations_access')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    text = "📋 <b>لیست دادگاه‌های سازمان ملل</b>\n\n"
    
    # نمایش دادگاه‌ها به ترتیب تاریخ ایجاد (جدیدترین اول)
    sorted_courts = sorted(utils.un_courts, key=lambda x: x['created_at'], reverse=True)
    
    for i, court in enumerate(sorted_courts[:10], 1):  # حداکثر ۱۰ دادگاه
        status_emoji = {
            'scheduled': '📅',
            'ongoing': '⚖️',
            'completed': '✅'
        }.get(court['status'], '❓')
        
        text += f"{i}. {status_emoji} <b>{court['topic']}</b>\n"
        text += f"   👥 شاکی: {court['plaintiff']}\n"
        text += f"   👤 متهم: {court['defendant']}\n"
        text += f"   ⏰ زمان: {court['time']}\n"
        text += f"   📍 محل: {court.get('location', 'نامشخص')}\n"
        text += f"   🏛️ وضعیت: {court['status']}\n\n"
    
    if len(sorted_courts) > 10:
        text += f"📄 <b>و {len(sorted_courts) - 10} دادگاه دیگر...</b>\n\n"
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='united_nations_access')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_send_president_callback(query):
    """ویزارد ارسال رییس‌جمهور به دادگاه با انتخاب اسکورت و ایجاد لینک دعوت تک‌نفره"""
    user_id = str(query.from_user.id)
    data = query.data
    # مرحله 1: انتخاب دادگاه
    if data == 'un_send_president':
        if not utils.un_courts:
            await query.answer('هیچ دادگاهی برنامه‌ریزی نشده است.', show_alert=True)
            return
        text = '🚀 <b>ارسال رییس‌جمهور به دادگاه</b>\n\nیک دادگاه را انتخاب کنید:'
        kb = []
        for c in sorted(utils.un_courts, key=lambda x: x['created_at'], reverse=True)[:10]:
            kb.append([InlineKeyboardButton(f"{c['topic']} — {c['time']} @ {c.get('location','-')}", callback_data=f"un_sp_select_{c['id']}")])
        kb.append([InlineKeyboardButton('🔙 بازگشت', callback_data='united_nations_access')])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        return
    # مرحله 2: انتخاب نوع اسکورت
    if data.startswith('un_sp_select_'):
        court_id = data.replace('un_sp_select_', '')
        utils.pending_send_president = {user_id: {'court_id': court_id}}
        kb = [
            [InlineKeyboardButton('🛡️ ارسال با اسکورت', callback_data=f'un_sp_escort_{court_id}')],
            [InlineKeyboardButton('🚶 ارسال بدون اسکورت (۱۰٪ حفاظت)', callback_data=f'un_sp_noescort_{court_id}')],
            [InlineKeyboardButton('🔙 بازگشت', callback_data='un_send_president')]
        ]
        await query.edit_message_text('نوع ارسال را انتخاب کنید:', reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        return
    # مرحله 3: انتخاب سطح حفاظت
    if data.startswith('un_sp_escort_'):
        court_id = data.replace('un_sp_escort_', '')
        kb = [
            [InlineKeyboardButton('🛡️ حفاظت ۲۰٪ — ۲۰M', callback_data=f'un_sp_prot_20_{court_id}')],
            [InlineKeyboardButton('🛡️ حفاظت ۴۰٪ — ۴۰M', callback_data=f'un_sp_prot_40_{court_id}')],
            [InlineKeyboardButton('🛡️ حفاظت ۸۰٪ — ۸۰M', callback_data=f'un_sp_prot_80_{court_id}')],
            [InlineKeyboardButton('🛡️ حفاظت ۱۰۰٪ — ۱۵۰M', callback_data=f'un_sp_prot_100_{court_id}')],
            [InlineKeyboardButton('🔙 بازگشت', callback_data='un_send_president')]
        ]
        await query.edit_message_text('سطح حفاظت را انتخاب کنید:', reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        return
    if data.startswith('un_sp_noescort_'):
        court_id = data.replace('un_sp_noescort_', '')
        await _finalize_send_president(query, user_id, court_id, protection=10)
        return
    if data.startswith('un_sp_prot_'):
        parts = data.split('_')
        # un_sp_prot_{pct}_{court}
        pct = int(parts[3])
        court_id = parts[4]
        await _finalize_send_president(query, user_id, court_id, protection=pct)
        return

async def _finalize_send_president(query, user_id: str, court_id: str, protection: int):
    # ذخیره حفاظت انتخابی روی کاربر
    u = utils.users.get(user_id, {})
    org = u.get('national_security_org') or {}
    org['president_protection'] = protection
    u['national_security_org'] = org
    utils.users[user_id] = u
    utils.save_users()
    # ثبت شرکت‌کننده برای این دادگاه
    try:
        if not hasattr(utils, 'court_attendees') or not isinstance(getattr(utils, 'court_attendees'), dict):
            utils.court_attendees = {}
        lst = utils.court_attendees.get(court_id) or []
        if user_id not in lst:
            lst.append(user_id)
        utils.court_attendees[court_id] = lst
        if hasattr(utils, 'save_un_data'):
            utils.save_un_data()
    except Exception:
        pass
    # ایجاد لینک دعوت تک‌نفره برای کاربر و یک لینک برای کاربر سازمان ملل
    try:
        group_id = getattr(utils, 'COURT_GROUP_ID', None)
        if not group_id:
            await query.answer('COURT_GROUP_ID تنظیم نشده است.', show_alert=True)
            return
        link_user = await query.bot.create_chat_invite_link(group_id, member_limit=1)
        link_un = await query.bot.create_chat_invite_link(group_id, member_limit=1)
        # ارسال لینک‌ها
        await query.bot.send_message(chat_id=int(user_id), text=f"🔗 لینک ورود به دادگاه (یک‌بارمصرف):\n{link_user.invite_link}")
        if utils.UN_ACTIVATED_USER:
            await query.bot.send_message(chat_id=int(utils.UN_ACTIVATED_USER), text=f"🔗 لینک ورود به دادگاه (یک‌بارمصرف):\n{link_un.invite_link}")
        await query.edit_message_text('✅ ثبت شد. لینک‌ها ارسال شدند.', parse_mode='HTML')
    except Exception as e:
        await query.answer(f'خطا در ایجاد لینک: {e}', show_alert=True)


# منوی سازمان ملل برای بازیکن‌های عادی
async def show_united_nations_access_menu(query):
    """نمایش منوی دسترسی به سازمان ملل برای بازیکن‌های عادی"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    country_name = user.get('country', 'کشور ناشناس')
    
    # بررسی اینکه آیا سازمان ملل فعال شده
    if not utils.UN_ACTIVATED_USER:
        text = f"🏛️ <b>سازمان ملل</b>\n\n"
        text += f"🌍 <b>کشور {country_name}</b>\n\n"
        text += "❌ <b>سازمان ملل هنوز فعال نشده است!</b>\n\n"
        text += "💡 <b>توضیحات:</b>\n"
        text += "▫️ سازمان ملل یک نهاد بین‌المللی برای مدیریت جهان است\n"
        text += "▫️ این نهاد می‌تواند قطعنامه صادر کند، تحریم اعمال کند\n"
        text += "▫️ دادگاه بین‌المللی برگزار کند و صلح را ترویج دهد\n"
        text += "▫️ در حال حاضر هیچ کاربری به عنوان سازمان ملل فعال نشده\n\n"
        text += "🔄 <b>لطفاً بعداً تلاش کنید</b>"
        
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت به منوی دیپلماسی', callback_data='diplomacy_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    # اگر سازمان ملل فعال شده
    text = f"🏛️ <b>سازمان ملل</b>\n\n"
    text += f"🌍 <b>کشور {country_name}</b>\n\n"
    text += "✅ <b>سازمان ملل فعال است!</b>\n\n"
    
    # تحلیل وزیر امور خارجه
    text += "💬 <b>تحلیل وزیر امور خارجه:</b>\n"
    text += "▫️ سازمان ملل در حال حاضر فعال است و توسط یک کاربر مدیریت می‌شود\n"
    text += "▫️ کشور شما می‌تواند در رای‌گیری‌های قطعنامه‌ها و تحریم‌ها شرکت کند\n"
    text += "▫️ هر کشور یک رای دارد و تصمیمات بر اساس اکثریت آرا گرفته می‌شود\n"
    text += "▫️ برای تصویب قطعنامه یا تحریم، حداقل 51% رای مثبت نیاز است\n\n"
    
    text += "💡 <b>قابلیت‌های موجود:</b>\n"
    text += "▫️ 📜 مشاهده قطعنامه‌های صادر شده\n"
    text += "▫️ 🚫 مشاهده تحریم‌های اعمال شده\n"
    text += "▫️ ⚖️ مشاهده دادگاه‌های بین‌المللی\n"
    text += "▫️ 👮‍♀️ مشاهده نظارت و گزارش‌ها\n"
    text += "▫️ 🏆 مشاهده جوایز صلح\n"
    text += "▫️ 🗳️ صندوق رای (رای‌گیری در قطعنامه‌ها و تحریم‌ها)\n\n"
    text += "🎯 <b>انتخاب کنید:</b>"
    
    keyboard = [
        [InlineKeyboardButton('📜 مشاهده قطعنامه‌ها', callback_data='un_view_resolutions'), InlineKeyboardButton('🚫 مشاهده تحریم‌ها', callback_data='un_view_sanctions')],
        [InlineKeyboardButton('⚖️ مشاهده دادگاه‌ها', callback_data='un_view_courts'), InlineKeyboardButton('👮‍♀️ مشاهده نظارت', callback_data='un_view_monitoring')],
        [InlineKeyboardButton('🏆 مشاهده جوایز صلح', callback_data='un_view_peace_prizes'), InlineKeyboardButton('🗳️ صندوق رای', callback_data='un_voting_booth')],
        [InlineKeyboardButton('📝 تنظیم شکایت‌نامه', callback_data='un_file_complaint')],
        [InlineKeyboardButton('🚀 ارسال رییس جمهور به دادگاه', callback_data='un_send_president')],
        [InlineKeyboardButton('🔙 بازگشت به منوی دیپلماسی', callback_data='diplomacy_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# منوی صندوق رای سازمان ملل
async def show_united_nations_voting_booth(query):
    """نمایش صندوق رای سازمان ملل"""
    # لودینگ کوتاه هنگام باز شدن صندوق رای
    try:
        from bot import show_loading_animation
        # context از bot.py پاس داده می‌شود، اینجا صرفاً تابع موجود باشد
    except Exception:
        pass
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    country_name = user.get('country', 'کشور ناشناس')
    
    # بررسی اینکه آیا سازمان ملل فعال شده
    if not utils.UN_ACTIVATED_USER:
        await query.edit_message_text(
            "❌ <b>سازمان ملل فعال نشده است!</b>\n\n"
            "لطفاً ابتدا سازمان ملل را فعال کنید.",
            parse_mode='HTML'
        )
        return
    
    # فهرست قطعنامه‌های در وضعیت رای‌گیری
    from utils import un_resolutions
    voting = [r for r in un_resolutions if r.get('status') == 'voting']
    text = f"🗳️ <b>صندوق رای سازمان ملل</b>\n\n"
    text += f"🌍 <b>کشور {country_name}</b>\n\n"
    if not voting:
        text += "📋 <b>وضعیت رای‌گیری:</b>\n"
        text += "✅ هیچ رای‌گیری فعالی در حال حاضر وجود ندارد\n\n"
        text += "💡 <b>توضیحات سیستم رای‌گیری:</b>\n"
        text += "▫️ هر کشور یک رای دارد\n"
        text += "▫️ برای تصویب: حداقل 51% رای مثبت نیاز است\n"
        text += "▫️ اگر رای ممتنع بیشتر باشد: رای‌گیری مجدد انجام می‌شود\n"
        text += "▫️ اگر رای منفی بیشتر باشد: قطعنامه/تحریم منحل می‌شود\n\n"
        keyboard = [[InlineKeyboardButton('🔙 بازگشت به منوی سازمان ملل', callback_data='united_nations_access')]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return
    text += "📋 <b>رای‌گیری‌های فعال:</b>\n"
    keyboard = []
    for r in voting:
        num = r.get('number')
        keyboard.append([InlineKeyboardButton(f"قطعنامه #{num}", callback_data=f"un_vote_view_{num}")])
    keyboard.append([InlineKeyboardButton('🔙 بازگشت به منوی سازمان ملل', callback_data='united_nations_access')])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_resolution_preview_for_voting(query, number: int):
    from utils import un_resolutions
    r = next((x for x in un_resolutions if x.get('number') == number), None)
    if not r:
        await query.answer('قطعنامه یافت نشد.', show_alert=True)
        return
    
    user_id = str(query.from_user.id)
    votes = r.get('votes', {})
    user_vote = votes.get(user_id)
    
    kind = r.get('sanction_kind')
    main_clause = f"اعمال تحریم {('اقتصادی' if kind=='economic' else 'نظامی' if kind=='military' else 'دیپلماتیک')} علیه {r.get('target_country')}"
    extras = "ایجاد سازوکار نظارت، بازبینی دوره‌ای و گزارش‌دهی به شورای امنیت"
    
    # آمار آرا
    total_players = sum(1 for u in utils.users.values() if u.get('activated'))
    yes = sum(1 for v in votes.values() if v == 'yes')
    no = sum(1 for v in votes.values() if v == 'no')
    abstain = sum(1 for v in votes.values() if v == 'abstain')
    
    draft_text = (
        f"📜 <b>قطعنامه شماره {number}</b>\n"
        "شورای امنیت سازمان ملل متحد،\n\n"
        f"با توجه به {r.get('reason')}،\n"
        f"با ابراز نگرانی نسبت به {r.get('concern')}،\n"
        f"با تأکید بر ضرورت {r.get('necessity')}،\n\n"
        "تصمیم می‌گیرد:\n\n"
        f"1. {main_clause}\n"
        f"2. {extras}\n"
        "3. این قطعنامه لازم‌الاجراست.\n\n"
        f"📊 <b>وضعیت آرا ({len(votes)}/{total_players}):</b>\n"
        f"✅ بله: {yes} ({round((yes/max(1,total_players))*100, 1)}%)\n"
        f"❌ خیر: {no} ({round((no/max(1,total_players))*100, 1)}%)\n"
        f"⚪ ممتنع: {abstain} ({round((abstain/max(1,total_players))*100, 1)}%)"
    )
    
    if user_vote:
        draft_text += f"\n\n🎯 <b>رای شما:</b> {'✅ بله' if user_vote == 'yes' else '❌ خیر' if user_vote == 'no' else '⚪ ممتنع'}"
    
    keyboard = []
    if not user_vote:
        keyboard.extend([
            [InlineKeyboardButton('✅ بله', callback_data=f'un_vote_yes_{number}')],
            [InlineKeyboardButton('⚪ ممتنع', callback_data=f'un_vote_abstain_{number}')],
            [InlineKeyboardButton('❌ خیر', callback_data=f'un_vote_no_{number}')]
        ])
    else:
        keyboard.append([InlineKeyboardButton('🎯 شما قبلاً رای داده‌اید', callback_data='no_action')])
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='un_voting_booth')])
    await query.edit_message_text(draft_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def handle_vote_action(query, action: str, number: int, context):
    from utils import un_resolutions, save_un_data
    user_id = str(query.from_user.id)
    # فقط کاربران فعال کشور حق رای دارند
    if user_id not in utils.users or not utils.users[user_id].get('activated'):
        await query.answer('فقط کشورهای فعال می‌توانند رای دهند.', show_alert=True)
        return
    r = next((x for x in un_resolutions if x.get('number') == number), None)
    if not r or r.get('status') != 'voting':
        await query.answer('رای‌گیری فعال نیست.', show_alert=True)
        return
    votes = r.setdefault('votes', {})
    # بررسی اینکه آیا کاربر قبلاً رای داده است
    if user_id in votes:
        await query.answer('شما قبلاً به این قطعنامه رای داده‌اید!', show_alert=True)
        return
    # ثبت رای
    if action == 'yes':
        votes[user_id] = 'yes'
    elif action == 'no':
        votes[user_id] = 'no'
    else:
        votes[user_id] = 'abstain'
    save_un_data()
    # بروزرسانی شمارش زودهنگام
    r['tally'] = {
        'yes': sum(1 for v in votes.values() if v == 'yes'),
        'no': sum(1 for v in votes.values() if v == 'no'),
        'abstain': sum(1 for v in votes.values() if v == 'abstain'),
    }
    save_un_data()
    # بروزرسانی پیام کانال به صورت زنده
    try:
        from united_nations import update_resolution_channel_message
        await update_resolution_channel_message(number)
    except Exception:
        pass
    # اگر همه رای دادند، نتیجه‌گیری شود (فراخوانی تابع finalize در united_nations)
    try:
        from united_nations import finalize_resolution_if_complete
        await finalize_resolution_if_complete(number, context)
    except Exception:
        pass
    await query.answer('رای شما ثبت شد.', show_alert=True)
    # بازگشت به پیش‌نمایش با آمار به‌روز
    await show_resolution_preview_for_voting(query, number)

def register_voting_callbacks_in_bot(button_handler):
    """Helper for bot.py to route voting callbacks without circular heavy imports"""
    pass

############################################
# شکایت‌نامه چندمرحله‌ای سازمان ملل (Wizard)
############################################

def _complaint_reset(user_id: str):
    utils.pending_un_complaint[user_id] = {
        'step': 'complainant',
        'complainant': utils.users.get(user_id, {}).get('country', ''),
        'defendant': None,
        'type': None,
        'short': None,
        'details': None,
        'remedy': None,
        'attachment': None
    }
    utils.save_un_data()


async def start_un_complaint(query):
    """شروع ویزارد تنظیم شکایت‌نامه (مرحله ۱: شاکی)"""
    user_id = str(query.from_user.id)
    _complaint_reset(user_id)
    text = (
        "📝 <b>مراحل تکمیل شکایت‌نامه به سازمان ملل</b>\n\n"
        "۱) معرفی کشور شاکی\n"
        "(پیش‌فرض روی کشور شما تنظیم می‌شود)."
    )
    kb = [[InlineKeyboardButton('✅ تایید و ادامه', callback_data='un_comp_next_defendant')],
          [InlineKeyboardButton('🔙 بازگشت', callback_data='united_nations_access')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')


async def handle_un_complaint_callback(query):
    user_id = str(query.from_user.id)
    data = query.data
    pending = utils.pending_un_complaint.get(user_id)
    if not pending:
        _complaint_reset(user_id)
        pending = utils.pending_un_complaint.get(user_id)

    # مرحله ۲: انتخاب متهم
    if data == 'un_comp_next_defendant':
        countries = []
        for uid, u in utils.users.items():
            if u.get('activated') and u.get('country') and uid != user_id:
                countries.append(u.get('country'))
        countries = sorted(set(countries))
        text = (
            "۲) انتخاب کشور یا نهاد متهم\n\n"
            "❓ <b>شکایت شما علیه کدام کشور یا نهاد است؟</b>"
        )
        keyboard = []
        row = []
        for c in countries:
            row.append(InlineKeyboardButton(c, callback_data=f'un_comp_def_{hash(c) & 0xfffffff}'))
            if len(row) == 2:
                keyboard.append(row); row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton('✍️ وارد کردن نام نهاد به صورت دستی', callback_data='un_comp_def_custom')])
        keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='united_nations_access')])
        # نگاشت هش به نام کشور در وضعیت موقت
        map_ = {}
        for c in countries:
            map_[str(hash(c) & 0xfffffff)] = c
        pending['def_map'] = map_
        pending['step'] = 'defendant'
        utils.pending_un_complaint[user_id] = pending
        utils.save_un_data()
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        return

    if data.startswith('un_comp_def_'):
        key = data.replace('un_comp_def_', '')
        pending = utils.pending_un_complaint.get(user_id, {})
        defendant = pending.get('def_map', {}).get(key)
        if defendant:
            pending['defendant'] = defendant
            pending['step'] = 'type'
            utils.pending_un_complaint[user_id] = pending
            utils.save_un_data()
            # مرحله ۳: نوع شکایت
            text = (
                "۳) نوع شکایت\n\n❓ <b>موضوع اصلی شکایت چیست؟</b>"
            )
            kb = [
                [InlineKeyboardButton('🚫 تجاوز نظامی', callback_data='un_comp_type_military')],
                [InlineKeyboardButton('🛑 نقض حقوق بشر', callback_data='un_comp_type_hr')],
                [InlineKeyboardButton('💰 تحریم غیرقانونی', callback_data='un_comp_type_sanction')],
                [InlineKeyboardButton('🧭 دخالت در امور داخلی', callback_data='un_comp_type_interfere')],
                [InlineKeyboardButton('⚖️ سایر موارد', callback_data='un_comp_type_other')],
                [InlineKeyboardButton('🔙 بازگشت', callback_data='united_nations_access')],
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
            return

    if data == 'un_comp_def_custom':
        pending['step'] = 'def_custom'
        utils.pending_un_complaint[user_id] = pending
        utils.save_un_data()
        await query.edit_message_text('✍️ نام نهاد/کشور متهم را ارسال کنید:', parse_mode='HTML')
        return

    if data.startswith('un_comp_type_'):
        ctype = data.replace('un_comp_type_', '')
        pending['type'] = ctype
        pending['step'] = 'short'
        utils.pending_un_complaint[user_id] = pending
        utils.save_un_data()
        await query.edit_message_text('۴) شرح کوتاه حادثه:\n❓ در یک جمله کوتاه، علت شکایت را توضیح دهید.\nمثال: «حمله نظامی به مرزهای شمالی کشور»', parse_mode='HTML')
        return

    if data == 'un_comp_remedy_options':
        # مرحله ۶: خواسته شاکی (گزینه‌ها)
        text = '۶) خواسته شاکی:\n❓ انتظار شما از سازمان ملل چیست؟'
        kb = [
            [InlineKeyboardButton('صدور قطعنامه محکومیت', callback_data='un_comp_remedy_resolution')],
            [InlineKeyboardButton('اعمال تحریم علیه متهم', callback_data='un_comp_remedy_sanction')],
            [InlineKeyboardButton('میانجی‌گری و گفت‌وگو', callback_data='un_comp_remedy_mediation')],
            [InlineKeyboardButton('سایر اقدامات (متن باز)', callback_data='un_comp_remedy_other')],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        return

    if data.startswith('un_comp_remedy_'):
        r = data.replace('un_comp_remedy_', '')
        if r == 'other':
            pending['step'] = 'remedy_other'
            utils.pending_un_complaint[user_id] = pending
            utils.save_un_data()
            await query.edit_message_text('متن خواسته خود را ارسال کنید:', parse_mode='HTML')
            return
        remedies = {
            'resolution': 'صدور قطعنامه محکومیت',
            'sanction': 'اعمال تحریم علیه متهم',
            'mediation': 'میانجی‌گری و گفت‌وگو',
        }
        pending['remedy'] = remedies.get(r, r)
        pending['step'] = 'attach_ask'
        utils.pending_un_complaint[user_id] = pending
        utils.save_un_data()
        kb = [[InlineKeyboardButton('بله، ضمیمه می‌کنم', callback_data='un_comp_attach_yes')],
              [InlineKeyboardButton('خیر', callback_data='un_comp_attach_no')]]
        await query.edit_message_text('۷) ضمیمه مدرک (اختیاری)\n❓ آیا می‌خواهید سند یا مدرکی ضمیمه کنید؟', reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        return

    if data == 'un_comp_attach_yes':
        pending['step'] = 'attach'
        utils.pending_un_complaint[user_id] = pending
        utils.save_un_data()
        await query.edit_message_text('لطفاً فایل (عکس/سند) یا یک متن کوتاه به عنوان مدرک ارسال کنید:', parse_mode='HTML')
        return
    if data == 'un_comp_attach_no':
        pending['attachment'] = None
        pending['step'] = 'finalize'
        utils.pending_un_complaint[user_id] = pending
        utils.save_un_data()
        await _finalize_complaint(query, user_id)
        return


async def handle_un_complaint_message(update, context):
    """پردازش ورودی‌های متنی/فایل در مراحل مختلف شکایت"""
    user_id = str(update.effective_user.id)
    p = utils.pending_un_complaint.get(user_id)
    if not p:
        return
    step = p.get('step')

    if step == 'def_custom':
        p['defendant'] = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
        p['step'] = 'type'
        utils.pending_un_complaint[user_id] = p
        utils.save_un_data()
        # نمایش نوع شکایت
        kb = [
            [InlineKeyboardButton('🚫 تجاوز نظامی', callback_data='un_comp_type_military')],
            [InlineKeyboardButton('🛑 نقض حقوق بشر', callback_data='un_comp_type_hr')],
            [InlineKeyboardButton('💰 تحریم غیرقانونی', callback_data='un_comp_type_sanction')],
            [InlineKeyboardButton('🧭 دخالت در امور داخلی', callback_data='un_comp_type_interfere')],
            [InlineKeyboardButton('⚖️ سایر موارد', callback_data='un_comp_type_other')],
        ]
        await update.message.reply_text('۳) نوع شکایت را انتخاب کنید:', reply_markup=InlineKeyboardMarkup(kb))
        return

    if step == 'short':
        p['short'] = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
        if not p['short']:
            await update.message.reply_text('❌ شرح کوتاه معتبر نیست. دوباره ارسال کنید.')
            return
        p['step'] = 'details'
        utils.pending_un_complaint[user_id] = p
        utils.save_un_data()
        await update.message.reply_text('۵) جزئیات شکایت (حداکثر ۵۰۰ کاراکتر) را ارسال کنید:')
        return

    if step == 'details':
        text = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
        if len(text) > 500:
            await update.message.reply_text('❌ متن بیش از ۵۰۰ کاراکتر است. لطفاً کوتاه‌تر بنویسید.')
            return
        p['details'] = text
        p['step'] = 'remedy'
        utils.pending_un_complaint[user_id] = p
        utils.save_un_data()
        kb = [[InlineKeyboardButton('انتخاب از گزینه‌ها', callback_data='un_comp_remedy_options')]]
        await update.message.reply_text('۶) خواسته شاکی: از گزینه‌ها انتخاب کنید یا «سایر اقدامات» را وارد نمایید.', reply_markup=InlineKeyboardMarkup(kb))
        return

    if step == 'remedy_other':
        p['remedy'] = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
        p['step'] = 'attach_ask'
        utils.pending_un_complaint[user_id] = p
        utils.save_un_data()
        kb = [[InlineKeyboardButton('بله، ضمیمه می‌کنم', callback_data='un_comp_attach_yes')],
              [InlineKeyboardButton('خیر', callback_data='un_comp_attach_no')]]
        await update.message.reply_text('۷) ضمیمه مدرک (اختیاری)\n❓ آیا می‌خواهید سند یا مدرکی ضمیمه کنید؟', reply_markup=InlineKeyboardMarkup(kb))
        return

    if step == 'attach':
        # دریافت فایل یا متن کوتاه
        attach = None
        if hasattr(update.message, 'document') and update.message.document:
            attach = {'type': 'document', 'file_id': update.message.document.file_id}
        elif hasattr(update.message, 'photo') and update.message.photo:
            attach = {'type': 'photo', 'file_id': update.message.photo[-1].file_id}
        else:
            attach = {'type': 'text', 'text': (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()}
        p['attachment'] = attach
        p['step'] = 'finalize'
        utils.pending_un_complaint[user_id] = p
        utils.save_un_data()
        # نهایی‌سازی
        await _finalize_complaint(update.message, user_id)
        return


async def _finalize_complaint(target, user_id: str):
    import time
    from uuid import uuid4
    p = utils.pending_un_complaint.get(user_id, {})
    complaint = {
        'id': str(uuid4())[:8],
        'from_user_id': user_id,
        'from_country': utils.users.get(user_id, {}).get('country', 'نامشخص'),
        'defendant': p.get('defendant'),
        'type': p.get('type'),
        'short': p.get('short'),
        'details': p.get('details'),
        'remedy': p.get('remedy'),
        'attachment': p.get('attachment'),
        'status': 'submitted',
        'created_turn': utils.game_data.get('turn', 1),
        'created_at': int(time.time())
    }
    utils.un_complaints.append(complaint)
    utils.pending_un_complaint.pop(user_id, None)
    utils.save_un_data()

    # اطلاع به کاربر
    try:
        await target.reply_text('✅ شکایت‌نامه شما ثبت شد و برای سازمان ملل ارسال گردید. منتظر بررسی باشید.', parse_mode='HTML')
    except Exception:
        await target.edit_message_text('✅ شکایت‌نامه شما ثبت شد و برای سازمان ملل ارسال گردید. منتظر بررسی باشید.', parse_mode='HTML')

    # اطلاع به کاربر سازمان ملل (به همراه ارسال مدرک در صورت وجود)
    try:
        if utils.UN_ACTIVATED_USER:
            from telegram import Bot
            bot = Bot(token=utils.BOT_TOKEN)
            preview = (
                "📥 <b>شکایت‌نامه جدید</b>\n\n"
                f"👤 کشور فرستنده: {complaint['from_country']}\n"
                f"🆚 متهم: {complaint.get('defendant','-')}\n"
                f"🗂️ نوع: {complaint.get('type','-')}\n"
                f"🆔 شناسه: {complaint['id']}\n"
                f"🕒 دور: {complaint['created_turn']}\n\n"
                f"📌 شرح کوتاه: {complaint.get('short','-')}\n\n"
                f"📝 جزئیات:\n{complaint.get('details','-')}"
            )
            kb = InlineKeyboardMarkup([[InlineKeyboardButton('🔙 بازگشت', callback_data='un_main')]])
            await bot.send_message(chat_id=int(utils.UN_ACTIVATED_USER), text=preview, parse_mode='HTML', reply_markup=kb)

            attach = complaint.get('attachment') or {}
            attach_type = attach.get('type')
            # ارسال مدرک ضمیمه در پیام جداگانه
            if attach_type == 'photo' and attach.get('file_id'):
                caption = f"🧾 مدرک شکایت {complaint['id']}"
                try:
                    await bot.send_photo(chat_id=int(utils.UN_ACTIVATED_USER), photo=attach['file_id'], caption=caption)
                except Exception:
                    pass
            elif attach_type == 'document' and attach.get('file_id'):
                caption = f"🧾 مدرک شکایت {complaint['id']}"
                try:
                    await bot.send_document(chat_id=int(utils.UN_ACTIVATED_USER), document=attach['file_id'], caption=caption)
                except Exception:
                    pass
            elif attach_type == 'text' and attach.get('text'):
                try:
                    await bot.send_message(chat_id=int(utils.UN_ACTIVATED_USER), text=f"🧾 مدرک متنی شکایت {complaint['id']}:\n{attach['text']}")
                except Exception:
                    pass
    except Exception as e:
        print(f"[UN COMPLAINT] notify UN error: {e}")

# ==================== سیستم تحریم ====================

from economy import _strip_flags_and_normalize

def _get_sanctions_for_country(country_name: str):
    """لیست تحریم‌ها با درنظرگرفتن کلید نرمال‌سازی‌شده و قدیمی."""
    norm = _strip_flags_and_normalize(country_name)
    current = utils.sanctions.get(norm) or utils.sanctions.get(country_name, [])
    return list(dict.fromkeys(current)) if current else []

def _resolve_display_country(norm_or_name: str):
    """برگرداندن نام کشور با پرچم در صورت وجود، بر اساس نرمال‌سازی."""
    target_norm = _strip_flags_and_normalize(norm_or_name)
    for _, ud in utils.users.items():
        c = ud.get('country')
        if c and _strip_flags_and_normalize(c) == target_norm:
            return c
    return norm_or_name

async def show_sanctions_menu(query):
    """نمایش منوی تحریم"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    country_name = user.get('country', 'کشور ناشناس')
    
    text = f"🚫 <b>منوی تحریم کشور {country_name}</b>\n\n"
    text += "🌍 در این بخش می‌توانید کشورهای دیگر را تحریم کنید یا تحریم‌ها را لغو کنید.\n\n"
    text += "⚠️ <b>تأثیرات تحریم:</b>\n"
    text += "• کشور تحریم شده نمی‌تواند از شما خرید کند\n"
    text += "• کشور تحریم شده نمی‌تواند سهام شرکت‌های شما را بخرد\n"
    text += "• سهام‌های موجود کشور تحریم شده در شرکت‌های شما فریز می‌شود\n\n"
    
    # نمایش تحریم‌های فعلی
    current_sanctions = _get_sanctions_for_country(country_name)
    if current_sanctions:
        text += f"🚫 <b>تحریم‌های فعلی شما:</b>\n"
        for target in current_sanctions:
            text += f"• {_resolve_display_country(target)}\n"
        text += "\n"
    
    keyboard = [
        [InlineKeyboardButton('🚫 تحریم کشورها', callback_data='sanction_countries')],
        [InlineKeyboardButton('✅ لغو تحریم', callback_data='remove_sanctions')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='diplomacy_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_sanction_countries_menu(query):
    """نمایش لیست کشورها برای تحریم"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    sanctioning_country = user.get('country', 'کشور ناشناس')
    
    # دریافت لیست کشورهای فعال
    available_countries = []
    for uid, user_data in utils.users.items():
        if user_data.get('activated') and user_data.get('country') != sanctioning_country:
            available_countries.append(user_data.get('country'))
    
    if not available_countries:
        text = "❌ هیچ کشور فعالی برای تحریم وجود ندارد."
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='sanctions_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    text = f"🚫 <b>انتخاب کشور برای تحریم</b>\n\n"
    text += f"🌍 کشور {sanctioning_country} می‌خواهد کدام کشور را تحریم کند؟\n\n"
    
    # ایجاد دکمه‌های دو ستونی
    keyboard = []
    row = []
    
    sanctioned_norm = { _strip_flags_and_normalize(c) for c in _get_sanctions_for_country(sanctioning_country) }
    
    for country in available_countries:
        # بررسی اینکه آیا این کشور قبلاً تحریم شده
        target_norm = _strip_flags_and_normalize(country)
        if target_norm in sanctioned_norm:
            button_text = f"🚫 {country} (تحریم شده)"
            callback_data = f'sanction_already_{country}'
        else:
            button_text = f"🌍 {country}"
            callback_data = f'sanction_target_{country}'
        
        row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:  # اضافه کردن ردیف آخر اگر کامل نباشد
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='sanctions_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_sanction_confirmation(query, target_country):
    """نمایش تأیید تحریم"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    sanctioning_country = user.get('country', 'کشور ناشناس')
    
    text = f"⚠️ <b>تأیید تحریم</b>\n\n"
    text += f"🚫 کشور {sanctioning_country} می‌خواهد کشور {target_country} را تحریم کند.\n\n"
    text += "🔴 <b>تأثیرات تحریم:</b>\n"
    text += f"• کشور {target_country} نمی‌تواند از {sanctioning_country} خرید کند\n"
    text += f"• کشور {target_country} نمی‌تواند سهام شرکت‌های {sanctioning_country} را بخرد\n"
    text += f"• سهام‌های موجود {target_country} در شرکت‌های {sanctioning_country} فریز می‌شود\n\n"
    text += "⚠️ <b>هشدار:</b> این عمل ممکن است روابط دیپلماتیک را تیره کند.\n\n"
    text += "آیا مطمئن هستید؟"
    
    # ذخیره وضعیت تحریم
    utils.pending_sanction[user_id] = {'target_country': target_country, 'step': 'confirm'}
    utils.save_un_data()
    
    keyboard = [
        [InlineKeyboardButton('✅ تأیید تحریم', callback_data=f'sanction_confirm_{target_country}')],
        [InlineKeyboardButton('❌ لغو', callback_data='sanction_countries')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def execute_sanction(query, target_country):
    """اجرای تحریم"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    sanctioning_country = user.get('country', 'کشور ناشناس')
    
    # بررسی مصونیت تحریم کشور هدف
    target_user_id = None
    for uid, user_data in utils.users.items():
        if user_data.get('country') == target_country and user_data.get('activated'):
            target_user_id = uid
            break
    
    if target_user_id:
        try:
            from bot import is_user_sanction_immune
            if is_user_sanction_immune(target_user_id):
                text = f"❌ <b>تحریم ناموفق!</b>\n\n"
                text += f"🛡️ کشور {target_country} از تحریم‌ها مصون است!\n"
                text += "این کشور توافق پشت پرده منعقد کرده و نمی‌تواند تحریم شود."
                
                keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='sanctions_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
                return
        except:
            pass
    
    # نرمال‌سازی نام‌های کشور برای ذخیره
    from economy import _strip_flags_and_normalize
    sanctioning_normalized = _strip_flags_and_normalize(sanctioning_country)
    target_normalized = _strip_flags_and_normalize(target_country)
    
    # اضافه کردن تحریم با نام‌های نرمال‌سازی شده
    if sanctioning_normalized not in utils.sanctions:
        utils.sanctions[sanctioning_normalized] = []
    
    if target_normalized not in utils.sanctions[sanctioning_normalized]:
        utils.sanctions[sanctioning_normalized].append(target_normalized)
    
    # پاک کردن وضعیت موقت
    utils.pending_sanction.pop(user_id, None)
    utils.save_un_data()
    
    # فریز کردن سهام‌های موجود
    await freeze_target_country_stocks(sanctioning_country, target_country)
    
    text = f"✅ <b>تحریم اعمال شد!</b>\n\n"
    text += f"🚫 کشور {target_country} توسط {sanctioning_country} تحریم شد.\n\n"
    text += "🔴 <b>تأثیرات:</b>\n"
    text += f"• {target_country} نمی‌تواند از {sanctioning_country} خرید کند\n"
    text += f"• {target_country} نمی‌تواند سهام شرکت‌های {sanctioning_country} را بخرد\n"
    text += f"• سهام‌های موجود {target_country} در شرکت‌های {sanctioning_country} فریز شد\n\n"
    text += "📢 این تحریم در کانال اخبار اعلام خواهد شد."
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='sanctions_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    # ارسال پیام به کاربر تحریم شده
    await notify_sanctioned_user(sanctioning_country, target_country, bot_client=query.bot)
    
    # اعلام در کانال اخبار
    await announce_sanction_in_news(sanctioning_country, target_country, bot_client=query.bot)

async def show_remove_sanctions_menu(query):
    """نمایش منوی لغو تحریم"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    sanctioning_country = user.get('country', 'کشور ناشناس')
    
    current_sanctions = _get_sanctions_for_country(sanctioning_country)
    
    if not current_sanctions:
        text = "✅ شما هیچ تحریمی اعمال نکرده‌اید."
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='sanctions_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    text = f"✅ <b>لغو تحریم</b>\n\n"
    text += f"🌍 کشور {sanctioning_country} می‌خواهد تحریم کدام کشور را لغو کند؟\n\n"
    
    # ایجاد دکمه‌های دو ستونی
    keyboard = []
    row = []
    
    for target_country in current_sanctions:
        target_display = _resolve_display_country(target_country)
        button_text = f"🚫 {target_display}"
        callback_data = f'remove_sanction_{target_display}'
        
        row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:  # اضافه کردن ردیف آخر اگر کامل نباشد
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='sanctions_menu')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def remove_sanction(query, target_country):
    """لغو تحریم"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    sanctioning_country = user.get('country', 'کشور ناشناس')
    
    # نرمال‌سازی نام‌های کشور برای حذف
    from economy import _strip_flags_and_normalize
    sanctioning_normalized = _strip_flags_and_normalize(sanctioning_country)
    target_normalized = _strip_flags_and_normalize(target_country)
    
    # حذف تحریم با نام‌های نرمال‌سازی شده
    if sanctioning_normalized in utils.sanctions and target_normalized in utils.sanctions[sanctioning_normalized]:
        utils.sanctions[sanctioning_normalized].remove(target_normalized)
        
        # اگر لیست خالی شد، کلید را حذف کن
        if not utils.sanctions[sanctioning_normalized]:
            del utils.sanctions[sanctioning_normalized]
    
    # حذف تحریم با نام‌های اصلی (برای سازگاری با داده‌های قدیمی)
    if sanctioning_country in utils.sanctions and target_country in utils.sanctions[sanctioning_country]:
        utils.sanctions[sanctioning_country].remove(target_country)
        
        # اگر لیست خالی شد، کلید را حذف کن
        if not utils.sanctions[sanctioning_country]:
            del utils.sanctions[sanctioning_country]
    
    utils.save_un_data()
    
    # آزاد کردن سهام‌های فریز شده
    await unfreeze_target_country_stocks(sanctioning_country, target_country)
    
    text = f"✅ <b>تحریم لغو شد!</b>\n\n"
    text += f"🌍 تحریم کشور {target_country} توسط {sanctioning_country} لغو شد.\n\n"
    text += "🟢 <b>تأثیرات:</b>\n"
    text += f"• {target_country} حالا می‌تواند از {sanctioning_country} خرید کند\n"
    text += f"• {target_country} می‌تواند سهام شرکت‌های {sanctioning_country} را بخرد\n"
    text += f"• سهام‌های {target_country} در شرکت‌های {sanctioning_country} آزاد شد\n\n"
    text += "📢 لغو تحریم در کانال اخبار اعلام خواهد شد."
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='sanctions_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    # ارسال پیام به کاربر آزاد شده از تحریم
    await notify_sanction_lifted_user(sanctioning_country, target_country, bot_client=query.bot)
    
    # اعلام در کانال اخبار
    await announce_sanction_removal_in_news(sanctioning_country, target_country, bot_client=query.bot)

async def freeze_target_country_stocks(sanctioning_country, target_country):
    """فریز کردن سهام‌های کشور تحریم شده"""
    # پیدا کردن کاربران کشور تحریم شده
    target_users = []
    for uid, user_data in utils.users.items():
        if user_data.get('country') == target_country and user_data.get('activated'):
            target_users.append(uid)
    
    # فریز کردن سهام‌های کشور تحریم شده در شرکت‌های کشور تحریم کننده
    from economy import company_templates
    
    frozen_stocks = 0
    for uid in target_users:
        user = utils.users[uid]
        user_stocks = user.get('stocks', {})
        
        # بررسی سهام‌های کشور تحریم کننده
        for country, companies in company_templates.items():
            if country == sanctioning_country:
                for company in companies:
                    symbol = company['symbol']
                    if symbol in user_stocks and user_stocks[symbol] > 0:
                        # فریز کردن سهام
                        if 'frozen_stocks' not in user:
                            user['frozen_stocks'] = {}
                        if symbol not in user['frozen_stocks']:
                            user['frozen_stocks'][symbol] = 0
                        user['frozen_stocks'][symbol] += user_stocks[symbol]
                        frozen_stocks += user_stocks[symbol]
                        # حذف سهام از موجودی عادی
                        del user_stocks[symbol]
    
    utils.save_users()
    print(f"[SANCTIONS] {frozen_stocks} سهام {target_country} در شرکت‌های {sanctioning_country} فریز شد")

async def unfreeze_target_country_stocks(sanctioning_country, target_country):
    """آزاد کردن سهام‌های کشور تحریم شده"""
    # پیدا کردن کاربران کشور تحریم شده
    target_users = []
    for uid, user_data in utils.users.items():
        if user_data.get('country') == target_country and user_data.get('activated'):
            target_users.append(uid)
    
    # آزاد کردن سهام‌های فریز شده
    from economy import company_templates
    
    unfrozen_stocks = 0
    for uid in target_users:
        user = utils.users[uid]
        frozen_stocks = user.get('frozen_stocks', {})
        
        # بررسی سهام‌های فریز شده کشور تحریم کننده
        for country, companies in company_templates.items():
            if country == sanctioning_country:
                for company in companies:
                    symbol = company['symbol']
                    if symbol in frozen_stocks and frozen_stocks[symbol] > 0:
                        # آزاد کردن سهام
                        if 'stocks' not in user:
                            user['stocks'] = {}
                        if symbol not in user['stocks']:
                            user['stocks'][symbol] = 0
                        user['stocks'][symbol] += frozen_stocks[symbol]
                        unfrozen_stocks += frozen_stocks[symbol]
                        # حذف سهام از فریز شده
                        del frozen_stocks[symbol]
    
    utils.save_users()
    print(f"[SANCTIONS] {unfrozen_stocks} سهام {target_country} در شرکت‌های {sanctioning_country} آزاد شد")

async def notify_sanctioned_user(sanctioning_country, target_country, bot_client=None):
    """ارسال پیام به کاربر تحریم شده"""
    try:
        # پیدا کردن کاربر کشور تحریم شده
        target_user_id = None
        for uid, user_data in utils.users.items():
            if user_data.get('country') == target_country and user_data.get('activated'):
                target_user_id = uid
                break
        
        if target_user_id:
            # پیام از زبان وزیر امور خارجه
            text = f"🚨 <b>اطلاعیه وزارت امور خارجه</b>\n\n"
            text += f"📢 <b>وزیر امور خارجه {target_country}:</b>\n\n"
            text += f"💬 <i>\"کشور {sanctioning_country} ما را تحریم کرده است. ما تمام تلاش‌مان را کردیم که این اتفاق صورت نگیرد، در حالی که آن‌ها به کار خود ادامه دادند. امیدواریم کشور آسیب جدی نبیند. ما مجدداً در حال رایزنی هستیم.\"</i>\n\n"
            text += f"🔴 <b>تأثیرات تحریم:</b>\n"
            text += f"• {target_country} نمی‌تواند از {sanctioning_country} خرید کند\n"
            text += f"• {target_country} نمی‌تواند سهام شرکت‌های {sanctioning_country} را بخرد\n"
            text += f"• سهام‌های موجود {target_country} در شرکت‌های {sanctioning_country} فریز شد\n\n"
            text += f"🤝 وزارت امور خارجه در تلاش برای حل این موضوع است."
            
            from bot import bot
            client = bot_client or bot
            await client.send_message(chat_id=int(target_user_id), text=text, parse_mode='HTML')
            print(f"[SANCTIONS] Notification sent to {target_country} (user {target_user_id})")
    except Exception as e:
        print(f"[ERROR] خطا در ارسال پیام تحریم به کاربر: {e}")

async def notify_sanction_lifted_user(sanctioning_country, target_country, bot_client=None):
    """ارسال پیام به کاربر آزاد شده از تحریم"""
    try:
        # پیدا کردن کاربر کشور آزاد شده
        target_user_id = None
        for uid, user_data in utils.users.items():
            if user_data.get('country') == target_country and user_data.get('activated'):
                target_user_id = uid
                break
        
        if target_user_id:
            # پیام مثبت از زبان وزیر امور خارجه
            text = f"🎉 <b>اطلاعیه وزارت امور خارجه</b>\n\n"
            text += f"📢 <b>وزیر امور خارجه {target_country}:</b>\n\n"
            text += f"💬 <i>\"خوشحالیم که اعلام کنیم کشور {sanctioning_country} تحریم‌های اعمال شده علیه ما را لغو کرده است. رایزنی‌های دیپلماتیک ما نتیجه داده و روابط بین دو کشور به حالت عادی بازگشته است.\"</i>\n\n"
            text += f"🟢 <b>تأثیرات لغو تحریم:</b>\n"
            text += f"• {target_country} حالا می‌تواند از {sanctioning_country} خرید کند\n"
            text += f"• {target_country} می‌تواند سهام شرکت‌های {sanctioning_country} را بخرد\n"
            text += f"• سهام‌های {target_country} در شرکت‌های {sanctioning_country} آزاد شد\n\n"
            text += f"🤝 روابط تجاری و اقتصادی بین دو کشور از سر گرفته شد."
            
            from bot import bot
            client = bot_client or bot
            await client.send_message(chat_id=int(target_user_id), text=text, parse_mode='HTML')
            print(f"[SANCTIONS] Lift notification sent to {target_country} (user {target_user_id})")
    except Exception as e:
        print(f"[ERROR] خطا در ارسال پیام لغو تحریم به کاربر: {e}")

async def announce_sanction_in_news(sanctioning_country, target_country, bot_client=None):
    """اعلام تحریم در کانال اخبار"""
    try:
        text = f"🚫 <b>اعلام تحریم</b>\n\n"
        text += f"🌍 کشور {sanctioning_country} کشور {target_country} را تحریم کرد.\n\n"
        text += "🔴 <b>تأثیرات تحریم:</b>\n"
        text += f"• {target_country} نمی‌تواند از {sanctioning_country} خرید کند\n"
        text += f"• {target_country} نمی‌تواند سهام شرکت‌های {sanctioning_country} را بخرد\n"
        text += f"• سهام‌های موجود {target_country} در شرکت‌های {sanctioning_country} فریز شد\n\n"
        text += "⚠️ این تحریم تا زمان لغو آن ادامه خواهد داشت."
        
        # ارسال به کانال اخبار
        from bot import bot
        client = bot_client or bot
        await client.send_message(chat_id=utils.NEWS_CHANNEL_ID, text=text, parse_mode='HTML')
    except Exception as e:
        print(f"[ERROR] خطا در اعلام تحریم: {e}")

async def announce_sanction_removal_in_news(sanctioning_country, target_country, bot_client=None):
    """اعلام لغو تحریم در کانال اخبار"""
    try:
        text = f"✅ <b>لغو تحریم</b>\n\n"
        text += f"🌍 کشور {sanctioning_country} تحریم کشور {target_country} را لغو کرد.\n\n"
        text += "🟢 <b>تأثیرات لغو تحریم:</b>\n"
        text += f"• {target_country} حالا می‌تواند از {sanctioning_country} خرید کند\n"
        text += f"• {target_country} می‌تواند سهام شرکت‌های {sanctioning_country} را بخرد\n"
        text += f"• سهام‌های {target_country} در شرکت‌های {sanctioning_country} آزاد شد\n\n"
        text += "🤝 روابط تجاری بین دو کشور از سر گرفته شد."
        
        # ارسال به کانال اخبار
        from bot import bot
        client = bot_client or bot
        await client.send_message(chat_id=utils.NEWS_CHANNEL_ID, text=text, parse_mode='HTML')
    except Exception as e:
        print(f"[ERROR] خطا در اعلام لغو تحریم: {e}")

# تابع بررسی تحریم
def is_country_sanctioned(sanctioning_country, target_country):
    """بررسی اینکه آیا کشور هدف توسط کشور تحریم کننده تحریم شده"""
    # نرمال‌سازی نام‌های کشور برای تطبیق
    from economy import _strip_flags_and_normalize
    sanctioning_normalized = _strip_flags_and_normalize(sanctioning_country)
    target_normalized = _strip_flags_and_normalize(target_country)
    
    # بررسی تحریم با نام‌های نرمال‌سازی شده
    if sanctioning_normalized in utils.sanctions:
        sanctioned_countries = utils.sanctions[sanctioning_normalized]
        return target_normalized in sanctioned_countries
    
    # بررسی تحریم با نام‌های اصلی (برای سازگاری با داده‌های قدیمی)
    return (sanctioning_country in utils.sanctions and 
            target_country in utils.sanctions[sanctioning_country])











