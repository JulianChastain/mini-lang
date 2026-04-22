import unittest
from lexer import lex
from evaluator import eval, Closure
from parser import Var, Lam, App, Parser

class TestEvaluator(unittest.TestCase):
    def test_eval_var(self):
        self.assertEqual(eval(Var("x"), {"x": "test_val"}), "test_val")

    def test_eval_lam(self):
        lam = Lam("x", Var("y"))
        closure = eval(lam, {"y": "captured"})
        self.assertTrue(isinstance(closure, Closure))
        self.assertEqual(closure.param, "x")
        self.assertEqual(closure.env, {"y": "captured"})

    def test_lexical_scoping(self):
        # This test ensures that lexical scoping is used rather than dynamic scoping.
        # We evaluate the expression: ((\x -> (\y -> x)) a) b
        # With initial environment: a = "lexical_value", b = "dynamic_value"
        # The result should be "lexical_value" if scope is captured statically.
        expr = App(
            func=App(
                func=Lam("x", Lam("y", Var("x"))),
                arg=Var("a")
            ),
            arg=Var("b")
        )
        env = {"a": "lexical_value", "b": "dynamic_value"}
        
        result = eval(expr, env)
        self.assertEqual(result, "lexical_value")

class TestIntegration(unittest.TestCase):
    def test_pipeline_identity_plus_one(self):
        source = "(/x -> x + 1) 2"
        tokens = lex(source)
        ast = Parser(tokens)()
        result = eval(ast, {})
        self.assertEqual(result, 3)

if __name__ == "__main__":
    unittest.main()
