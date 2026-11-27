from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="payment_method",
            field=models.CharField(
                choices=[("UPI", "UPI"), ("QR", "QR Code")],
                default="UPI",
                max_length=10,
            ),
        ),
    ]