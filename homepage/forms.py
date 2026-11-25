import re
from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Booking, VisitSchedule, Payment, CarReview, CarComment

from .models import SiteSettings
from .models import Car, CompanyCarOwner

User = get_user_model()


FIELD_CLASS = "auth-input"
SELECT_CLASS = "auth-input auth-select"
UPLOAD_FIELD_CLASS = "upload-input"
UPLOAD_SELECT_CLASS = "upload-input upload-select"


def normalize_rwanda_phone(phone):
    """Accept 07XXXXXXXX, 2507XXXXXXXX or +2507XXXXXXXX and return +2507XXXXXXXX."""
    phone = re.sub(r"[\s\-().]", "", phone or "")
    if not phone:
        raise ValidationError("Phone number is required.")
    if phone.startswith("00250"):
        phone = "+" + phone[2:]
    elif phone.startswith("250"):
        phone = "+" + phone
    elif phone.startswith("07"):
        phone = "+250" + phone[1:]
    if not re.fullmatch(r"\+2507\d{8}", phone):
        raise ValidationError("Enter a valid Rwandan mobile number, e.g. 078 123 4567 or +250 78 123 4567.")
    return phone


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": FIELD_CLASS, "placeholder": "Email address"})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": FIELD_CLASS, "placeholder": "Password"})
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("Please enter a correct email and password.")
            if not self.user_cache.is_active:
                raise forms.ValidationError("This account is inactive.")
        return cleaned_data

    def get_user(self):
        return self.user_cache


class CustomerRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("full_name", "email", "phone", "province", "district", "password1", "password2")
        widgets = {
            "full_name": forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "Full name"}),
            "email": forms.EmailInput(attrs={"class": FIELD_CLASS, "placeholder": "Email address"}),
            "phone": forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "+250XXXXXXXXX"}),
            "province": forms.Select(attrs={"class": SELECT_CLASS}),
            "district": forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "District"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["province"].required = False
        self.fields["password1"].widget.attrs.update({"class": FIELD_CLASS, "placeholder": "Password"})
        self.fields["password2"].widget.attrs.update({"class": FIELD_CLASS, "placeholder": "Confirm password"})

    def clean_phone(self):
        return normalize_rwanda_phone(self.cleaned_data.get("phone"))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "customer"
        user.is_staff = False
        if commit:
            user.save()
        return user


class StaffCreationForm(UserCreationForm):
    STAFF_ROLE_CHOICES = [
        ("manager", "Manager"),
        ("marketer", "Marketer / Online Marketer"),
        ("sales_agent", "Sales Agent"),
        ("accountant", "Accountant"),
        ("inventory_manager", "Inventory Manager"),
        ("customer_support", "Customer Support"),
    ]

    role = forms.ChoiceField(choices=STAFF_ROLE_CHOICES, widget=forms.Select(attrs={"class": SELECT_CLASS}))

    class Meta:
        model = User
        fields = ("full_name", "email", "phone", "role", "province", "district", "password1", "password2")
        widgets = {
            "full_name": forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "Full name"}),
            "email": forms.EmailInput(attrs={"class": FIELD_CLASS, "placeholder": "Email address"}),
            "phone": forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "+250XXXXXXXXX"}),
            "province": forms.Select(attrs={"class": SELECT_CLASS}),
            "district": forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "District"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["province"].required = False
        self.fields["password1"].widget.attrs.update({"class": FIELD_CLASS, "placeholder": "Password"})
        self.fields["password2"].widget.attrs.update({"class": FIELD_CLASS, "placeholder": "Confirm password"})

    def clean_phone(self):
        return normalize_rwanda_phone(self.cleaned_data.get("phone"))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data["role"]
        user.is_staff = True
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("full_name", "email", "phone", "profile_photo", "province", "district")
        widgets = {
            "full_name": forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "Full name"}),
            "email": forms.EmailInput(attrs={"class": FIELD_CLASS, "placeholder": "Email address"}),
            "phone": forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "+250XXXXXXXXX"}),
            "profile_photo": forms.ClearableFileInput(attrs={"class": FIELD_CLASS}),
            "province": forms.Select(attrs={"class": SELECT_CLASS}),
            "district": forms.TextInput(attrs={"class": FIELD_CLASS, "placeholder": "District"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["province"].required = False

    def clean_phone(self):
        return normalize_rwanda_phone(self.cleaned_data.get("phone"))


class CompanyCarOwnerForm(forms.ModelForm):
    class Meta:
        model = CompanyCarOwner
        fields = (
            "owner_type",
            "full_name",
            "phone",
            "email",
            "national_id",
            "province",
            "district",
            "id_document",
            "commission_rate",
        )
        widgets = {
            "owner_type": forms.Select(attrs={"class": UPLOAD_SELECT_CLASS, "data-owner-type": "true"}),
            "full_name": forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "Owner full name"}),
            "phone": forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "+250XXXXXXXXX"}),
            "email": forms.EmailInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "owner@example.com"}),
            "national_id": forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "National ID"}),
            "province": forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "Province"}),
            "district": forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "District"}),
            "id_document": forms.ClearableFileInput(attrs={"class": UPLOAD_FIELD_CLASS}),
            "commission_rate": forms.NumberInput(attrs={"class": UPLOAD_FIELD_CLASS, "step": "0.01", "min": "0"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        owner_type = cleaned_data.get("owner_type")

        if owner_type == "citizen":
            for field in ("full_name", "phone", "national_id", "province", "district"):
                if not cleaned_data.get(field):
                    self.add_error(field, "This field is required for citizen consignment cars.")
        return cleaned_data


class CarUploadForm(forms.ModelForm):
    brand_name = forms.CharField(
        label="Brand",
        max_length=100,
        widget=forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "Toyota"}),
    )

    class Meta:
        model = Car
        fields = (
            "title",
            "model",
            "year",
            "condition",
            "mileage_km",
            "color",
            "engine_size_cc",
            "transmission",
            "fuel_type",
            "drive_type",
            "seats",
            "doors",
            "stock_number",
            "registration_plate",
            "price",
            "is_negotiable",
            "scheduling_fee",
            "province",
            "district",
            "exact_location",
            "description",
            "features_summary",
            "is_featured",
        )
        widgets = {
            "title": forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "Toyota RAV4 2026"}),
            "model": forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "RAV4"}),
            "year": forms.NumberInput(attrs={"class": UPLOAD_FIELD_CLASS, "min": "1900", "max": "2100"}),
            "condition": forms.Select(attrs={"class": UPLOAD_SELECT_CLASS}),
            "mileage_km": forms.NumberInput(attrs={"class": UPLOAD_FIELD_CLASS, "min": "0"}),
            "color": forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "Pearl white"}),
            "engine_size_cc": forms.NumberInput(attrs={"class": UPLOAD_FIELD_CLASS, "min": "0", "placeholder": "1500"}),
            "transmission": forms.Select(attrs={"class": UPLOAD_SELECT_CLASS}),
            "fuel_type": forms.Select(attrs={"class": UPLOAD_SELECT_CLASS}),
            "drive_type": forms.Select(attrs={"class": UPLOAD_SELECT_CLASS}),
            "seats": forms.NumberInput(attrs={"class": UPLOAD_FIELD_CLASS, "min": "1"}),
            "doors": forms.NumberInput(attrs={"class": UPLOAD_FIELD_CLASS, "min": "1"}),
            "stock_number": forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "OCD-0001"}),
            "registration_plate": forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "RAA 001 A"}),
            "price": forms.NumberInput(attrs={"class": UPLOAD_FIELD_CLASS, "min": "0", "step": "0.01"}),
            "is_negotiable": forms.CheckboxInput(attrs={"class": "upload-checkbox"}),
            "scheduling_fee": forms.NumberInput(attrs={"class": UPLOAD_FIELD_CLASS, "min": "0", "step": "0.01"}),
            "province": forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "Kigali City"}),
            "district": forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "Gasabo"}),
            "exact_location": forms.TextInput(attrs={"class": UPLOAD_FIELD_CLASS, "placeholder": "Showroom or parking location"}),
            "description": forms.Textarea(attrs={"class": UPLOAD_FIELD_CLASS, "rows": 5, "placeholder": "Describe condition, inspection notes, and selling points"}),
            "features_summary": forms.Textarea(attrs={"class": UPLOAD_FIELD_CLASS, "rows": 3, "placeholder": "GPS, backup camera, leather seats"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "upload-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["drive_type"].required = False
        self.fields["registration_plate"].required = True


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(file_data, initial) for file_data in data]
        return [single_file_clean(data, initial)]


class MultipleImageField(MultipleFileField, forms.ImageField):
    pass


class CarMediaUploadForm(forms.Form):
    photos = MultipleImageField(
        required=True,
        widget=MultipleFileInput(attrs={"class": UPLOAD_FIELD_CLASS, "accept": "image/*", "multiple": True}),
        help_text="Upload at least 3 car photos. The first selected photo becomes the cover image.",
    )
    videos = MultipleFileField(
        required=True,
        widget=MultipleFileInput(attrs={"class": UPLOAD_FIELD_CLASS, "accept": "video/*", "multiple": True}),
        help_text="Upload at least 1 video.",
    )

    def clean_photos(self):
        photos = self.cleaned_data["photos"]
        if len(photos) < 3:
            raise forms.ValidationError("Upload at least 3 photos for this car.")
        return photos

    def clean_videos(self):
        videos = self.cleaned_data["videos"]
        if len(videos) < 1:
            raise forms.ValidationError("Upload at least 1 video for this car.")
        return videos
    


class BookingForm(forms.Form):
    """
    Form for customers to book a car directly from the listing page.
    Handles both full and half payment options.
    """
    PAYMENT_TYPE_CHOICES = [
        ('full', 'Full Payment'),
        ('half', 'Half Payment (50%)'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('mtn_momo', 'MTN Mobile Money'),
        ('airtel_money', 'Airtel Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash (In Person)'),
    ]

    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Jean-Pierre Uwimana',
        })
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+250 7XX XXX XXX',
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'you@example.com',
        })
    )
    payment_type = forms.ChoiceField(
        choices=PAYMENT_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'payment-radio'}),
        initial='full',
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    payment_receipt = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-input',
            'accept': 'image/*',
        }),
        label='Upload payment screenshot',
        help_text='Upload your MTN, bank transfer, or mobile money receipt to help staff verify payment faster.',
    )

    def clean_payment_receipt(self):
        receipt = self.cleaned_data.get('payment_receipt')
        if receipt and receipt.size > 5 * 1024 * 1024:
            raise ValidationError('Receipt image must be 5 MB or smaller.')
        return receipt
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Any special requests or questions…',
            'rows': 3,
        })
    )
    driver_needed = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        label='I need a driver to deliver the car',
    )

    def clean_phone(self):
        return normalize_rwanda_phone(self.cleaned_data.get("phone"))


class VisitScheduleForm(forms.Form):
    """
    Form for customers to schedule a physical visit to see a car.
    Multiple customers can schedule visits to the same car simultaneously.
    """
    PAYMENT_METHOD_CHOICES = [
        ('mtn_momo', 'MTN Mobile Money'),
        ('airtel_money', 'Airtel Money'),
        ('cash', 'Cash'),
    ]

    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Your full name',
        })
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+250 7XX XXX XXX',
        })
    )
    visit_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-input',
            'type': 'date',
        })
    )
    visit_time = forms.TimeField(
        widget=forms.TimeInput(attrs={
            'class': 'form-input',
            'type': 'time',
        })
    )
    district = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Where you\'d like to meet',
        })
    )
    fee_payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'placeholder': 'Additional notes…',
            'rows': 2,
        })
    )

    def clean_phone(self):
        return normalize_rwanda_phone(self.cleaned_data.get("phone"))

    def clean_visit_date(self):
        visit_date = self.cleaned_data.get('visit_date')
        if visit_date and visit_date < timezone.now().date():
            raise ValidationError('Visit date must be in the future.')
        return visit_date


class CarSearchForm(forms.Form):
    """
    Main search/filter form for the car listing page.
    All fields are optional — used for GET-based filtering.
    """
    FUEL_CHOICES = [
        ('', 'All Fuels'),
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
    ]
    TRANSMISSION_CHOICES = [
        ('', 'All Transmissions'),
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
        ('cvt', 'CVT'),
    ]
    PROVINCE_CHOICES = [
        ('', 'All Provinces'),
        ('kigali', 'Kigali City'),
        ('northern', 'Northern Province'),
        ('southern', 'Southern Province'),
        ('eastern', 'Eastern Province'),
        ('western', 'Western Province'),
    ]
    SORT_CHOICES = [
        ('newest', 'Newest First'),
        ('price_asc', 'Price: Low → High'),
        ('price_desc', 'Price: High → Low'),
        ('popular', 'Most Viewed'),
        ('rating', 'Top Rated'),
    ]

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'search-input',
            'id': 'searchInput',
            'placeholder': 'Search brand, model, year…',
        })
    )
    brand = forms.CharField(
        required=False,
        widget=forms.Select(attrs={
            'class': 'filter-select',
            'id': 'filterBrand',
        })
    )
    fuel = forms.ChoiceField(
        required=False,
        choices=FUEL_CHOICES,
        widget=forms.Select(attrs={
            'class': 'filter-select',
            'id': 'filterFuel',
        })
    )
    transmission = forms.ChoiceField(
        required=False,
        choices=TRANSMISSION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'filter-select',
            'id': 'filterTransmission',
        })
    )
    province = forms.ChoiceField(
        required=False,
        choices=PROVINCE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'filter-select',
            'id': 'filterProvince',
        })
    )
    sort = forms.ChoiceField(
        required=False,
        choices=SORT_CHOICES,
        initial='newest',
        widget=forms.Select(attrs={
            'class': 'filter-select',
            'id': 'sortSelect',
        })
    )
    price_min = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'price-input',
            'id': 'priceMin',
            'placeholder': 'Min',
        })
    )
    price_max = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'price-input',
            'id': 'priceMax',
            'placeholder': 'Max',
        })
    )
    # Sidebar checkboxes
    show_available = forms.BooleanField(required=False, initial=True)
    show_scheduled = forms.BooleanField(required=False, initial=True)
    drive = forms.MultipleChoiceField(
        required=False,
        choices=[('fwd', 'FWD'), ('rwd', 'RWD'), ('awd', 'AWD'), ('4wd', '4WD')],
        widget=forms.CheckboxSelectMultiple(),
    )
    negotiable = forms.BooleanField(required=False)
    featured = forms.BooleanField(required=False)


class CarReviewForm(forms.ModelForm):
    """Star rating + written review — one per customer per car"""
    class Meta:
        model = CarReview
        fields = ['rating', 'title', 'body']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 1,
                'max': 5,
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Summary of your experience',
            }),
            'body': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Tell others about this car…',
                'rows': 4,
            }),
        }


class CarCommentForm(forms.ModelForm):
    """Public comment on a car listing"""
    class Meta:
        model = CarComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Leave a comment or question about this car…',
                'rows': 3,
            }),
        }    
        
     #help admin to set logo, contact info, social links, and other site-wide settings from the admin dashboard   
class SiteSettingsForm(forms.ModelForm):
    """Form for managing site settings (logo, contact info, social links, etc.)"""
    
    class Meta:
        model = SiteSettings
        fields = [
            'site_name',
            'site_logo',
            'hero_banner',
            'tagline',
            'contact_phone',
            'contact_email',
            'address',
            'facebook_url',
            'instagram_url',
            'twitter_url',
            'youtube_url',
            'whatsapp_number',
            'payment_phone',
            'payment_mtn_code',
            'payment_account',
            'payment_account_name',
            'default_scheduling_fee',
            'half_payment_percent',
            'commission_rate',
        ]
        widgets = {
            'site_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., On Call Driver'
            }),
            'tagline': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your catchy tagline here'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+250 788 123 456'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'info@example.com'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kigali, Rwanda'
            }),
            'whatsapp_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '250788123456 (without +)'
            }),
            'payment_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+250 792 456 127'
            }),
            'payment_mtn_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1159490'
            }),
            'payment_account': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '123456789'
            }),
            'payment_airtel_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+250 73X XXX XXX'
            }),
            'payment_account_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'OnCall Driver'
            }),
            'facebook_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://facebook.com/yourpage'
            }),
            'instagram_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://instagram.com/yourhandle'
            }),
            'twitter_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://twitter.com/yourhandle'
            }),
            'youtube_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://youtube.com/yourchannel'
            }),
            'default_scheduling_fee': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1000',
                'min': '0'
            }),
            'half_payment_percent': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '5',
                'min': '0',
                'max': '100'
            }),
            'commission_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0',
                'max': '100'
            }),
        }
        help_texts = {
            'site_logo': 'Recommended size: 200x60px. Formats: PNG, JPG, SVG',
            'hero_banner': 'Recommended size: 1920x800px. Will be used as homepage hero background.',
            'whatsapp_number': 'Enter numbers only, without + or spaces (e.g., 250788123456)',
            'payment_phone': 'Payment phone number shown to customers',
            'payment_mtn_code': 'MTN payment code or shortcode shown to customers',
            'payment_account': 'Account number shown to customers',
            'payment_account_name': 'Account holder name shown to customers',
            'default_scheduling_fee': 'Default fee in RWF for scheduling a car visit',
            'half_payment_percent': 'Percentage of total price required for half payment',
            'commission_rate': 'Company commission percentage on citizen car sales',
        }
    
    def clean_whatsapp_number(self):
        """Clean WhatsApp number to remove any non-digit characters"""
        number = self.cleaned_data.get('whatsapp_number', '')
        if number:
            # Remove any non-digit characters
            import re
            number = re.sub(r'\D', '', number)
            # Remove leading '250' if present (Rwanda code) for storage
            if number.startswith('250') and len(number) > 9:
                number = number[3:]
        return number
    
    def clean_half_payment_percent(self):
        """Validate half payment percentage"""
        percent = self.cleaned_data.get('half_payment_percent', 50)
        if percent < 0 or percent > 100:
            raise forms.ValidationError('Percentage must be between 0 and 100')
        return percent
    
    def clean_commission_rate(self):
        """Validate commission rate"""
        rate = self.cleaned_data.get('commission_rate', 5)
        if rate < 0 or rate > 100:
            raise forms.ValidationError('Commission rate must be between 0 and 100')
        return rate        
