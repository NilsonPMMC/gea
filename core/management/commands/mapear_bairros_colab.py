import csv
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from core.models import Bairro

class Command(BaseCommand):
    help = 'Usa o CSV do Colab para renomear polígonos de bairros pendentes.'

    def add_arguments(self, parser):
        parser.add_argument('colab_csv_file', type=str, help='O caminho para o arquivo CSV do Colab.')

    def handle(self, *args, **options):
        colab_csv_path = options['colab_csv_file']
        self.stdout.write(self.style.SUCCESS(f'Iniciando mapeamento de bairros com: {colab_csv_path}'))

        bairros_mapeados = set()
        bairros_ja_existentes = set(Bairro.objects.exclude(nome__startswith='Polígono Pendente').values_list('nome', flat=True))

        try:
            with open(colab_csv_path, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file, delimiter=';')

                for row in reader:
                    try:
                        nome_bairro_colab = row.get("Bairro", "").strip()
                        if not nome_bairro_colab:
                            continue

                        # Se já mapeamos esse bairro, pulamos para economizar tempo
                        if nome_bairro_colab in bairros_mapeados or nome_bairro_colab in bairros_ja_existentes:
                            continue

                        # Pega um ponto de GPS válido para este bairro
                        lon = float(row.get("Longitude").replace("'", "").strip())
                        lat = float(row.get("Latitude").replace("'", "").strip())
                        ponto = Point(lon, lat, srid=4326)

                        # Pergunta ao PostGIS: Qual polígono contém este ponto?
                        bairro_encontrado = Bairro.objects.filter(geom__contains=ponto).first()

                        if bairro_encontrado:
                            # Se encontramos um polígono e ele é um "Pendente"
                            if bairro_encontrado.nome.startswith('Polígono Pendente'):
                                nome_antigo = bairro_encontrado.nome
                                bairro_encontrado.nome = nome_bairro_colab
                                bairro_encontrado.save()

                                # Adiciona aos sets para não processar de novo
                                bairros_mapeados.add(nome_bairro_colab)
                                bairros_ja_existentes.add(nome_bairro_colab)

                                self.stdout.write(self.style.SUCCESS(f'SUCESSO: "{nome_antigo}" foi renomeado para "{nome_bairro_colab}".'))
                            else:
                                # O polígono já tinha um nome correto, apenas marcamos como feito
                                bairros_ja_existentes.add(nome_bairro_colab)

                    except Exception as e:
                        # Pula linhas com lat/lon inválidos etc.
                        continue

            self.stdout.write(self.style.SUCCESS('Mapeamento de bairros concluído!'))

            pendentes_restantes = Bairro.objects.filter(nome__startswith='Polígono Pendente').count()
            if pendentes_restantes > 0:
                self.stdout.write(self.style.WARNING(f'Atenção: {pendentes_restantes} polígonos não puderam ser nomeados. Verifique se o CSV do Colab cobre todos os bairros.'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Arquivo CSV do Colab não encontrado: {colab_csv_path}'))