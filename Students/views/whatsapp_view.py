import os
import re
from typing import Tuple, Dict, Any

import requests
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

"""
Automatic WhatsApp sending using Meta's official WhatsApp Cloud API.

Environment variables required:
- WHATSAPP_PHONE_NUMBER_ID: Your WhatsApp Business phone number ID
- WHATSAPP_ACCESS_TOKEN: A valid access token with permissions to send messages

Docs:
- https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages

Usage in Python (e.g., in approve_leave view):
    from Students.views.whatsapp_view import send_whatsapp_message
    ok, err, details = send_whatsapp_message("+254712345678", "Leave approved ...")
    # ok: True/False, err: message on failure, details: provider response

This module does not use third-party providers; it calls the Cloud API directly.
"""


API_BASE = os.environ.get('WHATSAPP_API_BASE', 'https://graph.facebook.com/v20.0')


def _normalize_phone_e164_digits(phone: str) -> Tuple[bool, str, str]:
    """Normalize to digits-only international format (E.164 without '+').

    Returns (ok, error, digits_only_phone).
    """
    if not phone:
        return False, 'Phone is required', ''

    digits = re.sub(r'\D+', '', phone)
    if len(digits) < 8 or len(digits) > 15:
        return False, 'Phone must be 8-15 digits in international format', ''
    return True, '', digits


def send_whatsapp_message(phone: str, message: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Send a WhatsApp message via the Cloud API.

    Params:
        phone: Destination number in international form (e.g., +2547XXXXXXX). Other punctuation is allowed; it will be normalized.
        message: Text body to send.

    Returns:
        (ok, error_message, details_dict)
    """
    if not message:
        return False, 'Message is required', {}

    ok, err, to_number = _normalize_phone_e164_digits(phone)
    if not ok:
        return False, err, {}

    phone_number_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID')
    access_token = os.environ.get('WHATSAPP_ACCESS_TOKEN')

    if not phone_number_id or not access_token:
        return False, 'WhatsApp Cloud API not configured (missing WHATSAPP_PHONE_NUMBER_ID or WHATSAPP_ACCESS_TOKEN)', {}

    url = f"{API_BASE}/{phone_number_id}/messages"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    payload = {
        'messaging_product': 'whatsapp',
        'to': to_number,
        'type': 'text',
        'text': {'body': message},
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        # Success statuses are 200 or 201 with a JSON containing messages array
        if resp.status_code in (200, 201):
            data = resp.json()
            return True, '', {'status_code': resp.status_code, 'response': data}
        else:
            # Try to extract error from Meta format
            try:
                data = resp.json()
                err_msg = data.get('error', {}).get('message') or str(data)
            except Exception:
                err_msg = resp.text
            return False, f'Cloud API error ({resp.status_code}): {err_msg}', {'status_code': resp.status_code}
    except requests.RequestException as e:
        return False, f'HTTP error: {e}', {}


@csrf_exempt
@require_POST
def send_whatsapp_view(request: HttpRequest) -> JsonResponse:
    """HTTP API endpoint to send a WhatsApp message.

    Accepts JSON or form data with: phone, message.
    """
    try:
        if request.content_type and 'application/json' in request.content_type:
            import json
            payload = json.loads(request.body.decode('utf-8'))
        else:
            payload = request.POST
    except Exception:
        payload = {}

    phone = payload.get('phone', '')
    message = payload.get('message', '')

    ok, err, details = send_whatsapp_message(phone, message)
    if not ok:
        return JsonResponse({'success': False, 'error': err, 'details': details}, status=400)

    return JsonResponse({'success': True, 'details': details})
