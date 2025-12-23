import asyncio
import random
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import utils

# لیست فایل‌های GIF
GIF_FILES = [
    "https://t.me/TextEmpire_IR/160",
    "https://t.me/TextEmpire_IR/163",
    "https://t.me/TextEmpire_IR/148",
    "https://t.me/TextEmpire_IR/162",
    "https://t.me/TextEmpire_IR/168",
    "https://t.me/TextEmpire_IR/169",
    "https://t.me/TextEmpire_IR/165",
    "https://t.me/TextEmpire_IR/170",
    "https://t.me/TextEmpire_IR/166",
    "https://t.me/TextEmpire_IR/167",
    "https://t.me/TextEmpire_IR/149",
    "https://t.me/TextEmpire_IR/156",
    "https://t.me/TextEmpire_IR/174",  # گیف آماده‌سازی حمله موشکی
    "https://t.me/TextEmpire_IR/175",  # گیف شلیک موشک
    "https://t.me/TextEmpire_IR/161",  # گیف شکست حمله موشکی
    "https://t.me/TextEmpire_IR/177"   # گیف تغییر نوع تجارت
]

# لیست گیف‌های جنگ زمینی
GROUND_BATTLE_GIFS = [
    "https://t.me/TextEmpire_IR/173",
    "https://t.me/TextEmpire_IR/172"
]

async def send_media_safe(bot, chat_id, file_url, caption=None, parse_mode=None):
    """ارسال ایمن فایل (تصویر یا GIF)"""
    try:
        # تشخیص نوع فایل بر اساس URL
        if (file_url in GIF_FILES or 
            file_url in GROUND_BATTLE_GIFS or 
            file_url == "https://t.me/TextEmpire_IR/160"):
            # برای GIF ها از send_animation استفاده کن
            await bot.send_animation(chat_id=chat_id, animation=file_url, caption=caption, parse_mode=parse_mode)
        else:
            # برای تصاویر از send_photo استفاده کن
            await bot.send_photo(chat_id=chat_id, photo=file_url, caption=caption, parse_mode=parse_mode)
    except Exception as e:
        print(f"خطا در ارسال فایل {file_url}: {e}")
        # اگر خطا داد، سعی کن با send_document
        try:
            await bot.send_document(chat_id=chat_id, document=file_url, caption=caption, parse_mode=parse_mode)
        except Exception as e2:
            print(f"خطا در ارسال document {file_url}: {e2}")
from utils import NEWS_CHANNEL_ID, NAVAL_ATTACK_CHANNEL_ID, pending_naval_attack, pending_air_attack, SEA_BORDER_COUNTRIES, war_declarations, LAND_BORDERS, users, pending_ground_attack, save_users, simulate_ground_battle, initialize_user_resources, naval_attacks, naval_attack_counter, pending_sea_raid, pending_trades, military_technologies, pending_military_production, COUNTRY_POPULATIONS, has_sea_border, transfer_alliance_on_leader_loss
import json
import os

# تابع امن برای ویرایش پیام از bot.py import می‌شود

# متغیرهای سیستم حمله زمینی
ground_attacks = {}  # {attack_id: {'attacker_id': user_id, 'target_id': target_id, 'attacker_forces': {...}, 'attacker_power': power, 'target_power': power, 'start_time': timestamp, 'phase': 0}}
# فایل‌های پایداری حملات
GROUND_ATTACKS_FILE = 'ground_attacks.json'
NAVAL_ATTACKS_FILE = 'naval_attacks_active.json'

def save_ground_attacks():
    try:
        with open(GROUND_ATTACKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(ground_attacks, f, ensure_ascii=False, indent=2)
    except Exception as _:
        pass

def load_ground_attacks():
    global ground_attacks
    try:
        with open(GROUND_ATTACKS_FILE, 'r', encoding='utf-8') as f:
            ground_attacks = json.load(f)
    except Exception:
        ground_attacks = {}

def save_naval_attacks():
    try:
        with open(NAVAL_ATTACKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(naval_attacks, f, ensure_ascii=False, indent=2)
    except Exception as _:
        pass

def load_naval_attacks():
    try:
        if os.path.exists(NAVAL_ATTACKS_FILE):
            with open(NAVAL_ATTACKS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    naval_attacks.update(data)
    except Exception:
        pass

async def resume_battles_after_restart(context):
    """پس از روشن شدن ربات، حملات ذخیره‌شده را بارگذاری و بر اساس منطق جدید زمینی/دریایی زمان‌بندی می‌کند."""
    # بارگذاری از دیسک
    load_ground_attacks()
    load_naval_attacks()
    now = time.time()
    # ادامه جنگ‌های زمینی (حل در 5 دقیقه پس از start_time)
    for aid, ad in list(ground_attacks.items()):
        started = float(ad.get('start_time', now))
        elapsed = max(0, now - started)
        remaining = max(1, int(300 - elapsed)) if elapsed < 300 else 1
        context.job_queue.run_once(lambda ctx, _aid=aid: asyncio.create_task(resolve_ground_battle_simple(_aid, ctx)), remaining)
    # ادامه حملات دریایی
    for aid, ad in list(naval_attacks.items()):
        phase = int(ad.get('phase', 0))
        started = float(ad.get('start_time', now))
        if phase <= 0:
            delay = max(1, int(120 - (now - started)))
            context.job_queue.run_once(lambda ctx, _aid=aid: naval_battle_phase_1(_aid, ctx), delay)
        elif phase == 1:
            delay = 120
            context.job_queue.run_once(lambda ctx, _aid=aid: naval_battle_phase_2(_aid, ctx), max(1, delay))
        elif phase == 2:
            delay = 120
            context.job_queue.run_once(lambda ctx, _aid=aid: naval_battle_phase_3(_aid, ctx), max(1, delay))

# فرض: این متغیرها باید از bot.py import شوند یا global باشند:
# users, pending_ground_attack, save_users, NEWS_CHANNEL_ID
async def process_attack_forces(message, context):
    user_id = str(message.from_user.id)
    if user_id not in pending_ground_attack:
        return
    
    attack_data = pending_ground_attack[user_id]
    user_resources = utils.users[user_id]['resources']
    
    try:
        # پردازش متن ارسالی
        lines = message.text.strip().split('\n')
        requested_forces = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # تبدیل نام نیرو به کلید دیتابیس
            force_mapping = {
                'سربازان': 'soldiers',
                'نیروی ویژه': 'special_forces',
                'تانک': 'tanks',
                'نفربر': 'armored_vehicles',
                'توپخانه': 'artillery',
                'ربات جنگی': 'war_robots'
            }
            
            if ':' in line:
                force_name, amount_str = line.split(':', 1)
                force_name = force_name.strip()
                amount_str = amount_str.strip()
                
                # بررسی دقیق‌تر نام نیرو (حذف فاصله‌های اضافی و کاراکترهای نامرئی)
                force_name_clean = force_name.replace('\u200c', '').replace('\u200d', '').strip()
                
                if force_name_clean in force_mapping:
                    try:
                        amount = int(amount_str.replace(',', ''))
                        if amount > 0:
                            requested_forces[force_mapping[force_name_clean]] = amount
                    except ValueError:
                        continue
        
        if not requested_forces:
            await message.reply_text('❌ هیچ نیروی معتبری یافت نشد. لطفاً دوباره تلاش کنید.')
            return
        
        # بررسی موجودی نیروها
        insufficient_forces = []
        for force, requested_amount in requested_forces.items():
            available = user_resources.get(force, 0)
            if available < requested_amount:
                insufficient_forces.append(f"{force}: {available}/{requested_amount}")
        
        if insufficient_forces:
            await message.reply_text(f'❌ نیروهای کافی ندارید:\n' + '\n'.join(insufficient_forces))
            return
        
        # کسر نیروها از موجودی
        for force, amount in requested_forces.items():
            user_resources[force] -= amount
        
        # علامت‌گذاری به‌عنوان کسرشده و ذخیره نیروهای ارسالی برای بازگردانی بعدی
        attack_data['forces_deducted'] = True
        attack_data['attacker_forces'] = dict(requested_forces)
        
        # ذخیره تغییرات
        from utils import save_users
        save_users()
        
        # ثبت نیروهای انتخاب‌شده در attack_data تا در شروع جنگ استفاده شوند
        attack_data['forces'] = requested_forces
        pending_ground_attack[user_id] = attack_data
        
        # شروع جنگ زمینی
        await start_ground_battle(message, attack_data, context)
        
    except Exception as e:
        print(f"خطا در پردازش نیروهای زمینی: {e}")
        await message.reply_text('❌ خطا در پردازش اطلاعات. لطفاً دوباره تلاش کنید.')

async def start_ground_battle(message, attack_data, context):
    user_id = str(message.from_user.id)
    target_country = attack_data['target']
    
    # استفاده از target_id ذخیره شده یا پیدا کردن آن
    target_id = attack_data.get('target_id')
    if not target_id:
        # پیدا کردن target_id با تطبیق مقاوم در برابر ایموجی/فاصله/حروف کوچک-بزرگ
        try:
            import re
            def normalize(name: str) -> str:
                if not isinstance(name, str):
                    name = str(name)
                # حذف کاراکترهای نامرئی و ایموجی پرچم/سایر علائم
                name = name.replace('\u200c', '').replace('\u200d', '')
                # حذف هر چیزی به جز حروف، اعداد و فاصله
                name = re.sub(r'[^\w\s\u0600-\u06FF]', '', name)
                return re.sub(r'\s+', ' ', name).strip().lower()
            target_norm = normalize(target_country)
            # تطبیق مستقیم نرمال‌شده
            for uid, user_data in utils.users.items():
                if normalize(user_data.get('country', '')) == target_norm:
                    target_id = uid
                    break
            # اگر پیدا نشد، تطبیق شامل‌گونه
            if not target_id:
                for uid, user_data in utils.users.items():
                    cn = normalize(user_data.get('country', ''))
                    if target_norm and target_norm in cn:
                        target_id = uid
                        break
        except Exception:
            pass
    
    if not target_id:
        await message.reply_text('❌ کشور هدف یافت نشد.')
        return

    # جلوگیری از حمله به کشوری که قبلاً فتح شده است
    try:
        if utils.users.get(target_id, {}).get('conquered_by'):
            conqueror = utils.users[target_id].get('conquered_by')
            await message.reply_text(f"❌ حمله ناموفق!\n\nکشور {target_country} قبلاً توسط {conqueror} فتح شده است و قابل هدف قرار دادن نیست.")
            return
    except Exception:
        pass

    # جلوگیری از حمله به کشوری که صلح اجباری فعال دارد
    try:
        from bot import is_user_peace_protected
        if is_user_peace_protected(target_id):
            turns = utils.users[target_id].get('diplomacy', {}).get('forced_peace_turns', 0)
            # بازگرداندن نیروهای هوایی اعزامی به دلیل صلح اجباری
            try:
                forces = attack_data.get('forces', {}) or {}
                if forces:
                    for k, amount in forces.items():
                        try:
                            amt = int(amount)
                        except Exception:
                            amt = 0
                        if amt > 0:
                            # بازگرداندن به موجودی کاربر
                            utils.users[user_id]['resources'][k] = int(utils.users[user_id]['resources'].get(k, 0)) + amt
                    save_users()
            except Exception as _e:
                print(f"[air_refund] error on forced_peace refund: {_e}")
            await message.reply_text(
                f"❌ حمله ناموفق!\n\n🤝 کشور {target_country} تحت صلح اجباری است.\n⏰ {turns} نوبت باقی‌مانده"
            )
            return
    except Exception:
        pass
    
    # دریافت نیروهای حمله‌کننده
    attacker_forces = attack_data.get('forces', {})
    
    # کسر نیروها قبلاً در process_attack_forces انجام می‌شود؛ از کسر دوباره جلوگیری می‌کنیم
    
    # دریافت نیروهای دفاع‌کننده
    initialize_user_resources(target_id)
    target_resources = utils.users[target_id]['resources']
    target_forces = {
        'soldiers': target_resources.get('soldiers', 0),
        'special_forces': target_resources.get('special_forces', 0),
        'tanks': target_resources.get('tanks', 0),
        'armored_vehicles': target_resources.get('armored_vehicles', 0),
        'artillery': target_resources.get('artillery', 0),
        'war_robots': target_resources.get('war_robots', 0)
    }
    
    # شبیه‌سازی جنگ (نسخه utils با attacker_id و defender_id)
    try:
        from utils import simulate_ground_battle as utils_sim_ground
        battle_result = utils_sim_ground(attacker_forces, user_id, target_id)
    except Exception:
        battle_result = simulate_ground_battle(attacker_forces, user_id)
    
    # ساخت شناسه و ثبت حمله برای فازها
    if 'ground_attack_counter' not in globals():
        global ground_attack_counter
        ground_attack_counter = 0
    ground_attack_counter += 1
    attack_id = f"ground_{ground_attack_counter}"
    # محاسبه قدرت اولیه دو طرف با درنظرگرفتن تکنولوژی/حکومت مشابه utils
    try:
        from utils import calculate_military_power_with_tech
        attacker_power = calculate_military_power_with_tech(user_id)
        target_power = calculate_military_power_with_tech(target_id)
    except Exception:
        attacker_power = battle_result.get('power', 0)
        target_power = sum(target_forces.values())
    ground_attacks[attack_id] = {
        'attacker_id': user_id,
        'target_id': target_id,
        'attacker_forces': attacker_forces,
        'target_forces': target_forces,
        'attacker_power': attacker_power,
        'original_attacker_power': attacker_power,  # ذخیره قدرت اولیه برای محاسبه تلفات
        'target_power': target_power,
        'start_time': time.time(),
        'phase': 0
    }
    save_ground_attacks()
    
    # اطلاع‌رسانی فوری شروع جنگ
    try:
        await context.bot.send_message(chat_id=int(user_id), text=f"🪖 حمله زمینی به {target_country} آغاز شد. نتایج مرحله‌ای طی چند دقیقه اعلام می‌شود. شناسه نبرد: {attack_id}")
    except Exception:
        pass
    try:
        attacker_country = utils.users[user_id]['country']
        await context.bot.send_message(chat_id=int(target_id), text=f"⚠️ {attacker_country} به شما حمله زمینی کرد! نتایج مرحله‌ای طی چند دقیقه اعلام می‌شود. شناسه نبرد: {attack_id}")
    except Exception:
        pass

    # تنظیم روابط: پس از اعلان جنگ، روابط دو کشور = -100
    try:
        from utils import set_mutual_relation
        set_mutual_relation(user_id, target_id, -100)
    except Exception as _:
        pass
    
    # ثبت اعلان جنگ دوطرفه
    if user_id not in war_declarations:
        war_declarations[user_id] = []
    if target_country not in war_declarations[user_id]:
        war_declarations[user_id].append(target_country)

    # برنامه‌ریزی مراحل جنگ
    await schedule_ground_battle_phases(attack_id, context)
    
    # پاک‌سازی حالت انتظار
    if user_id in pending_ground_attack:
        del pending_ground_attack[user_id]
async def schedule_ground_battle_phases(attack_id, context):
    """زمان‌بندی مراحل جنگ زمینی"""
    try:
        # اطلاع‌رسانی زمان‌بندی فاز 1
        try:
            if attack_id in ground_attacks:
                ad = ground_attacks[attack_id]
                user_id = ad.get('attacker_id')
                target_id = ad.get('target_id')
                attacker_country = utils.users.get(user_id, {}).get('country', 'نامشخص')
                target_country = utils.users.get(target_id, {}).get('country', 'نامشخص')
                msg = (
                    f"🕒 آغاز جنگ زمینی برنامه‌ریزی شد\n\n"
                    f"⚔️ {attacker_country} → {target_country}\n"
                    f"🆔 شناسه نبرد: {attack_id}\n"
                    f"⏳ شروع فاز 1 تا 2 دقیقه آینده"
                )
                try:
                    await context.bot.send_message(chat_id=int(user_id), text=msg)
                except Exception:
                    pass
                try:
                    await context.bot.send_message(chat_id=int(target_id), text=msg)
                except Exception:
                    pass
                try:
                    # انتخاب گیف رندوم برای جنگ زمینی و ارسال به کانال اخبار
                    random_gif = random.choice(GROUND_BATTLE_GIFS)
                    caption = f"🕒 برنامه‌ریزی جنگ زمینی | {attacker_country} vs {target_country}\n🆔 {attack_id}"
                    # ارسال مستقیم برای گرفتن file_id
                    msg = await context.bot.send_animation(chat_id=NEWS_CHANNEL_ID, animation=random_gif, caption=caption, parse_mode='HTML')
                    # استفاده از همان file_id برای ارسال به هر دو طرف
                    try:
                        file_id = getattr(msg, 'animation', None).file_id if hasattr(msg, 'animation') and msg.animation else None
                    except Exception:
                        file_id = None
                    if file_id:
                        try:
                            await context.bot.send_animation(chat_id=int(user_id), animation=file_id, caption=caption, parse_mode='HTML')
                        except Exception:
                            pass
                        try:
                            await context.bot.send_animation(chat_id=int(target_id), animation=file_id, caption=caption, parse_mode='HTML')
                        except Exception:
                            pass
                except Exception as e:
                    print(f"خطا در ارسال گیف جنگ زمینی: {e}")
                    # fallback به پیام متنی
                    try:
                        await context.bot.send_message(chat_id=NEWS_CHANNEL_ID, text=f"🕒 برنامه‌ریزی جنگ زمینی | {attacker_country} vs {target_country}\n🆔 {attack_id}")
                    except Exception:
                        pass
        except Exception:
            pass
        context.job_queue.run_once(
            lambda ctx: ground_battle_phase_1(attack_id, ctx),
            2 * 60
        )
        print(f"مرحله اول جنگ زمینی {attack_id} زمان‌بندی شد")
    except Exception as e:
        print(f"خطا در زمان‌بندی مراحل جنگ زمینی {attack_id}: {e}")
        raise

async def ground_battle_phase_1(attack_id, context):
    """مرحله اول جنگ زمینی"""
    try:
        if attack_id not in ground_attacks:
            print(f"جنگ زمینی {attack_id} یافت نشد")
            return
        
        attack_data = ground_attacks[attack_id]
        user_id = attack_data['attacker_id']
        target_id = attack_data['target_id']
        user_country = utils.users[user_id]['country']
        target_country = utils.users[target_id]['country']
        
        # سیستم شانس رندوم برای تلفات (25-40%)
        attacker_loss_rate = random.uniform(0.25, 0.40)
        target_loss_rate = random.uniform(0.25, 0.40)
        
        target_losses_30 = int(attack_data['target_power'] * target_loss_rate)
        attacker_losses_30 = int(attack_data['attacker_power'] * attacker_loss_rate)
        
        attack_data['target_power'] -= target_losses_30
        attack_data['attacker_power'] -= attacker_losses_30
        attack_data['phase'] = 1
        save_ground_attacks()
        
        phase1_photo = "https://t.me/TextEmpire_IR/57"  # فایل ایدی مرحله اول
        phase1_text = f"⚔️ <b>مرحله اول جنگ زمینی!</b>\n\nنیروهای {user_country} ({utils.get_user_capital(user_id)}) به مرزهای {target_country} ({utils.get_user_capital(target_id)}) رسیدند و با نیروهای دفاعی درگیر شدند!\n\nتلفات {target_country}: {target_losses_30:,}\nتلفات {user_country}: {attacker_losses_30:,}"
        
        try:
            await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=phase1_photo, caption=phase1_text, parse_mode='HTML')
        except Exception:
            pass
        
        # اعمال تلفات مرحله 1 روی اسنپ‌شات و موجودیِ مدافع به تفکیک نوع نیرو
        attacker_forces = attack_data.get('attacker_forces_active', {})
        target_forces = attack_data.get('target_forces_active', {})
        # نرخ مرحله اول (برای نمایش 25-40% بود؛ برای توزیع نوعی از 30% میانگین استفاده می‌کنیم)
        per_type_attacker_rate = 0.30
        per_type_defender_rate = 0.30
        for force_type in ['soldiers', 'special_forces', 'tanks', 'armored_vehicles', 'artillery', 'war_robots']:
            if force_type in target_forces:
                initial = int(target_forces.get(force_type, 0))
                loss = int(initial * per_type_defender_rate)
                # از موجودیِ مدافع کسر شود
                cur = int(utils.users[target_id]['resources'].get(force_type, 0))
                utils.users[target_id]['resources'][force_type] = max(0, cur - loss)
                # و در اسنپ‌شات نبرد هم به‌روز شود
                target_forces[force_type] = max(0, initial - loss)
        attack_data['target_forces'] = target_forces
        from utils import save_users as _save_users
        _save_users()
        
        # ارسال عکس مرحله به هر دو طرف با فایل ایدی
        try:
            user_caption = f"⚔️ مرحله اول: مرزهای {target_country} تسخیر شد!\nتلفات شما: {attacker_losses_30:,}"
            await context.bot.send_photo(chat_id=int(user_id), photo=phase1_photo, caption=user_caption, parse_mode='HTML')
        except Exception:
            pass
        try:
            target_caption = f"⚔️ مرحله اول: مرزهای شما مورد حمله قرار گرفت!\nتلفات شما: {target_losses_30:,}"
            await context.bot.send_photo(chat_id=int(target_id), photo=phase1_photo, caption=target_caption, parse_mode='HTML')
        except Exception:
            pass
        
        if attack_data['attacker_power'] <= 0:
            await ground_battle_defeat(attack_id, context)
            return
        
        try:
            context.job_queue.run_once(
                lambda ctx: ground_battle_phase_2(attack_id, ctx),
                2 * 60
            )
            print(f"مرحله دوم جنگ زمینی {attack_id} زمان‌بندی شد")
        except Exception as e:
            print(f"خطا در زمان‌بندی مرحله دوم جنگ زمینی {attack_id}: {e}")
    except Exception as e:
        print(f"خطا در مرحله اول جنگ زمینی {attack_id}: {e}")
async def ground_battle_phase_2(attack_id, context):
    """مرحله دوم جنگ زمینی"""
    if attack_id not in ground_attacks:
        return
    
    attack_data = ground_attacks[attack_id]
    user_id = attack_data['attacker_id']
    target_id = attack_data['target_id']
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    
    remaining_target_power = attack_data['target_power']
    
    # سیستم شانس رندوم برای تلفات مرحله دوم (25-40%)
    attacker_loss_rate = random.uniform(0.25, 0.40)
    target_loss_rate = random.uniform(0.25, 0.40)
    
    target_losses_70 = int(remaining_target_power * target_loss_rate)
    attacker_losses_70 = int(attack_data['attacker_power'] * attacker_loss_rate)
    
    attack_data['target_power'] -= target_losses_70
    attack_data['attacker_power'] -= attacker_losses_70
    attack_data['phase'] = 2
    save_ground_attacks()
    
    phase2_photo = "https://t.me/TextEmpire_IR/58"  # فایل ایدی مرحله دوم
    phase2_text = (
        f"⚔️ <b>مرحله دوم جنگ زمینی!</b>\n\nنیروهای {target_country} ({utils.get_user_capital(target_id)}) شکست خورد!\n\n"
        f"تلفات {target_country}: {target_losses_70:,}\nتلفات {user_country}: {attacker_losses_70:,}\n"
        f"\n<b>تلفات زمینی:</b>\nسربازان {user_country}: {attacker_losses_70:,}\nسربازان {target_country}: {target_losses_70:,}"
    )
    
    try:
        await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=phase2_photo, caption=phase2_text, parse_mode='HTML')
    except Exception:
        pass
    attacker_forces = attack_data.get('attacker_forces', {})
    target_forces = attack_data.get('target_forces', {})
    force_keys = [
        ('soldiers', 'سرباز'),
        ('special_forces', 'نیروی ویژه'),
        ('speedboats', 'قایق تندرو'),
        ('naval_ship', 'ناو جنگی'),
        ('submarines', 'زیردریایی'),
        ('aircraft_carriers', 'ناو هواپیمابر'),
    ]
    attacker_losses_detail = []
    target_losses_detail = []
    for key, fa_name in force_keys:
        att_init = attacker_forces.get(key, 0)
        tar_init = target_forces.get(key, 0)
        if key == 'soldiers':
            att_loss = attacker_losses_70
            tar_loss = target_losses_70
        else:
            att_loss = int(att_init * 0.25)
            tar_loss = int(tar_init * 0.57)
        # اعمال تلفات مدافع روی موجودی واقعی و اسنپ‌شات
        if key in target_forces and tar_loss > 0:
            cur = int(utils.users[target_id]['resources'].get(key, 0))
            utils.users[target_id]['resources'][key] = max(0, cur - tar_loss)
            target_forces[key] = max(0, int(tar_init) - tar_loss)
        if att_init > 0:
            attacker_losses_detail.append(f"{fa_name}: {att_loss:,} از {att_init:,}")
        if tar_init > 0:
            target_losses_detail.append(f"{fa_name}: {tar_loss:,} از {tar_init:,}")
    # ذخیره تغییرات بعد از کسر تلفات مدافع
    from utils import save_users as _save_users
    _save_users()
    attack_data['target_forces'] = target_forces
    attacker_losses_text = '\n'.join(attacker_losses_detail)
    target_losses_text = '\n'.join(target_losses_detail)
    try:
        user_caption = f"⚔️ مرحله دوم: نیروهای {target_country} شکست خورد!\n\nتلفات شما:\n{attacker_losses_text}"
        await context.bot.send_photo(chat_id=int(user_id), photo=phase2_photo, caption=user_caption, parse_mode='HTML')
    except Exception:
        pass
    try:
        target_caption = f"⚔️ مرحله دوم: نیروی زمینی شما شکست خورد!\n\nتلفات شما:\n{target_losses_text}"
        await context.bot.send_photo(chat_id=int(target_id), photo=phase2_photo, caption=target_caption, parse_mode='HTML')
    except Exception:
        pass
    if attack_data['attacker_power'] <= 0:
        await ground_battle_defeat(attack_id, context)
        return
    context.job_queue.run_once(
        lambda ctx: ground_battle_phase_3(attack_id, ctx),
        2 * 60
    )

async def ground_battle_phase_3(attack_id, context):
    """مرحله سوم جنگ زمینی"""
    if attack_id not in ground_attacks:
        return
    
    attack_data = ground_attacks[attack_id]
    user_id = attack_data['attacker_id']
    target_id = attack_data['target_id']
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    
    remaining_target_power = attack_data['target_power']
    
    # سیستم شانس رندوم برای تلفات مرحله سوم (25-40%) + تاثیر آب‌وهوا
    attacker_loss_rate = random.uniform(0.25, 0.40)
    target_loss_rate = random.uniform(0.25, 0.40)
    try:
        from utils import get_current_weather, get_weather_modifiers
        mods = get_weather_modifiers(get_current_weather())
        attacker_loss_rate *= float(mods.get('attacker_casualty_mul', 1.0))
        target_loss_rate *= float(mods.get('defender_casualty_mul', 1.0))
    except Exception:
        pass
    
    target_losses_final = int(remaining_target_power * target_loss_rate)
    attacker_losses_final = int(attack_data['attacker_power'] * attacker_loss_rate)
    
    # بررسی جنگ مساوی
    remaining_attacker_power = attack_data['attacker_power'] - attacker_losses_final
    remaining_target_power = remaining_target_power - target_losses_final
    
    if remaining_attacker_power <= 0 and remaining_target_power <= 0:
        await ground_battle_draw(attack_id, context, attacker_losses_final, target_losses_final)
    elif remaining_attacker_power <= 0:
        # حمله‌کننده شکست خورد
        await ground_battle_defeat(attack_id, context)
    elif remaining_target_power <= 0:
        # دفاع‌کننده شکست خورد
        await ground_battle_conquest(attack_id, context, attacker_losses_final, target_losses_final)
    else:
        # هر دو طرف هنوز قدرت دارند؛ برنده را با مقایسه تعیین می‌کنیم
        attack_data['attacker_power'] = remaining_attacker_power
        attack_data['target_power'] = remaining_target_power
        save_ground_attacks()
        if remaining_attacker_power > remaining_target_power:
            await ground_battle_conquest(attack_id, context, attacker_losses_final, target_losses_final)
        elif remaining_target_power > remaining_attacker_power:
            await ground_battle_defeat(attack_id, context)
        else:
            await ground_battle_draw(attack_id, context, attacker_losses_final, target_losses_final)

def _get_unit_power(force: str, user_id: str) -> float:
    """قدرت هر واحد برای یک نوع نیرو (مطابق محاسبه قدرت نبرد)."""
    if force == 'soldiers':
        return 1.0
    if force == 'special_forces':
        return 3.0
    if force == 'tanks':
        return 10.0
    if force == 'armored_vehicles':
        return 5.0
    if force == 'artillery':
        return 8.0
    if force == 'war_robots':
        try:
            from utils import military_technologies
            tech_level = military_technologies.get(str(user_id), {}).get('war_robots', 1)
        except Exception:
            tech_level = 1
        tech_bonus = 1 + (tech_level - 1) * 0.2
        return 15.0 * tech_bonus
    # نیروهای غیرزمینی در این محاسبه لحاظ نمی‌شوند
    return 0.0

def calculate_remaining_forces_by_power(original_forces: dict, total_power_losses: int, user_id: str) -> dict:
    """تبدیل تلفات بر حسب قدرت به کاهش واحدی هر نیرو به‌صورت منصفانه.
    - مجموع قدرت اولیه را محاسبه می‌کند (تعداد × قدرت هر واحد)
    - تلفات را به نسبت سهم قدرت هر نوع نیرو توزیع می‌کند
    - سپس با تقسیم بر قدرت هر واحد، تلفات واحدی آن نیرو را به‌دست می‌آورد
    """
    # محاسبه قدرت اولیه هر نیرو و مجموع آن
    per_force_power = {}
    total_initial_power = 0.0
    for force, amount in original_forces.items():
        if amount and amount > 0:
            unit_power = _get_unit_power(force, user_id)
            if unit_power <= 0:
                continue
            p = amount * unit_power
            per_force_power[force] = (amount, unit_power, p)
            total_initial_power += p

    if total_initial_power <= 0:
        return {}

    remaining_forces: dict[str, int] = {}
    power_losses_left = float(max(0, int(total_power_losses)))

    # توزیع تلفات بر حسب سهم قدرت
    for force, (amount, unit_power, power_val) in per_force_power.items():
        share = power_val / total_initial_power
        power_loss_for_force = power_losses_left * share
        unit_losses = int(power_loss_for_force / unit_power)
        remaining_forces[force] = max(0, int(amount) - unit_losses)

    return remaining_forces
def simulate_ground_battle(attacker_forces, user_id):
    # محاسبه قدرت کلی حمله‌کننده
    total_power = 0
    
    # دریافت فناوری‌های کاربر
    from utils import military_technologies
    user_techs = military_technologies.get(str(user_id), {})
    
    for force, amount in attacker_forces.items():
        if force == 'soldiers':
            total_power += amount * 1
        elif force == 'special_forces':
            total_power += amount * 3
        elif force == 'tanks':
            total_power += amount * 10
        elif force == 'armored_vehicles':
            total_power += amount * 5
        elif force == 'artillery':
            total_power += amount * 8
        elif force == 'war_robots':
            # محاسبه قدرت ربات‌های جنگی با در نظر گرفتن فناوری
            base_power = amount * 15
            tech_level = user_techs.get('war_robots', 1)
            tech_bonus = 1 + (tech_level - 1) * 0.2  # هر لول = 20% بونوس اضافی
            total_power += base_power * tech_bonus
    
    # شبیه‌سازی ساده - 60% شانس پیروزی
    victory_chance = 0.6
    if random.random() < victory_chance:
        return {'victory': True, 'power': total_power}
    else:
        return {'victory': False, 'power': total_power}

async def ground_battle_conquest(attack_id, context, attacker_losses, target_losses):
    """فتح کشور در جنگ زمینی"""
    attack_data = ground_attacks[attack_id]
    user_id = attack_data['attacker_id']
    target_id = attack_data['target_id']
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    
    # بازگرداندن نیروهای باقی‌مانده به حمله‌کننده (محاسبه بر اساس قدرت واقعی از دست‌رفته)
    attacker_forces = attack_data.get('attacker_forces', {})
    remaining_forces = calculate_remaining_forces_by_power(attacker_forces, attacker_losses, user_id)
    
    # اضافه کردن نیروهای باقی‌مانده به موجودی کاربر و ذخیره
    user_resources = utils.users[user_id]['resources']
    for force, amount in remaining_forces.items():
        if amount > 0:
            user_resources[force] = user_resources.get(force, 0) + amount
    try:
        from utils import save_users as _save_users
        _save_users()
    except Exception:
        pass
    
    # بررسی مجدد که آیا کشور قبلاً فتح شده است
    if utils.users[target_id].get('conquered_by'):
        await context.bot.send_message(chat_id=int(user_id), text=f"❌ کشور {target_country} قبلاً توسط {utils.users[target_id]['conquered_by']} فتح شده است!")
        del ground_attacks[attack_id]
        return
    
    # استفاده از utils.users به صورت صریح برای اطمینان از ذخیره درست
    target_resources = utils.users[target_id]['resources']
    user_resources = utils.users[user_id]['resources']
    # اسنپ‌شات منابع/نیرو در لحظه فتح برای بازگردانی هنگام استقلال
    try:
        from utils import conquered_countries_data, save_conquered_countries_data
        snapshot = {
            'resources': dict(target_resources),
            'forces': {
                'soldiers': target_resources.get('soldiers', 0),
                'special_forces': target_resources.get('special_forces', 0),
                'tanks': target_resources.get('tanks', 0),
                'armored_vehicles': target_resources.get('armored_vehicles', 0),
                'artillery': target_resources.get('artillery', 0),
                'war_robots': target_resources.get('war_robots', 0),
                'speedboats': target_resources.get('speedboats', 0),
                'naval_ship': target_resources.get('naval_ship', 0),
                'submarines': target_resources.get('submarines', 0),
                'aircraft_carriers': target_resources.get('aircraft_carriers', 0),
            },
            'conquered_by': user_country,
            'conquered_at': time.time(),
        }
        conquered_countries_data[str(target_id)] = snapshot
        save_conquered_countries_data()
    except Exception:
        pass
    # ثبت مبلغ نقدی انتقال‌یافته برای نمایش در مستعمرات
    try:
        original_target_cash = int(target_resources.get('cash', 0))
        utils.users[target_id]['conquered_captured_cash'] = original_target_cash
    except Exception:
        pass
    
    # انتقال تمام منابع
    for resource, amount in target_resources.items():
        if resource in user_resources:
            user_resources[resource] += amount
        else:
            user_resources[resource] = amount
        target_resources[resource] = 0
    
    # انتقال پناهجویان (جمعیت هدف به عنوان مهاجر به کشور فاتح اضافه می‌شود)
    try:
        from jame import get_country_population_by_user_id
        pop = int(get_country_population_by_user_id(target_id))
        utils.users[user_id]['immigrants'] = utils.users[user_id].get('immigrants', 0) + max(0, pop)
    except Exception:
        pass
    
    # علامت‌گذاری کشور فتح شده + انتقال مرزها و دسترسی دریا
    utils.users[target_id]['conquered_by'] = user_country
    utils.users[target_id]['conquered_at'] = time.time()
    # غیرفعال‌سازی موقت تا 6 دور
    try:
        from utils import game_data as _gd
        utils.users[target_id]['activated'] = False
        utils.users[target_id]['independence_deadline_turn'] = int(_gd.get('turn', 1)) + 6
    except Exception:
        utils.users[target_id]['activated'] = False
    # انتقال رهبری اتحاد در صورت فتح رهبر
    try:
        transfer_result = transfer_alliance_on_leader_loss(target_id)
        if transfer_result:
            if transfer_result.get('deleted'):
                pass
            elif transfer_result.get('new_leader'):
                new_leader = transfer_result['new_leader']
                try:
                    await context.bot.send_message(
                        chat_id=int(new_leader),
                        text=f"👑 شما رهبر جدید اتحاد {transfer_result.get('alliance_name','')} شدید (رهبر قبلی فتح شد)."
                    )
                except Exception:
                    pass
    except Exception as e:
        print(f"[alliance-transfer] failed on conquest: {e}")
    # انتقال مرزهای زمینی و دسترسی دریایی به کشور فاتح
    try:
        from utils import grant_conquest_borders
        grant_conquest_borders(user_id, target_country, target_id)
    except Exception:
        pass
    
    # تنظیم روابط بین فاتح و کشور فتح شده به 0
    try:
        from utils import set_mutual_relation
        set_mutual_relation(user_id, target_id, 0)
    except Exception:
        pass
    
    # ذخیره تغییرات
    from utils import save_users
    save_users()
    try:
        # ثبت پیروزی نظامی
        from utils import increment_military_win
        increment_military_win(user_id)
    except Exception:
        pass
    
    # انتخاب رندوم تصویر/گیف فتح
    conquest_media = [
        "https://t.me/TextEmpire_IR/56",   # تصویر
        "https://t.me/TextEmpire_IR/160"   # گیف
    ]
    conquest_photo = random.choice(conquest_media)
    # اعمال تأثیر جنگ بر رضایت مردم
    from utils import apply_war_satisfaction_effect
    apply_war_satisfaction_effect(user_id, True)  # پیروزی برای حمله‌کننده
    apply_war_satisfaction_effect(target_id, False)  # شکست برای دفاع‌کننده
    
    conquest_text = f"🏆 <b>فتح کامل!</b>\n\nکشور {user_country} ({utils.get_user_capital(user_id)}) کشور {target_country} ({utils.get_user_capital(target_id)}) را فتح کرد!\n\nتمام دارایی‌ها و منابع به کشور فاتح منتقل شد."
    try:
        await send_media_safe(context.bot, NEWS_CHANNEL_ID, conquest_photo, conquest_text, 'HTML')
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=int(user_id), text=f"🏆 کشور {target_country} ({utils.get_user_capital(target_id)}) فتح شد! تمام دارایی‌ها به شما منتقل شد.")
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=int(target_id), text=f"💀 کشور شما توسط {user_country} ({utils.get_user_capital(user_id)}) فتح شد! تمام دارایی‌ها از دست رفت.")
    except Exception:
        pass
    del ground_attacks[attack_id]
    
    # ارسال درخواست پناهندگی به 5 کشور تصادفی
    try:
        from bot import send_refugee_requests_to_random_countries
        await send_refugee_requests_to_random_countries(user_country, target_country, context)
    except Exception as e:
        print(f"خطا در ارسال درخواست‌های پناهندگی: {e}")
    
    # انتقال سلسله‌مراتب مستعمرات: مستعمرات هدف به فاتح منتقل می‌شوند
    try:
        conquered_children = []
        for cid, cu in utils.users.items():
            if cu.get('conquered_by') == target_country:
                conquered_children.append(cid)
        # تغییر مالکیت همه مستعمرات هدف به کشور فاتح
        for cid in conquered_children:
            utils.users[cid]['conquered_by'] = user_country
            # زمان فتحِ به ارث رسیده را ثبت کنیم (بدون تغییر سایر داده‌ها)
            utils.users[cid]['conquered_at'] = time.time()
        save_users()
    except Exception:
        pass
    # پایان خودکار اعلان جنگ بین طرفین پس از فتح
    try:
        import utils as _utils
        from utils import save_war_declarations as _save_wars
        for wid, w in list(_utils.war_declarations.items()):
            a = w.get('attacker')
            d = w.get('defender')
            if w.get('status') == 'active' and ((a == user_country and d == target_country) or (a == target_country and d == user_country)):
                _utils.war_declarations[wid]['status'] = 'ended'
                _utils.war_declarations[wid]['end_turn'] = _utils.game_data.get('turn', 1)
                _utils.war_declarations[wid]['end_reason'] = 'conquest'
        _save_wars()
    except Exception:
        pass

async def ground_battle_defeat(attack_id, context):
    """شکست حمله زمینی"""
    attack_data = ground_attacks[attack_id]
    user_id = attack_data['attacker_id']
    target_id = attack_data['target_id']
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    
    # بازگرداندن نیروهای باقی‌مانده به حمله‌کننده (حتی در صورت شکست) بر اساس قدرت از دست‌رفته
    attacker_forces = attack_data.get('attacker_forces', {})
    # محاسبه کل تلفات از قدرت اولیه
    original_power = attack_data.get('original_attacker_power', 0)
    remaining_power = attack_data.get('attacker_power', 0)
    total_attacker_losses = max(0, original_power - remaining_power)
    remaining_forces = calculate_remaining_forces_by_power(attacker_forces, total_attacker_losses, user_id)
    
    # اضافه کردن نیروهای باقی‌مانده به موجودی کاربر و ذخیره
    user_resources = utils.users[user_id]['resources']
    for force, amount in remaining_forces.items():
        if amount > 0:
            user_resources[force] = user_resources.get(force, 0) + amount
    try:
        from utils import save_users as _save_users
        _save_users()
    except Exception:
        pass
    
    # اعمال تأثیر جنگ بر رضایت مردم
    from utils import apply_war_satisfaction_effect
    apply_war_satisfaction_effect(user_id, False)  # شکست برای حمله‌کننده
    apply_war_satisfaction_effect(target_id, True)  # پیروزی برای دفاع‌کننده
    
    defeat_photo = "https://t.me/TextEmpire_IR/61"  # فایل ایدی شکست
    defeat_text = f"❌ <b>شکست حمله زمینی!</b>\n\nحمله {user_country} به {target_country} شکست خورد!\n\nنیروهای باقی‌مانده به کشور حمله‌کننده بازگشتند."
    try:
        await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=defeat_photo, caption=defeat_text, parse_mode='HTML')
    except Exception:
        pass
    # پایان اعلان جنگ فعال بین طرفین (در صورت وجود)
    try:
        import utils as _utils
        from utils import save_war_declarations as _save_wars
        for wid, w in list(_utils.war_declarations.items()):
            a = w.get('attacker')
            d = w.get('defender')
            if w.get('status') == 'active' and ((a == user_country and d == target_country) or (a == target_country and d == user_country)):
                _utils.war_declarations[wid]['status'] = 'ended'
                _utils.war_declarations[wid]['end_turn'] = _utils.game_data.get('turn', 1)
                _utils.war_declarations[wid]['end_reason'] = 'defeat'
        _save_wars()
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=int(user_id), text=f"❌ حمله زمینی به {target_country} شکست خورد! نیروهای باقی‌مانده بازگشتند.")
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=int(target_id), text=f"✅ حمله زمینی {user_country} دفع شد! کشور شما محافظت شد.")
    except Exception:
        pass
    del ground_attacks[attack_id]
    
    # ارسال درخواست پناهندگی به 5 کشور تصادفی
    try:
        from bot import send_refugee_requests_to_random_countries
        await send_refugee_requests_to_random_countries(user_country, target_country, context)
    except Exception as e:
        print(f"خطا در ارسال درخواست‌های پناهندگی: {e}")
async def ground_battle_draw(attack_id, context, attacker_losses, target_losses):
    """جنگ مساوی زمینی"""
    attack_data = ground_attacks[attack_id]
    user_id = attack_data['attacker_id']
    target_id = attack_data['target_id']
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    
    # بازگرداندن نیروهای باقی‌مانده به حمله‌کننده (در جنگ مساوی) بر اساس قدرت از دست‌رفته
    attacker_forces = attack_data.get('attacker_forces', {})
    # استفاده از تلفات محاسبه شده که به عنوان پارامتر ارسال شده
    remaining_forces = calculate_remaining_forces_by_power(attacker_forces, attacker_losses, user_id)
    
    # اضافه کردن نیروهای باقی‌مانده به موجودی کاربر و ذخیره
    user_resources = utils.users[user_id]['resources']
    for force, amount in remaining_forces.items():
        if amount > 0:
            user_resources[force] = user_resources.get(force, 0) + amount
    try:
        from utils import save_users
        save_users()
    except Exception:
        pass
    
    # انتخاب رندوم تصویر جنگ برابر زمینی
    draw_photos = [
        "https://t.me/TextEmpire_IR/52",
        "https://t.me/TextEmpire_IR/167"
    ]
    draw_photo = random.choice(draw_photos)
    draw_text = (
        f"⚖️ <b>جنگ برابر!</b>\n\n"
        f"هیچ یک از طرفین پیروز نشد!\n\n"
        f"قدرت‌های دنیا برقراری صلح بین دو طرف خواستار شدند.\n"
        f"سازمان ملل طرفین را به جلسه فوری شورای امنیت فراخواند.\n\n"
        f"تلفات {user_country}: {attacker_losses:,}\n"
        f"تلفات {target_country}: {target_losses:,}"
    )
    try:
        await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=draw_photo, caption=draw_text, parse_mode='HTML')
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=int(user_id), text=f"⚖️ جنگ با {target_country} مساوی شد! سازمان ملل درخواست صلح داد.")
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=int(target_id), text=f"⚖️ جنگ با {user_country} مساوی شد! سازمان ملل درخواست صلح داد.")
    except Exception:
        pass
    del ground_attacks[attack_id]
    
    # ارسال درخواست پناهندگی به 5 کشور تصادفی
    try:
        from bot import send_refugee_requests_to_random_countries
        await send_refugee_requests_to_random_countries(user_country, target_country, context)
    except Exception as e:
        print(f"خطا در ارسال درخواست‌های پناهندگی: {e}")
async def schedule_battle_result(user_id, target_country, battle_result, attacker_forces, context):
    # انتظار 2 دقیقه
    await asyncio.sleep(120)
    
    user_country = utils.users[user_id]['country']
    
    if battle_result['victory']:
        # پیام پیروزی
        victory_msg = f"🏆 <b>پیروزی در نبرد!</b>\n\nکشور {user_country} در نبرد با {target_country} پیروز شد!\n\n"
        victory_msg += "نیروهای ارسالی:\n"
        for force, amount in attacker_forces.items():
            victory_msg += f"▫️ {force}: {amount:,}\n"
        
        try:
            await send_media_safe(context.bot, int(user_id), "https://t.me/TextEmpire_IR/66", victory_msg, 'HTML')
        except Exception as e:
            print(f"خطا در ارسال پیام پیروزی: {e}")
    else:
        # پیام شکست
        defeat_msg = f"❌ <b>شکست در نبرد!</b>\n\nکشور {user_country} در نبرد با {target_country} شکست خورد!\n\n"
        defeat_msg += "نیروهای ارسالی:\n"
        for force, amount in attacker_forces.items():
            defeat_msg += f"▫️ {force}: {amount:,}\n"
        
        try:
            await send_media_safe(context.bot, int(user_id), "https://t.me/TextEmpire_IR/65", defeat_msg, 'HTML')
        except Exception as e:
            print(f"خطا در ارسال پیام شکست: {e}")

# --- توابع نبرد دریایی ---
async def start_naval_battle(message, attack_data, context):
    global naval_attack_counter
    naval_attack_counter += 1
    attack_id = f"naval_{naval_attack_counter}"
    user_id = attack_data['user_id']
    target_id = attack_data['target_id']
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    
    # بررسی اینکه آیا کشور هدف قبلاً فتح شده است
    if utils.users[target_id].get('conquered_by'):
        await context.bot.send_message(chat_id=int(user_id), text=f"❌ کشور {target_country} قبلاً توسط {utils.users[target_id]['conquered_by']} فتح شده است!")
        return
    
    # بررسی اینکه آیا کشور هدف در حال جنگ است
    ongoing_attacks = [attack for attack in naval_attacks.values() if attack['target_id'] == target_id]
    if ongoing_attacks:
        await context.bot.send_message(chat_id=int(user_id), text=f"❌ کشور {target_country} در حال حاضر در جنگ است. لطفاً صبر کنید تا جنگ فعلی پایان یابد.")
        return
    
    # بررسی اینکه آیا کشور حمله‌کننده در حال جنگ است
    ongoing_attacks_attacker = [attack for attack in naval_attacks.values() if attack['attacker_id'] == user_id]
    if ongoing_attacks_attacker:
        await context.bot.send_message(chat_id=int(user_id), text=f"❌ شما در حال حاضر در جنگ هستید. لطفاً صبر کنید تا جنگ فعلی پایان یابد.")
        return
    
    # محاسبه قدرت با در نظر گرفتن لول فناوری
    from utils import calculate_military_power_with_tech
    
    # قدرت حمله‌کننده با لول فناوری (بدون توپخانه دریایی)
    attacker_power = calculate_military_power_with_tech(user_id)
    
    # قدرت دفاع‌کننده با لول فناوری (شامل توپخانه دریایی)
    target_naval_power = calculate_military_power_with_tech(target_id)
    
    # اضافه کردن قدرت توپخانه دریایی برای دفاع
    target_resources = utils.users[target_id]['resources']
    target_techs = military_technologies.get(str(target_id), {})
    coastal_artillery_count = target_resources.get('coastal_artillery', 0)
    coastal_artillery_tech = target_techs.get('coastal_artillery', 1)
    coastal_artillery_power = coastal_artillery_count * 24 * (coastal_artillery_tech / 2)  # قدرت 24 با در نظر گرفتن لول
    
    target_naval_power += coastal_artillery_power

    # اعمال ضریب تجهیزات ویژه (defense_power) از فروشگاه برای مدافع در نبرد دریایی
    try:
        from bot import get_user_defense_power
        shop_defense_multiplier = float(get_user_defense_power(str(target_id)))
        target_naval_power = int(target_naval_power * shop_defense_multiplier)
    except Exception:
        pass
    
    # دریافت منابع دفاع‌کننده
    target_resources = utils.users[target_id]['resources']
    
    # کسر فوری نیروهای اعزامیِ حمله‌کننده از موجودی کشور تا از بازگشت زودهنگام جلوگیری شود
    try:
        attacker_committed = {
            'soldiers': int(attack_data.get('soldiers', 0)),
            'speedboats': int(attack_data.get('speedboats', 0)),
            'naval_ship': int(attack_data.get('naval_ship', 0)),
            'submarines': int(attack_data.get('submarines', 0)),
            'aircraft_carriers': int(attack_data.get('aircraft_carriers', 0)),
        }
        # اگر قبلاً در مرحله ورود کسر شده است، دوباره کم نکن
        if not attack_data.get('already_deducted'):
            for key in ['soldiers', 'speedboats', 'naval_ship', 'submarines', 'aircraft_carriers']:
                available = int(utils.users[user_id]['resources'].get(key, 0))
                send_count = attacker_committed.get(key, 0)
                if send_count > 0:
                    utils.users[user_id]['resources'][key] = max(0, available - send_count)
            save_users()
    except Exception:
        pass

    # تشکیل نیروهای فعال/ذخیره ۵۰/۵۰ برای حمله‌کننده و مدافع
    def _split_active_reserve(forces_dict):
        active = {}
        reserve = {}
        for _k, _v in forces_dict.items():
            try:
                _vi = int(_v)
            except Exception:
                _vi = 0
            _act = int(_vi * 0.5)
            _res = max(0, _vi - _act)
            active[_k] = _act
            reserve[_k] = _res
        return active, reserve

    attacker_active, attacker_reserve = _split_active_reserve({
        'soldiers': attacker_committed.get('soldiers', 0),
        'speedboats': attacker_committed.get('speedboats', 0),
        'naval_ship': attacker_committed.get('naval_ship', 0),
        'submarines': attacker_committed.get('submarines', 0),
        'aircraft_carriers': attacker_committed.get('aircraft_carriers', 0),
    })
    target_full = {
        'soldiers': target_resources.get('soldiers', 0),
        'speedboats': target_resources.get('speedboats', 0),
        'naval_ship': target_resources.get('naval_ship', 0),
        'submarines': target_resources.get('submarines', 0),
        'aircraft_carriers': target_resources.get('aircraft_carriers', 0),
        'coastal_artillery': target_resources.get('coastal_artillery', 0),
    }
    target_active, target_reserve = _split_active_reserve(target_full)

    naval_attacks[attack_id] = {
        'attacker_id': user_id,
        'target_id': target_id,
        # ذخیره اسنپ‌شات نیروهای اعزامیِ حمله‌کننده پس از کسر از موجودی
        'attacker_forces': {
            'soldiers': attacker_committed.get('soldiers', 0),
            'speedboats': attacker_committed.get('speedboats', 0),
            'naval_ship': attacker_committed.get('naval_ship', 0),
            'submarines': attacker_committed.get('submarines', 0),
            'aircraft_carriers': attacker_committed.get('aircraft_carriers', 0),
        },
        'target_forces': {
            'soldiers': target_resources.get('soldiers', 0),
            'speedboats': target_resources.get('speedboats', 0),
            'naval_ship': target_resources.get('naval_ship', 0),
            'submarines': target_resources.get('submarines', 0),
            'aircraft_carriers': target_resources.get('aircraft_carriers', 0),
            'coastal_artillery': target_resources.get('coastal_artillery', 0),
        },
        # نسخه جدید: فعال/ذخیره
        'attacker_forces_active': attacker_active,
        'attacker_forces_reserve': attacker_reserve,
        'target_forces_active': target_active,
        'target_forces_reserve': target_reserve,
        'attacker_power': attacker_power,
        'target_power': target_naval_power,
        'start_time': time.time(),
        'phase': 0
    }
    try:
        save_naval_attacks()
    except Exception:
        pass
    # انتخاب رندوم تصویر حمله دریایی
    attack_photos = [
        "https://t.me/TextEmpire_IR/48",
        "https://t.me/TextEmpire_IR/168",
        "https://t.me/TextEmpire_IR/169"
    ]
    attack_photo = random.choice(attack_photos)
    attack_text = f"🌊 <b>حمله دریایی آغاز شد!</b>\n\nکشور {user_country} ({utils.get_user_capital(user_id)}) به {target_country} ({utils.get_user_capital(target_id)}) حمله دریایی کرد!\n\nنتیجه تا 15 دقیقه دیگر اعلام خواهد شد."
    try:
        await send_media_safe(context.bot, NAVAL_ATTACK_CHANNEL_ID, attack_photo, attack_text, 'HTML')
    except Exception:
        pass
    # پیام آغاز حمله به حمله‌کننده حذف شد؛ پیام تایید قبلاً ارسال شده است
    try:
        await context.bot.send_message(chat_id=int(target_id), text=f"🌊 کشور {user_country} به شما حمله دریایی کرد! نتیجه تا 15 دقیقه دیگر اعلام خواهد شد.")
    except Exception:
        pass
    try:
        await schedule_naval_battle_phases(attack_id, context)
    except Exception as e:
        print(f"خطا در زمان‌بندی مراحل حمله دریایی: {e}")
        if attack_id in naval_attacks:
            del naval_attacks[attack_id]

async def schedule_naval_battle_phases(attack_id, context):
    try:
        attack_data = naval_attacks[attack_id]
        # اطلاع‌رسانی زمان‌بندی فاز 1 نبرد دریایی
        try:
            user_id = attack_data.get('attacker_id')
            target_id = attack_data.get('target_id')
            attacker_country = utils.users.get(user_id, {}).get('country', 'نامشخص')
            target_country = utils.users.get(target_id, {}).get('country', 'نامشخص')
            msg = (
                f"🕒 آغاز حمله دریایی برنامه‌ریزی شد\n\n"
                f"🌊 {attacker_country} → {target_country}\n"
                f"🆔 شناسه نبرد: {attack_id}\n"
                f"⏳ شروع فاز 1 تا 5 دقیقه آینده"
            )
            # ارسال پیام زمان‌بندی به حمله‌کننده حذف شد تا از پیام‌های تکراری جلوگیری شود
            try:
                await context.bot.send_message(chat_id=int(target_id), text=msg)
            except Exception:
                pass
            try:
                await context.bot.send_message(chat_id=NEWS_CHANNEL_ID, text=f"🕒 برنامه‌ریزی حمله دریایی | {attacker_country} vs {target_country}\n🆔 {attack_id}")
            except Exception:
                pass
        except Exception:
            pass
        context.job_queue.run_once(
            lambda ctx: naval_battle_phase_1(attack_id, ctx),
            1 * 60
        )
        print(f"مرحله اول حمله دریایی {attack_id} زمان‌بندی شد (۵ دقیقه)")
    except Exception as e:
        print(f"خطا در زمان‌بندی مراحل حمله دریایی {attack_id}: {e}")
        raise

async def ask_sea_raid_forces(query, trade_id):
    user_id = str(query.from_user.id)
    pending_sea_raid[user_id] = trade_id
    text = (
        "چه تعداد نیروی ویژه، قایق تندرو و سرباز برای حمله ارسال می‌کنید؟\n"
        "<b>مثال:</b>\n"
        "<code>نیروی ویژه: 100\nقایق تندرو: 10\nسرباز: 500</code>"
    )
    await query.edit_message_text(text, parse_mode='HTML')


async def naval_battle_phase_1(attack_id, context):
    try:
        if attack_id not in naval_attacks:
            print(f"حمله دریایی {attack_id} یافت نشد")
            return
        attack_data = naval_attacks[attack_id]
        user_id = attack_data['attacker_id']
        target_id = attack_data['target_id']
        user_country = utils.users[user_id]['country']
        target_country = utils.users[target_id]['country']
        
        # سیستم شانس رندوم برای تلفات و محاسبه قدرت مرحله اول
        attacker_loss_rate = random.uniform(0.20, 0.30)  # 20-30% رندوم
        target_loss_rate = random.uniform(0.20, 0.30)    # 20-30% رندوم
        attacker_forces = attack_data.get('attacker_forces', {})
        target_forces = attack_data.get('target_forces', {})
        # قدرت مرحله با در نظر گرفتن لول فناوری (هر لول ×0.1)
        atk_techs = military_technologies.get(str(user_id), {})
        tgt_techs = military_technologies.get(str(target_id), {})
        def tech_mult(level):
            try:
                return 1.0 + 0.1 * int(level)
            except Exception:
                return 1.0
        def sum_power(forces, techs):
            total = 0.0
            for k in ['speedboats', 'naval_ship', 'submarines', 'aircraft_carriers']:
                cnt = int(forces.get(k, 0))
                lvl = int(techs.get(k, 0))
                total += cnt * tech_mult(lvl)
            return total
        attacker_phase_power = sum_power(attacker_forces, atk_techs) * attacker_loss_rate
        target_phase_power = sum_power(target_forces, tgt_techs) * target_loss_rate
        naval_keys = [('soldiers', 'سرباز'), ('speedboats', 'قایق تندرو'), ('naval_ship', 'ناو جنگی'), ('submarines', 'زیردریایی'), ('aircraft_carriers', 'ناو هواپیمابر'), ('coastal_artillery', 'توپخانه ساحلی')]
        attacker_losses_list = []
        target_losses_list = []
        for k, fa in naval_keys:
            att0 = attacker_forces.get(k, 0)
            tar0 = target_forces.get(k, 0)
            att_loss_units = int(att0 * attacker_loss_rate) if att0 > 0 else 0
            tar_loss_units = int(tar0 * target_loss_rate) if tar0 > 0 else 0
            if att_loss_units > 0:
                attacker_losses_list.append(f"{fa}: {att_loss_units:,}")
            if tar_loss_units > 0:
                target_losses_list.append(f"{fa}: {tar_loss_units:,}")

        # به‌روزرسانی شاخص قدرت برای سازگاری با کد موجود (با مجموع واحد باقی‌مانده)
        # ابتدا قدرت نمایشی مرحله (برای پیام‌ها) محاسبه شد؛ حالا قدرت در attack_data را با جمع واحدها همگام می‌کنیم بعد از کسر
        attack_data['phase'] = 1
        try:
            save_naval_attacks()
        except Exception:
            pass
        
        # Deduct phase 1 losses from user resources AND update in-attack remaining forces
        attacker_forces = attack_data.get('attacker_forces_active', {})
        target_forces = attack_data.get('target_forces_active', {})
        
        # Calculate and deduct phase 1 losses for attacker
        for force_type in ['soldiers', 'speedboats', 'naval_ship', 'submarines', 'aircraft_carriers']:
            if force_type in attacker_forces:
                initial_count = int(attacker_forces.get(force_type, 0))
                losses = int(initial_count * attacker_loss_rate)
                # update remaining in attack_data
                attacker_forces[force_type] = max(0, initial_count - losses)
                # کسر تلفات از موجودی مهاجم
                try:
                    cur_inv = int(utils.users[user_id]['resources'].get(force_type, 0))
                    # کسر تلفات از موجودی مهاجم
                    utils.users[user_id]['resources'][force_type] = max(0, cur_inv - losses)
                except Exception:
                    pass
        
        # Calculate and deduct phase 1 losses for target
        for force_type in ['soldiers', 'speedboats', 'naval_ship', 'submarines', 'aircraft_carriers', 'coastal_artillery']:
            if force_type in target_forces:
                initial_count = int(target_forces.get(force_type, 0))
                losses = int(initial_count * target_loss_rate)
                current_count = int(utils.users[target_id]['resources'].get(force_type, 0))
                utils.users[target_id]['resources'][force_type] = max(0, current_count - losses)
                target_forces[force_type] = max(0, initial_count - losses)

        # persist updated attack_data forces
        attack_data['attacker_forces_active'] = attacker_forces
        attack_data['target_forces_active'] = target_forces
        try:
            save_naval_attacks()
        except Exception:
            pass
        
        save_users()
        # انتخاب رندوم تصویر مرحله اول حمله دریایی
        phase1_photos = [
            "https://t.me/TextEmpire_IR/49",
            "https://t.me/TextEmpire_IR/165",
            "https://t.me/TextEmpire_IR/170"
        ]
        phase1_photo = random.choice(phase1_photos)
        # متن کانال با جزئیات تلفات به تفکیک نیرو
        losses_user = "\n".join(attacker_losses_list) if attacker_losses_list else "-"
        losses_tgt = "\n".join(target_losses_list) if target_losses_list else "-"
        phase1_text = (
            f"🌊 <b>مرحله اول حمله دریایی!</b>\n\n"
            f"کشتی‌های {user_country} به ساحل {target_country} رسیدند و با نیروهای دفاعی درگیر شدند!\n\n"
            f"🔻 <b>تلفات {target_country}:</b>\n{losses_tgt}\n\n"
            f"🔺 <b>تلفات {user_country}:</b>\n{losses_user}"
        )
        try:
            await send_media_safe(context.bot, NAVAL_ATTACK_CHANNEL_ID, phase1_photo, phase1_text, 'HTML')
        except Exception:
            pass
        try:
            await context.bot.send_message(chat_id=int(user_id), text=(
                f"🌊 مرحله اول: ساحل {target_country} تسخیر شد!\n\n"
                f"🔻 تلفات شما:\n{losses_user}\n\n"
                f"🔺 تلفات {target_country}:\n{losses_tgt}"
            ))
        except Exception:
            pass
        try:
            await context.bot.send_message(chat_id=int(target_id), text=(
                f"🌊 مرحله اول: ساحل شما مورد حمله قرار گرفت!\n\n"
                f"🔻 تلفات شما:\n{losses_tgt}\n\n"
                f"🔺 تلفات {user_country}:\n{losses_user}"
            ))
        except Exception:
            pass
        if attack_data['attacker_power'] <= 0:
            await naval_battle_defeat(attack_id, context)
            return
        try:
            context.job_queue.run_once(
                lambda ctx: naval_battle_phase_2(attack_id, ctx),
                1 * 60
            )
            print(f"مرحله دوم حمله دریایی {attack_id} زمان‌بندی شد (۵ دقیقه)")
        except Exception as e:
            print(f"خطا در زمان‌بندی مرحله دوم حمله دریایی {attack_id}: {e}")
    except Exception as e:
        print(f"خطا در مرحله اول حمله دریایی {attack_id}: {e}")
async def naval_battle_phase_2(attack_id, context):
    if attack_id not in naval_attacks:
        return
    attack_data = naval_attacks[attack_id]
    user_id = attack_data['attacker_id']
    target_id = attack_data['target_id']
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    # افزودن ۵۰٪ ذخیره حمله‌کننده به نیروهای فعال باقی‌مانده
    attacker_active = dict(attack_data.get('attacker_forces_active', {}))
    attacker_reserve = dict(attack_data.get('attacker_forces_reserve', {}))
    for fk in ['soldiers','speedboats','naval_ship','submarines','aircraft_carriers']:
        addin = int(attacker_reserve.get(fk, 0) * 0.50)
        attacker_active[fk] = int(attacker_active.get(fk, 0)) + addin
        attacker_reserve[fk] = max(0, int(attacker_reserve.get(fk, 0)) - addin)

    # مدافع: ۵۰٪ موجودی فعلی + باقی‌مانده فعال مرحله قبل
    target_active = dict(attack_data.get('target_forces_active', {}))
    for fk in ['soldiers','speedboats','naval_ship','submarines','aircraft_carriers','coastal_artillery']:
        cur_inv = int(utils.users[target_id]['resources'].get(fk, 0))
        addin = int(cur_inv * 0.50)
        target_active[fk] = int(target_active.get(fk, 0)) + addin

    # محاسبه قدرت مرحله دوم با لول فناوری و ۱۰-۲۰٪ شانس
    atk_techs = military_technologies.get(str(user_id), {})
    tgt_techs = military_technologies.get(str(target_id), {})
    def tech_mult(level):
        try:
            return 1.0 + 0.1 * int(level)
        except Exception:
            return 1.0
    def sum_power(forces, techs):
        total = 0.0
        for k in ['soldiers','speedboats', 'naval_ship', 'submarines', 'aircraft_carriers','coastal_artillery']:
            cnt = int(forces.get(k, 0))
            lvl = int(techs.get(k, 0))
            total += cnt * tech_mult(lvl)
        return total
    atk_rand = 1.0 + random.uniform(0.10, 0.20)
    tgt_rand = 1.0 + random.uniform(0.10, 0.20)
    attacker_phase_power = sum_power(attacker_active, atk_techs) * atk_rand
    target_phase_power = sum_power(target_active, tgt_techs) * tgt_rand
    attack_data['phase'] = 2
    try:
        save_naval_attacks()
    except Exception:
        pass
    # تلفات مرحله دوم و کسر از موجودی مدافع
    total_pow = max(1.0, attacker_phase_power + target_phase_power)
    att_ratio = attacker_phase_power / total_pow
    tgt_ratio = target_phase_power / total_pow
    attacker_losses_detail = []
    target_losses_detail = []
    for fk, fa_name in [('soldiers','سرباز'),('speedboats','قایق تندرو'),('naval_ship','ناو جنگی'),('submarines','زیردریایی'),('aircraft_carriers','ناو هواپیمابر'),('coastal_artillery','توپخانه ساحلی')]:
        att0 = int(attacker_active.get(fk, 0))
        tgt0 = int(target_active.get(fk, 0))
        att_loss = int(att0 * (0.15 + 0.25 * (1 - att_ratio)))
        tgt_loss = int(tgt0 * (0.15 + 0.25 * (1 - tgt_ratio)))
        if att_loss > 0:
            attacker_active[fk] = max(0, att0 - att_loss)
            # کسر تلفات از موجودی مهاجم
            cur_inv = int(utils.users[user_id]['resources'].get(fk, 0))
            utils.users[user_id]['resources'][fk] = max(0, cur_inv - att_loss)
            attacker_losses_detail.append(f"{fa_name}: {att_loss:,}")
        if tgt_loss > 0:
            target_active[fk] = max(0, tgt0 - tgt_loss)
            cur_inv = int(utils.users[target_id]['resources'].get(fk, 0))
            utils.users[target_id]['resources'][fk] = max(0, cur_inv - tgt_loss)
            target_losses_detail.append(f"{fa_name}: {tgt_loss:,}")

    attack_data['attacker_forces_active'] = attacker_active
    attack_data['attacker_forces_reserve'] = attacker_reserve
    attack_data['target_forces_active'] = target_active
    save_users()
    
    save_users()
    if attack_data['target_power'] <= 0:
        utils.users[target_id]['naval_blockade'] = True
        utils.users[target_id]['alliance_help_blocked'] = True
        utils.users[target_id]['military_purchase_blocked'] = True
    # انتخاب رندوم تصویر مرحله دوم حمله دریایی
    phase2_photos = [
        "https://t.me/TextEmpire_IR/50",
        "https://t.me/TextEmpire_IR/166"
    ]
    phase2_photo = random.choice(phase2_photos)
    # متن کانال با تلفات به تفکیک هر نیرو (شامل سربازان)
    # لیست‌ها در پایین محاسبه می‌شوند؛ ابتدا متن را پس از محاسبه آنها ارسال می‌کنیم
    # آماده‌سازی متن مرحله دوم پس از محاسبه جزئیات
    # متن تلفات مرحله دوم برای کاربران
    losses_user = '\n'.join(attacker_losses_detail) if attacker_losses_detail else '-'
    losses_tgt = '\n'.join(target_losses_detail) if target_losses_detail else '-'
    phase2_text = (
        f"🌊 <b>مرحله دوم حمله دریایی!</b>\n\n"
        f"نیروی دریایی {target_country} شکست خورد!\n\n"
        f"🔻 <b>تلفات {target_country}:</b>\n{losses_tgt}\n\n"
        f"🔺 <b>تلفات {user_country}:</b>\n{losses_user}"
    )
    try:
        await send_media_safe(context.bot, NAVAL_ATTACK_CHANNEL_ID, phase2_photo, phase2_text, 'HTML')
    except Exception:
        pass
    attacker_losses_text = losses_user
    target_losses_text = losses_tgt
    try:
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"🌊 مرحله دوم: نیروی دریایی {target_country} شکست خورد!\n\nتلفات شما:\n{attacker_losses_text}",
        )
    except Exception:
        pass
    try:
        await context.bot.send_message(
            chat_id=int(target_id),
            text=f"🌊 مرحله دوم: نیروی دریایی شما شکست خورد!\n\nتلفات شما:\n{target_losses_text}",
        )
    except Exception:
        pass
    # نتیجه‌گیری نهایی پس از مرحله دوم: مقایسه موجودی باقی‌مانده طرفین
    def _sum_forces(fd: dict) -> int:
        s = 0
        for _v in fd.values():
            try:
                s += int(_v)
            except Exception:
                continue
        return s
    attacker_remaining = _sum_forces(attack_data.get('attacker_forces_active', {})) + _sum_forces(attack_data.get('attacker_forces_reserve', {}))
    defender_remaining = 0
    for _k in ['soldiers','speedboats','naval_ship','submarines','aircraft_carriers','coastal_artillery']:
        defender_remaining += int(attack_data.get('target_forces_active', {}).get(_k, 0)) + int(utils.users[target_id]['resources'].get(_k, 0))

    total_all = max(1, attacker_remaining + defender_remaining)
    diff_ratio = abs(attacker_remaining - defender_remaining) / total_all
    if (attacker_remaining == 0 and defender_remaining == 0) or diff_ratio < 0.05:
        await naval_battle_draw(attack_id, context, attacker_remaining, defender_remaining)
        return
    if attacker_remaining > defender_remaining:
        await naval_battle_conquest(attack_id, context, attacker_remaining, defender_remaining)
    else:
        await naval_battle_defeat(attack_id, context)

async def naval_battle_phase_3(attack_id, context):
    if attack_id not in naval_attacks:
        return
    attack_data = naval_attacks[attack_id]
    user_id = attack_data['attacker_id']
    target_id = attack_data['target_id']
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    remaining_target_power = attack_data['target_power']
    
    # سیستم شانس رندوم برای تلفات مرحله سوم
    attacker_loss_rate = random.uniform(0.20, 0.40)  # 20-40% رندوم
    target_loss_rate = random.uniform(0.20, 0.40)    # 20-40% رندوم
    
    target_losses_final = int(remaining_target_power * target_loss_rate)
    attacker_losses_final = int(attack_data['attacker_power'] * attacker_loss_rate)
    
    # کسر تلفات نهایی از موجودی مهاجم
    try:
        for force_type in ['soldiers', 'speedboats', 'naval_ship', 'submarines', 'aircraft_carriers']:
            if force_type in attack_data.get('attacker_forces_active', {}):
                initial_count = int(attack_data['attacker_forces_active'].get(force_type, 0))
                losses = int(initial_count * attacker_loss_rate)
                cur_inv = int(utils.users[user_id]['resources'].get(force_type, 0))
                utils.users[user_id]['resources'][force_type] = max(0, cur_inv - losses)
    except Exception as e:
        print(f"Error deducting final attacker losses: {e}")
    
    # کسر تلفات نهایی از موجودی مدافع
    try:
        for force_type in ['soldiers', 'speedboats', 'naval_ship', 'submarines', 'aircraft_carriers', 'coastal_artillery']:
            if force_type in attack_data.get('target_forces_active', {}):
                initial_count = int(attack_data['target_forces_active'].get(force_type, 0))
                losses = int(initial_count * target_loss_rate)
                cur_inv = int(utils.users[target_id]['resources'].get(force_type, 0))
                utils.users[target_id]['resources'][force_type] = max(0, cur_inv - losses)
    except Exception as e:
        print(f"Error deducting final target losses: {e}")
    
    # بررسی جنگ مساوی
    remaining_attacker_power = attack_data['attacker_power'] - attacker_losses_final
    remaining_target_power = attack_data['target_power'] - target_losses_final
    
    if remaining_attacker_power <= 0 and remaining_target_power <= 0:
        # جنگ مساوی - هر دو طرف تمام نیروهای خود را از دست دادند
        await naval_battle_draw(attack_id, context, attacker_losses_final, target_losses_final)
    elif remaining_attacker_power <= 0:
        # حمله‌کننده شکست خورد
        await naval_battle_defeat(attack_id, context)
    elif remaining_target_power <= 0:
        # دفاع‌کننده شکست خورد
        await naval_battle_conquest(attack_id, context, attacker_losses_final, target_losses_final)
    else:
        # هر دو طرف هنوز قدرت دارند؛ برنده را با مقایسه قدرت باقی‌مانده تعیین می‌کنیم
        attack_data['attacker_power'] = remaining_attacker_power
        attack_data['target_power'] = remaining_target_power
        if remaining_attacker_power > remaining_target_power:
            await naval_battle_conquest(attack_id, context, attacker_losses_final, target_losses_final)
        elif remaining_target_power > remaining_attacker_power:
            await naval_battle_defeat(attack_id, context)
        else:
            # قدرت‌ها برابر است → مساوی
            await naval_battle_draw(attack_id, context, attacker_losses_final, target_losses_final)

async def naval_battle_conquest(attack_id, context, attacker_losses, target_losses):
    attack_data = naval_attacks[attack_id]
    user_id = attack_data['attacker_id']
    target_id = attack_data['target_id']
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    
    # بررسی مجدد که آیا کشور قبلاً فتح شده است
    if utils.users[target_id].get('conquered_by'):
        await context.bot.send_message(chat_id=int(user_id), text=f"❌ کشور {target_country} قبلاً توسط {utils.users[target_id]['conquered_by']} فتح شده است!")
        del naval_attacks[attack_id]
        return
    
    target_resources = utils.users[target_id]['resources']
    user_resources = utils.users[user_id]['resources']

    # بازگرداندن نیروهای باقی‌ماندهٔ حمله‌کننده به موجودی (نیروها در آغاز از موجودی کسر شده بودند)
    try:
        # استفاده از نیروهای باقی‌مانده بعد از تلفات
        attacker_forces_active = attack_data.get('attacker_forces_active', {})
        attacker_forces_reserve = attack_data.get('attacker_forces_reserve', {})
        
        for key in ['soldiers', 'speedboats', 'naval_ship', 'submarines', 'aircraft_carriers']:
            # جمع‌آوری نیروهای باقی‌مانده از فعال و ذخیره
            remain_active = int(attacker_forces_active.get(key, 0))
            remain_reserve = int(attacker_forces_reserve.get(key, 0))
            total_remain = remain_active + remain_reserve
            
            if total_remain > 0:
                utils.users[user_id]['resources'][key] = int(utils.users[user_id]['resources'].get(key, 0)) + total_remain
        from utils import save_users as _save_users
        _save_users()
    except Exception:
        pass
    # ثبت مبلغ نقدی انتقال‌یافته برای نمایش در مستعمرات
    try:
        original_target_cash = int(target_resources.get('cash', 0))
        utils.users[target_id]['conquered_captured_cash'] = original_target_cash
    except Exception:
        pass
    
    # انتقال تمام منابع
    for resource, amount in target_resources.items():
        if resource in user_resources:
            user_resources[resource] += amount
        else:
            user_resources[resource] = amount
        target_resources[resource] = 0
    
    # انتقال پناهجویان (جمعیت هدف به عنوان مهاجر به کشور فاتح اضافه می‌شود)
    try:
        from jame import get_country_population_by_user_id
        pop = int(get_country_population_by_user_id(target_id))
        utils.users[user_id]['immigrants'] = utils.users[user_id].get('immigrants', 0) + max(0, pop)
    except Exception:
        pass
    
    # علامت‌گذاری کشور فتح شده + انتقال مرزها و دسترسی دریا
    utils.users[target_id]['conquered_by'] = user_country
    utils.users[target_id]['conquered_at'] = time.time()
    # غیرفعال‌سازی موقت تا 6 دور
    try:
        from utils import game_data as _gd
        utils.users[target_id]['activated'] = False
        utils.users[target_id]['independence_deadline_turn'] = int(_gd.get('turn', 1)) + 6
    except Exception:
        utils.users[target_id]['activated'] = False
    # انتقال دسترسی دریا اگر هدف دریا داشت
    try:
        if has_sea_border(target_country):
            utils.users[user_id]['extra_sea_access'] = True
    except Exception:
        pass
    
    # ذخیره تغییرات
    from utils import save_users
    save_users()
    # پایان خودکار اعلان جنگ بین طرفین پس از فتح
    try:
        import utils as _utils
        from utils import save_war_declarations as _save_wars
        for wid, w in list(_utils.war_declarations.items()):
            a = w.get('attacker')
            d = w.get('defender')
            if w.get('status') == 'active' and ((a == user_country and d == target_country) or (a == target_country and d == user_country)):
                _utils.war_declarations[wid]['status'] = 'ended'
                _utils.war_declarations[wid]['end_turn'] = _utils.game_data.get('turn', 1)
                _utils.war_declarations[wid]['end_reason'] = 'conquest'
        _save_wars()
    except Exception as _:
        pass
    try:
        # ثبت پیروزی نظامی
        from utils import increment_military_win
        increment_military_win(user_id)
    except Exception:
        pass
    conquest_photo = "https://t.me/TextEmpire_IR/51"
    conquest_text = f"🏆 <b>فتح کامل!</b>\n\nکشور {user_country} ({utils.get_user_capital(user_id)}) کشور {target_country} ({utils.get_user_capital(target_id)}) را فتح کرد!\n\nتمام دارایی‌ها و منابع به کشور فاتح منتقل شد."
    try:
        await send_media_safe(context.bot, NAVAL_ATTACK_CHANNEL_ID, conquest_photo, conquest_text, 'HTML')
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=int(user_id), text=f"🏆 کشور {target_country} ({utils.get_user_capital(target_id)}) فتح شد! تمام دارایی‌ها به شما منتقل شد.")
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=int(target_id), text=f"💀 کشور شما توسط {user_country} ({utils.get_user_capital(user_id)}) فتح شد! تمام دارایی‌ها از دست رفت.")
    except Exception:
        pass
    del naval_attacks[attack_id]
    
    # ارسال درخواست پناهندگی به 5 کشور تصادفی
    try:
        from bot import send_refugee_requests_to_random_countries
        await send_refugee_requests_to_random_countries(user_country, target_country, context)
    except Exception as e:
        print(f"خطا در ارسال درخواست‌های پناهندگی: {e}")
    
    # انتقال سلسله‌مراتب مستعمرات: مستعمرات هدف به فاتح منتقل می‌شوند
    try:
        conquered_children = []
        for cid, cu in utils.users.items():
            if cu.get('conquered_by') == target_country:
                conquered_children.append(cid)
        for cid in conquered_children:
            utils.users[cid]['conquered_by'] = user_country
            utils.users[cid]['conquered_at'] = time.time()
        from utils import save_users as _save_users
        _save_users()
    except Exception:
        pass

async def naval_battle_defeat(attack_id, context):
    attack_data = naval_attacks[attack_id]
    user_id = attack_data['attacker_id']
    target_id = attack_data['target_id']
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    # بازگرداندن نیروهای باقی‌ماندهٔ حمله‌کننده به موجودی (نیروها در آغاز از موجودی کسر شده بودند)
    try:
        # استفاده از نیروهای باقی‌مانده بعد از تلفات
        attacker_forces_active = attack_data.get('attacker_forces_active', {})
        attacker_forces_reserve = attack_data.get('attacker_forces_reserve', {})
        
        for key in ['soldiers', 'speedboats', 'naval_ship', 'submarines', 'aircraft_carriers']:
            # جمع‌آوری نیروهای باقی‌مانده از فعال و ذخیره
            remain_active = int(attacker_forces_active.get(key, 0))
            remain_reserve = int(attacker_forces_reserve.get(key, 0))
            total_remain = remain_active + remain_reserve
            
            if total_remain > 0:
                utils.users[user_id]['resources'][key] = int(utils.users[user_id]['resources'].get(key, 0)) + total_remain
        save_users()
    except Exception:
        pass
    # انتخاب رندوم تصویر شکست حمله دریایی
    defeat_photos = [
        "https://t.me/TextEmpire_IR/52",
        "https://t.me/TextEmpire_IR/167"
    ]
    defeat_photo = random.choice(defeat_photos)
    defeat_text = f"❌ <b>شکست حمله دریایی!</b>\n\nحمله {user_country} به {target_country} شکست خورد!\n\nنیروهای باقی‌مانده به کشور حمله‌کننده بازگشتند."
    try:
        await send_media_safe(context.bot, NAVAL_ATTACK_CHANNEL_ID, defeat_photo, defeat_text, 'HTML')
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=int(user_id), text=f"❌ حمله دریایی به {target_country} شکست خورد! نیروهای باقی‌مانده بازگشتند.")
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=int(target_id), text=f"✅ حمله دریایی {user_country} دفع شد! کشور شما محافظت شد.")
    except Exception:
        pass
    del naval_attacks[attack_id]
    
    # ارسال درخواست پناهندگی به 5 کشور تصادفی
    try:
        from bot import send_refugee_requests_to_random_countries
        await send_refugee_requests_to_random_countries(user_country, target_country, context)
    except Exception as e:
        print(f"خطا در ارسال درخواست‌های پناهندگی: {e}")
async def naval_battle_draw(attack_id, context, attacker_losses, target_losses):
    attack_data = naval_attacks[attack_id]
    user_id = attack_data['attacker_id']
    target_id = attack_data['target_id']
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    
    # بازگرداندن نیروهای باقی‌ماندهٔ حمله‌کننده به موجودی (نیروها در آغاز از موجودی کسر شده بودند)
    try:
        # استفاده از نیروهای باقی‌مانده بعد از تلفات
        attacker_forces_active = attack_data.get('attacker_forces_active', {})
        attacker_forces_reserve = attack_data.get('attacker_forces_reserve', {})
        
        for key in ['soldiers', 'speedboats', 'naval_ship', 'submarines', 'aircraft_carriers']:
            # جمع‌آوری نیروهای باقی‌مانده از فعال و ذخیره
            remain_active = int(attacker_forces_active.get(key, 0))
            remain_reserve = int(attacker_forces_reserve.get(key, 0))
            total_remain = remain_active + remain_reserve
            
            if total_remain > 0:
                utils.users[user_id]['resources'][key] = int(utils.users[user_id]['resources'].get(key, 0)) + total_remain
        from utils import save_users
        save_users()
    except Exception:
        pass
    
    # انتخاب رندوم تصویر جنگ برابر دریایی
    draw_photos = [
        "https://t.me/TextEmpire_IR/52",
        "https://t.me/TextEmpire_IR/167"
    ]
    draw_photo = random.choice(draw_photos)
    draw_text = (
        f"⚖️ <b>جنگ برابر!</b>\n\n"
        f"هیچ یک از طرفین پیروز نشد!\n\n"
        f"قدرت‌های دنیا برقراری صلح بین دو طرف خواستار شدند.\n"
        f"سازمان ملل طرفین را به جلسه فوری شورای امنیت فراخواند.\n\n"
        f"تلفات {user_country}: {attacker_losses:,}\n"
        f"تلفات {target_country}: {target_losses:,}"
    )
    try:
        await send_media_safe(context.bot, NAVAL_ATTACK_CHANNEL_ID, draw_photo, draw_text, 'HTML')
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=int(user_id), text=f"⚖️ جنگ با {target_country} مساوی شد! سازمان ملل درخواست صلح داد.")
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=int(target_id), text=f"⚖️ جنگ با {user_country} مساوی شد! سازمان ملل درخواست صلح داد.")
    except Exception:
        pass
    del naval_attacks[attack_id]
    
    # ارسال درخواست پناهندگی به 5 کشور تصادفی
    try:
        from bot import send_refugee_requests_to_random_countries
        await send_refugee_requests_to_random_countries(user_country, target_country, context)
    except Exception as e:
        print(f"خطا در ارسال درخواست‌های پناهندگی: {e}")
async def handle_sea_raid_forces(update, context):
    user_id = str(update.effective_user.id)
    trade_id = pending_sea_raid.get(user_id)
    if not trade_id:
        return

    # استخراج تعداد نیروها
    text = update.message.text if hasattr(update.message, 'text') and update.message.text else ""
    import re
    special_forces = 0
    speedboats = 0
    soldiers = 0
    for line in text.split('\n'):
        if 'ویژه' in line:
            nums = re.findall(r'\d+', line)
            if nums:
                special_forces = int(nums[0])
        if 'قایق' in line:
            nums = re.findall(r'\d+', line)
            if nums:
                speedboats = int(nums[0])
        if 'سرباز' in line:
            nums = re.findall(r'\d+', line)
            if nums:
                soldiers = int(nums[0])

    user_resources = utils.users[user_id]['resources']
    if user_resources.get('special_forces', 0) < special_forces or user_resources.get('speedboats', 0) < speedboats or user_resources.get('soldiers', 0) < soldiers:
        await update.message.reply_text('موجودی کافی از نیروی ویژه، قایق تندرو یا سرباز ندارید.')
        del pending_sea_raid[user_id]
        return

    # کم کردن نیروها
    user_resources['special_forces'] -= special_forces
    user_resources['speedboats'] -= speedboats
    user_resources['soldiers'] -= soldiers
    save_users()

    # پیدا کردن تجارت یا محموله کمک اتحاد
    trade = None
    is_alliance_trade = False
    
    if trade_id.startswith('alliance_'):
        # محموله کمک اتحاد
        from diplomaci import alliance_trades
        alliance_trade_id = trade_id.replace('alliance_', '')
        trade = alliance_trades.get(alliance_trade_id)
        is_alliance_trade = True
    else:
        # تجارت معمولی
        trade = next((t for t in pending_trades if t['id'] == trade_id and t['status'] == 'pending'), None)
    
    if not trade:
        await update.message.reply_text('کشتی تجاری یا محموله مورد نظر یافت نشد یا دیگر در مسیر نیست.')
        del pending_sea_raid[user_id]
        return

    # شانس موفقیت بر اساس اسکورت
    if trade.get('has_escort', False):
        # با اسکورت: 90% شانس موفقیت برای دفاع
        success = random.random() < 0.1  # 10% شانس موفقیت حمله
    else:
        # بدون اسکورت: 50% شانس موفقیت
        success = random.random() < 0.5  # 50% شانس موفقیت حمله

    if success:
        if is_alliance_trade:
            # غارت محموله کمک اتحاد
            utils.users[user_id]['resources'][trade['resource']] = utils.users[user_id]['resources'].get(trade['resource'], 0) + trade['amount']
            trade['status'] = 'looted'
            save_users()
            
            # پیام به کانال اخبار
            from_country = utils.users.get(trade['from_id'], {}).get('country', 'نامشخص')
            to_country = utils.users.get(trade['to_id'], {}).get('country', 'نامشخص')
            news_msg = f"🚢 محموله کمک اتحاد حامل {trade['amount']} واحد {trade['resource']} از {from_country} به مقصد {to_country} در مسیر توسط کشور {utils.users[user_id]['country']} غارت شد!"
            raid_success_photo_id = "https://t.me/TextEmpire_IR/39"
            await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=raid_success_photo_id, caption=news_msg, parse_mode='HTML')

            # پیام به ارسال‌کننده کمک
            await context.bot.send_photo(
                chat_id=int(trade['from_id']),
                photo=raid_success_photo_id,
                caption=f"⚠️ محموله کمک شما که قرار بود {trade['amount']} واحد {trade['resource']} به {to_country} ارسال کند، در مسیر توسط {utils.users[user_id]['country']} غارت شد و محموله به مقصد نرسید.",
                parse_mode='HTML'
            )

            # پیام به دریافت‌کننده کمک
            await context.bot.send_photo(
                chat_id=int(trade['to_id']),
                photo=raid_success_photo_id,
                caption=f"⚠️ محموله کمک شما که قرار بود {trade['amount']} واحد {trade['resource']} از {from_country} دریافت کند، در مسیر توسط {utils.users[user_id]['country']} غارت شد و محموله به مقصد نرسید.",
                parse_mode='HTML'
            )

            # پیام به دزد (حمله‌کننده)
            await context.bot.send_photo(
                chat_id=int(user_id),
                photo=raid_success_photo_id,
                caption=f"🏴‍☠️ حمله شما به محموله کمک اتحاد موفقیت‌آمیز بود و {trade['amount']} واحد {trade['resource']} به دست آوردید!",
                parse_mode='HTML'
            )

            await update.message.reply_text('✅ حمله موفقیت‌آمیز بود و تمام منابع محموله کمک به شما منتقل شد!')
        else:
            # غارت کشتی تجاری معمولی
            utils.users[user_id]['resources']['cash'] += trade['total_price']
            utils.users[user_id]['resources'][trade['resource']] = utils.users[user_id]['resources'].get(trade['resource'], 0) + trade['amount']
            trade['status'] = 'looted'
            save_users()
                    
        # پیام به کانال اخبار
        news_msg = f"🚢 کشتی تجاری حامل {trade['amount']} واحد {trade['resource']} از {trade['seller_country']} به مقصد {trade['buyer_country']} در مسیر توسط کشور {utils.users[user_id]['country']} غارت شد!"
        raid_success_photo_id = "https://t.me/TextEmpire_IR/39"
        await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=raid_success_photo_id, caption=news_msg, parse_mode='HTML')

        # پیام به خریدار
        await context.bot.send_photo(
            chat_id=int(trade['buyer_id']),
            photo=raid_success_photo_id,
            caption=f"⚠️ کشتی تجاری شما که قرار بود {trade['amount']} واحد {trade['resource']} از {trade['seller_country']} دریافت کند، در مسیر توسط {utils.users[user_id]['country']} غارت شد و محموله به مقصد نرسید.",
            parse_mode='HTML'
        )

        # پیام به فروشنده
        await context.bot.send_photo(
            chat_id=int(trade['seller_id']),
            photo=raid_success_photo_id,
            caption=f"⚠️ کشتی تجاری شما که قرار بود {trade['amount']} واحد {trade['resource']} به {trade['buyer_country']} ارسال کند، در مسیر توسط {utils.users[user_id]['country']} غارت شد و محموله به مقصد نرسید.",
            parse_mode='HTML'
        )

        # پیام به دزد (حمله‌کننده)
        await context.bot.send_photo(
            chat_id=int(user_id),
            photo=raid_success_photo_id,
            caption=f"🏴‍☠️ حمله شما به کشتی تجاری موفقیت‌آمیز بود و {trade['amount']} واحد {trade['resource']} به ارزش {trade['total_price']:,} دلار به دست آوردید!",
            parse_mode='HTML'
        )

        await update.message.reply_text('✅ حمله موفقیت‌آمیز بود و تمام منابع و پول کشتی به شما منتقل شد!')
    else:
        if is_alliance_trade:
            # محموله کمک اتحاد به سلامت عبور کرد
            from_country = utils.users.get(trade['from_id'], {}).get('country', 'نامشخص')
            to_country = utils.users.get(trade['to_id'], {}).get('country', 'نامشخص')
            news_msg = f"🚢 حمله ناموفق به محموله کمک اتحاد حامل {trade['amount']} واحد {trade['resource']} از {from_country} به مقصد {to_country} در مسیر انجام شد اما محموله به سلامت عبور کرد."
            await context.bot.send_message(NEWS_CHANNEL_ID, news_msg)
            await update.message.reply_text('حمله شما ناموفق بود و محموله کمک به مسیر خود ادامه داد.')
        else:
            # کشتی تجاری به روال عادی ادامه پیدا می‌کند
        # پیام به کانال اخبار (بدون ذکر نام کشور غارت‌کننده)
            news_msg = f"🚢 حمله ناموفق به کشتی تجاری حامل {trade['amount']} واحد {trade['resource']} از {trade['seller_country']} به مقصد {trade['buyer_country']} در مسیر انجام شد اما کشتی به سلامت عبور کرد."
            await context.bot.send_message(NEWS_CHANNEL_ID, news_msg)
            await update.message.reply_text('حمله شما ناموفق بود و کشتی به مسیر خود ادامه داد.')
    del pending_sea_raid[user_id]
async def show_attackable_countries(query):
    user_id = str(query.from_user.id)
    if user_id not in users:
        await query.answer("شما در بازی ثبت‌نام نکرده‌اید!")
        return
    
    initialize_user_resources(user_id)
    user_country = utils.users[user_id]['country']
    
    # استفاده از ژنرال انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'general' in selected_officials:
        general = selected_officials['general']
    else:
        general = {'name': 'ژنرال', 'title': 'ژنرال'}
    
    # پیدا کردن کشورهای هم‌مرز که در جنگ فعال هستند (ساختار جدید)
    attackable_countries = []
    # استفاده از مرزهای مؤثر شامل مرزهای فتح شده
    from utils import get_effective_land_borders
    borders = get_effective_land_borders(user_id)
    for border_country in borders:
        # بررسی جنگ فعال بین کشور کاربر و کشور مرزی
        in_war = False
        for wid, w in utils.war_declarations.items():
            if w.get('status') == 'active' and (
                (w.get('attacker') == user_country and w.get('defender') == border_country) or
                (w.get('defender') == user_country and w.get('attacker') == border_country)
            ):
                in_war = True
                break
        if in_war:
                # کشورهایی که قبلاً فتح شده‌اند را نمایش نده
                try:
                    # پیدا کردن user_id کشور مرزی
                    target_id = None
                    for uid, u in utils.users.items():
                        if u.get('country') == border_country:
                            target_id = uid
                            break
                    if target_id and utils.users.get(target_id, {}).get('conquered_by'):
                        continue
                except Exception:
                    pass
                attackable_countries.append(border_country)
    
    if not attackable_countries:
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"⚔️ {general['name']}: رهبر محترم، هیچ کشور قابل حمله‌ای یافت نشد!\n\n"
        text += "برای حمله زمینی باید:\n"
        text += "1. کشور هدف هم‌مرز زمینی باشد\n"
        text += "2. قبلاً به آن کشور اعلان جنگ کرده باشید"
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    # ایجاد دکمه‌ها (کلیک روی کشور → نمایش تحلیل اختصاصی)
    keyboard = []
    for i in range(0, len(attackable_countries), 2):
        row = []
        row.append(InlineKeyboardButton(attackable_countries[i], callback_data=f'ground_target_{attackable_countries[i]}'))
        if i + 1 < len(attackable_countries):
            row.append(InlineKeyboardButton(attackable_countries[i + 1], callback_data=f'ground_target_{attackable_countries[i + 1]}'))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"⚔️ {general['name']}: رهبر محترم، کشور مورد نظر برای حمله زمینی را انتخاب کنید:\n\n"
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_air_attackable_countries(query):
    user_id = str(query.from_user.id)
    if user_id not in utils.users:
        await query.answer("شما در بازی ثبت‌نام نکرده‌اید!")
        return
    
    initialize_user_resources(user_id)
    user_country = utils.users[user_id]['country']
    
    # استفاده از ژنرال انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'general' in selected_officials:
        general = selected_officials['general']
    else:
        general = {'name': 'ژنرال', 'title': 'ژنرال'}
    
    # پیدا کردن تمام کشورهایی که در جنگ فعال هستند (بدون محدودیت هم‌مرز بودن)
    attackable_countries = []
    for wid, w in utils.war_declarations.items():
        if w.get('status') == 'active' and (w.get('attacker') == user_country or w.get('defender') == user_country):
            other = w.get('defender') if w.get('attacker') == user_country else w.get('attacker')
            if other and other != user_country:
                attackable_countries.append(other)
    
    # حذف موارد تکراری با نرمال‌سازی و کاننیکال‌سازی نام
    try:
        from utils import _normalize_country_name, get_canonical_country_name
        unique_map = {}
        for cname in attackable_countries:
            canon = get_canonical_country_name(cname)
            norm = _normalize_country_name(canon)
            if norm and norm not in unique_map:
                unique_map[norm] = canon
        attackable_countries = list(unique_map.values())
    except Exception:
        pass
    
    if not attackable_countries:
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"🛩️ {general['name']}: رهبر محترم، هیچ کشور قابل حمله‌ای یافت نشد!\n\n"
        text += "برای حمله هوایی باید:\n"
        text += "1. قبلاً به کشور هدف اعلان جنگ کرده باشید\n"
        text += "2. کشور هدف در بازی فعال باشد"
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    # ایجاد دکمه‌ها (کلیک روی کشور → نمایش تحلیل اختصاصی)
    keyboard = []
    for i in range(0, len(attackable_countries), 2):
        row = []
        row.append(InlineKeyboardButton(attackable_countries[i], callback_data=f'air_target_{attackable_countries[i]}'))
        if i + 1 < len(attackable_countries):
            row.append(InlineKeyboardButton(attackable_countries[i + 1], callback_data=f'air_target_{attackable_countries[i + 1]}'))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"🛩️ {general['name']}: رهبر محترم، کشور مورد نظر برای حمله هوایی را انتخاب کنید:\n\n"
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# تابع نمایش موجودی نیروهای زمینی
async def show_ground_forces_inventory(query, target_country):
    user_id = str(query.from_user.id)
    initialize_user_resources(user_id)
    user_resources = utils.users[user_id]['resources']
    
    # استفاده از ژنرال انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'general' in selected_officials:
        general = selected_officials['general']
    else:
        general = {'name': 'ژنرال', 'title': 'ژنرال'}
    
    # پیدا کردن target_id
    target_id = None
    for uid, user_data in utils.users.items():
        if user_data.get('country') == target_country:
            target_id = uid
            break
    
    # نیروهای زمینی
    ground_forces = {
        'سربازان': user_resources.get('soldiers', 0),
        'نیروی ویژه': user_resources.get('special_forces', 0),
        'تانک': user_resources.get('tanks', 0),
        'نفربر': user_resources.get('armored_vehicles', 0),
        'توپخانه': user_resources.get('artillery', 0),
        'ربات جنگی': user_resources.get('war_robots', 0)
    }
    
    inventory_text = f"🪖 <b>گزارش {general['title']} {general['name']}:</b>\n\n"
    inventory_text += f"⚔️ {general['name']}: رهبر محترم، موجودی نیروهای زمینی برای حمله به {target_country}:\n\n"
    inventory_text += "<code>"
    for force, amount in ground_forces.items():
        inventory_text += f"{force}: {amount:,}\n"
    inventory_text += "</code>"
    
    inventory_text += f"\n📋 {general['name']}: لطفاً متن بالا را کپی کنید و تعداد نیروهایی که می‌خواهید ارسال کنید را به همین ترتیب وارد کنید."
    
    # ذخیره اطلاعات حمله
    pending_ground_attack[user_id] = {
        'target': target_country,
        'target_id': target_id,  # اضافه کردن target_id
        'step': 'amount',
        'ground_forces': ground_forces
    }
    
    keyboard = [
        [InlineKeyboardButton('لغو حمله زمینی ❌', callback_data='cancel_ground_attack')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='ground_attack')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(inventory_text, reply_markup=reply_markup, parse_mode='HTML')

# تابع نمایش موجودی نیروهای هوایی
async def show_air_forces_inventory(query, target_country):
    user_id = str(query.from_user.id)
    initialize_user_resources(user_id)
    user_resources = utils.users[user_id]['resources']
    
    # استفاده از ژنرال انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'general' in selected_officials:
        general = selected_officials['general']
    else:
        general = {'name': 'ژنرال', 'title': 'ژنرال'}
    
    # پیدا کردن target_id
    target_id = None
    for uid, user_data in users.items():
        if user_data.get('country') == target_country:
            target_id = uid
            break
    
    # نیروهای هوایی (بدون پدافند هوایی)
    air_forces = {
        'هواپیمای ترابری': user_resources.get('transport_planes', 0),
        'بالگرد': user_resources.get('helicopters', 0),
        'جنگنده': user_resources.get('fighter_jets', 0),
        'بمب‌افکن': user_resources.get('bombers', 0),
        'پهپاد': user_resources.get('drones', 0)
    }
    
    inventory_text = f"🛩️ <b>گزارش {general['title']} {general['name']}:</b>\n\n"
    inventory_text += f"⚔️ {general['name']}: رهبر محترم، موجودی نیروهای هوایی برای حمله به {target_country}:\n\n"
    inventory_text += "<code>"
    for force, amount in air_forces.items():
        inventory_text += f"{force}: {amount:,}\n"
    inventory_text += "</code>"
    
    inventory_text += f"\n📋 {general['name']}: لطفاً متن بالا را کپی کنید و تعداد نیروهایی که می‌خواهید ارسال کنید را به همین ترتیب وارد کنید."
    
    # ذخیره اطلاعات حمله هوایی
    pending_air_attack[user_id] = {
        'target': target_country,
        'target_id': target_id,  # اضافه کردن target_id
        'step': 'amount',
        'air_forces': air_forces
    }
    
    keyboard = [
        [InlineKeyboardButton('لغو حمله هوایی ❌', callback_data='cancel_air_attack')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='air_attack')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(inventory_text, reply_markup=reply_markup, parse_mode='HTML')

# تابع پردازش تعداد نیروهای ارسالی
async def process_attack_forces(message, context):
    user_id = str(message.from_user.id)
    if user_id not in pending_ground_attack:
        return
    
    attack_data = pending_ground_attack[user_id]
    user_resources = utils.users[user_id]['resources']
    
    try:
        # پردازش متن ارسالی
        lines = message.text.strip().split('\n')
        requested_forces = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # تبدیل نام نیرو به کلید دیتابیس
            force_mapping = {
                'سربازان': 'soldiers',
                'نیروی ویژه': 'special_forces',
                'تانک': 'tanks',
                'نفربر': 'armored_vehicles',
                'توپخانه': 'artillery',
                'ربات جنگی': 'war_robots'
            }
            
            if ':' in line:
                force_name, amount_str = line.split(':', 1)
                force_name = force_name.strip()
                amount_str = amount_str.strip()
                
                # بررسی دقیق‌تر نام نیرو (حذف فاصله‌های اضافی و کاراکترهای نامرئی)
                force_name_clean = force_name.replace('\u200c', '').replace('\u200d', '').strip()
                
                if force_name_clean in force_mapping:
                    try:
                        amount = int(amount_str.replace(',', ''))
                        if amount > 0:
                            requested_forces[force_mapping[force_name_clean]] = amount
                    except ValueError:
                        continue
        
        if not requested_forces:
            await message.reply_text('❌ هیچ نیروی معتبری یافت نشد. لطفاً دوباره تلاش کنید.')
            return
        
        # بررسی موجودی نیروها
        insufficient_forces = []
        for force, requested_amount in requested_forces.items():
            available = user_resources.get(force, 0)
            if available < requested_amount:
                insufficient_forces.append(f"{force}: {available}/{requested_amount}")
        
        if insufficient_forces:
            await message.reply_text(f'❌ نیروهای کافی ندارید:\n' + '\n'.join(insufficient_forces))
            return
            
        # کسر نیروها از موجودی
        for force, amount in requested_forces.items():
            user_resources[force] -= amount
        
        # ذخیره تغییرات
        from utils import save_users
        save_users()
        
        # شروع جنگ زمینی
        await start_ground_battle(message, attack_data, context)
        
    except Exception as e:
        print(f"خطا در پردازش نیروهای زمینی: {e}")
        await message.reply_text('❌ خطا در پردازش اطلاعات. لطفاً دوباره تلاش کنید.')
async def start_ground_battle(message, attack_data, context):
    user_id = str(message.from_user.id)
    target_country = attack_data['target']
    
    # استفاده از target_id ذخیره شده یا پیدا کردن آن
    target_id = attack_data.get('target_id')
    if not target_id:
        # پیدا کردن target_id
        for uid, user_data in utils.users.items():
            if user_data.get('country') == target_country:
                target_id = uid
                break
    
    if not target_id:
        await message.reply_text('❌ کشور هدف یافت نشد.')
        return
    
    # دریافت نیروهای حمله‌کننده
    attacker_forces = attack_data.get('forces', {})
    
    # دریافت نیروهای دفاع‌کننده
    initialize_user_resources(target_id)
    target_resources = utils.users[target_id]['resources']
    target_forces = {
        'soldiers': target_resources.get('soldiers', 0),
        'special_forces': target_resources.get('special_forces', 0),
        'tanks': target_resources.get('tanks', 0),
        'armored_vehicles': target_resources.get('armored_vehicles', 0),
        'artillery': target_resources.get('artillery', 0),
        'war_robots': target_resources.get('war_robots', 0)
    }
    
    # ساخت شناسه و ثبت حمله برای حل ساده با تاخیر
    if 'ground_attack_counter' not in globals():
        global ground_attack_counter
        ground_attack_counter = 0
    ground_attack_counter += 1
    attack_id = f"ground_{ground_attack_counter}"
    # ذخیره داده‌های لازم
    ground_attacks[attack_id] = {
        'attacker_id': user_id,
        'target_id': target_id,
        'attacker_forces': attacker_forces,
        'target_forces': target_forces,
        'start_time': time.time()
    }
    # اعلام برنامه‌ریزی حمله (پیام به دو طرف و کانال)
    try:
        user_country = utils.users[user_id]['country']
        target_country = utils.users[target_id]['country']
        plan_text = (
            f"🕒 <b>آغاز جنگ زمینی برنامه‌ریزی شد</b>\n\n"
            f"⚔️ {user_country} → {target_country}\n"
            f"🆔 شناسه نبرد: {attack_id}\n"
            f"⏳ شروع تا 5 دقیقه آینده"
        )
        from utils import NEWS_CHANNEL_ID
        try:
            await message.reply_text(plan_text, parse_mode='HTML')
        except Exception:
            pass
        try:
            await context.bot.send_message(chat_id=int(target_id), text=plan_text, parse_mode='HTML')
        except Exception:
            pass
        try:
            await context.bot.send_message(chat_id=NEWS_CHANNEL_ID, text=plan_text, parse_mode='HTML')
        except Exception:
            pass
    except Exception:
        pass
    # زمان‌بندی حل جنگ بعد از 5 دقیقه
    def _runner(ctx):
        return asyncio.create_task(resolve_ground_battle_simple(attack_id, ctx))
    context.job_queue.run_once(lambda ctx: _runner(ctx), 300)
    
    # پاک‌سازی حالت انتظار
    if user_id in pending_ground_attack:
        del pending_ground_attack[user_id]

async def resolve_ground_battle_simple(attack_id, context):
    # استخراج داده‌ها
    attack = ground_attacks.get(attack_id)
    if not attack:
        return
    user_id = attack['attacker_id']
    target_id = attack['target_id']
    user_country = utils.users.get(user_id, {}).get('country', '')
    target_country = utils.users.get(target_id, {}).get('country', '')
    attacker_forces = dict(attack.get('attacker_forces', {}))
    target_forces = dict(attack.get('target_forces', {}))

    # ضرایب قدرت پایه طبق درخواست
    BASE = {
        'soldiers': 1,
        'special_forces': 8,
        'tanks': 100,
        'armored_vehicles': 20,
        'artillery': 100,       # فقط برای مدافع اعمال می‌شود
        'war_robots': 50,
    }

    # عامل آب‌وهوا
    def get_weather_factor():
        # می‌توانید به داده‌های بازی وصل کنید؛ فعلاً تصادفی/نرمال
        return ('معمولی', 1.10)

    weather_name, weather_factor = get_weather_factor()

    # لول فناوری‌ها
    try:
        techs_att = utils.military_technologies.get(str(user_id), {})
        techs_def = utils.military_technologies.get(str(target_id), {})
    except Exception:
        techs_att, techs_def = {}, {}

    def _power(forces: dict, techs: dict, is_defender: bool) -> float:
        total = 0.0
        for k, v in forces.items():
            if k == 'artillery' and not is_defender:
                continue
            base = BASE.get(k, 0)
            if base <= 0:
                continue
            lvl = max(1, int(techs.get(k, 1)))
            total += int(v) * base * lvl
        return total * weather_factor

    attacker_power = _power(attacker_forces, techs_att, False)
    defender_power = _power(target_forces, techs_def, True)

    # تلفات نسبتی ساده بر اساس نسبت قدرت‌ها
    def _loss_rate(my, other):
        if my <= 0:
            return 0.5
        ratio = min(2.0, max(0.0, other / my))
        return min(0.5, max(0.05, 0.15 * ratio))

    att_loss_rate = _loss_rate(attacker_power, defender_power)
    def_loss_rate = _loss_rate(defender_power, attacker_power)

    # اعمال تلفات به شمارش نیروها
    def _apply_losses(forces: dict, rate: float, is_defender: bool) -> dict:
        out = {}
        for k, v in forces.items():
            if k == 'artillery' and not is_defender:
                out[k] = int(v)
                continue
            lost = int(int(v) * rate)
            out[k] = max(0, int(v) - lost)
        return out

    attacker_remain = _apply_losses(attacker_forces, att_loss_rate, False)
    defender_remain = _apply_losses(target_forces, def_loss_rate, True)

    # تعیین نتیجه
    outcome = 'draw'
    if sum(defender_remain.values()) == 0 or defender_power <= 0:
        outcome = 'conquest'
    elif sum(attacker_remain.values()) == 0 or attacker_power <= 0:
        outcome = 'defeat'

    # بازگرداندن نیروهای باقی‌مانده به حمله‌کننده
    try:
        ur = utils.users[user_id]['resources']
        for k, v in attacker_remain.items():
            if v > 0:
                ur[k] = ur.get(k, 0) + int(v)
        from utils import save_users as _save
        _save()
    except Exception:
        pass

    # کم کردن تلفات از مدافع
    try:
        dr = utils.users[target_id]['resources']
        for k, v in target_forces.items():
            remain = defender_remain.get(k, 0)
            lost = max(0, int(v) - int(remain))
            if lost > 0:
                cur = int(dr.get(k, 0))
                dr[k] = max(0, cur - lost)
        from utils import save_users as _save
        _save()
    except Exception:
        pass

    # پیام نتیجه برای دو طرف و کانال
    caption = (
        f"⚔️ نتیجه جنگ زمینی\n\n"
        f"🌦️ وضعیت: {weather_name}\n"
        f"🗡️ {user_country} → 🛡️ {target_country}\n"
        f"⚖️ قدرت حمله: {int(attacker_power):,} | دفاع: {int(defender_power):,}\n"
    )
    if outcome == 'conquest':
        caption = "🏆 پیروزی حمله‌کننده و فتح کشور!\n\n" + caption
        # ثبت فتح و پایان جنگ فعال
        try:
            # علامت‌گذاری کشور هدف
            utils.users[target_id]['conquered_by'] = user_country
            utils.users[target_id]['conquered_at'] = time.time()
            from utils import save_users as _su
            _su()
        except Exception:
            pass
        # پایان جنگ‌های فعال
        try:
            for wid, w in list(utils.war_declarations.items()):
                a = w.get('attacker'); d = w.get('defender')
                if w.get('status') == 'active' and ((a == user_country and d == target_country) or (a == target_country and d == user_country)):
                    utils.war_declarations[wid]['status'] = 'ended'
                    utils.war_declarations[wid]['end_reason'] = 'conquest'
            utils.save_war_declarations()
        except Exception:
            pass
    elif outcome == 'defeat':
        caption = "❌ شکست حمله‌کننده!\n\n" + caption
        try:
            for wid, w in list(utils.war_declarations.items()):
                a = w.get('attacker'); d = w.get('defender')
                if w.get('status') == 'active' and ((a == user_country and d == target_country) or (a == target_country and d == user_country)):
                    utils.war_declarations[wid]['status'] = 'ended'
                    utils.war_declarations[wid]['end_reason'] = 'defeat'
            utils.save_war_declarations()
        except Exception:
            pass
    else:
        caption = "🤝 نتیجه مساوی، جنگ پایان یافت.\n\n" + caption
        try:
            for wid, w in list(utils.war_declarations.items()):
                a = w.get('attacker'); d = w.get('defender')
                if w.get('status') == 'active' and ((a == user_country and d == target_country) or (a == target_country and d == user_country)):
                    utils.war_declarations[wid]['status'] = 'ended'
                    utils.war_declarations[wid]['end_reason'] = 'draw'
            utils.save_war_declarations()
        except Exception:
            pass

    try:
        await context.bot.send_message(chat_id=int(user_id), text=caption)
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=int(target_id), text=caption)
    except Exception:
        pass
    try:
        await context.bot.send_message(chat_id=utils.NEWS_CHANNEL_ID, text=caption)
    except Exception:
        pass

    # پاکسازی
    try:
        del ground_attacks[attack_id]
    except Exception:
        pass

# تابع شروع نبرد هوایی
async def start_air_battle(message, attack_data, context):
    user_id = str(message.from_user.id)
    target_country = attack_data['target']
    user_resources = utils.users[user_id].get('resources', {})
    
    # استفاده از target_id ذخیره شده یا پیدا کردن آن
    target_id = attack_data.get('target_id')
    if not target_id:
        # پیدا کردن target_id با تطبیق مقاوم در برابر ایموجی/فاصله/حروف کوچک-بزرگ
        try:
            import re
            def normalize(name: str) -> str:
                if not isinstance(name, str):
                    name = str(name)
                name = name.replace('\u200c', '').replace('\u200d', '')
                name = re.sub(r'[^\w\s\u0600-\u06FF]', '', name)
                return re.sub(r'\s+', ' ', name).strip().lower()
            target_norm = normalize(target_country)
            for uid, user_data in utils.users.items():
                if normalize(user_data.get('country', '')) == target_norm:
                    target_id = uid
                    break
            if not target_id:
                for uid, user_data in utils.users.items():
                    cn = normalize(user_data.get('country', ''))
                    if target_norm and target_norm in cn:
                        target_id = uid
                        break
        except Exception:
            pass
    
    if not target_id:
        # در صورت عدم یافتن هدف، نیروهای کسرشده را برگردان
        try:
            forces = attack_data.get('forces', {}) or {}
            if forces:
                for k, amount in forces.items():
                    try:
                        amt = int(amount)
                    except Exception:
                        amt = 0
                    if amt > 0:
                        # بازگرداندن به موجودی کاربر
                        utils.users[user_id]['resources'][k] = int(utils.users[user_id]['resources'].get(k, 0)) + amt
                save_users()
        except Exception as _e:
            print(f"[air_refund] error on target_not_found refund: {_e}")
        await message.reply_text('❌ کشور هدف یافت نشد.')
        return

    # جلوگیری از حمله به کشوری که قبلاً فتح شده است
    try:
        if utils.users.get(target_id, {}).get('conquered_by'):
            conqueror = utils.users[target_id].get('conquered_by')
            # بازگرداندن نیروهای هوایی اعزامی به دلیل لغو حمله
            try:
                forces = attack_data.get('forces', {}) or {}
                if forces:
                    for k, amount in forces.items():
                        try:
                            amt = int(amount)
                        except Exception:
                            amt = 0
                        if amt > 0:
                            # بازگرداندن به موجودی کاربر
                            utils.users[user_id]['resources'][k] = int(utils.users[user_id]['resources'].get(k, 0)) + amt
                    save_users()
            except Exception as _e:
                print(f"[air_refund] error on conquered_by refund: {_e}")
            await message.reply_text(f"❌ حمله ناموفق!\n\nکشور {target_country} قبلاً توسط {conqueror} فتح شده است و قابل هدف قرار دادن نیست.")
            return
    except Exception:
        pass

    # جلوگیری از حمله به کشوری که صلح اجباری فعال دارد
    try:
        from bot import is_user_peace_protected
        if is_user_peace_protected(target_id):
            turns = utils.users[target_id].get('diplomacy', {}).get('forced_peace_turns', 0)
            await message.reply_text(
                f"❌ حمله ناموفق!\n\n🤝 کشور {target_country} تحت صلح اجباری است.\n⏰ {turns} نوبت باقی‌مانده"
            )
            return
    except Exception:
        pass
    
    # دریافت نیروهای حمله‌کننده
    attacker_forces = attack_data.get('forces', {})
    
    # دریافت نیروهای دفاع‌کننده
    initialize_user_resources(target_id)
    target_resources = utils.users[target_id]['resources']
    target_forces = {
        'transport_planes': target_resources.get('transport_planes', 0),
        'helicopters': target_resources.get('helicopters', 0),
        'fighter_jets': target_resources.get('fighter_jets', 0),
        'bombers': target_resources.get('bombers', 0),
        'drones': target_resources.get('drones', 0),
        'air_defense': target_resources.get('air_defense', 0)
    }
    
    # شبیه‌سازی جنگ هوایی جدید
    battle_result = simulate_air_battle_new(attacker_forces, target_forces, user_id, target_id)
    
    # برنامه‌ریزی مراحل جنگ هوایی
    await schedule_air_battle_phases_new(user_id, target_id, attacker_forces, target_forces, battle_result, context)
    
    # پاک‌سازی حالت انتظار
    if user_id in pending_air_attack:
        del pending_air_attack[user_id]

# تابع زمان‌بندی اعلام نتیجه نبرد
async def schedule_battle_result(user_id, target_country, battle_result, attacker_forces, context):
    # انتظار 2 دقیقه
    await asyncio.sleep(120)
    
    user_country = utils.users[user_id]['country']
    
    if battle_result['victory']:
        # پیام پیروزی
        victory_msg = f"🏆 <b>پیروزی در نبرد!</b>\n\nکشور {user_country} در نبرد با {target_country} پیروز شد!\n\n"
        victory_msg += "نیروهای ارسالی:\n"
        for force, amount in attacker_forces.items():
            victory_msg += f"▫️ {force}: {amount:,}\n"
        
        try:
            await send_media_safe(context.bot, int(user_id), "https://t.me/TextEmpire_IR/66", victory_msg, 'HTML')
        except Exception as e:
            print(f"خطا در ارسال پیام پیروزی: {e}")
    else:
        # پیام شکست
        defeat_msg = f"❌ <b>شکست در نبرد!</b>\n\nکشور {user_country} در نبرد با {target_country} شکست خورد!\n\n"
        defeat_msg += "نیروهای ارسالی:\n"
        for force, amount in attacker_forces.items():
            defeat_msg += f"▫️ {force}: {amount:,}\n"
        
        try:
            await send_media_safe(context.bot, int(user_id), "https://t.me/TextEmpire_IR/65", defeat_msg, 'HTML')
        except Exception as e:
            print(f"خطا در ارسال پیام شکست: {e}")

async def show_loot_menu(query):
    user_id = str(query.from_user.id)
    if user_id not in users:
        await query.answer("شما در بازی ثبت‌نام نکرده‌اید!")
        return

    initialize_user_resources(user_id)
    user_country = utils.users[user_id]['country']
    
    # استفاده از ژنرال انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'general' in selected_officials:
        general = selected_officials['general']
    else:
        general = {'name': 'ژنرال', 'title': 'ژنرال'}

    # پیدا کردن کاروان‌های تجاری زمینی قابل غارت
    lootable_caravans = []
    for trade in pending_trades:
        if trade['status'] == 'pending' and trade.get('trade_type') == 'land':
            # بررسی اینکه آیا کاروان از مرز کشور شما عبور می‌کند
            if is_caravan_passing_through_border(trade, user_country):
                lootable_caravans.append(trade)

    if not lootable_caravans:
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"💰 {general['name']}: رهبر محترم، هیچ کاروان تجاری قابل غارت یافت نشد!\n\n"
        text += "کاروان‌های زمینی در حال عبور از مرز کشور شما:"
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return

    # ایجاد دکمه‌ها
    keyboard = []
    for caravan in lootable_caravans:
        from_country = caravan['seller_country']
        to_country = caravan['buyer_country']
        resource = caravan['resource']
        amount = caravan['amount']
        btn_text = f"🛤️ {from_country} → {to_country}\n{resource}: {amount:,}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f'loot_caravan_{caravan["id"]}')])

    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"💰 {general['name']}: رهبر محترم، کاروان‌های تجاری قابل غارت:"
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_ground_attack_analysis(query):
    """نمایش تحلیل تخصصی حمله زمینی"""
    user_id = str(query.from_user.id)
    if user_id not in users:
        await query.answer("شما در بازی ثبت‌نام نکرده‌اید!")
        return
    
    initialize_user_resources(user_id)
    user_country = utils.users[user_id]['country']
    
    # استفاده از ژنرال انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'general' in selected_officials:
        general = selected_officials['general']
    else:
        general = {'name': 'ژنرال', 'title': 'ژنرال'}
    
    # پیدا کردن کشورهای هم‌مرز که در جنگ فعال هستند (ساختار جدید)
    attackable_countries = []
    # استفاده از مرزهای مؤثر شامل مرزهای فتح شده
    from utils import get_effective_land_borders
    borders = get_effective_land_borders(user_id)
    for border_country in borders:
        in_war = False
        for wid, w in utils.war_declarations.items():
            if w.get('status') == 'active' and ((w.get('attacker') == user_country and w.get('defender') == border_country) or (w.get('defender') == user_country and w.get('attacker') == border_country)):
                in_war = True
                break
        if in_war:
                attackable_countries.append(border_country)
    
    if not attackable_countries:
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"⚔️ {general['name']}: رهبر محترم، هیچ کشور قابل حمله‌ای یافت نشد!"
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    # ایجاد تحلیل برای هر کشور
    analysis_text = f"📊 <b>تحلیل تخصصی حمله زمینی {general['name']}:</b>\n\n"
    
    try:
        from analysis import generate_ground_attack_analysis
        for i, country in enumerate(attackable_countries, 1):
            country_analysis = generate_ground_attack_analysis(user_id, country)
            analysis_text += f"<b>{i}. {country}:</b>\n"
            analysis_text += f"<blockquote>{country_analysis}</blockquote>\n\n"
    except Exception as e:
        print(f"خطا در تحلیل تخصصی: {e}")
        analysis_text += "خطا در تحلیل تخصصی"
    
    keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='ground_attack')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(analysis_text, reply_markup=reply_markup, parse_mode='HTML')

async def show_air_attack_analysis(query):
    """نمایش تحلیل تخصصی حمله هوایی"""
    user_id = str(query.from_user.id)
    if user_id not in users:
        await query.answer("شما در بازی ثبت‌نام نکرده‌اید!")
        return
    
    initialize_user_resources(user_id)
    user_country = utils.users[user_id]['country']
    
    # استفاده از ژنرال انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'general' in selected_officials:
        general = selected_officials['general']
    else:
        general = {'name': 'ژنرال', 'title': 'ژنرال'}
    
    # پیدا کردن تمام کشورهایی که در جنگ فعال هستند
    attackable_countries = []
    for wid, w in utils.war_declarations.items():
        if w.get('status') == 'active' and (w.get('attacker') == user_country or w.get('defender') == user_country):
            other = w.get('defender') if w.get('attacker') == user_country else w.get('attacker')
            if other and other != user_country:
                attackable_countries.append(other)
    
    if not attackable_countries:
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"🛩️ {general['name']}: رهبر محترم، هیچ کشور قابل حمله‌ای یافت نشد!"
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    # ایجاد تحلیل برای هر کشور
    analysis_text = f"📊 <b>تحلیل تخصصی حمله هوایی {general['name']}:</b>\n\n"
    
    try:
        from analysis import generate_air_attack_analysis
        for i, country in enumerate(attackable_countries, 1):
            country_analysis = generate_air_attack_analysis(user_id, country)
            analysis_text += f"<b>{i}. {country}:</b>\n"
            analysis_text += f"<blockquote>{country_analysis}</blockquote>\n\n"
    except Exception as e:
        print(f"خطا در تحلیل تخصصی: {e}")
        analysis_text += "خطا در تحلیل تخصصی"
    
    keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='air_attack')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(analysis_text, reply_markup=reply_markup, parse_mode='HTML')
async def show_naval_attack_analysis(query):
    """نمایش تحلیل تخصصی حمله دریایی"""
    user_id = str(query.from_user.id)
    if user_id not in users:
        await query.answer("شما در بازی ثبت‌نام نکرده‌اید!")
        return
    
    user_country = utils.users[user_id]['country']
    if not has_sea_border(user_country):
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "کشور شما مرز دریایی ندارد!"
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    # استفاده از ژنرال انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'general' in selected_officials:
        general = selected_officials['general']
    else:
        general = {'name': 'ژنرال', 'title': 'ژنرال'}
    
    # کشورهای دارای مرز دریایی که با آنها در جنگ هستیم (با ساختار جدید war_declarations)
    available_countries = []
    # جمع‌آوری لیست کشورهایی که با کاربر در جنگ فعال هستند
    active_opponents = set()
    try:
        for wid, w in utils.war_declarations.items():
            if not isinstance(w, dict):
                continue
            if w.get('status', 'active') == 'ended':
                continue
            attacker = w.get('attacker')
            defender = w.get('defender')
            if attacker == user_country and defender:
                active_opponents.add(defender)
            elif defender == user_country and attacker:
                active_opponents.add(attacker)
    except Exception:
        pass
    # نگاشت کشورهای حریف فعال به user_id آنها و فیلتر به کشورهایی که مرز دریایی دارند
    for target_id, u in users.items():
        if target_id == user_id:
            continue
        target_country = u.get('country', '')
        if target_country and target_country in active_opponents and has_sea_border(target_country):
            available_countries.append((target_id, target_country))
    
    if not available_countries:
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"🌊 {general['name']}: رهبر محترم، هیچ کشور دریایی قابل حمله‌ای یافت نشد!"
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    # ایجاد تحلیل برای هر کشور
    analysis_text = f"📊 <b>تحلیل تخصصی حمله دریایی {general['name']}:</b>\n\n"
    
    try:
        from analysis import generate_naval_attack_analysis
        for i, (target_id, country) in enumerate(available_countries, 1):
            country_analysis = generate_naval_attack_analysis(user_id, country)
            analysis_text += f"<b>{i}. {country}:</b>\n"
            analysis_text += f"<blockquote>{country_analysis}</blockquote>\n\n"
    except Exception as e:
        print(f"خطا در تحلیل تخصصی: {e}")
        analysis_text += "خطا در تحلیل تخصصی"
    
    keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='naval_attack')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(analysis_text, reply_markup=reply_markup, parse_mode='HTML')

# تابع بررسی عبور کاروان از مرز
def is_caravan_passing_through_border(trade, user_country):
    """بررسی اینکه آیا کاروان از مرز کشور کاربر عبور می‌کند"""
    from_country = trade['seller_country']
    to_country = trade['buyer_country']
    
    # اگر کشور کاربر در مسیر کاروان باشد
    if user_country in [from_country, to_country]:
        return False  # نمی‌تواند کاروان خودش را غارت کند
    
    # بررسی هم‌مرز بودن با کشورهای مبدا و مقصد
    from utils import get_effective_land_borders
    # پیدا کردن user_id از user_country
    user_id = None
    for uid, u in utils.users.items():
        if u.get('country') == user_country:
            user_id = uid
            break
    
    if user_id:
        borders = get_effective_land_borders(user_id)
        if from_country in borders or to_country in borders:
            return True
    
    return False
# تابع اجرای غارت
async def execute_loot(user_id, caravan_id, context):
    """اجرای غارت کاروان تجاری"""
    user = utils.users.get(user_id, {})
    user_resources = user.get('resources', {})
    
    # بررسی نیروهای ویژه
    special_forces = user_resources.get('special_forces', 0)
    if special_forces < 100:
        return False, "نیاز به حداقل 100 نیروی ویژه برای غارت"
    
    # بررسی محدودیت زمانی
    current_time = time.time()
    last_loot_time = loot_cooldowns.get(user_id, 0)
    if current_time - last_loot_time < 6 * 3600:  # 6 ساعت
        remaining_time = 6 * 3600 - (current_time - last_loot_time)
        hours = int(remaining_time // 3600)
        minutes = int((remaining_time % 3600) // 60)
        return False, f"محدودیت زمانی غارت: {hours} ساعت و {minutes} دقیقه باقی مانده"
    
    # پیدا کردن کاروان
    caravan = next((t for t in pending_trades if t['id'] == caravan_id and t['status'] == 'pending'), None)
    if not caravan:
        return False, "کاروان مورد نظر یافت نشد"
    
    # محاسبه غنائم (50% از منابع کاروان)
    loot_rewards = {}
    resource = caravan.get('resource')
    amount = caravan.get('amount', 0)
    if resource and amount > 0 and resource != 'cash':  # cash را در نظر نمی‌گیریم
        loot_amount = int(amount * 0.5)
        if loot_amount > 0:
            loot_rewards[resource] = loot_amount
    
    # ریسک تلفات (30% احتمال)
    casualties = 0
    if random.random() < 0.3:
        casualties = random.randint(10, 50)
        user_resources['special_forces'] = max(0, special_forces - casualties)
    
    # اعمال غنائم
    for resource, amount in loot_rewards.items():
        user_resources[resource] = user_resources.get(resource, 0) + amount
    
    # ثبت محدودیت زمانی
    loot_cooldowns[user_id] = current_time
    
    # ذخیره تغییرات
    save_users()
    from utils import save_pending_trades
    save_pending_trades()
    
    # اطلاع‌رسانی
    loot_photo = "https://t.me/TextEmpire_IR/69"
    loot_text = f"💰 غارت موفق!\n\nکشور {user['country']} کاروان تجاری {caravan['seller_country']} → {caravan['buyer_country']} را غارت کرد!\n\nغنائم:\n"
    for resource, amount in loot_rewards.items():
        loot_text += f"• {resource}: {amount:,}\n"
    
    if casualties > 0:
        loot_text += f"\n💀 تلفات: {casualties} نیروی ویژه"
    else:
        loot_text += "\n✅ بدون تلفات"
    
    # ارسال به کانال اخبار
    await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=loot_photo, caption=loot_text, parse_mode='HTML')
    
    # ارسال به غارت‌کننده
    await context.bot.send_photo(chat_id=int(user_id), photo=loot_photo, caption=loot_text, parse_mode='HTML')
    
    return True, "غارت با موفقیت انجام شد"

# متغیرهای سیستم غارت
loot_cooldowns = {}  # {user_id: last_loot_time}

# --- سیستم حمله دریایی ---

# تابع نمایش کشورهای قابل حمله دریایی
async def show_naval_attackable_countries(query):
    user_id = str(query.from_user.id)
    if user_id not in utils.users:
        await query.answer("شما در بازی ثبت‌نام نکرده‌اید!")
        return
    
    user_country = utils.users[user_id]['country']
    # دسترسی دکمه آزاد است؛ فیلترها بعداً روی کشورها اعمال می‌شوند
    
    # کشورهای دارای مرز دریایی که با آنها در جنگ فعال هستیم (پشتیبانی از ساختارهای مختلف اعلان جنگ)
    available_countries = []
    active_opponents = set()
    active_opponents_norm = set()
    try:
        for wid, w in utils.war_declarations.items():
            if isinstance(w, dict) and ('attacker' in w or 'defender' in w):
                if w.get('status', 'active') == 'ended':
                    continue
                attacker = w.get('attacker')
                defender = w.get('defender')
                if attacker == user_country and defender:
                    active_opponents.add(defender)
                elif defender == user_country and attacker:
                    active_opponents.add(attacker)
            elif isinstance(w, (list, set)) and str(wid) == user_id:
                for cname in w:
                    active_opponents.add(cname)
        # Normalize names for robust matching
        from utils import _normalize_country_name
        for name in list(active_opponents):
            active_opponents_norm.add(_normalize_country_name(name))
    except Exception as e:
        print(f"Error in war processing: {e}")
        pass
    for target_id, u in utils.users.items():
        if target_id == user_id:
            continue
        target_country = u.get('country', '') or u.get('current_country_name', '')
        if not target_country:
            continue
        # کشور فتح‌شده نمایش داده نشود
        if u.get('conquered_by'):
            continue
        try:
            from utils import _normalize_country_name
            target_norm = _normalize_country_name(target_country)
        except Exception:
            target_norm = target_country
        in_war = (target_country in active_opponents) or (target_norm in active_opponents_norm)
        if in_war and has_sea_border(target_country):
            available_countries.append((target_id, target_country))
    
    if not available_countries:
        await query.edit_message_text('هیچ کشور دریایی در حال جنگ با شما وجود ندارد!', 
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]))
        return
    
    # ایجاد دکمه‌ها (کلیک روی کشور → نمایش تحلیل اختصاصی)
    keyboard = []
    for i in range(0, len(available_countries), 2):
        row = []
        target_id, target_country = available_countries[i]
        row.append(InlineKeyboardButton(target_country, callback_data=f'naval_target_{target_id}'))
        if i + 1 < len(available_countries):
            target_id2, target_country2 = available_countries[i + 1]
            row.append(InlineKeyboardButton(target_country2, callback_data=f'naval_target_{target_id2}'))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # استفاده از ژنرال انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'general' in selected_officials:
        general = selected_officials['general']
    else:
        general = {'name': 'ژنرال', 'title': 'ژنرال'}
    
    text = f"🌊 {general['name']}: رهبر محترم، کشور مورد نظر برای حمله دریایی را انتخاب کنید:\n\n"
    
    # اضافه کردن تحلیل کلی حمله دریایی
    try:
        from analysis import generate_naval_attack_analysis
        # تحلیل برای اولین کشور در لیست (نمونه)
        if available_countries:
            sample_analysis = generate_naval_attack_analysis(user_id, available_countries[0][1])
            text += f"<b>📊 نمونه تحلیل {general['name']}:</b>\n"
            text += f"<blockquote>{sample_analysis}</blockquote>\n\n"
    except Exception as e:
        print(f"خطا در تحلیل حمله دریایی: {e}")
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# تابع نمایش نیروهای دریایی برای حمله
async def show_naval_forces_inventory(query, target_id):
    user_id = str(query.from_user.id)
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    
    # نیروهای دریایی موجود
    naval_forces = {
        'سرباز': utils.users[user_id]['resources'].get('soldiers', 0),
        'قایق تندرو': utils.users[user_id]['resources'].get('speedboats', 0),
        'ناوچه': utils.users[user_id]['resources'].get('naval_ship', 0),
        'زیردریایی': utils.users[user_id]['resources'].get('submarines', 0),
        'ناو هواپیمابر': utils.users[user_id]['resources'].get('aircraft_carriers', 0)
    }
    
    # استفاده از ژنرال انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'general' in selected_officials:
        general = selected_officials['general']
    else:
        general = {'name': 'ژنرال', 'title': 'ژنرال'}
    
    inventory_text = f"🌊 <b>گزارش {general['title']} {general['name']}:</b>\n\n"
    inventory_text += f"🌊 {general['name']}: رهبر محترم، موجودی نیروهای دریایی برای حمله به {target_country}:\n\n"
    inventory_text += "<code>"
    for force, amount in naval_forces.items():
        inventory_text += f"{force}: {amount:,}\n"
    inventory_text += "</code>"
    
    inventory_text += f"\n📋 {general['name']}: لطفاً متن بالا را کپی کنید و تعداد نیروهایی که می‌خواهید ارسال کنید را به همین ترتیب وارد کنید."
    
    # ذخیره اطلاعات حمله
    pending_naval_attack[user_id] = {
        'target_id': target_id,
        'step': 'amount',
        'naval_forces': naval_forces
    }
    
    keyboard = [
        [InlineKeyboardButton('لغو حمله دریایی ❌', callback_data='cancel_naval_attack')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='naval_attack')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(inventory_text, reply_markup=reply_markup, parse_mode='HTML')
# تابع پردازش نیروهای حمله دریایی
async def process_naval_attack_forces(message, context):
    user_id = str(message.from_user.id)
    if user_id not in pending_naval_attack:
        return
    
    attack_data = pending_naval_attack[user_id]
    target_id = attack_data['target_id']
    user_resources = utils.users[user_id]['resources']
    
    try:
        # پردازش متن ارسالی
        lines = message.text.strip().split('\n')
        requested_forces = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # تبدیل نام نیرو به کلید دیتابیس
            force_mapping = {
                'سرباز': 'soldiers',
                'قایق تندرو': 'speedboats',
                'ناوچه': 'naval_ship',
                'زیردریایی': 'submarines',
                'ناو هواپیمابر': 'aircraft_carriers'
            }
            
            # بررسی هر نیرو در خط
            for force_name, db_key in force_mapping.items():
                # حذف کاراکترهای نامرئی از نام نیرو
                force_name_clean = force_name.replace('\u200c', '').replace('\u200d', '').strip()
                line_clean = line.replace('\u200c', '').replace('\u200d', '').strip()
                
                if force_name_clean in line_clean:
                    # استخراج عدد از خط
                    import re
                    numbers = re.findall(r'\d+(?:,\d+)*', line)
                    if numbers:
                        # حذف کاما و تبدیل به عدد
                        amount_str = numbers[0].replace(',', '')
                        try:
                            amount = int(amount_str)
                            if amount > 0:
                                requested_forces[db_key] = amount
                                break  # اولین عدد پیدا شده را استفاده کن
                        except ValueError:
                            continue
        
        # بررسی کفایت موجودی
        insufficient_forces = []
        for force, amount in requested_forces.items():
            if amount > user_resources.get(force, 0):
                insufficient_forces.append(force)
        
        # اگر هیچ نیرویی وارد نشده، پیام راهنما
        if not requested_forces:
            await context.bot.send_message(message.chat.id, "❌ هیچ نیرویی پردازش نشد. لطفاً فرمت صحیح را رعایت کنید:\n\nسرباز: 100000\nقایق تندرو: 10\nناوچه: 5\nزیردریایی: 2\nناو هواپیمابر: 1")
            print(f"هیچ نیروی دریایی پردازش نشد. متن ارسالی: {message.text}")
            return
        
        if insufficient_forces:
            await context.bot.send_message(message.chat.id, "❌ موجودی کافی نیست برای:\n" + "\n".join(insufficient_forces))
            return
        
        # ثبت حمله (برای تایید) و کسر فوری نیروها + علامت‌گذاری
        attack_data['forces'] = requested_forces
        attack_data['step'] = 'confirm'
        # کسر فوری از موجودی کاربر برای جلوگیری از سوءاستفاده و ذخیره اسنپ‌شات
        try:
            for key, amount in requested_forces.items():
                if amount > 0:
                    user_resources[key] = max(0, int(user_resources.get(key, 0)) - int(amount))
            from utils import save_users as _save_users
            _save_users()
            attack_data['already_deducted'] = True
            # ارسال تایید کسر با نمایش موجودی جدید همان اقلام
            try:
                name_map = {
                    'soldiers': 'سرباز',
                    'speedboats': 'قایق تندرو',
                    'naval_ship': 'ناوچه',
                    'submarines': 'زیردریایی',
                    'aircraft_carriers': 'ناو هواپیمابر'
                }
                remaining_lines = []
                for k, v in requested_forces.items():
                    remaining = int(utils.users[user_id]['resources'].get(k, 0))
                    remaining_lines.append(f"{name_map.get(k,k)}: {remaining:,}")
                remaining_text = "\n".join(remaining_lines)
                await context.bot.send_message(message.chat.id, f"✅ نیروها رزرو و از موجودی کسر شد.\n\nموجودی فعلی اقلام ارسالی:\n<code>{remaining_text}</code>", parse_mode='HTML')
            except Exception:
                pass
        except Exception:
            pass
        
        print(f"نیروهای دریایی پردازش شده: {requested_forces}")
        
        # ذخیره اطلاعات حمله برای بازیابی در صورت قطعی
        from utils import naval_attack_saves, save_naval_attack_saves
        naval_attack_saves[user_id] = {
            'target_id': target_id,
            'forces': requested_forces,
            'timestamp': time.time()
        }
        save_naval_attack_saves()
        
        # نمایش خلاصه و دکمه تایید
        name_map = {
            'soldiers': 'سرباز',
            'speedboats': 'قایق تندرو',
            'naval_ship': 'ناوچه', 
            'submarines': 'زیردریایی',
            'aircraft_carriers': 'ناو هواپیمابر'
        }
        summary = "\n".join([f"{name_map.get(k,k)}: {v:,}" for k, v in requested_forces.items()])
        keyboard = [[InlineKeyboardButton('تایید ✅', callback_data='confirm_naval_attack')],
                    [InlineKeyboardButton('لغو ❌', callback_data='cancel_naval_attack')]]
        await context.bot.send_message(message.chat.id, f"📦 نیروهای انتخابی شما:\n\n<code>{summary}</code>", parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        # بازگرداندن نیروها در صورت خطا
        try:
            if user_id in pending_naval_attack:
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
                    # پاک کردن وضعیت
                    pending_naval_attack.pop(user_id, None)
        except Exception as restore_error:
            print(f"خطا در بازگرداندن نیروها: {restore_error}")
        
        await context.bot.send_message(message.chat.id, "❌ خطا در پردازش اطلاعات. لطفاً دوباره تلاش کنید.")
        print(f"خطا در پردازش نیروهای حمله دریایی: {e}")
        import traceback
        traceback.print_exc()

# تابع آغاز حمله دریایی بر اساس داده‌های ذخیره‌شده (برای دکمه تایید)
async def start_naval_battle_custom(user_id, context, target_id):
    try:
        user_id = str(user_id)
        if user_id not in pending_naval_attack:
            return
        data = pending_naval_attack.get(user_id, {})
        forces = data.get('forces', {})
        # ساخت attack_data سازگار با start_naval_battle
        attack_data = {
            'user_id': user_id,
            'target_id': str(target_id),
            'soldiers': int(forces.get('soldiers', 0)),
            'speedboats': int(forces.get('speedboats', 0)),
            'naval_ship': int(forces.get('naval_ship', 0)),
            'submarines': int(forces.get('submarines', 0)),
            'aircraft_carriers': int(forces.get('aircraft_carriers', 0)),
            'already_deducted': bool(data.get('already_deducted')),
        }
        # شروع حمله (پارامتر message در تابع اصلی استفادهٔ عملی ندارد)
        await start_naval_battle(message=None, attack_data=attack_data, context=context)
        # پاکسازی وضعیت در انتظار
        try:
            del pending_naval_attack[user_id]
        except Exception:
            pass
    except Exception as e:
        print(f"start_naval_battle_custom error: {e}")
        import traceback
        traceback.print_exc()
        # بازگرداندن نیروها در صورت خطا
        try:
            if user_id in pending_naval_attack:
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
                    # پاک کردن وضعیت
                    pending_naval_attack.pop(user_id, None)
                    # اطلاع به کاربر
                    try:
                        await context.bot.send_message(
                            chat_id=int(user_id),
                            text="❌ خطا در شروع حمله دریایی. نیروهای رزرو شده به موجودی شما بازگردانده شدند."
                        )
                    except Exception:
                        pass
        except Exception as restore_error:
            print(f"خطا در بازگرداندن نیروها در start_naval_battle_custom: {restore_error}")
# تابع اجازه استقلال کشورهای فتح شده
async def free_conquered_country(query, target_id):
    if target_id in utils.users:
        if utils.users[target_id].get('conquered_by'):
            conquered_by = utils.users[target_id]['conquered_by']
            country_name = utils.users[target_id]['country']
            
            # حذف اطلاعات فتح و اعطای استقلال
            utils.users[target_id].pop('conquered_by', None)
            utils.users[target_id].pop('conquered_at', None)
            
            # علامت‌گذاری که این کشور قبلاً فتح شده بوده
            utils.users[target_id]['was_conquered'] = True
            
            # حذف از conquered_countries_data برای وام استقلال
            from utils import conquered_countries_data, save_conquered_countries_data
            if target_id in conquered_countries_data:
                del conquered_countries_data[target_id]
                save_conquered_countries_data()
            
            # تنظیم روابط بین فاتح و کشور مستقل شده به 100+ (روابط مثبت پس از استقلال)
            from utils import set_mutual_relation
            liberator_id = str(query.from_user.id)
            target_id_str = str(target_id)
            
            set_mutual_relation(liberator_id, target_id_str, 100)
            
            # بازگردانی منابع بر اساس «منابع پیش‌فرض» (نه اسنپ‌شات)
            try:
                from utils import force_initialize_user_resources
                # اگر کاربر منابع ندارد، ابتدا منابع پیش‌فرض را مقداردهی کن (اما اگر دارد، تغییری نده)
                force_initialize_user_resources(target_id)
            except Exception:
                pass

            # محاسبه درصد بازگشتی از «منابع پیش‌فرض» با توجه به دسته کشور
            from utils import users as _US
            target_cat = _US.get(str(target_id), {}).get('category', '')
            # ساختن یک دیکشنری از منابع پیش‌فرض براساس دسته برای محاسبه درصدها
            def _get_default_resources_by_category(cat: str):
                # نگاشت کوچک از دسته به مقادیر پیش‌فرض هم‌ارز initialize_user_resources
                if 'ابرقدرت' in cat:
                    start_cash = 1_000_000_000
                    mil = {"soldiers":1000000,'special_forces':25000,"tanks":450,"armored_vehicles":1050,'transport_planes':40,"helicopters":540,"fighter_jets":460,'bombers':25,'artillery':60,'drones':180,"air_defense":35,'coastal_artillery':51,'speedboats':140,"naval_ship":46,"submarines":23,"aircraft_carriers":11,"war_robots":1000,"defense_missiles":400,"ballistic_missiles":300}
                    res = {'gold':60,'steel':500,'iron':600,'copper':250,'diamond':25,'uranium':20,'wheat':400,'rice':400,'fruits':400,'oil':2000,'gas':2000,'electronics':500000,'pride_cars':50000,'benz_cars':20000,'electricity':800,'uranium_ore':200,'centrifuge':30,'yellowcake':100,'space_parts':10,'aluminum':500,'titanium':150}
                elif 'قدرت منطقه‌ای' in cat:
                    start_cash = 550_000_000
                    mil = {"soldiers":500000,'special_forces':12000,"tanks":250,"armored_vehicles":600,'transport_planes':19,"helicopters":300,"fighter_jets":250,'bombers':6,'artillery':28,'drones':100,"air_defense":18,'coastal_artillery':24,'speedboats':90,"naval_ship":21,"submarines":9,"aircraft_carriers":4,"war_robots":500,"defense_missiles":250,"ballistic_missiles":150}
                    res = {'gold':40,'steel':350,'iron':400,'copper':150,'diamond':15,'uranium':10,'wheat':200,'rice':200,'fruits':200,'oil':1000,'gas':1000,'electronics':200000,'pride_cars':30000,'benz_cars':10000,'electricity':400,'uranium_ore':100,'centrifuge':15,'yellowcake':50,'space_parts':5,'aluminum':300,'titanium':75}
                elif 'قدرت نوظهور' in cat:
                    start_cash = 300_000_000
                    mil = {"soldiers":200000,'special_forces':5000,"tanks":100,"armored_vehicles":200,'transport_planes':7,"helicopters":150,"fighter_jets":100,'bombers':2,'artillery':16,'drones':51,"air_defense":9,'coastal_artillery':9,'speedboats':40,"naval_ship":9,"submarines":4,"aircraft_carriers":1,"war_robots":260,"defense_missiles":150,"ballistic_missiles":90}
                    res = {'gold':20,'steel':100,'iron':200,'copper':50,'diamond':10,'uranium':10,'wheat':100,'rice':100,'fruits':100,'oil':500,'gas':500,'electronics':100000,'pride_cars':10000,'benz_cars':5000,'electricity':200,'uranium_ore':50,'centrifuge':7,'yellowcake':25,'space_parts':2,'aluminum':150,'titanium':45}
                else:
                    start_cash = 100_000_000
                    mil = {"soldiers":50000,'special_forces':2000,"tanks":45,"armored_vehicles":100,'transport_planes':15,"helicopters":10,"fighter_jets":10,'bombers':0,'artillery':7,'drones':24,"air_defense":5,'coastal_artillery':7,'speedboats':22,"naval_ship":4,"submarines":1,"aircraft_carriers":0,"war_robots":120,"defense_missiles":90,"ballistic_missiles":50}
                    res = {'gold':15,'steel':150,'iron':300,'copper':100,'diamond':5,'uranium':5,'wheat':50,'rice':50,'fruits':50,'oil':250,'gas':250,'electronics':50000,'pride_cars':10000,'benz_cars':5000,'electricity':100,'uranium_ore':25,'centrifuge':1,'yellowcake':10,'space_parts':1,'aluminum':80,'titanium':25}
                return start_cash, mil, res

            base_cash, base_mil, base_res = _get_default_resources_by_category(target_cat)
            # 50% نیرو + 20% منابع + 20% پول
            grant_mil = {k: int(v * 0.50) for k, v in base_mil.items()}
            grant_res = {k: int(v * 0.20) for k, v in base_res.items()}
            grant_cash = int(base_cash * 0.20)

            if 'resources' not in utils.users[target_id]:
                utils.users[target_id]['resources'] = {}
            # اعمال
            utils.users[target_id]['resources']['cash'] = utils.users[target_id]['resources'].get('cash', 0) + grant_cash
            for k, v in grant_res.items():
                if v > 0:
                    utils.users[target_id]['resources'][k] = utils.users[target_id]['resources'].get(k, 0) + v
            for k, v in grant_mil.items():
                if v > 0:
                    utils.users[target_id]['resources'][k] = utils.users[target_id]['resources'].get(k, 0) + v
            
            # ذخیره تغییرات
            from utils import save_users
            save_users()
            
            # ارسال پیام به کانال خبری
            liberation_photo = "https://t.me/TextEmpire_IR/62"  # فایل ایدی اجازه استقلال
            liberation_text = f"🕊️ <b>اجازه استقلال!</b>\n\nکشور {country_name} از سلطه {conquered_by} استقلال یافت!\n\n🔄 20% منابع + 20% پول و 50% نیروهای نظامی به کشور مستقل بازگردانده شد.\n\n🌍 روابط بین دو کشور به حالت مثبت (100) تنظیم شد."
            try:
                from telegram import Bot
                from utils import BOT_TOKEN
                bot = Bot(token=BOT_TOKEN)
                await bot.send_photo(chat_id='@TextEmpire_News', photo=liberation_photo, caption=liberation_text, parse_mode='HTML')
                print(f"پیام اعطای استقلال به کانال ارسال شد: {country_name}")
            except Exception as e:
                print(f"خطا در ارسال پیام به کانال: {e}")
            
            # ارسال پیام به فاتح (کسی که اجازه استقلال داد)
            liberator_photo = "https://t.me/TextEmpire_IR/62"  # فایل ایدی پیام فاتح
            liberator_text = f"🕊️ به کشور {country_name} اجازه استقلال دادید!\n\n🔄 20% منابع + 20% پول و 50% نیروهای نظامی به کشور مستقل بازگردانده شد.\n\n🌍 روابط بین دو کشور به حالت مثبت (100) تنظیم شد."
            try:
                from telegram import Bot
                from utils import BOT_TOKEN
                bot = Bot(token=BOT_TOKEN)
                await bot.send_photo(chat_id=int(query.from_user.id), photo=liberator_photo, caption=liberator_text, parse_mode='HTML')
                print(f"پیام اعطای استقلال به فاتح ارسال شد: {query.from_user.id}")
            except Exception as e:
                print(f"خطا در ارسال پیام به فاتح: {e}")
            
            # ارسال پیام به کشور مستقل شده
            liberated_photo = "https://t.me/TextEmpire_IR/62"  # فایل ایدی پیام کشور مستقل شده
            liberated_text = f"🕊️ <b>کشور شما مستقل شد!</b>\n\nکشور شما توسط {conquered_by} استقلال یافت!\n\n🔄 20% منابع + 20% پول و 50% نیروهای نظامی به شما بازگردانده شد.\n\n🌍 روابط بین دو کشور به حالت مثبت (100) تنظیم شد.\n\n🎉 حالا می‌توانید دوباره بازی کنید!"
            try:
                from telegram import Bot
                from utils import BOT_TOKEN
                bot = Bot(token=BOT_TOKEN)
                await bot.send_photo(chat_id=int(target_id), photo=liberated_photo, caption=liberated_text, parse_mode='HTML')
                print(f"پیام اعطای استقلال به کشور مستقل شده ارسال شد: {target_id}")
            except Exception as e:
                print(f"خطا در ارسال پیام به کشور مستقل شده: {e}")
            
            from bot import safe_edit_message
            await safe_edit_message(query, f"✅ کشور {country_name} از سلطه {conquered_by} استقلال یافت!\n\n🔄 10% منابع اولیه و 50% نیروهای نظامی بازگردانده شد.\n\n🌍 روابط بین دو کشور به حالت مثبت (100) تنظیم شد.")
        else:
            from bot import safe_edit_message
            await safe_edit_message(query, "❌ این کشور فتح شده است!")
    else:
        from bot import safe_edit_message
        await safe_edit_message(query, "❌ کاربر یافت نشد!")
# تابع نمایش کشورهای فتح شده
async def show_conquered_countries(query):
    conquered_countries = []
    for user_id, user_data in utils.users.items():
        if user_data.get('conquered_by'):
            conquered_countries.append({
                'user_id': user_id,
                'country': user_data['country'],
                'conquered_by': user_data['conquered_by'],
                'conquered_at': user_data.get('conquered_at', 0)
            })
    
    if not conquered_countries:
        await query.edit_message_text("✅ هیچ کشور فتح شده‌ای وجود ندارد.")
        return
    
    text = "🌍 <b>کشورهای فتح شده:</b>\n\n"
    keyboard = []
    
    for country in conquered_countries:
        from datetime import datetime
        conquered_time = datetime.fromtimestamp(country['conquered_at']).strftime('%Y-%m-%d %H:%M') if country['conquered_at'] else 'نامشخص'
        text += f"🏳️ {country['country']}\n"
        text += f"   👑 فتح شده توسط: {country['conquered_by']}\n"
        text += f"   📅 تاریخ فتح: {conquered_time}\n\n"
        
        keyboard.append([InlineKeyboardButton(
            f"اجازه استقلال {country['country']}", 
            callback_data=f'free_country_{country["user_id"]}'
        )])
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='admin_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

def simulate_air_battle(attacker_forces):
    # محاسبه قدرت کلی حمله‌کننده
    total_power = 0
    for force, amount in attacker_forces.items():
        if force == 'transport_planes':
            total_power += amount * 2
        elif force == 'helicopters':
            total_power += amount * 4
        elif force == 'fighter_jets':
            total_power += amount * 12
        elif force == 'bombers':
            total_power += amount * 15
        elif force == 'drones':
            total_power += amount * 6
        # پدافند هوایی در حمله نقشی ندارد
    
    # شبیه‌سازی ساده - 55% شانس پیروزی (کمی سخت‌تر از زمینی)
    victory_chance = 0.55
    if random.random() < victory_chance:
        return {'victory': True, 'power': total_power}
    else:
        return {'victory': False, 'power': total_power}
# تابع شبیه‌سازی نبرد هوایی جدید
def simulate_air_battle_new(attacker_forces, defender_forces, attacker_id=None, defender_id=None):
    # محاسبه قدرت حمله‌کننده (بدون پدافند هوایی)
    attack_power = 0
    attacker_level_bonus = 1.0
    
    # بررسی لول نیروهای هوایی حمله‌کننده
    if attacker_id and attacker_id in users:
        attacker_techs = military_technologies.get(str(attacker_id), {})
        # محاسبه میانگین لول فناوری‌های هوایی
        air_techs = ['transport_planes', 'helicopters', 'fighter_jets', 'bombers', 'drones']
        total_air_tech_level = sum(attacker_techs.get(tech, 1) for tech in air_techs)
        avg_air_tech_level = total_air_tech_level / len(air_techs)
        attacker_level_bonus = 1.0 + (avg_air_tech_level - 1) * 0.2  # هر لول 20% افزایش
    
    for force, amount in attacker_forces.items():
        base_power = 0
        if force == 'transport_planes':
            base_power = amount * 2
        elif force == 'helicopters':
            base_power = amount * 4
        elif force == 'fighter_jets':
            base_power = amount * 12
        elif force == 'bombers':
            base_power = amount * 15
        elif force == 'drones':
            base_power = amount * 6
        # پدافند هوایی در حمله نقشی ندارد
        
        # اعمال ضریب لول برای هر آیتم
        level_multiplier = 1.0 + (attacker_level_bonus - 1.0) * 0.1  # هر لول 10% افزایش
        attack_power += int(base_power * level_multiplier)
    
    # محاسبه قدرت دفاع‌کننده (فقط پدافند هوایی، جنگنده و بالگرد)
    defense_power = 0
    defender_level_bonus = 1.0
    
    # بررسی لول نیروهای هوایی دفاع‌کننده
    if defender_id and defender_id in users:
        defender_techs = military_technologies.get(str(defender_id), {})
        # محاسبه میانگین لول فناوری‌های هوایی
        air_techs = ['air_defense', 'fighter_jets', 'helicopters']
        total_air_tech_level = sum(defender_techs.get(tech, 1) for tech in air_techs)
        avg_air_tech_level = total_air_tech_level / len(air_techs)
        defender_level_bonus = 1.0 + (avg_air_tech_level - 1) * 0.2  # هر لول 20% افزایش
    
    for force, amount in defender_forces.items():
        base_power = 0
        if force == 'air_defense':
            base_power = amount * 25  # قدرت هر پدافند هوایی
        elif force == 'fighter_jets':
            base_power = amount * 12
        elif force == 'helicopters':
            base_power = amount * 4
        # بقیه نیروها در دفاع هوایی نقشی ندارند
        
        # اعمال ضریب لول برای هر آیتم
        level_multiplier = 1.0 + (defender_level_bonus - 1.0) * 0.1  # هر لول 10% افزایش
        defense_power += int(base_power * level_multiplier)

    # اعمال ضریب تجهیزات ویژه (defense_power) از فروشگاه برای مدافع
    try:
        if defender_id:
            from bot import get_user_defense_power
            shop_defense_multiplier = float(get_user_defense_power(str(defender_id)))
            # مقدار ذخیره‌شده در کاربر ضریب کلی است (پیش‌فرض 1.0). روی دفاع هوایی اعمال می‌شود.
            defense_power = int(defense_power * shop_defense_multiplier)
    except Exception:
        pass
    
    # شانس رندوم بین 40 تا 60 درصد برای هر دو طرف
    attacker_chance = random.uniform(0.4, 0.6)
    defender_chance = random.uniform(0.4, 0.6)
    
    # محاسبه نسبت قدرت برای تاثیر بر نتیجه
    power_ratio = attack_power / max(defense_power, 1)
    
    # اعمال تاثیر نسبت قدرت بر شانس‌ها (بدون محدود کردن)
    if power_ratio > 1.5:  # برتری قاطع
        attacker_chance += 0.15
        defender_chance -= 0.15
    elif power_ratio > 1.2:  # برتری نسبی
        attacker_chance += 0.08
        defender_chance -= 0.08
    elif power_ratio < 0.8:  # ضعف نسبی
        attacker_chance -= 0.08
        defender_chance += 0.08
    elif power_ratio < 0.6:  # ضعف قاطع
        attacker_chance -= 0.15
        defender_chance += 0.15
    
    # مقایسه شانس‌ها
    if attacker_chance > defender_chance:
        return {
            'victory': True, 
            'attack_power': attack_power,
            'defense_power': defense_power,
            'attacker_chance': attacker_chance,
            'defender_chance': defender_chance,
            'attacker_level_bonus': attacker_level_bonus,
            'defender_level_bonus': defender_level_bonus
        }
    else:
        return {
            'victory': False, 
            'attack_power': attack_power,
            'defense_power': defense_power,
            'attacker_chance': attacker_chance,
            'defender_chance': defender_chance,
            'attacker_level_bonus': attacker_level_bonus,
            'defender_level_bonus': defender_level_bonus
        }

# تابع برنامه‌ریزی مراحل جنگ هوایی جدید
async def schedule_air_battle_phases_new(user_id, target_id, attacker_forces, target_forces, battle_result, context):
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    
    # انتخاب رندوم تصویر جنگ هوایی
    air_battle_photos = [
        "https://t.me/TextEmpire_IR/64",
        "https://t.me/TextEmpire_IR/156", 
        "https://t.me/TextEmpire_IR/163"
    ]
    air_battle_photo = random.choice(air_battle_photos)
    # انتخاب رندوم تصویر مرحله دوم نبرد هوایی
    air1_battle_photos = [
        "https://t.me/TextEmpire_IR/73",
        "https://t.me/TextEmpire_IR/148",
        "https://t.me/TextEmpire_IR/162"
    ]
    air1_battle_photo = random.choice(air1_battle_photos)
    # مرحله 1: ارسال پیام شروع جنگ هوایی به کانال و هر دو کاربر
    battle_start_msg = f"🛩️ <b>نبرد هوایی آغاز شد!</b>\n\nکشور {user_country} ({utils.get_user_capital(user_id)}) به کشور {target_country} ({utils.get_user_capital(target_id)}) حمله هوایی کرد!\n\n⏰ مرحله نبرد اصلی در 2 دقیقه آغاز خواهد شد."
    
    # ارسال به کانال اخبار
    try:
        await send_media_safe(context.bot, NEWS_CHANNEL_ID, air_battle_photo, battle_start_msg, 'HTML')
    except Exception as e:
        print(f"خطا در ارسال پیام شروع نبرد هوایی به کانال: {e}")
    
    # ارسال به حمله‌کننده
    try:
        await send_media_safe(context.bot, int(user_id), air_battle_photo, battle_start_msg, 'HTML')
    except Exception as e:
        print(f"خطا در ارسال پیام شروع نبرد هوایی به حمله‌کننده: {e}")
    
    # ارسال به دفاع‌کننده
    try:
        await send_media_safe(context.bot, int(target_id), air_battle_photo, battle_start_msg, 'HTML')
    except Exception as e:
        print(f"خطا در ارسال پیام شروع نبرد هوایی به دفاع‌کننده: {e}")
    
    # ایجاد background task برای ادامه نبرد
    async def continue_battle():
        # انتظار 2 دقیقه
        await asyncio.sleep(120)
        
        # مرحله 2: مرحله نبرد اصلی
        attacker_level = utils.users[user_id].get('military', {}).get('air_tech_level', 1)
        defender_level = utils.users[target_id].get('military', {}).get('air_tech_level', 1)
        
        battle_main_msg = f"⚔️ <b>مرحله نبرد اصلی!</b>\n\nنبرد هوایی بین {user_country} ({utils.get_user_capital(user_id)}) و {target_country} ({utils.get_user_capital(target_id)}) در حال انجام است!\n\n🛩️ قدرت حمله: {battle_result['attack_power']:,} (لول {attacker_level})\n🛡️ قدرت دفاع: {battle_result['defense_power']:,} (لول {defender_level})\n\n⏰ نتیجه نهایی در چند ثانیه اعلام خواهد شد."
        
        # ارسال به کانال اخبار
        try:
            await send_media_safe(context.bot, NEWS_CHANNEL_ID, air1_battle_photo, battle_main_msg, 'HTML')
        except Exception as e:
            print(f"خطا در ارسال پیام نبرد اصلی به کانال: {e}")
        
        # ارسال به هر دو طرف
        try:
            await send_media_safe(context.bot, int(user_id), air1_battle_photo, battle_main_msg, 'HTML')
            await send_media_safe(context.bot, int(target_id), air1_battle_photo, battle_main_msg, 'HTML')
        except Exception as e:
            print(f"خطا در ارسال پیام نبرد اصلی به کاربران: {e}")
        
        # انتظار کوتاه برای نمایش نتیجه
        await asyncio.sleep(5)
        
        # مرحله 3: اعلام نتیجه نهایی
        if battle_result['victory']:
            # حمله موفق
            await handle_successful_air_attack(user_id, target_id, attacker_forces, target_forces, battle_result, context)
        else:
            # حمله ناموفق
            await handle_failed_air_attack(user_id, target_id, attacker_forces, target_forces, battle_result, context)
    
    # شروع background task
    asyncio.create_task(continue_battle())
# تابع مدیریت حمله هوایی موفق
async def handle_successful_air_attack(user_id, target_id, attacker_forces, target_forces, battle_result, context):
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    
    # نرخ تلفات بر اساس نتیجه (برای هر نوع هواگرد)
    attacker_loss_rate = 0.25
    defender_loss_rate = 0.35

    attacker_resources = utils.users[user_id].get('resources', {})
    target_resources = utils.users[target_id].get('resources', {})
    
    # محاسبه بازگشت نیروهای باقی‌مانده به حمله‌کننده (در شروع کسر شده‌اند)
    air_types = ['transport_planes', 'helicopters', 'fighter_jets', 'bombers', 'drones']
    for k in air_types:
        sent = int(attacker_forces.get(k, 0))
        if sent <= 0:
            continue
        losses = int(sent * attacker_loss_rate)
        survivors = max(0, sent - losses)
        if survivors > 0:
            attacker_resources[k] = int(attacker_resources.get(k, 0)) + survivors

    # کسر تلفات دفاع‌کننده به تفکیک نوع
    defender_air_types = ['transport_planes', 'helicopters', 'fighter_jets', 'bombers', 'drones', 'air_defense']
    for k in defender_air_types:
        have = int(target_resources.get(k, 0))
        if have <= 0:
            continue
        loss = int(have * defender_loss_rate)
        target_resources[k] = max(0, have - loss)
    
    # نابودی سازه‌ها و نیروهای دفاع‌کننده
    
    # 1. نابودی 2 سازه رندوم
    target_economy = utils.users[target_id].get('economy', {})
    all_buildings = []
    for section, buildings in target_economy.items():
        if isinstance(buildings, list):
            for building in buildings:
                all_buildings.append((section, building))
    
    destroyed_building_details = []
    buildings_to_destroy = min(2, len(all_buildings))
    
    if all_buildings:
        # انتخاب تصادفی 2 سازه
        selected_buildings = random.sample(all_buildings, buildings_to_destroy)
        
        # حذف سازه‌های انتخاب شده
        for section, building in selected_buildings:
            if building in target_economy.get(section, []):
                target_economy[section].remove(building)
                destroyed_building_details.append(f"{section}: {building}")

    # 2. نابودی 10% جمعیت (همیشه اعمال شود حتی اگر سازه‌ای برای تخریب نباشد)
    from jame import get_country_population_by_user_id, update_population_damage
    current_population = get_country_population_by_user_id(target_id)
    population_damage = int(current_population * 0.10)  # 10% جمعیت
    update_population_damage(target_id, population_damage)
    
    # 3. نابودی 10% نیروی نظامی
    target_resources = utils.users[target_id]['resources']
    military_forces = ['soldiers', 'special_forces', 'tanks', 'armored_vehicles', 'artillery', 'war_robots', 
                      'transport_planes', 'helicopters', 'fighter_jets', 'bombers', 'drones', 'air_defense',
                      'speedboats', 'naval_ship', 'submarines', 'aircraft_carriers', 'coastal_artillery']
    
    military_losses = {}
    for force in military_forces:
        if force in target_resources and target_resources[force] > 0:
            loss = int(target_resources[force] * 0.1)  # 10% نابودی
            target_resources[force] -= loss
            military_losses[force] = loss
    
    # ذخیره تغییرات
    save_users()
    
    # پیام به کانال اخبار
    channel_msg = f"🏆 <b>حمله هوایی موفق!</b>\n\nکشور {user_country} ({utils.get_user_capital(user_id)}) در نبرد هوایی با {target_country} ({utils.get_user_capital(target_id)}) پیروز شد!\n\n💥 {buildings_to_destroy} سازه نابود شد!\n💀 {population_damage:,} نفر از جمعیت نابود شد!\n⚔️ 10% نیروی نظامی نابود شد!\n\n🛩️ قدرت حمله: {battle_result['attack_power']:,}\n🛡️ قدرت دفاع: {battle_result['defense_power']:,}"
    
    try:
        await send_media_safe(context.bot, NEWS_CHANNEL_ID, "https://t.me/TextEmpire_IR/66", channel_msg, 'HTML')
    except Exception as e:
        print(f"خطا در ارسال پیام پیروزی به کانال: {e}")
    
    # پیام دقیق به حمله‌کننده
    attacker_msg = f"🏆 <b>حمله هوایی موفق!</b>\n\nشما در نبرد هوایی با {target_country} ({utils.get_user_capital(target_id)}) پیروز شدید!\n\n📊 آمار دقیق:\n"
    attacker_msg += f"🛩️ قدرت حمله شما: {battle_result['attack_power']:,}\n"
    attacker_msg += f"🛡️ قدرت دفاع حریف: {battle_result['defense_power']:,}\n"
    attacker_msg += f"📉 تلفات شما: تقریباً 25% از هواگردهای اعزامی\n"
    
    attacker_msg += f"💥 سازه‌های نابود شده: {buildings_to_destroy}\n"
    attacker_msg += f"💀 جمعیت نابود شده: {population_damage:,} نفر (10%)\n"
    attacker_msg += f"⚔️ نیروی نظامی نابود شده: 10%\n\n"
    
    if destroyed_building_details:
            attacker_msg += "🔍 جزئیات سازه‌های نابود شده:\n"
            for detail in destroyed_building_details:
                attacker_msg += f"▫️ {detail}\n"
    
    if military_losses:
        attacker_msg += "\n🔍 جزئیات نیروی نظامی نابود شده:\n"
        force_names = {
            'soldiers': 'سربازان',
            'special_forces': 'نیروهای ویژه',
            'tanks': 'تانک',
            'armored_vehicles': 'نفربر زرهی',
            'artillery': 'توپخانه',
            'war_robots': 'ربات جنگی',
            'air_defense': 'پدافند هوایی',
            'speedboats': 'قایق تندرو',
            'naval_ship': 'ناوچه',
            'submarines': 'زیردریایی',
            'aircraft_carriers': 'ناو هواپیمابر',
            'coastal_artillery': 'توپ ساحلی',
            'transport_planes': 'هواپیمای ترابری',
            'helicopters': 'بالگرد',
            'fighter_jets': 'جنگنده',
            'bombers': 'بمب‌افکن',
            'drones': 'پهپاد'
        }
        for force, loss in military_losses.items():
            if loss > 0:
                force_name = force_names.get(force, force)
                attacker_msg += f"▫️ {force_name}: {loss:,}\n"
    
    try:
        await send_media_safe(context.bot, int(user_id), "https://t.me/TextEmpire_IR/66", attacker_msg, 'HTML')
    except Exception as e:
        print(f"خطا در ارسال پیام شکست به حمله‌کننده: {e}")
    
    # پیام دقیق به دفاع‌کننده
    defender_msg = f"❌ <b>دفاع هوایی ناموفق!</b>\n\nکشور {user_country} در نبرد هوایی با شما پیروز شد!\n\n📊 آمار دقیق:\n"
    defender_msg += f"🛩️ قدرت حمله حریف: {battle_result['attack_power']:,}\n"
    defender_msg += f"🛡️ قدرت دفاع شما: {battle_result['defense_power']:,}\n"
    defender_msg += f"📉 تلفات شما: تقریباً 35% از هواگردها/پدافند\n"
    
    defender_msg += f"💥 سازه‌های نابود شده: {buildings_to_destroy}\n"
    defender_msg += f"💀 جمعیت نابود شده: {population_damage:,} نفر (10%)\n"
    defender_msg += f"⚔️ نیروی نظامی نابود شده: 10%\n\n"
    
    if destroyed_building_details:
            defender_msg += "🔍 جزئیات سازه‌های نابود شده:\n"
            for detail in destroyed_building_details:
                defender_msg += f"▫️ {detail}\n"
    if military_losses:
        defender_msg += "\n🔍 جزئیات نیروی نظامی نابود شده:\n"
        force_names = {
            'soldiers': 'سربازان',
            'special_forces': 'نیروهای ویژه',
            'tanks': 'تانک',
            'armored_vehicles': 'نفربر زرهی',
            'artillery': 'توپخانه',
            'war_robots': 'ربات جنگی',
            'air_defense': 'پدافند هوایی',
            'speedboats': 'قایق تندرو',
            'naval_ship': 'ناوچه',
            'submarines': 'زیردریایی',
            'aircraft_carriers': 'ناو هواپیمابر',
            'coastal_artillery': 'توپ ساحلی',
            'transport_planes': 'هواپیمای ترابری',
            'helicopters': 'بالگرد',
            'fighter_jets': 'جنگنده',
            'bombers': 'بمب‌افکن',
            'drones': 'پهپاد'
        }
        for force, loss in military_losses.items():
            if loss > 0:
                force_name = force_names.get(force, force)
                defender_msg += f"▫️ {force_name}: {loss:,}\n"
    
    try:
        await send_media_safe(context.bot, int(target_id), "https://t.me/TextEmpire_IR/66", defender_msg, 'HTML')
    except Exception as e:
        print(f"خطا در ارسال پیام شکست به دفاع‌کننده: {e}")

# تابع مدیریت حمله هوایی ناموفق
async def handle_failed_air_attack(user_id, target_id, attacker_forces, target_forces, battle_result, context):
    user_country = utils.users[user_id]['country']
    target_country = utils.users[target_id]['country']
    
    # نرخ تلفات بر اساس شکست
    attacker_loss_rate = 0.40
    defender_loss_rate = 0.20

    attacker_resources = utils.users[user_id].get('resources', {})
    target_resources = utils.users[target_id].get('resources', {})
    
    # بازگرداندن بازمانده‌های حمله‌کننده به موجودی (در شروع کسر شده‌اند)
    air_types = ['transport_planes', 'helicopters', 'fighter_jets', 'bombers', 'drones']
    for k in air_types:
        sent = int(attacker_forces.get(k, 0))
        if sent <= 0:
            continue
        losses = int(sent * attacker_loss_rate)
        survivors = max(0, sent - losses)
        if survivors > 0:
            attacker_resources[k] = int(attacker_resources.get(k, 0)) + survivors

    # کسر تلفات دفاع‌کننده به تفکیک نوع
    defender_air_types = ['transport_planes', 'helicopters', 'fighter_jets', 'bombers', 'drones', 'air_defense']
    for k in defender_air_types:
        have = int(target_resources.get(k, 0))
        if have <= 0:
            continue
        loss = int(have * defender_loss_rate)
        target_resources[k] = max(0, have - loss)
    
    # ذخیره تغییرات
    save_users()
    
    # پیام به کانال اخبار
    channel_msg = f"🛡️ <b>دفاع هوایی موفق!</b>\n\nکشور {target_country} در برابر حمله هوایی {user_country} مقاومت کرد!\n\n🛩️ قدرت حمله: {battle_result['attack_power']:,}\n🛡️ قدرت دفاع: {battle_result['defense_power']:,}"
    
    # انتخاب رندوم تصویر دفاع هوایی موفق
    defense_photos = [
        "https://t.me/TextEmpire_IR/74",   # عکس
        "https://t.me/TextEmpire_IR/149",  # عکس
        "https://t.me/TextEmpire_IR/175"   # گیف
    ]
    defense_photo = random.choice(defense_photos)
    
    try:
        await send_media_safe(context.bot, NEWS_CHANNEL_ID, defense_photo, channel_msg, 'HTML')
    except Exception as e:
        print(f"خطا در ارسال پیام دفاع موفق به کانال: {e}")
    
    # پیام دقیق به حمله‌کننده
    attacker_msg = f"❌ <b>حمله هوایی ناموفق!</b>\n\nشما در نبرد هوایی با {target_country} شکست خوردید!\n\n📊 آمار دقیق:\n"
    attacker_msg += f"🛩️ قدرت حمله شما: {battle_result['attack_power']:,}\n"
    attacker_msg += f"🛡️ قدرت دفاع حریف: {battle_result['defense_power']:,}\n"
    attacker_msg += f"📉 تلفات شما: تقریباً 40% از هواگردهای اعزامی\n"
    attacker_msg += f"🔄 نیروهای بازگشتی: تقریباً 60% از اعزامی‌ها"
    
    try:
        await send_media_safe(context.bot, int(user_id), "https://t.me/TextEmpire_IR/65", attacker_msg, 'HTML')
    except Exception as e:
        print(f"خطا در ارسال پیام شکست به حمله‌کننده: {e}")
    
    # پیام دقیق به دفاع‌کننده
    defender_msg = f"🛡️ <b>دفاع هوایی موفق!</b>\n\nشما در برابر حمله هوایی {user_country} مقاومت کردید!\n\n📊 آمار دقیق:\n"
    defender_msg += f"🛩️ قدرت حمله حریف: {battle_result['attack_power']:,}\n"
    defender_msg += f"🛡️ قدرت دفاع شما: {battle_result['defense_power']:,}\n"
    defender_msg += f"📉 تلفات شما: تقریباً 20% از هواگردها/پدافند"
    
    try:
        await send_media_safe(context.bot, int(target_id), defense_photo, defender_msg, 'HTML')
    except Exception as e:
        print(f"خطا در ارسال پیام دفاع موفق به دفاع‌کننده: {e}")
# تابع پردازش نیروهای هوایی
async def process_air_attack_forces(message, context):
    user_id = str(message.from_user.id)
    
    if user_id not in pending_air_attack:
        return
    
    attack_data = pending_air_attack[user_id]
    user_resources = utils.users[user_id]['resources']
    
    try:
        # پردازش متن ارسالی
        lines = message.text.strip().split('\n')
        requested_forces = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # تبدیل نام نیرو به کلید دیتابیس
            force_mapping = {
                'هواپیمای ترابری': 'transport_planes',
                'بالگرد': 'helicopters',
                'جنگنده': 'fighter_jets',
                'بمب‌افکن': 'bombers',
                'پهپاد': 'drones'
            }
            
            if ':' in line:
                force_name, amount_str = line.split(':', 1)
                force_name = force_name.strip()
                amount_str = amount_str.strip()
                
                # بررسی دقیق‌تر نام نیرو (حذف فاصله‌های اضافی و کاراکترهای نامرئی)
                force_name_clean = force_name.replace('\u200c', '').replace('\u200d', '').strip()
                
                if force_name_clean in force_mapping:
                    try:
                        amount = int(amount_str.replace(',', ''))
                        if amount > 0:
                            requested_forces[force_mapping[force_name_clean]] = amount
                    except ValueError:
                        continue
        
        if not requested_forces:
            await message.reply_text('❌ هیچ نیروی معتبری یافت نشد. لطفاً فرمت صحیح را رعایت کنید:\n\nهواپیمای ترابری: 59\nبالگرد: 840\nجنگنده: 710\nبمب‌افکن: 31\nپهپاد: 280')
            return
        
        # بررسی موجودی نیروها
        insufficient_forces = []
        for force, requested_amount in requested_forces.items():
            available = user_resources.get(force, 0)
            if available < requested_amount:
                insufficient_forces.append(f"{force}: {available}/{requested_amount}")
        
        if insufficient_forces:
            await message.reply_text(f'❌ نیروهای کافی ندارید:\n' + '\n'.join(insufficient_forces))
            return
        
        # کسر نیروها از موجودی
        for force, amount in requested_forces.items():
            user_resources[force] -= amount
        
        # ذخیره تغییرات
        from utils import save_users
        save_users()
        
        # اضافه کردن نیروها به attack_data
        attack_data['forces'] = requested_forces
        
        # شروع جنگ هوایی
        await start_air_battle(message, attack_data, context)
        
    except Exception as e:
        print(f"خطا در پردازش نیروهای هوایی: {e}")
        await message.reply_text('❌ خطا در پردازش اطلاعات. لطفاً دوباره تلاش کنید.')

# متغیرهای سیستم غارت
loot_cooldowns = {}  # {user_id: last_loot_time}

async def show_sea_raid_menu(query):
    user_id = str(query.from_user.id)
    user_country = utils.users.get(user_id, {}).get('country', '')
    # فقط کشورهایی که مرز دریایی دارند
    if user_country not in SEA_BORDER_COUNTRIES:
        await query.edit_message_text('کشور شما مرز دریایی ندارد و نمی‌تواند به کشتی تجاری حمله کند.')
        return

    # تجارت‌های دریایی که در وضعیت pending هستند
    sea_trades = [trade for trade in pending_trades if trade['status'] == 'pending' and trade.get('trade_type') == 'naval']
    
    # محموله‌های کمک اتحاد که در حال ارسال هستند
    from diplomaci import alliance_trades
    alliance_help_trades = []
    if isinstance(alliance_trades, dict):
        alliance_help_trades = [trade for trade in alliance_trades.values() if trade.get('status') == 'sending']
    elif isinstance(alliance_trades, list):
        alliance_help_trades = [trade for trade in alliance_trades if trade.get('status') == 'sending']
    
    if not sea_trades and not alliance_help_trades:
        await query.edit_message_text('در حال حاضر هیچ کشتی تجاری در مسیر وجود ندارد.')
        return

    keyboard = []
    
    # تجارت‌های معمولی
    for trade in sea_trades:
        btn_text = f"🛳️ کشتی تجاری: {trade['seller_country']} → {trade['buyer_country']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f'sea_raid_{trade["id"]}')])
    
    # محموله‌های کمک اتحاد
    for i, trade in enumerate(alliance_help_trades):
        from_country = utils.users.get(trade.get('from_id', ''), {}).get('country', 'نامشخص')
        to_country = utils.users.get(trade.get('to_id', ''), {}).get('country', 'نامشخص')
        btn_text = f"🤲 محموله کمک: {from_country} → {to_country}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f'sea_raid_alliance_{i}')])
    
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')])
    await query.edit_message_text('کشتی‌های تجاری و محموله‌های کمک در مسیر:', reply_markup=InlineKeyboardMarkup(keyboard))

# pending_sea_raid در utils.py تعریف شده است

# تابع نمایش لیست کشورها برای اعلان جنگ
async def show_countries_for_war_declaration(query):
    user_id = str(query.from_user.id)
    if user_id not in utils.users:
        await query.answer("شما در بازی ثبت‌نام نکرده‌اید!")
        return
    
    initialize_user_resources(user_id)
    # حذف کشور خود کاربر از لیست
    user_country = utils.users[user_id]['country']
    # استخراج نام کشورها از لیست countries
    all_countries = [country['name'] for country in utils.countries]
    
    # 1) محاسبه فهرست کشورهایی که هم‌اکنون با کاربر در جنگ فعال هستند
    active_opponents = set()
    active_opponents_norm = set()
    try:
        from utils import _normalize_country_name, get_canonical_country_name
        for wid, w in utils.war_declarations.items():
            if isinstance(w, dict) and ('attacker' in w or 'defender' in w):
                if w.get('status', 'active') == 'ended':
                    continue
                attacker = w.get('attacker')
                defender = w.get('defender')
                if attacker == user_country and defender:
                    active_opponents.add(get_canonical_country_name(defender))
                elif defender == user_country and attacker:
                    active_opponents.add(get_canonical_country_name(attacker))
            elif isinstance(w, (list, set)) and str(wid) == user_id:
                for cname in w:
                    active_opponents.add(get_canonical_country_name(cname))
        for name in list(active_opponents):
            active_opponents_norm.add(_normalize_country_name(name))
    except Exception:
        pass
    
    # 2) ساخت لیست کشورهایی که می‌توان به آن‌ها اعلان جنگ داد (کاننیکال)
    available_countries = []
    unique_norm = set()
    try:
        from utils import _normalize_country_name, get_canonical_country_name
    except Exception:
        def _normalize_country_name(x):
            return str(x)
        def get_canonical_country_name(x):
            return str(x)
    
    for country in all_countries:
        country = get_canonical_country_name(country)
        if country == user_country:
            continue
        cn_norm = _normalize_country_name(country)
        if cn_norm in active_opponents_norm:
            continue
        
        # پیدا کردن user_id کشور مقابل
        target_id = None
        for uid, u in utils.users.items():
            if get_canonical_country_name(u.get('country')) == country:
                target_id = uid
                break
        if not target_id:
            continue
        
        # بررسی روابط منفی
        try:
            rel = utils.country_relations.get(user_id, {}).get(target_id, 0)
        except Exception:
            rel = 0
        if rel >= 0:
            continue
        
        if cn_norm in unique_norm:
            continue
        unique_norm.add(cn_norm)
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

    # تنظیم روابط: پس از اعلان جنگ، روابط دو کشور = -100
    try:
        from utils import set_mutual_relation
        set_mutual_relation(user_id, target_id, -100)
    except Exception as _:
        pass
    
    # ثبت اعلان جنگ دوطرفه
    if user_id not in war_declarations:
        war_declarations[user_id] = []
    if target_country not in war_declarations[user_id]:
        war_declarations[user_id].append(target_country)
    if target_id not in war_declarations:
        war_declarations[target_id] = []
    if user_country not in war_declarations[target_id]:
        war_declarations[target_id].append(user_country)
    
    # ذخیره اعلان‌های جنگ
    from utils import save_war_declarations, war_declarations as utils_war_declarations
    utils_war_declarations.update(war_declarations)
    save_war_declarations()
    
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
    
    # بازگشت به منوی استراتژی
    keyboard = [
        [InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('اعلان جنگ با موفقیت انجام شد!', reply_markup=reply_markup)

# --- 4. نمایش لیست کشورها برای آتش‌بس ---
async def show_peace_menu(query):
    user_id = str(query.from_user.id)
    user_country = utils.users.get(user_id, {}).get('country', '')
    # کشورهایی که با آن‌ها در جنگ است
    war_list = war_declarations.get(user_id, [])
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
    minister_message = f"🕊️ {foreign_minister['name']}: درخواست آتش‌بس با {target_country} ارسال شد. امیدواریم صلح برقرار شود."
    
    # ارسال پیام به کشور هدف
    peace_message = f"🕊️ <b>درخواست آتش‌بس</b>\n\nکشور {utils.users[user_id]['country']} از شما درخواست آتش‌بس کرده است.\n\n🤝 آیا می‌خواهید صلح کنید؟"
    try:
        from telegram import Bot
        bot = Bot(token='7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I')
        await bot.send_message(chat_id=int(target_id), text=peace_message, parse_mode='HTML')
    except Exception as e:
        print(f"خطا در ارسال درخواست صلح: {e}")
    
    # پیام تأیید به کاربر
    confirm_message = f"🕊️ <b>درخواست آتش‌بس ارسال شد!</b>\n\nدرخواست صلح شما به کشور {target_country} ارسال شد.\n\n<blockquote>{minister_message}</blockquote>"
    await query.edit_message_text(confirm_message, parse_mode='HTML')

# --- توابع حمله موشکی (Missile Attack) ---

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils import users, war_declarations, save_users, COUNTRY_POPULATIONS




async def show_missile_attack_menu(query):
    user_id = str(query.from_user.id)
    user_data = utils.users.get(user_id, {})
    tech_levels = utils.military_technologies.get(user_id, {})  # دریافت سطوح فناوری از military_technologies
    
    missile_techs = {
        'atomic': {'name': 'موشک اتمی', 'key': 'atomic_bomb', 'max_level': 10, 'power': 100, 'defense_needed': 10},
        'hydrogen': {'name': 'موشک هیدروژنی', 'key': 'hydrogen_bomb', 'max_level': 25, 'power': 100, 'defense_needed': 10},
        'chemical': {'name': 'موشک شیمیایی', 'key': 'chemical_bomb', 'max_level': 25, 'power': 50, 'defense_needed': 5},
        'destructive': {'name': 'موشک تخریبی', 'key': 'destructive_bomb', 'max_level': 25, 'power': 25, 'defense_needed': 3},
        'ballistic': {'name': 'موشک بالستیک ساده', 'key': 'ballistic_missiles', 'max_level': 1, 'power': 10, 'defense_needed': 1},
    }
    
    keyboard = []
    for mtype, info in missile_techs.items():
        tech_level = tech_levels.get(info['key'], 0)
        print(f"[DEBUG] {mtype}: tech_level={tech_level}, max_level={info['max_level']}, key={info['key']}")
        if mtype == 'ballistic' or tech_level >= info['max_level']:
            keyboard.append([InlineKeyboardButton(f"{info['name']} ✅", callback_data=f'missile_type_{mtype}')])
        else:
            progress = min(tech_level, info['max_level'])
            keyboard.append([InlineKeyboardButton(f"{info['name']} 🔒 ({progress}/{info['max_level']})", callback_data='missile_locked')])
    
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = '🚀 نوع موشک مورد نظر برای حمله را انتخاب کنید:'
    from bot import safe_edit_message
    await safe_edit_message(query, text, reply_markup=reply_markup)

async def start_missile_attack_phases(query, missile_type):
    user_id = str(query.from_user.id)
    user_data = utils.users.get(user_id, {})
    user_country = user_data.get('country', '')
    
    # برای همه موشک‌ها، تعداد موشک پرسیده بشه
    max_count = user_data.get('resources', {}).get('ballistic_missiles', 0)
    if max_count < 1:
        from bot import safe_edit_message
        await safe_edit_message(query, 'شما هیچ موشک بالستیک ندارید!', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='missile_attack')]]))
        return
    
    # ثبت وضعیت انتخاب تعداد موشک برای کاربر
    utils.pending_military_production[user_id] = {'step': 'missile_count', 'missile_type': missile_type}
    print(f"[DEBUG] Set pending_military_production for user {user_id}: {utils.pending_military_production[user_id]}")
    print(f"[DEBUG] Full pending_military_production: {utils.pending_military_production}")
    
    # نام موشک بر اساس نوع
    missile_names = {
        'atomic': 'موشک اتمی',
        'hydrogen': 'موشک هیدروژنی',
        'chemical': 'موشک شیمیایی',
        'destructive': 'موشک تخریبی',
        'ballistic': 'موشک بالستیک ساده'
    }
    missile_name = missile_names.get(missile_type, 'موشک')
    
    from bot import safe_edit_message
    await safe_edit_message(query, f'تعداد {missile_name} برای حمله را به صورت عددی ارسال کنید (حداکثر {max_count}):', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='missile_attack')]]))

async def missile_attack_phase_1(query, missile_type, target_country, count):
    text = f"🚀 آماده‌سازی حمله موشکی به {target_country} با موشک نوع {missile_type} (تعداد: {count})...\n\nلطفاً برای ادامه تایید کنید."
    file_id = ''
    keyboard = [[InlineKeyboardButton('ادامه ▶️', callback_data=f'missile_phase2_{missile_type}_{target_country}_{count}')],
                [InlineKeyboardButton('بازگشت ⬅️', callback_data='missile_attack')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    from bot import safe_edit_message
    await safe_edit_message(query, text, reply_markup=reply_markup)

async def missile_attack_phase_2(query, missile_type, target_country, count):
    text = f"🔥 تعدادی موشک {missile_type} به سمت {target_country} شلیک شدند!\n\nدر حال رهگیری..."
    # انتخاب رندوم تصویر حمله موشکی
    missile_photos = [
        "https://t.me/TextEmpire_IR/74",
        "https://t.me/TextEmpire_IR/149",
        "https://t.me/TextEmpire_IR/175"
    ]
    file_id = random.choice(missile_photos)
    keyboard = [[InlineKeyboardButton('ادامه ▶️', callback_data=f'missile_phase3_{missile_type}_{target_country}_{count}')],
                [InlineKeyboardButton('بازگشت ⬅️', callback_data='missile_attack')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    from bot import safe_edit_message
    await safe_edit_message(query, text, reply_markup=reply_markup)

async def missile_attack_phase_3(query, missile_type, target_country, count):
    text = f"💥 {count} موشک {missile_type} در نزدیکی {target_country} منفجر شدند!\n\nدر حال محاسبه نتیجه..."
    file_id = ''
    keyboard = [[InlineKeyboardButton('نمایش نتیجه نهایی 📝', callback_data=f'missile_result_{missile_type}_{target_country}_{count}')],
                [InlineKeyboardButton('بازگشت ⬅️', callback_data='missile_attack')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    from bot import safe_edit_message
    await safe_edit_message(query, text, reply_markup=reply_markup)
async def missile_attack_result(query, missile_type, target_country, count, context):
    """
    تابع قدیمی برای نتیجه حمله موشکی - حالا از تابع مشترک استفاده می‌کنه
    """
    user_id = str(query.from_user.id)
    attacker = utils.users.get(user_id, {})
    attacker_country = attacker.get('country', 'نامشخص')

    defender_id = None
    for uid, u in utils.users.items():
        if u.get('country') == target_country:
            defender_id = uid
            break
    if not defender_id:
        text = f"❌ کشور هدف یافت نشد."
        from bot import safe_edit_message
        await safe_edit_message(query, text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]))
        return
    
    # استفاده از تابع مشترک برای محاسبه نتیجه
    result_data = await calculate_missile_attack_result(
        user_id, attacker_country, defender_id, target_country, 
        missile_type, count, context
    )
    
    if result_data['success']:
        # نمایش نتیجه موفقیت
        text = f"📊 <b>نتیجه نهایی حمله موشکی {result_data['missile_name']} به {target_country}:</b>\n\n"
        text += f"- جمعیت نابود شده: {result_data['population_damage']:,}\n"
        if result_data['destroyed_structures']:
            text += f"- سازه‌های نابود شده: {', '.join(result_data['destroyed_structures'])}\n"
        else:
            text += "- هیچ سازه‌ای نابود نشد.\n"
        text += f"- موشک دفاعی مصرف شده: {result_data['used_defense']}\n"
        text += f"- موشک ارسالی مصرف شده: {count}\n"
        text += f"- حمله موفقیت‌آمیز بود!"
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        from bot import safe_edit_message
        await safe_edit_message(query, text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        # نتیجه قبلاً در تابع مشترک نمایش داده شده
        pass

async def calculate_missile_attack_result(user_id, attacker_country, defender_id, target_country, missile_type, count, context):
    """
    تابع مشترک برای محاسبه نتیجه حمله موشکی
    """
    attacker = utils.users.get(user_id, {})
    defender = utils.users.get(defender_id, {})
    
    missile_info = {
        'atomic': {'name': 'موشک اتمی', 'power': 100, 'defense_needed': 10, 'resource': 'ballistic_missiles'},
        'hydrogen': {'name': 'موشک هیدروژنی', 'power': 100, 'defense_needed': 10, 'resource': 'ballistic_missiles'},
        'chemical': {'name': 'موشک شیمیایی', 'power': 50, 'defense_needed': 5, 'resource': 'ballistic_missiles'},
        'destructive': {'name': 'موشک تخریبی', 'power': 25, 'defense_needed': 3, 'resource': 'ballistic_missiles'},
        'ballistic': {'name': 'موشک بالستیک ساده', 'power': 10, 'defense_needed': 1, 'resource': 'ballistic_missiles'},
    }
    info = missile_info.get(missile_type, missile_info['ballistic'])
    missile_count = count
    total_power = info['power'] * missile_count
    total_defense_needed = info['defense_needed'] * missile_count
    
    # بررسی موجودی موشک (فقط برای تابع auto_phases)
    if 'auto_phases' in context.__dict__:
        # موشک‌ها قبلاً در process_missile_count_input کم شده‌اند
        # نیازی به چک مجدد نیست
        pass
    
    defender_missiles = defender['resources'].get('defense_missiles', 0)
    # ۱٪ احتمال خطا در رهگیری
    random_fail = random.random() < 0.01
    attack_success = defender_missiles < total_defense_needed or random_fail
    used_defense = min(defender_missiles, total_defense_needed)
    defender['resources']['defense_missiles'] -= used_defense
    
    if not attack_success:
        from utils import save_users
        save_users()
        if random_fail:
            result_text = f"🛡️ موشک‌های دفاعی تلاش کردند اما به دلیل خطای رهگیری، حمله موفق شد!"
            
            # ارسال فایل برای موفقیت به دلیل خطای رهگیری (بدون پیام متنی جداگانه)
            success_file_id = 'https://t.me/TextEmpire_IR/87'
            await context.bot.send_photo(chat_id=int(user_id), photo=success_file_id, caption=result_text)
            await context.bot.send_photo(chat_id=int(defender_id), photo=success_file_id, caption="🛡️ خطای رهگیری: موشک‌های دفاعی موفق به رهگیری نشدند!")
            await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=success_file_id, caption=f"🛡️ خطای رهگیری: حمله موشکی {attacker_country} به {target_country} موفق شد!")
        else:
            result_text = f"🛡️ حمله موشکی شما توسط {used_defense} موشک دفاعی دفع شد و موشک‌های ارسالی نابود شدند."
            
            # ارسال فایل برای شکست حمله (بدون پیام متنی جداگانه)
            # انتخاب رندوم فایل برای شکست حمله
            failure_photos = [
                "https://t.me/TextEmpire_IR/86",   # عکس
                "https://t.me/TextEmpire_IR/161"   # گیف
            ]
            failure_file_id = random.choice(failure_photos)
            await send_media_safe(context.bot, int(user_id), failure_file_id, result_text)
            await send_media_safe(context.bot, int(defender_id), failure_file_id, "🛡️ حمله موشکی توسط پدافند دفع شد!")
            await send_media_safe(context.bot, NEWS_CHANNEL_ID, failure_file_id, f"🛡️ حمله موشکی {attacker_country} به {target_country} توسط پدافند دفع شد!")
        return {'success': False}
    # محاسبه خسارات
    defender_country = defender.get('country', target_country)
    population = defender.get('population', COUNTRY_POPULATIONS.get(defender_country, 1000000))
    
    destroyed_population = 0
    destroyed_structures = []
    
    # موشک‌های شیمیایی، هیدروژنی و اتمی جمعیت نابود می‌کنن
    if missile_type in ['chemical', 'hydrogen', 'atomic']:
        destroyed_population = int((total_power / 10) * 0.001 * population)
        defender['population'] = max(0, population - destroyed_population)
        
        print(f"[DEBUG] Population destruction:")
        print(f"[DEBUG] - missile_type: {missile_type}")
        print(f"[DEBUG] - defender_country: {defender_country}")
        print(f"[DEBUG] - original population: {population}")
        print(f"[DEBUG] - total_power: {total_power}")
        print(f"[DEBUG] - destroyed_population: {destroyed_population}")
        print(f"[DEBUG] - new population: {defender['population']}")
    
    # موشک‌های تخریبی، هیدروژنی و اتمی سازه نابود می‌کنن
    if missile_type in ['destructive', 'hydrogen', 'atomic'] and missile_count >= 5:
        num_structures = max(1, missile_count // 10)  # هر 10 موشک = 1 سازه
        all_structures = []
        
        # بررسی اینکه آیا بازیکن اصلاً سازه‌ای داره
        if 'buildings' in defender and defender['buildings']:
            for cat in defender.get('buildings', {}):
                if defender['buildings'][cat]:  # اگر دسته‌بندی خالی نباشه
                    all_structures.extend(defender['buildings'][cat])
        
        print(f"[DEBUG] Structure destruction:")
        print(f"[DEBUG] - missile_type: {missile_type}")
        print(f"[DEBUG] - missile_count: {missile_count}")
        print(f"[DEBUG] - num_structures to destroy: {num_structures}")
        print(f"[DEBUG] - available structures: {all_structures}")
        print(f"[DEBUG] - has buildings: {'buildings' in defender}")
        print(f"[DEBUG] - buildings data: {defender.get('buildings', {})}")
        
        # فقط اگر سازه‌ای موجود باشه
        if all_structures:
            for _ in range(num_structures):
                if all_structures:
                    s = random.choice(all_structures)
                    destroyed_structures.append(s)
                    all_structures.remove(s)  # حذف از لیست موقت
                    for cat in defender.get('buildings', {}):
                        if s in defender['buildings'][cat]:
                            defender['buildings'][cat].remove(s)
                            print(f"[DEBUG] - destroyed structure: {s} from category: {cat}")
                            break
        else:
            print(f"[DEBUG] - No structures available to destroy")
            destroyed_structures = []  # هیچ سازه‌ای نابود نشد
    
    # ذخیره تغییرات بلافاصله
    from utils import save_users
    save_users()
    print(f"[DEBUG] Users saved after all changes")
    
    from utils import save_users
    save_users()
    
    return {
        'success': True,
        'missile_name': info['name'],
        'population_damage': destroyed_population,
        'destroyed_structures': destroyed_structures,
        'used_defense': used_defense,
        'missile_count': missile_count
    }

async def show_missile_target_selection(message_or_query, missile_type, count):
    """
    نمایش انتخاب هدف برای حمله موشکی
    message_or_query می‌تونه message یا query باشه
    """
    if hasattr(message_or_query, 'from_user'):
        user_id = str(message_or_query.from_user.id)
    else:
        user_id = str(message_or_query.from_user.id)
    
    user_data = utils.users.get(user_id, {})
    user_country = user_data.get('country', '')
    attackable_countries = []
    # بررسی جنگ‌های فعال با فرمت جدید war_declarations
    for wid, war in utils.war_declarations.items():
        if isinstance(war, dict) and war.get('status') == 'active':
            attacker = war.get('attacker')
            defender = war.get('defender')
            if attacker == user_country and defender != user_country:
                attackable_countries.append(defender)
            elif defender == user_country and attacker != user_country:
                attackable_countries.append(attacker)
    if not attackable_countries:
        # بازگرداندن موشک‌ها به موجودی کاربر
        missile_resources = {
            'atomic': 'ballistic_missiles',
            'hydrogen': 'ballistic_missiles', 
            'chemical': 'ballistic_missiles',
            'destructive': 'ballistic_missiles',
            'ballistic': 'ballistic_missiles'
        }
        resource_type = missile_resources.get(missile_type, 'ballistic_missiles')
        user_data['resources'][resource_type] += count
        from utils import save_users
        save_users()
        
        if hasattr(message_or_query, 'reply_text'):
            await message_or_query.reply_text('❌ هیچ کشور قابل حمله‌ای یافت نشد! موشک‌های شما به موجودی بازگردانده شد.')
        else:
            from bot import safe_edit_message
            keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await safe_edit_message(message_or_query, '❌ هیچ کشور قابل حمله‌ای یافت نشد! موشک‌های شما به موجودی بازگردانده شد.', reply_markup=reply_markup)
        return
    
    keyboard = []
    for country in attackable_countries:
        # جلوگیری از هدف قرار دادن کشور دارای صلح اجباری
        try:
            defender_id = None
            for uid, u in utils.users.items():
                if u.get('country') == country:
                    defender_id = uid
                    break
            protected = False
            if defender_id:
                from bot import is_user_peace_protected
                protected = is_user_peace_protected(defender_id)
            if protected:
                label = f"{country} 🔒"
                callback = 'missile_attack'  # دکمه غیرفعال‌نما
            else:
                label = country
                callback = f'missile_target_{missile_type}_{country}_{count}'
        except Exception:
            label = country
            callback = f'missile_target_{missile_type}_{country}_{count}'
        keyboard.append([InlineKeyboardButton(label, callback_data=callback)])
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='missile_attack')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(message_or_query, 'reply_text'):
        await message_or_query.reply_text('🎯 کشور هدف برای حمله موشکی را انتخاب کنید:', reply_markup=reply_markup)
    else:
        from bot import safe_edit_message
        await safe_edit_message(message_or_query, '🎯 کشور هدف برای حمله موشکی را انتخاب کنید:', reply_markup=reply_markup)
async def missile_attack_auto_phases(user_id, missile_type, target_country, count, context):
    from bot import safe_edit_message
    attacker = utils.users.get(user_id, {})
    defender_id = None
    for uid, u in utils.users.items():
        if u.get('country') == target_country:
            defender_id = uid
            break
    if not defender_id:
        return
    defender = utils.users[defender_id]
    attacker_country = attacker.get('country', '')
    # مرحله ۱: آماده‌سازی
    prep_text = f"🚀 آماده‌سازی حمله موشکی به {target_country} با موشک نوع {missile_type} (تعداد: {count})..."
    # انتخاب رندوم فایل برای آماده‌سازی
    prep_photos = [
        "https://t.me/TextEmpire_IR/88",   # تصویر
        "https://t.me/TextEmpire_IR/174"    # گیف
    ]
    file_id = random.choice(prep_photos)
    try:
        # ارسال فایل با caption (بدون پیام متنی جداگانه)
        await send_media_safe(context.bot, int(user_id), file_id, prep_text)
        await send_media_safe(context.bot, int(defender_id), file_id, f"🚨 هشدار: {attacker_country} در حال آماده‌سازی حمله موشکی است!")
        await send_media_safe(context.bot, NEWS_CHANNEL_ID, file_id, f"🚀 آماده‌سازی حمله موشکی توسط {attacker_country} به {target_country}")
    except Exception:
        pass
    await asyncio.sleep(120)
    # مرحله ۲: شلیک
    fire_text = f"🔥 تعدادی موشک {missile_type} به سمت {target_country} شلیک شدند!"
    # انتخاب رندوم تصویر شلیک موشک
    fire_photos = [
        "https://t.me/TextEmpire_IR/74",   # عکس
        "https://t.me/TextEmpire_IR/149",  # عکس
        "https://t.me/TextEmpire_IR/175"   # گیف
    ]
    fire_file_id = random.choice(fire_photos)
    try:
        # ارسال فایل با caption (بدون پیام متنی جداگانه)
        await send_media_safe(context.bot, int(user_id), fire_file_id, fire_text)
        await send_media_safe(context.bot, int(defender_id), fire_file_id, f"🚨 هشدار: تعدادی موشک {missile_type} به سمت کشور شما شلیک شد!")
        await send_media_safe(context.bot, NEWS_CHANNEL_ID, fire_file_id, f"🔥 تعدادی موشک {missile_type} توسط {attacker_country} به سمت {target_country} شلیک شد!")
    except Exception:
        pass
    await asyncio.sleep(120)
    # مرحله ۳: نزدیکی هدف
    hit_text = f"💥 {count} موشک {missile_type} در نزدیکی {target_country} منفجر شدند!"
    hit_file_id = 'https://t.me/TextEmpire_IR/85'  # TODO: فایل ID مناسب برای نزدیکی هدف
    try:
        # ارسال فایل با caption (بدون پیام متنی جداگانه)
        await context.bot.send_photo(chat_id=int(user_id), photo=hit_file_id, caption=hit_text)
        await context.bot.send_photo(chat_id=int(defender_id), photo=hit_file_id, caption=f"💥 {count} موشک {missile_type} در نزدیکی کشور شما منفجر شد!")
        await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=hit_file_id, caption=f"💥 {count} موشک {missile_type} در نزدیکی {target_country} منفجر شد!")
    except Exception:
        pass
    await asyncio.sleep(120)
    # مرحله ۴: نتیجه نهایی
    # استفاده از تابع مشترک برای محاسبه نتیجه
    context.auto_phases = True  # علامت برای تابع مشترک
    result_data = await calculate_missile_attack_result(
        user_id, attacker_country, defender_id, target_country, 
        missile_type, count, context
    )
    
    if result_data['success']:
        # نمایش نتیجه موفقیت
        result_text = f"📊 <b>نتیجه نهایی حمله موشکی {result_data['missile_name']} به {target_country}:</b>\n\n"
        result_text += f"- جمعیت نابود شده: {result_data['population_damage']:,}\n"
        if result_data['destroyed_structures']:
            result_text += f"- سازه‌های نابود شده: {', '.join(result_data['destroyed_structures'])}\n"
        else:
            result_text += "- هیچ سازه‌ای نابود نشد.\n"
        result_text += f"- موشک دفاعی مصرف شده: {result_data['used_defense']}\n"
        result_text += f"- موشک ارسالی مصرف شده: {result_data['missile_count']}\n"
        result_text += f"- حمله موفقیت‌آمیز بود!"
        
        # فایل ID برای موفقیت حمله
        success_file_id = 'https://t.me/TextEmpire_IR/87'  # TODO: فایل ID مناسب برای موفقیت حمله
        
        # ارسال فایل همراه با پیام موفقیت (بدون پیام متنی جداگانه)
        await context.bot.send_photo(chat_id=int(user_id), photo=success_file_id, caption=result_text, parse_mode='HTML')
        await context.bot.send_photo(chat_id=int(defender_id), photo=success_file_id, caption=result_text, parse_mode='HTML')
        await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=success_file_id, caption=f"📊 نتیجه نهایی حمله موشکی {attacker_country} به {target_country}:\n{result_text}", parse_mode='HTML')

async def process_missile_count_input(message, context):
    """
    پردازش تعداد موشک وارد شده توسط کاربر
    """
    user_id = str(message.from_user.id)
    print(f"[DEBUG] process_missile_count_input called for user {user_id}")
    
    # بررسی اینکه آیا کاربر در مرحله انتخاب تعداد موشک هست
    print(f"[DEBUG] pending_military_production in process_missile_count_input: {utils.pending_military_production}")
    print(f"[DEBUG] User {user_id} in pending_military_production: {user_id in utils.pending_military_production}")
    
    if user_id not in utils.pending_military_production:
        print(f"[DEBUG] User {user_id} not in pending_military_production")
        return
    
    if utils.pending_military_production[user_id].get('step') != 'missile_count':
        print(f"[DEBUG] User {user_id} step is not missile_count: {utils.pending_military_production[user_id]}")
        return
    
    missile_type = utils.pending_military_production[user_id].get('missile_type')
    if not missile_type:
        print(f"[DEBUG] No missile_type for user {user_id}")
        return
    
    print(f"[DEBUG] Processing missile count for type: {missile_type}")
    
    try:
        count = int(message.text.strip())
        print(f"[DEBUG] Count entered: {count}")
        
        if count < 1:
            await message.reply_text('❌ تعداد موشک باید حداقل 1 باشد!')
            return
        
        # بررسی موجودی موشک
        user_data = utils.users.get(user_id, {})
        
        # تعیین نوع منبع موشک بر اساس نوع موشک
        missile_resources = {
            'atomic': 'ballistic_missiles',
            'hydrogen': 'ballistic_missiles', 
            'chemical': 'ballistic_missiles',
            'destructive': 'ballistic_missiles',
            'ballistic': 'ballistic_missiles'
        }
        resource_type = missile_resources.get(missile_type, 'ballistic_missiles')
        max_count = user_data.get('resources', {}).get(resource_type, 0)
        
        if count > max_count:
            await message.reply_text(f'❌ شما فقط {max_count} {missile_type} دارید!')
            return
        
        # کم کردن موشک از موجودی
        user_data['resources'][resource_type] -= count
        from utils import save_users
        save_users()
        print(f"[DEBUG] Deducted {count} {missile_type} from user {user_id}, remaining: {user_data['resources'][resource_type]}")
        
        # پاک کردن وضعیت
        del utils.pending_military_production[user_id]
        print(f"[DEBUG] Cleared pending_military_production for user {user_id}")
        
        # نمایش انتخاب هدف
        await show_missile_target_selection(message, missile_type, count)
        
    except ValueError:
        await message.reply_text('❌ لطفاً یک عدد معتبر وارد کنید!')
