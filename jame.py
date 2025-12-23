import json
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timedelta

# جمعیت واقعی کشورها (بر اساس آمار 2024)
COUNTRY_POPULATIONS = {
    "سازمان ملل 🇺🇳": 8000000000,  # جمعیت کل جهان
    "ایالات متحده آمریکا 🇺🇸": 340000000,
    "چین 🇨🇳": 1400000000,
    "روسیه 🇷🇺": 144000000,
    "بریتانیا 🇬🇧": 67000000,
    "آلمان 🇩🇪": 83000000,
    "ژاپن 🇯🇵": 125000000,
    "فرانسه 🇫🇷": 68000000,
    "هند 🇮🇳": 1400000000,
    "ایتالیا 🇮🇹": 60000000,
    "کانادا 🇨🇦": 38000000,
    "ایران 🇮🇷": 85000000,
    "کره‌ جنوبی 🇰🇷": 52000000,
    "برزیل 🇧🇷": 214000000,
    "ترکیه 🇹🇷": 85000000,
    "اسرائیل 🇮🇱": 9500000,
    "اسپانیا 🇪🇸": 47000000,
    "عربستان سعودی 🇸🇦": 36000000,
    "سوئیس 🇨🇭": 8700000,
    "مکزیک 🇲🇽": 130000000,
    "مصر 🇪🇬": 105000000,
    "پاکستان 🇵🇰": 230000000,
    "استرالیا 🇦🇺": 26000000,
    "اندونزی 🇮🇩": 275000000,
    "اوکراین 🇺🇦": 44000000,
    "لهستان 🇵🇱": 38000000,
    "نیجریه 🇳🇬": 220000000,
    "تایلند 🇹🇭": 70000000,
    "امارات متحده عربی 🇦🇪": 10000000,
    "قطر 🇶🇦": 3000000,
    "آفریقای جنوبی 🇿🇦": 60000000,
    "ویتنام 🇻🇳": 98000000,
    "مالزی 🇲🇾": 33000000,
    "آرژانتین 🇦🇷": 45000000,
    "سوئد 🇸🇪": 10000000,
    "نروژ 🇳🇴": 5400000,
    "هلند 🇳🇱": 17000000,
    "عراق 🇮🇶": 41000000,
    "حذب نازی اروپا 🇮🇲": 450000000,  # جمعیت اروپا
    "الجزایر 🇩🇿": 45000000,
    "یونان 🇬🇷": 11000000,
    "رومانی 🇷🇴": 19000000,
    "فیلیپین 🇵🇭": 115000000,
    "بلژیک 🇧🇪": 12000000,
    "دانمارک 🇩🇰": 5800000,
    "اتریش 🇦🇹": 9000000,
    "مجارستان 🇭🇺": 9700000,
    "داعش 🏴‍☠️": 50000000,  # تخمینی
    "فنلاند 🇫🇮": 5500000,
    "پرتغال 🇵🇹": 10000000,
    "صربستان 🇷🇸": 8700000,
    "کره شمالی 🇰🇵": 26000000
}

# نیازمندی‌های غذایی برای هر 1 میلیون نفر جمعیت
FOOD_REQUIREMENTS_PER_MILLION = {
    'wheat': 0.35,  # 35% از جمعیت (هر 1M نفر = 0.35 واحد گندم)
    'rice': 0.30,   # 30% از جمعیت (هر 1M نفر = 0.30 واحد برنج)
    'fruits': 0.20  # 20% از جمعیت (هر 1M نفر = 0.20 واحد میوه)
}

# نرخ رشد برای هر منبع غذایی
GROWTH_RATES = {
    'wheat': 0.50,  # 0.50% رشد برای گندم
    'rice': 0.60,   # 0.60% رشد برای برنج
    'fruits': 0.75  # 0.75% رشد برای میوه
}

def get_country_population(country_name):
    """دریافت جمعیت یک کشور"""
    pop = COUNTRY_POPULATIONS.get(country_name, 0)
    if pop:
        return pop
    # fallback: تطبیق نام بدون ایموجی با کلیدهای دارای ایموجی
    try:
        base = (country_name or '').strip()
        if not base:
            return 0
        for key in COUNTRY_POPULATIONS.keys():
            # کلیدی که با نام پایه شروع می‌شود (مثلاً "روسیه 🇷🇺")
            if key.startswith(base + ' ') or key == base:
                return COUNTRY_POPULATIONS.get(key, 0)
    except Exception:
        pass
    # fallback: از utils.COUNTRY_POPULATIONS نیز تلاش کن
    try:
        from utils import COUNTRY_POPULATIONS as U_POP
        pop = U_POP.get(country_name, 0)
        if pop:
            return pop
        base = (country_name or '').strip()
        if base:
            for key in U_POP.keys():
                if key.startswith(base + ' ') or key == base:
                    return U_POP.get(key, 0)
    except Exception:
        pass
    return 0

def get_country_population_by_user_id(user_id):
    """دریافت جمعیت کشور بر اساس user_id"""
    import utils
    user = utils.users.get(user_id, {})
    country_name = user.get('country', '')
    pop = COUNTRY_POPULATIONS.get(country_name, 0)
    if pop:
        return pop
    # fallback: جستجو با نام پایه (بدون ایموجی)
    try:
        base = (country_name or '').strip()
        if base:
            for key in COUNTRY_POPULATIONS.keys():
                if key.startswith(base + ' ') or key == base:
                    return COUNTRY_POPULATIONS.get(key, 0)
    except Exception:
        pass
    # fallback: utils.COUNTRY_POPULATIONS
    try:
        from utils import COUNTRY_POPULATIONS as U_POP
        pop = U_POP.get(country_name, 0)
        if pop:
            return pop
        base = (country_name or '').strip()
        if base:
            for key in U_POP.keys():
                if key.startswith(base + ' ') or key == base:
                    return U_POP.get(key, 0)
    except Exception:
        pass
    return 0

def update_population_damage(user_id, damage_amount):
    """به‌روزرسانی آسیب جمعیت (فعلاً فقط در حافظه ذخیره می‌شود)"""
    # این تابع می‌تواند در آینده برای ذخیره آسیب‌های جمعیت استفاده شود
    print(f"جمعیت کشور {user_id} به اندازه {damage_amount:,} نفر آسیب دید")
    return True

def get_world_population():
    """دریافت جمعیت کل جهان"""
    return sum(COUNTRY_POPULATIONS.values())

def get_population_rank(country_name):
    """دریافت رتبه جمعیتی یک کشور"""
    sorted_countries = sorted(COUNTRY_POPULATIONS.items(), key=lambda x: x[1], reverse=True)
    for i, (country, _) in enumerate(sorted_countries, 1):
        if country == country_name:
            return i
    return 0

def get_population_percentage(country_name):
    """دریافت درصد جمعیت یک کشور از کل جهان"""
    country_pop = get_country_population(country_name)
    world_pop = get_world_population()
    if world_pop > 0:
        return (country_pop / world_pop) * 100
    return 0

def get_population_categories():
    """دریافت دسته‌بندی کشورها بر اساس جمعیت"""
    large_countries = [c for c, p in COUNTRY_POPULATIONS.items() if p >= 100000000]
    medium_countries = [c for c, p in COUNTRY_POPULATIONS.items() if 10000000 <= p < 100000000]
    small_countries = [c for c, p in COUNTRY_POPULATIONS.items() if p < 10000000]
    
    return {
        'large': large_countries,
        'medium': medium_countries,
        'small': small_countries
    }

def get_top_populated_countries(limit=10):
    """دریافت کشورهای پرجمعیت"""
    sorted_countries = sorted(COUNTRY_POPULATIONS.items(), key=lambda x: x[1], reverse=True)
    return sorted_countries[:limit]

# توابع جدید برای آمار اقتصادی
def get_country_economy(country_name):
    """دریافت اقتصاد یک کشور"""
    import utils
    for user_id, user_data in utils.users.items():
        if user_data.get('country') == country_name and user_data.get('activated', False):
            return utils.calculate_total_economy(user_id)
    return 0

def get_world_economy():
    """دریافت اقتصاد کل جهان"""
    import utils
    total_economy = 0
    for user_id, user_data in utils.users.items():
        if user_data.get('activated', False):
            total_economy += utils.calculate_total_economy(user_id)
    return total_economy

def get_economy_rank(country_name):
    """دریافت رتبه اقتصادی یک کشور"""
    import utils
    country_economies = []
    for user_id, user_data in utils.users.items():
        if user_data.get('activated', False):
            country = user_data.get('country')
            economy = utils.calculate_total_economy(user_id)
            country_economies.append((country, economy))
    
    sorted_countries = sorted(country_economies, key=lambda x: x[1], reverse=True)
    for i, (country, _) in enumerate(sorted_countries, 1):
        if country == country_name:
            return i
    return 0

def get_economy_percentage(country_name):
    """دریافت درصد اقتصاد یک کشور از کل جهان"""
    country_economy = get_country_economy(country_name)
    world_economy = get_world_economy()
    if world_economy > 0:
        return (country_economy / world_economy) * 100
    return 0

def get_economy_categories():
    """دریافت دسته‌بندی کشورها بر اساس اقتصاد"""
    import utils
    large_economies = []
    medium_economies = []
    small_economies = []
    
    for user_id, user_data in utils.users.items():
        if user_data.get('activated', False):
            country = user_data.get('country')
            economy = utils.calculate_total_economy(user_id)
            
            if economy >= 1000000000:  # 1B+
                large_economies.append(country)
            elif economy >= 100000000:  # 100M+
                medium_economies.append(country)
            else:
                small_economies.append(country)
    
    return {
        'large': large_economies,
        'medium': medium_economies,
        'small': small_economies
    }

def get_top_economy_countries(limit=10):
    """دریافت کشورهای با اقتصاد قوی"""
    import utils
    country_economies = []
    for user_id, user_data in utils.users.items():
        if user_data.get('activated', False):
            country = user_data.get('country')
            economy = utils.calculate_total_economy(user_id)
            country_economies.append((country, economy))
    
    sorted_countries = sorted(country_economies, key=lambda x: x[1], reverse=True)
    return sorted_countries[:limit]

def get_current_date():
    """دریافت تاریخ فعلی بر اساس دور بازی"""
    import utils
    # استفاده از تاریخ اصلی بازی
    return utils.game_data['game_date']

# توابع جدید برای رشد جمعیت
def calculate_food_requirements(population):
    """محاسبه نیازمندی‌های غذایی بر اساس جمعیت"""
    population_millions = population / 1000000
    return {
        'wheat': int(population_millions * FOOD_REQUIREMENTS_PER_MILLION['wheat']),
        'rice': int(population_millions * FOOD_REQUIREMENTS_PER_MILLION['rice']),
        'fruits': int(population_millions * FOOD_REQUIREMENTS_PER_MILLION['fruits'])
    }

def calculate_growth_rate(user_id):
    """محاسبه نرخ رشد جمعیت بر اساس منابع غذایی"""
    import utils
    from bot import get_user_robin_hood_bonus
    
    if user_id not in utils.users or not utils.users[user_id].get('activated', False):
        return 0.0
    
    country_name = utils.users[user_id]['country']
    current_population = get_country_population(country_name)
    user_resources = utils.users[user_id].get('resources', {})
    
    # محاسبه نیازمندی‌های غذایی
    requirements = calculate_food_requirements(current_population)
    
    # بررسی منابع موجود
    available_wheat = user_resources.get('wheat', 0)
    available_rice = user_resources.get('rice', 0)
    available_fruits = user_resources.get('fruits', 0)
    
    # محاسبه نرخ رشد برای هر منبع
    wheat_growth = 0.0
    rice_growth = 0.0
    fruits_growth = 0.0
    
    if available_wheat >= requirements['wheat']:
        wheat_growth = GROWTH_RATES['wheat']
    
    if available_rice >= requirements['rice']:
        rice_growth = GROWTH_RATES['rice']
    
    if available_fruits >= requirements['fruits']:
        fruits_growth = GROWTH_RATES['fruits']
    
    # مجموع نرخ رشد
    total_growth_rate = wheat_growth + rice_growth + fruits_growth
    # بونوس اخراج مهاجران: +0.5% برای 3 دور
    buffs = utils.users[user_id].get('temporary_buffs', {})
    gb_turns = int(buffs.get('growth_buff_turns', 0))
    gb_rate = float(buffs.get('growth_buff_rate', 0.0)) if gb_turns > 0 else 0.0
    total_growth_rate += gb_rate
    # بونوس ثابت رابین هود (مستقل از سیستم غذا)
    try:
        total_growth_rate += float(get_user_robin_hood_bonus(user_id))
    except Exception:
        pass
    
    return total_growth_rate

def calculate_population_growth(user_id):
    """محاسبه جمعیت اضافه شده در این دور"""
    import utils
    
    if user_id not in utils.users or not utils.users[user_id].get('activated', False):
        return 0
    
    country_name = utils.users[user_id]['country']
    current_population = get_country_population(country_name)
    growth_rate = calculate_growth_rate(user_id)
    
    # محاسبه جمعیت اضافه شده
    population_growth = int(current_population * (growth_rate / 100))
    
    return population_growth

def calculate_tax_revenue(population):
    """محاسبه مالیات دریافتی از جمعیت پایه + اثر مهاجران"""
    import utils
    # find user by country population usage is upstream; here we just return base
    # Actual immigrant tax bonus will be applied at collection
    return int(population * 0.10)

def collect_tax(user_id):
    """دریافت مالیات از جمعیت کشور"""
    import utils
    
    print(f"[DEBUG] collect_tax called for user_id: {user_id}")
    
    if user_id not in utils.users or not utils.users[user_id].get('activated', False):
        print(f"[DEBUG] User not found or not activated: {user_id}")
        return False, "شما هنوز کشور فعال نکرده‌اید."
    
    country_name = utils.users[user_id]['country']
    current_population = get_country_population(country_name)
    
    print(f"[DEBUG] Country: {country_name}, Population: {current_population}")
    
    # محاسبه مالیات پایه + بونوس مهاجران (+10% به ازای هر 1M)
    base_tax = calculate_tax_revenue(current_population)
    immigrants = utils.users[user_id].get('immigrants', 0)
    imm_units = immigrants // 1_000_000
    bonus_multiplier = 1 + (imm_units * 10) / 100.0
    tax_amount = int(base_tax * bonus_multiplier)
    
    print(f"[DEBUG] Tax amount: {tax_amount}")
    
    # بررسی اینکه آیا 2 دور گذشته است
    current_turn = utils.game_data['turn']
    last_tax_collection = utils.users[user_id].get('last_tax_collection', 0)
    
    print(f"[DEBUG] Current turn: {current_turn}, Last tax collection: {last_tax_collection}")
    
    if current_turn - last_tax_collection < 2:
        remaining_turns = 2 - (current_turn - last_tax_collection)
        print(f"[DEBUG] Tax collection too soon, remaining turns: {remaining_turns}")
        return False, f"شما باید {remaining_turns} دور دیگر صبر کنید تا بتوانید مالیات دریافت کنید."
    
    # اضافه کردن مالیات به موجودی نقدی
    if 'resources' not in utils.users[user_id]:
        utils.users[user_id]['resources'] = {}
    
    current_cash = utils.users[user_id]['resources'].get('cash', 0)
    utils.users[user_id]['resources']['cash'] = current_cash + tax_amount
    
    print(f"[DEBUG] Cash before: {current_cash}, after: {current_cash + tax_amount}")
    
    # ذخیره زمان آخرین دریافت مالیات
    utils.users[user_id]['last_tax_collection'] = current_turn
    
    # فعال کردن سیستم مالیات برای 2 دور آینده
    utils.users[user_id]['tax_active_until'] = current_turn + 2
    
    # کاهش رضایت مردم به دلیل دریافت مالیات
    if 'satisfaction' not in utils.users[user_id]:
        utils.users[user_id]['satisfaction'] = 70
    
    utils.users[user_id]['satisfaction'] = max(0, utils.users[user_id]['satisfaction'] - 5)
    
    # ذخیره اطلاعات مالیات در فایل
    save_tax_data()
    utils.save_users()
    
    print(f"[DEBUG] Tax collection successful: {tax_amount}")
    
    return True, f"مالیات {tax_amount:,} دلار با موفقیت دریافت شد و به موجودی نقدی شما اضافه شد.\n⚠️ رضایت مردم 5 واحد کاهش یافت.\n💡 سیستم مالیات برای 2 دور آینده فعال است.\n📊 تأثیر بر رضایت: -10 واحد در هر دور (تا 2 دور)"

def get_tax_status(user_id):
    """دریافت وضعیت مالیات کاربر"""
    import utils
    
    if user_id not in utils.users or not utils.users[user_id].get('activated', False):
        return "شما هنوز کشور فعال نکرده‌اید."
    
    current_turn = utils.game_data.get('turn', 1)
    last_tax_collection = utils.users[user_id].get('last_tax_collection', 0)
    tax_active_until = utils.users[user_id].get('tax_active_until', 0)
    
    # بررسی وضعیت مالیات
    if current_turn <= tax_active_until:
        remaining_turns = tax_active_until - current_turn + 1
        return f"✅ سیستم مالیات فعال است\n📅 {remaining_turns} دور باقی‌مانده\n⚠️ هر دور 10 واحد از رضایت مردم کم می‌شود\n💡 اگر نیازها برآورده شوند: +9 - 10 = -1 واحد"
    else:
        # بررسی اینکه آیا می‌تواند مالیات دریافت کند
        if current_turn - last_tax_collection >= 2:
            return "💰 آماده دریافت مالیات\n⚠️ هر دور 2 واحد از رضایت مردم کم می‌شود (عدم دریافت مالیات)\n💡 اگر نیازها برآورده شوند: +9 - 2 = +7 واحد"
        else:
            remaining_turns = 2 - (current_turn - last_tax_collection)
            return f"⏳ {remaining_turns} دور تا دریافت مالیات\n⚠️ هر دور 2 واحد از رضایت مردم کم می‌شود (عدم دریافت مالیات)\n💡 اگر نیازها برآورده شوند: +9 - 2 = +7 واحد"

def consume_food_resources(user_id):
    """مصرف منابع غذایی و کاهش آن‌ها"""
    import utils
    
    if user_id not in utils.users or not utils.users[user_id].get('activated', False):
        return
    
    country_name = utils.users[user_id]['country']
    current_population = get_country_population(country_name)
    user_resources = utils.users[user_id].get('resources', {})
    
    # محاسبه نیازمندی‌های غذایی
    requirements = calculate_food_requirements(current_population)
    
    # مصرف منابع
    available_wheat = user_resources.get('wheat', 0)
    available_rice = user_resources.get('rice', 0)
    available_fruits = user_resources.get('fruits', 0)
    
    # کاهش منابع بر اساس نیازمندی
    if available_wheat >= requirements['wheat']:
        user_resources['wheat'] = available_wheat - requirements['wheat']
    
    if available_rice >= requirements['rice']:
        user_resources['rice'] = available_rice - requirements['rice']
    
    if available_fruits >= requirements['fruits']:
        user_resources['fruits'] = available_fruits - requirements['fruits']

def update_population(user_id):
    """به‌روزرسانی جمعیت کشور"""
    import utils
    # اگر کشور فعال نیست، صرف‌نظر
    if not utils.users.get(user_id, {}).get('activated', False):
        return
    
    if user_id not in utils.users or not utils.users[user_id].get('activated', False):
        return
    
    country_name = utils.users[user_id]['country']
    current_population = get_country_population(country_name)
    
    # محاسبه نرخ رشد و جمعیت اضافه شده قبل از مصرف منابع
    growth_rate = calculate_growth_rate(user_id)
    population_growth = calculate_population_growth(user_id)
    
    # ذخیره اطلاعات رشد دور فعلی (که در دور بعدی به عنوان دور قبلی استفاده می‌شود)
    if 'population_growth_history' not in utils.users[user_id]:
        utils.users[user_id]['population_growth_history'] = {}
    
    utils.users[user_id]['population_growth_history'] = {
        'growth_rate': growth_rate,
        'population_growth': population_growth,
        'turn': utils.game_data['turn']  # این turn فعلی است که در دور بعدی به عنوان turn قبلی استفاده می‌شود
    }
    
    # به‌روزرسانی جمعیت
    new_population = current_population + population_growth
    COUNTRY_POPULATIONS[country_name] = new_population
    
    # ذخیره جمعیت جدید در فایل
    save_population_data()
    
    # مصرف منابع غذایی
    consume_food_resources(user_id)
    
    return population_growth

async def show_population_status(query):
    """نمایش وضعیت جمعیت کشور کاربر"""
    import utils
    user_id = str(query.from_user.id)
    
    if user_id not in utils.users or not utils.users[user_id].get('activated', False):
        from bot import show_simple_section
        await show_simple_section(query, 'شما هنوز کشور فعال نکرده‌اید.')
        return
    
    country_name = utils.users[user_id]['country']
    
    # جمعیت کشور کاربر
    user_population = get_country_population(country_name)
    
    # دریافت اطلاعات رشد دور فعلی
    growth_history = utils.users[user_id].get('population_growth_history', {})
    current_turn = utils.game_data['turn']
    
    # اگر اطلاعات رشد دور فعلی وجود دارد، از آن استفاده کن
    if growth_history and growth_history.get('turn', 0) == current_turn:
        growth_rate = growth_history.get('growth_rate', 0.0)
        population_growth = growth_history.get('population_growth', 0)
    else:
        # اگر اطلاعات دور فعلی وجود ندارد، از محاسبه فعلی استفاده کن
        growth_rate = calculate_growth_rate(user_id)
        population_growth = calculate_population_growth(user_id)
    
    # محاسبه مالیات
    tax_revenue = calculate_tax_revenue(user_population)
    
    # بررسی امکان دریافت مالیات
    last_tax_collection = utils.users[user_id].get('last_tax_collection', 0)
    can_collect_tax = (current_turn - last_tax_collection) >= 2
    
    # محاسبه نیازمندی‌های غذایی
    requirements = calculate_food_requirements(user_population)
    user_resources = utils.users[user_id].get('resources', {})
    
    # دریافت اطلاعات رضایت مردم
    satisfaction_info = utils.format_satisfaction_info(user_id)
    
    # Immigration effects summary
    immigrants = utils.users[user_id].get('immigrants', 0)
    imm_units = immigrants // 1_000_000
    prod_bonus = imm_units * 5
    tax_bonus = imm_units * 10
    sat_pen = imm_units * 5
    rev_bonus = imm_units * 2

    text = f"⚖️ <b>وضعیت جمعیت کشور شما</b>\n\n"
    text += f"🏛️ <b>کشور:</b> {country_name}\n"
    text += f"👥 <b>جمعیت فعلی:</b> {user_population:,} نفر\n"
    text += f"📈 <b>نرخ رشد جمعیت:</b> {growth_rate:.2f}%\n"
    text += f"➕ <b>جمعیت اضافه شده:</b> {population_growth:,} نفر\n"
    text += f"💰 <b>مالیات دریافتی:</b> {tax_revenue:,} دلار\n\n"
    
    # اضافه کردن اطلاعات رضایت مردم
    text += f"{satisfaction_info}\n\n"
    
    # نمایش نیازمندی‌های غذایی
    text += "🍽️ <b>نیازمندی‌های غذایی:</b>\n"
    text += f"🌾 گندم: {requirements['wheat']} واحد (موجودی: {user_resources.get('wheat', 0)})\n"
    text += f"🍚 برنج: {requirements['rice']} واحد (موجودی: {user_resources.get('rice', 0)})\n"
    text += f"🍎 میوه: {requirements['fruits']} واحد (موجودی: {user_resources.get('fruits', 0)})\n\n"
    
    # Immigrants UI block
    text += "\n🛂 <b>مهاجران:</b> {:,}\n".format(immigrants)
    text += "📌 <b>اثرات فعال:</b> +{}% تولید | +{}% مالیات | -{}% رضایت | +{}% انقلاب\n\n".format(prod_bonus, tax_bonus, sat_pen, rev_bonus)

    # رتبه کشور کاربر
    user_rank = get_population_rank(country_name)
    percentage = get_population_percentage(country_name)
    
    text += f"🏆 <b>رتبه جهانی:</b> {user_rank} از {len(COUNTRY_POPULATIONS)}\n"
    text += f"🌍 <b>درصد از جمعیت جهان:</b> {percentage:.2f}%\n"
    
    # دکمه‌های مختلف بر اساس امکان دریافت مالیات
    if can_collect_tax:
        keyboard = [
            [InlineKeyboardButton('💰 مطالبه مالیات', callback_data='collect_tax')],
            [InlineKeyboardButton('❌ اخراج مهاجران', callback_data='deport_immigrants')],
            [InlineKeyboardButton('🛡️ سرکوب شورش', callback_data='suppress_revolution')],
            [InlineKeyboardButton('🔙 بازگشت', callback_data='back_to_game_menu')]
        ]
    else:
        remaining_turns = 2 - (current_turn - last_tax_collection)
        keyboard = [
            [InlineKeyboardButton(f'⏳ مطالبه مالیات ({remaining_turns} دور باقی)', callback_data='tax_waiting')],
            [InlineKeyboardButton('❌ اخراج مهاجران', callback_data='deport_immigrants')],
            [InlineKeyboardButton('🛡️ سرکوب شورش', callback_data='suppress_revolution')],
            [InlineKeyboardButton('🔙 بازگشت', callback_data='back_to_game_menu')]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def send_population_report_to_channel(bot):
    """ارسال گزارش جمعیت به گروه اخبار"""
    try:
        import utils
        
        # آمار کلی جهان
        total_world_population = get_world_population()
        categories = get_population_categories()
        current_date = get_current_date()
        
        text = f"📊 <b>آمار جمعیتی جهان - {current_date}</b>\n\n"
        text += f"🌍 <b>جمعیت کل جهان:</b> {total_world_population:,} نفر\n\n"
        
        # دسته‌بندی کشورها
        text += "📋 <b>دسته‌بندی کشورها:</b>\n"
        text += f"🔴 کشورهای پرجمعیت (100M به بالا): {len(categories['large'])} کشور\n"
        text += f"🟡 کشورهای متوسط (10M تا 100M): {len(categories['medium'])} کشور\n"
        text += f"🟢 کشورهای کم‌جمعیت (کمتر از 10M): {len(categories['small'])} کشور\n\n"
        
        # 10 کشور پرجمعیت در حالت quote
        top_countries = get_top_populated_countries(10)
        text += "🏆 <b>10 کشور پرجمعیت جهان:</b>\n"
        text += "<blockquote>"
        for i, (country, population) in enumerate(top_countries, 1):
            text += f"{i}. {country}: {population:,} نفر\n"
        text += "</blockquote>"
        
        # ارسال پیام بدون دکمه
        print(f"تلاش برای ارسال پیام به: {utils.NEWS_CHANNEL_ID}")
        result = await bot.send_message(
            chat_id=utils.NEWS_CHANNEL_ID,
            text=text,
            parse_mode='HTML'
        )
        print(f"پیام با موفقیت ارسال شد: {result.message_id}")
        
        return True
    except Exception as e:
        print(f"خطا در ارسال گزارش جمعیت به گروه: {e}")
        print(f"نوع خطا: {type(e).__name__}")
        return False

async def send_economy_report_to_channel(bot):
    """ارسال گزارش اقتصادی به گروه اخبار"""
    try:
        import utils
        
        # آمار کلی جهان
        total_world_economy = get_world_economy()
        categories = get_economy_categories()
        current_date = get_current_date()
        
        text = f"💎 <b>آمار اقتصادی جهان - {current_date}</b>\n\n"
        text += f"🌍 <b>اقتصاد کل جهان:</b> {total_world_economy:,} دلار\n\n"
        
        # دسته‌بندی کشورها
        text += "📋 <b>دسته‌بندی کشورها:</b>\n"
        text += f"🔴 کشورهای با اقتصاد قوی (1B+ دلار): {len(categories['large'])} کشور\n"
        text += f"🟡 کشورهای با اقتصاد متوسط (100M تا 1B دلار): {len(categories['medium'])} کشور\n"
        text += f"🟢 کشورهای با اقتصاد ضعیف (کمتر از 100M دلار): {len(categories['small'])} کشور\n\n"
        
        # 10 کشور با اقتصاد قوی در حالت quote
        top_countries = get_top_economy_countries(10)
        text += "🏆 <b>10 کشور با اقتصاد قوی جهان:</b>\n"
        text += "<blockquote>"
        for i, (country, economy) in enumerate(top_countries, 1):
            text += f"{i}. {country}: {economy:,} دلار\n"
        text += "</blockquote>"
        
        # ارسال پیام بدون دکمه
        print(f"تلاش برای ارسال گزارش اقتصادی به: {utils.NEWS_CHANNEL_ID}")
        result = await bot.send_message(
            chat_id=utils.NEWS_CHANNEL_ID,
            text=text,
            parse_mode='HTML'
        )
        print(f"گزارش اقتصادی با موفقیت ارسال شد: {result.message_id}")
        
        return True
    except Exception as e:
        print(f"خطا در ارسال گزارش اقتصادی به گروه: {e}")
        print(f"نوع خطا: {type(e).__name__}")
        return False

async def show_my_country_population(query):
    """نمایش اطلاعات جمعیت کشور کاربر"""
    import utils
    user_id = str(query.from_user.id)
    
    if user_id not in utils.users or not utils.users[user_id].get('activated', False):
        await query.answer('شما هنوز کشور فعال نکرده‌اید!', show_alert=True)
        return
    
    country_name = utils.users[user_id]['country']
    user_population = get_country_population(country_name)
    user_rank = get_population_rank(country_name)
    percentage = get_population_percentage(country_name)
    
    text = f"👤 <b>اطلاعات جمعیت کشور شما</b>\n\n"
    text += f"🏛️ <b>کشور:</b> {country_name}\n"
    text += f"👥 <b>جمعیت:</b> {user_population:,} نفر\n"
    text += f"🏆 <b>رتبه جهانی:</b> {user_rank} از {len(COUNTRY_POPULATIONS)}\n"
    text += f"🌍 <b>درصد از جمعیت جهان:</b> {percentage:.2f}%\n\n"
    
    # مقایسه با کشورهای همسایه (اگر وجود داشته باشد)
    categories = get_population_categories()
    if country_name in categories['large']:
        text += "🔴 <b>دسته‌بندی:</b> کشور پرجمعیت (100M به بالا)\n"
    elif country_name in categories['medium']:
        text += "🟡 <b>دسته‌بندی:</b> کشور متوسط (10M تا 100M)\n"
    else:
        text += "🟢 <b>دسته‌بندی:</b> کشور کم‌جمعیت (کمتر از 10M)\n"
    
    await query.answer(text, show_alert=True)

def save_population_data():
    """ذخیره داده‌های جمعیت در فایل"""
    try:
        with open('population_data.json', 'w', encoding='utf-8') as f:
            json.dump(COUNTRY_POPULATIONS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"خطا در ذخیره داده‌های جمعیت: {e}")

def load_population_data():
    """بارگذاری داده‌های جمعیت از فایل"""
    global COUNTRY_POPULATIONS
    try:
        with open('population_data.json', 'r', encoding='utf-8') as f:
            COUNTRY_POPULATIONS = json.load(f)
    except FileNotFoundError:
        # اگر فایل وجود نداشت، از داده‌های پیش‌فرض استفاده کن
        pass
    except Exception as e:
        print(f"خطا در بارگذاری داده‌های جمعیت: {e}")

def save_tax_data():
    """ذخیره اطلاعات مالیات کاربران در فایل"""
    import utils
    try:
        tax_data = {}
        for user_id, user_data in utils.users.items():
            if 'last_tax_collection' in user_data:
                tax_data[user_id] = {
                    'last_tax_collection': user_data['last_tax_collection']
                }
        
        with open('tax_data.json', 'w', encoding='utf-8') as f:
            json.dump(tax_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"خطا در ذخیره اطلاعات مالیات: {e}")

def load_tax_data():
    """بارگذاری اطلاعات مالیات کاربران از فایل"""
    import utils
    try:
        with open('tax_data.json', 'r', encoding='utf-8') as f:
            tax_data = json.load(f)
            
        for user_id, tax_info in tax_data.items():
            if user_id in utils.users:
                utils.users[user_id]['last_tax_collection'] = tax_info.get('last_tax_collection', 0)
    except FileNotFoundError:
        # اگر فایل وجود نداشت، مشکلی نیست
        pass
    except Exception as e:
        print(f"خطا در بارگذاری اطلاعات مالیات: {e}")

# بارگذاری داده‌ها در هنگام import
load_population_data()
load_tax_data()

# اضافه کردن handler های جدید به bot.py
async def handle_population_callbacks(query):
    """مدیریت callback های مربوط به جمعیت"""
    import utils
    if query.data == 'my_country_population':
        await show_my_country_population(query)
    elif query.data == 'collect_tax':
        success, message = collect_tax(str(query.from_user.id))
        if success:
            await query.answer(message, show_alert=True)
        else:
            await query.answer(message, show_alert=True)
    elif query.data == 'tax_waiting':
        current_turn = utils.game_data['turn']
        last_tax_collection = utils.users[str(query.from_user.id)].get('last_tax_collection', 0)
        remaining_turns = 2 - (current_turn - last_tax_collection)
        await query.answer(f"شما باید {remaining_turns} دور دیگر صبر کنید تا بتوانید مالیات دریافت کنید.", show_alert=True)
    elif query.data == 'deport_immigrants':
        uid = str(query.from_user.id)
        try:
            immigrants_before = utils.users.get(uid, {}).get('immigrants', 0)
            utils.users[uid]['immigrants'] = 0
            # Apply instant effects: +5% satisfaction, -2% revolution, +0.5% population growth for next 3 turns
            utils.users[uid]['satisfaction'] = min(100, utils.users[uid].get('satisfaction', 70) + 5)
            utils.users[uid]['revolution'] = max(0, utils.users[uid].get('revolution', 0) - 2)
            # store temporary growth buff tracker
            buffs = utils.users[uid].setdefault('temporary_buffs', {})
            buffs['growth_buff_turns'] = 3
            buffs['growth_buff_rate'] = buffs.get('growth_buff_rate', 0.0) + 0.5
            utils.save_users()
            # پیام به خود کاربر
            await query.answer(f"❌ {immigrants_before:,} مهاجر اخراج شدند. اثرات اعمال شد.", show_alert=True)

            # ارسال گزارش به کانال اخبار با گیف اخراج مهاجران
            try:
                country_name = utils.users.get(uid, {}).get('country', 'کشور نامشخص')
                try:
                    bot_inst = query.get_bot() if hasattr(query, 'get_bot') else query.bot
                except Exception:
                    bot_inst = None
                if bot_inst and immigrants_before > 0:
                    news_text = (
                        f"❌ <b>اخراج مهاجران</b>\n\n"
                        f"کشور {country_name} تعداد {immigrants_before:,} مهاجر را از کشور خود اخراج کرد.\n\n"
                        f"📉 اثرات داخلی: افزایش رضایت، کاهش ریسک انقلاب و رشد جمعیت موقت."
                    )
                    from utils import NEWS_CHANNEL_ID
                    deport_gif = "https://t.me/TextEmpire_IR/131"
                    await bot_inst.send_animation(
                        chat_id=NEWS_CHANNEL_ID,
                        animation=deport_gif,
                        caption=news_text,
                        parse_mode='HTML'
                    )
            except Exception as e:
                print(f"deport_immigrants news send error: {e}")
        except Exception:
            await query.answer("خطا در اخراج مهاجران.", show_alert=True)
