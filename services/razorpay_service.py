import hashlib
import hmac
import json
import os
from typing import Any, Dict, Optional

import razorpay


RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')


def get_razorpay_client():
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise RuntimeError('Razorpay credentials are not configured.')
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_payment_order(amount: float, receipt: str, currency: str = 'INR', notes: Optional[Dict[str, str]] = None):
    client = get_razorpay_client()
    payload = {
        'amount': int(float(amount) * 100),
        'currency': currency,
        'receipt': receipt,
        'notes': notes or {},
    }
    return client.order.create(data=payload)


def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str):
    if not RAZORPAY_KEY_SECRET:
        raise ValueError('Razorpay secret is not configured.')

    payload = f'{razorpay_order_id}|{razorpay_payment_id}'.encode()
    secret = RAZORPAY_KEY_SECRET.encode()
    generated_signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated_signature, razorpay_signature)


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    if not RAZORPAY_KEY_SECRET:
        return False
    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
