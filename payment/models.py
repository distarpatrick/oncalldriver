from django.db import models


class BankAccount(models.Model):
    """A company bank account customers can pay into by transfer or deposit."""

    bank_name = models.CharField(max_length=100, help_text="e.g. Bank of Kigali, Equity Bank, I&M Bank")
    account_name = models.CharField(max_length=150)
    account_number = models.CharField(max_length=50)
    branch = models.CharField(max_length=100, blank=True)
    swift_code = models.CharField(max_length=20, blank=True, help_text="Needed for international transfers")
    currency = models.CharField(max_length=5, default="RWF")
    brand_color = models.CharField(
        max_length=7, blank=True, default="#1e5eff",
        help_text="Hex colour used for this bank's badge on the checkout page",
    )
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "bank_name"]

    def __str__(self):
        return f"{self.bank_name} — {self.account_number}"

    @property
    def initials(self):
        words = [w for w in self.bank_name.replace("&", " ").split() if w[:1].isalpha()]
        return "".join(w[0] for w in words[:2]).upper() or "BK"
