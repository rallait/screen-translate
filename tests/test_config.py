# -*- coding: utf-8 -*-
"""config._merge：用户配置深合并，缺省值兜底"""
from config import _merge


def test_merge_fills_missing_with_defaults():
    base = {"ui": {"theme": "midnight", "font_size": 11}, "behavior": {"drag_enabled": True}}
    merged = _merge(base, {"ui": {"theme": "sakura"}})
    assert merged["ui"]["theme"] == "sakura"
    assert merged["ui"]["font_size"] == 11
    assert merged["behavior"]["drag_enabled"] is True


def test_merge_tolerates_bad_input():
    base = {"a": 1}
    assert _merge(base, None) == base
    assert _merge(base, "broken") == base
