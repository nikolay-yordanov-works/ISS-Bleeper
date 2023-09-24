from skyfield.api import load

# load the timescale, get the stations, get the ISS from the stations and create the satelite object
ts = load.timescale()
stations_url = 'http://celestrak.org/NORAD/elements/stations.txt'
satellites = load.tle_file(stations_url)
by_name = {sat.name: sat for sat in satellites}
satellite = by_name['ISS (ZARYA)']
print(satellite)

