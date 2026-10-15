from dataclasses import dataclass
from typing import cast

import cadquery as cq

from braille import BrailleLine


@dataclass(frozen=True)
class CVHToken:
    """A circular token."""

    radius: float = 18
    """The radius of the circle."""

    thickness: float = 3.5
    """The thickness of the token."""

    fillet: float = 1.5
    """How much to fillet the edges of the token."""

    braille_string: str = "⠉⠧⠓"
    """The braille to use."""

    text_string: str = "CVH"
    """The text to engrave into the bottom surface."""

    font_size: float = 14
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
        edge = self.radius - self.fillet
        box = shape.BoundingBox()
        if box.xmin < -edge:
            raise RuntimeError(
                f"Left edge of text ({box.xmin}) does not fit within token ({-edge})."
            )
        if box.xmax > edge:
            raise RuntimeError(
                f"Right edge of text ({box.xmax}) does not fit within token ({edge})."
            )
        if box.ymin < -edge:
            raise RuntimeError(
                f"Bottom edge of text ({box.ymin}) does not fit within token ({-edge})."
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
        edge = self.radius - self.fillet
        if box.xmin < -edge:
            raise RuntimeError(
                f"Braille left edge ({box.xmin}) does not fit within token ({-edge})."
            )
        if box.xmax > edge:
            raise RuntimeError(
                f"Braille width ({box.xmax}) does not fit within token ({edge})."
            )
        if box.ymin < -edge:
            raise RuntimeError(
                f"Braille bottom edge ({box.ymin}) does not fit within token ({-edge})."
            )
        if box.ymax > edge:
            raise RuntimeError(
                f"Braille height ({box.ymax}) does not fit within token ({edge})."
            )
        return braille.translate(
            (-box.xlen / 2, -box.ylen / 2, self.thickness - box.zmin)
        )

    def get_shape(self) -> cq.Workplane:
        """Get the entire shape."""
        return self.token.cut(self.text).union(self.braille)

    def nest(self, size: float = 256, spacing: float = 1) -> list[cq.Shape]:
        """Nest as many tokens as possible.

        Arguments:
            size: The size of the area to nest tokens within.
            spacing: The spacing between tokens.
        """
        objects: list[cq.Shape] = []
        token = self.get_shape()
        shape = cast(cq.Shape, token.val())
        box = shape.BoundingBox()
        shape = shape.translate((-box.xmin, -box.ymin, -box.zmin))
        width = self.radius * 2
        full_width = width + spacing
        multiplier = int(size // full_width)
        for x in range(multiplier):
            for y in range(multiplier):
                objects.append(shape.translate((x * full_width, y * full_width, 0)))
        return objects


if __name__ == "__main__":
    token = CVHToken()
    objects = token.nest()
    nest = cq.Compound.makeCompound(objects)
    box = nest.BoundingBox()
    print(box.xlen, box.ylen)
    token.get_shape().export("token.step")
    nest.export("nest.step")
