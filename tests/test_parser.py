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
    Let,
    Definition,
    Con,
    TCon,
    TypeDecl,
    DeclGroup,
    Program,
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

    def test_parse_forall_binder_list(self):
        self.assertEqual(
            self.parse_type("forall a b. a -> b"),
            Forall("a", Forall("b", FunType(TVar("a"), TVar("b")))),
        )

    def test_parse_type_application(self):
        self.assertEqual(self.parse_type("List a"), TCon("List", (TVar("a"),)))

    def test_parse_nested_type_application(self):
        self.assertEqual(
            self.parse_type("Option (List Int)"),
            TCon("Option", (TCon("List", (IntType(),)),)),
        )

    def test_type_application_binds_tighter_than_arrow(self):
        a = TVar("a")
        self.assertEqual(
            self.parse_type("List a -> Option a"),
            FunType(TCon("List", (a,)), TCon("Option", (a,))),
        )

    def test_parse_nullary_type(self):
        self.assertEqual(self.parse_type("Bool -> Bool"), FunType(TCon("Bool"), TCon("Bool")))

    def test_parse_nested_forall(self):
        self.assertEqual(
            self.parse_type("forall a. forall b. a -> b"),
            Forall("a", Forall("b", FunType(TVar("a"), TVar("b")))),
        )


class TestParseDeclarations(unittest.TestCase):
    def parse_program(self, src):
        return Parser(lex(src)).parse_program()

    def parse_decl(self, src):
        program = self.parse_program(src)
        (group,) = program.items
        (decl,) = group.decls
        return decl

    def test_bool(self):
        self.assertEqual(
            self.parse_decl("type Bool = True | False"),
            TypeDecl("Bool", (), (("True", ()), ("False", ()))),
        )

    def test_option(self):
        self.assertEqual(
            self.parse_decl("type Option a = None | Some a"),
            TypeDecl("Option", ("a",), (("None", ()), ("Some", (TVar("a"),)))),
        )

    def test_list(self):
        a = TVar("a")
        self.assertEqual(
            self.parse_decl("type List a = Nil | Cons a (List a)"),
            TypeDecl(
                "List", ("a",), (("Nil", ()), ("Cons", (a, TCon("List", (a,)))))
            ),
        )

    def test_tree_with_leading_bar(self):
        a = TVar("a")
        tree = TCon("Tree", (a,))
        self.assertEqual(
            self.parse_decl("type Tree a =\n  | Leaf\n  | Node (Tree a) a (Tree a)"),
            TypeDecl("Tree", ("a",), (("Leaf", ()), ("Node", (tree, a, tree)))),
        )

    def test_polymorphic_field(self):
        decl = self.parse_decl("type Poly = Poly (forall a. a -> a)")
        self.assertEqual(
            decl.constructors,
            (("Poly", (Forall("a", FunType(TVar("a"), TVar("a"))),)),),
        )

    def test_consecutive_declarations_form_one_group(self):
        program = self.parse_program(
            "type Tree = Node Forest  type Forest = Empty | Trees Tree Forest"
        )
        (group,) = program.items
        self.assertEqual([d.name for d in group.decls], ["Tree", "Forest"])

    def test_program_items_and_expression(self):
        program = self.parse_program(
            "type Option a = None | Some a\n"
            "let x = Some 1\n"
            "let y = 2 in x"
        )
        self.assertIsInstance(program.items[0], DeclGroup)
        self.assertEqual(program.items[1], Definition("x", None, App(Con("Some"), IntLit(1))))
        self.assertEqual(program.expr, Let("y", None, IntLit(2), Var("x")))

    def test_program_without_expression(self):
        program = self.parse_program("let x = 1 let y = x")
        self.assertEqual(len(program.items), 2)
        self.assertIsNone(program.expr)

    def test_expression_only_program(self):
        self.assertEqual(self.parse_program("1 + 2").items, ())

    def test_constructor_expression(self):
        self.assertEqual(
            Parser(lex("Cons 1 Nil"))(),
            App(App(Con("Cons"), IntLit(1)), Con("Nil")),
        )

    def test_missing_constructor(self):
        with self.assertRaises(SyntaxError):
            self.parse_program("type T =")


class TestParseLet(unittest.TestCase):
    def test_parse_let(self):
        self.assertEqual(
            Parser(lex("let x = 1 in x + 2"))(),
            Let("x", None, IntLit(1), Add(Var("x"), IntLit(2))),
        )

    def test_parse_annotated_let(self):
        self.assertEqual(
            Parser(lex("let id : forall a. a -> a = /x -> x in id"))(),
            Let(
                "id",
                Forall("a", FunType(TVar("a"), TVar("a"))),
                Lam("x", Var("x")),
                Var("id"),
            ),
        )

    def test_lambda_in_let_value_stops_at_in(self):
        self.assertEqual(
            Parser(lex("let f = /x -> x in f 1"))(),
            Let("f", None, Lam("x", Var("x")), App(Var("f"), IntLit(1))),
        )

    def test_nested_let(self):
        self.assertEqual(
            Parser(lex("let x = 1 in let y = x in y"))(),
            Let("x", None, IntLit(1), Let("y", None, Var("x"), Var("y"))),
        )

    def test_let_requires_in(self):
        with self.assertRaises(SyntaxError):
            Parser(lex("let x = 1"))()

    def test_repl_definition(self):
        self.assertEqual(
            Parser(lex("let x : Int = 1")).parse_repl_input(),
            Definition("x", IntType(), IntLit(1)),
        )

    def test_repl_let_in_is_an_expression(self):
        self.assertEqual(
            Parser(lex("let x = 1 in x")).parse_repl_input(),
            Let("x", None, IntLit(1), Var("x")),
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
