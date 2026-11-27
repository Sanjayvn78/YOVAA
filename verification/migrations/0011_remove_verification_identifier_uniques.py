from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("verification", "0010_remove_umisstudent_umis_number_unique"),
    ]

    operations = [
        migrations.AlterField(
            model_name="emisstudent",
            name="student_id",
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name="disabledperson",
            name="disability_id",
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name="governmenttransportstaff",
            name="staff_number",
            field=models.CharField(max_length=50),
        ),
    ]