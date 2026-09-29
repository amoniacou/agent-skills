---
name: principles
description: Design rules for writing and changing code. Load it yourself, without being asked, before adding structure to code.
when_to_use: Before adding a base class, interface, trait, abstract method, factory, strategy, registry, adapter, config option or extension point. Before extracting shared code, removing duplication or refactoring. Before putting a dependency behind an interface or mock for tests. Also on "DRY", "KISS", "YAGNI", "SOLID", "refactor", "abstraction", "make this generic".
---

# Principles

Rules in priority order. When two rules conflict, the higher one wins.

## 1. KISS and YAGNI

Build the simplest thing that meets today's requirements. Add a layer, option, parameter or extension point only when a concrete, current problem needs it. "We might need it later" is not a reason.

Signs of going too far:

- a base class with one child
- an interface with one implementation that is never swapped
- a strategy, factory or registry with one entry
- config options nobody sets

## 2. Prefer deletion

Code that does not exist costs nothing to maintain. Before extracting or generalizing, ask whether the feature, branch or parameter should exist at all. Removing a code path beats wrapping it.

Delete commented-out code. Git remembers it, and nobody else will know why it was switched off.

You own this code, so change it directly. Editing or deleting existing code is better than leaving it untouched and adding new code next to it. Do not add extension points to avoid touching old code.

The exception is a public API with outside users who cannot follow your changes.

## 3. DRY by the rule of three

Only remove duplication that is the same rule. When that rule changes, every copy must change together.

Code that looks alike but stands for different ideas is not duplication. Leave it alone, because the copies will drift apart.

Wait for the third copy before extracting. One is a fact, two may be chance, three is a pattern. If unsure, inline first and see whether the duplication matters.

A copied module is duplication from the first copy. Do not copy a whole file or package to make a new version or support a new backend: every bug then has to be fixed twice. Pull out the shared part right away, or change the original.

## 4. One reason to change

A function, class or module has one job. Split by what changes together, not by technical layer. Do not split into many tiny pieces that have to be read together to make sense.

## 5. Fail loudly, never lie

A subclass or implementation either does the job or raises a clear error. It never pretends to succeed by returning `nil`, an empty result or a no-op.

A base-class method that raises `NotImplementedError` (or similar) for children to fill in is fine. Do not build logic nobody needs, or reshape a class hierarchy, just to avoid that raise.

## 6. Test against real dependencies

Test with the real database, broker or service (docker-compose, testcontainers). Do not put a dependency behind an interface only to mock it in unit tests. That grows the interface and gives tests that check the mocks.

Replace a dependency in tests only when running the real one is not possible or not reliable: time, randomness, paid or external third-party APIs.

## 7. Read config in one place

Read environment variables and config files once, at startup, into one config value. Pass what each part needs explicitly. Do not call `os.Getenv`, `ENV[...]` or `os.environ` deep inside handlers, routers or services.
