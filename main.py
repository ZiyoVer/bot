import logging
import random
import json
import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ChatMemberStatus

API_TOKEN = os.getenv("API_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
YOUR_ADMIN_ID = int(os.getenv("YOUR_ADMIN_ID"))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

ROLES_FILE = "user_roles.json"

user_roles = {}  # {user_id: {"role": role, "username": username}}

MAX_CONTENT_CREATORS = 8

def save_roles():
    with open(ROLES_FILE, "w") as f:
        json.dump(user_roles, f)

def load_roles():
    global user_roles
    if os.path.exists(ROLES_FILE):
        with open(ROLES_FILE, "r") as f:
            user_roles = json.load(f)
    else:
        user_roles = {}

def count_content_creators():
    return sum(1 for v in user_roles.values() if v["role"] == "content_creator")

def assign_role():
    if count_content_creators() >= MAX_CONTENT_CREATORS:
        return "spectator"
    # 20% content_creator, 80% spectator
    return random.choices(["spectator", "content_creator"], weights=[80, 20], k=1)[0]

async def check_subscription(user_id: int):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Subscription check error for {user_id}: {e}")
        return False

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "NoUsername"

    subscribed = await check_subscription(int(user_id))
    if not subscribed:
        await message.answer(
            f"Iltimos, avvalo {CHANNEL_USERNAME} kanaliga obuna bo‘ling va /start ni qaytadan bosing."
        )
        return

    # Challenge haqida ma'lumot
    challenge_info = (
        "👋 Assalomu alaykum!\n\n"
        "Siz **Content Creator Battle** challenge-ga qo‘shildingiz.\n"
        "Content Creator bo‘lsangiz, sizga maxsus mavzu beriladi va post tayyorlashingiz kerak bo‘ladi.\n"
        "Spectator bo‘lsangiz, challenge jarayonini kuzatib boring va o‘z fikringizni bildirishingiz mumkin!\n"
        "Spectatorlarga ham random tanlash orqali sovg'alar beriladi challengeda faol qatnashing\n"
        "Content creatorlarning postlari kanalimizda qoyib boriladi ularni kuzatib boring @oktamziyodullayev\n"
        "Boshladik! 🔥"
    )
    await message.answer(challenge_info)

    if user_id in user_roles:
        role = user_roles[user_id]["role"]
        await message.answer(f"Sizga berilgan rol: {role}")
        if role == "content_creator":
            await message.answer(f"Content Creator sifatida, adminga murojat qiling @Ziyodullayev_U")
        return

    role = assign_role()
    user_roles[user_id] = {"role": role, "username": username}
    save_roles()

    await message.answer(f"Sizga berilgan rolingiz: {role}")

    if role == "content_creator":
        await message.answer(f"Content Creator sifatida, adminga murojat qiling @Ziyodullayev_U")
        # Adminga tabrik xabarini yuborish
        admin_text = f"🎉 @{username} Content Creator roli oldi! Tabriklaymiz!"
        await bot.send_message(YOUR_ADMIN_ID, admin_text)

@dp.message_handler(commands=['roles'])
async def show_roles(message: types.Message):
    if message.from_user.id != YOUR_ADMIN_ID:
        await message.answer("Sizda admin huquqi yo‘q.")
        return
    if not user_roles:
        await message.answer("Hozircha ro‘llar berilmagan.")
        return

    text = "Foydalanuvchilarning rollari:\n"
    for uid, info in user_roles.items():
        text += f"ID: {uid}, Username: @{info['username']}, Role: {info['role']}\n"
    await message.answer(text)

@dp.message_handler(commands=['resetroles'])
async def reset_roles(message: types.Message):
    if message.from_user.id != YOUR_ADMIN_ID:
        await message.answer("Sizda admin huquqi yo‘q.")
        return
    user_roles.clear()
    save_roles()
    await message.answer("Barcha ro‘llar tozalandi. Yangi raund boshlash uchun /start ni bosinglar.")

@dp.message_handler(commands=['giverole'])
async def give_role(message: types.Message):
    if message.from_user.id != YOUR_ADMIN_ID:
        await message.answer("Sizda admin huquqi yo‘q.")
        return

    args = message.get_args().split()
    if len(args) != 2:
        await message.answer("Foydalanish: /giverole <user_id> <role>")
        return

    user_id_str, role = args
    if role not in ['content_creator', 'spectator']:
        await message.answer("Rol faqat 'content_creator' yoki 'spectator' bo‘lishi mumkin.")
        return

    if not user_id_str.isdigit():
        await message.answer("Iltimos, to‘g‘ri user_id kiriting.")
        return

    user_id = user_id_str

    username = "NoUsername"
    try:
        user = await bot.get_chat_member(CHANNEL_USERNAME, int(user_id))
        if user.user.username:
            username = user.user.username
    except:
        pass

    user_roles[user_id] = {"role": role, "username": username}
    save_roles()

    await message.answer(f"Foydalanuvchi ID: {user_id} ga '{role}' roli berildi.")

    if role == "content_creator":
        await bot.send_message(YOUR_ADMIN_ID, f"🎉 @{username} content_creator roli bilan qo‘lda tanlandi!")
        # Foydalanuvchiga o'ziga xabar yuborish
        try:
            await bot.send_message(int(user_id), "🎉 Qayta tanlash amalga oshirildi va URU AI tizmi random ravishta sizni content creator deb topdi!\nEndi siz adminga yozishingiz kerak boladi @Ziyodullayev_U")
        except Exception as e:
            logging.error(f"Foydalanuvchiga xabar yuborishda xatolik: {e}")

@dp.message_handler(lambda m: user_roles.get(str(m.from_user.id), {}).get("role") == "content_creator", content_types=types.ContentTypes.TEXT)
async def receive_post(message: types.Message):
    # Bu yerda postni qayta ishlash yoki admin kanaliga yuborish mumkin
    await message.answer("Postingiz qabul qilindi, rahmat!")

if __name__ == '__main__':
    load_roles()
    executor.start_polling(dp, skip_updates=True)
