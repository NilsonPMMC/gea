# /var/www/gea/core/admin.py

from django.contrib import admin
from .models import Secretaria, Departamento, Divisao, CartaDeServicos, SolucaoDeOperacaoDoServico, Processo

class SolucaoDeOperacaoDoServicoInline(admin.StackedInline):
    model = SolucaoDeOperacaoDoServico
    can_delete = False  # Não permite deletar o inline, apenas editar
    verbose_name_plural = 'Solução de Operação do Serviço (POP)'

# Para uma visualização mais rica, usamos o ModelAdmin
@admin.register(Secretaria)
class SecretariaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sigla')
    search_fields = ('nome', 'sigla')

@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'secretaria')
    list_filter = ('secretaria',)
    search_fields = ('nome',)

@admin.register(Divisao)
class DivisaoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'departamento')
    list_filter = ('departamento__secretaria', 'departamento')
    search_fields = ('nome',)

@admin.register(CartaDeServicos)
class CartaDeServicosAdmin(admin.ModelAdmin):
    list_display = ('nome_servico', 'divisao_responsavel', 'prazo_maximo_dias')
    list_filter = ('divisao_responsavel',)
    search_fields = ('nome_servico',)
    inlines = [SolucaoDeOperacaoDoServicoInline]

@admin.register(Processo)
class ProcessoAdmin(admin.ModelAdmin):
    # Campos que aparecerão na lista de processos
    list_display = ('numero_protocolo', 'servico_solicitado', 'status', 'data_prazo', 'responsavel_atual')
    
    # Filtros que aparecerão na barra lateral direita
    list_filter = ('status', 'servico_solicitado__divisao_responsavel', 'data_prazo')
    
    # Campos pelos quais você poderá pesquisar
    search_fields = ('numero_protocolo', 'solicitante')
    
    # Campos que não podem ser editados (são automáticos)
    readonly_fields = ('data_protocolo', 'data_prazo')
    
    # Para organizar os campos no formulário de edição
    fieldsets = (
        ('Informações Gerais', {
            'fields': ('numero_protocolo', 'servico_solicitado', 'solicitante', 'status', 'responsavel_atual')
        }),
        ('Datas', {
            'fields': ('data_protocolo', 'data_prazo', 'data_conclusao')
        }),
        ('Detalhes', {
            'fields': ('detalhes_solicitacao',)
        }),
    )