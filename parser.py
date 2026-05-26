# a parse takes a list of tokens and returns an AST
from dataclasses import dataclass
from lexer import Token, TokenType

# Conceptual Structure
# EXPR := LAMBDA | LET | ADD
# LAMBDA := '/' IDENT '->' EXPR
# LET := 'let' IDENT (':' TYPE)? '=' EXPR 'in' EXPR
# ADD := APP ('+' APP)*
# ATOM := IDENT | '(' EXPR (':' TYPE)? ')'
# APP := atom atom*
#
# TYPE := 'forall' IDENT+ '.' TYPE | TATOM ('->' TYPE)?
# TATOM := 'Int' | IDENT | '(' TYPE ')'


@dataclass(frozen=True)
class IntType:
    pass


@dataclass(frozen=True)
class FunType:
    param: "Type"
    result: "Type"


@dataclass(frozen=True)
class TVar:
    name: str


@dataclass(frozen=True)
class Forall:
    var: str
    body: "Type"


# Existential type variable (α̂). Never produced by the parser; the
# typechecker creates these as placeholders for types it hasn't solved yet.
@dataclass(frozen=True)
class Exists:
    name: str


Type = FunType | IntType | TVar | Forall | Exists


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Lam:
    param: str
    body: "Expr"


@dataclass(frozen=True)
class App:
    func: "Expr"
    arg: "Expr"


@dataclass(frozen=True)
class IntLit:
    value: int


@dataclass(frozen=True)
class Add:
    lhs: "Expr"
    rhs: "Expr"


@dataclass(frozen=True)
class Anno:
    expr: "Expr"
    type: Type


# let name : type = value in body. `type` is None when unannotated.
@dataclass(frozen=True)
class Let:
    name: str
    type: Type | None
    value: "Expr"
    body: "Expr"


Expr = Var | Lam | App | IntLit | Add | Anno | Let


# A REPL definition: `let name : type = value` with no `in`.
@dataclass(frozen=True)
class Definition:
    name: str
    type: Type | None
    value: Expr


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
            if self.peek().type == TokenType.COLON:
                self.incr()
                exprv = Anno(exprv, self.parse_type())
            self.expect(TokenType.RPAREN)
            return exprv
        if nextv.type == TokenType.INT:
            self.incr()
            return IntLit(int(nextv.value))
        raise SyntaxError("Failed to parse atom")

    def parse_lam(self):
        self.expect(TokenType.LAMBDA)
        param = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.ARROW)
        body = self.parse_expr()
        return Lam(param.value, body)

    def parse_let_header(self):
        """'let' IDENT (':' TYPE)? '=' EXPR, shared by `let ... in` and
        REPL definitions."""
        self.expect(TokenType.LET)
        name = self.expect(TokenType.IDENTIFIER).value
        annotation = None
        if self.peek().type == TokenType.COLON:
            self.incr()
            annotation = self.parse_type()
        self.expect(TokenType.EQUALS)
        return name, annotation, self.parse_expr()

    def parse_let(self):
        name, annotation, value = self.parse_let_header()
        self.expect(TokenType.IN)
        return Let(name, annotation, value, self.parse_expr())

    def parse_addexpr(self):
        lhs = self.parse_app()
        while self.peek().type == TokenType.PLUS:
            self.incr()
            lhs = Add(lhs, self.parse_app())
        return lhs

    def parse_app(self):
        cur = self.parse_atom()
        while True:
            next_tok_type = self.peek().type
            if (
                next_tok_type == TokenType.IDENTIFIER
                or next_tok_type == TokenType.LPAREN
                or next_tok_type == TokenType.INT
            ):
                cur = App(cur, self.parse_atom())
            else:
                return cur

    def parse_type_atom(self):
        nextv = self.peek()
        if nextv.type == TokenType.INT_TYPE:
            self.incr()
            return IntType()
        if nextv.type == TokenType.IDENTIFIER:
            self.incr()
            return TVar(nextv.value)
        if nextv.type == TokenType.LPAREN:
            self.incr()
            typev = self.parse_type()
            self.expect(TokenType.RPAREN)
            return typev
        raise SyntaxError("Failed to parse type atom")

    def parse_type(self):
        if self.peek().type == TokenType.FORALL:
            self.incr()
            # forall a b. T is shorthand for forall a. forall b. T
            names = [self.expect(TokenType.IDENTIFIER).value]
            while self.peek().type == TokenType.IDENTIFIER:
                names.append(self.expect(TokenType.IDENTIFIER).value)
            self.expect(TokenType.DOT)
            t = self.parse_type()
            for name in reversed(names):
                t = Forall(name, t)
            return t
        param = self.parse_type_atom()
        if self.peek().type == TokenType.ARROW:
            self.incr()
            return FunType(param, self.parse_type())
        return param

    def parse_expr(self):
        t = self.peek().type
        if t == TokenType.LAMBDA:
            return self.parse_lam()
        if t == TokenType.LET:
            return self.parse_let()
        return self.parse_addexpr()

    def __call__(self):
        v = self.parse_expr()
        self.expect(TokenType.EOF)
        return v

    def parse_repl_input(self) -> Expr | Definition:
        """An expression, or a `let` without `in` that defines a name."""
        if self.peek().type != TokenType.LET:
            return self()
        name, annotation, value = self.parse_let_header()
        if self.peek().type == TokenType.EOF:
            return Definition(name, annotation, value)
        self.expect(TokenType.IN)
        v = Let(name, annotation, value, self.parse_expr())
        self.expect(TokenType.EOF)
        return v
