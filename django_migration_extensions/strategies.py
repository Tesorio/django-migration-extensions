import itertools
import json
from collections import OrderedDict

from django.apps import apps
from django.conf import settings

from . import utils


class BaseConflictStrategy(object):
    def __init__(self, loader):
        self.loader = loader

    def write_manifest_file(self, changes):
        """
        Writes changes to a manifest file

        The main purpose of the manifest file, is to make it work as a tool for
        detecting conflicts in DVCS systems, see ``ModelDetectConflictStrategy`` for
        more details
        """
        raise NotImplementedError()

    def detect_conflicts(self, graph):
        """
        Detect conflicts in a graph

        For reference, the way that Django detect conflicts is very simple: it won't let
        an app have more than one leaf node in the graph, which means that you cannot
        have more than one person creating migrations at the same time for a given app
        """
        raise NotImplementedError()


class ModelDetectConflictStrategy(BaseConflictStrategy):
    """
    Detect conflicts at model-level

    This means that we can have people creating migrations for different models, but not
    on the same model. In case of more than one leaf node in an app referring to the
    same model, a conflict error will be triggered.

    Manifest file
    -------------

    The manifest file for this strategy has the following format::

        {
            "app_label.model": "<last migration name>",
            ...
        }

    Everytime a new migration is created, the strategy will look at the manifest file
    and update the line that refers to the model affected and update the last migration
    name. In case that another person is working on changes to the same model, the DVCS
    system (eg. git) will be able to catch the conflicts before the code gets merged

    To fix the conflit, like any other migration conflict, the person will have to redo
    the migration, as described in Django docs:

    https://docs.djangoproject.com/en/3.0/topics/migrations/#version-control

    """

    @property
    def _manifest_file_path(self):
        return getattr(
            settings,
            "MIGRATION_CONFLICT_DETECTOR_MANIFEST_FILE",
            ".django_migrations.manifest.json",
        )

    @property
    def _manifest_header(self):
        yield "---------------------------------------------------------------------"
        yield " You should NEVER change this file by hand or it will break things   "
        yield "                                                                     "
        yield " This is a manifest file that is automatically created after running "
        yield " the makemigrations command. The manifest describes the models that  "
        yield " have been migrated and the latest migration that touched that model "
        yield "                                                                     "
        yield " If you get a conflict, it means that you and another person changed "
        yield " the same model, and one of you will have to redo your migration in  "
        yield " order to resolve the conflict.                                      "
        yield "---------------------------------------------------------------------"
        yield ""

    def write_manifest_file(self, changes):
        """
        Writes the manifest file
        """
        app_labels = [app_config.label for app_config in apps.get_app_configs()]

        # create mapping (1-1) between model and last migration name
        model_migration_map = {}
        nodes = self._get_sorted_nodes(app_labels)
        for (app_label, migration_name), migration in nodes:
            models_changed = self._find_models_changed(migration)
            for model in models_changed:
                model_migration_map[model] = migration_name

        # write to manifest file
        header = [
            ("_H{:02d}".format(i), msg) for i, msg in enumerate(self._manifest_header)
        ]

        # turn model_migration_map into a list
        def _model_migration_map_item_key(item):
            (app_label, model_name), migration_name = item
            return (app_labels.index(app_label), model_name)

        model_migration_map_items = sorted(
            model_migration_map.items(), key=_model_migration_map_item_key
        )

        model_changes = [
            ("{}.{}".format(app_label, model_name), migration_name)
            for (app_label, model_name), migration_name in model_migration_map_items
        ]

        manifest = OrderedDict(header + model_changes)

        with open(self._manifest_file_path, "w") as fp:
            json.dump(manifest, fp, indent=4, ensure_ascii=True)

    def detect_conflicts(self, graph):
        """
        Detect conflicts in migrations at model level
        """
        # get all leaf node migrations
        leaf_nodes = graph.leaf_nodes()
        migrations = list(itertools.starmap(self.loader.get_migration, leaf_nodes))

        # find conflicting models: models referred in more than one leaf node migration
        seen_models = {}
        conflicting_models = set()
        for migration in migrations:
            models = set(self._find_models_changed(migration))
            for model in models:
                if model in seen_models:
                    conflicting_models.add(model)
                seen_models.setdefault(model, set()).add(migration.name)

        return {
            app_label: seen_models[(app_label, model_name)]
            for app_label, model_name in conflicting_models
        }

    def _get_sorted_nodes(self, app_labels):
        """
        Helper function used to write the manifest file in a deterministic way (sorted)

        Return graph nodes sorted by app order, which is its position in
        ``INSTALLED_APPS`` and the migration name
        """

        def _sort_node_key(node):
            (app_label, migration_name), migration = node
            app_order = app_labels.index(app_label)
            return app_order, migration_name

        return sorted(self.loader.graph.nodes.items(), key=_sort_node_key)

    def _find_models_changed(self, migration):
        """
        Given a ``Migration`` object, find all changes that may affect any models
        """
        for operation in migration.operations:
            if utils.is_model_operation(operation):
                yield (migration.app_label, operation.name_lower)
            elif utils.is_field_operation(operation):
                yield (migration.app_label, operation.model_name_lower)
