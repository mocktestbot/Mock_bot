# admin.py
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import requests
import config
import database

# एडमिन का डेटा टेम्पररी सेव करने के लिए डिक्शनरी
admin_test_data = {}

def register_admin_handlers(bot):
    def is_admin(user_id):
        return user_id in config.ADMIN_IDS

    # 👑 सुपर एडमिन डैशबोर्ड 👑
    @bot.message_handler(commands=['admin', 'panel'])
    def show_admin_panel(message):
        if not is_admin(message.from_user.id): return
        
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📊 बॉट के आंकड़े", callback_data="adm_stats"))
        markup.row(
            InlineKeyboardButton("📝 एग्जाम जोड़ें", callback_data="adm_addexam"),
            InlineKeyboardButton("📚 विषय जोड़ें", callback_data="adm_addsub")
        )
        markup.row(InlineKeyboardButton("🎯 नया मॉक टेस्ट डालें", callback_data="adm_addtest"))
        markup.row(
            InlineKeyboardButton("🗑️ मैनेज (डिलीट)", callback_data="adm_manage"),
            InlineKeyboardButton("🚫 बैन / अनबैन", callback_data="adm_ban")
        )
        markup.row(InlineKeyboardButton("🖼️ इमेज लिंक बनाएं", callback_data="adm_getlink"))
        
        bot.send_message(
            message.chat.id, 
            "👑 **सुपर एडमिन डैशबोर्ड** 👑\n\nयहाँ से पूरे बॉट को कंट्रोल करें:",
            reply_markup=markup, parse_mode="Markdown"
        )

    # 🎛️ एडमिन बटनों को हैंडल करना
    @bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
    def handle_admin_panel_clicks(call):
        bot.answer_callback_query(call.id) # 'Bot not responding' का पक्का इलाज
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        if not is_admin(user_id): return
        
        action = call.data.split("_")[1]
        
        if action == "stats":
            stats = database.get_bot_stats()
            text = f"📊 **लाइव आंकड़े**\n\n👥 कुल छात्र: `{stats['total_users']}`\n🚫 बैन यूज़र्स: `{stats['banned_users']}`\n🎯 कुल टेस्ट: `{stats['total_tests']}`\n✍️ कुल दिए गए टेस्ट: `{stats['total_attempts']}`"
            bot.send_message(chat_id, text, parse_mode="Markdown")
            
        elif action == "addexam":
            msg = bot.send_message(chat_id, "📝 **नई परीक्षा का नाम टाइप करें:** (उदा: SSC GD)")
            bot.register_next_step_handler(msg, process_add_exam)
            
        elif action == "addsub":
            exams = database.get_all_exams()
            if not exams:
                bot.send_message(chat_id, "❌ **अभी कोई परीक्षा उपलब्ध नहीं है।** पहले 'एग्जाम जोड़ें' पर क्लिक करें।")
                return
            markup = InlineKeyboardMarkup()
            for exam in exams:
                markup.add(InlineKeyboardButton(exam, callback_data=f"selsub_{exam}"))
            bot.send_message(chat_id, "📚 **विषय जोड़ने के लिए परीक्षा (Exam) चुनें:**", reply_markup=markup)
            
        elif action == "addtest":
            msg = bot.send_message(chat_id, "🎯 **टेस्ट का ID टाइप करें:** (उदा: ssc_gk_01)")
            bot.register_next_step_handler(msg, step_test_id_input)
            
        elif action == "getlink":
            msg = bot.send_message(chat_id, "🖼️ **कृपया फोटो भेजें:**")
            bot.register_next_step_handler(msg, process_image_for_link)
            
        elif action == "manage":
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("🗑️ एग्जाम हटाएं", callback_data="del_exam"))
            markup.row(InlineKeyboardButton("🗑️ विषय हटाएं", callback_data="del_sub_sel"))
            markup.row(InlineKeyboardButton("🗑️ टेस्ट हटाएं", callback_data="del_test"))
            bot.send_message(chat_id, "⚠️ **क्या डिलीट करना है?**", reply_markup=markup)

        elif action == "ban":
            msg = bot.send_message(chat_id, "🚫 **यूज़र को बैन/अनबैन करने के लिए उसकी ID भेजें:**")
            bot.register_next_step_handler(msg, process_ban_user)

    # ==========================================
    # 📚 एग्जाम और विषय जोड़ने का फ्लो
    # ==========================================
    def process_add_exam(message):
        exam_name = message.text.strip()
        database.add_category(exam_name, "General")
        bot.send_message(message.chat.id, f"✅ **{exam_name}** परीक्षा सफलतापूर्वक जोड़ दी गई है।")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("selsub_"))
    def select_exam_for_subject(call):
        bot.answer_callback_query(call.id)
        exam_name = call.data.replace("selsub_", "")
        msg = bot.send_message(call.message.chat.id, f"✅ **{exam_name}** चुना गया।\n📝 **अब नए विषय का नाम टाइप करें:** (उदा: Reasoning)")
        bot.register_next_step_handler(msg, lambda m: process_add_subject_final(m, exam_name))

    def process_add_subject_final(message, exam_name):
        subject_name = message.text.strip()
        database.add_category(exam_name, subject_name)
        bot.send_message(message.chat.id, f"✅ **{exam_name}** में **{subject_name}** विषय जोड़ दिया गया है।")

    # ==========================================
    # 🎯 टेस्ट अपलोड फ्लो (ऑटोमैटिक बटनों के साथ)
    # ==========================================
    def step_test_id_input(message):
        test_id = message.text.strip()
        user_id = message.from_user.id
        admin_test_data[user_id] = {'test_id': test_id}
        
        exams = database.get_all_exams()
        if not exams:
            bot.send_message(message.chat.id, "❌ **अभी कोई परीक्षा उपलब्ध नहीं है।** पहले परीक्षा जोड़ें।")
            return
            
        markup = InlineKeyboardMarkup()
        for exam in exams:
            markup.add(InlineKeyboardButton(exam, callback_data=f"addt_ex_{exam}"))
        bot.send_message(message.chat.id, f"✅ टेस्ट ID सेव।\n📝 **किस परीक्षा (Exam) में टेस्ट डालना है, उसे चुनें:**", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("addt_ex_"))
    def step_select_exam_for_test(call):
        bot.answer_callback_query(call.id)
        exam_name = call.data.replace("addt_ex_", "")
        user_id = call.from_user.id
        
        if user_id not in admin_test_data: admin_test_data[user_id] = {}
        admin_test_data[user_id]['exam_name'] = exam_name
        
        subjects = database.get_subjects_by_exam(exam_name)
        if not subjects:
            bot.send_message(call.message.chat.id, f"❌ **{exam_name}** में कोई विषय नहीं है। पहले विषय जोड़ें।")
            return
            
        markup = InlineKeyboardMarkup()
        for sub in subjects:
            markup.add(InlineKeyboardButton(sub, callback_data=f"addt_su_{sub}"))
        bot.edit_message_text(f"✅ परीक्षा: {exam_name}\n📚 **अब विषय (Subject) चुनें:**", call.message.chat.id, call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("addt_su_"))
    def step_select_sub_for_test(call):
        bot.answer_callback_query(call.id)
        sub_name = call.data.replace("addt_su_", "")
        user_id = call.from_user.id
        
        if user_id in admin_test_data:
            admin_test_data[user_id]['subject_name'] = sub_name
            
        msg = bot.send_message(call.message.chat.id, f"✅ विषय: {sub_name}\n🏷 **टेस्ट का नाम लिखें** (उदा: Mock Test - 01):")
        bot.register_next_step_handler(msg, step_test_name_input)

    def step_test_name_input(message):
        test_name = message.text.strip()
        user_id = message.from_user.id
        if user_id in admin_test_data:
            admin_test_data[user_id]['test_name'] = test_name
            
        msg = bot.send_message(message.chat.id, "🚧 **इस टेस्ट की कट-ऑफ (Cutoff) कितने अंक रखें?** (उदा: 35):")
        bot.register_next_step_handler(msg, step_cutoff_input)

    def step_cutoff_input(message):
        try:
            cutoff = float(message.text.strip())
            user_id = message.from_user.id
            if user_id in admin_test_data:
                admin_test_data[user_id]['cutoff'] = cutoff
                
            msg = bot.send_message(message.chat.id, "📂 **शानदार! अब प्रश्नों वाली `.json` फाइल अपलोड करें:**")
            bot.register_next_step_handler(msg, process_json_file)
        except ValueError:
            bot.send_message(message.chat.id, "❌ कट-ऑफ सिर्फ अंकों में होनी चाहिए। दोबारा /admin टाइप करें।")

    def process_json_file(message):
        user_id = message.from_user.id
        if user_id not in admin_test_data: return
        
        data = admin_test_data[user_id]
        
        if message.document and message.document.file_name.endswith('.json'):
            try:
                file_info = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                questions_data = json.loads(downloaded_file)

                database.save_test(
                    data['test_id'], data['exam_name'], data['subject_name'],
                    data['test_name'], config.DEFAULT_POSITIVE_MARK, config.DEFAULT_NEGATIVE_MARK, 
                    data['cutoff'], questions_data
                )

                markup = InlineKeyboardMarkup()
                preview_url = f"{config.WEBAPP_BASE_URL}{data['test_id']}"
                markup.add(InlineKeyboardButton("👁️ टेस्ट प्रीव्यू करें (Preview)", url=preview_url))
                markup.add(InlineKeyboardButton("📢 पब्लिक कर दें (Publish)", callback_data=f"publish_{data['test_id']}"))

                bot.send_message(
                    message.chat.id, 
                    f"✅ **टेस्ट सफलतापूर्वक सेव हो गया है!**\n\nकुल प्रश्न: {len(questions_data)}\nकट-ऑफ: {data['cutoff']}\n\nकृपया पब्लिक करने से पहले प्रीव्यू बटन पर क्लिक करके टेस्ट चेक कर लें।", 
                    reply_markup=markup
                )
                admin_test_data.pop(user_id, None) # मेमोरी साफ करना
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ JSON फाइल पढ़ने में त्रुटि: {e}")
        else:
            bot.send_message(message.chat.id, "❌ कृपया एक वैध `.json` फाइल भेजें।")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("publish_"))
    def publish_test(call):
        bot.answer_callback_query(call.id)
        if not is_admin(call.from_user.id): return
        test_id = call.data.split("_")[1]
        database.make_test_public(test_id)
        bot.edit_message_text("✅ **टेस्ट सफलतापूर्वक पब्लिक (लाइव) कर दिया गया है!**", call.message.chat.id, call.message.message_id)
        bot.send_message(config.PUBLIC_CHANNEL_ID, f"🚀 **नया मॉक टेस्ट उपलब्ध है!**\n\n🎯 अभी बॉट में जाएं और अपना टेस्ट दें।")

    # ==========================================
    # 🗑️ मैनेज / डिलीट और अन्य फ्लो (Ban, Image)
    # ==========================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
    def handle_delete(call):
        bot.answer_callback_query(call.id)
        
        if call.data == "del_exam":
            exams = database.get_all_exams()
            if not exams:
                bot.send_message(call.message.chat.id, "❌ कोई एग्जाम नहीं है।")
                return
            markup = InlineKeyboardMarkup()
            for exam in exams: markup.add(InlineKeyboardButton(f"❌ {exam}", callback_data=f"confirmdel_{exam}"))
            bot.send_message(call.message.chat.id, "⚠️ **डिलीट करने के लिए एग्जाम चुनें (इसके सारे विषय और टेस्ट भी मिट जाएंगे):**", reply_markup=markup)
            
        elif call.data == "del_sub_sel":
            bot.send_message(call.message.chat.id, "⚠️ यह फीचर सीधे डेटाबेस से मैनेज किया जा सकता है।")
            
        elif call.data == "del_test":
            msg = bot.send_message(call.message.chat.id, "🗑️ **डिलीट करने के लिए टेस्ट की ID (Test ID) भेजें:**")
            bot.register_next_step_handler(msg, lambda m: process_delete_test(m))

    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirmdel_"))
    def confirm_delete_exam(call):
        bot.answer_callback_query(call.id)
        exam_name = call.data.replace("confirmdel_", "")
        database.delete_exam(exam_name)
        bot.edit_message_text(f"✅ **{exam_name}** और उसके सारे टेस्ट हमेशा के लिए डिलीट कर दिए गए हैं।", call.message.chat.id, call.message.message_id)

    def process_delete_test(message):
        test_id = message.text.strip()
        database.delete_test(test_id)
        bot.send_message(message.chat.id, f"✅ टेस्ट `{test_id}` डिलीट कर दिया गया है।")

    def process_ban_user(message):
        try:
            target_id = int(message.text.strip())
            is_banned = database.check_banned(target_id)
            new_status = not is_banned
            database.update_ban_status(target_id, new_status)
            status_text = "बैन (Banned) 🚫" if new_status else "अनबैन (Unbanned) ✅"
            bot.send_message(message.chat.id, f"✅ यूज़र ID `{target_id}` को सफलतापूर्वक **{status_text}** कर दिया गया है।")
        except:
            bot.send_message(message.chat.id, "❌ कृपया सही नंबर (User ID) डालें।")

    def process_image_for_link(message):
        if message.content_type != 'photo':
            bot.send_message(message.chat.id, "⚠️ कृपया सिर्फ फोटो भेजें।")
            return
        bot.send_message(message.chat.id, "⏳ फोटो अपलोड हो रही है...")
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            response = requests.post('https://telegra.ph/upload', files={'file': ('image.jpg', downloaded_file, 'image/jpeg')}).json()
            if type(response) is list:
                img_url = f"https://telegra.ph{response[0]['src']}"
                bot.send_message(message.chat.id, f"✅ **इमेज लिंक:**\n`{img_url}`")
        except:
            bot.send_message(message.chat.id, "❌ अपलोड फेल।")
