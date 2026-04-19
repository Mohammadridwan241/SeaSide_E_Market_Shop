from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse


class SSLCommerzError(Exception):
    pass


def _get_base_urls():
    if settings.SSLCOMMERZ_SANDBOX:
        return {
            'api': 'https://sandbox.sslcommerz.com/gwprocess/v4/api.php',
            'validator': 'https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php',
        }
    return {
        'api': 'https://securepay.sslcommerz.com/gwprocess/v4/api.php',
        'validator': 'https://securepay.sslcommerz.com/validator/api/validationserverAPI.php',
    }


def _get_session():
    session = requests.Session()
    session.trust_env = False
    return session


def _ensure_credentials():
    missing = []
    if not settings.SSLCOMMERZ_STORE_ID:
        missing.append('SSLCOMMERZ_STORE_ID')
    if not settings.SSLCOMMERZ_STORE_PASSWORD:
        missing.append('SSLCOMMERZ_STORE_PASSWORD')

    if missing:
        raise SSLCommerzError(
            'SSLCommerz credentials are not configured. Missing: ' + ', '.join(missing)
        )


def create_payment_session(request, order):
    _ensure_credentials()
    urls = _get_base_urls()
    session = _get_session()

    payload = {
        'store_id': settings.SSLCOMMERZ_STORE_ID,
        'store_passwd': settings.SSLCOMMERZ_STORE_PASSWORD,
        'total_amount': f'{order.get_total_cost():.2f}',
        'currency': 'BDT',
        'tran_id': order.transaction_id,
        'success_url': request.build_absolute_uri(reverse('sslcommerz_success')),
        'fail_url': request.build_absolute_uri(reverse('sslcommerz_fail')),
        'cancel_url': request.build_absolute_uri(reverse('sslcommerz_cancel')),
        'ipn_url': request.build_absolute_uri(reverse('sslcommerz_ipn')),
        'shipping_method': 'Courier',
        'product_name': f'Order #{order.id}',
        'product_category': 'Ecommerce',
        'product_profile': 'general',
        'cus_name': f'{order.first_name} {order.last_name}'.strip(),
        'cus_email': order.email,
        'cus_add1': order.address,
        'cus_city': order.city,
        'cus_postcode': order.postal_code,
        'cus_country': 'Bangladesh',
        'cus_phone': order.phone or 'N/A',
        'ship_name': f'{order.first_name} {order.last_name}'.strip(),
        'ship_add1': order.address,
        'ship_city': order.city,
        'ship_postcode': order.postal_code,
        'ship_country': 'Bangladesh',
        'num_of_item': str(order.order_items.count()),
        'value_a': str(order.id),
        'value_b': order.payment_method,
        'value_c': str(order.user_id),
    }

    try:
        response = session.post(urls['api'], data=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise SSLCommerzError('Could not create SSLCommerz payment session.') from exc

    if data.get('status') != 'SUCCESS' or not data.get('GatewayPageURL'):
        raise SSLCommerzError(data.get('failedreason') or 'SSLCommerz session creation failed.')

    return data


def validate_payment(val_id, amount, currency='BDT'):
    _ensure_credentials()
    urls = _get_base_urls()
    session = _get_session()

    params = {
        'val_id': val_id,
        'store_id': settings.SSLCOMMERZ_STORE_ID,
        'store_passwd': settings.SSLCOMMERZ_STORE_PASSWORD,
        'v': 1,
        'format': 'json',
    }

    try:
        response = session.get(urls['validator'], params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise SSLCommerzError('Could not validate SSLCommerz payment.') from exc

    try:
        gateway_amount = Decimal(str(data.get('amount', '0')))
        expected_amount = Decimal(str(amount))
    except (InvalidOperation, TypeError) as exc:
        raise SSLCommerzError('SSLCommerz returned an invalid amount.') from exc

    if data.get('status') not in {'VALID', 'VALIDATED'}:
        raise SSLCommerzError('Payment validation failed.')
    if gateway_amount != expected_amount:
        raise SSLCommerzError('Payment amount mismatch.')
    if data.get('currency') != currency:
        raise SSLCommerzError('Payment currency mismatch.')

    return data


def send_order_confirmation_email(order):
    subject = f'Order Confirmation - Order #{order.id}'
    message = render_to_string('SeaSide_Shop/email/order_confirmation.html', {'order': order})
    to = order.email
    send_email = EmailMultiAlternatives(subject, '', to=[to])
    send_email.attach_alternative(message, 'text/html')
    send_email.send()
