"""The README's rule-by-rule tables name, for each rule, the function that
implements it. Check that every such function exists and mentions the rule,
so the tables can't drift from the code."""
import importlib
import inspect
import re
import unittest
from pathlib import Path

README = Path(__file__).parent.parent / "README.md"
ROW = re.compile(r"^\| (?P<rule>[^|]+?) \| [^|]+ \| `(?P<target>[\w.]+)` \|$")


def rule_rows() -> list[tuple[str, str]]:
    text = README.read_text()
    section = text[text.index("### Rule by rule") : text.index("### The new rules")]
    return [
        (m["rule"], m["target"])
        for line in section.splitlines()
        if (m := ROW.match(line))
    ]


def resolve(target: str):
    module_name, *attrs = target.split(".")
    obj = importlib.import_module(module_name)
    for attr in attrs:
        obj = getattr(obj, attr)
    return obj


class TestReadmeRuleTables(unittest.TestCase):
    def test_tables_are_found(self):
        rules = [rule for rule, _ in rule_rows()]
        # Fig. 9 has 8 rules, Fig. 10 has 8, and Fig. 11 has 12.
        for rule in ["<:Var", "InstRAllL", "→App", "PCon", "Match⇐"]:
            self.assertIn(rule, rules)
        self.assertGreaterEqual(len(rules), 28 + 15)

    def test_every_rule_appears_in_its_function(self):
        for rule, target in rule_rows():
            with self.subTest(rule=rule, target=target):
                source = inspect.getsource(resolve(target))
                self.assertIn(rule, source)


if __name__ == "__main__":
    unittest.main()
