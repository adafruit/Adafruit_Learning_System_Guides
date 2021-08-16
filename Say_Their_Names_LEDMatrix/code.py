import time
import board
import displayio
import framebufferio
import rgbmatrix
import terminalio
import adafruit_display_text.label

names = [
    "Rodney King",
    "Abner Louima",
    "Amadou Diallo",
    "Sean Bell",
    "Oscar Grant",
    "Eric Garner",
    "Michael Brown",
    "Laquan McDonald",
    "Freddie Gray",
    "Antwon Rose Jr",
    "Ahmaud Arbery",
    "Breonna Taylor",
    "John Crawford III",
    "Ezell Ford",
    "Dante Parker",
    "Michelle Cusseaux",
    "Laquan Mcdonald",
    "George Mann",
    "Tanisha Anderson",
    "Akai Gurley",
    "Tamir Rice",
    "Rumain Brisbon",
    "Jerame Reid",
    "Matthew Ajibade",
    "Frank Smart",
    "Nastasha McKenna",
    "Tony Robinson",
    "Anthony Hill",
    "Mya Hall",
    "Phillip White",
    "Eric Harris",
    "Walter Scott",
    "William Chapman II",
    "Alexia Christian",
    "Brendon Glenn",
    "Victor Maunel Larosa",
    "Jonathan Sanders",
    "Freddie Blue",
    "Joseph Mann",
    "Salvado Ellswood",
    "Sanda Bland",
    "Albert Joseph Davis",
    "Darrius Stewart",
    "Billy Ray Davis",
    "Samuel Dubose",
    "Michael Sabbie",
    "Brian Keith Day",
    "Christian Taylor",
    "Troy Robinson",
    "Asshams Pharoah Manley",
    "Felix Kumi",
    "Keith Harrison Mcleod",
    "Junior Prosper",
    "Lamontez Jones",
    "Paterson Brown",
    "Dominic Hutchinson",
    "Anthony Ashford",
    "Alonzo Smith",
    "Tyree Crawford",
    "India Kager",
    "La'vante Biggs",
    "Michael Lee Marshall",
    "Jamar Clark",
    "Richard Perkins",
    "Nathaniel Harris Pickett",
    "Benni Lee Tignor",
    "Miguel Espinal",
    "Michael Noel",
    "Kevin Matthews",
    "Bettie Jones",
    "Quintonio Legrier",
    "Keith Childress Jr",
    "Janet Wilson",
    "Randy Nelson",
    "Antronie Scott",
    "Wendell Celestine",
    "David Joseph",
    "Calin Roquemore",
    "Dyzhawn Perkins",
    "Christoper Davis",
    "Marco Loud",
    "Peter Gaines",
    "Torry Robison",
    "Darius Robinson",
    "Kevin Hicks",
    "Mary Truxillo",
    "Demarcus Semer",
    "Willie Tillman",
    "Terrill Thomas",
    "Sylville Smith",
    "Sean Reed",
    "Alton Streling",
    "Philando Castile",
    "Terence Crutcher",
    "Paul O'Neal",
    "Alteria Woods",
    "Jordan Edwards",
    "Aaron Bailey",
    "Ronell Foster",
    "Stephon Clark",
    "Antwon Rose II",
    "Botham Jean",
    "Pamela Turner",
    "Dominique Clayton",
    "Atatiana Jefferson",
    "Christopher Whitfield",
    "Christopher Mccovey",
    "Eric Reason",
    "Michael Lorenzo Dean",
    "Tony McDade",
    "David McAtee",
    "George Floyd",
]

displayio.release_displays()
matrix = rgbmatrix.RGBMatrix(
    width=64,
    bit_depth=4,
    rgb_pins=[board.D6, board.D5, board.D9, board.D11, board.D10, board.D12],
    addr_pins=[board.A5, board.A4, board.A3, board.A2],
    clock_pin=board.D13,
    latch_pin=board.D0,
    output_enable_pin=board.D1,
)
display = framebufferio.FramebufferDisplay(matrix)

# Create a 3 line set of small font text
blm_font = [None, None, None]
for line in range(3):
    label = adafruit_display_text.label.Label(
        terminalio.FONT, color=0xFFFFFF, x=2, y=line * 10 + 5
    )
    blm_font[line] = label

# Create a 2 line set of font text
names_font = [None, None]
for line in range(2):
    label = adafruit_display_text.label.Label(
        terminalio.FONT,
        color=0xFFFFFF,
        anchored_position=(32, line * 14)  # these will center text when anchor is top-middle
    )
    label.anchor_point = (0.5, 0)
    names_font[line] = label

g = displayio.Group()
for line in blm_font:
    g.append(line)
for line in names_font:
    g.append(line)
display.show(g)


while True:
    # show three small font lines in white
    for line in blm_font:
        line.color = 0xFFFFFF
    # set up text
    blm_font[0].text = "BLACK"
    blm_font[1].text = "LIVES"
    blm_font[2].text = "MATTER"
    time.sleep(1)

    blm_font[1].color = blm_font[2].color = 0  # hide lines 2&3
    time.sleep(1)
    blm_font[1].color = 0xFFFFFF  # show middle line
    blm_font[0].color = blm_font[2].color = 0  # hide lines 1&3
    time.sleep(1)
    blm_font[2].color = 0xFFFFFF  # show last line
    blm_font[0].color = blm_font[1].color = 0  # hide lines 1&2
    time.sleep(1)

    # hide the three small text lines
    for line in blm_font:
        line.color = 0
    time.sleep(1)

    for name in names:
        # say their names!
        print(name)
        lines = name.split(" ")
        names_font[0].text = lines[0]
        names_font[1].text = lines[1]
        time.sleep(5)
    names_font[0].text = names_font[1].text = ""
