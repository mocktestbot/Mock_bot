# config.py
import os

# 1. बॉट और डेटाबेस टोकन (Environment Variables से)
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# 2. चैनल और एडमिन आईडी
# एडमिन आईडी कोमा (,) से अलग करके डालेंगे, और यहाँ यह उसे लिस्ट में बदल देगा
admin_ids_string = os.getenv("ADMIN_IDS", "123456789") 
ADMIN_IDS = [int(admin_id.strip()) for admin_id in admin_ids_string.split(",")]

PUBLIC_CHANNEL_ID = os.getenv("PUBLIC_CHANNEL_ID")
COMPLAINT_CHANNEL_ID = os.getenv("COMPLAINT_CHANNEL_ID")

# 3. गिटहब पेजेज़ (वेब ऐप) का लिंक
WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL")

# 4. सिस्टम सेटिंग्स (ये सीक्रेट नहीं हैं, इन्हें यहीं रहने दें)
DEFAULT_POSITIVE_MARK = 2.0
DEFAULT_NEGATIVE_MARK = 0.25
MAINTENANCE_MODE = False
