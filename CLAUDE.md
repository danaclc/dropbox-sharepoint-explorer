# Development Guidelines

> For project-specific requirements and conventions, see `PROJECT.md`

## Core Concepts



## Code Quality Standards

### General Principles
- All code must be well-tested, clear, concise, well-organized, optimized, and documented
- Prioritize readability over cleverness
- Follow the principle of least surprise
- Keep functions small and focused (single responsibility principle)
- Avoid premature optimization - profile before optimizing

### Code Structure
- **Functions and classes**: Must have clear docstrings following NumPy style
- **Type hints**: Required for all function parameters and return values
- **Variable naming**: Use short but explicit names (e.g., `file_count` not `fc`, `user_data` not `ud`)
- **Constants**: Extract magic numbers and strings to named constants at module level
- **Refactoring**: Keep functions focused on a single responsibility; refactor when complexity increases

### Documentation Requirements
- **Docstrings**: Required for all public functions, classes, and methods
- **Inline comments**: Use sparingly, only for complex logic that isn't self-explanatory
- **README.md**: Must include setup, usage, and examples
- **docs/**: Additional documentation for architecture, design decisions, and API reference
- **Style**: Avoid emojis in documentation, code, comments, and commit messages

### Type Hints
```python
# Good
def process_data(input_data: str, threshold: int = 100) -> dict[str, Any]:
    """Process input data and return results."""
    pass

# Bad (missing type hints)
def process_data(input_data, threshold=100):
    pass
```

## Testing Standards

### Test Coverage
- **Requirement**: All new features must have tests
- **Minimum coverage**: Aim for 80%+ code coverage
- **Test types**: Unit tests, integration tests, and edge cases
- **Test location**: All tests go in `tests/` directory
- **Test naming**: Use descriptive names that explain what is being tested

### Testing Best Practices
- Test one thing per test function
- Use fixtures for common setup/teardown
- Test both success and failure cases
- Test edge cases (empty inputs, null values, boundary conditions)
- Use parametrized tests for similar test cases with different inputs
- Mock external dependencies (APIs, file system, etc.)

### Example Test Structure
```python
# tests/test_calculator.py
import pytest
from src.calculator import Calculator

class TestCalculator:
    @pytest.fixture
    def calculator(self):
        """Create a test calculator instance."""
        return Calculator()

    def test_add_returns_sum_of_two_numbers(self, calculator):
        """Test that add method correctly sums two numbers."""
        assert calculator.add(2, 3) == 5
        assert calculator.add(-1, 1) == 0

    def test_divide_by_zero_raises_exception(self, calculator):
        """Test that dividing by zero raises appropriate error."""
        with pytest.raises(ZeroDivisionError):
            calculator.divide(10, 0)
```

## Development Tools

### Package Management
- **Tool**: `uv` for all package management and script execution
- **Commands**:
  - `uv pip install <package>` - Install dependencies
  - `uv run <script>` - Run Python scripts
  - `uv sync` - Sync dependencies from pyproject.toml

### Versioning
- **Strategy**: VCS-based versioning using `hatch-vcs`
- **Version source**: Git tags (e.g., `v0.1.0`, `v1.0.0`)
- **Version file**: Auto-generated at `src/_version.py` during build
- **Fallback**: `0.0.0+unknown` for non-VCS installs

#### How It Works

The project uses `hatch-vcs` to automatically derive version numbers from Git tags:

1. **Release versions**: Tag format `vX.Y.Z` (e.g., `v0.1.0`, `v1.2.3`)
2. **Development versions**: Automatically includes commit distance and hash
   - Example: `0.1.0.dev5+g1234567` (5 commits after v0.1.0)
3. **Dirty working tree**: Adds `.d<timestamp>` suffix if uncommitted changes exist

#### Creating a Release

```bash
# Tag the current commit
git tag v0.1.0

# Push the tag
git push origin v0.1.0

# Build will now use version 0.1.0
uv build
```

#### Version Access

```python
# In code
from src import __version__
print(f"Version: {__version__}")

# From command line
python -c "from src import __version__; print(__version__)"
```

#### Configuration

In `pyproject.toml`:

```toml
[project]
dynamic = ["version"]  # Version is dynamic from VCS

[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[tool.hatch.version]
source = "vcs"
fallback-version = "0.0.0+unknown"

[tool.hatch.build.hooks.vcs]
version-file = "src/_version.py"
```

#### Version Format

- **Release**: `0.1.0` (from tag `v0.1.0`)
- **Post-release**: `0.1.0.post1` (tagged but with local changes)
- **Development**: `0.2.0.dev5+g1234567` (5 commits after v0.1.0, working toward v0.2.0)
- **Fallback**: `0.0.0+unknown` (no VCS or tags found)

#### Best Practices

1. **Use semantic versioning**: `MAJOR.MINOR.PATCH`
   - MAJOR: Breaking changes
   - MINOR: New features (backward compatible)
   - PATCH: Bug fixes

2. **Tag releases**: Always tag releases with `v` prefix
   ```bash
   git tag -a v0.1.0 -m "Release version 0.1.0"
   ```

3. **Don't manually edit version**: Let VCS manage it automatically

4. **Check version**: Use `python -c "from src import __version__; print(__version__)"` to verify

### Code Quality
- **Linter/Formatter**: `ruff` for linting, formatting, and import sorting
- **Configuration**: Define rules in `pyproject.toml` under `[tool.ruff]`
- **Required checks before commit**:
  ```bash
  uv run ruff check .          # Lint code
  uv run ruff format .         # Format code
  uv run pytest                # Run tests
  uv run pytest --cov=src      # Check coverage
  ```

### Ruff Configuration Example
```toml
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = ["E501"]  # line too long (handled by formatter)
```

## Development Workflow

### Feature Implementation Checklist
1. **Plan**: Review existing code and identify refactoring opportunities
2. **Implement**: Write clear, documented code with type hints
3. **Test**: Write comprehensive tests covering all cases
4. **Lint**: Run `uv run ruff check .` and fix issues
5. **Format**: Run `uv run ruff format .`
6. **Verify**: Run full test suite with `uv run pytest`
7. **Document**: Update README.md and docs/ as needed
8. **Review**: Self-review changes before committing

### Refactoring Guidelines
- When implementing a new feature, take the opportunity to refactor existing code
- Look for code duplication, long functions, and unclear variable names
- Extract common functionality into reusable functions
- Improve error handling and edge case coverage
- Update tests to match refactored code

### Error Handling
- Use specific exception types, not bare `except:`
- Provide helpful error messages with context
- Log errors appropriately (see Logging Guidelines below)
- Clean up resources in `finally` blocks or use context managers
- Validate inputs early and fail fast

## Logging Guidelines

### Logging Framework
- **Library**: `loguru` for all logging needs
- **Configuration**: Centralized in `src/logger.py`
- **Usage**: Import and use the configured logger instance

### Log Levels

Use appropriate log levels for different message types:

| Level | When to Use | Example |
|-------|-------------|---------|
| **DEBUG** | Detailed diagnostic information, variable values, internal state | `logger.debug(f"Processing item {i} of {total}")` |
| **INFO** | General informational messages about program flow | `logger.info("Starting data export")` |
| **SUCCESS** | Successful completion of significant operations | `logger.success("Export completed successfully")` |
| **WARNING** | Warning messages for recoverable issues | `logger.warning("Rate limit approaching")` |
| **ERROR** | Error messages for failures that don't stop execution | `logger.error(f"Failed to process file: {filename}")` |
| **CRITICAL** | Critical errors that may cause program termination | `logger.critical("Database connection lost")` |

### Never Use Print Statements

**❌ Bad - Don't use print():**
```python
print(f"[INFO] Processing {count} items...")
print(f"[ERROR] Failed to connect: {error}")
print(f"[SUCCESS] Operation completed!")
```

**✅ Good - Use logger:**
```python
logger.info(f"Processing {count} items...")
logger.error(f"Failed to connect: {error}")
logger.success("Operation completed!")
```

### Logging Best Practices

#### 1. Use Structured Logging
```python
# Good - Structured with context
logger.info(f"User {user_id} logged in from {ip_address}")
logger.error(f"Database query failed: {query}", exc_info=True)

# Bad - Unstructured
logger.info("User logged in")
logger.error("Query failed")
```

#### 2. Include Relevant Context
```python
# Good - Includes context for debugging
def process_file(filepath: str) -> None:
    logger.debug(f"Opening file: {filepath}")
    try:
        with open(filepath, 'r') as f:
            data = f.read()
        logger.info(f"Successfully processed {filepath} ({len(data)} bytes)")
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}", exc_info=True)
```

#### 3. Don't Log Sensitive Information
```python
# Bad - Logs password
logger.info(f"User login: {username} with password {password}")

# Good - No sensitive data
logger.info(f"User login attempt: {username}")
```

#### 4. Use Appropriate Log Levels
```python
# Configuration and startup
logger.info("Application started")
logger.info(f"Configuration: {config}")

# Normal operations
logger.debug("Entering processing loop")
logger.info("Processing batch 1 of 10")

# Warnings for non-critical issues
logger.warning("Retrying connection (attempt 2 of 5)")

# Errors for failures
logger.error("Failed to save session", exc_info=True)

# Success for completed operations
logger.success("Export completed: 1000 items exported")
```

#### 5. Exception Logging
```python
# Good - Include exception info
try:
    risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)

# Good - For re-raising
try:
    risky_operation()
except ValueError as e:
    logger.error(f"Invalid input: {e}")
    raise

# Bad - Swallowing exceptions
try:
    risky_operation()
except Exception:
    pass  # Silent failure
```

#### 6. Progress Logging for Long Operations
```python
# Good - Informative progress updates
logger.info(f"Starting export of {total_items} items")

for i, item in enumerate(items, 1):
    process_item(item)
    
    # Log at intervals
    if i % 1000 == 0:
        logger.info(f"Progress: {i}/{total_items} items processed")

logger.success(f"Export complete: {total_items} items")
```

### Logger Configuration

The logger is configured in `src/logger.py` with the following features:

- **UTC timestamps** for consistency across timezones
- **Colored console output** for better readability
- **Separate log levels** for console and file output
- **Automatic file rotation** at 100MB
- **Log retention** of 30 days with compression
- **Thread-safe** logging

### Environment Variables

Configure logging behavior via `.env`:

```bash
# Console output level (NONE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL_CONSOLE=INFO

# File output level (NONE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL_FILE=DEBUG

# Log files directory
LOG_DIR=logs
```

### Usage Example

```python
# Import the pre-configured logger instance
from src import logger

# In main.py or entry point, configure logging once
from src.logger import configure_logging

configure_logging(
    console_level="INFO",
    file_level="DEBUG",
    log_dir="logs"
)

# Use the logger throughout your code
logger.debug("Debug information")
logger.info("General information")
logger.success("Operation succeeded")
logger.warning("Warning message")
logger.error("Error occurred")
```

**Note:** The logger is available as `from src import logger` in all modules. You only need to call `configure_logging()` once at application startup (typically in `main()`).

### Log File Management

Log files are automatically:
- **Named** with UTC timestamp: `YYYYMMDD-HHMMSS.log`
- **Rotated** when reaching 100MB
- **Compressed** as `.zip` after rotation
- **Cleaned up** after 30 days

View logs:
```bash
# View latest log
ls -t logs/*.log | head -1 | xargs cat

# Follow live logs
ls -t logs/*.log | head -1 | xargs tail -f

# Search logs
grep "ERROR" logs/*.log
```

### Testing with Logging

When writing tests, you may want to capture or suppress log output:

```python
import pytest
from loguru import logger

def test_function_logs_correctly(caplog):
    """Test that function logs expected messages."""
    with caplog.at_level("INFO"):
        my_function()
        assert "Expected message" in caplog.text

def test_without_log_noise():
    """Test with suppressed logging."""
    logger.remove()  # Remove handlers
    try:
        my_function()
        # assertions
    finally:
        logger.add(sys.stderr)  # Restore
```

### Common Patterns

#### Initialization and Configuration
```python
logger.info("=" * 70)
logger.info("Application Name")
logger.info("=" * 70)
logger.info("")
logger.info("Configuration:")
logger.info(f"   Output directory: {output_dir}")
logger.info(f"   Session save interval: {interval} seconds")
```

#### Progress Updates
```python
logger.info("Starting exploration...")
logger.info(f"Accessing path: {path}")
logger.debug(f"Skipping fully explored folder: {path}")
```

#### Error Reporting
```python
logger.error(f"Authentication error: {e}")
logger.info("Attempting to refresh authentication...")
logger.error(f"Failed to refresh: {error}")
```

#### Completion Messages
```python
logger.info("")
logger.info("=" * 70)
logger.success("Exploration complete!")
logger.info("=" * 70)
logger.info(f"   Files: {file_count}")
logger.info(f"   Folders: {folder_count}")
```

### Code Review Focus Areas
- Are all functions properly documented?
- Are type hints complete and accurate?
- Are tests comprehensive and meaningful?
- Are magic numbers extracted to constants?
- Is error handling appropriate?
- Are there any code smells (duplication, long functions, etc.)?

## Project Structure

```
project/
├── src/                    # Source code
│   ├── __init__.py
│   ├── main.py            # Entry point
│   └── module.py          # Feature modules
├── tests/                 # Test files
│   ├── __init__.py
│   ├── test_main.py
│   └── test_module.py
├── docs/                  # Additional documentation
│   ├── architecture.md
│   └── api.md
├── pyproject.toml         # Project configuration
├── README.md              # Main documentation
├── CLAUDE.md              # This file
├── PROJECT.md             # Project-specific guidelines
└── .env.example           # Example environment variables
```

## Git Commit Messages

### Format
```
<type>: <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code restructuring without behavior change
- `test`: Adding or updating tests
- `chore`: Build process, dependencies, etc.

### Example
```
feat: add data validation module

Add input validation for user-submitted data with support for
common patterns (email, phone, URL). Includes custom validators
and comprehensive error messages.

Closes #123
```

### Rules
- Keep subject line under 50 characters
- Use imperative mood ("add" not "added")
- Don't use emojis
- Reference issue numbers in footer

## Performance Considerations

- Profile before optimizing
- Use generators for large datasets
- Implement pagination for large result sets
- Cache expensive computations when appropriate
- Use bulk operations instead of loops where possible
- Consider memory usage for long-running processes

## Security Best Practices

- Never commit secrets or API keys
- Use environment variables for sensitive data
- Validate and sanitize all inputs
- Use type hints to catch type-related bugs early
- Keep dependencies up to date
- Review security advisories for dependencies
