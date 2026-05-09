from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    LAMBDA = auto()
    ARROW = auto()
    LPAREN = auto()
    RPAREN = auto()
    IDENTIFIER = auto()
    INT = auto()
    PLUS = auto()
    COLON = auto()
    DOT = auto()
    FORALL = auto()
    INT_TYPE = auto()
    EOF = auto()


KEYWORDS = {"forall": TokenType.FORALL, "Int": TokenType.INT_TYPE}


@dataclass
class Token:
    type: TokenType
    value: str


def lex(text: str) -> list[Token]:
    tokens = []
    t = enumerate(text)
    while True:
        try:
            idx, char = next(t)
            match char:
                case "(":
                    tokens.append(Token(TokenType.LPAREN, char))
                case ")":
                    tokens.append(Token(TokenType.RPAREN, char))
                case "/":
                    tokens.append(Token(TokenType.LAMBDA, char))
                case "+":
                    tokens.append(Token(TokenType.PLUS, "+"))
                case ":":
                    tokens.append(Token(TokenType.COLON, char))
                case ".":
                    tokens.append(Token(TokenType.DOT, char))
                case "-":
                    try:
                        next_idx, next_char = next(t)
                        if next_char != ">":
                            raise SyntaxError(
                                f"Expected `>` after `-`, but encountered {next_char}"
                            )
                        tokens.append(Token(TokenType.ARROW, "->"))
                    except StopIteration:
                        raise SyntaxError("Expected `>` after `-`, but encountered EOF")
                case _ if char.isnumeric():
                    n = char
                    while idx + 1 < len(text) and text[idx + 1].isnumeric():
                        idx += 1
                        n += next(t)[1]
                    tokens.append(Token(TokenType.INT, n))
                case _ if char.isspace():
                    pass
                case _ if char.isalpha() or char == "_":
                    name = char
                    while idx + 1 < len(text) and (
                        text[idx + 1].isalnum() or text[idx + 1] == "_"
                    ):
                        name += next(t)[1]
                        idx += 1
                    tokens.append(
                        Token(KEYWORDS.get(name, TokenType.IDENTIFIER), name)
                    )
                case _:
                    raise SyntaxError(
                        f"Unexpected character {char}. Don't know how to process it"
                    )
        except StopIteration:
            tokens.append(Token(TokenType.EOF, "EOF"))
            return tokens
