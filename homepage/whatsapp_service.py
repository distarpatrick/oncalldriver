"""
WhatsApp Integration Service using Facebook Graph API
Handles sending booking confirmations and visit reminders via WhatsApp
"""

import requests
import json
import logging
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from .models import WhatsAppMessage

logger = logging.getLogger(__name__)

class WhatsAppService:
    """Service to handle WhatsApp messaging via Facebook Graph API"""
    
    def __init__(self):
        self.phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
        self.access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')
        self.api_version = getattr(settings, 'WHATSAPP_API_VERSION', 'v22.0')
        self.base_url = f'https://graph.facebook.com/{self.api_version}'
        self.company_phone = getattr(settings, 'COMPANY_PHONE_NUMBER', '0791273368')
    
    def send_booking_confirmation(self, user_phone, booking_data):
        """
        Send booking confirmation via WhatsApp
        
        Args:
            user_phone: Customer's phone number (format: +250XXXXXXXXX)
            booking_data: Dictionary with booking details
                - car_title
                - booking_date
                - booking_time
                - price
                - company_name (optional)
        """
        try:
            # Template name should be pre-approved in Meta Business Manager
            template_name = 'booking_confirmation'
            
            message_body = self._build_booking_message(booking_data)
            
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": user_phone,
                "type": "text",
                "text": {
                    "body": message_body
                }
            }
            
            response = self._send_message(payload)
            
            if response.get('messages'):
                message_id = response['messages'][0]['id']
                self._log_message(
                    phone_number=user_phone,
                    message_type='booking_confirmation',
                    status='sent',
                    message_id=message_id,
                    content=message_body,
                    metadata=booking_data
                )
                logger.info(f"Booking confirmation sent to {user_phone}. Message ID: {message_id}")
                return True
            else:
                error = response.get('error', {})
                logger.error(f"Failed to send booking confirmation: {error}")
                self._log_message(
                    phone_number=user_phone,
                    message_type='booking_confirmation',
                    status='failed',
                    content=message_body,
                    metadata={**booking_data, 'error': str(error)}
                )
                return False
                
        except Exception as e:
            logger.exception(f"Error sending booking confirmation: {str(e)}")
            return False
    
    def send_visit_reminder(self, user_phone, visit_data):
        """
        Send visit schedule reminder via WhatsApp
        
        Args:
            user_phone: Customer's phone number
            visit_data: Dictionary with visit details
                - car_title
                - visit_date
                - visit_time
                - location
        """
        try:
            message_body = self._build_visit_reminder_message(visit_data)
            
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": user_phone,
                "type": "text",
                "text": {
                    "body": message_body
                }
            }
            
            response = self._send_message(payload)
            
            if response.get('messages'):
                message_id = response['messages'][0]['id']
                self._log_message(
                    phone_number=user_phone,
                    message_type='visit_reminder',
                    status='sent',
                    message_id=message_id,
                    content=message_body,
                    metadata=visit_data
                )
                logger.info(f"Visit reminder sent to {user_phone}. Message ID: {message_id}")
                return True
            else:
                error = response.get('error', {})
                logger.error(f"Failed to send visit reminder: {error}")
                self._log_message(
                    phone_number=user_phone,
                    message_type='visit_reminder',
                    status='failed',
                    content=message_body,
                    metadata={**visit_data, 'error': str(error)}
                )
                return False
                
        except Exception as e:
            logger.exception(f"Error sending visit reminder: {str(e)}")
            return False
    
    def send_payment_confirmation(self, user_phone, payment_data):
        """
        Send payment confirmation via WhatsApp
        
        Args:
            user_phone: Customer's phone number
            payment_data: Dictionary with payment details
                - amount
                - car_title
                - transaction_id
                - payment_method
        """
        try:
            message_body = self._build_payment_confirmation_message(payment_data)
            
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": user_phone,
                "type": "text",
                "text": {
                    "body": message_body
                }
            }
            
            response = self._send_message(payload)
            
            if response.get('messages'):
                message_id = response['messages'][0]['id']
                self._log_message(
                    phone_number=user_phone,
                    message_type='payment_confirmation',
                    status='sent',
                    message_id=message_id,
                    content=message_body,
                    metadata=payment_data
                )
                logger.info(f"Payment confirmation sent to {user_phone}. Message ID: {message_id}")
                return True
            else:
                error = response.get('error', {})
                logger.error(f"Failed to send payment confirmation: {error}")
                self._log_message(
                    phone_number=user_phone,
                    message_type='payment_confirmation',
                    status='failed',
                    content=message_body,
                    metadata={**payment_data, 'error': str(error)}
                )
                return False
                
        except Exception as e:
            logger.exception(f"Error sending payment confirmation: {str(e)}")
            return False
    
    def send_text_reply(self, user_phone, reply_message):
        """
        Send a reply to customer's text message
        
        Args:
            user_phone: Customer's phone number
            reply_message: Reply message content
        """
        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": user_phone,
                "type": "text",
                "text": {
                    "body": reply_message
                }
            }
            
            response = self._send_message(payload)
            
            if response.get('messages'):
                message_id = response['messages'][0]['id']
                self._log_message(
                    phone_number=user_phone,
                    message_type='text_reply',
                    status='sent',
                    message_id=message_id,
                    content=reply_message,
                    metadata={'reply': True}
                )
                logger.info(f"Text reply sent to {user_phone}. Message ID: {message_id}")
                return True
            else:
                error = response.get('error', {})
                logger.error(f"Failed to send text reply: {error}")
                return False
                
        except Exception as e:
            logger.exception(f"Error sending text reply: {str(e)}")
            return False
    
    def _send_message(self, payload):
        """
        Send message via WhatsApp API
        
        Args:
            payload: Message payload dict
            
        Returns:
            API response or empty dict on error
        """
        try:
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {str(e)}")
            return {}
    
    def _build_booking_message(self, booking_data):
        """Build formatted booking confirmation message"""
        company_name = booking_data.get('company_name', 'On Call Driver')
        
        message = f"""🎉 *BOOKING CONFIRMATION* 🎉

Thank you for booking with {company_name}!

📋 *Booking Details:*
🚗 Car: {booking_data.get('car_title', 'N/A')}
📅 Date: {booking_data.get('booking_date', 'N/A')}
⏰ Time: {booking_data.get('booking_time', 'N/A')}
💰 Price: {booking_data.get('price', 'N/A')} RWF

📞 Questions? Contact us at {self.company_phone}

Thank you for choosing {company_name}! ✨"""
        
        return message
    
    def _build_visit_reminder_message(self, visit_data):
        """Build formatted visit reminder message"""
        company_name = visit_data.get('company_name', 'On Call Driver')
        
        message = f"""📅 *VISIT REMINDER* 📅

You have a scheduled visit coming up!

🚗 Car: {visit_data.get('car_title', 'N/A')}
📅 Date: {visit_data.get('visit_date', 'N/A')}
⏰ Time: {visit_data.get('visit_time', 'N/A')}
📍 Location: {visit_data.get('location', 'N/A')}

Please arrive 5 minutes early. If you need to reschedule, contact us at {self.company_phone}

See you soon! 🚗✨"""
        
        return message
    
    def _build_payment_confirmation_message(self, payment_data):
        """Build formatted payment confirmation message"""
        company_name = payment_data.get('company_name', 'On Call Driver')
        
        message = f"""✅ *PAYMENT CONFIRMATION* ✅

Your payment has been received!

💰 Amount: {payment_data.get('amount', 'N/A')} RWF
🚗 Vehicle: {payment_data.get('car_title', 'N/A')}
🆔 Transaction ID: {payment_data.get('transaction_id', 'N/A')}
💳 Method: {payment_data.get('payment_method', 'N/A')}

Thank you for your trust in {company_name}! 

For any inquiries, reach out to {self.company_phone}"""
        
        return message
    
    def _log_message(self, phone_number, message_type, status, content, 
                     message_id=None, metadata=None):
        """Log WhatsApp message to database for tracking"""
        try:
            WhatsAppMessage.objects.create(
                phone_number=phone_number,
                message_type=message_type,
                status=status,
                message_id=message_id,
                content=content,
                metadata=metadata or {}
            )
        except Exception as e:
            logger.error(f"Error logging WhatsApp message: {str(e)}")


# Global instance
whatsapp_service = WhatsAppService()


def send_booking_notification(booking_obj):
    """
    Convenience function to send booking notification
    Call this from booking views
    """
    try:
        user_phone = booking_obj.user.phone
        booking_data = {
            'car_title': f"{booking_obj.car.brand.name} {booking_obj.car.model} ({booking_obj.car.year})",
            'booking_date': booking_obj.booking_date.strftime('%d-%m-%Y'),
            'booking_time': booking_obj.booking_date.strftime('%H:%M'),
            'price': booking_obj.price,
            'company_name': 'On Call Driver'
        }
        return whatsapp_service.send_booking_confirmation(user_phone, booking_data)
    except Exception as e:
        logger.error(f"Error sending booking notification: {str(e)}")
        return False


def send_visit_notification(visit_obj):
    """
    Convenience function to send visit notification
    Call this from visit scheduling views
    """
    try:
        user_phone = visit_obj.user.phone
        visit_data = {
            'car_title': f"{visit_obj.car.brand.name} {visit_obj.car.model}",
            'visit_date': visit_obj.visit_date.strftime('%d-%m-%Y'),
            'visit_time': visit_obj.visit_date.strftime('%H:%M'),
            'location': visit_obj.location or 'Our Showroom',
            'company_name': 'On Call Driver'
        }
        return whatsapp_service.send_visit_reminder(user_phone, visit_data)
    except Exception as e:
        logger.error(f"Error sending visit notification: {str(e)}")
        return False


def send_payment_notification(payment_obj):
    """
    Convenience function to send payment notification
    Call this from payment processing
    """
    try:
        user_phone = payment_obj.user.phone
        payment_data = {
            'amount': payment_obj.amount,
            'car_title': f"{payment_obj.booking.car.brand.name} {payment_obj.booking.car.model}",
            'transaction_id': payment_obj.transaction_id or payment_obj.id,
            'payment_method': payment_obj.payment_method or 'Online',
            'company_name': 'On Call Driver'
        }
        return whatsapp_service.send_payment_confirmation(user_phone, payment_data)
    except Exception as e:
        logger.error(f"Error sending payment notification: {str(e)}")
        return False
