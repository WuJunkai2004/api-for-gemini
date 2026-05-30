import re

class StarMatch:
    """
    专门处理仅支持 '*' 通配符匹配的类。
    除 '*' 以外的所有字符都会被视为字面量进行匹配。
    """
    def __init__(self, pattern: str):
        self.pattern = pattern
        self._regex = self._compile(pattern)

    def _compile(self, pattern: str) -> re.Pattern:
        """
        将通配符模式编译为正则表达式。
        """
        # 转义所有正则特殊字符，然后将转义后的 \* 替换为 .*
        regex_str = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
        return re.compile(regex_str)

    def match(self, text: str) -> bool:
        """
        检查给定文本是否匹配该模式。
        """
        return bool(self._regex.match(text))

    def __repr__(self) -> str:
        return f"StarMatch(pattern={self.pattern!r})"
