import secrets

from django.db import migrations

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def backfill(apps, schema_editor):
    Payment = apps.get_model("homepage", "Payment")
    for payment in Payment.objects.filter(reference_code=""):
        payment.reference_code = "OCD-" + "".join(secrets.choice(ALPHABET) for _ in range(6))
        payment.save(update_fields=["reference_code"])


class Migration(migrations.Migration):
    dependencies = [
        ("homepage", "0007_payment_bank_account_payment_payer_name_and_more"),
    ]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
