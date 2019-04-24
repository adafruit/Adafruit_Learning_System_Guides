// LED Icosahedron visual prototype, via Adafruit Industries
// This DOES NOT communicate with Arduino or LEDs, it is strictly
// for testing the geometry.

static final int nPoints = 12;                   // # polyhedron vertices
PVector          pt[]    = new PVector[nPoints]; // 3D vertex coordinates

void setup() {
  int   i;
  float c, r, h, angle, a;

  size(400, 400, P3D);
  sphereDetail(6);

  // Calculate a few icoshedron fundamentals (thanks Wikipedia!)
  c = 2.0 * sin(radians(72.0) / 2.0);           // Edge length (chord)
  r = (c / 4.0) * sqrt(10.0 + 2.0 * sqrt(5.0)); // Radius of circumsphere
  h = sqrt(c * c - 1.0);                        // Height of "endcaps"

  // Place vertices using 5-fold symmetry around Y axis.
  // Processing 3D coord system is a little funky, positive Y being down.
  pt[0] = new PVector(0.0, -r, 0.0);            // Point 0 = top vertex
  for(angle=0.0, i=1; i<6; i++, angle += 72.0) {
    a       = radians(angle);                   // Azimuth of "upper" vertex
    pt[i]   = new PVector(cos(a), h-r, sin(a)); // Points 1-5 = upper ring
    a       = radians(angle + 36.0);            // Azimuth of "lower" vertex
    pt[i+5] = new PVector(cos(a), r-h, sin(a)); // Points 6-10 = lower ring
  }
  pt[11] = new PVector(0.0, r, 0.0);            // Point 11 = Bottom vertex
}

void draw() {
  int i, j, k;

  background(0);
  translate(width / 2.0, height / 2.0);
  rotateX(frameCount * 0.01);
  rotateY(frameCount * 0.01);
  rotateZ(frameCount * 0.01);
  scale(width / 3.0);

  for(i=0; i<5; i++) {
    j = 1 + (i + 1) % 5;
    k = 6 + (i + 1) % 5;
    face(0,i+1,j);   // Top endcap faces
    face(i+1,j,i+6); // Upper mid faces
    face(j,i+6,k);   // Lower mid faces
    face(i+6,k,11);  // Bottom endcap faces
  }
}

void face(int p1, int p2, int p3) {
  int     x, y;
  PVector a, b, c, ab, bc, n;

  // Draw polygon face
  a = pt[p1]; b = pt[p2]; c = pt[p3];
  fill(128);
  stroke(255);
  beginShape(TRIANGLES);
  vertex(a.x, a.y, a.z);
  vertex(b.x, b.y, b.z);
  vertex(c.x, c.y, c.z);
  endShape();

  // Interpolate & draw LED dots
  ab = PVector.div(PVector.sub(b, a), 7.0); // Edge vectors, scaled
  bc = PVector.div(PVector.sub(c, b), 7.0); // to 1/2 pixel spacing
  fill(220);
  noStroke();
  for(y=0; y<3; y++) {
    for(x=0; x<=y; x++) {
      n = PVector.add(PVector.add(a,
        PVector.mult(bc, (x*2+1))), PVector.mult(ab, (y*2+2)));
      pushMatrix();
      translate(n.x, n.y, n.z);
      scale(0.01); // Processing has trouble with tiny spheres,
      sphere(5);   // so set 'scale' small & draw a big one.
      popMatrix();
    }
  }
}
