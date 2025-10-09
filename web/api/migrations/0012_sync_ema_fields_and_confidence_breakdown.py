# Generated manually to sync existing database fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_indicator_adx_marketregime_tradingsignal'),
    ]

    operations = [
        # All these fields already exist in database, only update Django's migration state
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # No database changes needed - all fields already exist
            ],
            state_operations=[
                migrations.AddField(
                    model_name='indicator',
                    name='ema_high_33',
                    field=models.DecimalField(decimal_places=8, max_digits=18, null=True),
                ),
                migrations.AddField(
                    model_name='indicator',
                    name='ema_low_33',
                    field=models.DecimalField(decimal_places=8, max_digits=18, null=True),
                ),
                migrations.AddField(
                    model_name='tradingsignal',
                    name='confidence_breakdown',
                    field=models.JSONField(blank=True, null=True),
                ),
            ],
        ),
    ]

