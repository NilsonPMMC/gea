# /var/www/gea/core/admin.py

from django.contrib import admin
from django.utils import timezone
from .models import (
    Entidade, Secretaria, Departamento, Divisao, 
    CartaDeServicos, Processo
)

# --- INLINES ---

class DepartamentoInline(admin.TabularInline):
    model = Departamento
    extra = 1

# --- MODEL ADMINS ---

@admin.register(Entidade)
class EntidadeAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)

@admin.register(Secretaria)
class SecretariaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sigla')
    search_fields = ('nome', 'sigla')
    inlines = [DepartamentoInline]

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
    # 4. ATUALIZAMOS O ADMIN DA CARTA DE SERVIÇOS
    list_display = ('nome_servico', 'entidade', 'forma_solicitacao', 'tipo_sistema')
    list_filter = ('entidade', 'forma_solicitacao', 'tipo_sistema', 'divisao_responsavel__departamento__secretaria')
    search_fields = ('nome_servico', 'orgao_responsavel')
    # Removemos o inline antigo
    inlines = [] 

@admin.register(Processo)
class ProcessoAdmin(admin.ModelAdmin):
    list_display = ('numero_protocolo', 'servico_solicitado', 'status', 'data_prazo', 'responsavel_atual', 'dias_em_aberto')
    list_filter = ('status', 'servico_solicitado__divisao_responsavel__departamento__secretaria', 'data_prazo')
    search_fields = ('numero_protocolo', 'solicitante', 'responsavel_atual__username')
    readonly_fields = ('data_protocolo', 'data_prazo')
    date_hierarchy = 'data_protocolo'
    actions = ['marcar_como_concluido']

    fieldsets = (
        ('Informações Gerais', {
            'fields': ('numero_protocolo', 'servico_solicitado', 'solicitante', 'status', 'responsavel_atual')
        }),
        ('Localização (GIS)', {
            'fields': ('localizacao',)
        }),
        ('Datas', {
            'fields': ('data_protocolo', 'data_prazo', 'data_conclusao')
        }),
        ('Detalhes', {
            'fields': ('detalhes_solicitacao',)
        }),
    )

    @admin.display(description='Dias em Aberto')
    def dias_em_aberto(self, obj):
        if obj.status != 'CONCLUIDO' and obj.data_protocolo:
            return (timezone.now() - obj.data_protocolo).days
        return "-"

    @admin.action(description='Marcar processos selecionados como Concluído')
    def marcar_como_concluido(self, request, queryset):
        queryset.update(status='CONCLUIDO', data_conclusao=timezone.now())
        self.message_user(request, f"{queryset.count()} processos foram marcados como concluídos.")