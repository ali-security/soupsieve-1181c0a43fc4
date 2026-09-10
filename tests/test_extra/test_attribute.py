"""Test attribute selectors."""
import signal
import time
from contextlib import contextmanager
from .. import util
import soupsieve as sv

# `SIGALRM` is only available on Unix-like systems.
HAS_SIGALRM = hasattr(signal, 'SIGALRM')
# Seconds a pattern is allowed to take before it is considered to be catastrophically backtracking.
TIME_LIMIT = 3


@contextmanager
def time_limit(limit=TIME_LIMIT):
    """Ensure the enclosed pattern fails fast instead of catastrophically backtracking."""

    def alarm_handler(signum, frame):
        """Interrupt an operation that is taking too long."""

        raise TimeoutError('Operation timed out after {} seconds'.format(limit))

    original = signal.signal(signal.SIGALRM, alarm_handler) if HAS_SIGALRM else None
    if HAS_SIGALRM:
        signal.alarm(limit)

    start = time.time()
    try:
        yield
    finally:
        if HAS_SIGALRM:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, original)

    # `SIGALRM` cannot interrupt the operation on all platforms (Windows),
    # so verify the elapsed time as well.
    elapsed = time.time() - start
    if elapsed >= limit:
        raise TimeoutError('Operation timed out after {:.2f} seconds'.format(elapsed))


class TestAttribute(util.TestCase):
    """Test attribute selectors."""

    MARKUP = """
    <div id="div">
    <p id="0">Some text <span id="1"> in a paragraph</span>.</p>
    <a id="2" href="http://google.com">Link</a>
    <span id="3">Direct child</span>
    <pre id="pre">
    <span id="4">Child 1</span>
    <span id="5">Child 2</span>
    <span id="6">Child 3</span>
    </pre>
    </div>
    """

    def test_attribute_not_equal_no_quotes(self):
        """Test attribute with value that does not equal specified value (no quotes)."""

        # No quotes
        self.assert_selector(
            self.MARKUP,
            'body [id!=\\35]',
            ["div", "0", "1", "2", "3", "pre", "4", "6"],
            flags=util.HTML5
        )

    def test_attribute_not_equal_quotes(self):
        """Test attribute with value that does not equal specified value (quotes)."""

        # Quotes
        self.assert_selector(
            self.MARKUP,
            "body [id!='5']",
            ["div", "0", "1", "2", "3", "pre", "4", "6"],
            flags=util.HTML5
        )

    def test_attribute_not_equal_double_quotes(self):
        """Test attribute with value that does not equal specified value (double quotes)."""

        # Double quotes
        self.assert_selector(
            self.MARKUP,
            'body [id!="5"]',
            ["div", "0", "1", "2", "3", "pre", "4", "6"],
            flags=util.HTML5
        )

    def test_bad_attribute(self):
        """Test bad attribute fails."""

        pattern = r"[\]!=D4XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

        with time_limit():
            with self.assertRaises(sv.SelectorSyntaxError) as cm:
                sv.compile(pattern)

        e = cm.exception
        self.assertEqual(e.context, pattern + '\n^')
        self.assertEqual(e.line, 1)
        self.assertEqual(e.col, 1)

    def test_bad_attribute_unclused(self):
        """Test bad attribute fails for syntax error, not timeout error."""

        # An unterminated value (quoted or not) must fail fast, not backtrack catastrophically.
        patterns = (
            '[a="' + ('x' * 300),
            "[a='" + ('x' * 300),
            '[a=' + ('x' * 300)
        )

        for pattern in patterns:
            with time_limit():
                with self.assertRaises(sv.SelectorSyntaxError):
                    sv.compile(pattern)
