rows = 4;
cols = 5;
border = 3;

dx = .76*25.4;
dy = .76*25.4;

sx = .551*25.4;
sy = .551*25.4;

hdia = 5.5; // note: m2.5 nylon screw heads are 4.5mm dia
linear_extrude(.06*25.4)
difference() {
    translate([-border-sx/2,-border-sx/2])
    square([dx*(rows-1) + sx + 2*border, dy*(cols-1) + sy +2*border]);

    for(r=[0:1:rows-1]) {
        for(c=[0:1:cols-1]) {
            translate([dx*r, dy*c])
            square([sx,sy], center=true);
        }

        translate([dx/2, dy/2])
        circle(d=hdia, $fn=36);
        translate([dx*(2 +1/2), dy/2])
        circle(d=hdia, $fn=36);
    }

}
