"""Return the closest lake or river name and distance"""
import psycopg2

DEGREES_TO_FEET = 364567  # Conversion factor from decimal degrees to feet


class NhdData:
    """Return the closest lake or river name and distance"""

    def __init__(self, host="localhost", database="national_hydrography_dataset", user="postgres", password="postgres"):
        """Constructor"""
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        self.dam_dict = {}
        self.x_coord = -9999
        self.y_coord = -9999
        self.__connect_to_database()

    def __connect_to_database(self):
        """Connect to the database"""
        self.connection = psycopg2.connect(host=self.host,
                                           database=self.database,
                                           user=self.user,
                                           password=self.password)

    @staticmethod
    def convert_river_class_to_char(in_class_as_num):
        """Convert the River Class (streamorde) from an integer to a character.
        0 <= dd_ft <1 A
        1 <= dd_ft <2 B
        2 <= dd_ft <3 C
        3 <= dd_ft <4 D
        4 <= dd_ft <5 E
        5 <= dd_ft <6 F
        6 <= dd_ft <7 G
        7 <= dd_ft <8 H
        8 <= dd_ft I
        """
        in_class_as_char = ""

        try:
            in_class_as_num = int(in_class_as_num)
            if in_class_as_num >= 8:
                in_class_as_char = 'I'
            elif in_class_as_num >= 7:
                in_class_as_char = 'H'
            elif in_class_as_num >= 6:
                in_class_as_char = 'G'
            elif in_class_as_num >= 5:
                in_class_as_char = 'F'
            elif in_class_as_num >= 4:
                in_class_as_char = 'E'
            elif in_class_as_num >= 3:
                in_class_as_char = 'C'
            elif in_class_as_num >= 1:
                in_class_as_char = 'B'
            elif in_class_as_num >= 0:
                in_class_as_char = 'A'

            return in_class_as_char
        except ValueError:
            in_class_as_char = ""
            

    def closest_flowline_utm(self, x_coord: float, y_coord: float, utm_zone=None, table="nhd_flowline"):
        """Find the closest flowline."""
        # Final dictionary template to return
        flowline_dict = {"Nearest_Flowline_Name": "",
                         "Distance_to_Flowline_meters": "",
                         "Distance_to_Flowline_feet": "",
                         "River_Class": "",
                         "Drainage_Area_Sq_km": ""}

        utm_epsg = 32600 + utm_zone

        # Check that the UTM Zone is appropriate
        acceptable_zones = list(range(1, 21))
        acceptable_zones.append(55)
        acceptable_zones.append(59)
        acceptable_zones.append(60)
        if utm_zone not in acceptable_zones:
            return flowline_dict

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                cursor.execute(f"""
                    SELECT gnis_name, 
                           streamorde, 
                           divdasqkm, 
                           geom_utm <-> ST_Transform(
                                            ST_SetSRID(
                                                ST_MakePoint({x_coord}, {y_coord}), 4269), {utm_epsg}) AS distance                                
                    FROM {table}
                    ORDER BY distance
                    LIMIT 1
                    """)

                row = cursor.fetchone()

                if row:
                    flowline_dict['Nearest_Flowline_Name'] = row[0]
                    flowline_dict["River_Class"] = self.convert_river_class_to_char(row[1])
                    flowline_dict["Drainage_Area_Sq_km"] = row[2]
                    flowline_dict["Distance_to_Flowline_meters"] = round(row[3], 2)
                    flowline_dict['Distance_to_Flowline_feet'] = round(row[3] * 3.28084, 2)

        return flowline_dict

    def closest_nhd_river_line_utm(self, x_coord: float, y_coord: float, utm_zone=None, table=None):
        """Find the data for the closest NHD rive line feature"""
        river_line_dict = {
            "nearest_river_line_name": "",
            "distance_to_river_line_meters": "",
            "distance_to_river_line_feet": "",
            "closest_river_line_coordinate_as_text": "",
            "closest_nhd_river_line_longitude": "",
            "closest_nhd_river_line_latitude": ""
        }

        utm_epsg = 32600 + utm_zone

        # Check that the UTM Zone is appropriate
        acceptable_zones = list(range(1, 21))
        acceptable_zones.append(55)
        acceptable_zones.append(59)
        acceptable_zones.append(60)
        if utm_zone not in acceptable_zones:
            return river_line_dict

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                # Query the closest feature
                cursor.execute(f"""
                    SELECT gnis_name, 
                           geom_utm <-> ST_Transform(
                                            ST_SetSRID(
                                                ST_MakePoint({x_coord}, {y_coord}), 4269), {utm_epsg}) AS distance,
                                ST_AsText(
                                    ST_Transform(            
                                        ST_ClosestPoint(geom_utm, 
                                                ST_Transform(
                                                    ST_SetSRID(
                                                        ST_MakePoint({x_coord}, 
                                                                     {y_coord}), 4269), {utm_epsg})
                                ), 4269))                            
                    FROM {table}
                    ORDER BY distance
                    LIMIT 1
                    """)

                row = cursor.fetchone()

                if row:
                    river_line_dict['nearest_river_line_name'] = row[0]
                    river_line_dict["distance_to_river_line_meters"] = round(row[1], 2)
                    river_line_dict["distance_to_river_line_feet"] = round(row[1] * 3.28084, 2)
                    river_line_dict["closest_river_line_coordinate_as_text"] = row[2]

                # Get the X and Y values
                cursor.execute(f"""
                    SELECT ST_X(ST_GeomFromText('{river_line_dict["closest_river_line_coordinate_as_text"]}')) AS X,
                           ST_Y(ST_GeomFromText('{river_line_dict["closest_river_line_coordinate_as_text"]}')) AS Y
                """)
                row = cursor.fetchone()
                if row:
                    river_line_dict["closest_nhd_river_line_longitude"] = row[0]
                    river_line_dict["closest_nhd_river_line_latitude"] = row[1]

        return river_line_dict

    def closest_nhd_river_area_utm(self, x_coord: float, y_coord: float, utm_zone=None, table=None):
        """Find the data for the closest NHD river area feature"""
        river_polygon_dict = {
            "nearest_river_area_name": "",
            "distance_to_river_area_meters": "",
            "distance_to_river_area_feet": "",
            "closest_river_area_coordinate_as_text": "",
            "closest_nhd_river_area_longitude": "",
            "closest_nhd_river_area_latitude": ""
        }

        utm_epsg = 32600 + utm_zone

        # Check that the UTM Zone is appropriate
        acceptable_zones = list(range(1, 21))
        acceptable_zones.append(55)
        acceptable_zones.append(59)
        acceptable_zones.append(60)
        if utm_zone not in acceptable_zones:
            return river_polygon_dict

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                # Query the closest feature
                cursor.execute(f"""
                    SELECT gnis_name, 
                           geom_utm <-> ST_Transform(
                                            ST_SetSRID(
                                                ST_MakePoint({x_coord}, {y_coord}), 4269), {utm_epsg}) AS distance,
                                ST_AsText(
                                    ST_Transform(            
                                        ST_ClosestPoint(geom_utm, 
                                                ST_Transform(
                                                    ST_SetSRID(
                                                        ST_MakePoint({x_coord}, 
                                                                     {y_coord}), 4269), {utm_epsg})
                                ), 4269))                            
                    FROM {table}
                    ORDER BY distance
                    LIMIT 1
                    """)

                row = cursor.fetchone()

                if row:
                    river_polygon_dict['nearest_river_area_name'] = row[0]
                    river_polygon_dict["distance_to_river_area_meters"] = round(row[1], 2)
                    river_polygon_dict["distance_to_river_area_feet"] = round(row[1] * 3.28084, 2)
                    river_polygon_dict["closest_river_area_coordinate_as_text"] = row[2]

                    # Get the X and Y values
                    cursor.execute(f"""
                        SELECT ST_X(ST_GeomFromText('{river_polygon_dict["closest_river_area_coordinate_as_text"]}')) AS X,
                               ST_Y(ST_GeomFromText('{river_polygon_dict["closest_river_area_coordinate_as_text"]}')) AS Y
                    """)
                    row = cursor.fetchone()
                    if row:
                        river_polygon_dict["closest_nhd_river_area_longitude"] = row[0]
                        river_polygon_dict["closest_nhd_river_area_latitude"] = row[1]

        return river_polygon_dict

    def closest_nhd_lake_utm(self, x_coord: float, y_coord: float, utm_zone=None, table=None):
        """Find the data for the closest NHD lake feature"""
        lake_dict = {
            "nearest_lake_name": "",
            "distance_to_lake_meters": "",
            "distance_to_lake_feet": "",
            "closest_lake_coordinate_as_text": "",
            "closest_nhd_lake_longitude": "",
            "closest_nhd_lake_latitude": ""
        }

        utm_epsg = 32600 + utm_zone

        # Check that the UTM Zone is appropriate
        acceptable_zones = list(range(1, 21))
        acceptable_zones.append(55)
        acceptable_zones.append(59)
        acceptable_zones.append(60)
        if utm_zone not in acceptable_zones:
            return lake_dict

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                # Query the closest feature
                cursor.execute(f"""
                    SELECT gnis_name, 
                           geom_utm <-> ST_Transform(
                                            ST_SetSRID(
                                                ST_MakePoint({x_coord}, {y_coord}), 4269), {utm_epsg}) AS distance,
                                ST_AsText(
                                    ST_Transform(            
                                        ST_ClosestPoint(geom_utm, 
                                                ST_Transform(
                                                    ST_SetSRID(
                                                        ST_MakePoint({x_coord}, 
                                                                     {y_coord}), 4269), {utm_epsg})
                                ), 4269))                            
                    FROM {table}
                    ORDER BY distance
                    LIMIT 1
                    """)

                row = cursor.fetchone()

                if row:
                    lake_dict['nearest_lake_name'] = row[0]
                    lake_dict["distance_to_lake_meters"] = round(row[1], 2)
                    lake_dict["distance_to_lake_feet"] = round(row[1] * 3.28084, 2)
                    lake_dict["closest_lake_coordinate_as_text"] = row[2]

                    # Get the X and Y values
                    cursor.execute(f"""
                        SELECT ST_X(ST_GeomFromText('{lake_dict["closest_lake_coordinate_as_text"]}')) AS X,
                               ST_Y(ST_GeomFromText('{lake_dict["closest_lake_coordinate_as_text"]}')) AS Y
                    """)
                    lake_row = cursor.fetchone()
                    if lake_row:
                        lake_dict["closest_nhd_lake_longitude"] = lake_row[0]
                        lake_dict["closest_nhd_lake_latitude"] = lake_row[1]

        return lake_dict


if __name__ == '__main__':
    import pprint
    import time

    x, y = (-77.811651, 39.506993)

    start_time = time.perf_counter()
    nhd_data = NhdData()
    print("RIVER LINE:")
    pprint.pprint(nhd_data.closest_nhd_river_line_utm(x_coord=x, y_coord=y, utm_zone=18, table="production.nhd_streamriver_utm_18"))
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time:.6f} seconds")      
    print("\n")

    start_time = time.perf_counter()
    nhd_data = NhdData()
    print("LAKE:")
    pprint.pprint(nhd_data.closest_nhd_lake_utm(x_coord=x, y_coord=y, utm_zone=18, table="production.nhd_lakes_utm_18"))
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time:.6f} seconds")      
    print("\n")

    start_time = time.perf_counter()
    nhd_data = NhdData()
    print("FLOWLINE:")
    pprint.pprint(nhd_data.closest_nhd_lake_utm(x_coord=x, y_coord=y, utm_zone=18, table="production.nhd_flowlines_utm_18"))
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time:.6f} seconds")      
    print("\n")

    start_time = time.perf_counter()
    nhd_data = NhdData()
    print("RIVER AREA:")
    pprint.pprint(nhd_data.closest_nhd_river_area_utm(x_coord=x, y_coord=y, utm_zone=18, table="production.nhd_area_utm_18"))
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time:.6f} seconds")      
