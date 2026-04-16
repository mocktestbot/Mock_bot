# admin.py
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import requests
import config
import database

admin_data = {}

def register_admin_handlers(bot):
    def is_admin(user_id): return user_id in config.ADMIN_IDS

    @bot.message_handler(commands=['admin', 'panel'])
    def show_admin_panel(message):
        if not is_admin(message.from_user.id): return
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📊 आंकड़े", callback_data="adm_stats"), InlineKeyboardButton("🖼️ इमेज लिंक", callback_data="adm_getlink"))
        markup.row(InlineKeyboardButton("📝 एग्जाम जोड़ें", callback_data="adm_addexam"), InlineKeyboardButton("📚 विषय जोड़ें", callback_data="adm_addsub"))
        markup.row(InlineKeyboardButton("🎯 नया टेस्ट डालें", callback_data="adm_addtest"))
        markup.row(InlineKeyboardButton("🗑️ मैनेज (डिलीट)", callback_data="adm_manage"), InlineKeyboardButton("🚫 बैन/अनबैन", callback_data="adm_ban"))
        bot.send_message(message.chat.id, "👑 **सुपर एडमिन डैशबोर्ड**", reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
    def handle_admin_main(call):
        bot.answer_callback_query(call.id) # 🛠️ NOT RESPONDING FIX
        chat_id = call.message.chat.id
        if not is_admin(call.from_user.id): return
        act = call.data.split("_")[1]
        
        if act == "stats":
            st = database.get_bot_stats()
            bot.send_message(chat_id, f"📊 **आंकड़े:**\n👥 छात्र: `{st['total_users']}`\n🚫 बैन: `{st['banned_users']}`\n🎯 टेस्ट: `{st['total_tests']}`")
        elif act == "addexam":
            msg = bot.send_message(chat_id, "📝 **नई परीक्षा का नाम लिखें:**")
            bot.register_next_step_handler(msg, lambda m: [database.add_category(m.text.strip(), "General"), bot.send_message(chat_id, "✅ जुड़ गया।")])
        elif act == "addsub":
            exams = database.get_all_exams()
            if not exams: 
                bot.send_message(chat_id, "❌ पहले एग्जाम जोड़ें।")
                return
            m = InlineKeyboardMarkup()
            for e in exams: m.add(InlineKeyboardButton(e, callback_data=f"ad_sub_ex_{e}"))
            bot.send_message(chat_id, "📚 **एग्जाम चुनें:**", reply_markup=m)
        elif act == "addtest":
            msg = bot.send_message(chat_id, "🎯 **टेस्ट का ID लिखें:** (उदा: test_01)")
            bot.register_next_step_handler(msg, step_t_id)
        elif act == "getlink":
            msg = bot.send_message(chat_id, "🖼️ **लिंक बनाने के लिए फोटो भेजें:**")
            bot.register_next_step_handler(msg, make_image_link) # 🛠️ नया फिक्स फंक्शन
        elif act == "ban":
            msg = bot.send_message(chat_id, "🚫 **यूज़र ID भेजें:**")
            bot.register_next_step_handler(msg, ban_user)
        elif act == "manage":
            m = InlineKeyboardMarkup()
            m.row(InlineKeyboardButton("🗑️ एग्जाम हटाएं", callback_data="del_exm"), InlineKeyboardButton("🗑️ विषय हटाएं", callback_data="del_sub"))
            m.row(InlineKeyboardButton("🗑️ टेस्ट हटाएं", callback_data="del_tst"))
            bot.send_message(chat_id, "⚠️ **क्या डिलीट करना है?**", reply_markup=m)

    # ==========================================
    # 🖼️ इमेज लिंक जनरेटर (100% परमानेंट फिक्स)
    # ==========================================
    def make_image_link(message):
        if message.content_type != 'photo':
            bot.send_message(message.chat.id, "⚠️ कृपया सिर्फ फोटो भेजें।")
            return
            
        load_msg = bot.send_message(message.chat.id, "⏳ फोटो अपलोड हो रही है, कृपया प्रतीक्षा करें...")
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            res = requests.post(
                'https://telegra.ph/upload', 
                files={'file': ('image.jpg', downloaded_file, 'image/jpeg')}
            )
            
            if res.status_code == 200:
                data = res.json()
                if type(data) is list and 'src' in data[0]:
                    img_url = f"https://telegra.ph{data[0]['src']}"
                    bot.edit_message_text(f"✅ **इमेज लिंक तैयार है:**\n\n`{img_url}`\n\n*(इसे कॉपी करने के लिए लिंक पर क्लिक करें)*", message.chat.id, load_msg.message_id, parse_mode="Markdown")
                elif 'error' in data:
                    bot.edit_message_text(f"❌ अपलोड फेल (Telegraph Error): {data['error']}", message.chat.id, load_msg.message_id)
            else:
                bot.edit_message_text(f"❌ सर्वर एरर: API ने जवाब नहीं दिया।", message.chat.id, load_msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ तकनीकी एरर: {e}", message.chat.id, load_msg.message_id)

    # ==========================================
    # --- Add Subject Flow ---
    # ==========================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("ad_sub_ex_"))
    def step_add_sub(call):
        bot.answer_callback_query(call.id)
        e = call.data.replace("ad_sub_ex_", "")
        msg = bot.send_message(call.message.chat.id, f"✅ {e} चुना गया।\n📝 **विषय का नाम लिखें:**")
        bot.register_next_step_handler(msg, lambda m: [database.add_category(e, m.text.strip()), bot.send_message(m.chat.id, "✅ जुड़ गया।")])

    # ==========================================
    # --- Add Test Flow ---
    # ==========================================
    def step_t_id(m):
        admin_data[m.from_user.id] = {'id': m.text.strip()}
        exams = database.get_all_exams()
        if not exams: bot.send_message(m.chat.id, "❌ एग्जाम नहीं है।"); return
        mk = InlineKeyboardMarkup()
        for e in exams: mk.add(InlineKeyboardButton(e, callback_data=f"ad_tst_ex_{e}"))
        bot.send_message(m.chat.id, "📝 **एग्जाम चुनें:**", reply_markup=mk)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("ad_tst_ex_"))
    def step_t_ex(call):
        bot.answer_callback_query(call.id)
        e = call.data.replace("ad_tst_ex_", "")
        admin_data[call.from_user.id]['exam'] = e
        subs = database.get_subjects_by_exam(e)
        if not subs: 
            bot.send_message(call.message.chat.id, "❌ विषय नहीं है। पहले विषय जोड़ें।")
            return
        mk = InlineKeyboardMarkup()
        for s in subs: mk.add(InlineKeyboardButton(s, callback_data=f"ad_tst_su_{s}"))
        bot.edit_message_text("📚 **विषय चुनें:**", call.message.chat.id, call.message.message_id, reply_markup=mk)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("ad_tst_su_"))
    def step_t_su(call):
        bot.answer_callback_query(call.id)
        admin_data[call.from_user.id]['sub'] = call.data.replace("ad_tst_su_", "")
        msg = bot.send_message(call.message.chat.id, "🏷 **टेस्ट का नाम लिखें:**")
        bot.register_next_step_handler(msg, step_t_nm)

    def step_t_nm(m):
        admin_data[m.from_user.id]['name'] = m.text.strip()
        msg = bot.send_message(m.chat.id, "🚧 **कट-ऑफ लिखें (अंकों में):**")
        bot.register_next_step_handler(msg, step_t_cf)

    def step_t_cf(m):
        try:
            admin_data[m.from_user.id]['cutoff'] = float(m.text.strip())
            msg = bot.send_message(m.chat.id, "📂 **.json फाइल भेजें:**")
            bot.register_next_step_handler(msg, process_j)
        except ValueError:
            bot.send_message(m.chat.id, "❌ कट-ऑफ सिर्फ अंकों में होनी चाहिए।")

    def process_j(m):
        d = admin_data.get(m.from_user.id)
        if not d: return
        if m.document and m.document.file_name.endswith('.json'):
            try:
                file_info = bot.get_file(m.document.file_id)
                jd = json.loads(bot.download_file(file_info.file_path))
                database.save_test(d['id'], d['exam'], d['sub'], d['name'], config.DEFAULT_POSITIVE_MARK, config.DEFAULT_NEGATIVE_MARK, d['cutoff'], jd)
                mk = InlineKeyboardMarkup().add(InlineKeyboardButton("👁️ प्रीव्यू", url=f"{config.WEBAPP_BASE_URL}{d['id']}")).add(InlineKeyboardButton("📢 पब्लिक करें", callback_data=f"pub_{d['id']}"))
                bot.send_message(m.chat.id, f"✅ सेव हो गया।", reply_markup=mk)
                admin_data.pop(m.from_user.id, None) # मेमोरी क्लीन
            except Exception as e:
                bot.send_message(m.chat.id, f"❌ JSON एरर: {e}")
        else:
            bot.send_message(m.chat.id, "❌ कृपया .json फाइल भेजें।")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("pub_"))
    def pub_t(call):
        bot.answer_callback_query(call.id)
        database.make_test_public(call.data.replace("pub_", ""))
        bot.edit_message_text("✅ लाइव हो गया!", call.message.chat.id, call.message.message_id)
        bot.send_message(config.PUBLIC_CHANNEL_ID, f"🚀 **नया मॉक टेस्ट उपलब्ध है!**\n\n🎯 अभी बॉट में जाएं और अपना टेस्ट दें।")

    # ==========================================
    # --- Manage/Delete Flow ---
    # ==========================================
    @bot.callback_query_handler(func=lambda call: call.data in ["del_exm", "del_sub", "del_tst"])
    def del_menu(call):
        bot.answer_callback_query(call.id)
        if call.data == "del_exm":
            mk = InlineKeyboardMarkup()
            for e in database.get_all_exams(): mk.add(InlineKeyboardButton(f"❌ {e}", callback_data=f"cfm_ex_{e}"))
            bot.send_message(call.message.chat.id, "⚠️ **डिलीट करने के लिए एग्जाम चुनें:**", reply_markup=mk)
        elif call.data == "del_sub":
            mk = InlineKeyboardMarkup()
            for e in database.get_all_exams(): mk.add(InlineKeyboardButton(e, callback_data=f"ds_ex_{e}"))
            bot.send_message(call.message.chat.id, "⚠️ **विषय डिलीट करने के लिए पहले एग्जाम चुनें:**", reply_markup=mk)
        elif call.data == "del_tst":
            msg = bot.send_message(call.message.chat.id, "🗑 **डिलीट करने के लिए Test ID भेजें:**")
            bot.register_next_step_handler(msg, lambda m: [database.delete_test(m.text.strip()), bot.send_message(m.chat.id, "✅ डिलीट हो गया।")])

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cfm_ex_"))
    def cfm_ex(call):
        bot.answer_callback_query(call.id)
        database.delete_exam(call.data.replace("cfm_ex_", ""))
        bot.edit_message_text("✅ एग्जाम डिलीट हो गया।", call.message.chat.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("ds_ex_"))
    def ds_ex(call):
        bot.answer_callback_query(call.id)
        e = call.data.replace("ds_ex_", "")
        mk = InlineKeyboardMarkup()
        for s in database.get_subjects_by_exam(e): mk.add(InlineKeyboardButton(f"❌ {s}", callback_data=f"cfm_su_{e}_{s}"))
        bot.edit_message_text(f"⚠️ **{e} से विषय डिलीट करें:**", call.message.chat.id, call.message.message_id, reply_markup=mk)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cfm_su_"))
    def cfm_su(call):
        bot.answer_callback_query(call.id)
        parts = call.data.replace("cfm_su_", "").split("_")
        database.delete_subject(parts[0], parts[1])
        bot.edit_message_text("✅ विषय डिलीट हो गया।", call.message.chat.id, call.message.message_id)

    def ban_user(m):
        try:
            tid = int(m.text.strip())
            ns = not database.check_banned(tid)
            database.update_ban_status(tid, ns)
            bot.send_message(m.chat.id, f"✅ बैन स्टेटस बदला गया: {ns}")
        except: bot.send_message(m.chat.id, "❌ गलत ID")
