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

    def test_lex_declaration_tokens(self):
        types = [t.type for t in lex("type List a = Nil | Cons a (List a)")]
        self.assertEqual(
            types,
            [
                TokenType.TYPE,
                TokenType.UIDENT,
                TokenType.IDENTIFIER,
                TokenType.EQUALS,
                TokenType.UIDENT,
                TokenType.BAR,
                TokenType.UIDENT,
                TokenType.IDENTIFIER,
                TokenType.LPAREN,
                TokenType.UIDENT,
                TokenType.IDENTIFIER,
                TokenType.RPAREN,
                TokenType.EOF,
            ],
        )

    def test_lex_match_tokens(self):
        types = [t.type for t in lex("match p with | (x, _) -> x")]
        self.assertEqual(
            types,
            [
                TokenType.MATCH,
                TokenType.IDENTIFIER,
                TokenType.WITH,
                TokenType.BAR,
                TokenType.LPAREN,
                TokenType.IDENTIFIER,
                TokenType.COMMA,
                TokenType.UNDERSCORE,
                TokenType.RPAREN,
                TokenType.ARROW,
                TokenType.IDENTIFIER,
                TokenType.EOF,
            ],
        )

    def test_underscore_prefix_is_still_an_identifier(self):
        self.assertEqual(lex("_x")[0].type, TokenType.IDENTIFIER)
        self.assertEqual(lex("_")[0].type, TokenType.UNDERSCORE)

    def test_lex_rec(self):
        self.assertEqual(lex("let rec")[1].type, TokenType.REC)

    def test_capitalized_names_are_uident(self):
        tokens = lex("Some x Int")
        self.assertEqual(
            [t.type for t in tokens[:3]],
            [TokenType.UIDENT, TokenType.IDENTIFIER, TokenType.INT_TYPE],
        )

    def test_lex_operators(self):
        types = [t.type for t in lex("a-b*c == d < e = f -> g")]
        self.assertEqual(
            types,
            [
                TokenType.IDENTIFIER,
                TokenType.MINUS,
                TokenType.IDENTIFIER,
                TokenType.STAR,
                TokenType.IDENTIFIER,
                TokenType.EQEQ,
                TokenType.IDENTIFIER,
                TokenType.LT,
                TokenType.IDENTIFIER,
                TokenType.EQUALS,
                TokenType.IDENTIFIER,
                TokenType.ARROW,
                TokenType.IDENTIFIER,
                TokenType.EOF,
            ],
        )

    def test_minus_at_end(self):
        self.assertEqual(lex("-")[0].type, TokenType.MINUS)

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
        self.assertEqual(tokens[0].type, TokenType.UIDENT)
        self.assertEqual(tokens[1].type, TokenType.IDENTIFIER)


if __name__ == "__main__":
    unittest.main()
