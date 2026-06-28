from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0011_bookingrequest_agreement_sent_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookingrequest',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
    ]
