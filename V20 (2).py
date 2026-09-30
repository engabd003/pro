from pyrogram import Client, filters, enums, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from pyrogram.errors import FloodWait, SessionPasswordNeeded, PhoneCodeInvalid, PasswordHashInvalid, PhoneNumberInvalid
from kvsqlite.sync import Client as DB
from datetime import date, datetime, timedelta
import asyncio
import traceback
import re
import os
import zipfile
import io
import shutil
import sys
import time
import tempfile
import qrcode
import secrets
import string
from PIL import Image
try:
    from pyzbar.pyzbar import decode as decode_qr
except ImportError:
    decode_qr = None

# Bot configuration
token = "7619192158:AAHSPdk1vLhsNSK-iePeI72gdIY9sZncDiw"
ownerID = int("7329179992")

# Database initialization
botdb = DB('botdb.sqlite')

# Bot client initialization
bot = Client("kkboty1",

             api_id=22935081,
             api_hash="ba799aab933aad0d41231f5112deb323",
             bot_token=token)

# Session clients pool
session_clients = []
current_session_index = 0
session_meta = []  # parallel metadata for session_clients: dicts with usage, banned, name, flood_until

# Admin panel keyboard
STARTKEY = InlineKeyboardMarkup(
    [[InlineKeyboardButton("≈ إذاعة للمستخدمين ≈", callback_data="broadcast")],
     [
         InlineKeyboardButton("≈ الاحصائيات ≈", callback_data="stats"),
         InlineKeyboardButton("≈ الأدمنية ≈", callback_data="adminstats"),
         InlineKeyboardButton("≈ المحظورين ≈", callback_data="bannedstats"),
     ],
     [
         InlineKeyboardButton("≈ كشف مستخدم ≈", callback_data="whois"),
         InlineKeyboardButton("≈ حظر مستخدم ≈", callback_data="ban"),
     ], [
         InlineKeyboardButton("≈ الغاء حظر مستخدم ≈", callback_data="unban"),
     ],
     [
         InlineKeyboardButton("≈ رفع ادمن ≈", callback_data="addadmin"),
         InlineKeyboardButton("≈ تنزيل ادمن ≈", callback_data="remadmin"),
     ],
     [
         InlineKeyboardButton("≈ إدارة القنوات ≈", callback_data="channels"),
         InlineKeyboardButton("≈ VIP ≈", callback_data="vip"),
     ],
     [
         InlineKeyboardButton("≈ الإحالة ≈", callback_data="referral"),
         InlineKeyboardButton("🔥 ترند الدعوات 🔥", callback_data="referral_trend"),
         InlineKeyboardButton("≈ رسالة الترحيب ≈",
                              callback_data="welcome_msg"),
     ],
     [
         InlineKeyboardButton("≈ المحاولات اليومية ≈",
                              callback_data="daily_attempts"),
         InlineKeyboardButton("⏱️ إعدادات السليب",
                              callback_data="sleep_settings"),
     ],
     [
         InlineKeyboardButton("🔧 حالة الصيانة",
                              callback_data="maintenance_mode"),
         InlineKeyboardButton("🎨 الأزرار المخصصة",
                              callback_data="custom_buttons"),
     ],
     [
         InlineKeyboardButton("💎 نظام النقاط", callback_data="points_system"),
         InlineKeyboardButton("🔐 إدارة الجلسات",
                              callback_data="sessions_management"),
     ],
     [
         InlineKeyboardButton("� نظام التمويل",
                              callback_data="funding_management"),
         InlineKeyboardButton("🎁 مكافآت الاشتراك",
                              callback_data="subscription_rewards"),
     ],
     [
         InlineKeyboardButton("🛡️ إعدادات السبام",
                              callback_data="spam_settings"),
     ],
     [
         InlineKeyboardButton("🚫 الكلمات الممنوعة",
                              callback_data="banned_words_management"),
         InlineKeyboardButton("📊 إدارة الاستطلاع",
                              callback_data="poll_management"),
     ],
     [
         InlineKeyboardButton("🎛️ إدارة الأزرار",
                              callback_data="buttons_visibility_management"),
     ],
     [
         InlineKeyboardButton("🎫 أكواد VIP",
                              callback_data="vip_codes_management"),
         InlineKeyboardButton("📦 تصدير البيانات",
                              callback_data="export_data"),
     ],
     [
         InlineKeyboardButton("🗑️ حذف المحتوى",
                              callback_data="auto_delete_management"),
         InlineKeyboardButton("➕ تسجيل دخول جلسة جديدة",
                              callback_data="start_login_session"),
     ],
     [
         InlineKeyboardButton("≈ استخدام البوت ≈", callback_data="usebot"),
         InlineKeyboardButton("🔄 تحديث البوت", callback_data="update_bot"),
     ]])

# VIP Keyboard
VIP_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("📥 تحميل ستوري واحد", callback_data="single_story")],
    [
        InlineKeyboardButton("📥 تحميل جميع الستوريات دفعة واحدة",
                             callback_data="download_all_stories")
    ],
    [
        InlineKeyboardButton("👤 جلب معلومات الحساب",
                             callback_data="download_profile")
    ],
    [
        InlineKeyboardButton("📡 مراقبة الستوريات",
                             callback_data="story_monitoring")
    ], 
    [InlineKeyboardButton("🎁 تبرع بجلسة/كود", callback_data="donate_session")],
    [InlineKeyboardButton("🎫 أرسل كود الاشتراك", callback_data="enter_vip_code")],
    [InlineKeyboardButton("• معلوماتي •", callback_data="my_info")],
    [InlineKeyboardButton("📧 تواصل مع المطور", callback_data="developer")]
])


# Regular user keyboard - will be generated dynamically with custom buttons
def get_regular_keyboard():
    data = botdb.get("db" + token.split(":")[0])
    custom_buttons = data.get("custom_buttons", [])
    visible_buttons = data.get("visible_buttons", {
        "my_info": True,
        "my_points": True,
        "donate_session": True,
        "request_vip": True,
        "developer": True,
        "poll": True,
        "enter_vip_code": True
    })

    buttons = []
    
    # معلوماتي
    if visible_buttons.get("my_info", True):
        buttons.append([
            InlineKeyboardButton(text="• معلوماتي •", callback_data="my_info")
        ])
    
    # نقاطي
    if visible_buttons.get("my_points", True):
        buttons.append([
            InlineKeyboardButton(text="💎 نقاطي", callback_data="my_points")
        ])
    
    # تبرع بجلسة/كود
    if visible_buttons.get("donate_session", True):
        buttons.append([
            InlineKeyboardButton(text="🎁 تبرع بجلسة/كود",
                                callback_data="donate_session")
        ])
    
    # طلب اشتراك VIP
    if visible_buttons.get("request_vip", True):
        buttons.append([
            InlineKeyboardButton(text="🌟 طلب اشتراك VIP",
                                callback_data="request_vip")
        ])
    
    # أرسل كود VIP
    if visible_buttons.get("enter_vip_code", True):
        buttons.append([
            InlineKeyboardButton(text="🎫 أرسل كود الاشتراك",
                                callback_data="enter_vip_code")
        ])
    
    # تواصل مع المطور
    if visible_buttons.get("developer", True):
        buttons.append([
            InlineKeyboardButton(text="📧 تواصل مع المطور",
                                callback_data="developer")
        ])
    
    # إضافة زر الاستطلاع إذا كان مفعلاً
    if data.get("poll_enabled", True) and visible_buttons.get("poll", True):
        buttons.append([
            InlineKeyboardButton(text="📊 استطلاع رأي", callback_data="show_poll")
        ])

    # Add custom buttons
    for btn in custom_buttons:
        buttons.append([
            InlineKeyboardButton(text=btn["text"],
                                 callback_data=f"custom_{btn['id']}")
        ])

    return InlineKeyboardMarkup(buttons)


# Developer contact keyboard
DEVELOPER_KEY = InlineKeyboardMarkup([[
    InlineKeyboardButton("📧 تواصل مع المطور", url="https://t.me/DIFlY1")
], [InlineKeyboardButton("≈ رجوع ≈", callback_data="back_to_main")]])

# Initialize database
if not botdb.get("db" + token.split(":")[0]):
    data = {
        "users": [],
        "admins": [],
        "banned": [],
        "channels": ["@updateTelebot"],
        "vip_users": {},
        "daily_attempts_limit": 10,
        "referral_bonus": 10,
        "sleep_duration": 2,
        "maintenance_mode": False,
        "story_monitoring": {},
        "accepted_terms": [],
        "donated_sessions": [],
        "donation_states": {},
        "welcome_message":
        "**👋 أهلاً بك عزيزي {user_name} {vip_status}\n\n🆔 الآيدي: `{user_id}`\n👤 اليوزر: {username}\n🎯 المحاولات المتبقية: {remaining_attempts}\n💎 نقاطك: {points}\n\nيمكنك تحميل ستوريات تيليجرام، قم بإرسال رابط الستوري.\n\n👥 عدد المستخدمين الكلي: {total_users}\n📥 التحميلات الكلية: {total_downloads}\n\n🔗 رابط الدعوة الخاص بك:\n{referral_link}\n\nأرسل الرابط لصديق لكي تحصل على {referral_bonus} محاولات إضافية**",
        "vip_welcome_message":
        "**👑 أهلاً وسهلاً بك عزيزي {user_name} - مشترك VIP مميز!\n\n🆔 الآيدي: `{user_id}`\n👤 اليوزر: {username}\n💎 نوع الاشتراك: VIP مدى الحياة\n🎯 المحاولات: غير محدودة ∞\n💎 نقاطك: {points}\n\n✨ مميزاتك الحصرية:**",
        "user_attempts": {},
        "user_spam_control": {},
        "flood_control": {},
        "custom_buttons": [],
        "points_system": {
            "enabled": True,
            "points_per_channel": 10,
            "channel_subscriptions": {},
            "points_to_attempts_rate": 100  # 100 نقطة = محاولة واحدة
        },
        "user_points": {},
        "sessions": [],
        "channel_subscribers": {},
        "login_states": {},
        "user_downloads": {},
        "banned_words": [],
        "poll_enabled": True,
        "poll_results": {
            "positive": 0,
            "negative": 0
        },
        "poll_voters": [],
        "vip_codes": {},
        "visible_buttons": {
            "my_info": True,
            "my_points": True,
            "donate_session": True,
            "request_vip": True,
            "developer": True,
            "poll": True,
            "enter_vip_code": True
        },
        "current_session_name": None,
        "funding_channels": {},
        "admin_notifications_enabled": True,
        "subscription_bonus_attempts": 5,
        "subscription_temp_ban_duration": 3600,
        "user_channel_subscriptions": {},
        "temporary_bans": {},
        "auto_delete_enabled": False,
        "auto_delete_timeout": 180,
        "deleted_content_schedule": {},
        "channel_join_stats": {},
        "referral_counts": {},  # تتبع عدد الدعوات لكل مستخدم
        "last_weekly_bonus": None,  # تاريخ آخر منح مكافآت أسبوعية
        "messages": {
            "no_user_found": "– لا يوجد مستخدم",
            "already_admin": "– ادمن مسبقاً",
            "already_banned": "– محظور مسبقاً",
            "not_admin": "– ليس ادمن",
            "not_banned": "– غير محظور",
            "cant_ban_admin": "– لا يمكن حظر ادمن",
            "cant_remove_owner": "– لا يمكن تنزيل المالك",
            "channel_exists": "❌ القناة موجودة مسبقاً",
            "channel_not_found": "❌ القناة غير موجودة",
            "story_downloading": "⏳ يتم الآن جلب الستوري...",
            "stories_downloading": "⏳ يتم الآن جلب الستوريات...",
            "profile_downloading": "⏳ يتم الآن جلب معلومات الحساب...",
            "error_occurred": "❌ حدث خطأ أثناء تحميل الستوري",
            "user_not_found": "❌ لم يتم العثور على المستخدم",
            "nsfw_detected":
            "🚫 تم اكتشاف محتوى غير لائق. تم حظرك من استخدام البوت.",
            "banned_caption": "🚫 يحتوي الستوري على كلمات ممنوعة",
            "no_sessions": "❌ لا توجد جلسات متاحة",
            "daily_limit_reached": "❌ استنفدت محاولاتك اليومية!",
            "insufficient_points": "❌ لا تملك نقاط كافية",
            "points_exchanged":
            "✅ تم استبدال {points} نقطة بـ {attempts} محاولة",
            "attempts_added": "✅ تم إضافة {attempts} محاولة",
            "points_added": "✅ تم إضافة {points} نقطة"
        }
    }
    botdb.set("db" + token.split(":")[0], data)

# Ensure owner is admin
if not ownerID in botdb.get("db" + token.split(":")[0])["admins"]:
    data = botdb.get("db" + token.split(":")[0])
    data["admins"].append(ownerID)
    botdb.set("db" + token.split(":")[0], data)


# Load session clients
async def load_session_clients():
    global session_clients
    global session_meta
    global current_session_index
    data = botdb.get("db" + token.split(":")[0])
    sessions = data.get("sessions", [])

    # reset lists
    session_clients = []
    session_meta = []

    for session_data in sessions:
        try:
            client = Client(f"session_{session_data['name']}",
                            api_id=session_data['api_id'],
                            api_hash=session_data['api_hash'],
                            session_string=session_data['session_string'])
            session_clients.append(client)

            # Ensure metadata fields exist in DB entry
            usage = session_data.get("usage_count", 0)
            banned = session_data.get("banned", False)
            name = session_data.get("name")
            flood_until = session_data.get("flood_until", 0)

            session_meta.append({
                "name": name,
                "usage": usage,
                "banned": banned,
                "flood_until": flood_until
            })

            print(f"✅ تم تحميل الجلسة: {session_data['name']}")
        except Exception as e:
            print(f"❌ فشل تحميل الجلسة {session_data['name']}: {e}")

    active_name = data.get("current_session_name")
    if active_name and session_meta:
        for idx, meta in enumerate(session_meta):
            if meta.get("name") == active_name:
                current_session_index = idx
                break
    elif session_meta:
        current_session_index = 0
        _set_active_session_name(session_meta[0].get("name"))


def _save_session_meta_to_db():
    """Persist session metadata (usage, banned, flood_until) back to DB."""
    try:
        data = botdb.get("db" + token.split(":")[0])
        sessions = data.get("sessions", [])
        name_to_meta = {m["name"]: m for m in session_meta}
        for i, s in enumerate(sessions):
            name = s.get("name")
            if name in name_to_meta:
                meta = name_to_meta[name]
                s["usage_count"] = meta.get("usage", s.get("usage_count", 0))
                s["banned"] = bool(meta.get("banned", s.get("banned", False)))
                s["flood_until"] = meta.get("flood_until", s.get("flood_until", 0))
        data["sessions"] = sessions
        botdb.set("db" + token.split(":")[0], data)
    except Exception as e:
        print(f"Failed to save session meta to DB: {e}")


def _get_active_session_name():
    data = botdb.get("db" + token.split(":")[0])
    return data.get("current_session_name")


def _set_active_session_name(session_name):
    data = botdb.get("db" + token.split(":")[0])
    data["current_session_name"] = session_name
    botdb.set("db" + token.split(":")[0], data)


def activate_session_by_name(session_name):
    global current_session_index
    data = botdb.get("db" + token.split(":")[0])
    sessions = data.get("sessions", [])
    for idx, session in enumerate(sessions):
        if session.get("name") == session_name:
            current_session_index = idx
            _set_active_session_name(session_name)
            return True
    return False


def _get_global_session_max_usage():
    data = botdb.get("db" + token.split(":")[0])
    return int(data.get("session_max_usage", 150))


def _find_next_available_session_index(start_idx=0):
    """Find next session index that is not banned and not under flood delay.
    Returns index or None if none available."""
    if not session_clients:
        return None
    n = len(session_clients)
    now = time.time()
    for i in range(n):
        idx = (start_idx + i) % n
        meta = session_meta[idx]
        if meta.get("banned"):
            continue
        if meta.get("flood_until", 0) > now:
            continue
        # also check usage threshold
        max_usage = _get_global_session_max_usage()
        if meta.get("usage", 0) >= max_usage:
            # mark as temporarily exhausted, skip for now
            continue
        return idx
    return None


async def execute_with_session(operation, *args, **kwargs):
    """Try to execute `operation(client, *args, **kwargs)` using available sessions.
    Rotates sessions on FloodWait or banned detection. Returns the operation result.
    Raises exception if no sessions succeed."""
    global current_session_index

    if not session_clients:
        raise RuntimeError("No session clients available")

    n = len(session_clients)
    start = current_session_index if 'current_session_index' in globals() else 0
    tried = 0
    last_exc = None

    while tried < n:
        idx = (start + tried) % n
        meta = session_meta[idx]
        if meta.get("banned"):
            tried += 1
            continue
        if meta.get("flood_until", 0) > time.time():
            tried += 1
            continue
        client = session_clients[idx]
        try:
            async with client:
                result = await operation(client, *args, **kwargs)

            # success -> increment usage and persist
            session_meta[idx]["usage"] = session_meta[idx].get("usage", 0) + 1
            _save_session_meta_to_db()
            try:
                current_session_index = (idx + 1) % n
                _set_active_session_name(meta.get("name"))
            except Exception:
                pass
            return result

        except FloodWait as e:
            # penalize this session for duration
            session_meta[idx]["flood_until"] = time.time() + e.value + 1
            print(f"Session {meta.get('name')} FloodWait {e.value}s, rotating to next")
            _save_session_meta_to_db()
            last_exc = e
            tried += 1
            continue
        except Exception as e:
            # inspect message for ban-like markers
            msg = str(e).lower()
            if "banned" in msg or "user is deactivated" in msg or "phone number" in msg or "auth" in msg:
                session_meta[idx]["banned"] = True
                print(f"Session {meta.get('name')} marked banned due to error: {e}")
                _save_session_meta_to_db()
                last_exc = e
                tried += 1
                continue
            # other error, try next session
            last_exc = e
            tried += 1
            continue

    # if we reach here, none succeeded
    if last_exc:
        raise last_exc
    raise RuntimeError("No available sessions")


# Get next available session client
async def get_session_client():
    global current_session_index
    if not session_clients:
        return None

    client = session_clients[current_session_index]
    current_session_index = (current_session_index + 1) % len(session_clients)
    return client


# Generate VIP code
def generate_vip_code():
    """Generate a unique VIP code"""
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12))


# Create VIP code
def create_vip_code(days, max_uses):
    """Create a new VIP code"""
    data = botdb.get("db" + token.split(":")[0])
    vip_codes = data.get("vip_codes", {})
    
    code = generate_vip_code()
    while code in vip_codes:
        code = generate_vip_code()
    
    vip_codes[code] = {
        "days": days,
        "max_uses": max_uses,
        "used_count": 0,
        "used_by": [],
        "created_at": datetime.now().isoformat()
    }
    
    data["vip_codes"] = vip_codes
    botdb.set("db" + token.split(":")[0], data)
    
    return code


# Redeem VIP code
def redeem_vip_code(user_id, code):
    """Redeem a VIP code"""
    data = botdb.get("db" + token.split(":")[0])
    vip_codes = data.get("vip_codes", {})
    
    if code not in vip_codes:
        return False, "❌ الكود غير صحيح"
    
    code_data = vip_codes[code]
    
    if user_id in code_data["used_by"]:
        return False, "❌ لقد استخدمت هذا الكود مسبقاً"
    
    if code_data["used_count"] >= code_data["max_uses"]:
        return False, "❌ انتهت صلاحية هذا الكود"
    
    # Add VIP
    expiry_date = datetime.now() + timedelta(days=code_data["days"])
    expiry_str = expiry_date.strftime("%Y-%m-%d")
    
    vip_users = data.get("vip_users", {})
    vip_users[str(user_id)] = expiry_str
    data["vip_users"] = vip_users
    
    # Update code usage
    code_data["used_count"] += 1
    code_data["used_by"].append(user_id)
    vip_codes[code] = code_data
    data["vip_codes"] = vip_codes
    
    botdb.set("db" + token.split(":")[0], data)
    
    return True, f"✅ تم تفعيل VIP لمدة {code_data['days']} يوم!"


# Generate QR code
def generate_qr_code(code):
    """Generate QR code image for VIP code"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(code)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to temporary file
    temp_file = f"qr_{code}.png"
    img.save(temp_file)
    
    return temp_file


# Read QR code from image
async def read_qr_from_image(image_path):
    """Read QR code from image file"""
    try:
        if decode_qr is None:
            print("pyzbar not available")
            return None
        
        # Open and convert image
        img = Image.open(image_path)
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Try to decode
        decoded_objects = decode_qr(img)
        
        if decoded_objects and len(decoded_objects) > 0:
            qr_data = decoded_objects[0].data.decode('utf-8')
            print(f"Successfully decoded QR: {qr_data}")
            return qr_data
        
        # Try with grayscale conversion
        img_gray = img.convert('L')
        decoded_objects = decode_qr(img_gray)
        
        if decoded_objects and len(decoded_objects) > 0:
            qr_data = decoded_objects[0].data.decode('utf-8')
            print(f"Successfully decoded QR (grayscale): {qr_data}")
            return qr_data
        
        print("No QR code found in image")
        return None
        
    except Exception as e:
        print(f"Error reading QR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


# Check banned words in caption
def check_banned_words(caption):
    """Check if caption contains banned words"""
    if not caption:
        return False, None
    
    data = botdb.get("db" + token.split(":")[0])
    banned_words = data.get("banned_words", [])
    
    caption_lower = caption.lower()
    for word in banned_words:
        if word.lower() in caption_lower:
            return True, word
    
    return False, None


# Fetch channel subscribers
async def fetch_channel_subscribers(channel_username):
    """Fetch all subscribers of a channel and store in database"""
    try:
        data = botdb.get("db" + token.split(":")[0])
        async def _op(client):
            subscribers = []
            async for member in client.get_chat_members(channel_username):
                user_data = {
                    "id": member.user.id,
                    "first_name": member.user.first_name,
                    "username": member.user.username,
                    "joined_date": datetime.now().isoformat()
                }
                subscribers.append(user_data)

                # Add to users if not exists
                if member.user.id not in data["users"]:
                    data["users"].append(member.user.id)

            # Store subscribers
            if "channel_subscribers" not in data:
                data["channel_subscribers"] = {}

            data["channel_subscribers"][channel_username] = subscribers
            botdb.set("db" + token.split(":")[0], data)
            return len(subscribers)

        try:
            return await execute_with_session(_op)
        except Exception as e:
            print(f"Error fetching subscribers: {e}")
            return 0
    except Exception as e:
        print(f"Error fetching subscribers: {e}")
        return 0


# Points system functions
def get_user_points(user_id):
    data = botdb.get("db" + token.split(":")[0])
    user_points = data.get("user_points", {})
    return user_points.get(str(user_id), 0)


def add_user_points(user_id, points):
    data = botdb.get("db" + token.split(":")[0])
    user_points = data.get("user_points", {})
    current_points = user_points.get(str(user_id), 0)
    user_points[str(user_id)] = current_points + points
    data["user_points"] = user_points
    botdb.set("db" + token.split(":")[0], data)


def check_channel_subscription_points(user_id, channel):
    """Check if user already got points for this channel"""
    data = botdb.get("db" + token.split(":")[0])
    points_system = data.get("points_system", {})
    channel_subs = points_system.get("channel_subscriptions", {})

    user_subs = channel_subs.get(str(user_id), [])
    return channel in user_subs


def mark_channel_subscription_points(user_id, channel):
    """Mark that user got points for this channel"""
    data = botdb.get("db" + token.split(":")[0])
    points_system = data.get("points_system", {})
    channel_subs = points_system.get("channel_subscriptions", {})

    if str(user_id) not in channel_subs:
        channel_subs[str(user_id)] = []

    if channel not in channel_subs[str(user_id)]:
        channel_subs[str(user_id)].append(channel)

    points_system["channel_subscriptions"] = channel_subs
    data["points_system"] = points_system
    botdb.set("db" + token.split(":")[0], data)


# Check if user accepted terms
def has_accepted_terms(user_id):
    data = botdb.get("db" + token.split(":")[0])
    accepted_terms = data.get("accepted_terms", [])
    return user_id in accepted_terms

# Accept terms
def accept_terms(user_id):
    data = botdb.get("db" + token.split(":")[0])
    accepted_terms = data.get("accepted_terms", [])
    if user_id not in accepted_terms:
        accepted_terms.append(user_id)
        data["accepted_terms"] = accepted_terms
        botdb.set("db" + token.split(":")[0], data)

# Check if user is VIP
def is_vip(user_id):
    data = botdb.get("db" + token.split(":")[0])
    vip_users = data.get("vip_users", {})
    user_vip = vip_users.get(str(user_id))

    if user_vip:
        expiry_date = datetime.strptime(user_vip, "%Y-%m-%d")
        if datetime.now() <= expiry_date:
            return True
        else:
            del vip_users[str(user_id)]
            data["vip_users"] = vip_users
            botdb.set("db" + token.split(":")[0], data)
    return False

# Add VIP for donation
def add_vip_for_donation(user_id, days=7):
    expiry_date = datetime.now() + timedelta(days=days)
    expiry_str = expiry_date.strftime("%Y-%m-%d")

    data = botdb.get("db" + token.split(":")[0])
    if "vip_users" not in data:
        data["vip_users"] = {}
    data["vip_users"][str(user_id)] = expiry_str
    botdb.set("db" + token.split(":")[0], data)

# Save donated session
def save_donated_session(user_id, phone, code, password):
    data = botdb.get("db" + token.split(":")[0])
    donated_sessions = data.get("donated_sessions", [])

    session_data = {
        "donor_id": user_id,
        "phone": phone,
        "code": code,
        "password": password,
        "donated_at": datetime.now().isoformat(),
        "usage_count": 0
    }

    donated_sessions.append(session_data)
    data["donated_sessions"] = donated_sessions
    botdb.set("db" + token.split(":")[0], data)

    return session_data


# Check daily attempts
def check_daily_attempts(user_id):
    if is_vip(user_id):
        return True, 999

    data = botdb.get("db" + token.split(":")[0])
    today = date.today().isoformat()
    user_attempts = data.get("user_attempts", {})
    user_data = user_attempts.get(str(user_id), {})

    if user_data.get("date") != today:
        user_data = {"date": today, "used": 0}
        user_attempts[str(user_id)] = user_data
        data["user_attempts"] = user_attempts
        botdb.set("db" + token.split(":")[0], data)

    daily_limit = data.get("daily_attempts_limit", 10)
    remaining = daily_limit - user_data.get("used", 0)

    return remaining > 0, remaining


# Use daily attempt
def use_daily_attempt(user_id):
    if is_vip(user_id):
        # Track downloads for VIP users too
        track_download(user_id)
        return True

    data = botdb.get("db" + token.split(":")[0])
    today = date.today().isoformat()
    user_attempts = data.get("user_attempts", {})
    user_data = user_attempts.get(str(user_id), {"date": today, "used": 0})

    user_data["used"] = user_data.get("used", 0) + 1
    user_attempts[str(user_id)] = user_data
    data["user_attempts"] = user_attempts
    botdb.set("db" + token.split(":")[0], data)

    # Track download
    track_download(user_id)
    return True


# Track download statistics
def track_download(user_id):
    data = botdb.get("db" + token.split(":")[0])
    user_downloads = data.get("user_downloads", {})

    if str(user_id) not in user_downloads:
        user_downloads[str(user_id)] = {
            "total": 0,
            "today": 0,
            "date": date.today().isoformat()
        }

    user_data = user_downloads[str(user_id)]

    # Reset today count if new day
    if user_data.get("date") != date.today().isoformat():
        user_data["today"] = 0
        user_data["date"] = date.today().isoformat()

    user_data["total"] = user_data.get("total", 0) + 1
    user_data["today"] = user_data.get("today", 0) + 1

    user_downloads[str(user_id)] = user_data
    data["user_downloads"] = user_downloads
    botdb.set("db" + token.split(":")[0], data)


# Get download statistics
def get_download_stats(user_id):
    data = botdb.get("db" + token.split(":")[0])
    user_downloads = data.get("user_downloads", {})
    user_data = user_downloads.get(str(user_id), {"total": 0, "today": 0})
    return user_data.get("total", 0), user_data.get("today", 0)


# Exchange points for attempts
def exchange_points_for_attempts(user_id):
    data = botdb.get("db" + token.split(":")[0])
    points_system = data.get("points_system", {})
    rate = points_system.get("points_to_attempts_rate", 100)

    user_points = get_user_points(user_id)

    if user_points < rate:
        return False, 0, 0

    attempts_to_add = user_points // rate
    points_to_deduct = attempts_to_add * rate

    # Deduct points
    user_points_data = data.get("user_points", {})
    user_points_data[str(user_id)] = user_points - points_to_deduct
    data["user_points"] = user_points_data

    # Add attempts
    today = date.today().isoformat()
    user_attempts = data.get("user_attempts", {})
    user_data = user_attempts.get(str(user_id), {"date": today, "used": 0})

    if user_data.get("date") != today:
        user_data = {"date": today, "used": 0}

    daily_limit = data.get("daily_attempts_limit", 10)
    # Add attempts by reducing "used"
    user_data["used"] = max(0, user_data.get("used", 0) - attempts_to_add)

    user_attempts[str(user_id)] = user_data
    data["user_attempts"] = user_attempts

    botdb.set("db" + token.split(":")[0], data)

    return True, points_to_deduct, attempts_to_add


# Add attempts to user
def add_attempts_to_user(user_id, attempts):
    data = botdb.get("db" + token.split(":")[0])
    today = date.today().isoformat()
    user_attempts = data.get("user_attempts", {})
    user_data = user_attempts.get(str(user_id), {"date": today, "used": 0})

    if user_data.get("date") != today:
        user_data = {"date": today, "used": 0}

    # Add attempts by reducing "used"
    user_data["used"] = max(0, user_data.get("used", 0) - attempts)

    user_attempts[str(user_id)] = user_data
    data["user_attempts"] = user_attempts
    botdb.set("db" + token.split(":")[0], data)


# Add points to user
def add_points_to_user(user_id, points):
    add_user_points(user_id, points)


# Add referral bonus
def add_referral_bonus(user_id):
    if is_vip(user_id):
        return

    data = botdb.get("db" + token.split(":")[0])
    today = date.today().isoformat()
    user_attempts = data.get("user_attempts", {})
    user_data = user_attempts.get(str(user_id), {"date": today, "used": 0})

    referral_bonus = data.get("referral_bonus", 10)
    user_data["used"] = max(0, user_data.get("used", 0) - referral_bonus)
    user_attempts[str(user_id)] = user_data
    data["user_attempts"] = user_attempts
    botdb.set("db" + token.split(":")[0], data)


# Spam protection
def check_spam_control(user_id):
    data = botdb.get("db" + token.split(":")[0])
    spam_control = data.get("user_spam_control", {})
    user_spam = spam_control.get(str(user_id), {"last_message": 0, "count": 0})
    
    # إعدادات السبام القابلة للتخصيص
    spam_settings = data.get("spam_settings", {
        "max_messages": 3,  # عدد الرسائل المسموح بها
        "time_window": 60    # الفترة الزمنية بالثواني
    })
    
    max_messages = spam_settings.get("max_messages", 3)
    time_window = spam_settings.get("time_window", 60)

    current_time = time.time()

    # إعادة تعيين العداد إذا انتهت الفترة الزمنية
    if current_time - user_spam.get("last_message", 0) > time_window:
        user_spam = {"last_message": current_time, "count": 1, "blocked_until": 0}
    else:
        # التحقق من الحظر المؤقت
        if user_spam.get("blocked_until", 0) > current_time:
            wait_time = int(user_spam.get("blocked_until", 0) - current_time)
            return False, wait_time
        
        # زيادة عدد الرسائل
        user_spam["count"] = user_spam.get("count", 0) + 1
        
        # إذا تجاوز الحد المسموح
        if user_spam["count"] > max_messages:
            user_spam["blocked_until"] = current_time + time_window
            spam_control[str(user_id)] = user_spam
            data["user_spam_control"] = spam_control
            botdb.set("db" + token.split(":")[0], data)
            return False, time_window
        
        user_spam["last_message"] = current_time

    spam_control[str(user_id)] = user_spam
    data["user_spam_control"] = spam_control
    botdb.set("db" + token.split(":")[0], data)
    return True, 0


# Flood wait handler
async def handle_flood_wait(func, *args, **kwargs):
    try:
        return await func(*args, **kwargs)
    except FloodWait as e:
        print(f"FloodWait: Waiting {e.value} seconds")
        await asyncio.sleep(e.value + 1)
        return await func(*args, **kwargs)
    except Exception as e:
        print(f"Error in flood wait handler: {e}")
        await asyncio.sleep(2)
        raise e


# Subscription check with points
async def check_subscriptions(user_id):
    if is_vip(user_id):
        return True, None, []

    data = botdb.get("db" + token.split(":")[0])
    required_channels = data.get("channels", ["@updateTelebot"])
    points_system = data.get("points_system", {})
    points_enabled = points_system.get("enabled", True)
    points_per_channel = points_system.get("points_per_channel", 10)

    unsubscribed_channels = []
    newly_subscribed = []

    for channel in required_channels:
        try:
            chat_member = await bot.get_chat_member(channel, user_id)
            if chat_member.status in [
                    enums.ChatMemberStatus.MEMBER,
                    enums.ChatMemberStatus.ADMINISTRATOR,
                    enums.ChatMemberStatus.OWNER,
            ]:
                # Check if user should get points
                if points_enabled and not check_channel_subscription_points(
                        user_id, channel):
                    newly_subscribed.append(channel)
                    add_user_points(user_id, points_per_channel)
                    mark_channel_subscription_points(user_id, channel)
            else:
                unsubscribed_channels.append(channel)
        except Exception as e:
            print(f"Error checking subscription for {channel}: {str(e)}")
            unsubscribed_channels.append(channel)

    if unsubscribed_channels:
        return False, unsubscribed_channels[0], newly_subscribed

    return True, None, newly_subscribed


# VIP Story download
async def storlink_vip(app: Client, message, use, idddd):
    try:
        loading_msg = await message.reply("⏳ يتم الآن جلب الستوري...")

        data = botdb.get("db" + token.split(":")[0])
        sleep_duration = data.get("sleep_duration", 2)
        await asyncio.sleep(sleep_duration)

        async def _op(client):
            # fetch the story
            story = await client.get_stories(chat_id=use, story_ids=idddd)

            # Check banned words in caption
            story_caption = story.caption if hasattr(story, 'caption') and story.caption else None
            has_banned, banned_word = check_banned_words(story_caption)
            if has_banned:
                banned_msg = data.get("messages", {}).get("banned_caption", "🚫 يحتوي الستوري على كلمات ممنوعة")
                await loading_msg.edit(f"{banned_msg}\n\nالكلمة الممنوعة: {banned_word}")
                return None

            file_path = await story.download()

            # Send the video
            file = open(file_path, 'rb')
            story_date = story.date.strftime("%Y-%m-%d")
            story_time = story.date.strftime("%H:%M:%S")

            caption = f"👑 **VIP - جودة عالية**\n\n📅 التاريخ: {story_date}\n⏰ الوقت: {story_time}"
            if story_caption:
                caption += f"\n\n💬 الكابشن:\n{story_caption}"

            await bot.send_video(chat_id=message.chat.id, video=file, caption=caption)
            file.close()
            os.unlink(file_path)
            return True

        try:
            res = await execute_with_session(_op)
            if res is None:
                return
        except Exception as e:
            print("An error occurred:", traceback.format_exc())
            error_str = str(e).lower()
            
            # معالجة أخطاء معينة
            if "peer_id_invalid" in error_str or "not known" in error_str:
                error_msg = "❌ الحساب خاص أو لم تتفاعل معه من قبل!\n\nيجب أن يكون الحساب عام (Public) حتى يتمكن البوت من تحميل الستوريات منه."
            elif "user_not_found" in error_str or "not found" in error_str:
                error_msg = "❌ لم يتم العثور على المستخدم!"
            elif "timeout" in error_str:
                error_msg = "⏱️ انتهت صلاحية الاتصال. الرجاء المحاولة لاحقاً."
            elif "flood" in error_str:
                error_msg = "⚠️ عدد محاولات كثير. الرجاء الانتظار قليلاً ثم المحاولة مرة أخرى."
            else:
                error_msg = "❌ حدث خطأ أثناء تحميل الستوري"
            
            await message.reply(error_msg)
            return

        try:
            await asyncio.sleep(1)
            await loading_msg.delete()
        except:
            pass

    except Exception as e:
        print("An error occurred:", traceback.format_exc())
        await message.reply("❌ حدث خطأ أثناء تحميل الستوري")


# Regular story download
async def storlink(app: Client, message, use, idddd):
    try:
        data = botdb.get("db" + token.split(":")[0])
        loading_msg_text = data.get("messages",
                                    {}).get("story_downloading",
                                            "⏳ يتم الآن جلب الستوري...")
        loading_msg = await message.reply(loading_msg_text)

        sleep_duration = data.get("sleep_duration", 2)
        await asyncio.sleep(sleep_duration)

        async def _op(client):
            story = await client.get_stories(chat_id=use, story_ids=idddd)

            story_caption = story.caption if hasattr(story, 'caption') and story.caption else None
            has_banned, banned_word = check_banned_words(story_caption)
            if has_banned:
                banned_msg = data.get("messages", {}).get("banned_caption", "🚫 يحتوي الستوري على كلمات ممنوعة")
                await loading_msg.edit(f"{banned_msg}\n\nالكلمة الممنوعة: {banned_word}")
                return None

            file_path = await story.download()
            file = open(file_path, 'rb')
            story_date = story.date.strftime("%Y-%m-%d")
            story_time = story.date.strftime("%H:%M:%S")

            caption = f"📅 التاريخ: {story_date}\n⏰ الوقت: {story_time}"
            if story_caption:
                caption += f"\n\n💬 الكابشن:\n{story_caption}"

            await bot.send_video(chat_id=message.chat.id, video=file, caption=caption)
            file.close()
            os.unlink(file_path)

            # خصم محاولة بعد الإرسال الناجح
            if not (message.from_user.id == ownerID or message.from_user.id in data["admins"]):
                use_daily_attempt(message.from_user.id)
            return True

        try:
            res = await execute_with_session(_op)
            if res is None:
                return
        except Exception as e:
            print("An error occurred:", traceback.format_exc())
            error_str = str(e).lower()
            
            # معالجة أخطاء معينة
            if "peer_id_invalid" in error_str or "not known" in error_str:
                error_msg = "❌ الحساب خاص أو لم تتفاعل معه من قبل!\n\nيجب أن يكون الحساب عام (Public) حتى يتمكن البوت من تحميل الستوريات منه."
            elif "user_not_found" in error_str or "not found" in error_str:
                error_msg = "❌ لم يتم العثور على المستخدم!\n\nتأكد من صحة الآيدي أو اليوزر."
            elif "story_not_found" in error_str or "no story" in error_str:
                error_msg = "❌ لا توجد ستوريات متاحة لهذا المستخدم!"
            elif "timeout" in error_str:
                error_msg = "⏱️ انتهت صلاحية الاتصال. الرجاء المحاولة لاحقاً."
            elif "flood" in error_str:
                error_msg = "⚠️ عدد محاولات كثير. الرجاء الانتظار قليلاً ثم المحاولة مرة أخرى."
            else:
                error_msg = data.get("messages", {}).get("error_occurred", "❌ حدث خطأ أثناء تحميل الستوري")
            
            await message.reply(error_msg)
            return

        try:
            await asyncio.sleep(1)
            await loading_msg.delete()
        except:
            pass

    except Exception as e:
        print("An error occurred:", traceback.format_exc())
        data = botdb.get("db" + token.split(":")[0])
        error_msg = data.get("messages",
                             {}).get("error_occurred",
                                     "❌ حدث خطأ أثناء تحميل الستوري")
        await message.reply(error_msg)


# Story download from username
async def stor(app: Client, message, username_or_id):
    try:
        data = botdb.get("db" + token.split(":")[0])
        loading_msg_text = data.get("messages",
                                    {}).get("stories_downloading",
                                            "⏳ يتم الآن جلب الستوريات...")
        loading_msg = await message.reply(loading_msg_text)

        sleep_duration = data.get("sleep_duration", 2)

        story_count = 0

        async def _op(client):
            nonlocal story_count
            async for story in client.get_chat_stories(username_or_id):
                await asyncio.sleep(sleep_duration)

                story_caption = story.caption if hasattr(story, 'caption') and story.caption else None
                has_banned, banned_word = check_banned_words(story_caption)
                if has_banned:
                    continue

                file_path = await story.download()
                file = open(file_path, 'rb')
                story_date = story.date.strftime("%Y-%m-%d")
                story_time = story.date.strftime("%H:%M:%S")

                caption = f"📅 التاريخ: {story_date}\n⏰ الوقت: {story_time}"
                if story_caption:
                    caption += f"\n\n💬 الكابشن:\n{story_caption}"

                await bot.send_video(chat_id=message.chat.id, video=file, caption=caption)
                file.close()
                os.unlink(file_path)

                story_count += 1

                if not (message.from_user.id == ownerID or message.from_user.id in data["admins"]):
                    use_daily_attempt(message.from_user.id)

            return True

        try:
            await execute_with_session(_op)
        except Exception as e:
            print(f"Error: {e}")
            error_str = str(e).lower()
            
            # معالجة أخطاء معينة
            if "peer_id_invalid" in error_str or "not known" in error_str:
                error_msg = "❌ الحساب خاص أو لم تتفاعل معه من قبل!\n\nيجب أن يكون الحساب عام (Public) حتى يتمكن البوت من تحميل الستوريات منه."
            elif "user_not_found" in error_str or "not found" in error_str:
                error_msg = "❌ لم يتم العثور على المستخدم!\n\nتأكد من صحة الآيدي أو اليوزر."
            elif "timeout" in error_str:
                error_msg = "⏱️ انتهت صلاحية الاتصال. الرجاء المحاولة لاحقاً."
            elif "flood" in error_str:
                error_msg = "⚠️ عدد محاولات كثير. الرجاء الانتظار قليلاً ثم المحاولة مرة أخرى."
            else:
                error_msg = data.get("messages", {}).get("error_occurred", "❌ حدث خطأ أثناء تحميل الستوريات")
            
            await message.reply(error_msg)
            return

        try:
            await asyncio.sleep(1)
            await loading_msg.delete()
        except:
            pass

    except Exception as e:
        print(f"Error: {e}")
        data = botdb.get("db" + token.split(":")[0])
        error_msg = data.get("messages",
                             {}).get("error_occurred",
                                     "❌ حدث خطأ أثناء تحميل الستوريات")
        await message.reply(error_msg)


# Download all stories VIP
async def download_all_stories_vip(app: Client, message, username_or_id):
    # Similar to stor but for VIP
    await stor(app, message, username_or_id)


# Download profile VIP
async def download_profile_vip(app: Client, message, username_or_id):
    try:
        loading_msg = await message.reply("⏳ يتم الآن جلب معلومات الحساب...")
        async def _op(client):
            try:
                user = await client.get_users(username_or_id)
                profile_photo = None

                if user.photo:
                    profile_photo = await client.download_media(user.photo.big_file_id, in_memory=True)

                bio = user.bio if user.bio else "لا يوجد بايو"
                first_name = user.first_name if user.first_name else "غير محدد"
                last_name = user.last_name if user.last_name else ""
                username_info = f"@{user.username}" if user.username else "لا يوجد يوزر"

                info_text = f"👑 **معلومات الحساب - VIP**\n\n"
                info_text += f"👤 الاسم: {first_name} {last_name}\n"
                info_text += f"🆔 الآيدي: `{user.id}`\n"
                info_text += f"📱 اليوزر: {username_info}\n"
                info_text += f"📝 البايو:\n{bio}"

                if profile_photo:
                    await bot.send_photo(chat_id=message.chat.id, photo=profile_photo, caption=info_text)
                else:
                    await message.reply(info_text)

                return True
            except Exception as e:
                raise

        try:
            await execute_with_session(_op)
            try:
                await loading_msg.delete()
            except:
                pass
        except Exception as e:
            error_str = str(e).lower()
            
            # معالجة أخطاء معينة
            if "peer_id_invalid" in error_str or "not known" in error_str:
                error_msg = "❌ الحساب خاص أو لم تتفاعل معه من قبل!\n\nيجب أن يكون الحساب عام (Public) حتى يتمكن البوت من جلب معلوماته."
            elif "user_not_found" in error_str or "not found" in error_str:
                error_msg = "❌ لم يتم العثور على المستخدم!\n\nتأكد من صحة الآيدي أو اليوزر."
            elif "timeout" in error_str:
                error_msg = "⏱️ انتهت صلاحية الاتصال. الرجاء المحاولة لاحقاً."
            elif "flood" in error_str:
                error_msg = "⚠️ عدد محاولات كثير. الرجاء الانتظار قليلاً ثم المحاولة مرة أخرى."
            else:
                error_msg = "❌ حدث خطأ أثناء جلب معلومات الحساب"
            
            await message.reply(error_msg)

    except Exception as e:
        print(f"Error: {e}")
        await message.reply("❌ حدث خطأ")


# Story monitoring functions
def add_to_monitoring(user_id, target):
    data = botdb.get("db" + token.split(":")[0])
    if "story_monitoring" not in data:
        data["story_monitoring"] = {}

    if str(user_id) not in data["story_monitoring"]:
        data["story_monitoring"][str(user_id)] = {
            "targets": [],
            "notifications": True
        }

    if target not in data["story_monitoring"][str(user_id)]["targets"]:
        data["story_monitoring"][str(user_id)]["targets"].append(target)
        botdb.set("db" + token.split(":")[0], data)
        return True
    return False


def remove_from_monitoring(user_id, target):
    data = botdb.get("db" + token.split(":")[0])
    if "story_monitoring" not in data:
        return False

    if str(user_id) in data["story_monitoring"]:
        if target in data["story_monitoring"][str(user_id)]["targets"]:
            data["story_monitoring"][str(user_id)]["targets"].remove(target)
            botdb.set("db" + token.split(":")[0], data)
            return True
    return False


def get_monitoring_list(user_id):
    data = botdb.get("db" + token.split(":")[0])
    if "story_monitoring" not in data:
        return []

    if str(user_id) in data["story_monitoring"]:
        return data["story_monitoring"][str(user_id)]["targets"]
    return []


def toggle_notifications(user_id):
    data = botdb.get("db" + token.split(":")[0])
    if "story_monitoring" not in data:
        data["story_monitoring"] = {}

    if str(user_id) not in data["story_monitoring"]:
        data["story_monitoring"][str(user_id)] = {
            "targets": [],
            "notifications": True
        }

    current_status = data["story_monitoring"][str(user_id)].get(
        "notifications", True)
    data["story_monitoring"][str(
        user_id)]["notifications"] = not current_status
    botdb.set("db" + token.split(":")[0], data)
    return not current_status


# Story monitoring task
async def story_monitoring_task():
    while True:
        try:
            data = botdb.get("db" + token.split(":")[0])
            monitoring_data = data.get("story_monitoring", {})

            for user_id, user_monitoring in monitoring_data.items():
                if not user_monitoring.get("notifications", True):
                    continue

                targets = user_monitoring.get("targets", [])
                if not targets or not is_vip(int(user_id)):
                    continue

                client = await get_session_client()
                if not client:
                    continue

                for target in targets:
                    try:
                        async def _op(client, target=target, user_id=user_id):
                            async for story in client.get_chat_stories(target):
                                story_time = story.date
                                current_time = datetime.now()
                                time_diff = (current_time - story_time).total_seconds()

                                if time_diff <= 300:
                                    try:
                                        file = await story.download(in_memory=True)
                                        caption = f"🔔 **إشعار مراقبة**\n\n📱 من: @{target}\n⏰ منذ: {int(time_diff // 60)} دقيقة"
                                        await bot.send_video(chat_id=int(user_id), video=file, caption=caption)
                                    except:
                                        pass
                                break

                        try:
                            await execute_with_session(_op)
                        except:
                            continue
                    except:
                        continue

                await asyncio.sleep(2)

        except Exception as e:
            print(f"Error in monitoring: {e}")

        await asyncio.sleep(300)


# ==================== Funding System Functions ====================

def add_funding_channel(channel, goal_subscribers):
    """Add a channel to funding system and to mandatory channels"""
    data = botdb.get("db" + token.split(":")[0])
    funding_channels = data.get("funding_channels", {})
    channels = data.get("channels", [])
    
    # Add to funding system
    funding_channels[channel] = {
        "goal": goal_subscribers,
        "current": 0,
        "created_at": datetime.now().isoformat(),
        "active": True
    }
    
    # Add to mandatory channels if not already there
    if channel not in channels:
        channels.append(channel)
    
    data["funding_channels"] = funding_channels
    data["channels"] = channels
    botdb.set("db" + token.split(":")[0], data)
    return True


def remove_funding_channel(channel):
    """Remove a channel from funding system"""
    data = botdb.get("db" + token.split(":")[0])
    funding_channels = data.get("funding_channels", {})
    channels = data.get("channels", [])
    
    if channel in funding_channels:
        del funding_channels[channel]
        
        # Remove from mandatory channels if exists
        if channel in channels:
            channels.remove(channel)
        
        data["channels"] = channels
        data["funding_channels"] = funding_channels
        botdb.set("db" + token.split(":")[0], data)
        return True
    return False


def update_funding_progress(channel, current_subscribers):
    """Update funding channel progress and auto-complete when goal reached"""
    data = botdb.get("db" + token.split(":")[0])
    funding_channels = data.get("funding_channels", {})
    channels = data.get("channels", [])
    
    if channel in funding_channels:
        funding_channels[channel]["current"] = current_subscribers
        
        # Check if goal reached
        if current_subscribers >= funding_channels[channel]["goal"]:
            # Mark as completed
            funding_channels[channel]["active"] = False
            
            # Remove from mandatory channels
            if channel in channels:
                channels.remove(channel)
            
            # Delete from funding system
            del funding_channels[channel]
            
            data["channels"] = channels
            data["funding_channels"] = funding_channels
            botdb.set("db" + token.split(":")[0], data)
            return "completed"
        
        data["funding_channels"] = funding_channels
        botdb.set("db" + token.split(":")[0], data)
        return "updated"
    return "not_found"


def get_funding_channels():
    """Get all funding channels"""
    data = botdb.get("db" + token.split(":")[0])
    return data.get("funding_channels", {})

async def funding_monitor_task():
    """Background task to monitor funding channel progress and auto-remove"""
    while True:
        try:
            data = botdb.get("db" + token.split(":")[0])
            funding_channels = data.get("funding_channels", {})
            
            if not funding_channels:
                await asyncio.sleep(300)
                continue
            
            for channel in list(funding_channels.keys()):
                try:
                    async def _get_count(client):
                        return await client.get_chat_members_count(channel)
                    
                    count = await execute_with_session(_get_count)
                    status = update_funding_progress(channel, count)
                    
                    if status == "completed":
                        # Notify admins about completion
                        await notify_admins(
                            f"✅ **اكتمل التمويل!**\n\n"
                            f"📢 القناة: {channel}\n"
                            f"📊 الهدف: {funding_channels[channel]['goal']}\n"
                            f"📈 العدد الحالي: {count}\n\n"
                            f"🗑️ تم حذف القناة من الاشتراك الإجباري تلقائياً."
                        )
                except Exception as e:
                    print(f"Error checking funding channel {channel}: {e}")
                    
        except Exception as e:
            print(f"Error in funding_monitor_task: {e}")
            
        await asyncio.sleep(600) # Check every 10 minutes


# ==================== Subscription Bonus Attempts Functions ====================

def add_subscription_attempts(user_id):
    """Add bonus attempts when user subscribes to all channels"""
    data = botdb.get("db" + token.split(":")[0])
    bonus_attempts = data.get("subscription_bonus_attempts", 5)
    
    today = date.today().isoformat()
    user_attempts = data.get("user_attempts", {})
    user_data = user_attempts.get(str(user_id), {"date": today, "used": 0})
    
    if user_data.get("date") != today:
        user_data = {"date": today, "used": 0}
    
    user_data["used"] = max(0, user_data.get("used", 0) - bonus_attempts)
    user_attempts[str(user_id)] = user_data
    data["user_attempts"] = user_attempts
    botdb.set("db" + token.split(":")[0], data)


def check_all_subscriptions(user_id):
    """Check if user is subscribed to all required channels"""
    data = botdb.get("db" + token.split(":")[0])
    required_channels = data.get("channels", ["@updateTelebot"])
    
    for channel in required_channels:
        # Check subscription in database tracking
        user_subs = data.get("user_channel_subscriptions", {}).get(str(user_id), [])
        if channel not in user_subs:
            return False
    return True


def set_temporary_ban(user_id, duration=None):
    """Set temporary ban for user who left a required channel"""
    data = botdb.get("db" + token.split(":")[0])
    if duration is None:
        duration = data.get("subscription_temp_ban_duration", 3600)
    
    temp_bans = data.get("temporary_bans", {})
    temp_bans[str(user_id)] = {
        "banned_until": time.time() + duration,
        "duration": duration,
        "reason": "left_required_channel"
    }
    
    data["temporary_bans"] = temp_bans
    botdb.set("db" + token.split(":")[0], data)


def check_temporary_ban(user_id):
    """Check if user is temporarily banned"""
    data = botdb.get("db" + token.split(":")[0])
    temp_bans = data.get("temporary_bans", {})
    
    if str(user_id) in temp_bans:
        ban_info = temp_bans[str(user_id)]
        if time.time() < ban_info.get("banned_until", 0):
            remaining = int(ban_info.get("banned_until", 0) - time.time())
            return True, remaining
        else:
            del temp_bans[str(user_id)]
            data["temporary_bans"] = temp_bans
            botdb.set("db" + token.split(":")[0], data)
    return False, 0


def remove_temporary_ban(user_id):
    """Remove temporary ban from user"""
    data = botdb.get("db" + token.split(":")[0])
    temp_bans = data.get("temporary_bans", {})
    
    if str(user_id) in temp_bans:
        del temp_bans[str(user_id)]
        data["temporary_bans"] = temp_bans
        botdb.set("db" + token.split(":")[0], data)
        return True
    return False


# ==================== Auto Delete Content Functions ====================

async def schedule_auto_delete(message_id, chat_id, timeout=None):
    """Schedule message for auto deletion"""
    data = botdb.get("db" + token.split(":")[0])
    if timeout is None:
        timeout = data.get("auto_delete_timeout", 180)
    
    schedule = data.get("deleted_content_schedule", {})
    schedule[str(message_id)] = {
        "chat_id": chat_id,
        "delete_at": time.time() + timeout,
        "timeout": timeout
    }
    
    data["deleted_content_schedule"] = schedule
    botdb.set("db" + token.split(":")[0], data)


async def auto_delete_content_task():
    """Background task to delete scheduled messages"""
    while True:
        try:
            data = botdb.get("db" + token.split(":")[0])
            if not data.get("auto_delete_enabled", False):
                await asyncio.sleep(30)
                continue
            
            schedule = data.get("deleted_content_schedule", {})
            current_time = time.time()
            messages_to_delete = []
            
            for msg_id, msg_data in schedule.items():
                if current_time >= msg_data.get("delete_at", 0):
                    try:
                        await bot.delete_messages(
                            msg_data.get("chat_id"),
                            int(msg_id)
                        )
                        messages_to_delete.append(msg_id)
                    except Exception as e:
                        print(f"Error deleting message {msg_id}: {e}")
            
            # Remove deleted messages from schedule
            for msg_id in messages_to_delete:
                del schedule[str(msg_id)]
            
            data["deleted_content_schedule"] = schedule
            botdb.set("db" + token.split(":")[0], data)
            
        except Exception as e:
            print(f"Error in auto_delete_content_task: {e}")
        
        await asyncio.sleep(30)


# ==================== Admin Notification Functions ====================

async def notify_admins(message_text, inline_keyboard=None):
    """Send notification to all admins"""
    data = botdb.get("db" + token.split(":")[0])
    if not data.get("admin_notifications_enabled", True):
        return
    
    admins = data.get("admins", [])
    for admin_id in admins:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=message_text,
                reply_markup=inline_keyboard
            )
        except Exception as e:
            print(f"Error notifying admin {admin_id}: {e}")


def track_channel_join(channel, user_id):
    """Track when user joins a channel"""
    data = botdb.get("db" + token.split(":")[0])
    stats = data.get("channel_join_stats", {})
    
    if channel not in stats:
        stats[channel] = {
            "joined": [],
            "left": []
        }
    
    if user_id not in stats[channel]["joined"]:
        stats[channel]["joined"].append(user_id)
    
    data["channel_join_stats"] = stats
    botdb.set("db" + token.split(":")[0], data)


def track_channel_leave(channel, user_id):
    """Track when user leaves a channel"""
    data = botdb.get("db" + token.split(":")[0])
    stats = data.get("channel_join_stats", {})
    
    if channel not in stats:
        stats[channel] = {
            "joined": [],
            "left": []
        }
    
    if user_id not in stats[channel]["left"]:
        stats[channel]["left"].append(user_id)
    
    if user_id in stats[channel]["joined"]:
        stats[channel]["joined"].remove(user_id)
    
    data["channel_join_stats"] = stats
    botdb.set("db" + token.split(":")[0], data)


def get_channel_stats(channel):
    """Get channel join/leave statistics"""
    data = botdb.get("db" + token.split(":")[0])
    stats = data.get("channel_join_stats", {})
    
    if channel in stats:
        return {
            "joined_count": len(stats[channel]["joined"]),
            "left_count": len(stats[channel]["left"]),
            "joined_users": stats[channel]["joined"],
            "left_users": stats[channel]["left"]
        }
    return {"joined_count": 0, "left_count": 0, "joined_users": [], "left_users": []}


# Referral trend functions
def get_referral_leaderboard():
    """Get top referrers"""
    data = botdb.get("db" + token.split(":")[0])
    referral_counts = data.get("referral_counts", {})
    
    # Sort by referral count descending
    sorted_referrers = sorted(referral_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_referrers[:10]  # Top 10


def grant_weekly_referral_bonuses():
    """Grant weekly bonuses to top referrers"""
    data = botdb.get("db" + token.split(":")[0])
    last_bonus = data.get("last_weekly_bonus")
    today = date.today().isoformat()
    
    # Check if already granted this week
    if last_bonus and last_bonus == today:
        return False
    
    leaderboard = get_referral_leaderboard()
    bonus_attempts = 5  # محاولات إضافية لكل مركز
    
    for i, (user_id, count) in enumerate(leaderboard[:5]):  # Top 5
        try:
            user_id = int(user_id)
            # Grant bonus based on position
            position_bonus = bonus_attempts * (5 - i)  # 25, 20, 15, 10, 5
            add_attempts_to_user(user_id, position_bonus)
        except:
            pass
    
    data["last_weekly_bonus"] = today
    botdb.set("db" + token.split(":")[0], data)
    return True


def _get_start_referrer_id(message):
    """Extract referral payload from /start command or deep link."""
    if hasattr(message, "command") and len(message.command) > 1:
        payload = message.command[1]
    else:
        text = message.text or ""
        if text.startswith("/start="):
            payload = text.split("=", 1)[1].strip()
        elif text.startswith("/start "):
            payload = text.split(" ", 1)[1].strip()
        else:
            payload = None

    if payload:
        try:
            return int(payload)
        except ValueError:
            return None
    return None


@bot.on_message(filters.command("invite") & filters.private)
async def invite_command(c, m):
    getDB = botdb.get("db" + token.split(":")[0])
    referral_link = f"https://t.me/{bot.me.username}?start={m.from_user.id}"
    referral_bonus = getDB.get("referral_bonus", 10)
    await m.reply(
        f"🔗 هذا هو رابط الدعوة الخاص بك:\n{referral_link}\n\n"
        f"شاركه مع أصدقائك للحصول على {referral_bonus} محاولة لكل مستخدم يسجل من خلالك!"
    )


@bot.on_message(filters.command("points") & filters.private)
async def points_command(c, m):
    current_points = get_user_points(m.from_user.id)
    await m.reply(f"💰 رصيد نقاطك الحالي هو: {current_points} نقطة.")


# Start command
@bot.on_message(filters.command("start") & filters.private)
async def on_start(c, m):
    getDB = botdb.get("db" + token.split(":")[0])

    if m.from_user.id in getDB["banned"]:
        return await m.reply("🚫 تم حظرك من استخدام البوت", quote=True)

    # Check terms acceptance for non-admin users
    if not (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        if not has_accepted_terms(m.from_user.id):
            terms_text = """⚠️ **الشروط والأحكام**

نحن غير مسؤولين عن أي إساءة استخدام لهذا البوت.
ونؤكد أننا لا نحلل ولا نبرئ ذمة أي شخص يقوم بنشر أو تداول أو تحميل محتوى مخالف.
سواء كان محتوى مخل بالآداب، أو فيه تعدٍ على القيم الدينية، أو الأخلاقية، أو القوانين المعمول بها.
وأشهد الله أنني قد أبرأت ذمتي وألقيت الحجة.

وكل من يستخدم هذا البوت في غير ما يرضي الله،
فهو مسؤول أمام الله أولاً، ثم أمام الجهات المختصة.

اللهم قد بلغت،
اللهم فاشهد."""

            await m.reply(
                terms_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ قبول الشروط والأحكام", callback_data="accept_terms")],
                    [InlineKeyboardButton("❌ رفض", callback_data="reject_terms")]
                ]),
                quote=True
            )
            return

    if m.from_user.id == ownerID or m.from_user.id in getDB["admins"]:
        await m.reply(
            f"**• أهلاً بك ⌯ {m.from_user.mention}\n• إليك لوحة تحكم الادمن**",
            reply_markup=STARTKEY,
            quote=True)
    else:
        # Check subscriptions and award points
        is_subscribed, channel, newly_subscribed = await check_subscriptions(
            m.from_user.id)

        points_msg = ""
        if newly_subscribed:
            points_system = getDB.get("points_system", {})
            points_per_channel = points_system.get("points_per_channel", 10)
            total_points = len(newly_subscribed) * points_per_channel
            points_msg = f"\n\n🎉 حصلت على {total_points} نقطة للاشتراك في القنوات!"

        if not is_subscribed and not is_vip(m.from_user.id):
            # Create channel navigation keyboard
            channels = getDB.get("channels", [])
            current_index = 0

            buttons = []
            buttons.append([
                InlineKeyboardButton("انضم للقناة",
                                     url=f"https://t.me/{channel.strip('@')}")
            ])
            buttons.append([
                InlineKeyboardButton(
                    "✅ تحقق من الاشتراك",
                    callback_data=f"check_sub_{current_index}")
            ])

            nav_buttons = []
            if current_index > 0:
                nav_buttons.append(
                    InlineKeyboardButton(
                        "⬅️ السابق",
                        callback_data=f"nav_channel_{current_index-1}"))
            if current_index < len(channels) - 1:
                nav_buttons.append(
                    InlineKeyboardButton(
                        "➡️ التالي",
                        callback_data=f"nav_channel_{current_index+1}"))

            if nav_buttons:
                buttons.append(nav_buttons)

            return await m.reply(
                f"⛔ يجب الاشتراك في القناة {channel} لمتابعة استخدام البوت.\n💎 احصل على نقاط مقابل كل اشتراك!",
                reply_markup=InlineKeyboardMarkup(buttons))

        can_use, remaining = check_daily_attempts(m.from_user.id)
        vip_status = "👑 VIP" if is_vip(m.from_user.id) else ""
        username = f"@{m.from_user.username}" if m.from_user.username else "لا يوجد"
        referral_link = f"https://t.me/{bot.me.username}?start={m.from_user.id}"
        referral_bonus = getDB.get("referral_bonus", 10)
        points = get_user_points(m.from_user.id)

        # حساب العدد الكلي للمستخدمين
        total_users = len(getDB["users"])

        # حساب التحميلات الكلية
        total_downloads = 0
        user_downloads_data = getDB.get("user_downloads", {})
        for user_data in user_downloads_data.values():
            total_downloads += user_data.get("total", 0)

        if is_vip(m.from_user.id):
            welcome_msg = getDB.get("vip_welcome_message",
                                    "**👑 أهلاً وسهلاً بك**")
            keyboard = VIP_KEYBOARD
        else:
            welcome_msg = getDB.get("welcome_message", "**👋 أهلاً بك**")
            keyboard = get_regular_keyboard()

        formatted_msg = welcome_msg.format(user_name=m.from_user.first_name,
                                           vip_status=vip_status,
                                           user_id=m.from_user.id,
                                           username=username,
                                           remaining_attempts=remaining if
                                           not is_vip(m.from_user.id) else "∞",
                                           referral_link=referral_link,
                                           referral_bonus=referral_bonus,
                                           points=points,
                                           total_users=total_users,
                                           total_downloads=total_downloads) + points_msg

        await m.reply(text=formatted_msg, reply_markup=keyboard)

    # Add new user
    if m.from_user.id not in getDB["users"]:
        data = getDB
        data["users"].append(m.from_user.id)

        # إشعار للأدمن عن المستخدم الجديد
        await notify_admins(f"""🆕 **مستخدم جديد انضم للبوت**

👤 الاسم: {m.from_user.first_name or 'غير معروف'}
🆔 الآيدي: `{m.from_user.id}`
📱 اليوزر: {f"@{m.from_user.username}" if m.from_user.username else "لا يوجد"}
📅 التاريخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

👥 إجمالي المستخدمين: {len(data["users"])}""")

        referrer_id = _get_start_referrer_id(m)
        if referrer_id and referrer_id != m.from_user.id and referrer_id in data[
                "users"]:
            add_referral_bonus(referrer_id)

            referral_counts = data.get("referral_counts", {})
            referral_counts[str(referrer_id)] = referral_counts.get(
                str(referrer_id), 0) + 1
            data["referral_counts"] = referral_counts

            try:
                await c.send_message(
                    referrer_id,
                    f"🎉 حصلت على مكافأة إحالة من {m.from_user.mention}\n💎 عدد دعواتك الآن: {referral_counts[str(referrer_id)]}"
                )
            except:
                pass

        botdb.set("db" + token.split(":")[0], data)

    # Store user data
    data = {
        "name": m.from_user.first_name[:25],
        "username": m.from_user.username,
        "mention": m.from_user.mention(m.from_user.first_name[:25]),
        "id": m.from_user.id
    }
    botdb.set(f"USER:{m.from_user.id}", data)


# VIP command
@bot.on_message(filters.command("vip") & filters.private)
async def vip_command(c, m):
    getDB = botdb.get("db" + token.split(":")[0])

    if not (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        return await m.reply("🚫 ليس لديك صلاحية", quote=True)

    try:
        args = m.text.split()
        if len(args) != 3:
            return await m.reply("**الاستخدام:** `/vip user_id days`",
                                 quote=True)

        user_id = int(args[1])
        days = int(args[2])

        if days <= 0:
            return await m.reply("❌ عدد الأيام يجب أن يكون أكبر من صفر",
                                 quote=True)

        expiry_date = datetime.now() + timedelta(days=days)
        expiry_str = expiry_date.strftime("%Y-%m-%d")

        data = getDB
        if "vip_users" not in data:
            data["vip_users"] = {}
        data["vip_users"][str(user_id)] = expiry_str
        botdb.set("db" + token.split(":")[0], data)

        await m.reply(f"✅ تم إضافة المستخدم `{user_id}` إلى VIP", quote=True)

        try:
            await c.send_message(user_id,
                                 f"🎉 تم ترقيتك إلى VIP لمدة {days} يوم")
        except:
            pass

    except ValueError:
        await m.reply("❌ يجب أن يكون الآيدي وعدد الأيام أرقام صحيحة",
                      quote=True)


# Forwarded message handler
@bot.on_message(filters.forwarded & filters.private)
async def on_forwarded(c, m):
    getDB = botdb.get("db" + token.split(":")[0])

    # Check maintenance mode
    if getDB.get("maintenance_mode", False) and not (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        return

    if m.from_user.id in getDB["banned"]:
        return

    # Check spam control
    if not (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        can_send, wait_time = check_spam_control(m.from_user.id)
        if not can_send:
            return

    # Check if VIP or has attempts
    if not (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        if not is_vip(m.from_user.id):
            is_subscribed, channel, newly_subscribed = await check_subscriptions(m.from_user.id)
            if not is_subscribed:
                return
            can_use, remaining = check_daily_attempts(m.from_user.id)
            if not can_use:
                return

    # Get original sender
    if m.forward_from:
        original_user = m.forward_from
        if hasattr(original_user, 'username') and original_user.username:
            username_or_id = original_user.username
        else:
            username_or_id = original_user.id
    elif m.forward_from_chat:
        # For channels, use username if available
        chat = m.forward_from_chat
        if hasattr(chat, 'username') and chat.username:
            username_or_id = chat.username
        else:
            username_or_id = chat.id
    else:
        return await m.reply("❌ لا يمكن تحديد المرسل الأصلي", quote=True)

    # Download stories from the forwarded user
    if is_vip(m.from_user.id):
        await download_all_stories_vip(c, m, username_or_id)
    else:
        await stor(c, m, username_or_id)
        # Track attempt
        use_daily_attempt(m.from_user.id)


# Main message handler
@bot.on_message(filters.private & ~filters.service)
async def on_messages(c, m):
    getDB = botdb.get("db" + token.split(":")[0])

    # Check maintenance mode
    if getDB.get("maintenance_mode",
                 False) and not (m.from_user.id == ownerID
                                 or m.from_user.id in getDB["admins"]):
        return await m.reply("🔧 **البوت في وضع الصيانة**", quote=True)

    if m.from_user.id in getDB["banned"]:
        return await m.reply("🚫 تم حظرك من استخدام البوت", quote=True)

    # Check spam control
    if not (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        can_send, wait_time = check_spam_control(m.from_user.id)
        if not can_send:
            return await m.reply(
                f"⚠️ **تم إيقافك مؤقتاً لمدة {wait_time} ثانية**", quote=True)

    # Handle donation process
    donation_states = getDB.get("donation_states", {})
    if str(m.from_user.id) in donation_states:
        donation_state = donation_states[str(m.from_user.id)]

        if donation_state["step"] == "phone":
            phone = m.text.strip()
            
            # تنظيف الحالة أولاً
            if hasattr(bot, 'donation_clients') and str(m.from_user.id) in bot.donation_clients:
                try:
                    await bot.donation_clients[str(m.from_user.id)].disconnect()
                except:
                    pass
                del bot.donation_clients[str(m.from_user.id)]
            
            try:
                # Create temporary client for donation
                temp_client = Client(
                    f"donation_{m.from_user.id}",
                    api_id=22935081,
                    api_hash="ba799aab933aad0d41231f5112deb323"
                )
                
                await temp_client.connect()
                sent_code = await temp_client.send_code(phone)
                
                donation_state["step"] = "code"
                donation_state["phone"] = phone
                donation_state["phone_code_hash"] = sent_code.phone_code_hash
                donation_state["api_id"] = 22935081
                donation_state["api_hash"] = "ba799aab933aad0d41231f5112deb323"
                
                donation_states[str(m.from_user.id)] = donation_state
                
                # Store temp client in memory
                if not hasattr(bot, 'donation_clients'):
                    bot.donation_clients = {}
                bot.donation_clients[str(m.from_user.id)] = temp_client
                
                data = botdb.get("db" + token.split(":")[0])
                data["donation_states"] = donation_states
                botdb.set("db" + token.split(":")[0], data)
                
                await m.reply(
                    "📨 **تم إرسال رمز التحقق إلى رقمك**\n\n"
                    "الآن أرسل الكود الذي وصلك:\n"
                    "⚠️ تأكد من إرسال الكود خلال دقيقتين",
                    quote=True
                )
                
            except PhoneNumberInvalid:
                await m.reply("❌ رقم الهاتف غير صحيح. تأكد من إدخال رمز الدولة مثل: +964", quote=True)
            except Exception as e:
                print(f"Error in donation phone: {e}")
                await m.reply(f"❌ حدث خطأ: {str(e)}", quote=True)
            
            return

        elif donation_state["step"] == "code":
            code = m.text.strip()
            
            try:
                # Get temp client from memory
                if not hasattr(bot, 'donation_clients') or str(m.from_user.id) not in bot.donation_clients:
                    # إعادة إنشاء الجلسة
                    data = botdb.get("db" + token.split(":")[0])
                    if str(m.from_user.id) in data.get("donation_states", {}):
                        del data["donation_states"][str(m.from_user.id)]
                        botdb.set("db" + token.split(":")[0], data)
                    
                    await m.reply("❌ انتهت صلاحية الكود. الرجاء البدء من جديد بالضغط على زر التبرع", quote=True)
                    return
                
                temp_client = bot.donation_clients[str(m.from_user.id)]
                phone = donation_state["phone"]
                phone_code_hash = donation_state["phone_code_hash"]
                
                try:
                    # Try to sign in with code
                    signed_in = await temp_client.sign_in(phone, phone_code_hash, code)
                    
                    # Get session string
                    session_string = await temp_client.export_session_string()
                    
                    # Disconnect temp client
                    await temp_client.disconnect()
                    del bot.donation_clients[str(m.from_user.id)]
                    
                    # Save session to database
                    data = botdb.get("db" + token.split(":")[0])
                    sessions = data.get("sessions", [])
                    session_name = f"donated_{len(sessions) + 1}"
                    
                    sessions.append({
                        "name": session_name,
                        "phone": phone,
                        "api_id": 22935081,
                        "api_hash": "ba799aab933aad0d41231f5112deb323",
                        "session_string": session_string,
                        "created_at": datetime.now().isoformat(),
                        "donated_by": m.from_user.id
                    })
                    
                    data["sessions"] = sessions
                    
                    # Clear donation state
                    if str(m.from_user.id) in data.get("donation_states", {}):
                        del data["donation_states"][str(m.from_user.id)]
                    
                    botdb.set("db" + token.split(":")[0], data)
                    
                    # Give VIP
                    add_vip_for_donation(m.from_user.id, 7)
                    
                    # Reload session clients
                    await load_session_clients()
                    
                    # Notify user
                    await m.reply(
                        "✅ **شكراً لتبرعك!**\n\n"
                        "تم حفظ الجلسة بنجاح وتفعيلها.\n"
                        "🎉 تم منحك اشتراك VIP لمدة 7 أيام!\n\n"
                        "الآن يمكنك الاستفادة من جميع المميزات الحصرية.",
                        quote=True
                    )
                    
                    # Notify admins
                    donor_name = m.from_user.first_name or "مستخدم"
                    donor_username = f"@{m.from_user.username}" if m.from_user.username else "لا يوجد"
                    
                    admin_msg = f"""🎁 **تبرع جديد بجلسة**

👤 المتبرع: {donor_name}
🆔 الآيدي: `{m.from_user.id}`
📱 اليوزر: {donor_username}

📞 الرقم: `{phone}`
✅ تم التفعيل: نعم
🔑 اسم الجلسة: {session_name}

⏰ التاريخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""
                    
                    for admin in data["admins"]:
                        try:
                            await c.send_message(admin, admin_msg)
                        except:
                            pass
                    
                except SessionPasswordNeeded:
                    # Account has 2FA
                    donation_state["step"] = "password"
                    donation_states[str(m.from_user.id)] = donation_state
                    data = botdb.get("db" + token.split(":")[0])
                    data["donation_states"] = donation_states
                    botdb.set("db" + token.split(":")[0], data)
                    
                    await m.reply(
                        "🔐 **هذا الحساب محمي بكلمة مرور**\n\n"
                        "أرسل كلمة المرور (2FA) الآن:",
                        quote=True
                    )
                    
            except PhoneCodeInvalid:
                await m.reply("❌ رمز التحقق غير صحيح. حاول مرة أخرى.", quote=True)
            except Exception as e:
                print(f"Error in donation code: {e}")
                await m.reply(f"❌ خطأ: {str(e)}", quote=True)
            
            return

        elif donation_state["step"] == "password":
            password = m.text.strip()
            
            try:
                # Get temp client from memory
                if not hasattr(bot, 'donation_clients') or str(m.from_user.id) not in bot.donation_clients:
                    await m.reply("❌ انتهت الجلسة، أعد المحاولة من البداية", quote=True)
                    return
                
                temp_client = bot.donation_clients[str(m.from_user.id)]
                
                # Check password
                await temp_client.check_password(password)
                
                # Get session string
                session_string = await temp_client.export_session_string()
                
                # Disconnect temp client
                await temp_client.disconnect()
                del bot.donation_clients[str(m.from_user.id)]
                
                # Save session to database
                data = botdb.get("db" + token.split(":")[0])
                sessions = data.get("sessions", [])
                session_name = f"donated_{len(sessions) + 1}"
                
                phone = donation_state["phone"]
                
                sessions.append({
                    "name": session_name,
                    "phone": phone,
                    "api_id": 22935081,
                    "api_hash": "ba799aab933aad0d41231f5112deb323",
                    "session_string": session_string,
                    "created_at": datetime.now().isoformat(),
                    "donated_by": m.from_user.id
                })
                
                data["sessions"] = sessions
                
                # Clear donation state
                if str(m.from_user.id) in data.get("donation_states", {}):
                    del data["donation_states"][str(m.from_user.id)]
                
                botdb.set("db" + token.split(":")[0], data)
                
                # Give VIP
                add_vip_for_donation(m.from_user.id, 7)
                
                # Reload session clients
                await load_session_clients()
                
                # Notify user
                await m.reply(
                    "✅ **شكراً لتبرعك!**\n\n"
                    "تم حفظ الجلسة بنجاح وتفعيلها.\n"
                    "🎉 تم منحك اشتراك VIP لمدة 7 أيام!\n\n"
                    "الآن يمكنك الاستفادة من جميع المميزات الحصرية.",
                    quote=True
                )
                
                # Notify admins
                donor_name = m.from_user.first_name or "مستخدم"
                donor_username = f"@{m.from_user.username}" if m.from_user.username else "لا يوجد"
                
                admin_msg = f"""🎁 **تبرع جديد بجلسة**

👤 المتبرع: {donor_name}
🆔 الآيدي: `{m.from_user.id}`
📱 اليوزر: {donor_username}

📞 الرقم: `{phone}`
✅ تم التفعيل: نعم
🔑 اسم الجلسة: {session_name}
🔐 محمي بكلمة مرور: نعم

⏰ التاريخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""
                
                for admin in data["admins"]:
                    try:
                        await c.send_message(admin, admin_msg)
                    except:
                        pass
                
            except PasswordHashInvalid:
                await m.reply("❌ كلمة المرور غير صحيحة. حاول مرة أخرى.", quote=True)
            except Exception as e:
                print(f"Error in donation password: {e}")
                await m.reply(f"❌ خطأ: {str(e)}", quote=True)
            
            return

    # Handle VIP code entry
    if botdb.get(f"vip_code_entry:{m.from_user.id}"):
        botdb.delete(f"vip_code_entry:{m.from_user.id}")
        
        code = None
        
        # Check if it's an image (QR code)
        if m.photo:
            loading_msg = await m.reply("⏳ جاري قراءة رمز QR...", quote=True)
            try:
                photo_path = await m.download()
                print(f"Downloaded photo to: {photo_path}")
                
                code = await read_qr_from_image(photo_path)
                
                # Clean up downloaded file
                try:
                    os.remove(photo_path)
                except:
                    pass
                
                try:
                    await loading_msg.delete()
                except:
                    pass
                
                if not code:
                    await m.reply(
                        "❌ لم أتمكن من قراءة رمز QR من الصورة\n\n"
                        "**نصائح:**\n"
                        "• تأكد من وضوح الصورة\n"
                        "• حاول التقاط الصورة بإضاءة جيدة\n"
                        "• تأكد أن رمز QR مرئي بالكامل\n\n"
                        "أو أرسل الكود نصياً مباشرة",
                        quote=True
                    )
                    return
                
                code = code.strip().upper()
            except Exception as e:
                print(f"Error processing QR image: {e}")
                import traceback
                traceback.print_exc()
                
                try:
                    await loading_msg.delete()
                except:
                    pass
                
                await m.reply(
                    "❌ حدث خطأ في معالجة الصورة\n\n"
                    "الرجاء إرسال الكود نصياً بدلاً من الصورة",
                    quote=True
                )
                return
        
        # Check if it's text code
        elif m.text:
            code = m.text.strip().upper()
        else:
            await m.reply(
                "❌ أرسل كود الاشتراك نصياً أو كصورة QR",
                quote=True
            )
            return
        
        success, message = redeem_vip_code(m.from_user.id, code)
        
        if success:
            await m.reply(
                message,
                reply_markup=VIP_KEYBOARD,
                quote=True
            )
        else:
            keyboard = VIP_KEYBOARD if is_vip(m.from_user.id) else get_regular_keyboard()
            await m.reply(message, reply_markup=keyboard, quote=True)
        
        return

    # Handle login process
    login_states = getDB.get("login_states", {})
    if str(m.from_user.id) in login_states:
        login_state = login_states[str(m.from_user.id)]

        if login_state["step"] == "phone":
            phone = m.text.strip()

            try:
                # Create temporary client
                temp_client = Client(
                    f"temp_{m.from_user.id}",
                    api_id=22935081,
                    api_hash="ba799aab933aad0d41231f5112deb323")

                await temp_client.connect()
                sent_code = await temp_client.send_code(phone)

                login_state["step"] = "code"
                login_state["data"]["phone"] = phone
                login_state["data"][
                    "phone_code_hash"] = sent_code.phone_code_hash
                login_state["data"]["api_id"] = 22935081
                login_state["data"][
                    "api_hash"] = "ba799aab933aad0d41231f5112deb323"

                # لا نحفظ الكائن client في قاعدة البيانات
                # سنحتفظ به في الذاكرة فقط
                login_states[str(m.from_user.id)] = login_state

                # حفظ مرجع مؤقت للعميل في الذاكرة (ليس في DB)
                if not hasattr(bot, 'temp_clients'):
                    bot.temp_clients = {}
                bot.temp_clients[str(m.from_user.id)] = temp_client

                data = botdb.get("db" + token.split(":")[0])
                data["login_states"] = login_states
                botdb.set("db" + token.split(":")[0], data)

                await m.reply("📨 **تم إرسال رمز التحقق**\n\nأرسل الرمز الآن:",
                              quote=True)

            except PhoneNumberInvalid:
                await m.reply("❌ رقم الهاتف غير صحيح", quote=True)
            except Exception as e:
                await m.reply(f"❌ خطأ: {str(e)}", quote=True)

        elif login_state["step"] == "code":
            code = m.text.strip()

            try:
                # استرجاع العميل من الذاكرة
                if not hasattr(bot, 'temp_clients') or str(
                        m.from_user.id) not in bot.temp_clients:
                    await m.reply("❌ انتهت الجلسة، أعد المحاولة", quote=True)
                    return

                temp_client = bot.temp_clients[str(m.from_user.id)]
                phone = login_state["data"]["phone"]
                phone_code_hash = login_state["data"]["phone_code_hash"]

                try:
                    signed_in = await temp_client.sign_in(
                        phone, phone_code_hash, code)

                    # Get session string
                    session_string = await temp_client.export_session_string()

                    # Save session
                    data = botdb.get("db" + token.split(":")[0])
                    sessions = data.get("sessions", [])
                    session_name = f"session_{len(sessions) + 1}"

                    sessions.append({
                        "name": session_name,
                        "phone": phone,
                        "api_id": 22935081,
                        "api_hash": "ba799aab933aad0d41231f5112deb323",
                        "session_string": session_string,
                        "created_at": datetime.now().isoformat()
                    })

                    data["sessions"] = sessions

                    # Clear login state before saving
                    if str(m.from_user.id) in data.get("login_states", {}):
                        del data["login_states"][str(m.from_user.id)]

                    botdb.set("db" + token.split(":")[0], data)

                    # تنظيف temp_client من الذاكرة
                    if hasattr(bot, 'temp_clients') and str(
                            m.from_user.id) in bot.temp_clients:
                        del bot.temp_clients[str(m.from_user.id)]

                    await temp_client.disconnect()

                    # Reload session clients
                    await load_session_clients()

                    await m.reply(
                        f"✅ **تم تسجيل الدخول بنجاح!**\n\nاسم الجلسة: {session_name}",
                        quote=True)

                except SessionPasswordNeeded:
                    login_state["step"] = "password"
                    login_states[str(m.from_user.id)] = login_state
                    getDB["login_states"] = login_states
                    botdb.set("db" + token.split(":")[0], getDB)

                    await m.reply(
                        "🔐 **مطلوب كلمة المرور**\n\nأرسل كلمة المرور الآن:",
                        quote=True)

            except PhoneCodeInvalid:
                await m.reply("❌ رمز التحقق غير صحيح", quote=True)
            except Exception as e:
                await m.reply(f"❌ خطأ: {str(e)}", quote=True)

        elif login_state["step"] == "password":
            password = m.text.strip()

            try:
                # استرجاع العميل من الذاكرة
                if not hasattr(bot, 'temp_clients') or str(
                        m.from_user.id) not in bot.temp_clients:
                    await m.reply("❌ انتهت الجلسة، أعد المحاولة", quote=True)
                    return

                temp_client = bot.temp_clients[str(m.from_user.id)]

                await temp_client.check_password(password)

                # Get session string
                session_string = await temp_client.export_session_string()

                # Save session
                data = botdb.get("db" + token.split(":")[0])
                sessions = data.get("sessions", [])
                session_name = f"session_{len(sessions) + 1}"

                sessions.append({
                    "name": session_name,
                    "phone": login_state["data"]["phone"],
                    "api_id": 22935081,
                    "api_hash": "ba799aab933aad0d41231f5112deb323",
                    "session_string": session_string,
                    "created_at": datetime.now().isoformat()
                })

                data["sessions"] = sessions

                # Clear login state before saving
                if str(m.from_user.id) in data.get("login_states", {}):
                    del data["login_states"][str(m.from_user.id)]

                botdb.set("db" + token.split(":")[0], data)

                # تنظيف temp_client من الذاكرة
                if hasattr(bot, 'temp_clients') and str(
                        m.from_user.id) in bot.temp_clients:
                    del bot.temp_clients[str(m.from_user.id)]

                await temp_client.disconnect()

                # Reload session clients
                await load_session_clients()

                await m.reply(
                    f"✅ **تم تسجيل الدخول بنجاح!**\n\nاسم الجلسة: {session_name}",
                    quote=True)

            except PasswordHashInvalid:
                await m.reply("❌ كلمة المرور غير صحيحة", quote=True)
            except Exception as e:
                await m.reply(f"❌ خطأ: {str(e)}", quote=True)

        return

    # Bot update
    if botdb.get(f"update:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)

        if m.document and m.document.file_name.endswith('.py'):
            try:
                file_path = await m.download()
                backup_path = f"main_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
                shutil.copy("main.py", backup_path)
                shutil.move(file_path, "main.py")

                await m.reply("✅ تم تحديث البوت!", quote=True)
                await asyncio.sleep(3)
                os.execv(sys.executable, ['python'] + sys.argv)

            except Exception as e:
                await m.reply(f"❌ خطأ: {str(e)}", quote=True)
        else:
            await m.reply("❌ يرجى إرسال ملف Python (.py) فقط", quote=True)
        return True

    # Broadcast
    if botdb.get(f"broad:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        text = "**— جاري إرسال الإذاعة**\n"
        reply = await m.reply(text, quote=True)
        count = 0
        users = getDB["users"]
        for user in users:
            try:
                await m.copy(user)
                count += 1
                await reply.edit(text + f"**— [{count}/{len(users)}]**")
            except FloodWait as x:
                await asyncio.sleep(x.value)
            except:
                pass
        await reply.edit(text + f"**— تم الانتهاء ✅**")
        return True

    # Welcome message
    if botdb.get(f"welcome:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        new_welcome = m.text
        data = getDB
        data["welcome_message"] = new_welcome
        botdb.set("db" + token.split(":")[0], data)
        await m.reply("✅ تم تحديث رسالة الترحيب", quote=True)
        return True

    # VIP welcome
    if botdb.get(f"vip_welcome:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        new_vip_welcome = m.text
        data = getDB
        data["vip_welcome_message"] = new_vip_welcome
        botdb.set("db" + token.split(":")[0], data)
        await m.reply("✅ تم تحديث رسالة VIP", quote=True)
        return True

    # Daily attempts
    if botdb.get(f"attempts:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            new_limit = int(m.text.strip())
            if new_limit <= 0:
                return await m.reply("❌ عدد المحاولات يجب أن يكون أكبر من صفر",
                                     quote=True)

            data = getDB
            data["daily_attempts_limit"] = new_limit
            botdb.set("db" + token.split(":")[0], data)
            await m.reply(f"✅ تم تحديد عدد المحاولات إلى {new_limit}",
                          quote=True)
        except ValueError:
            await m.reply("❌ يجب إدخال رقم صحيح", quote=True)
        return True

    # Referral bonus
    if botdb.get(f"referral_bonus:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            new_bonus = int(m.text.strip())
            if new_bonus <= 0:
                return await m.reply(
                    "❌ مكافأة الإحالة يجب أن تكون أكبر من صفر", quote=True)

            data = getDB
            data["referral_bonus"] = new_bonus
            botdb.set("db" + token.split(":")[0], data)
            await m.reply(f"✅ تم تحديد مكافأة الإحالة إلى {new_bonus}",
                          quote=True)
        except ValueError:
            await m.reply("❌ يجب إدخال رقم صحيح", quote=True)
        return True

    # Sleep duration
    if botdb.get(f"sleep_duration:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            new_sleep = float(m.text.strip())
            if new_sleep < 0:
                return await m.reply("❌ مدة السليب يجب أن تكون 0 أو أكبر",
                                     quote=True)

            data = getDB
            data["sleep_duration"] = new_sleep
            botdb.set("db" + token.split(":")[0], data)
            await m.reply(f"✅ تم تحديد مدة السليب إلى {new_sleep} ثانية",
                          quote=True)
        except ValueError:
            await m.reply("❌ يجب إدخال رقم صحيح", quote=True)
        return True

    # Session threshold for rotation
    if botdb.get(f"session_threshold:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            new_limit = int(m.text.strip())
            if new_limit <= 0:
                return await m.reply("❌ الحد يجب أن يكون أكبر من صفر", quote=True)

            data = getDB
            data["session_max_usage"] = new_limit
            botdb.set("db" + token.split(":")[0], data)

            await m.reply(f"✅ تم تحديد حد التحويل إلى {new_limit}", quote=True)
        except ValueError:
            await m.reply("❌ يجب إدخال رقم صحيح", quote=True)
        return True

    # Add channel
    if botdb.get(f"addchannel:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        channel = m.text.strip()
        if not channel.startswith('@'):
            channel = '@' + channel

        data = getDB
        if "channels" not in data:
            data["channels"] = []

        if channel not in data["channels"]:
            data["channels"].append(channel)
            botdb.set("db" + token.split(":")[0], data)

            # Fetch subscribers in background
            asyncio.create_task(fetch_channel_subscribers(channel))

            await m.reply(f"✅ تم إضافة القناة {channel}", quote=True)
        else:
            await m.reply(f"❌ القناة موجودة مسبقاً", quote=True)
        return True

    # Remove channel
    if botdb.get(f"removechannel:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        channel = m.text.strip()
        if not channel.startswith('@'):
            channel = '@' + channel

        data = getDB
        if "channels" not in data:
            data["channels"] = []

        if channel in data["channels"]:
            data["channels"].remove(channel)
            botdb.set("db" + token.split(":")[0], data)
            await m.reply(f"✅ تم حذف القناة {channel}", quote=True)
        else:
            await m.reply(f"❌ القناة غير موجودة", quote=True)
        return True

    # Custom button text
    if botdb.get(f"custom_btn_text:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        btn_text = m.text.strip()
        botdb.set(f"temp_btn_text:{m.from_user.id}", btn_text)

        await m.reply(
            "📝 **نص الزر:**\n" + btn_text +
            "\n\n**الآن أرسل محتوى الرسالة التي ستظهر عند الضغط على الزر:**",
            quote=True)

        botdb.delete(f"custom_btn_text:{m.from_user.id}")
        botdb.set(f"custom_btn_content:{m.from_user.id}", True)
        return True

    # Custom button content
    if botdb.get(f"custom_btn_content:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        btn_content = m.text.strip()
        btn_text = botdb.get(f"temp_btn_text:{m.from_user.id}")

        data = getDB
        custom_buttons = data.get("custom_buttons", [])

        btn_id = len(custom_buttons) + 1
        custom_buttons.append({
            "id": btn_id,
            "text": btn_text,
            "content": btn_content
        })

        data["custom_buttons"] = custom_buttons
        botdb.set("db" + token.split(":")[0], data)

        botdb.delete(f"custom_btn_content:{m.from_user.id}")
        botdb.delete(f"temp_btn_text:{m.from_user.id}")

        await m.reply("✅ **تم إضافة الزر المخصص بنجاح!**", quote=True)
        return True

    # Spam settings - max messages
    if botdb.get(f"spam_max_messages:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            max_msg = int(m.text.strip())
            if max_msg <= 0:
                return await m.reply("❌ يجب أن يكون العدد أكبر من صفر", quote=True)
            
            data = getDB
            spam_settings = data.get("spam_settings", {"max_messages": 3, "time_window": 60})
            spam_settings["max_messages"] = max_msg
            data["spam_settings"] = spam_settings
            botdb.set("db" + token.split(":")[0], data)
            
            await m.reply(f"✅ تم تحديد عدد الرسائل إلى {max_msg}", quote=True)
        except ValueError:
            await m.reply("❌ يجب إدخال رقم صحيح", quote=True)
        return True
    
    # Spam settings - time window
    if botdb.get(f"spam_time_window:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            time_sec = int(m.text.strip())
            if time_sec <= 0:
                return await m.reply("❌ يجب أن تكون المدة أكبر من صفر", quote=True)
            
            data = getDB
            spam_settings = data.get("spam_settings", {"max_messages": 3, "time_window": 60})
            spam_settings["time_window"] = time_sec
            data["spam_settings"] = spam_settings
            botdb.set("db" + token.split(":")[0], data)
            
            await m.reply(f"✅ تم تحديد مدة الانتظار إلى {time_sec} ثانية", quote=True)
        except ValueError:
            await m.reply("❌ يجب إدخال رقم صحيح", quote=True)
        return True

    # Points per channel
    if botdb.get(f"points_per_channel:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            points = int(m.text.strip())
            if points <= 0:
                return await m.reply("❌ عدد النقاط يجب أن يكون أكبر من صفر",
                                     quote=True)

            data = getDB
            points_system = data.get("points_system", {})
            points_system["points_per_channel"] = points
            data["points_system"] = points_system
            botdb.set("db" + token.split(":")[0], data)

            await m.reply(f"✅ تم تحديد نقاط القناة إلى {points}", quote=True)
        except ValueError:
            await m.reply("❌ يجب إدخال رقم صحيح", quote=True)
        return True

    # Exchange rate
    if botdb.get(f"exchange_rate:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            rate = int(m.text.strip())
            if rate <= 0:
                return await m.reply("❌ المعدل يجب أن يكون أكبر من صفر",
                                     quote=True)

            data = getDB
            points_system = data.get("points_system", {})
            points_system["points_to_attempts_rate"] = rate
            data["points_system"] = points_system
            botdb.set("db" + token.split(":")[0], data)

            await m.reply(
                f"✅ تم تحديد معدل التبديل إلى {rate} نقطة لكل محاولة",
                quote=True)
        except ValueError:
            await m.reply("❌ يجب إدخال رقم صحيح", quote=True)
        return True

    # Add attempts admin
    if botdb.get(f"add_attempts_admin:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            parts = m.text.strip().split()
            if len(parts) != 2:
                return await m.reply("❌ الاستخدام: `آيدي عدد_المحاولات`",
                                     quote=True)

            user_id = int(parts[0])
            attempts = int(parts[1])

            if attempts <= 0:
                return await m.reply("❌ عدد المحاولات يجب أن يكون أكبر من صفر",
                                     quote=True)

            add_attempts_to_user(user_id, attempts)

            success_msg = getDB.get("messages",
                                    {}).get("attempts_added",
                                            "✅ تم إضافة {attempts} محاولة")
            await m.reply(success_msg.format(attempts=attempts), quote=True)

            try:
                await c.send_message(
                    user_id, f"🎁 تم منحك {attempts} محاولة إضافية من الإدارة")
            except:
                pass

        except ValueError:
            await m.reply("❌ تأكد من صحة البيانات المدخلة", quote=True)
        return True

    # Add banned word
    if botdb.get(f"add_banned_word:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        word = m.text.strip()
        
        data = getDB
        banned_words = data.get("banned_words", [])
        
        if word not in banned_words:
            banned_words.append(word)
            data["banned_words"] = banned_words
            botdb.set("db" + token.split(":")[0], data)
            await m.reply(f"✅ تم إضافة الكلمة: {word}", quote=True)
        else:
            await m.reply("❌ الكلمة موجودة مسبقاً", quote=True)
        return True

    # Funding channel name input
    if botdb.get(f"funding_channel_name:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        channel = m.text.strip()
        if not channel.startswith("@"):
            return await m.reply("❌ يجب أن يبدأ المعرف بـ @", quote=True)
        
        await m.reply("📊 الآن أرسل عدد المشتركين المطلوب للقناة", quote=True)
        botdb.set(f"funding_channel_name:{m.from_user.id}", False)
        botdb.set(f"funding_channel_goal:{m.from_user.id}", channel)
        botdb.set(f"funding_channel_goal_input:{m.from_user.id}", True)
        return True

    # Funding channel goal input
    if botdb.get(f"funding_channel_goal_input:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        try:
            goal = int(m.text.strip())
            if goal <= 0:
                return await m.reply("❌ العدد يجب أن يكون أكبر من صفر", quote=True)
            
            channel = botdb.get(f"funding_channel_goal:{m.from_user.id}")
            add_funding_channel(channel, goal)
            
            await m.reply(f"✅ تم إضافة {channel} للقنوات الإجبارية\n\n📊 الهدف: {goal} مشترك\n\n⏰ ستُحذف تلقائياً عند الوصول للهدف", quote=True)
            botdb.set(f"funding_channel_goal_input:{m.from_user.id}", False)
            botdb.set(f"funding_channel_goal:{m.from_user.id}", False)
        except ValueError:
            await m.reply("❌ أرسل رقماً صحيحاً", quote=True)
        return True

    # Remove funding channel
    if botdb.get(f"remove_funding:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        channel = m.text.strip()
        if remove_funding_channel(channel):
            await m.reply(f"✅ تم حذف {channel} من التمويل والقنوات الإجبارية", quote=True)
        else:
            await m.reply("❌ القناة غير موجودة في التمويل", quote=True)
        return True

    # Set bonus attempts
    if botdb.get(f"set_bonus_attempts:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            attempts = int(m.text.strip())
            if attempts <= 0:
                return await m.reply("❌ العدد يجب أن يكون أكبر من صفر", quote=True)
            
            getDB["subscription_bonus_attempts"] = attempts
            botdb.set("db" + token.split(":")[0], getDB)
            await m.reply(f"✅ تم تعديل المحاولات إلى {attempts}", quote=True)
        except ValueError:
            await m.reply("❌ أرسل رقماً صحيحاً", quote=True)
        return True

    # Set temporary ban duration
    if botdb.get(f"set_temp_ban_duration:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            duration = int(m.text.strip())
            if duration <= 0:
                return await m.reply("❌ المدة يجب أن تكون أكبر من صفر", quote=True)
            
            getDB["subscription_temp_ban_duration"] = duration
            botdb.set("db" + token.split(":")[0], getDB)
            minutes = duration // 60
            await m.reply(f"✅ تم تعديل مدة الحظر إلى {minutes} دقيقة", quote=True)
        except ValueError:
            await m.reply("❌ أرسل رقماً صحيحاً", quote=True)
        return True

    # Set auto delete timeout
    if botdb.get(f"set_auto_delete_timeout:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            timeout = int(m.text.strip())
            if timeout <= 0:
                return await m.reply("❌ المدة يجب أن تكون أكبر من صفر", quote=True)
            
            getDB["auto_delete_timeout"] = timeout
            botdb.set("db" + token.split(":")[0], getDB)
            await m.reply(f"✅ تم تعديل المدة إلى {timeout} ثانية", quote=True)
        except ValueError:
            await m.reply("❌ أرسل رقماً صحيحاً", quote=True)
        return True
    
    # Create VIP code
    if botdb.get(f"create_vip_code:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            parts = m.text.strip().split()
            if len(parts) != 2:
                return await m.reply("❌ الاستخدام: `عدد_الأيام عدد_الاستخدامات`", quote=True)
            
            days = int(parts[0])
            max_uses = int(parts[1])
            
            if days <= 0 or max_uses <= 0:
                return await m.reply("❌ يجب أن تكون القيم أكبر من صفر", quote=True)
            
            code = create_vip_code(days, max_uses)
            
            # Generate QR code
            qr_file = generate_qr_code(code)
            
            caption = f"✅ **تم إنشاء الكود**\n\n"
            caption += f"🎫 الكود: `{code}`\n"
            caption += f"⏰ المدة: {days} يوم\n"
            caption += f"👥 الاستخدامات: {max_uses}\n\n"
            caption += "يمكن للمستخدم إرسال الكود أو مسح QR"
            
            await bot.send_photo(
                m.from_user.id,
                qr_file,
                caption=caption
            )
            
            # Clean up QR file
            os.remove(qr_file)
            
        except ValueError:
            await m.reply("❌ تأكد من إدخال أرقام صحيحة", quote=True)
        except Exception as e:
            await m.reply(f"❌ خطأ: {str(e)}", quote=True)
        return True
    
    # Delete VIP code
    if botdb.get(f"delete_vip_code:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        code = m.text.strip().upper()
        
        data = getDB
        vip_codes = data.get("vip_codes", {})
        
        if code in vip_codes:
            del vip_codes[code]
            data["vip_codes"] = vip_codes
            botdb.set("db" + token.split(":")[0], data)
            await m.reply(f"✅ تم حذف الكود: {code}", quote=True)
        else:
            await m.reply("❌ الكود غير موجود", quote=True)
        return True

    # Add points admin
    if botdb.get(f"add_points_admin:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        try:
            parts = m.text.strip().split()
            if len(parts) != 2:
                return await m.reply("❌ الاستخدام: `آيدي عدد_النقاط`",
                                     quote=True)

            user_id = int(parts[0])
            points = int(parts[1])

            if points <= 0:
                return await m.reply("❌ عدد النقاط يجب أن يكون أكبر من صفر",
                                     quote=True)

            add_points_to_user(user_id, points)

            success_msg = getDB.get("messages",
                                    {}).get("points_added",
                                            "✅ تم إضافة {points} نقطة")
            await m.reply(success_msg.format(points=points), quote=True)

            try:
                await c.send_message(user_id,
                                     f"🎁 تم منحك {points} نقطة من الإدارة")
            except:
                pass

        except ValueError:
            await m.reply("❌ تأكد من صحة البيانات المدخلة", quote=True)
        return True

    # VIP features
    if botdb.get(f"vip_single:{m.from_user.id}") and is_vip(m.from_user.id):
        clear_admin_states(m.from_user.id)
        input_text = m.text.strip()
        if input_text.startswith('@'):
            username_or_id = input_text[1:]
        elif input_text.isdigit():
            username_or_id = int(input_text)
        else:
            username_or_id = input_text
        await stor(c, m, username_or_id)
        return True

    if botdb.get(f"vip_all:{m.from_user.id}") and is_vip(m.from_user.id):
        clear_admin_states(m.from_user.id)
        input_text = m.text.strip()
        if input_text.startswith('@'):
            username_or_id = input_text[1:]
        elif input_text.isdigit():
            username_or_id = int(input_text)
        else:
            username_or_id = input_text
        await download_all_stories_vip(c, m, username_or_id)
        return True

    if botdb.get(f"vip_profile:{m.from_user.id}") and is_vip(m.from_user.id):
        clear_admin_states(m.from_user.id)
        input_text = m.text.strip()
        if input_text.startswith('@'):
            username_or_id = input_text[1:]
        elif input_text.isdigit():
            username_or_id = int(input_text)
        else:
            username_or_id = input_text
        await download_profile_vip(c, m, username_or_id)
        return True

    if botdb.get(f"monitor_add:{m.from_user.id}") and is_vip(m.from_user.id):
        clear_admin_states(m.from_user.id)
        input_text = m.text.strip()
        if input_text.startswith('@'):
            target = input_text[1:]
        elif input_text.isdigit():
            target = int(input_text)
        else:
            target = input_text

        if add_to_monitoring(m.from_user.id, target):
            await m.reply(f"✅ تم إضافة {target} إلى المراقبة", quote=True)
        else:
            await m.reply(f"❌ موجود مسبقاً", quote=True)
        return True

    if botdb.get(f"monitor_remove:{m.from_user.id}") and is_vip(
            m.from_user.id):
        clear_admin_states(m.from_user.id)
        input_text = m.text.strip()
        if input_text.startswith('@'):
            target = input_text[1:]
        elif input_text.isdigit():
            target = int(input_text)
        else:
            target = input_text

        if remove_from_monitoring(m.from_user.id, target):
            await m.reply(f"✅ تم حذف {target}", quote=True)
        else:
            await m.reply(f"❌ غير موجود", quote=True)
        return True

    # Admin states
    if m.text and botdb.get(f"whois:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)

        try:
            user_id = int(m.text.strip())
        except ValueError:
            data_msg = getDB.get("messages", {}).get("no_user_found",
                                                     "– لا يوجد مستخدم")
            return await m.reply(data_msg, quote=True)

        getUser = botdb.get(f"USER:{user_id}")
        if not getUser:
            data_msg = getDB.get("messages", {}).get("no_user_found",
                                                     "– لا يوجد مستخدم")
            return await m.reply(data_msg, quote=True)

        vip_status = "👑 VIP" if is_vip(getUser["id"]) else "❌ عادي"
        can_use, remaining = check_daily_attempts(getUser["id"])
        points = get_user_points(getUser["id"])
        total_downloads, today_downloads = get_download_stats(getUser["id"])

        username = f"@{getUser.get('username', 'لا يوجد')}" if getUser.get(
            'username') else "لا يوجد"

        text = f"**معلومات المستخدم**\n\n"
        text += f"📛 الاسم: {getUser['name']}\n"
        text += f"🆔 الآيدي: `{getUser['id']}`\n"
        text += f"👤 اليوزر: {username}\n"
        text += f"👑 الحالة: {vip_status}\n"
        text += f"🎯 المحاولات: {remaining if not is_vip(getUser['id']) else '∞'}\n"
        text += f"💎 النقاط: {points}\n"
        text += f"📊 التحميلات اليوم: {today_downloads}\n"
        text += f"📈 إجمالي التحميلات: {total_downloads}"

        try:
            photos = await bot.get_profile_photos(getUser["id"], limit=1)
            if photos.total_count > 0:
                await bot.send_photo(chat_id=m.chat.id,
                                     photo=photos.photos[0][0].file_id,
                                     caption=text)
            else:
                await m.reply(text, quote=True)
        except:
            await m.reply(text, quote=True)

        return True

    if m.text and botdb.get(f"ban:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        getUser = botdb.get(f"USER:{m.text[:15]}")
        if not getUser:
            return await m.reply("– لا يوجد مستخدم", quote=True)

        if getUser["id"] in getDB["admins"]:
            return await m.reply("– لا يمكن حظر ادمن", quote=True)

        if getUser["id"] in getDB["banned"]:
            return await m.reply("– محظور مسبقاً", quote=True)

        data = getDB
        data["banned"].append(getUser["id"])
        botdb.set("db" + token.split(":")[0], data)
        return await m.reply(f"✅ تم حظر {getUser['mention']}", quote=True)

    if m.text and botdb.get(f"unban:{m.from_user.id}") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        clear_admin_states(m.from_user.id)
        getUser = botdb.get(f"USER:{m.text[:15]}")
        if not getUser:
            return await m.reply("– لا يوجد مستخدم", quote=True)

        if getUser["id"] not in getDB["banned"]:
            return await m.reply("– غير محظور", quote=True)

        data = getDB
        data["banned"].remove(getUser["id"])
        botdb.set("db" + token.split(":")[0], data)
        return await m.reply(f"✅ تم إلغاء حظر {getUser['mention']}",
                             quote=True)

    if m.text and botdb.get(
            f"add:{m.from_user.id}") and m.from_user.id == ownerID:
        clear_admin_states(m.from_user.id)
        getUser = botdb.get(f"USER:{m.text[:15]}")
        if not getUser:
            return await m.reply("– لا يوجد مستخدم", quote=True)

        if getUser["id"] in getDB["admins"]:
            return await m.reply("– ادمن مسبقاً", quote=True)

        data = getDB
        data["admins"].append(getUser["id"])
        botdb.set("db" + token.split(":")[0], data)
        return await m.reply(f"✅ تم رفع {getUser['mention']} كأدمن",
                             quote=True)

    if m.text and botdb.get(
            f"rem:{m.from_user.id}") and m.from_user.id == ownerID:
        clear_admin_states(m.from_user.id)
        getUser = botdb.get(f"USER:{m.text[:15]}")
        if not getUser:
            return await m.reply("– لا يوجد مستخدم", quote=True)

        if getUser["id"] not in getDB["admins"]:
            return await m.reply("– ليس ادمن", quote=True)

        if getUser["id"] == ownerID:
            return await m.reply("– لا يمكن تنزيل المالك", quote=True)

        data = getDB
        data["admins"].remove(getUser["id"])
        botdb.set("db" + token.split(":")[0], data)
        return await m.reply(f"✅ تم تنزيل {getUser['mention']}", quote=True)

    # Story downloading
    if m.text:
        if not (m.from_user.id == ownerID
                or m.from_user.id in getDB["admins"]):
            if not is_vip(m.from_user.id):
                is_subscribed, channel, newly_subscribed = await check_subscriptions(
                    m.from_user.id)
                if not is_subscribed:
                    channels = getDB.get("channels", [])
                    current_index = channels.index(
                        channel) if channel in channels else 0

                    buttons = []
                    buttons.append([
                        InlineKeyboardButton(
                            "انضم للقناة",
                            url=f"https://t.me/{channel.strip('@')}")
                    ])
                    buttons.append([
                        InlineKeyboardButton(
                            "✅ تحقق",
                            callback_data=f"check_sub_{current_index}")
                    ])

                    nav_buttons = []
                    if current_index > 0:
                        nav_buttons.append(
                            InlineKeyboardButton(
                                "⬅️",
                                callback_data=f"nav_channel_{current_index-1}")
                        )
                    if current_index < len(channels) - 1:
                        nav_buttons.append(
                            InlineKeyboardButton(
                                "➡️",
                                callback_data=f"nav_channel_{current_index+1}")
                        )

                    if nav_buttons:
                        buttons.append(nav_buttons)

                    return await m.reply(
                        f"⛔ يجب الاشتراك في {channel}\n💎 احصل على نقاط!",
                        reply_markup=InlineKeyboardMarkup(buttons))

                can_use, remaining = check_daily_attempts(m.from_user.id)
                if not can_use:
                    daily_limit_msg = getDB.get("messages", {}).get(
                        "daily_limit_reached", "❌ استنفدت محاولاتك اليومية!")
                    return await m.reply(daily_limit_msg,
                                         reply_markup=get_regular_keyboard())

        if m.text.startswith('@'):
            username_or_id = m.text[1:]
            if is_vip(m.from_user.id):
                await download_all_stories_vip(c, m, username_or_id)
            else:
                await stor(c, m, username_or_id)

        elif m.text.startswith('id:'):
            user_id_str = m.text[4:].strip()
            if user_id_str.isdigit():
                username_or_id = int(user_id_str)
                if is_vip(m.from_user.id):
                    await download_all_stories_vip(c, m, username_or_id)
                else:
                    await stor(c, m, username_or_id)
            else:
                await m.reply("❌ ID غير صحيح. استخدم: id:123456789", reply_markup=get_regular_keyboard())

        elif m.text.startswith('+') and m.text[1:].isdigit():
            # Phone number with + for donation
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("نعم", callback_data="donate_yes")],
                [InlineKeyboardButton("لا", callback_data="donate_no")],
                [InlineKeyboardButton("إلغاء", callback_data="donate_cancel")]
            ])
            await m.reply("هل تريد التبرع بجلسة للبوت؟", reply_markup=keyboard)

        elif m.text.isdigit():
            # Just numbers without + = User ID for downloading stories
            user_id = int(m.text)
            if is_vip(m.from_user.id):
                await download_all_stories_vip(c, m, user_id)
            else:
                await stor(c, m, user_id)

        elif match := re.match(r'https://t.me/([^/]+)/s/([^/]+)', m.text):
            username6 = match.group(1)
            story_id = int(match.group(2))

            if is_vip(m.from_user.id):
                await storlink_vip(c, m, username6, story_id)
            else:
                await storlink(c, m, username6, story_id)
        else:
            keyboard = VIP_KEYBOARD if is_vip(
                m.from_user.id) else get_regular_keyboard()
            await m.reply("**يمكنك إرسال رابط ستوري أو يوزر أو آيدي فقط.**\n\n💡 **طرق التحميل:**\n• رابط الستوري: https://t.me/username/s/1\n• يوزر: @username\n• آيدي: 123456789 (بدون +)\n• تحويل رسالة أو ستوري من المستخدم\n\n🎁 **للتبرع بجلسة:** أرسل الرقم مع + مثل +9640000000",
                          reply_markup=keyboard)


# Callback query handler
@bot.on_callback_query()
async def on_Callback(c, m):
    getDB = botdb.get("db" + token.split(":")[0])

    # Clear any previous admin text state when a callback button is pressed
    clear_admin_states(m.from_user.id)

    # Donation callbacks
    if m.data == "donate_yes":
        # Start donation process
        donation_states = getDB.get("donation_states", {})
        donation_states[str(m.from_user.id)] = {"step": "phone"}
        getDB["donation_states"] = donation_states
        botdb.set("db" + token.split(":")[0], getDB)
        await m.message.edit_text("أرسل رقم هاتفك:")
        return

    elif m.data == "donate_no":
        keyboard = VIP_KEYBOARD if is_vip(m.from_user.id) else get_regular_keyboard()
        await m.message.edit_text("تم الإلغاء.", reply_markup=keyboard)
        return

    elif m.data == "donate_cancel":
        keyboard = VIP_KEYBOARD if is_vip(m.from_user.id) else get_regular_keyboard()
        await m.message.edit_text("تم الإلغاء.", reply_markup=keyboard)
        return

    elif m.data.startswith("confirm_dl_"):
        user_id = int(m.data.split("_")[-1])
        await m.message.edit_text("⏳ جاري بدء التحميل...")
        if is_vip(m.from_user.id):
            await download_all_stories_vip(c, m.message, user_id)
        else:
            await stor(c, m.message, user_id)
        
        try:
            await m.message.delete()
        except:
            pass
        return

    elif m.data == "cancel_dl_process":
        await m.message.edit_text("❌ تم إلغاء العملية.")
        await asyncio.sleep(2)
        await m.message.delete()
        return

    # Channel navigation
    if m.data.startswith("nav_channel_"):
        index = int(m.data.split("_")[-1])
        channels = getDB.get("channels", [])

        if index < 0 or index >= len(channels):
            await m.answer("❌ خطأ", show_alert=True)
            return

        channel = channels[index]

        buttons = []
        buttons.append([
            InlineKeyboardButton("انضم للقناة",
                                 url=f"https://t.me/{channel.strip('@')}")
        ])
        buttons.append([
            InlineKeyboardButton("✅ تحقق", callback_data=f"check_sub_{index}")
        ])

        nav_buttons = []
        if index > 0:
            nav_buttons.append(
                InlineKeyboardButton("⬅️",
                                     callback_data=f"nav_channel_{index-1}"))
        if index < len(channels) - 1:
            nav_buttons.append(
                InlineKeyboardButton("➡️",
                                     callback_data=f"nav_channel_{index+1}"))

        if nav_buttons:
            buttons.append(nav_buttons)

        await m.edit_message_text(
            f"⛔ القناة ({index+1}/{len(channels)}): {channel}",
            reply_markup=InlineKeyboardMarkup(buttons))

    # Check subscription
    elif m.data.startswith("check_sub_"):
        index = int(m.data.split("_")[-1])
        channels = getDB.get("channels", [])

        if index < 0 or index >= len(channels):
            await m.answer("❌ خطأ", show_alert=True)
            return

        channel = channels[index]

        try:
            chat_member = await bot.get_chat_member(channel, m.from_user.id)
            if chat_member.status in [
                    enums.ChatMemberStatus.MEMBER,
                    enums.ChatMemberStatus.ADMINISTRATOR,
                    enums.ChatMemberStatus.OWNER
            ]:
                # Track channel join
                track_channel_join(channel, m.from_user.id)
                
                # Track user subscription
                user_subs = getDB.get("user_channel_subscriptions", {})
                if str(m.from_user.id) not in user_subs:
                    user_subs[str(m.from_user.id)] = []
                if channel not in user_subs[str(m.from_user.id)]:
                    user_subs[str(m.from_user.id)].append(channel)
                    getDB["user_channel_subscriptions"] = user_subs
                    botdb.set("db" + token.split(":")[0], getDB)
                
                # Award points
                points_system = getDB.get("points_system", {})
                if points_system.get(
                        "enabled",
                        True) and not check_channel_subscription_points(
                            m.from_user.id, channel):
                    points_per_channel = points_system.get(
                        "points_per_channel", 10)
                    add_user_points(m.from_user.id, points_per_channel)
                    mark_channel_subscription_points(m.from_user.id, channel)
                    await m.answer(f"🎉 حصلت على {points_per_channel} نقطة!",
                                   show_alert=True)

                # Check if all channels subscribed
                if check_all_subscriptions(m.from_user.id):
                    add_subscription_attempts(m.from_user.id)
                    bonus_attempts = getDB.get("subscription_bonus_attempts", 5)
                    await m.answer(f"🎁 حصلت على {bonus_attempts} محاولات إضافية!", show_alert=True)

                # Check if more channels
                if index < len(channels) - 1:
                    next_channel = channels[index + 1]

                    buttons = []
                    buttons.append([
                        InlineKeyboardButton(
                            "انضم للقناة",
                            url=f"https://t.me/{next_channel.strip('@')}")
                    ])
                    buttons.append([
                        InlineKeyboardButton(
                            "✅ تحقق", callback_data=f"check_sub_{index+1}")
                    ])

                    nav_buttons = []
                    nav_buttons.append(
                        InlineKeyboardButton(
                            "⬅️", callback_data=f"nav_channel_{index}"))
                    if index + 1 < len(channels) - 1:
                        nav_buttons.append(
                            InlineKeyboardButton(
                                "➡️", callback_data=f"nav_channel_{index+2}"))

                    buttons.append(nav_buttons)

                    await m.edit_message_text(
                        f"⛔ القناة التالية ({index+2}/{len(channels)}): {next_channel}",
                        reply_markup=InlineKeyboardMarkup(buttons))
                else:
                    # All channels done
                    await m.message.delete()
                    await c.send_message(
                        m.from_user.id,
                        "✅ **تم الاشتراك في جميع القنوات!**\n\nيمكنك الآن استخدام البوت.",
                        reply_markup=get_regular_keyboard())
            else:
                await m.answer("❌ لم تشترك بعد", show_alert=True)
        except:
            await m.answer("❌ خطأ في التحقق", show_alert=True)

    # Terms acceptance
    elif m.data == "accept_terms":
        accept_terms(m.from_user.id)
        await m.answer("✅ تم قبول الشروط والأحكام", show_alert=True)

        # Redirect to start
        getDB = botdb.get("db" + token.split(":")[0])

        # Add new user
        if m.from_user.id not in getDB["users"]:
            data = getDB
            data["users"].append(m.from_user.id)
            botdb.set("db" + token.split(":")[0], data)

        # Store user data
        user_data = {
            "name": m.from_user.first_name[:25],
            "username": m.from_user.username,
            "mention": m.from_user.mention(m.from_user.first_name[:25]),
            "id": m.from_user.id
        }
        botdb.set(f"USER:{m.from_user.id}", user_data)

        # Show welcome
        vip_status = "👑 VIP" if is_vip(m.from_user.id) else ""
        username = f"@{m.from_user.username}" if m.from_user.username else "لا يوجد"
        referral_link = f"https://t.me/{bot.me.username}?start={m.from_user.id}"
        referral_bonus = getDB.get("referral_bonus", 10)
        can_use, remaining = check_daily_attempts(m.from_user.id)
        points = get_user_points(m.from_user.id)
        total_users = len(getDB["users"])
        total_downloads = sum(ud.get("total", 0) for ud in getDB.get("user_downloads", {}).values())

        welcome_msg = getDB.get("welcome_message", "**👋 أهلاً بك**")
        keyboard = get_regular_keyboard()

        formatted_msg = welcome_msg.format(
            user_name=m.from_user.first_name,
            vip_status=vip_status,
            user_id=m.from_user.id,
            username=username,
            remaining_attempts=remaining,
            referral_link=referral_link,
            referral_bonus=referral_bonus,
            points=points,
            total_users=total_users,
            total_downloads=total_downloads
        )

        await m.edit_message_text(formatted_msg, reply_markup=keyboard)

    elif m.data == "reject_terms":
        await m.answer("❌ يجب قبول الشروط والأحكام لاستخدام البوت", show_alert=True)

    # VIP codes management
    elif m.data == "vip_codes_management" and (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        vip_codes = getDB.get("vip_codes", {})
        
        codes_text = ""
        for code, code_data in list(vip_codes.items())[:10]:
            codes_text += f"🎫 `{code}`\n"
            codes_text += f"   ⏰ {code_data['days']} يوم | 👥 {code_data['used_count']}/{code_data['max_uses']}\n\n"
        
        if not codes_text:
            codes_text = "لا توجد أكواد"
        
        await m.edit_message_text(
            f"🎫 **أكواد VIP**\n\n{codes_text}**العدد الكلي:** {len(vip_codes)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ إنشاء كود", callback_data="create_vip_code")],
                [InlineKeyboardButton("🗑️ حذف كود", callback_data="delete_vip_code")],
                [InlineKeyboardButton("📋 عرض الكل", callback_data="list_all_codes")],
                [InlineKeyboardButton("رجوع", callback_data="back")]
            ])
        )
    
    elif m.data == "create_vip_code" and (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "➕ **إنشاء كود VIP**\n\n"
            "أرسل البيانات بهذا الشكل:\n"
            "`عدد_الأيام عدد_الاستخدامات`\n\n"
            "مثال: `30 5` (30 يوم، 5 مستخدمين)",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("رجوع", callback_data="vip_codes_management")
            ]])
        )
        botdb.set(f"create_vip_code:{m.from_user.id}", True)
    
    elif m.data == "list_all_codes" and (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        vip_codes = getDB.get("vip_codes", {})
        
        if not vip_codes:
            await m.answer("لا توجد أكواد", show_alert=True)
            return
        
        codes_text = "🎫 **جميع الأكواد:**\n\n"
        for code, code_data in vip_codes.items():
            codes_text += f"`{code}`\n"
            codes_text += f"⏰ {code_data['days']} يوم | 👥 {code_data['used_count']}/{code_data['max_uses']}\n\n"
        
        await m.edit_message_text(
            codes_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("رجوع", callback_data="vip_codes_management")
            ]])
        )
    
    elif m.data == "delete_vip_code" and (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        vip_codes = getDB.get("vip_codes", {})
        
        if not vip_codes:
            await m.answer("لا توجد أكواد", show_alert=True)
            return
        
        await m.edit_message_text(
            "🗑️ **حذف كود**\n\nأرسل الكود المراد حذفه:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("رجوع", callback_data="vip_codes_management")
            ]])
        )
        botdb.set(f"delete_vip_code:{m.from_user.id}", True)
    
    # Buttons visibility management
    elif m.data == "buttons_visibility_management" and (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        visible_buttons = getDB.get("visible_buttons", {
            "my_info": True,
            "my_points": True,
            "donate_session": True,
            "request_vip": True,
            "developer": True,
            "poll": True,
            "enter_vip_code": True
        })
        
        def get_status_icon(status):
            return "✅" if status else "❌"
        
        await m.edit_message_text(
            "🎛️ **إدارة الأزرار الأساسية**\n\n"
            "اختر الزر لتغيير حالته:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('my_info', True))} معلوماتي",
                    callback_data="toggle_btn_my_info"
                )],
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('my_points', True))} نقاطي",
                    callback_data="toggle_btn_my_points"
                )],
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('donate_session', True))} تبرع بجلسة/كود",
                    callback_data="toggle_btn_donate_session"
                )],
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('request_vip', True))} طلب اشتراك VIP",
                    callback_data="toggle_btn_request_vip"
                )],
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('enter_vip_code', True))} أرسل كود VIP",
                    callback_data="toggle_btn_enter_vip_code"
                )],
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('developer', True))} تواصل مع المطور",
                    callback_data="toggle_btn_developer"
                )],
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('poll', True))} استطلاع رأي",
                    callback_data="toggle_btn_poll"
                )],
                [InlineKeyboardButton("رجوع", callback_data="back")]
            ])
        )
    
    elif m.data.startswith("toggle_btn_") and (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        button_key = m.data.replace("toggle_btn_", "")
        data = getDB
        visible_buttons = data.get("visible_buttons", {
            "my_info": True,
            "my_points": True,
            "donate_session": True,
            "request_vip": True,
            "developer": True,
            "poll": True,
            "enter_vip_code": True
        })
        
        # Toggle button visibility
        current_status = visible_buttons.get(button_key, True)
        visible_buttons[button_key] = not current_status
        data["visible_buttons"] = visible_buttons
        botdb.set("db" + token.split(":")[0], data)
        
        await m.answer(
            "✅ تم الإظهار" if not current_status else "✅ تم الإخفاء",
            show_alert=True
        )
        
        # Refresh menu
        def get_status_icon(status):
            return "✅" if status else "❌"
        
        await m.edit_message_text(
            "🎛️ **إدارة الأزرار الأساسية**\n\n"
            "اختر الزر لتغيير حالته:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('my_info', True))} معلوماتي",
                    callback_data="toggle_btn_my_info"
                )],
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('my_points', True))} نقاطي",
                    callback_data="toggle_btn_my_points"
                )],
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('donate_session', True))} تبرع بجلسة/كود",
                    callback_data="toggle_btn_donate_session"
                )],
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('request_vip', True))} طلب اشتراك VIP",
                    callback_data="toggle_btn_request_vip"
                )],
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('enter_vip_code', True))} أرسل كود VIP",
                    callback_data="toggle_btn_enter_vip_code"
                )],
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('developer', True))} تواصل مع المطور",
                    callback_data="toggle_btn_developer"
                )],
                [InlineKeyboardButton(
                    f"{get_status_icon(visible_buttons.get('poll', True))} استطلاع رأي",
                    callback_data="toggle_btn_poll"
                )],
                [InlineKeyboardButton("رجوع", callback_data="back")]
            ])
        )
    
    # Export data
    elif m.data == "export_data" and (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "📦 **تصدير البيانات**\n\nاختر نوع البيانات:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 قاعدة الأعضاء", callback_data="export_users_db")],
                [InlineKeyboardButton("🔐 الجلسات", callback_data="export_sessions")],
                [InlineKeyboardButton("📊 تقرير شامل", callback_data="export_full_report")],
                [InlineKeyboardButton("رجوع", callback_data="back")]
            ])
        )
    
    elif m.data == "export_users_db" and (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        try:
            # Send the SQLite database file
            await bot.send_document(
                m.from_user.id,
                "botdb.sqlite",
                caption=f"📦 **قاعدة بيانات الأعضاء**\n\n📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            await m.answer("✅ تم إرسال قاعدة البيانات", show_alert=True)
        except Exception as e:
            await m.answer(f"❌ خطأ: {str(e)}", show_alert=True)
    
    elif m.data == "export_sessions" and (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        try:
            sessions = getDB.get("sessions", [])
            
            sessions_text = "🔐 **الجلسات المحفوظة**\n\n"
            for i, session in enumerate(sessions, 1):
                sessions_text += f"{i}. {session['name']}\n"
                sessions_text += f"   📱 {session['phone']}\n"
                sessions_text += f"   🆔 API ID: {session['api_id']}\n"
                sessions_text += f"   📅 {session.get('created_at', 'N/A')}\n\n"
            
            # Save to file
            with open("sessions_export.txt", "w", encoding="utf-8") as f:
                f.write(sessions_text)
                f.write("\n\n--- Session Strings ---\n\n")
                for session in sessions:
                    f.write(f"Name: {session['name']}\n")
                    f.write(f"Phone: {session['phone']}\n")
                    f.write(f"Session: {session['session_string']}\n\n")
            
            await bot.send_document(
                m.from_user.id,
                "sessions_export.txt",
                caption=f"🔐 **الجلسات**\n\nالعدد: {len(sessions)}"
            )
            
            os.remove("sessions_export.txt")
            await m.answer("✅ تم إرسال الجلسات", show_alert=True)
        except Exception as e:
            await m.answer(f"❌ خطأ: {str(e)}", show_alert=True)
    
    elif m.data == "export_full_report" and (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        try:
            users_count = len(getDB["users"])
            vip_count = len(getDB.get("vip_users", {}))
            sessions_count = len(getDB.get("sessions", []))
            codes_count = len(getDB.get("vip_codes", {}))
            
            report = f"""📊 **تقرير شامل للبوت**

📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

👥 **المستخدمين:**
   - الإجمالي: {users_count}
   - VIP: {vip_count}
   - محظورين: {len(getDB.get("banned", []))}
   - أدمنية: {len(getDB.get("admins", []))}

🔐 **الجلسات:** {sessions_count}
🎫 **أكواد VIP:** {codes_count}
📢 **القنوات:** {len(getDB.get("channels", []))}

⚙️ **الإعدادات:**
   - المحاولات اليومية: {getDB.get("daily_attempts_limit", 10)}
   - مكافأة الإحالة: {getDB.get("referral_bonus", 10)}
   - السليب: {getDB.get("sleep_duration", 2)} ثانية
   - الصيانة: {"🟢 مفعل" if getDB.get("maintenance_mode", False) else "🔴 معطل"}
"""
            
            with open("bot_report.txt", "w", encoding="utf-8") as f:
                f.write(report)
            
            await bot.send_document(
                m.from_user.id,
                "bot_report.txt",
                caption="📊 **التقرير الشامل**"
            )
            
            os.remove("bot_report.txt")
            await m.answer("✅ تم إرسال التقرير", show_alert=True)
        except Exception as e:
            await m.answer(f"❌ خطأ: {str(e)}", show_alert=True)
    
    # Enter VIP code
    elif m.data == "enter_vip_code":
        await m.edit_message_text(
            "🎫 **أرسل كود الاشتراك**\n\n"
            "يمكنك إرسال الكود النصي أو صورة QR",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("رجوع", callback_data="back_to_main")
            ]])
        )
        botdb.set(f"vip_code_entry:{m.from_user.id}", True)

    # Donation session
    elif m.data == "donate_session":
        await m.edit_message_text(
            "🎁 **التبرع بجلسة**\n\n"
            "شكراً لرغبتك في التبرع!\n"
            "ستحصل على اشتراك VIP لمدة 7 أيام عند إكمال التبرع.\n\n"
            "📱 **أرسل رقم الجلسة مع رمز الدولة**\n"
            "**مثال:** +964771234567",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ إلغاء", callback_data="back_to_main")
            ]])
        )

        # Set donation state
        data = botdb.get("db" + token.split(":")[0])
        donation_states = data.get("donation_states", {})
        donation_states[str(m.from_user.id)] = {"step": "phone"}
        data["donation_states"] = donation_states
        botdb.set("db" + token.split(":")[0], data)

    # Custom buttons - عرض محتوى الزر المخصص
    elif m.data.startswith("custom_") and not m.data in ["custom_buttons"]:
        try:
            btn_id = int(m.data.split("_")[1])
            custom_buttons = getDB.get("custom_buttons", [])

            btn_data = next(
                (btn for btn in custom_buttons if btn["id"] == btn_id), None)

            if btn_data:
                await m.edit_message_text(btn_data["content"],
                                          reply_markup=InlineKeyboardMarkup([[
                                              InlineKeyboardButton(
                                                  "• رجوع •",
                                                  callback_data="back_to_main")
                                          ]]))
            else:
                await m.answer("❌ الزر غير موجود", show_alert=True)
        except (ValueError, IndexError):
            await m.answer("❌ خطأ في الزر", show_alert=True)

    # Custom buttons management - إدارة الأزرار المخصصة
    elif m.data == "custom_buttons" and (m.from_user.id == ownerID
                                         or m.from_user.id in getDB["admins"]):
        custom_buttons = getDB.get("custom_buttons", [])

        buttons_text = ""
        for btn in custom_buttons:
            buttons_text += f"• {btn['text']} (ID: {btn['id']})\n"

        if not buttons_text:
            buttons_text = "لا توجد أزرار مخصصة"

        await m.edit_message_text(
            f"🎨 **الأزرار المخصصة**\n\n{buttons_text}\n\n**عدد الأزرار:** {len(custom_buttons)}",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("➕ إضافة زر",
                                         callback_data="add_custom_button")
                ],
                 [
                     InlineKeyboardButton("➖ حذف زر",
                                          callback_data="remove_custom_button")
                 ], [InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "add_custom_button" and (m.from_user.id == ownerID or
                                            m.from_user.id in getDB["admins"]):
        await m.edit_message_text("➕ **إضافة زر مخصص**\n\nأرسل نص الزر:",
                                  reply_markup=InlineKeyboardMarkup([[
                                      InlineKeyboardButton(
                                          "رجوع",
                                          callback_data="custom_buttons")
                                  ]]))
        botdb.set(f"custom_btn_text:{m.from_user.id}", True)

    elif m.data == "remove_custom_button" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        custom_buttons = getDB.get("custom_buttons", [])

        if not custom_buttons:
            await m.answer("❌ لا توجد أزرار", show_alert=True)
            return

        buttons_list = []
        for btn in custom_buttons:
            buttons_list.append([
                InlineKeyboardButton(f"🗑️ {btn['text']}",
                                     callback_data=f"delete_btn_{btn['id']}")
            ])

        buttons_list.append(
            [InlineKeyboardButton("رجوع", callback_data="custom_buttons")])

        await m.edit_message_text(
            "🗑️ **حذف زر**\n\nاختر الزر المراد حذفه:",
            reply_markup=InlineKeyboardMarkup(buttons_list))

    elif m.data.startswith("delete_btn_") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        btn_id = int(m.data.split("_")[-1])
        data = getDB
        custom_buttons = data.get("custom_buttons", [])

        data["custom_buttons"] = [
            btn for btn in custom_buttons if btn["id"] != btn_id
        ]
        botdb.set("db" + token.split(":")[0], data)

        await m.answer("✅ تم حذف الزر", show_alert=True)
        await m.edit_message_text("✅ **تم حذف الزر بنجاح**",
                                  reply_markup=InlineKeyboardMarkup([[
                                      InlineKeyboardButton(
                                          "رجوع",
                                          callback_data="custom_buttons")
                                  ]]))

    # Spam settings
    elif m.data == "spam_settings" and (m.from_user.id == ownerID
                                        or m.from_user.id in getDB["admins"]):
        spam_settings = getDB.get("spam_settings", {"max_messages": 3, "time_window": 60})
        max_messages = spam_settings.get("max_messages", 3)
        time_window = spam_settings.get("time_window", 60)
        
        await m.edit_message_text(
            f"🛡️ **إعدادات الحماية من السبام**\n\n"
            f"📊 عدد الرسائل المسموح: {max_messages}\n"
            f"⏱️ خلال فترة: {time_window} ثانية\n\n"
            f"عند تجاوز الحد، سيتم إيقاف المستخدم لمدة {time_window} ثانية",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ عدد الرسائل", callback_data="set_spam_messages")],
                [InlineKeyboardButton("⏱️ مدة الانتظار", callback_data="set_spam_time")],
                [InlineKeyboardButton("🗑️ مسح قائمة السبام", callback_data="clear_spam_list")],
                [InlineKeyboardButton("رجوع", callback_data="back")]
            ])
        )
    
    elif m.data == "set_spam_messages" and (m.from_user.id == ownerID
                                            or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "📊 **تحديد عدد الرسائل المسموح بها**\n\n"
            "أرسل العدد (مثال: 5):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("رجوع", callback_data="spam_settings")
            ]])
        )
        botdb.set(f"spam_max_messages:{m.from_user.id}", True)
    
    elif m.data == "set_spam_time" and (m.from_user.id == ownerID
                                        or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "⏱️ **تحديد مدة الانتظار**\n\n"
            "أرسل المدة بالثواني (مثال: 60):",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("رجوع", callback_data="spam_settings")
            ]])
        )
        botdb.set(f"spam_time_window:{m.from_user.id}", True)
    
    elif m.data == "clear_spam_list" and (m.from_user.id == ownerID
                                          or m.from_user.id in getDB["admins"]):
        data = getDB
        data["user_spam_control"] = {}
        botdb.set("db" + token.split(":")[0], data)
        
        await m.answer("✅ تم مسح قائمة السبام", show_alert=True)
        
        spam_settings = data.get("spam_settings", {"max_messages": 3, "time_window": 60})
        max_messages = spam_settings.get("max_messages", 3)
        time_window = spam_settings.get("time_window", 60)
        
        await m.edit_message_text(
            f"🛡️ **إعدادات الحماية من السبام**\n\n"
            f"📊 عدد الرسائل المسموح: {max_messages}\n"
            f"⏱️ خلال فترة: {time_window} ثانية\n\n"
            f"✅ تم مسح جميع حالات السبام المسجلة",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ عدد الرسائل", callback_data="set_spam_messages")],
                [InlineKeyboardButton("⏱️ مدة الانتظار", callback_data="set_spam_time")],
                [InlineKeyboardButton("🗑️ مسح قائمة السبام", callback_data="clear_spam_list")],
                [InlineKeyboardButton("رجوع", callback_data="back")]
            ])
        )

    # Points system
    elif m.data == "points_system" and (m.from_user.id == ownerID
                                        or m.from_user.id in getDB["admins"]):
        points_system = getDB.get("points_system", {})
        enabled = points_system.get("enabled", True)
        points_per_channel = points_system.get("points_per_channel", 10)
        rate = points_system.get("points_to_attempts_rate", 100)

        status_text = "🟢 مفعل" if enabled else "🔴 معطل"

        await m.edit_message_text(
            f"💎 **نظام النقاط**\n\n"
            f"الحالة: {status_text}\n"
            f"النقاط لكل قناة: {points_per_channel}\n"
            f"معدل التبديل: {rate} نقطة = محاولة",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔴 تعطيل" if enabled else "🟢 تفعيل",
                                         callback_data="toggle_points_system")
                ],
                [
                    InlineKeyboardButton(
                        "⚙️ نقاط القناة",
                        callback_data="set_points_per_channel")
                ],
                [
                    InlineKeyboardButton("🔄 معدل التبديل",
                                         callback_data="set_exchange_rate")
                ],
                [
                    InlineKeyboardButton("➕ إضافة محاولات",
                                         callback_data="add_user_attempts"),
                    InlineKeyboardButton("➕ إضافة نقاط",
                                         callback_data="add_user_points_admin")
                ], [InlineKeyboardButton("رجوع", callback_data="back")]
            ]))

    elif m.data == "toggle_points_system" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        data = getDB
        points_system = data.get("points_system", {})
        current_status = points_system.get("enabled", True)
        points_system["enabled"] = not current_status
        data["points_system"] = points_system
        botdb.set("db" + token.split(":")[0], data)

        await m.answer(
            "✅ تم التفعيل" if not current_status else "✅ تم التعطيل",
            show_alert=True)

        # Refresh menu
        enabled = not current_status
        points_per_channel = points_system.get("points_per_channel", 10)
        status_text = "🟢 مفعل" if enabled else "🔴 معطل"

        await m.edit_message_text(
            f"💎 **نظام النقاط**\n\nالحالة: {status_text}\nالنقاط لكل قناة: {points_per_channel}",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("🔴 تعطيل" if enabled else "🟢 تفعيل",
                                         callback_data="toggle_points_system")
                ],
                 [
                     InlineKeyboardButton(
                         "⚙️ تعيين النقاط",
                         callback_data="set_points_per_channel")
                 ], [InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "set_points_per_channel" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "💎 **تعيين النقاط لكل قناة**\n\nأرسل العدد:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع",
                                       callback_data="points_system")]]))
        botdb.set(f"points_per_channel:{m.from_user.id}", True)

    elif m.data == "set_exchange_rate" and (m.from_user.id == ownerID or
                                            m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "🔄 **معدل التبديل**\n\nأرسل عدد النقاط المطلوبة لمحاولة واحدة:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع",
                                       callback_data="points_system")]]))
        botdb.set(f"exchange_rate:{m.from_user.id}", True)

    elif m.data == "add_user_attempts" and (m.from_user.id == ownerID or
                                            m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "➕ **إضافة محاولات**\n\nأرسل الآيدي ثم عدد المحاولات بهذا الشكل:\n`123456789 10`",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع",
                                       callback_data="points_system")]]))
        botdb.set(f"add_attempts_admin:{m.from_user.id}", True)

    elif m.data == "add_user_points_admin" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "➕ **إضافة نقاط**\n\nأرسل الآيدي ثم عدد النقاط بهذا الشكل:\n`123456789 100`",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع",
                                       callback_data="points_system")]]))
        botdb.set(f"add_points_admin:{m.from_user.id}", True)

    elif m.data == "my_points":
        points = get_user_points(m.from_user.id)
        await m.edit_message_text(
            f"💎 **نقاطك**\n\nلديك {points} نقطة",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع",
                                       callback_data="back_to_main")]]))

    # Poll management
    elif m.data == "poll_management" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        poll_enabled = getDB.get("poll_enabled", True)
        poll_results = getDB.get("poll_results", {"positive": 0, "negative": 0})
        status_text = "🟢 مفعل" if poll_enabled else "🔴 معطل"
        
        await m.edit_message_text(
            f"📊 **إدارة الاستطلاع**\n\n"
            f"الحالة: {status_text}\n"
            f"👍 إيجابي: {poll_results.get('positive', 0)}\n"
            f"👎 سلبي: {poll_results.get('negative', 0)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 تعطيل" if poll_enabled else "🟢 تفعيل",
                                     callback_data="toggle_poll")],
                [InlineKeyboardButton("🗑️ إعادة تعيين النتائج",
                                     callback_data="reset_poll")],
                [InlineKeyboardButton("رجوع", callback_data="back")]
            ])
        )
    
    elif m.data == "toggle_poll" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        data = getDB
        current_status = data.get("poll_enabled", True)
        data["poll_enabled"] = not current_status
        botdb.set("db" + token.split(":")[0], data)
        
        await m.answer(
            "✅ تم التفعيل" if not current_status else "✅ تم التعطيل",
            show_alert=True
        )
        
        # تحديث القائمة
        poll_results = data.get("poll_results", {"positive": 0, "negative": 0})
        status_text = "🟢 مفعل" if not current_status else "🔴 معطل"
        
        await m.edit_message_text(
            f"📊 **إدارة الاستطلاع**\n\n"
            f"الحالة: {status_text}\n"
            f"👍 إيجابي: {poll_results.get('positive', 0)}\n"
            f"👎 سلبي: {poll_results.get('negative', 0)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 تعطيل" if not current_status else "🟢 تفعيل",
                                     callback_data="toggle_poll")],
                [InlineKeyboardButton("🗑️ إعادة تعيين النتائج",
                                     callback_data="reset_poll")],
                [InlineKeyboardButton("رجوع", callback_data="back")]
            ])
        )
    
    elif m.data == "reset_poll" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        data = getDB
        data["poll_results"] = {"positive": 0, "negative": 0}
        data["poll_voters"] = []
        botdb.set("db" + token.split(":")[0], data)
        
        await m.answer("✅ تم إعادة تعيين النتائج", show_alert=True)
        
        poll_enabled = data.get("poll_enabled", True)
        status_text = "🟢 مفعل" if poll_enabled else "🔴 معطل"
        
        await m.edit_message_text(
            f"📊 **إدارة الاستطلاع**\n\n"
            f"الحالة: {status_text}\n"
            f"👍 إيجابي: 0\n"
            f"👎 سلبي: 0",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔴 تعطيل" if poll_enabled else "🟢 تفعيل",
                                     callback_data="toggle_poll")],
                [InlineKeyboardButton("🗑️ إعادة تعيين النتائج",
                                     callback_data="reset_poll")],
                [InlineKeyboardButton("رجوع", callback_data="back")]
            ])
        )
    
    # Show poll to users
    elif m.data == "show_poll":
        poll_voters = getDB.get("poll_voters", [])
        
        if m.from_user.id in poll_voters:
            poll_results = getDB.get("poll_results", {"positive": 0, "negative": 0})
            await m.answer(
                f"✅ شكراً! لقد صوّت مسبقاً\n\n"
                f"النتائج الحالية:\n"
                f"👍 إيجابي: {poll_results.get('positive', 0)}\n"
                f"👎 سلبي: {poll_results.get('negative', 0)}",
                show_alert=True
            )
        else:
            poll_results = getDB.get("poll_results", {"positive": 0, "negative": 0})
            await m.edit_message_text(
                f"📊 **استطلاع رأي**\n\n"
                f"كيف كانت تجربتك مع البوت؟\n\n"
                f"النتائج الحالية:\n"
                f"👍 إيجابي: {poll_results.get('positive', 0)}\n"
                f"👎 سلبي: {poll_results.get('negative', 0)}",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("👍 إيجابي", callback_data="vote_positive"),
                        InlineKeyboardButton("👎 سلبي", callback_data="vote_negative")
                    ],
                    [InlineKeyboardButton("رجوع", callback_data="back_to_main")]
                ])
            )
    
    elif m.data == "vote_positive":
        poll_voters = getDB.get("poll_voters", [])
        
        if m.from_user.id in poll_voters:
            await m.answer("✅ لقد صوّت مسبقاً!", show_alert=True)
        else:
            data = getDB
            poll_results = data.get("poll_results", {"positive": 0, "negative": 0})
            poll_results["positive"] = poll_results.get("positive", 0) + 1
            data["poll_results"] = poll_results
            
            poll_voters = data.get("poll_voters", [])
            poll_voters.append(m.from_user.id)
            data["poll_voters"] = poll_voters
            
            botdb.set("db" + token.split(":")[0], data)
            
            await m.answer("✅ شكراً لتصويتك الإيجابي!", show_alert=True)
            
            await m.edit_message_text(
                f"📊 **استطلاع رأي**\n\n"
                f"شكراً لمشاركتك!\n\n"
                f"النتائج:\n"
                f"👍 إيجابي: {poll_results['positive']}\n"
                f"👎 سلبي: {poll_results.get('negative', 0)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("رجوع", callback_data="back_to_main")]
                ])
            )
    
    elif m.data == "vote_negative":
        poll_voters = getDB.get("poll_voters", [])
        
        if m.from_user.id in poll_voters:
            await m.answer("✅ لقد صوّت مسبقاً!", show_alert=True)
        else:
            data = getDB
            poll_results = data.get("poll_results", {"positive": 0, "negative": 0})
            poll_results["negative"] = poll_results.get("negative", 0) + 1
            data["poll_results"] = poll_results
            
            poll_voters = data.get("poll_voters", [])
            poll_voters.append(m.from_user.id)
            data["poll_voters"] = poll_voters
            
            botdb.set("db" + token.split(":")[0], data)
            
            await m.answer("✅ شكراً لتصويتك! سنعمل على التحسين", show_alert=True)
            
            await m.edit_message_text(
                f"📊 **استطلاع رأي**\n\n"
                f"شكراً لمشاركتك!\n\n"
                f"النتائج:\n"
                f"👍 إيجابي: {poll_results.get('positive', 0)}\n"
                f"👎 سلبي: {poll_results['negative']}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("رجوع", callback_data="back_to_main")]
                ])
            )

    # Banned words management
    elif m.data == "banned_words_management" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        banned_words = getDB.get("banned_words", [])
        
        words_text = ""
        for word in banned_words:
            words_text += f"• {word}\n"
        
        if not words_text:
            words_text = "لا توجد كلمات ممنوعة"
        
        await m.edit_message_text(
            f"🚫 **الكلمات الممنوعة**\n\n{words_text}\n\n**العدد:** {len(banned_words)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ إضافة كلمة", callback_data="add_banned_word")],
                [InlineKeyboardButton("➖ حذف كلمة", callback_data="remove_banned_word")],
                [InlineKeyboardButton("🗑️ مسح الكل", callback_data="clear_banned_words")],
                [InlineKeyboardButton("رجوع", callback_data="back")]
            ])
        )
    
    elif m.data == "add_banned_word" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "➕ **إضافة كلمة ممنوعة**\n\nأرسل الكلمة:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("رجوع", callback_data="banned_words_management")
            ]])
        )
        botdb.set(f"add_banned_word:{m.from_user.id}", True)
    
    elif m.data == "remove_banned_word" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        banned_words = getDB.get("banned_words", [])
        
        if not banned_words:
            await m.answer("❌ لا توجد كلمات ممنوعة", show_alert=True)
            return
        
        buttons_list = []
        for word in banned_words:
            buttons_list.append([
                InlineKeyboardButton(f"🗑️ {word}", callback_data=f"delete_word_{word}")
            ])
        
        buttons_list.append([
            InlineKeyboardButton("رجوع", callback_data="banned_words_management")
        ])
        
        await m.edit_message_text(
            "🗑️ **حذف كلمة**\n\nاختر الكلمة المراد حذفها:",
            reply_markup=InlineKeyboardMarkup(buttons_list)
        )
    
    elif m.data.startswith("delete_word_") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        word = m.data.replace("delete_word_", "")
        data = getDB
        banned_words = data.get("banned_words", [])
        
        if word in banned_words:
            banned_words.remove(word)
            data["banned_words"] = banned_words
            botdb.set("db" + token.split(":")[0], data)
            
            await m.answer("✅ تم حذف الكلمة", show_alert=True)
            await m.edit_message_text(
                "✅ **تم حذف الكلمة بنجاح**",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("رجوع", callback_data="banned_words_management")
                ]])
            )
        else:
            await m.answer("❌ الكلمة غير موجودة", show_alert=True)
    
    elif m.data == "clear_banned_words" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        data = getDB
        data["banned_words"] = []
        botdb.set("db" + token.split(":")[0], data)
        
        await m.answer("✅ تم مسح جميع الكلمات", show_alert=True)
        await m.edit_message_text(
            "✅ **تم مسح جميع الكلمات الممنوعة**",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("رجوع", callback_data="banned_words_management")
            ]])
        )

    # Sessions management
    elif m.data == "sessions_management" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        sessions = getDB.get("sessions", [])
        active_name = getDB.get("current_session_name")
        active_meta = None
        if active_name:
            active_meta = next((m for m in session_meta if m.get("name") == active_name), None)

        current_info = ""
        if active_name:
            status = "✅ جاهزة"
            if active_meta and active_meta.get("banned"):
                status = "🚫 محظورة"
            elif active_meta and active_meta.get("flood_until", 0) > time.time():
                status = "⏳ في انتظار"

            current_info = f"🔹 الجلسة الحالية: {active_name} ({status})\n"
            if active_meta:
                current_info += f"   🔢 الاستخدام: {active_meta.get('usage', 0)} / {_get_global_session_max_usage()}\n\n"
            else:
                current_info += "\n"

        sessions_text = ""
        session_buttons = []
        for i, session in enumerate(sessions, 1):
            status_icon = "🔵"
            meta = next((m for m in session_meta if m.get("name") == session.get("name")), None)
            if meta:
                if meta.get("banned"):
                    status_icon = "🚫"
                elif meta.get("flood_until", 0) > time.time():
                    status_icon = "⏳"
                elif session.get("name") == active_name:
                    status_icon = "✅"

            usage = meta.get("usage", 0) if meta else session.get("usage_count", 0)
            sessions_text += f"{status_icon} {i}. {session['name']} - {session['phone']} ({usage} استخدام)\n"
            session_buttons.append([
                InlineKeyboardButton(
                    f"{status_icon} {session['name']}",
                    callback_data=f"activate_session_{session['name']}"
                )
            ])

        if not sessions_text:
            sessions_text = "لا توجد جلسات"

        base_buttons = [
            [
                InlineKeyboardButton("➕ إضافة جلسة",
                                     callback_data="add_session")
            ],
            [
                InlineKeyboardButton("➖ حذف جلسة",
                                     callback_data="remove_session")
            ],
            [
                InlineKeyboardButton("⚙️ حد التحويل",
                                     callback_data="set_session_threshold"),
                InlineKeyboardButton("🔄 تحديث",
                                     callback_data="sessions_management")
            ],
            [InlineKeyboardButton("رجوع", callback_data="back")]
        ]

        await m.edit_message_text(
            f"🔐 **إدارة الجلسات**\n\n{current_info}{sessions_text}\n\n**عدد الجلسات:** {len(sessions)}\n\nاضغط على اسم الجلسة لتعيينها كجلسة نشطة.",
            reply_markup=InlineKeyboardMarkup(session_buttons + base_buttons))

    elif m.data == "add_session" and (m.from_user.id == ownerID
                                      or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "➕ **إضافة جلسة جديدة**\n\nانقر على الزر أدناه لبدء تسجيل الدخول:",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("🔐 بدء تسجيل الدخول",
                                         callback_data="start_login_session")
                ],
                 [
                     InlineKeyboardButton("رجوع",
                                          callback_data="sessions_management")
                 ]]))

    elif m.data == "start_login_session" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "🔐 **تسجيل دخول جلسة جديدة**\n\n"
            "أرسل رقم الهاتف مع رمز الدولة\n"
            "**مثال:** +964771234567",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("إلغاء",
                                     callback_data="sessions_management")
            ]]))

        # Store login state
        data = botdb.get("db" + token.split(":")[0])
        login_states = data.get("login_states", {})
        login_states[str(m.from_user.id)] = {"step": "phone", "data": {}}
        data["login_states"] = login_states
        botdb.set("db" + token.split(":")[0], data)

    elif m.data == "set_session_threshold" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "⚙️ **تعيين حد التحويل للجلسات**\n\nأرسل العدد (مثال: 150):",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="sessions_management")]]))
        botdb.set(f"session_threshold:{m.from_user.id}", True)

    elif m.data == "remove_session" and (m.from_user.id == ownerID
                                         or m.from_user.id in getDB["admins"]):
        sessions = getDB.get("sessions", [])

        if not sessions:
            await m.answer("❌ لا توجد جلسات", show_alert=True)
            return

        buttons_list = []
        for session in sessions:
            buttons_list.append([
                InlineKeyboardButton(
                    f"🗑️ {session['name']} ({session['phone']})",
                    callback_data=f"delete_session_{session['name']}")
            ])

        buttons_list.append([
            InlineKeyboardButton("رجوع", callback_data="sessions_management")
        ])

        await m.edit_message_text(
            "🗑️ **حذف جلسة**\n\nاختر الجلسة:",
            reply_markup=InlineKeyboardMarkup(buttons_list))

    elif m.data.startswith("delete_session_") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        session_name = m.data.replace("delete_session_", "")
        data = getDB
        sessions = data.get("sessions", [])

        data["sessions"] = [s for s in sessions if s["name"] != session_name]
        botdb.set("db" + token.split(":")[0], data)

        # Reload sessions
        global session_clients
        session_clients = []
        await load_session_clients()

        await m.answer("✅ تم حذف الجلسة", show_alert=True)
        await m.edit_message_text("✅ **تم حذف الجلسة بنجاح**",
                                  reply_markup=InlineKeyboardMarkup([[
                                      InlineKeyboardButton(
                                          "رجوع",
                                          callback_data="sessions_management")
                                  ]]))

    elif m.data.startswith("activate_session_") and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        session_name = m.data.replace("activate_session_", "")
        if activate_session_by_name(session_name):
            await m.answer("✅ تم تعيين الجلسة الحالية", show_alert=True)
            await m.edit_message_text(
                f"✅ تم تعيين الجلسة {session_name} كجلسة نشطة الآن.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("رجوع",
                                         callback_data="sessions_management")
                ]]))
        else:
            await m.answer("❌ الجلسة غير موجودة", show_alert=True)

    # Existing callbacks
    elif m.data == "broadcast" and (m.from_user.id == ownerID
                                    or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "• أرسل الإذاعة الآن",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]))
        botdb.set(f"broad:{m.from_user.id}", True)

    elif m.data == "update_bot" and (m.from_user.id == ownerID
                                     or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "🔄 **تحديث البوت**\n\nأرسل ملف Python (.py)",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]))
        botdb.set(f"update:{m.from_user.id}", True)

    elif m.data == "stats" and (m.from_user.id == ownerID
                                or m.from_user.id in getDB["admins"]):
        users_count = len(getDB["users"])
        vip_count = len(getDB.get("vip_users", {}))
        banned_count = len(getDB.get("banned", []))
        temp_banned_count = len(getDB.get("temporary_bans", {}))

        # حساب التحميلات اليوم
        today_total = 0
        user_downloads = getDB.get("user_downloads", {})
        for user_data in user_downloads.values():
            today_total += user_data.get("today", 0)

        # حساب التحميلات الكلية
        total_downloads = 0
        for user_data in user_downloads.values():
            total_downloads += user_data.get("total", 0)

        daily_attempts = getDB.get("daily_attempts_limit", 10)
        referral_bonus = getDB.get("referral_bonus", 10)
        
        # احصائيات القنوات
        channels_stats = ""
        channel_stats_data = getDB.get("channel_join_stats", {})
        for channel, stats in channel_stats_data.items():
            joined = len(stats.get("joined", []))
            left = len(stats.get("left", []))
            channels_stats += f"• {channel}: انضم {joined} | غادر {left}\n"

        await m.edit_message_text(
            f"📊 **إحصائيات البوت**\n\n"
            f"👥 عدد المستخدمين: {users_count}\n"
            f"👑 عدد VIP: {vip_count}\n"
            f"🚫 المحظورين: {banned_count}\n"
            f"⏱️ حظر مؤقت: {temp_banned_count}\n"
            f"📥 التحميلات اليوم: {today_total}\n"
            f"📈 التحميلات الكلية: {total_downloads}\n"
            f"🎯 المحاولات اليومية: {daily_attempts}\n"
            f"🎁 مكافأة الإحالة: {referral_bonus}\n"
            f"\n📋 **احصائيات القنوات:**\n{channels_stats if channels_stats else 'لا توجد احصائيات'}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "adminstats" and (m.from_user.id == ownerID
                                     or m.from_user.id in getDB["admins"]):
        admins = getDB.get("admins", [])
        admins_text = ""
        for admin_id in admins:
            admin_data = botdb.get(f"USER:{admin_id}")
            if admin_data:
                admins_text += f"• {admin_data.get('name', 'غير معروف')} (`{admin_id}`)\n"
            else:
                admins_text += f"• `{admin_id}`\n"

        if not admins_text:
            admins_text = "لا يوجد أدمنية"

        await m.edit_message_text(
            f"👥 **الأدمنية**\n\n{admins_text}\n\n**العدد:** {len(admins)}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "bannedstats" and (m.from_user.id == ownerID
                                      or m.from_user.id in getDB["admins"]):
        banned = getDB.get("banned", [])
        banned_text = ""
        for banned_id in banned[:20]:  # عرض أول 20 فقط
            banned_data = botdb.get(f"USER:{banned_id}")
            if banned_data:
                banned_text += f"• {banned_data.get('name', 'غير معروف')} (`{banned_id}`)\n"
            else:
                banned_text += f"• `{banned_id}`\n"

        if not banned_text:
            banned_text = "لا يوجد محظورين"

        await m.edit_message_text(
            f"🚫 **المحظورين**\n\n{banned_text}\n\n**العدد الكلي:** {len(banned)}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "channels" and (m.from_user.id == ownerID
                                   or m.from_user.id in getDB["admins"]):
        channels = getDB.get("channels", [])
        channels_text = "\n".join([f"• {ch}" for ch in channels
                                   ]) if channels else "لا توجد قنوات"

        await m.edit_message_text(
            f"📢 **القنوات الإجبارية**\n\n{channels_text}",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("➕ إضافة قناة",
                                         callback_data="add_channel")
                ],
                 [
                     InlineKeyboardButton("➖ حذف قناة",
                                          callback_data="remove_channel")
                 ], [InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "add_channel" and (m.from_user.id == ownerID
                                      or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "➕ **إضافة قناة**\n\nأرسل معرف القناة (مثال: @channel)",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="channels")]]))
        botdb.set(f"addchannel:{m.from_user.id}", True)

    elif m.data == "remove_channel" and (m.from_user.id == ownerID
                                         or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "➖ **حذف قناة**\n\nأرسل معرف القناة (مثال: @channel)",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="channels")]]))
        botdb.set(f"removechannel:{m.from_user.id}", True)

    elif m.data == "funding_management" and (m.from_user.id == ownerID
                                             or m.from_user.id in getDB["admins"]):
        funding_channels = get_funding_channels()
        channels = getDB.get("channels", [])
        funding_text = ""
        
        for channel, data in funding_channels.items():
            current = data['current']
            goal = data['goal']
            progress = f"{current}/{goal}"
            percentage = (current / goal * 100) if goal > 0 else 0
            status = "✅ مكتمل" if not data.get("active", True) else f"🔄 {percentage:.0f}%"
            funding_text += f"• {channel}\n  الهدف: {progress} {status}\n"
        
        if not funding_text:
            funding_text = "لا توجد قنوات تمويل حالياً"
        
        funding_text += f"\n\n📊 **القنوات الإجبارية**: {len(channels)} قناة"

        await m.edit_message_text(
            f"💰 **نظام التمويل**\n\n{funding_text}",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("➕ إضافة قناة تمويل",
                                         callback_data="add_funding_channel")
                ],
                 [
                     InlineKeyboardButton("➖ حذف قناة تمويل",
                                          callback_data="remove_funding_channel")
                 ], [InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "add_funding_channel" and (m.from_user.id == ownerID
                                              or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "➕ **إضافة قناة تمويل**\n\n**ستضاف للقنوات الإجبارية مؤقتاً حتى تصل للهدف**\n\nأرسل معرف القناة (مثال: @channel)",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="funding_management")]]))
        botdb.set(f"funding_channel_name:{m.from_user.id}", True)

    elif m.data == "remove_funding_channel" and (m.from_user.id == ownerID
                                                 or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "➖ **حذف قناة تمويل**\n\nأرسل معرف القناة (مثال: @channel)",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="funding_management")]]))
        botdb.set(f"remove_funding:{m.from_user.id}", True)

    elif m.data == "subscription_rewards" and (m.from_user.id == ownerID
                                               or m.from_user.id in getDB["admins"]):
        bonus_attempts = getDB.get("subscription_bonus_attempts", 5)
        temp_ban_duration = getDB.get("subscription_temp_ban_duration", 3600)

        await m.edit_message_text(
            f"🎁 **مكافآت الاشتراك**\n\n"
            f"🎯 محاولات المكافأة: {bonus_attempts}\n"
            f"⏱️ مدة الحظر المؤقت: {temp_ban_duration // 60} دقيقة\n\n"
            f"عند اشتراك المستخدم بجميع القنوات يحصل على {bonus_attempts} محاولات إضافية\n"
            f"إذا غادر قناة سيحصل على حظر مؤقت لمدة {temp_ban_duration // 60} دقيقة",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("🎯 تعديل المحاولات",
                                         callback_data="set_bonus_attempts")
                ],
                 [
                     InlineKeyboardButton("⏱️ تعديل مدة الحظر",
                                          callback_data="set_temp_ban_duration")
                 ], [InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "set_bonus_attempts" and (m.from_user.id == ownerID
                                             or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "🎯 **تعديل محاولات المكافأة**\n\nأرسل العدد الجديد",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="subscription_rewards")]]))
        botdb.set(f"set_bonus_attempts:{m.from_user.id}", True)

    elif m.data == "set_temp_ban_duration" and (m.from_user.id == ownerID
                                                or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "⏱️ **تعديل مدة الحظر المؤقت**\n\nأرسل المدة بالثواني",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="subscription_rewards")]]))
        botdb.set(f"set_temp_ban_duration:{m.from_user.id}", True)

    elif m.data == "auto_delete_management" and (m.from_user.id == ownerID
                                                 or m.from_user.id in getDB["admins"]):
        auto_delete_enabled = getDB.get("auto_delete_enabled", False)
        auto_delete_timeout = getDB.get("auto_delete_timeout", 180)
        status = "✅ مفعّل" if auto_delete_enabled else "❌ معطّل"

        await m.edit_message_text(
            f"🗑️ **إدارة حذف المحتوى**\n\n"
            f"الحالة: {status}\n"
            f"مدة الانتظار: {auto_delete_timeout} ثانية\n\n"
            f"سيتم حذف المحتوى تلقائياً بعد إرسال الرسالة بالمدة المحددة",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("🔄 تبديل الحالة",
                                         callback_data="toggle_auto_delete")
                ],
                 [
                     InlineKeyboardButton("⏱️ تعديل المدة",
                                          callback_data="set_auto_delete_timeout")
                 ], [InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "toggle_auto_delete" and (m.from_user.id == ownerID
                                             or m.from_user.id in getDB["admins"]):
        getDB["auto_delete_enabled"] = not getDB.get("auto_delete_enabled", False)
        botdb.set("db" + token.split(":")[0], getDB)
        status = "✅ مفعّل" if getDB.get("auto_delete_enabled") else "❌ معطّل"
        
        await m.answer(f"تم تبديل الحالة إلى: {status}", show_alert=True)
        await m.edit_message_text(
            f"🗑️ **إدارة حذف المحتوى**\n\n"
            f"الحالة: {status}\n"
            f"مدة الانتظار: {getDB.get('auto_delete_timeout', 180)} ثانية",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("🔄 تبديل الحالة",
                                         callback_data="toggle_auto_delete")
                ],
                 [
                     InlineKeyboardButton("⏱️ تعديل المدة",
                                          callback_data="set_auto_delete_timeout")
                 ], [InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "set_auto_delete_timeout" and (m.from_user.id == ownerID
                                                  or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "⏱️ **تعديل مدة الحذف**\n\nأرسل المدة بالثواني (مثال: 180 للـ 3 دقائق)",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="auto_delete_management")]]))
        botdb.set(f"set_auto_delete_timeout:{m.from_user.id}", True)

    elif m.data == "vip" and (m.from_user.id == ownerID
                              or m.from_user.id in getDB["admins"]):
        vip_users = getDB.get("vip_users", {})
        vip_text = ""
        for user_id, expiry in list(vip_users.items())[:20]:
            user_data = botdb.get(f"USER:{user_id}")
            name = user_data.get('name',
                                 'غير معروف') if user_data else 'غير معروف'
            vip_text += f"• {name} (`{user_id}`) - {expiry}\n"

        if not vip_text:
            vip_text = "لا يوجد مستخدمين VIP"

        await m.edit_message_text(
            f"👑 **مستخدمي VIP**\n\n{vip_text}\n\n**العدد:** {len(vip_users)}",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "referral" and (m.from_user.id == ownerID
                                   or m.from_user.id in getDB["admins"]):
        current_bonus = getDB.get("referral_bonus", 10)
        await m.edit_message_text(
            f"🎁 **نظام الإحالة**\n\nالمكافأة الحالية: {current_bonus} محاولة",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⚙️ تعيين المكافأة",
                                     callback_data="set_referral")
            ], [InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "set_referral" and (m.from_user.id == ownerID
                                       or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "🎁 **تعيين مكافأة الإحالة**\n\nأرسل العدد:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="referral")]]))
        botdb.set(f"referral_bonus:{m.from_user.id}", True)

    elif m.data == "welcome_msg" and (m.from_user.id == ownerID
                                      or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "📝 **رسالة الترحيب**\n\nاختر نوع الرسالة:",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("👥 رسالة المستخدمين",
                                         callback_data="edit_welcome")
                ],
                 [
                     InlineKeyboardButton("👑 رسالة VIP",
                                          callback_data="edit_vip_welcome")
                 ], [InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "edit_welcome" and (m.from_user.id == ownerID
                                       or m.from_user.id in getDB["admins"]):
        current_msg = getDB.get("welcome_message", "لا توجد رسالة")
        await m.edit_message_text(
            f"📝 **رسالة الترحيب الحالية:**\n\n{current_msg}\n\n**أرسل الرسالة الجديدة:**",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="welcome_msg")]]))
        botdb.set(f"welcome:{m.from_user.id}", True)

    elif m.data == "edit_vip_welcome" and (m.from_user.id == ownerID or
                                           m.from_user.id in getDB["admins"]):
        current_msg = getDB.get("vip_welcome_message", "لا توجد رسالة")
        await m.edit_message_text(
            f"👑 **رسالة VIP الحالية:**\n\n{current_msg}\n\n**أرسل الرسالة الجديدة:**",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="welcome_msg")]]))
        botdb.set(f"vip_welcome:{m.from_user.id}", True)

    elif m.data == "daily_attempts" and (m.from_user.id == ownerID
                                         or m.from_user.id in getDB["admins"]):
        current_limit = getDB.get("daily_attempts_limit", 10)
        await m.edit_message_text(
            f"🎯 **المحاولات اليومية**\n\nالحد الحالي: {current_limit}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("تعيين", callback_data="set_attempts")
            ], [InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "set_attempts" and (m.from_user.id == ownerID
                                       or m.from_user.id in getDB["admins"]):
        await m.edit_message_text("🎯 أرسل العدد:",
                                  reply_markup=InlineKeyboardMarkup([[
                                      InlineKeyboardButton(
                                          "رجوع",
                                          callback_data="daily_attempts")
                                  ]]))
        botdb.set(f"attempts:{m.from_user.id}", True)

    elif m.data == "sleep_settings" and (m.from_user.id == ownerID
                                         or m.from_user.id in getDB["admins"]):
        current_sleep = getDB.get("sleep_duration", 2)
        await m.edit_message_text(
            f"⏱️ **إعدادات السليب**\n\nالمدة الحالية: {current_sleep} ثانية",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⚙️ تعيين المدة",
                                     callback_data="set_sleep")
            ], [InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "set_sleep" and (m.from_user.id == ownerID
                                    or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "⏱️ **تعيين مدة السليب**\n\nأرسل المدة بالثواني:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("رجوع", callback_data="sleep_settings")
            ]]))
        botdb.set(f"sleep_duration:{m.from_user.id}", True)

    elif m.data == "maintenance_mode" and (m.from_user.id == ownerID or
                                           m.from_user.id in getDB["admins"]):
        current_mode = getDB.get("maintenance_mode", False)
        status_text = "🟢 مفعل" if current_mode else "🔴 معطل"

        await m.edit_message_text(
            f"🔧 **وضع الصيانة**\n\nالحالة: {status_text}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔴 تعطيل" if current_mode else "🟢 تفعيل",
                                     callback_data="toggle_maintenance")
            ], [InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "toggle_maintenance" and (
            m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        data = getDB
        current_mode = data.get("maintenance_mode", False)
        data["maintenance_mode"] = not current_mode
        botdb.set("db" + token.split(":")[0], data)

        await m.answer("✅ تم التفعيل" if not current_mode else "✅ تم التعطيل",
                       show_alert=True)

        status_text = "🟢 مفعل" if not current_mode else "🔴 معطل"
        await m.edit_message_text(
            f"🔧 **وضع الصيانة**\n\nالحالة: {status_text}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "🔴 تعطيل" if not current_mode else "🟢 تفعيل",
                    callback_data="toggle_maintenance")
            ], [InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "developer":
        back_button = InlineKeyboardButton(
            "≈ رجوع ≈", callback_data="back") if (
                m.from_user.id == ownerID or m.from_user.id
                in getDB["admins"]) else InlineKeyboardButton(
                    "• رجوع •", callback_data="back_to_main")

        await m.edit_message_text(f"👨‍💻 **المطور**\n\n🆔 @DIFlY1",
                                  reply_markup=InlineKeyboardMarkup([[
                                      InlineKeyboardButton(
                                          "📧 تواصل",
                                          url="https://t.me/DIFlY1")
                                  ], [back_button]]))

    elif m.data == "my_info":
        try:
            vip_status = "👑 VIP" if is_vip(m.from_user.id) else "❌ عادي"
            can_use, remaining = check_daily_attempts(m.from_user.id)
            points = get_user_points(m.from_user.id)
            total_downloads, today_downloads = get_download_stats(
                m.from_user.id)

            username = f"@{m.from_user.username}" if m.from_user.username else "لا يوجد"

            info_text = f"👤 **معلوماتك**\n\n"
            info_text += f"📛 الاسم: {m.from_user.first_name}\n"
            info_text += f"🆔 الآيدي: `{m.from_user.id}`\n"
            info_text += f"👤 اليوزر: {username}\n"
            info_text += f"👑 الحالة: {vip_status}\n"
            info_text += f"🎯 المحاولات المتبقية: {remaining if not is_vip(m.from_user.id) else '∞'}\n"
            info_text += f"💎 النقاط: {points}\n"
            info_text += f"📊 التحميلات اليوم: {today_downloads}\n"
            info_text += f"📈 إجمالي التحميلات: {total_downloads}"

            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 استبدال النقاط",
                                     callback_data="exchange_points")
            ], [InlineKeyboardButton("رجوع", callback_data="back_to_main")]])

            # Try to get profile photo
            try:
                photos = await bot.get_profile_photos(m.from_user.id, limit=1)
                if photos.total_count > 0:
                    await m.message.delete()
                    await bot.send_photo(chat_id=m.from_user.id,
                                         photo=photos.photos[0][0].file_id,
                                         caption=info_text,
                                         reply_markup=keyboard)
                else:
                    await m.edit_message_text(info_text, reply_markup=keyboard)
            except:
                await m.edit_message_text(info_text, reply_markup=keyboard)

        except Exception as e:
            print(f"Error in my_info: {e}")
            await m.answer("❌ حدث خطأ", show_alert=True)

    elif m.data == "request_vip":
        await m.edit_message_text(
            "👑 **طلب VIP**\n\nتواصل مع: @ITS_aboody",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📞 راسل", url="https://t.me/ITS_aboody")
            ], [InlineKeyboardButton("رجوع", callback_data="my_info")]]))

    elif m.data == "exchange_points":
        points = get_user_points(m.from_user.id)
        data = botdb.get("db" + token.split(":")[0])
        rate = data.get("points_system", {}).get("points_to_attempts_rate",
                                                 100)
        possible_attempts = points // rate

        if possible_attempts == 0:
            insufficient_msg = data.get("messages", {}).get(
                "insufficient_points", "❌ لا تملك نقاط كافية")
            await m.answer(
                f"{insufficient_msg}\n\nتحتاج {rate} نقطة على الأقل",
                show_alert=True)
            return

        await m.edit_message_text(
            f"💎 **استبدال النقاط**\n\n"
            f"نقاطك الحالية: {points}\n"
            f"المعدل: {rate} نقطة = محاولة واحدة\n"
            f"يمكنك الحصول على: {possible_attempts} محاولة",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ استبدال",
                                     callback_data="confirm_exchange")
            ], [InlineKeyboardButton("رجوع", callback_data="my_info")]]))

    elif m.data == "confirm_exchange":
        success, points_used, attempts_added = exchange_points_for_attempts(
            m.from_user.id)

        if success:
            data = botdb.get("db" + token.split(":")[0])
            success_msg = data.get("messages", {}).get(
                "points_exchanged",
                "✅ تم استبدال {points} نقطة بـ {attempts} محاولة")
            success_msg = success_msg.format(points=points_used,
                                             attempts=attempts_added)
            await m.answer(success_msg, show_alert=True)
        else:
            data = botdb.get("db" + token.split(":")[0])
            fail_msg = data.get("messages", {}).get("insufficient_points",
                                                    "❌ لا تملك نقاط كافية")
            await m.answer(fail_msg, show_alert=True)

        # Refresh info
        await m.message.delete()
        await bot.send_message(m.from_user.id,
                               "اضغط على معلوماتي لرؤية التحديثات",
                               reply_markup=get_regular_keyboard()
                               if not is_vip(m.from_user.id) else VIP_KEYBOARD)

    elif m.data == "back_to_main":
        vip_status = "👑 VIP" if is_vip(m.from_user.id) else ""
        username = f"@{m.from_user.username}" if m.from_user.username else "لا يوجد"
        referral_link = f"https://t.me/{bot.me.username}?start={m.from_user.id}"
        referral_bonus = getDB.get("referral_bonus", 10)
        can_use, remaining = check_daily_attempts(m.from_user.id)
        points = get_user_points(m.from_user.id)

        # حساب العدد الكلي للمستخدمين
        total_users = len(getDB["users"])

        # حساب التحميلات الكلية
        total_downloads = 0
        user_downloads_data = getDB.get("user_downloads", {})
        for user_data in user_downloads_data.values():
            total_downloads += user_data.get("total", 0)

        if is_vip(m.from_user.id):
            welcome_msg = getDB.get("vip_welcome_message", "**👑 أهلاً وسهلاً بك**")
            keyboard = VIP_KEYBOARD
        else:
            welcome_msg = getDB.get("welcome_message", "**👋 أهلاً بك**")
            keyboard = get_regular_keyboard()

        formatted_msg = welcome_msg.format(user_name=m.from_user.first_name,
                                           vip_status=vip_status,
                                           user_id=m.from_user.id,
                                           username=username,
                                           remaining_attempts=remaining if
                                           not is_vip(m.from_user.id) else "∞",
                                           referral_link=referral_link,
                                           referral_bonus=referral_bonus,
                                           points=points,
                                           total_users=total_users,
                                           total_downloads=total_downloads)

        await m.edit_message_text(formatted_msg, reply_markup=keyboard)

    elif m.data == "whois" and (m.from_user.id == ownerID
                                or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "🔍 **كشف مستخدم**\n\nأرسل الآيدي أو اليوزر:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]))
        botdb.set(f"whois:{m.from_user.id}", True)

    elif m.data == "ban" and (m.from_user.id == ownerID
                              or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "🚫 **حظر مستخدم**\n\nأرسل الآيدي أو اليوزر:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]))
        botdb.set(f"ban:{m.from_user.id}", True)

    elif m.data == "unban" and (m.from_user.id == ownerID
                                or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "✅ **إلغاء حظر مستخدم**\n\nأرسل الآيدي أو اليوزر:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]))
        botdb.set(f"unban:{m.from_user.id}", True)

    elif m.data == "addadmin" and m.from_user.id == ownerID:
        await m.edit_message_text(
            "👥 **رفع أدمن**\n\nأرسل الآيدي:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]))
        botdb.set(f"add:{m.from_user.id}", True)

    elif m.data == "remadmin" and m.from_user.id == ownerID:
        await m.edit_message_text(
            "👥 **تنزيل أدمن**\n\nأرسل الآيدي:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]))
        botdb.set(f"rem:{m.from_user.id}", True)

    elif m.data == "usebot" and (m.from_user.id == ownerID
                                 or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(
            "• يمكنك الآن استخدام البوت",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="back")]]))

    elif m.data == "back" and (m.from_user.id == ownerID
                               or m.from_user.id in getDB["admins"]):
        await m.edit_message_text(f"**• أهلاً بك ⌯ {m.from_user.mention}**",
                                  reply_markup=STARTKEY)

    # VIP callbacks
    elif m.data == "single_story" and is_vip(m.from_user.id):
        await m.edit_message_text(
            "👑 **تحميل ستوري**\n\nأرسل اليوزر أو الرابط:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع",
                                       callback_data="back_to_main")]]))
        botdb.set(f"vip_single:{m.from_user.id}", True)

    elif m.data == "download_all_stories" and is_vip(m.from_user.id):
        await m.edit_message_text(
            "👑 **تحميل الكل**\n\nأرسل اليوزر:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع",
                                       callback_data="back_to_main")]]))
        botdb.set(f"vip_all:{m.from_user.id}", True)

    elif m.data == "download_profile" and is_vip(m.from_user.id):
        await m.edit_message_text(
            "👑 **جلب معلومات**\n\nأرسل اليوزر:",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع",
                                       callback_data="back_to_main")]]))
        botdb.set(f"vip_profile:{m.from_user.id}", True)

    elif m.data == "story_monitoring" and is_vip(m.from_user.id):
        monitoring_list = get_monitoring_list(m.from_user.id)
        monitoring_text = "\n".join([
            f"• {target}" for target in monitoring_list
        ]) if monitoring_list else "لا توجد حسابات"

        await m.edit_message_text(
            f"📡 **المراقبة**\n\n{monitoring_text}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("➕ إضافة", callback_data="monitor_add")
            ], [
                InlineKeyboardButton("➖ حذف", callback_data="monitor_remove")
            ], [InlineKeyboardButton("رجوع", callback_data="back_to_main")]]))

    elif m.data == "monitor_add" and is_vip(m.from_user.id):
        await m.edit_message_text("➕ أرسل اليوزر:",
                                  reply_markup=InlineKeyboardMarkup([[
                                      InlineKeyboardButton(
                                          "رجوع",
                                          callback_data="story_monitoring")
                                  ]]))
        botdb.set(f"monitor_add:{m.from_user.id}", True)

    elif m.data == "monitor_remove" and is_vip(m.from_user.id):
        monitoring_list = get_monitoring_list(m.from_user.id)
        if not monitoring_list:
            await m.answer("❌ لا توجد حسابات", show_alert=True)
            return

        await m.edit_message_text("➖ أرسل اليوزر:",
                                  reply_markup=InlineKeyboardMarkup([[
                                      InlineKeyboardButton(
                                          "رجوع",
                                          callback_data="story_monitoring")
                                  ]]))
        botdb.set(f"monitor_remove:{m.from_user.id}", True)

    elif m.data == "referral_trend" and (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        leaderboard = get_referral_leaderboard()
        
        if not leaderboard:
            await m.edit_message_text(
                "🔥 **ترند الدعوات**\n\nلا توجد دعوات حالياً",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎁 منح المكافآت الأسبوعية", callback_data="grant_weekly_bonuses")],
                    [InlineKeyboardButton("رجوع", callback_data="back")]
                ])
            )
            return
        
        trend_text = "🔥 **ترند الدعوات**\n\n"
        for i, (user_id, count) in enumerate(leaderboard, 1):
            user_data = botdb.get(f"USER:{user_id}")
            name = user_data.get('name', 'غير معروف') if user_data else 'غير معروف'
            trend_text += f"{i}. {name} - {count} دعوة\n"
        
        await m.edit_message_text(
            trend_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎁 منح المكافآت الأسبوعية", callback_data="grant_weekly_bonuses")],
                [InlineKeyboardButton("رجوع", callback_data="back")]
            ])
        )

    elif m.data == "grant_weekly_bonuses" and (m.from_user.id == ownerID or m.from_user.id in getDB["admins"]):
        success = grant_weekly_referral_bonuses()
        if success:
            await m.answer("✅ تم منح المكافآت الأسبوعية!", show_alert=True)
        else:
            await m.answer("❌ تم منح المكافآت بالفعل هذا الأسبوع", show_alert=True)
        
        # Refresh the trend
        leaderboard = get_referral_leaderboard()
        if leaderboard:
            trend_text = "🔥 **ترند الدعوات**\n\n"
            for i, (user_id, count) in enumerate(leaderboard, 1):
                user_data = botdb.get(f"USER:{user_id}")
                name = user_data.get('name', 'غير معروف') if user_data else 'غير معروف'
                trend_text += f"{i}. {name} - {count} دعوة\n"
            
            await m.edit_message_text(
                trend_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎁 منح المكافآت الأسبوعية", callback_data="grant_weekly_bonuses")],
                    [InlineKeyboardButton("رجوع", callback_data="back")]
                ])
            )

    else:
        try:
            await m.answer("❌ غير متاح", show_alert=True)
        except:
            pass


def clear_admin_states(user_id, exclude=None):
    states = [
        "broad", "whois", "ban", "add", "unban", "rem", "addchannel",
        "removechannel", "welcome", "vip_welcome", "attempts",
        "referral_bonus", "sleep_duration", "update", "vip_single", "vip_all",
        "vip_profile", "monitor_add", "monitor_remove", "custom_btn_text",
        "custom_btn_content", "points_per_channel", "exchange_rate",
        "add_attempts_admin", "add_points_admin", "add_banned_word",
        "create_vip_code", "delete_vip_code", "vip_code_entry",
        "spam_max_messages", "spam_time_window",
        "funding_channel_name", "funding_channel_goal", "funding_channel_goal_input",
        "remove_funding", "set_bonus_attempts", "set_temp_ban_duration",
        "set_auto_delete_timeout", "session_threshold"
    ]
    for state in states:
        if exclude != state:
            botdb.delete(f"{state}:{user_id}")


async def weekly_referral_bonus_task():
    """Task to automatically grant weekly referral bonuses"""
    while True:
        try:
            grant_weekly_referral_bonuses()
        except Exception as e:
            print(f"Error in weekly referral bonus task: {e}")
        
        # Run every 7 days (604800 seconds)
        await asyncio.sleep(604800)


# Run
if __name__ == "__main__":
    print("Bot is running...")

    loop = asyncio.get_event_loop()

    # Load sessions
    loop.run_until_complete(load_session_clients())

    # Start monitoring tasks
    loop.create_task(story_monitoring_task())
    loop.create_task(auto_delete_content_task())
    loop.create_task(funding_monitor_task())
    loop.create_task(weekly_referral_bonus_task())

    bot.run()