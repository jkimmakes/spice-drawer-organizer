import argparse
import json
from pathlib import Path
import sys
from .layout import merge_config,plan,write_plan

def parser():
    root=argparse.ArgumentParser(description="Plan and print a modular spice drawer for Ball 4 oz jars.")
    commands=root.add_subparsers(dest="command",required=True)
    layout=commands.add_parser("plan",help="Size the grid and produce an assembly map and quantities")
    layout.add_argument("--config",type=Path)
    layout.add_argument("--out",type=Path,default=Path("build/my-drawer"))
    layout.add_argument("--units",choices=["mm","in"],default="mm",help="Units for dimensional CLI flags; JSON fields are always mm")
    for name in ["drawer-width","drawer-depth","drawer-height","bed-width","bed-depth","brim","clearance"]:
        layout.add_argument("--"+name,type=float)
    for name in ["columns","rows","max-module-columns","max-module-rows"]:
        layout.add_argument("--"+name,type=int)
    layout.add_argument("--track",choices=["universal","drawer-specific"])
    for name in ["build","verify"]:
        command=commands.add_parser(name,help=f"{name.title()} STLs for an existing layout")
        command.add_argument("directory",type=Path)
        command.add_argument("--openscad",default="openscad")
        if name=="build": command.add_argument("--step",type=float,default=.4)
    return root

def main(argv=None):
    args=parser().parse_args(argv)
    try:
        if args.command=="plan":
            config=merge_config(json.loads(args.config.read_text()) if args.config else {})
            dimensions={"drawer_width":("drawer","width_mm"),"drawer_depth":("drawer","depth_mm"),
                "drawer_height":("drawer","height_mm"),"bed_width":("printer","bed_width_mm"),
                "bed_depth":("printer","bed_depth_mm"),"brim":("printer","brim_mm"),"clearance":("layout","clearance_mm")}
            for flag,(group,field) in dimensions.items():
                value=getattr(args,flag)
                if value is not None: config[group][field]=value*(25.4 if args.units=="in" else 1)
            for flag in ["columns","rows","max_module_columns","max_module_rows","track"]:
                value=getattr(args,flag)
                if value is not None: config["layout"][flag]=value
            spec=plan(config);write_plan(spec,args.out)
            print(f"{spec['columns']} × {spec['rows']}: {spec['jars']} jars, {len(spec['panels'])} panels")
            print("Tray:",*spec["footprint_mm"],"mm; connectors:",spec["connector_quantities"])
            print("Plan:",(args.out/"PRINT_PLAN.md").resolve())
        elif args.command=="build":
            from .build import build
            report=build(args.directory,args.openscad,args.step)
            print("Built",len(report["files"]),"unique parts and",len(report["connector_plates"]),"connector plates")
        else:
            from .verify import verify
            report=verify(args.directory,args.openscad)
            print("Passed",report["passed"],"CAD checks")
    except (ValueError,OSError,RuntimeError,AssertionError) as error:
        print("Error:",error,file=sys.stderr)
        raise SystemExit(1)
