from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='MetaAdSpend',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('account_id', models.CharField(max_length=100)),
                ('account_name', models.CharField(max_length=255)),
                ('campaign_id', models.CharField(max_length=100, null=True)),
                ('campaign_name', models.CharField(max_length=255, null=True)),
                ('spend', models.DecimalField(decimal_places=2, max_digits=10)),
                ('impressions', models.IntegerField()),
                ('clicks', models.IntegerField()),
                ('ctr', models.DecimalField(decimal_places=2, max_digits=5)),
                ('cpc', models.DecimalField(decimal_places=2, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Meta Ad Spend',
                'verbose_name_plural': 'Meta Ad Spend',
            },
        ),
        migrations.AddIndex(
            model_name='metaadspend',
            index=models.Index(fields=['date', 'account_id'], name='meta_metaad_date_ac_idx'),
        ),
        migrations.AddIndex(
            model_name='metaadspend',
            index=models.Index(fields=['account_name'], name='meta_metaad_account_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='metaadspend',
            unique_together={('date', 'account_id', 'campaign_id')},
        ),
    ] 