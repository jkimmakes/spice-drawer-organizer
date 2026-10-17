from copy import deepcopy
import math
from pathlib import Path
import tempfile
import unittest
from spice_drawer.layout import plan,write_plan
from spice_drawer.cli import main

BASE={"drawer":{"width_mm":379.2,"depth_mm":502.7}}

class LayoutTests(unittest.TestCase):
    def test_measured_drawer(self):
        p=plan(BASE)
        self.assertEqual((p["columns"],p["rows"],p["jars"]),(5,8,40))
        self.assertEqual(p["footprint_mm"],[378.7,499.7])
        self.assertEqual(len(p["panels"]),6)
        self.assertEqual(p["connector_quantities"],dict(key_x=8,key_y=10,plug_left=8,plug_right=8,plug_front=5,plug_back=5))
    def test_outside_edges_and_cell_coverage(self):
        for columns in range(1,11):
            for rows in range(1,12):
                for track in ["universal","drawer-specific"]:
                    p=plan({"drawer":{"width_mm":columns*75.8+1,"depth_mm":rows*62.5+1},
                            "layout":{"track":track}})
                    cells={}
                    for panel in p["panels"]:
                        x,y,w,h=(panel[k] for k in ["column","row","columns","rows"])
                        self.assertLessEqual(w*75.8-.3+6,250)
                        self.assertLessEqual(h*62.5-.3+6,210)
                        for a in range(x,x+w):
                            for b in range(y,y+h):
                                self.assertNotIn((a,b),cells);cells[a,b]=panel["id"]
                        if track=="drawer-specific":
                            self.assertEqual(panel["edges"],[int(x>0),int(x+w<columns),int(y>0),int(y+h<rows)])
                    self.assertEqual(len(cells),columns*rows)
                    expected_x=sum(cells[x,y]!=cells[x+1,y] for x in range(columns-1) for y in range(rows))
                    expected_y=sum(cells[x,y]!=cells[x,y+1] for x in range(columns) for y in range(rows-1))
                    self.assertEqual(p["connector_quantities"].get("key_x",0),expected_x)
                    self.assertEqual(p["connector_quantities"].get("key_y",0),expected_y)
    def test_small_bed(self):
        p=plan(dict(BASE,printer={"bed_width_mm":180,"bed_depth_mm":180}))
        self.assertTrue(all(t["columns"]<=2 and t["rows"]<=2 for t in p["panels"]))
    def test_rejects_unsafe_or_mistyped_inputs(self):
        for change in [{"drawer":{"width_mm":-1}},{"drawer":{"height_mm":60}},
                       {"layout":{"columns":6}},{"layout":{"max_module_rows":4}},
                       {"printer":{"bed_width_mm":60}},{"drawer":{"width_mm":math.nan}},
                       {"layout":{"columns":True}},{"layout":{"clearence_mm":2}},
                       {"profile":"unknown"}]:
            config=deepcopy(BASE)
            for key,value in change.items():
                if isinstance(value,dict): config.setdefault(key,{}).update(value)
                else: config[key]=value
            with self.assertRaises(ValueError): plan(config)
    def test_imperial_flags_and_files(self):
        with tempfile.TemporaryDirectory() as folder:
            main(["plan","--units","in","--drawer-width",str(379.2/25.4),"--drawer-depth",str(502.7/25.4),"--out",folder])
            for name in ["layout.json","assembly.svg","PRINT_PLAN.md"]:
                self.assertTrue((Path(folder)/name).is_file())

if __name__=="__main__": unittest.main()
