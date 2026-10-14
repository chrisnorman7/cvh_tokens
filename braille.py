from collections.abc import Reversible
from dataclasses import dataclass
from typing import ClassVar, Literal, cast

import cadquery as cq

BrailleDots = Literal[6, 8]
"""The possible braille dots."""


@dataclass(frozen=True)
class BrailleSettings:
    """Settings for a type of braille."""

    dot_sides: int | None
    """The number of sides for a braille dot.

    If `dot_sides` is `None`, then each dot will be modelled as a cylinder.
    """

    dot_radius: float
    """The radius of individual braille dots."""

    dot_height: float
    """The height of individual braille dots."""

    dot_spacing_x: float
    """The space between dots 123, and 456."""

    dot_spacing_y: float
    """The space between dots 36, 25, and 14."""

    cell_spacing: float
    """The space between cells on the same line."""

    dot_fillet: float | None
    """The amount to fillet individual dots.

    If `dot_fillet` is `None`, then the top of dots will be left alone.
    """

    line_spacing: float
    """The space between braille lines."""

    standard: ClassVar["BrailleSettings"]
    """Settings for standard braille."""

    standard_fillet: ClassVar["BrailleSettings"]
    """Settings for standard braille with a fillet."""

    jumbo: ClassVar["BrailleSettings"]
    """Settings for jumbo braille."""

    bolt_head: ClassVar["BrailleSettings"]
    """Settings for bolt head braille."""

    def braille_dot(self) -> cq.Shape:
        """Model a single braille dot."""
        workplane = cq.Workplane("XY")
        sides = self.dot_sides
        radius = self.dot_radius
        if sides is None:
            workplane = workplane.cylinder(
                height=self.dot_height, radius=radius, centered=False
            )
        else:
            workplane = (
                workplane.polygon(sides, radius * 2)
                .translate((radius, radius, 0))
                .extrude(self.dot_height)
            )
        fillet = self.dot_fillet
        if fillet is not None:
            workplane = workplane.edges(">Z").fillet(fillet)
        return cast(
            cq.Shape,
            workplane.val(),
        )

    def braille_cell(self, char: str, dots: BrailleDots = 6) -> cq.Compound | None:
        """Model a single braille cell.

        This method will return `None` if `char` is a space character.
        """
        parts: list[cq.Shape] = []
        bits = braille_bits(char, dots=dots)
        for i, dot in enumerate(bits):
            if dot:
                col = 0 if i < 3 else 1
                row = [0, 1, 2, 0, 1, 2, 3, 3][i]
                x = self.dot_radius + col * self.dot_spacing_x
                y = (
                    (self.dot_radius * (dots / 2)) - row
                ) * self.dot_spacing_y + self.dot_radius
                parts.append(self.braille_dot().translate((x, y, 0)))
        if len(parts) == 0:
            return None
        return cq.Compound.makeCompound(parts)

    def braille_line(self, line: str, dots: BrailleDots = 6) -> cq.Compound | None:
        """Model a braille line with these settings.

        You can model either 6 or 8 dot braille."""
        cells: list[cq.Compound] = []
        for i, char in enumerate(line):
            if not is_braille_character(char):
                if not is_allowed_braille_spacing(char):
                    raise ValueError(
                        f'Non-braille character "{char}" found in braille line "{line}".'
                    )
                continue
            result = self.braille_cell(char, dots=dots)
            if result is not None:
                cells.append(result.translate((i * self.cell_spacing, 0, 0)))
        if len(cells) == 0:
            return None
        return cq.Compound.makeCompound(cells)


BrailleSettings.standard = BrailleSettings(
    dot_sides=16,
    dot_radius=0.75,
    dot_height=0.6,
    dot_spacing_x=2.5,
    dot_spacing_y=2.5,
    cell_spacing=6.0,
    dot_fillet=None,
    line_spacing=10.0,
)

BrailleSettings.standard_fillet = BrailleSettings(
    dot_sides=16,
    dot_radius=0.75,
    dot_height=0.5,
    dot_spacing_x=2.5,
    dot_spacing_y=2.5,
    cell_spacing=6.0,
    dot_fillet=0.49,
    line_spacing=10.0,
)

BrailleSettings.jumbo = BrailleSettings(
    dot_sides=None,
    dot_radius=1.5,
    dot_height=1,
    dot_spacing_x=4,
    dot_spacing_y=4,
    cell_spacing=8,
    dot_fillet=None,
    line_spacing=16,
)

BrailleSettings.bolt_head = BrailleSettings(
    dot_sides=None,
    dot_radius=2,
    dot_height=2,
    dot_spacing_x=5,
    dot_spacing_y=5,
    cell_spacing=10,
    dot_fillet=0.2,
    line_spacing=17,
)


def braille_bits(character: str, dots: int = 6) -> list[int]:
    """Return the bits of a 6-dot braille character.

    `dots` should be 6 or 8, depending on whether you want to use 6 or 8 dot braille. The length of the resulting list will be equal to `dots`.
    """
    code = ord(character)

    braille_min = 0x2800
    braille_max = 0x28FF
    if code < braille_min or code > braille_max:
        raise ValueError(f"Not a braille character: {character}.")

    value = code - braille_min

    return [1 if value & (1 << i) else 0 for i in range(dots)]


def is_braille_character(char: str) -> bool:
    return 0x2800 <= ord(char) <= 0x28FF


def is_allowed_braille_spacing(char: str) -> bool:
    return char.isspace() or char == "\u2800"


@dataclass(frozen=True)
class BrailleLine:
    """A class which represents a single line of braille."""

    line: str
    """The braille text."""

    settings: BrailleSettings = BrailleSettings.standard
    """The braille settings to use."""

    def get_shape(self, dots: BrailleDots = 6) -> cq.Compound | None:
        """Return the line as geometry."""
        return self.settings.braille_line(self.line, dots=dots)


def multiline_braille(
    lines: Reversible[BrailleLine], dots: BrailleDots = 6, print_progress: bool = True
) -> cq.Compound:
    """Model multiline braille.

    The `dots` argument should be either 6 or 8, for 6 or 8 dot braille."""
    parts: list[cq.Compound] = []
    y = 0
    for line in reversed(lines):
        result = line.get_shape(dots=dots)
        if result is not None:
            if print_progress:
                box = result.BoundingBox()
                print(f"{line}:\n{box.xlen}, {box.ylen}, {box.zlen}")
            parts.append(result.translate((0, y, 0)))
        y += line.settings.line_spacing
    if len(parts) == 0:
        raise ValueError("No braille characters were found.")
    return cq.Compound.makeCompound(parts)
