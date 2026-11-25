from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
import uuid

# =================== ACCOUNTS APP MODELS ====================
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'super_admin')
        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    
    ROLE_CHOICES = [
        ('super_admin',       'Super Admin'),
        ('admin',             'Admin'),
        ('manager',           'Manager'),
        ('marketer',          'Marketer / Online Marketer'),
        ('sales_agent',       'Sales Agent'),
        ('accountant',        'Accountant'),
        ('inventory_manager', 'Inventory Manager'),
        ('customer_support',  'Customer Support'),
        ('customer',          'Customer'),
    ]

    PROVINCE_CHOICES = [
        ('kigali',   'Kigali City'),
        ('northern', 'Northern Province'),
        ('southern', 'Southern Province'),
        ('eastern',  'Eastern Province'),
        ('western',  'Western Province'),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email         = models.EmailField(unique=True)
    full_name     = models.CharField(max_length=150)
    phone         = models.CharField(
                        max_length=15,
                        validators=[RegexValidator(r'^\+250[0-9]{9}$', 'Enter a valid Rwandan phone number (+250XXXXXXXXX)')],
                    )
    profile_photo = models.ImageField(upload_to='accounts/profiles/', blank=True, null=True)
    role          = models.CharField(max_length=30, choices=ROLE_CHOICES, default='customer')
    province      = models.CharField(max_length=20, choices=PROVINCE_CHOICES, blank=True, null=True)
    district      = models.CharField(max_length=100, blank=True, null= True)

    # Status
    is_active     = models.BooleanField(default=True)
    is_staff      = models.BooleanField(default=False)
    is_verified   = models.BooleanField(default=False)
    date_joined   = models.DateTimeField(default=timezone.now)
    last_login    = models.DateTimeField(blank=True, null=True)

    # ✅ ADD THESE TWO FIELDS RIGHT HERE
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        related_name='marketing_users',
        related_query_name='marketing_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        related_name='marketing_users',
        related_query_name='marketing_user',
    )

    objects = CustomUserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name', 'phone']

    class Meta:
        verbose_name        = 'User'
        verbose_name_plural = 'Users'
        ordering            = ['-date_joined']

    def __str__(self):
        return f"{self.full_name} ({self.role})"

    # Role helpers
    @property
    def is_admin(self):         return self.role in ('super_admin', 'admin')
    @property
    def is_marketer(self):      return self.role == 'marketer'
    @property
    def is_sales_agent(self):   return self.role == 'sales_agent'
    @property
    def is_accountant(self):    return self.role == 'accountant'
    @property
    def is_manager(self):       return self.role == 'manager'
    @property
    def is_customer(self):      return self.role == 'customer'
    @property
    def is_customer_support(self): return self.role == 'customer_support'
    @property
    def is_inventory_manager(self): return self.role == 'inventory_manager'

class CompanyCarOwner(models.Model):
    """
    Represents a citizen who handed their car to the company for e-marketing/sale.
    The company acts as the e-marketing agent for both its own cars and citizens' cars.
    """
    OWNER_TYPE_CHOICES = [
        ('company',  'Company Owned'),
        ('citizen',  'Citizen Consignment'),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_type      = models.CharField(max_length=20, choices=OWNER_TYPE_CHOICES, default='citizen')

    # Only filled if owner_type == 'citizen'
    full_name       = models.CharField(max_length=150, blank=True)
    phone           = models.CharField(max_length=15, blank=True)
    email           = models.EmailField(blank=True)
    national_id     = models.CharField(max_length=20, blank=True)
    province        = models.CharField(max_length=100, blank=True)
    district        = models.CharField(max_length=100, blank=True)
    id_document     = models.FileField(upload_to='owners/documents/', blank=True, null=True)

    # Agreement
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00, help_text="Company commission % on sale")
    agreement_file  = models.FileField(upload_to='owners/agreements/', blank=True, null=True)
    registered_by   = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='registered_owners')
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.owner_type == 'company':
            return "Company Owned"
        return f"Citizen: {self.full_name} ({self.phone})"

# ===================== CARS APP MODELS ======================
class CarBrand(models.Model):
    name     = models.CharField(max_length=100, unique=True)
    logo     = models.ImageField(upload_to='cars/brands/', blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Car(models.Model):

    CONDITION_CHOICES = [
        ('new',  'Brand New'),
    ]
    TRANSMISSION_CHOICES = [
        ('manual',    'Manual'),
        ('automatic', 'Automatic'),
        ('cvt',       'CVT'),
    ]
    FUEL_CHOICES = [
        ('petrol',   'Petrol'),
        ('diesel',   'Diesel'),
        ('electric', 'Electric'),
        ('hybrid',   'Hybrid'),
    ]
    DRIVE_CHOICES = [
        ('fwd', 'Front-Wheel Drive'),
        ('rwd', 'Rear-Wheel Drive'),
        ('awd', 'All-Wheel Drive'),
        ('4wd', '4WD'),
    ]
    STATUS_CHOICES = [
        ('available',  'Available'),      # visible on platform
        ('booked',     'Booked'),         # hidden — full/half payment done
        ('scheduled',  'Scheduled'),      # visible — visits scheduled, not yet purchased
        ('sold',       'Sold'),           # hidden — removed from platform
        ('pending',    'Pending Review'), # waiting admin approval
        ('rejected',   'Rejected'),       # admin rejected listing
        ('inactive',   'Inactive'),       # marketer unpublished it
    ]

    id                    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Ownership
    owner                 = models.ForeignKey(CompanyCarOwner, on_delete=models.PROTECT, related_name='cars')
    uploaded_by           = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='uploaded_cars',
                                              help_text="Marketer who uploaded this listing")
    approved_by           = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_cars')
    approved_at           = models.DateTimeField(null=True, blank=True)

    # Basic Info
    title                 = models.CharField(max_length=200)
    brand                 = models.ForeignKey(CarBrand, on_delete=models.SET_NULL, null=True, related_name='cars')
    model                 = models.CharField(max_length=100)
    year                  = models.PositiveIntegerField(validators=[MinValueValidator(1900), MaxValueValidator(2100)])
    condition             = models.CharField(max_length=10, choices=CONDITION_CHOICES)

    # Specs
    mileage_km            = models.PositiveIntegerField(default=0, help_text="Mileage in kilometers")
    color                 = models.CharField(max_length=50)
    engine_size_cc        = models.PositiveIntegerField(blank=True, null=True, help_text="Engine in CC e.g. 1500")
    transmission          = models.CharField(max_length=15, choices=TRANSMISSION_CHOICES)
    fuel_type             = models.CharField(max_length=10, choices=FUEL_CHOICES)
    drive_type            = models.CharField(max_length=5, choices=DRIVE_CHOICES, blank=True)
    seats                 = models.PositiveIntegerField(default=5)
    doors                 = models.PositiveIntegerField(default=4)
    stock_number           = models.CharField(max_length=100, blank=True, unique=True, null=True)
    # Rwanda-Specific
    registration_plate    = models.CharField(max_length=15, blank=True, unique=True, null=False,
                                             validators=[RegexValidator(r'^R[A-Z]{2}\s?\d{3}\s?[A-Z]$', 'Enter valid Rwanda plate e.g. RAA 001 A')])
    # Pricing
    price                 = models.DecimalField(max_digits=15, decimal_places=2, help_text="Price in RWF")
    is_negotiable         = models.BooleanField(default=False)
    scheduling_fee        = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                                help_text="Fee in RWF to schedule a visit for this car")

    # Location
    province              = models.CharField(max_length=100)
    district              = models.CharField(max_length=100)
    exact_location        = models.CharField(max_length=255, blank=True)

    # Description
    description           = models.TextField()
    features_summary      = models.TextField(blank=True, help_text="Comma-separated key features")

    # Status & Visibility
    status                = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    is_featured           = models.BooleanField(default=False, help_text="Show as hero/featured on homepage")

    # Stats
    views_count           = models.PositiveIntegerField(default=0)
    average_rating        = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews         = models.PositiveIntegerField(default=0)

    created_at            = models.DateTimeField(auto_now_add=True)
    updated_at            = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Car'

    def __str__(self):
        return f"{self.year} {self.brand} {self.model} — {self.price} RWF"

    def is_visible_on_platform(self):
        """Car shows on platform while it can still be viewed by customers."""
        return self.status in ('available', 'scheduled', 'booked')

    def mark_as_booked(self):
        """Keep the car visible, but mark it as already booked."""
        self.status = 'booked'
        self.save(update_fields=['status'])

    def mark_as_sold(self):
        """Remove from platform permanently when sold after visit"""
        self.status = 'sold'
        self.save(update_fields=['status'])

    def update_rating(self):
        """Recalculate average rating from all approved reviews"""
        reviews = self.reviews.filter(is_approved=True)
        count   = reviews.count()
        if count > 0:
            total = sum(r.rating for r in reviews)
            self.average_rating = round(total / count, 2)
        else:
            self.average_rating = 0.00
        self.total_reviews = count
        self.save(update_fields=['average_rating', 'total_reviews'])

class CarPhoto(models.Model):
    """Minimum 8 photos required per car listing"""
    car         = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='photos')
    photo       = models.ImageField(upload_to='cars/photos/')
    caption     = models.CharField(max_length=200, blank=True)
    is_cover    = models.BooleanField(default=False, help_text="Main/hero photo shown on listing card")
    order       = models.PositiveIntegerField(default=0, help_text="Display order")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'uploaded_at']

    def __str__(self):
        return f"Photo for {self.car.title} (cover={self.is_cover})"

    def save(self, *args, **kwargs):
        # Only one cover photo per car
        if self.is_cover:
            CarPhoto.objects.filter(car=self.car, is_cover=True).update(is_cover=False)
        super().save(*args, **kwargs)

class CarVideo(models.Model):
    """Minimum 2 videos required per car listing"""
    car         = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='videos')
    video       = models.FileField(upload_to='cars/videos/')
    title       = models.CharField(max_length=200, blank=True)
    duration_sec = models.PositiveIntegerField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Video: {self.title} — {self.car.title}"

class CarFeature(models.Model):
    """Individual features/amenities of a car"""
    FEATURE_CATEGORIES = [
        ('comfort',   'Comfort'),
        ('safety',    'Safety'),
        ('tech',      'Technology'),
        ('exterior',  'Exterior'),
        ('interior',  'Interior'),
        ('performance','Performance'),
    ]
    car      = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='features')
    name     = models.CharField(max_length=100, help_text="e.g. Sunroof, GPS, Leather Seats, Backup Camera")
    category = models.CharField(max_length=15, choices=FEATURE_CATEGORIES, default='comfort')
    has_it   = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({'✓' if self.has_it else '✗'}) — {self.car.title}"

class CarComment(models.Model):
    """Public comments on a car listing"""
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    car        = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='comments')
    user       = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='comments')
    parent     = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies',
                                   help_text="For threaded replies")
    content    = models.TextField()
    is_approved = models.BooleanField(default=True)
    is_flagged  = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.user.full_name} on {self.car.title}"

class CarReview(models.Model):
    """Star rating + written review per car — one per customer"""
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    car         = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='reviews')
    customer    = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews')
    rating      = models.PositiveIntegerField(
                      validators=[MinValueValidator(1), MaxValueValidator(5)],
                      help_text="Rating from 1 to 5 stars"
                  )
    title       = models.CharField(max_length=200, blank=True)
    body        = models.TextField(blank=True)
    is_approved = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('car', 'customer')  # one review per customer per car
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating}★ by {self.customer.full_name} on {self.car.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Auto-update car average rating after every save
        self.car.update_rating()

    def delete(self, *args, **kwargs):
        car = self.car
        super().delete(*args, **kwargs)
        car.update_rating()

class CarWishlist(models.Model):
    """Customers can save/wishlist cars"""
    user       = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='wishlists')
    car        = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'car')

    def __str__(self):
        return f"{self.user.full_name} wishlisted {self.car.title}"

class CarView(models.Model):
    """Track unique views per car"""
    car        = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='view_logs')
    user       = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    viewed_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-viewed_at']

# =================== BOOKINGS APP MODELS ====================

class Booking(models.Model):
    """
    A booking is created when a customer pays (half or full).
    Car is immediately hidden from platform upon booking creation.
    """
    BOOKING_STATUS = [
        ('pending',    'Pending Payment'),
        ('confirmed',  'Confirmed'),
        ('cancelled',  'Cancelled'),
        ('completed',  'Completed / Sold'),
    ]
    PAYMENT_TYPE = [
        ('full', 'Full Payment'),
        ('half', 'Half Payment (50%)'),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_number  = models.CharField(max_length=20, unique=True, editable=False)
    car             = models.ForeignKey(Car, on_delete=models.PROTECT, related_name='bookings')
    customer        = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='bookings')
    handled_by      = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='handled_bookings', help_text="Sales agent handling this booking")
    commission_fees = models.DecimalField(max_digits=15, decimal_places=2, default=0, help_text="Commission fees in 40000 RWF for this booking")
    # Payment
    driver_needed = models.BooleanField(default=False, help_text="Does the customer need a driver to deliver the car?")
    payment_type    = models.CharField(max_length=10, choices=PAYMENT_TYPE)
    total_price     = models.DecimalField(max_digits=15, decimal_places=2, help_text="Full car price in RWF")
    amount_paid     = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    remaining_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    status          = models.CharField(max_length=15, choices=BOOKING_STATUS, default='pending')
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking {self.booking_number} — {self.car.title}"

    def save(self, *args, **kwargs):
        # Auto-generate booking number
        if not self.booking_number:
            last = Booking.objects.order_by('-created_at').first()
            num  = (int(last.booking_number.split('-')[-1]) + 1) if last else 1
            self.booking_number = f"BK-{timezone.now().year}-{num:04d}"

        # Calculate remaining balance
        self.remaining_balance = self.total_price - self.amount_paid
        super().save(*args, **kwargs)

        # Hide car from platform immediately upon confirmed booking
        if self.status == 'confirmed':
            self.car.mark_as_booked()

        # Mark car as sold when booking is completed
        if self.status == 'completed':
            self.car.mark_as_sold()

class VisitSchedule(models.Model):
    """
    Multiple customers can schedule visits to the SAME car at the SAME time.
    Car stays VISIBLE (status=scheduled) while visits are pending.
    If a visitor buys/books during visit → car is removed from platform automatically.
    """
    VISIT_STATUS = [
        ('pending',     'Pending Confirmation'),
        ('confirmed',   'Confirmed'),
        ('rescheduled', 'Rescheduled'),
        ('visited',     'Visited — No Purchase'),
        ('purchased',   'Visited & Purchased'),   # triggers car removal
        ('cancelled',   'Cancelled'),
        ('no_show',     'No Show'),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule_number = models.CharField(max_length=20, unique=True, editable=False)
    car             = models.ForeignKey(Car, on_delete=models.PROTECT, related_name='schedules')
    customer        = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='schedules')
    confirmed_by    = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='confirmed_schedules')

    # Visit details
    visit_date      = models.DateField()
    visit_time      = models.TimeField()
    location        = models.CharField(max_length=255, help_text="Where the car can be visited")
    district        = models.CharField(max_length=100)

    # Scheduling fee
    scheduling_fee  = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Fee in RWF to schedule this visit")
    fee_paid        = models.BooleanField(default=False)

    status          = models.CharField(max_length=15, choices=VISIT_STATUS, default='pending')
    notes           = models.TextField(blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['visit_date', 'visit_time']
        # Multiple customers CAN visit the same car at the same time — no unique constraint on (car, visit_date, visit_time)

    def __str__(self):
        return f"Visit {self.schedule_number} — {self.car.title} on {self.visit_date}"

    def save(self, *args, **kwargs):
        if not self.schedule_number:
            last = VisitSchedule.objects.order_by('-created_at').first()
            num  = (int(last.schedule_number.split('-')[-1]) + 1) if last else 1
            self.schedule_number = f"VS-{timezone.now().year}-{num:04d}"
        super().save(*args, **kwargs)

        # If visitor purchased during visit → auto-remove car from platform
        if self.status == 'purchased':
            self.car.mark_as_sold()

        # Update car status to 'scheduled' when first visit is confirmed
        elif self.status == 'confirmed' and self.car.status == 'available':
            self.car.status = 'scheduled'
            self.car.save(update_fields=['status'])

# =================== PAYMENTS APP MODELS ====================

class Payment(models.Model):

    PAYMENT_METHOD = [
        ('mtn_momo',       'MTN Mobile Money'),
        ('airtel_money',   'Airtel Money'),
        ('bank_transfer',  'Bank Transfer'),
        ('cash',           'Cash (In Person)'),
    ]
    PAYMENT_PURPOSE = [
        ('half_payment',     'Half Payment for Car'),
        ('full_payment',     'Full Payment for Car'),
        ('remaining_balance','Remaining Balance'),
        ('scheduling_fee',   'Visit Scheduling Fee'),
    ]
    PAYMENT_STATUS = [
        ('pending',  'Pending'),
        ('success',  'Success'),
        ('failed',   'Failed'),
        ('refunded', 'Refunded'),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_number  = models.CharField(max_length=20, unique=True, editable=False)

    # References (one of these will be set)
    booking         = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    schedule        = models.ForeignKey(VisitSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    customer        = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='payments')
    processed_by    = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='processed_payments', help_text="Accountant who processed this")

    amount          = models.DecimalField(max_digits=15, decimal_places=2, help_text="Amount in RWF")
    payment_method  = models.CharField(max_length=20, choices=PAYMENT_METHOD)
    purpose         = models.CharField(max_length=20, choices=PAYMENT_PURPOSE)
    phone_number    = models.CharField(max_length=15, blank=True, help_text="MoMo phone number used")
    transaction_id  = models.CharField(max_length=200, blank=True, help_text="Transaction ID from MTN/Flutterwave/Bank")
    receipt_image   = models.ImageField(upload_to='payments/receipts/', blank=True, null=True, help_text="Screenshot or receipt image for manual payments")
    status          = models.CharField(max_length=10, choices=PAYMENT_STATUS, default='pending')
    failure_reason  = models.TextField(blank=True)
    paid_at         = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    # Gateway / verification tracking
    reference_code     = models.CharField(max_length=20, blank=True, db_index=True,
                                          help_text="Short code the customer quotes on transfers (e.g. OCD-7K2Q9X)")
    provider_reference = models.CharField(max_length=64, blank=True, db_index=True,
                                          help_text="Reference returned by MTN/Airtel API")
    provider_status    = models.CharField(max_length=30, blank=True,
                                          help_text="awaiting_approval, awaiting_verification, successful, failed…")
    provider_payload   = models.JSONField(default=dict, blank=True)
    payer_name         = models.CharField(max_length=150, blank=True)
    bank_account       = models.ForeignKey('payment.BankAccount', on_delete=models.SET_NULL,
                                           null=True, blank=True, related_name='payments')
    updated_at         = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.payment_number} — {self.amount} RWF ({self.status})"

    @property
    def is_paid(self):
        return self.status == 'success'

    @property
    def awaiting_verification(self):
        return self.status == 'pending' and self.provider_status == 'awaiting_verification'

    def save(self, *args, **kwargs):
        if not self.reference_code:
            import secrets
            alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
            self.reference_code = "OCD-" + "".join(secrets.choice(alphabet) for _ in range(6))
        if not self.payment_number:
            last = Payment.objects.order_by('-created_at').first()
            num  = (int(last.payment_number.split('-')[-1]) + 1) if last else 1
            self.payment_number = f"PAY-{timezone.now().year}-{num:04d}"
        if self.status == 'success' and not self.paid_at:
            self.paid_at = timezone.now()
        super().save(*args, **kwargs)

class Invoice(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=20, unique=True, editable=False)
    payment        = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='invoice')
    issued_to      = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='invoices')
    issued_by      = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='issued_invoices')
    pdf_file       = models.FileField(upload_to='invoices/', blank=True, null=True)
    is_sent        = models.BooleanField(default=False)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice {self.invoice_number}"

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            last = Invoice.objects.order_by('-created_at').first()
            num  = (int(last.invoice_number.split('-')[-1]) + 1) if last else 1
            self.invoice_number = f"INV-{timezone.now().year}-{num:04d}"
        super().save(*args, **kwargs)

class Refund(models.Model):
    REFUND_STATUS = [
        ('pending',   'Pending'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
        ('processed', 'Processed'),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment       = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name='refunds')
    reason        = models.TextField()
    amount        = models.DecimalField(max_digits=15, decimal_places=2, help_text="Refund amount in RWF")
    status        = models.CharField(max_length=10, choices=REFUND_STATUS, default='pending')
    requested_by  = models.ForeignKey(CustomUser, on_delete=models.PROTECT, related_name='refund_requests')
    approved_by   = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_refunds')
    created_at    = models.DateTimeField(auto_now_add=True)
    processed_at  = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Refund {self.amount} RWF — {self.status}"

# ================ NOTIFICATIONS APP MODELS ==================

class Notification(models.Model):
    NOTIF_TYPE = [
        ('booking',    'Booking'),
        ('payment',    'Payment'),
        ('schedule',   'Visit Schedule'),
        ('car',        'Car Listing'),
        ('system',     'System'),
        ('review',     'Review / Comment'),
    ]

    id        = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user      = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    title     = models.CharField(max_length=200)
    message   = models.TextField()
    notif_type = models.CharField(max_length=15, choices=NOTIF_TYPE)
    link      = models.URLField(blank=True, help_text="Link to relevant page")
    is_read   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notif → {self.user.full_name}: {self.title}"

class SMSLog(models.Model):
    STATUS = [('sent', 'Sent'), ('failed', 'Failed')]
    PROVIDER = [('mtn', 'MTN'), ('airtel', 'Airtel'), ('other', 'Other')]

    recipient_phone = models.CharField(max_length=15)
    message         = models.TextField()
    status          = models.CharField(max_length=10, choices=STATUS)
    provider        = models.CharField(max_length=10, choices=PROVIDER, default='mtn')
    sent_at         = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SMS to {self.recipient_phone} ({self.status})"

class EmailLog(models.Model):
    STATUS = [('sent', 'Sent'), ('failed', 'Failed')]

    recipient_email = models.EmailField()
    subject         = models.CharField(max_length=255)
    body            = models.TextField()
    status          = models.CharField(max_length=10, choices=STATUS)
    sent_at         = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Email to {self.recipient_email}: {self.subject} ({self.status})"

# ================ DASHBOARD / SETTINGS MODELS ===============

class SiteSettings(models.Model):
    """Singleton model — only one row"""
    site_name            = models.CharField(max_length=100, default='CAR_MARKETING')
    site_logo            = models.ImageField(upload_to='site/', blank=True, null=True)
    hero_banner          = models.ImageField(upload_to='site/banners/', blank=True, null=True,
                                             help_text="Large homepage hero photo")
    tagline              = models.CharField(max_length=255, blank=True)
    contact_phone        = models.CharField(max_length=15, blank=True)
    contact_email        = models.EmailField(blank=True)
    address              = models.CharField(max_length=255, default='Kigali, Rwanda')
    facebook_url         = models.URLField(blank=True)
    instagram_url        = models.URLField(blank=True)
    twitter_url          = models.URLField(blank=True)
    youtube_url          = models.URLField(blank=True)
    whatsapp_number      = models.CharField(max_length=15, blank=True)
    payment_phone        = models.CharField(max_length=25, blank=True, default='+250 792 456 127')
    payment_mtn_code     = models.CharField(max_length=25, blank=True, default='1159490')
    payment_account      = models.CharField(max_length=50, blank=True, default='123456789')
    payment_account_name = models.CharField(max_length=100, blank=True, default='OnCall Driver')
    payment_airtel_phone = models.CharField(max_length=25, blank=True,
                                            help_text="Airtel Money number customers send money to (manual mode)")

    # Business rules
    default_scheduling_fee = models.DecimalField(max_digits=10, decimal_places=2, default=5000,
                                                  help_text="Default visit scheduling fee in RWF")
    half_payment_percent   = models.DecimalField(max_digits=5, decimal_places=2, default=50.00,
                                                  help_text="Half payment percentage (default 50%)")
    commission_rate        = models.DecimalField(max_digits=5, decimal_places=2, default=5.00,
                                                  help_text="Default company commission % on citizen cars")

    updated_at             = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Site Settings'
        verbose_name_plural = 'Site Settings'

    def __str__(self):
        return self.site_name

    def save(self, *args, **kwargs):
        self.pk = 1  # Enforce singleton
        super().save(*args, **kwargs)

class Promotion(models.Model):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title           = models.CharField(max_length=200)
    description     = models.TextField(blank=True)
    banner_image    = models.ImageField(upload_to='promotions/', blank=True, null=True)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cars            = models.ManyToManyField(Car, blank=True, related_name='promotions')
    start_date      = models.DateField()
    end_date        = models.DateField()
    is_active       = models.BooleanField(default=True)
    created_by      = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='promotions')
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Promo: {self.title} ({self.discount_percent}% off)"

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('created',  'Created'),
        ('updated',  'Updated'),
        ('deleted',  'Deleted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('booked',   'Booked'),
        ('sold',     'Sold'),
        ('login',    'Login'),
        ('logout',   'Logout'),
    ]

    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user            = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action          = models.CharField(max_length=15, choices=ACTION_CHOICES)
    model_affected  = models.CharField(max_length=100, help_text="e.g. Car, Booking, Payment")
    object_id       = models.CharField(max_length=100, blank=True)
    description     = models.TextField()
    ip_address      = models.GenericIPAddressField(blank=True, null=True)
    timestamp       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} {self.action} {self.model_affected} at {self.timestamp}"

class SupportTicket(models.Model):
    """Customer support tickets handled by customer_support role"""
    PRIORITY = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')]
    STATUS   = [('open', 'Open'), ('in_progress', 'In Progress'), ('resolved', 'Resolved'), ('closed', 'Closed')]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=20, unique=True, editable=False)
    submitted_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tickets')
    assigned_to  = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='assigned_tickets')
    subject      = models.CharField(max_length=255)
    message      = models.TextField()
    priority     = models.CharField(max_length=10, choices=PRIORITY, default='medium')
    status       = models.CharField(max_length=15, choices=STATUS, default='open')
    related_car  = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    resolved_at  = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            last = SupportTicket.objects.order_by('-created_at').first()
            num  = (int(last.ticket_number.split('-')[-1]) + 1) if last else 1
            self.ticket_number = f"TK-{timezone.now().year}-{num:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ticket {self.ticket_number}: {self.subject}"

class TicketReply(models.Model):
    ticket     = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='replies')
    replied_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message    = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply to {self.ticket.ticket_number} by {self.replied_by.full_name}"
    
    
    
    
# to add the contact form submissions from the website,
# which can be viewed and managed by admins in the dashboard. 
#   This allows customers to reach out with inquiries, feedback, or support requests directly from the site.

class SiteMessage(models.Model):
    """Model to store contact form submissions from the website"""
    STATUS_CHOICES = [
        ('unread', 'Unread'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('spam', 'Spam'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=300)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unread')
    reply_message = models.TextField(blank=True)
    replied_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='site_message_replies',
    )
    replied_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
    
    def __str__(self):
        return f"{self.name} - {self.subject[:50]}"


# ================ WHATSAPP MESSAGING MODELS ===============

class WhatsAppMessage(models.Model):
    """
    Track all WhatsApp messages sent and received for bookings, visits, and support
    """
    MESSAGE_TYPES = [
        ('booking_confirmation', 'Booking Confirmation'),
        ('visit_reminder', 'Visit Reminder'),
        ('payment_confirmation', 'Payment Confirmation'),
        ('text_reply', 'Text Reply'),
        ('custom_message', 'Custom Message'),
        ('inbound_message', 'Inbound Customer Message'),
    ]
    
    STATUS_CHOICES = [
        ('sent', 'Sent Successfully'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('read', 'Read by Recipient'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=15, help_text="Recipient WhatsApp number")
    message_type = models.CharField(max_length=30, choices=MESSAGE_TYPES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='sent')
    message_id = models.CharField(max_length=255, unique=True, null=True, blank=True, 
                                  help_text="Meta WhatsApp message ID")
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional message data (booking ID, car details, etc)")
    
    # Relations (optional - for linking to specific objects)
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='whatsapp_messages')
    visit = models.ForeignKey(VisitSchedule, on_delete=models.SET_NULL, null=True, blank=True, related_name='whatsapp_messages')
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='whatsapp_messages')
    
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'WhatsApp Message'
        verbose_name_plural = 'WhatsApp Messages'
        indexes = [
            models.Index(fields=['phone_number', '-created_at']),
            models.Index(fields=['message_type', 'status']),
        ]
    
    def __str__(self):
        return f"WhatsApp to {self.phone_number} - {self.message_type} ({self.status})"    
