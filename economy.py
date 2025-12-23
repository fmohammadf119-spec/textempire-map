import asyncio
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from uuid import uuid4
from datetime import datetime, timedelta
import utils
import re
import json
from utils import format_price_short, NEWS_CHANNEL_ID, NAVAL_ATTACK_CHANNEL_ID, ADMIN_ID, pending_sell_amount, pending_sell_total_price, game_data, global_market_inventory, save_users, save_global_market, pending_trades, player_sell_ads, save_player_sell_ads, country_relations, save_country_relations, SEA_BORDER_COUNTRIES
from battle import send_media_safe


# شرکت‌های معروف برای هر کشور (50 شرکت برتر جهان)
company_templates = {
    # 🌍 ابرقدرت‌ها
    'چین': [
        {'symbol': 'HUAWEI', 'name': 'Huawei Technologies Co., Ltd.', 'price': 85, 'growth': 3.2, 'description': 'غول تکنولوژی و مخابرات چین، پیشگام در شبکه‌های 5G'},
        {'symbol': 'ALIBABA', 'name': 'Alibaba Group Holding Limited', 'price': 75, 'growth': -1.5, 'description': 'بزرگترین شرکت تجارت الکترونیک و فناوری چین'}
    ],
    'روسیه': [
        {'symbol': 'GAZPROM', 'name': 'Gazprom PJSC', 'price': 25, 'growth': -15.2, 'description': 'بزرگترین شرکت گاز طبیعی جهان و صادرکننده اصلی انرژی روسیه'}
    ],
    'بریتانیا': [
        {'symbol': 'BP', 'name': 'British Petroleum PLC', 'price': 35, 'growth': -0.8, 'description': 'یکی از بزرگترین شرکت‌های نفتی جهان با فعالیت در 70 کشور'}
    ],
    'آمریکا': [
        {'symbol': 'APPLE', 'name': 'Apple Inc.', 'price': 150, 'growth': 2.5, 'description': 'پیشگام تکنولوژی و تولیدکننده آیفون، مک و محصولات دیجیتال'},
        {'symbol': 'MICROSOFT', 'name': 'Microsoft Corporation', 'price': 280, 'growth': 1.8, 'description': 'غول نرم‌افزار جهان، سازنده ویندوز و آفیس'}
    ],
    
    # 🌐 قدرت‌های منطقه‌ای
    'ژاپن': [
        {'symbol': 'TOYOTA', 'name': 'Toyota Motor Corporation', 'price': 25, 'growth': 2.8, 'description': 'بزرگترین تولیدکننده خودرو جهان و پیشگام در تکنولوژی هیبریدی'}
    ],
    'آلمان': [
        {'symbol': 'VOLKSWAGEN', 'name': 'Volkswagen AG', 'price': 45, 'growth': 1.2, 'description': 'بزرگترین تولیدکننده خودرو اروپا با برندهای معروف مثل آئودی و پورشه'},
        {'symbol': 'SIEMENS', 'name': 'Siemens AG', 'price': 85, 'growth': 1.5, 'description': 'غول صنعتی آلمان در زمینه انرژی، حمل و نقل و اتوماسیون'}
    ],
    'فرانسه': [
        {'symbol': 'TOTAL', 'name': 'TotalEnergies SE', 'price': 55, 'growth': 1.3, 'description': 'بزرگترین شرکت نفتی فرانسه و یکی از غول‌های انرژی جهان'},
        {'symbol': 'AIRBUS', 'name': 'Airbus SE', 'price': 120, 'growth': 2.1, 'description': 'بزرگترین تولیدکننده هواپیماهای مسافربری جهان'}
    ],
    'هند': [
        {'symbol': 'RELIANCE', 'name': 'Reliance Industries Limited', 'price': 25, 'growth': 3.1, 'description': 'بزرگترین شرکت خصوصی هند در زمینه نفت، گاز و مخابرات'},
        {'symbol': 'TATA', 'name': 'Tata Group', 'price': 35, 'growth': 2.4, 'description': 'غول صنعتی هند با فعالیت در خودرو، فولاد، فناوری و خدمات مالی'}
    ],
    'ایتالیا': [
        {'symbol': 'ENI', 'name': 'Eni S.p.A.', 'price': 25, 'growth': 0.9, 'description': 'شرکت ملی نفت و گاز ایتالیا با فعالیت در 70 کشور جهان'}
    ],
    'کانادا': [
        {'symbol': 'RBC', 'name': 'Royal Bank of Canada', 'price': 95, 'growth': 1.7, 'description': 'بزرگترین بانک کانادا و یکی از قوی‌ترین موسسات مالی جهان'},
        {'symbol': 'SHOPIFY', 'name': 'Shopify Inc.', 'price': 45, 'growth': 4.2, 'description': 'پلتفرم پیشرو تجارت الکترونیک برای کسب و کارهای آنلاین'}
    ],
    'ایران': [
        {'symbol': 'NIOC', 'name': 'شرکت ملی نفت ایران', 'price': 25, 'growth': 1.5, 'description': 'شرکت ملی نفت ایران، چهارمین تولیدکننده نفت جهان'}
    ],
    'کره جنوبی': [
        {'symbol': 'SAMSUNG', 'name': 'Samsung Electronics Co., Ltd.', 'price': 70, 'growth': 2.3, 'description': 'غول تکنولوژی کره جنوبی در تولید گوشی، تلویزیون و تراشه'}
    ],
    
    # 🚀 قدرت‌های نوظهور
    'برزیل': [
        {'symbol': 'PETROBRAS', 'name': 'Petrobras', 'price': 25, 'growth': -0.8, 'description': 'شرکت ملی نفت برزیل و یکی از بزرگترین شرکت‌های نفتی آمریکای لاتین'}
    ],
    'ترکیه': [
        {'symbol': 'TURKISH_AIR', 'name': 'Turkish Airlines', 'price': 25, 'growth': 1.8, 'description': 'بزرگترین خط هوایی ترکیه و یکی از پیشگامان صنعت هوانوردی'},
        {'symbol': 'BAYKAR', 'name': 'Baykar Defense', 'price': 25, 'growth': 3.5, 'description': 'تولیدکننده پیشرفته پهپادهای نظامی و تکنولوژی دفاعی'}
    ],
    'اسرائیل': [
        {'symbol': 'TEVA', 'name': 'Teva Pharmaceutical Industries', 'price': 25, 'growth': 1.2, 'description': 'بزرگترین تولیدکننده داروهای ژنریک جهان'},
        {'symbol': 'ELBIT', 'name': 'Elbit Systems Ltd.', 'price': 25, 'growth': 2.8, 'description': 'شرکت پیشرفته تکنولوژی دفاعی و هوافضا'}
    ],
    'اسپانیا': [
        {'symbol': 'SANTANDER', 'name': 'Banco Santander S.A.', 'price': 25, 'growth': 0.7, 'description': 'بزرگترین بانک اسپانیا و یکی از قوی‌ترین بانک‌های اروپا'},
        {'symbol': 'TELEFONICA', 'name': 'Telefónica S.A.', 'price': 25, 'growth': 0.9, 'description': 'غول مخابرات اسپانیا با فعالیت در اروپا و آمریکای لاتین'}
    ],
    'عربستان سعودی': [
        {'symbol': 'ARAMCO', 'name': 'Saudi Aramco', 'price': 30, 'growth': 2.1, 'description': 'بزرگترین شرکت نفتی جهان و ارزشمندترین شرکت سهامی عام'}
    ],
    'سوئیس': [
        {'symbol': 'NESTLE', 'name': 'Nestlé S.A.', 'price': 95, 'growth': 1.7, 'description': 'بزرگترین شرکت مواد غذایی جهان با 2000 برند مختلف'},
        {'symbol': 'NOVARTIS', 'name': 'Novartis AG', 'price': 85, 'growth': 1.9, 'description': 'غول داروسازی سوئیس و یکی از بزرگترین شرکت‌های دارویی جهان'}
    ],
    'مکزیک': [
        {'symbol': 'PEMEX', 'name': 'Petróleos Mexicanos', 'price': 25, 'growth': -0.5, 'description': 'شرکت ملی نفت مکزیک و بزرگترین شرکت انرژی آمریکای لاتین'}
    ],
    'مصر': [
        {'symbol': 'EGYPTAIR', 'name': 'EgyptAir', 'price': 25, 'growth': 0.8, 'description': 'خط هوایی ملی مصر و یکی از قدیمی‌ترین شرکت‌های هواپیمایی آفریقا'},
        {'symbol': 'EGPC', 'name': 'Egyptian General Petroleum Corporation', 'price': 25, 'growth': 1.1, 'description': 'شرکت ملی نفت مصر و کنترل‌کننده صنعت انرژی کشور'}
    ],
    'پاکستان': [
        {'symbol': 'PAKISTAN_STEEL', 'name': 'Pakistan Steel Mills', 'price': 25, 'growth': -0.3, 'description': 'بزرگترین کارخانه فولاد پاکستان و ستون صنعت کشور'},
        {'symbol': 'ENGRO', 'name': 'Engro Corporation Limited', 'price': 25, 'growth': 0.9, 'description': 'غول صنعتی پاکستان در زمینه انرژی، کشاورزی و مواد شیمیایی'}
    ],
    'استرالیا': [
        {'symbol': 'BHP', 'name': 'BHP Group Limited', 'price': 45, 'growth': 1.8, 'description': 'بزرگترین شرکت معدن‌کاری جهان در زمینه مس، آهن و زغال سنگ'}
    ],
    
    # ⚖️ کشورهای عادی
    'اندونزی': [
        {'symbol': 'PERTAMINA', 'name': 'Pertamina', 'price': 25, 'growth': 0.7, 'description': 'شرکت ملی نفت اندونزی و کنترل‌کننده صنعت انرژی کشور'}
    ],
    'اوکراین': [
        {'symbol': 'NAFTOGAZ', 'name': 'Naftogaz of Ukraine', 'price': 25, 'growth': -5.2, 'description': 'شرکت ملی نفت و گاز اوکراین، تحت تاثیر جنگ روسیه'},
        {'symbol': 'MOTOR_SICH', 'name': 'Motor Sich', 'price': 25, 'growth': -8.5, 'description': 'تولیدکننده موتورهای هواپیما و هلیکوپتر، آسیب دیده از جنگ'}
    ],
    'لهستان': [
        {'symbol': 'PKN_ORLEN', 'name': 'PKN Orlen S.A.', 'price': 25, 'growth': 1.2, 'description': 'بزرگترین شرکت نفتی لهستان و یکی از قوی‌ترین شرکت‌های اروپای شرقی'}
    ],
    'نیجریه': [
        {'symbol': 'DANGOTE', 'name': 'Dangote Group', 'price': 25, 'growth': 1.5, 'description': 'بزرگترین شرکت خصوصی آفریقا در زمینه سیمان، شکر و نفت'}
    ],
    'تایلند': [
        {'symbol': 'THAI_AIRWAYS', 'name': 'Thai Airways International', 'price': 25, 'growth': -1.2, 'description': 'خط هوایی ملی تایلند، تحت بازسازی مالی'},
        {'symbol': 'PTT', 'name': 'PTT Public Company Limited', 'price': 25, 'growth': 0.8, 'description': 'شرکت ملی نفت تایلند و بزرگترین شرکت انرژی جنوب شرق آسیا'}
    ],
    'امارات متحده عربی': [
        {'symbol': 'EMIRATES', 'name': 'Emirates Airlines', 'price': 25, 'growth': 2.3, 'description': 'بزرگترین خط هوایی خاورمیانه و یکی از لوکس‌ترین شرکت‌های هواپیمایی'},
        {'symbol': 'ADNOC', 'name': 'Abu Dhabi National Oil Company', 'price': 25, 'growth': 1.8, 'description': 'شرکت ملی نفت ابوظبی و یکی از بزرگترین تولیدکنندگان نفت جهان'}
    ],
    'قطر': [
        {'symbol': 'QATAR_ENERGY', 'name': 'QatarEnergy', 'price': 25, 'growth': 2.5, 'description': 'بزرگترین تولیدکننده گاز طبیعی مایع جهان'},
        {'symbol': 'QATAR_AIRWAYS', 'name': 'Qatar Airways', 'price': 25, 'growth': 2.1, 'description': 'خط هوایی ملی قطر و یکی از بهترین شرکت‌های هواپیمایی جهان'}
    ],
    'آفریقای جنوبی': [
        {'symbol': 'SASOL', 'name': 'Sasol Limited', 'price': 25, 'growth': 0.6, 'description': 'پیشگام در تکنولوژی تبدیل زغال سنگ به سوخت مایع'},
        {'symbol': 'MTN', 'name': 'MTN Group Limited', 'price': 25, 'growth': 1.1, 'description': 'بزرگترین اپراتور مخابرات آفریقا با حضور در 20 کشور'}
    ],
    'ویتنام': [
        {'symbol': 'VIETTEL', 'name': 'Viettel Group', 'price': 25, 'growth': 1.3, 'description': 'بزرگترین اپراتور مخابرات ویتنام و شرکت نظامی-تجاری'},
        {'symbol': 'VINGROUP', 'name': 'VinGroup', 'price': 25, 'growth': 1.7, 'description': 'غول صنعتی ویتنام در زمینه خودرو، املاک و تکنولوژی'}
    ],
    'مالزی': [
        {'symbol': 'PETRONAS', 'name': 'Petronas', 'price': 25, 'growth': 1.4, 'description': 'شرکت ملی نفت مالزی و یکی از قوی‌ترین شرکت‌های انرژی آسیا'}
    ],
    'آرژانتین': [
        {'symbol': 'YPF', 'name': 'YPF S.A.', 'price': 25, 'growth': -0.8, 'description': 'شرکت ملی نفت آرژانتین، تحت تاثیر مشکلات اقتصادی کشور'}
    ],
    'سوئد': [
        {'symbol': 'ERICSSON', 'name': 'Ericsson AB', 'price': 25, 'growth': 1.2, 'description': 'پیشگام تکنولوژی مخابرات و شبکه‌های 5G جهان'},
        {'symbol': 'VOLVO', 'name': 'Volvo Group', 'price': 25, 'growth': 1.8, 'description': 'تولیدکننده معروف کامیون، اتوبوس و ماشین‌آلات صنعتی'}
    ],
    'نروژ': [
        {'symbol': 'EQUINOR', 'name': 'Equinor ASA', 'price': 25, 'growth': 1.6, 'description': 'شرکت ملی نفت نروژ و پیشگام در انرژی‌های تجدیدپذیر'}
    ],
    'هلند': [
        {'symbol': 'SHELL', 'name': 'Royal Dutch Shell PLC', 'price': 65, 'growth': -1.2, 'description': 'یکی از بزرگترین شرکت‌های نفتی جهان با سابقه 100 ساله'},
        {'symbol': 'PHILIPS', 'name': 'Koninklijke Philips N.V.', 'price': 25, 'growth': 0.9, 'description': 'غول تکنولوژی هلند در زمینه تجهیزات پزشکی و روشنایی'}
    ],
    'عراق': [
        {'symbol': 'INOC', 'name': 'Iraqi National Oil Company', 'price': 25, 'growth': 0.5, 'description': 'شرکت ملی نفت عراق و کنترل‌کننده ذخایر نفتی کشور'}
    ],
    'قزاقستان': [
        {'symbol': 'KAZMUNAYGAS', 'name': 'KazMunayGas', 'price': 25, 'growth': 0.8, 'description': 'شرکت ملی نفت و گاز قزاقستان و بزرگترین شرکت انرژی آسیای مرکزی'}
    ],
    'الجزایر': [
        {'symbol': 'SONATRACH', 'name': 'Sonatrach', 'price': 25, 'growth': 0.9, 'description': 'شرکت ملی نفت الجزایر و بزرگترین شرکت انرژی آفریقا'}
    ],
    'یونان': [
        {'symbol': 'HELLENIC_PETROLEUM', 'name': 'Hellenic Petroleum S.A.', 'price': 25, 'growth': 0.7, 'description': 'بزرگترین شرکت نفتی یونان و کنترل‌کننده صنعت انرژی'},
        {'symbol': 'OTE', 'name': 'Hellenic Telecommunications Organization', 'price': 25, 'growth': 0.6, 'description': 'اپراتور اصلی مخابرات یونان و ارائه‌دهنده خدمات دیجیتال'}
    ],
    'رومانی': [
        {'symbol': 'OMV_PETROM', 'name': 'OMV Petrom S.A.', 'price': 4, 'growth': 0.8, 'description': 'بزرگترین شرکت نفتی رومانی و یکی از قوی‌ترین شرکت‌های اروپای شرقی'}
    ],
    'فیلیپین': [
        {'symbol': 'SAN_MIGUEL', 'name': 'San Miguel Corporation', 'price': 3, 'growth': 0.9, 'description': 'بزرگترین شرکت خصوصی فیلیپین در زمینه غذا، نوشیدنی و انرژی'}
    ],
    'بلژیک': [
        {'symbol': 'AB_INBEV', 'name': 'Anheuser-Busch InBev', 'price': 55, 'growth': 1.1, 'description': 'بزرگترین شرکت تولیدکننده آبجو جهان با 500 برند مختلف'}
    ],
    'دانمارک': [
        {'symbol': 'MAERSK', 'name': 'A.P. Møller-Mærsk A/S', 'price': 85, 'growth': 1.4, 'description': 'بزرگترین شرکت کشتیرانی جهان و پیشگام در حمل و نقل دریایی'}
    ],
    'اتریش': [
        {'symbol': 'OMV', 'name': 'OMV AG', 'price': 85, 'growth': 1.2, 'description': 'بزرگترین شرکت نفتی اتریش و یکی از قوی‌ترین شرکت‌های انرژی اروپا'}
    ],
    'مجارستان': [
        {'symbol': 'MOL', 'name': 'MOL Group', 'price': 12, 'growth': 0.8, 'description': 'بزرگترین شرکت نفتی مجارستان و پیشگام در انرژی‌های تجدیدپذیر'}
    ],
    'جمهوری چک': [
        {'symbol': 'CEZ', 'name': 'ČEZ Group', 'price': 18, 'growth': 1.0, 'description': 'بزرگترین شرکت انرژی جمهوری چک و تولیدکننده برق و گاز'}
    ],
    'فنلاند': [
        {'symbol': 'NOKIA', 'name': 'Nokia Corporation', 'price': 4, 'growth': 0.5, 'description': 'پیشگام تکنولوژی مخابرات فنلاند و سازنده تجهیزات شبکه'}
    ],
    'پرتغال': [
        {'symbol': 'EDP', 'name': 'EDP - Energias de Portugal', 'price': 8, 'growth': 0.7, 'description': 'بزرگترین شرکت انرژی پرتغال و پیشگام در انرژی‌های تجدیدپذیر'}
    ],
    'صربستان': [
        {'symbol': 'NIS', 'name': 'Naftna Industrija Srbije', 'price': 2, 'growth': 0.6, 'description': 'شرکت ملی نفت صربستان و کنترل‌کننده صنعت انرژی کشور'}
    ]
}
# --------------------- وضعیت/ذخیره بازار سهام ---------------------
STOCK_MARKET_FILE = 'stock_market.json'
STOCK_MARKET_STATE = {
    # 'prices': { 'AAPL': 150.0, ... },
    # 'growth': { 'AAPL': +1.2, ... }  # درصد تغییر آخرین دور
}

def load_stock_market():
    global STOCK_MARKET_STATE
    try:
        with open(STOCK_MARKET_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                STOCK_MARKET_STATE = data
    except (FileNotFoundError, json.JSONDecodeError):
        STOCK_MARKET_STATE = {'prices': {}, 'growth': {}}

def save_stock_market():
    try:
        with open(STOCK_MARKET_FILE, 'w', encoding='utf-8') as f:
            json.dump(STOCK_MARKET_STATE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[DEBUG] Failed to save stock market: {e}")

# بارگذاری در شروع ماژول
load_stock_market()

# پرچم‌های کشورها
country_flags = {
    # 🌍 ابرقدرت‌ها
    'آمریکا': '🇺🇸', 'چین': '🇨🇳', 'روسیه': '🇷🇺', 'بریتانیا': '🇬🇧',
    
    # 🌐 قدرت‌های منطقه‌ای
    'ژاپن': '🇯🇵', 'آلمان': '🇩🇪', 'فرانسه': '🇫🇷', 'هند': '🇮🇳', 'ایتالیا': '🇮🇹', 
    'کانادا': '🇨🇦', 'ایران': '🇮🇷', 'کره جنوبی': '🇰🇷',
    
    # 🚀 قدرت‌های نوظهور
    'برزیل': '🇧🇷', 'ترکیه': '🇹🇷', 'اسرائیل': '🇮🇱', 'اسپانیا': '🇪🇸', 
    'عربستان سعودی': '🇸🇦', 'سوئیس': '🇨🇭', 'مکزیک': '🇲🇽', 'مصر': '🇪🇬', 
    'پاکستان': '🇵🇰', 'استرالیا': '🇦🇺',
    
    # ⚖️ کشورهای عادی
    'اندونزی': '🇮🇩', 'اوکراین': '🇺🇦', 'لهستان': '🇵🇱', 'نیجریه': '🇳🇬', 
    'تایلند': '🇹🇭', 'امارات متحده عربی': '🇦🇪', 'قطر': '🇶🇦', 'آفریقای جنوبی': '🇿🇦', 
    'ویتنام': '🇻🇳', 'مالزی': '🇲🇾', 'آرژانتین': '🇦🇷', 'سوئد': '🇸🇪', 
    'نروژ': '🇳🇴', 'هلند': '🇳🇱', 'عراق': '🇮🇶', 'قزاقستان': '🇰🇿', 
    'الجزایر': '🇩🇿', 'یونان': '🇬🇷', 'رومانی': '🇷🇴', 'فیلیپین': '🇵🇭', 
    'بلژیک': '🇧🇪', 'دانمارک': '🇩🇰', 'اتریش': '🇦🇹', 'مجارستان': '🇭🇺', 
    'جمهوری چک': '🇨🇿', 'فنلاند': '🇫🇮', 'پرتغال': '🇵🇹', 'صربستان': '🇷🇸'
}

# تعریف متغیر pending_global_trade در این فایل
pending_global_trade = {}
# متغیرهای مورد نیاز (باید از bot.py ایمپورت شوند یا global باشند):
# users, game_data, global_market_inventory, save_users, save_global_market, player_sell_ads, pending_trades, NEWS_CHANNEL_ID

# تابع تعیین نوع تجارت
def determine_trade_type(from_country, to_country):
    """تعیین نوع تجارت بر اساس موقعیت جغرافیایی کشورها"""
    from_sea = from_country in SEA_BORDER_COUNTRIES
    to_sea = to_country in SEA_BORDER_COUNTRIES
    
    if from_sea and to_sea:
        return "naval"  # تجارت دریایی
    elif not from_sea and not to_sea:
        return "land"   # تجارت زمینی
    else:
        return "mixed"  # تجارت مختلط

# تابع محاسبه زمان‌های تجارت مختلط
def calculate_mixed_trade_times():
    """محاسبه زمان‌های تجارت مختلط"""
    phase1_duration = 600  # 10 دقیقه
    phase2_duration = 600  # 10 دقیقه
    return phase1_duration, phase2_duration

# تابع مدیریت مراحل تجارت مختلط
async def handle_mixed_trade_phases(trade, bot):
    """مدیریت مراحل تجارت مختلط"""
    from_country = trade['seller_country']
    to_country = trade['buyer_country']
    
    # مرحله 1: بر اساس کشور مبدا
    phase1_duration = trade['phase1_duration']
    await asyncio.sleep(phase1_duration)
    
    # تعیین نوع مرحله 1
    from_sea = from_country in SEA_BORDER_COUNTRIES
    phase1_type = "🌊 تجارت دریایی" if from_sea else "🛤️ تجارت زمینی"
    phase1_attack = "حمله به کشتی تجاری" if from_sea else "غارت کاروان"
    
    # اطلاع‌رسانی تغییر فاز (فقط یک‌بار)
    if not trade.get('phase_change_announced'):
        # انتخاب رندوم فایل برای تغییر نوع تجارت
        change_photos = [
            "https://t.me/TextEmpire_IR/67",   # عکس
            "https://t.me/TextEmpire_IR/177"   # گیف
        ]
        change_photo = random.choice(change_photos)
        change_text = f"🔄 تغییر نوع تجارت!\n\nتجارت میان {from_country} و {to_country}\nمرحله 1: {phase1_type} (10 دقیقه)\nمرحله 2: {'🌊 تجارت دریایی' if not from_sea else '🛤️ تجارت زمینی'} (10 دقیقه)\n\nحالا قابل {phase1_attack} است."
        await send_media_safe(bot, NEWS_CHANNEL_ID, change_photo, change_text, 'HTML')
        await send_media_safe(bot, int(trade['buyer_id']), change_photo, change_text, 'HTML')
        await send_media_safe(bot, int(trade['seller_id']), change_photo, change_text, 'HTML')
        trade['phase_change_announced'] = True
        from utils import save_pending_trades
        save_pending_trades()
    
    # مرحله 2: بر اساس کشور مقصد
    phase2_duration = trade['phase2_duration']
    await asyncio.sleep(phase2_duration)
    
    # تکمیل تجارت
    await finalize_trade_after_delay(trade, 1, bot)  # 1 ثانیه تاخیر برای اطمینان


async def show_trade_menu(query):
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    current_turn = utils.game_data.get('turn', 1)
    panel_suspensions = user.get('panel_suspensions', {})
    if current_turn < panel_suspensions.get('trade', 0):
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_game_menu')]]
        await query.edit_message_text(
            '⚫️ <b>دوره سوگواری اقتصادی</b>\n\nبه دلیل ترور وزیر دارایی، این بخش تا دو دور آینده در دسترس نیست.',
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML'
        )
        return
    
    # استفاده از وزیر دارایی انتخاب شده
    selected_officials = user.get('selected_officials', {})
    if 'finance' in selected_officials:
        finance_minister = selected_officials['finance']
    else:
        # اگر وزیر دارایی انتخاب نشده، از اسامی پیش‌فرض استفاده کن
        finance_minister = {'name': 'وزیر دارایی', 'title': 'وزیر دارایی'}
    
    # پیام خوشامدگویی اقتصادی
    welcome_text = f'💰 <b>خوش آمدید!</b>\n\n'
    welcome_text += f'💼 من {finance_minister["name"]}، {finance_minister["title"]} شما هستم.\n'
    welcome_text += f'🏛️ <b>منوی تجارت و اقتصاد کشور شما</b>\n\n'
    
    # تحلیل هوشمند تجارت (اگر وزیر دارایی زنده است)
    try:
        is_alive = user.get('selected_officials', {}).get('finance', {}).get('alive', True)
        if is_alive:
            from analysis import generate_trade_analysis
            analysis = generate_trade_analysis(user_id)
            welcome_text += f'<b>پیشنهاد {finance_minister["title"]} {finance_minister["name"]}:</b>\n<blockquote>{analysis}</blockquote>\n\n'
        else:
            welcome_text += '<b>پیشنهاد وزیر دارایی:</b>\n<blockquote>این مقام ترور شده و پیشنهادی ارائه نمی‌شود.</blockquote>\n\n'
    except Exception:
        pass
    welcome_text += 'یکی از گزینه‌های زیر را انتخاب کنید:'
    
    keyboard = [
        [InlineKeyboardButton('خرید از بازیکن 👤', callback_data='buy_from_player')],
        [InlineKeyboardButton('فروش به بازیکن 👥', callback_data='sell_to_player')],
        [InlineKeyboardButton('خرید از بازار جهانی 🌍', callback_data='buy_from_market')],
        [InlineKeyboardButton('فروش به بازار جهانی 🌎', callback_data='sell_to_market')],
        [InlineKeyboardButton('مدیریت آگهی‌های فروش 🗂', callback_data='manage_sell_ads')],
        [InlineKeyboardButton('قیمت‌ها 💰', callback_data='show_prices')],
        [InlineKeyboardButton('بازار سهام خارجی 📈', callback_data='foreign_exchange_market')],
        [InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_game_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='HTML')

# وضعیت خرید/فروش بازار جهانی برای هر کاربر


# نمایش منابع بازار جهانی به صورت دو ستونی
async def show_global_market_resources(query, action):
    resource_names = {
        'gold': '🪙 طلا', 'steel': '🔧 فولاد', 'iron': '🔩 آهن', 'copper': '🔌 مس', 'aluminum': '🔧 آلومینیوم', 'titanium': '🔧 تیتانیوم', 'diamond': '💎 الماس', 'uranium': '☢️ اورانیوم',
        'wheat': '🌾 گندم', 'rice': '🍚 برنج', 'fruits': '🍎 میوه', 'oil': '🛢️ نفت', 'gas': '⛽ گاز', 'electronics': '📱 الکترونیک',
        'pride_cars': '🚗 پراید', 'benz_cars': '🚙 بنز', 'electricity': '⚡ برق',
        'uranium_ore': '⛏️ سنگ اورانیوم', 'centrifuge': '🔬 سانتریفیوژ', 'yellowcake': '🍰 کیک زرد', 'space_parts': '🚀 قطعات فضایی'
    }
    resources = list(resource_names.keys())
    keyboard = []
    for i in range(0, len(resources), 2):
        row = []
        for j in range(2):
            if i + j < len(resources):
                res = resources[i + j]
                row.append(InlineKeyboardButton(resource_names[res], callback_data=f'{action}_choose_{res}'))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_trade')])
    await query.edit_message_text('کدام منبع را انتخاب می‌کنید؟', reply_markup=InlineKeyboardMarkup(keyboard))

# مرحله اول خرید از بازار جهانی
async def buy_from_market_start(query, user_id):
    await show_global_market_resources(query, 'buy_market')

# مرحله اول فروش به بازار جهانی
async def sell_to_market_start(query, user_id):
    await show_global_market_resources(query, 'sell_market')

# مرحله دوم خرید: نمایش موجودی بازار جهانی
async def buy_market_show_inventory(query, user_id, resource):
    # تحریم اقتصادی UN: کشور تحت تحریم حق خرید از بازار جهانی ندارد
    try:
        from utils import is_country_under_un_economic_sanction
        buyer_country = utils.users.get(user_id, {}).get('country', '')
        if is_country_under_un_economic_sanction(buyer_country):
            await query.answer("❌ کشور شما تحت تحریم اقتصادی UN است و حق خرید از بازار جهانی را ندارد.", show_alert=True)
            return
    except Exception:
        pass
    amount = global_market_inventory.get(resource, 0)
    resource_names = {
        'gold': '🪙 طلا', 'steel': '🔧 فولاد', 'iron': '🔩 آهن', 'copper': '🔌 مس', 'aluminum': '🔧 آلومینیوم', 'titanium': '🔧 تیتانیوم', 'diamond': '💎 الماس', 'uranium': '☢️ اورانیوم',
        'wheat': '🌾 گندم', 'rice': '🍚 برنج', 'fruits': '🍎 میوه', 'oil': '🛢️ نفت', 'gas': '⛽ گاز', 'electronics': '📱 الکترونیک',
        'pride_cars': '🚗 پراید', 'benz_cars': '🚙 بنز', 'electricity': '⚡ برق',
        'uranium_ore': '⛏️ سنگ اورانیوم', 'centrifuge': '🔬 سانتریفیوژ', 'yellowcake': '🍰 کیک زرد', 'space_parts': '🚀 قطعات فضایی'
    }
    name = resource_names.get(resource, resource)
    if amount <= 0:
        await query.edit_message_text(f'موجودی بازار جهانی برای {name} صفر است و امکان خرید وجود ندارد.')
        return
    pending_global_trade[user_id] = {'action': 'buy', 'resource': resource}
    await query.edit_message_text(f'موجودی بازار جهانی برای {name}: {amount:,}\nچه تعداد می‌خواهید بخرید؟ (عدد را ارسال کنید)')

# مرحله دوم فروش: دریافت تعداد
async def sell_market_ask_amount(query, user_id, resource):
    # تحریم اقتصادی UN: کشور تحت تحریم حق فروش به بازار جهانی ندارد
    try:
        from utils import is_country_under_un_economic_sanction
        seller_country = utils.users.get(user_id, {}).get('country', '')
        if is_country_under_un_economic_sanction(seller_country):
            await query.answer("❌ کشور شما تحت تحریم اقتصادی UN است و حق فروش به بازار جهانی را ندارد.", show_alert=True)
            return
    except Exception:
        pass
    pending_global_trade[user_id] = {'action': 'sell', 'resource': resource}
    resource_names = {
        'gold': '🪙 طلا', 'steel': '🔧 فولاد', 'iron': '🔩 آهن', 'copper': '🔌 مس', 'aluminum': '🔧 آلومینیوم', 'titanium': '🔧 تیتانیوم', 'diamond': '💎 الماس', 'uranium': '☢️ اورانیوم',
        'wheat': '🌾 گندم', 'rice': '🍚 برنج', 'fruits': '🍎 میوه', 'oil': '🛢️ نفت', 'gas': '⛽ گاز', 'electronics': '📱 الکترونیک',
        'pride_cars': '🚗 پراید', 'benz_cars': '🚙 بنز', 'electricity': '⚡ برق',
        'uranium_ore': '⛏️ سنگ اورانیوم', 'centrifuge': '🔬 سانتریفیوژ', 'yellowcake': '🍰 کیک زرد', 'space_parts': '🚀 قطعات فضایی'
    }
    name = resource_names.get(resource, resource)
    await query.edit_message_text(f'چه تعداد از {name} می‌خواهید به بازار جهانی بفروشید؟ (عدد را ارسال کنید)')

# هندلر پیام متنی برای خرید/فروش بازار جهانی
async def handle_global_market_amount(update, context):
    user_id = str(update.effective_user.id)
    if user_id not in pending_global_trade:
        return
    data = pending_global_trade[user_id]
    action = data['action']
    resource = data['resource']
    # اگر خرید از بازار جهانی است و کشور کاربر توسط یک کشور تحریم‌کننده مالک منبع هدف‌گذاری شده، محدودیت نداریم چون بازار جهانی است.
    # اما اگر بخواهیم سخت‌گیرانه باشیم می‌توان بررسی کرد. فعلاً بازار جهانی را آزاد می‌گذاریم.
    try:
        amount = int((update.message.text if hasattr(update.message, 'text') and update.message.text else '').replace(',', ''))
    except Exception:
        await update.message.reply_text('عدد وارد شده معتبر نیست. لطفاً فقط عدد وارد کنید.')
        pending_global_trade.pop(user_id, None)
        return
    if amount <= 0:
        await update.message.reply_text('تعداد وارد شده باید بیشتر از صفر باشد.')
        pending_global_trade.pop(user_id, None)
        return
    user = utils.users.get(user_id, {})
    resources = user.get('resources', {})
    price = game_data.get('prices', {}).get(resource, 0)
    if action == 'buy':
        market_amount = global_market_inventory.get(resource, 0)
        if amount > market_amount:
            await update.message.reply_text('موجودی بازار جهانی کافی نیست. معامله لغو شد.')
            pending_global_trade.pop(user_id, None)
            return
        total_price = price * amount
        if resources.get('cash', 0) < total_price:
            await update.message.reply_text('موجودی نقد شما کافی نیست. معامله لغو شد.')
            pending_global_trade.pop(user_id, None)
            return
        # انجام خرید
        resources['cash'] -= total_price
        resources[resource] = resources.get(resource, 0) + amount
        # به‌روزرسانی utils.users
        utils.users[user_id]['resources'] = resources
        global_market_inventory[resource] -= amount
        save_users()
        save_global_market()
        resource_names = {
            'gold': '🪙 طلا', 'steel': '🔧 فولاد', 'iron': '🔩 آهن', 'copper': '🔌 مس', 'aluminum': '🔧 آلومینیوم', 'titanium': '🔧 تیتانیوم', 'diamond': '💎 الماس', 'uranium': '☢️ اورانیوم',
            'wheat': '🌾 گندم', 'rice': '🍚 برنج', 'fruits': '🍎 میوه', 'oil': '🛢️ نفت', 'gas': '⛽ گاز', 'electronics': '📱 الکترونیک',
            'pride_cars': '🚗 پراید', 'benz_cars': '🚙 بنز', 'electricity': '⚡ برق',
            'uranium_ore': '⛏️ سنگ اورانیوم', 'centrifuge': '🔬 سانتریفیوژ', 'yellowcake': '🍰 کیک زرد', 'space_parts': '🚀 قطعات فضایی'
        }
        name = resource_names.get(resource, resource)
        await update.message.reply_text(f'خرید {amount:,} واحد {name} با موفقیت انجام شد و {total_price:,} دلار از حساب شما کسر شد.')
        pending_global_trade.pop(user_id, None)
    elif action == 'sell':
        current_amount = resources.get(resource, 0)
        if current_amount < amount:
            resource_names = {
                'gold': '🪙 طلا', 'steel': '🔧 فولاد', 'iron': '🔩 آهن', 'copper': '🔌 مس', 'aluminum': '🔧 آلومینیوم', 'titanium': '🔧 تیتانیوم', 'diamond': '💎 الماس', 'uranium': '☢️ اورانیوم',
                'wheat': '🌾 گندم', 'rice': '🍚 برنج', 'fruits': '🍎 میوه', 'oil': '🛢️ نفت', 'gas': '⛽ گاز', 'electronics': '📱 الکترونیک',
                'pride_cars': '🚗 پراید', 'benz_cars': '🚙 بنز', 'electricity': '⚡ برق',
                'uranium_ore': '⛏️ سنگ اورانیوم', 'centrifuge': '🔬 سانتریفیوژ', 'yellowcake': '🍰 کیک زرد', 'space_parts': '🚀 قطعات فضایی'
            }
            name = resource_names.get(resource, resource)
            await update.message.reply_text(f'موجودی شما کافی نیست. موجودی شما: {current_amount:,} واحد، درخواست شما: {amount:,} واحد. معامله لغو شد.')
            pending_global_trade.pop(user_id, None)
            return
        total_price = price * amount
        resources[resource] -= amount
        resources['cash'] = resources.get('cash', 0) + total_price
        # به‌روزرسانی utils.users
        utils.users[user_id]['resources'] = resources
        global_market_inventory[resource] += amount
        save_users()
        save_global_market()
        resource_names = {
            'gold': '🪙 طلا', 'steel': '🔧 فولاد', 'iron': '🔩 آهن', 'copper': '🔌 مس', 'aluminum': '🔧 آلومینیوم', 'titanium': '🔧 تیتانیوم', 'diamond': '💎 الماس', 'uranium': '☢️ اورانیوم',
            'wheat': '🌾 گندم', 'rice': '🍚 برنج', 'fruits': '🍎 میوه', 'oil': '🛢️ نفت', 'gas': '⛽ گاز', 'electronics': '📱 الکترونیک',
            'pride_cars': '🚗 پراید', 'benz_cars': '🚙 بنز', 'electricity': '⚡ برق',
            'uranium_ore': '⛏️ سنگ اورانیوم', 'centrifuge': '🔬 سانتریفیوژ', 'yellowcake': '🍰 کیک زرد', 'space_parts': '🚀 قطعات فضایی'
        }
        name = resource_names.get(resource, resource)
        await update.message.reply_text(f'فروش {amount:,} واحد {name} با موفقیت انجام شد و {total_price:,} دلار به حساب شما واریز شد.')
        pending_global_trade.pop(user_id, None)


# منوی قیمت‌ها
async def show_prices_menu(query):
    units = {
        'iron': 'تن',
        'copper': 'تن',
        'uranium_ore': 'تن',
        'uranium': 'کیلوگرم',
        'steel': 'تن',
        'aluminum': 'تن',
        'titanium': 'کیلوگرم',
        'diamond': 'کیلوگرم',
        'gold': 'کیلوگرم',
        'wheat': 'تن',
        'rice': 'تن',
        'fruits': 'تن',
        'oil': 'بشکه',
        'gas': 'متر مکعب',
        'electronics': 'عدد',
        'pride_cars': 'عدد',
        'benz_cars': 'عدد',
        'electricity': 'مگاوات',
        'centrifuge': 'عدد',
        'yellowcake': 'کیلوگرم',
        'space_parts': 'عدد',
        # واحدهای نظامی
        'soldiers': 'نفر', 'special_forces': 'نفر', 'tanks': 'عدد', 'armored_vehicles': 'عدد',
        'transport_planes': 'عدد', 'helicopters': 'عدد', 'fighter_jets': 'عدد', 'bombers': 'عدد',
        'artillery': 'عدد', 'drones': 'عدد', 'air_defense': 'عدد', 'coastal_artillery': 'عدد',
        'speedboats': 'عدد', 'naval_ship': 'عدد', 'submarines': 'عدد', 'aircraft_carriers': 'عدد',
        'war_robots': 'عدد', 'defense_missiles': 'عدد', 'ballistic_missiles': 'عدد'
    }
    prices_text = f"""
💰 <b>قیمت‌های فعلی بازار</b>\n\n
🪙 <b>طلا :</b> <code>{game_data['prices']['gold']:,}</code> دلار / 1 {units['gold']}

<b>فلزات:</b>\n"""
    prices_text += f"🔧 فولاد: <code>{game_data['prices']['steel']:,}</code> دلار / 1 {units['steel']}\n"
    prices_text += f"🔩 آهن: <code>{game_data['prices']['iron']:,}</code> دلار / 1 {units['iron']}\n"
    prices_text += f"🔌 مس: <code>{game_data['prices']['copper']:,}</code> دلار / 1 {units['copper']}\n"
    prices_text += f"🔧 آلومینیوم: <code>{game_data['prices']['aluminum']:,}</code> دلار / 1 {units['aluminum']}\n"
    prices_text += f"🔧 تیتانیوم: <code>{game_data['prices']['titanium']:,}</code> دلار / 1 {units['titanium']}\n"

    prices_text += "\n💎 <b>سنگ‌های قیمتی:</b>\n"
    prices_text += f"💎 الماس: <code>{game_data['prices']['diamond']:,}</code> دلار / 1 {units['diamond']}\n"
    prices_text += f"☢️ اورانیوم: <code>{game_data['prices']['uranium']:,}</code> دلار / 1 {units['uranium']}\n"
    prices_text += f"🪨 سنگ اورانیوم: <code>{game_data['prices']['uranium_ore']:,}</code> دلار / 1 {units['uranium_ore']}\n"

    prices_text += "\n🌾 <b>کشاورزی:</b>\n"
    prices_text += f"🌾 گندم: <code>{game_data['prices']['wheat']:,}</code> دلار / 1 {units['wheat']}\n"
    prices_text += f"🍚 برنج: <code>{game_data['prices']['rice']:,}</code> دلار / 1 {units['rice']}\n"
    prices_text += f"🍎 میوه: <code>{game_data['prices']['fruits']:,}</code> دلار / 1 {units['fruits']}\n"

    prices_text += "\n⛽ <b>انرژی:</b>\n"
    prices_text += f"🛢️ نفت: <code>{game_data['prices']['oil']:,}</code> دلار / 1 {units['oil']}\n"
    prices_text += f"🔥 گاز: <code>{game_data['prices']['gas']:,}</code> دلار / 1 {units['gas']}\n"
    prices_text += f"⚡ برق: <code>{game_data['prices']['electricity']:,}</code> دلار / 1 {units['electricity']}\n"

    prices_text += "\n🚗 <b>خودرو:</b>\n"
    prices_text += f"🚗 پراید: <code>{game_data['prices']['pride_cars']:,}</code> دلار / 1 {units['pride_cars']}\n"
    prices_text += f"🚙 بنز: <code>{game_data['prices']['benz_cars']:,}</code> دلار / 1 {units['benz_cars']}\n"

    prices_text += "\n📱 <b>الکترونیک:</b>\n"
    prices_text += f"📱 لوازم الکترونیکی: <code>{game_data['prices']['electronics']:,}</code> دلار / 1 {units['electronics']}\n"

    prices_text += "\n⚛️ <b>هسته‌ای و فضا:</b>\n"
    prices_text += f"🛢️ کیک زرد: <code>{game_data['prices']['yellowcake']:,}</code> دلار / 1 {units['yellowcake']}\n"
    prices_text += f"🌀 سانتریفیوژ: <code>{game_data['prices']['centrifuge']:,}</code> دلار / 1 {units['centrifuge']}\n"
    prices_text += f"🛰️ قطعات فضایی: <code>{game_data['prices']['space_parts']:,}</code> دلار / 1 {units['space_parts']}\n"
    
    prices_text += "\n<b>💣 قیمت جنگ‌افزارها (ثابت):</b>\n"
    military_items = [
        ("soldiers", "سربازان", "🪖"),
        ("special_forces", "نیروهای ویژه", "🎖️"),
        ("tanks", "تانک", "🛡️"),
        ("armored_vehicles", "نفربر", "🚙"),
        ("transport_planes", "هواپیمای ترابری", "🛩️"),
        ("helicopters", "بالگرد", "🚁"),
        ("fighter_jets", "جنگنده", "✈️"),
        ("bombers", "بمب‌افکن", "💣"),
        ("artillery", "توپخانه", "🧨"),
        ("drones", "پهپاد", "🛸"),
        ("air_defense", "پدافند هوایی", "🛡️"),
        ("coastal_artillery", "توپخانه ساحلی", "🏝️"),
        ("speedboats", "قایق تندرو", "🚤"),
        ("naval_ship", "ناو جنگی", "🚢"),
        ("submarines", "زیردریایی", "🛳️"),
        ("aircraft_carriers", "ناو هواپیمابر", "🛳️"),
        ("war_robots", "ربات جنگی", "🤖"),
        ("defense_missiles", "موشک دفاعی", "🛰️"),
        ("ballistic_missiles", "موشک بالستیک", "🚀")
    ]
    military_prices = {
        'soldiers': 10000,
        'special_forces': 50000,
        'tanks': 2000000,
        'armored_vehicles': 1200000,
        'transport_planes': 8000000,
        'helicopters': 6000000,
        'fighter_jets': 25000000,
        'bombers': 40000000,
        'artillery': 1500000,
        'drones': 500000,
        'air_defense': 7000000,
        'coastal_artillery': 2000000,
        'speedboats': 900000,
        'naval_ship': 35000000,
        'submarines': 50000000,
        'aircraft_carriers': 200000000,
        'war_robots': 300000,
        'defense_missiles': 1200000,
        'ballistic_missiles': 5000000
    }
    for key, fa_name, emoji in military_items:
        price = military_prices[key]
        prices_text += f"{emoji} {fa_name}: <code>{price:,}</code> دلار / 1 {units.get(key, 'عدد')}\n"
    keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_trade')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(prices_text, reply_markup=reply_markup, parse_mode='HTML')

async def sell_to_player_start(query, user_id):
    user = utils.users.get(user_id, {})
    resources = user.get('resources', {})
    # فقط منابعی که مقدارشان بیشتر از صفر است
    resource_names = {
        'gold': '🪙 طلا', 'steel': '🔧 فولاد', 'iron': '🔩 آهن', 'copper': '🔌 مس', 'aluminum': '🔧 آلومینیوم', 'titanium': '🔧 تیتانیوم', 'diamond': '💎 الماس', 'uranium': '☢️ اورانیوم',
        'wheat': '🌾 گندم', 'rice': '🍚 برنج', 'fruits': '🍎 میوه', 'oil': '🛢️ نفت', 'gas': '⛽ گاز', 'electronics': '📱 الکترونیک',
        'pride_cars': '🚗 پراید', 'benz_cars': '🚙 بنز', 'electricity': '⚡ برق',
        'uranium_ore': '⛏️ سنگ اورانیوم', 'centrifuge': '🔬 سانتریفیوژ', 'yellowcake': '🍰 کیک زرد', 'space_parts': '🚀 قطعات فضایی',
        # منابع نظامی:
        "soldiers": "👥 سربازان", 'special_forces': "🎖️ نیروهای ویژه", "tanks": "🛡️ تانک", "armored_vehicles": "⚔️ نفربر",
        'transport_planes': "✈️ هواپیمای ترابری", "helicopters": "🚁 بالگرد", "fighter_jets": "🛩️ جنگنده",
        'bombers': "💣 بمب‌افکن", 'artillery': "🎯 توپخانه", 'drones': "🛸 پهپاد", "air_defense": "🛡️ پدافند هوایی",
        'coastal_artillery': "🏖️ توپخانه ساحلی", 'speedboats': "🚤 قایق تندرو", "naval_ship": "⚓ ناو جنگی",
        "submarines": "🚢 زیردریایی", "aircraft_carriers": "🚢 ناو هواپیمابر", "war_robots": "🤖 ربات جنگی",
        "defense_missiles": "🚀 موشک دفاعی", "ballistic_missiles": "🚀 موشک بالستیک"
    }
    keyboard = []
    row = []
    for res, val in resources.items():
        if res == 'cash' or val <= 0:
            continue
        name = resource_names.get(res, res)
        row.append(InlineKeyboardButton(f'{name} ({val})', callback_data=f'sell_choose_{res}'))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_trade')])
    await query.edit_message_text('کدام منبع را می‌خواهید برای فروش آگهی کنید؟', reply_markup=InlineKeyboardMarkup(keyboard))

async def sell_to_player_ask_amount(query, user_id, resource):
    pending_sell_amount[user_id] = resource
    resource_names = {
        'gold': '🪙 طلا', 'steel': '🔧 فولاد', 'iron': '🔩 آهن', 'copper': '🔌 مس', 'aluminum': '🔧 آلومینیوم', 'titanium': '🔧 تیتانیوم', 'diamond': '💎 الماس', 'uranium': '☢️ اورانیوم',
        'wheat': '🌾 گندم', 'rice': '🍚 برنج', 'fruits': '🍎 میوه', 'oil': '🛢️ نفت', 'gas': '⛽ گاز', 'electronics': '📱 الکترونیک',
        'pride_cars': '🚗 پراید', 'benz_cars': '🚙 بنز', 'electricity': '⚡ برق',
        'uranium_ore': '⛏️ سنگ اورانیوم', 'centrifuge': '🔬 سانتریفیوژ', 'yellowcake': '🍰 کیک زرد', 'space_parts': '🚀 قطعات فضایی',
        # منابع نظامی:
        "soldiers": "👥 سربازان", 'special_forces': "🎖️ نیروهای ویژه", "tanks": "🛡️ تانک", "armored_vehicles": "⚔️ نفربر",
        'transport_planes': "✈️ هواپیمای ترابری", "helicopters": "🚁 بالگرد", "fighter_jets": "🛩️ جنگنده",
        'bombers': "💣 بمب‌افکن", 'artillery': "🎯 توپخانه", 'drones': "🛸 پهپاد", "air_defense": "🛡️ پدافند هوایی",
        'coastal_artillery': "🏖️ توپخانه ساحلی", 'speedboats': "🚤 قایق تندرو", "naval_ship": "⚓ ناو جنگی",
        "submarines": "🚢 زیردریایی", "aircraft_carriers": "🚢 ناو هواپیمابر", "war_robots": "🤖 ربات جنگی",
        "defense_missiles": "🚀 موشک دفاعی", "ballistic_missiles": "🚀 موشک بالستیک"
    }
    name = resource_names.get(resource, resource)
    await query.edit_message_text(f'چه مقدار از {name} می‌خواهید بفروشید؟ (عدد را ارسال کنید)')

# مرحله سوم: دریافت قیمت کل


async def handle_sell_amount(update, context):
    user_id = str(update.effective_user.id)
    if user_id not in pending_sell_amount:
        return
    resource = pending_sell_amount[user_id]
    try:
        amount = int((update.message.text if hasattr(update.message, 'text') and update.message.text else '').replace(',', ''))
    except Exception:
        await update.message.reply_text('عدد وارد شده معتبر نیست. لطفاً فقط عدد وارد کنید.')
        pending_sell_amount.pop(user_id, None)
        pending_sell_total_price.pop(user_id, None)
        return
    user = utils.users.get(user_id, {})
    if user.get('resources', {}).get(resource, 0) < amount or amount <= 0:
        await update.message.reply_text('مقدار وارد شده بیشتر از موجودی شماست یا نامعتبر است.')
        pending_sell_amount.pop(user_id, None)
        pending_sell_total_price.pop(user_id, None)
        return
    pending_sell_total_price[user_id] = {'resource': resource, 'amount': amount}
    del pending_sell_amount[user_id]
    
    resource_names = {
        'gold': '🪙 طلا', 'steel': '🔧 فولاد', 'iron': '🔩 آهن', 'copper': '🔌 مس', 'aluminum': '🔧 آلومینیوم', 'titanium': '🔧 تیتانیوم', 'diamond': '💎 الماس', 'uranium': '☢️ اورانیوم',
        'wheat': '🌾 گندم', 'rice': '🍚 برنج', 'fruits': '🍎 میوه', 'oil': '🛢️ نفت', 'gas': '⛽ گاز', 'electronics': '📱 الکترونیک',
        'pride_cars': '🚗 پراید', 'benz_cars': '🚙 بنز', 'electricity': '⚡ برق',
        'uranium_ore': '⛏️ سنگ اورانیوم', 'centrifuge': '🔬 سانتریفیوژ', 'yellowcake': '🍰 کیک زرد', 'space_parts': '🚀 قطعات فضایی',
        # منابع نظامی:
        "soldiers": "👥 سربازان", 'special_forces': "🎖️ نیروهای ویژه", "tanks": "🛡️ تانک", "armored_vehicles": "⚔️ نفربر",
        'transport_planes': "✈️ هواپیمای ترابری", "helicopters": "🚁 بالگرد", "fighter_jets": "🛩️ جنگنده",
        'bombers': "💣 بمب‌افکن", 'artillery': "🎯 توپخانه", 'drones': "🛸 پهپاد", "air_defense": "🛡️ پدافند هوایی",
        'coastal_artillery': "🏖️ توپخانه ساحلی", 'speedboats': "🚤 قایق تندرو", "naval_ship": "⚓ ناو جنگی",
        "submarines": "🚢 زیردریایی", "aircraft_carriers": "🚢 ناو هواپیمابر", "war_robots": "🤖 ربات جنگی",
        "defense_missiles": "🚀 موشک دفاعی", "ballistic_missiles": "🚀 موشک بالستیک"
    }
    name = resource_names.get(resource, resource)
    await update.message.reply_text(f'قیمت کل برای فروش {amount} واحد {name} را به دلار وارد کنید:')

async def handle_sell_total_price(update, context):
    user_id = str(update.effective_user.id)
    if user_id not in pending_sell_total_price:
        return
    try:
        total_price = int((update.message.text if hasattr(update.message, 'text') and update.message.text else '').replace(',', ''))
    except Exception:
        await update.message.reply_text('عدد وارد شده معتبر نیست. لطفاً فقط عدد وارد کنید.')
        pending_sell_amount.pop(user_id, None)
        pending_sell_total_price.pop(user_id, None)
        return
    data = pending_sell_total_price[user_id]
    resource = data['resource']
    amount = data['amount']
    user = utils.users.get(user_id, {})
    # کم کردن موقت منابع
    user['resources'][resource] -= amount
    # ثبت آگهی
    ad = {
        'id': str(uuid4()),
        'user_id': user_id,
        'country': user.get('country', ''),
        'resource': resource,
        'amount': amount,
        'total_price': total_price,
        'timestamp': datetime.now().isoformat(),
        'status': 'active'
    }
    player_sell_ads.append(ad)
    save_users()
    save_player_sell_ads()
    
    resource_names = {
        'gold': '🪙 طلا', 'steel': '🔧 فولاد', 'iron': '🔩 آهن', 'copper': '🔌 مس', 'aluminum': '🔧 آلومینیوم', 'titanium': '🔧 تیتانیوم', 'diamond': '💎 الماس', 'uranium': '☢️ اورانیوم',
        'wheat': '🌾 گندم', 'rice': '🍚 برنج', 'fruits': '🍎 میوه', 'oil': '🛢️ نفت', 'gas': '⛽ گاز', 'electronics': '📱 الکترونیک',
        'pride_cars': '🚗 پراید', 'benz_cars': '🚙 بنز', 'electricity': '⚡ برق',
        'uranium_ore': '⛏️ سنگ اورانیوم', 'centrifuge': '🔬 سانتریفیوژ', 'yellowcake': '🍰 کیک زرد', 'space_parts': '🚀 قطعات فضایی',
        # منابع نظامی:
        "soldiers": "👥 سربازان", 'special_forces': "🎖️ نیروهای ویژه", "tanks": "🛡️ تانک", "armored_vehicles": "⚔️ نفربر",
        'transport_planes': "✈️ هواپیمای ترابری", "helicopters": "🚁 بالگرد", "fighter_jets": "🛩️ جنگنده",
        'bombers': "💣 بمب‌افکن", 'artillery': "🎯 توپخانه", 'drones': "🛸 پهپاد", "air_defense": "🛡️ پدافند هوایی",
        'coastal_artillery': "🏖️ توپخانه ساحلی", 'speedboats': "🚤 قایق تندرو", "naval_ship": "⚓ ناو جنگی",
        "submarines": "🚢 زیردریایی", "aircraft_carriers": "🚢 ناو هواپیمابر", "war_robots": "🤖 ربات جنگی",
        "defense_missiles": "🚀 موشک دفاعی", "ballistic_missiles": "🚀 موشک بالستیک"
    }
    name = resource_names.get(resource, resource)
    await update.message.reply_text(f'آگهی فروش {amount} واحد {name} با قیمت کل {total_price:,} دلار ثبت شد و منابع موقتاً از حساب شما کسر شد. برای مدیریت آگهی‌ها به "مدیریت آگهی‌های فروش" بروید.')
    
    # اطلاع‌رسانی در کانال اخبار
    await announce_trade_offer_in_news(user.get('country', 'کشور ناشناس'), name, amount, total_price)
    
    pending_sell_amount.pop(user_id, None)
    pending_sell_total_price.pop(user_id, None)

# مدیریت آگهی‌های فروش
async def manage_sell_ads_menu(query, user_id):
    ads = [ad for ad in player_sell_ads if ad['user_id'] == user_id and ad['status'] == 'active']
    if not ads:
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_trade')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('شما هیچ آگهی فعالی ندارید.', reply_markup=reply_markup)
        return
    keyboard = []
    resource_names = {
        'gold': '🪙 طلا', 'steel': '🔧 فولاد', 'iron': '🔩 آهن', 'copper': '🔌 مس', 'aluminum': '🔧 آلومینیوم', 'titanium': '🔧 تیتانیوم', 'diamond': '💎 الماس', 'uranium': '☢️ اورانیوم',
        'wheat': '🌾 گندم', 'rice': '🍚 برنج', 'fruits': '🍎 میوه', 'oil': '🛢️ نفت', 'gas': '⛽ گاز', 'electronics': '📱 الکترونیک',
        'pride_cars': '🚗 پراید', 'benz_cars': '🚙 بنز', 'electricity': '⚡ برق',
        'uranium_ore': '⛏️ سنگ اورانیوم', 'centrifuge': '🔬 سانتریفیوژ', 'yellowcake': '🍰 کیک زرد', 'space_parts': '🚀 قطعات فضایی',
        # منابع نظامی:
        "soldiers": "👥 سربازان", 'special_forces': "🎖️ نیروهای ویژه", "tanks": "🛡️ تانک", "armored_vehicles": "⚔️ نفربر",
        'transport_planes': "✈️ هواپیمای ترابری", "helicopters": "🚁 بالگرد", "fighter_jets": "🛩️ جنگنده",
        'bombers': "💣 بمب‌افکن", 'artillery': "🎯 توپخانه", 'drones': "🛸 پهپاد", "air_defense": "🛡️ پدافند هوایی",
        'coastal_artillery': "🏖️ توپخانه ساحلی", 'speedboats': "🚤 قایق تندرو", "naval_ship": "⚓ ناو جنگی",
        "submarines": "🚢 زیردریایی", "aircraft_carriers": "🚢 ناو هواپیمابر", "war_robots": "🤖 ربات جنگی",
        "defense_missiles": "🚀 موشک دفاعی", "ballistic_missiles": "🚀 موشک بالستیک"
    }
    for ad in ads:
        name = resource_names.get(ad['resource'], ad['resource'])
        btn_text = f"{name} | {ad['amount']} عدد | {ad['total_price']:,} دلار"
        keyboard.append([InlineKeyboardButton(f'حذف {btn_text}', callback_data=f'delete_sell_ad_{ad["id"]}')])
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_trade')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('آگهی‌های فعال شما:', reply_markup=reply_markup)

# حذف آگهی و بازگرداندن منابع
async def delete_sell_ad(query, user_id, ad_id):
    ad = next((a for a in player_sell_ads if a['id'] == ad_id and a['user_id'] == user_id and a['status'] == 'active'), None)
    if not ad:
        await query.edit_message_text('آگهی مورد نظر یافت نشد یا قبلاً حذف شده است.')
        return
    # بازگرداندن منابع
    user = utils.users.get(user_id, {})
    user['resources'][ad['resource']] = user['resources'].get(ad['resource'], 0) + ad['amount']
    ad['status'] = 'deleted'
    save_users()
    save_player_sell_ads()
    await query.edit_message_text('آگهی با موفقیت حذف شد و منابع به حساب شما بازگشت.')

async def buy_from_player_start(query, user_id):
    resource_names = {
        'gold': '🪙 طلا', 'steel': '🔧 فولاد', 'iron': '🔩 آهن', 'copper': '🔌 مس', 'aluminum': '🔧 آلومینیوم', 'titanium': '🔧 تیتانیوم', 'diamond': '💎 الماس', 'uranium': '☢️ اورانیوم',
        'wheat': '🌾 گندم', 'rice': '🍚 برنج', 'fruits': '🍎 میوه', 'oil': '🛢️ نفت', 'gas': '⛽ گاز', 'electronics': '📱 الکترونیک',
        'pride_cars': '🚗 پراید', 'benz_cars': '🚙 بنز', 'electricity': '⚡ برق',
        'uranium_ore': '⛏️ سنگ اورانیوم', 'centrifuge': '🔬 سانتریفیوژ', 'yellowcake': '🍰 کیک زرد', 'space_parts': '🚀 قطعات فضایی',
        # منابع نظامی:
        "soldiers": "👥 سربازان", 'special_forces': "🎖️ نیروهای ویژه", "tanks": "🛡️ تانک", "armored_vehicles": "⚔️ نفربر",
        'transport_planes': "✈️ هواپیمای ترابری", "helicopters": "🚁 بالگرد", "fighter_jets": "🛩️ جنگنده",
        'bombers': "💣 بمب‌افکن", 'artillery': "🎯 توپخانه", 'drones': "🛸 پهپاد", "air_defense": "🛡️ پدافند هوایی",
        'coastal_artillery': "🏖️ توپخانه ساحلی", 'speedboats': "🚤 قایق تندرو", "naval_ship": "⚓ ناو جنگی",
        "submarines": "🚢 زیردریایی", "aircraft_carriers": "🚢 ناو هواپیمابر", "war_robots": "🤖 ربات جنگی",
        "defense_missiles": "🚀 موشک دفاعی", "ballistic_missiles": "🚀 موشک بالستیک"
    }
    keys = list(resource_names.keys())
    keyboard = []
    for i in range(0, len(keys), 2):
        row = []
        for j in range(2):
            if i + j < len(keys):
                res = keys[i + j]
                name = resource_names[res]
                row.append(InlineKeyboardButton(name, callback_data=f'buy_choose_{res}'))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='back_to_trade')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('کدام منبع را می‌خواهید از بازیکنان بخرید؟', reply_markup=reply_markup)

# مرحله دوم: نمایش آگهی‌های فعال آن منبع
async def buy_from_player_ads(query, user_id, resource):
    ads = [ad for ad in player_sell_ads if ad['resource'] == resource and ad['status'] == 'active']
    if not ads:
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='buy_from_player')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('هیچ آگهی فعالی برای این منبع وجود ندارد.', reply_markup=reply_markup)
        return
    
    # بررسی تحریم برای فیلتر کردن آگهی‌های غیرمجاز
    from diplomaci import is_country_sanctioned
    from utils import is_country_under_un_economic_sanction
    
    buyer = utils.users.get(user_id, {})
    buyer_country = buyer.get('country', 'کشور ناشناس')
    
    # فیلتر کردن آگهی‌های تحریم شده
    available_ads = []
    for ad in ads:
        seller_country = ad.get('country', '')
        
        # بررسی تحریم: اگر کشور فروشنده، کشور خریدار را تحریم کرده باشد، آگهی نمایش داده نمی‌شود
        if is_country_sanctioned(seller_country, buyer_country):
            continue  # این آگهی را نمایش نده
        
        available_ads.append(ad)
    
    if not available_ads:
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='buy_from_player')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('هیچ آگهی فعالی برای این منبع وجود ندارد یا شما توسط فروشندگان تحریم شده‌اید.', reply_markup=reply_markup)
        return
    
    keyboard = []
    for ad in available_ads:
        price_per_unit = ad['total_price'] // ad['amount'] if ad['amount'] else ad['total_price']
        btn_text = f"{ad['country']}  {ad['amount']}&  {format_price_short(ad['total_price'])}$ (هر واحد: {format_price_short(price_per_unit)}$)"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f'buy_ad_{ad["id"]}')])
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='buy_from_player')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('آگهی‌های فروش فعال برای این منبع:', reply_markup=reply_markup)

# مرحله سوم: سوال اسکورت
async def buy_from_player_confirm(query, user_id, ad_id, context):
    ad = next((a for a in player_sell_ads if a['id'] == ad_id and a['status'] == 'active'), None)
    if not ad:
        await query.edit_message_text('آگهی مورد نظر یافت نشد یا قبلاً فروخته شده است.')
        return
    buyer = utils.users.get(user_id, {})
    # بررسی تحریم: اگر کشور فروشنده، کشور خریدار را تحریم کرده باشد، خرید ممنوع است
    try:
        from diplomaci import is_country_sanctioned
        from utils import is_country_under_un_economic_sanction
        seller_country = ad.get('country', '')
        buyer_country = buyer.get('country', '')
        # تحریم دوطرفه: تحریم کشور فروشنده علیه خریدار یا تحریم اقتصادی UN علیه خریدار
        if is_country_sanctioned(seller_country, buyer_country):
            await query.answer(f"❌ شما توسط کشور {seller_country} تحریم شده‌اید و نمی‌توانید از این کشور خرید کنید.", show_alert=True)
            return
        elif is_country_under_un_economic_sanction(buyer_country):
            await query.answer(f"❌ کشور {buyer_country} تحت تحریم اقتصادی سازمان ملل است و مجاز به خرید نیست.", show_alert=True)
            return
    except Exception as _:
        pass
    if buyer.get('resources', {}).get('cash', 0) < ad['total_price']:
        await query.edit_message_text('موجودی نقد شما برای خرید کافی نیست.')
        return
    
    # محاسبه هزینه اسکورت (10% برای زمینی/دریایی، 20% برای مختلط)
    trade_type = determine_trade_type(ad['country'], buyer.get('country', ''))
    if trade_type == "mixed":
        escort_cost = int(ad['total_price'] * 0.2)  # 20% برای مختلط
    else:
        escort_cost = int(ad['total_price'] * 0.1)  # 10% برای زمینی/دریایی
    
    # ذخیره اطلاعات خرید برای مرحله بعد
    pending_escort_decision = {
        'user_id': user_id,
        'ad_id': ad_id,
        'ad': ad,
        'buyer': buyer,
        'escort_cost': escort_cost
    }
    
    # سوال اسکورت
    keyboard = [
        [InlineKeyboardButton('بله، اسکورت می‌خواهم 🛡️', callback_data=f'escort_yes_{ad_id}')],
        [InlineKeyboardButton('خیر، بدون اسکورت ⚡', callback_data=f'escort_no_{ad_id}')],
        [InlineKeyboardButton('بازگشت ⬅️', callback_data='buy_from_player')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    escort_text = f"🛡️ آیا می‌خواهید برای محافظت از تجارت اسکورت استخدام کنید؟\n\n💰 هزینه اسکورت: {escort_cost:,} دلار (10% از کل مبلغ)\n\n🛡️ با اسکورت: 90% شانس موفقیت در برابر حمله\n⚡ بدون اسکورت: 50% شانس موفقیت در برابر حمله"
    
    await query.edit_message_text(escort_text, reply_markup=reply_markup)

# تابع پردازش تصمیم اسکورت - با اسکورت
async def process_escort_yes(query, user_id, ad_id, context):
    ad = next((a for a in player_sell_ads if a['id'] == ad_id and a['status'] == 'active'), None)
    if not ad:
        await query.edit_message_text('آگهی مورد نظر یافت نشد یا قبلاً فروخته شده است.')
        return
    
    buyer = utils.users.get(user_id, {})
    # بررسی تحریم مجدد در مرحله تایید برای امنیت
    try:
        from diplomaci import is_country_sanctioned
        from utils import is_country_under_un_economic_sanction
        seller_country = ad.get('country', '')
        buyer_country = buyer.get('country', '')
        if is_country_sanctioned(seller_country, buyer_country) or is_country_under_un_economic_sanction(buyer_country):
            await query.answer(f"❌ کشور {buyer_country} مجاز به خرید نیست (تحریم فعال).", show_alert=True)
            return
    except Exception as _:
        pass
    escort_cost = int(ad['total_price'] * 0.1)
    total_cost = ad['total_price'] + escort_cost
    
    if buyer.get('resources', {}).get('cash', 0) < total_cost:
        await query.edit_message_text(f'موجودی نقد شما برای خرید و اسکورت کافی نیست.\nنیاز: {total_cost:,} دلار\nموجودی: {buyer.get("resources", {}).get("cash", 0):,} دلار')
        return
    
    # کم کردن پول (قیمت + اسکورت)
    buyer['resources']['cash'] -= total_cost
    ad['status'] = 'pending'
    save_player_sell_ads()
    
    # هزینه اسکورت به سیستم بین‌المللی می‌رود (فروشنده دریافت نمی‌کند)
    # seller = utils.users.get(ad['user_id'], {})
    # seller['resources']['cash'] = seller['resources'].get('cash', 0) + escort_cost
    
    # تعیین نوع تجارت
    trade_type = determine_trade_type(ad['country'], buyer.get('country', ''))
    
    # ثبت در صف انتظار با اسکورت
    trade = {
        'id': ad['id'],
        'buyer_id': user_id,
        'buyer_country': buyer.get('country', ''),
        'seller_id': ad['user_id'],
        'seller_country': ad['country'],
        'resource': ad['resource'],
        'amount': ad['amount'],
        'total_price': ad['total_price'],
        'start_time': datetime.now().isoformat(),
        'status': 'pending',
        'trade_type': trade_type,
        'current_phase': 1,
        'has_escort': True,
        'escort_cost': escort_cost
    }
    pending_trades.append(trade)
    save_users()
    from utils import save_pending_trades
    save_pending_trades()
    
    # ارسال پیام بر اساس نوع تجارت با اسکورت
    if trade_type == "naval":
        photo_file_id = "https://t.me/TextEmpire_IR/71"  # فایل ID جدید برای تجارت دریایی با اسکورت
        trade_text = "🌊 تجارت دریایی با اسکورت"
        attack_type = "حمله به کشتی تجاری"
    elif trade_type == "land":
        photo_file_id = "https://t.me/TextEmpire_IR/70"  # فایل ID جدید برای تجارت زمینی با اسکورت
        trade_text = "🛤️ تجارت زمینی با اسکورت"
        attack_type = "غارت کاروان"
    else:  # mixed
        photo_file_id = "https://t.me/TextEmpire_IR/72"  # فایل ID جدید برای تجارت مختلط با اسکورت
        trade_text = "🔄 تجارت مختلط با اسکورت"
        attack_type = "حمله به کشتی/غارت کاروان"
    
    # تایمر بر اساس نوع تجارت
    if trade_type == "mixed":
        phase1_duration, phase2_duration = calculate_mixed_trade_times()
        total_duration = phase1_duration + phase2_duration
        trade['phase1_duration'] = phase1_duration
        trade['phase2_duration'] = phase2_duration
        trade['total_duration'] = total_duration
        # ثبت زمان تغییر فاز و فلگ اعلان برای بازیابی دقیق
        phase_change_time = datetime.now() + timedelta(seconds=phase1_duration)
        trade['phase_change_time'] = phase_change_time.isoformat()
        trade['phase_change_announced'] = False
        wait_seconds = total_duration
    else:
        wait_seconds = random.randint(600, 1200)  # 10-20 دقیقه
    
    trade['estimated_arrival'] = (datetime.now() + timedelta(seconds=wait_seconds)).isoformat()
    
    # محاسبه زمان رسیدن احتمالی
    arrival_time = datetime.now() + timedelta(seconds=wait_seconds)
    arrival_str = arrival_time.strftime('%H:%M')
    
    # ارسال پیام به کانال اخبار
    news_text = f"🛡️ {trade_text} میان کشور {ad['country']} و {buyer.get('country','')} درحال انجام است.\nارزش محموله: {ad['total_price']:,} دلار\n💰 هزینه اسکورت: {escort_cost:,} دلار\n⏰ زمان رسیدن احتمالی: {arrival_str}\n🎯 قابل {attack_type} (90% شانس دفاع)"
    await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=photo_file_id, caption=news_text, parse_mode='HTML')
    
    # ارسال پیام به خریدار
    await context.bot.send_photo(
        chat_id=int(user_id),
        photo=photo_file_id,
        caption=f"تجارت شما با کشور {ad['country']} آغاز شد.\n{trade_text}\nارزش محموله: {ad['total_price']:,} دلار\n💰 هزینه اسکورت: {escort_cost:,} دلار\n⏰ زمان رسیدن احتمالی: {arrival_str}",
        parse_mode='HTML'
    )
    
    # ارسال پیام به فروشنده
    await context.bot.send_photo(
        chat_id=int(ad['user_id']),
        photo=photo_file_id,
        caption=f"یک بازیکن ({buyer.get('country','')}) محموله {ad['amount']} واحد {ad['resource']} شما را به قیمت {ad['total_price']:,} دلار خریداری کرد.\n{trade_text}\n⏰ زمان رسیدن احتمالی: {arrival_str}",
        parse_mode='HTML'
    )
    
    await query.edit_message_text(f'خرید شما با اسکورت ثبت شد و در صف انجام قرار گرفت.\n{trade_text}\nنتیجه تجارت پس از مدتی اعلام خواهد شد.')
    
    # شروع تایمر تجارت
    if trade_type == "mixed":
        asyncio.create_task(handle_mixed_trade_phases(trade, context.bot))
    else:
        asyncio.create_task(finalize_trade_after_delay(trade, wait_seconds, context.bot))

# تابع پردازش تصمیم اسکورت - بدون اسکورت
async def process_escort_no(query, user_id, ad_id, context):
    ad = next((a for a in player_sell_ads if a['id'] == ad_id and a['status'] == 'active'), None)
    if not ad:
        await query.edit_message_text('آگهی مورد نظر یافت نشد یا قبلاً فروخته شده است.')
        return
    
    buyer = utils.users.get(user_id, {})
    # بررسی تحریم مجدد در مرحله تایید برای امنیت
    try:
        from diplomaci import is_country_sanctioned
        from utils import is_country_under_un_economic_sanction
        seller_country = ad.get('country', '')
        buyer_country = buyer.get('country', '')
        if is_country_sanctioned(seller_country, buyer_country) or is_country_under_un_economic_sanction(buyer_country):
            await query.answer(f"❌ کشور {buyer_country} مجاز به خرید نیست (تحریم فعال).", show_alert=True)
            return
    except Exception as _:
        pass
    if buyer.get('resources', {}).get('cash', 0) < ad['total_price']:
        await query.edit_message_text('موجودی نقد شما برای خرید کافی نیست.')
        return
    
    # کم کردن پول (فقط قیمت)
    buyer['resources']['cash'] -= ad['total_price']
    ad['status'] = 'pending'
    save_player_sell_ads()
    
    # تعیین نوع تجارت
    trade_type = determine_trade_type(ad['country'], buyer.get('country', ''))
    
    # ثبت در صف انتظار بدون اسکورت
    trade = {
        'id': ad['id'],
        'buyer_id': user_id,
        'buyer_country': buyer.get('country', ''),
        'seller_id': ad['user_id'],
        'seller_country': ad['country'],
        'resource': ad['resource'],
        'amount': ad['amount'],
        'total_price': ad['total_price'],
        'start_time': datetime.now().isoformat(),
        'status': 'pending',
        'trade_type': trade_type,
        'current_phase': 1,
        'has_escort': False
    }
    pending_trades.append(trade)
    save_users()
    from utils import save_pending_trades
    save_pending_trades()
    
    # ارسال پیام بر اساس نوع تجارت بدون اسکورت
    if trade_type == "naval":
        photo_file_id = "https://t.me/TextEmpire_IR/37"
        trade_text = "🌊 تجارت دریایی"
        attack_type = "حمله به کشتی تجاری"
    elif trade_type == "land":
        photo_file_id = "https://t.me/TextEmpire_IR/68"
        trade_text = "🛤️ تجارت زمینی"
        attack_type = "غارت کاروان"
    else:  # mixed
        photo_file_id = "https://t.me/TextEmpire_IR/38"
        trade_text = "🔄 تجارت مختلط"
        attack_type = "حمله به کشتی/غارت کاروان"
    
    # تایمر بر اساس نوع تجارت
    if trade_type == "mixed":
        phase1_duration, phase2_duration = calculate_mixed_trade_times()
        total_duration = phase1_duration + phase2_duration
        trade['phase1_duration'] = phase1_duration
        trade['phase2_duration'] = phase2_duration
        trade['total_duration'] = total_duration
        # ثبت زمان تغییر فاز و فلگ اعلان برای بازیابی دقیق
        phase_change_time = datetime.now() + timedelta(seconds=phase1_duration)
        trade['phase_change_time'] = phase_change_time.isoformat()
        trade['phase_change_announced'] = False
        wait_seconds = total_duration
    else:
        wait_seconds = random.randint(600, 1200)  # 10-20 دقیقه
    
    trade['estimated_arrival'] = (datetime.now() + timedelta(seconds=wait_seconds)).isoformat()
    
    # محاسبه زمان رسیدن احتمالی
    arrival_time = datetime.now() + timedelta(seconds=wait_seconds)
    arrival_str = arrival_time.strftime('%H:%M')
    
    # ارسال پیام به کانال اخبار
    news_text = f"📦 {trade_text} میان کشور {ad['country']} و {buyer.get('country','')} درحال انجام است.\nارزش محموله: {ad['total_price']:,} دلار\n⏰ زمان رسیدن احتمالی: {arrival_str}\n🎯 قابل {attack_type} (50% شانس دفاع)"
    await context.bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=photo_file_id, caption=news_text, parse_mode='HTML')
    
    # ارسال پیام به خریدار
    await context.bot.send_photo(
        chat_id=int(user_id),
        photo=photo_file_id,
        caption=f"تجارت شما با کشور {ad['country']} آغاز شد.\n{trade_text}\nارزش محموله: {ad['total_price']:,} دلار\n⏰ زمان رسیدن احتمالی: {arrival_str}",
        parse_mode='HTML'
    )
    
    # ارسال پیام به فروشنده
    await context.bot.send_photo(
        chat_id=int(ad['user_id']),
        photo=photo_file_id,
        caption=f"یک بازیکن ({buyer.get('country','')}) محموله {ad['amount']} واحد {ad['resource']} شما را به قیمت {ad['total_price']:,} دلار خریداری کرد.\n{trade_text}\n⏰ زمان رسیدن احتمالی: {arrival_str}",
        parse_mode='HTML'
    )
    
    await query.edit_message_text(f'خرید شما بدون اسکورت ثبت شد و در صف انجام قرار گرفت.\n{trade_text}\nنتیجه تجارت پس از مدتی اعلام خواهد شد.')
    
    # شروع تایمر تجارت
    if trade_type == "mixed":
        asyncio.create_task(handle_mixed_trade_phases(trade, context.bot))
    else:
        asyncio.create_task(finalize_trade_after_delay(trade, wait_seconds, context.bot))

async def finalize_trade_after_delay(trade, wait_seconds, bot):
    await asyncio.sleep(wait_seconds)
    # پیدا کردن آگهی و کاربران
    ad = next((a for a in player_sell_ads if a['id'] == trade['id']), None)
    buyer = utils.users.get(trade['buyer_id'], {})
    seller = utils.users.get(trade['seller_id'], {})
    if not ad or not buyer or not seller:
        return
    # انتقال منابع و پول
    buyer['resources'][trade['resource']] = buyer['resources'].get(trade['resource'], 0) + trade['amount']
    seller['resources']['cash'] = seller['resources'].get('cash', 0) + trade['total_price']
    ad['status'] = 'completed'
    trade['status'] = 'completed'
    save_player_sell_ads()
    save_users()
    from utils import save_pending_trades
    save_pending_trades()
    # پیام موفقیت به کانال اخبار
    # ... انتقال منابع و پول و تغییر وضعیت‌ها انجام شد

    resource_names = {
        'gold': 'طلا', 'steel': 'فولاد', 'iron': 'آهن', 'copper': 'مس', 'aluminum': 'آلومینیوم', 'titanium': 'تیتانیوم', 'diamond': 'الماس', 'uranium': 'اورانیوم',
        'wheat': 'گندم', 'rice': 'برنج', 'fruits': 'میوه', 'oil': 'نفت', 'gas': 'گاز', 'electronics': 'الکترونیک',
        'pride_cars': 'پراید', 'benz_cars': 'بنز', 'electricity': 'برق',
        'uranium_ore': 'سنگ اورانیوم', 'centrifuge': 'سانتریفیوژ', 'yellowcake': 'کیک زرد', 'space_parts': 'قطعات فضایی'
    }
    res_name = resource_names.get(trade['resource'], trade['resource'])

    # file_id مخصوص پیام موفقیت
    success_photo_file_id = "https://t.me/TextEmpire_IR/37"  # این را با file_id واقعی عکس موفقیت جایگزین کن

    success_text = (
        f"✅ تجارت میان کشور {trade['seller_country']} و {trade['buyer_country']} با موفقیت انجام شد.\n"
        f"{trade['amount']} واحد {res_name} منتقل شد.\n"
        f"ارزش محموله: {trade['total_price']:,} دلار"
    )

    # ارسال به کانال اخبار
    await bot.send_photo(chat_id=NEWS_CHANNEL_ID, photo=success_photo_file_id, caption=success_text, parse_mode='HTML')

    # ارسال به خریدار
    await bot.send_photo(chat_id=int(trade['buyer_id']), photo=success_photo_file_id, caption="تجارت شما با موفقیت انجام شد!\n" + success_text, parse_mode='HTML')

    # ارسال به فروشنده
    await bot.send_photo(chat_id=int(trade['seller_id']), photo=success_photo_file_id, caption="تجارت شما با موفقیت انجام شد!\n" + success_text, parse_mode='HTML')
    
    # افزایش روابط دوطرفه پس از تجارت موفق
    buyer_id = trade['buyer_id']
    seller_id = trade['seller_id']
    
    # اطمینان از وجود روابط
    if buyer_id not in country_relations:
        country_relations[buyer_id] = {}
    if seller_id not in country_relations:
        country_relations[seller_id] = {}
    
    # افزایش ۲ واحدی روابط دوطرفه
    current_buyer_relation = country_relations[buyer_id].get(seller_id, 0)
    current_seller_relation = country_relations[seller_id].get(buyer_id, 0)
    
    country_relations[buyer_id][seller_id] = min(100, current_buyer_relation + 2)
    country_relations[seller_id][buyer_id] = min(100, current_seller_relation + 2)
    save_country_relations()  # ذخیره روابط
    
    # پیام افزایش روابط به هر دو طرف
    try:
        await bot.send_message(
            chat_id=int(buyer_id),
            text=f"🤝 روابط شما با {trade['seller_country']} به دلیل تجارت موفق ۲ واحد بهبود یافت!"
        )
    except Exception:
        pass
    
    try:
        await bot.send_message(
            chat_id=int(seller_id),
            text=f"🤝 روابط شما با {trade['buyer_country']} به دلیل تجارت موفق ۲ واحد بهبود یافت!"
        )
    except Exception:
        pass

# تابع بازیابی تایمرهای تجارت در زمان startup
async def announce_trade_offer_in_news(country, resource_name, amount, total_price):
    """اطلاع‌رسانی آگهی فروش در کانال اخبار"""
    try:
        # متن کپشن
        text = f"🛒 <b>آگهی تجاری جدید</b>\n\n"
        text += f"🌍 کشور {country} منبع {resource_name} را برای فروش گذاشته است.\n\n"
        text += f"📦 <b>جزئیات:</b>\n"
        text += f"• منبع: {resource_name}\n"
        text += f"• مقدار: {amount:,} واحد\n"
        text += f"• قیمت کل: ${total_price:,}\n\n"
        text += f"💰 جهت مشاهده قیمت و تعداد به بخش تجارت مراجعه فرمایید."
        
        # ایجاد دکمه برای هدایت به پنل تجارت
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [[InlineKeyboardButton('🛒 رفتن به پنل تجارت', url='https://t.me/TextEmpireBot?start=trade')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # ارسال عکس با کپشن به کانال اخبار
        import utils
        from bot import bot
        await bot.send_photo(
            chat_id=utils.NEWS_CHANNEL_ID, 
            photo='https://t.me/TextEmpire_IR/182',
            caption=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        print(f"[TRADE] Trade announcement sent for {country}: {resource_name}")
    except Exception as e:
        print(f"[ERROR] خطا در اطلاع‌رسانی آگهی تجاری: {e}")

async def restore_trade_timers(bot):
    """بازیابی تایمرهای تجارت‌های در حال انجام در زمان startup"""
    from utils import pending_trades
    from datetime import datetime
    
    current_time = datetime.now()
    
    for trade in pending_trades:
        if trade.get('status') != 'pending':
            continue
        if 'estimated_arrival' not in trade:
            continue
        try:
            arrival_time = datetime.fromisoformat(trade['estimated_arrival'])
            remaining_seconds = (arrival_time - current_time).total_seconds()

            # اگر تجارت مختلط است، وضعیت فازها را نیز بازیابی کن
            if trade.get('trade_type') == 'mixed':
                # اگر زمان عبور از فاز ۱ گذشته و اعلانش ارسال نشده، اعلان را ارسال کن
                phase_change_time_iso = trade.get('phase_change_time')
                if phase_change_time_iso:
                    phase_change_time = datetime.fromisoformat(phase_change_time_iso)
                    if current_time >= phase_change_time and not trade.get('phase_change_announced'):
                        # ارسال اعلان تغییر فاز یک‌بار
                        from_country = trade['seller_country']
                        to_country = trade['buyer_country']
                        from_sea = from_country in SEA_BORDER_COUNTRIES
                        phase1_type = "🌊 تجارت دریایی" if from_sea else "🛤️ تجارت زمینی"
                        phase1_attack = "حمله به کشتی تجاری" if from_sea else "غارت کاروان"
                        # انتخاب رندوم فایل برای تغییر نوع تجارت
                        change_photos = [
                            "https://t.me/TextEmpire_IR/67",   # عکس
                            "https://t.me/TextEmpire_IR/177"   # گیف
                        ]
                        change_photo = random.choice(change_photos)
                        change_text = f"🔄 تغییر نوع تجارت!\n\nتجارت میان {from_country} و {to_country}\nمرحله 1: {phase1_type} (10 دقیقه)\nمرحله 2: {'🌊 تجارت دریایی' if not from_sea else '🛤️ تجارت زمینی'} (10 دقیقه)\n\nحالا قابل {phase1_attack} است."
                        await send_media_safe(bot, NEWS_CHANNEL_ID, change_photo, change_text, 'HTML')
                        await send_media_safe(bot, int(trade['buyer_id']), change_photo, change_text, 'HTML')
                        await send_media_safe(bot, int(trade['seller_id']), change_photo, change_text, 'HTML')
                        trade['phase_change_announced'] = True
                        from utils import save_pending_trades
                        save_pending_trades()

            if remaining_seconds > 0:
                asyncio.create_task(finalize_trade_after_delay(trade, remaining_seconds, bot))
                print(f"[DEBUG] Restored timer for trade {trade.get('id')} with {remaining_seconds:.1f} seconds remaining")
            else:
                asyncio.create_task(finalize_trade_after_delay(trade, 1, bot))
                print(f"[DEBUG] Trade {trade.get('id')} was overdue, completing now")
        except Exception as e:
            print(f"[ERROR] Failed to restore timer for trade {trade.get('id')}: {e}")

# ==================== بازار سهام خارجی ====================

def _strip_flags_and_normalize(name: str) -> str:
    """حذف ایموجی پرچم، نیم‌فاصله و یکسان‌سازی نام کشور برای تطبیق با کلیدهای company_templates"""
    if not name:
        return ''
    # حذف کاراکترهای پرچم (REGIONAL INDICATOR SYMBOLS)
    name = re.sub(r'[\U0001F1E6-\U0001F1FF]', '', name)
    # حذف سایر ایموجی‌های معمول در نام‌ها
    name = re.sub(r'[\u200d\ufe0f\u200c]', ' ', name)  # ZWJ/ZWNJ → space
    # فشرده‌سازی فاصله‌ها
    name = re.sub(r'\s+', ' ', name).strip()
    # نگاشت نام‌های معادل به کلیدهای company_templates
    synonyms = {
        'ایالات متحده آمریکا': 'آمریکا',
        'بریتانیا': 'بریتانیا',
        'کره جنوبی': 'کره جنوبی',
        'کره  جنوبی': 'کره جنوبی',
        'کره‌ جنوبی': 'کره جنوبی',
        'امارات متحده عربی': 'امارات متحده عربی',
        'عربستان سعودی': 'عربستان سعودی',
        'هلند': 'هلند',
        'چین': 'چین',
        'روسیه': 'روسیه',
        'آلمان': 'آلمان',
        'فرانسه': 'فرانسه',
        'ژاپن': 'ژاپن',
        'هند': 'هند',
        'ایتالیا': 'ایتالیا',
        'کانادا': 'کانادا',
        'ایران': 'ایران',
        'برزیل': 'برزیل',
        'ترکیه': 'ترکیه',
        'اسرائیل': 'اسرائیل',
        'اسپانیا': 'اسپانیا',
        'سوئیس': 'سوئیس',
        'مکزیک': 'مکزیک',
        'مصر': 'مصر',
        'پاکستان': 'پاکستان',
        'استرالیا': 'استرالیا',
        'اندونزی': 'اندونزی',
        'اوکراین': 'اوکراین',
        'لهستان': 'لهستان',
        'نیجریه': 'نیجریه',
        'تایلند': 'تایلند',
        'قطر': 'قطر',
        'آفریقای جنوبی': 'آفریقای جنوبی',
        'ویتنام': 'ویتنام',
        'مالزی': 'مالزی',
        'آرژانتین': 'آرژانتین',
        'سوئد': 'سوئد',
        'نروژ': 'نروژ',
        'عراق': 'عراق',
        'قزاقستان': 'قزاقستان',
        'الجزایر': 'الجزایر',
        'یونان': 'یونان',
        'رومانی': 'رومانی',
        'فیلیپین': 'فیلیپین',
        'بلژیک': 'بلژیک',
        'دانمارک': 'دانمارک',
        'اتریش': 'اتریش',
        'مجارستان': 'مجارستان',
        'جمهوری چک': 'جمهوری چک',
        'فنلاند': 'فنلاند',
        'پرتغال': 'پرتغال',
        'صربستان': 'صربستان',
    }
    # اگر دقیقا در نگاشت بود
    if name in synonyms:
        return synonyms[name]
    # تلاش: اگر نام شامل این موارد باشد، معادل‌سازی شود
    if 'ایالات متحده' in name:
        return 'آمریکا'
    if 'کره' in name and 'جنوبی' in name:
        return 'کره جنوبی'
    return name

def _get_symbol_country(symbol: str) -> str:
    """پیدا کردن کشور صاحب نماد در قالب نام نرمال‌شده"""
    for country, companies in company_templates.items():
        for c in companies:
            if c['symbol'] == symbol:
                return country
    return ''

def _is_country_in_active_war(country_base_name: str) -> bool:
    try:
        for wid, w in getattr(utils, 'war_declarations', {}).items():
            status = w.get('status', 'active')
            if status == 'ended':
                continue
            attacker = _strip_flags_and_normalize(w.get('attacker', ''))
            defender = _strip_flags_and_normalize(w.get('defender', ''))
            if country_base_name and (country_base_name in (attacker, defender)):
                return True
    except Exception:
        pass
    return False

def update_stock_prices_per_turn():
    """به‌روزرسانی قیمت سهام برای هر دور بر اساس وضعیت کشور و نویز تصادفی"""
    if 'prices' not in STOCK_MARKET_STATE:
        STOCK_MARKET_STATE['prices'] = {}
    if 'growth' not in STOCK_MARKET_STATE:
        STOCK_MARKET_STATE['growth'] = {}

    # فقط شرکت‌های کشورهای فعال را در نظر بگیر
    active_symbols = []
    import utils
    active_country_names = set()
    for uid, u in utils.users.items():
        if u.get('activated') and u.get('country'):
            active_country_names.add(_strip_flags_and_normalize(u['country']))

    for country, companies in company_templates.items():
        if active_country_names and country not in active_country_names:
            continue
        for c in companies:
            active_symbols.append(c['symbol'])

    for symbol in active_symbols:
        # قیمت فعلی و پایه
        country = _get_symbol_country(symbol)
        base_template_price = None
        base_template_growth = 0.0
        for c in company_templates.get(country, []):
            if c['symbol'] == symbol:
                base_template_price = c['price']
                base_template_growth = float(c.get('growth', 0.0))
                break
        if base_template_price is None:
            continue

        current_price = float(STOCK_MARKET_STATE['prices'].get(symbol, base_template_price))

        # درایفت بر اساس رشد پایه شرکت
        drift = 0.0
        if base_template_growth > 0:
            drift = 0.003  # +0.3%
        elif base_template_growth < 0:
            drift = -0.003  # -0.3%

        # اثر وضعیت کشور
        country_base = country
        # تحریم اقتصادی UN
        from utils import is_country_under_un_economic_sanction, un_peace_prize_winners
        sanction_penalty = -0.0
        if is_country_under_un_economic_sanction(country_base):
            sanction_penalty += -0.02  # -2%
        # جنگ فعال
        war_penalty = -0.02 if _is_country_in_active_war(country_base) else 0.0
        # جایزه صلح (اثر مثبت ملایم)
        peace_bonus = 0.0
        try:
            if isinstance(un_peace_prize_winners, list):
                if any(_strip_flags_and_normalize(w.get('country', '')) == country_base for w in un_peace_prize_winners):
                    peace_bonus = 0.01  # +1%
        except Exception:
            pass

        # نویز عادی بازار
        noise = random.uniform(-0.01, 0.01)  # ±1%

        # مولفه اقتصاد کل کشور: دامنه برابر (اقتصاد به میلیارد / 1.5) درصد
        econ_component = 0.0
        try:
            total_country_economy = 0
            for uid, u in utils.users.items():
                if u.get('activated') and _strip_flags_and_normalize(u.get('country', '')) == country:
                    total_country_economy += utils.calculate_total_economy(uid)
            economy_in_billions = total_country_economy / 1_000_000_000
            econ_amplitude_percent = economy_in_billions / 1.5  # 1.5b → 1% ، 15b → 10%
            econ_amplitude = min(max(econ_amplitude_percent / 100.0, 0.0), 0.10)  # حداکثر ±10%
            if econ_amplitude > 0:
                econ_component = random.uniform(-econ_amplitude, econ_amplitude)
        except Exception:
            econ_component = 0.0

        total_change = drift + sanction_penalty + war_penalty + peace_bonus + noise + econ_component
        # محدود کردن تغییر برای ثبات (برای پوشش مولفه اقتصاد تا ±10% + سایر موارد)
        total_change = max(min(total_change, 0.12), -0.12)  # ±12% سقف

        new_price = max(0.1, round(current_price * (1 + total_change), 2))
        STOCK_MARKET_STATE['growth'][symbol] = round(total_change * 100, 1)
        STOCK_MARKET_STATE['prices'][symbol] = new_price

    save_stock_market()


# تابع تولید شرکت‌های سهام بر اساس کشورهای فعال در بازی
def generate_stock_market_data():
    """تولید شرکت‌های سهام بر اساس کشورهای فعال در بازی"""
    from utils import countries  # استفاده از منبع اصلی کشورها
    
    stock_data = {}

    # پرچم‌های کشورها
    country_flags = {
        # 🌍 ابرقدرت‌ها
        'آمریکا': '🇺🇸', 'چین': '🇨🇳', 'روسیه': '🇷🇺', 'بریتانیا': '🇬🇧',
        
        # 🌐 قدرت‌های منطقه‌ای
        'ژاپن': '🇯🇵', 'آلمان': '🇩🇪', 'فرانسه': '🇫🇷', 'هند': '🇮🇳', 'ایتالیا': '🇮🇹', 
        'کانادا': '🇨🇦', 'ایران': '🇮🇷', 'کره جنوبی': '🇰🇷',
        
        # 🚀 قدرت‌های نوظهور
        'برزیل': '🇧🇷', 'ترکیه': '🇹🇷', 'اسرائیل': '🇮🇱', 'اسپانیا': '🇪🇸', 
        'عربستان سعودی': '🇸🇦', 'سوئیس': '🇨🇭', 'مکزیک': '🇲🇽', 'مصر': '🇪🇬', 
        'پاکستان': '🇵🇰', 'استرالیا': '🇦🇺',
        
        # ⚖️ کشورهای عادی
        'اندونزی': '🇮🇩', 'اوکراین': '🇺🇦', 'لهستان': '🇵🇱', 'نیجریه': '🇳🇬', 
        'تایلند': '🇹🇭', 'امارات متحده عربی': '🇦🇪', 'قطر': '🇶🇦', 'آفریقای جنوبی': '🇿🇦', 
        'ویتنام': '🇻🇳', 'مالزی': '🇲🇾', 'آرژانتین': '🇦🇷', 'سوئد': '🇸🇪', 
        'نروژ': '🇳🇴', 'هلند': '🇳🇱', 'عراق': '🇮🇶', 'قزاقستان': '🇰🇿', 
        'الجزایر': '🇩🇿', 'یونان': '🇬🇷', 'رومانی': '🇷🇴', 'فیلیپین': '🇵🇭', 
        'بلژیک': '🇧🇪', 'دانمارک': '🇩🇰', 'اتریش': '🇦🇹', 'مجارستان': '🇭🇺', 
        'جمهوری چک': '🇨🇿', 'فنلاند': '🇫🇮', 'پرتغال': '🇵🇹', 'صربستان': '🇷🇸'
    }
    
    # تعیین کشورهای فعال (کاربران فعال). اگر نبود، از کل لیست کشورها استفاده می‌کنیم
    active_country_names = set()
    try:
        for uid, u in utils.users.items():
            if u.get('activated') and u.get('country'):
                active_country_names.add(_strip_flags_and_normalize(u['country']))
    except Exception:
        pass

    # تولید شرکت‌ها برای هر کشور فعال
    source_iterable = countries if not active_country_names else [
        {'name': n} for n in active_country_names
    ]
    
    for country in source_iterable:
        raw_name = country['name']
        base_name = _strip_flags_and_normalize(raw_name)
        if base_name in company_templates:
            companies = company_templates[base_name]
            flag = country_flags.get(base_name, '🏳️')
            for company in companies:
                symbol = company['symbol']
                # قیمت و رشد از وضعیت جاری بازار
                current_price = STOCK_MARKET_STATE.get('prices', {}).get(symbol, company['price'])
                last_growth = STOCK_MARKET_STATE.get('growth', {}).get(symbol, company.get('growth', 0.0))
                history = 'صعودی' if last_growth > 1 else 'نزولی' if last_growth < -1 else 'پایدار'
                prediction = 'مثبت' if last_growth > 0 else 'منفی' if last_growth < 0 else 'پایدار'
                # محاسبه تعداد کل سهام در دسترس (کل سهام منهای سهام‌های خریداری شده)
                total_issued_shares = 5000000
                sold_shares = 0
                
                # محاسبه سهام‌های خریداری شده توسط همه کاربران
                for uid, user_data in utils.users.items():
                    user_stocks = user_data.get('stocks', {})
                    sold_shares += user_stocks.get(symbol, 0)
                
                available_shares = total_issued_shares - sold_shares
                
                stock_data[symbol] = {
                    'name': company['name'],
                    'country': flag,
                    'price': current_price,
                    'growth': last_growth,
                    'history': history,
                    'prediction': prediction,
                    'total_shares': available_shares,
                    'description': company['description']
                }
    
    return stock_data

# داده‌های سهام شرکت‌های معروف (تولید شده بر اساس کشورهای فعال)
STOCK_MARKET_DATA = generate_stock_market_data()

async def show_foreign_exchange_market(query):
    """نمایش منوی بازار سهام خارجی"""
    text = "📈 <b>بازار سهام خارجی</b>\n\n"
    text += "🌍 به بازار سهام بین‌المللی خوش آمدید!\n"
    text += "💼 در اینجا می‌توانید سهام شرکت‌های معروف جهان را خرید و فروش کنید.\n\n"
    # معرفی کاراکتر: وارن بافت
    text += "🧓 <b>وارن بافت</b>، مشاور سرمایه‌گذاری شما:\n"
    text += "<blockquote>به دنیای سرمایه‌گذاری خوش آمدی! من وارن بافتم و اینجام تا کمکت کنم جیبت پرپول‌تر بشه — البته زحمت خودت هم لازمه!😉\nقیمت، چیزی‌ست که می‌پردازی؛ ارزش، چیزی‌ست که به‌دست می‌آوری. روی شرکت‌های عالی با بنیاد قوی تمرکز کن.</blockquote>\n\n"
    text += "📊 <b>گزینه‌های موجود:</b>"
    
    keyboard = [
        [InlineKeyboardButton('💼 کیف پول سهام', callback_data='stock_wallet')],
        [InlineKeyboardButton('📈 سهام شرکت‌ها', callback_data='company_stocks')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='trade_menu')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_stock_wallet(query):
    """نمایش کیف پول سهام کاربر"""
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    
    # دریافت سهام‌های کاربر
    stocks = user.get('stocks', {})
    
    text = "💼 <b>کیف پول سهام شما</b>\n\n"
    
    if not stocks:
        text += "📭 شما هنوز هیچ سهامی ندارید.\n"
        text += "💡 برای شروع سرمایه‌گذاری، از منوی سهام شرکت‌ها استفاده کنید."
    else:
        # تولید داده‌های سهام بر اساس کشورهای فعال
        stock_data = generate_stock_market_data()
        
        total_value = 0
        text += "📊 <b>سهام‌های شما:</b>\n\n"
        
        # دریافت سهام‌های فریز شده
        frozen_stocks = user.get('frozen_stocks', {})
        
        for symbol, amount in stocks.items():
            if amount > 0 and symbol in stock_data:
                stock_info = stock_data[symbol]
                value = amount * stock_info['price']
                total_value += value
                
                growth_emoji = "📈" if stock_info['growth'] > 0 else "📉" if stock_info['growth'] < 0 else "➡️"
                
                # بررسی فریز بودن سهام
                frozen_amount = frozen_stocks.get(symbol, 0)
                if frozen_amount > 0:
                    # سهام فریز شده
                    text += f"🧊 {growth_emoji} <b>{symbol}</b> - {stock_info['name']}\n"
                    text += f"   📊 کشور: {stock_info['country']}\n"
                    text += f"   📈 تعداد: {amount:,} سهم (فریز شده: {frozen_amount:,})\n"
                    text += f"   💰 ارزش: ${value:,}\n"
                    text += f"   📊 قیمت: ${stock_info['price']:,} ({stock_info['growth']:+.2f}%)\n\n"
                else:
                    # سهام عادی
                    text += f"{growth_emoji} <b>{symbol}</b> - {stock_info['name']}\n"
                    text += f"   📊 کشور: {stock_info['country']}\n"
                    text += f"   📈 تعداد: {amount:,} سهم\n"
                    text += f"   💰 ارزش: ${value:,}\n"
                    text += f"   📊 قیمت: ${stock_info['price']:,} ({stock_info['growth']:+.2f}%)\n\n"
        
        text += f"💰 <b>ارزش کل کیف پول:</b> ${total_value:,}"
    
    keyboard = [
        [InlineKeyboardButton('🔄 بروزرسانی', callback_data='stock_wallet')],
        [InlineKeyboardButton('🔙 بازگشت', callback_data='foreign_exchange_market')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_company_stocks(query, page: int = 0):
    """نمایش لیست سهام شرکت‌ها (مرتب بر اساس قیمت نزولی) با صفحه‌بندی 20‌تایی و 2 ستونی"""
    try:
        from bot import show_loading_animation
    except Exception:
        pass
    # تولید داده‌های سهام بر اساس کشورهای فعال
    stock_data = generate_stock_market_data()

    # مرتب‌سازی بر اساس قیمت (نزولی)
    items = sorted(stock_data.items(), key=lambda kv: kv[1].get('price', 0), reverse=True)
    # انتخاب بهترین سهم از نظر نرخ رشد فعلی
    buffett_pick = None
    if stock_data:
        try:
            growth_sorted = sorted(stock_data.items(), key=lambda kv: kv[1].get('growth', 0), reverse=True)
            if growth_sorted:
                buffett_pick = growth_sorted[0]
        except Exception:
            buffett_pick = None

    page_size = 20
    total = len(items)
    start = max(0, page) * page_size
    end = start + page_size
    page_items = items[start:end]

    text = "📈 <b>سهام شرکت‌های معروف جهان</b>\n\n"
    text += f"🌍 {total} شرکت از کشورهای فعال در بازی\n"
    # توصیه وارن بافت در صفحه لیست
    if buffett_pick:
        sym, info = buffett_pick
        be = "📈" if info.get('growth', 0) > 0 else ("📉" if info.get('growth', 0) < 0 else "➡️")
        text += "🧓 <b>پیشنهاد وارن بافت:</b>\n"
        text += f"<blockquote>{info.get('country', '')} {sym} - {info.get('name', '')} {be} {info.get('growth', 0):+.1f}%</blockquote>\n"
    
    text += "💡 روی هر شرکت کلیک کنید تا جزئیات و امکان خرید/فروش را ببینید.\n\n"

    keyboard = []
    row = []

    for symbol, data in page_items:
        growth_emoji = "📈" if data['growth'] > 0 else "📉" if data['growth'] < 0 else "➡️"
        button_text = f"{data['country']} {symbol}\n{growth_emoji} ${data['price']}"
        row.append(InlineKeyboardButton(button_text, callback_data=f'stock_details_{symbol}'))
        if len(row) == 2:  # دو ستونی
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    # دکمه‌های صفحه‌بندی
    nav_row = []
    if start > 0:
        nav_row.append(InlineKeyboardButton('⬅️ صفحه قبل', callback_data=f'company_stocks_{max(0, page-1)}'))
    if end < total:
        nav_row.append(InlineKeyboardButton('صفحه بعد ➡️', callback_data=f'company_stocks_{page+1}'))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='foreign_exchange_market')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_stock_details(query, symbol):
    """نمایش جزئیات سهام خاص"""
    # نمایش لودینگ کوتاه
    try:
        from bot import show_loading_animation
    except Exception:
        pass
    # تولید داده‌های سهام بر اساس کشورهای فعال
    stock_data = generate_stock_market_data()
    
    if symbol not in stock_data:
        await query.answer("❌ سهام یافت نشد!", show_alert=True)
        return
    
    stock_info = stock_data[symbol]
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    user_stocks = user.get('stocks', {})
    user_amount = user_stocks.get(symbol, 0)
    
    growth_emoji = "📈" if stock_info['growth'] > 0 else "📉" if stock_info['growth'] < 0 else "➡️"
    prediction_emoji = "✅" if stock_info['prediction'] == 'مثبت' else "❌" if stock_info['prediction'] == 'منفی' else "➡️"
    
    text = f"📊 <b>جزئیات سهام {symbol}</b>\n\n"
    text += f"🏢 <b>نام کامل:</b> {stock_info['name']}\n"
    text += f"🌍 <b>کشور:</b> {stock_info['country']}\n"
    text += f"💰 <b>قیمت فعلی:</b> ${stock_info['price']:,}\n"
    text += f"📈 <b>نرخ رشد:</b> {growth_emoji} {stock_info['growth']:+.1f}%\n"
    text += f"📋 <b>سابقه بازار:</b> {stock_info['history']}\n"
    text += f"🔮 <b>پیش‌بینی:</b> {prediction_emoji} {stock_info['prediction']}\n"
    text += f"📊 <b>تعداد کل سهام:</b> {stock_info['total_shares']:,}\n"
    text += f"💼 <b>سهام شما:</b> {user_amount:,} سهم\n\n"
    text += f"📝 <b>توضیحات:</b>\n{stock_info['description']}\n\n"

    # توصیه وارن بافت بر اساس وضعیت سهم و موجودی کاربر
    def _buffett_advice(info: dict, held_amount: int) -> str:
        growth = info.get('growth', 0)
        history = info.get('history', '')
        prediction = info.get('prediction', '')
        price = info.get('price', 0)

        notes = []
        # کیفیت روند
        if growth >= 2 and history == 'صعودی' and prediction == 'مثبت':
            notes.append('کسب‌وکار با کیفیت و روند مناسب؛ خرید تدریجی در قیمت‌های منصفانه قابل دفاع است.')
        elif growth >= 0 and history in ('پایدار', 'صعودی') and prediction != 'منفی':
            notes.append('صبور باشید و تنها با حاشیه امن کافی اضافه کنید.')
        elif growth < 0 or prediction == 'منفی' or history == 'نزولی':
            notes.append('از خرید هیجانی پرهیز کنید؛ نخست به ثبات بنیادی و قیمت منصفانه برسید.')

        # مدیریت موقعیت موجود
        if held_amount > 0:
            if growth >= 0 and prediction != 'منفی':
                notes.append('اگر افق شما بلندمدت است، نگهداری متمایل به بلندمدت معقول است.')
            else:
                notes.append('بازبینی اطراف کسب‌وکار و عدم گسترش موقعیت تا روشن‌شدن روند منطقی است.')

        # انضباط قیمتی
        if price >= 100:
            notes.append('به جای تمرکز بر قیمت اسمی، روی ارزش‌گذاری و کیفیت جریان نقدی تمرکز کنید.')
        else:
            notes.append('کم‌قیمت بودن به‌تنهایی دلیل خوب بودن نیست؛ به کیفیت مزیت رقابتی نگاه کنید.')

        return ' '.join(notes)

    advice = _buffett_advice(stock_info, user_amount)
    if advice:
        text += "🧓 <b>وارن بافت می‌گوید:</b>\n"
        text += f"<blockquote>{advice}</blockquote>\n\n"
    
    if user_amount > 0:
        user_value = user_amount * stock_info['price']
        text += f"💰 <b>ارزش سهام شما:</b> ${user_value:,}\n\n"
    
    # دکمه‌های خرید و فروش
    keyboard = []
    
    # بررسی تحریم - تعریف متغیرها در ابتدا
    from diplomaci import is_country_sanctioned
    from utils import is_country_under_un_economic_sanction
    
    buyer_country = user.get('country', 'کشور ناشناس')
    
    # پیدا کردن کشور صاحب سهام
    stock_country = None
    for country, companies in company_templates.items():
        for company in companies:
            if company['symbol'] == symbol:
                stock_country = country
                break
        if stock_country:
            break
    
    # یکسان‌سازی نام کشورها برای تطبیق با sanctions
    buyer_country_normalized = _strip_flags_and_normalize(buyer_country)
    stock_country_normalized = _strip_flags_and_normalize(stock_country) if stock_country else None
    
    if user_amount > 0:
        # بررسی تحریم - اگر تحریم شده، دکمه فروش نمایش داده نمی‌شود
        can_sell = True
        if is_country_under_un_economic_sanction(buyer_country_normalized):
            can_sell = False
        elif stock_country_normalized and (is_country_sanctioned(buyer_country_normalized, stock_country_normalized) or 
                                            is_country_sanctioned(stock_country_normalized, buyer_country_normalized)):
            can_sell = False
        
        if can_sell:
            keyboard.append([InlineKeyboardButton('💸 فروش سهام', callback_data=f'sell_stock_{symbol}')])
    
    # بررسی تحریم برای دکمه خرید
    can_buy = True
    if is_country_under_un_economic_sanction(buyer_country_normalized):
        can_buy = False
    elif stock_country_normalized and (is_country_sanctioned(buyer_country_normalized, stock_country_normalized) or 
                                        is_country_sanctioned(stock_country_normalized, buyer_country_normalized)):
        can_buy = False
    
    if can_buy:
        keyboard.append([InlineKeyboardButton('💵 خرید سهام', callback_data=f'buy_stock_{symbol}')])
    
    keyboard.append([InlineKeyboardButton('🔙 بازگشت', callback_data='company_stocks')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_buy_stock_menu(query, symbol):
    """نمایش منوی خرید سهام"""
    # تولید داده‌های سهام بر اساس کشورهای فعال
    stock_data = generate_stock_market_data()
    
    if symbol not in stock_data:
        await query.answer("❌ سهام یافت نشد!", show_alert=True)
        return
    
    stock_info = stock_data[symbol]
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    user_cash = user.get('resources', {}).get('cash', 0)
    
    # بررسی تحریم قبل از نمایش منوی خرید
    from diplomaci import is_country_sanctioned
    from utils import is_country_under_un_economic_sanction
    
    buyer_country = user.get('country', 'کشور ناشناس')
    
    # پیدا کردن کشور صاحب سهام
    stock_country = None
    for country, companies in company_templates.items():
        for company in companies:
            if company['symbol'] == symbol:
                stock_country = country
                break
        if stock_country:
            break
    
    # یکسان‌سازی نام کشورها برای تطبیق با sanctions
    buyer_country_normalized = _strip_flags_and_normalize(buyer_country)
    stock_country_normalized = _strip_flags_and_normalize(stock_country) if stock_country else None
    
    # بررسی تحریم
    if is_country_under_un_economic_sanction(buyer_country_normalized):
        await query.answer("❌ کشور شما تحت تحریم اقتصادی سازمان ملل است و مجاز به خرید سهام نیست.", show_alert=True)
        return
    
    # بررسی تحریم دوطرفه
    if stock_country_normalized and (is_country_sanctioned(buyer_country_normalized, stock_country_normalized) or 
                                     is_country_sanctioned(stock_country_normalized, buyer_country_normalized)):
        await query.answer(f"❌ بین کشور شما ({buyer_country}) و کشور {stock_country} تحریم دوطرفه برقرار است و نمی‌توانید سهام شرکت‌های این کشور را خریداری کنید.", show_alert=True)
        return
    
    text = f"💵 <b>خرید سهام {symbol}</b>\n\n"
    text += f"🏢 {stock_info['name']}\n"
    text += f"💰 قیمت هر سهم: ${stock_info['price']:,}\n"
    text += f"💼 موجودی شما: ${user_cash:,}\n\n"
    
    max_shares = user_cash // stock_info['price']
    
    if max_shares == 0:
        text += "❌ موجودی کافی برای خرید سهام ندارید!"
        keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data=f'stock_details_{symbol}')]]
    else:
        text += f"📊 حداکثر سهام قابل خرید: {max_shares:,} سهم\n\n"
        text += "🔢 تعداد سهام مورد نظر را وارد کنید:"
        
        # ذخیره وضعیت خرید
        if user_id not in utils.users:
            utils.users[user_id] = {}
        if 'pending_stock_purchase' not in utils.users[user_id]:
            utils.users[user_id]['pending_stock_purchase'] = {}
        utils.users[user_id]['pending_stock_purchase'][symbol] = {'step': 'amount'}
        utils.save_users()
        
        keyboard = [
            [InlineKeyboardButton('🔙 بازگشت', callback_data=f'stock_details_{symbol}')]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def show_sell_stock_menu(query, symbol):
    """نمایش منوی فروش سهام"""
    # تولید داده‌های سهام بر اساس کشورهای فعال
    stock_data = generate_stock_market_data()
    
    if symbol not in stock_data:
        await query.answer("❌ سهام یافت نشد!", show_alert=True)
        return
    
    stock_info = stock_data[symbol]
    user_id = str(query.from_user.id)
    user = utils.users.get(user_id, {})
    user_stocks = user.get('stocks', {})
    user_amount = user_stocks.get(symbol, 0)
    
    if user_amount == 0:
        await query.answer("❌ شما این سهام را ندارید!", show_alert=True)
        return
    
    # بررسی تحریم قبل از نمایش منوی فروش
    from diplomaci import is_country_sanctioned
    from utils import is_country_under_un_economic_sanction
    
    buyer_country = user.get('country', 'کشور ناشناس')
    
    # پیدا کردن کشور صاحب سهام
    stock_country = None
    for country, companies in company_templates.items():
        for company in companies:
            if company['symbol'] == symbol:
                stock_country = country
                break
        if stock_country:
            break
    
    # یکسان‌سازی نام کشورها برای تطبیق با sanctions
    buyer_country_normalized = _strip_flags_and_normalize(buyer_country)
    stock_country_normalized = _strip_flags_and_normalize(stock_country) if stock_country else None
    
    # بررسی تحریم
    if is_country_under_un_economic_sanction(buyer_country_normalized):
        await query.answer("❌ کشور شما تحت تحریم اقتصادی سازمان ملل است و مجاز به فروش سهام نیست.", show_alert=True)
        return
    
    # بررسی تحریم دوطرفه
    if stock_country_normalized and (is_country_sanctioned(buyer_country_normalized, stock_country_normalized) or 
                                     is_country_sanctioned(stock_country_normalized, buyer_country_normalized)):
        await query.answer(f"❌ بین کشور شما ({buyer_country}) و کشور {stock_country} تحریم دوطرفه برقرار است و نمی‌توانید سهام شرکت‌های این کشور را بفروشید.", show_alert=True)
        return
    
    sell_value = user_amount * stock_info['price']
    
    text = f"💸 <b>فروش سهام {symbol}</b>\n\n"
    text += f"🏢 {stock_info['name']}\n"
    text += f"💰 قیمت هر سهم: ${stock_info['price']:,}\n"
    text += f"📊 سهام شما: {user_amount:,} سهم\n"
    text += f"💵 ارزش کل: ${sell_value:,}\n\n"
    
    # ذخیره وضعیت فروش
    if user_id not in utils.users:
        utils.users[user_id] = {}
    if 'pending_stock_sale' not in utils.users[user_id]:
        utils.users[user_id]['pending_stock_sale'] = {}
    utils.users[user_id]['pending_stock_sale'][symbol] = {'step': 'amount'}
    utils.save_users()
    
    text += "🔢 تعداد سهام مورد نظر برای فروش را وارد کنید:"
    
    keyboard = [
        [InlineKeyboardButton('🔙 بازگشت', callback_data=f'stock_details_{symbol}')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def handle_stock_purchase(user_id, symbol, amount):
    """پردازش خرید سهام"""
    # تولید داده‌های سهام بر اساس کشورهای فعال
    stock_data = generate_stock_market_data()
    
    if symbol not in stock_data:
        return False, "❌ سهام یافت نشد!"
    
    stock_info = stock_data[symbol]
    user = utils.users.get(user_id, {})
    user_cash = user.get('resources', {}).get('cash', 0)
    
    # بررسی تحریم
    buyer_country = user.get('country', 'کشور ناشناس')
    stock_country = None
    
    # پیدا کردن کشور صاحب سهام
    for country, companies in company_templates.items():
        for company in companies:
            if company['symbol'] == symbol:
                stock_country = country
                break
        if stock_country:
            break
    
    # ممنوعیت سهام در صورت تحریم اقتصادی UN یا تحریم دوجانبه
    if stock_country:
        from diplomaci import is_country_sanctioned
        from utils import is_country_under_un_economic_sanction
        
        # یکسان‌سازی نام کشورها برای تطبیق با sanctions
        buyer_country_normalized = _strip_flags_and_normalize(buyer_country)
        stock_country_normalized = _strip_flags_and_normalize(stock_country)
        
        if (is_country_sanctioned(buyer_country_normalized, stock_country_normalized) or 
            is_country_sanctioned(stock_country_normalized, buyer_country_normalized)):
            return False, f"❌ بین کشور شما ({buyer_country}) و کشور {stock_country} تحریم دوطرفه برقرار است و نمی‌توانید سهام شرکت‌های این کشور را خریداری کنید."
        elif is_country_under_un_economic_sanction(buyer_country_normalized):
            return False, f"❌ کشور {buyer_country} تحت تحریم اقتصادی سازمان ملل است و مجاز به خرید سهام نیست."
    
    # بررسی موجودی سهام در بازار
    available_shares = stock_info.get('total_shares', 0)
    if amount > available_shares:
        return False, f"❌ موجودی سهام در بازار کافی نیست!\n💡 فقط {available_shares:,} سهم در دسترس است."
    
    total_cost = amount * stock_info['price']
    
    if user_cash < total_cost:
        return False, "❌ موجودی کافی ندارید!"
    
    if amount <= 0:
        return False, "❌ تعداد سهام باید مثبت باشد!"
    
    # انجام تراکنش
    user['resources']['cash'] -= total_cost
    
    if 'stocks' not in user:
        user['stocks'] = {}
    user['stocks'][symbol] = user['stocks'].get(symbol, 0) + amount
    
    # پاک کردن وضعیت خرید
    if 'pending_stock_purchase' in user and symbol in user['pending_stock_purchase']:
        del user['pending_stock_purchase'][symbol]
    
    utils.save_users()
    
    return True, f"✅ {amount:,} سهم {symbol} با موفقیت خریداری شد!\n💰 هزینه: ${total_cost:,}"

async def handle_stock_sale(user_id, symbol, amount):
    """پردازش فروش سهام"""
    # تولید داده‌های سهام بر اساس کشورهای فعال
    stock_data = generate_stock_market_data()
    
    if symbol not in stock_data:
        return False, "❌ سهام یافت نشد!"
    
    stock_info = stock_data[symbol]
    user = utils.users.get(user_id, {})
    user_stocks = user.get('stocks', {})
    user_amount = user_stocks.get(symbol, 0)
    
    # بررسی سهام‌های فریز شده
    frozen_stocks = user.get('frozen_stocks', {})
    frozen_amount = frozen_stocks.get(symbol, 0)
    
    # بررسی تحریم
    from utils import is_country_under_un_economic_sanction
    from economy import company_templates
    from diplomaci import is_country_sanctioned
    
    buyer_country = utils.users.get(user_id, {}).get('country', '')
    
    # پیدا کردن کشور صاحب سهام
    stock_country = None
    for country, companies in company_templates.items():
        for company in companies:
            if company['symbol'] == symbol:
                stock_country = country
                break
        if stock_country:
            break
    
    # یکسان‌سازی نام کشورها برای تطبیق با sanctions
    buyer_country_normalized = _strip_flags_and_normalize(buyer_country)
    stock_country_normalized = _strip_flags_and_normalize(stock_country) if stock_country else None
    
    # بررسی تحریم
    if is_country_under_un_economic_sanction(buyer_country_normalized):
        return False, "❌ به دلیل تحریم اقتصادی فعال، خرید و فروش سهام مجاز نیست."
    
    # بررسی تحریم دوطرفه
    if stock_country_normalized and (is_country_sanctioned(buyer_country_normalized, stock_country_normalized) or 
                                     is_country_sanctioned(stock_country_normalized, buyer_country_normalized)):
        return False, f"❌ بین کشور شما ({buyer_country}) و کشور {stock_country} تحریم دوطرفه برقرار است و نمی‌توانید سهام شرکت‌های این کشور را بفروشید."
    
    if user_amount < amount:
        if frozen_amount > 0:
            return False, f"❌ سهام کافی ندارید!\n💡 {frozen_amount:,} سهم {symbol} شما فریز شده است (تحریم فعال)."
        else:
            return False, "❌ سهام کافی ندارید!"
    
    if amount <= 0:
        return False, "❌ تعداد سهام باید مثبت باشد!"
    
    total_value = amount * stock_info['price']
    
    # انجام تراکنش
    user['resources']['cash'] += total_value
    user['stocks'][symbol] -= amount
    
    # اگر سهام تمام شد، کلید را حذف کن
    if user['stocks'][symbol] == 0:
        del user['stocks'][symbol]
    
    # پاک کردن وضعیت فروش
    if 'pending_stock_sale' in user and symbol in user['pending_stock_sale']:
        del user['pending_stock_sale'][symbol]
    
    utils.save_users()
    
    return True, f"✅ {amount:,} سهم {symbol} با موفقیت فروخته شد!\n💰 درآمد: ${total_value:,}"
