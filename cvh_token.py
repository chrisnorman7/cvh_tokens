from dataclasses import dataclass
from typing import cast

import cadquery as cq

from braille import BrailleLine


@dataclass(frozen=True)
class CVHToken:
    """A circular token."""

    radius: float = 12
    """The radius of the circle."""

    thickness: float = 5
    """The thickness of the token."""

    fillet: float = 2.4
    """How much to fillet the edges of the token."""

    braille_string: str = "⠉⠧⠓"
    """The braille to use."""

    text_string: str = "CVH"
    """The text to engrave into the bottom surface."""

    font_size: float = 19
    """The font size to use."""

    text_distance: float = 1.0
    """How deep the text will be engraved."""

    @property
    def text(self) -> cq.Workplane:
        """Get the text to be engraved into the bottom."""
        string = self.text_string
        text = cq.Workplane("XY").text(
            txt=string, distance=self.text_distance, fontsize=self.font_size
        )
        shape = cast(cq.Shape, text.val())
        edge = (self.radius - self.fillet) * 2
        box = shape.BoundingBox()
        if box.xmax > edge:
            raise RuntimeError(
                f"Right edge of text ({box.xmax}) does not fit within token ({edge})."
            )
        if box.ymax > edge:
            raise RuntimeError(
                f"Top edge of text ({box.ymax}) does not fit within token ({edge})."
            )
        return text.rotate((0, 0, 0), (0, 1, 0), 180).translate(
            (0, 0, self.text_distance)
        )

    @property
    def token(self) -> cq.Workplane:
        """Get the token."""
        return (
            cq.Workplane("XY")
            .cylinder(self.thickness, self.radius, centered=(True, True, False))
            .edges("<Z or >Z")
            .fillet(self.fillet)
        )

    @property
    def braille(self) -> cq.Compound:
        """Return the braille to use."""
        braille = BrailleLine(line=self.braille_string).get_shape()
        if braille is None:
            raise RuntimeError(
                f"Braille string {self.braille_string} produced no braille."
            )
        box = braille.BoundingBox()
        edge = (self.radius - self.fillet) * 2
        if box.xlen > edge:
            raise RuntimeError(
                f"Braille width ({box.xlen}) does not fit within token ({edge})."
            )
        if box.ylen > edge:
            raise RuntimeError(
                f"Braille height ({box.ylen}) does not fit within token ({edge})."
            )
        return braille.translate((-box.xlen / 2, -box.ylen / 2, self.radius * 2))

    def get_shape(self) -> cq.Workplane:
        """Get the entire shape."""
        return self.token.cut(self.text).union(self.braille)


if __name__ == "__main__":
    token = CVHToken()
    token.get_shape().export("token.stl")
