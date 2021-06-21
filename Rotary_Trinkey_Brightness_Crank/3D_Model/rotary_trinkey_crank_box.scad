shaft_cutout = 6.2 + 1.7;

Z_HEIGHT = 30;
X_HEIGHT = 36;
Y_HEIGHT = 38;
THICKNESS = 1.5 * 2;

USB_CUTOUT_Z = 20;
USB_CUTOUT_X = 17;
USB_CUTOUT_Y = 40;

TAB_SIZE = 6;
TAB_HEIGHT = 2;
TAB_TOLERANCE = 0.1;

USB_WALL_OFFSET = 1;

/*
difference(){
    cube([X_HEIGHT, Y_HEIGHT, Z_HEIGHT], center=true);
    translate([0,0,THICKNESS/2])
    cube([X_HEIGHT-THICKNESS, Y_HEIGHT-THICKNESS, Z_HEIGHT], center=true);
    
    translate([10,-3,0])
    rotate([0,90,0])
    cylinder(r=shaft_cutout/2, h=40, center=true, $fn=30);
    
    translate([X_HEIGHT/2 - USB_CUTOUT_X/2 - THICKNESS/2 - USB_WALL_OFFSET,20,0])
    cube([USB_CUTOUT_X, USB_CUTOUT_Y, USB_CUTOUT_Z], center=true);
}*/


/*
translate([7.5,20.5 - 3,0])
rotate([-90,0,-90])
import("4964 Rotary Trinkey.stl");
*/

module close_tab(){
    difference(){
        cube([TAB_SIZE,TAB_SIZE,TAB_HEIGHT], center=true);
        translate([1.5, 1.5, 0])
        cube([TAB_SIZE,TAB_SIZE,TAB_HEIGHT+1], center=true);
    }
}


module lid(){
    cube([X_HEIGHT, Y_HEIGHT, THICKNESS/2], center=true);
    
    translate([
        -X_HEIGHT/2 + 6/2 + THICKNESS/2 + TAB_TOLERANCE,
        -Y_HEIGHT/2 + 6/2 + THICKNESS/2 + TAB_TOLERANCE,
        THICKNESS/4 + 2/2
    ])
    close_tab();
    
    translate([
        X_HEIGHT/2 - 6/2 - THICKNESS/2 - TAB_TOLERANCE,
        Y_HEIGHT/2 - 6/2 - THICKNESS/2 - TAB_TOLERANCE,
        THICKNESS/4 + 2/2
    ])
    rotate([0,0,180])
    close_tab();
    
    translate([
        X_HEIGHT/2 - 6/2 - THICKNESS/2 - TAB_TOLERANCE,
        -Y_HEIGHT/2 + 6/2 + THICKNESS/2 + TAB_TOLERANCE,
        THICKNESS/4 + 2/2
    ])
    rotate([0,0,90])
    close_tab();
    
    translate([
        -X_HEIGHT/2 + 6/2 + THICKNESS/2 + TAB_TOLERANCE,
        Y_HEIGHT/2 - 6/2 - THICKNESS/2 - TAB_TOLERANCE,
        THICKNESS/4 + 2/2
    ])
    rotate([0,0,270])
    close_tab();
}

translate([0,0,16])
//rotate([0,180,0])
lid();

//translate([0, Y_HEIGHT/2-1, 10])
//cube([1,1,1], center=true);
