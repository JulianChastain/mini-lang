import unittest
from lexer import Token, TokenType, lex
from parser import (
    Parser,
    Var,
    Lam,
    App,
    IntLit,
    Add,
    Anno,
    IntType,
    FunType,
    TVar,
    Forall,
)


class TestParser(unittest.TestCase):
    def test_parse_bare_variable(self):
        tokens = [
            Token(type=TokenType.IDENTIFIER, value="x"),
            Token(type=TokenType.EOF, value="EOF"),
        ]
        parser = Parser(tokens)
        self.assertEqual(parser(), Var("x"))

    def test_parse_lambda(self):
        tokens = [
            Token(type=TokenType.LAMBDA, value="/"),
            Token(type=TokenType.IDENTIFIER, value="x"),
            Token(type=TokenType.ARROW, value="->"),
            Token(type=TokenType.IDENTIFIER, value="x"),
            Token(type=TokenType.EOF, value="EOF"),
        ]
        parser = Parser(tokens)
        self.assertEqual(parser(), Lam("x", Var("x")))

    def test_parse_application(self):
        tokens = [
            Token(type=TokenType.LPAREN, value="("),
            Token(type=TokenType.LAMBDA, value="/"),
            Token(type=TokenType.IDENTIFIER, value="x"),
            Token(type=TokenType.ARROW, value="->"),
            Token(type=TokenType.IDENTIFIER, value="x"),
            Token(type=TokenType.RPAREN, value=")"),
            Token(TokenType.IDENTIFIER, value="y"),
            Token(type=TokenType.EOF, value="EOF"),
        ]
        parser = Parser(tokens)
        self.assertEqual(parser(), App(Lam("x", Var("x")), Var("y")))

    def test_parse_left_associative_application(self):
        tokens = [
            Token(type=TokenType.IDENTIFIER, value="f"),
            Token(type=TokenType.IDENTIFIER, value="x"),
            Token(type=TokenType.IDENTIFIER, value="y"),
            Token(type=TokenType.EOF, value="EOF"),
        ]
        parser = Parser(tokens)
        self.assertEqual(parser(), App(App(Var("f"), Var("x")), Var("y")))


class TestIntegration(unittest.TestCase):
    def test_parse_int(self):
        self.assertEqual(Parser(lex("42"))(), IntLit(42))

    def test_parse_add(self):
        self.assertEqual(Parser(lex("1 + 2"))(), Add(IntLit(1), IntLit(2)))

    def test_parse_add_add(self):
        self.assertEqual(Parser(lex("1 + 2 + 3"))(), Add(Add(IntLit(1), IntLit(2)), IntLit(3)))

    def test_parse_app_add(self):
        self.assertEqual(Parser(lex("f 1 + 2"))(), Add(App(Var("f"), IntLit(1)), IntLit(2)))

    def test_parse_app_int(self):
        self.assertEqual(Parser(lex("f 42"))(), App(Var("f"), IntLit(42)))


class TestParseTypes(unittest.TestCase):
    def parse_type(self, src):
        parser = Parser(lex(src))
        t = parser.parse_type()
        parser.expect(TokenType.EOF)
        return t

    def test_parse_int_type(self):
        self.assertEqual(self.parse_type("Int"), IntType())

    def test_parse_type_var(self):
        self.assertEqual(self.parse_type("a"), TVar("a"))

    def test_parse_arrow_is_right_associative(self):
        self.assertEqual(
            self.parse_type("Int -> Int -> Int"),
            FunType(IntType(), FunType(IntType(), IntType())),
        )

    def test_parse_parenthesized_arrow(self):
        self.assertEqual(
            self.parse_type("(Int -> Int) -> Int"),
            FunType(FunType(IntType(), IntType()), IntType()),
        )

    def test_parse_forall(self):
        self.assertEqual(
            self.parse_type("forall a. a -> a"),
            Forall("a", FunType(TVar("a"), TVar("a"))),
        )

    def test_parse_nested_forall(self):
        self.assertEqual(
            self.parse_type("forall a. forall b. a -> b"),
            Forall("a", Forall("b", FunType(TVar("a"), TVar("b")))),
        )


class TestParseAnnotations(unittest.TestCase):
    def test_parse_annotation(self):
        self.assertEqual(Parser(lex("(x : Int)"))(), Anno(Var("x"), IntType()))

    def test_parse_annotated_lambda_applied(self):
        self.assertEqual(
            Parser(lex("((/x -> x + 1) : Int -> Int) 2"))(),
            App(
                Anno(
                    Lam("x", Add(Var("x"), IntLit(1))),
                    FunType(IntType(), IntType()),
                ),
                IntLit(2),
            ),
        )

    def test_annotation_on_lambda_body_without_inner_parens(self):
        self.assertEqual(
            Parser(lex("(/x -> x : Int -> Int)"))(),
            Anno(Lam("x", Var("x")), FunType(IntType(), IntType())),
        )

    def test_missing_type_after_colon(self):
        with self.assertRaises(SyntaxError):
            Parser(lex("(x : )"))()


if __name__ == "__main__":
    unittest.main()
