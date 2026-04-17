# main.py
import sys
import traceback
import os
import time

try:
    import telebot
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
    import config
    import database
    import admin

    print("🔄 Checking Token and Starting Bot...", flush=True)
    bot = telebot.TeleBot(config.BOT_TOKEN)
    admin.register_admin_handlers(bot)

    # ==========================================
    # 1. स्टार्ट कमांड और मुख्य मेनू (पुराने लंबे मैसेज के साथ)
    # ==========================================
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        try:
            user_id = message.from_user.id
            first_name = message.from_user.first_name

            if database.check_banned(user_id):
                bot.send_message(user_id, "❌ आपको एडमिन द्वारा प्रतिबंधित (Ban) कर दिया गया है।")
                return

            database.register_user(user_id, first_name, message.from_user.username or "")

            # 🎯 आपका पुराना और सबसे शानदार स्टार्ट मैसेज 🎯
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
            
            if not exams:
                markup.row(InlineKeyboardButton("🚧 अभी डेटा उपलब्ध नहीं है", callback_data="no_data"))
            else:
                exam_buttons = [InlineKeyboardButton(exam, callback_data=f"st_ex_{exam}") for exam in exams]
                for i in range(0, len(exam_buttons), 2): markup.row(*exam_buttons[i:i+2])
            
            markup.row(InlineKeyboardButton("📊 मेरा स्कोर", callback_data="menu_myscore"), InlineKeyboardButton("🏆 लीडरबोर्ड", callback_data="menu_leaderboard"))
            
            channel_link = os.getenv("CHANNEL_LINK", "https://t.me/telegram")
            markup.row(InlineKeyboardButton("📢 हमारा चैनल", url=channel_link), InlineKeyboardButton("🎧 सहायता / शिकायत", callback_data="menu_complaint"))

            bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode='Markdown')
        except Exception as e:
            print(f"❌ Start Command Error: {e}", flush=True)

    # ==========================================
    # 2. छात्रों के एग्जाम -> विषय -> टेस्ट का फ्लो
    # ==========================================
    student_sessions = {}

    @bot.callback_query_handler(func=lambda call: call.data.startswith("st_ex_"))
    def handle_student_exam(call):
        bot.answer_callback_query(call.id)
        exam_name = call.data.replace("st_ex_", "")
        user_id = call.from_user.id
        student_sessions[user_id] = {'exam': exam_name}
        
        subjects = database.get_subjects_by_exam(exam_name)
        if not subjects:
            bot.send_message(call.message.chat.id, f"🚧 **{exam_name}** में अभी विषय जोड़े जा रहे हैं।")
            return
            
        markup = InlineKeyboardMarkup()
        for sub in subjects: markup.add(InlineKeyboardButton(sub, callback_data=f"st_su_{sub}"))
        bot.edit_message_text(f"🎯 परीक्षा: **{exam_name}**\n📚 **अब अपना विषय (Subject) चुनें:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("st_su_"))
    def handle_student_subject(call):
        bot.answer_callback_query(call.id)
        sub_name = call.data.replace("st_su_", "")
        user_id = call.from_user.id
        
        if user_id not in student_sessions: return
        exam_name = student_sessions[user_id].get('exam')
        
        tests = database.get_public_tests(exam_name, sub_name)
        if not tests:
            bot.send_message(call.message.chat.id, f"🚧 **{sub_name}** के टेस्ट अभी उपलब्ध नहीं हैं।")
            return
            
        markup = InlineKeyboardMarkup()
        for t in tests:
            test_url = f"{config.WEBAPP_BASE_URL}{t['test_id']}"
            markup.add(InlineKeyboardButton(f"📝 {t['test_name']}", url=test_url))
            
        bot.edit_message_text(f"📚 विषय: **{sub_name}**\n👇 **नीचे दिए गए टेस्ट पर क्लिक करके शुरू करें:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # ==========================================
    # 3. मेनू बटन्स और शिकायत फ्लो (100% Fixed)
    # ==========================================
    @bot.callback_query_handler(func=lambda call: call.data in ["no_data", "menu_myscore", "menu_leaderboard", "menu_complaint"] or call.data.startswith("reply_"))
    def handle_general_menu(call):
        bot.answer_callback_query(call.id) 
        
        if call.data == "no_data":
            bot.send_message(call.from_user.id, "🚧 अभी कोई परीक्षा उपलब्ध नहीं है।")
        elif call.data in ["menu_myscore", "menu_leaderboard"]:
            bot.send_message(call.from_user.id, "🚧 यह फीचर जल्द ही आ रहा है!")
        elif call.data == "menu_complaint":
            msg = bot.send_message(call.from_user.id, "📝 **अपनी समस्या या शिकायत टाइप करें (फोटो भी भेज सकते हैं):**", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_complaint)
        elif call.data.startswith("reply_"):
            target = call.data.split("_")[1]
            msg = bot.send_message(call.message.chat.id, "✍️ **छात्र के लिए रिप्लाई टाइप करें (अगला मैसेज सीधा छात्र को जाएगा):**", parse_mode="Markdown")
            # यहाँ हमने target को भेज दिया है
            bot.register_next_step_handler(msg, send_reply_to_user, target)

    def process_complaint(message):
        user_id = message.from_user.id
        bot.send_message(user_id, "✅ शिकायत एडमिन को भेज दी गई है। कृपया उत्तर का इंतज़ार करें।")
        admin_alert = f"🚨 **नई शिकायत:**\n👤 **छात्र:** {message.from_user.first_name} (`{user_id}`)\n💬 **समस्या:** {message.text or 'मीडिया'}"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("↩️ रिप्लाई करें", callback_data=f"reply_{user_id}"))
        
        if message.content_type != 'text': 
            bot.copy_message(config.COMPLAINT_CHANNEL_ID, user_id, message.message_id)
        
        bot.send_message(config.COMPLAINT_CHANNEL_ID, admin_alert, reply_markup=markup, parse_mode='Markdown')

    # 🛠️ यहाँ रिप्लाई की समस्या को हमेशा के लिए फिक्स कर दिया गया है
    def send_reply_to_user(message, target):
        try:
            target_id = int(target) # ID को Text से Number में बदल दिया
            bot.send_message(target_id, f"🎧 **एडमिन सपोर्ट से उत्तर:**\n\n{message.text}", parse_mode="Markdown")
            bot.send_message(message.chat.id, "✅ **छात्र को सफलतापूर्वक रिप्लाई भेज दिया गया है।**", parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ **एरर:** रिप्लाई नहीं गया। (कारण: {e})", parse_mode="Markdown")

    # ==========================================
    # क्रैश-प्रूफ रनिंग
    # ==========================================
    if __name__ == "__main__":
        print("🚀 Bot Started Polling...", flush=True)
        while True:
            try:
                bot.infinity_polling(timeout=20, long_polling_timeout=10)
            except Exception as e:
                print(f"❌ POLLING ERROR: {e}", flush=True)
                time.sleep(5)

except Exception as e:
    print("\n💥 CRITICAL STARTUP ERROR 💥", flush=True)
    traceback.print_exc()
