"""
EXAMPLE: How to Integrate WhatsApp into Your Views
Copy and adapt these examples to your actual views

This file shows example code that you should add to:
- homepage/views.py (for bookings and visits)
- payment/views.py (for payments)
"""

# ============================================================================
# EXAMPLE 1: Send WhatsApp on Booking Confirmation
# Add this to: homepage/views.py
# ============================================================================

from django.shortcuts import redirect
from django.contrib import messages
from homepage.whatsapp_service import send_booking_notification
from homepage.models import Booking, Car

def book_car_example(request, pk):
    """
    Example view that creates a booking and sends WhatsApp notification
    """
    if request.method == 'POST':
        car = Car.objects.get(pk=pk)
        
        # Create booking
        booking = Booking.objects.create(
            car=car,
            customer=request.user,
            payment_type='full',  # or 'half'
            total_price=car.price,
            status='confirmed'
        )
        
        # ✅ SEND WHATSAPP NOTIFICATION
        try:
            success = send_booking_notification(booking)
            if success:
                messages.success(request, 'Booking confirmed! WhatsApp notification sent.')
            else:
                messages.warning(request, 'Booking confirmed, but WhatsApp notification failed.')
        except Exception as e:
            print(f"WhatsApp error: {e}")
            messages.warning(request, 'Booking confirmed, but WhatsApp notification failed.')
        
        return redirect('homepage:booking_detail', pk=booking.id)


# ============================================================================
# EXAMPLE 2: Send WhatsApp on Visit Schedule
# Add this to: homepage/views.py
# ============================================================================

from datetime import datetime
from homepage.whatsapp_service import send_visit_notification
from homepage.models import VisitSchedule

def schedule_visit_example(request, pk):
    """
    Example view that schedules a visit and sends WhatsApp reminder
    """
    if request.method == 'POST':
        car = Car.objects.get(pk=pk)
        
        # Create visit schedule
        visit = VisitSchedule.objects.create(
            car=car,
            customer=request.user,
            visit_date=request.POST['visit_date'],  # YYYY-MM-DD format
            visit_time=request.POST['visit_time'],  # HH:MM format
            location=request.POST.get('location', 'Our Showroom'),
            district=request.POST.get('district', 'Kigali'),
            status='pending'
        )
        
        # ✅ SEND WHATSAPP REMINDER
        try:
            success = send_visit_notification(visit)
            if success:
                print(f"Visit reminder sent to {request.user.phone}")
            else:
                print(f"Failed to send visit reminder to {request.user.phone}")
        except Exception as e:
            print(f"WhatsApp error: {e}")
        
        return redirect('homepage:schedule_detail', pk=visit.id)


# ============================================================================
# EXAMPLE 3: Send WhatsApp on Payment Success
# Add this to: payment/views.py
# ============================================================================

from homepage.whatsapp_service import send_payment_notification
from homepage.models import Payment, Booking

def payment_success_example(request):
    """
    Example view after successful payment processing
    """
    booking_id = request.GET.get('booking_id')
    booking = Booking.objects.get(id=booking_id)
    
    # Create payment record
    payment = Payment.objects.create(
        booking=booking,
        customer=request.user,
        amount=booking.total_price,
        payment_method='mtn_momo',  # or airtel_money, bank_transfer, cash
        purpose='full_payment',
        transaction_id='TXN123456',  # from payment gateway
        status='success'
    )
    
    # ✅ SEND WHATSAPP CONFIRMATION
    try:
        success = send_payment_notification(payment)
        if success:
            print("Payment confirmation sent via WhatsApp")
    except Exception as e:
        print(f"WhatsApp error: {e}")
    
    return redirect('payment:success', payment_id=payment.id)


# ============================================================================
# EXAMPLE 4: Send Custom WhatsApp Message
# Add this to: homepage/views.py
# ============================================================================

from homepage.whatsapp_service import whatsapp_service

def send_promo_offer(request):
    """
    Admin function to send promotional offers to customers
    
    Usage: Call this from a scheduled task or button
    """
    from homepage.models import CustomUser
    
    if not request.user.is_admin:
        return "Only admins can send promotions"
    
    # Get all customers
    customers = CustomUser.objects.filter(role='customer', is_active=True)
    
    sent_count = 0
    failed_count = 0
    
    for customer in customers:
        message = f"""🎉 *SPECIAL OFFER THIS WEEK!* 🎉

Get EXCLUSIVE DEALS on these amazing vehicles:

✅ 2023 Toyota Corolla - 25,000,000 RWF
✅ 2022 Honda CR-V - 28,000,000 RWF
✅ 2023 Nissan Sentra - 22,000,000 RWF

*LIMITED TIME OFFER - Valid until Sunday!*

👉 Browse now: https://your-site.com/cars

📞 Questions? WhatsApp us!"""
        
        try:
            success = whatsapp_service.send_text_reply(
                phone_number=customer.phone,
                reply_message=message
            )
            if success:
                sent_count += 1
            else:
                failed_count += 1
        except Exception as e:
            print(f"Error sending to {customer.phone}: {e}")
            failed_count += 1
    
    return f"Sent: {sent_count}, Failed: {failed_count}"


# ============================================================================
# EXAMPLE 5: Handle Incoming Customer Questions (Auto-reply)
# This is already implemented in whatsapp_webhook.py
# But here's how to customize it
# ============================================================================

def customize_autoreply():
    """
    Edit file: homepage/whatsapp_webhook.py
    Function: _handle_customer_inquiry()
    
    Add your custom logic here:
    """
    # Example customization:
    
    message_lower = "i want to check cars near kigali"
    
    if 'kigali' in message_lower or 'location' in message_lower:
        reply = """Perfect! We have many cars available in Kigali.

Current inventory in Kigali:
• 15 Sedans
• 8 SUVs
• 5 Vans

Filter by location on our site: https://your-site.com/cars?location=kigali

Or let me know what you're looking for! 🚗"""
        
        # Send reply (implement in your webhook handler)
        # whatsapp_service.send_text_reply(phone_number, reply)


# ============================================================================
# EXAMPLE 6: Bulk Send Messages to Inactive Users
# Add this to: homepage/views.py or management command
# ============================================================================

from datetime import timedelta
from django.utils import timezone

def send_reactivation_offers(request):
    """
    Send WhatsApp offers to customers who haven't visited in 30 days
    """
    from homepage.models import CustomUser, CarView
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Find inactive customers
    inactive_users = CustomUser.objects.filter(
        role='customer',
        is_active=True
    ).exclude(
        view_logs__viewed_at__gt=thirty_days_ago
    ).distinct()
    
    for user in inactive_users:
        message = f"""Hi {user.full_name}! 👋

We noticed you haven't visited us in a while.

We have NEW vehicles in stock with even better prices! 🚗✨

Come check out our latest:
https://your-site.com/cars

Use code: WELCOME10 for 10% OFF scheduling fees! 

See you soon! 🚗"""
        
        try:
            whatsapp_service.send_text_reply(user.phone, message)
        except Exception as e:
            print(f"Error sending to {user.phone}: {e}")


# ============================================================================
# EXAMPLE 7: Management Command (Django scheduled task)
# Save as: homepage/management/commands/send_visit_reminders.py
# Run: python manage.py send_visit_reminders
# ============================================================================

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from homepage.models import VisitSchedule
from homepage.whatsapp_service import whatsapp_service

class Command(BaseCommand):
    help = 'Send WhatsApp reminders for visits scheduled tomorrow'

    def handle(self, *args, **options):
        tomorrow = timezone.now() + timedelta(days=1)
        tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0)
        tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59)
        
        visits = VisitSchedule.objects.filter(
            visit_date__gte=tomorrow_start.date(),
            visit_date__lte=tomorrow_end.date(),
            status='confirmed'
        )
        
        sent = 0
        for visit in visits:
            message = f"""📅 VISIT REMINDER - TOMORROW

Don't forget about your scheduled car visit!

🚗 Car: {visit.car.brand.name} {visit.car.model}
⏰ Time: {visit.visit_time.strftime('%H:%M')}
📍 Location: {visit.location}

See you tomorrow! 🚗✨"""
            
            try:
                whatsapp_service.send_text_reply(visit.customer.phone, message)
                sent += 1
            except Exception as e:
                print(f"Error: {e}")
        
        self.stdout.write(self.style.SUCCESS(f'Sent {sent} reminders'))


# ============================================================================
# EXAMPLE 8: Configure in Cron/Celery (Optional)
# For automated scheduled messages
# ============================================================================

"""
Option A: Using Celery (recommended for production)
--------------------------------------------------

1. Install: pip install celery redis

2. Create file: E_marketing/celery.py
   
   import os
   from celery import Celery
   
   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'E_marketing.settings')
   
   app = Celery('E_marketing')
   app.config_from_object('django.conf:settings', namespace='CELERY')
   app.autodiscover_tasks()

3. Create file: homepage/tasks.py
   
   from celery import shared_task
   from datetime import timedelta
   from django.utils import timezone
   from homepage.models import VisitSchedule
   from homepage.whatsapp_service import send_visit_notification
   
   @shared_task
   def send_tomorrow_visit_reminders():
       tomorrow = timezone.now() + timedelta(days=1)
       visits = VisitSchedule.objects.filter(
           visit_date=tomorrow.date(),
           status='confirmed'
       )
       for visit in visits:
           send_visit_notification(visit)

4. In settings.py add:
   
   CELERY_BEAT_SCHEDULE = {
       'send-visit-reminders': {
           'task': 'homepage.tasks.send_tomorrow_visit_reminders',
           'schedule': crontab(hour=10, minute=0),  # Daily at 10 AM
       },
   }

5. Run:
   celery -A E_marketing worker -l info
   celery -A E_marketing beat -l info


Option B: Using Django-APScheduler
-----------------------------------

1. Install: pip install django-apscheduler

2. See: https://github.com/jcass77/django-apscheduler
"""


# ============================================================================
# TESTING: How to test WhatsApp integration
# ============================================================================

def test_whatsapp_integration():
    """
    Run this in Django shell to test:
    python manage.py shell
    """
    
    # Test 1: Check if credentials are configured
    from django.conf import settings
    
    print("WhatsApp Configuration:")
    print(f"Phone Number ID: {settings.WHATSAPP_PHONE_NUMBER_ID}")
    print(f"Access Token: {settings.WHATSAPP_ACCESS_TOKEN[:20]}...")
    print(f"Verify Token: {settings.WHATSAPP_VERIFY_TOKEN}")
    
    # Test 2: Send test message
    from homepage.whatsapp_service import whatsapp_service
    
    test_message = "Test message from Django WhatsApp integration!"
    result = whatsapp_service.send_text_reply('+250791273368', test_message)
    print(f"Message sent: {result}")
    
    # Test 3: Check message logs
    from homepage.models import WhatsAppMessage
    
    messages = WhatsAppMessage.objects.all().order_by('-created_at')[:10]
    for msg in messages:
        print(f"{msg.created_at} - {msg.phone_number} - {msg.status}: {msg.content[:30]}...")


if __name__ == '__main__':
    print("""
    This file contains examples for integrating WhatsApp into your views.
    
    Copy relevant sections to your actual view files:
    - homepage/views.py (bookings, visits)
    - payment/views.py (payments)
    
    Then adapt the code to match your existing structure.
    """)
