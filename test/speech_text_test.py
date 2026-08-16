from __future__ import annotations

import unittest

from muxiva_voice_transport.speech_text import normalize_for_speech


class SpeechTextNormalizerTest(unittest.TestCase):
    def test_strips_markdown_urls_and_emoji(self) -> None:
        source = "## 结果 🚀\n- **详情**见[文档](https://example.com) ✅"
        self.assertEqual(normalize_for_speech(source), "结果，详情见文档")

    def test_emoji_and_closing_parenthesis_preserve_tts_pauses(self) -> None:
        self.assertEqual(
            normalize_for_speech("你好🙂世界（补充说明）继续。✅"),
            "你好，世界，补充说明，继续。",
        )

    def test_display_boundaries_do_not_glue_english_words(self) -> None:
        self.assertEqual(
            normalize_for_speech("First🙂second (optional) next"),
            "First,second,optional,next",
        )

    def test_speaks_chinese_lists_dates_decimals_and_percentages(self) -> None:
        source = "1、2、3；2026年；版本 12.5；完成 80%。"
        self.assertEqual(
            normalize_for_speech(source),
            "一、二、三；二零二六年；版本十二点五；完成百分之八十。",
        )

    def test_preserves_english_numbers_for_english_text(self) -> None:
        self.assertEqual(normalize_for_speech("There are 3 options ✅"), "There are 3 options")

    def test_replaces_fenced_code(self) -> None:
        self.assertEqual(
            normalize_for_speech("已完成。```python\nprint(1)\n```请查看。"),
            "已完成。代码已经生成，请在聊天窗口查看。请查看。",
        )

    def test_removes_bare_domains_emails_rules_dashes_and_slashes(self) -> None:
        source = (
            "访问 example.com/guide 或 https://docs.example.org/a-b，联系 hi@example.com。\n"
            "---\n"
            "冷静——稳定 / 清晰 #"
        )
        self.assertEqual(normalize_for_speech(source), "访问或，联系。冷静，稳定，清晰")

    def test_keeps_markdown_link_label_but_never_speaks_its_address(self) -> None:
        self.assertEqual(
            normalize_for_speech("请查看[安装文档](https://example.com/install-guide)。"),
            "请查看安装文档。",
        )


if __name__ == "__main__":
    unittest.main()
