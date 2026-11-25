from django.db import migrations


def create_defaults(apps, schema_editor):
    SiteSettings = apps.get_model("homepage", "SiteSettings")
    if not SiteSettings.objects.exists():
        SiteSettings.objects.create(
            pk=1,
            site_name="On Call Driver",
            tagline="Verified cars, guided visits and secure mobile-money payments.",
            address="Kigali, Rwanda",
        )


class Migration(migrations.Migration):
    dependencies = [("homepage", "0008_backfill_payment_reference_codes")]
    operations = [migrations.RunPython(create_defaults, migrations.RunPython.noop)]
