from django.db import migrations

# Alertas gerados automaticamente por nível de água crítico eram gravados com nível "alto".
# A partir de agora eles usam "critico"; esta migração alinha os alertas antigos.
PREFIXOS = ('Nível de água crítico detectado', 'Nivel de agua critico')


def alto_para_critico(apps, schema_editor):
    Alerta = apps.get_model('monitoramento', 'Alerta')
    for prefixo in PREFIXOS:
        Alerta.objects.filter(nivel='alto', mensagem__startswith=prefixo).update(nivel='critico')


def critico_para_alto(apps, schema_editor):
    Alerta = apps.get_model('monitoramento', 'Alerta')
    for prefixo in PREFIXOS:
        Alerta.objects.filter(nivel='critico', mensagem__startswith=prefixo).update(nivel='alto')


class Migration(migrations.Migration):

    dependencies = [
        ('monitoramento', '0009_textos_em_portugues'),
    ]

    operations = [
        migrations.RunPython(alto_para_critico, critico_para_alto),
    ]
