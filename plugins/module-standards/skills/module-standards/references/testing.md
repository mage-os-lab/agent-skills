# Testing

The goal is tests that would catch a real regression, not a coverage number.
A test suite that mocks every collaborator and asserts that method X called
method Y proves nothing and breaks on every refactor. Test what the module
**does**: given this config and this input, the merchant sees this result.

## Criteria

- `Test/Unit` for logic that stands on its own: calculators, mappers,
  validators, value objects, anything with branches.
- `Test/Integration` for Magento wiring, because that's where Magento modules
  actually break: plugins applied in the right order, DI preferences and
  virtual types resolving, observers firing on the right event, config values
  read from the right path and scope, declarative schema creating the
  expected columns, GraphQL resolvers returning the expected shape.
  check-extension runs these against a real database.
- The critical paths have at least one test each. Identify them by asking
  "what would a merchant notice if this broke?"
- Tests are deterministic: no real HTTP calls, no dependence on current time
  without a clock abstraction, no order dependence.
- `phpunit.xml.dist` in the root for running unit tests standalone.

## What to test, and what not

**Do** test:
- Branches in business logic, especially edge cases: empty cart, zero price,
  missing optional config, disabled module flag.
- Config being respected: feature off means nothing happens.
- Plugins: the around/after result for representative inputs, via
  integration tests with the real subject.
- Bugs fixed in the past (check the CHANGELOG and closed issues). A
  regression test for each is high-value.

**Don't** generate:
- Tests for getters/setters or data objects without logic.
- Tests that assert on call counts or call order of mocks (`expects($this->once())`)
  when the observable result can be asserted instead.
- One test per method regardless of risk. Spend the effort where the
  branches are.

Prefer small hand-written fakes implementing the interface over mocking
frameworks when a collaborator has to be replaced; they read better and
survive refactors. Follow the module's existing test style if it has one.

## Fixing

1. List the module's behaviors (from the README, system.xml fields,
   plugins/observers in `etc/di.xml` and `etc/events.xml`, controllers,
   GraphQL schema). Rank them by merchant impact.
2. Show the maintainer the list and the proposed test type for each (unit or
   integration) before writing them. They know which behaviors matter.
3. Write the tests. Name them after behavior:
   `testItSkipsDiscountWhenCustomerGroupIsExcluded`, not `testExecute`.
4. Run unit tests locally. Integration tests need a full Magento install with
   a database; if none is available, say so, and note that CI will run them.
5. If a test reveals a bug, don't silently fix it inside the testing step.
   Report it, and fix it separately with the maintainer's ok.

## Questions to ask

Use the audit script's `tests` counts.

**Tests** (decision `tests.behavior_tests`):

> **The module has 0 tests for 14 PHP classes.** Tests catch regressions
> before a release reaches stores. I'd start with the behaviors merchants
> would notice: the gift wrap price on the order total, the feature being
> off when disabled, and the config being read per website.
>
> 1. Write tests for these behaviors, unit and integration (Recommended)
> 2. Only unit tests for now (no store needed to run them)
> 3. Skip for now

Then show the behavior list from step 2 of "Fixing" before writing
anything. When tests exist but miss critical paths, name the gaps instead.
