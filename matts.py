from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import utils
from utils import MILITARY_TECH_LIST, save_users
import sys
import utils
print("[DEBUG] UTILS ID:", id(sys.modules['utils']))
# نمایش منوی فناوری نظامی

def upgrade_technology(user_id, tech_key):
    user_techs = utils.military_technologies.get(user_id, {})
    current_level = user_techs.get(tech_key, 0)
    max_level = next((tech['max_level'] for tech in utils.MILITARY_TECH_LIST if tech['key'] == tech_key), 0)
    
    if current_level < max_level:
        user_techs[tech_key] = current_level + 1
        utils.military_technologies[user_id] = user_techs
        utils.save_military_technologies()  # تابعی برای ذخیره تغییرات در فایل
        return True
    return False
async def show_military_tech_menu(query, user_id):
    user_id_str = str(user_id)
    user_techs = utils.military_technologies.get(user_id_str, {})
    keyboard = []
    for tech in MILITARY_TECH_LIST:
        level = user_techs.get(tech["key"], 0)
        max_level = tech["max_level"]
        price = tech["upgrade_price"]
        name = tech["name"]
        
        # نمایش قیمت و اورانیوم (اگر نیاز باشد)
        price_text = f"{name} | قیمت ارتقا: {price//1_000_000}m"
        if "uranium" in tech:
            price_text += f" + {tech['uranium']} اورانیوم"
        
        # دکمه نمایش نام و قیمت
        keyboard.append([InlineKeyboardButton(price_text, callback_data=f"show_tech_{tech['key']}")])
        
        # دکمه لول و ارتقا
        if level < max_level:
            keyboard.append([
                InlineKeyboardButton(f"لول {level}/{max_level}", callback_data=f"upgrade_tech_{tech['key']}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(f"لول {level}/{max_level} (حداکثر)", callback_data="maxed_tech")
            ])
    keyboard.append([InlineKeyboardButton('بازگشت ⬅️', callback_data='technology')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('فناوری‌های نظامی:', reply_markup=reply_markup)

# ارتقا فناوری نظامی
async def upgrade_military_tech(query, user_id, tech_key):
    user_id_str = str(user_id)
    user_techs = utils.military_technologies.setdefault(user_id_str, {})
    tech = next((t for t in MILITARY_TECH_LIST if t["key"] == tech_key), None)
    if not tech:
        await query.answer("فناوری یافت نشد!", show_alert=True)
        return
    
    level = user_techs.get(tech_key, 0)
    max_level = tech["max_level"]
    price = tech["upgrade_price"]
    
    print(f"[DEBUG] upgrade_military_tech: user_id={user_id}, user_id_str={user_id_str}, tech_key={tech_key}, current_level={level}")
    print(f"[DEBUG] military_technologies keys: {list(utils.military_technologies.keys())}")
    
    if level >= max_level:
        await query.answer("این فناوری به حداکثر لول رسیده است!", show_alert=True)
        return
    
    user = utils.users.get(user_id_str, {})
    resources = user.get("resources", {})
    
    # بررسی موجودی نقد
    if resources.get("cash", 0) < price:
        await query.answer("موجودی نقد کافی نیست!", show_alert=True)
        return
    
    # بررسی اورانیوم (برای بمب اتم)
    if "uranium" in tech:
        uranium_needed = tech["uranium"]
        if resources.get("uranium", 0) < uranium_needed:
            await query.answer(f"اورانیوم کافی نیست! نیاز: {uranium_needed}", show_alert=True)
            return
    
    # کسر منابع
    resources["cash"] -= price
    if "uranium" in tech:
        resources["uranium"] -= tech["uranium"]
    
    # ارتقا لول
    user_techs[tech_key] = level + 1
    
    print(f"[DEBUG] Upgraded {tech_key} to level {level + 1}")
    print(f"[DEBUG] military_technologies before save: {utils.military_technologies}")
    
    # اعمال منطق خاص بر اساس نوع فناوری
    await apply_tech_logic(user_id_str, tech_key, level + 1)
    
    utils.save_military_technologies()
    save_users()
    
    print(f"[DEBUG] military_technologies after save: {utils.military_technologies}")
    
    await query.answer("ارتقا با موفقیت انجام شد!", show_alert=True)
    await show_military_tech_menu(query, user_id)

# اعمال منطق خاص برای هر فناوری
async def apply_tech_logic(user_id, tech_key, new_level):
    user = utils.users.get(user_id, {})
    military = user.get("military", {})
    resources = user.get("resources", {})
    
    # منطق برای سربازان و تجهیزات نظامی (افزایش قدرت)
    military_units = [
        "soldiers", "special_forces", "tanks", "armored_vehicles", 
        "transport_planes", "helicopters", "fighter_jets", "bombers",
        "artillery", "drones", "air_defense", "coastal_artillery",
        "speedboats", "naval_ship", "submarines", "aircraft_carriers",
        "war_robots"
    ]
    
    if tech_key in military_units:
        # افزایش قدرت واحدهای نظامی بر اساس لول
        power_multiplier = 1 + (new_level * 0.1)  # هر لول 10% قدرت اضافه می‌کند
        military[f"{tech_key}_power"] = power_multiplier
        military[f"{tech_key}_level"] = new_level
    
    # منطق برای موشک‌ها (تنظیم لول - تعداد در هر دور اضافه می‌شود)
    missile_types = ["ballistic_missiles", "defense_missiles"]
    if tech_key in missile_types:
        # فقط لول ذخیره می‌شود - تعداد در هر دور بر اساس لول اضافه می‌شود
        military[f"{tech_key}_level"] = new_level
    
    # منطق برای بمب‌ها (قفل تا max - فعلاً فقط لول ذخیره می‌شود)
    bomb_types = ["hydrogen_bomb", "chemical_bomb", "destructive_bomb", "atomic_bomb"]
    if tech_key in bomb_types:
        military[f"{tech_key}_level"] = new_level
        # در آینده می‌توان برای استفاده در جنگ اضافه کرد
    
    # ذخیره تغییرات
    user["military"] = military
    user["resources"] = resources
    utils.users[user_id] = user


