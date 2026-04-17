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
                bot.send_message(user_id, "🛑 **टेस्ट देने के लिए पहले हमारा मुख्य चैनल ज्वाइन करना अनिवार्य है!**", reply_markup=mk)
                return

            if database.check_banned(user_id):
                bot.send_message(user_id, "❌ आपको एडमिन द्वारा प्रतिबंधित कर दिया गया है।"); return

            if database.register_user(user_id, first_name, message.from_user.username or ""):
                try:
                    log_id = os.getenv("LOG_CHANNEL_ID")
                    if log_id: bot.send_message(log_id, f"🆕 **नया छात्र जुड़ा:**\n👤 नाम: {first_name}\n🔗 ID: `{user_id}`")
                except: pass

            welcome_text = (
                f"🎯 **स्वागत है {first_name}!** 🇮🇳\n"
                "वर्दी के आपके सपने को हकीकत में बदलने के लिए हम तैयार हैं।\n\n"
                "यह सिर्फ एक बॉट नहीं, आपका **स्मार्ट टेस्ट सेंटर** है। यहाँ आपको मिलता है असली परीक्षा (CBT) वाला अनुभव:\n\n"
                "✨ **हमारे मुख्य फीचर्स:**\n"
                "⏱ **लाइव टेस्ट इंटरफेस:** बिल्कुल असली परीक्षा पैटर्न वाला टाइमर.\n"
                "📊 **तुरंत स्कोरकार्ड:** टेस्ट सबमिट करते ही अपना रिज़ल्ट जानें.\n"
                "🏆 **रीयल-टाइम रैंक:** लीडरबोर्ड पर देखें कि आप कंपटीशन में कहाँ हैं.\n"
                "📂 **टेस्ट हिस्ट्री:** अपने पिछले सभी स्कोर्स का रिकॉर्ड एक ही जगह पाएं.\n\n"
                "👇 **अपनी तैयारी शुरू करने के लिए नीचे अपना 'टारगेट एग्जाम' चुनें:**\n\n"
                "⚠️ **डिस्क्लेमर (Disclaimer):**\n"
                "*इस बॉट पर उपलब्ध सभी मॉक टेस्ट और सामग्री केवल छात्रों की शिक्षा (Educational Purposes) और अभ्यास के लिए है।*"
            )
            bot.send_message(user_id, welcome_text, reply_markup=get_main_menu_markup(), parse_mode='Markdown')
        except Exception as e: print(f"❌ Start Error: {e}")

    @bot.callback_query_handler(func=lambda call: call.data == "check_sub")
    def check_sub_call(call):
        if is_subscribed(call.from_user.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_welcome(call.message)
        else: bot.answer_callback_query(call.id, "❌ आपने अभी तक चैनल ज्वाइन नहीं किया है!", show_alert=True)

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
        
        markup = InlineKeyboardMarkup()
        if not subjects: 
            markup.add(InlineKeyboardButton("🔙 वापस", callback_data="menu_main"))
            bot.edit_message_text("🚧 अभी विषय जोड़े जा रहे हैं।", call.message.chat.id, call.message.message_id, reply_markup=markup); return
        
        for sub in subjects: markup.add(InlineKeyboardButton(f"📘 {sub}", callback_data=f"st_su_{sub}"))
        markup.add(InlineKeyboardButton("🔙 मुख्य मेनू", callback_data="menu_main"))
        
        text = f"✨ **परीक्षा:** {exam_name}\n━━━━━━━━━━━━━━━━━━\n📖 **अपना विषय (Subject) चुनें:**"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("st_su_"))
    def handle_student_subject(call):
        bot.answer_callback_query(call.id)
        sub_name = call.data.replace("st_su_", "")
        user_id = call.from_user.id
        exam_name = student_sessions.get(user_id, {}).get('exam')
        tests = database.get_public_tests(exam_name, sub_name)
        
        markup = InlineKeyboardMarkup()
        if not tests: 
            markup.add(InlineKeyboardButton("🔙 वापस", callback_data=f"st_ex_{exam_name}"))
            bot.edit_message_text("🚧 टेस्ट उपलब्ध नहीं हैं।", call.message.chat.id, call.message.message_id, reply_markup=markup); return
        
        name_encoded = urllib.parse.quote(call.from_user.first_name)
        for t in tests:
            # 🚀 FIX: Cache Buster लगा दिया गया है ताकि हमेशा नया टाइमर और नंबर लोड हों!
            test_url = f"{config.WEBAPP_BASE_URL}{t['test_id']}&uid={user_id}&name={name_encoded}&v={int(time.time())}"
            markup.add(InlineKeyboardButton(f"📝 {t['test_name']}", web_app=WebAppInfo(url=test_url)))
            
        markup.add(InlineKeyboardButton("🔙 विषय सूची पर जाएं", callback_data=f"st_ex_{exam_name}"))
        
        text = (
            f"📚 **विषय:** {sub_name}\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "✨ **निर्देश:**\n"
            "🔸 टाइमर खत्म होने से पहले सबमिट करें।\n"
            "🔸 केवल 1st Attempt का स्कोर ही लीडरबोर्ड में जाएगा।\n\n"
            "👇 **अपना टेस्ट शुरू करें:**"
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "menu_myscore")
    def my_score_main(call):
        bot.answer_callback_query(call.id)
        exams = database.get_attempted_exams(call.from_user.id)
        mk = InlineKeyboardMarkup()
        if not exams:
            mk.add(InlineKeyboardButton("🔙 मुख्य मेनू", callback_data="menu_main"))
            bot.edit_message_text("🚧 आपने अभी तक कोई टेस्ट नहीं दिया है।", call.message.chat.id, call.message.message_id, reply_markup=mk)
            return
        for e in exams: mk.add(InlineKeyboardButton(f"📘 {e}", callback_data=f"sc_ex_{e}"))
        mk.add(InlineKeyboardButton("🔙 मुख्य मेनू", callback_data="menu_main"))
        bot.edit_message_text("📊 **आपका रिपोर्ट कार्ड**\n━━━━━━━━━━━━━━━━━━\n📖 **अपना एग्जाम चुनें:**", call.message.chat.id, call.message.message_id, reply_markup=mk, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("sc_ex_"))
    def my_score_exam(call):
        bot.answer_callback_query(call.id)
        exam = call.data.replace("sc_ex_", "")
        subs = database.get_attempted_subjects(call.from_user.id, exam)
        mk = InlineKeyboardMarkup()
        for s in subs: mk.add(InlineKeyboardButton(f"📗 {s}", callback_data=f"sc_su_{exam}_{s}"))
        mk.add(InlineKeyboardButton("🔙 वापस", callback_data="menu_myscore"))
        bot.edit_message_text(f"📊 **एग्जाम:** {exam}\n━━━━━━━━━━━━━━━━━━\n📖 **विषय चुनें:**", call.message.chat.id, call.message.message_id, reply_markup=mk, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("sc_su_"))
    def my_score_sub(call):
        bot.answer_callback_query(call.id)
        parts = call.data.replace("sc_su_", "").split("_", 1)
        exam, sub = parts[0], parts[1]
        tests = database.get_attempted_tests(call.from_user.id, exam, sub)
        mk = InlineKeyboardMarkup()
        for t in tests: mk.add(InlineKeyboardButton(f"📝 {t['test_name']}", callback_data=f"sc_ts_{t['test_id']}"))
        mk.add(InlineKeyboardButton("🔙 वापस", callback_data=f"sc_ex_{exam}"))
        bot.edit_message_text(f"📊 **विषय:** {sub}\n━━━━━━━━━━━━━━━━━━\n👇 **स्कोर देखने के लिए टेस्ट चुनें:**", call.message.chat.id, call.message.message_id, reply_markup=mk, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("sc_ts_"))
    def my_score_test(call):
        bot.answer_callback_query(call.id)
        tid = call.data.replace("sc_ts_", "")
        score_data = database.get_test_scorecard(call.from_user.id, tid)
        test_info = database.get_test_details(tid)
        
        if score_data and test_info:
            text = f"📊 **स्कोरकार्ड: {score_data.get('test_name', 'Mock Test')}**\n━━━━━━━━━━━━━━━━━━\n"
            text += f"🎯 **स्कोर:** `{score_data.get('score', 0)}` / `{len(test_info.get('questions', [])) * test_info.get('positive_mark', 2.0)}`\n"
            text += f"📈 **सटीकता:** `{score_data.get('accuracy', '0')}%`\n"
            text += f"⏱ **कुल समय:** `{test_info.get('time_limit', 15)}` मिनट\n"
            
            date_val = score_data.get('date')
            date_str = date_val.strftime('%d-%m-%Y %H:%M') if date_val else "पुराना डेटा"
            text += f"📅 **तारीख:** `{date_str}`\n"

            mk = InlineKeyboardMarkup()
            user_id = call.from_user.id
            name_encoded = urllib.parse.quote(call.from_user.first_name)
            # 🚀 FIX: यहाँ भी Cache Buster लगा दिया है 
            test_url = f"{config.WEBAPP_BASE_URL}{tid}&uid={user_id}&name={name_encoded}&v={int(time.time())}"
            mk.add(InlineKeyboardButton("🔄 टेस्ट फिर से दें (Reattempt)", web_app=WebAppInfo(url=test_url)))
            mk.add(InlineKeyboardButton("🔙 वापस", callback_data=f"sc_su_{score_data.get('exam_name', 'Unknown')}_{score_data.get('subject_name', 'Unknown')}"))
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=mk, parse_mode="Markdown")
        else:
            bot.edit_message_text("❌ टेस्ट का डेटा नहीं मिला।", call.message.chat.id, call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 वापस", callback_data="menu_myscore")))

    @bot.callback_query_handler(func=lambda call: call.data in ["menu_leaderboard", "menu_complaint"] or call.data.startswith("reply_"))
    def handle_general_menu(call):
        mk_back = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 मुख्य मेनू", callback_data="menu_main"))
        
        if call.data == "menu_leaderboard":
            bot.answer_callback_query(call.id)
            top_10, user_rank, user_data = database.get_smart_leaderboard(call.from_user.id)
            if not top_10: 
                bot.edit_message_text("🚧 अभी तक किसी ने टेस्ट नहीं दिया है।", call.message.chat.id, call.message.message_id, reply_markup=mk_back)
            else:
                text = "🏆 **ऑल इंडिया लीडरबोर्ड** 🏆\n*(केवल 1st Attempt के आधार पर)*\n━━━━━━━━━━━━━━━━━━\n"
                medals = ["🥇", "🥈", "🥉"]
                for i, s in enumerate(top_10): 
                    medal = medals[i] if i < 3 else f"  {i+1}. "
                    text += f"{medal} **{s['first_name']}** ➔ `{s['total_score']}` अंक\n"
                text += "━━━━━━━━━━━━━━━━━━\n"
                if user_rank:
                    if user_rank <= 10: text += f"🎯 **आप टॉप 10 में हैं! (रैंक: {user_rank})** 🌟"
                    else:
                        text += f"📍 **आपकी वर्तमान रैंक:** `{user_rank}`\n"
                        text += f"🔸 **आपका कुल स्कोर:** `{user_data['total_score']}` अंक\n"
                        text += "*मेहनत करते रहें, टॉप 10 दूर नहीं! 💪*"
                else: text += "📍 **आपकी रैंक:** `अभी कोई टेस्ट नहीं दिया`"
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=mk_back)
                
        elif call.data == "menu_complaint":
            bot.answer_callback_query(call.id)
            msg = bot.send_message(call.from_user.id, "📝 **शिकायत टाइप करें:**", reply_markup=mk_back)
            bot.register_next_step_handler(msg, process_complaint)
            
        elif call.data.startswith("reply_"):
            target = call.data.split("_")[1]
            bot.answer_callback_query(call.id)
            msg = bot.send_message(call.message.chat.id, f"✍️ **छात्र (`{target}`) के लिए रिप्लाई टाइप करें:**")
            bot.register_next_step_handler(msg, send_reply_to_user, target)

    def process_complaint(message):
        bot.send_message(message.from_user.id, "✅ शिकायत एडमिन को भेज दी गई है।")
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("↩️ रिप्लाई करें", callback_data=f"reply_{message.from_user.id}"))
        bot.send_message(config.COMPLAINT_CHANNEL_ID, f"🚨 **नई शिकायत:**\n👤 **छात्र:** {message.from_user.first_name}\n💬 {message.text}", reply_markup=markup)

    def send_reply_to_user(message, target):
        try: 
            bot.send_message(int(target), f"🎧 **एडमिन सपोर्ट से उत्तर:**\n━━━━━━━━━━━━━━━━━━\n{message.text}", parse_mode="Markdown")
            bot.send_message(message.chat.id, "✅ **छात्र को सफलतापुर्वक रिप्लाई भेज दिया गया है।**")
        except Exception as e: 
            bot.send_message(message.chat.id, f"❌ एरर: {e}")

    if __name__ == "__main__":
        print("🚀 Bot Started Polling...", flush=True)
        while True:
            try: bot.infinity_polling(timeout=20, long_polling_timeout=10)
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e): time.sleep(30)
                else: time.sleep(5)

except Exception as e:
    print(f"\n💥 CRITICAL STARTUP ERROR 💥\nError: {e}", flush=True)
    traceback.print_exc()
    time.sleep(60)
