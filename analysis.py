import utils
import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# تابع تحلیل هوشمند نظامی
def generate_military_analysis(user_id, resources):
    analysis = ""
    
    # محاسبه قدرت‌های مختلف
    ground_power = (resources.get('soldiers', 0) + 
                   resources.get('special_forces', 0) * 5 + 
                   resources.get('tanks', 0) * 10 + 
                   resources.get('armored_vehicles', 0) * 8)
    
    air_power = (resources.get('transport_planes', 0) * 5 + 
                 resources.get('helicopters', 0) * 8 + 
                 resources.get('fighter_jets', 0) * 20 + 
                 resources.get('bombers', 0) * 25 + 
                 resources.get('drones', 0) * 12)
    
    naval_power = (resources.get('speedboats', 0) * 5 + 
                   resources.get('naval_ship', 0) * 15 + 
                   resources.get('submarines', 0) * 20 + 
                   resources.get('aircraft_carriers', 0) * 50)
    
    missile_power = (resources.get('defense_missiles', 0) * 8 + 
                     resources.get('ballistic_missiles', 0) * 30)
    
    total_power = ground_power + air_power + naval_power + missile_power
    
    # تحلیل قدرت زمینی
    if ground_power > 1000:
        analysis += "🟢 <b>🦶 قدرت زمینی:</b> بسیار قوی - آماده برای عملیات‌های گسترده\n"
    elif ground_power > 500:
        analysis += "🟡 <b>🦶 قدرت زمینی:</b> متوسط - نیاز به تقویت دارد\n"
    else:
        analysis += "🔴 <b>🦶 قدرت زمینی:</b> ضعیف - نیاز به سرمایه‌گذاری فوری\n"
    
    # تحلیل قدرت هوایی
    if air_power > 800:
        analysis += "🟢 <b>🛩️ قدرت هوایی:</b> برتر - کنترل کامل آسمان\n"
    elif air_power > 400:
        analysis += "🟡 <b>🛩️ قدرت هوایی:</b> قابل قبول - نیاز به بهبود دارد\n"
    else:
        analysis += "🔴 <b>🛩️ قدرت هوایی:</b> ضعیف - آسیب‌پذیر در برابر حملات هوایی\n"
    
    # تحلیل قدرت دریایی
    if naval_power > 600:
        analysis += "🟢 <b>🌊 قدرت دریایی:</b> قوی - کنترل دریاها\n"
    elif naval_power > 300:
        analysis += "🟡 <b>🌊 قدرت دریایی:</b> متوسط - نیاز به تقویت ناوگان\n"
    else:
        analysis += "🔴 <b>🌊 قدرت دریایی:</b> ضعیف - آسیب‌پذیر در دریا\n"
    
    # تحلیل قدرت موشکی
    if missile_power > 400:
        analysis += "🟢 <b>🚀 قدرت موشکی:</b> پیشرفته - قابلیت ضربه‌زنی دوربرد\n"
    elif missile_power > 200:
        analysis += "🟡 <b>🚀 قدرت موشکی:</b> متوسط - نیاز به توسعه دارد\n"
    else:
        analysis += "🔴 <b>🚀 قدرت موشکی:</b> ضعیف - فاقد قابلیت‌های پیشرفته\n"
    
    # توصیه‌های استراتژیک
    analysis += "\n<b>🎯 توصیه‌های استراتژیک:</b>\n"
    
    if ground_power < 500:
        analysis += "🦶 تقویت نیروهای زمینی اولویت اول\n"
    if air_power < 400:
        analysis += "🛩️ توسعه نیروی هوایی ضروری است\n"
    if naval_power < 300:
        analysis += "🌊 سرمایه‌گذاری در نیروی دریایی\n"
    if missile_power < 200:
        analysis += "🚀 توسعه سیستم‌های موشکی\n"
    
    if total_power > 3000:
        analysis += "🎖️ <b>🏆 وضعیت کلی:</b> قدرت نظامی برتر جهان\n"
    elif total_power > 1500:
        analysis += "🥇 <b>💪 وضعیت کلی:</b> قدرت نظامی قوی\n"
    elif total_power > 800:
        analysis += "🥈 <b>⚖️ وضعیت کلی:</b> قدرت نظامی متوسط\n"
    else:
        analysis += "🥉 <b>⚠️ وضعیت کلی:</b> نیاز به تقویت فوری\n"
    
    return analysis

def generate_strategy_analysis(user_id):
    """تحلیل کلی استراتژی نظامی"""
    analysis = ""
    
    user = utils.users.get(user_id, {})
    if not user:
        return "اطلاعات کاربر یافت نشد."
    
    resources = user.get('resources', {})
    user_country = user.get('country', 'کشور ناشناس')
    
    # محاسبه قدرت‌های مختلف
    ground_power = (resources.get('soldiers', 0) + 
                   resources.get('special_forces', 0) * 5 + 
                   resources.get('tanks', 0) * 10 + 
                   resources.get('armored_vehicles', 0) * 8)
    
    air_power = (resources.get('transport_planes', 0) * 5 + 
                 resources.get('helicopters', 0) * 8 + 
                 resources.get('fighter_jets', 0) * 20 + 
                 resources.get('bombers', 0) * 25 + 
                 resources.get('drones', 0) * 12)
    
    naval_power = (resources.get('coastal_artillery', 0) * 10 + 
                   resources.get('speedboats', 0) * 5 + 
                   resources.get('naval_ship', 0) * 15 + 
                   resources.get('submarines', 0) * 20 + 
                   resources.get('aircraft_carriers', 0) * 50)
    
    total_power = ground_power + air_power + naval_power
    
    # اگر ژنرال ترور شده باشد، این تحلیل باید از بیرون مسدود شود.
    analysis += f"🎯 <b>تحلیل استراتژیک {user_country}:</b>\n\n"
    
    # تحلیل قابلیت‌های مختلف
    analysis += "<b>⚔️ قابلیت‌های نظامی:</b>\n"
    
    # حمله زمینی
    if ground_power > 800:
        analysis += "🟢 حمله زمینی: قوی - آماده برای عملیات‌های گسترده\n"
    elif ground_power > 400:
        analysis += "🟡 حمله زمینی: متوسط - نیاز به تقویت دارد\n"
    else:
        analysis += "🔴 حمله زمینی: ضعیف - ریسک بالا\n"
    
    # حمله هوایی
    if air_power > 600:
        analysis += "🟢 حمله هوایی: برتر - کنترل کامل آسمان\n"
    elif air_power > 300:
        analysis += "🟡 حمله هوایی: قابل قبول - نیاز به بهبود دارد\n"
    else:
        analysis += "🔴 حمله هوایی: ضعیف - آسیب‌پذیر\n"
    
    # حمله دریایی
    if naval_power > 500:
        analysis += "🟢 حمله دریایی: قوی - کنترل دریاها\n"
    elif naval_power > 250:
        analysis += "🟡 حمله دریایی: متوسط - نیاز به تقویت ناوگان\n"
    else:
        analysis += "🔴 حمله دریایی: ضعیف - محدودیت جغرافیایی\n"
    
    # غارت
    special_forces = resources.get('special_forces', 0)
    if special_forces > 200:
        analysis += "🟢 غارت: قوی - نیروهای ویژه کافی\n"
    elif special_forces > 100:
        analysis += "🟡 غارت: متوسط - نیاز به نیروهای ویژه بیشتر\n"
    else:
        analysis += "🔴 غارت: ضعیف - نیاز به نیروهای ویژه\n"
    
    # توصیه‌های استراتژیک
    analysis += "\n<b>🎯 توصیه‌های استراتژیک:</b>\n"
    
    if ground_power < 400:
        analysis += "🦶 اولویت: تقویت نیروهای زمینی\n"
    if air_power < 300:
        analysis += "🛩️ اولویت: توسعه نیروی هوایی\n"
    if naval_power < 250:
        analysis += "🌊 اولویت: سرمایه‌گذاری در نیروی دریایی\n"
    if special_forces < 100:
        analysis += "⚔️ اولویت: افزایش نیروهای ویژه\n"
    
    # تحلیل ریسک
    analysis += "\n<b>⚠️ تحلیل ریسک:</b>\n"
    
    if total_power < 1000:
        analysis += "🔴 ریسک بالا: آسیب‌پذیر در برابر حملات\n"
        analysis += "💡 توصیه: تمرکز بر دفاع و تقویت نیروها\n"
    elif total_power < 2000:
        analysis += "🟡 ریسک متوسط: نیاز به بهبود قابلیت‌ها\n"
        analysis += "💡 توصیه: توسعه متعادل نیروها\n"
    else:
        analysis += "🟢 ریسک پایین: قدرت نظامی قوی\n"
        analysis += "💡 توصیه: حفظ برتری و توسعه بیشتر\n"
    
    return analysis

def generate_ground_attack_analysis(user_id, target_country):
    """تحلیل حمله زمینی بر اساس رتبه نظامی"""
    analysis = ""
    
    user = utils.users.get(user_id, {})
    if not user:
        return "اطلاعات کاربر یافت نشد."
    
    user_resources = user.get('resources', {})
    user_country = user.get('country', 'کشور ناشناس')
    
    # محاسبه قدرت زمینی خود
    own_ground_power = (user_resources.get('soldiers', 0) + 
                       user_resources.get('special_forces', 0) * 5 + 
                       user_resources.get('tanks', 0) * 10 + 
                       user_resources.get('armored_vehicles', 0) * 8)
    
    # تخمین قدرت زمینی هدف (با 30% اختلاف رندوم)
    target_ground_power_real = 0
    target_id = None
    for uid, target_user in utils.users.items():
        if target_user.get('country') == target_country:
            target_id = uid
            target_resources = target_user.get('resources', {})
            target_ground_power_real = (target_resources.get('soldiers', 0) + 
                                      target_resources.get('special_forces', 0) * 5 + 
                                      target_resources.get('tanks', 0) * 10 + 
                                      target_resources.get('armored_vehicles', 0) * 8)
            break
    
    # اعمال اختلاف رندوم برای تخمین
    deviation = random.uniform(-0.3, 0.3)  # 30% اختلاف
    target_ground_power_estimated = int(target_ground_power_real * (1 + deviation))
    
    analysis += f"⚔️ <b>تحلیل حمله زمینی به {target_country}:</b>\n\n"
    
    # مقایسه قدرت‌ها
    power_ratio = own_ground_power / max(target_ground_power_estimated, 1)
    
    analysis += f"🦶 قدرت زمینی شما: {own_ground_power:,}\n"
    analysis += f"🦶 قدرت زمینی {target_country} (تخمین): {target_ground_power_estimated:,}\n"
    analysis += f"📊 نسبت قدرت: {power_ratio:.2f}\n\n"
    
    # تحلیل ریسک و توصیه
    if power_ratio > 2.0:
        analysis += "🟢 <b>وضعیت: برتری قاطع</b>\n"
        analysis += "✅ احتمال پیروزی: بسیار بالا\n"
        analysis += "💡 توصیه: حمله با اطمینان بالا\n"
        analysis += "⚠️ هشدار: مراقب اتحادهای احتمالی باشید\n"
    elif power_ratio > 1.5:
        analysis += "🟡 <b>وضعیت: برتری نسبی</b>\n"
        analysis += "✅ احتمال پیروزی: بالا\n"
        analysis += "💡 توصیه: حمله با احتیاط\n"
        analysis += "⚠️ هشدار: تلفات قابل توجه انتظار می‌رود\n"
    elif power_ratio > 1.0:
        analysis += "🟡 <b>وضعیت: برابری نسبی</b>\n"
        analysis += "⚖️ احتمال پیروزی: متوسط\n"
        analysis += "💡 توصیه: نیاز به تقویت نیروها\n"
        analysis += "⚠️ هشدار: ریسک بالا - تلفات سنگین\n"
    elif power_ratio > 0.7:
        analysis += "🔴 <b>وضعیت: ضعف نسبی</b>\n"
        analysis += "❌ احتمال پیروزی: پایین\n"
        analysis += "💡 توصیه: تقویت نیروها قبل از حمله\n"
        analysis += "⚠️ هشدار: احتمال شکست بالا\n"
    else:
        analysis += "🔴 <b>وضعیت: ضعف قاطع</b>\n"
        analysis += "❌ احتمال پیروزی: بسیار پایین\n"
        analysis += "💡 توصیه: پرهیز از حمله\n"
        analysis += "⚠️ هشدار: ریسک فاجعه‌بار\n"
    
    # توصیه‌های تخصصی
    analysis += "\n<b>🎯 توصیه‌های تخصصی:</b>\n"
    
    if own_ground_power < 500:
        analysis += "🦶 نیاز به تقویت فوری نیروهای زمینی\n"
    if user_resources.get('tanks', 0) < 50:
        analysis += "🛡️ افزایش تعداد تانک‌ها ضروری\n"
    if user_resources.get('artillery', 0) < 30:
        analysis += "🎯 تقویت توپخانه برای پشتیبانی\n"
    if user_resources.get('special_forces', 0) < 100:
        analysis += "⚔️ نیروهای ویژه برای عملیات‌های ویژه\n"
    
    analysis += f"\n⚠️ <b>هشدار:</b> ما آمار دقیق از قدرت نظامی {target_country} نداریم. این تحلیل بر اساس تخمین اطلاعات است و ممکن است با واقعیت متفاوت باشد.\n"
    
    return analysis

def generate_air_attack_analysis(user_id, target_country):
    """تحلیل حمله هوایی بر اساس رتبه نظامی"""
    analysis = ""
    
    user = utils.users.get(user_id, {})
    if not user:
        return "اطلاعات کاربر یافت نشد."
    
    user_resources = user.get('resources', {})
    user_country = user.get('country', 'کشور ناشناس')
    
    # محاسبه قدرت هوایی خود (بدون پدافند هوایی)
    own_air_power = (user_resources.get('transport_planes', 0) * 5 + 
                     user_resources.get('helicopters', 0) * 8 + 
                     user_resources.get('fighter_jets', 0) * 20 + 
                     user_resources.get('bombers', 0) * 25 + 
                     user_resources.get('drones', 0) * 12)
    
    # تخمین قدرت هوایی هدف (با 30% اختلاف رندوم)
    target_air_power_real = 0
    target_id = None
    for uid, target_user in utils.users.items():
        if target_user.get('country') == target_country:
            target_id = uid
            target_resources = target_user.get('resources', {})
            target_air_power_real = (target_resources.get('transport_planes', 0) * 5 + 
                                   target_resources.get('helicopters', 0) * 8 + 
                                   target_resources.get('fighter_jets', 0) * 20 + 
                                   target_resources.get('bombers', 0) * 25 + 
                                   target_resources.get('drones', 0) * 12 + 
                                   target_resources.get('air_defense', 0) * 15)  # پدافند هوایی برای دفاع
            break
    
    # اعمال اختلاف رندوم برای تخمین
    deviation = random.uniform(-0.3, 0.3)  # 30% اختلاف
    target_air_power_estimated = int(target_air_power_real * (1 + deviation))
    
    analysis += f"🛩️ <b>تحلیل حمله هوایی به {target_country}:</b>\n\n"
    
    # مقایسه قدرت‌ها
    power_ratio = own_air_power / max(target_air_power_estimated, 1)
    
    analysis += f"🛩️ قدرت هوایی شما: {own_air_power:,}\n"
    analysis += f"🛩️ قدرت هوایی {target_country} (تخمین): {target_air_power_estimated:,}\n"
    analysis += f"📊 نسبت قدرت: {power_ratio:.2f}\n\n"
    
    # تحلیل ریسک و توصیه
    if power_ratio > 2.0:
        analysis += "🟢 <b>وضعیت: برتری هوایی قاطع</b>\n"
        analysis += "✅ احتمال پیروزی: بسیار بالا\n"
        analysis += "💡 توصیه: حمله هوایی با اطمینان\n"
        analysis += "⚠️ هشدار: مراقب پدافند هوایی باشید\n"
    elif power_ratio > 1.5:
        analysis += "🟡 <b>وضعیت: برتری هوایی نسبی</b>\n"
        analysis += "✅ احتمال پیروزی: بالا\n"
        analysis += "💡 توصیه: حمله با احتیاط\n"
        analysis += "⚠️ هشدار: تلفات هوایی قابل توجه\n"
    elif power_ratio > 1.0:
        analysis += "🟡 <b>وضعیت: برابری هوایی</b>\n"
        analysis += "⚖️ احتمال پیروزی: متوسط\n"
        analysis += "💡 توصیه: نیاز به تقویت نیروی هوایی\n"
        analysis += "⚠️ هشدار: نبرد هوایی سخت\n"
    elif power_ratio > 0.7:
        analysis += "🔴 <b>وضعیت: ضعف هوایی نسبی</b>\n"
        analysis += "❌ احتمال پیروزی: پایین\n"
        analysis += "💡 توصیه: تقویت نیروی هوایی\n"
        analysis += "⚠️ هشدار: احتمال شکست بالا\n"
    else:
        analysis += "🔴 <b>وضعیت: ضعف هوایی قاطع</b>\n"
        analysis += "❌ احتمال پیروزی: بسیار پایین\n"
        analysis += "💡 توصیه: پرهیز از حمله هوایی\n"
        analysis += "⚠️ هشدار: ریسک فاجعه‌بار\n"
    
    # توصیه‌های تخصصی
    analysis += "\n<b>🎯 توصیه‌های تخصصی:</b>\n"
    
    if own_air_power < 400:
        analysis += "🛩️ نیاز به تقویت فوری نیروی هوایی\n"
    if user_resources.get('fighter_jets', 0) < 30:
        analysis += "🛩️ افزایش جنگنده‌ها ضروری\n"
    if user_resources.get('bombers', 0) < 20:
        analysis += "💣 تقویت بمب‌افکن‌ها\n"
    if user_resources.get('air_defense', 0) < 50:
        analysis += "🛡️ تقویت پدافند هوایی\n"
    
    analysis += f"\n⚠️ <b>هشدار:</b> ما آمار دقیق از قدرت نظامی {target_country} نداریم. این تحلیل بر اساس تخمین اطلاعات است و ممکن است با واقعیت متفاوت باشد.\n"
    
    return analysis

def generate_naval_attack_analysis(user_id, target_country):
    """تحلیل حمله دریایی بر اساس رتبه نظامی"""
    analysis = ""
    
    user = utils.users.get(user_id, {})
    if not user:
        return "اطلاعات کاربر یافت نشد."
    
    user_resources = user.get('resources', {})
    user_country = user.get('country', 'کشور ناشناس')
    
    # محاسبه قدرت دریایی خود
    own_naval_power = (user_resources.get('speedboats', 0) * 5 + 
                      user_resources.get('naval_ship', 0) * 15 + 
                      user_resources.get('submarines', 0) * 20 + 
                      user_resources.get('aircraft_carriers', 0) * 50)
    
    # تخمین قدرت دریایی هدف (با 30% اختلاف رندوم)
    target_naval_power_real = 0
    target_id = None
    for uid, target_user in utils.users.items():
        if target_user.get('country') == target_country:
            target_id = uid
            target_resources = target_user.get('resources', {})
            target_naval_power_real = (target_resources.get('speedboats', 0) * 5 + 
                                     target_resources.get('naval_ship', 0) * 15 + 
                                     target_resources.get('submarines', 0) * 20 + 
                                     target_resources.get('aircraft_carriers', 0) * 50)
            break
    
    # اعمال اختلاف رندوم برای تخمین
    deviation = random.uniform(-0.3, 0.3)  # 30% اختلاف
    target_naval_power_estimated = int(target_naval_power_real * (1 + deviation))
    
    analysis += f"🌊 <b>تحلیل حمله دریایی به {target_country}:</b>\n\n"
    
    # مقایسه قدرت‌ها
    power_ratio = own_naval_power / max(target_naval_power_estimated, 1)
    
    analysis += f"🌊 قدرت دریایی شما: {own_naval_power:,}\n"
    analysis += f"🌊 قدرت دریایی {target_country} (تخمین): {target_naval_power_estimated:,}\n"
    analysis += f"📊 نسبت قدرت: {power_ratio:.2f}\n\n"
    
    # تحلیل ریسک و توصیه
    if power_ratio > 2.0:
        analysis += "🟢 <b>وضعیت: برتری دریایی قاطع</b>\n"
        analysis += "✅ احتمال پیروزی: بسیار بالا\n"
        analysis += "💡 توصیه: حمله دریایی با اطمینان\n"
        analysis += "⚠️ هشدار: مراقب اتحادهای احتمالی باشید\n"
    elif power_ratio > 1.5:
        analysis += "🟡 <b>وضعیت: برتری دریایی نسبی</b>\n"
        analysis += "✅ احتمال پیروزی: بالا\n"
        analysis += "💡 توصیه: حمله با احتیاط\n"
        analysis += "⚠️ هشدار: تلفات قابل توجه انتظار می‌رود\n"
    elif power_ratio > 1.0:
        analysis += "🟡 <b>وضعیت: برابری دریایی</b>\n"
        analysis += "⚖️ احتمال پیروزی: متوسط\n"
        analysis += "💡 توصیه: نیاز به تقویت نیروها\n"
        analysis += "⚠️ هشدار: ریسک بالا - تلفات سنگین\n"
    elif power_ratio > 0.7:
        analysis += "🔴 <b>وضعیت: ضعف دریایی نسبی</b>\n"
        analysis += "❌ احتمال پیروزی: پایین\n"
        analysis += "💡 توصیه: تقویت نیروها قبل از حمله\n"
        analysis += "⚠️ هشدار: احتمال شکست بالا\n"
    else:
        analysis += "🔴 <b>وضعیت: ضعف دریایی قاطع</b>\n"
        analysis += "❌ احتمال پیروزی: بسیار پایین\n"
        analysis += "💡 توصیه: پرهیز از حمله\n"
        analysis += "⚠️ هشدار: ریسک فاجعه‌بار\n"
    
    # توصیه‌های تخصصی
    analysis += "\n<b>🎯 توصیه‌های تخصصی:</b>\n"
    
    if own_naval_power < 500:
        analysis += "🌊 نیاز به تقویت فوری نیروهای دریایی\n"
    if user_resources.get('naval_ship', 0) < 30:
        analysis += "🚢 افزایش تعداد ناوچه‌ها ضروری\n"
    if user_resources.get('submarines', 0) < 20:
        analysis += "🛥️ تقویت زیردریایی‌ها برای عملیات مخفی\n"
    if user_resources.get('aircraft_carriers', 0) < 5:
        analysis += "✈️ ناو هواپیمابر برای کنترل دریاها\n"
    
    analysis += f"\n⚠️ <b>هشدار:</b> ما آمار دقیق از قدرت نظامی {target_country} نداریم. این تحلیل بر اساس تخمین اطلاعات است و ممکن است با واقعیت متفاوت باشد.\n"
    
    return analysis

def generate_trade_analysis(user_id):
    """تحلیل تجارت و منابع کاربر"""
    analysis = ""
    
    # دریافت اطلاعات کاربر
    user = utils.users.get(user_id, {})
    if not user:
        return "اطلاعات کاربر یافت نشد."
    
    resources = user.get('resources', {})
    cash = resources.get('cash', 0)
    
    # دریافت تجارت‌های فعال
    try:
        user_trades = [trade for trade in utils.pending_trades if str(trade.get('buyer_id')) == str(user_id) or str(trade.get('seller_id')) == str(user_id)]
    except:
        user_trades = []
    
    analysis += f"💰 <b>تحلیل اقتصادی کشور شما:</b>\n\n"
    
    # تحلیل منابع
    resource_names = {
        'gold': 'طلا', 'steel': 'فولاد', 'iron': 'آهن', 'copper': 'مس', 'aluminum': 'آلومینیوم', 
        'titanium': 'تیتانیوم', 'diamond': 'الماس', 'uranium': 'اورانیوم',
        'wheat': 'گندم', 'rice': 'برنج', 'fruits': 'میوه', 'oil': 'نفت', 'gas': 'گاز', 
        'electronics': 'الکترونیک', 'pride_cars': 'پراید', 'benz_cars': 'بنز', 
        'electricity': 'برق', 'uranium_ore': 'سنگ اورانیوم', 'centrifuge': 'سانتریفیوژ', 
        'yellowcake': 'کیک زرد', 'space_parts': 'قطعات فضایی'
    }
    
    # منابع کم
    low_resources = []
    # منابع زیاد
    high_resources = []
    
    for resource, name in resource_names.items():
        amount = resources.get(resource, 0)
        if amount < 10:
            low_resources.append((name, amount))
        elif amount > 100:
            high_resources.append((name, amount))
    
    if low_resources:
        analysis += "📉 <b>منابع کم (نیاز به خرید):</b>\n"
        for name, amount in low_resources[:5]:  # فقط 5 مورد اول
            analysis += f"   • {name}: {amount} واحد\n"
        analysis += "\n"
    
    if high_resources:
        analysis += "📈 <b>منابع زیاد (مناسب برای فروش):</b>\n"
        for name, amount in high_resources[:5]:  # فقط 5 مورد اول
            analysis += f"   • {name}: {amount} واحد\n"
        analysis += "\n"
    
    # تحلیل تجارت‌های فعال
    if user_trades:
        analysis += f"📦 <b>تجارت‌های فعال شما ({len(user_trades)} تجارت):</b>\n\n"
        
        for i, trade in enumerate(user_trades, 1):
            resource = trade.get('resource', 'نامشخص')
            amount = trade.get('amount', 0)
            total_price = trade.get('total_price', 0)
            estimated_arrival = trade.get('estimated_arrival', 'نامشخص')
            
            # محاسبه زمان باقی‌مانده
            try:
                from datetime import datetime
                if isinstance(estimated_arrival, str):
                    arrival_time = datetime.fromisoformat(estimated_arrival)
                    current_time = datetime.now()
                    remaining_time = arrival_time - current_time
                    remaining_minutes = int(remaining_time.total_seconds() / 60)
                    if remaining_minutes > 0:
                        time_text = f"{remaining_minutes} دقیقه دیگر"
                    else:
                        time_text = "در حال رسیدن"
                else:
                    time_text = "نامشخص"
            except:
                time_text = "نامشخص"
            
            trade_type = "خرید" if trade.get('buyer_id') == user_id else "فروش"
            analysis += f"📋 <b>تجارت {i} ({trade_type}):</b>\n"
            analysis += f"   📦 کالا: {resource_names.get(resource, resource)}\n"
            analysis += f"   📊 مقدار: {amount:,} واحد\n"
            analysis += f"   💰 قیمت: {total_price:,} دلار\n"
            analysis += f"   ⏰ زمان: {time_text}\n\n"
    else:
        analysis += "📦 <b>تجارت‌های فعال:</b> هیچ تجارت فعالی ندارید.\n\n"
    
    # توصیه‌های تجاری
    analysis += "💡 <b>توصیه‌های تجاری:</b>\n"
    
    if low_resources:
        analysis += "🛒 منابع کم را از بازار جهانی یا بازیکنان دیگر خریداری کنید.\n"
    
    if high_resources:
        analysis += "💰 منابع زیاد را در بازار جهانی یا به بازیکنان دیگر بفروشید.\n"
    
    if cash < 1000000:
        analysis += "⚠️ پول نقد شما کم است. سعی کنید منابع اضافی را بفروشید.\n"
    elif cash > 10000000:
        analysis += "💎 پول نقد شما زیاد است. برای توسعه کشور سرمایه‌گذاری کنید.\n"
    
    if not user_trades:
        analysis += "📈 برای افزایش درآمد، تجارت فعال داشته باشید.\n"
    
    return analysis

# تابع تحلیل هوشمند دیپلماتیک
def generate_diplomatic_analysis(user_id):
    analysis = ""
    
    # دریافت اطلاعات کاربر
    user = utils.users.get(user_id, {})
    if not user:
        return "اطلاعات کاربر یافت نشد."
    
    country_name = user.get('country', 'کشور ناشناس')
    category = user.get('category', '')
    resources = user.get('resources', {})
    cash = resources.get('cash', 0)
    
    # محاسبه قدرت اقتصادی
    total_economy = utils.calculate_total_economy(user_id)
    
    # بررسی روابط دیپلماتیک
    country_relations = utils.country_relations.get(str(user_id), {})
    total_relations = len(country_relations)
    positive_relations = sum(1 for rel in country_relations.values() if rel > 0)
    negative_relations = sum(1 for rel in country_relations.values() if rel < 0)
    
    # بررسی اتحادها
    user_alliance_id = utils.user_alliances.get(str(user_id))
    alliance_count = 1 if user_alliance_id and user_alliance_id in utils.alliances else 0
    
    # بررسی مستعمرات (شمارش کشورهایی که توسط این کاربر فتح شده‌اند)
    colony_count = 0
    for uid, user_data in utils.users.items():
        if user_data.get('conquered_by') == country_name:
            colony_count += 1
    
    # تحلیل وضعیت اقتصادی
    if total_economy > 1000000000:  # بیش از 1 میلیارد
        analysis += "🟢 <b>💰 وضعیت اقتصادی:</b> بسیار قوی - نفوذ اقتصادی بالا\n"
    elif total_economy > 500000000:  # بیش از 500 میلیون
        analysis += "🟡 <b>💰 وضعیت اقتصادی:</b> قوی - پتانسیل دیپلماتیک خوب\n"
    else:
        analysis += "🔴 <b>💰 وضعیت اقتصادی:</b> ضعیف - نیاز به بهبود اقتصادی\n"
    
    # تحلیل روابط دیپلماتیک
    if total_relations > 10:
        analysis += "🟢 <b>🤝 روابط دیپلماتیک:</b> گسترده - شبکه روابط قوی\n"
    elif total_relations > 5:
        analysis += "🟡 <b>🤝 روابط دیپلماتیک:</b> متوسط - نیاز به گسترش روابط\n"
    else:
        analysis += "🔴 <b>🤝 روابط دیپلماتیک:</b> محدود - نیاز به دیپلماسی فعال\n"
    
    # تحلیل اتحادها
    if alliance_count > 2:
        analysis += "🟢 <b>🤝 اتحادها:</b> عضو چندین اتحاد قوی\n"
    elif alliance_count > 0:
        analysis += "🟡 <b>🤝 اتحادها:</b> عضو اتحاد - پتانسیل گسترش\n"
    else:
        analysis += "🔴 <b>🤝 اتحادها:</b> بدون اتحاد - آسیب‌پذیر\n"
    
    # تحلیل مستعمرات
    if colony_count > 3:
        analysis += "🟢 <b>🏛️ مستعمرات:</b> امپراتوری گسترده\n"
    elif colony_count > 0:
        analysis += "🟡 <b>🏛️ مستعمرات:</b> دارای مستعمره - پتانسیل گسترش\n"
    else:
        analysis += "🔴 <b>🏛️ مستعمرات:</b> بدون مستعمره - نیاز به توسعه\n"
    
    # توصیه‌های دیپلماتیک
    analysis += "\n<b>🎯 توصیه‌های دیپلماتیک:</b>\n"
    
    if total_relations < 5:
        analysis += "🤝 گسترش روابط دیپلماتیک با کشورهای دیگر\n"
    if alliance_count == 0:
        analysis += "🤝 پیوستن به اتحادهای موجود یا تشکیل اتحاد جدید\n"
    if colony_count == 0:
        analysis += "🏛️ تلاش برای کسب مستعمرات جدید\n"
    if total_economy < 500000000:
        analysis += "💰 بهبود وضعیت اقتصادی برای افزایش نفوذ\n"
    
    # وضعیت کلی دیپلماتیک
    diplomatic_score = (total_relations * 2 + alliance_count * 5 + colony_count * 3 + 
                       (total_economy // 100000000))
    
    if diplomatic_score > 50:
        analysis += "🏆 <b>🌟 وضعیت کلی:</b> قدرت دیپلماتیک برتر جهان\n"
    elif diplomatic_score > 30:
        analysis += "🥇 <b>💪 وضعیت کلی:</b> قدرت دیپلماتیک قوی\n"
    elif diplomatic_score > 15:
        analysis += "🥈 <b>⚖️ وضعیت کلی:</b> قدرت دیپلماتیک متوسط\n"
    else:
        analysis += "🥉 <b>⚠️ وضعیت کلی:</b> نیاز به بهبود دیپلماتیک\n"
    
    return analysis

# تابع تحلیل هوشمند روابط دیپلماتیک
def generate_relations_analysis(user_id):
    analysis = ""
    
    # دریافت اطلاعات کاربر
    user = utils.users.get(user_id, {})
    if not user:
        return "اطلاعات کاربر یافت نشد."
    
    country_name = user.get('country', 'کشور ناشناس')
    user_relations = utils.country_relations.get(str(user_id), {})
    
    # آمار روابط
    total_relations = len(user_relations)
    positive_relations = sum(1 for rel in user_relations.values() if rel > 0)
    negative_relations = sum(1 for rel in user_relations.values() if rel < 0)
    neutral_relations = sum(1 for rel in user_relations.values() if rel == 0)
    
    # تحلیل تعداد روابط
    if total_relations == 0:
        analysis += "🔴 <b>وضعیت روابط:</b> هیچ رابطه‌ای برقرار نشده - نیاز به دیپلماسی فعال\n"
    elif total_relations < 3:
        analysis += "🟡 <b>وضعیت روابط:</b> روابط محدود - نیاز به گسترش شبکه دیپلماتیک\n"
    else:
        analysis += "🟢 <b>وضعیت روابط:</b> شبکه روابط گسترده - وضعیت مطلوب\n"
    
    # تحلیل کیفیت روابط
    if positive_relations > negative_relations:
        analysis += "🟢 <b>کیفیت روابط:</b> اکثر روابط مثبت - دیپلماسی موفق\n"
    elif positive_relations == negative_relations:
        analysis += "🟡 <b>کیفیت روابط:</b> تعادل در روابط - نیاز به بهبود\n"
    else:
        analysis += "🔴 <b>کیفیت روابط:</b> اکثر روابط منفی - نیاز به اصلاح فوری\n"
    
    # تحلیل عمق روابط
    strong_relations = sum(1 for rel in user_relations.values() if abs(rel) >= 3)
    if strong_relations > 0:
        analysis += f"🟢 <b>روابط قوی:</b> {strong_relations} رابطه عمیق برقرار شده\n"
    else:
        analysis += "🟡 <b>روابط قوی:</b> هیچ رابطه عمیقی وجود ندارد\n"
    
    # توصیه‌های استراتژیک
    analysis += "\n<b>🎯 توصیه‌های استراتژیک:</b>\n"
    
    if total_relations < 5:
        analysis += "🤝 گسترش روابط با کشورهای جدید\n"
    if positive_relations < 2:
        analysis += "🤝 تلاش برای بهبود روابط موجود\n"
    if negative_relations > 2:
        analysis += "🛡️ تلاش برای کاهش تنش‌های دیپلماتیک\n"
    if strong_relations < 2:
        analysis += "💪 تقویت روابط موجود برای ایجاد اتحاد\n"
    
    # وضعیت کلی دیپلماتیک
    diplomatic_score = (positive_relations * 2 - negative_relations + strong_relations * 3)
    
    if diplomatic_score > 10:
        analysis += "🏆 <b>🌟 وضعیت کلی:</b> قدرت دیپلماتیک برتر\n"
    elif diplomatic_score > 5:
        analysis += "🥇 <b>💪 وضعیت کلی:</b> قدرت دیپلماتیک قوی\n"
    elif diplomatic_score > 0:
        analysis += "🥈 <b>⚖️ وضعیت کلی:</b> قدرت دیپلماتیک متوسط\n"
    else:
        analysis += "🥉 <b>⚠️ وضعیت کلی:</b> نیاز به بهبود دیپلماتیک\n"
    
    return analysis

# تابع تحلیل هوشمند مستعمرات
def generate_colonies_analysis(user_id):
    analysis = ""
    
    # دریافت اطلاعات کاربر
    user = utils.users.get(user_id, {})
    if not user:
        return "اطلاعات کاربر یافت نشد."
    
    country_name = user.get('country', 'کشور ناشناس')
    
    # پیدا کردن مستعمرات کاربر
    user_colonies = []
    for uid, user_data in utils.users.items():
        if user_data.get('conquered_by') == country_name:
            colony_resources = user_data.get('resources', {})
            user_colonies.append({
                'user_id': uid,
                'country': user_data.get('country', 'نامشخص'),
                'conquered_at': user_data.get('conquered_at', 0),
                'resources': colony_resources,
                'cash': colony_resources.get('cash', 0)
            })
    
    colony_count = len(user_colonies)
    
    # تحلیل تعداد مستعمرات
    if colony_count == 0:
        analysis += "🔴 <b>وضعیت مستعمرات:</b> بدون مستعمره - آسیب‌پذیر در برابر رقبا\n"
    elif colony_count < 3:
        analysis += "🟡 <b>وضعیت مستعمرات:</b> مستعمرات محدود - نیاز به گسترش\n"
    else:
        analysis += "🟢 <b>وضعیت مستعمرات:</b> امپراتوری گسترده - قدرت برتر\n"
    
    # تحلیل ارزش اقتصادی مستعمرات
    total_colony_value = 0
    for colony in user_colonies:
        # محاسبه ارزش اقتصادی مستعمره
        colony_value = colony.get('cash', 0)
        resources = colony.get('resources', {})
        for resource, amount in resources.items():
            if resource != 'cash':
                colony_value += amount * 1000  # ارزش تقریبی هر واحد منبع
        total_colony_value += colony_value
    
    if total_colony_value > 1000000000:  # بیش از 1 میلیارد
        analysis += "🟢 <b>ارزش اقتصادی:</b> مستعمرات بسیار ارزشمند\n"
    elif total_colony_value > 500000000:  # بیش از 500 میلیون
        analysis += "🟡 <b>ارزش اقتصادی:</b> مستعمرات با ارزش متوسط\n"
    else:
        analysis += "🔴 <b>ارزش اقتصادی:</b> مستعمرات کم‌ارزش - نیاز به توسعه\n"
    
    # تحلیل تنوع جغرافیایی مستعمرات
    if colony_count > 0:
        analysis += f"🟢 <b>تنوع جغرافیایی:</b> {colony_count} مستعمره در مناطق مختلف\n"
    
    # توصیه‌های استراتژیک
    analysis += "\n<b>🎯 توصیه‌های استراتژیک:</b>\n"
    
    if colony_count == 0:
        analysis += "🏛️ تلاش برای فتح کشورهای ضعیف به عنوان مستعمره\n"
    elif colony_count < 3:
        analysis += "🏛️ گسترش امپراتوری با فتح مستعمرات بیشتر\n"
    else:
        analysis += "🏛️ حفظ و توسعه مستعمرات موجود\n"
    
    if total_colony_value < 500000000:
        analysis += "💰 سرمایه‌گذاری در توسعه اقتصادی مستعمرات\n"
    
    # وضعیت کلی امپراتوری
    empire_score = (colony_count * 10 + (total_colony_value // 100000000))
    
    if empire_score > 50:
        analysis += "🏆 <b>🌟 وضعیت کلی:</b> امپراتوری برتر جهان\n"
    elif empire_score > 30:
        analysis += "🥇 <b>💪 وضعیت کلی:</b> امپراتوری قوی\n"
    elif empire_score > 15:
        analysis += "🥈 <b>⚖️ وضعیت کلی:</b> امپراتوری متوسط\n"
    else:
        analysis += "🥉 <b>⚠️ وضعیت کلی:</b> نیاز به گسترش امپراتوری\n"
    
    return analysis

# تابع تحلیل هوشمند اتحاد
def generate_alliance_analysis(user_id):
    analysis = ""
    
    # دریافت اطلاعات کاربر
    user = utils.users.get(user_id, {})
    if not user:
        return "اطلاعات کاربر یافت نشد."
    
    country_name = user.get('country', 'کشور ناشناس')
    user_alliance_id = utils.user_alliances.get(str(user_id))
    
    if not user_alliance_id or user_alliance_id not in utils.alliances:
        return "شما در هیچ اتحادی عضو نیستید."
    
    alliance = utils.alliances[user_alliance_id]
    is_leader = (alliance.get('leader') == user_id)
    is_deputy = (alliance.get('deputy') == user_id)
    
    # آمار اتحاد
    member_count = len(alliance['members'])
    entry_fee = alliance.get('entry_fee', 0)
    
    # تحلیل قدرت اتحاد
    if member_count > 5:
        analysis += "🟢 <b>قدرت اتحاد:</b> اتحاد قوی با اعضای زیاد\n"
    elif member_count > 2:
        analysis += "🟡 <b>قدرت اتحاد:</b> اتحاد متوسط - پتانسیل رشد\n"
    else:
        analysis += "🔴 <b>قدرت اتحاد:</b> اتحاد کوچک - نیاز به جذب اعضا\n"
    
    # تحلیل نقش کاربر
    if is_leader:
        analysis += "👑 <b>نقش شما:</b> رهبر اتحاد - مسئولیت کامل\n"
    elif is_deputy:
        analysis += "👑 <b>نقش شما:</b> جانشین رهبر - قدرت مدیریتی\n"
    else:
        analysis += "👤 <b>نقش شما:</b> عضو عادی - مشارکت در تصمیمات\n"
    
    # تحلیل هزینه عضویت
    if entry_fee > 1000000:
        analysis += "🟢 <b>هزینه عضویت:</b> بالا - اتحاد انحصاری\n"
    elif entry_fee > 100000:
        analysis += "🟡 <b>هزینه عضویت:</b> متوسط - تعادل مناسب\n"
    else:
        analysis += "🔴 <b>هزینه عضویت:</b> پایین - دسترسی آسان\n"
    
    # توصیه‌های استراتژیک
    analysis += "\n<b>🎯 توصیه‌های استراتژیک:</b>\n"
    
    if member_count < 3:
        analysis += "👥 تلاش برای جذب اعضای جدید\n"
    if is_leader and member_count < 5:
        analysis += "📢 تبلیغ اتحاد برای جذب اعضا\n"
    if not is_leader and not is_deputy:
        analysis += "🤝 مشارکت فعال در فعالیت‌های اتحاد\n"
    
    # وضعیت کلی اتحاد
    alliance_score = (member_count * 5 + (entry_fee // 100000))
    
    if alliance_score > 30:
        analysis += "🏆 <b>🌟 وضعیت کلی:</b> اتحاد برتر جهان\n"
    elif alliance_score > 20:
        analysis += "🥇 <b>💪 وضعیت کلی:</b> اتحاد قوی\n"
    elif alliance_score > 10:
        analysis += "🥈 <b>⚖️ وضعیت کلی:</b> اتحاد متوسط\n"
    else:
        analysis += "🥉 <b>⚠️ وضعیت کلی:</b> نیاز به تقویت اتحاد\n"
    
    return analysis

# تابع تحلیل هوشمند برای کاربران بدون اتحاد
def generate_no_alliance_analysis(user_id):
    analysis = ""
    
    # دریافت اطلاعات کاربر
    user = utils.users.get(user_id, {})
    if not user:
        return "اطلاعات کاربر یافت نشد."
    
    country_name = user.get('country', 'کشور ناشناس')
    
    # بررسی اتحادهای موجود
    available_alliances = len(utils.alliances)
    
    # تحلیل وضعیت اتحادها
    if available_alliances == 0:
        analysis += "🔴 <b>وضعیت اتحادها:</b> هیچ اتحادی وجود ندارد - فرصت ایجاد\n"
    elif available_alliances < 3:
        analysis += "🟡 <b>وضعیت اتحادها:</b> اتحادهای محدود - انتخاب محدود\n"
    else:
        analysis += "🟢 <b>وضعیت اتحادها:</b> تنوع اتحادها - انتخاب مناسب\n"
    
    # تحلیل قدرت اقتصادی کاربر
    resources = user.get('resources', {})
    cash = resources.get('cash', 0)
    
    if cash > 10000000:  # بیش از 10 میلیون
        analysis += "🟢 <b>قدرت اقتصادی:</b> قوی - قابلیت ایجاد اتحاد\n"
    elif cash > 1000000:  # بیش از 1 میلیون
        analysis += "🟡 <b>قدرت اقتصادی:</b> متوسط - قابلیت عضویت\n"
    else:
        analysis += "🔴 <b>قدرت اقتصادی:</b> ضعیف - نیاز به بهبود\n"
    
    # توصیه‌های استراتژیک
    analysis += "\n<b>🎯 توصیه‌های استراتژیک:</b>\n"
    
    if available_alliances == 0:
        analysis += "➕ ایجاد اتحاد جدید برای رهبری\n"
    else:
        analysis += "📋 بررسی اتحادهای موجود برای عضویت\n"
    
    if cash < 1000000:
        analysis += "💰 بهبود وضعیت اقتصادی برای عضویت\n"
    
    analysis += "🤝 تلاش برای ایجاد روابط دیپلماتیک\n"
    
    # وضعیت کلی
    if available_alliances > 0 and cash > 1000000:
        analysis += "🥇 <b>💪 وضعیت کلی:</b> آماده برای عضویت در اتحاد\n"
    elif cash > 10000000:
        analysis += "🥈 <b>⚖️ وضعیت کلی:</b> قابلیت ایجاد اتحاد\n"
    else:
        analysis += "🥉 <b>⚠️ وضعیت کلی:</b> نیاز به بهبود قبل از اتحاد\n"
    
    return analysis

# تابع تحلیل هوشمند بانکی
def generate_bank_analysis(user_id):
    analysis = ""
    
    # دریافت اطلاعات کاربر
    user = utils.users.get(user_id, {})
    if not user:
        return "اطلاعات کاربر یافت نشد."
    
    country_name = user.get('country', 'کشور ناشناس')
    resources = user.get('resources', {})
    cash = resources.get('cash', 0)
    
    # بررسی وام‌های فعال
    active_loans = []
    if user_id in utils.independence_loans:
        loan_data = utils.independence_loans[user_id]
        active_loans.append(loan_data)
    
    # بررسی بدهی‌های معوق
    overdue_debts = utils.overdue_debts.get(user_id, {})
    overdue_count = len(overdue_debts)
    
    # تحلیل وضعیت مالی
    if cash > 10000000:  # بیش از 10 میلیون
        analysis += "🟢 <b>وضعیت مالی:</b> قوی - قابلیت وام‌گیری محدود\n"
    elif cash > 1000000:  # بیش از 1 میلیون
        analysis += "🟡 <b>وضعیت مالی:</b> متوسط - نیاز به وام برای توسعه\n"
    else:
        analysis += "🔴 <b>وضعیت مالی:</b> ضعیف - نیاز فوری به وام\n"
    
    # تحلیل وام‌های فعال
    if active_loans:
        analysis += f"🟡 <b>وام‌های فعال:</b> {len(active_loans)} وام در حال پرداخت\n"
    else:
        analysis += "🟢 <b>وام‌های فعال:</b> بدون وام - آماده برای وام‌گیری\n"
    
    # تحلیل بدهی‌های معوق
    if overdue_count > 0:
        analysis += f"🔴 <b>بدهی‌های معوق:</b> {overdue_count} بدهی معوق - نیاز به پرداخت فوری\n"
    else:
        analysis += "🟢 <b>بدهی‌های معوق:</b> بدون بدهی معوق - وضعیت مطلوب\n"
    
    # توصیه‌های استراتژیک
    analysis += "\n<b>🎯 توصیه‌های استراتژیک:</b>\n"
    
    if cash < 1000000:
        if not active_loans:
            analysis += "💰 درخواست وام توسعه برای بهبود اقتصادی\n"
        else:
            analysis += "💰 درخواست وام اضطراری برای رفع مشکلات مالی\n"
    
    if overdue_count > 0:
        analysis += "⚠️ پرداخت فوری بدهی‌های معوق برای جلوگیری از جریمه\n"
    
    if not active_loans and cash > 5000000:
        analysis += "🏗️ درخواست وام استقلال برای پروژه‌های بزرگ\n"
    
    if active_loans:
        analysis += "📋 برنامه‌ریزی برای پرداخت به موقع وام‌ها\n"
    
    # توصیه نوع وام مناسب
    if cash < 500000:
        analysis += "🚨 وام اضطراری مناسب‌ترین گزینه برای شما\n"
    elif cash < 2000000:
        analysis += "🏗️ وام توسعه برای بهبود زیرساخت‌ها\n"
    else:
        analysis += "💎 وام استقلال برای پروژه‌های بزرگ\n"
    
    # وضعیت کلی مالی
    financial_score = (cash // 1000000) - (overdue_count * 5) - (len(active_loans) * 2)
    
    if financial_score > 10:
        analysis += "🏆 <b>🌟 وضعیت کلی:</b> قدرت مالی برتر\n"
    elif financial_score > 5:
        analysis += "🥇 <b>💪 وضعیت کلی:</b> قدرت مالی قوی\n"
    elif financial_score > 0:
        analysis += "🥈 <b>⚖️ وضعیت کلی:</b> قدرت مالی متوسط\n"
    else:
        analysis += "🥉 <b>⚠️ وضعیت کلی:</b> نیاز به بهبود مالی\n"
    
    return analysis

# تابع تحلیل هوشمند وام‌ها
def generate_loan_analysis(user_id):
    analysis = ""
    
    # دریافت اطلاعات کاربر
    user = utils.users.get(user_id, {})
    if not user:
        return "اطلاعات کاربر یافت نشد."
    
    country_name = user.get('country', 'کشور ناشناس')
    resources = user.get('resources', {})
    cash = resources.get('cash', 0)
    
    # بررسی وام‌های فعال
    active_loan = None
    if user_id in utils.independence_loans:
        active_loan = utils.independence_loans[user_id]
    
    # بررسی بدهی‌های معوق
    overdue_debts = utils.overdue_debts.get(user_id, {})
    overdue_count = len(overdue_debts)
    
    # تحلیل وام فعال
    if active_loan:
        loan_type = active_loan.get('loan_type', 'نامشخص')
        loan_amount = active_loan.get('amount', 0)
        interest_rate = active_loan.get('interest_rate', 0)
        due_turn = active_loan.get('due_turn', 0)
        current_turn = utils.game_data.get('turn', 0)
        remaining_turns = due_turn - current_turn
        
        # تحلیل وضعیت پرداخت
        if remaining_turns > 10:
            analysis += "🟢 <b>وضعیت پرداخت:</b> زمان کافی برای پرداخت\n"
        elif remaining_turns > 5:
            analysis += "🟡 <b>وضعیت پرداخت:</b> نیاز به برنامه‌ریزی\n"
        elif remaining_turns > 0:
            analysis += "🔴 <b>وضعیت پرداخت:</b> زمان محدود - نیاز به اقدام فوری\n"
        else:
            analysis += "🔴 <b>وضعیت پرداخت:</b> معوق - نیاز به پرداخت فوری\n"
        
        # تحلیل نوع وام
        loan_names = {
            'independence': 'وام استقلال',
            'development': 'وام توسعه',
            'emergency': 'وام اضطراری'
        }
        loan_name = loan_names.get(loan_type, loan_type)
        analysis += f"💰 <b>نوع وام:</b> {loan_name} - مبلغ {loan_amount:,} دلار\n"
        
        # تحلیل نرخ بهره
        if interest_rate < 0.1:
            analysis += "🟢 <b>نرخ بهره:</b> پایین - شرایط مطلوب\n"
        elif interest_rate < 0.2:
            analysis += "🟡 <b>نرخ بهره:</b> متوسط - قابل قبول\n"
        else:
            analysis += "🔴 <b>نرخ بهره:</b> بالا - نیاز به بازپرداخت سریع\n"
    else:
        analysis += "🟢 <b>وضعیت وام:</b> بدون وام فعال - آماده برای وام‌گیری\n"
    
    # تحلیل بدهی‌های معوق
    if overdue_count > 0:
        analysis += f"🔴 <b>بدهی‌های معوق:</b> {overdue_count} بدهی معوق - نیاز به پرداخت فوری\n"
    else:
        analysis += "🟢 <b>بدهی‌های معوق:</b> بدون بدهی معوق - وضعیت مطلوب\n"
    
    # توصیه‌های استراتژیک
    analysis += "\n<b>🎯 توصیه‌های استراتژیک:</b>\n"
    
    if active_loan:
        if remaining_turns <= 0:
            analysis += "⚠️ پرداخت فوری وام معوق برای جلوگیری از جریمه\n"
        elif remaining_turns <= 5:
            analysis += "💳 پرداخت زودهنگام برای بخشودگی سود\n"
        else:
            analysis += "📋 برنامه‌ریزی برای پرداخت به موقع\n"
    
    if overdue_count > 0:
        analysis += "🚨 پرداخت فوری بدهی‌های معوق\n"
    
    if not active_loan and cash < 1000000:
        analysis += "💰 درخواست وام جدید برای بهبود اقتصادی\n"
    
    # توصیه نوع وام مناسب
    if not active_loan:
        if cash < 500000:
            analysis += "🚨 وام اضطراری برای رفع مشکلات مالی\n"
        elif cash < 2000000:
            analysis += "🏗️ وام توسعه برای بهبود زیرساخت‌ها\n"
        else:
            analysis += "💎 وام استقلال برای پروژه‌های بزرگ\n"
    
    # وضعیت کلی مالی
    financial_score = (cash // 1000000) - (overdue_count * 5)
    if active_loan:
        financial_score -= 2
    
    if financial_score > 10:
        analysis += "🏆 <b>🌟 وضعیت کلی:</b> قدرت مالی برتر\n"
    elif financial_score > 5:
        analysis += "🥇 <b>💪 وضعیت کلی:</b> قدرت مالی قوی\n"
    elif financial_score > 0:
        analysis += "🥈 <b>⚖️ وضعیت کلی:</b> قدرت مالی متوسط\n"
    else:
        analysis += "🥉 <b>⚠️ وضعیت کلی:</b> نیاز به بهبود مالی\n"
    
    return analysis

# تابع محاسبه قدرت نظامی کل
def calculate_total_military_power(resources):
    ground_power = (resources.get('soldiers', 0) + 
                   resources.get('special_forces', 0) * 5 + 
                   resources.get('tanks', 0) * 10 + 
                   resources.get('armored_vehicles', 0) * 8)
    
    air_power = (resources.get('transport_planes', 0) * 5 + 
                 resources.get('helicopters', 0) * 8 + 
                 resources.get('fighter_jets', 0) * 20 + 
                 resources.get('bombers', 0) * 25 + 
                 resources.get('drones', 0) * 12)
    
    naval_power = (resources.get('speedboats', 0) * 5 + 
                   resources.get('naval_ship', 0) * 15 + 
                   resources.get('submarines', 0) * 20 + 
                   resources.get('aircraft_carriers', 0) * 50)
    
    missile_power = (resources.get('defense_missiles', 0) * 8 + 
                     resources.get('ballistic_missiles', 0) * 30)
    
    return ground_power + air_power + naval_power + missile_power

def calculate_fake_military_power(resources):
    """محاسبه قدرت نظامی غلط برای نمایش عمومی"""
    real_power = calculate_total_military_power(resources)
    
    # اعمال تغییر 20% رندوم (بالاتر یا پایین‌تر)
    import random
    change_percentage = random.uniform(-0.2, 0.2)  # -20% تا +20%
    fake_power = int(real_power * (1 + change_percentage))
    
    return fake_power

def get_real_military_power_message(user_id):
    """پیام قدرت نظامی واقعی برای کاربر"""
    user = utils.users.get(user_id, {})
    if not user:
        return "اطلاعات کاربر یافت نشد."
    
    resources = user.get('resources', {})
    real_power = calculate_total_military_power(resources)
    user_country = user.get('country', 'کشور ناشناس')
    
    # استفاده از ژنرال انتخاب شده
    selected_officials = utils.users.get(user_id, {}).get('selected_officials', {})
    if 'general' in selected_officials:
        general = selected_officials['general']
    else:
        general = {'name': 'ژنرال', 'title': 'ژنرال'}
    
    message = f"🎖️ <b>گزارش محرمانه {general['title']} {general['name']}:</b>\n\n"
    message += f"🌍 {general['name']}: رهبر محترم، قدرت نظامی واقعی {user_country}:\n\n"
    message += f"💪 <b>قدرت کل: {real_power:,} واحد</b>\n\n"
    
    # محاسبه جزئیات
    ground_power = (resources.get('soldiers', 0) + 
                   resources.get('special_forces', 0) * 5 + 
                   resources.get('tanks', 0) * 10 + 
                   resources.get('armored_vehicles', 0) * 8)
    
    air_power = (resources.get('transport_planes', 0) * 5 + 
                 resources.get('helicopters', 0) * 8 + 
                 resources.get('fighter_jets', 0) * 20 + 
                 resources.get('bombers', 0) * 25 + 
                 resources.get('drones', 0) * 12)
    
    naval_power = (resources.get('coastal_artillery', 0) * 10 + 
                   resources.get('speedboats', 0) * 5 + 
                   resources.get('naval_ship', 0) * 15 + 
                   resources.get('submarines', 0) * 20 + 
                   resources.get('aircraft_carriers', 0) * 50)
    
    missile_power = (resources.get('defense_missiles', 0) * 8 + 
                     resources.get('ballistic_missiles', 0) * 30)
    
    message += f"🦶 قدرت زمینی: {ground_power:,} واحد\n"
    message += f"🛩️ قدرت هوایی: {air_power:,} واحد\n"
    message += f"🌊 قدرت دریایی: {naval_power:,} واحد\n"
    message += f"🚀 قدرت موشکی: {missile_power:,} واحد\n\n"
    
    message += f"🎯 {general['name']}: ما توانستیم به خوبی اطلاعات غلط صادر کنیم و دشمنان را در سردرگمی بگذاریم. آمار عمومی که منتشر می‌شود همیشه 20% اختلاف دارد تا هیچکس آمار دقیق ما را نداشته باشد.\n\n"
    message += f"🛡️ {general['name']}: این استراتژی اطلاعاتی باعث می‌شود دشمنان در تصمیم‌گیری‌های خود دچار اشتباه شوند."
    
    return message

# تابع ارسال رتبه‌بندی نظامی جهانی به کانال
async def send_global_military_ranking():
    try:
        from telegram import Bot
        from utils import NEWS_CHANNEL_ID
        
        # محاسبه قدرت نظامی همه کشورها
        military_rankings = []
        
        for user_id, user_data in utils.users.items():
            if not user_data.get('activated', False):
                continue
                
            country_name = user_data.get('country', '')
            if not country_name:
                continue
                
            resources = user_data.get('resources', {})
            
            # محاسبه قدرت کل (استفاده از آمار غلط برای نمایش عمومی)
            total_power = calculate_fake_military_power(resources)
            
            military_rankings.append({
                'country': country_name,
                'power': total_power,
                'user_id': user_id
            })
        
        # مرتب‌سازی بر اساس قدرت
        military_rankings.sort(key=lambda x: x['power'], reverse=True)
        
        # ایجاد متن رتبه‌بندی
        from utils import game_data
        current_date = game_data['game_date']
        ranking_text = f"🏆 <b>رتبه‌بندی نظامی جهانی - {current_date}</b>\n\n"
        
        for i, ranking in enumerate(military_rankings[:10], 1):  # 10 کشور برتر
            country = ranking['country']
            power = ranking['power']
            
            if i == 1:
                ranking_text += f"🥇 <b>{country}</b>: {power:,} واحد قدرت\n"
            elif i == 2:
                ranking_text += f"🥈 <b>{country}</b>: {power:,} واحد قدرت\n"
            elif i == 3:
                ranking_text += f"🥉 <b>{country}</b>: {power:,} واحد قدرت\n"
            else:
                ranking_text += f"{i}. <b>{country}</b>: {power:,} واحد قدرت\n"
        
        # ارسال به کانال اخبار
        from utils import BOT_TOKEN
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=NEWS_CHANNEL_ID,
            text=ranking_text,
            parse_mode='HTML'
        )
        
    except Exception as e:
        print(f"Error sending military ranking: {e}")

# تابع نمایش رتبه‌بندی جهانی برای کاربران
async def show_global_military_ranking(query):
    try:
        # محاسبه قدرت نظامی همه کشورها
        military_rankings = []
        
        for user_id, user_data in utils.users.items():
            if not user_data.get('activated', False):
                continue
                
            country_name = user_data.get('country', '')
            if not country_name:
                continue
                
            resources = user_data.get('resources', {})
            
            # محاسبه قدرت کل (استفاده از آمار غلط برای نمایش عمومی)
            total_power = calculate_fake_military_power(resources)
            
            military_rankings.append({
                'country': country_name,
                'power': total_power,
                'user_id': user_id
            })
        
        # مرتب‌سازی بر اساس قدرت
        military_rankings.sort(key=lambda x: x['power'], reverse=True)
        
        # ایجاد متن رتبه‌بندی
        from utils import game_data
        current_date = game_data['game_date']
        ranking_text = f"🏆 <b>رتبه‌بندی نظامی جهانی - {current_date}</b>\n\n"
        
        for i, ranking in enumerate(military_rankings[:15], 1):  # 15 کشور برتر
            country = ranking['country']
            power = ranking['power']
            
            if i == 1:
                ranking_text += f"🥇 <b>{country}</b>: {power:,} واحد قدرت\n"
            elif i == 2:
                ranking_text += f"🥈 <b>{country}</b>: {power:,} واحد قدرت\n"
            elif i == 3:
                ranking_text += f"🥉 <b>{country}</b>: {power:,} واحد قدرت\n"
            else:
                ranking_text += f"{i}. <b>{country}</b>: {power:,} واحد قدرت\n"
        
        # اضافه کردن اطلاعات کشور کاربر
        user_id = str(query.from_user.id)
        user_country = utils.users.get(user_id, {}).get('country', '')
        user_rank = None
        
        for i, ranking in enumerate(military_rankings):
            if ranking['country'] == user_country:
                user_rank = i + 1
                user_power = ranking['power']
                break
        
        if user_rank:
            ranking_text += f"\n📍 <b>رتبه کشور شما ({user_country}):</b> {user_rank} با {user_power:,} واحد قدرت"
        
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(ranking_text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        print(f"Error showing military ranking: {e}")
        await query.answer("خطا در نمایش رتبه‌بندی", show_alert=True)

# تابع تحلیل اقتصادی
def generate_economic_analysis(user_id, resources, economy):
    analysis = ""
    
    # محاسبه درآمد کل
    total_income = utils.calculate_total_economy(user_id)
    
    # تحلیل منابع
    gold = resources.get('gold', 0)
    steel = resources.get('steel', 0)
    oil = resources.get('oil', 0)
    gas = resources.get('gas', 0)
    electricity = resources.get('electricity', 0)
    
    # تحلیل سازه‌ها (شامل تمام بخش‌های سازه‌ها)
    buildings_count = sum(len(economy.get(section, [])) for section in ['mines', 'farms', 'energy', 'factories', 'production_lines', 'nuclear'])
    
    # تحلیل قدرت اقتصادی
    if total_income > 10000:
        analysis += "🟢 <b>اقتصاد:</b> بسیار قوی - درآمد بالا و پایدار\n"
    elif total_income > 5000:
        analysis += "🟡 <b>اقتصاد:</b> متوسط - نیاز به توسعه دارد\n"
    else:
        analysis += "🔴 <b>اقتصاد:</b> ضعیف - نیاز به سرمایه‌گذاری فوری\n"
    
    # تحلیل منابع استراتژیک
    if gold > 100:
        analysis += "🟢 <b>طلا:</b> ذخایر کافی\n"
    else:
        analysis += "🔴 <b>طلا:</b> نیاز به افزایش ذخایر\n"
    
    if steel > 500:
        analysis += "🟢 <b>فولاد:</b> تولید کافی\n"
    else:
        analysis += "🔴 <b>فولاد:</b> نیاز به افزایش تولید\n"
    
    if oil > 1000:
        analysis += "🟢 <b>نفت:</b> ذخایر انرژی کافی\n"
    else:
        analysis += "🔴 <b>نفت:</b> نیاز به افزایش ذخایر انرژی\n"
    
    # توصیه‌های اقتصادی
    analysis += "\n<b>توصیه‌های اقتصادی:</b>\n"
    
    if total_income < 5000:
        analysis += "▫️ توسعه سازه‌های تولیدی اولویت اول\n"
    if buildings_count < 10:
        analysis += "▫️ ساخت سازه‌های بیشتر ضروری است\n"
    if gold < 100:
        analysis += "▫️ سرمایه‌گذاری در معادن طلا\n"
    if steel < 500:
        analysis += "▫️ توسعه صنعت فولاد\n"
    
    return analysis

# تابع calculate_total_economy در utils.py تعریف شده است

async def send_global_resources_ranking():
    """ارسال آمار منابع جهانی به چنل"""
    try:
        # محاسبه کل منابع هر کاربر
        resources_ranking = []
        total_world_resources = 0
        total_world_cash = 0
        
        for user_id, user_data in utils.users.items():
            if not user_data.get('activated', False):
                continue
                
            resources = user_data.get('resources', {})
            country = user_data.get('country', 'نامشخص')
            
            # محاسبه کل منابع (همه منابع موجود در بازی)
            total_resources = (
                resources.get('iron', 0) +
                resources.get('oil', 0) +
                resources.get('uranium', 0) +
                resources.get('steel', 0) +
                resources.get('aluminum', 0) +
                resources.get('gold', 0) +
                resources.get('copper', 0) +
                resources.get('diamond', 0) +
                resources.get('wheat', 0) +
                resources.get('rice', 0) +
                resources.get('fruits', 0) +
                resources.get('gas', 0) +
                resources.get('electronics', 0) +
                resources.get('pride_cars', 0) +
                resources.get('benz_cars', 0) +
                resources.get('electricity', 0) +
                resources.get('uranium_ore', 0) +
                resources.get('centrifuge', 0) +
                resources.get('yellowcake', 0) +
                resources.get('space_parts', 0) +
                resources.get('titanium', 0)
            )
            
            cash = resources.get('cash', 0)
            total_world_resources += total_resources
            total_world_cash += cash
            
            resources_ranking.append({
                'user_id': user_id,
                'country': country,
                'total_resources': total_resources,
                'cash': cash,
                'resources': resources
            })
        
        # دسته‌بندی کشورها بر اساس منابع
        rich_countries = []  # بیش از 1000 واحد
        medium_countries = []  # 100 تا 1000 واحد
        poor_countries = []  # کمتر از 100 واحد
        
        for country_data in resources_ranking:
            total = country_data['total_resources']
            if total > 1000:
                rich_countries.append(country_data)
            elif total > 100:
                medium_countries.append(country_data)
            else:
                poor_countries.append(country_data)
        
        # دسته‌بندی کشورها بر اساس پول
        rich_cash_countries = []  # بالای 1 بیلیون
        medium_cash_countries = []  # 500 میلیون تا 1 بیلیون
        poor_cash_countries = []  # زیر 500 میلیون
        
        for country_data in resources_ranking:
            cash = country_data['cash']
            if cash > 1000000000:  # 1 بیلیون
                rich_cash_countries.append(country_data)
            elif cash > 500000000:  # 500 میلیون
                medium_cash_countries.append(country_data)
            else:
                poor_cash_countries.append(country_data)
        
        # پیدا کردن بزرگترین دارنده هر منبع
        resource_leaders = {}
        resource_types = {
            'gold': '🥇 طلا',
            'steel': '🔩 فولاد',
            'iron': '⛓️ آهن',
            'copper': '🔧 مس',
            'diamond': '💎 الماس',
            'uranium': '☢️ اورانیوم',
            'wheat': '🌾 گندم',
            'rice': '🍚 برنج',
            'fruits': '🍎 میوه',
            'oil': '🛢️ نفت',
            'gas': '⛽ گاز',
            'electronics': '🔌 الکترونیک',
            'pride_cars': '🚗 پراید',
            'benz_cars': '🚙 بنز',
            'electricity': '⚡ برق',
            'uranium_ore': '🪨 سنگ اورانیوم',
            'centrifuge': '🔄 سانتریفیوژ',
            'yellowcake': '🍰 کیک زرد',
            'space_parts': '🚀 قطعات فضایی',
            'aluminum': '🔧 آلومینیوم',
            'titanium': '🔩 تیتانیوم'
        }
        
        for resource_type, persian_name in resource_types.items():
            max_amount = 0
            leader_country = "هیچ کشور"
            
            for country_data in resources_ranking:
                amount = country_data['resources'].get(resource_type, 0)
                if amount > max_amount:
                    max_amount = amount
                    leader_country = country_data['country']
            
            if max_amount > 0:
                resource_leaders[resource_type] = {
                    'country': leader_country,
                    'amount': max_amount,
                    'persian_name': persian_name
                }
        
        # پیدا کردن بزرگترین دارنده پول
        max_cash = 0
        richest_country = "هیچ کشور"
        for country_data in resources_ranking:
            cash = country_data['cash']
            if cash > max_cash:
                max_cash = cash
                richest_country = country_data['country']
        
        # تابع تبدیل اعداد به شکل تقریبی
        def format_amount(amount):
            if amount >= 1000000000:  # 1 بیلیون
                return f"بالای 1 بیلیون"
            elif amount >= 500000000:  # 500 میلیون
                return f"بالای 500 میلیون"
            else:
                return f"زیر 500 میلیون"
        
        # ایجاد پیام منابع
        current_date = utils.game_data.get('game_date', 'نامشخص')
        message = f"📊 <b>آمار منابع جهانی - {current_date}</b>\n\n"
        message += f"🌍 <b>کل منابع موجود جهان:</b> {total_world_resources:,} واحد\n\n"
        
        message += "📋 <b>دسته‌بندی کشورها:</b>\n"
        message += f"🟢 کشورهای ثروتمند (1000+ واحد): {len(rich_countries)} کشور\n"
        message += f"🟡 کشورهای متوسط (100 تا 1000 واحد): {len(medium_countries)} کشور\n"
        message += f"🔴 کشورهای فقیر (کمتر از 100 واحد): {len(poor_countries)} کشور\n\n"
        
        message += "🏆 <b>بزرگترین دارنده‌های منابع:</b>\n"
        
        for resource_type, leader_info in resource_leaders.items():
            country = leader_info['country']
            persian_name = leader_info['persian_name']
            message += f"▫️ {persian_name}: {country}\n"
        
        # ارسال پیام منابع
        from telegram import Bot
        from utils import BOT_TOKEN, NEWS_CHANNEL_ID
        bot = Bot(token=BOT_TOKEN)
        
        await bot.send_message(
            chat_id=NEWS_CHANNEL_ID,
            text=message,
            parse_mode='HTML'
        )
        
        # مرتب‌سازی کشورها بر اساس پول
        cash_rankings = []
        for country_data in resources_ranking:
            cash = country_data['cash']
            if cash > 0:
                cash_rankings.append({
                    'country': country_data['country'],
                    'cash': cash
                })
        
        # مرتب‌سازی بر اساس پول (نزولی)
        cash_rankings.sort(key=lambda x: x['cash'], reverse=True)
        
        # ایجاد پیام پول
        cash_message = f"💰 <b>آمار پول جهانی - {current_date}</b>\n\n"
        cash_message += f"🌍 <b>کل پول موجود جهان:</b> {total_world_cash:,} واحد\n\n"
        
        cash_message += "📋 <b>دسته‌بندی کشورها:</b>\n"
        cash_message += f"🔴 کشورهای ثروتمند (بالای 1 بیلیون): {len(rich_cash_countries)} کشور\n"
        cash_message += f"🟡 کشورهای متوسط (500 میلیون تا 1 بیلیون): {len(medium_cash_countries)} کشور\n"
        cash_message += f"🟢 کشورهای فقیر (زیر 500 میلیون): {len(poor_cash_countries)} کشور\n\n"
        
        if cash_rankings:
            cash_message += f"🏆 <b>10 کشور ثروتمند:</b>\n"
            for i, ranking in enumerate(cash_rankings[:10], 1):
                country = ranking['country']
                cash = ranking['cash']
                
                if i == 1:
                    cash_message += f"🥇 {country}: {cash:,}\n"
                elif i == 2:
                    cash_message += f"🥈 {country}: {cash:,}\n"
                elif i == 3:
                    cash_message += f"🥉 {country}: {cash:,}\n"
                else:
                    cash_message += f"{i}. {country}: {cash:,}\n"
        
        # ارسال پیام پول
        await bot.send_message(
            chat_id=NEWS_CHANNEL_ID,
            text=cash_message,
            parse_mode='HTML'
        )
        
        print(f"✅ آمار منابع و پول جهانی ارسال شد - {current_date}")
        
    except Exception as e:
        print(f"❌ خطا در ارسال آمار منابع جهانی: {e}")

async def show_global_resources_ranking(query):
    """نمایش آمار منابع جهانی به کاربر"""
    try:
        # محاسبه کل منابع هر کاربر
        resources_ranking = []
        total_world_resources = 0
        total_world_cash = 0
        
        for user_id, user_data in utils.users.items():
            if not user_data.get('activated', False):
                continue
                
            resources = user_data.get('resources', {})
            country = user_data.get('country', 'نامشخص')
            
            # محاسبه کل منابع (همه منابع موجود در بازی)
            total_resources = (
                resources.get('iron', 0) +
                resources.get('oil', 0) +
                resources.get('uranium', 0) +
                resources.get('steel', 0) +
                resources.get('aluminum', 0) +
                resources.get('gold', 0) +
                resources.get('copper', 0) +
                resources.get('diamond', 0) +
                resources.get('wheat', 0) +
                resources.get('rice', 0) +
                resources.get('fruits', 0) +
                resources.get('gas', 0) +
                resources.get('electronics', 0) +
                resources.get('pride_cars', 0) +
                resources.get('benz_cars', 0) +
                resources.get('electricity', 0) +
                resources.get('uranium_ore', 0) +
                resources.get('centrifuge', 0) +
                resources.get('yellowcake', 0) +
                resources.get('space_parts', 0) +
                resources.get('titanium', 0)
            )
            
            cash = resources.get('cash', 0)
            total_world_resources += total_resources
            total_world_cash += cash
            
            resources_ranking.append({
                'user_id': user_id,
                'country': country,
                'total_resources': total_resources,
                'cash': cash,
                'resources': resources
            })
        
        # دسته‌بندی کشورها بر اساس منابع
        rich_countries = []  # بیش از 1000 واحد
        medium_countries = []  # 100 تا 1000 واحد
        poor_countries = []  # کمتر از 100 واحد
        
        for country_data in resources_ranking:
            total = country_data['total_resources']
            if total > 1000:
                rich_countries.append(country_data)
            elif total > 100:
                medium_countries.append(country_data)
            else:
                poor_countries.append(country_data)
        
        # دسته‌بندی کشورها بر اساس پول
        rich_cash_countries = []  # بالای 1 بیلیون
        medium_cash_countries = []  # 500 میلیون تا 1 بیلیون
        poor_cash_countries = []  # زیر 500 میلیون
        
        for country_data in resources_ranking:
            cash = country_data['cash']
            if cash > 1000000000:  # 1 بیلیون
                rich_cash_countries.append(country_data)
            elif cash > 500000000:  # 500 میلیون
                medium_cash_countries.append(country_data)
            else:
                poor_cash_countries.append(country_data)
        
        # پیدا کردن بزرگترین دارنده هر منبع
        resource_leaders = {}
        resource_types = {
            'gold': '🥇 طلا',
            'steel': '🔩 فولاد',
            'iron': '⛓️ آهن',
            'copper': '🔧 مس',
            'diamond': '💎 الماس',
            'uranium': '☢️ اورانیوم',
            'wheat': '🌾 گندم',
            'rice': '🍚 برنج',
            'fruits': '🍎 میوه',
            'oil': '🛢️ نفت',
            'gas': '⛽ گاز',
            'electronics': '🔌 الکترونیک',
            'pride_cars': '🚗 پراید',
            'benz_cars': '🚙 بنز',
            'electricity': '⚡ برق',
            'uranium_ore': '🪨 سنگ اورانیوم',
            'centrifuge': '🔄 سانتریفیوژ',
            'yellowcake': '🍰 کیک زرد',
            'space_parts': '🚀 قطعات فضایی',
            'aluminum': '🔧 آلومینیوم',
            'titanium': '🔩 تیتانیوم'
        }
        
        for resource_type, persian_name in resource_types.items():
            max_amount = 0
            leader_country = "هیچ کشور"
            
            for country_data in resources_ranking:
                amount = country_data['resources'].get(resource_type, 0)
                if amount > max_amount:
                    max_amount = amount
                    leader_country = country_data['country']
            
            if max_amount > 0:
                resource_leaders[resource_type] = {
                    'country': leader_country,
                    'amount': max_amount,
                    'persian_name': persian_name
                }
        
        # پیدا کردن بزرگترین دارنده پول
        max_cash = 0
        richest_country = "هیچ کشور"
        for country_data in resources_ranking:
            cash = country_data['cash']
            if cash > max_cash:
                max_cash = cash
                richest_country = country_data['country']
        
        # تابع تبدیل اعداد به شکل تقریبی
        def format_amount(amount):
            if amount >= 1000000000:  # 1 بیلیون
                return f"بالای 1 بیلیون"
            elif amount >= 500000000:  # 500 میلیون
                return f"بالای 500 میلیون"
            else:
                return f"زیر 500 میلیون"
        
        # پیدا کردن رتبه کاربر فعلی
        current_user_id = str(query.from_user.id)
        user_rank = 0
        user_total = 0
        user_cash = 0
        for i, country_data in enumerate(resources_ranking, 1):
            if country_data['user_id'] == current_user_id:
                user_rank = i
                user_total = country_data['total_resources']
                user_cash = country_data['cash']
                break
        
        # ایجاد پیام منابع
        current_date = utils.game_data.get('game_date', 'نامشخص')
        message = f"📊 <b>آمار منابع جهانی - {current_date}</b>\n\n"
        message += f"🌍 <b>کل منابع موجود جهان:</b> {total_world_resources:,} واحد\n\n"
        
        message += "📋 <b>دسته‌بندی کشورها:</b>\n"
        message += f"🟢 کشورهای ثروتمند (1000+ واحد): {len(rich_countries)} کشور\n"
        message += f"🟡 کشورهای متوسط (100 تا 1000 واحد): {len(medium_countries)} کشور\n"
        message += f"🔴 کشورهای فقیر (کمتر از 100 واحد): {len(poor_countries)} کشور\n\n"
        
        message += "🏆 <b>بزرگترین دارنده‌های منابع:</b>\n"
        
        for resource_type, leader_info in resource_leaders.items():
            country = leader_info['country']
            persian_name = leader_info['persian_name']
            message += f"▫️ {persian_name}: {country}\n"
        
        # اضافه کردن آمار پول
        message += f"\n💰 <b>آمار پول جهانی:</b>\n"
        message += f"🌍 <b>کل پول موجود جهان:</b> {total_world_cash:,} واحد\n\n"
        
        message += "📋 <b>دسته‌بندی کشورها:</b>\n"
        message += f"🔴 کشورهای ثروتمند (بالای 1 بیلیون): {len(rich_cash_countries)} کشور\n"
        message += f"🟡 کشورهای متوسط (500 میلیون تا 1 بیلیون): {len(medium_cash_countries)} کشور\n"
        message += f"🟢 کشورهای فقیر (زیر 500 میلیون): {len(poor_cash_countries)} کشور\n\n"
        
        # مرتب‌سازی کشورها بر اساس پول
        cash_rankings = []
        for country_data in resources_ranking:
            cash = country_data['cash']
            if cash > 0:
                cash_rankings.append({
                    'country': country_data['country'],
                    'cash': cash
                })
        
        # مرتب‌سازی بر اساس پول (نزولی)
        cash_rankings.sort(key=lambda x: x['cash'], reverse=True)
        
        if cash_rankings:
            message += f"🏆 <b>10 کشور ثروتمند:</b>\n"
            for i, ranking in enumerate(cash_rankings[:10], 1):
                country = ranking['country']
                cash = ranking['cash']
                
                if i == 1:
                    message += f"🥇 {country}: {cash:,}\n"
                elif i == 2:
                    message += f"🥈 {country}: {cash:,}\n"
                elif i == 3:
                    message += f"🥉 {country}: {cash:,}\n"
                else:
                    message += f"{i}. {country}: {cash:,}\n"
        
        # نمایش اطلاعات کاربر
        if user_rank > 0:
            message += f"\n📍 <b>وضعیت کشور شما:</b>\n"
            message += f"▫️ منابع: رتبه {user_rank} از {len(resources_ranking)} با {user_total:,} واحد\n"
            message += f"▫️ پول: {format_amount(user_cash)}"
        else:
            message += f"\n📍 <b>وضعیت کشور شما:</b> در لیست نیست"
        
        keyboard = [[InlineKeyboardButton('بازگشت ⬅️', callback_data='strategy')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        print(f"❌ خطا در نمایش آمار منابع جهانی: {e}")
        await query.answer("❌ خطا در بارگذاری آمار منابع")

# تابع تحلیل هوشمند وضعیت کشور
def generate_country_status_analysis(user_id, resources, economy, total_economy, cash):
    """تحلیل هوشمند وضعیت کلی کشور"""
    analysis = ""
    
    # محاسبه کل منابع (بدون پول)
    total_resources = sum(val for key, val in resources.items() if key != 'cash')
    
    # تحلیل قدرت اقتصادی
    if total_economy > 50000:
        analysis += "🟢 <b>💰 اقتصاد:</b> بسیار قوی - درآمد بالا و پایدار\n"
    elif total_economy > 20000:
        analysis += "🟡 <b>💰 اقتصاد:</b> قوی - نیاز به توسعه بیشتر\n"
    elif total_economy > 10000:
        analysis += "🟡 <b>💰 اقتصاد:</b> متوسط - نیاز به سرمایه‌گذاری\n"
    else:
        analysis += "🔴 <b>💰 اقتصاد:</b> ضعیف - نیاز به تقویت فوری\n"
    
    # تحلیل منابع استراتژیک
    gold = resources.get('gold', 0)
    steel = resources.get('steel', 0)
    oil = resources.get('oil', 0)
    uranium = resources.get('uranium', 0)
    diamond = resources.get('diamond', 0)
    
    if gold > 500:
        analysis += "🟢 <b>🥇 طلا:</b> ذخایر کافی و امن\n"
    elif gold > 100:
        analysis += "🟡 <b>🥇 طلا:</b> نیاز به افزایش ذخایر\n"
    else:
        analysis += "🔴 <b>🥇 طلا:</b> نیاز به سرمایه‌گذاری فوری\n"
    
    if steel > 1000:
        analysis += "🟢 <b>🔩 فولاد:</b> تولید صنعتی قوی\n"
    elif steel > 500:
        analysis += "🟡 <b>🔩 فولاد:</b> تولید متوسط\n"
    else:
        analysis += "🔴 <b>🔩 فولاد:</b> نیاز به توسعه صنعت\n"
    
    if oil > 2000:
        analysis += "🟢 <b>🛢️ نفت:</b> ذخایر انرژی عالی\n"
    elif oil > 1000:
        analysis += "🟡 <b>🛢️ نفت:</b> ذخایر انرژی کافی\n"
    else:
        analysis += "🔴 <b>🛢️ نفت:</b> نیاز به افزایش ذخایر انرژی\n"
    
    if uranium > 100:
        analysis += "🟢 <b>☢️ اورانیوم:</b> قابلیت هسته‌ای\n"
    elif uranium > 50:
        analysis += "🟡 <b>☢️ اورانیوم:</b> ذخایر متوسط\n"
    else:
        analysis += "🔴 <b>☢️ اورانیوم:</b> نیاز به توسعه هسته‌ای\n"
    
    if diamond > 200:
        analysis += "🟢 <b>💎 الماس:</b> ثروت معدنی بالا\n"
    elif diamond > 50:
        analysis += "🟡 <b>💎 الماس:</b> ذخایر متوسط\n"
    else:
        analysis += "🔴 <b>💎 الماس:</b> نیاز به توسعه معادن\n"
    
    # تحلیل سازه‌ها
    total_buildings = sum(len(economy.get(section, [])) for section in ['mines', 'farms', 'energy', 'factories', 'military'])
    
    if total_buildings > 20:
        analysis += "🟢 <b>🏗️ سازه‌ها:</b> زیرساخت پیشرفته\n"
    elif total_buildings > 10:
        analysis += "🟡 <b>🏗️ سازه‌ها:</b> زیرساخت متوسط\n"
    else:
        analysis += "🔴 <b>🏗️ سازه‌ها:</b> نیاز به ساخت سازه‌های بیشتر\n"
    
    # تحلیل پول نقد
    if cash > 1000000000:  # 1 بیلیون
        analysis += "🟢 <b>💵 نقدینگی:</b> بسیار ثروتمند\n"
    elif cash > 500000000:  # 500 میلیون
        analysis += "🟡 <b>💵 نقدینگی:</b> ثروتمند\n"
    elif cash > 100000000:  # 100 میلیون
        analysis += "🟡 <b>💵 نقدینگی:</b> متوسط\n"
    else:
        analysis += "🔴 <b>💵 نقدینگی:</b> نیاز به افزایش سرمایه\n"
    
    # توصیه‌های استراتژیک
    analysis += "\n<b>🎯 توصیه‌های استراتژیک:</b>\n"
    
    if total_economy < 20000:
        analysis += "💰 توسعه سازه‌های تولیدی اولویت اول\n"
    if total_buildings < 10:
        analysis += "🏗️ ساخت سازه‌های بیشتر ضروری است\n"
    if gold < 100:
        analysis += "🥇 سرمایه‌گذاری در معادن طلا\n"
    if steel < 500:
        analysis += "🔩 توسعه صنعت فولاد\n"
    if oil < 1000:
        analysis += "🛢️ افزایش ذخایر انرژی\n"
    if cash < 100000000:
        analysis += "💵 افزایش سرمایه‌گذاری اقتصادی\n"
    if uranium < 50:
        analysis += "☢️ توسعه برنامه هسته‌ای\n"
    
    # رتبه‌بندی کلی
    score = 0
    if total_economy > 50000: score += 3
    elif total_economy > 20000: score += 2
    elif total_economy > 10000: score += 1
    
    if total_buildings > 20: score += 3
    elif total_buildings > 10: score += 2
    elif total_buildings > 5: score += 1
    
    if cash > 1000000000: score += 3
    elif cash > 500000000: score += 2
    elif cash > 100000000: score += 1
    
    if gold > 500: score += 2
    elif gold > 100: score += 1
    
    if steel > 1000: score += 2
    elif steel > 500: score += 1
    
    if oil > 2000: score += 2
    elif oil > 1000: score += 1
    
    if uranium > 100: score += 2
    elif uranium > 50: score += 1
    
    if diamond > 200: score += 2
    elif diamond > 50: score += 1
    
    # امتیاز کل: حداکثر 20
    if score >= 16:
        analysis += "\n🏆 <b>🌟 وضعیت کلی:</b> قدرت برتر جهان\n"
    elif score >= 12:
        analysis += "\n🥇 <b>💪 وضعیت کلی:</b> قدرت قوی\n"
    elif score >= 8:
        analysis += "\n🥈 <b>⚖️ وضعیت کلی:</b> قدرت متوسط\n"
    elif score >= 4:
        analysis += "\n🥉 <b>⚠️ وضعیت کلی:</b> قدرت ضعیف\n"
    else:
        analysis += "\n🔴 <b>🚨 وضعیت کلی:</b> نیاز به تقویت فوری\n"
    
    return analysis

# تابع تست ارسال گزارش‌ها
async def test_send_reports():
    """تست ارسال تمام گزارش‌ها"""
    try:
        from telegram import Bot
        from utils import BOT_TOKEN, NEWS_CHANNEL_ID
        
        bot = Bot(token=BOT_TOKEN)
        
        # تست ارسال رتبه‌بندی نظامی
        print("🔄 تست ارسال رتبه‌بندی نظامی...")
        await send_global_military_ranking()
        print("✅ رتبه‌بندی نظامی ارسال شد")
        
        # تست ارسال گزارش اقتصادی
        print("🔄 تست ارسال گزارش اقتصادی...")
        from jame import send_economy_report_to_channel
        await send_economy_report_to_channel(bot)
        print("✅ گزارش اقتصادی ارسال شد")
        
        # تست ارسال گزارش جمعیت
        print("🔄 تست ارسال گزارش جمعیت...")
        from jame import send_population_report_to_channel
        await send_population_report_to_channel(bot)
        
        # تست ارسال آمار منابع جهانی
        print("🔄 تست ارسال آمار منابع جهانی...")
        await send_global_resources_ranking()
        print("✅ آمار منابع جهانی ارسال شد")
        print("✅ گزارش جمعیت ارسال شد")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست ارسال گزارش‌ها: {e}")
        return False 