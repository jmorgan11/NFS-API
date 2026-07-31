import os
from spatialrt import shapewrap

CACHE_FOLDER = r'/mnt/mapvol/cache_folder'


class GenericDist:
    def __init__(self):
        self.feature_desc_for_msg = None
        self.miles_format_string = None
        self.layers = None
        self.x = None
        self.y = None
        self._response = None

    def query(self, x, y):
        self.x = x
        self.y = y
        if (not -180 < x < 180) or (not -90 < y < 90):
            self._response = "NA: Point is not geographic coordinates"
        else:
            self.calc_response()
        return self._response

    def calc_response(self):
        meters_per_mile = 5280.0 * (1200 / 3937)
        max_radius = meters_per_mile * 25  # 25 miles in meters

        min_dist_meters = None
        for layer in self.layers:
            radius = max_radius if min_dist_meters is None else min_dist_meters
            result = layer.find_closest_feature(self.x, self.y, radius=radius)
            if "distance" in result:
                meter_dist = result["distance"]
                min_dist_meters = meter_dist
                miles = meter_dist / meters_per_mile
                self._response = self.miles_format_string.format(miles)
                if min_dist_meters == 0:
                    break  # no need to keep looking in other layers
            elif min_dist_meters is None:  # no better point has been found
                self._response = "No {} within 25 miles".format(self.feature_desc_for_msg)


class CoastDist(GenericDist):
    def __init__(self):
        super().__init__()
        geo_file = os.path.join(CACHE_FOLDER, "_sea_ocean.geo")
        rb_file = os.path.join(CACHE_FOLDER, "_sea_ocean.rtu")
        self.layers = [shapewrap.ShapeIndexerGeoAsUTMFromFiles(geofile=geo_file, rbfile=rb_file)]
        self.feature_desc_for_msg = "coastline"
        self.miles_format_string = "{:.3f}"


class FreshWaterDist(GenericDist):
    def __init__(self):
        super().__init__()
        geo_file_1 = os.path.join(CACHE_FOLDER, "_nhd_area.geo")
        rb_file_1 = os.path.join(CACHE_FOLDER, "_nhd_area.rtu")
        geo_file_2 = os.path.join(CACHE_FOLDER, "_nhd_water_body.geo")
        rb_file_2 = os.path.join(CACHE_FOLDER, "_nhd_water_body.rtu")

        self.layers = [shapewrap.ShapeIndexerGeoAsUTMFromFiles(geofile=geo_file_1, rbfile=rb_file_1),
                       shapewrap.ShapeIndexerGeoAsUTMFromFiles(geofile=geo_file_2, rbfile=rb_file_2)]
        self.feature_desc_for_msg = "fresh water"
        self.miles_format_string = "{:.3f}"
