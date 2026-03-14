import re
from app.utils.logger import get_logger

logger = get_logger(__name__)


def parse_diff_with_positions(patch: str | None) -> dict[int, int]:
    """
    Returns a mapping of {actual_line_number: diff_position}.

    GitHub's review API requires diff positions (sequential line offsets
    within the diff hunk), not actual file line numbers.
    """
    if not patch:
        return {}

    position_map: dict[int, int] = {}
    position = 0
    current_line = 0

    for line in patch.split("\n"):
        position += 1

        if line.startswith("@@"):
            match = re.search(r"\+(\d+)", line)
            if match:
                current_line = int(match.group(1)) - 1
        elif line.startswith("+") and not line.startswith("+++"):
            current_line += 1
            position_map[current_line] = position
        elif not line.startswith("-"):
            current_line += 1

    return position_map


def get_diff_position(position_map: dict[int, int], line: int) -> int:
    """Returns the diff position for a given line number, defaulting to 1."""
    return position_map.get(line, 1)
