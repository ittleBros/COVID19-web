# Generated by Django 3.0.6 on 2020-09-06 14:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Hospital',
            fields=[
                ('h_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=256)),
                ('address', models.CharField(blank=True, max_length=512, null=True)),
                ('tel', models.CharField(blank=True, max_length=20, null=True)),
                ('contact', models.CharField(blank=True, max_length=10, null=True)),
                ('username', models.CharField(max_length=15)),
                ('passwd', models.CharField(max_length=50)),
                ('mild_left', models.IntegerField(blank=True, null=True)),
                ('severe_left', models.IntegerField(blank=True, null=True)),
                ('city', models.CharField(choices=[('1', '11010011'), ('2', '10101929'), ('3', '193918433')], max_length=10, null=True)),
            ],
            options={
                'db_table': 'hospital',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Patient',
            fields=[
                ('p_id', models.AutoField(primary_key=True, serialize=False)),
                ('no', models.CharField(max_length=64)),
                ('tel', models.CharField(max_length=20)),
                ('username', models.CharField(blank=True, max_length=64, null=True)),
                ('status', models.IntegerField()),
            ],
            options={
                'db_table': 'patient',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Pstatus',
            fields=[
                ('p', models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, primary_key=True, serialize=False, to='hospital.Patient')),
                ('status', models.IntegerField()),
                ('day', models.DateField()),
            ],
            options={
                'db_table': 'pstatus',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Supplies',
            fields=[
                ('h', models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, primary_key=True, serialize=False, to='hospital.Hospital')),
                ('n95', models.IntegerField(default=0, null=True)),
                ('surgeon', models.IntegerField(default=0, null=True)),
                ('ventilator', models.IntegerField(default=0, null=True)),
                ('clothe', models.IntegerField(default=0, null=True)),
                ('glasses', models.IntegerField(default=0, null=True)),
                ('alcohol', models.IntegerField(default=0, null=True)),
                ('pants', models.IntegerField(default=0, null=True)),
            ],
            options={
                'db_table': 'supplies',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Track',
            fields=[
                ('p', models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, primary_key=True, serialize=False, to='hospital.Patient')),
                ('date_time', models.DateTimeField()),
                ('longitude', models.FloatField()),
                ('latitude', models.FloatField()),
                ('description', models.CharField(blank=True, max_length=256, null=True)),
                ('location', models.CharField(blank=True, max_length=256, null=True)),
                ('district', models.CharField(blank=True, max_length=256, null=True)),
            ],
            options={
                'db_table': 'track',
                'managed': False,
            },
        ),
    ]
