from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitoramento', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='arearisco',
            name='bairro',
            field=models.CharField(blank=True, help_text='Neighborhood where the area is located', max_length=100),
        ),
        migrations.AddField(
            model_name='arearisco',
            name='foto',
            field=models.FileField(blank=True, help_text='Optional image or file', null=True, upload_to='areas/'),
        ),
    ]
