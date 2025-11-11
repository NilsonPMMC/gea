# /var/www/gea/core/models.py

import datetime
from django.db import models
from django.contrib.auth.models import User
from django.contrib.gis.db import models as gis_models

# --- NOVA TABELA (Conforme sua sugestão) ---
class Entidade(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Entidade")

    def __str__(self):
        return self.nome
    class Meta:
        verbose_name = "Entidade"
        verbose_name_plural = "Entidades"

# --- Estrutura Administrativa (Permanece Igual) ---
class Secretaria(models.Model):
    nome = models.CharField(max_length=200, unique=True, verbose_name="Nome da Secretaria")
    sigla = models.CharField(max_length=20, unique=True, verbose_name="Sigla")
    def __str__(self): return f"{self.nome} ({self.sigla})"
    class Meta:
        verbose_name = "Secretaria"
        verbose_name_plural = "Secretarias"

class Departamento(models.Model):
    secretaria = models.ForeignKey(Secretaria, on_delete=models.PROTECT, verbose_name="Secretaria")
    nome = models.CharField(max_length=200, verbose_name="Nome do Departamento")
    def __str__(self): return self.nome
    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"

class Divisao(models.Model):
    departamento = models.ForeignKey(Departamento, on_delete=models.PROTECT, verbose_name="Departamento")
    nome = models.CharField(max_length=200, verbose_name="Nome da Divisão")
    def __str__(self): return self.nome
    class Meta:
        verbose_name = "Divisão"
        verbose_name_plural = "Divisões"

# --- Catálogo de Serviços (MODELO REVISADO) ---
class CartaDeServicos(models.Model):
    divisao_responsavel = models.ForeignKey(Divisao, on_delete=models.PROTECT, verbose_name="Divisão Responsável")
    nome_servico = models.CharField(max_length=255, verbose_name="Nome do Serviço")
    descricao = models.TextField(verbose_name="Descrição", blank=True, null=True)
    prazo_maximo_dias = models.PositiveIntegerField(help_text="Prazo máximo em dias corridos.", default=30)
    
    # --- NOVOS CAMPOS (DA SUA PLANILHA) ---
    orgao_responsavel = models.CharField(max_length=200, blank=True, null=True, verbose_name="Órgão (ex: Procon)")
    tipos_atendimento = models.CharField(max_length=200, blank=True, null=True, verbose_name="Tipos de Atendimento")
    url_solicitacao = models.URLField(max_length=500, blank=True, null=True, verbose_name="Link para Solicitação")
    
    # --- CAMPO ATUALIZADO PARA FOREIGNKEY ---
    entidade = models.ForeignKey(Entidade, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Entidade")

    tipo_servico = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo (Serviço ou Informação)")
    forma_solicitacao = models.CharField(max_length=100, blank=True, null=True, verbose_name="Sistema de Origem")
    tipo_sistema = models.CharField(max_length=100, blank=True, null=True, verbose_name="Tipo do Sistema (Próprio, Terceirizado)")

    def __str__(self):
        return self.nome_servico
    class Meta:
        verbose_name = "Serviço da Carta"
        verbose_name_plural = "Carta de Serviços"


# --- Processos (Permanece Igual) ---
class Processo(models.Model):
    STATUS_CHOICES = [
        ('ABERTO', 'Aberto'),
        ('EM_ANALISE', 'Em Análise'),
        ('PENDENTE', 'Pendente de Informação'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    servico_solicitado = models.ForeignKey(CartaDeServicos, on_delete=models.PROTECT, verbose_name="Serviço Solicitado")
    numero_protocolo = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Número do Protocolo")
    solicitante = models.CharField(max_length=255, verbose_name="Solicitante")
    data_protocolo = models.DateTimeField(auto_now_add=True, verbose_name="Data do Protocolo")
    data_prazo = models.DateField(verbose_name="Prazo Final")
    data_conclusao = models.DateTimeField(verbose_name="Data de Conclusão", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTO', verbose_name="Status")
    responsavel_atual = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Responsável Atual")
    detalhes_solicitacao = models.TextField(verbose_name="Detalhes da Solicitação")
    
    localizacao = gis_models.PointField(null=True, blank=True, verbose_name="Localização Geográfica")

    def save(self, *args, **kwargs):
        if not self.pk and self.servico_solicitado:
            self.data_prazo = datetime.date.today() + datetime.timedelta(days=self.servico_solicitado.prazo_maximo_dias)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero_protocolo or 'Novo Processo'} - {self.servico_solicitado.nome_servico}"

    class Meta:
        verbose_name = "Processo"
        verbose_name_plural = "Processos"