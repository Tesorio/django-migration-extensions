from django.core.management.base import BaseCommand
from django_migration_extensions.utils import write_manifest


class Command(BaseCommand):
    help = "Write migration manifest file"

    def handle(self, *args, **options):
        write_manifest()
