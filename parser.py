# a parse takes a list of tokens and returns an AST
from dataclasses import dataclass
from lexer import Token, TokenType

# Conceptual Structure
# PROGRAM := ITEM* EXPR?
# ITEM := DECL+ | 'let' 'rec'? IDENT (':' TYPE)? '=' EXPR      (no `in`)
# DECL := 'type' UIDENT IDENT* '=' '|'? CON ('|' CON)*
# CON := UIDENT TATOM*
#
# EXPR := LAMBDA | LET | MATCH | IF | ADD
# LAMBDA := '/' IDENT '->' EXPR
# LET := 'let' 'rec'? IDENT (':' TYPE)? '=' EXPR 'in' EXPR
# MATCH := 'match' EXPR 'with' '|'? BRANCH ('|' BRANCH)*
# BRANCH := PAT '->' EXPR
# IF := 'if' EXPR 'then' EXPR 'else' EXPR       (a match on True/False)
# ADD := APP ('+' APP)*
# ATOM := IDENT | UIDENT | INT | '(' EXPR (':' TYPE)? ')'
# APP := atom atom*
#
# TYPE := 'forall' IDENT+ '.' TYPE | TAPP ('->' TYPE)?
# TAPP := UIDENT TATOM* | TATOM
# TATOM := 'Int' | IDENT | UIDENT | '(' TYPE ')'
#
# PAT := UIDENT PATOM* | PATOM
# PATOM := IDENT | '_' | INT | UIDENT | '(' PAT ')'


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


# A declared type applied to its arguments, e.g. List Int or Option (List a).
@dataclass(frozen=True)
class TCon:
    name: str
    args: tuple["Type", ...] = ()


Type = FunType | IntType | TVar | Forall | Exists | TCon


@dataclass(frozen=True)
class Var:
    name: str


# A constructor, e.g. Some or Nil. Applied with ordinary application.
@dataclass(frozen=True)
class Con:
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


# let [rec] name : type = value in body. `type` is None when unannotated,
# which `let rec` doesn't allow.
@dataclass(frozen=True)
class Let:
    name: str
    type: Type | None
    value: "Expr"
    body: "Expr"
    rec: bool = False


@dataclass(frozen=True)
class PVar:
    name: str


@dataclass(frozen=True)
class PWild:
    pass


@dataclass(frozen=True)
class PInt:
    value: int


@dataclass(frozen=True)
class PCon:
    name: str
    args: tuple["Pattern", ...] = ()


Pattern = PVar | PWild | PInt | PCon


# match scrutinee with | pattern -> body | ...
@dataclass(frozen=True)
class Match:
    scrutinee: "Expr"
    branches: tuple[tuple[Pattern, "Expr"], ...]


Expr = Var | Con | Lam | App | IntLit | Add | Anno | Let | Match


# A top-level definition: `let [rec] name : type = value` with no `in`.
@dataclass(frozen=True)
class Definition:
    name: str
    type: Type | None
    value: Expr
    rec: bool = False


# type Name params = Con1 fields | Con2 fields | ...
@dataclass(frozen=True)
class TypeDecl:
    name: str
    params: tuple[str, ...]
    constructors: tuple[tuple[str, tuple[Type, ...]], ...]


# Consecutive type declarations, which may refer to each other.
@dataclass(frozen=True)
class DeclGroup:
    decls: tuple[TypeDecl, ...]


Item = DeclGroup | Definition


# Top-level items, then an optional final expression.
@dataclass(frozen=True)
class Program:
    items: tuple[Item, ...]
    expr: Expr | None


_ATOM_START = (TokenType.IDENTIFIER, TokenType.UIDENT, TokenType.LPAREN, TokenType.INT)
_PATTERN_ATOM_START = (
    TokenType.IDENTIFIER,
    TokenType.UNDERSCORE,
    TokenType.INT,
    TokenType.UIDENT,
    TokenType.LPAREN,
)
_TYPE_ATOM_START = (
    TokenType.INT_TYPE,
    TokenType.IDENTIFIER,
    TokenType.UIDENT,
    TokenType.LPAREN,
)


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
        if nextv.type == TokenType.UIDENT:
            self.incr()
            return Con(nextv.value)
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
        """'let' 'rec'? IDENT (':' TYPE)? '=' EXPR, shared by `let ... in`
        and top-level definitions."""
        self.expect(TokenType.LET)
        rec = self.peek().type == TokenType.REC
        if rec:
            self.incr()
        name = self.expect(TokenType.IDENTIFIER).value
        annotation = None
        if self.peek().type == TokenType.COLON:
            self.incr()
            annotation = self.parse_type()
        elif rec:
            # The paper doesn't generalize, and a recursive use would need
            # the type before inferring it, so it has to be written down.
            raise SyntaxError(f"let rec {name} needs a type annotation")
        self.expect(TokenType.EQUALS)
        return name, annotation, self.parse_expr(), rec

    def parse_let(self):
        name, annotation, value, rec = self.parse_let_header()
        self.expect(TokenType.IN)
        return Let(name, annotation, value, self.parse_expr(), rec)

    def parse_addexpr(self):
        lhs = self.parse_app()
        while self.peek().type == TokenType.PLUS:
            self.incr()
            lhs = Add(lhs, self.parse_app())
        return lhs

    def parse_app(self):
        cur = self.parse_atom()
        while self.peek().type in _ATOM_START:
            cur = App(cur, self.parse_atom())
        return cur

    def parse_type_atom(self):
        nextv = self.peek()
        if nextv.type == TokenType.INT_TYPE:
            self.incr()
            return IntType()
        if nextv.type == TokenType.IDENTIFIER:
            self.incr()
            return TVar(nextv.value)
        if nextv.type == TokenType.UIDENT:
            # A bare type name; applied types need parentheses here.
            self.incr()
            return TCon(nextv.value)
        if nextv.type == TokenType.LPAREN:
            self.incr()
            typev = self.parse_type()
            self.expect(TokenType.RPAREN)
            return typev
        raise SyntaxError("Failed to parse type atom")

    def parse_type_app(self):
        if self.peek().type != TokenType.UIDENT:
            return self.parse_type_atom()
        name = self.expect(TokenType.UIDENT).value
        args = []
        while self.peek().type in _TYPE_ATOM_START:
            args.append(self.parse_type_atom())
        return TCon(name, tuple(args))

    def parse_decl(self) -> TypeDecl:
        self.expect(TokenType.TYPE)
        name = self.expect(TokenType.UIDENT).value
        params = []
        while self.peek().type == TokenType.IDENTIFIER:
            params.append(self.expect(TokenType.IDENTIFIER).value)
        self.expect(TokenType.EQUALS)
        if self.peek().type == TokenType.BAR:
            self.incr()
        constructors = [self.parse_constructor()]
        while self.peek().type == TokenType.BAR:
            self.incr()
            constructors.append(self.parse_constructor())
        return TypeDecl(name, tuple(params), tuple(constructors))

    def parse_constructor(self) -> tuple[str, tuple[Type, ...]]:
        name = self.expect(TokenType.UIDENT).value
        fields = []
        while self.peek().type in _TYPE_ATOM_START:
            fields.append(self.parse_type_atom())
        return name, tuple(fields)

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
        param = self.parse_type_app()
        if self.peek().type == TokenType.ARROW:
            self.incr()
            return FunType(param, self.parse_type())
        return param

    def parse_match(self) -> Match:
        self.expect(TokenType.MATCH)
        scrutinee = self.parse_expr()
        self.expect(TokenType.WITH)
        if self.peek().type == TokenType.BAR:
            self.incr()
        branches = [self.parse_branch()]
        while self.peek().type == TokenType.BAR:
            self.incr()
            branches.append(self.parse_branch())
        return Match(scrutinee, tuple(branches))

    def parse_if(self) -> Match:
        """`if c then a else b` is a match on the declared type Bool, so
        typing, evaluation and exhaustiveness need nothing extra."""
        self.expect(TokenType.IF)
        cond = self.parse_expr()
        self.expect(TokenType.THEN)
        then = self.parse_expr()
        self.expect(TokenType.ELSE)
        otherwise = self.parse_expr()
        return Match(cond, ((PCon("True"), then), (PCon("False"), otherwise)))

    def parse_branch(self) -> tuple[Pattern, Expr]:
        pattern = self.parse_pattern()
        self.expect(TokenType.ARROW)
        # The body extends as far right as possible, so a match nested in
        # a body that isn't the last one needs parentheses.
        return pattern, self.parse_expr()

    def parse_pattern(self) -> Pattern:
        if self.peek().type != TokenType.UIDENT:
            return self.parse_pattern_atom()
        name = self.expect(TokenType.UIDENT).value
        args = []
        while self.peek().type in _PATTERN_ATOM_START:
            args.append(self.parse_pattern_atom())
        return PCon(name, tuple(args))

    def parse_pattern_atom(self) -> Pattern:
        tok = self.peek()
        self.incr()
        match tok.type:
            case TokenType.IDENTIFIER:
                return PVar(tok.value)
            case TokenType.UNDERSCORE:
                return PWild()
            case TokenType.INT:
                return PInt(int(tok.value))
            case TokenType.UIDENT:
                return PCon(tok.value)
            case TokenType.LPAREN:
                pattern = self.parse_pattern()
                self.expect(TokenType.RPAREN)
                return pattern
        raise SyntaxError(f"Expected a pattern but got {tok.type}")

    def parse_expr(self):
        t = self.peek().type
        if t == TokenType.LAMBDA:
            return self.parse_lam()
        if t == TokenType.LET:
            return self.parse_let()
        if t == TokenType.MATCH:
            return self.parse_match()
        if t == TokenType.IF:
            return self.parse_if()
        return self.parse_addexpr()

    def __call__(self):
        v = self.parse_expr()
        self.expect(TokenType.EOF)
        return v

    def parse_repl_input(self) -> Expr | Definition:
        """An expression, or a `let` without `in` that defines a name."""
        program = self.parse_program()
        match program:
            case Program((), expr) if expr is not None:
                return expr
            case Program((Definition() as d,), None):
                return d
        raise SyntaxError("Expected one expression or definition")

    def parse_program(self) -> Program:
        """Items, then an optional final expression.

        Items always start with `type` or `let`. A `let` followed by `in` is
        the final expression rather than a definition. A plain expression
        after definitions would be swallowed by the last definition's body
        (`let x = f a  g x` reads as f a g x), so it needs to start with a
        keyword; otherwise define `main` instead.
        """
        items: list[Item] = []
        while True:
            t = self.peek().type
            if t == TokenType.TYPE:
                decls = []
                while self.peek().type == TokenType.TYPE:
                    decls.append(self.parse_decl())
                items.append(DeclGroup(tuple(decls)))
            elif t == TokenType.LET:
                start = self.Idx
                name, annotation, value, rec = self.parse_let_header()
                if self.peek().type == TokenType.IN:
                    self.Idx = start
                    break
                items.append(Definition(name, annotation, value, rec))
            else:
                break
        expr = None if self.peek().type == TokenType.EOF else self.parse_expr()
        self.expect(TokenType.EOF)
        return Program(tuple(items), expr)
