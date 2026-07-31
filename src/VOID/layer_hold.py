import os
from spatialrt import shapewrap


class LayerHold:
    meters_per_mile = 5280 * 1200 / 3937.0
    cache_geo_files_to_fr = {}  # tuple of geofiles is key, feature reader distributed is value

    def __init__(self, cache_folder=None):
        self.layers_geo_to_utm = {}
        self.layers = {}
        if not cache_folder:
            self.cache_folder = '/mnt/mapvol/cache_folder'
        else:
            self.cache_folder = cache_folder

    @staticmethod
    def check_files(geo_file, rb_file, rb_suffix):
        for filename, require_suffix in (geo_file, ".geo"), (rb_file, rb_suffix):
            if not os.path.exists(filename):
                print("{} does not exist".format(filename))
                raise ValueError
            if not filename.endswith(require_suffix):
                print("{} does not end in {}".format(filename, require_suffix))
                raise ValueError

    def load(self, key, geo_file, rb_file):
        geo_file = os.path.join(self.cache_folder, geo_file)
        rb_file = os.path.join(self.cache_folder, rb_file)
        self.check_files(geo_file, rb_file, ".rtu")
        self.layers[key] = shapewrap.ShapeIndexerGeoAsUTMFromFiles(geofile=geo_file, rbfile=rb_file)

    def load_native(self, key, geo_file, rb_file, record_counts=None, verify=True, folder=None):
        if folder is None:
            folder = self.cache_folder

        if isinstance(geo_file, str):
            geo_file = os.path.join(folder, geo_file)
            rb_file = os.path.join(folder, rb_file)
            self.layers[key] = shapewrap.ShapeIndexerFromFiles(rbfile=rb_file, geofile=geo_file)
        else:  # geofile is a list
            geo_files = geo_file
            cache_key = tuple(geo_files)

            if cache_key in self.cache_geo_files_to_fr:
                fr = self.cache_geo_files_to_fr[cache_key]
            else:
                fr = shapewrap.FeatureReaderDistributed(geo_files, reccounts=record_counts, verify=verify)
                self.cache_geo_files_to_fr[cache_key] = fr

            print(f"rb_file = {rb_file}")

            self.layers[key] = shapewrap.ShapeIndexerFromFiles(
                rbfile=rb_file, geofile=None, featurereader=fr, verify=verify)

    def load_geo_to_utm(self, key, geo_file, rb_file, record_counts=None, verify=True, folder=None):
        if folder is None:
            folder = self.cache_folder

        if isinstance(geo_file, str):
            geo_file = os.path.join(folder, geo_file)
            rb_file = os.path.join(folder, rb_file)
            self.layers_geo_to_utm[key] = shapewrap.ShapeIndexerGeoAsUTMFromFiles(rbfile=rb_file, geofile=geo_file)
        else:  # geofile is a list
            geo_files = geo_file
            cache_key = tuple(geo_files)

            if cache_key in self.cache_geo_files_to_fr:
                fr = self.cache_geo_files_to_fr[cache_key]
            else:
                fr = shapewrap.FeatureReaderDistributed(geo_files, reccounts=record_counts, verify=verify)
                self.cache_geo_files_to_fr[cache_key] = fr

            self.layers_geo_to_utm[key] = shapewrap.ShapeIndexerGeoAsUTMFromFiles(
                rbfile=rb_file, geofile=None, featurereader=fr, verify=verify)

    def nearest(self, layer_key, x, y, radius=None, fields=()):
        """
        Returns dictionary with 'distance', 'fieldvals' or an empty dictionary if nothing round radius is in meters
           Only for natively indexed features
        """
        if layer_key in self.layers:
            layer = self.layers[layer_key]
        else:
            layer = self.layers_geo_to_utm[layer_key]

        result = layer.find_closest_feature(x, y, radius=radius)

        if "distance" not in result:
            return {}
        else:
            d = {"distance": result["distance"]}

            if fields:
                zidx = result["zidx"]
                feature = layer.featurereader.GetFeatureByIdx(zidx)
                values = []

                for field in fields:
                    try:
                        value = feature.GetField(field)
                    except (ValueError, KeyError):
                        value = None

                    values.append(value)
                d["fieldvals"] = tuple(values)
            d.update(result)  # also add all the fields in result

            return d

    def nearest_field_values(self, layer_key, x, y, fields, radius_miles=None, notfound=None, return_feet_key=None):
        result = self.nearest(layer_key, x, y, radius=radius_miles * self.meters_per_mile, fields=fields)

        if "distance" not in result:
            return dict(zip(fields, [notfound] * len(fields)))
        else:
            d = dict(zip(fields, result["fieldvals"]))

            if return_feet_key:
                d[return_feet_key] = result["distance"] * 3937 / 1200
            return d

    def nearest_feet(self, layer_key, x, y, max_miles, not_found=None):
        result = self.nearest(layer_key, x, y)

        if "distance" in result:
            feet = result["distance"] * 3937 / 1200
            if feet > max_miles * 5280:
                return not_found
            else:
                return feet
        else:
            return not_found

    def inside(self, layer_key, x, y):
        result = self.nearest(layer_key, x, y, radius=0)

        if "distance" in result:
            return True
        else:
            return False

    def all_intersect_attributes(self, layer_key, x, y, attributes):
        layer = self.layers[layer_key]
        z_indexes = layer.find_zidxs_intersecting_point(x, y)
        results = []

        for z_index in z_indexes:
            feature = layer.featurereader.GetFeatureByIdx(z_index)
            d = {}
            for key in attributes:
                try:
                    value = feature.GetField(key)
                except (ValueError, KeyError):
                    value = None
                d[key] = value
            results.append(d)

        return results
