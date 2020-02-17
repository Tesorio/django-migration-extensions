import itertools

from django.apps import AppConfig as _AppConfig
from django.conf import settings
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.loader import MigrationLoader

from . import utils


class AppConfig(_AppConfig):
    name = "django_migration_extensions"

    def ready(self):
        if getattr(settings, "MIGRATION_CONFLICT_DETECTOR_STRATEGY", None):
            # Only patch if we have a strategy defined in settings
            _patch_everything()


def _patched_leaf_nodes(self, app=None):
    """
    Patched version of ``MigrationGraph.leaf_nodes`` that excludes duplicated leaves,
    keeping only the latest leaf.

    By excluding duplicated leaves, we move the responsibility of detecting conflicts to
    the strategy. The strategy is also responsible to ensure that the last leaf is the
    correct one.
    """
    leaf_nodes = _original_leaf_nodes(self, app=app)
    leaf_nodes_grouped_by_app = itertools.groupby(leaf_nodes, key=lambda t: t[0])

    fixed_leaf_nodes = []
    for app_label, grouper in leaf_nodes_grouped_by_app:
        migration_names = [node[1] for node in grouper]
        last_leaf_node = sorted(migration_names)[-1]
        fixed_leaf_nodes.append((app_label, last_leaf_node))

    return fixed_leaf_nodes


def _patched_detect_conflicts(self):
    """
    Patched version of ``MigrationLoader.detect_conflicts`` that passes the
    responsibility of detecting conflicts to the strategy
    """
    return utils.get_strategy(self).detect_conflicts(self.graph)


_original_leaf_nodes = None


def _patch_everything():
    """
    Patch ``MigrationGraph`` and ``MigrationLoader``
    """
    global _original_leaf_nodes

    _original_leaf_nodes = MigrationGraph.leaf_nodes

    MigrationGraph.leaf_nodes = _patched_leaf_nodes
    MigrationLoader.detect_conflicts = _patched_detect_conflicts
