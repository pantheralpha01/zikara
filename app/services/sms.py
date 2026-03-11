import httpx

TEXTSMS_API_URL = "https://sms.textsms.co.ke/api/services/sendsms"
TEXTSMS_API_KEY = "2621c089f51469047f73b56a40375fcc"
TEXTSMS_PARTNER_ID = 12554
TEXTSMS_SHORTCODE = "TextSMS"


def send_otp_sms(phone: str, code: str) -> bool:
    """Send an OTP via TextSMS. Returns True on success, False on failure."""
    payload = {
        "apikey": TEXTSMS_API_KEY,
        "partnerID": TEXTSMS_PARTNER_ID,
        "message": f"Your Zikara OTP is {code}. Valid for 30 minutes. Do not share this code.",
        "shortcode": TEXTSMS_SHORTCODE,
        "mobile": phone,
    }
    try:
        response = httpx.post(TEXTSMS_API_URL, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception:
        return False
