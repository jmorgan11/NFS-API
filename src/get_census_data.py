"""
Get data from the census database
"""
import psycopg2


class CensusData:
    """Collect data from the Census Database"""

    def __init__(self, host="localhost", database="census_data", user="postgres", password="postgres"):
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

    def get_census_block(self, x_coord: float, y_coord: float, table='production.census_blocks_view'):
        """Get the census block the point is within."""

        census_block_dict = {"census_block": "N/A"}

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                cursor.execute(f"""
                    SELECT geoid
                    FROM {table}
                    WHERE ST_WithIn(
                        ST_SetSRID(
                            ST_MakePoint({x_coord}, {y_coord}), 4269), {table}.geom)""")

                row = cursor.fetchone()

                while row is not None:
                    census_block_dict["census_block"] = row[0]
                    row = cursor.fetchone()

        return census_block_dict

    def get_census_block_utm(self, x_coord: float, y_coord: float, utm_zone=None, table='production.census_blocks'):
        """Get the census block the point is within."""

        census_block_dict = {"census_block": "N/A"}

        if utm_zone not in range(4, 20):
            return census_block_dict

        utm_epsg = 32600 + utm_zone

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                cursor.execute(f"""
                    SELECT geoid
                    FROM {table}
                    WHERE ST_WithIn(
                            ST_Transform(
                              ST_SetSRID(
                                ST_MakePoint({x_coord}, {y_coord}), 4269), {utm_epsg}), {table}.geom_utm)""")

                row = cursor.fetchone()
                if row:
                    census_block_dict["census_block"] = row[0]

        return census_block_dict

    def get_census_tract(self, x_coord: float, y_coord: float, table='production.census_tracts'):
        """Get the census tract the point is within."""

        census_tract_dict = {"census_tract": "N/A"}

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                cursor.execute(f"""
                    SELECT tract
                    FROM {table}
                    WHERE ST_WithIn(
                        ST_SetSRID(
                            ST_MakePoint({x_coord}, {y_coord}), 4269), {table}.geom)""")

                row = cursor.fetchone()

                while row is not None:
                    census_tract_dict["census_tract"] = row[0]
                    row = cursor.fetchone()

        return census_tract_dict

    def get_msa(self, x_coord: float, y_coord: float, table='production.msa'):
        """Get the MSA the point is within."""
        msa_dict = {"cbsafp": "", "name": "", "namelsad": ""}

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                cursor.execute(f"""
                    SELECT CBSAFP, NAME, NAMELSAD
                    FROM {table}
                    WHERE ST_WithIn(
                        ST_SetSRID(
                            ST_MakePoint({x_coord}, {y_coord}),4269), {table}.geom)
                """)

                row = cursor.fetchone()

                while row is not None:
                    msa_dict["cbsafp"] = row[0]
                    msa_dict["name"] = row[1]
                    msa_dict["namelsad"] = row[2]
                    row = cursor.fetchone()

        return msa_dict

    def get_state_name(self, x_coord: float, y_coord: float, table='production.tl_2022_us_state'):
        """Get the state name the point is within."""
        state_dict = {"us_state_name": "",
                      "us_state_abbreviation": ""}

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                cursor.execute(f"""
                    SELECT name, stusps
                    FROM {table}
                    WHERE ST_WithIn(
                        ST_SetSRID(
                            ST_MakePoint({x_coord}, {y_coord}),4269), {table}.geom)""")

                row = cursor.fetchone()
                while row is not None:
                    state_dict["us_state_name"] = row[0]
                    state_dict["us_state_abbreviation"] = row[1]
                    row = cursor.fetchone()

        return state_dict

    def get_county_name(self, x_coord: float, y_coord: float, table='production.us_counties'):
        """Get the county name the point is within."""
        county_dict = {"county": ""}

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                cursor.execute(f"""
                    SELECT name
                    FROM {table}
                    WHERE ST_WithIn(
                        ST_SetSRID(
                            ST_MakePoint({x_coord}, {y_coord}),4269), {table}.geom)""")

                row = cursor.fetchone()
                while row is not None:
                    county_dict["county"] = row[0]
                    row = cursor.fetchone()

        return county_dict

    def get_county_state_fips(self, x_coord: float, y_coord: float, table='production.us_counties'):
        """Get the County name, State name and FIPs code for the point."""
        county_dict = {"state_fips": "",
                       "county_fips": "",
                       "county_name": ""}

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                cursor.execute(f"""
                    SELECT statefp, countyfp, name
                    FROM {table}
                    WHERE ST_WithIn(
                        ST_SetSRID(
                            ST_MakePoint({x_coord}, {y_coord}),4269), {table}.geom)""")

                row = cursor.fetchone()
                while row is not None:
                    county_dict["state_fips"] = row[0]
                    county_dict["county_fips"] = row[1]
                    county_dict["county_name"] = row[2]
                    row = cursor.fetchone()

        return county_dict

    def get_zip_code(self, x_coord: float, y_coord: float, table='production.zip_codes'):
        """Get the zip code the point is within."""
        zip_code_dict = {"zip_code": ""}

        with self.connection.cursor() as cursor:
            if x_coord and y_coord:
                cursor.execute(f"""
                    SELECT zcta5ce20
                    FROM {table}
                    WHERE ST_WithIn(
                        ST_SetSRID(
                            ST_MakePoint({x_coord}, {y_coord}),4269), {table}.geom)""")

                row = cursor.fetchone()
                while row is not None:
                    zip_code_dict["zip_code"] = row[0]
                    row = cursor.fetchone()

        return zip_code_dict

if __name__ == '__main__':
    import time

    start_time = time.perf_counter()

    x, y = (-77.811651, 39.506993)

    census = CensusData()

    print("BLOCK:", census.get_census_block_utm(x_coord=x, y_coord=y, utm_zone=18, table='production.census_blocks_utm_18'))
    print("TRACT:", census.get_census_tract(x_coord=x, y_coord=y))
    print("MSA:", census.get_msa(x_coord=x, y_coord=y))
    print("STATE:", census.get_state_name(x_coord=x, y_coord=y))
    print("COUNTY:", census.get_county_name(x_coord=x, y_coord=y))
    print("ZIP CODE:", census.get_zip_code(x_coord=x, y_coord=y))

    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time:.6f} seconds")
