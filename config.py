# config.py

# 1. बॉट और डेटाबेस टोकन
BOT_TOKEN = "यहाँ_अपना_बॉट_टोकन_डालें"
MONGO_URI = "यहाँ_अपना_MongoDB_URI_डालें"

# 2. चैनल और एडमिन आईडी
ADMIN_IDS = [123456789, 987654321]  # यहाँ अपनी और अपने साथियों की टेलीग्राम ID डालें
PUBLIC_CHANNEL_ID = "-1001234567890"  # पब्लिक अपडेट चैनल की ID
COMPLAINT_CHANNEL_ID = "-1000987654321"  # शिकायतों वाले प्राइवेट चैनल की ID

# 3. गिटहब पेजेज़ (वेब ऐप) का लिंक
WEBAPP_BASE_URL = "https://your-username.github.io/mock-test/?test_id="

# 4. सिस्टम सेटिंग्स
DEFAULT_POSITIVE_MARK = 2.0
DEFAULT_NEGATIVE_MARK = 0.25
MAINTENANCE_MODE = False
