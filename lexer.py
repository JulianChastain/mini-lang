from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    LAMBDA = auto()
    ARROW = auto()
    LPAREN = auto()
    RPAREN = auto()
    IDENTIFIER = auto()
    UIDENT = auto()  # capitalized: constructor and type names
    INT = auto()
    PLUS = auto()
    COLON = auto()
    DOT = auto()
    FORALL = auto()
    INT_TYPE = auto()
    LET = auto()
    IN = auto()
    EQUALS = auto()
    TYPE = auto()
    MATCH = auto()
    WITH = auto()
    REC = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    BAR = auto()
    COMMA = auto()
    UNDERSCORE = auto()  # `_` on its own, the wildcard pattern
    EOF = auto()


KEYWORDS = {
    "forall": TokenType.FORALL,
    "Int": TokenType.INT_TYPE,
    "let": TokenType.LET,
    "in": TokenType.IN,
    "type": TokenType.TYPE,
    "match": TokenType.MATCH,
    "with": TokenType.WITH,
    "rec": TokenType.REC,
    "if": TokenType.IF,
    "then": TokenType.THEN,
    "else": TokenType.ELSE,
}


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
                case "=":
                    tokens.append(Token(TokenType.EQUALS, char))
                case "|":
                    tokens.append(Token(TokenType.BAR, char))
                case ",":
                    tokens.append(Token(TokenType.COMMA, char))
                case "-":
                    try:
                        next_idx, next_char = next(t)
                        if next_char == "-":
                            # `--` comments run to the end of the line
                            for _, c in t:
                                if c == "\n":
                                    break
                            continue
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
                    if name in KEYWORDS:
                        kind = KEYWORDS[name]
                    elif name == "_":
                        kind = TokenType.UNDERSCORE
                    elif name[0].isupper():
                        kind = TokenType.UIDENT
                    else:
                        kind = TokenType.IDENTIFIER
                    tokens.append(Token(kind, name))
                case _:
                    raise SyntaxError(
                        f"Unexpected character {char}. Don't know how to process it"
                    )
        except StopIteration:
            tokens.append(Token(TokenType.EOF, "EOF"))
            return tokens
