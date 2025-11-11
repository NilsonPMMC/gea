# /var/www/gea/core/views.py

from django.shortcuts import render
from django.db.models import Count
from django.utils import timezone
from .models import Processo, Secretaria, CartaDeServicos
import datetime
import json
from django.db.models import Q

def dashboard_view(request):
    # --- KPIs Principais ---
    hoje = timezone.now().date()
    processos_abertos_query = Processo.objects.filter(status__in=['ABERTO', 'EM_ANALISE', 'PENDENTE'])
    
    total_processos_abertos = processos_abertos_query.count()
    total_processos_atrasados = processos_abertos_query.filter(data_prazo__lt=hoje).count()
    
    # --- Dados para Gráficos ---
    # Gráfico de Pizza: Processos por Status
    status_counts = processos_abertos_query.values('status').annotate(total=Count('status')).order_by('status')
    status_data = {
        'labels': [item['status'] for item in status_counts],
        'data': [item['total'] for item in status_counts],
    }

    # Gráfico de Barras: Carga por Secretaria
    carga_secretarias = processos_abertos_query.values(
        'servico_solicitado__divisao_responsavel__departamento__secretaria__sigla'
    ).annotate(total=Count('id')).order_by('-total')[:5] # Top 5
    carga_secretarias_data = {
        'labels': [item['servico_solicitado__divisao_responsavel__departamento__secretaria__sigla'] for item in carga_secretarias],
        'data': [item['total'] for item in carga_secretarias],
    }

    # --- Dados para Tabelas ---
    processos_criticos = processos_abertos_query.filter(
        data_prazo__gte=hoje, 
        data_prazo__lte=hoje + datetime.timedelta(days=7)
    ).order_by('data_prazo')[:5]

    atividade_recente = Processo.objects.order_by('-data_protocolo')[:5]

    context = {
        'total_processos_abertos': total_processos_abertos,
        'total_processos_atrasados': total_processos_atrasados,
        'status_data_json': json.dumps(status_data), # Usamos json.dumps para passar para o JavaScript
        'carga_secretarias_data_json': json.dumps(carga_secretarias_data),
        'processos_criticos': processos_criticos,
        'atividade_recente': atividade_recente,
    }
    
    return render(request, 'core/dashboard.html', context)

def analise_servicos_view(request):
    # 1. Contagem total de serviços
    total_servicos = CartaDeServicos.objects.count()

    # 2. Contagem de serviços "Não Sistematizados" (Manual)
    # Definimos "manual" como qualquer forma de solicitação que não seja um sistema digital
    filtros_manuais = Q(forma_solicitacao__icontains='Presencial') | \
                      Q(forma_solicitacao__icontains='Telefone') | \
                      Q(forma_solicitacao__icontains='Whatsapp') | \
                      Q(forma_solicitacao__icontains='E-mail') | \
                      Q(forma_solicitacao__isnull=True) | \
                      Q(forma_solicitacao__exact='')

    total_nao_sistematizados = CartaDeServicos.objects.filter(filtros_manuais).count()

    # 3. Gráfico: Contagem por Secretaria (Top 10)
    por_secretaria = CartaDeServicos.objects.values(
        'divisao_responsavel__departamento__secretaria__sigla'
    ).annotate(total=Count('id')).order_by('-total')[:10]

    por_secretaria_data = {
        'labels': [s['divisao_responsavel__departamento__secretaria__sigla'] for s in por_secretaria],
        'data': [s['total'] for s in por_secretaria],
    }

    # 4. Gráfico: Próprio vs. Terceirizado
    por_tipo_sistema = CartaDeServicos.objects.exclude(
        tipo_sistema__isnull=True
    ).exclude(
        tipo_sistema__exact=''
    ).values('tipo_sistema').annotate(total=Count('id')).order_by('tipo_sistema')

    por_tipo_sistema_data = {
        'labels': [t['tipo_sistema'] for t in por_tipo_sistema],
        'data': [t['total'] for t in por_tipo_sistema],
    }

    # 5. Gráfico: Sistema Operante (Top 10)
    # Filtra para não incluir os manuais, focando apenas nos sistemas
    por_sistema_operante = CartaDeServicos.objects.exclude(filtros_manuais).values(
        'forma_solicitacao'
    ).annotate(total=Count('id')).order_by('-total')[:10]

    por_sistema_operante_data = {
        'labels': [s['forma_solicitacao'] for s in por_sistema_operante],
        'data': [s['total'] for s in por_sistema_operante],
    }

    context = {
        'total_servicos': total_servicos,
        'total_nao_sistematizados': total_nao_sistematizados,
        'por_secretaria_json': json.dumps(por_secretaria_data),
        'por_tipo_sistema_json': json.dumps(por_tipo_sistema_data),
        'por_sistema_operante_json': json.dumps(por_sistema_operante_data),
    }

    return render(request, 'core/analise_servicos.html', context)