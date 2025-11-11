import csv
from django.core.management.base import BaseCommand
from core.models import Entidade, Secretaria, Departamento, Divisao, CartaDeServicos

class Command(BaseCommand):
    help = 'Importa a Carta de Serviços COMPLETA. Cria hierarquia e popula metadados.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='O caminho para o arquivo CSV completo.')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        self.stdout.write(self.style.SUCCESS(f'Iniciando importação completa: {csv_file_path}'))

        try:
            with open(csv_file_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file) 

                for row in reader:
                    titulo = row.get('Titulo', '').strip()
                    secretaria_nome = row.get('Secretaria', '').strip()
                    entidade_nome = row.get('Entidade', '').strip()

                    if not titulo or not secretaria_nome:
                        self.stdout.write(self.style.WARNING(f'Linha ignorada: Título ou Secretaria em branco.'))
                        continue

                    try:
                        # 1. Garante a Entidade
                        entidade_obj = None
                        if entidade_nome:
                            entidade_obj, _ = Entidade.objects.get_or_create(nome=entidade_nome)

                        # --- LÓGICA DE SIGLA CORRIGIDA ---
                        words = secretaria_nome.upper().split()
                        if len(words) == 1:
                            # Se for palavra única (SEMAE, Segurança), usa o nome todo (até 20 chars)
                            sigla_auto = words[0][:20] 
                        else:
                            # Se for composto (Secretaria de Saúde), usa iniciais
                            sigla_auto = "".join(word[0] for word in words)[:20]
                        # --- FIM DA CORREÇÃO ---

                        # 2. Garante a hierarquia (Secretaria)
                        secretaria, _ = Secretaria.objects.get_or_create(
                            nome=secretaria_nome,
                            defaults={'sigla': sigla_auto}
                        )
                        departamento, _ = Departamento.objects.get_or_create(
                            secretaria=secretaria,
                            nome="Departamento Geral"
                        )
                        divisao, _ = Divisao.objects.get_or_create(
                            departamento=departamento,
                            nome="Atendimento Geral"
                        )

                        # 3. Cria ou atualiza a Carta de Serviço
                        servico, created = CartaDeServicos.objects.update_or_create(
                            nome_servico=titulo,
                            defaults={
                                'divisao_responsavel': divisao,
                                'orgao_responsavel': row.get('Orgao', '').strip(),
                                'tipos_atendimento': row.get('Tipos de Atendimento', '').strip(),
                                'url_solicitacao': row.get('Solicitação pela Internet', '').strip(),
                                'entidade': entidade_obj,
                                'tipo_servico': row.get('Tipo', '').strip(),
                                'forma_solicitacao': row.get('Forma Solicitação', '').strip(),
                                'tipo_sistema': row.get('Tipo Sistema', '').strip(),
                                'prazo_maximo_dias': 30
                            }
                        )

                        if created:
                            self.stdout.write(self.style.SUCCESS(f'Serviço "{titulo}" criado.'))
                        else:
                            self.stdout.write(self.style.NOTICE(f'Serviço "{titulo}" atualizado.'))

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'ERRO na linha "{titulo}": {e}'))
                        continue

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Arquivo não encontrado: {csv_file_path}'))
            return

        self.stdout.write(self.style.SUCCESS('Importação completa concluída!'))