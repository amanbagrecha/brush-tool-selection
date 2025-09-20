# __init__.py
from .brush_selection_plugin import BrushSelectionPlugin


def classFactory(iface):
    return BrushSelectionPlugin(iface)
