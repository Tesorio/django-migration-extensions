from django import get_version
from django.conf import settings
from django.db.migrations.loader import MigrationLoader
from django.utils.module_loading import import_string


def get_strategy(loader):
    """
    Returns a Strategy object based on ``settings.MIGRATION_CONFLICT_DETECTOR_STRATEGY``
    """
    strategy_dotted_path = getattr(settings, "MIGRATION_CONFLICT_DETECTOR_STRATEGY")
    return import_string(strategy_dotted_path)(loader)


def write_manifest(changes=(), strategy=None):
    if strategy is None:
        loader = MigrationLoader(None, ignore_no_migrations=True)
        strategy = get_strategy(loader)

    strategy.write_manifest_file(changes)


def is_field_operation(operation):
    if get_version() >= (1, 10):
        from django.db.migrations.operations.fields import FieldOperation

        return isinstance(operation, FieldOperation)

    else:
        # Backwards compatibility with Django 1.9
        from django.db.migrations.operations import fields as _fields_op

        return isinstance(
            operation,
            (
                _fields_op.AddField,
                _fields_op.RemoveField,
                _fields_op.AlterField,
                _fields_op.RenameField,
            ),
        )


def is_model_operation(operation):
    if get_version() >= (1, 10):
        from django.db.migrations.operations.models import ModelOperation

        return isinstance(operation, ModelOperation)

    else:
        # Backwards compatibility with Django 1.9
        from django.db.migrations.operations import models as _models_op

        return isinstance(
            operation,
            (
                _models_op.CreateModel,
                _models_op.DeleteModel,
                _models_op.RenameModel,
                _models_op.AlterModelTable,
                _models_op.AlterUniqueTogether,
                _models_op.AlterIndexTogether,
                _models_op.AlterOrderWithRespectTo,
                _models_op.AlterModelOptions,
                _models_op.AlterModelManagers,
            ),
        )
