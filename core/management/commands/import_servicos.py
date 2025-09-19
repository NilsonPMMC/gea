import csv
from django.core.management.base import BaseCommand
from core.models import Secretaria, Departamento, Divisao, CartaDeServicos

class Command(BaseCommand):
    help = 'Importa a Carta de Serviços de um CSV. Cria Secretarias, Departamentos e Divisões se não existirem.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='O caminho completo para o arquivo CSV a ser importado.')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        self.stdout.write(self.style.SUCCESS(f'Iniciando a importação do arquivo: {csv_file_path}'))

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file, delimiter=',', quotechar='"')
                next(reader, None)  # Pula o cabeçalho

                for row_num, row in enumerate(reader, 2):
                    if len(row) < 2:
                        continue

                    titulo = row[0].strip()
                    orgao_nome = row[1].strip()

                    if not titulo or not orgao_nome:
                        self.stdout.write(self.style.WARNING(f'Linha {row_num} ignorada: Título ou Órgão em branco.'))
                        continue

                    try:
                        # 1. Pega ou cria a Secretaria
                        sigla_auto = "".join(word[0] for word in orgao_nome.upper().split())
                        secretaria, sec_created = Secretaria.objects.get_or_create(
                            nome=orgao_nome,
                            defaults={'sigla': sigla_auto}
                        )
                        if sec_created:
                            self.stdout.write(self.style.SUCCESS(f'>>> Nova Secretaria "{orgao_nome}" criada com sigla "{sigla_auto}".'))

                        # 2. Pega ou cria o Departamento padrão
                        departamento, dep_created = Departamento.objects.get_or_create(
                            secretaria=secretaria,
                            nome="Departamento Geral"
                        )

                        # 3. Pega ou cria a Divisão padrão
                        divisao, div_created = Divisao.objects.get_or_create(
                            departamento=departamento,
                            nome="Atendimento Geral"
                        )

                        # 4. Cria ou atualiza a Carta de Serviço
                        servico, created = CartaDeServicos.objects.update_or_create(
                            nome_servico=titulo,
                            defaults={
                                'divisao_responsavel': divisao,
                                'prazo_maximo_dias': 30
                            }
                        )

                        if created:
                            self.stdout.write(self.style.SUCCESS(f'OK Linha {row_num}: Serviço "{titulo}" criado.'))
                        else:
                            self.stdout.write(self.style.NOTICE(f'OK Linha {row_num}: Serviço "{titulo}" já existia e foi atualizado.'))

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'ERRO INESPERADO na linha {row_num}: {e}'))
                        continue

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Arquivo não encontrado em: {csv_file_path}'))
            return

        self.stdout.write(self.style.SUCCESS('Importação concluída!'))