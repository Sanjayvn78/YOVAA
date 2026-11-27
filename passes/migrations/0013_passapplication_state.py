from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("passes", "0012_passapplication_address_proof_document_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="passapplication",
            name="state",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]