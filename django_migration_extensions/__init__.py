import itertools

from django.conf import settings
from django.db.migrations.graph import MigrationGraph
from django.db.migrations.loader import MigrationLoader
from django.utils.module_loading import import_string

DEFAULT_STRATEGY = "django_migration_extensions.strategies.ModelDetectConflictStrategy"


def get_strategy(loader):
    """
    Returns a Strategy object based on ``settings.MIGRATION_CONFLICT_DETECTOR_STRATEGY``
    """
    strategy_dotted_path = getattr(
        settings, "MIGRATION_CONFLICT_DETECTOR_STRATEGY", DEFAULT_STRATEGY
    )
    return import_string(strategy_dotted_path)(loader)


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
    return get_strategy(self).detect_conflicts(self.graph)


def _patch_everything():
    """
    Patch ``MigrationGraph`` and ``MigrationLoader``
    """
    MigrationGraph.leaf_nodes = _patched_leaf_nodes
    MigrationLoader.detect_conflicts = _patched_detect_conflicts


_original_leaf_nodes = MigrationGraph.leaf_nodes

_patch_everything()
