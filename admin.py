# admin.py
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import requests
import config
import database

def register_admin_handlers(bot):
    
    # चेक करने का फंक्शन कि यूज़र एडमिन है या नहीं
    def is_admin(user_id):
        return user_id in config.ADMIN_IDS

    # ==========================================
    # 1. स्टैट्स और यूज़र इन्फो (Stats & User Info)
    # ==========================================
    @bot.message_handler(commands=['stats'])
    def show_stats(message):
        if not is_admin(message.from_user.id): return
        stats = database.get_bot_stats()
        text = (
            "📊 **बॉट लाइव सांख्यिकी (Live Stats)**\n\n"
            f"👥 कुल पंजीकृत छात्र: `{stats['total_users']}`\n"
            f"🚫 बैन किए गए यूज़र्स: `{stats['banned_users']}`\n"
            f"🎯 कुल मॉक टेस्ट लाइव: `{stats['total_tests']}`\n"
            f"✍️ कुल दिए गए टेस्ट: `{stats['total_attempts']}`\n"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    # ==========================================
    # 2. एग्जाम और विषय जोड़ना (Add Exam & Subject)
    # ==========================================
    @bot.message_handler(commands=['addexam'])
    def add_exam(message):
        if not is_admin(message.from_user.id): return
        msg = bot.send_message(message.chat.id, "📝 **नई परीक्षा का नाम टाइप करें:** (उदा: UP Police)")
        bot.register_next_step_handler(msg, process_add_exam)

    def process_add_exam(message):
        exam_name = message.text.strip()
        database.add_category(exam_name, "General") # डिफ़ॉल्ट विषय
        bot.send_message(message.chat.id, f"✅ **{exam_name}** परीक्षा सफलतापूर्वक जोड़ दी गई है।")

    @bot.message_handler(commands=['addsubject'])
    def add_subject(message):
        if not is_admin(message.from_user.id): return
        msg = bot.send_message(message.chat.id, "📚 **किस परीक्षा में विषय जोड़ना है? (परीक्षा का नाम लिखें):**")
        bot.register_next_step_handler(msg, process_add_subject_exam)

    def process_add_subject_exam(message):
        exam_name = message.text.strip()
        msg = bot.send_message(message.chat.id, "📝 **अब नए विषय का नाम टाइप करें:** (उदा: Hindi)")
        bot.register_next_step_handler(msg, lambda m: process_add_subject_final(m, exam_name))

    def process_add_subject_final(message, exam_name):
        subject_name = message.text.strip()
        database.add_category(exam_name, subject_name)
        bot.send_message(message.chat.id, f"✅ **{exam_name}** में **{subject_name}** विषय जोड़ दिया गया है।")

    # ==========================================
    # 3. इमेज के लिए टेलीग्राफ लिंक (Get Link)
    # ==========================================
    @bot.message_handler(commands=['getlink'], content_types=['photo'])
    def generate_image_link(message):
        if not is_admin(message.from_user.id): return
        
        if message.content_type != 'photo':
            bot.send_message(message.chat.id, "⚠️ कृपया इस कमांड के साथ एक फोटो (डायग्राम) भेजें।")
            return

        bot.send_message(message.chat.id, "⏳ फोटो अपलोड हो रही है...")
        try:
            file_info = bot.get_file(message.photo[-1].file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            # Telegraph सर्वर पर भेजना
            response = requests.post(
                'https://telegra.ph/upload',
                files={'file': ('image.jpg', downloaded_file, 'image/jpeg')}
            ).json()
            
            if type(response) is list:
                img_url = f"https://telegra.ph{response[0]['src']}"
                bot.send_message(message.chat.id, f"✅ **इमेज लिंक तैयार है:**\n`{img_url}`\n\n(इसे कॉपी करके अपनी JSON फाइल में 'img' वाले हिस्से में पेस्ट करें)", parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "❌ अपलोड फेल हो गया।")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ एरर: {e}")

    # ==========================================
    # 4. टेस्ट अपलोड सिस्टम (Add Test Flow)
    # ==========================================
    @bot.message_handler(commands=['addtest'])
    def start_add_test(message):
        if not is_admin(message.from_user.id): return
        msg = bot.send_message(message.chat.id, "🎯 **टेस्ट का ID टाइप करें** (उदा: ssc_gk_01):")
        bot.register_next_step_handler(msg, step_exam_name)

    def step_exam_name(message):
        test_id = message.text.strip()
        msg = bot.send_message(message.chat.id, "📝 **परीक्षा का नाम लिखें** (उदा: SSC GD):")
        bot.register_next_step_handler(msg, lambda m: step_subject_name(m, test_id))

    def step_subject_name(message, test_id):
        exam_name = message.text.strip()
        msg = bot.send_message(message.chat.id, "📚 **विषय का नाम लिखें** (उदा: GK & GS):")
        bot.register_next_step_handler(msg, lambda m: step_test_name(m, test_id, exam_name))

    def step_test_name(message, test_id, exam_name):
        subject_name = message.text.strip()
        msg = bot.send_message(message.chat.id, "🏷 **टेस्ट का नाम लिखें** (उदा: Test - 01):")
        bot.register_next_step_handler(msg, lambda m: step_cutoff(m, test_id, exam_name, subject_name))

    def step_cutoff(message, test_id, exam_name, subject_name):
        test_name = message.text.strip()
        msg = bot.send_message(message.chat.id, "🚧 **इस टेस्ट की कट-ऑफ (Cutoff) कितने अंक रखें?** (उदा: 35):")
        bot.register_next_step_handler(msg, lambda m: step_json_upload(m, test_id, exam_name, subject_name, test_name))

    def step_json_upload(message, test_id, exam_name, subject_name, test_name):
        try:
            cutoff = float(message.text.strip())
            msg = bot.send_message(message.chat.id, "📂 **शानदार! अब प्रश्नों वाली `.json` फाइल अपलोड करें:**")
            bot.register_next_step_handler(msg, lambda m: process_json_file(m, test_id, exam_name, subject_name, test_name, cutoff))
        except ValueError:
            bot.send_message(message.chat.id, "❌ कट-ऑफ सिर्फ अंकों (Numbers) में होनी चाहिए। प्रक्रिया रद्द हो गई। दोबारा /addtest टाइप करें।")

    def process_json_file(message, test_id, exam_name, subject_name, test_name, cutoff):
        if message.document and message.document.file_name.endswith('.json'):
            try:
                file_info = bot.get_file(message.document.file_id)
                downloaded_file = bot.download_file(file_info.file_path)
                questions_data = json.loads(downloaded_file)

                # डेटाबेस में सेव करना (शुरुआत में is_public = False रहेगा)
                database.save_test(
                    test_id=test_id, exam_name=exam_name, subject_name=subject_name,
                    test_name=test_name, pos_mark=config.DEFAULT_POSITIVE_MARK,
                    neg_mark=config.DEFAULT_NEGATIVE_MARK, cutoff=cutoff,
                    questions_data=questions_data
                )

                # प्रीव्यू और पब्लिक बटन
                markup = InlineKeyboardMarkup()
                preview_url = f"{config.WEBAPP_BASE_URL}{test_id}"
                markup.add(InlineKeyboardButton("👁️ टेस्ट प्रीव्यू करें (Preview)", url=preview_url))
                markup.add(InlineKeyboardButton("📢 पब्लिक कर दें (Publish)", callback_data=f"publish_{test_id}"))

                bot.send_message(
                    message.chat.id, 
                    f"✅ **टेस्ट सफलतापूर्वक डेटाबेस में सेव हो गया है!**\n\n"
                    f"कुल प्रश्न: {len(questions_data)}\n"
                    f"कट-ऑफ: {cutoff}\n\n"
                    f"कृपया पब्लिक करने से पहले प्रीव्यू बटन पर क्लिक करके टेस्ट चेक कर लें।", 
                    reply_markup=markup
                )
            except Exception as e:
                bot.send_message(message.chat.id, f"❌ JSON फाइल पढ़ने में त्रुटि: {e}")
        else:
            bot.send_message(message.chat.id, "❌ कृपया एक वैध `.json` फाइल भेजें।")

    # टेस्ट पब्लिक करने का बटन क्लिक
    @bot.callback_query_handler(func=lambda call: call.data.startswith("publish_"))
    def publish_test(call):
        if not is_admin(call.from_user.id): return
        test_id = call.data.split("_")[1]
        database.make_test_public(test_id)
        
        bot.edit_message_text("✅ **टेस्ट सफलतापूर्वक पब्लिक (लाइव) कर दिया गया है!**", call.message.chat.id, call.message.message_id)
        
        # चैनल में नोटिफिकेशन भेजना
        bot.send_message(
            config.PUBLIC_CHANNEL_ID, 
            f"🚀 **नया मॉक टेस्ट उपलब्ध है!**\n\n🎯 अभी बॉट में जाएं और अपना टेस्ट दें।"
        )
