from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("verification", "0008_umisstudent_umis_number_and_state"),
    ]

    operations = [
        migrations.AddField(
            model_name="emisstudent",
            name="state",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="disabledperson",
            name="state",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="governmenttransportstaff",
            name="state",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]