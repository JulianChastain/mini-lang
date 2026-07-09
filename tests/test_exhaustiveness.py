import unittest
from lexer import lex
from parser import Parser, TCon, IntType, TVar
from context import TypeTable
from errors import TypeCheckError
from types_table import declare_group
from type_checker import typecheck
from exhaustiveness import missing_case, useless_branches
from program import Session, Warning, Result
from patterns import show_pattern

DATA = """
type Bool = True | False
type Option a = None | Some a
type List a = Nil | Cons a (List a)
type Pair a b = Pair a b
"""


def table():
    t = TypeTable()
    for group in Parser(lex(DATA)).parse_program().items:
        t = declare_group(t, group)
    return t


def missing(t, *srcs):
    patterns = [Parser(lex(s)).parse_pattern() for s in srcs]
    w = missing_case(table(), t, patterns)
    return None if w is None else show_pattern(w)


LIST_INT = TCon("List", (IntType(),))
BOOL = TCon("Bool")


class TestMissingCase(unittest.TestCase):
    def test_complete(self):
        self.assertIsNone(missing(LIST_INT, "Nil", "Cons _ _"))

    def test_missing_nil(self):
        self.assertEqual(missing(LIST_INT, "Cons x rest"), "Nil")

    def test_missing_cons(self):
        self.assertEqual(missing(LIST_INT, "Nil"), "Cons _ _")

    def test_wildcard_covers_everything(self):
        self.assertIsNone(missing(LIST_INT, "_"))
        self.assertIsNone(missing(LIST_INT, "Cons 1 _", "xs"))

    def test_nested_missing_case(self):
        self.assertEqual(
            missing(LIST_INT, "Nil", "Cons _ Nil"), "Cons _ (Cons _ _)"
        )

    def test_nested_complete(self):
        self.assertIsNone(missing(LIST_INT, "Nil", "Cons _ Nil", "Cons _ (Cons _ _)"))

    def test_integers_need_a_wildcard(self):
        self.assertEqual(missing(IntType(), "0", "1"), "2")
        self.assertIsNone(missing(IntType(), "0", "n"))

    def test_integer_inside_constructor(self):
        self.assertEqual(missing(LIST_INT, "Nil", "Cons 0 _"), "Cons 1 _")

    def test_two_columns_via_pair(self):
        pair = TCon("Pair", (BOOL, BOOL))
        self.assertEqual(
            missing(pair, "Pair True True", "Pair False _"), "Pair True False"
        )
        self.assertIsNone(missing(pair, "Pair True _", "Pair _ True", "Pair False False"))

    def test_unknown_type_falls_back_to_patterns(self):
        # The column's type is an unsolved existential; the constructors
        # in the patterns still identify it.
        self.assertEqual(missing(None, "Some (Cons _ _)", "None"), "Some Nil")


def check(expr):
    return typecheck(DATA + "let main = " + expr)


class TestTypecheckerRejectsMissingCases(unittest.TestCase):
    def test_match_missing_nil_is_caught(self):
        with self.assertRaises(TypeCheckError) as caught:
            check("/xs -> match xs with | Cons x _ -> x + 1")
        self.assertEqual(caught.exception.rule, "Match")
        self.assertIn("missing: Nil", caught.exception.message)
        self.assertIn("List Int", caught.exception.message)

    def test_complete_match_accepted(self):
        check("/xs -> match xs with | Nil -> 0 | Cons x _ -> x")

    def test_nested_missing_case_reported(self):
        with self.assertRaises(TypeCheckError) as caught:
            check("/o -> match o with | None -> 0 | Some True -> 1")
        self.assertIn("missing: Some False", caught.exception.message)

    def test_integer_match_needs_wildcard(self):
        with self.assertRaises(TypeCheckError) as caught:
            check("/n -> match n with | 0 -> 1 | 1 -> 0")
        self.assertIn("missing: 2", caught.exception.message)

    def test_match_inside_lambda_under_forall(self):
        # The scrutinee's type is only known through the annotation.
        with self.assertRaises(TypeCheckError) as caught:
            check("((/o -> match o with | Some x -> x) : forall a. Option a -> a)")
        self.assertIn("missing: None", caught.exception.message)

    def test_type_solved_after_the_match(self):
        # When the match is checked, o's type is only ^a; applying f to a
        # list later solves it, and the final context gives the real type.
        src = (
            "let f = /o -> match o with | Cons x _ -> x in f (Cons 1 Nil)"
        )
        with self.assertRaises(TypeCheckError) as caught:
            check(src)
        self.assertIn("List Int", caught.exception.message)
        self.assertIn("missing: Nil", caught.exception.message)


def useless(t, *srcs):
    patterns = [Parser(lex(s)).parse_pattern() for s in srcs]
    return useless_branches(table(), t, patterns)


class TestUselessBranches(unittest.TestCase):
    def test_none_useless(self):
        self.assertEqual(useless(LIST_INT, "Nil", "Cons _ _"), [])

    def test_branch_after_wildcard(self):
        self.assertEqual(useless(LIST_INT, "_", "Nil"), [1])

    def test_duplicate_branch(self):
        self.assertEqual(useless(BOOL, "True", "False", "True"), [2])

    def test_covered_by_earlier_branches_together(self):
        self.assertEqual(
            useless(LIST_INT, "Nil", "Cons _ Nil", "Cons _ (Cons _ _)", "Cons _ _"), [3]
        )

    def test_integers(self):
        self.assertEqual(useless(IntType(), "0", "n", "1"), [2])
        self.assertEqual(useless(IntType(), "0", "0", "n"), [1])


class TestWarningsAndExamples(unittest.TestCase):
    def run_source(self, src):
        return Session().run_source(DATA + src)

    def test_useless_branch_is_a_warning(self):
        outputs = self.run_source(
            "let main = match Some 1 with | Some x -> x | None -> 0 | Some 2 -> 2"
        )
        warnings = [o.message for o in outputs if isinstance(o, Warning)]
        self.assertEqual(len(warnings), 1)
        self.assertIn("branch 3 (| Some 2 -> ...) can never match", warnings[0])
        # It still runs.
        self.assertEqual(outputs[-1].value, 1)

    def test_missing_example_is_nested(self):
        with self.assertRaises(TypeCheckError) as caught:
            self.run_source(
                "let f = /xs -> match xs with | Nil -> 0 | Cons x Nil -> x"
            )
        self.assertIn("missing: Cons _ (Cons _ _)", caught.exception.message)

    def test_no_warnings_for_good_match(self):
        outputs = self.run_source("let f = /xs -> match xs with | Nil -> 0 | Cons x _ -> x")
        self.assertFalse(any(isinstance(o, Warning) for o in outputs))


if __name__ == "__main__":
    unittest.main()
