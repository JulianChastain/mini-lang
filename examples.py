# Programs that show off the checker, shared by `main.py --demo` and the
# tests so the demo can't drift from what actually works.
from dataclasses import dataclass


@dataclass(frozen=True)
class Accept:
    title: str
    src: str
    type: str  # the expected type, as show_type prints it
    value: str | None = None  # the expected result of running it, if printable


@dataclass(frozen=True)
class Reject:
    title: str
    src: str
    rule: str  # the rule the error should blame


ACCEPT = [
    Accept("identity, inferred and generalized", "/x -> x", "forall a. a -> a"),
    Accept("K combinator", "/x -> /y -> x", "forall a b. a -> b -> a"),
    Accept(
        "application", "/f -> /x -> f x", "forall a b. (a -> b) -> a -> b"
    ),
    Accept(
        "composition",
        "/f -> /g -> /x -> f (g x)",
        "forall a b c. (a -> b) -> (c -> a) -> c -> b",
    ),
    Accept("unannotated lambda, applied", "(/x -> x + 1) 41", "Int", "42"),
    Accept(
        "a function argument used twice",
        "(/k -> k 20 + k 22) (/n -> n)",
        "Int",
        "42",
    ),
    Accept(
        "polymorphic annotation, instantiated at Int",
        "((/x -> x) : forall a. a -> a) 42",
        "Int",
        "42",
    ),
    Accept(
        "subsumption: forall a. a -> a is usable as Int -> Int",
        "(((/x -> x) : forall a. a -> a) : Int -> Int)",
        "Int -> Int",
    ),
    Accept(
        "rank-2: the argument must be polymorphic",
        "((/f -> f 1) : (forall a. a -> a) -> Int) (/x -> x)",
        "Int",
        "1",
    ),
    Accept(
        "rank-2: f used at two different types in f f 1",
        "((/f -> f f 1) : (forall a. a -> a) -> Int) (/x -> x)",
        "Int",
        "1",
    ),
    Accept(
        "self-application, made legal by a rank-2 annotation",
        "((/x -> x x) : (forall a. a -> a) -> (forall b. b -> b))",
        "(forall a. a -> a) -> forall b. b -> b",
    ),
    Accept(
        "predicative instantiation: id applied to id",
        "((/x -> x) : forall a. a -> a) ((/y -> y) : forall b. b -> b)",
        "forall a. a -> a",
    ),
]

REJECT = [
    Reject(
        "rank-2: x + 1 isn't polymorphic enough",
        "((/f -> f 1) : (forall a. a -> a) -> Int) (/x -> x + 1)",
        "<:Var",
    ),
    Reject(
        "annotation more general than the code",
        "((/x -> x + 1) : forall a. a -> a)",
        "<:Var",
    ),
    Reject(
        "Int -> Int is not a subtype of forall a. a -> a",
        "(((/x -> x + 1) : Int -> Int) : forall a. a -> a)",
        "<:Var",
    ),
    Reject(
        "self-application without an annotation",
        "/x -> x x",
        "<:InstantiateR",
    ),
    Reject(
        "a type variable escaping its scope",
        "/f -> (f : forall a. a -> a)",
        "InstRSolve",
    ),
    Reject("lambda annotated as Int", "((/x -> x) : Int)", "<:→"),
    Reject("applying a non-function", "1 2", "→App"),
    Reject("unbound variable", "/x -> y", "Var"),
    Reject("annotation with a free type variable", "(1 : a)", "Anno"),
]
