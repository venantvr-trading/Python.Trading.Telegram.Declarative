# Contributing to Telegram Bot Framework

First off, thank you for considering contributing to the Telegram Bot Framework! It's people like you that make this project such a great tool.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive criticism
- Show empathy towards other community members

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples**
- **Describe the behavior you observed and expected**
- **Include screenshots if possible**
- **Include your environment details** (Python version, OS, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description of the suggested enhancement**
- **Explain why this enhancement would be useful**
- **List some examples of how it would be used**

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following our coding standards
3. **Add tests** for any new functionality
4. **Ensure all tests pass** by running `make test`
5. **Update documentation** as needed
6. **Format your code** using `make format`
7. **Submit your pull request**

## Development Setup

1. Clone your fork:
   ```bash
   git clone https://github.com/your-username/telegram-bot-framework.git
   cd telegram-bot-framework
   ```

2. Create a virtual environment:
   ```bash
   make venv
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   make dev-install
   ```

4. Run tests to ensure everything works:
   ```bash
   make test
   ```

## Coding Standards

### Python Style Guide

- Follow PEP 8
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions small and focused
- Use type hints where appropriate

### Testing

- Write unit tests for all new functionality
- Maintain or improve code coverage
- Use descriptive test names that explain what is being tested
- Follow the AAA pattern (Arrange, Act, Assert)

### Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

Example:

```
Add retry logic for network failures

- Implement exponential backoff
- Add configurable max retry attempts
- Handle specific error types differently

Fixes #123
```

## Project Structure

```
venantvr/telegram/
├── base.py              # Base service class
├── client.py            # HTTP client with retry logic
├── message_queue.py     # Queue management
├── service.py           # Main orchestrator
├── notification.py      # Notification service
├── handler.py           # Command handlers
├── history.py           # History management
├── classes/             # Data models
└── tools/               # Utilities

tests/
├── test_client.py       # Client tests
├── test_message_queue.py # Queue tests
└── test_service.py      # Service tests
```

## Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run specific test
make test-file TEST_FILE=tests/test_client.py

# Run with verbose output
make test-verbose
```

## Code Quality Checks

Before submitting a PR, ensure your code passes all checks:

```bash
# Run all checks
make check

# Individual checks
make lint        # Linting
make format      # Code formatting
make type-check  # Type checking
```

## Documentation

- Update README.md if you change functionality
- Add docstrings to new functions and classes
- Update CHANGELOG.md with your changes
- Include examples for new features

## Release Process

1. Update version numbers
2. Update CHANGELOG.md
3. Create a pull request
4. After merge, tag the release
5. Deploy to PyPI (maintainers only)

## Getting Help

- Check the [documentation](README.md)
- Look through [existing issues](https://github.com/yourusername/telegram-bot-framework/issues)
- Ask questions in discussions
- Contact maintainers

## Recognition

Contributors will be recognized in:

- The AUTHORS file
- Release notes
- Project documentation

Thank you for contributing! 🎉