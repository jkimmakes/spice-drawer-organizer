"""Remove metadata chunks from PNGs without changing their pixel data."""
from pathlib import Path
import struct
import sys

def strip(path):
    raw=path.read_bytes()
    if raw[:8]!=b"\x89PNG\r\n\x1a\n": raise ValueError("Expected PNG")
    output=bytearray(raw[:8]);offset=8
    while offset<len(raw):
        length=struct.unpack_from(">I",raw,offset)[0]
        end=offset+length+12;kind=raw[offset+4:offset+8]
        if end>len(raw): raise ValueError("Incomplete PNG")
        if kind not in [b"eXIf",b"tEXt",b"zTXt",b"iTXt"]: output.extend(raw[offset:end])
        offset=end
    path.write_bytes(output)
    print(path.name,"metadata removed; pixel chunks preserved")

if __name__=="__main__":
    for name in sys.argv[1:]: strip(Path(name))
