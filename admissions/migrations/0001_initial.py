# Generated by Django 3.1.2 on 2021-02-07 13:07

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Admission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(blank=True, null=True)),
                ('admission_closed', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Applicant',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('phone', models.CharField(blank=True, max_length=50)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('date_of_birth', models.DateField(blank=True)),
                ('study', models.CharField(blank=True, default='', max_length=100)),
                ('home_address', models.CharField(blank=True, default='', max_length=100)),
                ('town_address', models.CharField(blank=True, default='', max_length=100)),
                ('admissions', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='admissions', to='admissions.admission')),
            ],
        ),
    ]