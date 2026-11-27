from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("verification", "0007_rename_free_travel_eligible_governmenttransportstaff_is_eligible_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="umisstudent",
            name="state",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="umisstudent",
            name="umis_number",
            field=models.CharField(blank=True, max_length=50, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name="umisstudent",
            name="registration_number",
            field=models.CharField(max_length=50),
        ),
    ]