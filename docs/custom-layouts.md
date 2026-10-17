# Plan a layout for your drawer

The planner takes the space in your drawer and divides it into panels your
printer can make. It uses the tested Ball 4 oz jar shape throughout, so
changing the arrangement keeps the fit of each cradle and key intact.

## Start with the measurements

Measure the inside width and depth of the drawer and the available height
with it closed. The supported jar profile uses a fixed 75.8 × 62.5 mm pitch
and a 1.5° tilt. The empty tray is about 20.1 mm tall; the nominal loaded
height is 76.2 mm. Different jars or a different packing pitch need another
profile; resizing an STL also changes
the jar pockets and connector fit.

Planning needs Python 3.10 or newer. Clone this repository and open its folder:

```sh
git clone https://github.com/jkimmakes/spice-drawer-organizer.git
cd spice-drawer-organizer
```

Run the planner with your drawer and printer dimensions, in millimetres:

```sh
python3 -m spice_drawer plan \
  --drawer-width 379.2 --drawer-depth 502.7 \
  --bed-width 250 --bed-depth 210 \
  --out build/my-drawer
```

Open `build/my-drawer/PRINT_PLAN.md` and `assembly.svg` to review the result.
This example selects 5×8, six panels, eight X keys and ten Y keys. The default
universal layout also needs twenty-six plugs for the unused outside sockets.

Use `--units in` for dimensional command-line flags in inches. JSON
configurations always use millimetres. Two examples are included:
[the 5×8 drawer](../examples/drawer_5x8.json) and
[a smaller drawer](../examples/small_drawer.json).

```sh
python3 -m spice_drawer plan --config examples/small_drawer.json --out build/small
```

## Choose the edges

**Universal** is the default. Every panel has female sockets on all four edges,
so it can move within the grid or accept an extension. Matching plugs fill
unused sockets along the outside. Remove a plug to add another panel.

Use `--track drawer-specific` to put sockets only at joins needed for the
selected layout. The outside edges are solid and require no plugs. All panels
and keys retain the same orientation: lids and underside arrows point toward
the back of the drawer.

## Adjust the plan

| Option | What it changes |
| --- | --- |
| `--columns`, `--rows` | Requests an exact grid; a grid that does not fit is rejected. |
| `--max-module-columns`, `--max-module-rows` | Limits each panel to 1–3 cells in each direction. |
| `--bed-width`, `--bed-depth` | Sets the printer's usable bed dimensions. |
| `--brim` | Reserves space around each print; defaults to 3 mm. |
| `--clearance` | Reserves total spare width and depth in the drawer; defaults to 0.5 mm. |

Clearance is the **total**, rather than a value per side. Increase it for an
uneven drawer or uncertain measurements; this can reduce the number of jars
that fit. Printer fit includes the configured brim. Balanced panel divisions
avoid thin final strips where possible.

## Build the printable files

Install the Python build dependency and [OpenSCAD](https://openscad.org):

```sh
python3 -m pip install -e '.[build]'
python3 -m spice_drawer build build/my-drawer
python3 -m spice_drawer verify build/my-drawer
```

If OpenSCAD is outside your command path, pass its executable explicitly:

```sh
python3 -m spice_drawer build build/my-drawer \
  --openscad /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD
python3 -m spice_drawer verify build/my-drawer \
  --openscad /Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD
```

The source includes its required profile assets. A fresh checkout can build
without any earlier STLs or development directory. Panel and individual
connector files appear in `stls/`; connector print plates appear beside the
print plan. Large connector sets split across plates that fit the selected bed.

Follow the [printing and assembly guide](assembly.md) for settings and
quantities. The plan lists individual connectors as well as plates containing
them; choose one approach so you print the right number.

## Check the result

The verifier checks closed printable meshes, dimensions, modeled jar fit and
vertical removal, and actual connector insertion at the selected joins. The
printed 5×8 set uses an accepted R2 panel at the front-left and smoother R4
panels elsewhere. Generated layouts use the R4 skin, R2 boundary contours and
current X3/Y4 keys. See the [design notes](design.md) for the profile details.

Run the planner tests with:

```sh
python3 -m unittest discover -s tests -v
```

A fit trial remains useful for a new printer, filament or batch of jars.
