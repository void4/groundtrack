import os
import json
from argparse import ArgumentParser

import pandas as pd
import plotly.express as px

parser = ArgumentParser(prog="groundtrack.py", description="Plots lon,lat,alt groundtracks of (impacting) asteroids and all observatories with an MPC code")

parser.add_argument("--objname", default="2023 CX1", help="Name of the asteroid groundtrack to plot. Default is 2023 CX1")
parser.add_argument("--obscode", default="000", help="Observatory from which to calculate altitude and azimuth angles toward the asteroid. Default is Greenwich (000). You can search for them here: https://www.projectpluto.com/mpc_stat.htm or use the map generated with this tool.")
parser.add_argument("--imgpath", default="groundtrack.png", help="Path to save plot to")
parser.add_argument("--hide-mpc", action="store_true", default=False, help="Do not plot MPC observatory locations")
parser.add_argument("--no-html", action="store_true", default=False, help="Do not output html file")
parser.add_argument("--htmlpath", default="groundtrack.html", help="Path to store html map to")
parser.add_argument("--interactive", action="store_true", default=False, help="Open interactive map in browser")
parser.add_argument("--ephem-start", default="2023 Feb 13 02:00", help="Datetime of start of ephemeris calculation. Default: \"2023 Feb 13 02:00\"")
parser.add_argument("--ephem-size", default="1s", help="Size of ephemeris step. Default: \"1s\"")
parser.add_argument("--ephem-steps", default=60*60, help="Number of ephemeris calculation steps to make. Default: 3600")

args = parser.parse_args()

lons = []
lats = []
hover_names = []	
colors = []

if not args.hide_mpc:
	with open("mpc_stat.txt") as f:
		lines = [line.split(None, 7) for line in f.read().splitlines()][1:-1]
		
	for line in lines:
		#print(line)
		pl, code, lon, lat, alt, _, _, place = line
		lons.append(float(lon))
		lats.append(float(lat))
		colors.append("blue")
		region = ""
		place = place.strip()
		if "  " in place:
			region, place = place.split("  ", 1)
			region = region.strip()
			place = place.strip()
			
		region_name = f"Name: {place}"
			
		if region:
			region_name = region_name + f", {region}"
			
		hover_names.append(f"Code: {code} {region_name} @ Est. Altitude: {alt}m")

objname = args.objname
EPHEM_START = args.ephem_start
EPHEM_STEPS = args.ephem_steps
EPHEM_STEP_SIZE = args.ephem_size

#Custom coordinates apparently not supported by fo (yet?)
MPCOBSCODE = args.obscode

BINPATH = "/home/test/bin/"
OUTPATH = "/home/test/.find_orb/"

OBSTXTPATH = os.path.join(OUTPATH, "obs.txt")
ENVIRONPATH = os.path.join(OUTPATH, "environ.def")

GRABMPCPATH = os.path.join(BINPATH, 'grab_mpc')
GRABMPCCMD = f"{GRABMPCPATH} {OBSTXTPATH} {objname}"

"""
# fo flags
## -E
3 Alt/az output
8 Ground track (lat/lon/alt)

## only with -e generates combined.json i think
"""

FOPATH = "fo"#os.path.join(BINPATH, "fo")
FOCMD = f'{FOPATH} {OBSTXTPATH} -e astroeph.json -C {MPCOBSCODE} -E 3,8 -D {ENVIRONPATH} "EPHEM_START={EPHEM_START}" EPHEM_STEPS={EPHEM_STEPS} EPHEM_STEP_SIZE={EPHEM_STEP_SIZE}'

JSONPATH = os.path.join(OUTPATH, "combined.json")

try:
	os.remove(JSONPATH)
except FileNotFoundError:
	pass

print("Executing", GRABMPCCMD)
os.system(GRABMPCCMD)

print("Executing", FOCMD)
os.system(FOCMD)

if not os.path.exists(JSONPATH):
	print("`fo` output combined.json does not seem to exist. Did you give the right --outpath directory? ")
	exit(1)

with open(JSONPATH) as f:
    j = json.loads(f.read())

ephemerides = list(j["objects"][objname]["ephemeris"]["entries"].values())

for i, eph in enumerate(ephemerides):

    t = eph["ISO_time"]
    lon = eph["lon"]
    lat = eph["lat"]
    altkm = eph["alt(km)"]
    
    if altkm < -10:
    	break
    
    # ra, dec more accurate?
    lons.append(lon)
    lats.append(lat)
    
    hover_names.append(f"{t} {altkm}km (Az: {eph['az']}° Alt: {eph['alt']}° from {MPCOBSCODE})")
    
    colors.append("red")

df = pd.DataFrame({"Latitude":lats, "Longitude":lons, "hover_name": hover_names, "color": colors})

fig = px.scatter_mapbox(df, lat="Latitude", lon="Longitude", hover_name="hover_name", color="color", mapbox_style="carto-positron", zoom=0, title=f"Groundtrack of {objname}")
fig.write_image(args.imgpath)
if not args.no_html:
	fig.write_html(args.htmlpath, auto_open=args.interactive)
	if args.interactive:
		fig.show()

