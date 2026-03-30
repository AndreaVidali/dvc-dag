"""Color helpers for DVC DAG rendering."""

import random

from copy import deepcopy

import webcolors

from dvc_dag.logger import logger


def needs_white_text(name_color: str) -> bool:
    """Return True if the provided color needs a white text if used as background.

    From https://www.w3.org/TR/AERT/#color-contrast
    """
    rgb = webcolors.name_to_rgb(name_color)
    brightness = (rgb.red * 299 + rgb.green * 587 + rgb.blue * 114) / 1000
    return brightness < 128  # Threshold: 0-255 scale  # noqa: PLR2004


class Colors:
    """Handle the colors for each node category.

    Colors must be compatible with https://graphviz.org/doc/info/colors.html
    """

    def __init__(self, random_seed: int = 42) -> None:
        """Initialize the color palette and random seed."""
        self.category_to_color: dict[str, str] = {}
        self.available_colors = self.get_all_colors()
        random.seed(random_seed)

    def get_all_colors(self) -> list[str]:
        """Return the entire palette."""
        return deepcopy(webcolors.names("css3"))

    def fetch(self) -> str:
        """Return a new color."""
        if not self.available_colors:
            logger.warning("All available colors have been used, resetting the palette.")
            self.available_colors = self.get_all_colors()

        picked_color = random.choice(self.available_colors)  # noqa: S311
        self.available_colors.remove(picked_color)
        return picked_color

    def get_category_color(self, category: str) -> str:
        """Return the color assigned to the provided category."""
        if category not in self.category_to_color:
            self.category_to_color[category] = self.fetch()

        return self.category_to_color[category]
