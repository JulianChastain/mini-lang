import unittest
from lexer import lex
from parser import Parser, Match, PVar, PWild, PInt, PCon, Var, IntLit, App, Con
from evaluator import eval, ConValue, MatchError, show_value
from type_checker import show_expr, typecheck
from context import show_type
from errors import TypeCheckError
from program import run as run_program

DECLS = {"Nil": 0, "Cons": 2, "None": 0, "Some": 1, "Leaf": 0, "Node": 3}


def env():
    return {name: ConValue(name, arity) for name, arity in DECLS.items()}


def parse(src):
    return Parser(lex(src))()


def run(src):
    """Evaluate without typechecking: matches aren't typed yet."""
    return show_value(eval(parse(src), env()))


LENGTH = (
    "let rec length : forall a. List a -> Int = /xs -> match xs with"
    " | Nil -> 0"
    " | Cons _ rest -> 1 + length rest in "
)
MAP = (
    "let rec map : forall a b. (a -> b) -> List a -> List b = /f -> /xs -> match xs with"
    " | Nil -> Nil"
    " | Cons x rest -> Cons (f x) (map f rest) in "
)


class TestParseMatch(unittest.TestCase):
    def test_match(self):
        self.assertEqual(
            parse("match x with | Nil -> 0 | Cons y _ -> y"),
            Match(
                Var("x"),
                (
                    (PCon("Nil"), IntLit(0)),
                    (PCon("Cons", (PVar("y"), PWild())), Var("y")),
                ),
            ),
        )

    def test_leading_bar_is_optional(self):
        self.assertEqual(parse("match x with Nil -> 0"), parse("match x with | Nil -> 0"))

    def test_nested_and_integer_patterns(self):
        (pattern, _), = parse("match x with Some (Cons 1 (Cons y Nil)) -> y").branches
        self.assertEqual(
            pattern,
            PCon("Some", (PCon("Cons", (PInt(1), PCon("Cons", (PVar("y"), PCon("Nil"))))),)),
        )

    def test_branch_body_extends_right(self):
        (_, body), = parse("match x with Some f -> f 1").branches
        self.assertEqual(body, App(Var("f"), IntLit(1)))

    def test_show_round_trips(self):
        for src in [
            "match x with | Nil -> 0 | Cons y _ -> y",
            "match x with | Some (Cons 1 Nil) -> 1 | _ -> 0",
            "match x with | Some y -> (match y with | 0 -> 1 | n -> n) | None -> 0",
        ]:
            self.assertEqual(show_expr(parse(src)), src)
            self.assertEqual(parse(show_expr(parse(src))), parse(src))

    def test_bad_pattern(self):
        with self.assertRaises(SyntaxError):
            parse("match x with | /y -> 1")


class TestRunMatch(unittest.TestCase):
    def test_first_matching_branch_wins(self):
        self.assertEqual(run("match Some 1 with | Some _ -> 1 | Some 1 -> 2 | None -> 3"), "1")

    def test_binds_variables(self):
        self.assertEqual(run("match Cons 1 (Cons 2 Nil) with | Cons x (Cons y _) -> x + y"), "3")

    def test_integer_patterns(self):
        src = "(/n -> match n with | 0 -> 100 | 1 -> 200 | m -> m) "
        self.assertEqual([run(src + n) for n in "012"], ["100", "200", "2"])

    def test_nested_constructor_pattern(self):
        self.assertEqual(
            run("match Some (Cons 5 Nil) with | Some (Cons x Nil) -> x | _ -> 0"), "5"
        )

    def test_failed_match_is_a_runtime_error(self):
        with self.assertRaises(MatchError):
            run("match None with | Some x -> x")

    def test_branch_variables_shadow(self):
        self.assertEqual(run("let x = 1 in match Some 2 with | Some x -> x"), "2")

    def test_length(self):
        self.assertEqual(run(LENGTH + "length (Cons 1 (Cons 2 (Cons 3 Nil)))"), "3")

    def test_map(self):
        self.assertEqual(
            run(MAP + "map (/x -> x + 10) (Cons 1 (Cons 2 Nil))"),
            "Cons 11 (Cons 12 Nil)",
        )

    def test_tree(self):
        sum_tree = (
            "let rec sum : Tree Int -> Int = /t -> match t with"
            " | Leaf -> 0"
            " | Node l x r -> sum l + x + sum r in "
        )
        self.assertEqual(run(sum_tree + "sum (Node (Node Leaf 1 Leaf) 2 (Node Leaf 3 Leaf))"), "6")


if __name__ == "__main__":
    unittest.main()


DATA = """
type Bool = True | False
type Option a = None | Some a
type List a = Nil | Cons a (List a)
type Tree a = Leaf | Node (Tree a) a (Tree a)
"""


def type_of(src):
    return show_type(typecheck(DATA + "let main = " + src))


class TestTypeMatch(unittest.TestCase):
    def test_length(self):
        self.assertEqual(type_of(LENGTH + "length"), "forall a. List a -> Int")

    def test_map(self):
        self.assertEqual(
            type_of(MAP + "map"), "forall a b. (a -> b) -> List a -> List b"
        )

    def test_foldr(self):
        src = (
            "let rec foldr : forall a b. (a -> b -> b) -> b -> List a -> b ="
            " /f -> /z -> /xs -> match xs with"
            " | Nil -> z"
            " | Cons x rest -> f x (foldr f z rest) in foldr"
        )
        self.assertEqual(type_of(src), "forall a b. (a -> b -> b) -> b -> List a -> b")

    def test_length_and_map_run(self):
        src = DATA + "let main = " + LENGTH + MAP + "length (map (/x -> x + 1) (Cons 1 (Cons 2 Nil)))"
        self.assertEqual(run_program(src), ("Int", "2"))
        src = DATA + "let main = " + MAP + "map (/x -> Some x) (Cons 1 (Cons 2 Nil))"
        self.assertEqual(
            run_program(src), ("List (Option Int)", "Cons (Some 1) (Cons (Some 2) Nil)")
        )

    def test_field_type_mismatch_rejected(self):
        src = (
            "(/xs -> match xs with | Cons x _ -> x + 1 | Nil -> 0)"
            " (Cons True Nil)"
        )
        with self.assertRaises(TypeCheckError):
            type_of(src)

    def test_annotated_list_bool_rejects_arithmetic(self):
        src = (
            "((/xs -> match xs with | Cons x _ -> x + 1 | Nil -> 0)"
            " : List Bool -> Int)"
        )
        with self.assertRaises(TypeCheckError) as caught:
            type_of(src)
        self.assertEqual(caught.exception.message, "Bool is not a subtype of Int")

    def test_unannotated_match_is_inferred(self):
        # The scrutinee's α̂ is split by the first constructor pattern and
        # the result gets a fresh β̂, like a lambda's.
        self.assertEqual(
            type_of("/o -> match o with | None -> 0 | Some n -> n + 1"),
            "Option Int -> Int",
        )

    def test_polymorphic_inferred_match(self):
        self.assertEqual(
            type_of("/o -> /d -> match o with | None -> d | Some x -> x"),
            "forall a. Option a -> a -> a",
        )

    def test_integer_patterns(self):
        self.assertEqual(type_of("/n -> match n with | 0 -> True | _ -> False"), "Int -> Bool")

    def test_branches_must_agree(self):
        with self.assertRaises(TypeCheckError):
            type_of("/o -> match o with | None -> 0 | Some x -> True")

    def test_pattern_constructor_from_wrong_type(self):
        with self.assertRaises(TypeCheckError) as caught:
            type_of("match Some 1 with | Nil -> 0 | Some x -> x")
        self.assertEqual(caught.exception.trace[0][0], "PCon")

    def test_wrong_number_of_fields(self):
        with self.assertRaises(TypeCheckError) as caught:
            type_of("match Some 1 with | Some -> 0")
        self.assertEqual(caught.exception.rule, "PCon")

    def test_variable_bound_twice(self):
        with self.assertRaises(TypeCheckError) as caught:
            type_of("match Cons 1 Nil with | Cons x x -> x")
        self.assertEqual(caught.exception.rule, "PVar")

    def test_branch_variables_do_not_leak(self):
        with self.assertRaises(TypeCheckError) as caught:
            type_of("match Some 1 with | Some x -> 0 | None -> x")
        self.assertEqual(caught.exception.rule, "Var")

    def test_polymorphic_scrutinee_is_instantiated(self):
        self.assertEqual(type_of("match Nil with | Nil -> 0 | Cons x _ -> x"), "Int")
