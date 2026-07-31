#!/usr/bin/python3
import os
import sys
import csv
import pickle
import datetime
# import redis
# import pytz
# import accuweather
# from accuweather import AccuError
# from spatialrt import shapewrap
# from VOID.layer_hold import LayerHold
# from distance_measurement import CoastDist
# from distance_measurement import FreshWaterDist

CACHE_FOLDER = r'/mnt/mapvol/cache_folder'
# REDIS_SERVER = redis.Redis("localhost")
SERVICE_VERSION = "20260601"
NATION_CSV_FILE = rf'D:\GIS\nfs\data\raw\nation_{SERVICE_VERSION}.csv'
SHAPES_ROOT = r"/mnt/mapvol/pointserv/versioncache"


# class NWSError(Exception):
#     pass


# class GeoError(Exception):
#     pass


class LayerHoldFloodWrap(LayerHold):
    def __init__(self, cache_folder, verify=True):
        super().__init__(cache_folder=cache_folder)
        self.cache_folder = cache_folder
        self._locate_files()
        self.layers_geo2utm = {}
        self.layers_native = {}
        self.verify = verify
        self.load_pol_ar()

    @staticmethod
    def read_shape_source_textfile(filename):
        filenames = []
        filename_lengths = []
        filename_rec_counts = []
        for line in open(filename):
            parts = line.strip().split()
            assert len(parts) == 3
            filenames.append(parts[0])
            filename_lengths.append(int(parts[1]))
            filename_rec_counts.append(int(parts[2]))
        return tuple(filenames), tuple(filename_lengths), tuple(filename_rec_counts)

    def _locate_files(self):
        self._pol_ar_folder = os.path.join(SHAPES_ROOT, "shp_polar")
        self._polar_src_txt_file = os.path.join(SHAPES_ROOT, "indexes", "sources_spolar_{}.txt".format(SERVICE_VERSION))
        self._pol_ar_index_geo = os.path.join(SHAPES_ROOT, "indexes", "_spolar_{}.rtn".format(SERVICE_VERSION))
        self._confirm_files_exist((self._pol_ar_folder, self._polar_src_txt_file, self._pol_ar_index_geo))

    @staticmethod
    def _confirm_files_exist(filenames):
        for filename in filenames:
            if not os.path.exists(filename):
                print("Error: {} does not exist".format(filename))
                raise ValueError

    def load_pol_ar(self):
        raw_shape_names, file_lengths, file_rec_counts = self.read_shape_source_textfile(self._polar_src_txt_file)
        shape_names = tuple(os.path.join(self._pol_ar_folder, s) for s in raw_shape_names)
        self.load_native("spolar", shape_names, self._pol_ar_index_geo,
                         record_counts=file_rec_counts, verify=self.verify)


# class Cobra:
#     def __init__(self):
#         geo_file = os.path.join(CACHE_FOLDER, "_cobra_native.geo")
#         rb_file = os.path.join(CACHE_FOLDER, "_cobra_native.rtn")
#         self.layer = shapewrap.ShapeIndexerFromFiles(geofile=geo_file, rbfile=rb_file)

#     def in_cobra(self, x, y):
#         result = self.layer.find_closest_feature(x, y, radius=0)
#         if len(result):
#             return True
#         else:
#             return False


# class Query:
#     fresh_water_dist = FreshWaterDist()
#     coast_dist = CoastDist()
#     cobra = Cobra()
#     eastern_time_zone = pytz.timezone('US/Eastern')

#     def __init__(self, layer, csv_dict, x, y, skip_nws):
#         self.flood_elev_datum_result = None
#         self.flood_elev_result = None
#         self.layer = layer
#         self.nation_csv_dict = csv_dict
#         self.property_elev_result = None
#         self.query_time = None
#         self.riskscore = None
#         self.score = None
#         self.skip_nws = skip_nws
#         self.x = x
#         self.y = y
#         self.cid = self.get_cid()  # The CID value for the current latitude and longitude.
#         self.participating = self.get_participating_status()  # The Participating Status based on the CID value.

#         if not self.skip_nws:
#             self.findalerts = FindAlerts(x=self.x, y=self.y)
#             self.nwsxml = self.findalerts.to_xml()
#         else:
#             self.nwsxml = ""

#         self.coast_result = self.coast_dist.query(x=self.x, y=self.y)
#         self.query_risk_score_through_redis()
#         self.fresh_water_result = self.fresh_water_dist.query(x=self.x, y=self.y)

#         if self.cobra.in_cobra(x=self.x, y=self.y):
#             self.cobra_result = "Yes"
#         else:
#             self.cobra_result = "No"

#         self.set_time_string()

#     def get_participating_status(self):
#         """Determine the <Participating Status> based on the CID value."""
#         participating_status = "Unknown"

#         # Check if the CID value is in the <nation.csv> file.  If so, get
#         # <Participating> value from the CSV file.
#         if self.cid in self.nation_csv_dict.keys():
#             participating_status = self.nation_csv_dict[self.cid]

#         return participating_status

#     def query_risk_score_through_redis(self):
#         redis_server = REDIS_SERVER
#         risk_score_id = redis_server.incr("riskscoreid", 1)

#         d = {
#             "x": self.x,
#             "y": self.y,
#             "riskscoreid": risk_score_id,
#             "responsetypes": ("score", "floodelev", "topoelevfeet", "floodelevdatum")
#         }

#         query_pickle = pickle.dumps(d, protocol=0)
#         redis_server.rpush("riskscorequeries", query_pickle)
#         result_key = "riskscoreresponse{}".format(risk_score_id)
#         key_junk, response_pickle = redis_server.blpop(result_key, 0)
#         response = pickle.loads(response_pickle)
#         self.score = response["score"]

#         if response["topoelevfeet"] is not None:
#             self.property_elev_result = "{:.2f}".format(response["topoelevfeet"])
#         else:
#             self.property_elev_result = "No elevation available from USGS"

#         if response["floodelev"] is not None:
#             self.flood_elev_result = "{:.2f}".format(response["floodelev"])
#         else:
#             self.flood_elev_result = "No flood elevation available"

#         if response["score"] is not None:
#             self.riskscore = response["score"]
#         else:
#             self.riskscore = "NA"

#         if response["floodelevdatum"] is None or not (len(response["floodelevdatum"])):
#             self.flood_elev_datum_result = "NA"
#         else:
#             self.flood_elev_datum_result = response["floodelevdatum"]

#     def set_time_string(self):
#         utc_dt = datetime.datetime.now(pytz.UTC)
#         eastern_dt = utc_dt.astimezone(self.eastern_time_zone)
#         time_zone_str = eastern_dt.strftime("%Z")
#         if time_zone_str == "EDT":
#             zone_string = "Eastern Daylight Time"
#         elif time_zone_str == "EST":
#             zone_string = "Eastern Standard Time"
#         else:
#             zone_string = time_zone_str
#         self.query_time = eastern_dt.strftime("%Y-%m-%d %H:%M:%S {}".format(zone_string))

#     def get_cid(self):
#         """Get the CID for the current latitude and longitude."""

#         # Get the attribute values for the current latitude and longitude
#         # values.  The return is a list of one element.  That element is a
#         # dictionary with <CID> being one of the keys.
#         cid = self.layer.all_intersect_attributes("spolar",
#                                                   x=self.x,
#                                                   y=self.y,
#                                                   attributes=("DFIRM_ID", "CID", "POL_NAME1"))

#         # Check if the CID value returned is empty.  An empty CID value means the
#         # latitude and longitude value did not intersect a polygon in political
#         # shapefiles.  The data in the political shapefiles is derived from the NFHL
#         # S_POL_AR feature classes.
#         if len(cid) > 0:
#             return cid[0]['CID']
#         else:
#             return "Unknown"

#     def to_xml(self):
#         txt = ""
#         txt += "<QueryPointWrapResult>\n"
#         txt += " <Point_Latitude>{}</Point_Latitude>\n".format(self.y)
#         txt += " <Point_Longitude>{}</Point_Longitude>\n".format(self.x)
#         txt += " <Query_Time>{}</Query_Time>\n".format(self.query_time)
#         txt += " <COBRA_Zone>{}</COBRA_Zone>\n".format(self.cobra_result)
#         txt += " <Fresh_Water_Distance_Miles>{}</Fresh_Water_Distance_Miles>\n".format(self.fresh_water_result)
#         txt += " <Coast_Distance_Miles>{}</Coast_Distance_Miles>\n".format(self.coast_result)
#         txt += " <Property_Elevation>{}</Property_Elevation>\n".format(self.property_elev_result)
#         txt += " <BFE_Elevation>{}</BFE_Elevation>\n".format(self.flood_elev_result)
#         txt += " <BFE_Elevation_Datum>{}</BFE_Elevation_Datum>\n".format(self.flood_elev_datum_result)
#         txt += " <Risk_Score>{}</Risk_Score>\n".format(int(self.riskscore))
#         txt += " <CID>{}</CID>\n".format(self.cid)
#         txt += " <Participating_Status>{}</Participating_Status>\n".format(self.participating.title())
#         txt += self.nwsxml
#         txt += "</QueryPointWrapResult>\n"

#         return txt


# class FindAlerts:
#     accu_proc = accuweather.AccuAlertGetter()

#     def __init__(self, x, y):
#         self.alerts = None
#         self.xml = None
#         self.ziplookuptxt = None
#         self.state = None
#         self.fip = None
#         self.county = None
#         self.nwsfeed = None
#         self.x = x
#         self.y = y
#         self.process()

#     def process(self):

#         fipsgetter = accuweather.FipsGetter()
#         try:
#             result = fipsgetter.get_fips6(x=self.x, y=self.y)
#         except GeoError:
#             self.xml = " <NWS_Alerts>\n"
#             self.xml += "  <County>NA: Point is not in geographic coordinates</County>\n"
#             self.xml += "  <Number_Of_Alerts>NA: No county to look for alerts</Number_Of_Alerts>\n"
#             self.xml += " </NWS_Alerts>\n"
#             return

#         if result is None:
#             self.xml = " <NWS_Alerts>\n"
#             self.xml += "  <County>NA: Point is not inside a county</County>\n"
#             self.xml += "  <Number_Of_Alerts>NA: No county to look for alerts</Number_Of_Alerts>\n"
#             self.xml += " </NWS_Alerts>\n"
#         else:
#             self.fip, self.county, self.state = result
#             ziplookup = self.accu_proc.getzip(self.x, self.y)
#             self.ziplookuptxt = "ZIP Code lookup is {}".format(ziplookup)
#             try:
#                 self.alerts = self.accu_proc.get_lat_lon_zip_alerts(x=self.x, y=self.y)
#             except (AccuError, ValueError):
#                 try:
#                     self.nwsfeed = accuweather.NwsFeed()
#                 except NWSError:
#                     self.xml = " <NWS_Alerts>\n"
#                     self.xml += "  <County>{county}, {state}</County>\n".format(county=self.county,
#                                                                                 state=self.state)
#                     self.xml += "  <Number_Of_Alerts>0</Number_Of_Alerts>\n"
#                     self.xml += " </NWS_Alerts>\n"
#                 else:
#                     self.alerts = self.nwsfeed.get_alerts_for_fip(self.fip)
#                     self._gen_xml()
#             else:
#                 self._gen_xml()

#     def _gen_xml(self):
#         self.xml = " <NWS_Alerts>\n"
#         self.xml += "  <County>{county}, {state} ({ziplookuptxt})</County>\n".format(county=self.county,
#                                                                                      state=self.state,
#                                                                                      ziplookuptxt=self.ziplookuptxt)
#         if not len(self.alerts):
#             self.xml += "  <Number_Of_Alerts>0</Number_Of_Alerts>\n"
#         else:
#             self.xml += "  <Number_Of_Alerts>{}</Number_Of_Alerts>\n".format(len(self.alerts))
#             for alert in self.alerts:
#                 self.xml += alert.to_xml(prespaces=2)
#         self.xml += " </NWS_Alerts>\n"
#         self.xml = self.xml.replace("&", " ")

#     def to_xml(self):
#         return self.xml


def create_cid_dict():
    """Create a dictionary of <CID> values and <Participating Community> values."""
    nation_csv_dict = {}  # Holds the final dictionary.

    # Open the CSV file and iterate through it.
    with open(NATION_CSV_FILE, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # The CID values are stored in a variety of ways in the CSV file.  This code removes
            # anything that isn't a digit from the CID value.  The result should be a six
            # digit CID such as <321234>.
            cid = ''.join(ch for ch in row["CID"] if ch.isdigit())
            nation_csv_dict[cid] = row["Participating Community"]

    return nation_csv_dict


def main(x_coordinate, y_coordinate):
    """Return an XML based on a single latitude and longitude.  Used for testing."""
    nation_csv_dict = create_cid_dict()

    # # Create a layer.
    # layer = LayerHoldFloodWrap(cache_folder=CACHE_FOLDER)

    # # Query the latitude and longitude.
    # query_response = Query(layer, nation_csv_dict, x=x_coordinate, y=y_coordinate, skip_nws=False)

    # # Print the final XML based on the query response.
    # print(query_response.to_xml())


def random_test(iterations=10000, extent='world'):
    """Perform a test on random X/Y coordinates."""
    import random
    from datetime import datetime
    random.seed(datetime.now())

    for i in range(iterations):
        x_coord = 0
        y_coord = 0

        # US Based
        if extent.lower() == 'us':
            x_coord = random.uniform(-101, -85)
            y_coord = random.uniform(33, 40)

        # # Entire World
        if extent.lower() == 'world':
            x_coord = random.uniform(-180, 180)
            y_coord = random.uniform(-85, 85)

        print(i + 1, ": test point=", x_coord, y_coord)
        main(x_coord, y_coord)


# def wait_for_query():
#     while True:
#         # Create a layer.
#         lyr = LayerHoldFloodWrap(cache_folder=CACHE_FOLDER)

#         # Create the dictionary from the <nation.csv> file.
#         nation_csv_dict = create_cid_dict()

#         keyjunk, spickle = REDIS_SERVER.blpop("floodwrapqueries", 0)
#         d = pickle.loads(spickle)
#         idnumber = d["floodwrapid"]

#         if "skipnws" in d:
#             skipnws = d["skipnws"]
#         else:
#             skipnws = False

#         resultkey = "floodwrapresponse{}".format(idnumber)
#         qry = Query(lyr, nation_csv_dict, x=d["x"], y=d["y"], skip_nws=skipnws)
#         xmlresponse = qry.to_xml()
#         del qry
#         pickleresponse = pickle.dumps(xmlresponse, protocol=0)
#         print("Floodwrap service: responding {}".format(xmlresponse))
#         REDIS_SERVER.rpush(resultkey, pickleresponse)
#         REDIS_SERVER.expire(resultkey, time=120)


if __name__ == "__main__":
    main(x_coordinate=-79.71237, y_coordinate=32.89975)
