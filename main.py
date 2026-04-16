# main.py
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import config
import database
import admin

bot = telebot.TeleBot(config.BOT_TOKEN)
admin.register_admin_handlers(bot)

# ==========================================
# 1. स्टार्ट कमांड और मुख्य मेनू (पुराने मैसेज के साथ)
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name
        username = message.from_user.username or "No Username"

        if database.check_banned(user_id):
            bot.send_message(user_id, "❌ आपको एडमिन द्वारा प्रतिबंधित (Ban) कर दिया गया है।")
            return

        database.register_user(user_id, first_name, username)

        welcome_text = (
            f"🎯 **स्वागत है {first_name}!** 🇮🇳\n"
            "वर्दी के आपके सपने को हकीकत में बदलने के लिए हम तैयार हैं।\n\n"
            "यह सिर्फ एक बॉट नहीं, आपका **स्मार्ट टेस्ट सेंटर** है। यहाँ आपको मिलता है असली परीक्षा (CBT) वाला अनुभव:\n\n"
            "✨ **हमारे मुख्य फीचर्स:**\n"
            "⏱ **लाइव टेस्ट इंटरफेस:** बिल्कुल असली परीक्षा पैटर्न वाला टाइमर।\n"
            "📊 **तुरंत स्कोरकार्ड:** टेस्ट सबमिट करते ही अपना रिज़ल्ट जानें।\n"
            "🏆 **रीयल-टाइम रैंक:** लीडरबोर्ड पर देखें कि आप कंपटीशन में कहाँ हैं।\n"
            "📂 **टेस्ट हिस्ट्री:** अपने पिछले सभी स्कोर्स का रिकॉर्ड एक ही जगह पाएं।\n\n"
            "👇 **अपनी तैयारी शुरू करने के लिए नीचे अपना 'टारगेट एग्जाम' चुनें:**\n\n"
            "⚠️ **डिस्क्लेमर (Disclaimer):**\n"
            "*इस बॉट पर उपलब्ध सभी मॉक टेस्ट और सामग्री केवल छात्रों की शिक्षा (Educational Purposes) और अभ्यास के लिए है। इसका उद्देश्य किसी भी संस्थान के कॉपीराइट का उल्लंघन करना नहीं है। किसी भी विवाद के लिए एडमिन ज़िम्मेदार नहीं होगा।*"
        )

        markup = InlineKeyboardMarkup()
        exams = database.get_all_exams()
        
        # ⚠️ डेटा न होने पर मैसेज (Empty State Flow)
        if not exams:
            markup.row(InlineKeyboardButton("🚧 अभी डेटा उपलब्ध नहीं है", callback_data="no_data"))
        else:
            exam_buttons = [InlineKeyboardButton(exam, callback_data=f"exam_{exam}") for exam in exams]
            for i in range(0, len(exam_buttons), 2):
                markup.row(*exam_buttons[i:i+2])
        
        markup.row(
            InlineKeyboardButton("📊 मेरा स्कोर", callback_data="menu_myscore"),
            InlineKeyboardButton("🏆 लीडरबोर्ड", callback_data="menu_leaderboard")
        )
        markup.row(
            InlineKeyboardButton("📢 हमारा चैनल", url=config.CHANNEL_LINK if hasattr(config, 'CHANNEL_LINK') else "https://t.me/telegram"),
            InlineKeyboardButton("🎧 सहायता / शिकायत", callback_data="menu_complaint")
        )

        bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode='Markdown')

    except Exception as e:
        print(f"Start Error: {e}")

# ==========================================
# 2. बटन क्लिक हैंडलर (Bot Not Responding 100% Fixed)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data in ["no_data", "menu_myscore", "menu_leaderboard", "menu_complaint"] or call.data.startswith("reply_"))
def handle_menu_clicks(call):
    # 🛠️ यह लाइन हर क्लिक का जवाब देती है, जिससे लोडिंग (Not responding) नहीं आती
    bot.answer_callback_query(call.id) 
    
    if call.data == "no_data":
        bot.send_message(call.from_user.id, "🚧 **अभी कोई परीक्षा (Exam) उपलब्ध नहीं है। कृपया एडमिन द्वारा टेस्ट अपलोड करने का इंतज़ार करें।**")
        
    elif call.data in ["menu_myscore", "menu_leaderboard"]:
        bot.send_message(call.from_user.id, "🚧 **यह फीचर अभी तैयार हो रहा है, जल्द ही लाइव होगा!**")
        
    elif call.data == "menu_complaint":
        msg = bot.send_message(call.from_user.id, "📝 **अपनी समस्या या शिकायत टाइप करें:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_complaint)
        
    elif call.data.startswith("reply_"):
        target_user_id = call.data.split("_")[1]
        msg = bot.send_message(call.message.chat.id, "✍️ **छात्र के लिए अपना रिप्लाई टाइप करें:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, send_reply_to_user, target_user_id)

def process_complaint(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "✅ आपकी शिकायत एडमिन टीम को भेज दी गई है।")
    admin_alert = f"🚨 **नई शिकायत:**\n👤 **छात्र:** {message.from_user.first_name} (ID: `{user_id}`)\n💬 **समस्या:** {message.text if message.text else 'मीडिया'}"
    reply_markup = InlineKeyboardMarkup()
    reply_markup.add(InlineKeyboardButton("↩️ रिप्लाई करें (Reply)", callback_data=f"reply_{user_id}"))
    if message.content_type != 'text': bot.copy_message(config.COMPLAINT_CHANNEL_ID, user_id, message.message_id)
    bot.send_message(config.COMPLAINT_CHANNEL_ID, admin_alert, reply_markup=reply_markup, parse_mode='Markdown')

def send_reply_to_user(message, target_user_id):
    try:
        bot.send_message(target_user_id, f"🎧 **एडमिन सपोर्ट से उत्तर:**\n\n{message.text}", parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ **छात्र को रिप्लाई भेज दिया गया है।**", parse_mode="Markdown")
    except:
        pass

# ==========================================
if __name__ == "__main__":
    print("🚀 Bot is starting...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            time.sleep(5)
