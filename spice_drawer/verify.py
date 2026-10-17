"""Verify the actual exported parts and their configured assembly."""
from concurrent.futures import ThreadPoolExecutor
import json
import tempfile
from pathlib import Path
from .build import cad,digest,load_plan
from .mesh import read_mesh,verify as verify_mesh
from .profile import check_assets,ORIGIN,PITCH

def position(spec, connector, file):
    kind,col,row = (connector[k] for k in ["kind","column","row"])
    if kind in ["key_x","plug_left","plug_right"]:
        anchor = [ORIGIN[0]+col*PITCH[0],ORIGIN[1]+(row+.5)*PITCH[1],0]
        center = [16,8,0]
    else:
        anchor = [(col+.25)*PITCH[0],ORIGIN[1]+row*PITCH[1],0]
        center = [8,16,0]
    return [str(file.resolve())]+[anchor[i]-center[i] for i in range(3)]

def verify(output, openscad, workers=2):
    check_assets();spec=load_plan(output)
    build=json.loads((output/"build.json").read_text())
    stls=output/"stls"
    for name,info in build["files"].items():
        path=stls/name
        if digest(path)!=info["sha256"]:
            raise ValueError(f"Part changed after building: {name}")
        mesh=verify_mesh(*read_mesh(path))
        printer=spec["config"]["printer"]
        if abs(mesh["bounds_mm"][2][0])>.0001:
            raise ValueError(f"Part does not sit on the bed: {name}")
        if any(mesh["size_mm"][i]+2*printer["brim_mm"]>printer[field]+.001
               for i,field in enumerate(["bed_width_mm","bed_depth_mm"])):
            raise ValueError(f"Part does not fit the configured bed: {name}")
    for plate in build["connector_plates"]:
        path=output/plate["file"]
        if digest(path)!=plate["sha256"]:
            raise ValueError("Connector plate changed")
        verify_mesh(*read_mesh(path),expected_components=plate["parts"])
    jobs=[]
    for part in spec["panel_quantities"]:
        panel=next(p for p in spec["panels"] if p["part"]==part)
        for lip in [37,38,39]:
            for length in [58,59,60]:
                for mode in ["jar","sweep"]:
                    jobs.append((f"{part}-{mode}-{lip}-{length}",dict(mode=mode,
                        file=str((stls/(part+".stl")).resolve()),columns=panel["columns"],rows=panel["rows"],lip=lip,length=length)))
    for kind in ["key_x","key_y"]:
        if kind not in spec["connector_quantities"]: continue
        for mode in ["jar","sweep"]:
            jobs.append((f"{kind}-{mode}",dict(mode=mode,kind=kind,
                file=str((stls/(kind+".stl")).resolve()),columns=2,rows=2)))
    placed=[]
    for p in spec["panels"]:
        placed.append((p,[str((stls/(p["part"]+".stl")).resolve()),
            ORIGIN[0]+p["column"]*PITCH[0],ORIGIN[1]+p["row"]*PITCH[1],0]))
    # Only intersect each connector with panels whose bounding rectangles
    # touch that seam. This verifies actual sockets and actual plug clipping.
    for index,connector in enumerate(spec["connectors"]):
        col,row,kind=connector["column"],connector["row"],connector["kind"]
        is_x=kind in ["key_x","plug_left","plug_right"]
        adjacent=[]
        for p,transform in placed:
            a,b=p["column"],p["row"]
            if is_x:
                hit=col in [a,a+p["columns"]] and b<=row<b+p["rows"]
            else:
                hit=row in [b,b+p["rows"]] and a<=col<a+p["columns"]
            if hit: adjacent.append(transform)
        if not adjacent:
            raise ValueError("Connector without an adjacent panel")
        target=position(spec,connector,stls/(kind+".stl"))
        for mode in ["contacts","vertical"]:
            jobs.append((f"connector-{index}-{kind}-{mode}",dict(mode=mode,positions=adjacent,target=target)))
    with tempfile.TemporaryDirectory(prefix="spice-drawer-check-") as folder:
        folder=Path(folder)
        def run(job):
            name,settings=job
            cad(openscad,folder/(name+".stl"),settings,source="check.scad",empty=True)
            print("PASS",name,flush=True)
            return name
        with ThreadPoolExecutor(max_workers=workers) as pool:
            checks=list(pool.map(run,jobs))
    report=dict(passed=len(checks),checks=checks,files={name:v["sha256"] for name,v in build["files"].items()},
        scope="Mesh closure, bed contact, jar fit/lift for modeled size variants, actual connector collision and vertical insertion. Physical fit and friction depend on the printer and jars.")
    (output/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
    return report
