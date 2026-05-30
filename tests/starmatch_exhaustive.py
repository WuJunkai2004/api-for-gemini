import sys
from pathlib import Path
import unittest

# Add the project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api_for_gemini.utils.stars import StarMatch

class TestStarMatchExhaustive(unittest.TestCase):
    def test_prefix_matching(self):
        """测试前缀匹配，例如 gpt-*"""
        sm = StarMatch("gpt-*")
        self.assertTrue(sm.match("gpt-4"))
        self.assertTrue(sm.match("gpt-4-turbo"))
        self.assertTrue(sm.match("gpt-"))
        self.assertFalse(sm.match("agpt-4"))
        self.assertFalse(sm.match("openai-gpt"))

    def test_suffix_matching(self):
        """测试后缀匹配，例如 *-flash"""
        sm = StarMatch("*-flash")
        self.assertTrue(sm.match("gemini-1.5-flash"))
        self.assertTrue(sm.match("flash-flash"))
        self.assertTrue(sm.match("-flash"))
        self.assertFalse(sm.match("gemini-flash-lite"))

    def test_middle_matching(self):
        """测试中间匹配，例如 h*d"""
        sm = StarMatch("h*d")
        self.assertTrue(sm.match("helloworld"))
        self.assertTrue(sm.match("head"))
        self.assertTrue(sm.match("hd"))
        self.assertTrue(sm.match("h---d"))
        self.assertFalse(sm.match("hello"))
        self.assertFalse(sm.match("world"))

    def test_single_star_matching(self):
        """测试只有一个 * 的情况"""
        sm = StarMatch("*")
        self.assertTrue(sm.match("anything"))
        self.assertTrue(sm.match(""))
        self.assertTrue(sm.match("gpt-4o"))
        self.assertTrue(sm.match("!@#$%^&*()"))

    def test_multiple_stars(self):
        """测试多个 * 的情况"""
        sm = StarMatch("a*b*c")
        self.assertTrue(sm.match("abc"))
        self.assertTrue(sm.match("a123b456c"))
        self.assertTrue(sm.match("axbxc"))
        self.assertFalse(sm.match("ab"))
        self.assertFalse(sm.match("bc"))

    def test_strict_literal_matching(self):
        """确保除了 * 以外的正则特殊字符被转义"""
        sm = StarMatch("model.v1?")
        self.assertTrue(sm.match("model.v1?"))
        self.assertFalse(sm.match("modelxv1?")) # . 被转义，不匹配 x
        self.assertFalse(sm.match("model.v1"))  # ? 被转义，必须存在

if __name__ == "__main__":
    unittest.main()
