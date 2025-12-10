import requests
import json
import time
from decouple import config
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.contrib.gis.geos import Point
from core.models import Processo, MapeamentoServicos

class Command(BaseCommand):
    help = 'Sincroniza dados via API do Colab (Carga Incremental com Dicionário de Categorias)'

    def handle(self, *args, **options):
        # 1. CREDENCIAIS
        try:
            BASE_URL = "https://api.colabapp.com/v2/integration"
            APP_ID = config('COLAB_APP_ID')
            API_KEY = config('COLAB_API_KEY')
            USER_TOKEN = config('COLAB_USER_TOKEN')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro no .env: {e}"))
            return

        headers = {
            'x-colab-application-id': APP_ID,
            'x-colab-rest-api-key': API_KEY,
            'x-colab-admin-user-auth-ticket': USER_TOKEN,
            'Content-Type': 'application/json'
        }

        # 2. PRÉ-CARREGAR CATEGORIAS (O "DICIONÁRIO")
        self.stdout.write("Baixando lista de Categorias para criar dicionário de IDs...")
        try:
            cat_resp = requests.get(f"{BASE_URL}/categories", headers=headers)
            if cat_resp.status_code == 200:
                cat_data = cat_resp.json()
                # O JSON vem como {'categories': [{'id': 1, 'name': 'X'}, ...]}
                lista_cats = cat_data.get('categories', [])
                # Cria um dicionário { ID : "NOME" }
                self.category_map_dict = {}
                for c in lista_cats:
                    if c.get('name'):
                        # Remove espaços do início e fim
                        self.category_map_dict[c['id']] = c['name'].strip()
                self.stdout.write(self.style.SUCCESS(f"Dicionário criado com {len(self.category_map_dict)} categorias."))
            else:
                self.stdout.write(self.style.ERROR(f"Falha ao baixar categorias: {cat_resp.status_code}"))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro fatal ao baixar categorias: {e}"))
            return

        # 3. DEFINIR PONTO DE PARTIDA (TIME SLICING)
        ultimo_processo = Processo.objects.filter(
            servico_solicitado__forma_solicitacao='Colab'
        ).order_by('-data_protocolo').first()

        if ultimo_processo:
            dt_global_inicio = ultimo_processo.data_protocolo - timedelta(days=1)
        else:
            # Se vazio, pega todo o histórico (ou ajuste para 365 dias se preferir)
            dt_global_inicio = timezone.now() - timedelta(days=365*2) 

        dt_agora = timezone.now()
        self.stdout.write(self.style.SUCCESS(f"Sincronização Global: de {dt_global_inicio} até {dt_agora}"))

        JANELA_HORAS = 6
        chunk_start = dt_global_inicio
        total_importados = 0
        total_erros = 0

        # 4. LOOP DE IMPORTAÇÃO (POSTS)
        while chunk_start < dt_agora:
            chunk_end = chunk_start + timedelta(hours=JANELA_HORAS)
            if chunk_end > dt_agora: chunk_end = dt_agora

            start_str = chunk_start.strftime('%Y-%m-%d %H:%M:%S')
            end_str = chunk_end.strftime('%Y-%m-%d %H:%M:%S')
            
            self.stdout.write(f"Baixando: {start_str} -> {end_str} ...")

            params = {'start_date': start_str, 'end_date': end_str}

            try:
                response = requests.get(f"{BASE_URL}/posts", params=params, headers=headers)
                
                if response.status_code == 406:
                    self.stdout.write(self.style.WARNING("Erro 406 (Muitos dados). Tentando ignorar e seguir (ou reduza a janela)..."))
                elif response.status_code == 429:
                    self.stdout.write(self.style.WARNING("Erro 429 (Rate Limit). Esperando 5s..."))
                    time.sleep(5)
                    continue # Tenta a mesma fatia de novo
                elif response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"Erro na API: {response.status_code}"))
                else:
                    data = response.json()
                    reports = data if isinstance(data, list) else data.get('posts', [])

                    if reports:
                        self.stdout.write(f"   > {len(reports)} itens. Processando...")
                        for report in reports:
                            if self.processar_report(report):
                                total_importados += 1
                            else:
                                total_erros += 1
                    else:
                        self.stdout.write("   > 0 itens.")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro de conexão: {e}"))

            chunk_start = chunk_end
            time.sleep(0.5) # Gentileza com a API

        self.stdout.write(self.style.SUCCESS(f"FIM! Importados: {total_importados}. Pendentes/Ignorados: {total_erros}"))

    def processar_report(self, item):
        try:
            protocolo = str(item.get('id'))
            
            # --- AQUI ESTÁ A MUDANÇA PRINCIPAL ---
            # 1. Pegamos o ID da categoria
            cat_id = item.get('category_id')
            
            # 2. Buscamos o NOME no dicionário que criamos no início
            categoria_nome = self.category_map_dict.get(cat_id)

            if not categoria_nome:
                # Fallback: Se não achou no dicionário, tenta ver se veio no JSON (raro na v2)
                categoria_nome = item.get('category_description')
            
            if not categoria_nome:
                # self.stdout.write(self.style.ERROR(f"ID {protocolo}: Categoria ID {cat_id} desconhecida."))
                return False # Não tem como processar sem nome

            # --- MAPEAMENTO (Igual antes) ---
            servico_obj = None
            mapeamento = MapeamentoServicos.objects.filter(
                sistema_origem='COLAB', 
                categoria_externa=categoria_nome
            ).first()

            if mapeamento:
                if mapeamento.servico_gea:
                    servico_obj = mapeamento.servico_gea
                else:
                    return False # Pendente
            else:
                MapeamentoServicos.objects.create(
                    sistema_origem='COLAB',
                    categoria_externa=categoria_nome,
                    servico_gea=None
                )
                self.stdout.write(self.style.WARNING(f"Nova Categoria Pendente: {categoria_nome}"))
                return False

            # --- STATUS ---
            status_raw = str(item.get('status')).upper()
            status_gea = 'ABERTO'
            if status_raw in ['FECHADO', 'FINALIZADO', 'RECUSADO', 'SOLVED', 'CLOSED', '2', '3']:
                status_gea = 'CONCLUIDO'
            elif status_raw in ['ATENDIMENTO', 'IN_PROGRESS', '1']:
                status_gea = 'EM_ANALISE'

            # --- DATAS ---
            created_at = item.get('created_at')
            data_criacao = parse_datetime(str(created_at).replace(' ', 'T')) if created_at else timezone.now()
            
            data_conclusao = None
            if status_gea == 'CONCLUIDO':
                updated_at = item.get('updated_at')
                if updated_at:
                    data_conclusao = parse_datetime(str(updated_at).replace(' ', 'T'))

            # --- GEO ---
            lat = item.get('lat')
            lng = item.get('lng')
            ponto = None
            if lat and lng:
                try:
                    ponto = Point(float(lng), float(lat), srid=4326)
                except: pass

            # --- SOLICITANTE ---
            solicitante_nome = item.get('citizen') or "Anônimo"

            Processo.objects.update_or_create(
                numero_protocolo=protocolo,
                defaults={
                    'servico_solicitado': servico_obj,
                    'status': status_gea,
                    'solicitante': solicitante_nome,
                    'detalhes_solicitacao': item.get('description', ''),
                    'data_protocolo': data_criacao,
                    'data_conclusao': data_conclusao,
                    'localizacao': ponto,
                }
            )
            return True

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro item {item.get('id')}: {e}"))
            return False