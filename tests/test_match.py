import unittest
from lexer import lex
from parser import Parser, Match, PVar, PWild, PInt, PCon, Var, IntLit, App, Con
from evaluator import eval, ConValue, MatchError, show_value
from type_checker import show_expr

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
