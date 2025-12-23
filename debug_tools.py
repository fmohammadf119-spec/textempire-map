from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import utils
import random


def _count_users():
	all_users = utils.users or {}
	activated = sum(1 for u in all_users.values() if u.get('activated'))
	return len(all_users), activated


def _get_active_user_ids():
	return [uid for uid, u in utils.users.items() if u.get('activated') and u.get('country')]


async def show_debug_menu(query):
	text = "🧪 <b>پنل دیباگ ادمین</b>\n\nگزینه مورد نظر را انتخاب کنید:"
	keyboard = [
		[InlineKeyboardButton('📊 خلاصه وضعیت', callback_data='dbg_summary')],
		[InlineKeyboardButton('👥 تضمین حداقل ۲ کاربر فعال', callback_data='dbg_ensure_two')],
		[InlineKeyboardButton('⚔️ ساخت جنگ تست با نزدیک‌ترین کشور', callback_data='dbg_make_war')],
		[InlineKeyboardButton('🔥 انقلاب ۱۰۰٪ (سقوط تست)', callback_data='dbg_revolution_100')],
		[InlineKeyboardButton('💀 مرگ ژنرال', callback_data='dbg_kill_general'), InlineKeyboardButton('💀 مرگ وزیر کشور', callback_data='dbg_kill_minister')],
		[InlineKeyboardButton('💚 احیای ژنرال', callback_data='dbg_revive_general'), InlineKeyboardButton('💚 احیای وزیر کشور', callback_data='dbg_revive_minister')],
		[InlineKeyboardButton('🔙 بازگشت', callback_data='back_to_main')],
	]
	await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


async def dbg_summary(query):
	total, active = _count_users()
	wars = len(getattr(utils, 'war_declarations', {}) or {})
	alliances = len(getattr(utils, 'alliances', {}) or {})
	text = (
		"📊 <b>خلاصه سیستم</b>\n\n"
		f"• کل کاربران: {total}\n"
		f"• کاربران فعال: {active}\n"
		f"• جنگ‌های ثبت‌شده: {wars}\n"
		f"• اتحادها: {alliances}"
	)
	keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='admin_debug')]]
	await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


async def dbg_ensure_two(query):
	active_ids = _get_active_user_ids()
	if len(active_ids) >= 2:
		text = "✅ حداقل دو کاربر فعال موجود است."
	else:
		# تلاش برای فعال کردن یا ساخت یک کاربر تست دوم
		new_id = None
		for i in range(10000, 20000):
			if str(i) not in utils.users:
				new_id = str(i)
				break
		if new_id is None:
			text = "❌ نتوانستم کاربر تست ایجاد کنم."
		else:
			utils.users[new_id] = {
				'activated': True,
				'country': f'کشور تست {new_id}',
				'player_name': f'Test {new_id}',
				'government_title': 'رهبر',
				'resources': {'cash': 1_000_000_000},
			}
			try:
				utils.save_users()
			except Exception:
				pass
			text = f"✅ کاربر فعال تست ساخته شد: {new_id}"
	keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='admin_debug')]]
	await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


async def dbg_make_war(query, user_id: str):
	user_country = utils.users.get(user_id, {}).get('country')
	others = [uid for uid in _get_active_user_ids() if uid != user_id]
	if not user_country or not others:
		text = "❌ نیاز به حداقل دو کشور فعال است."
	else:
		target_id = random.choice(others)
		target_country = utils.users.get(target_id, {}).get('country')
		if not target_country:
			text = "❌ کشور هدف نامعتبر است."
		else:
			# ساخت جنگ ساده
			war_id = f"war_{random.randint(1000, 999999)}"
			w = {
				'id': war_id,
				'attacker': user_country,
				'defender': target_country,
				'created_at': utils.game_data.get('turn', 1),
				'created_by': user_id,
				'created_target': target_id,
				'created_reason': 'debug',
				'created_public': False,
				'type': 'ground',
				'level': 'normal',
				'location': 'border',
				'nearby': True,
				'weather': 'normal',
				'fiat': True,
				'consent': True,
				'from': user_country,
				'to': target_country,
				'turn_declared': utils.game_data.get('turn', 1),
				'status': 'active'
			}
			utils.war_declarations[war_id] = w
			try:
				if hasattr(utils, 'save_war_declarations'):
					utils.save_war_declarations()
			except Exception:
				pass
			# پخش پیشنهاد پناهندگی برای تست
			try:
				from bot import broadcast_refugee_offers
				import asyncio
				await broadcast_refugee_offers(war_id, user_country, target_country)
			except Exception:
				pass
			text = f"✅ جنگ تست بین {user_country} و {target_country} ساخته شد."
	keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='admin_debug')]]
	await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


def _set_official_alive(user_id: str, role_key: str, alive: bool):
	user = utils.users.get(user_id, {})
	sel = user.setdefault('selected_officials', {})
	role = sel.setdefault(role_key, {'name': role_key, 'title': role_key})
	role['alive'] = alive
	utils.save_users()


async def dbg_revolution_100(query, user_id: str):
	user = utils.users.get(user_id, {})
	user['revolution'] = 100
	utils.save_users()
	try:
		from utils import handle_country_collapse
		await handle_country_collapse(user_id)
	except Exception:
		pass
	keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='admin_debug')]]
	await query.edit_message_text('🔥 انقلاب روی ۱۰۰٪ تنظیم شد و روال سقوط فراخوانی شد.', reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


async def dbg_toggle_official(query, user_id: str, role_key: str, alive: bool):
	_set_official_alive(user_id, role_key, alive)
	state = 'زنده' if alive else 'کشته'
	keyboard = [[InlineKeyboardButton('🔙 بازگشت', callback_data='admin_debug')]]
	await query.edit_message_text(f'✅ وضعیت {role_key} به «{state}» تغییر کرد.', reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')


