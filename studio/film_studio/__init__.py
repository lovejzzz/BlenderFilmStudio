"""Personal Film Studio: versioned projects and a native Blender workbench."""

__version__ = "0.1.4"


def register():
    from . import ui
    ui.register()


def unregister():
    from . import ui
    ui.unregister()
