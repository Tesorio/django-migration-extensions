from django_migration_extensions import strategies

from django.core.management.commands.makemigrations import (
    Command as BaseCommand,
)
from django.db.migrations.loader import MigrationLoader


class Command(BaseCommand):
    def write_migration_files(self, changes):
        super(Command, self).write_migration_files(changes)

        loader = MigrationLoader(None, ignore_no_migrations=True)

        strategy = strategies.SameModelDetectConflictStrategy(loader)
        strategy.write_manifest_file(changes)
