"""Get the UTM Zone the point is within."""

import psycopg2


class UtmData:
    """Get the UTM Zone the point is within"""

    def __init__(self, host="localhost", database="misc",
                 user="postgres", password="postgres"):
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

    def get_utm_zone(self, x_coord: float, y_coord: float, table='production.utm_zones_view'):
        """Get the UTM Zone value"""

        utm_dict = {"utm_zone": 0}

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                # Query the database table
                cursor.execute(f"""
                    SELECT zone
                    FROM {table}
                    WHERE ST_WithIn(
                        ST_SetSRID(
                            ST_MakePoint({x_coord}, {y_coord}),4269), {table}.geom)""")

                row = cursor.fetchone()

                while row is not None:
                    utm_dict["utm_zone"] = row[0]
                    row = cursor.fetchone()

        return utm_dict


if __name__ == '__main__':
    import time

    x, y = (-77.811651, 39.506993)

    start_time = time.perf_counter()
    utm_data = UtmData()
    print("UTM Zone:", utm_data.get_utm_zone(x_coord=x, y_coord=y))
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time:.6f} seconds")        
