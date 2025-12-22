# shulebase_core/sms_utils.py (Using Option 1: Email/Username as Partner ID)
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
# ... (rest of the code)

def send_mobitech_sms(recipient_mobile, message_body):
    
    # Use the email/username as the Partner ID for the test
    partner_id = settings.MOBITECH_PARTNER_ID 
    
    payload = {
        'apikey': settings.MOBITECH_API_KEY,
        'partnerID': partner_id, # << Using the email/username here
        'message': message_body,
        'shortcode': settings.MOBITECH_SENDER_ID,
        'mobile': recipient_mobile 
    }

    try:
        response = requests.post(settings.MOBITECH_SMS_ENDPOINT, data=payload)
        # ... (rest of the success/error checking logic)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network or API connection error during SMS send: {e}")
        return False