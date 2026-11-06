# -*- coding: utf-8 -*-
"""translator 纯函数单测：取词判断、英文提取、双语排版"""
from translator import bilingual_text, english_only, needs_translation


class TestNeedsTranslation:
    def test_pure_chinese_skipped(self):
        assert needs_translation("你好，世界。") is False

    def test_english_detected(self):
        assert needs_translation("hello world") is True

    def test_mixed_detected(self):
        assert needs_translation("版本 v2 支持 feature X") is True

    def test_empty_and_digits_skipped(self):
        assert needs_translation("") is False
        assert needs_translation("12345，。") is False


class TestEnglishOnly:
    def test_mixed_extracts_english(self):
        assert english_only("你好 hello world 世界") == "hello world"

    def test_pure_english_passthrough(self):
        assert english_only("just read this") == "just read this"

    def test_pure_chinese_empty(self):
        assert english_only("没有英文") == ""


class TestBilingualText:
    def test_single_line_translation_first(self):
        assert bilingual_text("hello", "你好") == "你好\nhello"

    def test_multiline_interleaved(self):
        assert bilingual_text("a\nb", "甲\n乙") == "a\n甲\nb\n乙"

    def test_extra_lines_kept(self):
        # 译文行数不一致时不丢内容
        assert bilingual_text("a\nb", "甲乙") == "a\n甲乙\nb"
