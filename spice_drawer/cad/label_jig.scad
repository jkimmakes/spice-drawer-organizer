// One-piece Ball 4 oz jar label guide. Dimensions in millimetres.
// The circular base and guide retain the V2 seating and label geometry.
// No separate spacer or clamping mechanism.
$fn = 96;
part = "jig"; // jig, assembly, checks
check_mode = "jar"; // jar, insertion, label_removal
jar_length = 59;
floor_height = 3;
base_radius = 38;
floor_cutout_radius = 25;
label_center = 18.5; // Height above the glass bottom, not the print bed.
label_width = 35;
label_height = 18;
radial_clearance = 0.65;
wall = 2.4;
label_bottom = label_center-label_height/2;
label_top = label_center+label_height/2;
guide_height = label_top+2;

assert(jar_length >= 58 && jar_length <= 60);
assert(label_bottom > 0 && label_width > 0 && label_height > 0);
assert(floor_height > 0 && radial_clearance > 0 && wall > 0);
assert(floor_cutout_radius < 29 && base_radius > guide_r(guide_height)+wall);

function jar_r(z) = z<2 ? 29+z/2 : 30+3*(z-2)/34;
function guide_r(z) = max(31.25,jar_r(z)+radial_clearance);
function bump(z,zc,h,d) = d*max(0,1-abs(z-zc)/h);
function opening_angle(z) = (label_width/2+0.30
    +bump(z,label_center,1,1)+bump(z,label_top,0.6,0.6))
    /guide_r(z)*180/PI;
function polar(r,a,z) = [r*sin(a),-r*cos(a),z];

// Loft between equally sized CCW cross-sections; OpenSCAD winding reversed.
module loft(sections) {
    n=len(sections[0]);
    pts=[for(section=sections) each section];
    faces=concat([[for(i=[n-1:-1:0]) i]],
        [[for(i=[0:n-1]) (len(sections)-1)*n+i]],
        [for(k=[0:len(sections)-2],i=[0:n-1]) each
            let(a=k*n+i,b=k*n+(i+1)%n,c=(k+1)*n+(i+1)%n,d=(k+1)*n+i)
            [[a,b,c],[a,c,d]]]);
    polyhedron(pts,[for(f=faces) [for(i=[len(f)-1:-1:0]) f[i]]],convexity=12);
}

module sector(profile,half) {
    rotate([0,0,-90-half]) rotate_extrude(angle=2*half,convexity=10)
        polygon(profile);
}

module shell(height,half=180) {
    hs=concat([0,2,4,6,8],[for(z=[10:2:height-0.01]) z],[height]);
    sector(concat([for(z=hs) [guide_r(z)+wall,z]],
        [for(i=[len(hs)-1:-1:0]) [guide_r(hs[i]),hs[i]]]),half);
}

module label_slot() {
    zs=[label_bottom,label_center-1,label_center,label_center+1,
        label_top-0.6,label_top,label_top+0.6,guide_height+1];
    loft([for(z=zs) concat([[0,0,z]],
        [for(i=[0:12]) polar(100,-opening_angle(z)+2*opening_angle(z)*i/12,z)])]);
}

module label_and_cup() {
    difference() {
        union() {
            shell(12);
            shell(guide_height,42);
        }
        label_slot();
    }
}

module base() {
    difference() {
        union() {
            linear_extrude(floor_height) difference() {
                circle(r=base_radius);
                circle(r=floor_cutout_radius);
            }
            translate([0,0,floor_height]) label_and_cup();
        }
        translate([0,-36,floor_height-0.3]) linear_extrude(0.5)
            text("FRONT",size=2.5,halign="center",valign="center",
                font="Liberation Sans:style=Bold");
    }
}

module jar() {
    rotate_extrude() polygon([[0,0],[29,0],[30,2],[31.5,19],[33,36],
        [35,38],[35,41],[33,42],[33,jar_length-1],[0,jar_length-1]]);
    translate([0,0,41.5]) cylinder(r=36.5,h=2);
    translate([0,0,43.5]) cylinder(r=35.5,h=jar_length-43.5);
}

// Thin reference label follows the tapered jar surface; not a print part.
module label() {
    sector([[jar_r(label_bottom)+0.05,label_bottom],
        [jar_r(label_top)+0.05,label_top],
        [jar_r(label_top)+0.30,label_top],
        [jar_r(label_bottom)+0.30,label_bottom]],
        label_width/(2*jar_r(label_center))*180/PI);
}

if(part=="jig") color([0.12,0.50,0.46]) base();
else if(part=="assembly") {
    color([0.12,0.50,0.46]) base();
    color([0.75,0.79,0.80]) render() translate([0,0,floor_height]) jar();
    color([1,1,1]) translate([0,0,floor_height]) label();
}
else if(part=="checks") {
    if(check_mode=="jar") intersection() {
        base(); translate([0,0,floor_height+0.02]) jar();
    }
    else if(check_mode=="insertion")
        for(d=[1,5,15,30,60,90]) translate([d*5,0,0]) intersection() {
            base(); translate([0,0,floor_height+d]) jar();
        }
    else if(check_mode=="label_removal")
        for(d=[0,1,5,10,15,30,60]) translate([d*5,0,0]) intersection() {
            base(); translate([0,0,floor_height+d]) label();
        }
    else assert(false,"Unknown check");
}
else assert(false,"Unknown part");
