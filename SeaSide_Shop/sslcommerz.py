from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
    
def send_order_confirmation_email(order):
    subject = f'Order Confirmation - Order #{order.id}'
    message = render_to_string('SeaSide_Shop/email/order_confirmation.html', {'order' : order}) # html code ke --> string e convert kore
    to = order.email
    send_email = EmailMultiAlternatives(subject, '', to=[to])
    send_email.attach_alternative(message, 'text/html')
    send_email.send()
    
    
