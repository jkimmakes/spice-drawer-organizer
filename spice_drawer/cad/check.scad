// Independent solid-geometry checks of generated files.
mode="jar";
file="";
columns=1;
rows=1;
lip=38;
length=59;
kind="panel";
positions=[]; // [file, dx, dy, dz]
target=[]; // [file, dx, dy, dz]
ox=-37.9;
oy=-1.6619453570665357;
$fn=96;

module reference_piece(i) {
    p=[[29,0],[30,2],[31.5,lip/2],[33,lip-2],[35,lip],[35,lip+3],
       [33,lip+4],[33,length-.8]];
    if(i<7) translate([0,0,p[i][1]]) cylinder(r1=p[i][0],r2=p[i+1][0],h=p[i+1][1]-p[i][1]);
    else if(i==7) translate([0,0,lip+3]) cylinder(d=71,h=length-lip-3);
    else translate([0,0,lip+3]) cylinder(d=73,h=2);
}
module jar(sweep=false) {
    for(i=[0:8]) hull() for(lift=sweep?[0,85]:[0])
        translate([0,0,38.5404+lift]) rotate([-88.5,0,0]) reference_piece(i);
}
module part() {
    shift=kind=="panel"?[ox,oy,0]:kind=="key_x"?[21.9,oy+31.25-8,0]:[10.95,oy+62.5-16,0];
    translate(shift) import(file,convexity=12);
}
module placed(p) { translate([p[1],p[2],p[3]]) import(p[0],convexity=12); }
if(mode=="jar" || mode=="sweep") intersection() {
    part();
    for(row=[0:rows-1],col=[0:columns-1]) translate([col*75.8,row*62.5,0]) jar(mode=="sweep");
}
else if(mode=="contacts") intersection() { placed(target); for(p=positions) placed(p); }
else if(mode=="vertical") linear_extrude(height=1) intersection() {
    projection() placed(target); projection() for(p=positions) placed(p);
}
else assert(false,"Unknown check mode");
