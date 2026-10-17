"""Package a verified layout for printing; omit construction meshes and caches."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

def package(directory, destination):
    layout=json.loads((directory/"layout.json").read_text())
    build=json.loads((directory/"build.json").read_text())
    verification=json.loads((directory/"verification.json").read_text())
    files=[]
    for name,info in build["files"].items():
        path=directory/"stls"/name
        sha=hashlib.sha256(path.read_bytes()).hexdigest()
        if sha!=info["sha256"] or sha!=verification["files"][name]:
            raise ValueError("Changed or unverified STL: "+name)
        files.append(path)
    for plate in build["connector_plates"]:
        path=directory/plate["file"]
        if hashlib.sha256(path.read_bytes()).hexdigest()!=plate["sha256"]:
            raise ValueError("Changed connector plate")
        files.append(path)
    files += [directory/name for name in ["PRINT_PLAN.md","assembly.svg","layout.json","build.json","verification.json"]]
    destination.parent.mkdir(parents=True,exist_ok=True)
    checksums="".join(hashlib.sha256(p.read_bytes()).hexdigest()+"  "+str(p.relative_to(directory))+"\n" for p in files)
    with zipfile.ZipFile(destination,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in files: archive.write(path,str(path.relative_to(directory)))
        archive.writestr("SHA256SUMS.txt",checksums)
        if archive.testzip() is not None: raise ValueError("Archive verification failed")
    print(destination,layout["jars"],"jars",destination.stat().st_size,"bytes")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory",type=Path)
    p.add_argument("destination",type=Path)
    a=p.parse_args();package(a.directory,a.destination)
