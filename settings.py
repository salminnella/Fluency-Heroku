ACCOUNT_SID = "ACdd8953205cab360450e486f1a3a52fe9"
AUTH_TOKEN = "4eea9c2481e3f5f8b630a7d30942a1b6"
CALLER_ID = "+1 855-999-9083"
APP_SID = "AP2e55b89356bc0bb298806f1289e827cc"

import os
ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', None)
AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', None)
CALLER_ID = os.environ.get('TWILIO_CALLER_ID', None)
APP_SID = os.environ.get('TWILIO_APP_SID', None)
