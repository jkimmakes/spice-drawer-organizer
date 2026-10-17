"""Build portable R4 panels and current X3/Y4 connectors from a layout."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import numpy as np
from .geometry import distance_inside,ease,periodic_surface,raster,write_height_solid,write_plate
from .layout import plan,write_plan
from .mesh import read_mesh,verify
from .normalize import normalize
from .profile import check_assets,DATA,ORIGIN,PACKAGE,PITCH

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def cad(executable, output, settings, source="parts.scad", empty=False):
    command = [executable,"--hardwarnings","--export-format","binstl","-o",str(output)]
    for name, value in settings.items():
        command += ["-D",name+"="+json.dumps(value)]
    result = subprocess.run(command+[str(PACKAGE/"cad"/source)],capture_output=True,text=True,timeout=300)
    log = result.stdout+result.stderr
    if "WARNING:" in log or "ERROR:" in log:
        raise RuntimeError(log)
    if empty:
        if "Current top level object is empty." not in log:
            raise RuntimeError("Unexpected geometry in clearance check:\n"+log)
    elif result.returncode or not output.exists():
        raise RuntimeError(log)

def load_plan(output):
    stored = json.loads((output/"layout.json").read_text())
    calculated = plan(stored["config"])
    if calculated != stored:
        raise ValueError("layout.json differs from its configuration; regenerate the plan")
    return stored

def build(output, openscad, step=.4):
    if not .25 <= step <= .45:
        raise ValueError("STL sample step must be 0.25–0.45 mm")
    check_assets()
    spec = load_plan(output)
    stls = output/"stls"; cache = output/"_construction"
    stls.mkdir(exist_ok=True); cache.mkdir(exist_ok=True)
    data = np.load(DATA/"surface_r4.npz")
    references, results = {}, {}
    for kind in spec["panel_quantities"]:
        panel = next(p for p in spec["panels"] if p["part"] == kind)
        cols, rows = panel["columns"], panel["rows"]
        settings = dict(columns=cols,rows=rows,edges=panel["edges"])
        if (cols,rows) not in references:
            x0,x1 = ORIGIN[0]+.16,ORIGIN[0]+cols*PITCH[0]-.16
            y0,y1 = ORIGIN[1]+.16,ORIGIN[1]+rows*PITCH[1]-.16
            xs = np.linspace(x0,x1,math.ceil((x1-x0)/step)+1)
            ys = np.linspace(y0,y1,math.ceil((y1-y0)/step)+1)
            original = raster(DATA/"reference_r2_3x3.stl",xs,ys)
            if original.min()<2.39:
                raise ValueError("Incomplete reference surface")
            references[cols,rows] = xs,ys,original,periodic_surface(data,xs,ys)
        xs,ys,original,skin = references[cols,rows]
        maskfile = cache/(kind+"_mask.stl")
        cad(openscad,maskfile,dict(settings,mode="mask"))
        mask = raster(maskfile,xs,ys)>.5
        distance = distance_inside(mask,(xs[1]-xs[0],ys[1]-ys[0]))
        weight = ease((distance-.8)/5)
        z = original*(1-weight)+skin*weight
        if z.min()<2.4 or z.max()>20.0724:
            raise ValueError("Surface outside the supported height limits")
        stock = cache/(kind+"_stock.stl")
        write_height_solid(stock,np.r_[xs[0]-.2,xs,xs[-1]+.2],
                           np.r_[ys[0]-.2,ys,ys[-1]+.2],np.pad(z,1,mode="edge"))
        dest = stls/(kind+".stl")
        cad(openscad,dest,dict(settings,mode="panel",stock=str(stock.resolve())))
        normalize(dest)
        info = verify(*read_mesh(dest))
        expected = [round(cols*PITCH[0]-.3,3),round(rows*PITCH[1]-.3,3),20.072]
        if info["size_mm"] != expected or info["bounds_mm"][2][0] != 0:
            raise ValueError(f"Unexpected panel dimensions: {kind}: {info}")
        results[dest.name] = dict(mesh=info,sha256=digest(dest))
        print("BUILT",dest.name,flush=True)
    for kind in spec["connector_quantities"]:
        dest = stls/(kind+".stl")
        if kind in ["key_x","key_y"]:
            shutil.copyfile(DATA/(kind+".stl"),dest)
        else:
            axis = "x" if kind in ["plug_left","plug_right"] else "y"
            cad(openscad,dest,dict(mode="plug",accessory_kind=kind,
                accessory_file=str((DATA/f"key_{axis}.stl").resolve())))
            normalize(dest)
        results[dest.name] = dict(mesh=verify(*read_mesh(dest)),sha256=digest(dest))
        print("BUILT",dest.name,flush=True)
    plates = []
    printer = spec["config"]["printer"]
    # Separate key/plug plates avoid accidentally printing the same quantity
    # twice. Large layouts spill to numbered plates that still fit the bed.
    for group, prefix in [("keys","key_"),("plugs","plug_")]:
        files = [stls/(kind+".stl") for kind,n in spec["connector_quantities"].items()
                 if kind.startswith(prefix) for _ in range(n)]
        while files:
            dest = output/f"PRINT_ONCE_{group}_{len(plates)+1:02d}.stl"
            count = len(files)
            while count:
                if write_plate(dest,files[:count],(printer["bed_width_mm"],printer["bed_depth_mm"]),printer["brim_mm"]):
                    break
                count -= 1
            if not count:
                raise ValueError("Unable to pack connector plate")
            info = verify(*read_mesh(dest),expected_components=count)
            plates.append(dict(file=dest.name,group=group,parts=count,sha256=digest(dest),mesh=info))
            files = files[count:]
    report = dict(profile="ball-4oz",surface="R4",key_revisions=dict(key_x="X3",key_y="Y4"),
                  sample_step_mm=step,files=results,connector_plates=plates,
                  status="Built and mesh checked; run verify before printing")
    (output/"build.json").write_text(json.dumps(report,indent=2)+"\n")
    write_plan(spec,output)
    note = "\n## Connector plates\n\nPrint each listed plate **once**, instead of the corresponding individual connectors in the quantity table.\n\n"
    for plate in plates:
        note += f"- [{plate['file']}]({plate['file']}): {plate['parts']} {plate['group']}.\n"
    with (output/"PRINT_PLAN.md").open("a") as document:
        document.write(note)
    return report
