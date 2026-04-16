# main.py
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import config
import database

# बॉट इनिशियलाइज़ करना
bot = telebot.TeleBot(config.BOT_TOKEN)

# ==========================================
# 1. स्टार्ट कमांड और मुख्य मेनू (Start & Menu)
# ==========================================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name
        username = message.from_user.username or "No Username"

        # 1. बैन स्टेटस चेक करना
        if database.check_banned(user_id):
            bot.send_message(user_id, "❌ आपको एडमिन द्वारा इस बॉट से प्रतिबंधित (Ban) कर दिया गया है।")
            return

        # 2. डेटाबेस में रजिस्टर करना
        database.register_user(user_id, first_name, username)

        # 3. वेलकम मैसेज और डिस्क्लेमर
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
            "*इस बॉट पर उपलब्ध सभी मॉक टेस्ट और सामग्री केवल छात्रों की शिक्षा (Educational Purposes) और अभ्यास के लिए है। इसका उद्देश्य किसी भी संस्थान के कॉपीराइट का उल्लंघन करना नहीं है।*"
        )

        # 4. इनलाइन कीबोर्ड (बटन) बनाना
        markup = InlineKeyboardMarkup()
        
        # डेटाबेस से डायनामिक एग्जाम बटन लाना
        exams = database.get_all_exams()
        exam_buttons = [InlineKeyboardButton(exam, callback_data=f"exam_{exam}") for exam in exams]
        
        # बटनों को 2-2 की लाइन में लगाना
        for i in range(0, len(exam_buttons), 2):
            markup.row(*exam_buttons[i:i+2])
        
        # स्थायी (Static) बटन जोड़ना
        markup.row(
            InlineKeyboardButton("📊 मेरा स्कोर", callback_data="menu_myscore"),
            InlineKeyboardButton("🏆 लीडरबोर्ड", callback_data="menu_leaderboard")
        )
        markup.row(
            InlineKeyboardButton("📢 हमारा चैनल", url=f"https://t.me/{config.PUBLIC_CHANNEL_ID.replace('-100', '')}"),
            InlineKeyboardButton("🎧 सहायता / शिकायत", callback_data="menu_complaint")
        )

        bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode='Markdown')

    except Exception as e:
        print(f"Start Command Error: {e}")

# ==========================================
# 2. शिकायत / सहायता फ्लो (Complaint System)
# ==========================================

@bot.callback_query_handler(func=lambda call: call.data == "menu_complaint")
def handle_complaint_click(call):
    try:
        user_id = call.from_user.id
        msg = bot.send_message(
            user_id, 
            "📝 **अपनी समस्या या शिकायत टाइप करें:**\n(आप कोई स्क्रीनशॉट या फोटो भी भेज सकते हैं। एडमिन टीम जल्द ही आपकी सहायता करेगी।)",
            parse_mode="Markdown"
        )
        # अगले मैसेज का इंतज़ार करना
        bot.register_next_step_handler(msg, process_complaint)
    except Exception as e:
        print(f"Complaint Click Error: {e}")

def process_complaint(message):
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name
        
        # छात्र को कन्फर्मेशन देना
        bot.send_message(user_id, "✅ आपकी शिकायत एडमिन टीम को भेज दी गई है। कृपया उत्तर का इंतज़ार करें।")

        # एडमिन के प्राइवेट चैनल में शिकायत भेजना
        admin_alert = (
            "🚨 **नई शिकायत प्राप्त हुई:**\n\n"
            f"👤 **छात्र:** {first_name} (ID: `{user_id}`)\n"
            f"💬 **समस्या:** {message.text if message.text else '(मीडिया/फोटो संलग्न है)'}"
        )
        
        reply_markup = InlineKeyboardMarkup()
        reply_markup.add(InlineKeyboardButton("↩️ रिप्लाई करें (Reply)", callback_data=f"reply_{user_id}"))

        # अगर छात्र ने फोटो भेजी है तो फोटो फॉरवर्ड करना
        if message.content_type != 'text':
            bot.copy_message(config.COMPLAINT_CHANNEL_ID, user_id, message.message_id)
        
        bot.send_message(config.COMPLAINT_CHANNEL_ID, admin_alert, reply_markup=reply_markup, parse_mode='Markdown')

    except Exception as e:
        print(f"Process Complaint Error: {e}")

# एडमिन द्वारा रिप्लाई करने का फ्लो
@bot.callback_query_handler(func=lambda call: call.data.startswith("reply_"))
def handle_admin_reply(call):
    try:
        target_user_id = call.data.split("_")[1]
        msg = bot.send_message(call.message.chat.id, "✍️ **छात्र के लिए अपना रिप्लाई टाइप करें:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, send_reply_to_user, target_user_id)
    except Exception as e:
        print(f"Admin Reply Error: {e}")

def send_reply_to_user(message, target_user_id):
    try:
        reply_text = f"🎧 **एडमिन सपोर्ट से उत्तर:**\n\n{message.text}"
        bot.send_message(target_user_id, reply_text, parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ **छात्र को रिप्लाई भेज दिया गया है।**", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ **एरर:** छात्र को रिप्लाई नहीं भेजा जा सका। शायद उसने बॉट ब्लॉक कर दिया है।")

# ==========================================
# 3. क्रैश-प्रूफ रनिंग (Crash-Proof Polling)
# ==========================================

if __name__ == "__main__":
    print("🚀 Bot is starting...")
    while True:
        try:
            # infinity_polling बॉट को क्रैश होने से बचाता है
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"CRASH AVOIDED: {e}")
            time.sleep(5)  # अगर टेलीग्राम ब्लॉक करे, तो 5 सेकंड रुक कर फिर शुरू करें
