# main.py
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import config
import database
import admin

bot = telebot.TeleBot(config.BOT_TOKEN)

# एडमिन के सारे कमांड्स चालू करना
admin.register_admin_handlers(bot)

# ==========================================
# 1. स्टार्ट कमांड और मुख्य मेनू (Start & Menu)
# ==========================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name
        username = message.from_user.username or "No Username"

        if database.check_banned(user_id):
            bot.send_message(user_id, "❌ आपको एडमिन द्वारा इस बॉट से प्रतिबंधित (Ban) कर दिया गया है।")
            return

        database.register_user(user_id, first_name, username)

        welcome_text = (
            f"🎯 **स्वागत है {first_name}!** 🇮🇳\n"
            "वर्दी के आपके सपने को हकीकत में बदलने के लिए हम तैयार हैं।\n\n"
            "यह सिर्फ एक बॉट नहीं, आपका **स्मार्ट टेस्ट सेंटर** है।\n\n"
            "👇 **अपनी तैयारी शुरू करने के लिए नीचे अपना 'टारगेट एग्जाम' चुनें:**\n\n"
            "⚠️ **डिस्क्लेमर:** यह सामग्री केवल शिक्षा के उद्देश्य से है।"
        )

        markup = InlineKeyboardMarkup()
        
        # डेटाबेस से एग्जाम बटन लाना (अगर खाली होगा तो नहीं दिखेंगे)
        exams = database.get_all_exams()
        exam_buttons = [InlineKeyboardButton(exam, callback_data=f"exam_{exam}") for exam in exams]
        
        for i in range(0, len(exam_buttons), 2):
            markup.row(*exam_buttons[i:i+2])
        
        markup.row(
            InlineKeyboardButton("📊 मेरा स्कोर", callback_data="menu_myscore"),
            InlineKeyboardButton("🏆 लीडरबोर्ड", callback_data="menu_leaderboard")
        )
        markup.row(
            # यहाँ हमने नया CHANNEL_LINK लगा दिया है
            InlineKeyboardButton("📢 हमारा चैनल", url=config.CHANNEL_LINK),
            InlineKeyboardButton("🎧 सहायता / शिकायत", callback_data="menu_complaint")
        )

        bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode='Markdown')

    except Exception as e:
        print(f"Start Command Error: {e}")

# ==========================================
# 2. बटन क्लिक (Callback) हैंडलर - 'Not Responding' Fix
# ==========================================

@bot.callback_query_handler(func=lambda call: call.data == "menu_complaint")
def handle_complaint_click(call):
    # यह लाइन "bot not responding" वाले एरर को रोकती है
    bot.answer_callback_query(call.id) 
    try:
        msg = bot.send_message(
            call.from_user.id, 
            "📝 **अपनी समस्या या शिकायत टाइप करें:**\n(आप कोई स्क्रीनशॉट या फोटो भी भेज सकते हैं।)",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_complaint)
    except Exception as e:
        print(f"Complaint Click Error: {e}")

@bot.callback_query_handler(func=lambda call: call.data in ["menu_myscore", "menu_leaderboard"])
def handle_coming_soon(call):
    bot.answer_callback_query(call.id) # 'Not Responding' Fix
    bot.send_message(call.from_user.id, "🚧 **यह फीचर अभी तैयार हो रहा है, जल्द ही लाइव होगा!**")

@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
def handle_admin_reply(call):
    bot.answer_callback_query(call.id) # 'Not Responding' Fix
    try:
        target_user_id = call.data.split("_")[1]
        msg = bot.send_message(call.message.chat.id, "✍️ **छात्र के लिए अपना रिप्लाई टाइप करें:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, send_reply_to_user, target_user_id)
    except Exception as e:
        print(f"Admin Reply Error: {e}")

# ==========================================
# 3. शिकायत प्रोसेस फ्लो
# ==========================================

def process_complaint(message):
    try:
        user_id = message.from_user.id
        bot.send_message(user_id, "✅ आपकी शिकायत एडमिन टीम को भेज दी गई है। कृपया उत्तर का इंतज़ार करें।")

        admin_alert = (
            f"🚨 **नई शिकायत:**\n👤 **छात्र:** {message.from_user.first_name} (ID: `{user_id}`)\n"
            f"💬 **समस्या:** {message.text if message.text else '(मीडिया संलग्न है)'}"
        )
        
        reply_markup = InlineKeyboardMarkup()
        reply_markup.add(InlineKeyboardButton("↩️ रिप्लाई करें (Reply)", callback_data=f"reply_{user_id}"))

        if message.content_type != 'text':
            bot.copy_message(config.COMPLAINT_CHANNEL_ID, user_id, message.message_id)
        
        bot.send_message(config.COMPLAINT_CHANNEL_ID, admin_alert, reply_markup=reply_markup, parse_mode='Markdown')
    except Exception as e:
        print(f"Process Complaint Error: {e}")

def send_reply_to_user(message, target_user_id):
    try:
        bot.send_message(target_user_id, f"🎧 **एडमिन सपोर्ट से उत्तर:**\n\n{message.text}", parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ **छात्र को रिप्लाई भेज दिया गया है।**", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ **एरर:** छात्र को रिप्लाई नहीं भेजा जा सका।")

# ==========================================
# क्रैश-प्रूफ रनिंग
# ==========================================
if __name__ == "__main__":
    print("🚀 Bot is starting...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"CRASH AVOIDED: {e}")
            time.sleep(5)
