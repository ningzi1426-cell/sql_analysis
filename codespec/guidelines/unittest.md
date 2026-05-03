# Test Standards

<!-- Fill in your project's test requirements. Examples below: -->

## Coverage Requirements
- Minimum 80% line coverage on new code
- All public functions must have at least one test

## Test Structure
- One test file per source file
- Test files named `test_{source_file_name}`
- Use descriptive test names: `test_{function_name}_{scenario}_{expected_result}`

## What to Test
- Happy path
- Edge cases (empty input, null, boundary values)
- Error conditions

## What Not to Test
- Third-party library internals
- Pure boilerplate (e.g., __init__ with no logic)
