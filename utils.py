import json
import time
from datetime import datetime
import random
import os

users = {}
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
pending_military_production = {}
pending_statement = {}
pending_alliance_chat = {}

pending_help_request = {}
pending_peace_requests = {}
pending_relation_action = {} 
relation_improvement_requests = {} 
embassy_requests = {} 
embassies = {} 
pending_create_alliance = {}
pending_set_deputy = {}
pending_ground_attack = {}  # {user_id: {'target': target_id, 'step': 'amount'}}
pending_air_attack = {}  # {user_id: {'target': target_id, 'step': 'amount'}}
pending_war_declaration = {}  # {user_id: target_id}
alliance_messages = {}
# متغیرهای سیستم حمله دریایی
pending_naval_attack = {}  # {user_id: {'target': target_id, 'step': 'amount'}}
naval_attacks = {}  # {attack_id: {'attacker_id': user_id, 'target_id': target_id, 'attacker_forces': {...}, 'target_forces': {...}, 'start_time': timestamp, 'phase': 0}}
naval_attack_counter = 0  # شمارنده برای شناسه‌های حمله
pending_sea_raid = {}
alliances = {}
user_alliances = {}

# متغیرهای بانکی
overdue_debts = {}  # بدهی‌های معوق

# سیستم ذخیره‌سازی حمله دریایی
naval_attack_saves = {}  # {user_id: {'target_id': target_id, 'forces': {...}, 'timestamp': time}}

alliance_leave_turn = {}
pending_global_trade = {}
pending_edit_alliance = {}
alliance_help_requests = {}  
pending_help_give = {}
pending_national_security = {}  # {user_id: {'step': 'ask_name', 'name': None, 'description': None, 'logo_file_id': None, 'features': {}}} 
pending_assassination_respawn = {}  # {user_id: {'original_name': '', 'original_title': '', 'country': ''}}
country_relations = {}
war_declarations = {}
pending_activation = {}
pending_sell_amount = {}
pending_sell_total_price = {}
pending_government_selection = {}
pending_name_selection = {}
pending_country_slogan = {}
pending_minister_selection = {}
pending_general_selection = {}
pending_foreign_selection = {}
pending_finance_selection = {}
LAND_BORDERS = {}
SEA_BORDER_COUNTRIES = []
SEA_BORDER_COUNTRIES_NORMALIZED = set()
pending_trades = []
pending_sea_raid = {}  # {user_id: trade_id}
pending_payments = {}  # {user_id: {credits_amount, price, status}}
game_data = {'turn': 1, 'game_date': '01/01/2024', 'prices': {'gold': 5000000}}

# ------------------------------- سیستم آب‌وهوا -------------------------------
# حالت‌های آب‌وهوا: 'sunny' (آفتابی و خشک) / 'normal' (معمولی) / 'rainy' (بارانی) / 'snowy' (برفی)
# مقدار فعلی در game_data['weather'] ذخیره می‌شود. در صورت نبود، پیش‌فرض 'normal' است.

WEATHER_FILE_IDS = {
    # لینک/GIFهای تلگرام برای اطلاع‌رسانی آب‌وهوا در کانال
    'sunny': 'https://t.me/TextEmpire_IR/187',   # آفتابی و خشک
    'normal': 'https://t.me/TextEmpire_IR/186',  # معمولی
    'rainy': 'https://t.me/TextEmpire_IR/188',   # بارانی
    'snowy': 'https://t.me/TextEmpire_IR/185',   # برفی
}

def get_current_weather() -> str:
    return game_data.get('weather') or 'normal'

def get_weather_fa_title(weather: str) -> str:
    mapping = {
        'sunny': 'آفتابی و خشک',
        'normal': 'معمولی',
        'rainy': 'بارانی',
        'snowy': 'برفی',
    }
    return mapping.get(weather, 'معمولی')

def get_weather_modifiers(weather: str) -> dict:
    """ضرایب تاثیر آب‌وهوا بر نبردها.
    مقادیر بازگشتی:
      - attacker_casualty_mul: ضریب تلفات حمله‌کننده
      - defender_casualty_mul: ضریب تلفات مدافع
      - attacker_power_mul: ضریب قدرت تهاجمی
      - defender_power_mul: ضریب قدرت دفاعی
    """
    if weather == 'sunny':
        return {
            'attacker_casualty_mul': 0.9,
            'defender_casualty_mul': 1.0,
            'attacker_power_mul': 1.05,
            'defender_power_mul': 1.0,
        }
    if weather == 'rainy':
        return {
            'attacker_casualty_mul': 1.1,
            'defender_casualty_mul': 0.95,
            'attacker_power_mul': 0.95,
            'defender_power_mul': 1.0,
        }
    if weather == 'snowy':
        return {
            'attacker_casualty_mul': 1.25,
            'defender_casualty_mul': 1.15,
            'attacker_power_mul': 0.9,
            'defender_power_mul': 0.95,
        }
    # normal
    return {
        'attacker_casualty_mul': 1.0,
        'defender_casualty_mul': 1.0,
        'attacker_power_mul': 1.0,
        'defender_power_mul': 1.0,
    }

# ------------------------------- مدیریت رهبری اتحاد -------------------------------
def transfer_alliance_on_leader_loss(leader_id: str):
    """
    وقتی رهبر اتحاد غیرفعال/فتح می‌شود، رهبری را به جانشین یا اولین عضو منتقل می‌کند.
    اگر هیچ عضوی نماند، اتحاد حذف می‌شود.
    خروجی:
      None اگر نیازی به انتقال نباشد
      dict{'alliance_id','alliance_name','new_leader'} در صورت انتقال
      dict{'alliance_id','alliance_name','deleted':True} در صورت حذف اتحاد
    """
    alliance_id = user_alliances.get(leader_id)
    if not alliance_id or alliance_id not in alliances:
        return None
    alliance = alliances[alliance_id]
    if alliance.get('leader') != leader_id:
        return None

    members = list(dict.fromkeys(alliance.get('members', [])))
    # حذف رهبر قبلی از لیست اعضا
    if leader_id in members:
        members.remove(leader_id)
    alliance['members'] = members

    # اگر خود رهبر جانشین بوده، ریست شود
    if alliance.get('deputy') == leader_id:
        alliance['deputy'] = None

    deputy_id = alliance.get('deputy')
    new_leader = None
    if deputy_id and deputy_id in members:
        new_leader = deputy_id
    elif members:
        new_leader = members[0]

    if new_leader:
        alliance['leader'] = new_leader
        alliance['deputy'] = None
        if new_leader not in alliance['members']:
            alliance['members'].append(new_leader)
        # حذف نگاشت رهبر سابق
        user_alliances.pop(leader_id, None)
        save_alliances()
        return {
            'alliance_id': alliance_id,
            'alliance_name': alliance.get('name', 'اتحاد'),
            'new_leader': new_leader
        }

    # اگر هیچ عضوی باقی نماند، اتحاد حذف می‌شود
    for uid in list(members):
        if user_alliances.get(uid) == alliance_id:
            user_alliances.pop(uid, None)
    user_alliances.pop(leader_id, None)
    alliances.pop(alliance_id, None)
    save_alliances()
    return {
        'alliance_id': alliance_id,
        'alliance_name': alliance.get('name', 'اتحاد'),
        'deleted': True
    }

def format_weather_effects_text(weather: str) -> str:
    mods = get_weather_modifiers(weather)
    title = get_weather_fa_title(weather)
    # نمایش مختصر تاثیرات کلیدی برای پیام کانال
    lines = [
        f"🌤 وضعیت آب‌وهوا: {title}",
    ]
    if weather == 'sunny':
        lines.append('✅ روحیه و مانورپذیری بالاست: قدرت حمله +5%، تلفات حمله‌کننده −10%')
    elif weather == 'rainy':
        lines.append('🌧 گل‌آلودگی و دید کم: قدرت حمله −5%، تلفات حمله‌کننده +10%')
    elif weather == 'snowy':
        lines.append('❄️ سرما و یخبندان: قدرت‌ها کاهش و تلفات افزایش می‌یابد (حمله‌کننده بیشتر)')
    else:
        lines.append('ℹ️ شرایط عادی: تاثیر خاصی اعمال نمی‌شود')
    return '\n'.join(lines)
player_sell_ads = []
# --- متغیرهای ثابت و شناسه‌ها ---
ADMIN_ID = '6602925597'  # شناسه تلگرام ادمین

ADMIN_USERNAME = 'admin'  # نام کاربری ادمین
CHANNEL_ID = '@TextEmpireNews'  # شناسه کانال اخبار برای ارسال اعلان‌ها

# متغیر برای ذخیره کاربر فعال سازمان ملل
UN_ACTIVATED_USER = None

# متغیر برای ذخیره وضعیت درخواست فعال‌سازی سازمان ملل
pending_un_activation = None

# متغیر برای ذخیره درخواست‌های آتش بس
ceasefire_requests = {}

# Military Packages System Configuration
MILITARY_PACKAGES = {
    'hidden_eyes': {
        'name': 'پکیج چشم‌های پنهان',
        'emoji': '♟',
        'price': 50,
        'max_per_season': 5,
        'cooldown_hours': 24,
        'requires_admin_approval': False,
        'units': {
            'soldiers': 25000,
            'special_forces': 1000,
            'tanks': 25,
            'armored_vehicles': 500,
            'artillery': 25,
            'combat_robots': 250,
            'transport_planes': 10,
            'helicopters': 25,
            'fighter_jets': 25,
            'bombers': 1,
            'drones': 25,
            'air_defense': 10,
            'coastal_artillery': 10,
            'speedboats': 50,
            'frigates': 15,
            'submarines': 5,
            'aircraft_carriers': 0
        }
    },
    'thunder_fleet': {
        'name': 'پکیج ناوگان تندر',
        'emoji': '⚓️',
        'price': 150,
        'max_per_season': 3,
        'cooldown_hours': 24,
        'requires_admin_approval': False,
        'units': {
            'soldiers': 75000,
            'special_forces': 3000,
            'tanks': 100,
            'armored_vehicles': 1500,
            'artillery': 75,
            'combat_robots': 800,
            'transport_planes': 30,
            'helicopters': 75,
            'fighter_jets': 60,
            'bombers': 3,
            'drones': 75,
            'air_defense': 30,
            'coastal_artillery': 20,
            'speedboats': 150,
            'frigates': 35,
            'submarines': 10,
            'aircraft_carriers': 0
        }
    },
    'iron_legion': {
        'name': 'پکیج لشکر آهنین',
        'emoji': '🪖',
        'price': 400,
        'max_per_season': 1,
        'cooldown_hours': 24,
        'requires_admin_approval': False,
        'units': {
            'soldiers': 200000,
            'special_forces': 8000,
            'tanks': 400,
            'armored_vehicles': 4000,
            'artillery': 200,
            'combat_robots': 2500,
            'transport_planes': 80,
            'helicopters': 220,
            'fighter_jets': 180,
            'bombers': 8,
            'drones': 200,
            'air_defense': 80,
            'coastal_artillery': 50,
            'speedboats': 300,
            'frigates': 80,
            'submarines': 25,
            'aircraft_carriers': 1
        }
    },
    'sky_eagles': {
        'name': 'پکیج عقاب‌های آسمان',
        'emoji': '✈️',
        'price': 1000,
        'max_per_season': 1,
        'cooldown_hours': 24,
        'requires_admin_approval': False,
        'units': {
            'soldiers': 600000,
            'special_forces': 25000,
            'tanks': 1200,
            'armored_vehicles': 12000,
            'artillery': 600,
            'combat_robots': 7500,
            'transport_planes': 250,
            'helicopters': 700,
            'fighter_jets': 600,
            'bombers': 25,
            'drones': 700,
            'air_defense': 100,
            'coastal_artillery': 100,
            'speedboats': 1000,
            'frigates': 150,
            'submarines': 40,
            'aircraft_carriers': 4
        }
    },
    'united_armies': {
        'name': 'پکیج ارتش‌های متحد',
        'emoji': '🎖',
        'price': 2500,
        'max_per_season': 1,
        'cooldown_hours': 24,
        'requires_admin_approval': True,
        'units': {
            'soldiers': 1500000,
            'special_forces': 60000,
            'tanks': 3000,
            'armored_vehicles': 35000,
            'artillery': 1500,
            'combat_robots': 20000,
            'transport_planes': 500,
            'helicopters': 2000,
            'fighter_jets': 1800,
            'bombers': 50,
            'drones': 2000,
            'air_defense': 250,
            'coastal_artillery': 250,
            'speedboats': 1500,
            'frigates': 500,
            'submarines': 100,
            'aircraft_carriers': 10
        }
    }
}

# Military package purchase tracking
military_package_purchases = {}  # {user_id: {package_key: [{'date': str, 'turn': int}]}}
military_package_cooldowns = {}  # {user_id: {package_key: timestamp}}
military_package_approvals = {}  # {user_id: {package_key: {'status': 'pending'|'approved'|'rejected', 'admin_id': str, 'date': str}}}

# Economic Packages System Configuration
ECONOMIC_PACKAGES = {
    'needy': {
        'name': 'پکیج نیازمند',
        'emoji': '🆘',
        'price': 50,
        'money_amount': 50_000_000,  # 50M
        'max_per_season': 10,
        'cooldown_hours': 24,
        'requires_admin_approval': False
    },
    'peasant': {
        'name': 'پکیج رعیت',
        'emoji': '👨‍🌾',
        'price': 200,
        'money_amount': 200_000_000,  # 200M
        'max_per_season': 4,
        'cooldown_hours': 24,
        'requires_admin_approval': False
    },
    'merchant': {
        'name': 'پکیج تاجر',
        'emoji': '👨‍💼',
        'price': 500,
        'money_amount': 500_000_000,  # 500M
        'max_per_season': 2,
        'cooldown_hours': 24,
        'requires_admin_approval': False
    },
    'minister': {
        'name': 'پکیج وزیر رعیا',
        'emoji': '👨‍💻',
        'price': 1000,
        'money_amount': 1_000_000_000,  # 1B
        'max_per_season': 1,
        'cooldown_hours': 24,
        'requires_admin_approval': False
    },
    'king': {
        'name': 'پکیج پادشاه',
        'emoji': '👑',
        'price': 4999,
        'money_amount': 10_000_000_000,  # 10B
        'max_per_season': 1,
        'cooldown_hours': 24,
        'requires_admin_approval': True
    }
}

# Resource packages configuration
RESOURCE_PACKAGES = {
    'urgent': {
        'name': 'پکیج فوری',
        'cost': 50,
        'season_limit': 10,
        'cooldown_hours': 24,
        'requires_admin_approval': False,
        'resources': {
            'gold': 10,
            'steel': 100,
            'iron': 100,
            'copper': 100,
            'diamond': 5,
            'aluminum': 100,
            'titanium': 50,
            'oil': 500,
            'gas': 500,
            'electricity': 100,
            'uranium': 1,
            'uranium_ore': 100,
            'centrifuge': 10,
            'yellow_cake': 100,
            'wheat': 100,
            'rice': 100,
            'fruits': 100,
            'electronics': 100000,
            'space_parts': 1,
            'pride_cars': 10000,
            'benz_cars': 2000
        }
    },
    'emerging_power': {
        'name': 'پکیج قدرت نوظهور',
        'cost': 150,
        'season_limit': 5,
        'cooldown_hours': 24,
        'requires_admin_approval': False,
        'resources': {
            'gold': 50,
            'steel': 500,
            'iron': 500,
            'copper': 500,
            'diamond': 25,
            'aluminum': 500,
            'titanium': 200,
            'oil': 2000,
            'gas': 2000,
            'electricity': 500,
            'uranium': 5,
            'uranium_ore': 500,
            'centrifuge': 30,
            'yellow_cake': 500,
            'wheat': 500,
            'rice': 500,
            'fruits': 500,
            'electronics': 500000,
            'space_parts': 5,
            'pride_cars': 50000,
            'benz_cars': 10000
        }
    },
    'regional_power': {
        'name': 'پکیج قدرت منطقه‌ای',
        'cost': 400,
        'season_limit': 3,
        'cooldown_hours': 24,
        'requires_admin_approval': False,
        'resources': {
            'gold': 200,
            'steel': 2000,
            'iron': 2000,
            'copper': 2000,
            'diamond': 100,
            'aluminum': 2000,
            'titanium': 800,
            'oil': 10000,
            'gas': 10000,
            'electricity': 2000,
            'uranium': 20,
            'uranium_ore': 2000,
            'centrifuge': 100,
            'yellow_cake': 2000,
            'wheat': 2000,
            'rice': 2000,
            'fruits': 2000,
            'electronics': 2000000,
            'space_parts': 20,
            'pride_cars': 200000,
            'benz_cars': 50000
        }
    },
    'superpower': {
        'name': 'پکیج ابرقدرت',
        'cost': 1000,
        'season_limit': 1,
        'cooldown_hours': 24,
        'requires_admin_approval': False,
        'resources': {
            'gold': 1000,
            'steel': 10000,
            'iron': 10000,
            'copper': 10000,
            'diamond': 500,
            'aluminum': 10000,
            'titanium': 4000,
            'oil': 50000,
            'gas': 50000,
            'electricity': 10000,
            'uranium': 100,
            'uranium_ore': 10000,
            'centrifuge': 300,
            'yellow_cake': 10000,
            'wheat': 10000,
            'rice': 10000,
            'fruits': 10000,
            'electronics': 10000000,
            'space_parts': 100,
            'pride_cars': 1000000,
            'benz_cars': 200000
        }
    },
    'emperor': {
        'name': 'پکیج امپراطور',
        'cost': 4999,
        'season_limit': 1,
        'cooldown_hours': 24,
        'requires_admin_approval': True,
        'resources': {
            'gold': 5000,
            'steel': 50000,
            'iron': 50000,
            'copper': 50000,
            'diamond': 2500,
            'aluminum': 50000,
            'titanium': 20000,
            'oil': 200000,
            'gas': 200000,
            'electricity': 50000,
            'uranium': 500,
            'uranium_ore': 50000,
            'centrifuge': 1000,
            'yellow_cake': 50000,
            'wheat': 50000,
            'rice': 50000,
            'fruits': 50000,
            'electronics': 50000000,
            'space_parts': 500,
            'pride_cars': 5000000,
            'benz_cars': 1000000
        }
    }
}

# Economic package purchase tracking
economic_package_purchases = {}  # {user_id: {package_key: [{'date': str, 'turn': int, 'amount': int}]}}
economic_package_cooldowns = {}  # {user_id: {package_key: timestamp}}
economic_package_approvals = {}  # {user_id: {package_key: {'status': 'pending'|'approved'|'rejected', 'admin_id': str, 'date': str}}}

# Resource package purchase tracking
resource_package_purchases = {}  # {user_id: {package_key: [{'date': str, 'turn': int, 'amount': int}]}}
resource_package_cooldowns = {}  # {user_id: {package_key: timestamp}}
resource_package_approvals = {}  # {user_id: {package_key: {'status': 'pending'|'approved'|'rejected', 'admin_id': str, 'date': str}}}

# امتیاز صلح کشورها (بر اساس موافقت/مخالفت با آتش‌بس سازمان ملل)
un_peace_scores = {}  # {country_name: score}

# برندگان جایزه صلح
un_peace_prize_winners = []  # [{'country': str, 'turn': int}]

# آخرین دوری که جایزه صلح اعطا شده
last_peace_prize_award_turn = 0

# قطعنامه‌های سازمان ملل
un_resolutions = []  # [{'number': 1234, 'type': 'sanction', 'sanction_kind': 'economic'|'military'|'diplomatic', 'target_country': str, 'reason': str, 'concern': str, 'necessity': str, 'status': 'voting'|'adopted'|'rejected'|'revote', 'created_by': user_id, 'created_turn': int, 'votes': {user_id: 'yes'|'no'|'abstain'}, 'tally': {'yes': int, 'no': int, 'abstain': int}}]

# وضعیت موقت پیش‌نویس قطعنامه (ویزارد)
pending_un_resolution_draft = {}  # {user_id: {'step': str, 'sanction_kind': str|None, 'target_country': str|None, 'reason': str|None, 'concern': str|None, 'necessity': str|None, 'number': int|None}}

# سیستم تحریم کشورها
sanctions = {}  # {sanctioning_country: [target_countries]}
pending_sanction = {}  # {user_id: {'target_country': str, 'step': 'confirm'}}

# شکایت‌های ارسالی به سازمان ملل
un_complaints = []  # [{'id': str, 'from_user_id': str, 'from_country': str, 'text': str, 'status': 'submitted'|'reviewed'|'closed', 'created_turn': int, 'created_at': int}]
pending_un_complaint = {}  # {user_id: {'step': 'text'}}

# سیستم برگزاری دادگاه سازمان ملل
un_courts = []  # [{'id': str, 'topic': str, 'plaintiff': str, 'defendant': str, 'time': str, 'location': str, 'status': 'scheduled'|'ongoing'|'completed', 'created_by': str, 'created_turn': int, 'created_at': int}]
pending_un_court = {}  # {user_id: {'step': str, 'topic': str|None, 'plaintiff': str|None, 'defendant': str|None, 'time': str|None, 'location': str|None}}
pending_court_edit = {}  # {user_id: {'court_id': str, 'field': str}}

# وضعیت موقت عملیات مخفی (ترور)
# { user_id: { 'step': str, 'countries': [str], 'selected_country': str } }
pending_assassination = {}
pending_assassination_jobs = []  # [{'attacker_id': str, 'target_id': str, 'role': str, 'started_at': int, 'eta_sec': int}]
# Pending state for assassination victim respawn (new name input)
pending_assassination_respawn = {}
# Pending state for private messaging
pending_private_message = {}
# مینی‌گیم ترور: {game_id: {...}}
assassination_games = {}

# فلگ‌های انیمیشن لودینگ (در حافظه، بدون پایداری)
# کلید: str(message_id) => True/False
loading_flags = {}

# توابع ذخیره‌سازی اطلاعات سازمان ملل
def load_un_data():
    """بارگذاری اطلاعات سازمان ملل از فایل"""
    global UN_ACTIVATED_USER, pending_un_activation, ceasefire_requests, un_peace_scores, un_peace_prize_winners, last_peace_prize_award_turn, un_resolutions, sanctions, pending_sanction, un_complaints, pending_un_complaint, un_courts, pending_un_court
    try:
        with open('united_nations_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            UN_ACTIVATED_USER = data.get('un_activated_user')
            pending_un_activation = data.get('pending_un_activation')
            ceasefire_requests = data.get('ceasefire_requests', {})
            un_peace_scores = data.get('un_peace_scores', {})
            un_peace_prize_winners = data.get('un_peace_prize_winners', [])
            last_peace_prize_award_turn = data.get('last_peace_prize_award_turn', 0)
            un_resolutions = data.get('un_resolutions', [])
            sanctions = data.get('sanctions', {})
            pending_sanction = data.get('pending_sanction', {})
            un_complaints = data.get('un_complaints', [])
            pending_un_complaint = data.get('pending_un_complaint', {})
            un_courts = data.get('un_courts', [])
            pending_un_court = data.get('pending_un_court', {})
            pending_court_edit = data.get('pending_court_edit', {})
    except FileNotFoundError:
        print("[INFO] فایل united_nations_data.json یافت نشد. استفاده از مقادیر پیش‌فرض.")
    except Exception as e:
        print(f"[ERROR] خطا در بارگذاری اطلاعات سازمان ملل: {e}")
    
    # پاک‌سازی خودکار غیرفعال شد - اطلاعات سازمان ملل حفظ می‌شه
    # cleanup_deleted_un_users()

def cleanup_deleted_un_users():
    """پاک کردن کاربران سازمان ملل که حذف شدن"""
    global UN_ACTIVATED_USER, pending_un_activation
    cleaned = False
    
    # کاربر سازمان ملل را به کاربران عادی وابسته نمی‌کنیم؛ پاک‌سازی خودکار انجام نمی‌شود
    
    # بررسی کاربر در انتظار فعال‌سازی
    # pending_un_activation نیز مستقل مدیریت می‌شود
    
    # اگر تغییری بود، ذخیره کن
    if cleaned:
        save_un_data()
        print("[DEBUG] اطلاعات سازمان ملل پاک شد")
    
    return cleaned

def manual_cleanup_un_users():
    """پاک‌سازی دستی کاربران سازمان ملل - فقط در صورت نیاز"""
    print("[DEBUG] پاک‌سازی دستی کاربران سازمان ملل فراخوانی شد")
    return cleanup_deleted_un_users()

def save_un_data():
    """ذخیره اطلاعات سازمان ملل در فایل"""
    try:
        data = {
            'un_activated_user': UN_ACTIVATED_USER,
            'pending_un_activation': pending_un_activation,
            'ceasefire_requests': ceasefire_requests,
            'un_peace_scores': un_peace_scores,
            'un_peace_prize_winners': un_peace_prize_winners,
            'last_peace_prize_award_turn': last_peace_prize_award_turn,
            'un_resolutions': un_resolutions,
            'sanctions': sanctions,
            'pending_sanction': pending_sanction,
            'un_complaints': un_complaints,
            'pending_un_complaint': pending_un_complaint,
            'un_courts': un_courts,
            'pending_un_court': pending_un_court,
            'pending_court_edit': pending_court_edit
        }
        with open('united_nations_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] خطا در ذخیره اطلاعات سازمان ملل: {e}")

def is_country_under_un_economic_sanction(country_name: str) -> bool:
    """بررسی می‌کند آیا کشور تحت تحریم اقتصادی مصوب UN و داخل بازه زمانی است یا خیر."""
    try:
        current_turn = game_data.get('turn', 1)
    except Exception:
        current_turn = 1
    for r in un_resolutions:
        if r.get('sanction_kind') == 'economic' and r.get('status') == 'adopted':
            target = r.get('target_country')
            eff = r.get('effective_turn')
            exp = r.get('expires_at_turn')
            if target == country_name and eff is not None and exp is not None and eff <= current_turn <= exp:
                return True
    return False

def validate_un_user_after_load():
    """بررسی اعتبار کاربر سازمان ملل بعد از بارگذاری users"""
    global UN_ACTIVATED_USER, pending_un_activation
    
    print(f"[DEBUG] validate_un_user_after_load() شروع شد")
    print(f"[DEBUG] UN_ACTIVATED_USER قبل از بررسی: {UN_ACTIVATED_USER}")
    print(f"[DEBUG] pending_un_activation قبل از بررسی: {pending_un_activation}")
    print(f"[DEBUG] تعداد کاربران بارگذاری شده: {len(users)}")
    print(f"[DEBUG] کلیدهای کاربران: {list(users.keys())}")
    
    # هیچ پاک‌سازی بر اساس users انجام نمی‌دهیم؛ UN مستقل است
    
    print(f"[DEBUG] UN_ACTIVATED_USER بعد از بررسی: {UN_ACTIVATED_USER}")
    print(f"[DEBUG] pending_un_activation بعد از بررسی: {pending_un_activation}")
    
    # هیچ بررسی دیگری لازم نیست

def reset_un_data():
    """ریست کردن اطلاعات سازمان ملل"""
    global UN_ACTIVATED_USER, pending_un_activation, ceasefire_requests, un_peace_scores, un_peace_prize_winners, last_peace_prize_award_turn, un_resolutions, sanctions, pending_sanction, un_complaints, pending_un_complaint, un_courts, pending_un_court
    UN_ACTIVATED_USER = None
    pending_un_activation = None
    ceasefire_requests = {}
    un_peace_scores = {}
    un_peace_prize_winners = []
    last_peace_prize_award_turn = 0
    un_resolutions = []
    sanctions = {}
    pending_sanction = {}
    un_complaints = []
    pending_un_complaint = {}
    un_courts = []
    pending_un_court = {}
    save_un_data()
    print("[DEBUG] اطلاعات سازمان ملل ریست شد")
NEWS_CHANNEL_ID = '@TextEmpire_News'  # شناسه گروه اخبار
# گروه برگزاری دادگاه‌ها (برای ساخت لینک دعوت یک‌بارمصرف)
COURT_GROUP_ID = -1003124454628
SEASON_END_PHOTO_ID = 'https://t.me/TextEmpire_IR/104'  # فایل‌آیدی/لینک عکس پایان فصل

# سیستم بن کاربران
BANNED_USERS_FILE = 'banned_users.json'
banned_users = set()
pending_admin_ban = False  # ادمین در حال وارد کردن آیدی برای بن

# سیستم ثبت‌نام کاربران
pending_registration = {}  # {user_id: {'step': 'phone'|'location', 'phone': str|None}}
pending_admin_ban = False  # ادمین در حال وارد کردن آیدی برای بن
pending_admin_auto_profile = False  # ادمین در حال وارد کردن آیدی برای ساخت پروفایل خودکار

# سیستم تأیید موقعیت
LOCATION_VERIFICATION_FILE = 'location_verification.json'
location_verification_data = {}  # {user_id: {'latitude': float, 'longitude': float, 'location_attempts': int, 'location_verified': bool, 'status': str}}

def load_location_verification():
    """Load location verification data from JSON file"""
    global location_verification_data
    try:
        with open(LOCATION_VERIFICATION_FILE, 'r', encoding='utf-8') as f:
            location_verification_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        location_verification_data = {}

def save_location_verification():
    """Save location verification data to JSON file"""
    try:
        with open(LOCATION_VERIFICATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(location_verification_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving location verification data: {e}")

def add_location_verification(user_id: str, latitude: float, longitude: float):
    """Add new location verification request"""
    location_verification_data[user_id] = {
        'latitude': latitude,
        'longitude': longitude,
        'location_attempts': 0,
        'location_verified': False,
        'status': 'pending'
    }
    save_location_verification()

def approve_location(user_id: str):
    """Approve user location verification"""
    if user_id in location_verification_data:
        location_verification_data[user_id]['status'] = 'verified'
        location_verification_data[user_id]['location_verified'] = True
        save_location_verification()
        return True
    return False

def reject_location(user_id: str):
    """Reject user location verification and increment attempts"""
    if user_id in location_verification_data:
        location_verification_data[user_id]['location_attempts'] += 1
        if location_verification_data[user_id]['location_attempts'] >= 3:
            location_verification_data[user_id]['status'] = 'blocked'
        save_location_verification()
        return location_verification_data[user_id]['location_attempts']
    return 0

def get_location_verification_status(user_id: str):
    """Get user location verification status"""
    return location_verification_data.get(user_id, {
        'status': 'none',
        'location_verified': False,
        'location_attempts': 0
    })

def is_location_verified(user_id: str):
    """Check if user location is verified"""
    status = get_location_verification_status(user_id)
    return status['status'] == 'verified' and status['location_verified']

def is_user_blocked(user_id: str):
    """Check if user is blocked due to location verification"""
    # اگر کاربر مهمان باشد، هرگز مسدود محسوب نشود
    u = users.get(user_id, {})
    if u.get('profile', {}).get('guest'):
        return False
    status = get_location_verification_status(user_id)
    return status['status'] == 'blocked'

def ensure_user_profile(user_id: str):
    """Ensure user has complete profile structure"""
    u = users.get(user_id)
    if not u:
        users[user_id] = {
            'user_id': int(user_id) if str(user_id).isdigit() else user_id,
            'name': '',
            'nickname': '',
            'player_name': '',
            'phone': None,
            'capital': '',
            'location': {},
            'profile': {'is_registered': False, 'has_country': False},
            'country': users.get(user_id, {}).get('country', ''),
            'current_country_name': users.get(user_id, {}).get('current_country_name', users.get(user_id, {}).get('country', '')),
            'inventory': {'credits': 0, 'items': []},
            'titles': [],
            'production_tech_levels': {},
            'public_identifier': None
        }
    else:
        u.setdefault('profile', {}).setdefault('is_registered', False)
        u.setdefault('inventory', {}).setdefault('credits', u.get('inventory', {}).get('credits', 0))
        u.setdefault('titles', u.get('titles', []))
        u.setdefault('player_name', '')
        u.setdefault('capital', '')
        u.setdefault('current_country_name', u.get('current_country_name', u.get('country', '')))
        u.setdefault('production_tech_levels', {})
        u.setdefault('public_identifier', None)
        users[user_id] = u
        
        # اطمینان از وجود شناسه عمومی: فقط پس از تایید ثبت‌نام و برای غیر-مهمان
        profile_flags = u.get('profile', {})
        if (
            not u.get('public_identifier')
            and u.get('player_name')
            and profile_flags.get('is_registered')
            and not profile_flags.get('guest')
        ):
            assign_public_identifier(user_id, u.get('player_name'))

def _normalize_username(username: str) -> str:
    if not username:
        return ''
    name = username.strip()
    if name.startswith('@'):
        name = name[1:]
    return name.lower()

# ==================== Public Profile Identifier System ====================

def generate_public_identifier(player_name: str) -> str:
    """تولید شناسه عمومی منحصر به فرد برای پروفایل کاربر (فقط حروف و ارقام انگلیسی).
    همیشه شناسه تصادفی تولید می‌شود تا منحصر به فرد باشد.
    """
    import random as _rand
    import string
    
    # تولید شناسه کاملاً تصادفی
    alphabet = string.ascii_lowercase + string.digits
    length = 8  # طول شناسه
    
    # تولید شناسه تصادفی تا زمانی که منحصر به فرد باشد
    while True:
        identifier = ''.join(_rand.choice(alphabet) for _ in range(length))
        if is_identifier_unique(identifier):
            break
    
    return identifier

def is_identifier_unique(identifier: str) -> bool:
    """بررسی یکتایی شناسه"""
    for user_id, user_data in users.items():
        if user_data.get('public_identifier') == identifier:
            return False
    return True

def assign_public_identifier(user_id: str, player_name: str = None) -> str:
    """اختصاص شناسه عمومی به کاربر"""
    if user_id not in users:
        return None
    
    # اگر نام پلیر مشخص نشده، از پروفایل کاربر بگیر
    if not player_name:
        player_name = users[user_id].get('player_name', '')
    
    # تولید شناسه جدید
    new_identifier = generate_public_identifier(player_name)
    
    if new_identifier:
        users[user_id]['public_identifier'] = new_identifier
        save_users()
    
    return new_identifier

def get_user_by_public_identifier(identifier: str):
    """یافتن کاربر بر اساس شناسه عمومی
    ورودی می‌تواند با اسلش و بدون آن باشد، و می‌تواند فقط بخش پس از name باشد (مثل am برای nameam).
    """
    if not identifier:
        return None

    # پاک‌سازی شناسه
    clean_identifier = identifier.strip().lower()
    if clean_identifier.startswith('/'):
        clean_identifier = clean_identifier[1:]

    # تلاش اول: تطبیق مستقیم
    for user_id, user_data in users.items():
        if user_data.get('public_identifier', '').lower() == clean_identifier:
            return user_id, user_data

    # تلاش دوم: اگر ورودی با "name" شروع نمی‌شود، با پیشوند name امتحان کن
    if not clean_identifier.startswith('name'):
        prefixed = f"name{clean_identifier}"
        for user_id, user_data in users.items():
            if user_data.get('public_identifier', '').lower() == prefixed:
                return user_id, user_data

    return None

def update_user_identifier_if_needed(user_id: str):
    """تعیین شناسه عمومی فقط اگر کاربر تایید شده و فاقد شناسه است.
    شناسه پس از تعیین ثابت می‌ماند و با تغییر نام به‌روزرسانی نمی‌شود."""
    if user_id not in users:
        return None
    user_data = users[user_id]
    profile = user_data.get('profile', {})
    # اگر قبلاً شناسه دارد همان را برگردان
    if user_data.get('public_identifier'):
        return user_data.get('public_identifier')
    # فقط بعد از تایید ثبت‌نام و برای غیر-مهمان بساز
    if profile.get('is_registered') and not profile.get('guest'):
        return assign_public_identifier(user_id, user_data.get('player_name', ''))
    return None

def find_user_key_by_username(username: str):
    """Find a user record key by @username or alias/player_name.
    Returns the matching key in users dict or None.
    """
    uname = _normalize_username(username)
    if not uname:
        return None
    # direct key match by @username or username
    for key in list(users.keys()):
        if not isinstance(key, str):
            continue
        key_norm = _normalize_username(key)
        if key_norm and key_norm == uname:
            return key
    # search inside records
    for key, u in users.items():
        try:
            # aliases
            aliases = [ _normalize_username(a) for a in u.get('aliases', []) ]
            if uname in aliases:
                return key
            # player_name like @username
            pn = str(u.get('player_name', ''))
            if _normalize_username(pn) == uname:
                return key
            # stored username field
            un_field = str(u.get('username', ''))
            if _normalize_username(un_field) == uname:
                return key
        except Exception:
            continue
    return None

def migrate_user_identifier(real_user_id: str, username: str) -> bool:
    """If a user was created under an @username key, migrate it to numeric ID.
    Returns True if migration happened.
    """
    try:
        # Already has numeric record
        if real_user_id in users:
            # ensure alias stored for future
            if username:
                users[real_user_id].setdefault('aliases', [])
                norm = _normalize_username(username)
                if norm and norm not in [ _normalize_username(a) for a in users[real_user_id]['aliases'] ]:
                    users[real_user_id]['aliases'].append(username)
                    save_users()
            return False
        key = find_user_key_by_username(username)
        if key and key != real_user_id:
            record = users.get(key, {})
            # set numeric id and alias
            record['user_id'] = int(real_user_id) if str(real_user_id).isdigit() else real_user_id
            # update status from guest to active
            if record.get('status') == 'guest':
                record['status'] = 'active'
            # profile flags
            profile = record.setdefault('profile', {})
            if profile.get('guest'):
                # guest remains guest but is_registered stays True
                profile['is_registered'] = True
            else:
                profile.setdefault('is_registered', True)
            record.setdefault('aliases', [])
            norm = _normalize_username(username)
            if norm and norm not in [ _normalize_username(a) for a in record['aliases'] ]:
                record['aliases'].append(username)
            # move
            users[real_user_id] = record
            try:
                del users[key]
            except Exception:
                pass
            save_users()
            return True
    except Exception:
        pass
    return False

def increment_guest_interaction_and_maybe_expire(user_id: str) -> bool:
    """Increase guest interactions; if reached 3 and still guest, delete profile and return True."""
    try:
        u = users.get(user_id)
        if not u:
            return False
        if u.get('status') != 'guest':
            return False
        # init counter
        u['guest_interactions'] = int(u.get('guest_interactions', 0)) + 1
        users[user_id] = u
        save_users()
        if u['guest_interactions'] >= 3:
            # expire guest
            try:
                del users[user_id]
            except Exception:
                pass
            save_users()
            # optional: clear location verification state
            try:
                if user_id in location_verification_data:
                    del location_verification_data[user_id]
                    save_location_verification()
            except Exception:
                pass
            return True
    except Exception:
        pass
    return False

def mask_phone_number(phone: str) -> str:
    """Mask phone number for display (e.g., +98 912 *** 1234)"""
    if not phone or len(phone) < 7:
        return phone
    
    # Remove any non-digit characters except +
    clean_phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    if len(clean_phone) < 7:
        return phone
    
    # Find the + and country code
    if clean_phone.startswith('+'):
        country_code = clean_phone[:4] if len(clean_phone) > 10 else clean_phone[:3]
        remaining = clean_phone[len(country_code):]
    else:
        country_code = clean_phone[:3] if len(clean_phone) > 10 else clean_phone[:2]
        remaining = clean_phone[len(country_code):]
    
    if len(remaining) < 4:
        return phone
    
    # Show first 3 and last 3 digits
    visible_start = remaining[:3]
    visible_end = remaining[-3:]
    masked_middle = '***'
    
    return f"{country_code} {visible_start} {masked_middle} {visible_end}"

# ==================== Country Name Translation ====================
# Dictionary to translate country names to English
COUNTRY_NAME_TRANSLATION = {
    # Persian to English translations
    "ایران": "Iran",
    "ایالات متحده آمریکا": "United States",
    "چین": "China", 
    "روسیه": "Russia",
    "آلمان": "Germany",
    "فرانسه": "France",
    "انگلستان": "United Kingdom",
    "ژاپن": "Japan",
    "هند": "India",
    "برزیل": "Brazil",
    "کانادا": "Canada",
    "استرالیا": "Australia",
    "ایتالیا": "Italy",
    "اسپانیا": "Spain",
    "هلند": "Netherlands",
    "سوئد": "Sweden",
    "نروژ": "Norway",
    "دانمارک": "Denmark",
    "فنلاند": "Finland",
    "سوئیس": "Switzerland",
    "اتریش": "Austria",
    "بلژیک": "Belgium",
    "پرتغال": "Portugal",
    "یونان": "Greece",
    "ترکیه": "Turkey",
    "مصر": "Egypt",
    "عربستان سعودی": "Saudi Arabia",
    "امارات متحده عربی": "United Arab Emirates",
    "قطر": "Qatar",
    "کویت": "Kuwait",
    "بحرین": "Bahrain",
    "عمان": "Oman",
    "اردن": "Jordan",
    "لبنان": "Lebanon",
    "سوریه": "Syria",
    "عراق": "Iraq",
    "افغانستان": "Afghanistan",
    "پاکستان": "Pakistan",
    "بنگلادش": "Bangladesh",
    "اندونزی": "Indonesia",
    "مالزی": "Malaysia",
    "تایلند": "Thailand",
    "ویتنام": "Vietnam",
    "فیلیپین": "Philippines",
    "کره جنوبی": "South Korea",
    "کره شمالی": "North Korea",
    "مغولستان": "Mongolia",
    "قزاقستان": "Kazakhstan",
    "ازبکستان": "Uzbekistan",
    "ترکمنستان": "Turkmenistan",
    "تاجیکستان": "Tajikistan",
    "قرقیزستان": "Kyrgyzstan",
    "آذربایجان": "Azerbaijan",
    "ارمنستان": "Armenia",
    "گرجستان": "Georgia",
    "اوکراین": "Ukraine",
    "بلاروس": "Belarus",
    "مولداوی": "Moldova",
    "رومانی": "Romania",
    "بلغارستان": "Bulgaria",
    "صربستان": "Serbia",
    "کرواسی": "Croatia",
    "اسلوونی": "Slovenia",
    "اسلواکی": "Slovakia",
    "چک": "Czech Republic",
    "لهستان": "Poland",
    "مجارستان": "Hungary",
    "لیتوانی": "Lithuania",
    "لتونی": "Latvia",
    "استونی": "Estonia",
    "مکزیک": "Mexico",
    "آرژانتین": "Argentina",
    "شیلی": "Chile",
    "کلمبیا": "Colombia",
    "پرو": "Peru",
    "ونزوئلا": "Venezuela",
    "اکوادور": "Ecuador",
    "بولیوی": "Bolivia",
    "پاراگوئه": "Paraguay",
    "اروگوئه": "Uruguay",
    "آفریقای جنوبی": "South Africa",
    "نیجریه": "Nigeria",
    "کنیا": "Kenya",
    "اتیوپی": "Ethiopia",
    "مصر": "Egypt",
    "لیبی": "Libya",
    "تونس": "Tunisia",
    "الجزایر": "Algeria",
    "مراکش": "Morocco",
    "سودان": "Sudan",
    "اوگاندا": "Uganda",
    "تانزانیا": "Tanzania",
    "زیمبابوه": "Zimbabwe",
    "بوتسوانا": "Botswana",
    "نامیبیا": "Namibia",
    "موزامبیک": "Mozambique",
    "ماداگاسکار": "Madagascar",
    "سازمان ملل": "United Nations"
}

def translate_country_name(country_name: str) -> str:
    """Translate country name from Persian to English"""
    if not country_name:
        return country_name
    
    # Remove flags and extra spaces
    clean_name = country_name.replace('🇺🇳', '').replace('🇺🇸', '').replace('🇨🇳', '').replace('🇷🇺', '').replace('🇩🇪', '').replace('🇫🇷', '').replace('🇬🇧', '').replace('🇯🇵', '').replace('🇮🇳', '').replace('🇧🇷', '').replace('🇨🇦', '').replace('🇦🇺', '').replace('🇮🇹', '').replace('🇪🇸', '').replace('🇳🇱', '').replace('🇸🇪', '').replace('🇳🇴', '').replace('🇩🇰', '').replace('🇫🇮', '').replace('🇨🇭', '').replace('🇦🇹', '').replace('🇧🇪', '').replace('🇵🇹', '').replace('🇬🇷', '').replace('🇹🇷', '').replace('🇪🇬', '').replace('🇸🇦', '').replace('🇦🇪', '').replace('🇶🇦', '').replace('🇰🇼', '').replace('🇧🇭', '').replace('🇴🇲', '').replace('🇯🇴', '').replace('🇱🇧', '').replace('🇸🇾', '').replace('🇮🇶', '').replace('🇦🇫', '').replace('🇵🇰', '').replace('🇧🇩', '').replace('🇮🇩', '').replace('🇲🇾', '').replace('🇹🇭', '').replace('🇻🇳', '').replace('🇵🇭', '').replace('🇰🇷', '').replace('🇰🇵', '').replace('🇲🇳', '').replace('🇰🇿', '').replace('🇺🇿', '').replace('🇹🇲', '').replace('🇹🇯', '').replace('🇰🇬', '').replace('🇦🇿', '').replace('🇦🇲', '').replace('🇬🇪', '').replace('🇺🇦', '').replace('🇧🇾', '').replace('🇲🇩', '').replace('🇷🇴', '').replace('🇧🇬', '').replace('🇷🇸', '').replace('🇭🇷', '').replace('🇸🇮', '').replace('🇸🇰', '').replace('🇨🇿', '').replace('🇵🇱', '').replace('🇭🇺', '').replace('🇱🇹', '').replace('🇱🇻', '').replace('🇪🇪', '').replace('🇲🇽', '').replace('🇦🇷', '').replace('🇨🇱', '').replace('🇨🇴', '').replace('🇵🇪', '').replace('🇻🇪', '').replace('🇪🇨', '').replace('🇧🇴', '').replace('🇵🇾', '').replace('🇺🇾', '').replace('🇿🇦', '').replace('🇳🇬', '').replace('🇰🇪', '').replace('🇪🇹', '').replace('🇱🇾', '').replace('🇹🇳', '').replace('🇩🇿', '').replace('🇲🇦', '').replace('🇸🇩', '').replace('🇺🇬', '').replace('🇹🇿', '').replace('🇿🇼', '').replace('🇧🇼', '').replace('🇳🇦', '').replace('🇲🇿', '').replace('🇲🇬', '').strip()
    
    # Try exact match first
    if clean_name in COUNTRY_NAME_TRANSLATION:
        return COUNTRY_NAME_TRANSLATION[clean_name]
    
    # Try partial match
    for persian_name, english_name in COUNTRY_NAME_TRANSLATION.items():
        if persian_name in clean_name or clean_name in persian_name:
            return english_name
    
    # If no translation found, return the original name
    return country_name

# ==================== Location Province Inference ====================
# Approximate centroids for Iran's provinces (lat, lon)
IRAN_PROVINCES_CENTROIDS = [
    ("Tehran", 35.6892, 51.3890),
    ("Alborz", 35.8400, 50.9400),
    ("Razavi Khorasan", 36.2970, 59.6062),
    ("Fars", 29.5918, 52.5837),
    ("Isfahan", 32.6546, 51.6680),
    ("East Azerbaijan", 38.0962, 46.2738),
    ("West Azerbaijan", 37.5296, 45.0469),
    ("Ardabil", 38.4853, 47.8911),
    ("Hormozgan", 27.1832, 56.2666),
    ("Khuzestan", 31.3183, 48.6706),
    ("Bushehr", 28.9234, 50.8203),
    ("Kerman", 30.2839, 57.0834),
    ("Kermanshah", 34.3277, 47.0778),
    ("Gilan", 37.2808, 49.5832),
    ("Mazandaran", 36.3690, 52.2708),
    ("Golestan", 36.8427, 54.4331),
    ("Sistan and Baluchestan", 29.4921, 60.8669),
    ("Yazd", 31.8974, 54.3569),
    ("Qom", 34.6416, 50.8746),
    ("Zanjan", 36.6736, 48.4787),
    ("Hamadan", 34.7992, 48.5146),
    ("Kurdistan", 35.3090, 47.0026),
    ("Lorestan", 33.4868, 48.3550),
    ("Kohgiluyeh and Boyer-Ahmad", 30.6509, 51.6050),
    ("Chaharmahal and Bakhtiari", 31.9614, 50.8456),
    ("Qazvin", 36.0881, 50.3540),
    ("Semnan", 35.5720, 53.3980),
    ("North Khorasan", 37.4716, 57.1013),
    ("South Khorasan", 32.5176, 59.1042),
    ("Ilam", 33.6374, 46.4227),
    ("Kahrizak", 35.5160, 51.3540)  # filler to improve Tehran area; harmless overlap
]

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import radians, sin, cos, sqrt, atan2
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def infer_iran_province(lat: float, lon: float) -> str:
    try:
        # Rough bounds of Iran
        if not (24.0 <= float(lat) <= 40.0 and 44.0 <= float(lon) <= 63.5):
            return ''
        best_name = ''
        best_dist = 1e12
        for name, plat, plon in IRAN_PROVINCES_CENTROIDS:
            d = _haversine_km(float(lat), float(lon), plat, plon)
            if d < best_dist:
                best_dist = d
                best_name = name
        return best_name
    except Exception:
        return ''

def get_location_province(location_data: dict) -> str:
    """Return province name; compute from lat/lon if not present."""
    if not isinstance(location_data, dict):
        return '-'
    prov = location_data.get('province') or location_data.get('state')
    if prov:
        return prov
    lat = location_data.get('latitude')
    lon = location_data.get('longitude')
    if lat is not None and lon is not None:
        guessed = infer_iran_province(lat, lon)
        return guessed or '-'
    return '-'

def set_user_location_with_province(user_id: str, latitude: float, longitude: float):
    """Store user location and inferred province (if Iran)."""
    u = users.setdefault(user_id, {})
    loc = u.setdefault('location', {})
    loc['latitude'] = float(latitude)
    loc['longitude'] = float(longitude)
    prov = infer_iran_province(latitude, longitude)
    if prov:
        loc['province'] = prov
    save_users()

def get_location_display(location_data: dict) -> str:
    """Get formatted location display from location data"""
    if not location_data:
        return "Not Set"
    
    city = location_data.get('city', '')
    country = location_data.get('country', '')
    
    if city and country:
        return f"{city}, {country}"
    elif city:
        return city
    elif country:
        return country
    else:
        lat = location_data.get('latitude', 0)
        lon = location_data.get('longitude', 0)
        return f"{lat:.4f}, {lon:.4f}"

def add_user_title(user_id: str, title_name: str, season: int):
    """Add a title to user's profile"""
    if user_id not in users:
        return
    
    titles = users[user_id].get('titles', [])
    # Check if title already exists for this season
    for title in titles:
        if title.get('name') == title_name and title.get('season') == season:
            return
    
    titles.append({'name': title_name, 'season': season})
    users[user_id]['titles'] = titles
    save_users()

def add_credits_to_user(user_id: str, amount: int):
    """Add credits to user's inventory"""
    if user_id not in users:
        return
    
    current_credits = users[user_id].get('inventory', {}).get('credits', 0)
    users[user_id].setdefault('inventory', {})['credits'] = current_credits + amount
    save_users()

def end_season_rewards(winners: dict, season_number: int):
    """Distribute season end rewards to winners"""
    # Define rewards for each category
    rewards = {
        "emperor": {"credits": 500, "title": "امپراتور جهان"},
        "economy": {"credits": 250, "title": "سلطان اقتصاد"},
        "diplomat": {"credits": 100, "title": "دیپلمات اعظم"},
        "commander": {"credits": 100, "title": "فرمانده آهنین"},
        "popular": {"credits": 50, "title": "محبوب ملت‌ها"},
        "veteran": {"credits": 250, "title": "پیشکسوت جهان"}
    }
    
    for category, user_id in winners.items():
        if user_id and category in rewards:
            # Add credits
            add_credits_to_user(str(user_id), rewards[category]["credits"])
            # Add title
            add_user_title(str(user_id), rewards[category]["title"], season_number)

def load_banned_users():
    global banned_users
    try:
        with open(BANNED_USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                banned_users = set(str(x) for x in data)
            elif isinstance(data, dict):
                banned_users = set(str(x) for x in data.get('banned', []))
            else:
                banned_users = set()
    except (FileNotFoundError, json.JSONDecodeError):
        banned_users = set()

def save_banned_users():
    try:
        with open(BANNED_USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sorted(list(banned_users)), f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def is_user_banned(user_id: str) -> bool:
    try:
        return str(user_id) in banned_users
    except Exception:
        return False

def ban_user(user_id: str):
    banned_users.add(str(user_id))
    save_banned_users()
NAVAL_ATTACK_CHANNEL_ID = '@TextEmpire_News'  # شناسه کانال حمله دریایی
BOT_TOKEN = '7660355298:AAEX16hOXrD1g1StF8v6ymDtrZngzWObG3I'  # توکن ربات - این را با توکن واقعی جایگزین کنید
USERS_FILE = 'users.json'
COUNTRIES_FILE = 'countries.json'
PLAYER_SELL_ADS_FILE = 'player_sell_ads.json'
global_market_inventory = {}

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

# متغیرهای مربوط به وام استقلال
independence_loans = {}  # {user_id: {'amount': 1000000000, 'start_turn': turn, 'due_turn': turn+4, 'interest_rate': 0.04, 'paid': False}}
INDEPENDENCE_LOAN_FILE = 'independence_loans.json'

# متغیر مربوط به وام مخفی
secret_loan_claimed = False  # آیا وام مخفی قبلاً دریافت شده
SECRET_LOAN_CLAIMED_FILE = 'secret_loan_claimed.json'

# متغیر مربوط به جایزه مخفی اقتصاد
economy_secret_claimed = False  # آیا جایزه مخفی اقتصاد قبلاً دریافت شده
ECONOMY_SECRET_CLAIMED_FILE = 'economy_secret_claimed.json'

# متغیرهای مربوط به کشورهای فتح شده
conquered_countries_data = {}  # {user_id: {'conquered_by': country, 'conquered_at': timestamp, 'resources_saved': {...}}}
CONQUERED_COUNTRIES_FILE = 'conquered_countries.json'

# بارگذاری یا ایجاد فایل کاربران
def save_global_market():
    with open('global_market.json', 'w', encoding='utf-8') as f:
        json.dump(global_market_inventory, f, ensure_ascii=False, indent=2)

# قیمت‌های پایه منابع (بهبود یافته - نسخه نهایی)
base_prices = {
    # منابع پایه
    'gold': 5000000,      # طلا: 1.2M دلار
    'steel': 600000,      # فولاد: 600K دلار
    'iron': 200000,       # آهن: 200K دلار
    'copper': 400000,     # مس: 400K دلار
    'diamond': 12000000,   # الماس: 3M دلار
    'uranium': 8000000,    # اورانیوم: 800K دلار
    'wheat': 100000,      # گندم: 100K دلار
    'rice': 80000,        # برنج: 80K دلار
    'fruits': 60000,      # میوه: 60K دلار
    'oil': 600000,        # نفت: 600K دلار
    'gas': 300000,        # گاز: 300K دلار
    'electronics': 55,  # الکترونیک: 60K دلار
    'pride_cars': 700,  # پراید: 25K دلار
    'benz_cars': 4000,  # بنز: 100K دلار
    'electricity': 800000,  # برق: 800K دلار
    'uranium_ore': 150000,   # سنگ اورانیوم: 150K دلار
    'centrifuge': 2000000,   # سانتریفیوژ: 2M دلار
    'yellowcake': 1500000,   # کیک زرد: 1.5M دلار
    'space_parts': 4000000,  # قطعات فضایی: 4M دلار
    'aluminum': 1000000,      # آلومینیوم: 1M دلار
    'titanium': 2000000,      # تیتانیوم: 2M دلار
    
    # تسلیحات نظامی
    'soldiers': 5000,           # سرباز: 5K دلار
    'special_forces': 15000,    # نیروهای ویژه: 15K دلار
    'tanks': 500000,            # تانک: 500K دلار
    'armored_vehicles': 300000, # خودرو زرهی: 300K دلار
    'transport_planes': 2000000, # هواپیمای ترابری: 2M دلار
    'helicopters': 800000,      # هلیکوپتر: 800K دلار
    'fighter_jets': 3000000,    # جت جنگنده: 3M دلار
    'bombers': 5000000,         # بمب‌افکن: 5M دلار
    'artillery': 400000,        # توپخانه: 400K دلار
    'drones': 200000,           # پهپاد: 200K دلار
    'air_defense': 600000,      # پدافند هوایی: 600K دلار
    'coastal_artillery': 500000, # توپخانه ساحلی: 500K دلار
    'speedboats': 300000,       # قایق تندرو: 300K دلار
    'naval_ship': 2000000,      # کشتی جنگی: 2M دلار
    'submarines': 3000000,      # زیردریایی: 3M دلار
    'aircraft_carriers': 10000000, # ناو هواپیمابر: 10M دلار
    'war_robots': 100000,       # ربات جنگی: 100K دلار
    'defense_missiles': 50000,  # موشک دفاعی: 50K دلار
    'ballistic_missiles': 200000, # موشک بالستیک: 200K دلار
}

# محدوده نوسان قیمت برای هر منبع (درصد)
price_volatility = {
    'gold': 0.1,        # طلا: ±30%
    'steel': 0.4,       # فولاد: ±40%
    'iron': 0.35,       # آهن: ±35%
    'copper': 0.45,     # مس: ±45%
    'diamond': 0.25,    # الماس: ±25%
    'uranium': 0.5,     # اورانیوم: ±50%
    'wheat': 0.6,       # گندم: ±60%
    'rice': 0.55,       # برنج: ±55%
    'fruits': 0.5,      # میوه: ±70%
    'oil': 0.4,         # نفت: ±40%
    'gas': 0.45,        # گاز: ±45%
    'electronics': 0.35, # الکترونیک: ±35%
    'pride_cars': 0.3,  # پراید: ±30%
    'benz_cars': 0.2,   # بنز: ±20%
    'electricity': 0.25, # برق: ±25%
    'uranium_ore': 0.4,   # سنگ اورانیوم: ±40%
    'centrifuge': 0.4,    # سانتریفیوژ: ±40%
    'yellowcake': 0.4,    # کیک زرد: ±40%
    'space_parts': 0.4,    # قطعات فضایی: ±40%
    'aluminum': 0.35,      # آلومینیوم: ±35%
    'titanium': 0.3,       # تیتانیوم: ±30%
    # تسلیحات نظامی (قیمت ثابت)
    'soldiers': 0.0,           # سرباز: بدون نوسان
    'special_forces': 0.0,     # نیروهای ویژه: بدون نوسان
    'tanks': 0.0,              # تانک: بدون نوسان
    'armored_vehicles': 0.0,   # خودرو زرهی: بدون نوسان
    'transport_planes': 0.0,   # هواپیمای ترابری: بدون نوسان
    'helicopters': 0.0,        # هلیکوپتر: بدون نوسان
    'fighter_jets': 0.0,       # جت جنگنده: بدون نوسان
    'bombers': 0.0,            # بمب‌افکن: بدون نوسان
    'artillery': 0.0,          # توپخانه: بدون نوسان
    'drones': 0.0,             # پهپاد: بدون نوسان
    'air_defense': 0.0,        # پدافند هوایی: بدون نوسان
    'coastal_artillery': 0.0,  # توپخانه ساحلی: بدون نوسان
    'speedboats': 0.0,         # قایق تندرو: بدون نوسان
    'naval_ship': 0.0,         # کشتی جنگی: بدون نوسان
    'submarines': 0.0,         # زیردریایی: بدون نوسان
    'aircraft_carriers': 0.0,  # ناو هواپیمابر: بدون نوسان
    'war_robots': 0.0,         # ربات جنگی: بدون نوسان
    'defense_missiles': 0.0,   # موشک دفاعی: بدون نوسان
    'ballistic_missiles': 0.0, # موشک بالستیک: بدون نوسان
}

# متغیرهای بازی
game_data = {
    'turn': 1,
    'last_turn_time': None,
    'game_date': '01/01/2025',
    'resources': {},
    'prices': base_prices.copy(),  # استفاده از قیمت‌های پایه
    'season': 1
}

try:
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        users = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    users = {}

# ذخیره/بارگذاری آگهی‌های فروش بازیکنان
def save_player_sell_ads():
    """ذخیره آگهی‌های فروش بازیکنان در فایل پایدار."""
    try:
        with open(PLAYER_SELL_ADS_FILE, 'w', encoding='utf-8') as f:
            json.dump(player_sell_ads, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[player_sell_ads] save failed: {e}")

def load_player_sell_ads():
    """بارگذاری آگهی‌های فروش بازیکنان از فایل."""
    global player_sell_ads
    if not os.path.exists(PLAYER_SELL_ADS_FILE):
        player_sell_ads = []
        return
    try:
        with open(PLAYER_SELL_ADS_FILE, 'r', encoding='utf-8') as f:
            player_sell_ads = json.load(f)
    except Exception as e:
        print(f"[player_sell_ads] load failed, resetting empty: {e}")
        player_sell_ads = []


def save_game_data():
    with open('game_data.json', 'w', encoding='utf-8') as f:
        json.dump(game_data, f, ensure_ascii=False, indent=2)

def load_game_data():
    global game_data
    try:
        with open('game_data.json', 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
            game_data.update(loaded_data)
            # اطمینان از اینکه قیمت‌های جدید اضافه شده‌اند
            for resource, base_price in base_prices.items():
                if resource not in game_data['prices']:
                    game_data['prices'][resource] = base_price
    except (FileNotFoundError, json.JSONDecodeError):
        game_data = {
            'turn': 1,
            'last_turn_time': None,
            'game_date': '01/01/2025',
            'resources': {},
            'prices': base_prices.copy(),  # استفاده از قیمت‌های پایه جدید
            'season': 1
        }
        save_game_data()
    
    # اطمینان از اینکه تمام قیمت‌ها موجود هستند
    for resource, base_price in base_prices.items():
        if resource not in game_data['prices']:
            game_data['prices'][resource] = base_price
    # اطمینان از وجود فیلد فصل
    if 'season' not in game_data:
        game_data['season'] = 1

def update_prices():
    """به‌روزرسانی قیمت‌ها بر اساس سیستم مستقل هر منبع"""
    # لیست منابع اقتصادی (غیر نظامی)
    economic_resources = [
        'gold', 'steel', 'iron', 'copper', 'diamond', 'uranium',
        'wheat', 'rice', 'fruits', 'oil', 'gas', 'electronics',
        'pride_cars', 'benz_cars', 'electricity', 'uranium_ore',
        'centrifuge', 'yellowcake', 'space_parts', 'aluminum', 'titanium'
    ]
    
    # به‌روزرسانی قیمت فقط برای منابع اقتصادی
    for resource in economic_resources:
        if resource in base_prices and resource in price_volatility:
            base_price = base_prices[resource]
            volatility = price_volatility[resource]
            # تغییر رندوم بر اساس نوسان تعریف شده
            variation = random.uniform(1 - volatility, 1 + volatility)
            new_price = int(base_price * variation)
            game_data['prices'][resource] = new_price
    
    save_game_data()

# ==================== کمک‌کننده‌های فصل و رتبه‌بندی ====================
def calculate_total_wealth(user_id: str) -> int:
    """محاسبه ثروت کل (نقد + ارزش منابع بر اساس قیمت‌ها + پول legacy)."""
    u = users.get(user_id, {})
    if not u:
        return 0
    res = u.get('resources', {})
    total = 0
    # پول نقد
    total += int(res.get('cash', 0) or 0)
    # پول legacy در فیلد money (برای سازگاری)
    total += int(u.get('money', 0) or 0)
    # ارزش سایر منابع
    prices = game_data.get('prices', {})
    for k, amt in res.items():
        if k == 'cash':
            continue
        price = prices.get(k)
        if isinstance(amt, (int, float)) and isinstance(price, (int, float)):
            try:
                total += int(amt * price)
            except Exception:
                continue
    return int(total)

def get_positive_relations_count(user_id: str) -> int:
    rels = country_relations.get(user_id, {})
    try:
        return sum(1 for v in rels.values() if v > 0)
    except Exception:
        return 0

def get_country_to_user_map() -> dict:
    mapping = {}
    for uid, u in users.items():
        if not u.get('activated'):
            continue
        country = u.get('country')
        if country:
            mapping[country] = uid
    return mapping

def count_conquests_per_attacker() -> dict:
    """تعداد کشورهایی که هر بازیکن فتح کرده (از روی فیلد conquered_by در users)."""
    country_to_user = get_country_to_user_map()
    counts = {uid: 0 for uid in users.keys()}
    for target_uid, target in users.items():
        conquered_by_country = target.get('conquered_by')
        if conquered_by_country:
            attacker_uid = country_to_user.get(conquered_by_country)
            if attacker_uid:
                counts[attacker_uid] = counts.get(attacker_uid, 0) + 1
    return counts

# شمارنده پیروزی نظامی (برای فرمانده آهنین)
def increment_military_win(user_id: str):
    u = users.get(user_id, {})
    if not u:
        return
    u['military_wins'] = int(u.get('military_wins', 0) or 0) + 1
    users[user_id] = u
    save_users()

def get_military_wins(user_id: str) -> int:
    return int(users.get(user_id, {}).get('military_wins', 0) or 0)


countries = [
    {"name": "سازمان ملل 🇺🇳", "category": "گاد", "code": 48448615, "taken": False},
    {"name": "ایالات متحده آمریکا 🇺🇸", "category": "🎖ابرقدرت🎖", "code": 416268, "taken": False},
    {"name": "چین 🇨🇳", "category": "🎖ابرقدرت🎖", "code": 687333, "taken": False},
    {"name": "روسیه 🇷🇺", "category": "🎖ابرقدرت🎖", "code": 687444, "taken": False},
    {"name": "بریتانیا 🇬🇧", "category": "🎖ابرقدرت🎖", "code": 976873, "taken": False},
    {"name": "آلمان 🇩🇪", "category": "🥇قدرت منطقه‌ای🥇", "code": 997233, "taken": False},
    {"name": "ژاپن 🇯🇵", "category": "🥇قدرت منطقه‌ای🥇", "code": 373734, "taken": False},
    {"name": "فرانسه 🇫🇷", "category": "🥇قدرت منطقه‌ای🥇", "code": 987433, "taken": False},
    {"name": "هند 🇮🇳", "category": "🥇قدرت منطقه‌ای🥇", "code": 976573, "taken": False},
    {"name": "ایتالیا 🇮🇹", "category": "🥇قدرت منطقه‌ای🥇", "code": 973543, "taken": False},
    {"name": "کانادا 🇨🇦", "category": "🥇قدرت منطقه‌ای🥇", "code": 452781, "taken": False},
    {"name": "ایران 🇮🇷", "category": "🥇قدرت منطقه‌ای🥇", "code": 872257, "taken": False},
    {"name": "کره‌ جنوبی 🇰🇷", "category": "🥇قدرت منطقه‌ای🥇", "code": 349737, "taken": False},
    {"name": "برزیل 🇧🇷", "category": "🥈قدرت نوظهور🥈", "code": 132477, "taken": False},
    {"name": "ترکیه 🇹🇷", "category": "🥈قدرت نوظهور🥈", "code": 335723, "taken": False},
    {"name": "اسرائیل 🇮🇱", "category": "🥈قدرت نوظهور🥈", "code": 675982, "taken": False},
    {"name": "اسپانیا 🇪🇸", "category": "🥈قدرت نوظهور🥈", "code": 678912, "taken": False},
    {"name": "عربستان سعودی 🇸🇦", "category": "🥈قدرت نوظهور🥈", "code": 972324, "taken": False},
    {"name": "سوئیس 🇨🇭", "category": "🥈قدرت نوظهور🥈", "code": 123789, "taken": False},
    {"name": "مکزیک 🇲🇽", "category": "🥈قدرت نوظهور🥈", "code": 789123, "taken": False},
    {"name": "مصر 🇪🇬", "category": "🥈قدرت نوظهور🥈", "code": 894561, "taken": False},
    {"name": "پاکستان 🇵🇰", "category": "🥈قدرت نوظهور🥈", "code": 987651, "taken": False},
    {"name": "استرالیا 🇦🇺", "category": "🥈قدرت نوظهور🥈", "code": 563219, "taken": False},
    {"name": "اندونزی 🇮🇩", "category": "🥉عادی🥉", "code": 784563, "taken": False},
    {"name": "اوکراین 🇺🇦", "category": "🥉عادی🥉", "code": 456789, "taken": False},
    {"name": "لهستان 🇵🇱", "category": "🥉عادی🥉", "code": 567891, "taken": False},
    {"name": "اسپانیا 🇪🇸", "category": "🥉عادی🥉", "code": 678912, "taken": False},
    {"name": "نیجریه 🇳🇬", "category": "🥉عادی🥉", "code": 891234, "taken": False},
    {"name": "تایلند 🇹🇭", "category": "🥉عادی🥉", "code": 912345, "taken": False},
    {"name": "امارات متحده عربی 🇦🇪", "category": "🥉عادی🥉", "code": 123456, "taken": False},
    {"name": "قطر 🇶🇦", "category": "🥉عادی🥉", "code": 234567, "taken": False},
    {"name": "آفریقای جنوبی 🇿🇦", "category": "🥉عادی🥉", "code": 345678, "taken": False},
    {"name": "ویتنام 🇻🇳", "category": "🥉عادی🥉", "code": 456123, "taken": False},
    {"name": "مالزی 🇲🇾", "category": "🥉عادی🥉", "code": 567234, "taken": False},
    {"name": "آرژانتین 🇦🇷", "category": "🥉عادی🥉", "code": 678345, "taken": False},
    {"name": "سوئد 🇸🇪", "category": "🥉عادی🥉", "code": 789456, "taken": False},
    {"name": "نروژ 🇳🇴", "category": "🥉عادی🥉", "code": 891567, "taken": False},
    {"name": "هلند 🇳🇱", "category": "🥉عادی🥉", "code": 912678, "taken": False},
    {"name": "عراق 🇮🇶", "category": "🥉عادی🥉", "code": 234890, "taken": False},
    {"name": "حذب نازی اروپا 🇮🇲", "category": "🥇قدرت منطقه‌ای🥇", "code": 345901, "taken": False},
    {"name": "الجزایر 🇩🇿", "category": "🥉عادی🥉", "code": 456012, "taken": False},
    {"name": "یونان 🇬🇷", "category": "🥉عادی🥉", "code": 567123, "taken": False},
    {"name": "رومانی 🇷🇴", "category": "🥉عادی🥉", "code": 678234, "taken": False},
    {"name": "فیلیپین 🇵🇭", "category": "🥉عادی🥉", "code": 789345, "taken": False},
    {"name": "بلژیک 🇧🇪", "category": "🥉عادی🥉", "code": 891456, "taken": False},
    {"name": "دانمارک 🇩🇰", "category": "🥉عادی🥉", "code": 912567, "taken": False},
    {"name": "اتریش 🇦🇹", "category": "🥉عادی🥉", "code": 123678, "taken": False},
    {"name": "مجارستان 🇭", "category": "🥉عادی🥉", "code": 234789, "taken": False},
    {"name": "داعش 🏴‍☠️", "category": "🥈قدرت نوظهور🥈", "code": 345890, "taken": False},
    {"name": "فنلاند 🇫🇮", "category": "🥉عادی🥉", "code": 456901, "taken": False},
    {"name": "پرتغال 🇵🇹", "category": "🥉عادی🥉", "code": 567012, "taken": False},
    {"name": "صربستان 🇷🇸", "category": "🥉عادی🥉", "code": 678123, "taken": False},
    {"name": "کره شمالی 🇰🇵", "category": "🥉عادی🥉", "code": 486764, "taken": False},
]

# بارگذاری یا ایجاد فایل کشورها
if os.path.exists(COUNTRIES_FILE):
    try:
        with open(COUNTRIES_FILE, 'r', encoding='utf-8') as f:
            loaded_countries = json.load(f)
            if loaded_countries:  # اگر فایل خالی نباشد
                countries = loaded_countries
            else:  # اگر فایل خالی باشد، از لیست پیش‌فرض استفاده کن
                with open(COUNTRIES_FILE, 'w', encoding='utf-8') as f:
                    json.dump(countries, f, ensure_ascii=False, indent=2)
    except (FileNotFoundError, json.JSONDecodeError):
        # اگر فایل وجود نداشته باشد یا خراب باشد، از لیست پیش‌فرض استفاده کن
        with open(COUNTRIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(countries, f, ensure_ascii=False, indent=2)
else:
    # اگر فایل وجود نداشته باشد، ایجاد کن
    with open(COUNTRIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(countries, f, ensure_ascii=False, indent=2)

def save_countries():
    with open(COUNTRIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(countries, f, ensure_ascii=False, indent=2)

def load_countries():
    global countries
    try:
        with open(COUNTRIES_FILE, 'r', encoding='utf-8') as f:
            loaded_countries = json.load(f)
            if loaded_countries:  # اگر فایل خالی نباشد
                countries = loaded_countries
            else:  # اگر فایل خالی باشد، از لیست پیش‌فرض استفاده کن
                countries = [
                    {"name": "سازمان ملل 🇺🇳", "category": "گاد", "code": 48448615, "taken": False},
                    {"name": "ایالات متحده آمریکا 🇺🇸", "category": "🎖ابرقدرت🎖", "code": 416268, "taken": False},
                    {"name": "چین 🇨🇳", "category": "🎖ابرقدرت🎖", "code": 687333, "taken": False},
                    {"name": "روسیه 🇷🇺", "category": "🎖ابرقدرت🎖", "code": 687444, "taken": False},
                    {"name": "بریتانیا 🇬🇧", "category": "🎖ابرقدرت🎖", "code": 976873, "taken": False},
                    {"name": "آلمان 🇩🇪", "category": "🥇قدرت منطقه‌ای🥇", "code": 997233, "taken": False},
                    {"name": "ژاپن 🇯🇵", "category": "🥇قدرت منطقه‌ای🥇", "code": 373734, "taken": False},
                    {"name": "فرانسه 🇫🇷", "category": "🥇قدرت منطقه‌ای🥇", "code": 987433, "taken": False},
                    {"name": "هند 🇮🇳", "category": "🥇قدرت منطقه‌ای🥇", "code": 976573, "taken": False},
                    {"name": "ایتالیا 🇮🇹", "category": "🥇قدرت منطقه‌ای🥇", "code": 973543, "taken": False},
                    {"name": "کانادا 🇨🇦", "category": "🥇قدرت منطقه‌ای🥇", "code": 452781, "taken": False},
                    {"name": "ایران 🇮🇷", "category": "🥇قدرت منطقه‌ای🥇", "code": 872257, "taken": False},
                    {"name": "کره‌ جنوبی 🇰🇷", "category": "🥇قدرت منطقه‌ای🥇", "code": 349737, "taken": False},
                    {"name": "برزیل 🇧🇷", "category": "🥈قدرت نوظهور🥈", "code": 132477, "taken": False},
                    {"name": "ترکیه 🇹🇷", "category": "🥈قدرت نوظهور🥈", "code": 335723, "taken": False},
                    {"name": "اسرائیل 🇮🇱", "category": "🥈قدرت نوظهور🥈", "code": 675982, "taken": False},
                    {"name": "اسپانیا 🇪🇸", "category": "🥈قدرت نوظهور🥈", "code": 678912, "taken": False},
                    {"name": "عربستان سعودی 🇸🇦", "category": "🥈قدرت نوظهور🥈", "code": 972324, "taken": False},
                    {"name": "سوئیس 🇨🇭", "category": "🥈قدرت نوظهور🥈", "code": 123789, "taken": False},
                    {"name": "مکزیک 🇲🇽", "category": "🥈قدرت نوظهور🥈", "code": 789123, "taken": False},
                    {"name": "مصر 🇪🇬", "category": "🥈قدرت نوظهور🥈", "code": 894561, "taken": False},
                    {"name": "پاکستان 🇵🇰", "category": "🥈قدرت نوظهور🥈", "code": 987651, "taken": False},
                    {"name": "استرالیا 🇦🇺", "category": "🥈قدرت نوظهور🥈", "code": 563219, "taken": False},
                    {"name": "اندونزی 🇮🇩", "category": "🥉عادی🥉", "code": 784563, "taken": False},
                    {"name": "اوکراین 🇺🇦", "category": "🥉عادی🥉", "code": 456789, "taken": False},
                    {"name": "لهستان 🇵🇱", "category": "🥉عادی🥉", "code": 567891, "taken": False},
                    {"name": "نیجریه 🇳🇬", "category": "🥉عادی🥉", "code": 891234, "taken": False},
                    {"name": "تایلند 🇹🇭", "category": "🥉عادی🥉", "code": 912345, "taken": False},
                    {"name": "امارات متحده عربی 🇦🇪", "category": "🥉عادی🥉", "code": 123456, "taken": False},
                    {"name": "قطر 🇶🇦", "category": "🥉عادی🥉", "code": 234567, "taken": False},
                    {"name": "آفریقای جنوبی 🇿🇦", "category": "🥉عادی🥉", "code": 345678, "taken": False},
                    {"name": "ویتنام 🇻🇳", "category": "🥉عادی🥉", "code": 456123, "taken": False},
                    {"name": "مالزی 🇲🇾", "category": "🥉عادی🥉", "code": 567234, "taken": False},
                    {"name": "آرژانتین 🇦🇷", "category": "🥉عادی🥉", "code": 678345, "taken": False},
                    {"name": "سوئد 🇸🇪", "category": "🥉عادی🥉", "code": 789456, "taken": False},
                    {"name": "نروژ 🇳🇴", "category": "🥉عادی🥉", "code": 891567, "taken": False},
                    {"name": "هلند 🇳🇱", "category": "🥉عادی🥉", "code": 912678, "taken": False},
                    {"name": "عراق 🇮🇶", "category": "🥉عادی🥉", "code": 234890, "taken": False},
                    {"name": "حذب نازی اروپا 🇮🇲", "category": "🥇قدرت منطقه‌ای🥇", "code": 345901, "taken": False},
                    {"name": "الجزایر 🇩🇿", "category": "🥉عادی🥉", "code": 456012, "taken": False},
                    {"name": "یونان 🇬🇷", "category": "🥉عادی🥉", "code": 567123, "taken": False},
                    {"name": "رومانی 🇷🇴", "category": "🥉عادی🥉", "code": 678234, "taken": False},
                    {"name": "فیلیپین 🇵🇭", "category": "🥉عادی🥉", "code": 789345, "taken": False},
                    {"name": "بلژیک 🇧🇪", "category": "🥉عادی🥉", "code": 891456, "taken": False},
                    {"name": "دانمارک 🇩🇰", "category": "🥉عادی🥉", "code": 912567, "taken": False},
                    {"name": "اتریش 🇦🇹", "category": "🥉عادی🥉", "code": 123678, "taken": False},
                    {"name": "مجارستان 🇭🇺", "category": "🥉عادی🥉", "code": 234789, "taken": False},
                    {"name": "داعش 🏴‍☠️", "category": "🥈قدرت نوظهور🥈", "code": 345890, "taken": False},
                    {"name": "فنلاند 🇫🇮", "category": "🥉عادی🥉", "code": 456901, "taken": False},
                    {"name": "پرتغال 🇵🇹", "category": "🥉عادی🥉", "code": 567012, "taken": False},
                    {"name": "صربستان 🇷🇸", "category": "🥉عادی🥉", "code": 678123, "taken": False},
                    {"name": "کره شمالی 🇰🇵", "category": "🥉عادی🥉", "code": 486764, "taken": False},
                ]
                # ذخیره لیست پیش‌فرض در فایل
                with open(COUNTRIES_FILE, 'w', encoding='utf-8') as f:
                    json.dump(countries, f, ensure_ascii=False, indent=2)
    except (FileNotFoundError, json.JSONDecodeError):
        # اگر فایل وجود نداشته باشد یا خراب باشد، از لیست پیش‌فرض استفاده کن
        countries = [
            {"name": "سازمان ملل 🇺🇳", "category": "گاد", "code": 48448615, "taken": False},
            {"name": "ایالات متحده آمریکا 🇺🇸", "category": "🎖ابرقدرت🎖", "code": 416268, "taken": False},
            {"name": "چین 🇨🇳", "category": "🎖ابرقدرت🎖", "code": 687333, "taken": False},
            {"name": "روسیه 🇷🇺", "category": "🎖ابرقدرت🎖", "code": 687444, "taken": False},
            {"name": "بریتانیا 🇬🇧", "category": "🎖ابرقدرت🎖", "code": 976873, "taken": False},
            {"name": "آلمان 🇩🇪", "category": "🥇قدرت منطقه‌ای🥇", "code": 997233, "taken": False},
            {"name": "ژاپن 🇯🇵", "category": "🥇قدرت منطقه‌ای🥇", "code": 373734, "taken": False},
            {"name": "فرانسه 🇫🇷", "category": "🥇قدرت منطقه‌ای🥇", "code": 987433, "taken": False},
            {"name": "هند 🇮🇳", "category": "🥇قدرت منطقه‌ای🥇", "code": 976573, "taken": False},
            {"name": "ایتالیا 🇮🇹", "category": "🥇قدرت منطقه‌ای🥇", "code": 973543, "taken": False},
            {"name": "کانادا 🇨🇦", "category": "🥇قدرت منطقه‌ای🥇", "code": 452781, "taken": False},
            {"name": "ایران 🇮🇷", "category": "🥇قدرت منطقه‌ای🥇", "code": 872257, "taken": False},
            {"name": "کره‌ جنوبی 🇰🇷", "category": "🥇قدرت منطقه‌ای🥇", "code": 349737, "taken": False},
            {"name": "برزیل 🇧🇷", "category": "🥈قدرت نوظهور🥈", "code": 132477, "taken": False},
            {"name": "ترکیه 🇹🇷", "category": "🥈قدرت نوظهور🥈", "code": 335723, "taken": False},
            {"name": "اسرائیل 🇮🇱", "category": "🥈قدرت نوظهور🥈", "code": 675982, "taken": False},
            {"name": "اسپانیا 🇪🇸", "category": "🥈قدرت نوظهور🥈", "code": 678912, "taken": False},
            {"name": "عربستان سعودی 🇸🇦", "category": "🥈قدرت نوظهور🥈", "code": 972324, "taken": False},
            {"name": "سوئیس 🇨🇭", "category": "🥈قدرت نوظهور🥈", "code": 123789, "taken": False},
            {"name": "مکزیک 🇲🇽", "category": "🥈قدرت نوظهور🥈", "code": 789123, "taken": False},
            {"name": "مصر 🇪🇬", "category": "🥈قدرت نوظهور🥈", "code": 894561, "taken": False},
            {"name": "پاکستان 🇵🇰", "category": "🥈قدرت نوظهور🥈", "code": 987651, "taken": False},
            {"name": "استرالیا 🇦🇺", "category": "🥈قدرت نوظهور🥈", "code": 563219, "taken": False},
            {"name": "اندونزی 🇮🇩", "category": "🥉عادی🥉", "code": 784563, "taken": False},
            {"name": "اوکراین 🇺🇦", "category": "🥉عادی🥉", "code": 456789, "taken": False},
            {"name": "لهستان 🇵🇱", "category": "🥉عادی🥉", "code": 567891, "taken": False},
            {"name": "نیجریه 🇳🇬", "category": "🥉عادی🥉", "code": 891234, "taken": False},
            {"name": "تایلند 🇹🇭", "category": "🥉عادی🥉", "code": 912345, "taken": False},
            {"name": "امارات متحده عربی 🇦🇪", "category": "🥉عادی🥉", "code": 123456, "taken": False},
            {"name": "قطر 🇶🇦", "category": "🥉عادی🥉", "code": 234567, "taken": False},
            {"name": "آفریقای جنوبی 🇿🇦", "category": "🥉عادی🥉", "code": 345678, "taken": False},
            {"name": "ویتنام 🇻🇳", "category": "🥉عادی🥉", "code": 456123, "taken": False},
            {"name": "مالزی 🇲🇾", "category": "🥉عادی🥉", "code": 567234, "taken": False},
            {"name": "آرژانتین 🇦🇷", "category": "🥉عادی🥉", "code": 678345, "taken": False},
            {"name": "سوئد 🇸🇪", "category": "🥉عادی🥉", "code": 789456, "taken": False},
            {"name": "نروژ 🇳🇴", "category": "🥉عادی🥉", "code": 891567, "taken": False},
            {"name": "هلند 🇳🇱", "category": "🥉عادی🥉", "code": 912678, "taken": False},
            {"name": "عراق 🇮🇶", "category": "🥉عادی🥉", "code": 234890, "taken": False},
            {"name": "حذب نازی اروپا 🇮🇲", "category": "🥇قدرت منطقه‌ای🥇", "code": 345901, "taken": False},
            {"name": "الجزایر 🇩🇿", "category": "🥉عادی🥉", "code": 456012, "taken": False},
            {"name": "یونان 🇬🇷", "category": "🥉عادی🥉", "code": 567123, "taken": False},
            {"name": "رومانی 🇷🇴", "category": "🥉عادی🥉", "code": 678234, "taken": False},
            {"name": "فیلیپین 🇵🇭", "category": "🥉عادی🥉", "code": 789345, "taken": False},
            {"name": "بلژیک 🇧🇪", "category": "🥉عادی🥉", "code": 891456, "taken": False},
            {"name": "دانمارک 🇩🇰", "category": "🥉عادی🥉", "code": 912567, "taken": False},
            {"name": "اتریش 🇦🇹", "category": "🥉عادی🥉", "code": 123678, "taken": False},
            {"name": "مجارستان 🇭🇺", "category": "🥉عادی🥉", "code": 234789, "taken": False},
            {"name": "داعش 🏴‍☠️", "category": "🥈قدرت نوظهور🥈", "code": 345890, "taken": False},
            {"name": "فنلاند 🇫🇮", "category": "🥉عادی🥉", "code": 456901, "taken": False},
            {"name": "پرتغال 🇵🇹", "category": "🥉عادی🥉", "code": 567012, "taken": False},
            {"name": "صربستان 🇷🇸", "category": "🥉عادی🥉", "code": 678123, "taken": False},
            {"name": "کره شمالی 🇰🇵", "category": "🥉عادی🥉", "code": 486764, "taken": False},
        ]
        # ذخیره لیست پیش‌فرض در فایل
        with open(COUNTRIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(countries, f, ensure_ascii=False, indent=2)

# فایل ذخیره وضعیت فعال‌سازی کاربران



def save_users():
    global users
    # موقتاً غیرفعال کردن پاک‌سازی خودکار
    # cleanup_deleted_un_users()
    
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_production_tech_levels(user_id):
    """دریافت سطح فناوری تولید کاربر"""
    if user_id not in users:
        return {}
    
    if 'production_tech_levels' not in users[user_id]:
        users[user_id]['production_tech_levels'] = {}
        save_users()
    
    return users[user_id]['production_tech_levels']

def set_production_tech_level(user_id, resource_key, level):
    """تنظیم سطح فناوری تولید برای یک منبع خاص"""
    if user_id not in users:
        return False
    
    if 'production_tech_levels' not in users[user_id]:
        users[user_id]['production_tech_levels'] = {}
    
    users[user_id]['production_tech_levels'][resource_key] = level
    save_production_tech_levels(user_id)
    return True

def test_production_tech_save_system():
    """تست سیستم ذخیره‌سازی production_tech_levels"""
    test_user_id = "test_user_123"
    
    # ایجاد کاربر تست
    if test_user_id not in users:
        users[test_user_id] = {
            'user_id': test_user_id,
            'name': 'Test User',
            'production_tech_levels': {}
        }
    
    # تست تنظیم سطح
    test_resource = "copper_mine"
    test_level = 5
    
    success = set_production_tech_level(test_user_id, test_resource, test_level)
    if not success:
        print("❌ خطا در تنظیم سطح فناوری")
        return False
    
    # تست دریافت سطح
    levels = get_production_tech_levels(test_user_id)
    if levels.get(test_resource) != test_level:
        print("❌ خطا در دریافت سطح فناوری")
        return False
    
    # تست ذخیره
    save_success = save_production_tech_levels(test_user_id)
    if not save_success:
        print("❌ خطا در ذخیره سطح فناوری")
        return False
    
    print("✅ سیستم ذخیره‌سازی production_tech_levels به درستی کار می‌کند")
    
    # پاک کردن کاربر تست
    if test_user_id in users:
        del users[test_user_id]
    
    return True

def save_production_tech_levels(user_id):
    """ذخیره سطح فناوری تولید کاربر"""
    if user_id not in users:
        return False
    
    # اطمینان از وجود production_tech_levels
    if 'production_tech_levels' not in users[user_id]:
        users[user_id]['production_tech_levels'] = {}
    
    # ذخیره در فایل
    save_users()
    return True

def test_public_identifier_system():
    """تست سیستم شناسه‌های عمومی"""
    test_user_id = "test_user_456"
    
    # ایجاد کاربر تست
    if test_user_id not in users:
        users[test_user_id] = {
            'user_id': test_user_id,
            'name': 'Test User',
            'player_name': 'Ali',
            'public_identifier': None
        }
    
    # تست تولید شناسه
    identifier = generate_public_identifier('Ali')
    if not identifier:
        print("❌ خطا در تولید شناسه")
        return False
    
    # تست اختصاص شناسه
    assigned_id = assign_public_identifier(test_user_id, 'Ali')
    if not assigned_id:
        print("❌ خطا در اختصاص شناسه")
        return False
    
    # تست جستجو
    result = get_user_by_public_identifier(assigned_id)
    if not result or result[0] != test_user_id:
        print("❌ خطا در جستجوی کاربر")
        return False
    
    # تست یکتایی
    test_user_id2 = "test_user_789"
    users[test_user_id2] = {
        'user_id': test_user_id2,
        'name': 'Test User 2',
        'player_name': 'Ali',
        'public_identifier': None
    }
    
    identifier2 = assign_public_identifier(test_user_id2, 'Ali')
    if identifier2 == assigned_id:
        print("❌ خطا در یکتایی شناسه")
        return False
    
    print("✅ سیستم شناسه‌های عمومی به درستی کار می‌کند")
    
    # پاک کردن کاربران تست
    if test_user_id in users:
        del users[test_user_id]
    if test_user_id2 in users:
        del users[test_user_id2]
    
    return True

def ensure_all_users_have_public_identifiers():
    """اطمینان از اینکه فقط کاربران تاییدشده (و غیر-مهمان) شناسه عمومی دارند."""
    updated_count = 0
    for user_id, user_data in users.items():
        profile = user_data.get('profile', {})
        if profile.get('is_registered') and not profile.get('guest') and not user_data.get('public_identifier'):
            public_id = assign_public_identifier(user_id, user_data.get('player_name', ''))
            if public_id:
                updated_count += 1
                print(f"✅ Assigned public identifier to user {user_id}: {public_id}")
    if updated_count > 0:
        save_users()
        print(f"✅ Updated {updated_count} users with public identifiers (registered only)")
    return updated_count

def get_all_public_identifiers():
    """دریافت لیست همه شناسه‌های عمومی"""
    identifiers = []
    for user_id, user_data in users.items():
        if user_data.get('public_identifier'):
            identifiers.append({
                'user_id': user_id,
                'player_name': user_data.get('player_name', 'نامشخص'),
                'identifier': user_data.get('public_identifier'),
                'country': user_data.get('country', 'کشور انتخاب نشده')
            })
    return identifiers

def get_production_tech_status(user_id):
    """دریافت وضعیت کامل فناوری تولید کاربر"""
    if user_id not in users:
        return None
    
    levels = get_production_tech_levels(user_id)
    return {
        'user_id': user_id,
        'production_tech_levels': levels,
        'total_levels': len(levels),
        'max_level_reached': max(levels.values()) if levels else 0,
        'has_tech_levels': bool(levels)
    }

def load_users():
    global users
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except FileNotFoundError:
        users = {}
    
    # موقتاً غیرفعال کردن پاک‌سازی خودکار
    # cleanup_deleted_un_users()
    
    # اطمینان از وجود production_tech_levels برای همه کاربران
    for user_id in users:
        if 'production_tech_levels' not in users[user_id]:
            users[user_id]['production_tech_levels'] = {}
        
        # اطمینان از وجود public_identifier برای همه کاربران
        if 'public_identifier' not in users[user_id]:
            users[user_id]['public_identifier'] = None
        
        # اطمینان از وجود capital برای همه کاربران
        if 'capital' not in users[user_id]:
            users[user_id]['capital'] = ''
        
        # ایجاد شناسه عمومی برای کاربرانی که نام دارند اما شناسه ندارند
        if users[user_id].get('player_name') and not users[user_id].get('public_identifier'):
            assign_public_identifier(user_id, users[user_id].get('player_name'))

def reconcile_world_state():
    """Ensure core data files and flags are consistent after startup or data wipe.
    - Recreate files if missing (users.json, countries.json, country_relations.json already handled by loaders)
    - Sync countries[].taken with users who have activated=True and country set
    - Ensure profile.has_country mirrors activated flag
    - Ensure country_relations has an entry for each user
    - Canonicalize user country display names for consistency
    """
    global users, countries, country_relations
    try:
        # Build set of taken country names from active users
        taken_by_users = set()

        # Canonicalize users' country/current_country_name
        try:
            for uid, u in users.items():
                cname = u.get('current_country_name', u.get('country', ''))
                if cname:
                    canonical = get_canonical_country_display(cname)
                    if canonical and canonical != cname:
                        # update both fields for consistency
                        users[uid]['current_country_name'] = canonical
                        # only override country if present
                        if u.get('country'):
                            users[uid]['country'] = canonical
                # ensure relations bucket exists
                country_relations.setdefault(uid, {})
        except Exception:
            pass

        # Sync countries[].taken
        name_to_idx = {}
        try:
            for idx, c in enumerate(countries):
                if isinstance(c, dict):
                    name_to_idx[_normalize_country_name(c.get('name', ''))] = idx
        except Exception:
            pass

        active_users_with_country = []
        try:
            for uid, u in users.items():
                if u.get('activated') and (u.get('country') or u.get('current_country_name')):
                    # prefer canonical value
                    cname = u.get('current_country_name', u.get('country'))
                    active_users_with_country.append(uid)
                    taken_by_users.add(_normalize_country_name(cname))
            # ایجاد روابط دوطرفه پیش‌فرض 0 در صورت نبود
            for uid in active_users_with_country:
                country_relations.setdefault(uid, {})
                for vid in active_users_with_country:
                    if uid == vid:
                        continue
                    country_relations[uid].setdefault(vid, 0)
        except Exception:
            pass

        # Apply taken flags to countries list based on active users
        try:
            # ابتدا تمام کشورها را آزاد علامت بزن
            for c in countries:
                if isinstance(c, dict):
                    c['taken'] = False
            # سپس کشورهایی که توسط کاربران فعال گرفته شده‌اند را علامت بزن
            for norm_name in list(taken_by_users):
                idx = name_to_idx.get(norm_name)
                if idx is not None and isinstance(countries[idx], dict):
                    countries[idx]['taken'] = True
        except Exception:
            pass

        # Persist
        save_users()
        save_countries()
        save_country_relations()
    except Exception as e:
        print(f"[bootstrap] reconcile_world_state error: {e}")

def get_user_activated(user_id):
    global users
    return users.get(user_id, {}).get('activated', False)

async def check_message_ownership(query, user_id):
    """
    چک کردن اینکه آیا کاربر مالک این پیام هست یا نه
    """
    try:
        # اگر پیام در چت خصوصی باشه، همیشه مجاز
        if query.message.chat.type == 'private':
            return True
        
        # اگر پیام در گروه باشه، چک کن که آیا کاربر فعال شده
        if not get_user_activated(user_id):
            return False
        
        # برای پیام‌های گروهی، چک کن که آیا کاربر کشور فعال داره
        user_data = users.get(user_id, {})
        if not user_data.get('activated', False):
            return False
        
        return True
    except Exception as e:
        print(f"خطا در چک کردن مالکیت پیام: {e}")
        return False




def initialize_user_resources(user_id):
    if user_id not in users:
        return
    
    # اگر کاربر resources نداره یا resources خالیه، منابع پیشفرض اضافه کن
    if 'resources' not in users[user_id] or not users[user_id]['resources']:
        category = users[user_id].get('category', '')
        military_resources = {}
        if 'ابرقدرت' in category:
            start_cash = 1_000_000_000
            start_resources = {
                'gold': 60,
                'steel': 500,
                'iron': 600,
                'copper': 250,
                'diamond': 25,
                'uranium': 20,
                'wheat': 400,
                'rice': 400, 
                'fruits': 400,
                'oil': 2000,
                'gas': 2000, 
                'electronics': 500000, 
                'pride_cars': 50000, 
                'benz_cars': 20000, 
                'electricity': 800, 
                'uranium_ore': 200, 
                'centrifuge': 30, 
                'yellowcake': 100, 
                'space_parts': 10, 
                'aluminum': 500, 
                'titanium': 150
            }
            military_resources = {
                "soldiers": 1000000,
                'special_forces': 25000,
                "tanks": 450,
                "armored_vehicles": 1050,
                'transport_planes': 40,
                "helicopters": 540,
                "fighter_jets": 460,
                'bombers': 25,
                'artillery': 60,
                'drones': 180,
                "air_defense": 35,
                'coastal_artillery': 51,
                'speedboats': 140,
                "naval_ship": 46,
                "submarines": 23,
                "aircraft_carriers": 11,
                "war_robots": 1000,
                "defense_missiles": 400,
                "ballistic_missiles": 300
            }
        elif 'قدرت منطقه‌ای' in category:
            start_cash = 550_000_000
            start_resources = {
                'gold': 40,
                'steel': 350,
                'iron': 400,
                'copper': 150,
                'diamond': 15,
                'uranium': 10,
                'wheat': 200,
                'rice': 200, 
                'fruits': 200,
                'oil': 1000,
                'gas': 1000, 
                'electronics': 200000, 
                'pride_cars': 30000, 
                'benz_cars': 10000, 
                'electricity': 400, 
                'uranium_ore': 100, 
                'centrifuge': 15, 
                'yellowcake': 50, 
                'space_parts': 5, 
                'aluminum': 300, 
                'titanium': 75
            }
            military_resources = {
                "soldiers": 500000,
                'special_forces': 12000,
                "tanks": 250,
                "armored_vehicles": 600,
                'transport_planes': 19,
                "helicopters": 300,
                "fighter_jets": 250,
                'bombers': 6,
                'artillery': 28,
                'drones': 100,
                "air_defense": 18,
                'coastal_artillery': 24,
                'speedboats': 90,
                "naval_ship": 21,
                "submarines": 9,
                "aircraft_carriers": 4,
                "war_robots": 500,
                "defense_missiles": 250,
                "ballistic_missiles": 150
            }
        elif 'قدرت نوظهور' in category:
            start_cash = 300_000_000
            start_resources = {
                'gold': 20,
                'steel': 100,
                'iron': 200,
                'copper': 50,
                'diamond': 10,
                'uranium': 10,
                'wheat': 100,
                'rice': 100, 
                'fruits': 100,
                'oil': 500,
                'gas': 500, 
                'electronics': 100000, 
                'pride_cars': 10000, 
                'benz_cars': 5000, 
                'electricity': 200, 
                'uranium_ore': 50, 
                'centrifuge': 7, 
                'yellowcake': 25, 
                'space_parts': 2, 
                'aluminum': 150, 
                'titanium': 45
            }
            military_resources = {
                "soldiers": 200000,
                'special_forces': 5000,
                "tanks": 100,
                "armored_vehicles": 200,
                'transport_planes': 7,
                "helicopters": 150,
                "fighter_jets": 100,
                'bombers': 2,
                'artillery': 16,
                'drones': 51,
                "air_defense": 9,
                'coastal_artillery': 9,
                'speedboats': 40,
                "naval_ship": 9,
                "submarines": 4,
                "aircraft_carriers": 1,
                "war_robots": 260,
                "defense_missiles": 150,
                "ballistic_missiles": 90
            }
        else:  # عادی
            start_cash = 100_000_000
            start_resources = {
                'gold': 15,
                'steel': 150,
                'iron': 300,
                'copper': 100,
                'diamond': 5,
                'uranium': 5,
                'wheat': 50,
                'rice': 50,
                'fruits': 50,
                'oil': 250,
                'gas': 250,
                'electronics': 50000,
                'pride_cars': 10000, 
                'benz_cars': 5000, 
                'electricity': 100, 
                'uranium_ore': 25, 
                'centrifuge': 1, 
                'yellowcake': 10, 
                'space_parts': 1, 
                'aluminum': 80, 
                'titanium': 25
            }
            military_resources = {
                "soldiers": 50000,
                'special_forces': 2000,
                "tanks": 45,
                "armored_vehicles": 100,
                'transport_planes': 15,
                "helicopters": 10,
                "fighter_jets": 10,
                'bombers': 0,
                'artillery': 7,
                'drones': 24,
                "air_defense": 5,
                'coastal_artillery': 7,
                'speedboats': 22,
                "naval_ship": 4,
                "submarines": 1,
                "aircraft_carriers": 0,
                "war_robots": 120,
                "defense_missiles": 90,
                "ballistic_missiles": 50
            }
        users[user_id]['resources'] = {'cash': start_cash, **start_resources, **military_resources}
        users[user_id]['resources_initialized'] = True
    # فقط اگر economy وجود نداشته باشد، آن را initialize کن (نه اینکه همیشه ریست کن)
    if 'economy' not in users[user_id] or not users[user_id]['economy']:
        users[user_id]['economy'] = {
            'mines': [],
            'farms': [],
            'factories': [],
            'power_plants': [],
            'total_value': 1000000
        }
    else:
        # فقط total_value را اگر وجود نداشته باشد اضافه کن
        if 'total_value' not in users[user_id]['economy']:
            users[user_id]['economy']['total_value'] = 1000000
    
    # Initialize production tech levels if not exists
    if 'production_tech_levels' not in users[user_id]:
        users[user_id]['production_tech_levels'] = {}
    
    # حذف save_users() برای جلوگیری از overwrite شدن سازه‌های ساخته‌شده
    # save_users() باید فقط در جاهایی که داده تغییر می‌کند صدا زده شود

def force_initialize_user_resources(user_id):
    """اجباراً منابع پیشفرض رو برای کاربر اضافه می‌کنه"""
    if user_id not in users:
        return
    # اگر قبلاً منابع کاربر مقداردهی شده‌اند، دوباره بازنویسی نکن
    try:
        if users.get(user_id, {}).get('resources'):
            # اما همیشه ساختمان‌ها را ریست کن (حتی اگر منابع وجود دارد)
            users[user_id].setdefault('economy', {})
            users[user_id]['economy']['mines'] = []
            users[user_id]['economy']['farms'] = []
            users[user_id]['economy']['factories'] = []
            users[user_id]['economy']['power_plants'] = []
            save_users()
            return
    except Exception:
        pass
    
    category = users[user_id].get('category', '')
    military_resources = {}
    
    if 'ابرقدرت' in category:
        start_cash = 1_000_000_000
        start_resources = {
            'gold': 60,
            'steel': 500,
            'iron': 600,
            'copper': 250,
            'diamond': 25,
            'uranium': 20,
            'wheat': 400,
            'rice': 400, 
            'fruits': 400,
            'oil': 2000,
            'gas': 2000, 
            'electronics': 500000, 
            'pride_cars': 50000, 
            'benz_cars': 20000, 
            'electricity': 800, 
            'uranium_ore': 200, 
            'centrifuge': 30, 
            'yellowcake': 100, 
            'space_parts': 10, 
            'aluminum': 500, 
            'titanium': 150
        }
        military_resources = {
            "soldiers": 1000000,
            'special_forces': 25000,
            "tanks": 450,
            "armored_vehicles": 1050,
            'transport_planes': 40,
            "helicopters": 540,
            "fighter_jets": 460,
            'bombers': 25,
            'artillery': 60,
            'drones': 180,
            "air_defense": 35,
            'coastal_artillery': 51,
            'speedboats': 140,
            "naval_ship": 46,
            "submarines": 23,
            "aircraft_carriers": 11,
            "war_robots": 1000,
            "defense_missiles": 400,
            "ballistic_missiles": 300
        }
    elif 'قدرت منطقه‌ای' in category:
        start_cash = 550_000_000
        start_resources = {
            'gold': 40,
            'steel': 350,
            'iron': 400,
            'copper': 150,
            'diamond': 15,
            'uranium': 10,
            'wheat': 200,
            'rice': 200, 
            'fruits': 200,
            'oil': 1000,
            'gas': 1000, 
            'electronics': 200000, 
            'pride_cars': 30000, 
            'benz_cars': 10000, 
            'electricity': 400, 
            'uranium_ore': 100, 
            'centrifuge': 15, 
            'yellowcake': 50, 
            'space_parts': 5, 
            'aluminum': 300, 
            'titanium': 75
        }
        military_resources = {
            "soldiers": 500000,
            'special_forces': 12000,
            "tanks": 250,
            "armored_vehicles": 600,
            'transport_planes': 19,
            "helicopters": 300,
            "fighter_jets": 250,
            'bombers': 6,
            'artillery': 28,
            'drones': 100,
            "air_defense": 18,
            'coastal_artillery': 24,
            'speedboats': 90,
            "naval_ship": 21,
            "submarines": 9,
            "aircraft_carriers": 4,
            "war_robots": 500,
            "defense_missiles": 250,
            "ballistic_missiles": 150
        }
    elif 'قدرت نوظهور' in category:
        start_cash = 300_000_000
        start_resources = {
            'gold': 20,
            'steel': 100,
            'iron': 200,
            'copper': 50,
            'diamond': 10,
            'uranium': 10,
            'wheat': 100,
            'rice': 100, 
            'fruits': 100,
            'oil': 500,
            'gas': 500, 
            'electronics': 100000, 
            'pride_cars': 10000, 
            'benz_cars': 5000, 
            'electricity': 200, 
            'uranium_ore': 50, 
            'centrifuge': 7, 
            'yellowcake': 25, 
            'space_parts': 2, 
            'aluminum': 150, 
            'titanium': 45
        }
        military_resources = {
            "soldiers": 200000,
            'special_forces': 5000,
            "tanks": 100,
            "armored_vehicles": 200,
            'transport_planes': 7,
            "helicopters": 150,
            "fighter_jets": 100,
            'bombers': 2,
            'artillery': 16,
            'drones': 51,
            "air_defense": 9,
            'coastal_artillery': 9,
            'speedboats': 40,
            "naval_ship": 9,
            "submarines": 4,
            "aircraft_carriers": 1,
            "war_robots": 260,
            "defense_missiles": 150,
            "ballistic_missiles": 90
        }
    else:  # عادی
        start_cash = 100_000_000
        start_resources = {
            'gold': 15,
            'steel': 150,
            'iron': 300,
            'copper': 100,
            'diamond': 5,
            'uranium': 5,
            'wheat': 50,
            'rice': 50,
            'fruits': 50,
            'oil': 250,
            'gas': 250,
            'electronics': 50000,
            'pride_cars': 10000, 
            'benz_cars': 5000, 
            'electricity': 100, 
            'uranium_ore': 25, 
            'centrifuge': 1, 
            'yellowcake': 10, 
            'space_parts': 1, 
            'aluminum': 80, 
            'titanium': 25
        }
        military_resources = {
            "soldiers": 50000,
            'special_forces': 2000,
            "tanks": 45,
            "armored_vehicles": 100,
            'transport_planes': 15,
            "helicopters": 10,
            "fighter_jets": 10,
            'bombers': 0,
            'artillery': 7,
            'drones': 24,
            "air_defense": 5,
            'coastal_artillery': 7,
            'speedboats': 22,
            "naval_ship": 4,
            "submarines": 1,
            "aircraft_carriers": 0,
            "war_robots": 120,
            "defense_missiles": 90,
            "ballistic_missiles": 50
        }
    
    # مقداردهی منابع فقط یک‌بار (بازنویسی نشود)
    users[user_id]['resources'] = {'cash': start_cash, **start_resources, **military_resources}
    users[user_id]['resources_initialized'] = True
    
    # Initialize production tech levels if not exists
    if 'production_tech_levels' not in users[user_id]:
        users[user_id]['production_tech_levels'] = {}
    
    save_users()

def calculate_total_economy(user_id):
    if user_id not in users or 'resources' not in users[user_id]:
        return 0
    prices = game_data['prices']
    total = users[user_id]['resources'].get('cash', 0)
    for resource, amount in users[user_id]['resources'].items():
        if resource != 'cash' and resource in prices:
            total += amount * prices[resource]
    return total

# --- توابع کمکی عمومی ---
def format_price_short(price):
    if price >= 1_000_000_000_000:
        return f'{price//1_000_000_000_000}t'
    elif price >= 1_000_000_000:
        return f'{price//1_000_000_000}b'
    
    else:
        return f'{price:,}'




# نیازمندی‌های تولید هر محصول (بهبود یافته - نسخه نهایی)
PRODUCTION_RECIPES = {
    # کارخانه
    'steel_factory': {'output': 'steel', 'amount': 25, 'inputs': {'iron': 20, 'electricity': 3, 'oil': 15}},
    'yellowcake_factory': {'output': 'yellowcake', 'amount': 15, 'inputs': {'uranium_ore': 15, 'electricity': 8}},
    'space_parts_factory': {'output': 'space_parts', 'amount': 8, 'inputs': {'iron': 8, 'steel': 15, 'gold': 1, 'copper': 3, 'electricity': 4}},
    # خط تولید
    'pride_line': {'output': 'pride_cars', 'amount': 2000, 'inputs': {'steel': 8, 'iron': 12, 'electricity': 2, 'oil': 8}},
    'benz_line': {'output': 'benz_cars', 'amount': 800, 'inputs': {'steel': 15, 'iron': 20, 'gold': 1, 'electricity': 6, 'oil': 12}},
    'electronics_line': {'output': 'electronics', 'amount': 10000, 'inputs': {'copper': 8, 'iron': 6, 'gold': 1, 'electricity': 8}},
    # تاسیسات هسته‌ای
    'centrifuge': {'output': 'centrifuge', 'amount': 5, 'inputs': {'steel': 8, 'gold': 2, 'diamond': 1, 'gas': 8}},
    'uranium_facility': {'output': 'uranium', 'amount': 10, 'inputs': {'centrifuge': 10, 'yellowcake': 20, 'electricity': 8, 'gas': 8}},
}

# نیازمندی‌های تولید تسلیحات نظامی
MILITARY_PRODUCTION_RECIPES = {
    'soldiers': {'output': 'soldiers', 'amount': 100, 'inputs': {'steel': 5, 'oil': 2, 'electricity': 1}},
    'special_forces': {'output': 'special_forces', 'amount': 50, 'inputs': {'steel': 10, 'oil': 5, 'electricity': 3, 'electronics': 2}},
    'tanks': {'output': 'tanks', 'amount': 10, 'inputs': {'steel': 20, 'oil': 5, 'electricity': 2, 'iron': 20}},
    'armored_vehicles': {'output': 'armored_vehicles', 'amount': 15, 'inputs': {'steel': 15, 'oil': 3, 'electricity': 2, 'iron': 15}},
    'transport_planes': {'output': 'transport_planes', 'amount': 5, 'inputs': {'steel': 25, 'oil': 10, 'electricity': 5, 'aluminum': 10}},
    'helicopters': {'output': 'helicopters', 'amount': 8, 'inputs': {'steel': 15, 'oil': 8, 'electricity': 4, 'electronics': 3}},
    'fighter_jets': {'output': 'fighter_jets', 'amount': 3, 'inputs': {'steel': 30, 'oil': 15, 'electricity': 8, 'electronics': 5, 'titanium': 5}},
    'bombers': {'output': 'bombers', 'amount': 2, 'inputs': {'steel': 40, 'oil': 20, 'electricity': 10, 'electronics': 8, 'titanium': 8}},
    'artillery': {'output': 'artillery', 'amount': 12, 'inputs': {'steel': 18, 'oil': 4, 'electricity': 3, 'iron': 25}},
    'drones': {'output': 'drones', 'amount': 20, 'inputs': {'steel': 8, 'oil': 2, 'electricity': 6, 'electronics': 10}},
    'air_defense': {'output': 'air_defense', 'amount': 8, 'inputs': {'steel': 20, 'oil': 3, 'electricity': 5, 'electronics': 8}},
    'coastal_artillery': {'output': 'coastal_artillery', 'amount': 6, 'inputs': {'steel': 25, 'oil': 4, 'electricity': 4, 'iron': 30}},
    'speedboats': {'output': 'speedboats', 'amount': 8, 'inputs': {'steel': 12, 'oil': 6, 'electricity': 3, 'iron': 15}},
    'naval_ship': {'output': 'naval_ship', 'amount': 3, 'inputs': {'steel': 50, 'oil': 20, 'electricity': 10, 'iron': 40}},
    'submarines': {'output': 'submarines', 'amount': 2, 'inputs': {'steel': 60, 'oil': 25, 'electricity': 15, 'electronics': 12, 'titanium': 10}},
    'aircraft_carriers': {'output': 'aircraft_carriers', 'amount': 1, 'inputs': {'steel': 200, 'oil': 80, 'electricity': 40, 'electronics': 30, 'titanium': 50}},
}
# ساختار داده‌ای سازه‌ها
BUILDINGS = {
    'mines': {
        'title': '⛏️ معادن',
        'items': [
            {'key': 'iron_mine', 'name': 'معدن آهن', 'price': '15m', 'production': 'آهن'},
            {'key': 'uranium_ore_mine', 'name': 'معدن سنگ اورانیوم', 'price': '25m', 'production': 'سنگ اورانیوم'},
            {'key': 'copper_mine', 'name': 'معدن مس', 'price': '20m', 'production': 'مس'},
            {'key': 'gold_mine', 'name': 'معدن طلا', 'price': '45m', 'production': 'طلا'},
            {'key': 'diamond_mine', 'name': 'معدن الماس', 'price': '80m', 'production': 'الماس'},
            {'key': 'aluminum_mine', 'name': 'معدن آلومینیوم', 'price': '30m', 'production': 'آلومینیوم'},
            {'key': 'titanium_mine', 'name': 'معدن تیتانیوم', 'price': '60m', 'production': 'تیتانیوم'},
        ]
    },
    'farms': {
        'title': '🌾 کشاورزی',
        'items': [
            {'key': 'wheat_farm', 'name': 'مزرعه گندم', 'price': '25m', 'production': 'گندم'},
            {'key': 'rice_farm', 'name': 'مزرعه برنج', 'price': '20m', 'production': 'برنج'},
            {'key': 'fruit_farm', 'name': 'مزرعه میوه', 'price': '15m', 'production': 'میوه'},
        ]
    },
    'factories': {
        'title': '🏭 کارخانه',
        'items': [
            {'key': 'steel_factory', 'name': 'کارخانه فولاد', 'price': '40m', 'production': 'فولاد'},
            {'key': 'yellowcake_factory', 'name': 'کارخانه کیک زرد', 'price': '60m', 'production': 'کیک زرد'},
            {'key': 'space_parts_factory', 'name': 'کارخانه قطعات فضایی', 'price': '120m', 'production': 'قطعات فضایی'},
        ]
    },
    'production_lines': {
        'title': '🏗️ خط تولید',
        'items': [
            {'key': 'pride_line', 'name': 'خط تولید پراید', 'price': '60m', 'production': 'پراید'},
            {'key': 'benz_line', 'name': 'خط تولید بنز', 'price': '150m', 'production': 'بنز'},
            {'key': 'electronics_line', 'name': 'خط تولید الکترونیک', 'price': '35m', 'production': 'الکترونیک'},
        ]
    },
    'nuclear': {
        'title': '⚛️ تاسیسات هسته‌ای',
        'items': [
            {'key': 'centrifuge', 'name': 'تاسیسات سانتریفیوژ', 'price': '100m', 'production': 'سانتریفیوژ'},
            {'key': 'uranium_facility', 'name': 'تاسیسات اورانیوم', 'price': '120m', 'production': 'اورانیوم'},
        ]
    },
    'energy': {
        'title': '⚡ انرژی',
        'items': [
            {'key': 'power_plant', 'name': 'نیروگاه برق', 'price': '50m', 'production': 'برق'},
            {'key': 'gas_refinery', 'name': 'پالایشگاه گاز', 'price': '30m', 'production': 'گاز'},
            {'key': 'oil_refinery', 'name': 'پالایشگاه نفت', 'price': '60m', 'production': 'نفت'},
        ]
    },
    'space_mines': {
        'title': '🪐 معادن فضایی',
        'items': [
            {'key': 'platinum_asteroid', 'name': 'معدن سنگ پلاتین (سیارک ها)', 'price': '-', 'production': 'پلاتین'},
            {'key': 'cobalt_asteroid', 'name': 'معدن سنگ کبالت (سیارک ها)', 'price': '-', 'production': 'کبالت'},
            {'key': 'helium_moon', 'name': 'معدن گاز هلیوم (ماه)', 'price': '-', 'production': 'هلیوم'},
            {'key': 'hydrogen_mercury', 'name': 'معدن گاز هیدروژن (عطارد)', 'price': '-', 'production': 'هیدروژن'},
        ]
    },
    'space_farms': {
        'title': '🌱 کشاورزی فضایی',
        'items': [
            {'key': 'veggie_mars', 'name': 'مزرعه سبزیجات (مریخ)', 'price': '-', 'production': 'سبزیجات'},
            {'key': 'titan_plant', 'name': 'مزرعه گیاه تیتان (تیتان)', 'price': '-', 'production': 'گیاه تیتان'},
        ]
    },
    'space_energy': {
        'title': '🔋 انرژی فضایی',
        'items': [
            {'key': 'ice_refinery_ceres', 'name': 'پالایشگاه آب یخ زده (سرس)', 'price': '-', 'production': 'آب یخ زده'},
            {'key': 'methane_refinery_mars', 'name': 'پالایشگاه گاز متان (مریخ)', 'price': '-', 'production': 'گاز متان'},
        ]
    },
}

# متغیرهای سیستم جنگ

SEA_BORDER_COUNTRIES = [
    "ایالات متحده آمریکا 🇺🇸", "بریتانیا 🇬🇧", "ایران 🇮🇷", "ترکیه 🇹🇷", "عراق 🇮🇶", "عربستان سعودی 🇸🇦",
    "مصر 🇪🇬", "اسرائیل 🇮🇱", "فرانسه 🇫🇷", "ایتالیا 🇮🇹", "اسپانیا 🇪🇸", "پرتغال 🇵🇹", "کانادا 🇨🇦",
    "برزیل 🇧🇷", "آرژانتین 🇦🇷", "مکزیک 🇲🇽", "استرالیا 🇦🇺", "ژاپن 🇯🇵", "کره جنوبی 🇰🇷", "روسیه 🇷🇺", "چین 🇨🇳",
    "یونان 🇬🇷", "هلند 🇳🇱", "دانمارک 🇩🇰", "سوئد 🇸🇪", "نروژ 🇳🇴", "فنلاند 🇫🇮", "اندونزی 🇮🇩", "مالزی 🇲🇾",
    "قطر 🇶🇦", "امارات متحده عربی 🇦🇪", "الجزایر 🇩🇿", "آفریقای جنوبی 🇿🇦", "نیجریه 🇳🇬"
    # ... هر کشور دیگری که لازم است اضافه کنید
]

def _normalize_country_name(name: str) -> str:
    try:
        if not isinstance(name, str):
            return ''
        # حذف پرچم (هر چیزی بعد از فاصله آخر اگر ایموجی پرچم باشد)
        base = name.strip()
        # جایگزینی نیم‌فاصله با فاصله
        base = base.replace('\u200c', ' ').replace('\u200f', '')
        # اگر رشته شامل « 🇺🇸» یا پرچم مشابه باشد، فقط بخش نام را نگه داریم
        if ' 🇦' in base or ' 🇧' in base or ' 🇨' in base or ' 🇩' in base or ' 🇪' in base or ' 🇫' in base or ' 🇬' in base or ' 🇭' in base or ' 🇮' in base or ' 🇯' in base or ' 🇰' in base or ' 🇱' in base or ' 🇲' in base or ' 🇳' in base or ' 🇴' in base or ' 🇵' in base or ' 🇶' in base or ' 🇷' in base or ' 🇸' in base or ' 🇹' in base or ' 🇺' in base or ' 🇻' in base or ' 🇼' in base or ' 🇽' in base or ' 🇾' in base or ' 🇿' in base:
            parts = base.split(' ')
            # حذف آخرین توکن اگر پرچم باشد
            if parts and len(parts[-1]) == 2 and 0x1F1E6 <= ord(parts[-1][0]) <= 0x1F1FF:
                parts = parts[:-1]
            base = ' '.join(parts)
        # یکنواخت‌سازی چند فاصله
        base = ' '.join(base.split())
        return base
    except Exception:
        return str(name)

# پر کردن مجموعه نرمال‌شده
try:
    for cname in SEA_BORDER_COUNTRIES:
        SEA_BORDER_COUNTRIES_NORMALIZED.add(_normalize_country_name(cname))
except Exception:
    pass

def has_sea_border(country_name: str) -> bool:
    """بررسی دارد بودن مرز دریایی با نرمال‌سازی نام کشور (بدون پرچم/نیم‌فاصله)."""
    norm = _normalize_country_name(country_name)
    if norm in SEA_BORDER_COUNTRIES_NORMALIZED:
        return True
    # نگاشت نام‌های فارسی/متداول به نام‌های انگلیسیِ فهرست مرز دریایی
    try:
        alias_raw = {
            'چین': 'china',
            'ایالات متحده آمریکا': 'united states of america',
            'آمریکا': 'united states',
            'کانادا': 'canada',
            'ژاپن': 'japan',
            'روسیه': 'russia',
            'بریتانیا': 'united kingdom',
            'انگلستان': 'united kingdom',
            'فرانسه': 'france',
            'آلمان': 'germany',
            'هند': 'india',
            'ایران': 'iran',
            'ایتالیا': 'italy',
            'ترکیه': 'turkey',
            'عربستان سعودی': 'saudi arabia',
            'امارات': 'united arab emirates',
            'اسپانیا': 'spain',
            'برزیل': 'brazil',
            'استرالیا': 'australia',
            'مصر': 'egypt',
            'پاکستان': 'pakistan',
            'اندونزی': 'indonesia',
            'کره جنوبی': 'south korea',
            'کره شمالی': 'north korea',
            'هلند': 'netherlands',
            'چین تایپه': 'taiwan',
            'ویتنام': 'vietnam',
        }
        # نرمال‌سازی کلیدها و مقادیر
        alias_map = { _normalize_country_name(k): _normalize_country_name(v) for k, v in alias_raw.items() }
        alt = alias_map.get(norm)
        if alt and alt in SEA_BORDER_COUNTRIES_NORMALIZED:
            return True
    except Exception:
        pass
    return False

def user_has_sea_access(user_id: str) -> bool:
    """Return True if user's country has sea border or user gained sea access via conquest."""
    u = users.get(user_id, {})
    country = u.get('country', '')
    if has_sea_border(country):
        return True
    return bool(u.get('extra_sea_access'))

def get_effective_land_borders(user_id: str) -> list:
    """Return base land borders of user's country plus any extra borders gained via conquests."""
    u = users.get(user_id, {})
    country = u.get('country', '')
    base = list(LAND_BORDERS.get(country, []))
    extra = u.get('extra_land_borders', []) or []
    # Merge unique while preserving order
    seen = set()
    result = []
    for c in base + extra:
        if c and c not in seen:
            seen.add(c)
            result.append(c)
    return result

def grant_conquest_borders(attacker_id: str, target_country: str, target_id: str):
    """Give attacker extra land/sea access from the conquered target for future attacks."""
    attacker = users.setdefault(attacker_id, {})
    # Grant sea if target had sea
    try:
        if has_sea_border(target_country):
            attacker['extra_sea_access'] = True
            sources = set(attacker.get('extra_sea_access_sources', []))
            sources.add(str(target_id))
            attacker['extra_sea_access_sources'] = list(sources)
    except Exception:
        pass
    # Grant land borders from target country
    try:
        target_borders = LAND_BORDERS.get(target_country, [])
        extra_list = attacker.get('extra_land_borders', []) or []
        # record per-source for later revocation
        src_map = attacker.get('extra_land_borders_sources', {}) or {}
        src_map[str(target_id)] = list(target_borders)
        attacker['extra_land_borders_sources'] = src_map
        # merge
        for bc in target_borders:
            if bc and bc not in extra_list:
                extra_list.append(bc)
        attacker['extra_land_borders'] = extra_list
    except Exception:
        pass

def revoke_conquest_borders(attacker_id: str, target_id: str):
    """Revoke borders/sea access that came from specific colony when independence is granted."""
    attacker = users.get(attacker_id, {})
    # Revoke land borders contributed by this source
    try:
        src_map = attacker.get('extra_land_borders_sources', {}) or {}
        contributed = set(src_map.get(str(target_id), []) or [])
        if contributed:
            current = attacker.get('extra_land_borders', []) or []
            attacker['extra_land_borders'] = [c for c in current if c not in contributed]
            src_map.pop(str(target_id), None)
            attacker['extra_land_borders_sources'] = src_map
    except Exception:
        pass
    # Recompute sea access based on other sources
    try:
        sources = set(attacker.get('extra_sea_access_sources', []) or [])
        if str(target_id) in sources:
            sources.remove(str(target_id))
        attacker['extra_sea_access_sources'] = list(sources)
        # If no native sea and no remaining sources, drop extra sea access
        country = attacker.get('country', '')
        if not has_sea_border(country) and not sources:
            attacker.pop('extra_sea_access', None)
    except Exception:
        pass

# مرزهای زمینی کشورها (مثال)
LAND_BORDERS = {
    "ایالات متحده آمریکا 🇺🇸": ["کانادا 🇨🇦", "مکزیک 🇲🇽"],
    "چین 🇨🇳": ["روسیه 🇷🇺", "هند 🇮🇳", "پاکستان 🇵🇰", "افغانستان", "تاجیکستان", "قرقیزستان", "قزاقستان", "مغولستان", "کره شمالی 🇰🇵", "لائوس", "میانمار", "بوتان", "نپال", "ویتنام 🇻🇳"],
    "روسیه 🇷🇺": ["چین 🇨🇳", "کره شمالی 🇰🇵", "مغولستان", "قزاقستان", "قرقیزستان", "تاجیکستان", "آذربایجان", "گرجستان", "اوکراین 🇺🇦", "بلاروس", "لتونی", "استونی", "فنلاند 🇫🇮", "نروژ 🇳🇴"],
    "ایران 🇮🇷": ["عراق 🇮🇶", "ترکیه 🇹🇷", "آذربایجان", "ارمنستان", "ترکمنستان", "افغانستان", "پاکستان 🇵🇰"],
    "ترکیه 🇹🇷": ["ایران 🇮🇷", "عراق 🇮🶄", "سوریه", "گرجستان", "ارمنستان", "آذربایجان", "بلغارستان", "یونان 🇬🇷"],
    "عراق 🇮🇶": ["ایران 🇮🇷", "ترکیه 🇹🇷", "سوریه", "اردن", "عربستان سعودی 🇸🇦", "کویت"],
    "عربستان سعودی 🇸🇦": ["عراق 🇮🇶", "کویت", "قطر 🇶🇦", "امارات متحده عربی 🇦🇪", "عمان", "یمن", "اردن"],
    "مصر 🇪🇬": ["لیبی", "سودان", "اسرائیل 🇮🇱", "اردن"],
    "اسرائیل 🇮🇱": ["مصر 🇪🇬", "اردن", "سوریه", "لبنان"],
    "هند 🇮🇳": ["چین 🇨🇳", "پاکستان 🇵🇰", "بنگلادش", "نپال", "بوتان", "میانمار"],
    "پاکستان 🇵🇰": ["چین 🇨🇳", "هند 🇮🇳", "افغانستان", "ایران 🇮🇷"],
    "افغانستان": ["چین 🇨🇳", "پاکستان 🇵🇰", "ایران 🇮🇷", "ترکمنستان", "ازبکستان", "تاجیکستان"],
    "برزیل 🇧🇷": ["آرژانتین 🇦🇷", "پاراگوئه", "بولیوی", "پرو", "کلمبیا", "ونزوئلا", "گویان", "سورینام", "گویان فرانسه", "اروگوئه"],
    "آرژانتین 🇦🇷": ["برزیل 🇧🇷", "شیلی", "پاراگوئه", "بولیوی", "اروگوئه"],
    "مکزیک 🇲🇽": ["ایالات متحده آمریکا 🇺🇸", "گواتمالا", "بلیز"],
    "کانادا 🇨🇦": ["ایالات متحده آمریکا 🇺🇸"],
    "آلمان 🇩🇪": ["فرانسه 🇫🇷", "بلژیک 🇧🇪", "هلند 🇳🇱", "دانمارک 🇩🇰", "لهستان 🇵🇱", "جمهوری چک", "اتریش 🇦🇹", "سوئیس 🇨🇭"],
    "فرانسه 🇫🇷": ["آلمان 🇩🇪", "بلژیک 🇧🇪", "لوکزامبورگ", "سوئیس 🇨🇭", "ایتالیا 🇮🇹", "موناکو", "آندورا", "اسپانیا 🇪🇸"],
    "ایتالیا 🇮🇹": ["فرانسه 🇫🇷", "سوئیس 🇨🇭", "اتریش 🇦🇹", "اسلوونی", "کرواسی", "سان مارینو", "واتیکان"],
    "اسپانیا 🇪🇸": ["فرانسه 🇫🇷", "آندورا", "پرتغال 🇵🇹", "مراکش"],
    "پرتغال 🇵🇹": ["اسپانیا 🇪🇸"],
    "بریتانیا 🇬🇧": ["ایرلند"],
    "لهستان 🇵🇱": ["آلمان 🇩🇪", "جمهوری چک", "اسلوونی", "اوکراین 🇺🇦", "بلاروس", "لیتوانی", "روسیه 🇷🇺"],
    "اوکراین 🇺🇦": ["روسیه 🇷🇺", "بلاروس", "لهستان 🇵🇱", "اسلوونی", "مجارستان 🇭🇺", "رومانی 🇷🇴", "مولداوی"],
    "رومانی 🇷🇴": ["اوکراین 🇺🇦", "مولداوی", "بلغارستان", "صربستان 🇷🇸", "مجارستان 🇭🇺"],
    "بلغارستان": ["رومانی 🇷🇴", "صربستان 🇷🇸", "مقدونیه شمالی", "یونان 🇬🇷", "ترکیه 🇹🇷"],
    "یونان 🇬🇷": ["بلغارستان", "مقدونیه شمالی", "آلبانی", "ترکیه 🇹🇷"],
    "صربستان 🇷🇸": ["رومانی 🇷🇴", "بلغارستان", "مقدونیه شمالی", "کوزوو", "آلبانی", "مونته‌نگرو", "بوسنی و هرزگوین", "کرواسی", "مجارستان 🇭🇺"],
    "مجارستان 🇭🇺": ["اوکراین 🇺🇦", "رومانی 🇷🇴", "صربستان 🇷🇸", "کرواسی", "اسلوونی", "اتریش 🇦🇹", "اسلواکی"],
    "اتریش 🇦🇹": ["آلمان 🇩🇪", "جمهوری چک", "اسلواکی", "مجارستان 🇭🇺", "اسلوونی", "ایتالیا 🇮🇹", "سوئیس 🇨🇭", "لیختن‌اشتاین"],
    "سوئیس 🇨🇭": ["آلمان 🇩🇪", "فرانسه 🇫🇷", "ایتالیا 🇮🇹", "اتریش 🇦🇹", "لیختن‌اشتاین"],
    "بلژیک 🇧🇪": ["فرانسه 🇫🇷", "آلمان 🇩🇪", "هلند 🇳🇱", "لوکزامبورگ"],
    "هلند 🇳🇱": ["آلمان 🇩🇪", "بلژیک 🇧🇪"],
    "دانمارک 🇩🇰": ["آلمان 🇩🇪", "سوئد 🇸🇪"],
    "سوئد 🇸🇪": ["نروژ 🇳🇴", "فنلاند 🇫🇮", "دانمارک 🇩🇰"],
    "نروژ 🇳🇴": ["سوئد 🇸🇪", "فنلاند 🇫🇮", "روسیه 🇷🇺"],
    "فنلاند 🇫🇮": ["سوئد 🇸🇪", "نروژ 🇳🇴", "روسیه 🇷🇺"],
    "کره شمالی 🇰🇵": ["چین 🇨🇳", "روسیه 🇷🇺", "کره جنوبی 🇰🇷"],
    "کره جنوبی 🇰🇷": ["کره شمالی 🇰🇵"],
    "ویتنام 🇻🇳": ["چین 🇨🇳", "لائوس", "کامبوج"],
    "مالزی 🇲🇾": ["تایلند 🇹🇭", "اندونزی 🇮🇩", "برونئی"],
    "تایلند 🇹🇭": ["میانمار", "لائوس", "کامبوج", "مالزی 🇲🇾"],
    "اندونزی 🇮🇩": ["مالزی 🇲🇾", "پاپوآ گینه نو", "تیمور شرقی"],
    "فیلیپین 🇵🇭": [],
    "استرالیا 🇦🇺": [],
    "نیجریه 🇳🇬": ["نیجر", "چاد", "کامرون", "بنین", "توگو"],
    "آفریقای جنوبی 🇿🇦": ["نامیبیا", "بوتسوانا", "زیمبابوه", "موزامبیک", "اسواتینی", "لسوتو"],
    "قطر 🇶🇦": ["عربستان سعودی 🇸🇦"],
    "امارات متحده عربی 🇦🇪": ["عربستان سعودی 🇸🇦", "عمان"],
    "الجزایر 🇩🇿": ["مراکش", "تونس", "لیبی", "نیجر", "مالی", "موریتانی"],
}


def save_alliances():
    from diplomaci import alliance_trades
    print(f"[DEBUG] Saving alliances: {alliances}")
    print(f"[DEBUG] Saving user_alliances: {user_alliances}")
    print(f"[DEBUG] Saving alliance_trades: {alliance_trades}")
    with open('alliances.json', 'w', encoding='utf-8') as f:
        json.dump({
            'alliances': alliances,
            'user_alliances': user_alliances,
            'alliance_messages': alliance_messages,
            'alliance_help_requests': alliance_help_requests,
            'alliance_trades': alliance_trades,
            'country_relations': country_relations
        }, f, ensure_ascii=False, indent=2)
    print("[DEBUG] Alliances saved successfully!")

def load_alliances():
    global alliances, user_alliances, alliance_messages, alliance_help_requests, country_relations
    try:
        with open('alliances.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            alliances = data.get('alliances', {})
            user_alliances = data.get('user_alliances', {})
            alliance_messages = data.get('alliance_messages', {})
            alliance_help_requests = data.get('alliance_help_requests', {})
            country_relations = data.get('country_relations', {})
            
            # بارگذاری alliance_trades
            # alliance_trades در diplomaci.py تعریف شده و نیازی به import نیست
            
            # پاک کردن user_alliances برای اتحادهایی که وجود ندارند
            clean_orphaned_user_alliances()
            
            # --- مهاجرت خودکار ساختار اتحادها ---
            for aid, a in alliances.items():
                # اگر leader وجود ندارد، اولین عضو را رهبر کن
                if 'leader' not in a or not a['leader']:
                    if a.get('members'):
                        a['leader'] = a['members'][0]
                    else:
                        a['leader'] = None
                # اگر deputy وجود ندارد، مقدار None قرار بده
                if 'deputy' not in a:
                    a['deputy'] = None
                    
            # اگر alliances خالی است اما user_alliances خالی نیست، user_alliances را پاک کن
            if not alliances and user_alliances:
                print("[DEBUG] Alliances is empty but user_alliances has data. Clearing user_alliances.")
                user_alliances = {}
                
    except (FileNotFoundError, json.JSONDecodeError):
        alliances = {}
        user_alliances = {}
        alliance_messages = {}
        alliance_help_requests = {}
        country_relations = {}

def clean_orphaned_user_alliances():
    """پاک کردن کاربرانی که اتحادشان وجود ندارد"""
    global alliances, user_alliances
    valid_alliance_ids = set(alliances.keys())
    orphaned_users = []
    
    for user_id, alliance_id in list(user_alliances.items()):
        if alliance_id not in valid_alliance_ids:
            orphaned_users.append(user_id)
            del user_alliances[user_id]
    
    if orphaned_users:
        print(f"[DEBUG] Cleaned up {len(orphaned_users)} orphaned user_alliances entries: {orphaned_users}")
        save_alliances()

def simulate_ground_battle(attacker_forces, attacker_id=None, defender_id=None):
    # محاسبه قدرت کلی حمله‌کننده (بدون توپخانه)
    base_attack_power = (
        attacker_forces.get('soldiers', 0) * 1 +
        attacker_forces.get('special_forces', 0) * 5 +
        attacker_forces.get('tanks', 0) * 50 +
        attacker_forces.get('armored_vehicles', 0) * 20 +
        attacker_forces.get('war_robots', 0) * 10 # قدرت پایه ربات‌های جنگی
    )
    
    # اعمال تأثیرات فناوری اگر attacker_id داده شده باشد
    if attacker_id:
        user_techs = military_technologies.get(str(attacker_id), {})
        tech_bonus = 1.0
        
        # محاسبه بونوس فناوری برای ربات‌های جنگی
        war_robots_tech = user_techs.get('war_robots', 1)
        if war_robots_tech > 1:
            war_robots_count = attacker_forces.get('war_robots', 0)
            tech_bonus += (war_robots_tech - 1) * 0.2  # هر لول = 20% بونوس اضافی
        
        attack_power = base_attack_power * tech_bonus
        
        # اعمال بونوس فروشگاه برای حمله‌کننده
        try:
            from bot import get_user_war_success_bonus
            shop_bonus = get_user_war_success_bonus(str(attacker_id))
            attack_power *= (1.0 + shop_bonus)
        except:
            pass
    else:
        attack_power = base_attack_power
    
    # محاسبه قدرت دفاعی (شامل توپخانه)
    defender_power = 0
    if defender_id:
        defender_techs = military_technologies.get(str(defender_id), {})
        defender_resources = users.get(defender_id, {}).get('resources', {})
        
        # قدرت پایه نیروهای دفاعی (بدون توپخانه)
        base_defense_power = (
            defender_resources.get('soldiers', 0) * 1 +
            defender_resources.get('special_forces', 0) * 5 +
            defender_resources.get('tanks', 0) * 50 +
            defender_resources.get('armored_vehicles', 0) * 20 +
            defender_resources.get('war_robots', 0) * 10
        )
        
        # اضافه کردن قدرت توپخانه (فقط برای دفاع)
        artillery_count = defender_resources.get('artillery', 0)
        artillery_tech = defender_techs.get('artillery', 1)
        artillery_power = artillery_count * 24 * (artillery_tech / 2)  # قدرت 24 با در نظر گرفتن لول
        
        defender_power = base_defense_power + artillery_power
        
        # اعمال بونوس فروشگاه برای دفاع‌کننده
        try:
            from bot import get_user_defense_power
            defense_multiplier = get_user_defense_power(str(defender_id))
            defender_power *= defense_multiplier
        except:
            pass
    else:
        # شبیه‌سازی نیروهای دفاعی (تصادفی) اگر defender_id داده نشده باشد
        defender_power = random.randint(attack_power * 0.5, attack_power * 1.5)
    
    # اعمال تاثیر آب‌وهوا بر قدرت‌ها
    try:
        mods = get_weather_modifiers(get_current_weather())
        attack_power = int(attack_power * float(mods.get('attacker_power_mul', 1.0)))
        defender_power = int(defender_power * float(mods.get('defender_power_mul', 1.0)))
    except Exception:
        pass
    
    # محاسبه نتیجه
    if attack_power > defender_power:
        victory = True
        attacker_losses = random.randint(10, 40)  # درصد تلفات
        defender_losses = random.randint(50, 80)
    else:
        victory = False
        attacker_losses = random.randint(50, 80)
        defender_losses = random.randint(10, 40)
    
    # اعمال تاثیر آب‌وهوا بر درصد تلفات
    try:
        mods = get_weather_modifiers(get_current_weather())
        attacker_losses = max(0, min(100, int(attacker_losses * float(mods.get('attacker_casualty_mul', 1.0)))))
        defender_losses = max(0, min(100, int(defender_losses * float(mods.get('defender_casualty_mul', 1.0)))))
    except Exception:
        pass
    
    return {
        'victory': victory,
        'attacker_losses_percent': attacker_losses,
        'defender_losses_percent': defender_losses,
        'attack_power': attack_power,
        'defender_power': defender_power
    }
def load_country_relations():
    global country_relations, embassies
    try:
        with open('country_relations.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            country_relations = data.get('country_relations', {})
            embassies = data.get('embassies', {})
        print(f"[DEBUG] Loaded country_relations: {country_relations}")
        print(f"[DEBUG] Loaded embassies: {embassies}")
    except Exception as e:
        country_relations = {}
        embassies = {}
        print(f"[DEBUG] Created new country_relations: {country_relations}, error: {e}")
        print(f"[DEBUG] Created new embassies: {embassies}")
        
def save_country_relations():
    print(f"[DEBUG] Saving country_relations: {country_relations}")
    print(f"[DEBUG] Saving embassies: {embassies}")
    with open('country_relations.json', 'w', encoding='utf-8') as f:
        json.dump({
            'country_relations': country_relations,
            'embassies': embassies
        }, f, ensure_ascii=False, indent=2)
    print(f"[DEBUG] Saved country_relations and embassies to file")

def save_military_package_data():
    """ذخیره اطلاعات پکیج‌های نظامی"""
    try:
        data = {
            'military_package_purchases': military_package_purchases,
            'military_package_cooldowns': military_package_cooldowns,
            'military_package_approvals': military_package_approvals
        }
        with open('military_packages.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] خطا در ذخیره اطلاعات پکیج‌های نظامی: {e}")

def load_military_package_data():
    """بارگذاری اطلاعات پکیج‌های نظامی"""
    global military_package_purchases, military_package_cooldowns, military_package_approvals
    try:
        with open('military_packages.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            military_package_purchases = data.get('military_package_purchases', {})
            military_package_cooldowns = data.get('military_package_cooldowns', {})
            military_package_approvals = data.get('military_package_approvals', {})
    except FileNotFoundError:
        print("[INFO] فایل military_packages.json یافت نشد. استفاده از مقادیر پیش‌فرض.")
    except Exception as e:
        print(f"[ERROR] خطا در بارگذاری اطلاعات پکیج‌های نظامی: {e}")

def save_resource_package_data():
    """ذخیره اطلاعات پکیج‌های منابع"""
    try:
        data = {
            'resource_package_purchases': resource_package_purchases,
            'resource_package_cooldowns': resource_package_cooldowns,
            'resource_package_approvals': resource_package_approvals
        }
        with open('resource_packages.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"خطا در ذخیره اطلاعات پکیج‌های منابع: {e}")

def load_resource_package_data():
    """بارگذاری اطلاعات پکیج‌های منابع"""
    global resource_package_purchases, resource_package_cooldowns, resource_package_approvals
    try:
        with open('resource_packages.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            resource_package_purchases = data.get('resource_package_purchases', {})
            resource_package_cooldowns = data.get('resource_package_cooldowns', {})
            resource_package_approvals = data.get('resource_package_approvals', {})
    except FileNotFoundError:
        print("فایل resource_packages.json یافت نشد، استفاده از مقادیر پیشفرض")
    except Exception as e:
        print(f"خطا در بارگذاری اطلاعات پکیج‌های منابع: {e}")

def save_economic_package_data():
    """ذخیره اطلاعات پکیج‌های اقتصادی"""
    try:
        data = {
            'economic_package_purchases': economic_package_purchases,
            'economic_package_cooldowns': economic_package_cooldowns,
            'economic_package_approvals': economic_package_approvals
        }
        with open('economic_packages.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] خطا در ذخیره اطلاعات پکیج‌های اقتصادی: {e}")

def load_economic_package_data():
    """بارگذاری اطلاعات پکیج‌های اقتصادی"""
    global economic_package_purchases, economic_package_cooldowns, economic_package_approvals
    try:
        with open('economic_packages.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            economic_package_purchases = data.get('economic_package_purchases', {})
            economic_package_cooldowns = data.get('economic_package_cooldowns', {})
            economic_package_approvals = data.get('economic_package_approvals', {})
    except FileNotFoundError:
        print("[INFO] فایل economic_packages.json یافت نشد. استفاده از مقادیر پیش‌فرض.")
    except Exception as e:
        print(f"[ERROR] خطا در بارگذاری اطلاعات پکیج‌های اقتصادی: {e}")

def save_pending_payments():
    """ذخیره پرداخت‌های در انتظار"""
    try:
        with open('pending_payments.json', 'w', encoding='utf-8') as f:
            json.dump(pending_payments, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] خطا در ذخیره پرداخت‌های در انتظار: {e}")

def load_pending_payments():
    """بارگذاری پرداخت‌های در انتظار"""
    global pending_payments
    try:
        with open('pending_payments.json', 'r', encoding='utf-8') as f:
            pending_payments = json.load(f)
    except FileNotFoundError:
        print("[INFO] فایل pending_payments.json یافت نشد. استفاده از مقادیر پیش‌فرض.")
    except Exception as e:
        print(f"[ERROR] خطا در بارگذاری پرداخت‌های در انتظار: {e}")
global_market_inventory = {}

def load_global_market():
    global global_market_inventory
    try:
        with open('global_market.json', 'r', encoding='utf-8') as f:
            global_market_inventory = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        global_market_inventory = {
            'gold': 10, 'steel': 500, 'iron': 1000, 'copper': 1000, 'diamond': 50, 'uranium': 100,
            'wheat': 1000, 'rice': 1000, 'fruits': 1000, 'oil': 10000, 'gas': 10000, 'electronics': 1000000,
            'pride_cars': 100000, 'benz_cars': 100000, 'electricity': 1000, 'uranium_ore': 1000,
                'centrifuge': 100, 'yellowcake': 1000, 'space_parts': 100, 'aluminum': 50, 'titanium': 20
        }
        save_global_market()

def get_relation_text(level):
    if level >= 80:
        return "🤝 هم پیمان نظامی"
    elif level >= 60:
        return "😊 دوست"
    elif level >= 40:
        return "🙂 شریک تجاری"
    elif level >= 20:
        return "😐  صلح"
    elif level >= -20:
        return "😐 بی طرف"
    elif level >= -40:
        return "😐 روابط سرد "
    elif level >= -60:
        return "😠 آتش بس"
    elif level >= -80:
        return "😡 اعلان جنگ"
    else:
        return "💀 جنگ"

# --- فناوری‌های نظامی و وضعیت کاربران ---
# ساختار: {user_id: {tech_key: level, ...}}
military_technologies = {}

# لیست فناوری‌های نظامی و قیمت ارتقا (جدید و کامل)
MILITARY_TECH_LIST = [
    {"key": "hydrogen_bomb", "name": "بمب هیدروژنی", "max_level": 25, "upgrade_price": 20_000_000},  # قفل تا max
    {"key": "chemical_bomb", "name": "بمب شیمیایی", "max_level": 25, "upgrade_price": 10_000_000},  # قفل تا max
    {"key": "destructive_bomb", "name": "بمب تخریبی", "max_level": 25, "upgrade_price": 13_000_000},  # قفل تا max
    {"key": "atomic_bomb", "name": "بمب اتم", "max_level": 10, "upgrade_price": 50_000_000, "uranium": 50},  # قفل تا max، نیاز به اورانیوم
    {"key": "soldiers", "name": "سربازان", "max_level": 100, "upgrade_price": 4_000_000},  # هر لول قدرت سربازان را افزایش می‌دهد
    {"key": "special_forces", "name": "نیروهای ویژه", "max_level": 100, "upgrade_price": 5_000_000},
    {"key": "tanks", "name": "تانک", "max_level": 100, "upgrade_price": 5_000_000},
    {"key": "armored_vehicles", "name": "نفربر زرهی", "max_level": 100, "upgrade_price": 5_000_000},
    {"key": "transport_planes", "name": "هواپیمای ترابری", "max_level": 100, "upgrade_price": 8_000_000},
    {"key": "helicopters", "name": "بالگرد", "max_level": 100, "upgrade_price": 5_000_000},
    {"key": "fighter_jets", "name": "جنگنده", "max_level": 100, "upgrade_price": 10_000_000},
    {"key": "bombers", "name": "بمب‌افکن", "max_level": 100, "upgrade_price": 12_000_000},
    {"key": "artillery", "name": "توپخانه", "max_level": 100, "upgrade_price": 5_000_000},
    {"key": "drones", "name": "پهپاد", "max_level": 100, "upgrade_price": 4_000_000},
    {"key": "air_defense", "name": "پدافند هوایی", "max_level": 100, "upgrade_price": 7_000_000},
    {"key": "coastal_artillery", "name": "توپ ساحلی", "max_level": 100, "upgrade_price": 6_000_000},
    {"key": "speedboats", "name": "قایق تندرو", "max_level": 100, "upgrade_price": 4_000_000},
    {"key": "naval_ship", "name": "ناوچه", "max_level": 100, "upgrade_price": 6_000_000},
    {"key": "submarines", "name": "زیردریایی", "max_level": 100, "upgrade_price": 9_000_000},
    {"key": "aircraft_carriers", "name": "ناو هواپیمابر", "max_level": 100, "upgrade_price": 14_000_000},
    {"key": "war_robots", "name": "ربات جنگی", "max_level": 100, "upgrade_price": 11_000_000},
    {"key": "ballistic_missiles", "name": "موشک بالستیک", "max_level": 100, "upgrade_price": 10_000_000},  # هر دور به تعداد لول اضافه می‌شود
    {"key": "defense_missiles", "name": "موشک دفاعی", "max_level": 100, "upgrade_price": 9_000_000},      # هر دور به تعداد لول اضافه می‌شود
]

# تابع برای اضافه کردن موشک‌ها در هر دور (فراخوانی از advance_game_turn)
def calculate_military_power_with_tech(user_id):
    """محاسبه قدرت نظامی با در نظر گرفتن لول فناوری"""
    global users
    user = users.get(user_id, {})
    user_id_str = str(user_id)
    user_techs = military_technologies.get(user_id_str, {})
    resources = user.get("resources", {})
    
    # قدرت پایه هر نیرو (بدون توپخانه و توپخانه دریایی)
    base_power = {
        'soldiers': 1,
        'special_forces': 2,
        'tanks': 3,
        'armored_vehicles': 2,
        'transport_planes': 4,
        'helicopters': 3,
        'fighter_jets': 5,
        'bombers': 6,
        'drones': 2,
        'air_defense': 4,
        'speedboats': 1,
        'naval_ship': 4,
        'submarines': 6,
        'aircraft_carriers': 24,
        'war_robots': 10,  # قدرت بالاتر برای ربات‌های جنگی
    }
    
    total_power = 0
    
    # اعمال تأثیرات حکومت بر قدرت نظامی
    military_bonus = calculate_government_military_bonus(user_id)
    military_multiplier = 1 + (military_bonus / 100)  # تبدیل درصد به ضریب
    
    for unit_type, base_unit_power in base_power.items():
        unit_count = resources.get(unit_type, 0)
        tech_level = user_techs.get(unit_type, 1)  # حداقل لول 1
        
        # قدرت = (لول فناوری ÷ 2) × تعداد آیتم × بونوس حکومت
        unit_power = (tech_level / 2) * unit_count * military_multiplier
        total_power += unit_power
    
    return total_power

def add_missiles_per_turn(user_id):
    global users
    user = users.get(user_id, {})
    # تبدیل به string برای consistency
    user_id_str = str(user_id)
    user_techs = military_technologies.get(user_id_str, {})
    resources = user.get("resources", {})
    
    print(f"[DEBUG] add_missiles_per_turn for user {user_id}")
    print(f"[DEBUG] user_id_str: {user_id_str}")
    print(f"[DEBUG] military_technologies keys: {list(military_technologies.keys())}")
    print(f"[DEBUG] user_techs: {user_techs}")
    print(f"[DEBUG] current resources: {resources}")
    
    # اضافه کردن موشک‌های بالستیک - هر لول = 1 موشک در هر دور
    ballistic_level = user_techs.get("ballistic_missiles", 0)
    if ballistic_level > 0:
        current_ballistic = resources.get("ballistic_missiles", 0)
        new_ballistic = current_ballistic + ballistic_level
        resources["ballistic_missiles"] = new_ballistic
        print(f"[DEBUG] ballistic_missiles: {current_ballistic} + {ballistic_level} = {new_ballistic}")
    
    # اضافه کردن موشک‌های دفاعی - هر لول = 1 موشک در هر دور
    defense_level = user_techs.get("defense_missiles", 0)
    if defense_level > 0:
        current_defense = resources.get("defense_missiles", 0)
        new_defense = current_defense + defense_level
        resources["defense_missiles"] = new_defense
        print(f"[DEBUG] defense_missiles: {current_defense} + {defense_level} = {new_defense}")
    
    # ذخیره تغییرات در users
    user["resources"] = resources
    users[user_id] = user
    save_users()
    print(f"[DEBUG] Saved user resources: {resources}")

MILITARY_TECH_FILE = 'military_technologies.json'

def save_military_technologies():
    print(f"[DEBUG] save_military_technologies called with: {military_technologies}")
    print(f"[DEBUG] len(military_technologies): {len(military_technologies)}")
    print(f"[DEBUG] bool(military_technologies): {bool(military_technologies)}")
    
    # فقط اگر دیکشنری خالی نیست، ذخیره کن
    if military_technologies:
        with open(MILITARY_TECH_FILE, 'w', encoding='utf-8') as f:
            json.dump(military_technologies, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] Saved military_technologies: {military_technologies}")
    else:
        print("[DEBUG] Not saving empty military_technologies")

def load_military_technologies():
    global military_technologies
    try:
        with open(MILITARY_TECH_FILE, 'r', encoding='utf-8') as f:
            military_technologies = json.load(f)
        print(f"[DEBUG] Loaded military_technologies: {military_technologies}")
    except (FileNotFoundError, json.JSONDecodeError):
        military_technologies = {}
        print(f"[DEBUG] Created new military_technologies: {military_technologies}")
        # فقط در اولین بار ذخیره کن، نه در هر بار reload
        if not military_technologies:
            save_military_technologies()

def give_all_techs_level_one(user_id):
    user_id_str = str(user_id)
    if user_id_str not in military_technologies:
        military_technologies[user_id_str] = {}
    for tech in MILITARY_TECH_LIST:
        military_technologies[user_id_str][tech["key"]] = 1
    save_military_technologies()
    print(f"[DEBUG] All techs for user {user_id_str} set to 1.")

def save_independence_loans():
    """ذخیره وام‌های فعال (برای سازگاری با کد قدیمی)"""
    from bank import save_active_loans
    save_active_loans()

def load_independence_loans():
    """بارگذاری وام‌های فعال (برای سازگاری با کد قدیمی)"""
    try:
        from bank import load_active_loans
        load_active_loans()
    except ImportError:
        # اگر bank هنوز load نشده، این تابع را skip می‌کنیم
        pass

def save_conquered_countries_data():
    try:
        with open(CONQUERED_COUNTRIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(conquered_countries_data, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] Saved conquered_countries_data: {conquered_countries_data}")
    except Exception as e:
        print(f"[DEBUG] Error saving conquered_countries_data: {e}")

def load_conquered_countries_data():
    global conquered_countries_data
    try:
        with open(CONQUERED_COUNTRIES_FILE, 'r', encoding='utf-8') as f:
            conquered_countries_data = json.load(f)
        print(f"[DEBUG] Loaded conquered_countries_data: {conquered_countries_data}")
    except Exception as e:
        conquered_countries_data = {}
        print(f"[DEBUG] Created new conquered_countries_data: {conquered_countries_data}, error: {e}")

def save_alliance_messages():
    """ذخیره تاریخچه چت اتحادها در فایل"""
    try:
        with open('alliance_messages.json', 'w', encoding='utf-8') as f:
            json.dump(alliance_messages, f, ensure_ascii=False, indent=2)
        print(f"[DEBUG] Saved alliance_messages: {len(alliance_messages)} alliances")
    except Exception as e:
        print(f"[DEBUG] Error saving alliance_messages: {e}")

def load_alliance_messages():
    """بارگذاری تاریخچه چت اتحادها از فایل"""
    global alliance_messages
    try:
        with open('alliance_messages.json', 'r', encoding='utf-8') as f:
            alliance_messages = json.load(f)
        print(f"[DEBUG] Loaded alliance_messages: {len(alliance_messages)} alliances")
    except FileNotFoundError:
        alliance_messages = {}
        print(f"[DEBUG] Created new alliance_messages: {alliance_messages}")
    except Exception as e:
        alliance_messages = {}
        print(f"[DEBUG] Error loading alliance_messages: {e}")

def save_naval_attack_saves():
    """ذخیره اطلاعات حمله دریایی"""
    try:
        with open('naval_attack_saves.json', 'w', encoding='utf-8') as f:
            json.dump(naval_attack_saves, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"خطا در ذخیره naval_attack_saves: {e}")

def load_naval_attack_saves():
    """بارگذاری اطلاعات حمله دریایی"""
    global naval_attack_saves
    try:
        with open('naval_attack_saves.json', 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
            # اگر list بود، به dict تبدیل کن
            if isinstance(loaded_data, list):
                print("⚠️ naval_attack_saves.json به صورت list بود، تبدیل به dict شد")
                naval_attack_saves = {}
            elif isinstance(loaded_data, dict):
                naval_attack_saves = loaded_data
            else:
                print("⚠️ naval_attack_saves.json فرمت نامعتبر داشت، ریست شد")
                naval_attack_saves = {}
    except (FileNotFoundError, json.JSONDecodeError):
        naval_attack_saves = {}

# بارگذاری داده‌های اولیه
load_game_data()
load_alliances()
load_country_relations()
load_player_sell_ads()
load_global_market()
load_independence_loans()
load_conquered_countries_data()
load_military_package_data()
load_economic_package_data()
load_resource_package_data()
load_pending_payments()

# بارگذاری داده‌های بانکی - به صورت lazy import
def load_bank_data_lazy():
    global overdue_debts, bank_data
    from bank import load_bank_data, load_loan_history, load_bank_accounts, load_transfer_history, load_overdue_debts, load_active_loans, bank_data as bank_bank_data
    load_bank_data()
    load_loan_history()
    load_bank_accounts()
    load_transfer_history()
    load_overdue_debts()
    load_active_loans()
    # کپی کردن bank_data از bank.py به utils
    bank_data = bank_bank_data
    # کپی کردن overdue_debts از bank.py به utils
    try:
        from bank import overdue_debts as bank_overdue_debts
        overdue_debts = bank_overdue_debts
    except:
        overdue_debts = {}

# بارگذاری اطلاعات مالیات
from jame import load_tax_data
load_tax_data()

# بارگذاری داده‌های بانکی - به صورت lazy import
# load_bank_data_lazy()

# بارگذاری تاریخچه چت اتحادها
load_alliance_messages()

def save_war_declarations():
    """ذخیره اعلان‌های جنگ"""
    try:
        # فقط ورودی‌های معتبر (ساختار جدید دیکشنری) را ذخیره کن
        cleaned = {k: v for k, v in war_declarations.items() if isinstance(v, dict)}
        if len(cleaned) != len(war_declarations):
            print(f"[DEBUG] save_war_declarations: filtered out legacy entries: {len(war_declarations) - len(cleaned)}")
        with open('war_declarations.json', 'w', encoding='utf-8') as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"خطا در ذخیره اعلان‌های جنگ: {e}")

def load_war_declarations():
    """بارگذاری اعلان‌های جنگ"""
    global war_declarations
    try:
        with open('war_declarations.json', 'r', encoding='utf-8') as f:
            loaded = json.load(f)
            # مهاجرت فرمت‌های قدیمی به فرمت جدید استاندارد
            # فرمت جدید: { war_id: { 'attacker': country_name, 'defender': country_name, 'type': str, 'status': 'active'|'ended', 'turn_declared': int } }
            migrated = {}
            if isinstance(loaded, dict):
                # تشخیص فرمت قدیمی: { user_id: [country_name, ...] }
                legacy_format = any(isinstance(v, list) for v in loaded.values())
                new_like_format = any(isinstance(v, dict) and 'status' in v for v in loaded.values())
                if legacy_format and not new_like_format:
                    for attacker_id, targets in loaded.items():
                        if not isinstance(targets, list):
                            continue
                        attacker_country = users.get(str(attacker_id), {}).get('country', str(attacker_id))
                        for defender_country in targets:
                            # war_id پایدار بسازیم
                            war_id = f"{attacker_country}->{defender_country}"
                            migrated[war_id] = {
                                'attacker': attacker_country,
                                'defender': defender_country,
                                'type': 'war_declaration',
                                'status': 'active',
                                'turn_declared': game_data.get('turn', 1)
                            }
                    war_declarations = migrated
                    # بلافاصله ذخیره کن تا فرمت جدید پایدار شود
                    save_war_declarations()
                else:
                    # فرض می‌کنیم فرمت جدید است
                    war_declarations = loaded
            else:
                war_declarations = {}
    except FileNotFoundError:
        war_declarations = {}
    except Exception as e:
        print(f"خطا در بارگذاری اعلان‌های جنگ: {e}")
        war_declarations = {}

# بارگذاری اعلان‌های جنگ - در تابع main انجام می‌شه
# load_war_declarations()

def save_secret_loan_claimed():
    """ذخیره وضعیت وام مخفی"""
    try:
        with open(SECRET_LOAN_CLAIMED_FILE, 'w', encoding='utf-8') as f:
            json.dump({'claimed': secret_loan_claimed}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"خطا در ذخیره وضعیت وام مخفی: {e}")

def load_secret_loan_claimed():
    """بارگذاری وضعیت وام مخفی"""
    global secret_loan_claimed
    try:
        with open(SECRET_LOAN_CLAIMED_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # اطمینان از اینکه data یک dict است
            if isinstance(data, dict):
                secret_loan_claimed = data.get('claimed', False)
            else:
                # اگر data یک boolean است (فایل قدیمی)
                secret_loan_claimed = bool(data)
    except FileNotFoundError:
        secret_loan_claimed = False
    except Exception as e:
        print(f"خطا در بارگذاری وضعیت وام مخفی: {e}")
        secret_loan_claimed = False

# بارگذاری وضعیت وام مخفی
load_secret_loan_claimed()

def save_economy_secret_claimed():
    """ذخیره وضعیت جایزه مخفی اقتصاد"""
    try:
        with open(ECONOMY_SECRET_CLAIMED_FILE, 'w', encoding='utf-8') as f:
            json.dump({'claimed': economy_secret_claimed}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"خطا در ذخیره وضعیت جایزه مخفی اقتصاد: {e}")

def load_economy_secret_claimed():
    """بارگذاری وضعیت جایزه مخفی اقتصاد"""
    global economy_secret_claimed
    try:
        with open(ECONOMY_SECRET_CLAIMED_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # اطمینان از اینکه data یک dict است
            if isinstance(data, dict):
                economy_secret_claimed = data.get('claimed', False)
            else:
                # اگر data یک boolean است (فایل قدیمی)
                economy_secret_claimed = bool(data)
    except FileNotFoundError:
        economy_secret_claimed = False
    except Exception as e:
        print(f"خطا در بارگذاری وضعیت جایزه مخفی اقتصاد: {e}")
        economy_secret_claimed = False

# بارگذاری وضعیت جایزه مخفی اقتصاد
load_economy_secret_claimed()

# تابع ذخیره تجارت‌های در حال انجام
def save_pending_trades():
    """ذخیره تجارت‌های در حال انجام در فایل JSON"""
    try:
        from economy import pending_trades
        trades_data = []
        for trade in pending_trades:
            # تبدیل datetime objects به string برای ذخیره
            trade_copy = trade.copy()
            if 'start_time' in trade_copy:
                trade_copy['start_time'] = str(trade_copy['start_time'])
            if 'estimated_arrival' in trade_copy:
                trade_copy['estimated_arrival'] = str(trade_copy['estimated_arrival'])
            trades_data.append(trade_copy)
        
        with open('pending_trades.json', 'w', encoding='utf-8') as f:
            json.dump(trades_data, f, ensure_ascii=False, indent=2)
        print("[DEBUG] Saved pending_trades to file")
    except Exception as e:
        print(f"[ERROR] Failed to save pending_trades: {e}")

# تابع بارگذاری تجارت‌های در حال انجام
def load_pending_trades():
    """بارگذاری تجارت‌های در حال انجام از فایل JSON"""
    try:
        from economy import pending_trades
        if os.path.exists('pending_trades.json'):
            with open('pending_trades.json', 'r', encoding='utf-8') as f:
                trades_data = json.load(f)
            
            pending_trades.clear()
            for trade in trades_data:
                # تبدیل string به datetime objects
                if 'start_time' in trade:
                    trade['start_time'] = datetime.fromisoformat(trade['start_time'])
                if 'estimated_arrival' in trade:
                    trade['estimated_arrival'] = datetime.fromisoformat(trade['estimated_arrival'])
                pending_trades.append(trade)
            
            print(f"[DEBUG] Loaded {len(pending_trades)} pending trades from file")
        else:
            print("[DEBUG] No pending_trades.json file found, starting with empty list")
    except Exception as e:
        print(f"[ERROR] Failed to load pending_trades: {e}")

# بارگذاری تجارت‌های در حال انجام
load_pending_trades()

# بارگذاری کشورها
load_countries()

# بارگذاری کاربران
load_users()

# بارگذاری اطلاعات سازمان ملل - در bot.py انجام می‌شه
# load_un_data()

def check_foreign_minister_reward(user_id, target_id):
    """بررسی و اعطای جایزه وزیر خارجه"""
    user = users.get(user_id, {})
    if not user.get('activated'):
        return False
    
    # بررسی پیشنهادات وزیر خارجه
    suggestions = user.get('foreign_minister_suggestions', {})
    if target_id not in suggestions:
        return False
    
    suggestion = suggestions[target_id]
    if suggestion.get('followed', False):
        return False  # قبلاً جایزه داده شده
    
    # بررسی اینکه آیا روابط بهبود یافته
    user_relations = country_relations.get(user_id, {})
    current_relation = user_relations.get(target_id, 0)
    
    # اگر روابط بهتر شده (بیش از 0 یا بهبود یافته)
    if current_relation > 0:
        # علامت‌گذاری که این پیشنهاد دنبال شده
        suggestion['followed'] = True
        suggestion['followed_at'] = game_data.get('turn', 1)
        
        # شمارش تعداد پیشنهادات دنبال شده
        followed_count = sum(1 for s in suggestions.values() if s.get('followed', False))
        
        # اگر 10 بار پیشنهاد دنبال شده، جایزه بده
        if followed_count >= 10:
            # اعطای جایزه 50 میلیون
            reward_amount = 50_000_000
            
            if 'resources' not in user:
                user['resources'] = {}
            if 'cash' not in user['resources']:
                user['resources']['cash'] = 0
            
            user['resources']['cash'] += reward_amount
            
            # ذخیره تغییرات
            save_users()
            
            # ارسال پیام جایزه (بدون توضیح دلیل)
            try:
                reward_message = f"🎉 <b>جایزه ویژه!</b>\n\n"
                reward_message += f"💰 مبلغ {format_price_short(reward_amount)} به حساب شما واریز شد!\n\n"
                reward_message += "🎁 این جایزه به دلیل عملکرد عالی شما در دیپلماسی اعطا شده است."
                
                # ارسال پیام جایزه
                import asyncio
                from telegram import Bot
                bot = Bot(token=BOT_TOKEN)
                asyncio.create_task(bot.send_message(
                    chat_id=int(user_id),
                    text=reward_message,
                    parse_mode='HTML'
                ))
                
                # ریست کردن شمارنده
                user['foreign_minister_suggestions'] = {}
                save_users()
                
                return True
            except Exception as e:
                print(f"خطا در ارسال جایزه وزیر خارجه: {e}")
                return False
        
        save_users()
        return True
    
    return False

def apply_government_effects(user_id):
    """اعمال تأثیرات حکومت بر کاربر"""
    user = users.get(user_id, {})
    if not user:
        return
    
    gov_type = user.get('government_type')
    if not gov_type:
        return
    
    # import از government
    from government import get_government_bonuses
    bonuses = get_government_bonuses(gov_type)
    if not bonuses:
        return
    
    # اعمال تأثیرات بر منابع
    if 'resources' not in user:
        user['resources'] = {}
    
    # اعمال تأثیرات بر تولید
    if 'production_bonus' in bonuses['bonuses']:
        bonus = bonuses['bonuses']['production_bonus']
        user['production_bonus'] = bonus
    
    # اعمال تأثیرات بر تجارت
    if 'trade_bonus' in bonuses['bonuses']:
        bonus = bonuses['bonuses']['trade_bonus']
        user['trade_bonus'] = bonus
    
    # اعمال تأثیرات بر نوآوری
    if 'innovation_bonus' in bonuses['bonuses']:
        bonus = bonuses['bonuses']['innovation_bonus']
        user['innovation_bonus'] = bonus
    
    # اعمال تأثیرات بر قدرت نظامی
    if 'military_bonus' in bonuses['bonuses']:
        bonus = bonuses['bonuses']['military_bonus']
        user['military_bonus'] = bonus
    
    # اعمال تأثیرات بر روابط دیپلماتیک
    if 'diplomatic_bonus' in bonuses['bonuses']:
        bonus = bonuses['bonuses']['diplomatic_bonus']
        user['diplomatic_bonus'] = bonus
    
    # اعمال تأثیرات بر ثبات
    if 'stability_bonus' in bonuses['bonuses']:
        bonus = bonuses['bonuses']['stability_bonus']
        user['stability_bonus'] = bonus
    
    # اعمال تأثیرات بر ریسک شورش
    if 'rebellion_risk' in bonuses['penalties']:
        penalty = bonuses['penalties']['rebellion_risk']
        user['rebellion_risk'] = penalty
    
    # اعمال تأثیرات بر سرعت تصمیم‌گیری
    
    
    
    save_users()

def calculate_government_production_bonus(user_id):
    """محاسبه بونوس تولید بر اساس حکومت"""
    user = users.get(user_id, {})
    if not user:
        return 0
    
    return user.get('production_bonus', 0)

def calculate_government_trade_bonus(user_id):
    """محاسبه بونوس تجارت بر اساس حکومت"""
    user = users.get(user_id, {})
    if not user:
        return 0
    
    return user.get('trade_bonus', 0)

def calculate_government_military_bonus(user_id):
    """محاسبه بونوس نظامی بر اساس حکومت"""
    user = users.get(user_id, {})
    if not user:
        return 0
    
    return user.get('military_bonus', 0)

def calculate_government_diplomatic_bonus(user_id):
    """محاسبه بونوس دیپلماتیک بر اساس حکومت"""
    user = users.get(user_id, {})
    if not user:
        return 0
    
    return user.get('diplomatic_bonus', 0)

def calculate_government_innovation_bonus(user_id):
    """محاسبه بونوس نوآوری بر اساس حکومت"""
    user = users.get(user_id, {})
    if not user:
        return 0
    
    return user.get('innovation_bonus', 0)

def calculate_government_stability_bonus(user_id):
    """محاسبه بونوس ثبات بر اساس حکومت"""
    user = users.get(user_id, {})
    if not user:
        return 0
    
    return user.get('stability_bonus', 0)

def get_government_rebellion_risk(user_id):
    """دریافت ریسک شورش بر اساس حکومت"""
    user = users.get(user_id, {})
    if not user:
        return 0
    
    return user.get('rebellion_risk', 0)



def calculate_country_needs(user_id):
    """محاسبه نیازهای کشور بر اساس جمعیت"""
    user = users.get(user_id, {})
    if not user:
        return {}
    
    # دریافت جمعیت کشور
    country_name = user.get('country', '')
    population = COUNTRY_POPULATIONS.get(country_name, 10000000)  # پیش‌فرض 10 میلیون
    
    # محاسبه نیازها
    needs = {
        'pride_cars': int(population * 0.001),  # 0.1% جمعیت
        'benz_cars': int(population * 0.0005),  # 0.05% جمعیت
        'electronics': int(population * 0.005),  # 0.5% جمعیت
    }
    
    return needs

def calculate_satisfaction_change(user_id):
    """محاسبه تغییر رضایت مردم با سیستم جدید"""
    user = users.get(user_id, {})
    if not user:
        return 0
    
    satisfaction_change = 0
    resources = user.get('resources', {})
    needs = calculate_country_needs(user_id)
    
    # بررسی تأمین نیازهای اصلی (بنز، چراید، الکترونیک)
    main_needs = ['benz_cars', 'pride_cars', 'electronics']
    satisfied_needs = 0
    
    for item in main_needs:
        if item in needs:
            need_amount = needs[item]
            current_amount = resources.get(item, 0)
            
            if need_amount > 0 and current_amount >= need_amount:
                satisfied_needs += 1
                satisfaction_change += 3  # +3 برای هر نیاز برآورده شده
                print(f"[DEBUG] {item} satisfied: +3 satisfaction")
            else:
                print(f"[DEBUG] {item} not satisfied: {current_amount}/{need_amount}")
    
    # تأثیر مالیات
    current_turn = game_data.get('turn', 1)
    tax_active_until = user.get('tax_active_until', 0)
    
    if current_turn <= tax_active_until:
        # اگر مالیات فعال است
        satisfaction_change -= 10  # -10 برای مالیات
        print(f"[DEBUG] Tax penalty applied for user {user_id}: -10 satisfaction")
    else:
        # اگر مالیات فعال نیست
        satisfaction_change -= 2  # -2 برای عدم دریافت مالیات
        print(f"[DEBUG] No tax penalty applied for user {user_id}: -2 satisfaction (no tax)")
    
    # مهاجران: -5% رضایت به ازای هر 1M
    try:
        imm_units = int(user.get('immigrants', 0)) // 1_000_000
        satisfaction_change -= (imm_units * 5)
    except Exception:
        pass

    print(f"[DEBUG] Final satisfaction change for user {user_id}: {satisfaction_change} (satisfied needs: {satisfied_needs}/3)")
    
    return satisfaction_change

def update_satisfaction(user_id):
    """بروزرسانی رضایت مردم"""
    user = users.get(user_id, {})
    if not user:
        return
    
    # مقدار اولیه رضایت اگر وجود نداشته باشد
    if 'satisfaction' not in user:
        user['satisfaction'] = 70  # مقدار پیش‌فرض
    
    # اگر قفل رضایت فعال است، روی 100 نگه دار
    if user.get('satisfaction_locked'):
        user['satisfaction'] = 100
    else:
        # محاسبه تغییر رضایت
        satisfaction_change = calculate_satisfaction_change(user_id)
        # اعمال تغییر
        user['satisfaction'] = max(0, min(100, user['satisfaction'] + satisfaction_change))
    
    save_users()

def get_satisfaction_status(satisfaction):
    """دریافت وضعیت رضایت مردم"""
    if satisfaction >= 80:
        return "😊 بسیار راضی", "green"
    elif satisfaction >= 60:
        return "🙂 راضی", "blue"
    elif satisfaction >= 40:
        return "😐 متوسط", "yellow"
    elif satisfaction >= 20:
        return "😟 ناراضی", "orange"
    else:
        return "😡 بسیار ناراضی", "red"

def format_satisfaction_info(user_id):
    """فرمت کردن اطلاعات رضایت مردم"""
    user = users.get(user_id, {})
    if not user:
        return "اطلاعات موجود نیست"
    
    satisfaction = user.get('satisfaction', 70)
    revolution = user.get('revolution', 0)  # درصد انقلاب
    status, color = get_satisfaction_status(satisfaction)
    needs = calculate_country_needs(user_id)
    resources = user.get('resources', {})
    
    info = f"👥 <b>وضعیت رضایت مردم</b>\n\n"
    info += f"😊 <b>رضایت فعلی:</b> {satisfaction}%\n"
    info += f"📊 <b>وضعیت:</b> {status}\n"
    info += f"🔥 <b>انقلاب:</b> {revolution}%\n\n"
    
    info += "📋 <b>نیازهای کشور:</b>\n"
    for item, need_amount in needs.items():
        current_amount = resources.get(item, 0)
        supply_percentage = (current_amount / need_amount * 100) if need_amount > 0 else 100
        
        item_names = {
            'pride_cars': 'پراید',
            'benz_cars': 'بنز',
            'electronics': 'الکترونیک'
        }
        
        item_name = item_names.get(item, item)
        status_emoji = "✅" if supply_percentage >= 100 else "❌"
        
        info += f"{status_emoji} {item_name}: {current_amount:,} / {need_amount:,} ({supply_percentage:.1f}%)\n"
    
    return info

def apply_war_satisfaction_effect(user_id, victory):
    """اعمال تأثیر جنگ بر رضایت مردم"""
    user = users.get(user_id, {})
    if not user:
        return
    
    # مقدار اولیه رضایت اگر وجود نداشته باشد
    if 'satisfaction' not in user:
        user['satisfaction'] = 70
    
    if victory:
        # پیروزی در جنگ: +5% رضایت
        user['satisfaction'] = min(100, user['satisfaction'] + 5)
    else:
        # شکست در جنگ: -5% رضایت
        user['satisfaction'] = max(0, user['satisfaction'] - 5)
    
    save_users()

def suppress_revolution(user_id):
    """سرکوب شورش - افزایش رضایت و انقلاب"""
    user = users.get(user_id, {})
    if not user:
        return False, "کاربر یافت نشد"
    
    # مقدار اولیه اگر وجود نداشته باشد
    if 'satisfaction' not in user:
        user['satisfaction'] = 70
    if 'revolution' not in user:
        user['revolution'] = 0
    
    # افزایش رضایت و انقلاب
    user['satisfaction'] = min(100, user['satisfaction'] + 30)
    user['revolution'] = min(100, user['revolution'] + 30)
    
    save_users()
    
    return True, f"✅ سرکوب شورش انجام شد!\n😊 رضایت: +30% (فعلی: {user['satisfaction']}%)\n🔥 انقلاب: +30% (فعلی: {user['revolution']}%)"

def check_revolution_status(user_id):
    """بررسی وضعیت انقلاب"""
    user = users.get(user_id, {})
    if not user:
        return False, None
    
    revolution = user.get('revolution', 0)
    if revolution >= 100:
        return True, "کشور سقوط کرده است!"
    return False, None

async def handle_country_collapse(user_id):
    """مدیریت سقوط کشور"""
    user = users.get(user_id, {})
    if not user:
        return
    
    country_name = user.get('country', 'کشور ناشناس')
    player_name = user.get('player_name', 'بازیکن ناشناس')
    
    # ارسال پیام به کانال اخبار و خود کاربر
    from bot import bot, NEWS_CHANNEL_ID
    try:
        news_text = f"🔥 <b>اخبار فوری!</b>\n\n"
        news_text += f"🏛️ کشور {country_name} سقوط کرد!\n"
        news_text += f"👤 رهبر: {player_name}\n"
        news_text += f"📅 تاریخ: {get_current_date()}\n\n"
        news_text += "⚖️ رهبر کشور باید تصمیم بگیرد:\n"
        news_text += "1️⃣ فرار از کشور\n"
        news_text += "2️⃣ ماندن و محاکمه شدن"
        
        await bot.send_message(chat_id=NEWS_CHANNEL_ID, text=news_text, parse_mode='HTML')
        # ارسال پیام انتخاب به خود کاربر
        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [InlineKeyboardButton('🏃‍♂️ فرار از کشور', callback_data='escape_country')],
                [InlineKeyboardButton('⚖️ ماندن و محاکمه', callback_data='start_trial')]
            ]
            await bot.send_message(chat_id=int(user_id), text=(
                "🔥 <b>کشور شما سقوط کرد!</b>\n\n"
                "شما دو گزینه دارید:\n"
                "1️⃣ فرار از کشور (کشور غیرفعال می‌شود)\n"
                "2️⃣ ماندن و محاکمه شدن (۵ دقیقه فرصت دفاع)"
            ), parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            print(f"خطا در ارسال پیام انتخاب به کاربر {user_id}: {e}")
    except Exception as e:
        print(f"خطا در ارسال پیام به کانال اخبار: {e}")
    
    # تنظیم وضعیت سقوط
    user['country_collapsed'] = True
    user['collapse_time'] = time.time()
    save_users()

async def escape_from_country(user_id):
    """فرار از کشور"""
    user = users.get(user_id, {})
    if not user:
        return False, "کاربر یافت نشد"
    
    country_name = user.get('country', 'کشور ناشناس')
    player_name = user.get('player_name', 'بازیکن ناشناس')
    
    # غیرفعال کردن کشور
    user['activated'] = False
    user['country_collapsed'] = False
    user['revolution'] = 0
    user['satisfaction'] = 70
    
    save_users()
    
    # ارسال پیام به کانال اخبار
    from bot import bot, NEWS_CHANNEL_ID
    try:
        news_text = f"🏃‍♂️ <b>اخبار فوری!</b>\n\n"
        news_text += f"👤 {player_name} از کشور {country_name} فرار کرد!\n"
        news_text += f"📅 تاریخ: {get_current_date()}\n\n"
        news_text += "🏛️ کشور غیرفعال شد و رهبر از قدرت برکنار شد."
        
        await bot.send_message(chat_id=NEWS_CHANNEL_ID, text=news_text, parse_mode='HTML')
    except Exception as e:
        print(f"خطا در ارسال پیام به کانال اخبار: {e}")
    
    return True, "🏃‍♂️ شما از کشور فرار کردید و کشور غیرفعال شد."

# بانک سؤالات دادگاه
TRIAL_QUESTIONS = [
    {
        "question": "چرا مردم باید دوباره به شما اعتماد کنند؟",
        "correct": "اصلاح ساختار مالی و پاسخ‌گویی شفاف را آغاز کرده‌ام.",
        "emotional": "سال‌ها شب و روز فداکاری کرده‌ام، این خود نشانه وفاداری من است.",
        "wrong": "مردم موظفند به دولت اعتماد کنند چون انتخابشان همین بوده."
    },
    {
        "question": "علت بحران اخیر در کشور چه بود؟",
        "correct": "ترکیبی از ضعف داخلی و فشار خارجی که نیازمند اصلاح است.",
        "emotional": "این یک امتحان الهی بود که همه باید تحمل می‌کردیم.",
        "wrong": "بحران در واقع وجود نداشت، ساخته‌ی رسانه‌ها بود."
    },
    {
        "question": "برنامه شما برای آینده چیست؟",
        "correct": "ایجاد اشتغال پایدار با جذب سرمایه و توسعه زیرساخت.",
        "emotional": "روزی دوباره عظمت تاریخی‌مان بازخواهد گشت.",
        "wrong": "گذشته پرافتخار ما کافیست، نیازی به تغییر جدی نیست."
    },
    {
        "question": "در برابر مخالفان سیاسی چه خواهید کرد؟",
        "correct": "با اصلاح قانون، مشارکت همه جریان‌ها را تضمین می‌کنیم.",
        "emotional": "من از هیچ دشمنی نمی‌ترسم و مقابله می‌کنم.",
        "wrong": "مخالفان اگر ناراضی‌اند، بهتر است کشور را ترک کنند."
    },
    {
        "question": "چگونه اعتماد سرمایه‌گذاران خارجی را جلب می‌کنید؟",
        "correct": "با ثبات قوانین و تضمین امنیت حقوقی سرمایه‌گذاران.",
        "emotional": "نام ملت ما آنقدر بزرگ است که همه خواهان همکاری‌اند.",
        "wrong": "ما به سرمایه خارجی نیازی نداریم، باید آن‌ها به ما وابسته شوند."
    },
    {
        "question": "چرا سطح رضایت مردم کاهش یافته؟",
        "correct": "به دلیل مشکلات معیشتی که با اصلاحات اقتصادی جبران خواهد شد.",
        "emotional": "مردم همیشه ناراضی‌اند حتی اگر همه‌چیز خوب باشد.",
        "wrong": "نارضایتی وجود ندارد، این توهم دشمنان است."
    },
    {
        "question": "در برابر تحریم‌های خارجی چه می‌کنید؟",
        "correct": "تنوع‌بخشی به اقتصاد داخلی و تقویت روابط با شرکای جدید.",
        "emotional": "تحریم‌ها انگیزه ما برای ایستادگی بیشتر است.",
        "wrong": "تحریم‌ها هیچ اثری ندارند، می‌توان آن‌ها را نادیده گرفت."
    },
    {
        "question": "چرا اعتراضات خیابانی افزایش یافت؟",
        "correct": "بی‌توجهی به مطالبات مردم و مشکلات اقتصادی.",
        "emotional": "اعتراض‌ها نشانه‌ی عشق مردم به وطن است.",
        "wrong": "اعتراض‌کنندگان همه عامل بیگانه‌اند."
    },
    {
        "question": "نقش شما در بحران اخیر چه بود؟",
        "correct": "من مسئولیت ضعف مدیریت را می‌پذیرم و اصلاح می‌کنم.",
        "emotional": "من هم قربانی شرایط سخت مثل دیگران بودم.",
        "wrong": "من هیچ نقشی ندارم، دیگران باید پاسخگو باشند."
    },
    {
        "question": "چگونه امنیت کشور را تضمین می‌کنید؟",
        "correct": "با تقویت نیروهای قانونی و شفاف‌سازی عملکرد آن‌ها.",
        "emotional": "من شخصاً در خط مقدم امنیت می‌ایستم.",
        "wrong": "هرکس ناامنی ایجاد کند را باید بدون محاکمه حذف کرد."
    },
    {
        "question": "چرا اعتماد مردم به دولت کاهش یافت؟",
        "correct": "به دلیل وعده‌های برآورده‌نشده و ضعف پاسخ‌گویی.",
        "emotional": "مردم توقعات بی‌پایان دارند.",
        "wrong": "اعتماد کم نشده، فقط رسانه‌ها القا می‌کنند."
    },
    {
        "question": "با فساد اداری چگونه مقابله می‌کنید؟",
        "correct": "ایجاد سیستم شفافیت مالی و نظارت مستقل.",
        "emotional": "من خودم با فساد دشمنی شخصی دارم.",
        "wrong": "فساد بخشی طبیعی از هر حکومتی است."
    },
    {
        "question": "چرا وضعیت اقتصادی بدتر شد؟",
        "correct": "بی‌انضباطی مالی و وابستگی به یک منبع درآمد.",
        "emotional": "اقتصاد قربانی دشمنی‌ها و سرنوشت تلخ ماست.",
        "wrong": "اقتصاد کشور در بهترین وضعیت تاریخ است."
    },
    {
        "question": "برای جوانان چه برنامه‌ای دارید؟",
        "correct": "ایجاد فرصت شغلی از طریق حمایت از استارتاپ‌ها.",
        "emotional": "جوانان باید صبور باشند، آینده روشن است.",
        "wrong": "جوانان تجربه ندارند و نباید انتظار زیادی داشته باشند."
    },
    {
        "question": "علت مهاجرت گسترده مردم چیست؟",
        "correct": "نبود فرصت شغلی و ضعف امید اجتماعی.",
        "emotional": "مهاجرت همیشه بخشی از سرنوشت ملت‌ها بوده.",
        "wrong": "فقط خائنین کشور را ترک می‌کنند."
    },
    {
        "question": "چه‌طور می‌خواهید وحدت ملی را حفظ کنید؟",
        "correct": "با احترام به تنوع فرهنگی و مشارکت برابر همه گروه‌ها.",
        "emotional": "ملت ما همیشه متحد بوده و خواهد بود.",
        "wrong": "کسانی که متفاوت فکر می‌کنند تهدیدی برای وحدت‌اند."
    },
    {
        "question": "چرا مردم در انتخابات شرکت کمتری کردند؟",
        "correct": "به دلیل بی‌اعتمادی به روند و نبود شفافیت.",
        "emotional": "مردم خسته بودند و شرایط سخت بود.",
        "wrong": "عدم شرکت نشان وفاداری خاموش به حکومت است."
    },
    {
        "question": "چگونه می‌خواهید عدالت اجتماعی برقرار کنید؟",
        "correct": "با توزیع عادلانه منابع و اصلاح نظام مالیاتی.",
        "emotional": "عدالت در قلب همه ماست و خود به خود محقق می‌شود.",
        "wrong": "عدالت کامل هیچ‌وقت شدنی نیست، پس ضرورتی ندارد."
    },
    {
        "question": "چرا قیمت‌ها بی‌ثبات است؟",
        "correct": "به دلیل نبود نظارت کافی و تورم ناشی از کسری بودجه.",
        "emotional": "این سختی‌ها موقتی است و باید تحمل کرد.",
        "wrong": "افزایش قیمت‌ها نشانه رونق اقتصادی است."
    },
    {
        "question": "در برابر فشار افکار عمومی چه می‌کنید؟",
        "correct": "به خواسته‌های قانونی مردم گوش داده و سیاست‌ها را اصلاح می‌کنم.",
        "emotional": "فشارها نشانه‌ی عشق مردم به رهبری من است.",
        "wrong": "افکار عمومی ارزش تحلیل ندارد، فقط احساسات زودگذر است."
    }
]

def start_trial(user_id):
    """شروع محاکمه"""
    user = users.get(user_id, {})
    if not user:
        return False, "کاربر یافت نشد"
    
    # انتخاب 3 سؤال تصادفی
    import random
    selected_questions = random.sample(TRIAL_QUESTIONS, 3)
    
    # تنظیم زمان محاکمه (5 دقیقه)
    user['trial_start_time'] = time.time()
    user['trial_duration'] = 300  # 5 دقیقه
    user['trial_active'] = True
    user['trial_questions'] = selected_questions
    user['trial_answers'] = []
    user['trial_current_question'] = 0
    
    save_users()
    
    return True, "⚖️ محاکمه شروع شد! شما 5 دقیقه فرصت دارید تا به 3 سؤال پاسخ دهید."

def get_trial_question(user_id):
    """دریافت سؤال فعلی محاکمه"""
    user = users.get(user_id, {})
    if not user or not user.get('trial_active', False):
        return None, None
    
    questions = user.get('trial_questions', [])
    current_question = user.get('trial_current_question', 0)
    
    if current_question >= len(questions):
        return None, None
    
    question_data = questions[current_question]
    
    # ایجاد لیست پاسخ‌ها با callback_data
    answers = [
        {'text': question_data['correct'], 'callback_data': 'trial_answer_correct'},
        {'text': question_data['emotional'], 'callback_data': 'trial_answer_emotional'},
        {'text': question_data['wrong'], 'callback_data': 'trial_answer_wrong'}
    ]
    
    # رندوم کردن ترتیب پاسخ‌ها
    import random
    random.shuffle(answers)
    
    # ایجاد دکمه‌های پاسخ با ترتیب رندوم
    keyboard = [[answer] for answer in answers]
    
    reply_markup = keyboard
    
    return question_data['question'], reply_markup

async def process_trial_answer(user_id, answer_type):
    """پردازش پاسخ محاکمه"""
    user = users.get(user_id, {})
    if not user or not user.get('trial_active', False):
        return False, "محاکمه فعال نیست"
    
    # امتیازدهی بر اساس نوع پاسخ
    score_map = {
        'correct': 80,    # انتخاب درست (منطقی)
        'emotional': 30,  # انتخاب احساسی
        'wrong': 10      # انتخاب غلط
    }
    
    score = score_map.get(answer_type, 0)
    user['trial_answers'].append(score)
    
    # رفتن به سؤال بعدی
    user['trial_current_question'] += 1
    
    # بررسی اتمام سؤالات
    if user['trial_current_question'] >= len(user.get('trial_questions', [])):
        # محاسبه میانگین امتیاز
        avg_score = sum(user['trial_answers']) / len(user['trial_answers'])
        user['trial_final_score'] = avg_score
        
        # انجام محاکمه نهایی
        success, message = await conduct_trial(user_id, avg_score)
        return success, message
    else:
        save_users()
        return True, "پاسخ ثبت شد. سؤال بعدی:"

def get_current_date():
    """دریافت تاریخ فعلی به فرمت فارسی"""
    from datetime import datetime
    now = datetime.now()
    persian_months = {
        1: 'فروردین', 2: 'اردیبهشت', 3: 'خرداد',
        4: 'تیر', 5: 'مرداد', 6: 'شهریور',
        7: 'مهر', 8: 'آبان', 9: 'آذر',
        10: 'دی', 11: 'بهمن', 12: 'اسفند'
    }
    return f"{now.day} {persian_months[now.month]} {now.year}"

async def conduct_trial(user_id, defense_percentage):
    """انجام محاکمه"""
    user = users.get(user_id, {})
    if not user:
        return False, "کاربر یافت نشد"
    
    country_name = user.get('country', 'کشور ناشناس')
    player_name = user.get('player_name', 'بازیکن ناشناس')
    
    if defense_percentage >= 51:
        # موفقیت در دفاع
        user['activated'] = True
        user['country_collapsed'] = False
        user['revolution'] = 0
        user['satisfaction'] = 60
        user['trial_active'] = False
        
        save_users()
        
        # ارسال پیام به کانال اخبار
        from bot import bot, NEWS_CHANNEL_ID
        try:
            news_text = f"✅ <b>اخبار فوری!</b>\n\n"
            news_text += f"⚖️ محاکمه {player_name} در کشور {country_name} با موفقیت به پایان رسید!\n"
            news_text += f"📊 درصد دفاع: {defense_percentage:.1f}%\n"
            news_text += f"📅 تاریخ: {get_current_date()}\n\n"
            news_text += "🏛️ کشور به حالت عادی بازگشت و رضایت مردم به 60% رسید.\n"
            news_text += "🎉 رهبر کشور با موفقیت از بحران عبور کرد!"
            
            await bot.send_message(chat_id=NEWS_CHANNEL_ID, text=news_text, parse_mode='HTML')
        except Exception as e:
            print(f"خطا در ارسال پیام به کانال اخبار: {e}")
        
        # نمایش جزئیات امتیازات
        answers = user.get('trial_answers', [])
        details = ""
        for i, score in enumerate(answers, 1):
            if score >= 80:
                details += f"سؤال {i}: ✅ انتخاب منطقی ({score}%)\n"
            elif score >= 30:
                details += f"سؤال {i}: 🔸 انتخاب احساسی ({score}%)\n"
            else:
                details += f"سؤال {i}: ❌ انتخاب غلط ({score}%)\n"
        
        return True, f"🎉 <b>محاکمه موفقیت‌آمیز بود!</b>\n\n📊 <b>درصد دفاع:</b> {defense_percentage:.1f}%\n😊 <b>رضایت مردم:</b> 60%\n🏛️ <b>وضعیت:</b> کشور به حالت عادی بازگشت\n\n📋 <b>جزئیات امتیازات:</b>\n{details}\n✅ شما با موفقیت از بحران عبور کردید!"
    else:
        # شکست در دفاع
        user['activated'] = False
        user['country_collapsed'] = False
        user['trial_active'] = False
        
        save_users()
        
        # ارسال پیام به کانال اخبار
        from bot import bot, NEWS_CHANNEL_ID
        try:
            news_text = f"❌ <b>اخبار فوری!</b>\n\n"
            news_text += f"⚖️ محاکمه {player_name} در کشور {country_name} با شکست مواجه شد!\n"
            news_text += f"📊 درصد دفاع: {defense_percentage:.1f}%\n"
            news_text += f"📅 تاریخ: {get_current_date()}\n\n"
            news_text += "🏛️ کشور غیرفعال شد و رهبر از قدرت برکنار شد.\n"
            news_text += "🚫 رهبر کشور به دلیل عدم توانایی در دفاع، تبعید شد."
            
            await bot.send_message(chat_id=NEWS_CHANNEL_ID, text=news_text, parse_mode='HTML')
        except Exception as e:
            print(f"خطا در ارسال پیام به کانال اخبار: {e}")
        
        # نمایش جزئیات امتیازات
        answers = user.get('trial_answers', [])
        details = ""
        for i, score in enumerate(answers, 1):
            if score >= 80:
                details += f"سؤال {i}: ✅ انتخاب منطقی ({score}%)\n"
            elif score >= 30:
                details += f"سؤال {i}: 🔸 انتخاب احساسی ({score}%)\n"
            else:
                details += f"سؤال {i}: ❌ انتخاب غلط ({score}%)\n"
        
        return False, f"❌ <b>محاکمه با شکست مواجه شد!</b>\n\n📊 <b>درصد دفاع:</b> {defense_percentage:.1f}%\n🏛️ <b>وضعیت:</b> کشور غیرفعال شد\n🚫 <b>نتیجه:</b> شما تبعید شدید\n\n📋 <b>جزئیات امتیازات:</b>\n{details}\n💔 متأسفانه نتوانستید از بحران عبور کنید."

# تولید خودکار معادن و کشاورزی برای هر کاربر
# تولید متعادل بر اساس قیمت و استفاده
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

# Pending state for National Security organization creation flow
pending_national_security = {}

# --- Capital system helpers ---

# دیکشنری پایتخت‌های پیشفرض
DEFAULT_CAPITALS = {
    'ایران': 'تهران',
    'آلمان': 'برلین',
    'آمریکا': 'نیویورک',
    'انگلستان': 'لندن',
    'فرانسه': 'پاریس',
    'روسیه': 'مسکو',
    'چین': 'پکن',
    'ژاپن': 'توکیو',
    'کره جنوبی': 'سئول',
    'هند': 'دهلی نو',
    'برزیل': 'برازیلیا',
    'کانادا': 'اتاوا',
    'استرالیا': 'کانبرا',
    'ایتالیا': 'رم',
    'اسپانیا': 'مادرید',
    'ترکیه': 'آنکارا',
    'عربستان سعودی': 'ریاض',
    'مصر': 'قاهره',
    'آفریقای جنوبی': 'کیپ تاون',
    'مکزیک': 'مکزیکو سیتی',
    'آرژانتین': 'بوئنوس آیرس',
    'شیلی': 'سانتیاگو',
    'پرو': 'لیما',
    'کلمبیا': 'بوگوتا',
    'ونزوئلا': 'کاراکاس',
    'اکوادور': 'کیتو',
    'بولیوی': 'لاپاز',
    'پاراگوئه': 'آسونسیون',
    'اروگوئه': 'مونته‌ویدئو',
    'پاکستان': 'اسلام‌آباد',
    'بنگلادش': 'داکا',
    'اندونزی': 'جاکارتا',
    'مالزی': 'کوالالامپور',
    'تایلند': 'بانکوک',
    'ویتنام': 'هانوی',
    'فیلیپین': 'مانیل',
    'سنگاپور': 'سنگاپور',
    'نیوزیلند': 'ولینگتون',
    'نروژ': 'اسلو',
    'سوئد': 'استکهلم',
    'فنلاند': 'هلسینکی',
    'دانمارک': 'کپنهاگ',
    'هلند': 'آمستردام',
    'بلژیک': 'بروکسل',
    'سوئیس': 'برن',
    'اتریش': 'وین',
    'لهستان': 'ورشو',
    'چک': 'پراگ',
    'مجارستان': 'بوداپست',
    'رومانی': 'بخارست',
    'بلغارستان': 'صوفیه',
    'یونان': 'آتن',
    'پرتغال': 'لیسبون',
    'ایرلند': 'دوبلین',
    'ایسلند': 'ریکیاویک',
    'گرینلند': 'نوک',
    'مراکش': 'رباط',
    'الجزایر': 'الجزیره',
    'تونس': 'تونس',
    'لیبی': 'طرابلس',
    'سودان': 'خرطوم',
    'اتیوپی': 'آدیس آبابا',
    'کنیا': 'نایروبی',
    'تانزانیا': 'دودوما',
    'اوگاندا': 'کامپالا',
    'روآندا': 'کیگالی',
    'نیجریه': 'آبوجا',
    'غنا': 'آکرا',
    'ساحل عاج': 'یاموسوکرو',
    'سنگال': 'داکار',
    'مالی': 'باماکو',
    'بورکینافاسو': 'واگادوگو',
    'نیجر': 'نیامی',
    'چاد': 'انجامنا',
    'کامرون': 'یائونده',
    'جمهوری آفریقای مرکزی': 'بانگی',
    'جمهوری دموکراتیک کنگو': 'کینشاسا',
    'جمهوری کنگو': 'برازاویل',
    'گابن': 'لیبرویل',
    'گینه استوایی': 'مالابو',
    'سائوتومه و پرنسیپ': 'سائوتومه',
    'آنگولا': 'لواندا',
    'زامبیا': 'لوساکا',
    'زیمبابوه': 'هراره',
    'بوتسوانا': 'گابورون',
    'نامیبیا': 'ویندهوک',
    'لسوتو': 'ماسرو',
    'سوازیلند': 'امبابانه',
    'ماداگاسکار': 'آنتاناناریوو',
    'موریس': 'پورت لوئیس',
    'سیشل': 'ویکتوریا',
    'کومور': 'مورونی',
    'جیبوتی': 'جیبوتی',
    'اریتره': 'اسمره',
    'سومالی': 'موگادیشو',
    'موزامبیک': 'ماپوتو',
    'مالاوی': 'لیلونگوه',
    'زیمبابوه': 'هراره',
    'بوتسوانا': 'گابورون',
    'نامیبیا': 'ویندهوک',
    'آفریقای جنوبی': 'کیپ تاون',
    'لسوتو': 'ماسرو',
    'سوازیلند': 'امبابانه',
    'ماداگاسکار': 'آنتاناناریوو',
    'موریس': 'پورت لوئیس',
    'سیشل': 'ویکتوریا',
    'کومور': 'مورونی',
    'جیبوتی': 'جیبوتی',
    'اریتره': 'اسمره',
    'سومالی': 'موگادیشو',
    'موزامبیک': 'ماپوتو',
    'مالاوی': 'لیلونگوه'
}

def get_user_capital(user_id):
    """دریافت نام پایتخت کاربر بر اساس نام کشور"""
    if user_id not in users:
        return ''
    
    country = users[user_id].get('country', '')
    if not country:
        return ''
    
    # حذف پرچم از نام کشور (اگر وجود دارد)
    import re
    # حذف emoji های پرچم (🇦🇧🇨🇩🇪🇫🇬🇭🇮🇯🇰🇱🇲🇳🇴🇵🇶🇷🇸🇹🇺🇻🇼🇽🇾🇿)
    country_clean = re.sub(r'[🇦-🇿]', '', country).strip()
    
    # جستجو در دیکشنری پایتخت‌های پیشفرض
    capital = DEFAULT_CAPITALS.get(country_clean, '')
    if capital:
        return capital
    
    # اگر پایتخت پیدا نشد، نام کشور خالص را برگردان
    return country_clean

def set_user_capital(user_id, capital_name):
    """تنظیم نام پایتخت کاربر (اختیاری - برای موارد خاص)"""
    if user_id not in users:
        return False
    
    users[user_id]['capital'] = capital_name
    save_users()
    return True

def get_user_country_with_capital(user_id):
    """دریافت نام کشور همراه با پایتخت"""
    if user_id not in users:
        return ''
    
    country = users[user_id].get('country', '')
    capital = get_user_capital(user_id)
    
    if capital and capital != country:
        return f"{country} ({capital})"
    else:
        return country

# --- Country name canonicalization helpers ---

def get_canonical_country_display(name: str) -> str:
    """Return a canonical display name (with flag if available) for a given country-like name.
    Uses normalization to match aliases and falls back to the input stripped.
    """
    try:
        norm = _normalize_country_name(name)
        # Prefer names from loaded countries list if available
        try:
            for c in countries:
                if isinstance(c, dict):
                    disp = c.get('name') or ''
                    if _normalize_country_name(disp) == norm:
                        return disp
        except Exception:
            pass
        # Fallback to sea-border list (contains flags for many major countries)
        try:
            for disp in SEA_BORDER_COUNTRIES:
                if _normalize_country_name(disp) == norm:
                    return disp
        except Exception:
            pass
        # As last resort, return normalized string (without flag)
        return norm
    except Exception:
        return str(name)

def equal_country_names(a: str, b: str) -> bool:
    """Case/spacing/flag-insensitive comparison of two country names."""
    try:
        return _normalize_country_name(a) == _normalize_country_name(b)
    except Exception:
        return str(a) == str(b)

def get_canonical_country_name(name: str) -> str:
    """Return the official country name from countries list by normalized match.
    Falls back to the input name if no match found.
    """
    try:
        if not name:
            return name
        norm = _normalize_country_name(name)
        # Build cache of normalized -> official
        mapping = {}
        try:
            for c in countries:
                if isinstance(c, dict):
                    cname = c.get('name', '')
                else:
                    cname = str(c)
                if not cname:
                    continue
                mapping[_normalize_country_name(cname)] = cname
        except Exception:
            pass
        return mapping.get(norm, name)
    except Exception:
        return name
