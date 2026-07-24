import unittest
from pathlib import Path
from context import show_type
from errors import TypeCheckError
from type_checker import typecheck
from examples import ACCEPT, REJECT
from program import run, Session


class TestAccepted(unittest.TestCase):
    def test_accepted_programs(self):
        for ex in ACCEPT:
            with self.subTest(ex.title, src=ex.src):
                t, v = run(ex.src, Session.with_prelude())
                self.assertEqual(t, ex.type)
                if ex.value is not None:
                    self.assertEqual(v, ex.value)


class TestRejected(unittest.TestCase):
    def test_rejected_programs_blame_the_right_rule(self):
        for ex in REJECT:
            with self.subTest(ex.title, src=ex.src):
                with self.assertRaises(TypeCheckError) as caught:
                    typecheck(ex.src)
                self.assertEqual(caught.exception.rule, ex.rule)


class TestErrorTrace(unittest.TestCase):
    def test_trace_walks_out_from_the_failure(self):
        with self.assertRaises(TypeCheckError) as caught:
            typecheck("((/f -> f 1) : (forall a. a -> a) -> Int) (/x -> x + 1)")
        err = caught.exception
        self.assertEqual(err.message, "a is not a subtype of Int")
        self.assertEqual(
            [rule for rule, _ in err.trace], ["Sub", "Sub", "→I", "∀I", "→App"]
        )
        self.assertIn("checking x + 1 against a", str(err))

    def test_error_names_are_repeatable(self):
        def message(src):
            try:
                typecheck(src)
            except TypeCheckError as err:
                return str(err)

        self.assertEqual(message("/x -> x x"), message("/x -> x x"))


class TestPrelude(unittest.TestCase):
    def setUp(self):
        self.session = Session.with_prelude()

    def run_prelude(self, src):
        return run(src, self.session)

    def test_map(self):
        self.assertEqual(
            self.run_prelude("let main = map (/x -> x * 2) [1, 2, 3]"),
            ("List Int", "[2, 4, 6]"),
        )

    def test_filter(self):
        self.assertEqual(
            self.run_prelude("let main = filter (/x -> x < 3) [5, 1, 4, 2]"),
            ("List Int", "[1, 2]"),
        )

    def test_foldr_length_append(self):
        self.assertEqual(
            self.run_prelude("let main = foldr (/x -> /acc -> x + acc) 0 [1, 2, 3]"),
            ("Int", "6"),
        )
        self.assertEqual(self.run_prelude("let main = length [True, False]"), ("Int", "2"))
        self.assertEqual(
            self.run_prelude("let main = append [1] [2, 3]"), ("List Int", "[1, 2, 3]")
        )

    def test_prelude_types(self):
        types = {name: show_type(t) for name, t in self.session.types.items()}
        self.assertEqual(types["map"], "forall a b. (a -> b) -> List a -> List b")
        self.assertEqual(types["length"], "forall a. List a -> Int")
        self.assertEqual(types["not"], "Bool -> Bool")

    def test_prelude_declares_bool(self):
        self.assertEqual(self.run_prelude("let main = not (1 < 2)"), ("Bool", "False"))


class TestPrograms(unittest.TestCase):
    def test_church_numerals(self):
        path = Path(__file__).parent.parent / "programs" / "church.mini"
        self.assertEqual(run(path.read_text()), ("Int", "36"))


class TestSession(unittest.TestCase):
    def test_definitions_persist(self):
        session = Session()
        session.run_source("let inc = /x -> x + 1")
        self.assertEqual(run("inc 41", session), ("Int", "42"))

    def test_top_level_definition_is_generalized(self):
        session = Session()
        (defined,) = session.run_source("let id = /x -> x")
        self.assertEqual(show_type(defined.type), "forall a. a -> a")
        self.assertEqual(run("id id 42", session), ("Int", "42"))

    def test_annotated_definition_keeps_its_annotation(self):
        session = Session()
        (defined,) = session.run_source("let f : Int -> Int = /x -> x")
        self.assertEqual(show_type(defined.type), "Int -> Int")

    def test_failed_definition_is_not_stored(self):
        session = Session()
        with self.assertRaises(TypeCheckError):
            session.run_source("let bad = 1 2")
        self.assertNotIn("bad", session.types)

    def test_declarations_persist(self):
        session = Session()
        session.run_source("type Option a = None | Some a")
        self.assertEqual(run("let x = 1 in Some x", session), ("Option Int", "Some 1"))


class TestRecursion(unittest.TestCase):
    def test_rec_closure_sees_itself(self):
        # Never called, but evaluating it must not fail, and the closure's
        # environment must contain f.
        session = Session()
        session.run_source("let rec f : Int -> Int = /n -> f n")
        self.assertIn("f", session.values["f"].env)

    def test_rec_function_returning_data(self):
        src = (
            "type Stream = Next Int (Int -> Stream)\n"
            "let rec from : Int -> Stream = /n -> Next n (/u -> from (n + 1))\n"
            "let main = from 1"
        )
        t, v = run(src)
        self.assertEqual(t, "Stream")
        self.assertEqual(v, "Next 1 <function>")

    def test_definitions_are_lexically_scoped(self):
        session = Session()
        session.run_source("let x = 1\nlet f = /y -> x\nlet x = 2")
        self.assertEqual(run("f 0 + 0", session), ("Int", "1"))


class TestData(unittest.TestCase):
    DATA = (
        "type Option a = None | Some a\n"
        "type List a = Nil | Cons a (List a)\n"
    )

    def test_constructor_values(self):
        self.assertEqual(
            run(self.DATA + "let main = Some (Cons 1 (Cons 2 Nil))"),
            ("Option (List Int)", "Some [1, 2]"),
        )

    def test_partially_applied_constructor(self):
        self.assertEqual(
            run(self.DATA + "let cons1 = Cons 1\nlet main = cons1 (cons1 Nil)"),
            ("List Int", "[1, 1]"),
        )

    def test_partial_constructor_prints_as_function(self):
        self.assertEqual(
            run(self.DATA + "let main = Cons 1"), ("List Int -> List Int", "<function>")
        )

    def test_constructor_passed_to_function(self):
        src = self.DATA + "let main = (/f -> f 1) Some"
        self.assertEqual(run(src), ("Option Int", "Some 1"))


class TestGeneralization(unittest.TestCase):
    def test_names_avoid_type_variables_already_in_the_type(self):
        # The result keeps the annotation's `forall a`, so the leftover
        # existential (the type of z) must be named something else.
        t = typecheck(
            "((/x -> /y -> (/w -> w)) : forall c. c -> c -> (forall a. a -> a))"
            " (/z -> z)"
        )
        self.assertEqual(show_type(t), "forall b. (b -> b) -> forall a. a -> a")

    def test_existential_solved_monomorphically_under_lambda(self):
        # →I⇒ solves the result to a monotype, so the inner forall is
        # instantiated (predicativity) and then generalized at the top.
        t = typecheck("/y -> ((/x -> x) : forall a. a -> a)")
        self.assertEqual(show_type(t), "forall a b. a -> b -> b")

    def test_fully_solved_type_is_not_generalized(self):
        self.assertEqual(show_type(typecheck("/x -> x + 1")), "Int -> Int")


if __name__ == "__main__":
    unittest.main()
