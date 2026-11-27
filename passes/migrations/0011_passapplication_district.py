from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("passes", "0010_passapplication_aadhaar_document_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="passapplication",
            name="district",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]