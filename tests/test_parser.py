import unittest
from lexer import Token, TokenType, lex
from parser import Parser, Var, Lam, App, IntLit, Add


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


if __name__ == "__main__":
    unittest.main()
