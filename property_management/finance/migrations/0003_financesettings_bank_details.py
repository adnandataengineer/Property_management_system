from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0002_financesettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='financesettings',
            name='reminder_lead_days',
            field=models.PositiveIntegerField(default=10, help_text='Days before the rent due date to email the invoice and payment details.'),
        ),
        migrations.AddField(
            model_name='financesettings',
            name='bank_account_name',
            field=models.CharField(blank=True, default='', help_text='Account holder / beneficiary name', max_length=200),
        ),
        migrations.AddField(
            model_name='financesettings',
            name='bank_name',
            field=models.CharField(blank=True, default='', help_text='Name of the bank', max_length=200),
        ),
        migrations.AddField(
            model_name='financesettings',
            name='bank_iban',
            field=models.CharField(blank=True, default='', help_text='IBAN', max_length=64),
        ),
        migrations.AddField(
            model_name='financesettings',
            name='bank_bic',
            field=models.CharField(blank=True, default='', help_text='BIC / SWIFT code', max_length=32),
        ),
        migrations.AddField(
            model_name='financesettings',
            name='bank_account_number',
            field=models.CharField(blank=True, default='', help_text='Account number (optional)', max_length=64),
        ),
        migrations.AddField(
            model_name='financesettings',
            name='bank_sort_code',
            field=models.CharField(blank=True, default='', help_text='Sort code (optional)', max_length=32),
        ),
        migrations.AddField(
            model_name='financesettings',
            name='payment_reference_note',
            field=models.CharField(blank=True, default='Please use your full name and room as the payment reference.', help_text='Instruction shown to the tenant for the transfer reference.', max_length=255),
        ),
    ]
