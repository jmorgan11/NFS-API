"""Get the data to the coast."""

import psycopg2


class CoastalData:
    """Collect data from the coastal Database"""

    def __init__(self, host="localhost", database="coastal", user="postgres", password="postgres"):
        """Constructor"""
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.connection = None

        self.__connect_to_database()

    def __connect_to_database(self):
        """Connect to the database"""
        self.connection = psycopg2.connect(host=self.host,
                                           database=self.database,
                                           user=self.user,
                                           password=self.password)

    def __within_distance(self, x_coord: float, y_coord: float, table="production.coast", distance=0.0, utm_zone=0):
        """Check if the point is within a certain distance of the coast"""

        utm_epsg = 32600 + utm_zone

        found = False

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                cursor.execute(f"""
                    SELECT 'true'
                    FROM {table}
                    WHERE
                    ST_DWithin(
                              geom_utm,
                              ST_Transform(
                                  ST_SetSRID(ST_MakePoint({x_coord}, {y_coord}), 4269), {utm_epsg}),
                              {distance}) = 'true'
                    """)

                row = cursor.fetchone()
                if row:
                    found = True
        return found

    # def get_coastal_info(self, x_coord: float, y_coord: float, table="production.coast_view"):
    #     """Get X/Y and distance to the coast based on Risk Rating 2.0 requirements"""
    #
    #     coast_dict = {"distance_to_coast_meters": "",
    #                   "distance_to_coast_feet": "",
    #                   "distance_to_coast_miles": ""}
    #
    #     with self.connection.cursor() as cursor:
    #         if x_coord and y_coord:
    #             # If the lat/lon is within the coastal buffer, get the values
    #             if self.__within_distance(x_coord=x_coord, y_coord=y_coord, table=table, utm_zone=):
    #                 cursor.execute(f"""
    #                     SELECT geom <-> (ST_SetSRID(
    #                                          ST_MakePoint({x_coord},
    #                                                       {y_coord}),4269))::geography AS distance
    #                     FROM {table}
    #                     ORDER BY distance
    #                     LIMIT 1
    #                 """)
    #
    #                 row = cursor.fetchone()
    #
    #                 if row:
    #                     coast_dict["distance_to_coast_meters"] = round(row[0], 2)
    #                     coast_dict["distance_to_coast_feet"] = round(row[0] * 3.28084, 2)
    #                     coast_dict["distance_to_coast_miles"] = round(row[0] * 0.0006213712, 2)
    #
    #     return coast_dict

    def get_coastal_info_utm(self, x_coord: float, y_coord: float,
                                 utm_zone=None, table="production.coast_view", distance=0.0):
        """Get X/Y and distance to the coast based on Risk Rating 2.0 requirements"""

        coast_dict = {"distance_to_coast_meters": "",
                      "distance_to_coast_feet": "",
                      "distance_to_coast_miles": ""}

        utm_epsg = 32600 + utm_zone

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                # If the lat/lon is within the coastal buffer, get the values
                if utm_zone in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 15, 16, 17, 18, 19, 20, 60):
                    if self.__within_distance(x_coord=x_coord,
                                              y_coord=y_coord,
                                              utm_zone=utm_zone,
                                              table=table,
                                              distance=distance):
                        cursor.execute(f"""
                            SELECT geom_utm <-> ST_Transform(
                                                    ST_SetSRID(
                                                        ST_MakePoint({x_coord}, {y_coord}), 4269), {utm_epsg}) AS distance
                            FROM {table}
                            ORDER BY distance
                            LIMIT 1
                        """)

                        row = cursor.fetchone()

                        coast_dict["distance_to_coast_meters"] = round(row[0], 2)
                        coast_dict["distance_to_coast_feet"] = round(row[0] * 3.28084, 2)
                        coast_dict["distance_to_coast_miles"] = round(row[0] * 0.0006213712, 3)

        return coast_dict


if __name__ == '__main__':
    import time

    x, y = (-77.811651, 39.506993)
    utm_zone = 18

    coastal = CoastalData()

    # Outside a distance to the coast
    start_time = time.perf_counter() 
    print("IN UTM:", coastal.get_coastal_info_utm(
        x_coord=x,
        y_coord=y,
        utm_zone=utm_zone,
        table='production.coast_utm_' + str(utm_zone) + '_view',
        distance=40233.6))
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time:.6f} seconds")

    # Within a distance to the coast
    x, y = (-75.14577990, 38.26550297)
    start_time = time.perf_counter()
    print("OUT UTM:", coastal.get_coastal_info_utm(
        x_coord=x,
        y_coord=y,
        utm_zone=utm_zone,
        table='production.coast_utm_' + str(utm_zone) + '_view',
        distance=40233.6))
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time:.6f} seconds")

