import sys
import traceback
import os
import time
import urllib.parse

try:
    import telebot
    from telebot import apihelper
    from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    import config
    import database
    import admin

    apihelper.RETRY_ON_ERROR = True
    bot = telebot.TeleBot(config.BOT_TOKEN)
    admin.register_admin_handlers(bot)

    def is_subscribed(user_id):
        if str(user_id) in config.ADMIN_IDS: return True
        try:
            status = bot.get_chat_member(config.PUBLIC_CHANNEL_ID, user_id).status
            return status in ['member', 'administrator', 'creator']
        except: return True

    def get_main_menu_markup():
        markup = InlineKeyboardMarkup()
        exams = database.get_all_exams()
        if not exams: markup.row(InlineKeyboardButton("🚧 अभी डेटा उपलब्ध नहीं है", callback_data="no_data"))
        else:
            exam_buttons = [InlineKeyboardButton(exam, callback_data=f"st_ex_{exam}") for exam in exams]
            for i in range(0, len(exam_buttons), 2): markup.row(*exam_buttons[i:i+2])
        markup.row(InlineKeyboardButton("📊 मेरा स्कोर", callback_data="menu_myscore"), InlineKeyboardButton("🏆 लीडरबोर्ड", callback_data="menu_leaderboard"))
        markup.row(InlineKeyboardButton("📢 हमारा चैनल", url=os.getenv("CHANNEL_LINK", "https://t.me/telegram")), InlineKeyboardButton("🎧 सहायता / शिकायत", callback_data="menu_complaint"))
        return markup

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        try:
            user_id = message.from_user.id
            first_name = message.from_user.first_name

            if not is_subscribed(user_id):
                mk = InlineKeyboardMarkup()
                mk.add(InlineKeyboardButton("📢 पहले चैनल ज्वाइन करें", url=os.getenv("CHANNEL_LINK", "https://t.me/telegram")))
                mk.add(InlineKeyboardButton("✅ मैंने ज्वाइन कर लिया है", callback_data="check_sub"))
                bot.send_message(user_id, "🛑 **टेस्ट देने के लिए पहले चैनल ज्वाइन करना अनिवार्य है!**", reply_markup=mk)
                return

            if database.check_banned(user_id):
                bot.send_message(user_id, "❌ आपको प्रतिबंधित कर दिया गया है।"); return

            if database.register_user(user_id, first_name, message.from_user.username or ""):
                try:
                    log_id = os.getenv("LOG_CHANNEL_ID")
                    if log_id: bot.send_message(log_id, f"🆕 **नया छात्र:**\n👤 {first_name}\n🔗 `{user_id}`")
                except: pass

            # 🎯 आपका पुराना वाला ओरिजिनल स्टार्ट मैसेज
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

            bot.send_message(user_id, welcome_text, reply_markup=get_main_menu_markup(), parse_mode='Markdown')
        except Exception as e: print(f"❌ Start Error: {e}")

    @bot.callback_query_handler(func=lambda call: call.data == "check_sub")
    def check_sub_call(call):
        if is_subscribed(call.from_user.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_welcome(call.message)
        else: bot.answer_callback_query(call.id, "❌ पहले चैनल ज्वाइन करें!", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "menu_main")
    def back_to_main(call):
        bot.answer_callback_query(call.id)
        bot.edit_message_text(f"🎯 **मुख्य मेनू:**\n👇 **अपना टारगेट एग्जाम चुनें:**", call.message.chat.id, call.message.message_id, reply_markup=get_main_menu_markup(), parse_mode="Markdown")

    student_sessions = {}

    @bot.callback_query_handler(func=lambda call: call.data.startswith("st_ex_"))
    def handle_student_exam(call):
        bot.answer_callback_query(call.id)
        exam_name = call.data.replace("st_ex_", "")
        student_sessions[call.from_user.id] = {'exam': exam_name}
        subjects = database.get_subjects_by_exam(exam_name)
        if not subjects: bot.send_message(call.message.chat.id, "🚧 विषय जोड़े जा रहे हैं।"); return
        markup = InlineKeyboardMarkup()
        for sub in subjects: markup.add(InlineKeyboardButton(sub, callback_data=f"st_su_{sub}"))
        markup.add(InlineKeyboardButton("🔙 वापस (Back)", callback_data="menu_main"))
        bot.edit_message_text(f"🎯 परीक्षा: **{exam_name}**\n📚 **अपना विषय चुनें:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("st_su_"))
    def handle_student_subject(call):
        bot.answer_callback_query(call.id)
        sub_name = call.data.replace("st_su_", "")
        user_id = call.from_user.id
        exam_name = student_sessions.get(user_id, {}).get('exam')
        tests = database.get_public_tests(exam_name, sub_name)
        if not tests: bot.send_message(call.message.chat.id, "🚧 टेस्ट उपलब्ध नहीं हैं।"); return
        
        markup = InlineKeyboardMarkup()
        name_encoded = urllib.parse.quote(call.from_user.first_name)
        for t in tests:
            test_url = f"{config.WEBAPP_BASE_URL}{t['test_id']}&uid={user_id}&name={name_encoded}"
            markup.add(InlineKeyboardButton(f"📝 {t['test_name']}", web_app=WebAppInfo(url=test_url)))
        markup.add(InlineKeyboardButton("🔙 वापस (Back)", callback_data=f"st_ex_{exam_name}"))
        bot.edit_message_text(f"📚 विषय: **{sub_name}**\n👇 **टेस्ट शुरू करें:**", call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data in ["no_data", "menu_myscore", "menu_leaderboard", "menu_complaint"] or call.data.startswith("reply_"))
    def handle_general_menu(call):
        bot.answer_callback_query(call.id) 
        mk_back = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 मुख्य मेनू", callback_data="menu_main"))
        
        if call.data == "menu_myscore":
            scores = database.get_user_scores(call.from_user.id)
            if not scores: bot.edit_message_text("🚧 आपने अभी तक कोई टेस्ट नहीं दिया है।", call.message.chat.id, call.message.message_id, reply_markup=mk_back)
            else:
                text = "📊 **आपका रिपोर्ट कार्ड:**\n\n"
                for s in scores: text += f"📝 {s['test_name']} | अंक: `{s['score']}` | सटीकता: `{s['accuracy']}%`\n"
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=mk_back)
                
        elif call.data == "menu_leaderboard":
            top = database.get_top_scorers()
            if not top: bot.edit_message_text("🚧 अभी लीडरबोर्ड खाली है।", call.message.chat.id, call.message.message_id, reply_markup=mk_back)
            else:
                text = "🏆 **टॉप 10 लीडरबोर्ड** 🏆\n\n"
                for i, s in enumerate(top): text += f"{i+1}. {s['first_name']} - `{s['score']}` अंक\n"
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=mk_back)
                
        elif call.data == "menu_complaint":
            msg = bot.send_message(call.from_user.id, "📝 **शिकायत टाइप करें:**", reply_markup=mk_back)
            bot.register_next_step_handler(msg, process_complaint)
            
        elif call.data.startswith("reply_"):
            target = call.data.split("_")[1]
            msg = bot.send_message(call.message.chat.id, "✍️ **रिप्लाई टाइप करें:**")
            bot.register_next_step_handler(msg, send_reply_to_user, target)

    def process_complaint(message):
        bot.send_message(message.from_user.id, "✅ शिकायत एडमिन को भेज दी गई है।")
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("↩️ रिप्लाई करें", callback_data=f"reply_{message.from_user.id}"))
        bot.send_message(config.COMPLAINT_CHANNEL_ID, f"🚨 **शिकायत:** {message.text}", reply_markup=markup)

    def send_reply_to_user(message, target):
        try: bot.send_message(int(target), f"🎧 **एडमिन उत्तर:**\n{message.text}")
        except: pass

    if __name__ == "__main__":
        print("🚀 Bot Started Polling...", flush=True)
        while True:
            try: bot.infinity_polling(timeout=20, long_polling_timeout=10)
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e): time.sleep(30)
                else: time.sleep(5)

except Exception as e:
    traceback.print_exc()
