# WhatsApp Integration Guide - On Call Driver

## Overview

This document provides complete instructions for integrating WhatsApp messaging into your Django car e-marketing platform. Customers will receive real SMS notifications via WhatsApp when they:

- Complete a booking
- Schedule a visit
- Make a payment
- Send inquiries

---

## 📋 Prerequisites

### 1. **Meta Business Account Setup**

- Go to [Meta Business Suite](https://business.facebook.com)
- Create a Business Account or use existing one
- Add WhatsApp Business Account

### 2. **Get Your API Credentials**

You need three things from Meta Business Manager:

#### a) **Phone Number ID**

- Go to: **Business Settings → Apps & Assets → Apps → Your App**
- Select: **WhatsApp → API Setup**
- Copy: **Phone Number ID**
- Example: `120365123456789`

#### b) **Access Token**

- Go to: **Business Settings → Apps & Assets → System Users**
- Create new System User (if needed)
- Assign Admin role with WhatsApp permissions
- Generate Token under "User Token"
- Keep this **SECURE** - treat like password!
- Example: `EAAHxxx...` (very long string)

#### c) **Webhook Verify Token** (you create this)

- Create a random secure string for verification
- Example: `my_super_secure_token_123`

---

## ⚙️ Configuration Steps

### Step 1: Update Django Settings

Update `E_marketing/settings.py`:

```python
# ================ WHATSAPP INTEGRATION SETTINGS ===============

WHATSAPP_API_VERSION = 'v22.0'
WHATSAPP_PHONE_NUMBER_ID = 'YOUR_PHONE_NUMBER_ID'  # From step 2a
WHATSAPP_ACCESS_TOKEN = 'YOUR_ACCESS_TOKEN'  # From step 2b
WHATSAPP_VERIFY_TOKEN = 'your_secure_verify_token'  # From step 2c
COMPANY_PHONE_NUMBER = '0791273368'  # SMS sender number
```

### Step 2: Run Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

This creates the `WhatsAppMessage` table to track all messages.

### Step 3: Set Up Webhook in Meta Business Manager

1. Go to **Business Settings → Apps & Assets → Apps → Your App**
2. Select: **WhatsApp → Configuration**
3. Under **Webhook**, click **Add Webhook**
4. Fill in:
   - **Callback URL**: `https://your-domain.com/whatsapp/webhook/`
   - **Verify Token**: Use the token from Step 1
   - **Webhook Fields**: Select `messages` and `message_status`
5. Click **Verify and Save**

---

## 💻 Code Integration

### Option 1: Send Booking Confirmation (Automatic)

When a customer completes booking, hook into your booking view:

**File: `homepage/views.py`**

```python
from homepage.whatsapp_service import send_booking_notification

def book_car(request, pk):
    # ... existing booking logic ...

    booking = Booking.objects.create(
        car=car,
        customer=request.user,
        payment_type=payment_type,
        total_price=car.price,
        status='confirmed'
    )

    # ✅ Send WhatsApp notification
    send_booking_notification(booking)

    return redirect('homepage:booking_detail', pk=booking.id)
```

### Option 2: Send Visit Schedule Reminder

When customer schedules a visit:

**File: `homepage/views.py`**

```python
from homepage.whatsapp_service import send_visit_notification

def schedule_visit(request, pk):
    car = get_object_or_404(Car, pk=pk)

    visit = VisitSchedule.objects.create(
        car=car,
        customer=request.user,
        visit_date=request.POST['visit_date'],
        visit_time=request.POST['visit_time'],
        location=request.POST['location'],
        status='pending'
    )

    # ✅ Send WhatsApp reminder
    send_visit_notification(visit)

    return JsonResponse({'success': True})
```

### Option 3: Send Payment Confirmation

When payment is processed:

**File: `payment/views.py`**

```python
from homepage.whatsapp_service import send_payment_notification

def process_payment(request):
    # ... payment processing logic ...

    payment = Payment.objects.create(
        booking=booking,
        customer=request.user,
        amount=amount,
        payment_method='mtn_momo',
        status='success'
    )

    # ✅ Send WhatsApp confirmation
    send_payment_notification(payment)

    return redirect('payment:success')
```

### Option 4: Send Custom Message

For special offers, announcements, or manual messages:

```python
from homepage.whatsapp_service import whatsapp_service

# Send custom message to a customer
user_phone = request.user.phone  # Must be in format: +250XXXXXXXXX

message = """🎉 Special Offer This Week! 🎉

Get 10% OFF on all vehicles in stock!
Valid until Sunday midnight.

Browse our collection: https://yoursite.com/cars

Reply YES to get more details!"""

whatsapp_service.send_text_reply(user_phone, message)
```

---

## 📧 Message Templates

### Booking Confirmation

```
🎉 *BOOKING CONFIRMATION* 🎉

Thank you for booking with On Call Driver!

📋 *Booking Details:*
🚗 Car: 2023 Toyota Corolla
📅 Date: 15-05-2026
⏰ Time: 14:30
💰 Price: 25,000,000 RWF

📞 Questions? Contact us at 0791273368

Thank you for choosing On Call Driver! ✨
```

### Visit Reminder

```
📅 *VISIT REMINDER* 📅

You have a scheduled visit coming up!

🚗 Car: 2023 Toyota Corolla
📅 Date: 15-05-2026
⏰ Time: 14:30
📍 Location: Our Showroom

Please arrive 5 minutes early.
If you need to reschedule, contact us at 0791273368

See you soon! 🚗✨
```

### Payment Confirmation

```
✅ *PAYMENT CONFIRMATION* ✅

Your payment has been received!

💰 Amount: 12,500,000 RWF
🚗 Vehicle: 2023 Toyota Corolla
🆔 Transaction ID: PAY-2026-0001
💳 Method: MTN Mobile Money

Thank you for your trust in On Call Driver!

For any inquiries, reach out to 0791273368
```

---

## 🔄 Receiving Customer Messages

### Incoming Message Handler

When customers send messages to your WhatsApp number, they're automatically processed:

**File: `homepage/whatsapp_webhook.py`** - Function `_handle_customer_inquiry()`

Current auto-replies handle:

- `booking` / `book` → Booking instructions
- `visit` / `schedule` → Visit scheduling info
- `payment` / `price` → Payment methods
- `support` / `help` → Support hours

You can customize these in the webhook handler!

### View Messages in Admin

1. Go to Django Admin: `/admin/`
2. Navigate to: **WhatsApp Messages**
3. Filter by:
   - Message Type
   - Status (sent, delivered, read, failed)
   - Phone Number
   - Date Range

---

## 🚀 Deployment Checklist

- [ ] Get Phone Number ID from Meta
- [ ] Get Access Token from Meta
- [ ] Create Webhook Verify Token
- [ ] Update `settings.py` with credentials
- [ ] Run migrations: `python manage.py migrate`
- [ ] Add webhook URL in Meta Business Manager
- [ ] Test webhook verification (Meta will confirm ✓)
- [ ] Test sending message from views
- [ ] Verify messages appear in WhatsApp
- [ ] Check message logs in Django Admin
- [ ] Set up logging (optional but recommended)

---

## 🧪 Testing

### Test 1: Send Manual Message

```bash
python manage.py shell
```

```python
from homepage.whatsapp_service import whatsapp_service

# Test sending message
whatsapp_service.send_text_reply('+250791273368', 'Test message from Django!')

# Check database
from homepage.models import WhatsAppMessage
messages = WhatsAppMessage.objects.all()
print(messages)
```

### Test 2: Verify Webhook

```bash
# Make a GET request to webhook with verify token
curl -i -X GET "http://localhost:8000/whatsapp/webhook/?hub.verify_token=your_secure_verify_token&hub.challenge=test_challenge"

# Should return the challenge value (HTTP 200)
```

### Test 3: Simulate Incoming Message

```bash
curl -X POST http://localhost:8000/whatsapp/webhook/ \
  -H 'Content-Type: application/json' \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "250791273368",
            "type": "text",
            "text": {"body": "Hi! I want to book a car"},
            "id": "wamid.xxx",
            "timestamp": "1234567890"
          }]
        }
      }]
    }]
  }'
```

---

## 🔐 Security Best Practices

1. **Environment Variables** (Recommended)

```python
import os
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')
WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN')
```

2. **Restrict Webhook to Meta IP Range**

```python
# In settings.py add middleware to verify Meta's IP
# See: https://developers.facebook.com/docs/whatsapp/webhooks/verify-requests
```

3. **Token Rotation**

- Rotate access tokens every 90 days
- Keep backup tokens ready
- Monitor token usage

4. **HTTPS Only**

- Always use HTTPS for webhook URLs
- Never use HTTP in production

---

## 📊 Monitoring WhatsApp Messages

### View Recent Messages

```python
from homepage.models import WhatsAppMessage
from datetime import timedelta
from django.utils import timezone

# Get messages from last 24 hours
recent = WhatsAppMessage.objects.filter(
    created_at__gte=timezone.now() - timedelta(days=1)
)

# Count by status
sent = recent.filter(status='sent').count()
delivered = recent.filter(status='delivered').count()
failed = recent.filter(status='failed').count()

print(f"Sent: {sent}, Delivered: {delivered}, Failed: {failed}")
```

### Check Failures

```python
# Find failed messages
failed_messages = WhatsAppMessage.objects.filter(status='failed')

for msg in failed_messages:
    print(f"Failed: {msg.phone_number} - {msg.content[:50]}")
    print(f"Reason: {msg.metadata.get('error', 'Unknown')}")
```

---

## ❌ Troubleshooting

### Issue: "Invalid Access Token"

**Solution:**

- Go to Meta Business Manager
- Generate new System User token
- Update `settings.py`

### Issue: "Phone Number ID not found"

**Solution:**

- Verify Phone Number ID from Meta
- Make sure it's your WhatsApp Business phone
- NOT your personal phone number!

### Issue: "Webhook not receiving messages"

**Solution:**

1. Verify webhook URL is publicly accessible
2. Check HTTPS is working
3. Verify token in Meta matches `WHATSAPP_VERIFY_TOKEN`
4. Check Django logs for errors
5. Test webhook manually with curl

### Issue: "Phone format invalid"

**Solution:**

- User phone must be in format: `+250XXXXXXXXX`
- NOT: `0791273368` (local format)
- Always include country code +250

### Issue: "Message not formatted correctly"

**Solution:**

- Check message doesn't exceed 4096 characters
- Verify special characters are supported
- Check message doesn't contain forbidden content

---

## 📞 Support & Documentation

- **WhatsApp Business API Docs:** https://developers.facebook.com/docs/whatsapp/
- **Meta Graph API:** https://developers.facebook.com/docs/graph-api/
- **Troubleshooting Guide:** https://developers.facebook.com/docs/whatsapp/support/

---

## 📝 File Structure

Files created/modified for WhatsApp integration:

```
E_marketing/
├── E_marketing/
│   ├── settings.py  ← Add WhatsApp config
│   └── urls.py
├── homepage/
│   ├── models.py  ← Add WhatsAppMessage model
│   ├── admin.py  ← Register WhatsApp admin
│   ├── urls.py  ← Add webhook URL
│   ├── views.py  ← Hook into booking/payment views
│   ├── whatsapp_service.py  ← WhatsApp API client (CREATED)
│   ├── whatsapp_webhook.py  ← Webhook handler (CREATED)
│   ├── whatsapp_admin.py  ← Admin interface (CREATED)
│   └── templates/
│       └── ... existing templates ...
└── media/
    └── ... (logos in messages)
```

---

## 🎯 Next Steps

1. ✅ Complete setup using this guide
2. ✅ Test with single message
3. ✅ Integrate into booking view
4. ✅ Integrate into visit scheduling
5. ✅ Integrate into payment processing
6. ✅ Monitor messages in admin
7. ✅ Customize message templates as needed
8. ✅ Set up logging and alerting (optional)

---

**Last Updated:** May 17, 2026  
**Version:** 1.0
