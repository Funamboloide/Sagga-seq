// SAGGA HUB: the tray under the FM-1 that holds the modules: Raspberry Pi 3B, powerbank, MICROMIDITRS-USB v2,
// RP2040-Zero. Parametric: measure your own parts and the FM-1, put the numbers in the first block, press F6, export
// the STL. Units: mm. The FM-1 sits on top in a shallow seat and closes the tray; the modules sit below in pockets;
// the cables run in the gap above them. Print: PETG or PLA, 0.2 mm layers, 3 walls, no supports (open top).
//
// Coordinates: x from the left wall, y from the front wall, z from the floor; module positions are those of their
// front-left corner INSIDE the tray (the wall thickness is added for you).

// ============================ 1. measure these ============================
// the FM-1: length left-right, depth front-back, height; and where its ports are on its back face
fm1 = [236, 92, 34];                 // PLACEHOLDER
fm1_usbc_from_left = 30;             // PLACEHOLDER: centre of its USB-C socket, from its left edge
fm1_seat_depth = 6;                  // how far the FM-1 sinks into the seat (a lip all around; keep it under its ports)

// the Raspberry Pi 3B (fixed numbers, Raspberry Pi's own drawing), USB face toward the left wall
pi = [85, 56, 20];                   // board + connectors + the pegs it rests on
pi_pos = [14, 5];                    // x = the recess: cables from outside reach its four USB-A through the window
pi_usb_face_up = 12;                 // centre of the USB block above the floor (3 mm pegs + board + 8 mm)

// the powerbank: measure it, and where its input socket and button are
pb = [150, 70, 16];                  // PLACEHOLDER: length, depth, height
pb_pos = [106, 9];                   // PLACEHOLDER
pb_wall = "right";                   // the wall its input socket faces: "right", "back", "front" (or "left")
pb_in_along = 44;                    // PLACEHOLDER: centre of the input socket along that wall, measured from the
                                     //   front (right/left wall) or from the left (back/front wall), INSIDE coordinates
pb_in_up = 8;                        // PLACEHOLDER: its centre above the floor (the powerbank lies flat: ~ half its height)
pb_in_win = [15, 9];                 // the window: wide enough for the charger plug's overmold (USB-C plugs are ~ 12 x 6.5)
pb_btn_along = 60;                   // PLACEHOLDER: the power button, same wall (set to -1 if it has none you need)
pb_btn_d = 8;

// the MICROMIDITRS-USB v2: jacks and LEDs on one face, toward the back wall. Measure the body and the jack spacing.
midi = [40, 20, 12];                 // PLACEHOLDER
midi_pos = [20, 66];                 // PLACEHOLDER
midi_jack_dx = [-5, 5];              // PLACEHOLDER: the two TRS jacks, from the centre of its back face
midi_jack_up = 7;                    // PLACEHOLDER: their centre above the floor
midi_jack_d = 7;                     // hole for a 3.5 mm plug's barrel

// the RP2040-Zero (23.5 x 18), USB-C toward the back wall: the "PC" socket
rp = [24, 18, 6];
rp_pos = [72, 68];

// ============================ 2. the tray ============================
wall_t = 2.4;
floor_t = 2.0;
gap = 8;                             // cable room above the tallest module
corner = 4;
rib_h = 5;                           // the pockets' ribs

modules = [[pi, pi_pos], [pb, pb_pos], [midi, midi_pos], [rp, rp_pos]];
function need_x() = max([for (m = modules) m[1][0] + m[0][0]]) + 3;
function need_y() = max([for (m = modules) m[1][1] + m[0][1]]) + 3;
function tallest() = max([for (m = modules) m[0][2]]);

inner = [max(fm1[0], need_x()), max(fm1[1], need_y())];      // the tray grows past the FM-1 if the modules need it
inner_h = tallest() + gap;
tray = [inner[0] + 2 * wall_t, inner[1] + 2 * wall_t, floor_t + inner_h + fm1_seat_depth];
seat_off = [(inner[0] - fm1[0]) / 2, (inner[1] - fm1[1]) / 2];   // the FM-1 seat is centred on the tray

echo(str("tray ", tray[0], " x ", tray[1], " x ", tray[2], " mm; inner ", inner[0], " x ", inner[1], ", modules need ",
         need_x(), " x ", need_y()));
if (need_x() > fm1[0] || need_y() > fm1[1])
    echo("NOTE: the modules need more room than the FM-1's footprint: the tray is wider than the FM-1");

module rrect(size, r) { offset(r = r) offset(delta = -r) square(size); }

module shell() {
    difference() {
        linear_extrude(tray[2]) rrect([tray[0], tray[1]], corner);
        // the module space
        translate([wall_t, wall_t, floor_t]) linear_extrude(inner_h + 1) rrect(inner, corner - 1);
        // the seat: the FM-1 drops in fm1_seat_depth and rests on the rim of the module space
        translate([wall_t + seat_off[0] - 0.4, wall_t + seat_off[1] - 0.4, tray[2] - fm1_seat_depth])
            cube([fm1[0] + 0.8, fm1[1] + 0.8, fm1_seat_depth + 1]);
    }
}

// a window through one wall. along: its centre along the wall, inside coordinates (from the front for the left and
// right walls, from the left for the front and back walls); up: its centre above the floor; w, h: its size;
// d > 0 instead: a round hole of that diameter.
module win(wall, along, up, w = 0, h = 0, d = 0) {
    z = floor_t + up;
    a = wall_t + along;
    t = wall_t + 2;
    if (wall == "back")  translate([a, tray[1] - wall_t - 1, z]) rotate([-90, 0, 0]) hole(w, h, d, t);
    if (wall == "front") translate([a, -1, z])                    rotate([-90, 0, 0]) hole(w, h, d, t);
    if (wall == "left")  translate([-1, a, z])                    rotate([0, 90, 0])  hole(h, w, d, t);
    if (wall == "right") translate([tray[0] - wall_t - 1, a, z])  rotate([0, 90, 0])  hole(h, w, d, t);
}
module hole(w, h, d, t) {   // a prism along +z of length t, centred in x/y, square-ish or round
    if (d > 0) cylinder(d = d, h = t, $fn = 32);
    else translate([-w / 2, -h / 2, 0]) cube([w, h, t]);
}

module windows() {
    // the Pi's four USB-A (and the Ethernet, same block) through the left wall; the recess in front of them is
    // where the inside cables (FM-1, MICROMIDITRS) plug in too
    win("left", pi_pos[1] + pi[1] / 2, pi_usb_face_up, 54, 20);
    // the PC socket: the RP2040-Zero's USB-C
    win("back", rp_pos[0] + rp[0] / 2, 4, 11, 6);
    // the MIDI TRS jacks
    for (dx = midi_jack_dx) win("back", midi_pos[0] + midi[0] / 2 + dx, midi_jack_up, d = midi_jack_d);
    // the powerbank: charge it without taking it out, and reach its button
    win(pb_wall, pb_in_along, pb_in_up, pb_in_win[0], pb_in_win[1]);
    if (pb_btn_along >= 0) win(pb_wall, pb_btn_along, pb_in_up, d = pb_btn_d);
    // the FM-1's own USB-C: a slot through the seat's back lip so the right-angle plug comes down into the tray
    translate([wall_t + seat_off[0] + fm1_usbc_from_left - 8, tray[1] - wall_t - 1, floor_t + inner_h - 10])
        cube([16, wall_t + 2, 10 + fm1_seat_depth + 1]);
    // air under the Pi
    for (i = [0 : 6]) translate([wall_t + pi_pos[0] + 6 + i * 11, wall_t + pi_pos[1] + 6, -1]) cube([6, pi[1] - 12, floor_t + 2]);
}

module pockets() {   // low ribs around each module (not the Pi: its pegs locate it, and its USB block overhangs)
    for (m = [[pb, pb_pos], [midi, midi_pos], [rp, rp_pos]])
        translate([wall_t + m[1][0] - 1.2, wall_t + m[1][1] - 1.2, floor_t])
            difference() {
                cube([m[0][0] + 2.4, m[0][1] + 2.4, rib_h]);
                translate([1.2, 1.2, -1]) cube([m[0][0], m[0][1], rib_h + 2]);
            }
}

module pi_pegs() {   // the 3B rests on four pegs through its M2.5 holes (58 x 49 pattern, 3.5 mm from the edges);
                     // the board is turned so the USB block faces the left wall
    for (h = [[85 - 3.5, 3.5], [85 - 61.5, 3.5], [85 - 3.5, 52.5], [85 - 61.5, 52.5]])
        translate([wall_t + pi_pos[0] + h[0], wall_t + pi_pos[1] + h[1], floor_t]) {
            cylinder(d = 5, h = 3, $fn = 24);
            cylinder(d = 2.3, h = 3 + 4, $fn = 24);
        }
}

difference() {
    union() { shell(); pockets(); pi_pegs(); }
    windows();
}

// For checking: the modules as ghosts (comment out before export, or leave: % renders them transparent, not exported)
%for (m = modules) translate([wall_t + m[1][0], wall_t + m[1][1], floor_t]) cube(m[0]);
%translate([wall_t + seat_off[0], wall_t + seat_off[1], tray[2] - fm1_seat_depth]) cube(fm1);
