import secrets
import string


class PasswordGenerator:
    """Provides static methods for generated dash-separated randomized sequences"""

    @staticmethod
    def subsequence(alphabet: str, length: int) -> str:
        """Returns a string with `length` random characters from `alphabet`"""
        return "".join([secrets.choice(alphabet) for _ in range(length)])

    @staticmethod
    def new(parts: int, part_length: int) -> str:
        """Returns a string with dash-separated `parts` subsequences consisting of
        `part_length` ascii characters (alphanumeric+some special symbols)"""
        alphabet = string.ascii_letters + string.digits + "@#$%&>~<!?"
        output = ""
        for i in range(parts):
            output += PasswordGenerator.generate_sequence(alphabet, part_length)
            if i != parts - 1:
                output += "-"

        return output
