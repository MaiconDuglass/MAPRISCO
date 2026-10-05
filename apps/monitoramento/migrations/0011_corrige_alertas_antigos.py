from django.db import migrations

# Alertas gravados por versões antigas do sistema:
# - usavam o nível "alerta", que não existe entre as opções (baixo, médio, alto, crítico);
# - tinham mensagens sem acentuação.
MENSAGENS = {
    'Nivel de agua critico! Evacuacao pode ser necessaria.': 'Nível de água crítico! Evacuação pode ser necessária.',
    'Nivel de agua em alerta. Monitoramento intensificado.': 'Nível de água em alerta. Monitoramento intensificado.',
    'Situacao normal. Sem risco imediato.': 'Situação normal. Sem risco imediato.',
}


def corrigir(apps, schema_editor):
    Alerta = apps.get_model('monitoramento', 'Alerta')
    Alerta.objects.filter(nivel='alerta').update(nivel='medio')
    for antiga, nova in MENSAGENS.items():
        Alerta.objects.filter(mensagem=antiga).update(mensagem=nova)


class Migration(migrations.Migration):

    dependencies = [
        ('monitoramento', '0010_alertas_automaticos_critico'),
    ]

    operations = [
        migrations.RunPython(corrigir, migrations.RunPython.noop),
    ]
