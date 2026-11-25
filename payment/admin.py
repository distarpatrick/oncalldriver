from django.contrib import admin

from .models import BankAccount


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("bank_name", "account_name", "account_number", "currency", "is_active", "display_order")
    list_editable = ("is_active", "display_order")
    search_fields = ("bank_name", "account_name", "account_number")
