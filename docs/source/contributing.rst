Contributing
============

Thank you for considering contributing to Joget Toolkit!

Development Setup
-----------------

1. Clone the repository::

    git clone https://github.com/your-org/joget-toolkit.git
    cd joget-toolkit

2. Create a virtual environment::

    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\\Scripts\\activate

3. Install development dependencies::

    pip install -r requirements.txt
    pip install -e ".[dev]"

4. Run tests to verify setup::

    pytest

Code Style
----------

This project follows PEP 8 and uses:

* **Black** for code formatting
* **Ruff** for linting
* **MyPy** for type checking

Before submitting, run::

    black src/ tests/
    ruff check src/ tests/
    mypy src/

Testing
-------

All new code should have tests. Run the test suite with::

    pytest

For coverage report::

    pytest --cov=joget_deployment_toolkit --cov-report=html

Aim for >85% code coverage.

Pull Request Process
---------------------

1. Create a feature branch from ``main``
2. Write your code and tests
3. Ensure all tests pass
4. Update documentation if needed
5. Submit a pull request with a clear description

Commit Message Guidelines
-------------------------

Follow the Conventional Commits format::

    feat: Add async support for client operations
    fix: Handle connection timeout in health check
    docs: Update quickstart guide with new examples
    test: Add repository integration tests
    refactor: Extract authentication logic to separate module

Types:

* ``feat`` - New feature
* ``fix`` - Bug fix
* ``docs`` - Documentation only
* ``test`` - Adding/updating tests
* ``refactor`` - Code restructuring without functionality change
* ``perf`` - Performance improvement
* ``chore`` - Maintenance tasks

Documentation
-------------

Documentation is built with Sphinx. To build locally::

    cd docs
    make html

View at ``docs/build/html/index.html``.

When adding new modules or classes:

1. Add docstrings following Google style
2. Update relevant ``.rst`` files in ``docs/source/api/``
3. Add examples to ``docs/source/examples.rst``

Questions?
----------

Open an issue on GitHub or reach out to the maintainers.

Thank you for contributing!
