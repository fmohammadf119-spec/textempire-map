import json
import time
import random
import string
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import utils
from utils import (
    users, game_data, independence_loans, conquered_countries_data, NEWS_CHANNEL_ID,
    save_independence_loans, save_conquered_countries_data, save_users,
    secret_loan_claimed, save_secret_loan_claimed,
    economy_secret_claimed, save_economy_secret_claimed,
    format_price_short
)

# فایل‌های ذخیره‌سازی بانک
BANK_DATA_FILE = 'bank_data.json'
LOAN_HISTORY_FILE = 'loan_history.json'
BANK_ACCOUNTS_FILE = 'bank_accounts.json'
TRANSFER_HISTORY_FILE = 'transfer_history.json'
OVERDUE_DEBTS_FILE = 'overdue_debts.json'
SECRET_LOAN_ACTIVATED_FILE = 'secret_loan_activated.json'
SECRET_LOAN_CLAIMED_FILE = 'secret_loan_claimed.json'

# متغیرهای بانک
bank_data = {
    'total_loans_given': 0,
    'total_loans_paid': 0,
    'total_interest_earned': 0,
    'bank_reserves': 100000000000,  # 10 میلیارد دلار ذخیره اولیه
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
        },
        'secret': {
            'amount': 1_000_000_000,
            'interest_rate': 0.0,
            'duration': 24,
            'max_uses': 1
        }
    }
}

loan_history = {}  # تاریخچه وام‌های پرداخت شده
bank_accounts = {}  # حساب‌های بانکی کاربران
transfer_history = {}  # تاریخچه انتقالات
pending_transfers = {}  # انتقالات در انتظار تایید
overdue_debts = {}  # بدهی‌های معوق و جریمه‌های دیرکرد
secret_loan_activated = {}  # کاربرانی که وام مخفی برایشان فعال شده

def generate_account_number():
    """تولید شماره حساب تصادفی"""
    return ''.join(random.choices(string.digits, k=12))

def create_bank_account(user_id):
    """ایجاد حساب بانکی برای کاربر"""
    if user_id not in bank_accounts:
        account_number = generate_account_number()
        bank_accounts[user_id] = {
            'account_number': account_number,
            'balance': 0,
            'created_at': time.time(),
            'transactions': []
        }
        save_bank_accounts()
        return account_number
    return bank_accounts[user_id]['account_number']

def get_account_by_number(account_number):
    """یافتن حساب با شماره حساب"""
    for user_id, account in bank_accounts.items():
        if account['account_number'] == account_number:
            return user_id, account
    return None, None

def mask_account_number(account_number):
    """مخفی کردن بخشی از شماره حساب"""
    if len(account_number) >= 12:
        return f"{account_number[:3]}******{account_number[-3:]}"
    return account_number

def save_bank_accounts():
    """ذخیره حساب‌های بانکی"""
    try:
        with open(BANK_ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(bank_accounts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[DEBUG] Error saving bank_accounts: {e}")

def load_bank_accounts():
    """بارگذاری حساب‌های بانکی"""
    global bank_accounts
    try:
        with open(BANK_ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            bank_accounts = json.load(f)
    except Exception as e:
        bank_accounts = {}
        print(f"[DEBUG] Created new bank_accounts: {e}")

def save_transfer_history():
    """ذخیره تاریخچه انتقالات"""
    try:
        with open(TRANSFER_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(transfer_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[DEBUG] Error saving transfer_history: {e}")

def load_transfer_history():
    """بارگذاری تاریخچه انتقالات"""
    global transfer_history
    try:
        with open(TRANSFER_HISTORY_FILE, 'r', encoding='utf-8') as f:
            transfer_history = json.load(f)
    except Exception as e:
        transfer_history = {}
        print(f"[DEBUG] Created new transfer_history: {e}")

def save_bank_data():
    """ذخیره داده‌های بانک"""
    try:
        with open(BANK_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(bank_data, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] Saved bank_data: {bank_data}")
    except Exception as e:
        print(f"[DEBUG] Error saving bank_data: {e}")

def load_bank_data():
    """بارگذاری داده‌های بانک"""
    global bank_data
    try:
        with open(BANK_DATA_FILE, 'r', encoding='utf-8') as f:
            bank_data = json.load(f)
        print(f"[DEBUG] Loaded bank_data: {bank_data}")
    except Exception as e:
        bank_data = {
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
        print(f"[DEBUG] Created new bank_data: {bank_data}, error: {e}")

def save_loan_history():
    """ذخیره تاریخچه وام‌ها"""
    try:
        with open(LOAN_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(loan_history, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] Saved loan_history: {loan_history}")
    except Exception as e:
        print(f"[DEBUG] Error saving loan_history: {e}")

def load_loan_history():
    """بارگذاری تاریخچه وام‌ها"""
    global loan_history
    try:
        with open(LOAN_HISTORY_FILE, 'r', encoding='utf-8') as f:
            loan_history = json.load(f)
        # اگر loan_history لیست هست، به دیکشنری تبدیل کن
        if isinstance(loan_history, list):
            loan_history = {}
        print(f"[DEBUG] Loaded loan_history: {loan_history}")
    except Exception as e:
        loan_history = {}
        print(f"[DEBUG] Created new loan_history: {loan_history}, error: {e}")

def save_overdue_debts():
    """ذخیره بدهی‌های معوق"""
    try:
        with open(OVERDUE_DEBTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(overdue_debts, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[DEBUG] Error saving overdue_debts: {e}")

def load_overdue_debts():
    """بارگذاری بدهی‌های معوق"""
    global overdue_debts
    try:
        with open(OVERDUE_DEBTS_FILE, 'r', encoding='utf-8') as f:
            overdue_debts = json.load(f)
    except Exception as e:
        overdue_debts = {}
        print(f"[DEBUG] Created new overdue_debts: {e}")

def save_active_loans():
    """ذخیره وام‌های فعال در فایل"""
    try:
        with open('active_loans.json', 'w', encoding='utf-8') as f:
            json.dump(independence_loans, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"خطا در ذخیره وام‌های فعال: {e}")

def load_active_loans():
    """بارگذاری وام‌های فعال از فایل"""
    global independence_loans
    try:
        with open('active_loans.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            # اطمینان از اینکه independence_loans یک dict است
            if isinstance(data, dict):
                independence_loans = data
            else:
                print(f"خطا: independence_loans باید dict باشد، اما {type(data)} است")
                independence_loans = {}
    except FileNotFoundError:
        independence_loans = {}
    except Exception as e:
        print(f"خطا در بارگذاری وام‌های فعال: {e}")
        independence_loans = {}

def get_user_loan_count(user_id, loan_type):
    """دریافت تعداد وام‌های دریافت شده توسط کاربر"""
    user_history = loan_history.get(user_id, {})
    return user_history.get(loan_type, 0)

def can_user_get_loan(user_id, loan_type):
    """بررسی اینکه آیا کاربر می‌تواند وام دریافت کند"""
    if user_id not in utils.users:
        return False, "کاربر یافت نشد"
    
    user = utils.users[user_id]
    if not user.get('activated'):
        return False, "کشور فعال نشده است"
    
    # اگر وام مخفی درخواست می‌شود
    if loan_type == 'secret':
        if secret_loan_claimed:
            return False, "این وام مخفی قبلاً توسط شخص دیگری دریافت شده است"
        
        # بررسی اینکه آیا وام مخفی برای این کاربر فعال شده
        if not secret_loan_activated.get(user_id, False):
            return False, "این وام مخفی برای شما فعال نشده است"
        
        # بررسی وام‌های فعال کاربر
        if user_id in independence_loans:
            active_loan = independence_loans[user_id]
            active_loan_type = active_loan.get('loan_type', 'نامشخص')
            
            # بررسی اینکه آیا کاربر قبلاً وام مخفی گرفته
            if active_loan_type == 'secret':
                return False, "شما قبلاً این وام مخفی را دریافت کرده‌اید"
        
        return True, "موفق"
    
    # برای وام‌های عادی
    loan_config = bank_data['loan_types'].get(loan_type)
    if not loan_config:
        return False, "نوع وام نامعتبر است"
    
    # بررسی وام‌های فعال کاربر
    if user_id in independence_loans:
        active_loan = independence_loans[user_id]
        active_loan_type = active_loan.get('loan_type', 'نامشخص')
        
        # برای وام‌های عادی، اگر وام فعال دارید، اجازه نده
        if not active_loan.get('paid', False):
            return False, "شما وام فعالی دارید و نمی‌توانید وام جدید دریافت کنید"
    
    # بررسی تعداد استفاده‌های قبلی
    current_uses = get_user_loan_count(user_id, loan_type)
    if current_uses >= loan_config['max_uses']:
        return False, f"حداکثر تعداد استفاده از این وام ({loan_config['max_uses']}) رسیده است"
    
    # بررسی فاصله زمانی بین وام‌ها (2 دور) - فقط برای وام‌های عادی
    current_turn = game_data['turn']
    user_history = loan_history.get(user_id, {})
    last_loan_turn = user_history.get('last_loan_turn', 0)
    
    if current_turn - last_loan_turn < 2:
        remaining_turns = 2 - (current_turn - last_loan_turn)
        return False, f"برای دریافت وام جدید باید {remaining_turns} دور دیگر صبر کنید"
    
    # بررسی شرایط خاص برای وام استقلال
    if loan_type == 'independence':
        # بررسی اینکه آیا کاربر قبلاً فتح شده بوده و حالا مستقل شده
        user = utils.users.get(user_id, {})
        
        # اگر کاربر هنوز فتح شده است
        if user.get('conquered_by'):
            return False, "این وام فقط برای کشورهای آزاد شده در دسترس است"
        
        # اگر کاربر در conquered_countries_data است (هنوز فتح شده)
        if user_id in conquered_countries_data:
            return False, "این وام فقط برای کشورهای آزاد شده در دسترس است"
        
        # بررسی اینکه آیا کاربر قبلاً فتح شده بوده (از طریق was_conquered)
        if not user.get('was_conquered', False):
            return False, "این وام فقط برای کشورهای آزاد شده در دسترس است"
    
    # بررسی موجودی بانک (برای وام‌های عادی)
    if bank_data['bank_reserves'] < loan_config['amount']:
        return False, "موجودی بانک کافی نیست"
    
    return True, "موفق"

def grant_loan(user_id, loan_type):
    """اعطای وام به کاربر"""
    can_get, message = can_user_get_loan(user_id, loan_type)
    if not can_get:
        return False, message
    
    current_turn = game_data['turn']
    
    # اگر وام مخفی درخواست می‌شود
    if loan_type == 'secret':
        loan_amount = 1_000_000_000  # 1 میلیارد
        due_turn = current_turn + 24  # 24 دور مهلت
        
        # ایجاد وام مخفی
        loan_data = {
            'amount': loan_amount,
            'start_turn': current_turn,
            'due_turn': due_turn,
            'interest_rate': 0.0,
            'loan_type': 'secret',
            'paid': False
        }
        
        # علامت‌گذاری وام مخفی به عنوان دریافت شده
        secret_loan_claimed = True
        save_secret_loan_claimed()
        
        # حذف کاربر از لیست فعال‌ها
        if user_id in secret_loan_activated:
            del secret_loan_activated[user_id]
            save_secret_loan_activated()
    else:
        # برای وام‌های عادی
        loan_config = bank_data['loan_types'][loan_type]
        due_turn = current_turn + loan_config['duration']
        
        # ایجاد وام عادی
        loan_data = {
            'amount': loan_config['amount'],
            'start_turn': current_turn,
            'due_turn': due_turn,
            'interest_rate': loan_config['interest_rate'],
            'loan_type': loan_type,
            'paid': False
        }
        
        # کسر از موجودی بانک (فقط برای وام‌های عادی)
        bank_data['bank_reserves'] -= loan_config['amount']
    
    # ثبت آخرین دور وام در تاریخچه (فقط برای وام‌های عادی)
    if user_id not in loan_history:
        loan_history[user_id] = {}
    loan_history[user_id]['last_loan_turn'] = current_turn
    
    # ذخیره وام در فایل مناسب
    if loan_type == 'independence':
        independence_loans[user_id] = loan_data
    else:
        # برای وام‌های دیگر، در independence_loans ذخیره می‌کنیم (فایل مشترک)
        independence_loans[user_id] = loan_data
    
    # اضافه کردن پول به کاربر
    user = utils.users[user_id]
    if 'resources' not in user:
        user['resources'] = {}
    user['resources']['cash'] = user['resources'].get('cash', 0) + loan_data['amount']
    
    bank_data['total_loans_given'] += 1
    
    # ذخیره تغییرات
    save_users()
    save_active_loans()
    save_bank_data()
    save_loan_history()
    
    return True, f"وام {loan_type} با موفقیت اعطا شد"

async def process_loan_payments(current_turn):
    """پردازش پرداخت‌های وام در هر دور"""
    loans_to_remove = []
    
    for user_id, loan_data in independence_loans.items():
        if user_id in utils.users and not loan_data.get('paid', False):
            if current_turn >= loan_data['due_turn']:
                # کسر پول از کاربر
                loan_amount = loan_data['amount']
                interest_amount = int(loan_amount * loan_data['interest_rate'])
                total_amount = loan_amount + interest_amount
                
                user = utils.users[user_id]
                user_cash = user.get('resources', {}).get('cash', 0)
                
                if user_cash >= total_amount:
                    # پرداخت کامل
                    user['resources']['cash'] = user_cash - total_amount
                    bank_data['bank_reserves'] += total_amount
                    bank_data['total_loans_paid'] += 1
                    bank_data['total_interest_earned'] += interest_amount
                    
                    # ثبت در تاریخچه
                    if user_id not in loan_history:
                        loan_history[user_id] = {}
                    loan_history[user_id][loan_data['loan_type']] = loan_history[user_id].get(loan_data['loan_type'], 0) + 1
                    
                    # ارسال پیام به کاربر
                    try:
                        from telegram import Bot
                        bot = Bot(token='7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I')
                        loan_names = {
                            'independence': 'وام استقلال',
                            'development': 'وام توسعه',
                            'emergency': 'وام اضطراری',
                            'installment': 'وام اقساطی'
                        }
                        loan_name = loan_names.get(loan_data['loan_type'], 'وام')
                        await bot.send_message(
                            chat_id=int(user_id),
                            text=f"🏦 {loan_name} شما به مبلغ {format_price_short(total_amount)} به صورت خودکار کسر شد."
                        )
                    except Exception:
                        pass
                    
                else:
                    # اگر پول کافی نباشد - ایجاد بدهی معوق
                    remaining_debt = total_amount - user_cash
                    user['resources']['cash'] = 0
                    bank_data['bank_reserves'] += user_cash
                    
                    # ثبت بدهی معوق
                    overdue_debts[user_id] = {
                        'original_amount': total_amount,
                        'remaining_debt': remaining_debt,
                        'loan_type': loan_data['loan_type'],
                        'due_turn': loan_data['due_turn'],
                        'overdue_since': current_turn,
                        'late_fees': 0,
                        'installment_payments': []
                    }
                    
                    # ارسال پیام به کاربر
                    try:
                        from telegram import Bot
                        bot = Bot(token='7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I')
                        loan_names = {
                            'independence': 'وام استقلال',
                            'development': 'وام توسعه',
                            'emergency': 'وام اضطراری',
                            'installment': 'وام اقساطی'
                        }
                        loan_name = loan_names.get(loan_data['loan_type'], 'وام')
                        await bot.send_message(
                            chat_id=int(user_id),
                            text=f"🏦 {loan_name} شما کسر شد. موجودی شما صفر شد و {format_price_short(remaining_debt)} بدهی معوق ایجاد شد.\n\n💡 می‌توانید از منوی بانک، گزینه 'بدهی‌های معوق' را انتخاب کنید."
                        )
                    except Exception:
                        pass
                
                loans_to_remove.append(user_id)
    
    # حذف وام‌های پرداخت شده
    for user_id in loans_to_remove:
        independence_loans.pop(user_id, None)
    
    # پردازش جریمه‌های دیرکرد برای بدهی‌های معوق
    for user_id, debt_data in overdue_debts.items():
        if user_id in utils.users:
            overdue_turns = current_turn - debt_data['overdue_since']
            if overdue_turns > 0:
                # جریمه 5% در هر دور
                late_fee = int(debt_data['remaining_debt'] * 0.05)
                debt_data['late_fees'] += late_fee
                debt_data['remaining_debt'] += late_fee
    
    # ذخیره تغییرات
    save_users()
    save_active_loans()
    save_bank_data()
    save_loan_history()
    save_overdue_debts()

# توابع نمایش منوها
async def show_international_bank_menu(query):
    """نمایش منوی اصلی بانک بین‌المللی"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return
    
    country_name = user.get('country', 'کشور ناشناس')
    
    # پیام خوشامدگویی از جی پی مورگان
    text = "🏦 <b>خوش آمدید!</b>\n\n"
    text += "🏦 من جی پی مورگان، مدیر ارشد بانک بین‌المللی هستم.\n"
    text += f"🏦 <b>بانک بین‌المللی - خدمات برای کشور {country_name}</b>\n\n"
    
    text += f"💰 موجودی بانک: {format_price_short(bank_data['bank_reserves'])}\n"
    text += f"📊 کل وام‌های اعطا شده: {bank_data['total_loans_given']:,}\n"
    text += f"✅ کل وام‌های پرداخت شده: {bank_data['total_loans_paid']:,}\n"
    text += f"💵 کل سود کسب شده: {format_price_short(bank_data['total_interest_earned'])}\n\n"
    
    text += "💡 <b>خدمات موجود:</b>\n"
    text += "▫️ وام استقلال\n"
    text += "▫️ وام توسعه\n"
    text += "▫️ وام اضطراری\n"
    text += "▫️ حساب‌های بانکی\n"
    text += "▫️ بدهی‌های معوق\n\n"
    
    # بررسی بدهی‌های معوق
    overdue_count = len([uid for uid in overdue_debts.keys() if uid == user_id])
    if overdue_count > 0:
        text += f"⚠️ <b>شما {overdue_count} بدهی معوق دارید!</b>\n\n"
    
    # تحلیل هوشمند بانکی
    from analysis import generate_bank_analysis
    analysis = generate_bank_analysis(user_id)
    
    text += f"\n<b>پیشنهاد جی پی مورگان:</b>\n<blockquote>{analysis}</blockquote>"
    
    keyboard = [
        [InlineKeyboardButton('وام‌ها 💰', callback_data='loans_menu')],
        [InlineKeyboardButton('حساب بانکی 💳', callback_data='bank_account')],
        [InlineKeyboardButton('وام‌های من 📋', callback_data='my_loans')],
        [InlineKeyboardButton('بدهی‌های معوق ⚠️', callback_data='overdue_debts')],
        [InlineKeyboardButton('💬 صحبت با جی پی مورگان', callback_data='chat_with_morgan')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='diplomacy')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# متغیر برای ذخیره کاربری که از ایونت مخفی استفاده کرده
secret_event_user = None

async def show_chat_with_morgan(query):
    """نمایش چت با جی پی مورگان"""
    global secret_event_user
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return
    
    country_name = user.get('country', 'کشور ناشناس')
    
    # پیام معرفی جی پی مورگان
    text = "🏦 <b>خوش آمدید!</b>\n\n"
    text += "🏦 من جی پی مورگان، مدیر ارشد بانک بین‌المللی هستم.\n"
    text += f"🏦 <b>چت خصوصی با کشور {country_name}</b>\n\n"
    text += "💬 می‌توانید با من در مورد مسائل مالی صحبت کنید.\n"
    text += "📝 هر پیامی که ارسال کنید، من آن را بررسی می‌کنم.\n\n"
    text += "💡 <b>موضوعات قابل بحث:</b>\n"
    text += "▫️ وام‌ها و شرایط آن‌ها\n"
    text += "▫️ حساب‌های بانکی\n"
    text += "▫️ بدهی‌های معوق\n"
    text += "▫️ مسائل مالی دیگر\n\n"
    text += "📝 پیام خود را ارسال کنید:"
    
    # تنظیم کاربر برای دریافت پیام
    if secret_event_user is None:
        secret_event_user = user_id
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_morgan_chat(update, context):
    """پردازش پیام‌های چت با جی پی مورگان"""
    global secret_event_user, economy_secret_claimed, secret_loan_claimed
    user_id = str(update.effective_user.id)
    
    # بررسی اینکه آیا کاربر مجاز است
    if secret_event_user != user_id:
        await update.message.reply_text("متأسفانه این چت برای شما در دسترس نیست.")
        return
    
    message_text = update.message.text.lower()
    country_name = utils.users.get(user_id, {}).get('country', 'کشور ناشناس')
    
    # کلیدواژه‌های مخفی برای وام بزرگ
    secret_keywords = [
        "میتونی بهم یه وام بزرگتر بدی",
        "یه وام بزرگتر میخوام",
        "پول بیشتری لازم دارم"
    ]
    
    # کلیدواژه‌های مخفی برای جایزه اقتصاد
    economy_secret_keywords = [
        "اقتصاد مال خر است"
    ]
    
    # بررسی کلیدواژه‌های مخفی
    for keyword in secret_keywords:
        if keyword in message_text:
            # بررسی اینکه آیا قبلاً کسی وام مخفی گرفته
            if secret_loan_claimed:
                await update.message.reply_text("❌ متأسفانه این وام مخفی قبلاً توسط شخص دیگری دریافت شده است.")
                return
            
            # بررسی اینکه آیا قبلاً کسی کلیدواژه گفته و وام فعال کرده
            if secret_loan_activated:
                await update.message.reply_text("❌ متأسفانه این وام مخفی قبلاً توسط شخص دیگری فعال شده است.")
                return
            
            # فعال کردن وام مخفی فقط برای این کاربر
            secret_loan_activated[user_id] = True
            save_secret_loan_activated()
            
            response = f"🏦 <b>واو! شما کلیدواژه مخفی را پیدا کردید!</b>\n\n"
            response += f"🎭 <b>وام مخفی جی‌پی مورگان برای شما فعال شد!</b>\n\n"
            response += f"💰 <b>مشخصات وام:</b>\n"
            response += f"▫️ مبلغ: 1 میلیارد دلار\n"
            response += f"▫️ سود: 0% (بدون سود)\n"
            response += f"▫️ مهلت پرداخت: 24 دور\n"
            response += f"▫️ مبلغ کل: 1 میلیارد دلار\n\n"
            response += "💡 <b>برای دریافت وام:</b>\n"
            response += "▫️ به منوی وام‌ها بروید\n"
            response += "▫️ روی 'وام مخفی جی‌پی مورگان' کلیک کنید\n"
            response += "▫️ دکمه 'دریافت وام مخفی' را بزنید\n\n"
            response += "🎉 تبریک! شما یکی از معدود افرادی هستید که این وام مخفی را پیدا کرده‌اند!"
            
            await update.message.reply_text(response, parse_mode='HTML')
            
            # ارسال پیام به کانال اصلی
            try:
                from telegram import Bot
                bot = Bot(token='7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I')
                channel_message = f"🎉 <b>ایونت مخفی کشف شد!</b>\n\n"
                channel_message += f"🏆 بازیکن {country_name} توانست کلیدواژه مخفی بازی را پیدا کند!\n\n"
                channel_message += f"🎭 وام مخفی جی‌پی مورگان برای این بازیکن فعال شد!\n\n"
                channel_message += f"🔍 کلیدواژه مخفی: {keyword}\n\n"
                channel_message += "🎯 سایر بازیکنان می‌توانند با جی پی مورگان چت کنند تا شاید کلیدواژه‌های دیگری پیدا کنند!"
                
                await bot.send_photo(
                    chat_id=NEWS_CHANNEL_ID, 
                    photo="https://t.me/TextEmpire_IR/75",
                    caption=channel_message, 
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"خطا در ارسال پیام به کانال: {e}")
            
            return
    
    # بررسی کلیدواژه‌های مخفی اقتصاد
    for keyword in economy_secret_keywords:
        if keyword in message_text:
            # بررسی اینکه آیا قبلاً کسی جایزه مخفی اقتصاد گرفته
            if economy_secret_claimed:
                await update.message.reply_text("❌ متأسفانه این جایزه مخفی قبلاً توسط شخص دیگری دریافت شده است.")
                return
            
            # اعطای جایزه مخفی اقتصاد
            reward_amount = 200000000  # 200 میلیون
            current_turn = utils.game_data['turn']
            
            # اضافه کردن پول به کاربر
            if user_id in utils.users:
                if 'resources' not in utils.users[user_id]:
                    utils.users[user_id]['resources'] = {}
                if 'cash' not in utils.users[user_id]['resources']:
                    utils.users[user_id]['resources']['cash'] = 0
                
                utils.users[user_id]['resources']['cash'] += reward_amount
            
            # علامت‌گذاری جایزه مخفی اقتصاد به عنوان دریافت شده
            economy_secret_claimed = True
            save_economy_secret_claimed()
            
            # ذخیره تغییرات
            save_users()
            
            response = f"🏦 <b>واو! شما کلیدواژه مخفی اقتصاد را پیدا کردید!</b>\n\n"
            response += f"💰 <b>جایزه مخفی اعطا شد:</b>\n"
            response += f"▫️ مبلغ: {format_price_short(reward_amount)}\n"
            response += f"▫️ نوع: جایزه نقدی\n"
            response += f"▫️ وضعیت: واریز به حساب بانکی\n\n"
            response += "🎉 تبریک! شما یکی از معدود افرادی هستید که این جایزه مخفی را دریافت کرده‌اند!"
            
            await update.message.reply_text(response, parse_mode='HTML')
            
            # ارسال پیام به کانال اصلی
            try:
                from telegram import Bot
                bot = Bot(token='7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I')
                channel_message = f"🎉 <b>ایونت مخفی اقتصاد کشف شد!</b>\n\n"
                channel_message += f"🏆 بازیکن {country_name} توانست ایونت مخفی اقتصاد را پیدا کند!\n\n"
                channel_message += f"💰 این بازیکن صاحب 200 میلیون پول نقد شد\n\n"
                channel_message += f"🔍 کلیدواژه مخفی: {keyword}\n\n"
                channel_message += "🎯 سایر بازیکنان می‌توانند با جی پی مورگان چت کنند تا شاید کلیدواژه‌های دیگری پیدا کنند!"
                
                await bot.send_photo(
                    chat_id=NEWS_CHANNEL_ID, 
                    photo="https://t.me/TextEmpire_IR/76", 
                    caption=channel_message, 
                    parse_mode='HTML'
                )
            except Exception as e:
                print(f"خطا در ارسال پیام به کانال: {e}")
            
            return
    
    # کلیدواژه‌های مربوط به وام‌ها (گسترش یافته)
    loan_keywords = [
        'وام', 'loan', 'قرض', 'وام ها', 'وامها', 'وام‌ها', 'قرضه', 'قرضه ها',
        'وام استقلال', 'وام توسعه', 'وام اضطراری', 'وام مخفی',
        'میخوام درمورد وام ها صحبت کنیم', 'درمورد وام ها', 'وام ها چیه',
        'وام گرفتم', 'وام دارم', 'وامم چقدره', 'وامم چقدر است',
        'وام های من', 'وام‌های من', 'وام هایم', 'وام‌هایم',
        'تحلیل وام', 'تحلیل وام ها', 'تحلیل وام‌ها', 'تحلیل وام هایم'
    ]
    
    # کلیدواژه‌های مربوط به حساب بانکی
    account_keywords = [
        'حساب', 'account', 'بانک', 'حساب بانکی', 'حسابم', 'حساب من',
        'موجودی', 'موجودی حساب', 'موجودی حسابم', 'موجودی من',
        'پول', 'پولم', 'پول من', 'پول حسابم', 'پول حساب من',
        'تحلیل حساب', 'تحلیل حساب بانکی', 'تحلیل حسابم', 'تحلیل حساب من'
    ]
    
    # کلیدواژه‌های مربوط به بدهی‌ها
    debt_keywords = [
        'بدهی', 'debt', 'معوق', 'بدهی ها', 'بدهی‌ها', 'بدهی هایم', 'بدهی‌هایم',
        'بدهی معوق', 'بدهی های معوق', 'بدهی‌های معوق', 'بدهی معوق من',
        'بدهی دارم', 'بدهی ندارم', 'بدهی های من', 'بدهی‌های من',
        'قرض دارم', 'قرض ندارم', 'قرض های من', 'قرض‌های من',
        'وام دارم', 'وام ندارم', 'وام های من', 'وام‌های من'
    ]
    
    # کلیدواژه‌های مربوط به انتقال پول
    transfer_keywords = [
        'انتقال', 'transfer', 'انتقال پول', 'انتقال وجه', 'انتقال وجهی',
        'پول بفرست', 'پول بفرستم', 'پول بفرستید', 'پول بفرستیم',
        'حواله', 'حواله پول', 'حواله وجه', 'حواله وجهی',
        'به حساب', 'به حساب دیگر', 'به حساب کس دیگه', 'به حساب شخص دیگه'
    ]
    
    # کلیدواژه‌های مربوط به واریز و برداشت
    deposit_withdraw_keywords = [
        'واریز', 'deposit', 'واریز پول', 'واریز وجه', 'پول واریز کن',
        'برداشت', 'withdraw', 'برداشت پول', 'برداشت وجه', 'پول برداشت کن',
        'پول بذار', 'پول بذارم', 'پول بذارید', 'پول بذاریم',
        'پول بردار', 'پول بردارم', 'پول بردارید', 'پول برداریم'
    ]
    
    # کلیدواژه‌های مربوط به تاریخچه تراکنش‌ها
    history_keywords = [
        'تاریخچه', 'history', 'تاریخچه تراکنش', 'تاریخچه تراکنش ها',
        'تراکنش', 'تراکنش ها', 'تراکنش‌ها', 'تراکنش هایم', 'تراکنش‌هایم',
        'لیست تراکنش', 'لیست تراکنش ها', 'لیست تراکنش‌ها',
        'چه تراکنش هایی داشتم', 'چه تراکنش هایی کردم'
    ]
    
    # کلیدواژه‌های مربوط به سلام و احوالپرسی
    greeting_keywords = [
        'سلام', 'hi', 'hello', 'درود', 'سلام علیک', 'سلام علیکم',
        'خوبی', 'خوبی؟', 'حالت چطوره', 'حالت چطوره؟', 'حال شما چطوره',
        'خوب هستی', 'خوب هستی؟', 'خوبی؟', 'خوبی؟؟', 'خوبی؟؟؟'
    ]
    
    # کلیدواژه‌های مربوط به تشکر
    thanks_keywords = [
        'ممنون', 'thanks', 'thank you', 'تشکر', 'تشکر میکنم', 'تشکر می‌کنم',
        'مرسی', 'merci', 'متشکرم', 'متشکر', 'متشکر از شما',
        'دستت درد نکنه', 'دست شما درد نکنه', 'دستت درد نکنه'
    ]
    
    # کلیدواژه‌های مربوط به خداحافظی
    goodbye_keywords = [
        'خداحافظ', 'bye', 'goodbye', 'بای', 'خداحافظی', 'خداحافظی می‌کنم',
        'خداحافظی می‌کنم', 'خداحافظی می‌کنم', 'خداحافظی می‌کنم'
    ]
    
    # بررسی کلیدواژه‌ها و پاسخ مناسب
    if any(keyword in message_text for keyword in loan_keywords):
        # تحلیل وام‌ها
        try:
            from analysis import generate_loan_analysis
            analysis = generate_loan_analysis(user_id)
            response = f"💰 <b>تحلیل وام‌های شما:</b>\n\n{analysis}"
        except ImportError:
            # اگر ماژول analysis موجود نباشد، تحلیل ساده ارائه می‌دهیم
            user_loans = utils.independence_loans.get(user_id, {})
            if user_loans:
                response = f"💰 <b>وام‌های شما:</b>\n\n"
                response += f"▫️ نوع وام: {user_loans.get('loan_type', 'نامشخص')}\n"
                response += f"▫️ مبلغ: {format_price_short(user_loans.get('amount', 0))}\n"
                response += f"▫️ سود: {user_loans.get('interest_rate', 0) * 100}%\n"
                response += f"▫️ مهلت پرداخت: دور {user_loans.get('due_turn', 0)}\n"
            else:
                response = "💰 شما هیچ وام فعالی ندارید."
    
    elif any(keyword in message_text for keyword in account_keywords):
        # تحلیل حساب بانکی
        try:
            from analysis import generate_bank_analysis
            analysis = generate_bank_analysis(user_id)
            response = f"🏦 <b>تحلیل حساب بانکی شما:</b>\n\n{analysis}"
        except ImportError:
            # تحلیل ساده حساب بانکی
            user = utils.users.get(user_id, {})
            cash = user.get('resources', {}).get('cash', 0)
            response = f"🏦 <b>حساب بانکی شما:</b>\n\n"
            response += f"▫️ موجودی: {format_price_short(cash)}\n"
            response += f"▫️ کشور: {user.get('country', 'نامشخص')}\n"
    
    elif any(keyword in message_text for keyword in debt_keywords):
        # بررسی بدهی‌های معوق
        overdue_debts = utils.overdue_debts.get(user_id, {})
        if overdue_debts:
            response = "⚠️ <b>بدهی‌های معوق شما:</b>\n\n"
            for debt_type, debt_data in overdue_debts.items():
                response += f"▫️ {debt_type}: {format_price_short(debt_data['remaining_debt'])}\n"
        else:
            response = "✅ شما هیچ بدهی معوقی ندارید."
    
    elif any(keyword in message_text for keyword in transfer_keywords):
        response = "💸 <b>انتقال پول:</b>\n\nبرای انتقال پول، لطفاً از منوی اصلی بانک استفاده کنید."
    
    elif any(keyword in message_text for keyword in deposit_withdraw_keywords):
        response = "🏦 <b>واریز و برداشت:</b>\n\nبرای واریز یا برداشت پول، لطفاً از منوی اصلی بانک استفاده کنید."
    
    elif any(keyword in message_text for keyword in history_keywords):
        response = "📋 <b>تاریخچه تراکنش‌ها:</b>\n\nبرای مشاهده تاریخچه تراکنش‌ها، لطفاً از منوی اصلی بانک استفاده کنید."
    
    elif any(keyword in message_text for keyword in greeting_keywords):
        response = f"👋 سلام! من جی پی مورگان هستم. چطور می‌تونم کمکتون کنم؟\n\n"
        response += "می‌تونید در مورد:\n"
        response += "• وام‌ها و تحلیل آن‌ها\n"
        response += "• حساب بانکی و موجودی\n"
        response += "• بدهی‌های معوق\n"
        response += "• و سایر خدمات بانکی سوال کنید."
    
    elif any(keyword in message_text for keyword in thanks_keywords):
        response = "🙏 خواهش می‌کنم! خوشحالم که می‌تونم کمکتون کنم. اگر سوال دیگری دارید، در خدمت هستم."
    
    elif any(keyword in message_text for keyword in goodbye_keywords):
        response = "👋 خداحافظ! امیدوارم خدمات ما رضایت شما را جلب کرده باشد. هر وقت خواستید، در خدمت هستیم."
    
    else:
        response = "💬 متأسفانه متوجه منظور شما نشدم. لطفاً واضح‌تر توضیح دهید.\n\n"
        response += "می‌تونید در مورد:\n"
        response += "• وام‌ها و تحلیل آن‌ها\n"
        response += "• حساب بانکی و موجودی\n"
        response += "• بدهی‌های معوق\n"
        response += "• و سایر خدمات بانکی سوال کنید."
    
    await update.message.reply_text(response, parse_mode='HTML')

async def show_loans_menu(query):
    """نمایش منوی وام‌ها"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return
    
    text = "💰 <b>منوی وام‌ها</b>\n\n"
    text += "به بخش وام‌های بانک بین‌المللی خوش آمدید!\n\n"
    text += "💡 <b>انواع وام‌های موجود:</b>\n"
    text += "▫️ وام استقلال - برای کشورهای مستقل\n"
    text += "▫️ وام توسعه - برای پیشرفت اقتصادی\n"
    text += "▫️ وام اضطراری - برای شرایط بحرانی\n"
    text += "▫️ وام مخفی جی‌پی مورگان - ایونت ویژه\n\n"
    text += "📋 <b>وضعیت وام‌های شما:</b>\n"
    
    # بررسی وام‌های فعال کاربر
    active_loans = []
    if user_id in independence_loans:
        loan_data = independence_loans[user_id]
        loan_type = loan_data.get('loan_type', 'نامشخص')
        
        current_turn = game_data['turn']
        remaining_turns = loan_data['due_turn'] - current_turn
        loan_names = {
            'independence': 'وام استقلال',
            'development': 'وام توسعه',
            'emergency': 'وام اضطراری',
            'secret': 'وام مخفی جی‌پی مورگان'
        }
        loan_name = loan_names.get(loan_type, 'وام')
        active_loans.append(f"▫️ {loan_name}: {format_price_short(loan_data['amount'])} ({remaining_turns} دور باقی)")
    
    if active_loans:
        text += "\n".join(active_loans)
    else:
        text += "▫️ هیچ وام فعالی ندارید"
    
    keyboard = [
        [InlineKeyboardButton('وام استقلال 💰', callback_data='independence_loan')],
        [InlineKeyboardButton('وام توسعه 🏗️', callback_data='development_loan')],
        [InlineKeyboardButton('وام اضطراری 🚨', callback_data='emergency_loan')]
    ]
    
    # فقط اگر وام مخفی برای کاربر فعال شده، دکمه نمایش بده
    if secret_loan_activated and secret_loan_activated.get(user_id, False):
        keyboard.append([InlineKeyboardButton('وام مخفی جی‌پی مورگان 🎭', callback_data='secret_loan')])
    
    keyboard.extend([
        [InlineKeyboardButton('وضعیت وام‌های من 📋', callback_data='my_loans')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_loan_info(query, loan_type):
    """نمایش اطلاعات وام"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return
    
    loan_config = bank_data['loan_types'].get(loan_type)
    if not loan_config:
        await query.edit_message_text('نوع وام نامعتبر است.')
        return
    
    # بررسی وضعیت کاربر
    can_get, message = can_user_get_loan(user_id, loan_type)
    has_active_loan = user_id in independence_loans
    current_uses = get_user_loan_count(user_id, loan_type)
    
    loan_names = {
        'independence': 'وام استقلال',
        'development': 'وام توسعه',
        'emergency': 'وام اضطراری'
    }
    
    if loan_type == 'independence':
        text = f"💰 <b>{loan_names[loan_type]}</b>\n\n"
        text += f"📋 <b>شرایط وام:</b>\n"
        text += f"▫️ مبلغ: 1b\n"
        text += f"▫️ مهلت پرداخت: {loan_config['duration']} دور\n"
        text += f"▫️ سود: {loan_config['interest_rate'] * 100}%\n"
        text += f"▫️ حداکثر استفاده: {loan_config['max_uses']} بار\n"
        text += f"▫️ استفاده‌های قبلی: {current_uses}/{loan_config['max_uses']}\n\n"
    else:
        text = f"💰 <b>{loan_names[loan_type]}</b>\n\n"
        text += f"📋 <b>شرایط وام:</b>\n"
        text += f"▫️ مبلغ: {format_price_short(loan_config['amount'])}\n"
        text += f"▫️ مهلت پرداخت: {loan_config['duration']} دور\n"
        text += f"▫️ سود: {loan_config['interest_rate'] * 100}%\n"
        text += f"▫️ حداکثر استفاده: {loan_config['max_uses']} بار\n"
        text += f"▫️ استفاده‌های قبلی: {current_uses}/{loan_config['max_uses']}\n\n"
    
    if has_active_loan:
        loan_data = independence_loans[user_id]
        current_turn = game_data['turn']
        remaining_turns = loan_data['due_turn'] - current_turn
        
        text += "📊 <b>وضعیت وام فعلی:</b>\n"
        text += f"▫️ مبلغ وام: {format_price_short(loan_data['amount'])}\n"
        text += f"▫️ مهلت پرداخت: {remaining_turns} دور باقی مانده\n"
        text += f"▫️ مبلغ کل: {format_price_short(loan_data['amount'] + int(loan_data['amount'] * loan_data['interest_rate']))}\n\n"
        
        if remaining_turns <= 0:
            text += "⚠️ مهلت پرداخت شما تمام شده است!"
        else:
            text += "✅ وام شما فعال است."
    elif can_get:
        if loan_type == 'independence':
            text += "✅ شما شرایط دریافت این وام را دارید.\n\n"
            text += "❌ این وام فقط برای کشورهای آزاد شده در دسترس است"
        else:
            text += "✅ شما شرایط دریافت این وام را دارید."
    else:
        if loan_type == 'independence':
            text += f"❌ {message}\n\n"
            text += "❌ این وام فقط برای کشورهای آزاد شده در دسترس است"
        else:
            text += f"❌ {message}"
    
    keyboard = []
    if can_get and not has_active_loan:
        keyboard.append([InlineKeyboardButton(f'دریافت {loan_names[loan_type]} 💰', callback_data=f'request_{loan_type}_loan')])
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_independence_loan_info(query):
    """نمایش اطلاعات وام استقلال"""
    await show_loan_info(query, 'independence')

async def show_development_loan_info(query):
    """نمایش اطلاعات وام توسعه"""
    await show_loan_info(query, 'development')

async def show_emergency_loan_info(query):
    """نمایش اطلاعات وام اضطراری"""
    await show_loan_info(query, 'emergency')

async def show_secret_loan_info(query):
    """نمایش اطلاعات وام مخفی جی‌پی مورگان"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return
    
    text = "🎭 <b>وام مخفی جی‌پی مورگان</b>\n\n"
    text += "🔐 <b>این وام ویژه است!</b>\n\n"
    text += "📋 <b>شرایط وام:</b>\n"
    text += "▫️ مبلغ: 1 میلیارد دلار\n"
    text += "▫️ مهلت پرداخت: 24 دور\n"
    text += "▫️ سود: 0% (بدون سود)\n"
    text += "▫️ حداکثر استفاده: 1 بار\n"
    text += "▫️ استفاده‌های قبلی: 0/1\n\n"
    
    # بررسی اینکه آیا قبلاً کسی وام مخفی گرفته
    if secret_loan_claimed:
        text += "❌ این وام مخفی قبلاً توسط شخص دیگری دریافت شده است.\n\n"
        text += "💡 <b>نکته:</b> این وام فقط یک بار در کل بازی قابل دریافت است."
    else:
        # بررسی اینکه آیا کسی کلیدواژه گفته و وام فعال کرده
        if secret_loan_activated:
            # بررسی اینکه آیا وام مخفی برای این کاربر فعال شده
            is_activated = secret_loan_activated.get(user_id, False)
            
            if not is_activated:
                text += "🔒 این وام مخفی قبلاً توسط شخص دیگری فعال شده است.\n\n"
                text += "💡 <b>نکته:</b> این وام فقط برای اولین کسی که کلیدواژه مخفی را پیدا کند فعال می‌شود."
            else:
                # بررسی اینکه آیا کاربر وام مخفی فعال دارد
                has_secret_loan = False
                if user_id in independence_loans:
                    loan_data = independence_loans[user_id]
                    if loan_data.get('loan_type') == 'secret':
                        has_secret_loan = True
                
                if has_secret_loan:
                    text += "✅ شما این وام مخفی را قبلاً دریافت کرده‌اید.\n\n"
                    text += "💡 <b>نکته:</b> این وام فقط یک بار قابل دریافت است."
                else:
                    text += "✅ شما شرایط دریافت این وام را دارید.\n\n"
                    text += "💡 <b>نکته:</b> این وام فقط یک بار در کل بازی قابل دریافت است."
        else:
            text += "🔒 این وام مخفی هنوز فعال نشده است.\n\n"
            text += "💡 <b>نکته:</b> برای فعال‌سازی این وام، باید کلیدواژه مخفی را پیدا کنید."
    
    keyboard = []
    if not secret_loan_claimed and secret_loan_activated.get(user_id, False) and not has_secret_loan:
        keyboard.append([InlineKeyboardButton('دریافت وام مخفی جی‌پی مورگان 🎭', callback_data='request_secret_loan')])
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def request_loan(query, loan_type):
    """درخواست وام"""
    user_id = str(query.from_user.id)
    
    success, message = grant_loan(user_id, loan_type)
    
    if success:
        loan_names = {
            'independence': 'وام استقلال',
            'development': 'وام توسعه',
            'emergency': 'وام اضطراری'
        }
        
        text = f"✅ <b>{loan_names[loan_type]} اعطا شد!</b>\n\n"
        text += f"مبلغ وام: {format_price_short(bank_data['loan_types'][loan_type]['amount'])}\n"
        text += f"مهلت پرداخت: {bank_data['loan_types'][loan_type]['duration']} دور\n"
        text += f"سود: {bank_data['loan_types'][loan_type]['interest_rate'] * 100}%\n\n"
        text += "💡 <b>نکات مهم:</b>\n"
        text += "▫️ اگر زودتر از موعد پرداخت کنید، سود بخشوده می‌شود\n"
        text += "▫️ اگر تا موعد پرداخت نکنید، پول به صورت خودکار کسر می‌شود\n"
        text += "▫️ این وام محدودیت تعداد استفاده دارد\n"
        text += "▫️ وام مخفی: فقط یک نفر در کل بازی می‌تواند دریافت کند"
    else:
        text = f"❌ <b>خطا در اعطای وام</b>\n\n{message}"
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def request_independence_loan(query):
    """درخواست وام استقلال"""
    await request_loan(query, 'independence')

async def request_development_loan(query):
    """درخواست وام توسعه"""
    await request_loan(query, 'development')

async def request_emergency_loan(query):
    """درخواست وام اضطراری"""
    await request_loan(query, 'emergency')

async def request_secret_loan(query):
    """درخواست وام مخفی جی‌پی مورگان"""
    await request_loan(query, 'secret')

async def show_my_loans(query):
    """نمایش وام‌های کاربر"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return
    
    country_name = user.get('country', 'کشور ناشناس')
    
    # پیام خوشامدگویی از جی پی مورگان
    text = "📋 <b>خوش آمدید!</b>\n\n"
    text += "🏦 من جی پی مورگان، مدیر ارشد بانک بین‌المللی هستم.\n"
    text += f"📋 <b>وضعیت وام‌های کشور {country_name}</b>\n\n"
    
    # مقداردهی اولیه keyboard
    keyboard = []
    
    # وام فعال
    if user_id in independence_loans:
        loan_data = independence_loans[user_id]
        current_turn = game_data['turn']
        remaining_turns = loan_data['due_turn'] - current_turn
        loan_type = loan_data.get('loan_type', 'نامشخص')
        
        text += "💰 <b>وام فعال:</b>\n"
        loan_names = {
            'independence': 'وام استقلال',
            'development': 'وام توسعه',
            'emergency': 'وام اضطراری',
            'secret': 'وام مخفی جی‌پی مورگان'
        }
        loan_name = loan_names.get(loan_type, loan_type)
        text += f"▫️ نوع: {loan_name}\n"
        text += f"▫️ مبلغ: {format_price_short(loan_data['amount'])}\n"
        text += f"▫️ مهلت پرداخت: {remaining_turns} دور باقی مانده\n"
        text += f"▫️ مبلغ کل: {format_price_short(loan_data['amount'] + int(loan_data['amount'] * loan_data['interest_rate']))}\n\n"
        
        if remaining_turns <= 0:
            text += "⚠️ مهلت پرداخت شما تمام شده است!\n\n"
        
        # دکمه‌های پرداخت برای همه وام‌ها (شامل وام مخفی)
        keyboard.append([InlineKeyboardButton('💳 پرداخت زودهنگام (بخشودگی سود)', callback_data='pay_loan_early')])
    else:
        text += "✅ شما وام فعالی ندارید.\n\n"
    
    # بدهی‌های معوق
    if user_id in overdue_debts:
        debt_data = overdue_debts[user_id]
        text += "⚠️ <b>بدهی معوق:</b>\n"
        text += f"▫️ مبلغ باقی‌مانده: {format_price_short(debt_data['remaining_debt'])}\n"
        text += f"▫️ جریمه دیرکرد: {format_price_short(debt_data['late_fees'])}\n"
        text += f"▫️ معوق از: دور {debt_data['overdue_since']}\n\n"
        
        # اضافه کردن دکمه بدهی‌های معوق
        keyboard.append([InlineKeyboardButton('بدهی‌های معوق ⚠️', callback_data='overdue_debts')])
    
    # تاریخچه وام‌ها
    user_history = loan_history.get(user_id, {})
    if user_history:
        text += "📊 <b>تاریخچه وام‌ها:</b>\n"
        for loan_type, count in user_history.items():
            loan_names = {
                'independence': 'وام استقلال',
                'development': 'وام توسعه',
                'emergency': 'وام اضطراری',
                'installment': 'وام اقساطی',
                'secret': 'وام مخفی جی‌پی مورگان'
            }
            text += f"▫️ {loan_names.get(loan_type, loan_type)}: {count} بار\n"
    else:
        text += "📊 <b>تاریخچه وام‌ها:</b>\n"
        text += "▫️ هیچ وامی دریافت نکرده‌اید\n"
    
    # تحلیل هوشمند وام‌ها
    from analysis import generate_loan_analysis
    analysis = generate_loan_analysis(user_id)
    
    text += f"\n<b>پیشنهاد جی پی مورگان:</b>\n<blockquote>{analysis}</blockquote>"
    
    # اگر keyboard خالی است، دکمه بازگشت اضافه کن
    if not keyboard:
        keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')])
    else:
        keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def pay_loan_early(query):
    """پرداخت زودهنگام وام با بخشودگی سود"""
    user_id = str(query.from_user.id)
    
    if user_id not in independence_loans:
        await query.edit_message_text('شما وام فعالی ندارید!')
        return
    
    loan_data = independence_loans[user_id]
    loan_type = loan_data.get('loan_type', 'نامشخص')
    
    # وام مخفی قابل پرداخت نیست
    if loan_type == 'secret':
        await query.edit_message_text('وام مخفی جی پی مورگان قابل پرداخت زودهنگام نیست!')
        return
    
    loan_amount = loan_data['amount']
    interest_amount = int(loan_amount * loan_data['interest_rate'])
    total_amount = loan_amount + interest_amount
    
    # فقط اصل وام را پرداخت می‌کند (سود بخشوده می‌شود)
    user = utils.users[user_id]
    user_cash = user.get('resources', {}).get('cash', 0)
    
    if user_cash >= loan_amount:
        # کسر فقط اصل وام
        user['resources']['cash'] = user_cash - loan_amount
        bank_data['bank_reserves'] += loan_amount
        bank_data['total_loans_paid'] += 1
        
        # ثبت در تاریخچه
        if user_id not in loan_history:
            loan_history[user_id] = {}
        loan_history[user_id][loan_data['loan_type']] = loan_history[user_id].get(loan_data['loan_type'], 0) + 1
        
        # حذف وام
        del independence_loans[user_id]
        
        # ذخیره تغییرات
        save_users()
        save_active_loans()
        save_bank_data()
        save_loan_history()
        
        text = f"✅ <b>وام شما با موفقیت پرداخت شد!</b>\n\n"
        text += f"مبلغ پرداختی: {format_price_short(loan_amount)}\n"
        text += f"سود بخشوده شده: {format_price_short(interest_amount)}\n"
        text += f"کل صرفه‌جویی: {format_price_short(interest_amount)}\n\n"
        text += "🎉 به دلیل پرداخت زودهنگام، سود وام بخشوده شد!"
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        text = f"❌ <b>موجودی ناکافی!</b>\n\n"
        text += f"موجودی شما: {format_price_short(user_cash)}\n"
        text += f"مبلغ مورد نیاز: {format_price_short(loan_amount)}\n"
        text += f"کمبود: {format_price_short(loan_amount - user_cash)}"
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='my_loans')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_overdue_debts_menu(query):
    """نمایش منوی بدهی‌های معوق"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return
    
    if user_id not in overdue_debts:
        text = "✅ <b>بدهی معوقی ندارید!</b>\n\n"
        text += "شما هیچ بدهی معوقی ندارید. می‌توانید از خدمات بانک استفاده کنید."
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    debt_data = overdue_debts[user_id]
    loan_names = {
        'independence': 'وام استقلال',
        'development': 'وام توسعه',
        'emergency': 'وام اضطراری'
    }
    loan_name = loan_names.get(debt_data['loan_type'], 'وام')
    
    text = "⚠️ <b>بدهی‌های معوق شما</b>\n\n"
    text += f"📋 <b>نوع وام:</b> {loan_name}\n"
    text += f"💰 <b>مبلغ اصلی:</b> {format_price_short(debt_data['original_amount'])}\n"
    text += f"💸 <b>بدهی باقی‌مانده:</b> {format_price_short(debt_data['remaining_debt'])}\n"
    text += f"💳 <b>جریمه دیرکرد:</b> {format_price_short(debt_data['late_fees'])}\n"
    text += f"📅 <b>تاریخ سررسید:</b> دور {debt_data['due_turn']}\n"
    text += f"⏰ <b>معوق از:</b> دور {debt_data['overdue_since']}\n\n"
    
    # محاسبه 10% پرداخت اقساطی
    installment_amount = int(debt_data['remaining_debt'] * 0.1)
    
    text += "💡 <b>گزینه‌های پرداخت:</b>\n"
    text += f"▫️ پرداخت اقساطی (10%): {format_price_short(installment_amount)}\n"
    text += f"▫️ پرداخت کامل: {format_price_short(debt_data['remaining_debt'])}\n\n"
    
    text += "⚠️ <b>هشدار:</b> هر دور 5% جریمه دیرکرد اضافه می‌شود!\n\n"
    
    keyboard = [
        [InlineKeyboardButton('پرداخت اقساطی (10%)', callback_data='pay_installment')],
        [InlineKeyboardButton('پرداخت کامل', callback_data='pay_full_debt')],
        [InlineKeyboardButton('درخواست وام اقساطی (112% سود)', callback_data='request_installment_loan')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def pay_installment(query):
    """پرداخت اقساطی بدهی معوق"""
    user_id = str(query.from_user.id)
    
    if user_id not in overdue_debts:
        await query.edit_message_text('شما بدهی معوقی ندارید!')
        return
    
    debt_data = overdue_debts[user_id]
    installment_amount = int(debt_data['remaining_debt'] * 0.1)
    
    user = utils.users[user_id]
    user_cash = user.get('resources', {}).get('cash', 0)
    
    if user_cash >= installment_amount:
        # پرداخت اقساطی
        user['resources']['cash'] = user_cash - installment_amount
        bank_data['bank_reserves'] += installment_amount
        debt_data['remaining_debt'] -= installment_amount
        
        # ثبت پرداخت اقساطی
        if 'installment_payments' not in debt_data:
            debt_data['installment_payments'] = []
        debt_data['installment_payments'].append({
            'amount': installment_amount,
            'turn': game_data['turn'],
            'remaining_after': debt_data['remaining_debt']
        })
        
        # ثبت آخرین پرداخت برای آزادسازی موقت خدمات
        debt_data['last_payment_turn'] = game_data['turn']
        
        # اگر بدهی تمام شد
        if debt_data['remaining_debt'] <= 0:
            del overdue_debts[user_id]
            text = f"✅ <b>بدهی شما کاملاً پرداخت شد!</b>\n\n"
            text += f"آخرین پرداخت: {format_price_short(installment_amount)}\n"
            text += "🎉 تمام خدمات بانکی برای شما فعال شد!"
        else:
            text = f"✅ <b>پرداخت اقساطی موفقیت‌آمیز</b>\n\n"
            text += f"مبلغ پرداختی: {format_price_short(installment_amount)}\n"
            text += f"بدهی باقی‌مانده: {format_price_short(debt_data['remaining_debt'])}\n"
            text += f"تاریخ پرداخت: دور {game_data['turn']}\n\n"
            text += "🎉 <b>برای این دور، خدمات بانکی آزاد شد!</b>\n"
            text += "💡 می‌توانید انتقال و شارژ انجام دهید.\n"
            text += "⚠️ برای دور بعدی، 5% جریمه دیرکرد اضافه خواهد شد."
        
        # ذخیره تغییرات
        save_users()
        save_bank_data()
        save_overdue_debts()
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='overdue_debts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        text = f"❌ <b>موجودی ناکافی!</b>\n\n"
        text += f"موجودی شما: {format_price_short(user_cash)}\n"
        text += f"مبلغ مورد نیاز: {format_price_short(installment_amount)}\n"
        text += f"کمبود: {format_price_short(installment_amount - user_cash)}"
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='overdue_debts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def pay_full_debt(query):
    """پرداخت کامل بدهی معوق"""
    user_id = str(query.from_user.id)
    
    if user_id not in overdue_debts:
        await query.edit_message_text('شما بدهی معوقی ندارید!')
        return
    
    debt_data = overdue_debts[user_id]
    total_amount = debt_data['remaining_debt']
    
    user = utils.users[user_id]
    user_cash = user.get('resources', {}).get('cash', 0)
    
    if user_cash >= total_amount:
        # پرداخت کامل
        user['resources']['cash'] = user_cash - total_amount
        bank_data['bank_reserves'] += total_amount
        bank_data['total_loans_paid'] += 1
        
        # ثبت در تاریخچه
        if user_id not in loan_history:
            loan_history[user_id] = {}
        loan_history[user_id][debt_data['loan_type']] = loan_history[user_id].get(debt_data['loan_type'], 0) + 1
        
        # حذف بدهی معوق
        del overdue_debts[user_id]
        
        # ذخیره تغییرات
        save_users()
        save_bank_data()
        save_loan_history()
        save_overdue_debts()
        
        text = f"✅ <b>بدهی شما کاملاً پرداخت شد!</b>\n\n"
        text += f"مبلغ پرداختی: {format_price_short(total_amount)}\n"
        text += "🎉 بدهی معوق شما تسویه شد!"
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        text = f"❌ <b>موجودی ناکافی!</b>\n\n"
        text += f"موجودی شما: {format_price_short(user_cash)}\n"
        text += f"مبلغ مورد نیاز: {format_price_short(total_amount)}\n"
        text += f"کمبود: {format_price_short(total_amount - user_cash)}"
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='overdue_debts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def request_installment_loan(query):
    """درخواست وام اقساطی با سود 112%"""
    user_id = str(query.from_user.id)
    
    if user_id not in overdue_debts:
        await query.edit_message_text('شما بدهی معوقی ندارید!')
        return
    
    debt_data = overdue_debts[user_id]
    loan_amount = debt_data['remaining_debt']
    interest_amount = int(loan_amount * 1.12)  # 112% سود
    total_amount = loan_amount + interest_amount
    
    # بررسی موجودی بانک
    if bank_data['bank_reserves'] < loan_amount:
        text = "❌ <b>موجودی بانک کافی نیست!</b>\n\n"
        text += "بانک در حال حاضر قادر به اعطای وام اقساطی نیست."
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='overdue_debts')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    # اعطای وام اقساطی
    user = utils.users[user_id]
    user['resources']['cash'] = user['resources'].get('cash', 0) + loan_amount
    bank_data['bank_reserves'] -= loan_amount
    
    # حذف بدهی معوق و ایجاد وام جدید
    del overdue_debts[user_id]
    
    # ایجاد وام اقساطی جدید
    current_turn = game_data['turn']
    installment_loan = {
        'amount': total_amount,
        'start_turn': current_turn,
        'due_turn': current_turn + 6,  # 6 دور مهلت
        'interest_rate': 1.12,  # 112% سود
        'loan_type': 'installment',
        'paid': False
    }
    independence_loans[user_id] = installment_loan
    
    # ذخیره تغییرات
    save_users()
    save_bank_data()
    save_overdue_debts()
    save_independence_loans()
    
    text = f"✅ <b>وام اقساطی اعطا شد!</b>\n\n"
    text += f"مبلغ وام: {format_price_short(loan_amount)}\n"
    text += f"سود (112%): {format_price_short(interest_amount)}\n"
    text += f"کل مبلغ قابل پرداخت: {format_price_short(total_amount)}\n"
    text += f"مهلت پرداخت: 6 دور\n\n"
    text += "💡 بدهی معوق شما تسویه شد و وام اقساطی جدید دریافت کردید."
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

# --- توابع حساب بانکی ---
async def show_bank_account_menu(query):
    """نمایش منوی حساب بانکی"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return
    
    # ایجاد حساب بانکی اگر وجود نداشته باشد
    account_number = create_bank_account(user_id)
    account = bank_accounts[user_id]
    
    # بررسی بدهی معوق و وضعیت پرداخت
    has_overdue_debt = user_id in overdue_debts
    services_temporarily_unlocked = False
    
    if has_overdue_debt:
        debt_data = overdue_debts[user_id]
        # بررسی اینکه آیا در این دور پرداخت کرده یا نه
        if 'last_payment_turn' in debt_data and debt_data['last_payment_turn'] == game_data['turn']:
            services_temporarily_unlocked = True
    
    text = "💳 <b>حساب بانکی شما</b>\n\n"
    text += f"🏦 <b>بانک بین‌المللی</b>\n"
    text += f"📋 شماره حساب: <code>{account_number}</code>\n"
    text += f"💰 موجودی: {format_price_short(account['balance'])}\n"
    text += f"📅 تاریخ افتتاح: {time.strftime('%Y/%m/%d', time.localtime(account['created_at']))}\n\n"
    
    if has_overdue_debt and not services_temporarily_unlocked:
        debt_data = overdue_debts[user_id]
        text += "⚠️ <b>شما بدهی معوق دارید!</b>\n"
        text += f"مبلغ بدهی: {format_price_short(debt_data['remaining_debt'])}\n"
        text += "🔒 خدمات بانکی محدود شده است.\n\n"
        text += "💡 <b>خدمات در دسترس:</b>\n"
        text += "▫️ برداشت از حساب به موجودی کشور\n"
        text += "▫️ تاریخچه تراکنش‌ها\n"
        text += "▫️ مشاهده بدهی‌های معوق\n\n"
        text += "📝 <b>توضیحات:</b>\n"
        text += "• فقط برداشت مجاز است\n"
        text += "• انتقال و شارژ غیرفعال است\n"
        text += "• سایر کاربران می‌توانند به حساب شما انتقال دهند\n"
        text += "• پس از تسویه بدهی، تمام خدمات فعال می‌شود\n\n"
        
        keyboard = [
            [InlineKeyboardButton('💰 برداشت از حساب', callback_data='withdraw_from_account')],
            [InlineKeyboardButton('📊 تاریخچه تراکنش‌ها', callback_data='transaction_history')],
            [InlineKeyboardButton('بدهی‌های معوق ⚠️', callback_data='overdue_debts')],
            [InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')]
        ]
    elif has_overdue_debt and services_temporarily_unlocked:
        debt_data = overdue_debts[user_id]
        text += "🎉 <b>خدمات بانکی موقتاً آزاد شد!</b>\n"
        text += f"مبلغ بدهی باقی‌مانده: {format_price_short(debt_data['remaining_debt'])}\n"
        text += "✅ در این دور پرداخت اقساطی انجام داده‌اید.\n\n"
        text += "💡 <b>خدمات در دسترس:</b>\n"
        text += "▫️ انتقال پول به حساب دیگران\n"
        text += "▫️ شارژ حساب از موجودی کشور\n"
        text += "▫️ برداشت از حساب به موجودی کشور\n"
        text += "▫️ تاریخچه تراکنش‌ها\n"
        text += "▫️ مشاهده بدهی‌های معوق\n\n"
        text += "⚠️ <b>توجه:</b> این آزادسازی فقط برای این دور است!\n\n"
        
        keyboard = [
            [InlineKeyboardButton('💸 انتقال پول', callback_data='transfer_money')],
            [InlineKeyboardButton('💳 شارژ حساب', callback_data='deposit_to_account')],
            [InlineKeyboardButton('💰 برداشت از حساب', callback_data='withdraw_from_account')],
            [InlineKeyboardButton('📊 تاریخچه تراکنش‌ها', callback_data='transaction_history')],
            [InlineKeyboardButton('بدهی‌های معوق ⚠️', callback_data='overdue_debts')],
            [InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')]
        ]
    else:
        text += "💡 <b>خدمات موجود:</b>\n"
        text += "▫️ انتقال پول به حساب دیگران\n"
        text += "▫️ تاریخچه تراکنش‌ها\n"
        text += "▫️ شارژ حساب از موجودی کشور\n"
        text += "▫️ برداشت از حساب به موجودی کشور\n\n"
        
        keyboard = [
            [InlineKeyboardButton('💸 انتقال پول', callback_data='transfer_money')],
            [InlineKeyboardButton('📊 تاریخچه تراکنش‌ها', callback_data='transaction_history')],
            [InlineKeyboardButton('💳 شارژ حساب', callback_data='deposit_to_account')],
            [InlineKeyboardButton('💰 برداشت از حساب', callback_data='withdraw_from_account')],
            [InlineKeyboardButton('🔙 بازگشت', callback_data='international_bank')]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_transfer_money_menu(query):
    """نمایش منوی انتقال پول"""
    user_id = str(query.from_user.id)
    account = bank_accounts.get(user_id)
    
    if not account:
        await query.edit_message_text('حساب بانکی شما یافت نشد!')
        return
    
    text = "💸 <b>انتقال پول</b>\n\n"
    text += f"💰 موجودی حساب شما: {format_price_short(account['balance'])}\n\n"
    text += "📋 <b>مراحل انتقال:</b>\n"
    text += "1️⃣ شماره حساب مقصد را وارد کنید\n"
    text += "2️⃣ مبلغ انتقال را مشخص کنید\n"
    text += "3️⃣ اطلاعات را تایید کنید\n"
    text += "4️⃣ انتقال انجام می‌شود\n\n"
    text += "⚠️ <b>نکات مهم:</b>\n"
    text += "▫️ انتقال غیرقابل بازگشت است\n"
    text += "▫️ شماره حساب باید 12 رقمی باشد\n"
    text += "▫️ مبلغ باید از موجودی کمتر باشد\n\n"
    
    keyboard = [
        [InlineKeyboardButton('🚀 شروع انتقال', callback_data='start_transfer')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='bank_account')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def start_transfer_process(query):
    """شروع فرآیند انتقال پول"""
    user_id = str(query.from_user.id)
    
    # بررسی بدهی معوق و وضعیت آزادسازی موقت
    if user_id in overdue_debts:
        debt_data = overdue_debts[user_id]
        # بررسی اینکه آیا در این دور پرداخت کرده یا نه
        if 'last_payment_turn' in debt_data and debt_data['last_payment_turn'] == game_data['turn']:
            # خدمات موقتاً آزاد است
            text = "🎉 <b>انتقال پول موقتاً آزاد شد!</b>\n\n"
            text += f"شما در این دور پرداخت اقساطی انجام داده‌اید.\n"
            text += f"بدهی باقی‌مانده: {format_price_short(debt_data['remaining_debt'])}\n\n"
            text += "💡 <b>می‌توانید انتقال انجام دهید:</b>\n"
            text += "▫️ انتقال پول به حساب دیگران\n"
            text += "▫️ شارژ حساب از موجودی کشور\n"
            text += "▫️ برداشت از حساب\n\n"
            text += "⚠️ <b>توجه:</b> این آزادسازی فقط برای این دور است!\n\n"
            
            account = bank_accounts.get(user_id)
            text += "💸 <b>انتقال پول</b>\n\n"
            text += f"💰 موجودی حساب شما: {format_price_short(account['balance'])}\n\n"
            text += "📋 <b>مراحل انتقال:</b>\n"
            text += "1️⃣ شماره حساب مقصد را وارد کنید\n"
            text += "2️⃣ مبلغ انتقال را مشخص کنید\n"
            text += "3️⃣ تایید نهایی\n\n"
            text += "⚠️ <b>هشدار:</b> انتقال غیرقابل بازگشت است!"
            
            keyboard = [
                [InlineKeyboardButton('شروع انتقال', callback_data='start_transfer')],
                [InlineKeyboardButton('🔙 بازگشت', callback_data='bank_account')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            return
        else:
            # خدمات محدود است
            text = "⚠️ <b>انتقال پول غیرفعال است!</b>\n\n"
            text += f"شما بدهی معوق دارید: {format_price_short(debt_data['remaining_debt'])}\n"
            text += "🔒 تا زمان تسویه بدهی، انتقال پول غیرفعال است.\n\n"
            text += "💡 <b>گزینه‌های موجود:</b>\n"
            text += "▫️ برداشت از حساب\n"
            text += "▫️ مشاهده بدهی‌های معوق\n"
            text += "▫️ پرداخت بدهی\n\n"
            
            keyboard = [
                [InlineKeyboardButton('💰 برداشت از حساب', callback_data='withdraw_from_account')],
                [InlineKeyboardButton('بدهی‌های معوق ⚠️', callback_data='overdue_debts')],
                [InlineKeyboardButton('🔙 بازگشت', callback_data='bank_account')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            return
    
    # ذخیره وضعیت انتقال
    pending_transfers[user_id] = {
        'step': 'account_number',
        'data': {}
    }
    
    text = "💸 <b>انتقال پول - مرحله 1</b>\n\n"
    text += "📋 لطفاً شماره حساب مقصد را وارد کنید:\n"
    text += "شماره حساب باید 12 رقمی باشد\n\n"
    text += "مثال: 123456789012"
    
    keyboard = [[InlineKeyboardButton('🔙 انصراف', callback_data='cancel_transfer')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_transfer_account_number(update, context):
    """پردازش شماره حساب مقصد"""
    user_id = str(update.effective_user.id)
    
    # بررسی بدهی معوق و وضعیت آزادسازی موقت
    if user_id in overdue_debts:
        debt_data = overdue_debts[user_id]
        # بررسی اینکه آیا در این دور پرداخت کرده یا نه
        if 'last_payment_turn' not in debt_data or debt_data['last_payment_turn'] != game_data['turn']:
            await update.message.reply_text('❌ شما بدهی معوق دارید و نمی‌توانید انتقال انجام دهید!')
            del pending_transfers[user_id]
            return
    
    if user_id not in pending_transfers:
        await update.message.reply_text('فرآیند انتقال فعال نیست.')
        return
    
    account_number = update.message.text.strip()
    
    # بررسی فرمت شماره حساب
    if not account_number.isdigit() or len(account_number) != 12:
        await update.message.reply_text('❌ شماره حساب نامعتبر است! شماره حساب باید 12 رقمی باشد.')
        return
    
    # بررسی وجود حساب
    target_user_id, target_account = get_account_by_number(account_number)
    if not target_user_id:
        await update.message.reply_text('❌ شماره حساب یافت نشد! لطفاً شماره صحیح را وارد کنید.')
        return
    
    # بررسی انتقال به خود
    if target_user_id == user_id:
        await update.message.reply_text('❌ نمی‌توانید به حساب خودتان انتقال دهید!')
        return
    
    # ذخیره شماره حساب
    pending_transfers[user_id]['data']['target_account'] = account_number
    pending_transfers[user_id]['data']['target_user_id'] = target_user_id
    pending_transfers[user_id]['step'] = 'amount'
    
    # دریافت نام کشور مقصد
    target_user = utils.users.get(target_user_id, {})
    target_country = target_user.get('country', 'نامشخص')
    
    text = "💸 <b>انتقال پول - مرحله 2</b>\n\n"
    text += f"📋 شماره حساب مقصد: {account_number}\n"
    text += f"🏛️ کشور مقصد: {target_country}\n\n"
    text += "💰 لطفاً مبلغ انتقال را وارد کنید:"
    
    keyboard = [[InlineKeyboardButton('🔙 انصراف', callback_data='cancel_transfer')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_transfer_amount(update, context):
    """پردازش مبلغ انتقال"""
    user_id = str(update.effective_user.id)
    
    # بررسی بدهی معوق و وضعیت آزادسازی موقت
    if user_id in overdue_debts:
        debt_data = overdue_debts[user_id]
        # بررسی اینکه آیا در این دور پرداخت کرده یا نه
        if 'last_payment_turn' not in debt_data or debt_data['last_payment_turn'] != game_data['turn']:
            await update.message.reply_text('❌ شما بدهی معوق دارید و نمی‌توانید انتقال انجام دهید!')
            del pending_transfers[user_id]
            return
    
    if user_id not in pending_transfers:
        await update.message.reply_text('فرآیند انتقال فعال نیست.')
        return
    
    try:
        amount = int(update.message.text.replace(',', ''))
    except ValueError:
        await update.message.reply_text('❌ مبلغ نامعتبر است! لطفاً عدد صحیح وارد کنید.')
        return
    
    if amount <= 0:
        await update.message.reply_text('❌ مبلغ باید بیشتر از صفر باشد!')
        return
    
    # بررسی موجودی
    account = bank_accounts.get(user_id)
    if not account or account['balance'] < amount:
        await update.message.reply_text('❌ موجودی کافی نیست!')
        return
    
    # ذخیره مبلغ
    pending_transfers[user_id]['data']['amount'] = amount
    pending_transfers[user_id]['step'] = 'confirm'
    
    # دریافت اطلاعات مقصد
    target_account = pending_transfers[user_id]['data']['target_account']
    target_user_id = pending_transfers[user_id]['data']['target_user_id']
    target_user = utils.users.get(target_user_id, {})
    target_country = target_user.get('country', 'نامشخص')
    
    text = "💸 <b>انتقال پول - تایید نهایی</b>\n\n"
    text += "📋 <b>اطلاعات انتقال:</b>\n"
    text += f"▫️ شماره حساب مقصد: {target_account}\n"
    text += f"▫️ کشور مقصد: {target_country}\n"
    text += f"▫️ مبلغ انتقال: {format_price_short(amount)}\n"
    text += f"▫️ موجودی قبل از انتقال: {format_price_short(account['balance'])}\n"
    text += f"▫️ موجودی بعد از انتقال: {format_price_short(account['balance'] - amount)}\n\n"
    text += "⚠️ <b>توجه:</b> این عملیات غیرقابل بازگشت است!"
    
    keyboard = [
        [InlineKeyboardButton('✅ تایید انتقال', callback_data='confirm_transfer')],
        [InlineKeyboardButton('❌ انصراف', callback_data='cancel_transfer')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def confirm_transfer(query):
    """تایید و انجام انتقال"""
    user_id = str(query.from_user.id)
    
    # بررسی بدهی معوق و وضعیت آزادسازی موقت
    if user_id in overdue_debts:
        debt_data = overdue_debts[user_id]
        # بررسی اینکه آیا در این دور پرداخت کرده یا نه
        if 'last_payment_turn' not in debt_data or debt_data['last_payment_turn'] != game_data['turn']:
            await query.edit_message_text('❌ شما بدهی معوق دارید و نمی‌توانید انتقال انجام دهید!')
            del pending_transfers[user_id]
            return
    
    if user_id not in pending_transfers:
        await query.edit_message_text('فرآیند انتقال فعال نیست.')
        return
    
    transfer_data = pending_transfers[user_id]['data']
    amount = transfer_data['amount']
    target_account = transfer_data['target_account']
    target_user_id = transfer_data['target_user_id']
    
    # بررسی مجدد موجودی
    account = bank_accounts.get(user_id)
    if not account or account['balance'] < amount:
        await query.edit_message_text('❌ موجودی کافی نیست!')
        del pending_transfers[user_id]
        return
    
    # اعمال تأثیرات حکومت بر تجارت
    trade_bonus_user = utils.calculate_government_trade_bonus(user_id)
    trade_bonus_target = utils.calculate_government_trade_bonus(target_user_id)
    
    # محاسبه کارمزد انتقال بر اساس حکومت
    base_fee = amount * 0.01  # 1% کارمزد پایه
    user_fee_reduction = (trade_bonus_user / 100) * base_fee  # کاهش کارمزد بر اساس بونوس
    target_fee_reduction = (trade_bonus_target / 100) * base_fee
    
    # اعمال کارمزد نهایی
    final_fee = max(0, base_fee - user_fee_reduction - target_fee_reduction)
    transfer_amount = amount - final_fee
    
    # انجام انتقال
    account['balance'] -= amount
    target_account_data = bank_accounts[target_user_id]
    target_account_data['balance'] += transfer_amount
    
    # ثبت تراکنش
    transaction_id = f"TR{int(time.time())}"
    transaction = {
        'id': transaction_id,
        'from_user': user_id,
        'to_user': target_user_id,
        'amount': amount,
        'timestamp': time.time(),
        'type': 'transfer'
    }
    
    # ذخیره در تاریخچه
    if user_id not in transfer_history:
        transfer_history[user_id] = []
    if target_user_id not in transfer_history:
        transfer_history[target_user_id] = []
    
    transfer_history[user_id].append(transaction)
    transfer_history[target_user_id].append(transaction)
    
    # ذخیره تغییرات
    save_bank_accounts()
    save_transfer_history()
    
    # دریافت نام‌های کشورها
    user_data = utils.users.get(user_id, {})
    target_user_data = utils.users.get(target_user_id, {})
    from_country = user_data.get('country', 'نامشخص')
    to_country = target_user_data.get('country', 'نامشخص')
    
    # ایجاد رسید
    receipt_text = f"🏦 <b>رسید انتقال بانکی</b>\n\n"
    receipt_text += f"📋 شماره تراکنش: <code>{transaction_id}</code>\n"
    receipt_text += f"📅 تاریخ: {time.strftime('%Y/%m/%d %H:%M', time.localtime())}\n"
    receipt_text += f"💸 مبلغ: {format_price_short(amount)}\n"
    receipt_text += f"📤 از: <code>{mask_account_number(bank_accounts[user_id]['account_number'])}</code>\n"
    receipt_text += f"📥 به: <code>{mask_account_number(target_account)}</code>\n"
    receipt_text += f"🏛️ از کشور: {from_country}\n"
    receipt_text += f"🏛️ به کشور: {to_country}\n\n"
    receipt_text += "✅ <b>پرداخت موفقیت‌آمیز</b>"
    
    # ارسال رسید به فرستنده
    try:
        await query.edit_message_text(receipt_text, parse_mode='HTML')
    except Exception:
        await query.message.reply_text(receipt_text, parse_mode='HTML')
    
    # ارسال رسید به گیرنده
    try:
        from telegram import Bot
        bot = Bot(token='7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I')
        await bot.send_message(
            chat_id=int(target_user_id),
            text=receipt_text,
            parse_mode='HTML'
        )
    except Exception:
        pass
    
    # ارسال به کانال اخبار
    try:
        # نمایش شماره حساب‌ها با فرمت *123456******789*
        from_account = bank_accounts[user_id]['account_number']
        to_account = target_account
        from_account_display = f"*{from_account[:6]}******{from_account[-3:]}*"
        to_account_display = f"*{to_account[:6]}******{to_account[-3:]}*"
        
        news_text = f"🏦 <b>انتقال بانکی جدید</b>\n\n"
        news_text += f"💸 مبلغ: *\n"
        news_text += f"📤 از حساب: <code>{from_account_display}</code>\n"
        news_text += f"🏛️ مبدا: {from_country if from_country else 'نامشخص'}\n"
        news_text += f"📥 به حساب: <code>{to_account_display}</code>\n"
        news_text += f"🏛️ مقصد: {to_country if to_country else 'نامشخص'}\n"
        news_text += f"📋 شماره تراکنش: <code>{transaction_id}</code>\n\n"
        news_text += "✅ انتقال با موفقیت انجام شد"
        
        # استفاده از context.bot اگر در دسترس باشد
        try:
            # اگر context در دسترس باشد
            if hasattr(query, 'message') and hasattr(query.message, '_context'):
                context = query.message._context
                await context.bot.send_message(
                    chat_id='@TextEmpire_News',
                    text=news_text,
                    parse_mode='HTML'
                )
            else:
                # استفاده از bot جدید
                from telegram import Bot
                news_bot = Bot(token='7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I')
                await news_bot.send_message(
                    chat_id='@TextEmpire_News',
                    text=news_text,
                    parse_mode='HTML'
                )
        except Exception as bot_error:
            print(f"[DEBUG] Error with context.bot: {bot_error}")
            # استفاده از bot جدید
            from telegram import Bot
            news_bot = Bot(token='7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I')
            await news_bot.send_message(
                chat_id='@TextEmpire_News',
                text=news_text,
                parse_mode='HTML'
            )
        
        print(f"[DEBUG] News sent to channel: {news_text}")
    except Exception as e:
        print(f"[DEBUG] Error sending news to channel: {e}")
    
    # پاک کردن وضعیت انتقال
    del pending_transfers[user_id]

async def cancel_transfer(query):
    """انصراف از انتقال"""
    user_id = str(query.from_user.id)
    
    if user_id in pending_transfers:
        del pending_transfers[user_id]
    
    await query.edit_message_text('❌ انتقال لغو شد.')
    
    # بازگشت به منوی حساب بانکی
    await show_bank_account_menu(query)

async def show_transaction_history(query):
    """نمایش تاریخچه تراکنش‌ها"""
    user_id = str(query.from_user.id)
    
    if user_id not in transfer_history:
        text = "📊 <b>تاریخچه تراکنش‌ها</b>\n\n"
        text += "📋 هیچ تراکنشی یافت نشد."
        
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='bank_account')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return
    
    transactions = transfer_history[user_id][-10:]  # آخرین 10 تراکنش
    text = "📊 <b>تاریخچه تراکنش‌ها</b>\n\n"
    
    for transaction in reversed(transactions):
        timestamp = time.strftime('%Y/%m/%d %H:%M', time.localtime(transaction['timestamp']))
        amount = format_price_short(transaction['amount'])
        
        if transaction['from_user'] == user_id:
            # تراکنش خروجی
            other_user_id = transaction['to_user']
            other_user = utils.users.get(other_user_id, {})
            other_country = other_user.get('country', 'نامشخص')
            text += f"📤 {timestamp} → {other_country}: {amount}\n"
        else:
            # تراکنش ورودی
            other_user_id = transaction['from_user']
            other_user = utils.users.get(other_user_id, {})
            other_country = other_user.get('country', 'نامشخص')
            text += f"📥 {timestamp} ← {other_country}: {amount}\n"
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='bank_account')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_deposit_menu(query):
    """نمایش منوی شارژ حساب"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return
    
    # بررسی بدهی معوق و وضعیت آزادسازی موقت
    if user_id in overdue_debts:
        debt_data = overdue_debts[user_id]
        # بررسی اینکه آیا در این دور پرداخت کرده یا نه
        if 'last_payment_turn' in debt_data and debt_data['last_payment_turn'] == game_data['turn']:
            # خدمات موقتاً آزاد است
            text = "🎉 <b>شارژ حساب موقتاً آزاد شد!</b>\n\n"
            text += f"شما در این دور پرداخت اقساطی انجام داده‌اید.\n"
            text += f"بدهی باقی‌مانده: {format_price_short(debt_data['remaining_debt'])}\n\n"
            text += "💡 <b>می‌توانید شارژ انجام دهید:</b>\n"
            text += "▫️ شارژ حساب از موجودی کشور\n"
            text += "▫️ انتقال پول به حساب دیگران\n"
            text += "▫️ برداشت از حساب\n\n"
            text += "⚠️ <b>توجه:</b> این آزادسازی فقط برای این دور است!\n\n"
            
            user_cash = user.get('resources', {}).get('cash', 0)
            account = bank_accounts.get(user_id, {})
            account_balance = account.get('balance', 0)
            
            text += "💳 <b>شارژ حساب بانکی</b>\n\n"
            text += f"💰 موجودی نقد کشور: {format_price_short(user_cash)}\n"
            text += f"🏦 موجودی حساب بانکی: {format_price_short(account_balance)}\n\n"
            text += "📋 <b>مراحل شارژ:</b>\n"
            text += "1️⃣ مبلغ مورد نظر را وارد کنید\n"
            text += "2️⃣ تایید نهایی\n\n"
            text += "⚠️ <b>هشدار:</b> شارژ غیرقابل بازگشت است!"
            
            keyboard = [
                [InlineKeyboardButton('شروع شارژ', callback_data='start_deposit')],
                [InlineKeyboardButton('🔙 بازگشت', callback_data='bank_account')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            return
        else:
            # خدمات محدود است
            text = "⚠️ <b>شارژ حساب غیرفعال است!</b>\n\n"
            text += f"شما بدهی معوق دارید: {format_price_short(debt_data['remaining_debt'])}\n"
            text += "🔒 تا زمان تسویه بدهی، شارژ حساب غیرفعال است.\n\n"
            text += "💡 <b>گزینه‌های موجود:</b>\n"
            text += "▫️ برداشت از حساب\n"
            text += "▫️ مشاهده بدهی‌های معوق\n"
            text += "▫️ پرداخت بدهی\n\n"
            
            keyboard = [
                [InlineKeyboardButton('💰 برداشت از حساب', callback_data='withdraw_from_account')],
                [InlineKeyboardButton('بدهی‌های معوق ⚠️', callback_data='overdue_debts')],
                [InlineKeyboardButton('🔙 بازگشت', callback_data='bank_account')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
            return
    
    account = bank_accounts.get(user_id)
    if not account:
        await query.edit_message_text('حساب بانکی شما یافت نشد!')
        return
    
    user_cash = user.get('resources', {}).get('cash', 0)
    
    text = "💳 <b>شارژ حساب بانکی</b>\n\n"
    text += f"💰 موجودی کشور: {format_price_short(user_cash)}\n"
    text += f"💳 موجودی حساب: {format_price_short(account['balance'])}\n\n"
    text += "💡 لطفاً مبلغ شارژ را وارد کنید:"
    
    # ذخیره وضعیت شارژ
    pending_transfers[user_id] = {
        'step': 'deposit_amount',
        'data': {}
    }
    
    keyboard = [[InlineKeyboardButton('🔙 انصراف', callback_data='bank_account')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_deposit_amount(update, context):
    """پردازش مبلغ شارژ"""
    user_id = str(update.effective_user.id)
    
    # بررسی بدهی معوق و وضعیت آزادسازی موقت
    if user_id in overdue_debts:
        debt_data = overdue_debts[user_id]
        # بررسی اینکه آیا در این دور پرداخت کرده یا نه
        if 'last_payment_turn' not in debt_data or debt_data['last_payment_turn'] != game_data['turn']:
            await update.message.reply_text('❌ شما بدهی معوق دارید و نمی‌توانید حساب خود را شارژ کنید!')
            del pending_transfers[user_id]
            return
    
    if user_id not in pending_transfers or pending_transfers[user_id]['step'] != 'deposit_amount':
        await update.message.reply_text('فرآیند شارژ فعال نیست.')
        return
    
    try:
        amount = int(update.message.text.replace(',', ''))
    except ValueError:
        await update.message.reply_text('❌ مبلغ نامعتبر است! لطفاً عدد صحیح وارد کنید.')
        return
    
    if amount <= 0:
        await update.message.reply_text('❌ مبلغ باید بیشتر از صفر باشد!')
        return
    
    user = utils.users.get(user_id, {})
    user_cash = user.get('resources', {}).get('cash', 0)
    
    if user_cash < amount:
        await update.message.reply_text('❌ موجودی کشور کافی نیست!')
        del pending_transfers[user_id]
        return
    
    # انجام شارژ
    user['resources']['cash'] = user_cash - amount
    account = bank_accounts[user_id]
    account['balance'] += amount
    
    # ذخیره تغییرات
    save_users()
    save_bank_accounts()
    
    text = f"✅ <b>شارژ حساب موفقیت‌آمیز</b>\n\n"
    text += f"💸 مبلغ شارژ: {format_price_short(amount)}\n"
    text += f"💰 موجودی جدید حساب: {format_price_short(account['balance'])}\n"
    text += f"💵 موجودی جدید کشور: {format_price_short(user['resources']['cash'])}"
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='bank_account')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    # پاک کردن وضعیت شارژ
    del pending_transfers[user_id]

async def show_withdraw_menu(query):
    """نمایش منوی برداشت از حساب"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    
    if not user.get('activated'):
        await query.edit_message_text('لطفاً ابتدا کشور خود را فعال‌سازی کنید!')
        return
    
    account = bank_accounts.get(user_id)
    if not account:
        await query.edit_message_text('حساب بانکی شما یافت نشد!')
        return
    
    user_cash = user.get('resources', {}).get('cash', 0)
    
    text = "💰 <b>برداشت از حساب بانکی</b>\n\n"
    text += f"💳 موجودی حساب: {format_price_short(account['balance'])}\n"
    text += f"💰 موجودی کشور: {format_price_short(user_cash)}\n\n"
    text += "💡 لطفاً مبلغ برداشت را وارد کنید:"
    
    # ذخیره وضعیت برداشت
    pending_transfers[user_id] = {
        'step': 'withdraw_amount',
        'data': {}
    }
    
    keyboard = [[InlineKeyboardButton('🔙 انصراف', callback_data='bank_account')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_withdraw_amount(update, context):
    """پردازش مبلغ برداشت"""
    user_id = str(update.effective_user.id)
    
    if user_id not in pending_transfers or pending_transfers[user_id]['step'] != 'withdraw_amount':
        await update.message.reply_text('فرآیند برداشت فعال نیست.')
        return
    
    try:
        amount = int(update.message.text.replace(',', ''))
    except ValueError:
        await update.message.reply_text('❌ مبلغ نامعتبر است! لطفاً عدد صحیح وارد کنید.')
        return
    
    if amount <= 0:
        await update.message.reply_text('❌ مبلغ باید بیشتر از صفر باشد!')
        return
    
    account = bank_accounts.get(user_id)
    if not account or account['balance'] < amount:
        await update.message.reply_text('❌ موجودی حساب کافی نیست!')
        del pending_transfers[user_id]
        return
    
    # انجام برداشت
    account['balance'] -= amount
    user = utils.users.get(user_id, {})
    user['resources']['cash'] = user.get('resources', {}).get('cash', 0) + amount
    
    # ذخیره تغییرات
    save_users()
    save_bank_accounts()
    
    text = f"✅ <b>برداشت از حساب موفقیت‌آمیز</b>\n\n"
    text += f"💸 مبلغ برداشت: {format_price_short(amount)}\n"
    text += f"💳 موجودی جدید حساب: {format_price_short(account['balance'])}\n"
    text += f"💰 موجودی جدید کشور: {format_price_short(user['resources']['cash'])}"
    
    keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='bank_account')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    # پاک کردن وضعیت برداشت
    del pending_transfers[user_id]

def save_secret_loan_claimed():
    """ذخیره وضعیت وام مخفی"""
    try:
        with open(SECRET_LOAN_CLAIMED_FILE, 'w', encoding='utf-8') as f:
            json.dump({'claimed': secret_loan_claimed}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[DEBUG] Error saving secret_loan_claimed: {e}")

def load_secret_loan_claimed():
    """بارگذاری وضعیت وام مخفی"""
    global secret_loan_claimed
    try:
        with open(SECRET_LOAN_CLAIMED_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            secret_loan_claimed = data.get('claimed', False)
    except FileNotFoundError:
        secret_loan_claimed = False
    except Exception as e:
        print(f"[DEBUG] Error loading secret_loan_claimed: {e}")
        secret_loan_claimed = False

def save_secret_loan_activated():
    """ذخیره کاربرانی که وام مخفی برایشان فعال شده"""
    try:
        with open(SECRET_LOAN_ACTIVATED_FILE, 'w', encoding='utf-8') as f:
            json.dump(secret_loan_activated, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[DEBUG] Error saving secret_loan_activated: {e}")

def load_secret_loan_activated():
    """بارگذاری کاربرانی که وام مخفی برایشان فعال شده"""
    global secret_loan_activated
    try:
        with open(SECRET_LOAN_ACTIVATED_FILE, 'r', encoding='utf-8') as f:
            secret_loan_activated = json.load(f)
    except FileNotFoundError:
        secret_loan_activated = {}
    except Exception as e:
        print(f"[DEBUG] Error loading secret_loan_activated: {e}")
        secret_loan_activated = {}

# بارگذاری داده‌ها در شروع
load_bank_data()
load_loan_history()
load_bank_accounts()
load_transfer_history()
load_overdue_debts()
load_secret_loan_claimed()
load_secret_loan_activated()


