# core/models.py

import datetime
from django.db import models
from django.contrib.auth.models import User

# --- Estrutura Administrativa ---

class Secretaria(models.Model):
    nome = models.CharField(max_length=200, unique=True, verbose_name="Nome da Secretaria")
    sigla = models.CharField(max_length=20, unique=True, verbose_name="Sigla")

    def __str__(self):
        return f"{self.nome} ({self.sigla})"

    class Meta:
        verbose_name = "Secretaria"
        verbose_name_plural = "Secretarias"

class Departamento(models.Model):
    secretaria = models.ForeignKey(Secretaria, on_delete=models.PROTECT, verbose_name="Secretaria")
    nome = models.CharField(max_length=200, verbose_name="Nome do Departamento")

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"


class Divisao(models.Model):
    departamento = models.ForeignKey(Departamento, on_delete=models.PROTECT, verbose_name="Departamento")
    nome = models.CharField(max_length=200, verbose_name="Nome da Divisão")

    def __str__(self):
        return self.nome
        
    class Meta:
        verbose_name = "Divisão"
        verbose_name_plural = "Divisões"

# --- Catálogo de Serviços ---

class CartaDeServicos(models.Model):
    divisao_responsavel = models.ForeignKey(Divisao, on_delete=models.PROTECT, verbose_name="Divisão Responsável")
    nome_servico = models.CharField(max_length=255, verbose_name="Nome do Serviço")
    descricao = models.TextField(verbose_name="Descrição", blank=True, null=True)
    prazo_maximo_dias = models.PositiveIntegerField(help_text="Prazo máximo em dias corridos para a conclusão do serviço.")

    def __str__(self):
        return self.nome_servico

    class Meta:
        verbose_name = "Serviço da Carta"
        verbose_name_plural = "Carta de Serviços"

class SolucaoDeOperacaoDoServico(models.Model):
    carta_de_servico = models.OneToOneField(CartaDeServicos, on_delete=models.CASCADE)
    descricao_passos = models.TextField(help_text="Descreva o passo a passo interno para executar o serviço.")
    sistemas_utilizados = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"POP para: {self.carta_de_servico.nome_servico}"

# --- Processos (A parte transacional) ---

class Processo(models.Model):
    STATUS_CHOICES = [
        ('ABERTO', 'Aberto'),
        ('EM_ANALISE', 'Em Análise'),
        ('PENDENTE', 'Pendente de Informação'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
    ]

    numero_protocolo = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Número do Protocolo")
    servico_solicitado = models.ForeignKey(CartaDeServicos, on_delete=models.PROTECT, verbose_name="Serviço Solicitado")
    solicitante = models.CharField(max_length=255, verbose_name="Solicitante")
    
    data_protocolo = models.DateTimeField(auto_now_add=True, verbose_name="Data do Protocolo")
    data_prazo = models.DateField(verbose_name="Prazo Final")
    data_conclusao = models.DateTimeField(verbose_name="Data de Conclusão", null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTO', verbose_name="Status")
    responsavel_atual = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Responsável Atual")
    detalhes_solicitacao = models.TextField(verbose_name="Detalhes da Solicitação")

    def save(self, *args, **kwargs):
        # Calcula o prazo final automaticamente se for um novo processo
        if not self.pk and self.servico_solicitado:
            self.data_prazo = datetime.date.today() + datetime.timedelta(days=self.servico_solicitado.prazo_maximo_dias)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.numero_protocolo or 'Novo Processo'} - {self.servico_solicitado.nome_servico}"

    class Meta:
        verbose_name = "Processo"
        verbose_name_plural = "Processos"