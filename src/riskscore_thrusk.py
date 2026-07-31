#!python3
import sys
import urllib.request
import pickle
import xml.etree.ElementTree
from layer_hold import LayerHold
import redis

CACHE_FOLDER = r'/mnt/mapvol/cache_folder'
SERVICE_DATE = '20260601'


def query_sk_service(x, y):
    url = rf"http://127.0.0.1/spatialkey/query?x={x}&y={y}&key=L9bCAIzwt9&custid=" \
          rf"atkinsna-server&release={SERVICE_DATE}&priority=true&plustag=enhanced"
    page = urllib.request.urlopen(url, timeout=120)
    txt = page.read()
    root = xml.etree.ElementTree.fromstring(txt)
    d = {}
    for child in root:
        print(child.tag, child.text)
        d[child.tag] = child.text
    return d


class LyrHoldVM2Formula(LayerHold):
    def __init__(self, folder, topo_reader=None):
        super().__init__(cache_folder=folder)
        self.folder = folder
        self.topo_reader = topo_reader
        self.load("ocf_100", geo_file="_ocf_100_20160104.geo", rb_file="_ocf_100_20160104.rtu")
        self.load("ocf_profile", geo_file="_ocf_profile.geo", rb_file="_ocf_profile.rtu")
        self.load_native("hm2_acc_buffer_gcs_native",
                         geo_file="_hm2_acc_buffer_gcs.geo",
                         rb_file="_hm2_acc_buffer_gcs_native.rtn")
        self.load_native("hm2_reploss_native", geo_file="_hm2_replace_loss.geo", rb_file="_hm2_replace_l"
                                                                                         "oss_native.rtn")
        self.load("shoreline_ocean", geo_file="_sea_ocean.geo", rb_file="_sea_ocean.rtu")
        self.load_native("historic_flood", geo_file="_historic_flood.geo", rb_file="_historic_flood_native.rtn")


class ScoreVM2:
    MAX_RADIUS = 8000  # meters
    FEET_PERIMETER = 3937 / 1200.

    def __init__(self, layer_hold, lon, lat, final_flood_type=None,
                 calc_score=True, read_elevation=True, read_flood_zone=True):
        self.claim_count = 0
        self.claim_factor = 0
        self.claim_term = None
        self.cid = None
        self.distance = None
        self.elev_dist_term = None
        self.elev_diff = 0
        self.fema_policies = 0
        self.final_flood_type = final_flood_type
        self.flood_elev = 0
        self.flood_elev_datum = None
        self.flow_acc = 0
        self.flow_acc_term = None
        self.historic_term = None
        self.is_historic = 0
        self.is_levee = 0
        self.layer_hold = layer_hold
        self.lat = lat
        self.levee_term = None
        self.lon = lon
        self.ocean_distance = None
        self.ocf_distance = 0
        self.replace_loss_count = 0
        self.replace_loss_factor = 0
        self.replace_loss_term = None
        self.risk_score = None
        self.topo_elev_feet = 0
        self.total_payment = 0
        self.zone = None
        self.zone_type = None

        if self.final_flood_type is not None:
            assert self.final_flood_type in ("NFHL", "NON-NFHL", "ATKINS")

        self.skey_result = query_sk_service(x=lon, y=lat)  # queries updated service

        if read_flood_zone or calc_score:
            self.find_zone_dist_wse()

        if read_elevation or calc_score:
            self.read_elevation()

        if calc_score:
            self.check_historic()
            self.check_hm2_claims_pif()
            self.read_community_union_cid()
            self.read_replace_loss_count()
            self.calc_replace_loss_factor()
            self.read_acc_buffer()
            self.read_is_levee()
            self.calc_risk_score()

    def calc_risk_score(self):
        non_neg_elev_diff = max(0, self.elev_diff)

        self.elev_dist_term = (16 / (16 + non_neg_elev_diff ** 2)) * (1e+6 / (1e+6 + self.distance ** 2)) * 50
        self.flow_acc_term = (1e+6 + self.flow_acc ** 2) / 1e+6 * 0.5
        self.levee_term = 25 * self.is_levee
        self.historic_term = 12.5 * self.is_historic
        self.replace_loss_term = self.replace_loss_factor * 0.5
        self.claim_term = self.claim_factor / 16

        pre_risk_score = \
            self.elev_dist_term + self.flow_acc_term + self.levee_term + self.historic_term + self.replace_loss_term + \
            self.claim_term

        if self.topo_elev_feet is not None:
            self.risk_score = round(min(round(pre_risk_score), 100))
        else:
            self.risk_score = -9999

        if (self.risk_score is None or self.risk_score < 65) and self.zone is not None and (
                self.zone.startswith(("X500", "X;0.2"))):
            self.risk_score = 65

        if self.zone and ((self.zone.startswith(("A", "V")) and not self.zone.startswith("AREA")) or
                          self.zone.startswith("OPEN WATER")):
            self.risk_score = 100

        if self.distance == 0:
            self.risk_score = 100

    def check_historic(self):
        lyr = self.layer_hold.layers["historic_flood"]
        result = lyr.find_closest_feature(self.lon, self.lat, radius=0)

        if "zidx" in result:
            self.is_historic = 1
        else:
            self.is_historic = 0

    def read_is_levee(self):
        if self.skey_result["Levee_Protected_Area_Distance"] == "0":
            self.is_levee = 1
        else:
            self.is_levee = 0

    def read_acc_buffer(self):
        lyr = self.layer_hold.layers["hm2_acc_buffer_gcs_native"]
        zidxs = lyr.find_all_point_intersections(self.lon, self.lat)
        if not len(zidxs):
            self.flow_acc = 0
        else:
            self.flow_acc = 0
            for zidx in zidxs:
                feature = lyr.featurereader.GetFeatureByIdx(zidx)
                self.flow_acc = max(feature.GetField("cells"), self.flow_acc)

    def read_elevation(self):
        try:
            self.topo_elev_feet = float(self.skey_result["Property_Elev_From_NED"])
        except (ValueError, TypeError):
            self.topo_elev_feet = 0

        if self.flood_elev is not None:
            self.elev_diff = self.topo_elev_feet - self.flood_elev
        else:
            self.elev_diff = 0

    def check_hm2_claims_pif(self):
        try:
            self.claim_count = int(self.skey_result["Community_Claims"])
        except (ValueError, TypeError):
            self.claim_count = 0

        try:
            self.total_payment = int(self.skey_result["Community_Payouts"])
        except (ValueError, TypeError):
            self.total_payment = 0

        try:
            self.fema_policies = int(self.skey_result["Community_Policies"])
        except (ValueError, TypeError):
            self.fema_policies = 0

        self.claim_factor = min(10 * ((20 + self.claim_count ** 2) / 18 ** 2), 100)

    def read_community_union_cid(self):
        self.cid = self.skey_result["Community_Identification_Number"]

        if self.cid is None:
            self.cid = ""

    def read_replace_loss_count(self):
        lyr = self.layer_hold.layers["hm2_reploss_native"]
        result = lyr.find_closest_feature(self.lon, self.lat, radius=0)

        if "zidx" not in result:
            self.replace_loss_count = 0
        else:
            zidx = result["zidx"]
            feature = lyr.featurereader.GetFeatureByIdx(zidx)
            self.replace_loss_count = feature.GetField("sum_hlloss")

    def calc_replace_loss_factor(self):
        if self.replace_loss_count < 2:
            self.replace_loss_factor = 0
        elif self.replace_loss_count == 2:
            self.replace_loss_factor = 40
        else:
            assert self.replace_loss_count > 2
            self.replace_loss_factor = 60

    @staticmethod
    def _sort_results(results, key, source_key):
        high_number = 1e30

        def sorter(result):
            value = result[key]
            if result[source_key] and result[source_key].startswith("NFHL"):
                tiebreaker = 1
            elif result[source_key] and result[source_key].startswith("NON-NFHL"):
                tiebreaker = 2
            elif result[source_key] and result[source_key].startswith("OCF"):
                tiebreaker = 3
            elif result[source_key] is None:
                tiebreaker = 4
            else:
                raise ValueError

            if value is None:
                return high_number, tiebreaker
            else:
                return value, tiebreaker

        results.sort(key=sorter)

    def _find_zdw_null_override(self):
        if self.final_flood_type is not None:
            return

        if self.zone is None and self.flood_elev is None and self.distance is None:
            self.check_shoreline()

            if self.ocean_distance is not None:
                self.distance = self.ocean_distance
                self.distance_source = "Shoreline"
                self.flood_elev = 6
                self.flood_elev_source = "Shoreline"
                self.flood_elev_datum = "NAVD88"

    def find_zone_dist_wse(self):
        try:
            self.zone = self.skey_result["FEMA_Flood_Zone"].replace(",", ";").rstrip(";")
        except AttributeError:
            self.zone = None

        zs = self.skey_result["Zone_Source"]

        if zs == "nfhl":
            self.zone_type = "FEMA (NFHL)"
            self.final_flood_type = "NFHL"
            self.flood_elev_datum = self.skey_result["FEMA_Flood_Elev_Datum"]
            if self.flood_elev_datum == "ERROR" or not self.flood_elev_datum:
                self.flood_elev_datum = None
        elif zs == "digitized":
            self.zone_type = "FEMA (non-NFHL)"
            self.final_flood_type = "NON-NFHL"
            self.flood_elev_datum = None
        else:
            self.zone_type = "Complete flood hazard data not available for this county, " \
                            "our best available flood hazard analysis is shown"
            self.final_flood_type = None
            self.flood_elev_datum = None

        try:
            self.distance = float(self.skey_result["FEMA_Flood_Distance_Feet"])
        except (ValueError, TypeError):
            self.distance = None

        if self.final_flood_type is not None:
            try:
                self.flood_elev = float(self.skey_result["FEMA_Flood_Elevation_Feet"])
            except (ValueError, TypeError):
                try:
                    self.flood_elev = float(self.skey_result["Flood_Elevation_Estimated_From_Topo"])
                except (ValueError, TypeError):
                    self.flood_elev = 0
        else:
            self.flood_elev = 0

        ocf_result = self.get_ocf_distance_and_elev()
        try:
            if self.distance is None or ocf_result["distance"] < self.distance:
                self.distance = ocf_result["distance"]
                self.flood_elev = ocf_result["floodelev"]
                self.flood_elev_datum = "NAVD88"
                print("Setting Flood Elev from OCF ={}".format(self.flood_elev))
                if self.distance == 0:
                    self.final_flood_type = "ATKINS"
                    self.zone = "Atkins 100-year"
                    self.zone_type = "Atkins"
            self._find_zdw_null_override()
        except TypeError:
            pass

        if self.distance is None or self.distance > 9999:
            self.distance = 9999
        if self.flood_elev is None:
            self.flood_elev = 0

    def check_shoreline(self):
        lyr = self.layer_hold.layers["shoreline_ocean"]
        result = lyr.find_closest_feature(self.lon, self.lat,
                                          radius=self.MAX_RADIUS)
        if "distance" in result:
            self.ocean_distance = result["distance"] * self.FEET_PERIMETER
        else:
            self.ocean_distance = None

    def get_ocf_distance_and_elev(self):
        layer_ocf_100 = self.layer_hold.layers["ocf_100"]
        result_ocf_100 = layer_ocf_100.find_closest_feature(self.lon, self.lat, radius=self.MAX_RADIUS)

        dict_return = {
            "floodelev": None,
            "floodelevsrc": '',
            "floodelevdist": None,
            "floodelevdatum": None,
            "zone": None,
            "distance": None,
            "distancesrc": ''
        }

        if "distance" in result_ocf_100:
            self.ocf_distance = result_ocf_100["distance"] * self.FEET_PERIMETER
            dict_return["distance"] = result_ocf_100["distance"] * self.FEET_PERIMETER
            dict_return["distancesrc"] = "OCF"
            dict_return["zone"] = "Atkins 100-year" if result_ocf_100["distance"] == 0 else None

        layer_ocf_profile = self.layer_hold.layers["ocf_profile"]
        result_ocf_profile = layer_ocf_profile.find_closest_feature(self.lon, self.lat, radius=self.MAX_RADIUS)

        if "zidx" in result_ocf_profile:
            ocf_flood_elev = \
                layer_ocf_profile.featurereader.GetFeatureByIdx(result_ocf_profile["zidx"]).GetField(
                    "pf7_elev") * self.FEET_PERIMETER
            dict_return["floodelev"] = ocf_flood_elev
            dict_return["floodelevsrc"] = "OCF"
            dict_return["floodelevdist"] = result_ocf_profile["distance"] * self.FEET_PERIMETER

        return dict_return

    def get_flood_text_v1(self):
        if self.zone_type is not None:
            zone_type = self.zone_type
        else:
            zone_type = "Complete flood hazard data not available for this county, " \
                       "our best available flood hazard analysis is shown"

        txt = "Flood_Zone_Type={zonetype}<br>".format(zonetype=zone_type)

        if self.zone is not None:
            zone = self.zone
        else:
            zone = "Outside of Atkins 100-yr Flood Zone"

        txt += "FEMA_Flood_Zone={}<br>".format(zone)
        txt += "FEMA_Flood_Elevation_ft={floodelev:.0f}<br>".format(floodelev=self.flood_elev)
        txt += "FEMA_Flood_Distance_ft={distance:.0f}<br>".format(distance=self.distance)
        if self.topo_elev_feet is None:
            txt += "Property_Elevation_ft={}<br>".format("N/A")
        else:
            txt += "Property_Elevation_ft={:.0f}<br>".format(self.topo_elev_feet)
        txt += "FEMA_Policies={fema_policies:.0f}<br>".format(fema_policies=self.fema_policies)
        txt += "FEMA_Claims={claimcount:.0f}<br>".format(claimcount=self.claim_count)
        txt += "FEMA_Total_Payments={tot_pmnt:.0f}<br>".format(tot_pmnt=self.total_payment)
        txt += "CID={}<br>".format(self.cid)
        txt += "<br>"
        txt += "EQN_Elevation_Difference_ft={:.0f}<br>".format(self.elev_diff)
        txt += "EQN_Distance_ft={:.0f}<br>".format(self.distance)
        txt += "EQN_Flow_Accumulation={flowacc:.0f}<br>".format(flowacc=self.flow_acc)
        txt += "EQN_Levee={}<br>".format(bool(self.is_levee))
        txt += "EQN_Historic={}<br>".format("True" if self.is_historic else "False")
        txt += "EQN_Repetitive_Loss_Count={:.0f}<br>".format(self.replace_loss_count)
        txt += "EQN_Claim_Count={:.0f}<br>".format(self.claim_count)
        txt += "Risk_Score={}<br>".format(self.risk_score)

        return txt


def send_result_response(rs, result_key, result):
    pickle_response = pickle.dumps(result, protocol=0)
    print("Riskscore service: responding with {}".format(result))
    rs.rpush(result_key, pickle_response)
    rs.expire(result_key, time=120)


def wait_for_query():
    rs = redis.Redis("localhost")
    topo_reader = None
    layers = LyrHoldVM2Formula(folder=CACHE_FOLDER, topo_reader=topo_reader)

    while True:
        print("Waiting for redis query riskscorequeries")
        keyjunk, spickle = rs.blpop("riskscorequeries", 0)
        d = pickle.loads(spickle)

        print("Riskscore service: Got query {}".format(d))
        id_number = d["riskscoreid"]
        result = {}
        try:
            response_types = d["responsetypes"]
        except KeyError:
            response_types = None
            result = {"Error": "Error, responsetypes not specified"}
        print("Response types are {}".format(response_types))
        assert len(response_types)
        for resp in response_types:
            assert resp in ("score", "floodelev", "topoelevfeet", "floodelevdatum", "floodzone",
                            "floodzonetype", "floodtextv1")
        result_key = "riskscoreresponse{}".format(id_number)
        calc_score = ("score" in response_types)
        final_flood_type = d["finalfloodtype"] if "finalfloodtype" in d else None

        if "score" in response_types or "topoelevfeet" in response_types:
            read_elevation = True
        else:
            read_elevation = False

        if "floodzone" in response_types or "floodzonetype" in response_types or "score" in response_types:
            read_flood_zone = True
        else:
            read_flood_zone = True

        print("Scoring!")
        if "floodtextv1" in response_types:
            calc_score = True
            read_elevation = True
            read_flood_zone = True

        sc = ScoreVM2(layers, lon=d["x"], lat=d["y"], calc_score=calc_score,
                      final_flood_type=final_flood_type, read_elevation=read_elevation,
                      read_flood_zone=read_flood_zone)

        if "score" in response_types:
            result["score"] = sc.risk_score

        if "floodelev" in response_types:
            try:
                result["floodelev"] = sc.flood_elev
            except KeyError:
                result["floodelev"] = None

        if "topoelevfeet" in response_types:
            result["topoelevfeet"] = sc.topo_elev_feet

        if "floodelevdatum" in response_types:
            result["floodelevdatum"] = sc.flood_elev_datum

        if "floodzone" in response_types:
            result["floodzone"] = sc.zone

        if "floodzonetype" in response_types:
            result["floodzonetype"] = sc.zone_type

        if "floodtextv1" in response_types:
            result["floodtextv1"] = sc.get_flood_text_v1()

        send_result_response(rs, result_key, result)


def random_test(iterations=100, extent='us'):
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


def main(x_coordinate, y_coordinate):
    topo_reader = None

    layers = LyrHoldVM2Formula(folder=CACHE_FOLDER, topo_reader=topo_reader)

    score = ScoreVM2(layers, lon=x_coordinate, lat=y_coordinate, calc_score=True,
                     final_flood_type="ATKINS", read_elevation=True, read_flood_zone=True)

    print(score.get_flood_text_v1().replace("<br>", "\n"))


if __name__ == "__main__":
    if len(sys.argv) == 1:  # The default used for the web service.
        wait_for_query()
    elif len(sys.argv) > 1:
        if sys.argv[1] == "test":
            x_value = -90.113435
            y_value = 30.026541
            main(x_value, y_value)
        elif sys.argv[1] == "random":
            random_test()
        else:
            print("Error.  Use 'python3 riskscore_thrusk.py test' for testing.")
            sys.exit(1)
