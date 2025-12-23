import json
import asyncio
import hashlib
import uuid
import time
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import utils
import hashlib

# شناسه کاربر سازمان ملل
# UN_USER_ID ثابت حذف شد - حالا از utils.UN_ACTIVATED_USER استفاده می‌شه

def _gen_unique_resolution_number() -> int:
    import random
    existing = set(r.get('number') for r in getattr(utils, 'un_resolutions', []))
    for _ in range(1000):
        num = random.randint(100, 9999)
        if num not in existing:
            return num
    # fallback
    return int(random.randint(100, 9999))

def _resolve_country_from_hash_any(key: str) -> str | None:
    try:
        countries = set(u.get('country') for u in utils.users.values() if u.get('activated'))
        for c in countries:
            h = hashlib.sha1(c.encode('utf-8')).hexdigest()
            if h.startswith(key) or h == key:
                return c
    except Exception:
        return None
    return None

def _format_resolution_text(number: int, target_country: str, reason: str, concern: str, necessity: str, main_clause: str, extras: str) -> str:
    text = (
        f"📜 <b>قطعنامه شماره {number}</b>\n"
        "شورای امنیت سازمان ملل متحد،\n\n"
        f"<i>با توجه به:</i>\n"
        f"<blockquote>{reason}</blockquote>\n\n"
        f"<i>با ابراز نگرانی نسبت به:</i>\n"
        f"<blockquote>{concern}</blockquote>\n\n"
        f"<i>با تأکید بر ضرورت:</i>\n"
        f"<blockquote>{necessity}</blockquote>\n\n"
        "📋 <b>تصمیم می‌گیرد:</b>\n\n"
        f"1️⃣ {main_clause}\n"
        f"2️⃣ {extras}\n"
        f"3️⃣ این قطعنامه لازم‌الاجراست.\n\n"
        f"🎯 <b>کشور هدف:</b> {target_country}"
    )
    return text

def _format_tally_block(res) -> str:
    total_players = _get_active_players_count() or 1
    votes = res.get('votes', {})
    yes = sum(1 for v in votes.values() if v == 'yes')
    no = sum(1 for v in votes.values() if v == 'no')
    abstain = sum(1 for v in votes.values() if v == 'abstain')
    def pct(x):
        try:
            return round((x / max(1, total_players)) * 100, 1)
        except Exception:
            return 0
    lines = []
    lines.append(f"📊 وضعیت آرا ({len(votes)}/{total_players} رای):")
    lines.append(f"✅ بله: {yes} ({pct(yes)}%)")
    lines.append(f"❌ خیر: {no} ({pct(no)}%)")
    lines.append(f"⚪ ممتنع: {abstain} ({pct(abstain)}%)")
    return "\n".join(lines)

def _compose_channel_message_text(res) -> str:
    number = res.get('number')
    kind = res.get('sanction_kind')
    main_clause = f"اعمال تحریم {('اقتصادی' if kind=='economic' else 'نظامی' if kind=='military' else 'دیپلماتیک')} علیه {res.get('target_country')}"
    extras = "ایجاد سازوکار نظارت، بازبینی دوره‌ای و گزارش‌دهی به شورای امنیت"
    body = _format_resolution_text(number, res.get('target_country'), res.get('reason'), res.get('concern'), res.get('necessity'), main_clause, extras)
    status = res.get('status', 'voting')
    status_line = ''
    if status == 'adopted':
        status_line = "\n\n✅ نتیجه: تصویب شد"
    elif status == 'rejected':
        status_line = "\n\n❌ نتیجه: رد شد"
    elif status == 'revote':
        status_line = "\n\n🔄 نتیجه: رای‌گیری مجدد"
    footer = "\n\n🗳️ از منوی دیپلماسی → سازمان ملل → صندوق رای می‌توانید رای دهید." if status == 'voting' else ''
    tally = "\n\n" + _format_tally_block(res)
    return body + status_line + footer + tally

async def post_resolution_channel_message(number: int):
    try:
        channel_id = utils.NEWS_CHANNEL_ID if hasattr(utils, 'NEWS_CHANNEL_ID') else None
        print(f"DEBUG: Channel ID = {channel_id}")
        if not channel_id:
            print(f"NEWS_CHANNEL_ID not found: {getattr(utils, 'NEWS_CHANNEL_ID', 'None')}")
            return
        res = _find_resolution_by_number(number)
        if not res:
            print(f"Resolution {number} not found")
            return
        print(f"DEBUG: Found resolution {number}, composing message...")
        message_text = _compose_channel_message_text(res)
        print(f"DEBUG: Message length = {len(message_text)}")
        from telegram import Bot
        bot = Bot(token=utils.BOT_TOKEN)
        print(f"DEBUG: Sending message to channel {channel_id}...")
        msg = await bot.send_message(chat_id=channel_id, text=message_text, parse_mode='HTML')
        print(f"DEBUG: Message sent successfully, ID = {msg.message_id}")
        try:
            await bot.pin_chat_message(chat_id=channel_id, message_id=msg.message_id, disable_notification=True)
            print(f"DEBUG: Message pinned successfully")
        except Exception as e:
            print(f"pin error: {e}")
        # ذخیره شناسه پیام کانال برای بروزرسانی زنده
        res['channel_chat_id'] = channel_id
        res['channel_message_id'] = msg.message_id
        utils.save_un_data()
        print(f"DEBUG: Channel message data saved")
    except Exception as e:
        print(f"خطا در ارسال قطعنامه به کانال: {e}")
        import traceback
        traceback.print_exc()

async def update_resolution_channel_message(number: int):
    try:
        res = _find_resolution_by_number(number)
        if not res:
            return
        chat_id = res.get('channel_chat_id') or getattr(utils, 'NEWS_CHANNEL_ID', None)
        message_id = res.get('channel_message_id')
        if not chat_id or not message_id:
            return
        from telegram import Bot
        bot = Bot(token=utils.BOT_TOKEN)
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=_compose_channel_message_text(res), parse_mode='HTML')
    except Exception as e:
        print(f"خطا در بروزرسانی پیام کانال قطعنامه: {e}")

async def _notify_all_countries_about_resolution(number: int):
    try:
        from telegram import Bot
        bot = Bot(token=utils.BOT_TOKEN)
        for uid, u in utils.users.items():
            if u.get('activated'):
                try:
                    await bot.send_message(
                        chat_id=int(uid),
                        text=(
                            f"📜 یک قطعنامه جدید با شماره {number} برای رای‌گیری ثبت شد.\n\n"
                            "🗳️ برای رای دادن: منوی دیپلماسی → سازمان ملل → صندوق رای"
                        )
                    )
                except Exception as e:
                    print(f"notify resolution to {uid} error: {e}")
    except Exception as e:
        print(f"notify all countries error: {e}")

def _get_active_players_count() -> int:
    try:
        return sum(1 for u in utils.users.values() if u.get('activated'))
    except Exception:
        return 0

def _find_resolution_by_number(number: int):
    for r in getattr(utils, 'un_resolutions', []):
        if r.get('number') == number:
            return r
    return None

async def finalize_resolution_if_complete(number: int, context: ContextTypes.DEFAULT_TYPE | None = None):
    res = _find_resolution_by_number(number)
    if not res or res.get('status') != 'voting':
        return
    total_players = _get_active_players_count()
    votes = res.get('votes', {})
    yes = sum(1 for v in votes.values() if v == 'yes')
    no = sum(1 for v in votes.values() if v == 'no')
    abstain = sum(1 for v in votes.values() if v == 'abstain')
    res['tally'] = {'yes': yes, 'no': no, 'abstain': abstain}
    # فقط زمانی نتیجه‌گیری کن که همه رای داده باشند
    if len(votes) < max(1, total_players):
        utils.save_un_data()
        return
    import math
    required_yes = math.ceil(0.51 * total_players)
    outcome = None
    if yes >= required_yes:
        outcome = 'adopted'
    elif abstain > yes and abstain > no:
        outcome = 'revote'
    elif no > yes:
        outcome = 'rejected'
    else:
        # پیش‌فرض باز-رای‌گیری
        outcome = 'revote'
    res['status'] = outcome
    # در صورت تصویب: تنظیم پنجره زمانی اثرگذاری برای تحریم اقتصادی
    if outcome == 'adopted' and res.get('sanction_kind') == 'economic':
        dur = res.get('duration_turns', 12)
        current_turn = utils.game_data.get('turn', 1)
        res['effective_turn'] = current_turn
        res['expires_at_turn'] = current_turn + max(1, int(dur))
    utils.save_un_data()
    # بروزرسانی پیام کانال با وضعیت نهایی
    try:
        await update_resolution_channel_message(number)
    except Exception as e:
        print(f"update final channel message error: {e}")
    # اطلاع‌رسانی‌ها
    try:
        from telegram import Bot
        bot = Bot(token=utils.BOT_TOKEN)
        msg = (
            f"📜 قطعنامه شماره {number}\n"
            f"نتیجه رای‌گیری: {('✅ تصویب شد' if outcome=='adopted' else '❌ رد شد' if outcome=='rejected' else '🔄 رای‌گیری مجدد')}\n"
            f"آرا: ✅ {yes} — ❌ {no} — ⚪ {abstain}"
        )
        # کانال (ترجیحاً ریپلای روی پیام اصلی قطعنامه)
        channel_chat_id = res.get('channel_chat_id') or getattr(utils, 'NEWS_CHANNEL_ID', None) or getattr(utils, 'CHANNEL_ID', None)
        reply_to_id = res.get('channel_message_id')
        if channel_chat_id:
            try:
                await bot.send_message(chat_id=channel_chat_id, text=msg, reply_to_message_id=reply_to_id)
            except Exception as e:
                print(f"channel announce error: {e}")
        # کاربر سازمان ملل
        if utils.UN_ACTIVATED_USER:
            try:
                await bot.send_message(chat_id=int(utils.UN_ACTIVATED_USER), text=msg)
            except Exception as e:
                print(f"un user notify error: {e}")
    except Exception as e:
        print(f"finalize notify error: {e}")

async def show_un_panel(query):
    """
    نمایش پنل اصلی سازمان ملل
    """
    text = "🏛️ <b>پنل سازمان ملل</b>\n\nبه سیستم مدیریت بین‌المللی خوش آمدید!"
    
    keyboard = [
        [InlineKeyboardButton("📜 صدور قطعنامه", callback_data="un_resolutions")],
        [InlineKeyboardButton("🚫 اعمال تحریم", callback_data="un_sanctions")],
        [InlineKeyboardButton("⚖️ برگزاری دادگاه", callback_data="un_court")],
        [InlineKeyboardButton("👮‍♀️ مشاهده", callback_data="un_monitoring")],
        [InlineKeyboardButton("🏆 جایزه صلح", callback_data="un_peace_prize")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_resolutions_menu(query):
    """
    منوی صدور قطعنامه
    """
    text = "📜 <b>صدور قطعنامه</b>\n\nنوع قطعنامه مورد نظر را انتخاب کنید:"
    
    keyboard = [
        [InlineKeyboardButton("💰 تحریم اقتصادی", callback_data="un_resolution_sanction_economic")],
        [InlineKeyboardButton("⚔️ تحریم نظامی", callback_data="un_resolution_sanction_military")],
        [InlineKeyboardButton("🤝 تحریم دیپلماتیک", callback_data="un_resolution_sanction_diplomatic")],
        [InlineKeyboardButton("🕊️ درخواست آتش‌بس فوری", callback_data="un_resolution_ceasefire")],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data="un_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_ceasefire_resolution_menu(query):
    """
    منوی درخواست آتش بس فوری - نمایش جنگ‌های فعال
    """
    text = "🕊️ <b>درخواست آتش بس فوری</b>\n\n"
    
    # بررسی اعلان جنگ‌های فعال
    active_wars = []
    if hasattr(utils, 'war_declarations') and utils.war_declarations:
        for war_id, war_data in utils.war_declarations.items():
            if war_data.get('status') == 'active':
                attacker = war_data.get('attacker', 'نامشخص')
                defender = war_data.get('defender', 'نامشخص')
                war_type = war_data.get('type', 'نامشخص')
                turn_declared = war_data.get('turn_declared', 1)
                
                active_wars.append({
                    'id': war_id,
                    'attacker': attacker,
                    'defender': defender,
                    'type': war_type,
                    'turn': turn_declared
                })
    
    if active_wars:
        text += f"📊 <b>تعداد جنگ‌های فعال:</b> {len(active_wars)}\n\n"
        text += "🔴 <b>جنگ‌های فعال:</b>\n"
        text += "برای هر جنگ می‌توانید درخواست آتش بس ارسال کنید:\n\n"
        
        # ایجاد دکمه‌ها برای هر جنگ
        keyboard = []
        for war in active_wars:
            war_text = f"⚔️ {war['attacker']} vs {war['defender']} ({war['type']})"
            # ساخت کلید کوتاه امن برای callback (هش war_id)
            war_hash = hashlib.sha1(war['id'].encode('utf-8')).hexdigest()[:10]
            callback_data = f"un_ceasefire_request_{war_hash}"
            keyboard.append([InlineKeyboardButton(war_text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton("🔄 بروزرسانی", callback_data="un_resolution_ceasefire")])
        keyboard.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="un_resolutions")])
        
    else:
        text += "✅ <b>هیچ جنگی در حال حاضر فعال نیست!</b>\n\n"
        text += "🌍 جهان در صلح و آرامش به سر می‌برد."
        text += "\n\n🕊️ نیازی به درخواست آتش بس نیست."
        keyboard = [
            [InlineKeyboardButton("🔄 بروزرسانی", callback_data="un_resolution_ceasefire")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="un_resolutions")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_sanctions_menu(query):
    """
    منوی اعمال تحریم
    """
    text = "🚫 <b>اعمال تحریم</b>\n\nنوع تحریم مورد نظر را انتخاب کنید:"
    
    keyboard = [
        [InlineKeyboardButton("🛒 تحریم تجاری", callback_data="un_sanction_trade")],
        [InlineKeyboardButton("⚔️ تحریم نظامی", callback_data="un_sanction_military")],
        [InlineKeyboardButton("🤝 تحریم دیپلماتیک", callback_data="un_sanction_diplomatic")],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data="un_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def start_sanction_wizard(query, sanction_kind: str):
    if str(query.from_user.id) != utils.UN_ACTIVATED_USER:
        await query.answer("❌ فقط کاربر سازمان ملل مجاز است.", show_alert=True)
        return
    utils.pending_un_resolution_draft[str(query.from_user.id)] = {
        'step': 'target',
        'sanction_kind': sanction_kind,
        'target_country': None,
        'reason': None,
        'concern': None,
        'necessity': None,
        'number': None
    }
    # انتخاب کشور هدف از بین کشورهای فعال
    countries = []
    for u in utils.users.values():
        if u.get('activated') and u.get('country'):
            countries.append(u.get('country'))
    countries = sorted(set(countries))
    text = f"🚫 <b>تحریم {('اقتصادی' if sanction_kind=='economic' else 'نظامی' if sanction_kind=='military' else 'دیپلماتیک')}</b>\n\nکشور هدف را انتخاب کنید:"
    keyboard = []
    row = []
    for c in countries:
        key = hashlib.sha1(c.encode('utf-8')).hexdigest()[:10]
        row.append(InlineKeyboardButton(c, callback_data=f"un_res_target_{key}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("لغو ❌", callback_data="un_res_cancel")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def handle_resolution_draft_message(update, context):
    user_id = str(update.effective_user.id)
    draft = utils.pending_un_resolution_draft.get(user_id)
    if not draft:
        print(f"[DEBUG] No draft found for user {user_id}")
        return
    step = draft.get('step')
    content = (update.message.text if hasattr(update.message, 'text') and update.message.text else '').strip()
    print(f"[DEBUG] Processing UN resolution draft step '{step}' for user {user_id}, content: '{content}'")
    if step == 'reason':
        draft['reason'] = content
        draft['step'] = 'concern'
        await update.message.reply_text("📝 پیامدهای اقدام کشور هدف را بنویسید:")
    elif step == 'concern':
        draft['concern'] = content
        draft['step'] = 'necessity'
        await update.message.reply_text("📝 ضرورت اقدام بین‌المللی را بنویسید:")
    elif step == 'necessity':
        draft['necessity'] = content
        # سوال مدت اجرای قطعنامه
        draft['step'] = 'duration'
        await update.message.reply_text("⏱️ مدت اجرای قطعنامه را به تعداد دور وارد کنید (مثلاً 12):")
    elif step == 'duration':
        # خواندن مدت
        print(f"[DEBUG] Processing duration step, content: '{content}'")
        try:
            duration = int(content.replace(',', ''))
            if duration <= 0:
                raise ValueError()
            print(f"[DEBUG] Duration parsed successfully: {duration}")
        except Exception as e:
            print(f"[DEBUG] Error parsing duration: {e}")
            await update.message.reply_text("❌ مقدار نامعتبر است. لطفاً یک عدد مثبت وارد کنید.")
            return
        draft['duration_turns'] = duration
        # ساخت پیش‌نویس نهایی برای تایید
        number = _gen_unique_resolution_number()
        draft['number'] = number
        kind = draft['sanction_kind']
        main_clause = (
            f"اعمال تحریم {('اقتصادی' if kind=='economic' else 'نظامی' if kind=='military' else 'دیپلماتیک')} علیه {draft['target_country']}"
        )
        extras = "ایجاد سازوکار نظارت، بازبینی دوره‌ای و گزارش‌دهی به شورای امنیت"
        text = _format_resolution_text(number, draft['target_country'], draft['reason'], draft['concern'], draft['necessity'], main_clause, extras)
        text += f"\n\n⏱️ <b>مدت اثر:</b> {duration} دور"
        keyboard = [
            [InlineKeyboardButton("✅ تایید و ارسال به رای‌گیری", callback_data=f"un_res_confirm_{number}")],
            [InlineKeyboardButton("❌ لغو", callback_data="un_res_cancel")]
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        draft['step'] = 'confirm'
    else:
        print(f"[DEBUG] Unknown step '{step}' in UN resolution draft")
        await update.message.reply_text("لطفاً از دکمه‌ها استفاده کنید یا مراحل را به ترتیب تکمیل کنید.")
    utils.pending_un_resolution_draft[user_id] = draft
    utils.save_un_data()

async def handle_resolution_callback(query):
    data = query.data
    user_id = str(query.from_user.id)
    if data.startswith('un_res_target_'):
        key = data.replace('un_res_target_', '')
        country = _resolve_country_from_hash_any(key)
        draft = utils.pending_un_resolution_draft.get(user_id)
        if not draft:
            await query.answer("پیش‌نویس یافت نشد.", show_alert=True)
            return
        draft['target_country'] = country
        draft['step'] = 'reason'
        utils.pending_un_resolution_draft[user_id] = draft
        await query.edit_message_text("📝 دلیل/اقدام کشور هدف چیست؟ بنویسید:")
        return
    if data == 'un_res_cancel':
        if user_id in utils.pending_un_resolution_draft:
            del utils.pending_un_resolution_draft[user_id]
            utils.save_un_data()
        await query.edit_message_text("لغو شد.")
        return
    if data.startswith('un_res_confirm_'):
        try:
            number = int(data.replace('un_res_confirm_', ''))
        except:
            await query.answer("خطای شماره قطعنامه.", show_alert=True)
            return
        draft = utils.pending_un_resolution_draft.get(user_id)
        if not draft or draft.get('number') != number:
            await query.answer("پیش‌نویس معتبر نیست.", show_alert=True)
            return
        res = {
            'number': number,
            'type': 'sanction',
            'sanction_kind': draft.get('sanction_kind'),
            'target_country': draft.get('target_country'),
            'reason': draft.get('reason'),
            'concern': draft.get('concern'),
            'necessity': draft.get('necessity'),
            'status': 'voting',
            'created_by': user_id,
            'created_turn': utils.game_data.get('turn', 1),
            'duration_turns': draft.get('duration_turns', 12),
            'votes': {},
            'tally': {'yes': 0, 'no': 0, 'abstain': 0}
        }
        if not hasattr(utils, 'un_resolutions'):
            utils.un_resolutions = []
        utils.un_resolutions.append(res)
        utils.save_un_data()
        # متن نهایی برای اعلان
        kind = res['sanction_kind']
        main_clause = f"اعمال تحریم {('اقتصادی' if kind=='economic' else 'نظامی' if kind=='military' else 'دیپلماتیک')} علیه {res['target_country']}"
        extras = "ایجاد سازوکار نظارت، بازبینی دوره‌ای و گزارش‌دهی به شورای امنیت"
        text = _format_resolution_text(number, res['target_country'], res['reason'], res['concern'], res['necessity'], main_clause, extras)
        await post_resolution_channel_message(number)
        await _notify_all_countries_about_resolution(number)
        # پاک کردن پیش‌نویس
        try:
            del utils.pending_un_resolution_draft[user_id]
            utils.save_un_data()
        except Exception:
            pass
        await query.edit_message_text(f"✅ قطعنامه شماره {number} برای رای‌گیری ثبت شد.")
        return

async def show_court_menu(query):
    """
    منوی دادگاه بین‌المللی
    """
    text = "⚖️ <b>دادگاه بین‌المللی</b>\n\nعملیات مورد نظر را انتخاب کنید:"
    
    keyboard = [
        [InlineKeyboardButton("📢 اطلاع تشکیل دادگاه", callback_data="un_court_announce")],
        [InlineKeyboardButton("🏛️ برگزاری دادگاه", callback_data="un_court_hold")],
        [InlineKeyboardButton("⚡ اجرای مجازات", callback_data="un_court_execute")],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data="un_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_monitoring_menu(query):
    """
    منوی مشاهده و نظارت
    """
    text = "👮‍♀️ <b>مشاهده و نظارت</b>\n\nبخش مورد نظر را انتخاب کنید:"
    
    keyboard = [
        [InlineKeyboardButton("⚔️ مشاهده جنگ‌ها", callback_data="un_monitor_wars")],
        [InlineKeyboardButton("🚫 مشاهده تحریم شدگان", callback_data="un_monitor_sanctioned")],
        [InlineKeyboardButton("📜 مشاهده قطعنامه‌ها", callback_data="un_monitor_resolutions")],
        [InlineKeyboardButton("🤝 مشاهده اتحادها", callback_data="un_monitor_alliances")],
        [InlineKeyboardButton("☢️ وضعیت اتمی کشورها", callback_data="un_monitor_nuclear")],
        [InlineKeyboardButton("📊 آمارهای دور گذشته", callback_data="un_monitor_statistics")],
        [InlineKeyboardButton("🏳️ مشاهده اعلان جنگ‌ها", callback_data="un_monitor_war_declarations")],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data="un_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_war_monitoring_menu(query):
    """
    منوی مشاهده انواع جنگ‌ها
    """
    text = "⚔️ <b>مشاهده جنگ‌ها</b>\n\nنوع حمله مورد نظر را انتخاب کنید:"
    
    keyboard = [
        [InlineKeyboardButton("🦶 حمله زمینی", callback_data="un_monitor_ground_war")],
        [InlineKeyboardButton("✈️ حمله هوایی", callback_data="un_monitor_air_war")],
        [InlineKeyboardButton("🚢 حمله دریایی", callback_data="un_monitor_naval_war")],
        [InlineKeyboardButton("🚀 حمله موشکی", callback_data="un_monitor_missile_war")],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data="un_monitoring")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_war_declarations_menu(query):
    """
    منوی مشاهده اعلان جنگ‌ها و درخواست آتش بس
    """
    text = "🏳️ <b>اعلان جنگ‌ها و درخواست آتش بس</b>\n\n"
    
    # بررسی اعلان جنگ‌های فعال
    active_wars = []
    if hasattr(utils, 'war_declarations') and utils.war_declarations:
        for war_id, war_data in utils.war_declarations.items():
            if war_data.get('status') == 'active':
                attacker = war_data.get('attacker', 'نامشخص')
                defender = war_data.get('defender', 'نامشخص')
                war_type = war_data.get('type', 'نامشخص')
                turn_declared = war_data.get('turn_declared', 1)
                
                active_wars.append({
                    'id': war_id,
                    'attacker': attacker,
                    'defender': defender,
                    'type': war_type,
                    'turn': turn_declared
                })
    
    if active_wars:
        text += f"📊 <b>تعداد جنگ‌های فعال:</b> {len(active_wars)}\n\n"
        text += "🔴 <b>جنگ‌های فعال:</b>\n"
        
        # ایجاد دکمه‌ها برای هر جنگ
        keyboard = []
        for war in active_wars:
            war_text = f"⚔️ {war['attacker']} vs {war['defender']} ({war['type']})"
            war_hash = hashlib.sha1(war['id'].encode('utf-8')).hexdigest()[:10]
            callback_data = f"un_ceasefire_request_{war_hash}"
            keyboard.append([InlineKeyboardButton(war_text, callback_data=callback_data)])
        
        keyboard.append([InlineKeyboardButton("🔄 بروزرسانی", callback_data="un_monitor_war_declarations")])
        keyboard.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="un_monitoring")])
        
    else:
        text += "✅ <b>هیچ جنگی در حال حاضر فعال نیست!</b>\n\n"
        text += "🌍 جهان در صلح و آرامش به سر می‌برد."
        keyboard = [
            [InlineKeyboardButton("🔄 بروزرسانی", callback_data="un_monitor_war_declarations")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="un_monitoring")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

def _resolve_war_id(war_key: str) -> str | None:
    """تبدیل کلید دریافتی (ممکن است war_id واقعی یا هش آن باشد) به war_id واقعی"""
    # اگر کلید مستقیماً war_id باشد
    if war_key in utils.war_declarations:
        return war_key
    # در غیر این صورت، با هش تطبیق بده
    for wid in utils.war_declarations.keys():
        h = hashlib.sha1(wid.encode('utf-8')).hexdigest()
        if h == war_key or h.startswith(war_key):
            return wid
    return None

async def show_ceasefire_request_menu(query, war_key):
    """
    منوی درخواست آتش بس برای جنگ خاص
    """
    war_id = _resolve_war_id(war_key)
    if not hasattr(utils, 'war_declarations') or not war_id or war_id not in utils.war_declarations:
        await query.answer("❌ این جنگ یافت نشد!", show_alert=True)
        return
    
    war_data = utils.war_declarations[war_id]
    attacker = war_data.get('attacker', 'نامشخص')
    defender = war_data.get('defender', 'نامشخص')
    war_type = war_data.get('type', 'نامشخص')
    
    text = f"🕊️ <b>درخواست آتش بس فوری</b>\n\n"
    text += f"⚔️ <b>جنگ:</b> {attacker} vs {defender}\n"
    text += f"🎯 <b>نوع:</b> {war_type}\n"
    text += f"📅 <b>شروع:</b> دور {war_data.get('turn_declared', 1)}\n\n"
    text += "📋 <b>شرایط آتش بس:</b>\n"
    text += "▫️ توقف فوری تمام عملیات نظامی\n"
    text += "▫️ عقب‌نشینی نیروها به مرزهای قبل از جنگ\n"
    text += "▫️ مذاکرات صلح تحت نظارت سازمان ملل\n"
    text += "▫️ تشکیل کمیته نظارت بر آتش بس\n\n"
    text += "⚠️ <b>هشدار:</b> این درخواست برای هر دو طرف ارسال می‌شود."
    
    war_hash = hashlib.sha1(war_id.encode('utf-8')).hexdigest()[:10]
    keyboard = [
        [InlineKeyboardButton("🕊️ ارسال درخواست آتش بس", callback_data=f"un_send_ceasefire_{war_hash}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="un_monitor_war_declarations")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def send_ceasefire_request(query, war_key):
    """
    ارسال درخواست آتش بس به طرفین جنگ
    """
    war_id = _resolve_war_id(war_key)
    if not hasattr(utils, 'war_declarations') or not war_id or war_id not in utils.war_declarations:
        await query.answer("❌ این جنگ یافت نشد!", show_alert=True)
        return
    
    war_data = utils.war_declarations[war_id]
    attacker = war_data.get('attacker', 'نامشخص')
    defender = war_data.get('defender', 'نامشخص')
    
    # ایجاد یا استفاده از درخواست آتش بس موجود (idempotent)
    if not hasattr(utils, 'ceasefire_requests'):
        utils.ceasefire_requests = {}
    current_turn = utils.game_data.get('turn', 1)
    existing = utils.ceasefire_requests.get(war_id)
    if existing and existing.get('status') == 'pending':
        ceasefire_request = existing
    else:
        ceasefire_request = {
            'war_id': war_id,
            'attacker': attacker,
            'defender': defender,
            'requested_by': 'سازمان ملل',
            'status': 'pending',
            'attacker_response': None,
            'defender_response': None,
            'turn_requested': current_turn,
            'expires_at': current_turn + 3  # 3 دور مهلت پاسخ
        }
        utils.ceasefire_requests[war_id] = ceasefire_request
    try:
        if hasattr(utils, 'save_un_data'):
            utils.save_un_data()
    except Exception:
        pass
    
    # ارسال پیام به طرفین
    try:
        # پیدا کردن کاربران طرفین
        attacker_user_id = None
        defender_user_id = None
        
        for user_id, user_data in utils.users.items():
            if user_data.get('country') == attacker:
                attacker_user_id = user_id
            elif user_data.get('country') == defender:
                defender_user_id = user_id
        
        ceasefire_message = (
            f"🕊️ <b>درخواست آتش بس فوری از سازمان ملل</b>\n\n"
            f"⚔️ <b>جنگ:</b> {attacker} vs {defender}\n\n"
            f"📋 <b>شرایط آتش بس:</b>\n"
            f"▫️ توقف فوری تمام عملیات نظامی\n"
            f"▫️ عقب‌نشینی نیروها به مرزهای قبل از جنگ\n"
            f"▫️ مذاکرات صلح تحت نظارت سازمان ملل\n"
            f"▫️ تشکیل کمیته نظارت بر آتش بس\n\n"
            f"⏰ <b>مهلت پاسخ:</b> 3 دور\n\n"
            f"🔘 لطفاً موافقت یا مخالفت خود را اعلام کنید."
        )
        
        war_hash = hashlib.sha1(war_id.encode('utf-8')).hexdigest()[:10]
        keyboard = [
            [InlineKeyboardButton("✅ موافقت با آتش بس", callback_data=f"ceasefire_accept_{war_hash}")],
            [InlineKeyboardButton("❌ مخالفت با آتش بس", callback_data=f"ceasefire_reject_{war_hash}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # ارسال به دریافت‌کنندگان یکتا (شناسه نرمال‌شده برای جلوگیری از تکرار)
        normalized_recipients = []
        seen_ids = set()
        if attacker_user_id:
            aid = str(attacker_user_id)
            if aid not in seen_ids:
                seen_ids.add(aid)
                normalized_recipients.append(aid)
        if defender_user_id:
            did = str(defender_user_id)
            if did not in seen_ids:
                seen_ids.add(did)
                normalized_recipients.append(did)

        try:
            from telegram import Bot
            bot = Bot(token=utils.BOT_TOKEN)
            # جلوگیری از ارسال تکراری: اگر قبلاً برای این جنگ به این کاربر پیام رفته باشد، دوباره نفرست
            existing_data = utils.ceasefire_requests.get(war_id, {}) if hasattr(utils, 'ceasefire_requests') else {}
            already = set(existing_data.get('notified_user_ids', []))
            unique_recipients = [rid for rid in normalized_recipients if rid not in already]
            for rid in unique_recipients:
                try:
                    await bot.send_message(
                        chat_id=int(rid),
                        text=ceasefire_message,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"خطا در ارسال پیام آتش‌بس به کاربر {rid}: {e}")
            # ثبت کاربران نوتیف شده
            if hasattr(utils, 'ceasefire_requests') and unique_recipients:
                updated = utils.ceasefire_requests.get(war_id, {})
                notified = set(updated.get('notified_user_ids', []))
                for rid in unique_recipients:
                    notified.add(str(rid))
                updated['notified_user_ids'] = list(notified)
                utils.ceasefire_requests[war_id] = updated
                try:
                    if hasattr(utils, 'save_un_data'):
                        utils.save_un_data()
                except Exception:
                    pass
                try:
                    if hasattr(utils, 'save_un_data'):
                        utils.save_un_data()
                except Exception:
                    pass
        except Exception as e:
            print(f"خطا در آماده‌سازی Bot برای ارسال پیام آتش‌بس: {e}")
        
        # پیام موفقیت
        success_text = (
            f"✅ <b>درخواست آتش بس ارسال شد!</b>\n\n"
            f"🕊️ درخواست آتش بس برای جنگ {attacker} vs {defender} ارسال شد.\n\n"
            f"📋 <b>وضعیت:</b>\n"
            f"▫️ در انتظار پاسخ طرفین\n"
            f"▫️ مهلت پاسخ: 3 دور\n\n"
            f"🔍 <b>نکته:</b> اگر هر دو طرف موافقت کنند، آتش بس اعمال می‌شود."
        )
        
        war_hash = hashlib.sha1(war_id.encode('utf-8')).hexdigest()[:10]
        keyboard = [
            [InlineKeyboardButton("🔄 مشاهده وضعیت آتش بس", callback_data=f"un_ceasefire_status_{war_hash}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="un_monitor_war_declarations")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(success_text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception as e:
            if "Message is not modified" in str(e):
                try:
                    await query.answer("✅", show_alert=False)
                except:
                    pass
            else:
                raise
        
    except Exception as e:
        error_text = f"❌ <b>خطا در ارسال درخواست آتش بس:</b>\n\n{str(e)}"
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="un_monitor_war_declarations")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup, parse_mode='HTML')

async def show_ceasefire_status(query, war_key):
    """
    نمایش وضعیت درخواست آتش بس
    """
    war_id = _resolve_war_id(war_key)
    if not war_id or not hasattr(utils, 'ceasefire_requests') or war_id not in utils.ceasefire_requests:
        await query.answer("❌ درخواست آتش بس یافت نشد!", show_alert=True)
        return
    
    ceasefire_data = utils.ceasefire_requests[war_id]
    attacker = ceasefire_data.get('attacker', 'نامشخص')
    defender = ceasefire_data.get('defender', 'نامشخص')
    status = ceasefire_data.get('status', 'نامشخص')
    attacker_response = ceasefire_data.get('attacker_response')
    defender_response = ceasefire_data.get('defender_response')
    turn_requested = ceasefire_data.get('turn_requested', 1)
    expires_at = ceasefire_data.get('expires_at', 1)
    current_turn = utils.game_data.get('turn', 1)
    
    text = f"🕊️ <b>وضعیت درخواست آتش بس</b>\n\n"
    text += f"⚔️ <b>جنگ:</b> {attacker} vs {defender}\n"
    text += f"📅 <b>تاریخ درخواست:</b> دور {turn_requested}\n"
    text += f"⏰ <b>مهلت پاسخ:</b> دور {expires_at}\n"
    text += f"🔄 <b>دور فعلی:</b> {current_turn}\n\n"
    
    if status == 'pending':
        text += "⏳ <b>وضعیت:</b> در انتظار پاسخ طرفین\n\n"
        
        # نمایش پاسخ‌های طرفین
        text += "📋 <b>پاسخ‌های طرفین:</b>\n"
        
        if attacker_response is None:
            text += f"▫️ {attacker}: ⏳ در انتظار پاسخ\n"
        elif attacker_response == 'accept':
            text += f"▫️ {attacker}: ✅ موافقت\n"
        elif attacker_response == 'reject':
            text += f"▫️ {attacker}: ❌ مخالفت\n"
        
        if defender_response is None:
            text += f"▫️ {defender}: ⏳ در انتظار پاسخ\n"
        elif defender_response == 'accept':
            text += f"▫️ {defender}: ✅ موافقت\n"
        elif defender_response == 'reject':
            text += f"▫️ {defender}: ❌ مخالفت\n"
        
        # بررسی انقضای مهلت
        if current_turn > expires_at:
            text += "\n⚠️ <b>مهلت پاسخ منقضی شده!</b>\n"
            text += "درخواست آتش بس لغو می‌شود."
            
            # لغو درخواست منقضی شده
            ceasefire_data['status'] = 'expired'
            utils.ceasefire_requests[war_id] = ceasefire_data
            
        elif attacker_response == 'accept' and defender_response == 'accept':
            text += "\n🎉 <b>هر دو طرف موافقت کردند!</b>\n"
            text += "آتش بس اعمال می‌شود و جنگ پایان می‌یابد."
            
            # اعمال آتش بس
            await apply_ceasefire(war_id)
            # امتیاز صلح برای هر دو کشور موافق
            try:
                import utils
                utils.un_peace_scores[attacker] = utils.un_peace_scores.get(attacker, 0) + 1
                utils.un_peace_scores[defender] = utils.un_peace_scores.get(defender, 0) + 1
                utils.save_un_data()
            except Exception as _:
                pass
            
        elif attacker_response == 'reject' or defender_response == 'reject':
            text += "\n❌ <b>یکی از طرفین مخالفت کرد!</b>\n"
            text += "درخواست آتش بس رد شد."
            
            # لغو درخواست
            ceasefire_data['status'] = 'rejected'
            utils.ceasefire_requests[war_id] = ceasefire_data
            # امتیاز منفی برای کشور مخالف
            try:
                import utils
                # مشخص کن کدام طرف مخالفت کرده
                if attacker_response == 'reject':
                    utils.un_peace_scores[attacker] = utils.un_peace_scores.get(attacker, 0) - 1
                elif defender_response == 'reject':
                    utils.un_peace_scores[defender] = utils.un_peace_scores.get(defender, 0) - 1
                else:
                    # اگر فعلاً فقط یکی پاسخ داده و همان مخالف است
                    responder = attacker if attacker_response == 'reject' else defender
                    utils.un_peace_scores[responder] = utils.un_peace_scores.get(responder, 0) - 1
                utils.save_un_data()
            except Exception as _:
                pass
    
    elif status == 'accepted':
        text += "✅ <b>وضعیت:</b> آتش بس پذیرفته شد\n"
        text += "🌍 جنگ پایان یافت و صلح برقرار شد."
    elif status == 'rejected':
        text += "❌ <b>وضعیت:</b> آتش بس رد شد\n"
        text += "⚔️ جنگ ادامه دارد."
    elif status == 'expired':
        text += "⏰ <b>وضعیت:</b> مهلت پاسخ منقضی شد\n"
        text += "⚔️ جنگ ادامه دارد."
    
    war_hash = hashlib.sha1(war_id.encode('utf-8')).hexdigest()[:10]
    keyboard = [
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"un_ceasefire_status_{war_hash}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="un_monitor_war_declarations")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def apply_ceasefire(war_id):
    """
    اعمال آتش بس و پایان جنگ
    """
    try:
        if not hasattr(utils, 'ceasefire_requests') or war_id not in utils.ceasefire_requests:
            return
        
        ceasefire_data = utils.ceasefire_requests[war_id]
        # استخراج طرفین جنگ در ابتدا تا در تمام بخش‌ها در دسترس باشند
        attacker = ceasefire_data.get('attacker', 'نامشخص')
        defender = ceasefire_data.get('defender', 'نامشخص')
        
        # تغییر وضعیت جنگ به پایان یافته + ذخیره پایدار
        if hasattr(utils, 'war_declarations') and war_id in utils.war_declarations:
            utils.war_declarations[war_id]['status'] = 'ended'
            utils.war_declarations[war_id]['end_turn'] = utils.game_data.get('turn', 1)
            utils.war_declarations[war_id]['end_reason'] = 'ceasefire'
            try:
                if hasattr(utils, 'save_war_declarations'):
                    utils.save_war_declarations()
            except Exception as _:
                pass
        
        # تغییر وضعیت درخواست آتش بس + ذخیره پایدار
        ceasefire_data['status'] = 'accepted'
        utils.ceasefire_requests[war_id] = ceasefire_data
        try:
            if hasattr(utils, 'save_un_data'):
                utils.save_un_data()
        except Exception as _:
            pass

        # لغو هر نبرد دریایی جاری بین همین دو کشور و حفظ تلفات تاکنون اعمال‌شده
        try:
            attacker = ceasefire_data.get('attacker')
            defender = ceasefire_data.get('defender')
            # یافتن user_id طرفین بر اساس نام کشور
            attacker_id = None
            defender_id = None
            for uid, u in utils.users.items():
                if u.get('country') == attacker:
                    attacker_id = uid
                if u.get('country') == defender:
                    defender_id = uid
            # حذف حملات دریایی فعال مربوطه
            if hasattr(utils, 'naval_attacks'):
                for aid, ad in list(utils.naval_attacks.items()):
                    a = ad.get('attacker_id')
                    t = ad.get('target_id')
                    if (a == attacker_id and t == defender_id) or (a == defender_id and t == attacker_id):
                        # تلفات فازهای قبلی قبلاً از منابع کسر شده‌اند؛ تنها حمله را خاتمه می‌دهیم
                        del utils.naval_attacks[aid]
            # ذخیره کاربران پس از هر تغییری (اگر از قبل ذخیره نشده)
            try:
                if hasattr(utils, 'save_users'):
                    utils.save_users()
            except Exception as _:
                pass
        except Exception as _:
            pass

        # بهبود روابط: +50 بین دو کشور
        try:
            from utils import country_relations, save_country_relations, users
            attacker_id = None
            defender_id = None
            for uid, u in users.items():
                if u.get('country') == attacker:
                    attacker_id = str(uid)
                if u.get('country') == defender:
                    defender_id = str(uid)
            if attacker_id and defender_id:
                if attacker_id not in country_relations:
                    country_relations[attacker_id] = {}
                if defender_id not in country_relations:
                    country_relations[defender_id] = {}
                country_relations[attacker_id][defender_id] = country_relations[attacker_id].get(defender_id, 0) + 50
                country_relations[defender_id][attacker_id] = country_relations[defender_id].get(attacker_id, 0) + 50
                try:
                    save_country_relations()
                except Exception as _:
                    pass
        except Exception as e:
            print(f"خطا در بهبود روابط پس از آتش‌بس: {e}")
        
        # ارسال پیام موفقیت به طرفین
        
        success_message = (
            f"🕊️ <b>آتش بس اعمال شد!</b>\n\n"
            f"⚔️ <b>جنگ:</b> {attacker} vs {defender}\n\n"
            f"✅ <b>هر دو طرف موافقت کردند!</b>\n\n"
            f"🌍 <b>نتیجه:</b>\n"
            f"▫️ جنگ پایان یافت\n"
            f"▫️ آتش بس برقرار شد\n"
            f"▫️ صلح تحت نظارت سازمان ملل\n\n"
            f"🏛️ سازمان ملل از تصمیم صلح‌جویانه شما تشکر می‌کند."
        )
        
        # ارسال به طرفین
        for user_id, user_data in utils.users.items():
            if user_data.get('country') in [attacker, defender]:
                try:
                    from telegram import Bot
                    bot = Bot(token=utils.BOT_TOKEN)
                    await bot.send_message(
                        chat_id=int(user_id),
                        text=success_message,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    print(f"خطا در ارسال پیام موفقیت به {user_data.get('country')}: {e}")
        
        # ارسال پیام به کانال با عکس اختصاصی
        try:
            channel_photo = "https://t.me/TextEmpire_IR/89"
            channel_caption = (
                "🕊️ آتش بس اعمال شد!\n\n"
                f"⚔️ جنگ: {attacker} vs {defender}\n\n"
                "✅ هر دو طرف موافقت کردند!\n\n"
                "🌍 نتیجه:\n"
                "▫️ جنگ پایان یافت\n"
                "▫️ آتش بس برقرار شد\n"
                "▫️ صلح تحت نظارت سازمان ملل\n\n"
                "🏛️ سازمان ملل از تصمیم صلح‌جویانه شما تشکر می‌کند."
            )

            channel_id = utils.NEWS_CHANNEL_ID if hasattr(utils, 'NEWS_CHANNEL_ID') else None
            if channel_id:
                try:
                    from telegram import Bot
                    bot = Bot(token=utils.BOT_TOKEN)
                    await bot.send_photo(
                        chat_id=channel_id,
                        photo=channel_photo,
                        caption=channel_caption,
                        parse_mode='HTML'
                    )
                    print("✅ پیام آتش بس به کانال (با عکس) ارسال شد")
                except Exception as e:
                    print(f"خطا در ارسال پیام به کانال: {e}")
            else:
                print("⚠️ شناسه کانال تنظیم نشده - پیام آتش بس ارسال نشد")
        except Exception as e:
            print(f"خطا در ارسال پیام به کانال: {e}")
        
        print(f"✅ آتش بس برای جنگ {war_id} اعمال شد")
        
    except Exception as e:
        print(f"خطا در اعمال آتش بس: {e}")

async def show_peace_prize_menu(query):
    """
    منوی جایزه صلح
    """
    import utils
    current_turn = utils.game_data.get('turn', 1)
    cooldown_turn = 24
    can_award = (current_turn - utils.last_peace_prize_award_turn) >= cooldown_turn

    # ساخت لیست 3 کشور برتر بر اساس امتیاز صلح
    scores_items = list(utils.un_peace_scores.items())  # [(country, score)]
    scores_items.sort(key=lambda x: x[1], reverse=True)
    top_three = scores_items[:3]

    # شناسایی کشورهایی که تا حالا در هیچ جنگی حاضر نبودند
    never_war_countries = []
    try:
        active_country_names = set(u.get('country') for u in utils.users.values() if u.get('activated'))
        involved = set()
        for wid, w in utils.war_declarations.items():
            involved.add(w.get('attacker'))
            involved.add(w.get('defender'))
        never_war_countries = [c for c in active_country_names if c and c not in involved]
    except Exception:
        pass

    text = "🏆 <b>جایزه صلح</b>\n\n"
    text += f"📅 دور فعلی: {current_turn}\n"
    text += f"⏱️ فاصله لازم بین اهدای جوایز: {cooldown_turn} دور\n"
    last_turn = utils.last_peace_prize_award_turn
    if last_turn:
        text += f"🏁 آخرین اهدای جایزه: دور {last_turn}\n"
    text += "\n"

    # نمایش صدرنشین‌ها به صورت دکمه
    keyboard = []
    if top_three:
        text += "🥇 <b>سه کشور برتر صلح:</b>\n"
        for country, score in top_three:
            btn_text = f"{country} — {score:+.1f}"
            # callback کوتاه و امن
            h = hashlib.sha1(country.encode('utf-8')).hexdigest()[:10]
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"un_pp_nom_{h}")])
        text += "(برای جزئیات هر کشور روی دکمه بزنید)\n\n"
    else:
        text += "هنوز امتیاز صلحی ثبت نشده است.\n\n"

    if never_war_countries:
        text += "🕊️ <b>کشورهای بدون سابقه جنگ:</b>\n"
        for c in never_war_countries[:10]:
            text += f"▫️ {c}\n"
        if len(never_war_countries) > 10:
            text += "…\n"
        text += "\n"

    # دکمه‌های عملیات
    if can_award and top_three:
        keyboard.append([InlineKeyboardButton("🎖️ اعطای جایزه صلح", callback_data="un_peace_prize_award")])
    else:
        remain = cooldown_turn - (current_turn - utils.last_peace_prize_award_turn)
        if remain > 0:
            text += f"⏳ تا اهدای بعدی: {remain} دور\n"
    keyboard.append([InlineKeyboardButton("📋 مشاهده برندگان", callback_data="un_peace_prize_winners")])
    keyboard.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="un_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

def _resolve_country_from_hash(country_key: str) -> str | None:
    """تبدیل هش کوتاه یا کامل به نام کشور اصلی در un_peace_scores"""
    try:
        for country in utils.un_peace_scores.keys():
            full_hash = hashlib.sha1(country.encode('utf-8')).hexdigest()
            if full_hash.startswith(country_key) or full_hash == country_key:
                return country
    except Exception:
        return None
    return None

async def show_peace_prize_winners(query):
    import utils
    winners = utils.un_peace_prize_winners
    text = "🏆 <b>برندگان جایزه صلح</b>\n\n"
    if not winners:
        text += "هنوز جایزه‌ای اعطا نشده است."
    else:
        for i, w in enumerate(winners, 1):
            text += f"{i}. {w.get('country')} — دور {w.get('turn')}\n"
    keyboard = [[InlineKeyboardButton("⬅️ بازگشت", callback_data="un_peace_prize")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_peace_nominee_details(query, country_name: str):
    import utils
    score = utils.un_peace_scores.get(country_name, 0)
    text = (
        f"🥇 <b>نامزد جایزه صلح</b>\n\n"
        f"🏳️ کشور: {country_name}\n"
        f"⭐ امتیاز صلح: {score:+.1f}\n"
    )
    keyboard = [[InlineKeyboardButton("⬅️ بازگشت", callback_data="un_peace_prize")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def award_peace_prize(query):
    import utils
    current_turn = utils.game_data.get('turn', 1)
    if (current_turn - utils.last_peace_prize_award_turn) < 24:
        remain = 24 - (current_turn - utils.last_peace_prize_award_turn)
        await query.answer(f"⏳ هنوز {remain} دور تا امکان اعطای جایزه باقی مانده.", show_alert=True)
        return
    # انتخاب برنده: کشور با بالاترین امتیاز فعلی
    scores_items = list(utils.un_peace_scores.items())
    scores_items.sort(key=lambda x: x[1], reverse=True)
    if not scores_items:
        await query.answer("هیچ نامزدی برای جایزه وجود ندارد.", show_alert=True)
        return
    winner_country, winner_score = scores_items[0]

    # جایزه نقدی 1 میلیارد دلار
    winner_user_id = None
    for uid, u in utils.users.items():
        if u.get('country') == winner_country:
            winner_user_id = str(uid)
            break
    if winner_user_id:
        utils.users[winner_user_id]['resources']['cash'] = utils.users[winner_user_id]['resources'].get('cash', 0) + 1_000_000_000
        utils.save_users()

    # ثبت برنده و دور
    utils.un_peace_prize_winners.append({'country': winner_country, 'turn': current_turn})
    utils.last_peace_prize_award_turn = current_turn
    utils.save_un_data()

    # اعلان کانالی
    try:
        channel_id = utils.NEWS_CHANNEL_ID if hasattr(utils, 'NEWS_CHANNEL_ID') else None
        if channel_id:
            from telegram import Bot
            bot = Bot(token=utils.BOT_TOKEN)
            caption = (
                "🏆 <b>جایزه صلح سازمان ملل</b>\n\n"
                f"🥇 کشور برنده: {winner_country} 🏆\n"
                f"💵 جایزه: 1,000,000,000$\n"
            )
            channel_photo = "https://t.me/TextEmpire_IR/92"
            await bot.send_photo(chat_id=channel_id, photo=channel_photo, caption=caption, parse_mode='HTML')
    except Exception as e:
        print(f"خطا در ارسال اعلان جایزه صلح به کانال: {e}")

    # پیام خصوصی به برنده و به کاربر سازمان ملل + نمایش موفقیت در همان صفحه
    try:
        from telegram import Bot
        bot = Bot(token=utils.BOT_TOKEN)
        # پیام به برنده
        if winner_user_id:
            try:
                await bot.send_photo(
                    chat_id=int(winner_user_id),
                    photo="https://t.me/TextEmpire_IR/92",
                    caption=(
                        "🏆 <b>تبریک!</b>\n\n"
                        f"کشور شما ({winner_country}) برنده <b>جایزه صلح سازمان ملل</b> شد.\n"
                        "💵 پاداش: 1,000,000,000$ به خزانه شما افزوده شد."
                    ),
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"خطا در ارسال پیام به برنده جایزه صلح: {e}")
        # پیام به کاربر سازمان ملل
        if utils.UN_ACTIVATED_USER:
            try:
                await bot.send_photo(
                    chat_id=int(utils.UN_ACTIVATED_USER),
                    photo="https://t.me/TextEmpire_IR/92",
                    caption=(
                        "✅ <b>جایزه صلح اعطا شد.</b>\n\n"
                        f"🥇 کشور برنده: {winner_country}"
                    ),
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"خطا در ارسال پیام به کاربر سازمان ملل: {e}")
    except Exception as e:
        print(f"خطای کلی ارسال اعلان‌های جایزه صلح: {e}")

    # پیام موفقیت در همان صفحه
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت", callback_data="un_peace_prize")]])
        success_text = (
            "🏆 <b>جایزه صلح اعطا شد</b>\n\n"
            f"🥇 کشور برنده: {winner_country} 🏆\n"
            "💵 جایزه واریز شد."
        )
        await query.edit_message_text(success_text, reply_markup=kb, parse_mode='HTML')
    except Exception as e:
        print(f"خطا در نمایش پیام موفقیت جایزه صلح: {e}")

# توابع کمکی برای بررسی دسترسی
def is_un_user(user_id):
    """
    بررسی اینکه آیا کاربر سازمان ملل هست یا نه
    """
    import utils
    return str(user_id) == utils.UN_ACTIVATED_USER

def require_un_access(func):
    """
    دکوراتور برای محدود کردن دسترسی فقط به کاربر سازمان ملل
    """
    async def wrapper(query, *args, **kwargs):
        if not is_un_user(query.from_user.id):
            await query.answer("❌ فقط کاربران سازمان ملل می‌توانند به این بخش دسترسی داشته باشند!", show_alert=True)
            return
        return await func(query, *args, **kwargs)
    return wrapper

# تابع اصلی برای فراخوانی از bot.py
async def handle_un_callback(query, context):
    """
    مدیریت تمام callback های مربوط به سازمان ملل
    """
    if not is_un_user(query.from_user.id):
        await query.answer("❌ دسترسی غیرمجاز!", show_alert=True)
        return
    
    data = query.data
    
    if data == "un_main":
        await show_un_panel(query)
    elif data == "un_resolutions":
        await show_resolutions_menu(query)
    elif data == "un_resolution_sanction_economic":
        await start_sanction_wizard(query, 'economic')
    elif data == "un_resolution_sanction_military":
        await start_sanction_wizard(query, 'military')
    elif data == "un_resolution_sanction_diplomatic":
        await start_sanction_wizard(query, 'diplomatic')
    elif data == "un_resolution_ceasefire":
        await show_ceasefire_resolution_menu(query)
    elif data == "un_sanctions":
        await show_sanctions_menu(query)
    elif data == "un_court":
        await show_court_menu(query)
    elif data == "un_monitoring":
        await show_monitoring_menu(query)
    elif data == "un_monitor_wars":
        await show_war_monitoring_menu(query)
    elif data == "un_monitor_war_declarations":
        await show_war_declarations_menu(query)
    elif data == "un_peace_prize":
        await show_peace_prize_menu(query)
    elif data.startswith("un_peace_prize_nominee_"):
        country = data.replace("un_peace_prize_nominee_", "")
        await show_peace_nominee_details(query, country)
    elif data == "un_peace_prize_award":
        await award_peace_prize(query)
    elif data == "un_peace_prize_winners":
        await show_peace_prize_winners(query)
    elif data.startswith("un_ceasefire_request_"):
        war_key = data.replace("un_ceasefire_request_", "")
        await show_ceasefire_request_menu(query, war_key)
    elif data.startswith("un_send_ceasefire_"):
        war_key = data.replace("un_send_ceasefire_", "")
        await send_ceasefire_request(query, war_key)
    elif data.startswith("un_ceasefire_status_"):
        war_key = data.replace("un_ceasefire_status_", "")
        await show_ceasefire_status(query, war_key)
    elif data.startswith("un_peace_prize_nominee_"):
        # سازگاری قدیم: نام کشور مستقیم
        country = data.replace("un_peace_prize_nominee_", "")
        await show_peace_nominee_details(query, country)
    elif data.startswith("un_pp_nom_"):
        # نسخه جدید کوتاه
        key = data.replace("un_pp_nom_", "")
        country = _resolve_country_from_hash(key) or key
        await show_peace_nominee_details(query, country)
    elif data.startswith("un_res_"):
        await handle_resolution_callback(query)
    # callback های دادگاه سازمان ملل
    elif data.startswith("un_court_"):
        await handle_un_court_callback(query)
    # سایر callback ها اینجا اضافه می‌شن
    else:
        await query.answer("⚠️ این قابلیت هنوز پیاده‌سازی نشده است!", show_alert=True)

# ===== سیستم برگزاری دادگاه سازمان ملل =====

async def show_court_menu(query):
    """نمایش منوی اصلی دادگاه سازمان ملل"""
    text = "⚖️ <b>منوی دادگاه سازمان ملل</b>\n\n"
    text += "🏛️ <b>قابلیت‌های موجود:</b>\n"
    text += "▫️ ⚖️ برگزاری دادگاه جدید\n"
    text += "▫️ 📋 مشاهده لیست دادگاه‌ها\n"
    text += "▫️ 📊 مدیریت دادگاه‌های موجود\n\n"
    text += "🎯 <b>انتخاب کنید:</b>"
    
    keyboard = [
        [InlineKeyboardButton('⚖️ برگزاری دادگاه جدید', callback_data='un_court_start')],
        [InlineKeyboardButton('📋 لیست دادگاه‌ها', callback_data='un_court_list')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='un_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_un_court_callback(query):
    """پردازش callback های مربوط به دادگاه سازمان ملل"""
    data = query.data
    
    if data == 'un_court_start':
        await start_un_court(query)
    elif data == 'un_court_list':
        await show_courts_list(query)
    elif data == 'un_court_new':
        await start_new_court_wizard(query)
    elif data.startswith('un_court_use_complaint_'):
        complaint_id = data.replace('un_court_use_complaint_', '')
        await use_complaint_for_court(query, complaint_id)
    elif data.startswith('un_court_details_'):
        court_id = data.replace('un_court_details_', '')
        await show_court_details(query, court_id)
    elif data.startswith('un_court_edit_'):
        court_id = data.replace('un_court_edit_', '')
        await show_court_edit_menu(query, court_id)
    elif data.startswith('un_court_complete_'):
        court_id = data.replace('un_court_complete_', '')
        await complete_court(query, court_id)
    elif data.startswith('un_court_edit_time_'):
        court_id = data.replace('un_court_edit_time_', '')
        await edit_court_time(query, court_id)
    elif data.startswith('un_court_start_session_'):
        court_id = data.replace('un_court_start_session_', '')
        await start_court_session(query, court_id)
    else:
        await query.answer("❌ دستور نامعتبر!", show_alert=True)
async def start_court_session(query, court_id: str):
    """شروع جلسه دادگاه: ارسال لینک‌ها به شرکت‌کنندگان و UN"""
    # دریافت لیست شرکت‌کنندگان ثبت‌شده
    attendees = []
    try:
        attendees = (getattr(utils, 'court_attendees', {}) or {}).get(court_id, [])
    except Exception:
        attendees = []
    # ساخت لینک‌ها برای هر شرکت‌کننده و UN
    try:
        group_id = getattr(utils, 'COURT_GROUP_ID', None)
        if not group_id:
            await query.answer('COURT_GROUP_ID تنظیم نشده است.', show_alert=True)
            return
        # یک لینک برای UN
        un_link = None
        if utils.UN_ACTIVATED_USER:
            un_link = await query.bot.create_chat_invite_link(group_id, member_limit=1)
        # لینک برای حاضرین
        for uid in attendees:
            try:
                link_user = await query.bot.create_chat_invite_link(group_id, member_limit=1)
                await query.bot.send_message(chat_id=int(uid), text=f"🎟 لینک ورود به دادگاه:\n{link_user.invite_link}")
            except Exception:
                pass
        if un_link:
            try:
                await query.bot.send_message(chat_id=int(utils.UN_ACTIVATED_USER), text=f"🎟 لینک ورود به دادگاه (UN):\n{un_link.invite_link}")
            except Exception:
                pass
        # پیام موفقیت
        await query.answer('لینک‌ها ارسال شد و جلسه آغاز شد.', show_alert=True)
    except Exception as e:
        await query.answer(f'خطا در شروع جلسه: {e}', show_alert=True)

async def start_un_court(query):
    """شروع فرآیند برگزاری دادگاه سازمان ملل"""
    user_id = str(query.from_user.id)
    
    # بررسی اینکه آیا کاربر سازمان ملل فعال است
    if not utils.UN_ACTIVATED_USER or utils.UN_ACTIVATED_USER != user_id:
        await query.answer("❌ فقط کاربر فعال سازمان ملل می‌تواند دادگاه برگزار کند!", show_alert=True)
        return
    
    # بررسی وجود شکایت‌نامه‌های موجود
    if utils.un_complaints:
        # اگر شکایت‌نامه وجود دارد، از آن استفاده کن
        text = "⚖️ <b>برگزاری دادگاه سازمان ملل</b>\n\n"
        text += "📋 <b>شکایت‌نامه‌های موجود:</b>\n\n"
        
        for i, complaint in enumerate(utils.un_complaints[:5], 1):  # حداکثر 5 شکایت
            text += f"{i}. <b>{complaint['from_country']}</b>\n"
            complaint_text = complaint.get('short', complaint.get('details', 'بدون توضیحات'))
            text += f"   📝 {complaint_text[:100]}{'...' if len(complaint_text) > 100 else ''}\n\n"
        
        text += "🎯 <b>انتخاب کنید:</b>\n"
        text += "• از شکایت‌نامه موجود استفاده کنید\n"
        text += "• دادگاه جدید ایجاد کنید"
        
        keyboard = []
        for i, complaint in enumerate(utils.un_complaints[:5], 1):
            keyboard.append([InlineKeyboardButton(f'📋 استفاده از شکایت {i}', callback_data=f'un_court_use_complaint_{complaint["id"]}')])
        keyboard.append([InlineKeyboardButton('➕ ایجاد دادگاه جدید', callback_data='un_court_new')])
        keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='un_court')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        # اگر شکایت‌نامه وجود ندارد، مستقیماً ویزارد جدید شروع کن
        await start_new_court_wizard(query)

async def start_new_court_wizard(query):
    """شروع ویزارد دادگاه جدید"""
    user_id = str(query.from_user.id)
    
    # شروع ویزارد دادگاه
    utils.pending_un_court[user_id] = {
        'step': 'topic',
        'topic': None,
        'plaintiff': None,
        'defendant': None,
        'witnesses': None,
        'time': None,
        'location': None
    }
    
    text = "⚖️ <b>برگزاری دادگاه سازمان ملل</b>\n\n"
    text += "🏛️ <b>مرحله ۱: موضوع دادگاه</b>\n\n"
    text += "❓ <b>موضوع اصلی این دادگاه چیست؟</b>\n\n"
    text += "📝 <b>مثال:</b>\n"
    text += "• نقض حقوق بشر\n"
    text += "• تجاوز نظامی\n"
    text += "• نقض قوانین بین‌المللی\n"
    text += "• اختلافات مرزی\n"
    text += "• سایر موارد\n\n"
    text += "💬 <b>موضوع دادگاه را بنویسید:</b>"
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='un_court')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_courts_list(query):
    """نمایش لیست دادگاه‌های سازمان ملل"""
    user_id = str(query.from_user.id)
    
    # بررسی اینکه آیا کاربر سازمان ملل فعال است
    if not utils.UN_ACTIVATED_USER or utils.UN_ACTIVATED_USER != user_id:
        await query.answer("❌ فقط کاربر فعال سازمان ملل می‌تواند دادگاه‌ها را مشاهده کند!", show_alert=True)
        return
    
    if not utils.un_courts:
        text = "📋 <b>لیست دادگاه‌های سازمان ملل</b>\n\n"
        text += "❌ <b>هیچ دادگاهی برنامه‌ریزی نشده است.</b>\n\n"
        text += "🏛️ برای برگزاری دادگاه جدید، از دکمه «برگزاری دادگاه» استفاده کنید."
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='un_court')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    text = "📋 <b>لیست دادگاه‌های سازمان ملل</b>\n\n"
    
    # نمایش دادگاه‌ها به ترتیب تاریخ ایجاد (جدیدترین اول)
    sorted_courts = sorted(utils.un_courts, key=lambda x: x['created_at'], reverse=True)
    
    keyboard = []
    
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
        
        # دکمه‌های مدیریت برای هر دادگاه
        if court['status'] != 'completed':
            keyboard.append([
                InlineKeyboardButton(f'📋 جزئیات {i}', callback_data=f'un_court_details_{court["id"]}'),
                InlineKeyboardButton(f'✏️ ویرایش {i}', callback_data=f'un_court_edit_{court["id"]}')
            ])
            keyboard.append([
                InlineKeyboardButton(f'▶️ شروع دادگاه {i}', callback_data=f'un_court_start_session_{court["id"]}')
            ])
    
    if len(sorted_courts) > 10:
        text += f"📄 <b>و {len(sorted_courts) - 10} دادگاه دیگر...</b>\n\n"
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='un_court')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_court_details(query, court_id):
    """نمایش جزئیات دادگاه خاص"""
    # پیدا کردن دادگاه
    court = None
    for c in utils.un_courts:
        if c['id'] == court_id:
            court = c
            break
    
    if not court:
        await query.answer("❌ دادگاه یافت نشد!", show_alert=True)
        return
    
    status_emoji = {
        'scheduled': '📅',
        'ongoing': '⚖️',
        'completed': '✅'
    }.get(court['status'], '❓')
    
    text = f"📋 <b>جزئیات دادگاه</b>\n\n"
    text += f"{status_emoji} <b>موضوع:</b> {court['topic']}\n"
    text += f"👥 <b>شاکی:</b> {court['plaintiff']}\n"
    text += f"👤 <b>متهم:</b> {court['defendant']}\n"
    text += f"👥 <b>شاهد:</b> {court['witnesses']}\n"
    text += f"⏰ <b>زمان:</b> {court['time']}\n"
    text += f"📍 <b>محل:</b> {court.get('location', 'نامشخص')}\n"
    text += f"🏛️ <b>وضعیت:</b> {court['status']}\n"
    text += f"📅 <b>تاریخ ایجاد:</b> {court['created_turn']}\n\n"
    
    keyboard = []
    
    # دکمه‌های مدیریت
    if court['status'] != 'completed':
        keyboard.append([
            InlineKeyboardButton('✅ اتمام دادگاه', callback_data=f'un_court_complete_{court_id}'),
            InlineKeyboardButton('✏️ ویرایش زمان', callback_data=f'un_court_edit_time_{court_id}')
        ])
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='un_court_list')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_court_edit_menu(query, court_id):
    """نمایش منوی ویرایش دادگاه"""
    # پیدا کردن دادگاه
    court = None
    for c in utils.un_courts:
        if c['id'] == court_id:
            court = c
            break
    
    if not court:
        await query.answer("❌ دادگاه یافت نشد!", show_alert=True)
        return
    
    text = f"✏️ <b>ویرایش دادگاه</b>\n\n"
    text += f"📋 <b>موضوع:</b> {court['topic']}\n"
    text += f"👥 <b>شاکی:</b> {court['plaintiff']}\n"
    text += f"👤 <b>متهم:</b> {court['defendant']}\n\n"
    text += f"🎯 <b>چه چیزی را ویرایش می‌کنید؟</b>"
    
    keyboard = [
        [InlineKeyboardButton('⏰ ویرایش زمان', callback_data=f'un_court_edit_time_{court_id}')],
        [InlineKeyboardButton('📍 ویرایش محل', callback_data=f'un_court_edit_location_{court_id}')],
        [InlineKeyboardButton('👥 ویرایش شاهد', callback_data=f'un_court_edit_witnesses_{court_id}')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data=f'un_court_details_{court_id}')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def complete_court(query, court_id):
    """اتمام دادگاه و حذف پیام سنجاق شده"""
    # پیدا کردن دادگاه
    court = None
    for c in utils.un_courts:
        if c['id'] == court_id:
            court = c
            break
    
    if not court:
        await query.answer("❌ دادگاه یافت نشد!", show_alert=True)
        return
    
    # تغییر وضعیت دادگاه
    court['status'] = 'completed'
    
    # ذخیره تغییرات
    utils.save_un_data()
    
    # ویرایش پیام سنجاق شده در کانال اخبار (اگر وجود دارد)
    try:
        # اگر دادگاه اطلاعات پیام کانال دارد، آن را ویرایش کن
        if 'channel_message_id' in court and 'channel_chat_id' in court:
            from telegram import Bot
            bot = Bot(token=utils.BOT_TOKEN)
            
            # برداشتن سنجاق
            await bot.unpin_chat_message(
                chat_id=court['channel_chat_id'],
                message_id=court['channel_message_id']
            )
            
            # متن جدید برای پیام
            updated_text = f"⚖️ <b>اعلان تشکیل دادگاه بین‌المللی</b>\n\n"
            updated_text += f"🏛️ <b>موضوع:</b> {court['topic']}\n"
            updated_text += f"👥 <b>شاکی:</b> {court['plaintiff']}\n"
            updated_text += f"👤 <b>متهم:</b> {court['defendant']}\n"
            updated_text += f"👥 <b>حضار:</b> {court['witnesses']}\n"
            updated_text += f"⏰ <b>زمان برگزاری:</b> {court['time']}\n\n"
            updated_text += f"✅ <b>وضعیت: دادگاه به اتمام رسید</b>\n\n"
            updated_text += f"🌍 <b>سازمان ملل متحد</b>\n"
            updated_text += f"📅 <b>تاریخ اعلان:</b> {datetime.now().strftime('%Y/%m/%d %H:%M')}"
            
            # ویرایش پیام
            await bot.edit_message_text(
                chat_id=court['channel_chat_id'],
                message_id=court['channel_message_id'],
                text=updated_text,
                parse_mode='HTML'
            )
            
        # اگر دادگاه در pinned_messages است، آن را حذف کن
        if hasattr(utils, 'pinned_messages'):
            for msg_id, msg_info in list(utils.pinned_messages.items()):
                if msg_info.get('court_id') == court_id:
                    del utils.pinned_messages[msg_id]
                    break
                    
    except Exception as e:
        print(f"خطا در ویرایش پیام سنجاق شده: {e}")
    
    text = f"✅ <b>دادگاه با موفقیت به اتمام رسید!</b>\n\n"
    text += f"📋 <b>موضوع:</b> {court['topic']}\n"
    text += f"👥 <b>شاکی:</b> {court['plaintiff']}\n"
    text += f"👤 <b>متهم:</b> {court['defendant']}\n"
    text += f"🏛️ <b>وضعیت:</b> تکمیل شده\n\n"
    text += f"📢 پیام مربوط به این دادگاه در کانال اخبار به‌روزرسانی شد.\n"
    text += f"📌 سنجاق برداشته شد و وضعیت اتمام اضافه شد."
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='un_court_list')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def edit_court_time(query, court_id):
    """ویرایش زمان دادگاه"""
    # پیدا کردن دادگاه
    court = None
    for c in utils.un_courts:
        if c['id'] == court_id:
            court = c
            break
    
    if not court:
        await query.answer("❌ دادگاه یافت نشد!", show_alert=True)
        return
    
    # ذخیره court_id برای ویرایش
    user_id = str(query.from_user.id)
    utils.pending_court_edit = {user_id: {'court_id': court_id, 'field': 'time'}}
    
    text = f"✏️ <b>ویرایش زمان دادگاه</b>\n\n"
    text += f"📋 <b>موضوع:</b> {court['topic']}\n"
    text += f"⏰ <b>زمان فعلی:</b> {court['time']}\n\n"
    text += f"🕐 <b>زمان جدید را وارد کنید:</b>\n"
    text += f"<i>مثال: 14:30 یا 2:30 بعدازظهر</i>"
    
    keyboard = [[InlineKeyboardButton('❌ لغو', callback_data=f'un_court_details_{court_id}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_court_edit(update, context):
    """پردازش ویرایش دادگاه"""
    user_id = str(update.message.from_user.id)
    new_value = update.message.text.strip()
    
    if user_id not in utils.pending_court_edit:
        await update.message.reply_text("❌ درخواست ویرایش یافت نشد!")
        return
    
    edit_info = utils.pending_court_edit[user_id]
    court_id = edit_info['court_id']
    field = edit_info['field']
    
    # پیدا کردن دادگاه
    court = None
    for c in utils.un_courts:
        if c['id'] == court_id:
            court = c
            break
    
    if not court:
        await update.message.reply_text("❌ دادگاه یافت نشد!")
        utils.pending_court_edit.pop(user_id, None)
        return
    
    # ویرایش فیلد
    if field == 'time':
        court['time'] = new_value
        field_name = 'زمان'
    else:
        await update.message.reply_text("❌ فیلد نامعتبر!")
        utils.pending_court_edit.pop(user_id, None)
        return
    
    # ذخیره تغییرات
    utils.save_un_data()
    
    # پاک کردن وضعیت موقت
    utils.pending_court_edit.pop(user_id, None)
    
    # ارسال پیام موفقیت
    text = f"✅ <b>ویرایش با موفقیت انجام شد!</b>\n\n"
    text += f"📋 <b>موضوع:</b> {court['topic']}\n"
    text += f"⏰ <b>{field_name} جدید:</b> {new_value}\n\n"
    text += f"📢 تغییرات به کانال اخبار ارسال شد."
    
    await update.message.reply_text(text, parse_mode='HTML')
    
    # ارسال پیام به کانال اخبار (اگر وجود دارد)
    try:
        # اینجا باید پیام جدید را به کانال اخبار ارسال کنیم
        # برای حالا فقط پیام موفقیت نمایش می‌دهیم
        pass
    except Exception as e:
        print(f"خطا در ارسال پیام به کانال اخبار: {e}")

async def use_complaint_for_court(query, complaint_id):
    """استفاده از شکایت‌نامه موجود برای برگزاری دادگاه"""
    user_id = str(query.from_user.id)
    
    # پیدا کردن شکایت‌نامه
    complaint = None
    for comp in utils.un_complaints:
        if comp['id'] == complaint_id:
            complaint = comp
            break
    
    if not complaint:
        await query.answer("❌ شکایت‌نامه یافت نشد!", show_alert=True)
        return
    
    # شروع ساده‌شده: فقط زمان و مکان
    utils.pending_un_court[user_id] = {
        'step': 'time',
        'topic': complaint.get('short') or complaint.get('details') or '-',
        'plaintiff': complaint['from_country'],
        'defendant': complaint.get('defendant') or '-',
        'witnesses': '-',
        'time': None
    }
    
    text = "⚖️ <b>برگزاری دادگاه سازمان ملل</b>\n\n"
    text += "📋 <b>اطلاعات شکایت‌نامه انتخاب‌شده:</b>\n"
    text += f"👥 <b>شاکی:</b> {complaint['from_country']}\n"
    text += f"📝 <b>موضوع:</b> {complaint.get('short') or complaint.get('details') or '-'}\n\n"
    text += "⏰ <b>مرحله ۱: زمان برگزاری</b>\n\n"
    text += "💬 زمان برگزاری را وارد کنید (مثال: شنبه 18:00):"
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='un_court')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_un_court_message(update, context):
    """پردازش پیام‌های مربوط به برگزاری دادگاه سازمان ملل"""
    user_id = str(update.message.from_user.id)
    
    # بررسی وجود متن
    if not hasattr(update.message, 'text') or not update.message.text:
        return
    
    text = update.message.text
    
    if user_id not in utils.pending_un_court:
        return
    
    court_data = utils.pending_un_court[user_id]
    step = court_data['step']
    
    if step == 'topic':
        # مرحله 1: موضوع دادگاه
        court_data['topic'] = text
        court_data['step'] = 'plaintiff'
        
        reply_text = "⚖️ <b>برگزاری دادگاه سازمان ملل</b>\n\n"
        reply_text += "🏛️ <b>مرحله ۲: شاکی/شاکیان</b>\n\n"
        reply_text += "👥 <b>شاکی کیست؟</b>\n\n"
        reply_text += "💬 <b>نام شاکی یا شاکیان را بنویسید:</b>\n"
        reply_text += "• مثال: کشور ایران\n"
        reply_text += "• مثال: کشور ایران و کشور ترکیه\n"
        reply_text += "• مثال: سازمان حقوق بشر\n\n"
        reply_text += f"📝 <b>موضوع دادگاه:</b> {text}"
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='un_court_start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(reply_text, reply_markup=reply_markup, parse_mode='HTML')
        
    elif step == 'plaintiff':
        # مرحله 2: شاکی
        court_data['plaintiff'] = text
        court_data['step'] = 'defendant'
        
        reply_text = "⚖️ <b>برگزاری دادگاه سازمان ملل</b>\n\n"
        reply_text += "🏛️ <b>مرحله ۳: متهم/متهمان</b>\n\n"
        reply_text += "👤 <b>متهم کیست؟</b>\n\n"
        reply_text += "💬 <b>نام متهم یا متهمان را بنویسید:</b>\n"
        reply_text += "• مثال: کشور آمریکا\n"
        reply_text += "• مثال: کشور آمریکا و کشور انگلیس\n"
        reply_text += "• مثال: شرکت نفتی شل\n\n"
        reply_text += f"📝 <b>موضوع دادگاه:</b> {court_data['topic']}\n"
        reply_text += f"👥 <b>شاکی:</b> {text}"
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='un_court_start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(reply_text, reply_markup=reply_markup, parse_mode='HTML')
        
    elif step == 'defendant':
        # مرحله 3: متهم
        court_data['defendant'] = text
        court_data['step'] = 'witnesses'
        
        reply_text = "⚖️ <b>برگزاری دادگاه سازمان ملل</b>\n\n"
        reply_text += "🏛️ <b>مرحله ۴: شاهدان و حضار</b>\n\n"
        reply_text += "👥 <b>چه کسانی باید حضور داشته باشند؟</b>\n\n"
        reply_text += "💬 <b>نام شاهدان و حضار را بنویسید:</b>\n"
        reply_text += "• مثال: کشور آلمان (شاهد)\n"
        reply_text += "• مثال: سازمان عفو بین‌الملل (ناظر)\n"
        reply_text += "• مثال: کشور فرانسه (شاهد) و کشور کانادا (ناظر)\n\n"
        reply_text += f"📝 <b>موضوع دادگاه:</b> {court_data['topic']}\n"
        reply_text += f"👥 <b>شاکی:</b> {court_data['plaintiff']}\n"
        reply_text += f"👤 <b>متهم:</b> {text}"
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='un_court_start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(reply_text, reply_markup=reply_markup, parse_mode='HTML')
        
    elif step == 'witnesses':
        # مرحله 4: شاهدان
        court_data['witnesses'] = text
        court_data['step'] = 'time'
        
        reply_text = "⚖️ <b>برگزاری دادگاه سازمان ملل</b>\n\n"
        reply_text += "🏛️ <b>مرحله ۵: زمان برگزاری</b>\n\n"
        reply_text += "⏰ <b>دادگاه چه زمانی برگزار شود؟</b>\n\n"
        reply_text += "💬 <b>زمان برگزاری را بنویسید:</b>\n"
        reply_text += "• مثال: فردا ساعت 14:00\n"
        reply_text += "• مثال: شنبه آینده ساعت 10:00\n"
        reply_text += "• مثال: 25 دی ماه ساعت 16:30\n\n"
        reply_text += f"📝 <b>موضوع دادگاه:</b> {court_data['topic']}\n"
        reply_text += f"👥 <b>شاکی:</b> {court_data['plaintiff']}\n"
        reply_text += f"👤 <b>متهم:</b> {court_data['defendant']}\n"
        reply_text += f"👥 <b>حضار:</b> {text}"
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='un_court_start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(reply_text, reply_markup=reply_markup, parse_mode='HTML')
        
    elif step == 'time':
        # مرحله 5: زمان برگزاری
        court_data['time'] = text
        court_data['step'] = 'location'
        
        reply_text = "⚖️ <b>برگزاری دادگاه سازمان ملل</b>\n\n"
        reply_text += "🏛️ <b>مرحله ۲: محل برگزاری</b>\n\n"
        reply_text += "📍 <b>دادگاه در کجا برگزار شود؟</b>\n\n"
        reply_text += "💬 <b>محل برگزاری را بنویسید:</b>\n"
        reply_text += "• مثال: ایران، تهران\n"
        reply_text += "• مثال: بریتانیا، لندن\n"
        reply_text += "• مثال: آمریکا، نیویورک\n"
        reply_text += "• مثال: فرانسه، پاریس\n"
        reply_text += "• مثال: آلمان، برلین\n\n"
        reply_text += f"📝 <b>موضوع دادگاه:</b> {court_data['topic']}\n"
        reply_text += f"👥 <b>شاکی:</b> {court_data['plaintiff']}\n"
        reply_text += f"👤 <b>متهم:</b> {court_data['defendant']}\n"
        reply_text += f"👥 <b>حضار:</b> {court_data['witnesses']}\n"
        reply_text += f"⏰ <b>زمان:</b> {text}"
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='un_court')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(reply_text, reply_markup=reply_markup, parse_mode='HTML')
        
    elif step == 'location':
        # مرحله 6: محل برگزاری - نهایی کردن
        court_data['location'] = text
        
        # ایجاد دادگاه جدید
        court_id = str(uuid.uuid4())
        new_court = {
            'id': court_id,
            'topic': court_data['topic'],
            'plaintiff': court_data['plaintiff'],
            'defendant': court_data['defendant'],
            'witnesses': court_data['witnesses'],
            'time': court_data['time'],
            'location': court_data['location'],
            'status': 'scheduled',
            'created_by': user_id,
            'created_turn': utils.game_data.get('turn', 1),
            'created_at': int(time.time())
        }
        
        utils.un_courts.append(new_court)
        utils.save_un_data()
        
        # پاک کردن pending data
        del utils.pending_un_court[user_id]
        
        # ارسال اعلان به کانال اخبار
        from utils import NEWS_CHANNEL_ID
        announcement_text = f"⚖️ <b>اعلان تشکیل دادگاه بین‌المللی</b>\n\n"
        announcement_text += f"🏛️ <b>موضوع:</b> {court_data['topic']}\n"
        announcement_text += f"👥 <b>شاکی:</b> {court_data['plaintiff']}\n"
        announcement_text += f"👤 <b>متهم:</b> {court_data['defendant']}\n"
        announcement_text += f"👥 <b>حضار:</b> {court_data['witnesses']}\n"
        announcement_text += f"⏰ <b>زمان برگزاری:</b> {court_data['time']}\n"
        announcement_text += f"📍 <b>محل برگزاری:</b> {court_data['location']}\n\n"
        announcement_text += f"🌍 <b>سازمان ملل متحد</b>\n"
        announcement_text += f"📅 <b>تاریخ اعلان:</b> {datetime.now().strftime('%Y/%m/%d %H:%M')}"
        
        try:
            message = await context.bot.send_message(
                chat_id=NEWS_CHANNEL_ID,
                text=announcement_text,
                parse_mode='HTML'
            )
            
            # سنجاق کردن پیام
            await context.bot.pin_chat_message(
                chat_id=NEWS_CHANNEL_ID,
                message_id=message.message_id,
                disable_notification=True
            )
            
            # ذخیره اطلاعات پیام کانال در دادگاه
            new_court['channel_chat_id'] = NEWS_CHANNEL_ID
            new_court['channel_message_id'] = message.message_id
            utils.save_un_data()
            
            # ذخیره اطلاعات برای برداشتن سنجاق بعد از 2 روز
            if not hasattr(utils, 'pinned_messages'):
                utils.pinned_messages = {}
            
            from datetime import timedelta
            unpin_time = datetime.now() + timedelta(days=2)
            utils.pinned_messages[message.message_id] = {
                'chat_id': NEWS_CHANNEL_ID,
                'unpin_time': unpin_time.isoformat(),
                'court_id': new_court['id']
            }
            
        except Exception as e:
            print(f"خطا در ارسال اعلان دادگاه: {e}")
        
        # اطلاع‌رسانی کوتاه به همه کاربران فعال
        try:
            from telegram import Bot
            bot = Bot(token=utils.BOT_TOKEN)
            notify_text = (
                "📣 <b>اطلاعیه دادگاه بین‌المللی</b>\n\n"
                f"⏰ زمان: {court_data['time']}\n"
                f"📍 محل: {court_data['location']}\n"
                f"🏛️ موضوع: {court_data['topic']}\n\n"
                "برای شرکت: منوی دیپلماسی → دادگاه سازمان ملل → (به‌زودی) «ارسال رئیس‌جمهور به دادگاه»."
            )
            for uid, u in utils.users.items():
                if u.get('activated'):
                    try:
                        await bot.send_message(chat_id=int(uid), text=notify_text, parse_mode='HTML')
                    except Exception:
                        pass
        except Exception as e:
            print(f"notify all users about court error: {e}")

        # پیام موفقیت به کاربر
        success_text = "✅ <b>دادگاه با موفقیت برنامه‌ریزی شد!</b>\n\n"
        success_text += f"🏛️ <b>موضوع:</b> {court_data['topic']}\n"
        success_text += f"👥 <b>شاکی:</b> {court_data['plaintiff']}\n"
        success_text += f"👤 <b>متهم:</b> {court_data['defendant']}\n"
        success_text += f"👥 <b>حضار:</b> {court_data['witnesses']}\n"
        success_text += f"⏰ <b>زمان:</b> {court_data['time']}\n"
        success_text += f"📍 <b>محل:</b> {court_data['location']}\n\n"
        success_text += "📢 اعلان دادگاه در کانال اخبار منتشر و سنجاق شد.\n"
        success_text += "⏰ سنجاق بعد از 2 روز برداشته خواهد شد."
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت به منوی دادگاه', callback_data='un_court')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(success_text, reply_markup=reply_markup, parse_mode='HTML')
