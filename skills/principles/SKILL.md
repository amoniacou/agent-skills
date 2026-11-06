---
name: principles
description: Design rules for writing and changing code. Load it yourself, without being asked, before adding structure to code.
when_to_use: Before adding a base class, interface, trait, abstract method, factory, strategy, registry, adapter, config option or extension point. Before extracting shared code, removing duplication or refactoring. Before putting a dependency behind an interface or mock for tests. Also on "DRY", "KISS", "YAGNI", "SOLID", "refactor", "abstraction", "make this generic".
---

# Principles

Rules in priority order. When two rules conflict, the higher one wins.

## 1. KISS and YAGNI

Build the simplest thing that meets today's requirements. Add a layer, option, parameter or extension point only when a concrete, current problem needs it. "We might need it later" is not a reason.

Do not add an abstraction nobody asked for. Simple code is easier to read, easier to change and faster; every abstraction added for its own sake makes it worse at all three.

When you think an abstraction is needed, write the plain version first and show it. Propose the abstraction separately, as a question, with the plain code next to it.

"No new dependency" is not a reason by itself. Do not hand-write what a maintained library already does (sessions, crypto, auth, retries): a dependency costs less than owning that code. When proposing to write it yourself, name the library you are not taking and say why.

Signs of going too far:

- a base class with one child
- an interface with one implementation that is never swapped
- a strategy, factory or registry with one entry
- config options nobody sets
- a one-line wrapper with fewer than three callers

## 2. Prefer deletion

Code that does not exist costs nothing to maintain. Before extracting or generalizing, ask whether the feature, branch or parameter should exist at all. Removing a code path beats wrapping it.

Delete commented-out code. Git remembers it, and nobody else will know why it was switched off.

You own this code, so change it directly. Editing or deleting existing code is better than leaving it untouched and adding new code next to it. Do not add extension points to avoid touching old code.

The exception is a public API with outside users who cannot follow your changes.

## 3. DRY by the rule of three

Only remove duplication that is the same rule. When that rule changes, every copy must change together.

Code that looks alike but stands for different ideas is not duplication. Leave it alone, because the copies will drift apart.

The rule of three applies differently depending on whether you are discovering or creating duplication:

- **Discovering duplication:** Wait for the third copy of existing code before extracting. One is a fact, two may be chance, three is a pattern. If unsure, inline first and see whether the duplication matters.
- **Adding new code:** If you are writing new code that needs to exist in two places at once, extract the shared part immediately. Do not introduce duplication when you can see it from the start.

The same rule holds for a one-line function or method that only reads a field or calls one other thing. Keep it only when it is called from at least three places, or when it hides a decision such as a nil check or a fallback. Otherwise write the expression where it is used. When a change removes that decision, inline the wrapper at every call site and delete it.

A copied module is duplication from the first copy. Do not copy a whole file or package to make a new version or support a new backend: every bug then has to be fixed twice. Pull out the shared part right away, or change the original.

## 4. One reason to change

A function, class or module has one job. Split by what changes together, not by technical layer. Do not split into many tiny pieces that have to be read together to make sense.

## 5. Fail loudly, never lie

A subclass or implementation either does the job or raises a clear error. It never pretends to succeed by returning `nil`, an empty result or a no-op.

A base-class method that raises `NotImplementedError` (or similar) for children to fill in is fine. Do not build logic nobody needs, or reshape a class hierarchy, just to avoid that raise.

## 6. Test against real dependencies

Test with the real database, broker or service (docker-compose, testcontainers). Do not put a dependency behind an interface only to mock it in unit tests. That grows the interface and gives tests that check the mocks.

Replace a dependency in tests only when running the real one is not possible or not reliable: time, randomness, paid or external third-party APIs.

## 7. Test behaviour through the public entry point

Drive the code the way its callers do: the exported function, the handler, the reconciler, the command. Assert on what comes out: the stored object, the response, the status, the file. Do not call unexported helpers or internal methods from a test; they are the shape of today's code, and the test has to be rewritten every time the shape changes.

A value that is part of the public contract (a status phase, a reason, an API field, a URL) is written literally in the test. A value the code derives and nobody promises (a generated name, a hash, a registry entry) is read through the API or registry that produces it.

If you changed the implementation and the test now fails for a reason other than a change in behaviour, do not rewrite the test to match. Test from the entry point instead.

## 8. Read config in one place

Read environment variables and config files once, at startup, into one config value. Pass what each part needs explicitly. Do not call `os.Getenv`, `ENV[...]` or `os.environ` deep inside handlers, routers or services.
