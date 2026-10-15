"""Versioned dense vector manifest validation."""

from .manifest import IndexMismatchError, assert_compatible, make_index_manifest

__all__ = ["IndexMismatchError", "assert_compatible", "make_index_manifest"]
