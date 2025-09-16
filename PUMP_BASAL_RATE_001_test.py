```python
import pytest
from unittest.mock import MagicMock

# Assuming you have a Pump class or a function that controls the pump's basal rate.
# We'll create a mock for demonstration purposes.

# --- Mock Pump Implementation (for testing purposes) ---
class MockPump:
    def __init__(self):
        self._basal_rate_u_per_hr = 0.0

    def set_basal_rate(self, rate_u_per_hr: float):
        """
        Sets the basal rate of the pump.
        In a real scenario, this would interact with pump hardware.
        """
        self._basal_rate_u_per_hr = rate_u_per_hr
        print(f"Pump basal rate set to: {self._basal_rate_u_per_hr} U/hr")

    def get_basal_rate(self) -> float:
        """
        Gets the current basal rate of the pump.
        In a real scenario, this would read from pump hardware.
        """
        return self._basal_rate_u_per_hr

# --- Test Fixture ---
@pytest.fixture
def mock_pump():
    """Provides a mock pump instance for tests."""
    return MockPump()

# --- Test Cases ---

# Requirement ID: PUMP_BASAL_RATE_001
# Requirement: The pump shall deliver a basal rate of 0.5 U/hr ±5%.

@pytest.mark.parametrize(
    "input_rate, expected_lower_bound, expected_upper_bound",
    [
        # Test with the nominal value
        (0.5, 0.5 * 0.95, 0.5 * 1.05),
        # Test with a value slightly above nominal (within tolerance)
        (0.52, 0.5 * 0.95, 0.5 * 1.05),
        # Test with a value slightly below nominal (within tolerance)
        (0.48, 0.5 * 0.95, 0.5 * 1.05),
        # Test with the upper boundary of the tolerance
        (0.525, 0.5 * 0.95, 0.5 * 1.05),
        # Test with the lower boundary of the tolerance
        (0.475, 0.5 * 0.95, 0.5 * 1.05),
    ]
)
def test_pump_basal_rate_within_tolerance_PUMP_BASAL_RATE_001(
    mock_pump: MockPump,
    input_rate: float,
    expected_lower_bound: float,
    expected_upper_bound: float
):
    """
    Tests if the pump's basal rate can be set and retrieved within the specified tolerance.
    Requirement ID: PUMP_BASAL_RATE_001
    """
    print(f"\nTesting with input rate: {input_rate} U/hr")
    mock_pump.set_basal_rate(input_rate)
    actual_rate = mock_pump.get_basal_rate()

    print(f"Expected range: {expected_lower_bound:.3f} U/hr to {expected_upper_bound:.3f} U/hr")
    print(f"Actual rate: {actual_rate:.3f} U/hr")

    assert expected_lower_bound <= actual_rate <= expected_upper_bound, \
        f"Basal rate {actual_rate:.3f} U/hr is outside the allowed range " \
        f"[{expected_lower_bound:.3f}, {expected_upper_bound}] U/hr for input {input_rate} U/hr."

# You might also want tests for edge cases or values outside the tolerance,
# depending on the expected behavior of the pump when setting invalid rates.

# Example of a test for a value outside the tolerance (if the pump should reject it or behave predictably)
# This test assumes that setting a rate outside the tolerance still returns the set value,
# but the assertion checks against the *required* tolerance.
def test_pump_basal_rate_outside_tolerance_PUMP_BASAL_RATE_001(mock_pump: MockPump):
    """
    Tests that a basal rate outside the tolerance is handled correctly (e.g., by assertion failing).
    Requirement ID: PUMP_BASAL_RATE_001
    """
    target_rate = 0.5  # Nominal target rate
    tolerance = 0.05  # 5% tolerance
    lower_bound = target_rate * (1 - tolerance)
    upper_bound = target_rate * (1 + tolerance)

    rate_too_high = 0.6
    rate_too_low = 0.4

    print(f"\nTesting with rate too high: {rate_too_high} U/hr")
    mock_pump.set_basal_rate(rate_too_high)
    actual_rate_high = mock_pump.get_basal_rate()
    print(f"Expected range: {lower_bound:.3f} U/hr to {upper_bound:.3f} U/hr")
    print(f"Actual rate: {actual_rate_high:.3f} U/hr")
    # This assertion will fail if the pump *actually* delivers 0.6, which is outside the 5% tolerance of 0.5
    assert lower_bound <= actual_rate_high <= upper_bound, \
        f"Basal rate {actual_rate_high:.3f} U/hr is outside the allowed range " \
        f"[{lower_bound:.3f}, {upper_bound}] U/hr."

    print(f"\nTesting with rate too low: {rate_too_low} U/hr")
    mock_pump.set_basal_rate(rate_too_low)
    actual_rate_low = mock_pump.get_basal_rate()
    print(f"Expected range: {lower_bound:.3f} U/hr to {upper_bound:.3f} U/hr")
    print(f"Actual rate: {actual_rate_low:.3f} U/hr")
    # This assertion will fail if the pump *actually* delivers 0.4, which is outside the 5% tolerance of 0.5
    assert lower_bound <= actual_rate_low <= upper_bound, \
        f"Basal rate {actual_rate_low:.3f} U/hr is outside the allowed range " \
        f"[{lower_bound:.3f}, {upper_bound}] U/hr."


# To run these tests:
# 1. Save the code as a Python file, e.g., `test_pump_basal_rate_PUMP_BASAL_RATE_001.py`.
# 2. Make sure you have pytest installed (`pip install pytest`).
# 3. Run pytest from your terminal in the directory where you saved the file: `pytest`
```

**Explanation:**

1.  **Filename Convention:** The filename `test_pump_basal_rate_PUMP_BASAL_RATE_001.py` clearly indicates the module being tested and the specific requirement ID.

2.  **Mock Pump (`MockPump` class):**
    *   Since we don't have the actual pump hardware or its control software, we create a `MockPump` class. This class simulates the essential behavior:
        *   `set_basal_rate(rate_u_per_hr)`: This method is intended to set the basal rate. In a real test, this would call the pump's API or interact with its control module. Here, it just stores the value.
        *   `get_basal_rate()`: This method simulates retrieving the currently set basal rate from the pump.

3.  **Pytest Fixture (`mock_pump`):**
    *   The `@pytest.fixture` decorator makes `mock_pump` a reusable component for tests.
    *   When a test function requests `mock_pump` as an argument, pytest will call this fixture function, create an instance of `MockPump`, and pass it to the test function.

4.  **Test Function (`test_pump_basal_rate_within_tolerance_PUMP_BASAL_RATE_001`):**
    *   **`@pytest.mark.parametrize`:** This is a powerful pytest feature that allows you to run the same test function multiple times with different sets of input data.
        *   The first argument (`"input_rate, expected_lower_bound, expected_upper_bound"`) defines the names of the arguments that the test function will receive.
        *   The second argument is a list of tuples, where each tuple represents one test case.
        *   We define test cases for:
            *   The nominal value (0.5 U/hr).
            *   Values slightly above and below the nominal value, but still within the ±5% tolerance.
            *   The upper and lower bounds of the ±5% tolerance.
    *   **Requirement ID in Docstring:** The docstring clearly states the requirement ID `PUMP_BASAL_RATE_001`.
    *   **Test Logic:**
        *   `mock_pump.set_basal_rate(input_rate)`: The test sets the basal rate of the mock pump to the `input_rate` for the current test case.
        *   `actual_rate = mock_pump.get_basal_rate()`: The test then retrieves the rate from the mock pump.
        *   **Assertion (`assert expected_lower_bound <= actual_rate <= expected_upper_bound`)**: This is the core of the test. It checks if the `actual_rate` returned by the pump falls within the calculated acceptable range (0.5 U/hr ±5%).
            *   `expected_lower_bound` is calculated as `0.5 * (1 - 0.05) = 0.475`.
            *   `expected_upper_bound` is calculated as `0.5 * (1 + 0.05) = 0.525`.
        *   **Error Message:** A clear error message is provided if the assertion fails, making it easier to understand what went wrong.

5.  **Test for Outside Tolerance (`test_pump_basal_rate_outside_tolerance_PUMP_BASAL_RATE_001`):**
    *   This test demonstrates how you might test values that are *expected* to be outside the tolerance.
    *   It sets rates that are clearly higher (0.6 U/hr) and lower (0.4 U/hr) than the allowed range.
    *   The assertion still checks if these rates fall within the *required* tolerance. If the pump is designed to reject such rates or clamp them, this test would pass if the pump correctly handles them. However, if the pump simply returns the value it was given, this test will fail, indicating that the pump's *delivery* is not conforming to the requirement even if it accepted the command. This is crucial for verifying the *delivery* aspect of the requirement.