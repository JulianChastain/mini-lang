import unittest
from lexer import lex, Token, TokenType

class TestLexer(unittest.TestCase):
    def test_lex_parens(self):
        tokens = lex("()")
        self.assertEqual(len(tokens), 3)
        self.assertEqual(tokens[0].type, TokenType.LPAREN)
        self.assertEqual(tokens[1].type, TokenType.RPAREN)
        self.assertEqual(tokens[2].type, TokenType.EOF)

    def test_lex_lambda(self):
        tokens = lex("/x -> x")
        self.assertEqual(len(tokens), 5)
        self.assertEqual(tokens[0].type, TokenType.LAMBDA)
        self.assertEqual(tokens[1].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[1].value, "x")
        self.assertEqual(tokens[2].type, TokenType.ARROW)
        self.assertEqual(tokens[3].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[3].value, "x")
        self.assertEqual(tokens[4].type, TokenType.EOF)

    def test_lex_lambda_application(self):
        tokens = lex("(/x -> x) y")
        self.assertEqual(len(tokens), 8)
        self.assertEqual(tokens[0].type, TokenType.LPAREN)
        self.assertEqual(tokens[1].type, TokenType.LAMBDA)
        self.assertEqual(tokens[2].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[2].value, "x")
        self.assertEqual(tokens[3].type, TokenType.ARROW)
        self.assertEqual(tokens[4].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[4].value, "x")
        self.assertEqual(tokens[5].type, TokenType.RPAREN)
        self.assertEqual(tokens[6].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[6].value, "y")
        self.assertEqual(tokens[7].type, TokenType.EOF)

    def test_lex_let(self):
        types = [t.type for t in lex("let x = 1 in x")]
        self.assertEqual(
            types,
            [
                TokenType.LET,
                TokenType.IDENTIFIER,
                TokenType.EQUALS,
                TokenType.INT,
                TokenType.IN,
                TokenType.IDENTIFIER,
                TokenType.EOF,
            ],
        )

    def test_keywords_inside_identifiers(self):
        tokens = lex("letter inside")
        self.assertEqual([t.value for t in tokens[:2]], ["letter", "inside"])
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)

    def test_comment_to_end_of_line(self):
        types = [t.type for t in lex("x -- a comment -> y\ny")]
        self.assertEqual(
            types, [TokenType.IDENTIFIER, TokenType.IDENTIFIER, TokenType.EOF]
        )

    def test_comment_at_end_of_input(self):
        self.assertEqual([t.type for t in lex("x -- done")], [TokenType.IDENTIFIER, TokenType.EOF])

    def test_lex_identifier_with_underscore(self):
        tokens = lex("foo_bar _x x_1")
        self.assertEqual(len(tokens), 4)
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[0].value, "foo_bar")
        self.assertEqual(tokens[1].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[1].value, "_x")
        self.assertEqual(tokens[2].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[2].value, "x_1")
        self.assertEqual(tokens[3].type, TokenType.EOF)

    def test_lex_annotation(self):
        tokens = lex("(x : Int)")
        self.assertEqual(
            [t.type for t in tokens],
            [
                TokenType.LPAREN,
                TokenType.IDENTIFIER,
                TokenType.COLON,
                TokenType.INT_TYPE,
                TokenType.RPAREN,
                TokenType.EOF,
            ],
        )

    def test_lex_forall(self):
        tokens = lex("forall a. a")
        self.assertEqual(
            [t.type for t in tokens],
            [
                TokenType.FORALL,
                TokenType.IDENTIFIER,
                TokenType.DOT,
                TokenType.IDENTIFIER,
                TokenType.EOF,
            ],
        )

    def test_lex_keyword_prefix_is_identifier(self):
        tokens = lex("Integer foralls")
        self.assertEqual(tokens[0].type, TokenType.IDENTIFIER)
        self.assertEqual(tokens[1].type, TokenType.IDENTIFIER)


if __name__ == "__main__":
    unittest.main()
