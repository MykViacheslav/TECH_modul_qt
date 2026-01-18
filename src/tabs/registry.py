from __future__ import annotations
from types import SimpleNamespace

def ensure_ctx(ctx):
    if ctx is None:
        ctx = SimpleNamespace()

    # dict or object compatibility
    if isinstance(ctx, dict):
        if "bus" not in ctx or ctx["bus"] is None:
            from app.bus import AppBus
            ctx["bus"] = AppBus()
        if "state" not in ctx or not isinstance(ctx["state"], dict):
            ctx["state"] = {}
        return ctx

    if not hasattr(ctx, "bus") or ctx.bus is None:
        from app.bus import AppBus
        ctx.bus = AppBus()
    if not hasattr(ctx, "state") or not isinstance(ctx.state, dict):
        ctx.state = {}
    return ctx

def build_tabs(ctx):
    ctx = ensure_ctx(ctx)

    def wrap(widget):
        try:
            from .project_tree_wrapper import wrap_with_project_tree
            return wrap_with_project_tree(widget, ctx)
        except Exception:
            return widget

    from .tab_module import ModuleTab
    from .tab_module_base import ModuleBaseTab

    return [
        ("MODUL", wrap(ModuleTab(ctx))),
        ("BAZA MODULU", wrap(ModuleBaseTab(ctx))),
    ]
