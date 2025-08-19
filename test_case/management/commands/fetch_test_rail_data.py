from django.core.management.base import BaseCommand
from utils.ingestion import ingest_test_rail


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--fetch-fields', action='store_true')

    def handle(self, *args, **options):
        fetch_fields = options.get('fetch_fields')
        ingest_test_rail(fetch_fields=fetch_fields)
