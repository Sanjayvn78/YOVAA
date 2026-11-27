from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("verification", "0009_verification_state_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="umisstudent",
            name="umis_number",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]