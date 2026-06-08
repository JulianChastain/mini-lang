import unittest
from lexer import lex
from parser import Parser, IntType, FunType, TVar, Forall, TCon
from context import Context, TypeTable, show_type
from errors import TypeCheckError
from types_table import declare_group


def declare(src, table=TypeTable()):
    for group in Parser(lex(src)).parse_program().items:
        table = declare_group(table, group)
    return table


PRELUDE = """
type Bool = True | False
type Option a = None | Some a
type List a = Nil | Cons a (List a)
type Tree a = Leaf | Node (Tree a) a (Tree a)
"""


class TestDeclare(unittest.TestCase):
    def test_constructor_schemes(self):
        table = declare(PRELUDE)
        self.assertEqual(
            show_type(table.ctors["Cons"].scheme), "forall a. a -> List a -> List a"
        )
        self.assertEqual(show_type(table.ctors["Nil"].scheme), "forall a. List a")
        self.assertEqual(show_type(table.ctors["True"].scheme), "Bool")
        self.assertEqual(
            show_type(table.ctors["Node"].scheme),
            "forall a. Tree a -> a -> Tree a -> Tree a",
        )

    def test_type_info(self):
        table = declare(PRELUDE)
        self.assertEqual(table.types["Option"].params, ("a",))
        self.assertEqual(table.types["List"].constructors, ("Nil", "Cons"))

    def test_mutually_recursive_group(self):
        table = declare(
            "type Rose a = Rose a (Forest a)"
            " type Forest a = Empty | Grow (Rose a) (Forest a)"
        )
        self.assertEqual(
            show_type(table.ctors["Grow"].scheme),
            "forall a. Rose a -> Forest a -> Forest a",
        )

    def test_separate_groups_cannot_refer_forward(self):
        with self.assertRaises(TypeCheckError):
            declare("type A = A B\nlet x = 1\ntype B = B")

    def test_polymorphic_field(self):
        table = declare("type Poly = Poly (forall a. a -> a)")
        self.assertEqual(
            show_type(table.ctors["Poly"].scheme), "(forall a. a -> a) -> Poly"
        )

    def test_does_not_mutate_input_table(self):
        base = declare("type Bool = True | False")
        declare("type Unit = Unit", base)
        self.assertNotIn("Unit", base.types)

    def assertRejected(self, src, fragment):
        with self.assertRaises(TypeCheckError) as caught:
            declare(src)
        self.assertEqual(caught.exception.rule, "Decl")
        self.assertIn(fragment, caught.exception.message)

    def test_wrong_argument_count(self):
        self.assertRejected("type List a = Nil | Cons a (List a a)", "expects 1")
        self.assertRejected("type List a = Nil | Cons a List", "expects 1")

    def test_undeclared_type_variable(self):
        self.assertRejected("type Box = Box a", "isn't a parameter of Box")

    def test_unknown_type(self):
        self.assertRejected("type Box = Box Foo", "unknown type Foo")

    def test_duplicate_constructor(self):
        self.assertRejected("type A = X | X", "constructor X")
        self.assertRejected("type A = X  type B = X", "constructor X")

    def test_duplicate_type(self):
        self.assertRejected("type A = X  type A = Y", "type A")

    def test_repeated_parameter(self):
        self.assertRejected("type P a a = P a", "repeats")

    def test_polytype_argument_rejected(self):
        self.assertRejected(
            "type Option a = None | Some a  type Bad = Bad (Option (forall a. a))",
            "monotypes",
        )


class TestWellFormedDeclaredTypes(unittest.TestCase):
    def setUp(self):
        self.ctx = Context(table=declare(PRELUDE))

    def test_declared_type(self):
        self.assertTrue(self.ctx.well_formed(TCon("List", (IntType(),))))

    def test_wrong_arity(self):
        self.assertFalse(self.ctx.well_formed(TCon("List", ())))

    def test_unknown(self):
        self.assertFalse(self.ctx.well_formed(TCon("Map", ())))

    def test_argument_must_be_monotype(self):
        poly = Forall("a", FunType(TVar("a"), TVar("a")))
        self.assertFalse(self.ctx.well_formed(TCon("List", (poly,))))

    def test_table_survives_scopes(self):
        from context import CTVar

        inner = self.ctx.extend(CTVar("a")).drop(CTVar("a"))
        self.assertIs(inner.table, self.ctx.table)


if __name__ == "__main__":
    unittest.main()
