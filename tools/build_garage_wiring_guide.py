"""Build the wiring drawings and printable guide; no photo manipulation."""
from pathlib import Path
from html import escape
import sys

ROOT = Path(__file__).resolve().parents[1]
if (ROOT / ".diagram-deps").is_dir():
    sys.path.insert(0, str(ROOT / ".diagram-deps"))
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF

DOCS = ROOT / "docs"
W, H = 1600, 1100
INK = "#172e43"
COL = {"GND": "#344454", "5V": "#d26916", "3V3": "#a738a3", "IN1": "#17835d", "IN2": "#52677b", "B1": "#138fbc", "B2": "#138fbc", "OUT1": "#2760c5", "OUT2": "#2760c5", "BIAS1": "#dc8b20", "BIAS2": "#dc8b20"}


class Drawing:
    def __init__(self, title, subtitle, page):
        self.s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', '<rect width="1600" height="1100" fill="white"/>']
        self.text(50, 61, title, 36, bold=True)
        self.text(50, 102, subtitle, 21)
        self.line([(50, 126), (1550, 126)], "#cfdae3", 2)
        self.text(50, 1074, "LOLIN D1 mini V4 / photographed Wiegand reader | proposed build; not bench-tested", 17)
        self.text(1505, 1074, f"{page}/5", 18)

    def text(self, x, y, text, size=21, color=INK, bold=False, anchor="start"):
        self.s.append(f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{"bold" if bold else "normal"}" fill="{color}" text-anchor="{anchor}">{escape(str(text))}</text>')

    def rect(self, x, y, w, h, fill="#f1f6fa", stroke="#b6c9d6", radius=10):
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')

    def line(self, pts, color=INK, width=4, dash=False):
        attr = 'stroke-dasharray="9 6"' if dash else ''
        self.s.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" {attr}/>')

    def dot(self, x, y, color=INK, r=6):
        self.s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')

    def note(self, y, lines, fill="#fff1d9"):
        self.rect(50, y, 1500, 24 + 30 * len(lines), fill, fill)
        for i, line in enumerate(lines):
            self.text(70, y + 32 + i * 30, line, 21)

    def save(self, name):
        p = DOCS / name
        p.write_text("\n".join(self.s + ["</svg>"]) + "\n", encoding="utf-8", newline="\n")
        return p


def overview():
    d = Drawing("1. Complete wiring and the exact D1 mini pads", "USB powers the D1 mini. A separate fixed, regulated 12 V DC adapter powers the reader.", 1)
    d.rect(50, 175, 360, 165)
    d.text(75, 210, "Reader's 12 V DC adapter", 25, bold=True)
    d.text(75, 249, "+12 V -> reader RED only")
    d.text(75, 284, "Negative -> common GND")
    d.text(75, 316, "Plug-in supply; no mains wiring", 17)
    d.rect(50, 400, 360, 360)
    d.text(75, 440, "Outdoor reader cable", 27, bold=True)
    wires = [("RED", "+12 V", "#c03432"), ("BLACK", "GND", COL["GND"]), ("BROWN", "GND: select WG34", "#8a5036"), ("GREEN", "D0 -> interface IN1", COL["IN1"]), ("WHITE", "D1 -> interface IN2", COL["IN2"]), ("BLUE", "LED: insulate end", "#2760c5"), ("YELLOW", "BEEP: insulate end", "#aa7b00")]
    for i, (a, b, c) in enumerate(wires):
        d.text(75, 482 + i * 36, a, 20, c, True)
        d.text(177, 482 + i * 36, b, 20)
    d.line([(410, 259), (440, 259), (440, 370), (30, 370), (30, 475), (50, 475)], "#c03432")
    d.rect(500, 400, 390, 360)
    d.text(525, 440, "Soldered input interface", 27, bold=True)
    for i, t in enumerate(["Two identical NPN channels", "IN1: GREEN reader D0", "IN2: WHITE reader D1", "OUT1 -> pad 5 SCL (D1)", "OUT2 -> pad 4 SDA (D2)", "5V -> VBUS; 3V3 -> 3V3", "GND -> common GND"]):
        d.text(525, 488 + i * 36, t, 21)
    d.line([(410, 590), (470, 590), (470, 500), (500, 500)], COL["IN1"])
    d.line([(410, 625), (450, 625), (450, 540), (500, 540)], COL["IN2"])
    d.rect(1080, 225, 315, 485, "#d6eafa", "#659abf")
    d.text(1237, 262, "LOLIN D1 MINI", 24, bold=True, anchor="middle")
    d.text(1237, 291, "LABEL SIDE / BACK", 17, anchor="middle")
    left = ["TX", "RX", "5 SCL", "4 SDA", "0", "2", "GND", "VBUS"]
    right = ["RST", "A0", "16", "14 SCK", "12 MISO", "13 MOSI", "15 SS", "3V3"]
    for i in range(8):
        y = 329 + i * 41
        d.dot(1102, y, "white", 9)
        d.dot(1373, y, "white", 9)
        d.text(1120, y + 7, left[i], 21, bold=i in [2,3,6,7])
        d.text(1355, y + 7, right[i], 20, bold=i == 7, anchor="end")
    d.rect(1200, 680, 75, 58, "#626f7c", "#626f7c", 5)
    d.text(1240, 785, "USB-C", 22, bold=True, anchor="middle")
    d.text(1240, 819, "5 V USB wall charger", 21, anchor="middle")
    d.line([(1237, 738), (1237, 756)], COL["5V"], 9)
    d.line([(890, 540), (965, 540), (965, 411), (1102, 411)], COL["OUT1"])
    d.text(923, 398, "OUT1", 18, COL["OUT1"])
    d.line([(890, 581), (988, 581), (988, 452), (1102, 452)], COL["OUT2"])
    d.text(993, 482, "OUT2", 18, COL["OUT2"])
    d.text(949, 700, "5V bias only", 18, COL["5V"])
    d.text(1330, 895, "3V3 to interface only", 19, COL["3V3"])
    d.line([(410, 302), (460, 302), (460, 910), (1060, 910), (1060, 575), (1102, 575)], COL["GND"])
    d.line([(890, 655), (1008, 655), (1008, 616), (1102, 616)], COL["5V"])
    d.line([(1373, 616), (1450, 616), (1450, 870), (870, 870), (870, 760)], COL["3V3"])
    for x, y in [(460, 910), (700, 910)]: d.dot(x, y, COL["GND"])
    d.line([(410, 515), (430, 515), (430, 910), (460, 910)], COL["GND"])
    d.line([(410, 552), (425, 552), (425, 930), (700, 930), (700, 910)], "#8a5036")
    d.line([(700, 760), (700, 910)], COL["GND"])
    d.text(720, 940, "COMMON GND: adapter -, reader BLACK/BROWN, interface, D1 mini", 19)
    d.note(962, ["Orient your board by its printed labels. Reader D1 is NOT board D1; follow the mapping above.", "12 V never goes to VBUS, 3V3 or GPIO. Leave gate motor/relay wiring to the existing HA gate controller."])
    return d.save("garage-reader-wiring.svg")


def resistor(d, a, b, label):
    x1,y1=a; x2,y2=b
    d.line([a,b], INK, 3)
    if y1==y2:
        d.rect((x1+x2)/2-43, y1-13, 86, 26, "#f4deaf", INK, 4)
        d.text((x1+x2)/2, y1-28, label, 20, bold=True, anchor="middle")
    else:
        d.rect(x1-13, (y1+y2)/2-39, 26, 78, "#f4deaf", INK, 4)
        d.text(x1+30, (y1+y2)/2+7, label, 20, bold=True)


def schematic():
    d = Drawing("2. Electrical schematic - build both channels", "Every filled dot is a soldered junction. Crossing lines without a dot must stay electrically separate.", 2)
    for ch, y, input_name, gpio in [(1,355,"GREEN / reader D0","5 SCL / GPIO5 / board D1"),(2,765,"WHITE / reader D1","4 SDA / GPIO4 / board D2")]:
        d.text(55, y-177, f"CHANNEL {ch}: {input_name}", 25, bold=True)
        d.text(60, y-113, "Board VBUS / USB 5 V", 20, COL["5V"])
        d.line([(300,y-120),(350,y-120)], COL["5V"])
        d.rect(350,y-133,90,26,"#e39458",INK,3)
        d.line([(422,y-134),(422,y-106)], INK,6)
        d.text(395,y-155,f"D{ch} 1N4148",18,anchor="middle")
        d.text(400,y-80,"Stripe toward resistor",18,anchor="middle")
        d.line([(440,y-120),(470,y-120)],INK)
        resistor(d,(470,y-120),(650,y-120),f"R{4 if ch==1 else 8}  10k")
        d.line([(650,y-120),(685,y-120),(685,y)],COL[f"IN{ch}"])
        d.text(55,y+32,"Reader DATA",21,COL[f"IN{ch}"])
        d.line([(55,y),(720,y)],COL[f"IN{ch}"])
        d.dot(685,y,COL[f"IN{ch}"])
        resistor(d,(720,y),(905,y),f"R{1 if ch==1 else 5}  47k")
        d.line([(905,y),(1055,y)],COL[f"B{ch}"])
        d.dot(965,y,COL[f"B{ch}"])
        resistor(d,(965,y+35),(965,y+135),f"R{2 if ch==1 else 6}  100k")
        d.line([(965,y),(965,y+35)],COL[f"B{ch}"])
        d.line([(965,y+135),(965,y+160),(1120,y+160)],COL["GND"])
        d.s.append(f'<circle cx="1090" cy="{y}" r="53" fill="white" stroke="{INK}" stroke-width="2"/>')
        d.line([(1055,y),(1070,y),(1070,y-25),(1070,y+25)],INK)
        d.line([(1070,y-13),(1120,y-50),(1120,y-125)],INK)
        d.line([(1070,y+13),(1120,y+50),(1120,y+160)],COL["GND"])
        d.s.append(f'<polygon points="1118,{y+50} 1099,{y+43} 1110,{y+32}" fill="{INK}"/>')
        d.text(1142,y+14,f"Q{ch} 2N3904",22,bold=True)
        d.text(1030,y+12,"B",18)
        d.text(1130,y-62,"C",18)
        d.text(1130,y+92,"E",18)
        d.text(1140,y+165,"GND",20,COL["GND"])
        d.dot(1120,y-125,COL[f"OUT{ch}"])
        d.line([(1120,y-125),(1505,y-125)],COL[f"OUT{ch}"])
        d.text(1160,y-98,f"OUT{ch} -> {gpio}",20,COL[f"OUT{ch}"])
        # Pull-up is a separate parallel branch, not in series with GPIO.
        d.line([(1190,y-125),(1190,y-187),(1230,y-187)],COL["3V3"])
        resistor(d,(1230,y-187),(1390,y-187),f"R{3 if ch==1 else 7} 10k")
        d.line([(1390,y-187),(1490,y-187)],COL["3V3"])
        d.text(1490,y-201,"Board 3V3",19,COL["3V3"],anchor="end")
        d.dot(1190,y-125,COL[f"OUT{ch}"])
    d.note(960,["GPIO is connected to the collector junction, not through the collector pull-up resistor.","Both firmware Wiegand pins stay inverted: true. All four resistors in each channel are required here."])
    return d.save("garage-reader-schematic.svg")


# Isolated-pad perfboard coordinates. Viewed from component side.
PADS = {
    "5V": ["B2", "D2", "D12"], "3V3": ["V2", "T4", "T14"],
    "GND": ["V18", "J6", "L8", "J16", "L18"],
    "IN1": ["B6", "D4", "N2"], "B1": ["H4", "K6", "H8"],
    "OUT1": ["V6", "L6", "P4"], "BIAS1": ["H2", "J2"],
    "IN2": ["B16", "D14", "N12"], "B2": ["H14", "K16", "H18"],
    "OUT2": ["V16", "L16", "P14"], "BIAS2": ["H12", "J12"],
}
PARTS = [
    ("D1", "1N4148", "D2", "H2"), ("R4", "10k", "J2", "N2"),
    ("R1", "47k", "D4", "H4"), ("R3", "10k", "P4", "T4"),
    ("R2", "100k", "H8", "L8"),
    ("D2", "1N4148", "D12", "H12"), ("R8", "10k", "J12", "N12"),
    ("R5", "47k", "D14", "H14"), ("R7", "10k", "P14", "T14"),
    ("R6", "100k", "H18", "L18"),
]


def coord(p, mirrored=False):
    col=ord(p[0])-ord("A"); row=int(p[1:])-1
    return (85 + (23-col if mirrored else col)*32, 235 + row*32)


def layout(bottom=False):
    n=4 if bottom else 3
    d=Drawing(f"{n}. {'Solder side - mirrored wire connections' if bottom else 'Component side - placement on perfboard'}", "Use isolated copper pads, 2.54 mm pitch, at least 24 columns x 20 rows. Do NOT use connected stripboard.", n)
    d.rect(57,197,794,692,"#f1e5c9","#ad9569",2)
    for ci in range(24):
        letter=chr(65+(23-ci if bottom else ci))
        d.text(85+ci*32,219,letter,16,anchor="middle")
    for ri in range(20):
        d.text(43,241+ri*32,ri+1,15,anchor="end")
        for ci in range(24):
            x,y=85+ci*32,235+ri*32
            d.s.append(f'<circle cx="{x}" cy="{y}" r="5" fill="white" stroke="#b19566" stroke-width="2"/>')
    # B6 or its mirrored position identifies the same physical corner on both views.
    x,y=coord("A1",bottom)
    d.dot(x,y,"#d03434",8)
    if not bottom:
        for ref,value,a,b in PARTS:
            x1,y1=coord(a); x2,y2=coord(b)
            if ref.startswith("D"):
                d.line([(x1,y1),(x2,y2)],INK,3)
                cx=(x1+x2)/2
                d.rect(cx-37,y1-10,74,20,"#e39458",INK,2)
                d.line([(cx+23,y1-11),(cx+23,y1+11)],INK,5)
                d.text(cx,y1-22,f"{ref} stripe ->",17,bold=True,anchor="middle")
            else:
                resistor(d,(x1,y1),(x2,y2),"" if ref in ["R2","R6"] else f"{ref} {value}")
                if ref in ["R2","R6"]:
                    d.text((x1+x2)/2,y1+43,f"{ref} {value}",20,bold=True,anchor="middle")
        for ch, row in [(1,6),(2,16)]:
            x,y=coord(f"K{row}")
            d.s.append(f'<path d="M {x-43},{y-21} A 43 39 0 0 1 {x+43},{y-21} L {x+43},{y-8} L {x-43},{y-8} Z" fill="#3a4650" stroke="black" stroke-width="2"/>')
            d.text(x,y-24,f"Q{ch}",19,"white",True,"middle")
            for c,label in [("J","E"),("K","B"),("L","C")]:
                px,py=coord(f"{c}{row}")
                d.dot(px,py,INK,5)
                d.text(px,py+24,label,18,bold=True,anchor="middle")
        ports=[("B2","5V"),("V2","3V3"),("B6","IN1"),("V6","OUT1"),("B16","IN2"),("V16","OUT2"),("V18","GND")]
        for p,net in ports:
            x,y=coord(p)
            d.dot(x,y,COL[net],8)
            d.text(x,y+29,net,16,COL[net],True,"middle")
        d.text(910,200,"Placement / lead endpoints",26,bold=True)
        lines=["D1: D2 -> H2 (stripe at H2)","R4 10k: J2 - N2", "R1 47k: D4 - H4", "Q1: E J6 / B K6 / C L6", "R3 10k: P4 - T4", "R2 100k: H8 - L8", "", "D2: D12 -> H12 (stripe at H12)", "R8 10k: J12 - N12", "R5 47k: D14 - H14", "Q2: E J16 / B K16 / C L16", "R7 10k: P14 - T14", "R6 100k: H18 - L18"]
        for i,t in enumerate(lines):d.text(910,244+i*35,t,22)
        d.text(910,757,"No pads are connected by default.",23,bold=True)
        d.text(910,792,"Add the wires on page 4 after soldering",21)
        d.text(910,822,"and trimming the component leads.",21)
        d.note(923,["Q1/Q2 must be 2N3904 with the specified E-B-C pin order. Match the supplier's datasheet.","Mark corner A1 in red. Turn the board left-to-right for the solder-side view; keep row 1 at the top.","Q1 flat edge faces row 7; Q2 flat edge faces row 17. Keep all bare component leads separate."])
    else:
        # All connections are insulated hookup wires, NOT exposed solder bridges.
        for net,pads in PADS.items():
            for a,b in zip(pads,pads[1:]):
                xa,ya=coord(a,True); xb,yb=coord(b,True)
                # Routes illustrate endpoints; crossings are insulated.
                d.line([(xa,ya),(xb,yb)],"white",8)
                d.line([(xa,ya),(xb,yb)],COL[net],4)
            for p in pads:
                x,y=coord(p,True);d.dot(x,y,COL[net],7)
        for ref,value,a,b in PARTS:
            for p in [a,b]:
                x,y=coord(p,True);d.text(x+7,y-9,p,13)
        for ch,row in [(1,6),(2,16)]:
            for c,label in [("J","E"),("K","B"),("L","C")]:
                x,y=coord(f"{c}{row}",True)
                d.text(x,y+26,label,18,bold=True,anchor="middle")
        d.text(910,200,"Solder together ONLY these groups",25,bold=True)
        for i,(net,pads) in enumerate(PADS.items()):
            d.text(910,244+i*43,net,22,COL[net],True)
            d.text(1010,244+i*43," - ".join(pads),20)
        d.text(910,775,"Different groups must never touch.",23,bold=True)
        d.text(910,811,"Wire crossings are NOT junctions.",22)
        d.text(910,847,"Use insulation all the way to each pad.",21)
        d.note(923,["Dots mark solder points. Each color/group forms one electrical net. Route insulated wires as convenient.","Strip only 2-3 mm at each wire end. Solder the wire to the existing pad/lead; do not bridge adjacent pads.","The numbers and letters identify the SAME holes as page 3, even though this view is mirrored."])
    return d.save("garage-reader-solder-bottom.svg" if bottom else "garage-reader-solder-top.svg")


def steps():
    d=Drawing("5. Parts, soldering order and first power-up", "You already have the reader and D1 mini. The interface parts and reader power supply are still needed.",5)
    d.text(50,175,"Additional parts",27,bold=True)
    items=[("2", "2N3904 NPN, TO-92; matching E-B-C pinout"),("2", "1N4148 axial diodes"),("4", "10k ohm resistors, 1/4 W, 1% or 5%"),("2", "47k ohm resistors, 1/4 W, 1% or 5%"),("2", "100k ohm resistors, 1/4 W, 1% or 5%"),("1", "Isolated-pad perfboard, >=24 x 20 holes (2.54 mm)"),("1", "Fixed regulated 12 V DC wall adapter"),("1", "Matching DC barrel-to-screw adapter, if needed"),("1", "5 V USB charger + USB-C cable for the D1 mini"),("-", "Insulated wire, solder, flux, heat-shrink, enclosure")]
    for i,(qty,item) in enumerate(items):
        d.text(55,217+i*35,qty,23,bold=True)
        d.text(95,217+i*35,item,21)
    d.text(55,610,"Reader current rating is unknown: choose a regulated",20)
    d.text(55,640,"12 V supply with at least 1 A available for this reader.",20)
    d.text(55,686,"Resistor identification (4-band, gold tolerance)",23,bold=True)
    for i,t in enumerate(["10k: brown - black - orange - gold", "47k: yellow - violet - orange - gold", "100k: brown - black - yellow - gold"]):d.text(55,723+i*32,t,21)
    d.text(55,846,"2N3904 FRONT VIEW",21,bold=True)
    d.text(55,877,"Flat face toward you; legs down.",19)
    d.text(55,905,"Supplier pin order must match.",19)
    d.rect(460,813,135,55,"#344454","#344454",8)
    d.text(528,848,"2N3904",20,"white",True,"middle")
    for x,label in [(480,"E"),(528,"B"),(576,"C")]:
        d.line([(x,868),(x,903)],INK,5)
        d.text(x,927,label,20,bold=True,anchor="middle")
    d.text(850,175,"Build with both supplies unplugged",27,bold=True)
    lines=["1. Solder the D1 mini headers, or use short wires", "   directly on the labelled pads shown on page 1.", "2. Insert resistors and diodes per page 3. Resistors", "   have no polarity; diode stripes must face H2/H12.", "3. Fit both 2N3904s. Spread leads gently to the holes;", "   keep E, B and C separate. Solder; trim the leads.", "4. Add INSULATED wires on the copper side using", "   the page 4 groups. No stripboard / common rows.", "5. Connect the seven interface wire pads below.", "6. Connect RED to adapter +12 V. Adapter negative,", "   reader BLACK/BROWN and board GND join together.", "7. Heat-shrink BLUE and YELLOW separately. Secure", "   the cable; mount the interface/controller indoors.", "8. Inspect both sides closely for shorts and loose", "   strands. Neither supply is connected yet.", "9. Flash garage-reader.yaml over USB. Then power", "   the reader with 12 V. Keep the common GND wire.", "10. Check Last Frame Bits = 34 and Last Card in HA.", "    Try a notification before enabling gate actions."]
    for i,t in enumerate(lines):d.text(850,215+i*29,t,20)
    d.text(850,809,"Interface pads -> external wires",23,bold=True)
    for i,t in enumerate(["B2 -> board VBUS; V2 -> board 3V3; V18 -> GND", "B6 -> GREEN; B16 -> WHITE", "V6 -> board 5 SCL; V16 -> board 4 SDA"]):d.text(850,847+i*31,t,21)
    d.note(935,["Without a meter, use fixed regulated supplies, not an adjustable buck converter. Visual inspection is limited.","This input circuit is intended for ordinary 0-12 V Wiegand logic; it is not a certified outdoor surge protector.","Sources: your reader label; WEMOS D1 mini documentation; onsemi 2N3903/2N3904; Vishay 1N4148 datasheets."])
    return d.save("garage-reader-soldering-steps.svg")


def check_netlist():
    seen={}
    for net,pads in PADS.items():
        for p in pads:
            assert p not in seen, (p,net,seen.get(p))
            seen[p]=net
    wanted={"D1":("5V","BIAS1"), "R4":("BIAS1","IN1"), "R1":("IN1","B1"), "R2":("B1","GND"), "R3":("OUT1","3V3"), "D2":("5V","BIAS2"), "R8":("BIAS2","IN2"), "R5":("IN2","B2"), "R6":("B2","GND"), "R7":("OUT2","3V3")}
    for ref,_,a,b in PARTS:assert (seen[a],seen[b])==wanted[ref],ref
    for ch,row in [(1,6),(2,16)]:
        assert (seen[f"J{row}"],seen[f"K{row}"],seen[f"L{row}"]) == ("GND",f"B{ch}",f"OUT{ch}")


if __name__=="__main__":
    check_netlist()
    files=[overview(),schematic(),layout(),layout(True),steps()]
    out=ROOT/"output"/"pdf"/"garage-reader-soldering-guide.pdf"
    out.parent.mkdir(parents=True,exist_ok=True)
    pagesize=landscape(A4)
    c=canvas.Canvas(str(out),pagesize=pagesize)
    c.setTitle("Garage reader - detailed wiring and soldering guide")
    c.setAuthor("Garage card reader project")
    for p in files:
        drawing=svg2rlg(str(p))
        dw,dh=drawing.width,drawing.height
        scale=min(pagesize[0]/dw,pagesize[1]/dh)
        drawing.scale(scale,scale)
        renderPDF.draw(drawing,c,(pagesize[0]-dw*scale)/2,(pagesize[1]-dh*scale)/2)
        c.showPage()
    c.save()
    print(f"Created {out} and {len(files)} SVG drawings. Perfboard netlist checked.")
