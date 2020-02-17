from django.core.management.commands.makemigrations import Command as _Command

from django_migration_extensions.utils import write_manifest


class Command(_Command):
    def write_migration_files(self, changes):
        super(Command, self).write_migration_files(changes)

        write_manifest(changes)
