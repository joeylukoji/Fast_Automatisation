from . import builtin, erp  # noqa: F401  (enregistre les blocs)
from .registry import REGISTRY, NodeSpec, RunContext, catalogue, get_spec

__all__ = ["REGISTRY", "NodeSpec", "RunContext", "catalogue", "get_spec"]
