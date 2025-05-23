import re

patterns: list[tuple[str, str]] = (
    [r'para', r'$\\parallel$'],
    [r'perp', r'$\\perp$'],
    [r'alpha', r'$\\alpha$'],
    [r'beta', r'$\\beta$'],
    [r'gamma', r'$\\gamma$'],
)

class LabelString:
    """
    A class to convert specific keywords in a string to their corresponding LaTeX representations
    for use in matplotlib labels.

    Example:
        LabelString("para alpha") -> "$\\parallel$ $\\alpha$"
    """
    def __init__(self, value: str) -> None:
        """
        Initialize the LabelString with a given value.

        Args:
            value (str): The input string containing keywords to be converted.
        """
        self.value: str = value

    def __repr__(self) -> str:
            """
            Return the string with specific keywords replaced by their LaTeX representations.

            Returns:
                str: The processed string with LaTeX representations.
            """
            res: str = self.value
            for pattern, repl in patterns:
                res = re.sub(rf'\b{pattern}\b', repl, res)

            return res