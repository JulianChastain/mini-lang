# a parse takes a list of tokens and returns an AST
from dataclasses import dataclass
from lexer import Token, TokenType

# Conceptual Structure
# EXPR := LAMBDA | APP
# LAMBDA := '/' IDENT '->' EXPR
# ATOM := IDENT | '(' EXPR ')'
# APP := atom atom*


@dataclass
class Var:
    name: str


@dataclass
class Lam:
    param: str
    body: "Expr"


@dataclass
class App:
    func: "Expr"
    arg: "Expr"


Expr = Var | Lam | App


@dataclass
class Parser:
    Input: list[Token]
    Idx: int = 0

    def peek(self):
        return self.Input[self.Idx]

    def incr(self):
        self.Idx += 1

    def expect(self, v: TokenType):
        val = self.Input[self.Idx]
        if not val.type == v:
            raise SyntaxError(f"Expected {v} but got {self.Input[self.Idx].type}")
        self.incr()
        return val

    def parse_atom(self):
        nextv = self.peek()
        if nextv.type == TokenType.IDENTIFIER:
            self.incr()
            return Var(nextv.value)
        if nextv.type == TokenType.LPAREN:
            self.incr()
            exprv = self.parse_expr()
            self.expect(TokenType.RPAREN)
            return exprv
        raise SyntaxError("Failed to parse atom")

    def parse_lam(self):
        self.expect(TokenType.LAMBDA)
        param = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.ARROW)
        body = self.parse_expr()
        return Lam(param.value, body)

    def parse_app(self):
        cur = self.parse_atom()
        while True:
            next_tok_type = self.peek().type
            if (
                next_tok_type == TokenType.IDENTIFIER
                or next_tok_type == TokenType.LPAREN
            ):
                cur = App(cur, self.parse_atom())
            else:
                return cur

    def parse_expr(self):
        t = self.peek().type
        if t == TokenType.LAMBDA:
            return self.parse_lam()
        return self.parse_app()

    def __call__(self):
        v = self.parse_expr()
        self.expect(TokenType.EOF)
        return v
