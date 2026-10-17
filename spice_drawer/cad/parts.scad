// Cell-anchored M3 C interface. Dimensions and orientation match X3 / Y4.
columns=3;
rows=3;
edges=[1,1,1,1]; // left, right, front, back
mode="panel"; // panel, mask, plug
stock="";
accessory_file="";
accessory_kind="plug_left";
px=75.8;
py=62.5;
ox=-37.9;
oy=-1.6619453570665357;
gap=.30;

module bowtie() {
    offset(delta=-1) offset(r=1,$fn=48) union() {
        translate([-5,-8]) square([10,16]);
        for(y=[-8,8]) translate([0,y]) circle(d=16,$fn=64);
    }
}
module outline() {
    difference() {
        translate([ox+gap/2,oy+gap/2]) square([columns*px-gap,rows*py-gap]);
        for(side=[0:1]) if(edges[side]) for(row=[0:rows-1])
            translate([ox+side*columns*px,oy+(row+.5)*py]) rotate(-90)
                offset(delta=gap/2) bowtie();
        for(side=[0:1]) if(edges[side+2]) for(col=[0:columns-1])
            translate([(col+.25)*px,oy+side*rows*py]) offset(delta=gap/2) bowtie();
    }
}
module printable_mask() {
    linear_extrude(height=.2) offset(delta=-.15) children();
    translate([0,0,.2]) linear_extrude(height=150) children();
}
module arrow() {
    translate([0,0,-.01]) linear_extrude(height=.36)
        polygon([[-.4,-2],[.4,-2],[.4,.5],[1.2,.5],[0,2.2],[-1.2,.5],[-.4,.5]]);
}
module panel() {
    difference() {
        intersection() { import(stock,convexity=12); printable_mask() outline(); }
        translate([0,oy+30,-.01]) linear_extrude(height=.36)
            mirror([1,0,0]) text(str("SD ",columns,"x",rows),size=3.5,halign="center",valign="center");
        translate([25,oy+30,0]) arrow();
    }
}
module plug() {
    intersection() {
        import(accessory_file,convexity=12);
        if(accessory_kind=="plug_left") translate([16+gap/2,-20,-1]) cube([40,70,80]);
        else if(accessory_kind=="plug_right") translate([-40,-20,-1]) cube([56-gap/2,70,80]);
        else if(accessory_kind=="plug_front") translate([-20,16+gap/2,-1]) cube([70,40,80]);
        else if(accessory_kind=="plug_back") translate([-20,-40,-1]) cube([70,56-gap/2,80]);
        else assert(false,"Unknown outer plug");
    }
}
assert(columns>=1 && columns<=3 && rows>=1 && rows<=3);
if(mode=="mask") linear_extrude(height=1) outline();
else if(mode=="panel") translate([-ox,-oy,0]) panel();
else if(mode=="plug") plug();
else assert(false,"Unknown output mode");
