import csv
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.gis.geos import Point
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from core.models import Processo, CartaDeServicos, MapeamentoServicos

class Command(BaseCommand):
    help = 'Importa processos do Colab (CSV) usando a tabela de Mapeamento e corrigindo encoding.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='O caminho completo para o arquivo CSV do Colab.')

    def get_servico_from_mapping(self, categoria_colab):
        try:
            mapeamento = MapeamentoServicos.objects.get(
                sistema_origem='COLAB',
                categoria_externa=categoria_colab
            )
            if mapeamento.servico_gea is None:
                self.stdout.write(self.style.WARNING(f'Atenção: A categoria "{categoria_colab}" foi encontrada, mas está PENDENTE de mapeamento.'))
                return None
            return mapeamento.servico_gea
        except ObjectDoesNotExist:
            self.stdout.write(self.style.ERROR(f'NOVA CATEGORIA: "{categoria_colab}" não mapeada. Criando mapeamento pendente.'))
            MapeamentoServicos.objects.create(
                sistema_origem='COLAB',
                categoria_externa=categoria_colab,
                servico_gea=None
            )
            return None

    def handle(self, *args, **options):
        
        def fix_encoding(text_to_fix):
            if text_to_fix is None:
                return None
            try:
                return text_to_fix.encode('iso-8859-1').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                return text_to_fix

        csv_file_path = options['csv_file']
        self.stdout.write(self.style.SUCCESS(f'Iniciando importação do Colab: {csv_file_path}'))

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file, delimiter=';') 

                for row in reader:
                    protocolo = row.get("Protocolo da Empresa")
                    if not protocolo:
                        continue

                    # 2. TRADUZIR O SERVIÇO (COM LIMPEZA TOTAL)
                    categoria_colab_raw = row.get("Categoria")
                    categoria_colab = fix_encoding(categoria_colab_raw)
                    
                    if categoria_colab:
                        categoria_colab = categoria_colab.strip() # <--- AQUI ESTÁ A CORREÇÃO
                    else:
                        self.stdout.write(self.style.ERROR(f'Protocolo {protocolo} pulado. Categoria em branco.'))
                        continue

                    servico_gea_obj = self.get_servico_from_mapping(categoria_colab)
                    
                    if servico_gea_obj is None:
                        self.stdout.write(self.style.ERROR(f'Protocolo {protocolo} pulado. Categoria "{categoria_colab}" não mapeada.'))
                        continue

                    # 3. TRADUZIR O STATUS
                    status_colab = row.get("Status", "").upper()
                    status_gea = 'ABERTO'
                    if status_colab == 'FECHADO': status_gea = 'CONCLUIDO'
                    elif status_colab == 'EM ANDAMENTO': status_gea = 'EM_ANALISE'

                    # 4. TRATAR DATAS
                    data_criacao = None
                    data_conclusao = None
                    try:
                        data_str = row.get("Data de criação").replace("'", "").strip() 
                        
                        if data_str and data_str != "'-'":
                            data_parts = data_str.split('/')
                            data_iso = f"{data_parts[2]}-{data_parts[1]}-{data_parts[0]}T00:00:00"
                            data_criacao = parse_datetime(data_iso)
                        
                        if not data_criacao:
                            raise ValueError("Data inválida")

                        data_conclusao_str = row.get("Data de conclusão").replace("'", "").strip()
                        if data_conclusao_str and data_conclusao_str != "'-'" and status_gea == 'CONCLUIDO':
                            data_parts = data_conclusao_str.split('/')
                            data_iso = f"{data_parts[2]}-{data_parts[1]}-{data_parts[0]}T00:00:00"
                            data_conclusao = parse_datetime(data_iso)
                        
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'Protocolo {protocolo}: Falha data ({e}). Usando data atual.'))
                        data_criacao = timezone.now()
                        data_conclusao = None

                    # 5. TRATAR GEO
                    try:
                        lon = float(row.get("Longitude").replace("'", "").strip())
                        lat = float(row.get("Latitude").replace("'", "").strip())
                        localizacao_ponto = Point(lon, lat, srid=4326)
                    except:
                        localizacao_ponto = None

                    # 6. SALVAR NO BANCO (COM LIMPEZA DO NOME)
                    solicitante_raw = row.get("Nome do Cidadão", "Não informado")
                    solicitante_corrigido = fix_encoding(solicitante_raw)
                    if solicitante_corrigido:
                        solicitante_corrigido = solicitante_corrigido.strip() # <--- LIMPEZA AQUI TAMBÉM

                    processo, created = Processo.objects.update_or_create(
                        numero_protocolo=protocolo,
                        defaults={
                            'servico_solicitado': servico_gea_obj,
                            'status': status_gea,
                            'solicitante': solicitante_corrigido,
                            'data_protocolo': data_criacao,
                            'data_conclusao': data_conclusao,
                            'localizacao': localizacao_ponto,
                            'sistema_origem': 'COLAB',
                        }
                    )
                    
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Protocolo {protocolo} CRIADO.'))
                    else:
                        self.stdout.write(self.style.NOTICE(f'Protocolo {protocolo} ATUALIZADO.'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Arquivo CSV não encontrado: {csv_file_path}'))
        except UnicodeDecodeError:
            self.stdout.write(self.style.ERROR(f'ERRO DE ENCODING!'))
        
        self.stdout.write(self.style.SUCCESS('Importação do Colab concluída!'))