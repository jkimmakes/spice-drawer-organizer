# Profile and interface

The current profile is for Ball 4 oz regular-mouth Quilted Crystal jars,
SKU 1440080400. The measurements used in fitting were approximately:

| Feature | mm |
| --- | ---: |
| Capped jar length | 59 |
| Bottom to underside of glass lip | 38 |
| Body near rounded bottom | 60 |
| Body at mid-height | 63 |
| Body just below the glass lip | 66 |
| Projecting glass lip | 70 |
| Rolled metal rim | 73 |
| Metal band | 71 |

Diameters came from printed gauges; axial lengths came from a ruler. Foot
rounding, lip thickness and several hidden transitions remain modeled
assumptions. The supported reference varies lip position from 37–39 mm and
capped length from 58–60 mm during clearance checks.

The fixed cell pitch is 75.8 × 62.5 mm. The jar axis rises 1.5° toward the lid.
A 0.30 mm seam separates neighbouring modules. Connector position is anchored
to each cell, rather than the overall panel size, so 1×1 through 3×3 modules
can join in the same grid. Panels and connectors keep their orientation.

Each broad bow-tie connector has 16 mm round heads, a 10 mm neck, head centres
16 mm apart, and a 1 mm root blend. The socket outline offsets outward by
0.15 mm; the key offsets inward by 0.15 mm. A further 0.15 mm first-layer
relief lasts for the first 0.20 mm of height. This gives a nominal 0.30 mm
clearance between corresponding mating edges.

X keys retain the accepted X3 surface. Y4 keys restore the heel and lid-support
contour missing from the earlier Y3 keys, while retaining the same XY fit.
Old Y3 keys fit the sockets but can sit several millimetres below the intended
surface. Use the current Y4 asset for Y keys and front/back plugs.

The smooth top is a constrained cubic B-spline fitted to the accepted R2
support geometry. The tested two-row skin is repeated with a periodic quintic
blend. At panel and socket edges it approaches R2 heights over a 5 mm collar.
The exact analytical mask then sets the outline and insertion clearance.
The Y4 key preserves an exact R2 perimeter collar and blends to the R4 skin
inside. Existing R4 panels use approximately 0.4 mm surface tessellation at
steep transitions; exact pointwise flushness is not claimed at every facet.

`spice_drawer/data/ball-4oz/assets.json` records the checksums of the spline
data, reference mesh and keys. The generator checks these before building.
These construction assets are not parts to print. Printable files are written
to a generated layout's `stls/` directory and connector plates.

The data assets preserve the fitted surface independently of older
development scripts. The build code does not resize an existing jar cavity
or stretch an assembled STL to fill a different drawer.
