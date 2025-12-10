import json
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from core.models import Bairro

class Command(BaseCommand):
    help = 'Importa polígonos de bairros de um arquivo GeoJSON.'

    def add_arguments(self, parser):
        parser.add_argument('geojson_file', type=str, help='O caminho para o arquivo GeoJSON dos bairros.')

    def handle(self, *args, **options):
        geojson_file_path = options['geojson_file']
        self.stdout.write(self.style.SUCCESS(f'Iniciando importação do GeoJSON: {geojson_file_path}'))

        # Limpa bairros pendentes antigos para evitar lixo
        Bairro.objects.filter(nome__startswith='Polígono Pendente').delete()
        self.stdout.write(self.style.WARNING('Bairros pendentes antigos foram limpos.'))

        try:
            with open(geojson_file_path, mode='r', encoding='utf-8') as f:
                data = json.load(f)

                unnamed_counter = 1 # Contador para polígonos sem nome

                for feature in data['features']:
                    properties = feature.get('properties', {})

                    # Tenta pegar o nome. Se não existir, cria um temporário.
                    nome_bairro = properties.get('nome') # AJUSTE AQUI se o campo tiver outro nome

                    if not nome_bairro:
                        nome_bairro = f"Polígono Pendente {unnamed_counter}"
                        unnamed_counter += 1

                    # Converte a geometria do GeoJSON para o formato do Django
                    geom_str = json.dumps(feature['geometry'])
                    geom = GEOSGeometry(geom_str, srid=4326)

                    if geom.geom_type == 'Polygon':
                        geom = MultiPolygon(geom, srid=4326)

                    # Cria ou atualiza o bairro no banco
                    bairro, created = Bairro.objects.update_or_create(
                        nome=nome_bairro,
                        defaults={'geom': geom}
                    )

                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Bairro "{nome_bairro}" criado.'))
                    else:
                        self.stdout.write(self.style.NOTICE(f'Bairro "{nome_bairro}" atualizado.'))

            self.stdout.write(self.style.SUCCESS('Importação de polígonos concluída!'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'Arquivo GeoJSON não encontrado: {geojson_file_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ocorreu um erro: {e}'))