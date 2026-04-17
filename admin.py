import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import json
import requests
import config
import database

admin_data = {}

def register_admin_handlers(bot):
    def is_admin(user_id): return str(user_id) in config.ADMIN_IDS

    def render_admin_panel(chat_id, user_id, message_id=None):
        if not is_admin(user_id): return
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("📊 आंकड़े", callback_data="adm_stats"), InlineKeyboardButton("🖼️ इमेज लिंक", callback_data="adm_getlink"))
        markup.row(InlineKeyboardButton("📝 एग्जाम जोड़ें", callback_data="adm_addexam"), InlineKeyboardButton("📚 विषय जोड़ें", callback_data="adm_addsub"))
        markup.row(InlineKeyboardButton("🎯 नया टेस्ट डालें", callback_data="adm_addtest"), InlineKeyboardButton("🗑️ मैनेज (डिलीट)", callback_data="adm_manage"))
        markup.row(InlineKeyboardButton("📢 ब्रॉडकास्ट", callback_data="adm_broadcast"), InlineKeyboardButton("👤 यूज़र इन्फो", callback_data="adm_userinfo"))
        markup.row(InlineKeyboardButton("🚫 बैन/अनबैन", callback_data="adm_ban"))
        
        text = "👑 **सुपर एडमिन डैशबोर्ड**\nयहाँ से पूरे बॉट को कंट्रोल करें:"
        if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
        else: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

    @bot.message_handler(commands=['admin', 'panel'])
    def show_admin_panel_cmd(message):
        render_admin_panel(message.chat.id, message.from_user.id)

    @bot.callback_query_handler(func=lambda call: call.data == "adm_main")
    def back_to_admin_main(call):
        bot.answer_callback_query(call.id)
        render_admin_panel(call.message.chat.id, call.from_user.id, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
    def handle_admin_main(call):
        if call.data == "adm_main": return
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
        if not is_admin(call.from_user.id): return
        act = call.data.split("_")[1]
        
        if act == "stats":
            st = database.get_bot_stats()
            mk = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 वापस (Back)", callback_data="adm_main"))
            text = (
                "📊 **बॉट के विस्तृत आंकड़े (Bot Statistics)** 📊\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"👥 **कुल पंजीकृत छात्र:** `{st['total_users']}`\n"
                f"🚫 **बैन किए गए छात्र:** `{st['banned_users']}`\n"
                f"🎯 **कुल लाइव टेस्ट:** `{st['total_tests']}`\n"
                f"✍️ **कुल टेस्ट दिए गए:** `{st['total_attempts']}`\n"
                "━━━━━━━━━━━━━━━━━━"
            )
            bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=mk, parse_mode="Markdown")
            
        elif act == "addexam":
            msg = bot.send_message(chat_id, "📝 **नई परीक्षा का नाम लिखें:**", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 रद्द करें", callback_data="adm_main")))
            bot.register_next_step_handler(msg, lambda m: [database.add_category(m.text.strip(), "General"), bot.send_message(chat_id, "✅ जुड़ गया।", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 पैनल पर जाएँ", callback_data="adm_main")))])
            
        elif act == "addsub":
            exams = database.get_all_exams()
            if not exams: bot.send_message(chat_id, "❌ पहले एग्जाम जोड़ें।"); return
            m = InlineKeyboardMarkup()
            for e in exams: m.add(InlineKeyboardButton(e, callback_data=f"ad_sub_ex_{e}"))
            m.add(InlineKeyboardButton("🔙 वापस (Back)", callback_data="adm_main"))
            bot.edit_message_text("📚 **एग्जाम चुनें:**", chat_id, call.message.message_id, reply_markup=m)
            
        elif act == "addtest":
            msg = bot.send_message(chat_id, "🎯 **टेस्ट का ID लिखें:** (उदा: test_01)", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 रद्द करें", callback_data="adm_main")))
            bot.register_next_step_handler(msg, step_t_id)
            
        elif act == "getlink":
            msg = bot.send_message(chat_id, "🖼️ **लिंक बनाने के लिए फोटो भेजें:**", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 रद्द करें", callback_data="adm_main")))
            bot.register_next_step_handler(msg, make_image_link)
            
        elif act == "manage":
            m = InlineKeyboardMarkup()
            m.row(InlineKeyboardButton("🗑️ एग्जाम", callback_data="del_exm"), InlineKeyboardButton("🗑️ विषय", callback_data="del_sub"), InlineKeyboardButton("🗑️ टेस्ट", callback_data="del_tst"))
            m.add(InlineKeyboardButton("🔙 वापस (Back)", callback_data="adm_main"))
            bot.edit_message_text("⚠️ **क्या डिलीट करना है?**", chat_id, call.message.message_id, reply_markup=m)
            
        elif act == "broadcast":
            msg = bot.send_message(chat_id, "📢 **अपना ब्रॉडकास्ट मैसेज भेजें:**", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 रद्द करें", callback_data="adm_main")))
            bot.register_next_step_handler(msg, process_broadcast)
            
        elif act == "userinfo":
            msg = bot.send_message(chat_id, "👤 **यूज़र की ID (User ID) भेजें:**", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 रद्द करें", callback_data="adm_main")))
            bot.register_next_step_handler(msg, process_userinfo)
            
        elif act == "ban":
            msg = bot.send_message(chat_id, "🚫 **बैन करने के लिए ID भेजें:**", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 रद्द करें", callback_data="adm_main")))
            bot.register_next_step_handler(msg, ban_user)

    def process_broadcast(message):
        users = database.get_all_users()
        bot.send_message(message.chat.id, f"⏳ ब्रॉडकास्ट शुरू... (कुल: {len(users)})")
        success = 0
        for user_id in users:
            try: bot.copy_message(user_id, message.chat.id, message.message_id); success += 1
            except: pass 
        bot.send_message(message.chat.id, f"✅ सफलतापुर्वक भेजा गया: {success} छात्रों को।", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 पैनल पर जाएँ", callback_data="adm_main")))

    def process_userinfo(message):
        try:
            uid = int(message.text.strip())
            info = database.get_user_info(uid)
            if info:
                status = "🔴 बैन है" if info.get('is_banned') else "🟢 एक्टिव है"
                date = info['join_date'].strftime('%d-%m-%Y') if 'join_date' in info else "N/A"
                text = (f"👤 **यूज़र की जानकारी:**\n\n🆔 **ID:** `{info['user_id']}`\n📛 **नाम:** {info.get('first_name', 'N/A')}\n🌐 **Username:** @{info.get('username', 'N/A')}\n📅 **जॉइन डेट:** {date}\n✍️ **कुल टेस्ट दिए:** {info.get('total_tests_attempted', 0)}\n🛡️ **स्टेटस:** {status}")
                bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 वापस", callback_data="adm_main")))
            else: bot.send_message(message.chat.id, "❌ यह यूज़र डेटाबेस में नहीं मिला।", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 वापस", callback_data="adm_main")))
        except: bot.send_message(message.chat.id, "❌ कृपया सही नंबर (ID) डालें।")

    # 🖼️ FIX: Image Uploader with Headers
    def make_image_link(message):
        if message.content_type != 'photo':
            bot.send_message(message.chat.id, "⚠️ कृपया सिर्फ फोटो भेजें।"); return
        load_msg = bot.send_message(message.chat.id, "⏳ फोटो सर्वर पर अपलोड हो रही है...")
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            
            # कोशिश 1: Catbox
            try:
                res = requests.post('https://catbox.moe/user/api.php', data={'reqtype': 'fileupload'}, files={'fileToUpload': ('image.jpg', downloaded_file, 'image/jpeg')}, timeout=15, headers=headers)
                if res.status_code == 200 and "catbox.moe" in res.text:
                    mk = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 वापस (Back)", callback_data="adm_main"))
                    bot.edit_message_text(f"✅ **इमेज लिंक तैयार है:**\n\n`{res.text}`", message.chat.id, load_msg.message_id, reply_markup=mk)
                    return
            except: pass
            
            # कोशिश 2: Telegraph
            res2 = requests.post('https://telegra.ph/upload', files={'file': ('image.jpg', downloaded_file, 'image/jpeg')}, timeout=15)
            if res2.status_code == 200 and 'src' in res2.json()[0]:
                mk = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 वापस (Back)", callback_data="adm_main"))
                bot.edit_message_text(f"✅ **इमेज लिंक तैयार है:**\n\n`https://telegra.ph{res2.json()[0]['src']}`", message.chat.id, load_msg.message_id, reply_markup=mk)
            else: 
                bot.edit_message_text("❌ अपलोड फेल। सर्वर डाउन है।", message.chat.id, load_msg.message_id)
                
        except Exception as e:
            bot.edit_message_text(f"❌ सर्वर एरर: {e}", message.chat.id, load_msg.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("ad_sub_ex_"))
    def step_add_sub(call):
        bot.answer_callback_query(call.id)
        e = call.data.replace("ad_sub_ex_", "")
        msg = bot.send_message(call.message.chat.id, f"✅ {e}\n📝 **विषय लिखें:**")
        bot.register_next_step_handler(msg, lambda m: [database.add_category(e, m.text.strip()), bot.send_message(m.chat.id, "✅ जुड़ गया।", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 पैनल पर जाएँ", callback_data="adm_main")))])

    def step_t_id(m):
        admin_data[m.from_user.id] = {'id': m.text.strip()}
        exams = database.get_all_exams()
        mk = InlineKeyboardMarkup()
        for e in exams: mk.add(InlineKeyboardButton(e, callback_data=f"ad_tst_ex_{e}"))
        mk.add(InlineKeyboardButton("🔙 रद्द करें", callback_data="adm_main"))
        bot.send_message(m.chat.id, "📝 **एग्जाम चुनें:**", reply_markup=mk)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("ad_tst_ex_"))
    def step_t_ex(call):
        bot.answer_callback_query(call.id)
        e = call.data.replace("ad_tst_ex_", "")
        admin_data[call.from_user.id]['exam'] = e
        mk = InlineKeyboardMarkup()
        for s in database.get_subjects_by_exam(e): mk.add(InlineKeyboardButton(s, callback_data=f"ad_tst_su_{s}"))
        mk.add(InlineKeyboardButton("🔙 रद्द करें", callback_data="adm_main"))
        bot.edit_message_text("📚 **विषय चुनें:**", call.message.chat.id, call.message.message_id, reply_markup=mk)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("ad_tst_su_"))
    def step_t_su(call):
        bot.answer_callback_query(call.id)
        admin_data[call.from_user.id]['sub'] = call.data.replace("ad_tst_su_", "")
        msg = bot.send_message(call.message.chat.id, "🏷 **टेस्ट का नाम लिखें:**")
        bot.register_next_step_handler(msg, step_t_nm)

    def step_t_nm(m):
        admin_data[m.from_user.id]['name'] = m.text.strip()
        msg = bot.send_message(m.chat.id, "🚧 **कट-ऑफ (Cutoff) लिखें (अंकों में):**")
        bot.register_next_step_handler(msg, step_t_cf)

    def step_t_cf(m):
        try:
            admin_data[m.from_user.id]['cutoff'] = float(m.text.strip())
            msg = bot.send_message(m.chat.id, "⏱ **टेस्ट का समय (Time Limit) कितने मिनट का होगा?** (उदा: 15, 30):")
            bot.register_next_step_handler(msg, step_t_time)
        except ValueError: bot.send_message(m.chat.id, "❌ कृपया सिर्फ अंक लिखें।")

    def step_t_time(m):
        try:
            admin_data[m.from_user.id]['time_limit'] = int(m.text.strip())
            msg = bot.send_message(m.chat.id, "✅ **सही उत्तर (Positive Marking) पर कितने अंक देने हैं?** (उदा: 2.0 या 1.0):")
            bot.register_next_step_handler(msg, step_t_pos)
        except ValueError: bot.send_message(m.chat.id, "❌ कृपया सिर्फ मिनट (अंक) लिखें।")

    def step_t_pos(m):
        try:
            admin_data[m.from_user.id]['pos_mark'] = float(m.text.strip())
            msg = bot.send_message(m.chat.id, "❌ **गलत उत्तर (Negative Marking) पर कितने अंक काटने हैं?** (उदा: 0.25 या 0.50):")
            bot.register_next_step_handler(msg, step_t_neg)
        except ValueError: bot.send_message(m.chat.id, "❌ कृपया सिर्फ अंक लिखें।")

    def step_t_neg(m):
        try:
            admin_data[m.from_user.id]['neg_mark'] = float(m.text.strip())
            msg = bot.send_message(m.chat.id, "📂 **शानदार! अब प्रश्नों वाली `.json` फाइल भेजें:**")
            bot.register_next_step_handler(msg, process_j)
        except ValueError: bot.send_message(m.chat.id, "❌ कृपया सिर्फ अंक लिखें।")

    def process_j(m):
        d = admin_data.get(m.from_user.id)
        if m.document and m.document.file_name.endswith('.json'):
            try:
                file_info = bot.get_file(m.document.file_id)
                jd = json.loads(bot.download_file(file_info.file_path))
                database.save_test(d['id'], d['exam'], d['sub'], d['name'], d['pos_mark'], d['neg_mark'], d['cutoff'], d['time_limit'], jd)
                preview_url = f"{config.WEBAPP_BASE_URL}{d['id']}"
                mk = InlineKeyboardMarkup().add(InlineKeyboardButton("👁️ प्रीव्यू", web_app=WebAppInfo(url=preview_url))).add(InlineKeyboardButton("📢 पब्लिक करें", callback_data=f"pub_{d['id']}"))
                bot.send_message(m.chat.id, f"✅ **सेव हो गया!**\n⏱ समय: {d['time_limit']} मिनट\n✅ सही: +{d['pos_mark']} | ❌ गलत: -{d['neg_mark']}", reply_markup=mk)
            except Exception as e:
                bot.send_message(m.chat.id, f"❌ फाइल एरर: {e}")
        else:
            bot.send_message(m.chat.id, "❌ कृपया `.json` फाइल भेजें।")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("pub_"))
    def pub_t(call):
        bot.answer_callback_query(call.id)
        tid = call.data.replace("pub_", "")
        database.make_test_public(tid)
        t_data = database.get_test_details(tid)
        if t_data:
            msg = (f"🚀 **नया मॉक टेस्ट लाइव हो गया है!**\n\n📚 **परीक्षा:** {t_data['exam_name']}\n📖 **विषय:** {t_data['subject_name']}\n📝 **टेस्ट:** {t_data['test_name']}\n⏱ **समय:** {t_data['time_limit']} मिनट\n\n👇 **अभी बॉट में जाएं और टेस्ट दें!**")
            try: bot.send_message(config.PUBLIC_CHANNEL_ID, msg)
            except: pass
        bot.edit_message_text("✅ **टेस्ट लाइव कर दिया गया है!**", call.message.chat.id, call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 पैनल पर जाएँ", callback_data="adm_main")))

    @bot.callback_query_handler(func=lambda call: call.data in ["del_exm", "del_sub", "del_tst"])
    def del_menu(call):
        bot.answer_callback_query(call.id)
        if call.data == "del_exm":
            mk = InlineKeyboardMarkup()
            for e in database.get_all_exams(): mk.add(InlineKeyboardButton(f"❌ {e}", callback_data=f"cfm_ex_{e}"))
            mk.add(InlineKeyboardButton("🔙 वापस (Back)", callback_data="adm_main"))
            bot.edit_message_text("⚠️ **डिलीट करने के लिए एग्जाम चुनें:**", call.message.chat.id, call.message.message_id, reply_markup=mk)
        elif call.data == "del_sub":
            mk = InlineKeyboardMarkup()
            for e in database.get_all_exams(): mk.add(InlineKeyboardButton(e, callback_data=f"ds_ex_{e}"))
            mk.add(InlineKeyboardButton("🔙 वापस (Back)", callback_data="adm_main"))
            bot.edit_message_text("⚠️ **विषय डिलीट करने के लिए पहले एग्जाम चुनें:**", call.message.chat.id, call.message.message_id, reply_markup=mk)
        elif call.data == "del_tst":
            msg = bot.send_message(call.message.chat.id, "🗑 **Test ID भेजें:**", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 रद्द करें", callback_data="adm_main")))
            bot.register_next_step_handler(msg, lambda m: [database.delete_test(m.text.strip()), bot.send_message(m.chat.id, "✅ डिलीट हो गया।", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 वापस", callback_data="adm_main")))])

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cfm_ex_"))
    def cfm_ex(call):
        bot.answer_callback_query(call.id)
        database.delete_exam(call.data.replace("cfm_ex_", ""))
        bot.edit_message_text("✅ एग्जाम डिलीट हो गया।", call.message.chat.id, call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 वापस", callback_data="adm_main")))

    @bot.callback_query_handler(func=lambda call: call.data.startswith("ds_ex_"))
    def ds_ex(call):
        bot.answer_callback_query(call.id)
        e = call.data.replace("ds_ex_", "")
        mk = InlineKeyboardMarkup()
        for s in database.get_subjects_by_exam(e): mk.add(InlineKeyboardButton(f"❌ {s}", callback_data=f"cfm_su_{e}_{s}"))
        mk.add(InlineKeyboardButton("🔙 वापस (Back)", callback_data="adm_main"))
        bot.edit_message_text(f"⚠️ **{e} से विषय डिलीट करें:**", call.message.chat.id, call.message.message_id, reply_markup=mk)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cfm_su_"))
    def cfm_su(call):
        bot.answer_callback_query(call.id)
        parts = call.data.replace("cfm_su_", "").split("_")
        database.delete_subject(parts[0], parts[1])
        bot.edit_message_text("✅ विषय डिलीट हो गया।", call.message.chat.id, call.message.message_id, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 पैनल पर जाएँ", callback_data="adm_main")))

    def ban_user(m):
        try:
            tid = int(m.text.strip())
            database.update_ban_status(tid, not database.check_banned(tid))
            bot.send_message(m.chat.id, f"✅ बैन स्टेटस बदल दिया गया।", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 पैनल पर जाएँ", callback_data="adm_main")))
        except:
            bot.send_message(m.chat.id, "❌ गलत ID")
