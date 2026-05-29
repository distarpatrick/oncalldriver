"""
EXAMPLE: How to Use Database Security & Performance Tools in Your Views

Copy and adapt these examples to your actual view files:
- homepage/views.py
- booking/views.py
- payment/views.py
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction, IntegrityError

# Import our security and optimization tools
from homepage.database_security import (
    DatabaseSecurityManager,
    BookingLockManager,
    QueryOptimizer,
    CachingStrategy,
    ConcurrencyManager,
    atomic_transaction,
)

# ============================================================================
# EXAMPLE 1: SAFE CAR SEARCH (SQL Injection Prevention)
# ============================================================================

def search_cars_safe(request):
    """
    ✅ SECURE: Uses Django ORM, properly sanitized input
    """
    search_term = request.GET.get('q', '').strip()
    
    # Sanitize input
    search_term = DatabaseSecurityManager.sanitize_search_input(search_term)
    
    # Safe search using ORM
    cars = DatabaseSecurityManager.safe_search_query(
        model=Car,
        search_term=search_term,
        search_fields=['title', 'description', 'model']
    )
    
    # Optimize query
    cars = QueryOptimizer.get_cars_optimized()
    
    return render(request, 'cars/search_results.html', {'cars': cars})


# ============================================================================
# EXAMPLE 2: ATOMIC BOOKING (Race Condition Prevention)
# ============================================================================

@login_required
@require_POST
@atomic_transaction
def book_car_safe(request, car_pk):
    """
    ✅ ATOMIC: Prevents double-booking via database locking
    One user gets the car, others see it unavailable instantly
    """
    car = get_object_or_404(Car, pk=car_pk)
    payment_type = request.POST.get('payment_type', 'full')  # 'full' or 'half'
    
    # Use atomic transaction with locking
    result = ConcurrencyManager.handle_concurrent_booking(
        user=request.user,
        car=car,
        payment_type=payment_type,
        price=car.price
    )
    
    if result['success']:
        booking = result['booking']
        messages.success(request, f"Booking created: {booking.booking_number}")
        
        # Send WhatsApp notification
        from homepage.whatsapp_service import send_booking_notification
        send_booking_notification(booking)
        
        return redirect('homepage:booking_detail', pk=booking.id)
    else:
        # Another customer booked it first
        messages.error(request, result['error'])
        return redirect('homepage:cars')


# ============================================================================
# EXAMPLE 3: OPTIMIZED CAR LISTING (N+1 Query Prevention)
# ============================================================================

def car_list_optimized(request):
    """
    ✅ OPTIMIZED: Single query to get all car data with related objects
    Avoids N+1 query problem
    
    Bad:
        cars = Car.objects.all()  # Query 1
        for car in cars:
            print(car.brand.name)  # Query 2, 3, 4, ... N+1
    
    Good (our approach):
        cars = QueryOptimizer.get_cars_optimized()  # 1 query with all data
    """
    # Get all cars with related data in single optimized query
    cars = QueryOptimizer.get_cars_optimized(filters={
        'fuel_type': request.GET.get('fuel_type'),
        'price_min': request.GET.get('price_min'),
        'price_max': request.GET.get('price_max'),
    })
    
    # Paginate
    page = request.GET.get('page', 1)
    paginator = Paginator(cars, 20)  # 20 cars per page
    
    try:
        cars_page = paginator.page(page)
    except PageNotFound:
        cars_page = paginator.page(1)
    
    return render(request, 'cars/list.html', {'cars': cars_page})


# ============================================================================
# EXAMPLE 4: ATOMIC PAYMENT PROCESSING
# ============================================================================

@login_required
@require_POST
def process_payment_safe(request, booking_pk):
    """
    ✅ ATOMIC: Payment and booking status always stay in sync
    If payment succeeds, booking is updated. If booking update fails, payment is rolled back.
    """
    booking = get_object_or_404(Booking, pk=booking_pk, customer=request.user)
    
    amount = request.POST.get('amount')
    payment_method = request.POST.get('payment_method')
    transaction_id = request.POST.get('transaction_id')
    
    try:
        # Process payment atomically
        payment = BookingLockManager.atomic_payment_process(
            booking=booking,
            amount=amount,
            method=payment_method,
            transaction_id=transaction_id
        )
        
        messages.success(request, f"Payment processed: {payment.payment_number}")
        
        # Send WhatsApp confirmation
        from homepage.whatsapp_service import send_payment_notification
        send_payment_notification(payment)
        
        return redirect('homepage:payment_success', payment_id=payment.id)
    
    except IntegrityError as e:
        messages.error(request, "Payment processing failed. Please try again.")
        return redirect('homepage:booking_detail', pk=booking.id)


# ============================================================================
# EXAMPLE 5: CACHED USER DASHBOARD (Performance)
# ============================================================================

@login_required
def dashboard_optimized(request):
    """
    ✅ OPTIMIZED & CACHED: Reduces database queries significantly
    Dashboard loads in milliseconds instead of seconds
    """
    # Get all dashboard data in optimized queries
    dashboard_data = QueryOptimizer.get_user_dashboard_data(request.user)
    
    return render(request, 'user/dashboard.html', dashboard_data)


# ============================================================================
# EXAMPLE 6: CACHED CAR DETAIL PAGE
# ============================================================================

def car_detail_cached(request, car_pk):
    """
    ✅ CACHED: Car details are cached, reduces database load
    Cache invalidated when car is updated
    """
    try:
        car = CachingStrategy.get_car_detail_cached(car_pk)
    except Car.DoesNotExist:
        return redirect('homepage:cars')
    
    # Get related reviews (cached separately)
    reviews = car.reviews.filter(is_approved=True).order_by('-created_at')
    
    return render(request, 'cars/detail.html', {
        'car': car,
        'reviews': reviews,
    })


# ============================================================================
# EXAMPLE 7: ADMIN BULK UPDATE (Performance)
# ============================================================================

def approve_pending_cars_bulk(request):
    """
    ✅ BULK UPDATE: Update 1000 cars much faster than individual saves
    Instead of 1000 queries: SELECT + 1000 UPDATE
    Now: 1 query with all updates
    """
    if not request.user.is_admin:
        messages.error(request, "Admin access required")
        return redirect('homepage:dashboard')
    
    # Get all pending cars
    pending_car_ids = list(
        Car.objects.filter(status='pending').values_list('id', flat=True)
    )
    
    # Update all at once (1 query instead of N queries)
    updated_count = QueryOptimizer.bulk_update_status(
        Car,
        pending_car_ids,
        'approved'
    )
    
    messages.success(request, f"Approved {updated_count} cars")
    return redirect('homepage:dashboard')


# ============================================================================
# EXAMPLE 8: SAFE FILTERING & SEARCH PARAMS
# ============================================================================

def cars_with_safe_filters(request):
    """
    ✅ SAFE: Filters are validated before use
    Prevents injection through filter parameters
    """
    # Get and validate filter parameters
    filters = {
        'brand': request.GET.get('brand', ''),
        'fuel_type': request.GET.get('fuel_type', ''),
        'price_min': request.GET.get('price_min', ''),
        'price_max': request.GET.get('price_max', ''),
    }
    
    # Validate filters
    try:
        validated_filters = DatabaseSecurityManager.validate_filter_params(filters)
    except ValidationError as e:
        messages.error(request, f"Invalid filter: {str(e)}")
        return redirect('homepage:cars')
    
    # Use validated filters
    cars = QueryOptimizer.get_cars_optimized(filters=validated_filters)
    
    return render(request, 'cars/list.html', {'cars': cars})


# ============================================================================
# EXAMPLE 9: MONITORING DATABASE HEALTH
# ============================================================================

def admin_database_health(request):
    """
    Check database health and performance metrics
    Add to admin dashboard
    """
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    from homepage.database_security import DatabaseMonitor
    
    health = DatabaseMonitor.check_db_health()
    stats = DatabaseMonitor.get_connection_stats()
    
    return JsonResponse({
        'health': health,
        'stats': stats,
    })


# ============================================================================
# EXAMPLE 10: CONCURRENT VISIT SCHEDULING
# ============================================================================

@login_required
@require_POST
def schedule_visit_concurrent(request, car_pk):
    """
    ✅ HANDLES CONCURRENCY: Multiple users can schedule visits simultaneously
    Each gets their own visit record, no conflicts
    """
    car = get_object_or_404(Car, pk=car_pk)
    
    visit_date = request.POST.get('visit_date')
    visit_time = request.POST.get('visit_time')
    location = request.POST.get('location', 'Our Showroom')
    
    result = ConcurrencyManager.handle_concurrent_visit_schedule(
        user=request.user,
        car=car,
        visit_date=visit_date,
        visit_time=visit_time,
        location=location
    )
    
    if result['success']:
        visit = result['visit']
        messages.success(request, f"Visit scheduled: {visit.schedule_number}")
        
        # Send WhatsApp reminder
        from homepage.whatsapp_service import send_visit_notification
        send_visit_notification(visit)
        
        return redirect('homepage:schedule_detail', pk=visit.id)
    else:
        messages.error(request, result['error'])
        return redirect('homepage:car_detail', pk=car.pk)


# ============================================================================
# EXAMPLE 11: TRANSACTION DECORATOR ON CLASS-BASED VIEW METHOD
# ============================================================================

from django.views import View

class BookingView(View):
    """Class-based view with atomic transactions"""
    
    @atomic_transaction
    def post(self, request, car_pk):
        """
        ✅ ATOMIC: This entire method runs in a transaction
        """
        car = get_object_or_404(Car, pk=car_pk)
        
        # Create booking
        booking = Booking.objects.create(
            car=car,
            customer=request.user,
            payment_type=request.POST.get('payment_type'),
            total_price=car.price,
        )
        
        # If anything fails below, entire transaction rolls back
        # including the booking creation
        
        return redirect('homepage:booking_detail', pk=booking.id)


# ============================================================================
# EXAMPLE 12: SLOW QUERY DETECTION & LOGGING
# ============================================================================

def log_slow_queries(request):
    """
    Monitor slow database queries (for debugging)
    """
    if not settings.DEBUG:
        return JsonResponse({'error': 'Only available in debug mode'})
    
    from django.db import connection
    
    slow_queries = []
    for query in connection.queries:
        execution_time = float(query['time'])
        if execution_time > 0.5:  # > 500ms is slow
            slow_queries.append({
                'time': execution_time,
                'sql': query['sql'][:200] + '...',
            })
    
    return JsonResponse({
        'slow_queries_count': len(slow_queries),
        'queries': slow_queries[:10]  # Top 10 slowest
    })


# ============================================================================
# USAGE SUMMARY
# ============================================================================

"""
COPY & ADAPT THESE PATTERNS TO YOUR VIEWS:

1. SEARCH (SQL Injection Prevention):
   ✅ cars = DatabaseSecurityManager.safe_search_query(Car, search_term, fields)

2. BOOKING (Race Condition Prevention):
   ✅ booking = ConcurrencyManager.handle_concurrent_booking(...)

3. PAYMENT (Data Consistency):
   ✅ payment = BookingLockManager.atomic_payment_process(...)

4. QUERIES (Performance):
   ✅ cars = QueryOptimizer.get_cars_optimized()

5. CACHING (Speed):
   ✅ cars = CachingStrategy.get_cars_cached()

6. TRANSACTIONS (Reliability):
   ✅ @atomic_transaction
      def my_view(request):
          ...

7. MONITORING (Health):
   ✅ health = DatabaseMonitor.check_db_health()
"""
