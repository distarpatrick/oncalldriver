"""
WhatsApp Webhook Handler
Processes incoming messages from customers via WhatsApp
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import WhatsAppMessage
from .whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """
    Handle WhatsApp webhook from Meta's Graph API
    
    GET: Verification request from Meta
    POST: Incoming messages and status updates
    """
    
    # ===== WEBHOOK VERIFICATION (GET) =====
    if request.method == 'GET':
        return _verify_webhook(request)
    
    # ===== INCOMING MESSAGES (POST) =====
    elif request.method == 'POST':
        return _handle_webhook_message(request)


def _verify_webhook(request):
    """
    Verify webhook token with Meta
    This request is sent when you set up the webhook in Meta Business Manager
    """
    verify_token = getattr(settings, 'WHATSAPP_VERIFY_TOKEN', 'your-verify-token-here')
    token = request.GET.get('hub.verify_token', '')
    challenge = request.GET.get('hub.challenge', '')
    
    if token == verify_token:
        logger.info("WhatsApp webhook verified successfully")
        return JsonResponse(int(challenge))
    else:
        logger.warning(f"Invalid webhook verification token: {token}")
        return JsonResponse({'error': 'Invalid token'}, status=403)


def _handle_webhook_message(request):
    """
    Handle incoming WhatsApp messages and delivery status updates
    """
    try:
        data = json.loads(request.body)
        
        # Get the WhatsApp business account event
        entry = data.get('entry', [{}])[0]
        changes = entry.get('changes', [{}])[0]
        message_data = changes.get('value', {})
        
        # Handle incoming messages from customers
        messages = message_data.get('messages', [])
        if messages:
            for msg in messages:
                _process_incoming_message(msg, message_data)
        
        # Handle status updates (delivery, read, etc)
        statuses = message_data.get('statuses', [])
        if statuses:
            for status in statuses:
                _process_status_update(status)
        
        # Always return 200 to acknowledge receipt
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        logger.exception(f"Error processing WhatsApp webhook: {str(e)}")
        # Still return 200 to avoid retry loops
        return JsonResponse({'status': 'error'}, status=200)


def _process_incoming_message(message, message_data):
    """
    Process incoming customer message
    """
    try:
        message_id = message.get('id')
        from_phone = message.get('from')
        timestamp = message.get('timestamp')
        message_type = message.get('type', 'text')
        
        # Extract message content based on type
        if message_type == 'text':
            content = message.get('text', {}).get('body', '')
        elif message_type == 'image':
            content = "[Image received]"
        elif message_type == 'video':
            content = "[Video received]"
        elif message_type == 'document':
            content = "[Document received]"
        elif message_type == 'location':
            content = "[Location received]"
        else:
            content = f"[{message_type.upper()} received]"
        
        # Save to database
        WhatsAppMessage.objects.create(
            phone_number=from_phone,
            message_type='inbound_message',
            status='delivered',
            message_id=message_id,
            content=content,
            metadata={
                'from_phone': from_phone,
                'message_type': message_type,
                'timestamp': timestamp
            }
        )
        
        logger.info(f"Inbound message from {from_phone}: {content[:50]}")
        
        # Trigger auto-reply or process message (optional)
        _handle_customer_inquiry(from_phone, content)
        
    except Exception as e:
        logger.error(f"Error processing incoming message: {str(e)}")


def _process_status_update(status):
    """
    Process message delivery/read status updates
    """
    try:
        message_id = status.get('id')
        status_type = status.get('status')  # sent, delivered, read, failed
        
        # Update message status in database
        try:
            msg = WhatsAppMessage.objects.get(message_id=message_id)
            msg.status = status_type
            msg.save(update_fields=['status'])
            logger.info(f"Message {message_id} status updated to: {status_type}")
        except WhatsAppMessage.DoesNotExist:
            logger.warning(f"Message {message_id} not found in database")
            
    except Exception as e:
        logger.error(f"Error processing status update: {str(e)}")


def _handle_customer_inquiry(phone_number, message_content):
    """
    Process customer inquiries and send appropriate replies
    This is where you can add AI/chatbot logic for auto-responses
    """
    try:
        # Example: Check for common keywords and send relevant replies
        message_lower = message_content.lower()
        
        if 'booking' in message_lower or 'book' in message_lower:
            reply = """Thank you for your interest! 

To complete a booking:
1. Browse cars on our website
2. Select a car and proceed to checkout
3. Choose payment method (MoMo, Bank Transfer, etc)
4. Complete payment
5. Your confirmation will be sent to this number

Need help? Contact us at 0791273368"""
            whatsapp_service.send_text_reply(phone_number, reply)
        
        elif 'visit' in message_lower or 'schedule' in message_lower:
            reply = """Great! To schedule a visit:
1. Find the car you're interested in
2. Click "Schedule Visit"
3. Choose your preferred date & time
4. Pay the scheduling fee (if applicable)
5. We'll confirm your visit

Questions? Chat with us here or call 0791273368"""
            whatsapp_service.send_text_reply(phone_number, reply)
        
        elif 'payment' in message_lower or 'price' in message_lower:
            reply = """Our payment options:
💳 MTN Mobile Money
💳 Airtel Money  
💳 Bank Transfer
💵 Cash (In Person)

Prices shown are all-inclusive. No hidden charges!

Help needed? Call 0791273368"""
            whatsapp_service.send_text_reply(phone_number, reply)
        
        elif 'support' in message_lower or 'help' in message_lower:
            reply = """We're here to help! 

Our support hours:
Mon-Fri: 9:00 AM - 6:00 PM
Sat-Sun: 10:00 AM - 4:00 PM

For urgent matters, call: 0791273368
Or reply to this message with details

Thank you! 🚗"""
            whatsapp_service.send_text_reply(phone_number, reply)
        
        # Log inquiry for support team
        logger.info(f"Customer inquiry from {phone_number}: {message_content[:100]}")
        
    except Exception as e:
        logger.error(f"Error handling customer inquiry: {str(e)}")
