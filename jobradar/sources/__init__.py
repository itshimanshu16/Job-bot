from . import ashby, greenhouse, lever, smartrecruiters, workable

SOURCES = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "smartrecruiters": smartrecruiters,
    "workable": workable,
}

__all__ = ["SOURCES"]
