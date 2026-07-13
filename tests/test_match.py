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


POLY = DATA + """
type Poly = Poly (forall a. a -> a)
type Church = Church (forall a. (a -> a) -> a -> a)
"""


def poly_type(src):
    return show_type(typecheck(POLY + "let main = " + src))


class TestPolymorphicFields(unittest.TestCase):
    """What the 2013 paper buys: a field can hold a polymorphic function,
    and the matched variable keeps that type, so one branch can use it at
    several types."""

    USE_TWICE = (
        "/p -> match p with"
        " | Poly f -> (match f True with | True -> f 1 | False -> 0)"
    )

    def test_field_used_at_two_types_in_one_branch(self):
        self.assertEqual(poly_type(self.USE_TWICE), "Poly -> Int")

    def test_it_runs(self):
        src = POLY + "let main = (" + self.USE_TWICE + ") (Poly (/x -> x))"
        self.assertEqual(run_program(src), ("Int", "1"))

    def test_constructor_checks_its_argument_is_polymorphic(self):
        with self.assertRaises(TypeCheckError):
            poly_type("Poly (/x -> x + 1)")

    def test_constructor_accepts_polymorphic_argument(self):
        self.assertEqual(poly_type("Poly (/x -> x)"), "Poly")

    def test_without_the_field_annotation_it_fails(self):
        # The same use through an ordinary monomorphic argument is rejected.
        with self.assertRaises(TypeCheckError):
            poly_type("/f -> match f True with | True -> f 1 | False -> 0")

    def test_church_numeral_in_a_box(self):
        src = (
            "let two = Church (/s -> /z -> s (s z)) in "
            "match two with | Church n -> n (/x -> x + 1) 0 + n (/x -> x) 40"
        )
        self.assertEqual(poly_type(src), "Int")
        self.assertEqual(run_program(POLY + "let main = " + src), ("Int", "42"))

    def test_polymorphic_field_nested_in_another_type(self):
        src = (
            "/o -> match o with"
            " | Some (Poly f) -> (match f False with | True -> 0 | False -> f 1)"
            " | None -> 0"
        )
        self.assertEqual(poly_type(src), "Option Poly -> Int")


class TestNestedAndShadowedPatterns(unittest.TestCase):
    def test_deeply_nested_pattern(self):
        src = (
            "/t -> match t with"
            " | Node (Node Leaf x Leaf) y (Node (Node Leaf z Leaf) w Leaf) -> x + y + z + w"
            " | _ -> 0"
        )
        self.assertEqual(type_of(src), "Tree Int -> Int")
        tree = "(Node (Node Leaf 1 Leaf) 2 (Node (Node Leaf 3 Leaf) 4 Leaf))"
        self.assertEqual(run_program(DATA + f"let main = ({src}) {tree}"), ("Int", "10"))

    def test_nested_patterns_solve_inner_types(self):
        self.assertEqual(
            type_of("/x -> match x with | Some (Cons (Some n) Nil) -> n + 1 | _ -> 0"),
            "Option (List (Option Int)) -> Int",
        )

    def test_pattern_variable_shadows_outer_binding(self):
        src = "let x = True in match Some 1 with | Some x -> x + 1 | None -> 0"
        self.assertEqual(type_of(src), "Int")
        self.assertEqual(run_program(DATA + "let main = " + src), ("Int", "2"))

    def test_outer_binding_visible_again_after_branch(self):
        src = (
            "let x = True in match (match Some 1 with | Some x -> x | None -> 0) with"
            " | 1 -> x | _ -> x"
        )
        self.assertEqual(type_of(src), "Bool")

    def test_nested_match_shadows(self):
        src = (
            "/o -> match o with"
            " | Some x -> (match x with | Some x -> x | None -> 0)"
            " | None -> 0"
        )
        self.assertEqual(type_of(src), "Option (Option Int) -> Int")


class TestIf(unittest.TestCase):
    def test_parses_as_match(self):
        self.assertEqual(
            parse("if c then 1 else 2"),
            Match(Var("c"), ((PCon("True"), IntLit(1)), (PCon("False"), IntLit(2)))),
        )

    def test_prints_back_as_if(self):
        src = "if c then 1 else if d then 2 else 3"
        self.assertEqual(show_expr(parse(src)), src)

    def test_typechecks_and_runs(self):
        src = DATA + "let main = (/b -> if b then 1 else 2) False"
        self.assertEqual(run_program(src), ("Int", "2"))

    def test_condition_must_be_bool(self):
        with self.assertRaises(TypeCheckError):
            type_of("if 1 then 2 else 3")

    def test_branches_must_agree(self):
        with self.assertRaises(TypeCheckError):
            type_of("/b -> if b then 1 else True")

    def test_needs_bool_declared(self):
        with self.assertRaises(TypeCheckError) as caught:
            typecheck("let main = /b -> if b then 1 else 2")
        self.assertIn("unknown constructor True", caught.exception.message)
