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

if __name__ == '__main__':
    unittest.main()
