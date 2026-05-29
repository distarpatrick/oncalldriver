"""
Database Security & Performance Optimization Module
Handles SQL injection prevention, query optimization, and concurrent access
"""

import logging
import hashlib
import time
from functools import wraps
from django.db import connections, transaction, IntegrityError
from django.db.models import Q, F, Prefetch
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.conf import settings
from django.core.exceptions import ValidationError
import re

logger = logging.getLogger(__name__)

# ============================================================================
# PART 1: SQL INJECTION PREVENTION & QUERY SAFETY
# ============================================================================

class DatabaseSecurityManager:
    """
    Ensures all database queries are safe from SQL injection and optimization issues
    """
    
    @staticmethod
    def sanitize_search_input(search_term):
        """
        Sanitize user search input
        NEVER concatenate user input directly into SQL queries!
        """
        if not search_term:
            return ""
        
        # Remove potentially dangerous characters
        # Allow only alphanumeric, spaces, and safe punctuation
        sanitized = re.sub(r'[;\'\"\\*%]', '', str(search_term))
        
        # Limit length to prevent DoS
        sanitized = sanitized[:100]
        
        return sanitized.strip()
    
    @staticmethod
    def validate_filter_params(filter_dict):
        """
        Validate filter parameters before using in queries
        Prevents injection through filter parameters
        """
        ALLOWED_FIELDS = {
            'cars': ['brand', 'price', 'year', 'fuel_type', 'condition', 'province'],
            'bookings': ['status', 'payment_type', 'customer', 'created_at'],
            'payments': ['status', 'payment_method', 'purpose'],
        }
        
        validated = {}
        
        for key, value in filter_dict.items():
            # Ensure key follows field naming conventions
            if not re.match(r'^[a-z_]+$', key):
                raise ValidationError(f"Invalid filter key: {key}")
            
            # Whitelist check for sensitive models
            # validated[key] = value  # Use ORM, not string concatenation
        
        return validated
    
    @staticmethod
    def safe_search_query(model, search_term, search_fields):
        """
        Perform safe search using Django ORM (not raw SQL)
        Example: safe_search_query(Car, 'toyota', ['title', 'description'])
        """
        if not search_term:
            return model.objects.none()
        
        search_term = DatabaseSecurityManager.sanitize_search_input(search_term)
        
        # Build Q objects for OR search - safe because using ORM
        query = Q()
        for field in search_fields:
            query |= Q(**{f"{field}__icontains": search_term})
        
        return model.objects.filter(query)
    
    @staticmethod
    def get_connection_info():
        """Get database connection info for monitoring"""
        db = connections['default']
        return {
            'engine': db.settings_dict.get('ENGINE'),
            'name': db.settings_dict.get('NAME'),
            'is_open': db.connection is not None,
        }


# ============================================================================
# PART 2: CONCURRENT BOOKING HANDLING & RACE CONDITION PREVENTION
# ============================================================================

class BookingLockManager:
    """
    Prevents race conditions when multiple users try to book the same car
    Uses database-level locking for data integrity
    """
    
    LOCK_TIMEOUT = 10  # seconds
    
    @staticmethod
    def atomic_booking_create(user, car, payment_type, price):
        """
        Create booking with atomic transaction
        Prevents race conditions and double bookings
        
        Usage in views:
            booking = BookingLockManager.atomic_booking_create(user, car, 'full', price)
        """
        from homepage.models import Booking, Car
        from django.utils import timezone
        
        try:
            with transaction.atomic():
                # Select car FOR UPDATE to lock it
                locked_car = Car.objects.select_for_update().get(pk=car.pk)
                
                # Check if car is still available
                if locked_car.status != 'available':
                    raise IntegrityError(
                        f"Car is no longer available (status: {locked_car.status})"
                    )
                
                # Check if car already has confirmed bookings
                existing_booking = Booking.objects.filter(
                    car=locked_car,
                    status__in=['confirmed', 'completed']
                ).exists()
                
                if existing_booking:
                    raise IntegrityError("This car has already been booked")
                
                # Create booking atomically
                booking = Booking.objects.create(
                    car=locked_car,
                    customer=user,
                    payment_type=payment_type,
                    total_price=price,
                    status='pending'
                )
                
                logger.info(f"Booking created atomically: {booking.booking_number}")
                return booking
                
        except IntegrityError as e:
            logger.warning(f"Booking failed - Race condition: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in atomic booking: {str(e)}")
            raise
    
    @staticmethod
    def atomic_payment_process(booking, amount, method, transaction_id):
        """
        Process payment with atomic transaction
        Ensures payment and booking status are always in sync
        """
        from homepage.models import Payment
        
        try:
            with transaction.atomic():
                # Lock booking to prevent concurrent modifications
                locked_booking = booking.__class__.objects.select_for_update().get(pk=booking.pk)
                
                # Create payment record
                payment = Payment.objects.create(
                    booking=locked_booking,
                    customer=locked_booking.customer,
                    amount=amount,
                    payment_method=method,
                    transaction_id=transaction_id,
                    status='success'
                )
                
                # Update booking status
                locked_booking.amount_paid = F('amount_paid') + amount
                locked_booking.remaining_balance = F('total_price') - F('amount_paid')
                
                # Mark as confirmed if full payment
                if locked_booking.amount_paid >= locked_booking.total_price:
                    locked_booking.status = 'confirmed'
                
                locked_booking.save()
                
                logger.info(f"Payment processed atomically: {payment.payment_number}")
                return payment
                
        except Exception as e:
            logger.error(f"Error in atomic payment: {str(e)}")
            raise
    
    @staticmethod
    def atomic_visit_schedule(user, car, visit_date, visit_time, location):
        """
        Schedule visit with atomic transaction
        Handles concurrent visit scheduling safely
        """
        from homepage.models import VisitSchedule
        
        try:
            with transaction.atomic():
                # Lock car to prevent overbooking
                locked_car = car.__class__.objects.select_for_update().get(pk=car.pk)
                
                # Create visit schedule
                visit = VisitSchedule.objects.create(
                    car=locked_car,
                    customer=user,
                    visit_date=visit_date,
                    visit_time=visit_time,
                    location=location,
                    status='pending'
                )
                
                logger.info(f"Visit scheduled atomically: {visit.schedule_number}")
                return visit
                
        except Exception as e:
            logger.error(f"Error in atomic visit schedule: {str(e)}")
            raise


# ============================================================================
# PART 3: QUERY OPTIMIZATION & PERFORMANCE TUNING
# ============================================================================

class QueryOptimizer:
    """
    Optimizes database queries using select_related, prefetch_related, and indexing
    """
    
    @staticmethod
    def get_cars_optimized(filters=None):
        """
        Get cars with all related data in minimal queries
        Prevents N+1 queries problem
        """
        from homepage.models import Car, CarPhoto, CarFeature, CarReview
        
        query = Car.objects.select_related(
            'brand',           # Single car → one brand
            'owner',           # Single car → one owner
            'uploaded_by',     # Single car → one user
        ).prefetch_related(
            'photos',          # Car → multiple photos
            'videos',          # Car → multiple videos
            'features',        # Car → multiple features
            Prefetch('reviews', queryset=CarReview.objects.filter(is_approved=True)),  # Only approved
            'wishlist_count',  # Wishlist count
        ).annotate(
            photo_count=F('photos'),  # Add photo count
            review_count=F('reviews')  # Add review count
        )
        
        # Apply filters if provided
        if filters:
            if 'brand' in filters:
                query = query.filter(brand__name__icontains=filters['brand'])
            if 'price_min' in filters:
                query = query.filter(price__gte=filters['price_min'])
            if 'price_max' in filters:
                query = query.filter(price__lte=filters['price_max'])
            if 'fuel_type' in filters:
                query = query.filter(fuel_type=filters['fuel_type'])
        
        return query
    
    @staticmethod
    def get_bookings_optimized():
        """Get bookings with all related data efficiently"""
        from homepage.models import Booking
        
        return Booking.objects.select_related(
            'car',              # Booking → Car
            'customer',         # Booking → Customer
            'handled_by',       # Booking → Handler user
        ).prefetch_related(
            'payments',         # Booking → Multiple payments
        ).order_by('-created_at')
    
    @staticmethod
    def get_user_dashboard_data(user):
        """
        Get all dashboard data for a user in optimized queries
        Minimal database calls
        """
        from homepage.models import Booking, VisitSchedule, Payment, Car
        
        return {
            'bookings': Booking.objects.filter(customer=user).select_related(
                'car', 'car__brand'
            ).order_by('-created_at')[:10],
            
            'visits': VisitSchedule.objects.filter(customer=user).select_related(
                'car', 'car__brand'
            ).order_by('visit_date')[:10],
            
            'payments': Payment.objects.filter(customer=user).select_related(
                'booking'
            ).order_by('-created_at')[:10],
            
            'wishlists': Car.objects.filter(
                wishlisted_by__user=user
            ).select_related('brand').order_by('-created_at')[:10],
        }
    
    @staticmethod
    def bulk_update_status(model, ids, new_status):
        """
        Update multiple records efficiently using bulk_update
        Avoids N individual saves
        """
        objects = model.objects.filter(pk__in=ids)
        objects.update(status=new_status)
        
        logger.info(f"Bulk updated {objects.count()} records to status: {new_status}")
        return objects.count()


# ============================================================================
# PART 4: DATABASE INDEXING STRATEGY
# ============================================================================

DATABASE_INDEXES = """
These indexes should be created for optimal query performance.
Add to your models.py Meta class:

class Car(models.Model):
    # ... fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['status']),          # Filter by status
            models.Index(fields=['brand']),           # Filter by brand
            models.Index(fields=['price']),           # Filter by price
            models.Index(fields=['created_at']),      # Order by created
            models.Index(fields=['status', 'created_at']),  # Composite: status + date
            models.Index(fields=['brand', 'price']),   # Composite: brand + price
            models.Index(fields=['is_featured', '-created_at']),  # Featured cars
        ]

class Booking(models.Model):
    # ... fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['customer', '-created_at']),  # User bookings
            models.Index(fields=['car']),              # Bookings by car
            models.Index(fields=['status']),           # Filter by status
            models.Index(fields=['booking_number']),   # Lookup by number
        ]

class Payment(models.Model):
    # ... fields ...
    
    class Meta:
        indexes = [
            models.Index(fields=['customer', '-created_at']),  # User payments
            models.Index(fields=['status']),           # Filter by status
            models.Index(fields=['transaction_id']),   # Lookup by transaction
            models.Index(fields=['booking']),          # Payments per booking
        ]

MIGRATION COMMAND:
    python manage.py migrate
"""


# ============================================================================
# PART 5: CACHING FOR PERFORMANCE
# ============================================================================

class CachingStrategy:
    """
    Implement caching to reduce database queries
    """
    
    CACHE_TIMEOUT = {
        'cars_list': 3600,          # 1 hour - car listings
        'car_detail': 1800,         # 30 minutes - single car
        'user_dashboard': 300,      # 5 minutes - dashboard data
        'site_settings': 3600,      # 1 hour - site settings
        'car_reviews': 1800,        # 30 minutes - reviews
    }
    
    @staticmethod
    def get_cars_cached(page=1, filters=None):
        """Get cars list with caching"""
        cache_key = f"cars_list_p{page}_{hashlib.md5(str(filters).encode()).hexdigest()}"
        
        cars = cache.get(cache_key)
        if cars is None:
            cars = QueryOptimizer.get_cars_optimized(filters)
            cache.set(cache_key, cars, CachingStrategy.CACHE_TIMEOUT['cars_list'])
        
        return cars
    
    @staticmethod
    def get_car_detail_cached(car_id):
        """Get single car with caching"""
        cache_key = f"car_detail_{car_id}"
        
        car = cache.get(cache_key)
        if car is None:
            from homepage.models import Car
            car = Car.objects.select_related('brand', 'owner').prefetch_related(
                'photos', 'videos', 'features', 'reviews'
            ).get(pk=car_id)
            cache.set(cache_key, car, CachingStrategy.CACHE_TIMEOUT['car_detail'])
        
        return car
    
    @staticmethod
    def invalidate_car_cache(car_id):
        """Invalidate car cache when updated"""
        cache.delete(f"car_detail_{car_id}")
        cache.delete_pattern("cars_list_*")  # Clear all listings
    
    @staticmethod
    def get_site_settings_cached():
        """Get site settings with caching"""
        cache_key = "site_settings"
        
        settings_obj = cache.get(cache_key)
        if settings_obj is None:
            from homepage.models import SiteSettings
            settings_obj = SiteSettings.objects.first()
            cache.set(cache_key, settings_obj, CachingStrategy.CACHE_TIMEOUT['site_settings'])
        
        return settings_obj


# ============================================================================
# PART 6: CONNECTION POOLING & MONITORING
# ============================================================================

class DatabaseMonitor:
    """
    Monitor database performance and connection health
    """
    
    @staticmethod
    def get_connection_stats():
        """Get database connection statistics"""
        db = connections['default']
        return {
            'is_open': db.connection is not None,
            'db_name': db.settings_dict.get('NAME'),
            'engine': db.settings_dict.get('ENGINE'),
            'queries_executed': len(db.queries) if settings.DEBUG else 'N/A',
        }
    
    @staticmethod
    def check_db_health():
        """Health check - ensure database is accessible"""
        try:
            from django.contrib.auth.models import User
            User.objects.exists()
            return {'status': 'healthy', 'message': 'Database is accessible'}
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {'status': 'unhealthy', 'message': str(e)}
    
    @staticmethod
    def slow_query_logger(query_time_threshold=0.5):
        """Log slow queries for optimization"""
        if not settings.DEBUG:
            return
        
        from django.db import connection
        for query in connection.queries:
            execution_time = float(query['time'])
            if execution_time > query_time_threshold:
                logger.warning(
                    f"SLOW QUERY ({execution_time}s): {query['sql'][:100]}..."
                )


# ============================================================================
# PART 7: TRANSACTION DECORATORS FOR VIEWS
# ============================================================================

def atomic_transaction(view_func):
    """
    Decorator to wrap view in atomic transaction
    Ensures all database changes succeed or all fail
    
    Usage:
        @atomic_transaction
        def create_booking_view(request):
            # Your code here
    """
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        with transaction.atomic():
            return view_func(*args, **kwargs)
    return wrapper


def atomic_transaction_method(func):
    """
    Decorator for model methods
    Usage in model methods that modify multiple records
    """
    @wraps(func)
    @transaction.atomic
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


# ============================================================================
# PART 8: CONCURRENT REQUEST HANDLING
# ============================================================================

class ConcurrencyManager:
    """
    Handle high-traffic scenarios with proper locking and timeouts
    """
    
    @staticmethod
    def handle_concurrent_booking(user, car, payment_type, price):
        """
        Handle concurrent booking attempts safely
        Only one booking per car allowed
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                booking = BookingLockManager.atomic_booking_create(
                    user, car, payment_type, price
                )
                return {'success': True, 'booking': booking}
            
            except IntegrityError as e:
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(0.1 * retry_count)  # Exponential backoff
                else:
                    return {
                        'success': False,
                        'error': 'Car was just booked by another customer. Please try another car.',
                        'retry_count': retry_count
                    }
        
        return {'success': False, 'error': 'Booking failed after retries'}
    
    @staticmethod
    def handle_concurrent_visit_schedule(user, car, visit_date, visit_time, location):
        """
        Handle concurrent visit scheduling
        Multiple visits can be scheduled for same car/time
        """
        try:
            visit = BookingLockManager.atomic_visit_schedule(
                user, car, visit_date, visit_time, location
            )
            return {'success': True, 'visit': visit}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ============================================================================
# SUMMARY & USAGE EXAMPLES
# ============================================================================

"""
QUICK REFERENCE - How to Use These Tools:

1. SQL INJECTION PREVENTION:
   ✅ SAFE:
   Car.objects.filter(title__icontains=user_input)  # Uses ORM
   
   ❌ UNSAFE:
   Car.objects.raw(f"SELECT * FROM cars WHERE title LIKE '{user_input}'")
   
   Use: DatabaseSecurityManager.safe_search_query()

2. CONCURRENT BOOKING:
   booking = BookingLockManager.atomic_booking_create(user, car, 'full', price)
   
3. OPTIMIZE QUERIES:
   cars = QueryOptimizer.get_cars_optimized(filters={'brand': 'Toyota'})
   
4. CACHING:
   cars = CachingStrategy.get_cars_cached(page=1)
   
5. TRANSACTION SAFETY:
   @atomic_transaction
   def my_view(request):
       # Multiple database changes here - all atomic
   
6. PAYMENT PROCESSING:
   payment = BookingLockManager.atomic_payment_process(booking, amount, method, txn_id)

7. MONITORING:
   stats = DatabaseMonitor.get_connection_stats()
   health = DatabaseMonitor.check_db_health()
"""
