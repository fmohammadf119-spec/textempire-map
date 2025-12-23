#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import random
from datetime import datetime, timedelta
import utils

def generate_minister_report(user_id, turn):
    """تولید گزارش وزیر کشور"""
    user = utils.users.get(user_id, {})
    if not user.get('activated'):
        return None
    
    resources = user.get('resources', {})
    economy = user.get('economy', {})
    minister_name = user.get('selected_officials', {}).get('minister', {}).get('name', 'وزیر کشور')
    
    # محاسبه تولیدات
    production_stats = {
        'iron': 0, 'gold': 0, 'copper': 0, 'diamond': 0, 'aluminum': 0, 'titanium': 0,
        'wheat': 0, 'rice': 0, 'fruits': 0, 'electricity': 0, 'oil': 0, 'gas': 0
    }
    
    # محاسبه تولید معادن
    mines = economy.get('mines', [])
    for mine in mines:
        if mine == 'iron_mine':
            production_stats['iron'] += 10
        elif mine == 'gold_mine':
            production_stats['gold'] += 5
        elif mine == 'copper_mine':
            production_stats['copper'] += 10
        elif mine == 'diamond_mine':
            production_stats['diamond'] += 2
        elif mine == 'aluminum_mine':
            production_stats['aluminum'] += 8
        elif mine == 'titanium_mine':
            production_stats['titanium'] += 3
    
    # محاسبه تولید کشاورزی
    farms = economy.get('farms', [])
    for farm in farms:
        if farm == 'wheat_farm':
            production_stats['wheat'] += 10
        elif farm == 'rice_farm':
            production_stats['rice'] += 10
        elif farm == 'fruit_farm':
            production_stats['fruits'] += 10
    
    # محاسبه تولید انرژی
    energy = economy.get('energy', [])
    for plant in energy:
        if plant == 'power_plant':
            production_stats['electricity'] += 10
        elif plant == 'oil_refinery':
            production_stats['oil'] += 500
        elif plant == 'gas_refinery':
            production_stats['gas'] += 500
    
    # تولید گزارش
    report = f"📋 <b>گزارش وزیر کشور</b>\n\n"
    report += f"👨‍💼 <b>وزیر:</b> {minister_name}\n"
    report += f"📅 <b>تاریخ:</b> {utils.game_data.get('game_date', 'نامشخص')}\n"
    report += f"🔄 <b>دور:</b> {turn}\n\n"
    
    # بخش تولیدات
    report += "🏭 <b>تولیدات این دور:</b>\n"
    report += "<blockquote>\n"
    total_production = 0
    for resource, amount in production_stats.items():
        if amount > 0:
            report += f"▫️ {get_resource_name(resource)}: +{amount:,}\n"
            total_production += amount
    
    if total_production == 0:
        report += "▫️ هیچ تولیدی ثبت نشده\n"
    report += "</blockquote>\n"
    
    # بخش زیرساخت‌ها
    report += f"\n🏗️ <b>زیرساخت‌های فعال:</b>\n"
    report += "<blockquote>\n"
    report += f"▫️ معادن: {len(mines)} عدد\n"
    report += f"▫️ مزارع: {len(farms)} عدد\n"
    report += f"▫️ نیروگاه‌ها: {len(energy)} عدد\n"
    report += "</blockquote>\n"
    
    # بخش توصیه‌ها
    report += f"\n💡 <b>توصیه‌های وزیر:</b>\n"
    if len(mines) < 3:
        report += "▫️ ساخت معادن بیشتر برای افزایش تولید\n"
    if len(farms) < 2:
        report += "▫️ توسعه کشاورزی برای تامین غذا\n"
    if len(energy) < 2:
        report += "▫️ ساخت نیروگاه‌های بیشتر\n"
    if total_production > 0:
        report += "▫️ تولیدات این دور رضایت‌بخش بوده است\n"
    
    return report

def generate_general_report(user_id, turn):
    """تولید گزارش ژنرال"""
    user = utils.users.get(user_id, {})
    if not user.get('activated'):
        return None
    
    resources = user.get('resources', {})
    general_name = user.get('selected_officials', {}).get('general', {}).get('name', 'ژنرال')
    
    # محاسبه قدرت نظامی
    military_power = calculate_military_power(resources)
    
    # بررسی جنگ‌های اخیر
    wars = get_recent_wars(user_id, turn)
    
    report = f"⚔️ <b>گزارش نظامی</b>\n\n"
    report += f"🎖️ <b>ژنرال:</b> {general_name}\n"
    report += f"📅 <b>تاریخ:</b> {utils.game_data.get('game_date', 'نامشخص')}\n"
    report += f"🔄 <b>دور:</b> {turn}\n\n"
    
    # بخش قدرت نظامی
    report += "🛡️ <b>وضعیت نظامی:</b>\n"
    report += "<blockquote>\n"
    report += f"▫️ سربازان: {resources.get('soldiers', 0):,} نفر\n"
    report += f"▫️ نیروهای ویژه: {resources.get('special_forces', 0):,} نفر\n"
    report += f"▫️ تانک‌ها: {resources.get('tanks', 0):,} دستگاه\n"
    report += f"▫️ هواپیماهای جنگی: {resources.get('fighter_jets', 0):,} فروند\n"
    report += f"▫️ کشتی‌های جنگی: {resources.get('naval_ship', 0):,} فروند\n"
    report += f"▫️ قدرت کلی: {military_power:,}\n"
    report += "</blockquote>\n\n"
    
    # بخش جنگ‌های اخیر
    if wars:
        report += "🔥 <b>جنگ‌های اخیر:</b>\n"
        for war in wars:
            report += f"▫️ {war['description']}\n"
    else:
        report += "🕊️ <b>وضعیت صلح:</b>\n"
        report += "▫️ هیچ جنگی در این دور رخ نداده\n\n"
    
    # بخش توصیه‌ها
    report += "💡 <b>توصیه‌های ژنرال:</b>\n"
    if resources.get('soldiers', 0) < 100000:
        report += "▫️ افزایش تعداد سربازان\n"
    if resources.get('tanks', 0) < 50:
        report += "▫️ تقویت نیروی زرهی\n"
    if resources.get('fighter_jets', 0) < 20:
        report += "▫️ تقویت نیروی هوایی\n"
    if resources.get('naval_ship', 0) < 10:
        report += "▫️ تقویت نیروی دریایی\n"
    
    if military_power > 1000000:
        report += "▫️ قدرت نظامی در سطح مطلوب است\n"
    
    return report

def generate_foreign_minister_report(user_id, turn):
    """تولید گزارش وزیر خارجه"""
    user = utils.users.get(user_id, {})
    if not user.get('activated'):
        return None
    
    foreign_name = user.get('selected_officials', {}).get('foreign', {}).get('name', 'وزیر خارجه')
    
    # بررسی روابط دیپلماتیک
    from utils import country_relations
    user_relations = country_relations.get(user_id, {})
    
    # محاسبه آمار روابط
    positive_relations = sum(1 for rel in user_relations.values() if rel > 0)
    negative_relations = sum(1 for rel in user_relations.values() if rel < 0)
    neutral_relations = len(user_relations) - positive_relations - negative_relations
    
    report = f"🌍 <b>گزارش دیپلماتیک</b>\n\n"
    report += f"👨‍💼 <b>وزیر خارجه:</b> {foreign_name}\n"
    report += f"📅 <b>تاریخ:</b> {utils.game_data.get('game_date', 'نامشخص')}\n"
    report += f"🔄 <b>دور:</b> {turn}\n\n"
    
    # بخش روابط دیپلماتیک
    report += "🤝 <b>وضعیت روابط:</b>\n"
    report += "<blockquote>\n"
    report += f"▫️ روابط مثبت: {positive_relations} کشور\n"
    report += f"▫️ روابط منفی: {negative_relations} کشور\n"
    report += f"▫️ روابط خنثی: {neutral_relations} کشور\n"
    report += "</blockquote>\n\n"
    
    # بخش اتحادها
    from utils import alliances, user_alliances
    user_alliance = None
    for alliance_id, alliance_data in alliances.items():
        if user_id in alliance_data.get('members', []):
            user_alliance = alliance_data
            break
    
    if user_alliance:
        report += "🤝 <b>اتحاد:</b>\n"
        report += "<blockquote>\n"
        report += f"▫️ نام اتحاد: {user_alliance.get('name', 'نامشخص')}\n"
        report += f"▫️ تعداد اعضا: {len(user_alliance.get('members', []))}\n"
        report += "</blockquote>\n\n"
    else:
        report += "🤝 <b>اتحاد:</b>\n"
        report += "<blockquote>\n"
        report += "▫️ عضویت در هیچ اتحادی\n"
        report += "</blockquote>\n\n"
    
    # بخش توصیه‌ها
    report += "💡 <b>توصیه‌های وزیر خارجه:</b>\n"
    if positive_relations < 3:
        report += "▫️ بهبود روابط با کشورهای دیگر\n"
    if negative_relations > 2:
        report += "▫️ تلاش برای کاهش تنش‌های دیپلماتیک\n"
    if not user_alliance:
        report += "▫️ پیوستن به اتحاد یا تشکیل اتحاد جدید\n"
    else:
        report += "▫️ تقویت روابط درون اتحادی\n"
    
    return report

def generate_finance_minister_report(user_id, turn):
    """تولید گزارش وزیر دارایی"""
    user = utils.users.get(user_id, {})
    if not user.get('activated'):
        return None
    
    resources = user.get('resources', {})
    finance_name = user.get('selected_officials', {}).get('finance', {}).get('name', 'وزیر دارایی')
    
    # محاسبه ارزش کل دارایی‌ها
    prices = utils.game_data.get('prices', {})
    total_value = 0
    
    for resource, amount in resources.items():
        if resource in prices:
            total_value += amount * prices[resource]
    
    # محاسبه رشد اقتصادی
    previous_turn = turn - 1
    growth_rate = calculate_economic_growth(user_id, previous_turn)
    
    report = f"💰 <b>گزارش اقتصادی</b>\n\n"
    report += f"👨‍💼 <b>وزیر دارایی:</b> {finance_name}\n"
    report += f"📅 <b>تاریخ:</b> {utils.game_data.get('game_date', 'نامشخص')}\n"
    report += f"🔄 <b>دور:</b> {turn}\n\n"
    
    # بخش دارایی‌ها
    report += "💎 <b>دارایی‌های کلیدی:</b>\n"
    report += "<blockquote>\n"
    report += f"▫️ پول نقد: {resources.get('cash', 0):,} دلار\n"
    report += f"▫️ طلا: {resources.get('gold', 0):,} کیلوگرم\n"
    report += f"▫️ الماس: {resources.get('diamond', 0):,} قیراط\n"
    report += f"▫️ اورانیوم: {resources.get('uranium', 0):,} کیلوگرم\n"
    report += f"▫️ ارزش کل: {total_value:,} دلار\n"
    report += "</blockquote>\n\n"
    
    # بخش رشد اقتصادی
    report += "📈 <b>رشد اقتصادی:</b>\n"
    report += "<blockquote>\n"
    if growth_rate > 0:
        report += f"▫️ نرخ رشد: +{growth_rate:.1f}%\n"
    elif growth_rate < 0:
        report += f"▫️ نرخ رشد: {growth_rate:.1f}%\n"
    else:
        report += "▫️ نرخ رشد: ثابت\n"
    report += "</blockquote>\n"
    
    # بخش توصیه‌ها
    report += "\n💡 <b>توصیه‌های وزیر دارایی:</b>\n"
    if resources.get('cash', 0) < 100000000:
        report += "▫️ افزایش سرمایه‌گذاری\n"
    if resources.get('gold', 0) < 10:
        report += "▫️ افزایش ذخایر طلا\n"
    if total_value < 1000000000:
        report += "▫️ تنوع‌بخشی به دارایی‌ها\n"
    if growth_rate < 0:
        report += "▫️ بررسی سیاست‌های اقتصادی\n"
    
    return report

def get_resource_name(resource):
    """تبدیل نام انگلیسی منبع به فارسی"""
    names = {
        'iron': 'آهن', 'gold': 'طلا', 'copper': 'مس', 'diamond': 'الماس',
        'aluminum': 'آلومینیوم', 'titanium': 'تیتانیوم', 'wheat': 'گندم',
        'rice': 'برنج', 'fruits': 'میوه', 'electricity': 'برق',
        'oil': 'نفت', 'gas': 'گاز'
    }
    return names.get(resource, resource)

def get_leader_title(government_type):
    """دریافت لقب رهبر بر اساس نوع حکومت"""
    if 'democracy' in government_type:
        return 'رییس جمهور'
    elif 'republic' in government_type:
        return 'رییس جمهور'
    elif 'empire' in government_type:
        return 'امپراتور'
    elif 'kingdom' in government_type:
        return 'پادشاه'
    elif 'dictatorship' in government_type:
        return 'دیکتاتور'
    elif 'federation' in government_type:
        return 'فرمانده'
    elif 'alliance' in government_type:
        return 'رهبر'
    else:
        return 'رهبر'

def calculate_military_power(resources):
    """محاسبه قدرت نظامی"""
    power = 0
    power += resources.get('soldiers', 0) * 1
    power += resources.get('special_forces', 0) * 10
    power += resources.get('tanks', 0) * 1000
    power += resources.get('fighter_jets', 0) * 5000
    power += resources.get('naval_ship', 0) * 3000
    return power

def get_recent_wars(user_id, turn):
    """دریافت جنگ‌های اخیر"""
    # این تابع می‌تواند از فایل جنگ‌ها اطلاعات بگیرد
    # فعلاً خالی برمی‌گردانیم
    return []

def calculate_economic_growth(user_id, previous_turn):
    """محاسبه رشد اقتصادی"""
    user = utils.users.get(user_id, {})
    if not user:
        return 0
    
    resources = user.get('resources', {})
    
    # محاسبه ارزش کل دارایی‌ها
    prices = utils.game_data.get('prices', {})
    current_value = 0
    
    for resource, amount in resources.items():
        if resource in prices:
            current_value += amount * prices[resource]
    
    # محاسبه رشد بر اساس عوامل مختلف
    growth_factors = []
    
    # رشد بر اساس پول نقد
    cash = resources.get('cash', 0)
    if cash > 500000000:  # بیش از 500M
        growth_factors.append(2.0)
    elif cash > 200000000:  # بیش از 200M
        growth_factors.append(1.5)
    elif cash > 100000000:  # بیش از 100M
        growth_factors.append(1.0)
    else:
        growth_factors.append(0.5)
    
    # رشد بر اساس طلا
    gold = resources.get('gold', 0)
    if gold > 20:
        growth_factors.append(1.5)
    elif gold > 10:
        growth_factors.append(1.0)
    else:
        growth_factors.append(0.5)
    
    # رشد بر اساس زیرساخت‌ها
    economy = user.get('economy', {})
    mines = len(economy.get('mines', []))
    farms = len(economy.get('farms', []))
    energy = len(economy.get('energy', []))
    
    infrastructure_score = (mines + farms + energy) / 10.0
    growth_factors.append(min(infrastructure_score, 2.0))
    
    # رشد بر اساس حکومت
    gov_type = user.get('government_type', '')
    if 'democracy' in gov_type:
        growth_factors.append(1.2)
    elif 'republic' in gov_type:
        growth_factors.append(1.1)
    elif 'empire' in gov_type:
        growth_factors.append(1.0)
    else:
        growth_factors.append(0.8)
    
    # محاسبه میانگین رشد
    avg_growth = sum(growth_factors) / len(growth_factors)
    
    # اضافه کردن نوسان تصادفی
    random_factor = random.uniform(-1, 1)
    final_growth = avg_growth + random_factor
    
    # محدود کردن رشد بین -5 تا +10 درصد
    return max(-5, min(10, final_growth))

async def send_official_reports(bot, turn):
    """ارسال گزارش‌های مسئولین به تمام کاربران"""
    # اطمینان از اینکه users یک دیکشنری است
    if not isinstance(utils.users, dict):
        print(f"خطا: utils.users باید دیکشنری باشد، اما {type(utils.users)} است")
        return
    
    for user_id, user in utils.users.items():
        if not user.get('activated'):
            continue
        
        try:
            # ارسال گزارش وزیر کشور
            minister_report = generate_minister_report(user_id, turn)
            if minister_report:
                await bot.send_message(
                    chat_id=int(user_id),
                    text=minister_report,
                    parse_mode='HTML'
                )
            
            # ارسال گزارش ژنرال
            general_report = generate_general_report(user_id, turn)
            if general_report:
                await bot.send_message(
                    chat_id=int(user_id),
                    text=general_report,
                    parse_mode='HTML'
                )
            
            # ارسال گزارش وزیر خارجه
            foreign_report = generate_foreign_minister_report(user_id, turn)
            if foreign_report:
                await bot.send_message(
                    chat_id=int(user_id),
                    text=foreign_report,
                    parse_mode='HTML'
                )
            
            # ارسال گزارش وزیر دارایی
            finance_report = generate_finance_minister_report(user_id, turn)
            if finance_report:
                await bot.send_message(
                    chat_id=int(user_id),
                    text=finance_report,
                    parse_mode='HTML'
                )
                
        except Exception as e:
            print(f"خطا در ارسال گزارش به کاربر {user_id}: {e}")
            continue

async def send_economic_growth_report_to_channel(bot, turn):
    """ارسال گزارش رشد اقتصادی به کانال"""
    try:
        # اطمینان از اینکه utils.users یک دیکشنری است
        if not isinstance(utils.users, dict):
            print(f"خطا: utils.users باید دیکشنری باشد، اما {type(utils.users)} است")
            return
        from utils import NEWS_CHANNEL_ID
        
        # محاسبه آمار رشد اقتصادی
        growth_stats = []
        total_growth = 0
        positive_growth_count = 0
        negative_growth_count = 0
        
        for user_id, user in utils.users.items():
            if not user.get('activated'):
                continue
            
            growth_rate = calculate_economic_growth(user_id, turn - 1)
            if growth_rate > 0:
                positive_growth_count += 1
            elif growth_rate < 0:
                negative_growth_count += 1
            
            total_growth += growth_rate
            
            # دریافت لقب رهبر
            government_type = user.get('government_type', '')
            leader_title = get_leader_title(government_type)
            leader_name = user.get('player_name', 'نامشخص')
            
            growth_stats.append({
                'country': user.get('country', 'نامشخص'),
                'leader': f"{leader_title} {leader_name}",
                'growth': growth_rate
            })
        
        # مرتب‌سازی بر اساس رشد اقتصادی
        growth_stats.sort(key=lambda x: x['growth'], reverse=True)
        
        # تولید گزارش
        report = f"📈 <b>گزارش رشد اقتصادی جهانی - دور {turn}</b>\n\n"
        report += f"📅 <b>تاریخ:</b> {utils.game_data.get('game_date', 'نامشخص')}\n"
        report += f"🌍 <b>تعداد کشورها:</b> {len(growth_stats)}\n\n"
        
        # آمار کلی
        avg_growth = total_growth / len(growth_stats) if growth_stats else 0
        report += "📊 <b>آمار کلی:</b>\n"
        report += f"▫️ میانگین رشد: {avg_growth:.1f}%\n"
        report += f"▫️ کشورهای با رشد مثبت: {positive_growth_count}\n"
        report += f"▫️ کشورهای با رشد منفی: {negative_growth_count}\n\n"
        
        # برترین‌ها
        report += "🏆 <b>برترین‌های رشد اقتصادی:</b>\n"
        report += "<blockquote>\n"
        for i, stat in enumerate(growth_stats[:5], 1):
            emoji = "📈" if stat['growth'] > 0 else "📉" if stat['growth'] < 0 else "➡️"
            report += f"{i}. {emoji} {stat['country']}\n"
            report += f"   👑 {stat['leader']}\n"
            report += f"   📊 رشد: {stat['growth']:.1f}%\n\n"
        report += "</blockquote>\n"
        
        # بدترین‌ها
        if len(growth_stats) > 5:
            report += f"\n📉 <b>کشورهای با کمترین رشد:</b>\n"
            report += "<blockquote>\n"
            for i, stat in enumerate(growth_stats[-3:], 1):
                emoji = "📈" if stat['growth'] > 0 else "📉" if stat['growth'] < 0 else "➡️"
                report += f"{i}. {emoji} {stat['country']}\n"
                report += f"   👑 {stat['leader']}\n"
                report += f"   📊 رشد: {stat['growth']:.1f}%\n\n"
            report += "</blockquote>\n"
        
        # ارسال به کانال
        await bot.send_message(
            chat_id=NEWS_CHANNEL_ID,
            text=report,
            parse_mode='HTML'
        )
        
        print(f"گزارش رشد اقتصادی برای دور {turn} به کانال ارسال شد")
        
    except Exception as e:
        print(f"خطا در ارسال گزارش رشد اقتصادی: {e}") 