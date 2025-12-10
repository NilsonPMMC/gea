import csv
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from core.models import CartaDeServicos, MapeamentoServicos, Secretaria

class Command(BaseCommand):
    help = 'Importa o DE-PARA de serviços do Colab para a tabela de Mapeamento.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='O caminho para o arquivo CSV de-para.')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        self.stdout.write(self.style.SUCCESS(f'Iniciando importação do DE-PARA: {csv_file_path}'))

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                # O delimitador parece ser vírgula baseado no seu exemplo
                reader = csv.DictReader(file, delimiter=',') 

                count_created = 0
                count_updated = 0
                count_errors = 0

                for row in reader:
                    # Limpa espaços em branco extras
                    nome_gea = row.get('carta_servico_prefeitura', '').strip()
                    nome_colab = row.get('carta_servico_colab', '').strip()
                    
                    if not nome_gea or not nome_colab:
                        continue

                    # 1. Tenta encontrar o serviço na nossa Carta
                    servico_gea_obj = None
                    try:
                        # Tenta busca exata
                        servico_gea_obj = CartaDeServicos.objects.get(nome_servico__iexact=nome_gea)
                    except ObjectDoesNotExist:
                        self.stdout.write(self.style.ERROR(f'ERRO: Serviço GEA não encontrado: "{nome_gea}" (para o Colab: "{nome_colab}")'))
                        count_errors += 1
                        continue
                    except MultipleObjectsReturned:
                        self.stdout.write(self.style.ERROR(f'ERRO: Múltiplos serviços encontrados com o nome: "{nome_gea}". Verifique duplicatas.'))
                        count_errors += 1
                        continue

                    # 2. Cria ou Atualiza o Mapeamento
                    # A chave única é a combinação (sistema_origem + categoria_externa)
                    mapeamento, created = MapeamentoServicos.objects.update_or_create(
                        sistema_origem='COLAB',
                        categoria_externa=nome_colab,
                        defaults={
                            'servico_gea': servico_gea_obj
                        }
                    )

                    if created:
                        self.stdout.write(self.style.SUCCESS(f'CRIADO: "{nome_colab}" -> "{nome_gea}"'))
                        count_created += 1
                    else:
                        # Se já existia, atualizamos o vínculo para garantir que está certo
                        self.stdout.write(self.style.NOTICE(f'ATUALIZADO: "{nome_colab}" -> "{nome_gea}"'))
                        count_updated += 1

            self.stdout.write(self.style.SUCCESS(f'\nConcluído!'))
            self.stdout.write(f'Criados: {count_created}')
            self.stdout.write(f'Atualizados: {count_updated}')
            self.stdout.write(self.style.ERROR(f'Erros (Serviços não encontrados): {count_errors}'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Arquivo não encontrado: {csv_file_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ocorreu um erro inesperado: {e}'))