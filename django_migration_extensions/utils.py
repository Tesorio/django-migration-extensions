from django.conf import settings
from django.utils.module_loading import import_string


def get_strategy(loader):
    """
    Returns a Strategy object based on ``settings.MIGRATION_CONFLICT_DETECTOR_STRATEGY``
    """
    strategy_dotted_path = getattr(settings, "MIGRATION_CONFLICT_DETECTOR_STRATEGY")
    return import_string(strategy_dotted_path)(loader)
