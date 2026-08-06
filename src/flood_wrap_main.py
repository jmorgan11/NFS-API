"""
filename: flood_wrap_main.py
purpose: Get and return the required fields for the flood wrap API.
author: Jesse Morgan
contact: jmorgan1371@gmail.com
created: 8/6/2026

Return:
    <QueryPointWrapResult>
    <Point_Latitude>32.922617</Point_Latitude>
    <Point_Longitude>-117.07</Point_Longitude>
    <Query_Time>2026-08-06 18:52:17 Eastern Daylight Time</Query_Time>
    <COBRA_Zone>No</COBRA_Zone>
    <Fresh_Water_Distance_Miles>0.911</Fresh_Water_Distance_Miles>
    <Coast_Distance_Miles>10.329</Coast_Distance_Miles>
    <Property_Elevation>954.96</Property_Elevation>
    <BFE_Elevation>748.40</BFE_Elevation>
    <BFE_Elevation_Datum>NAVD88</BFE_Elevation_Datum>
    <Risk_Score>7</Risk_Score>
    <CID>060295</CID>
    <Participating_Status>Yes</Participating_Status>
    <NWS_Alerts>
    <County>San Diego County, California (ZIP Code lookup is 92131)</County>
    <Number_Of_Alerts>0</Number_Of_Alerts>
    </NWS_Alerts>
    </QueryPointWrapResult>

"""

def main(longitude: float, latitude: float):
    """
    Main function.

    Args:
        longitude (float): The longitude of the point.
        latitude (float): The latitude of the point.
    """
    flood_wrap_dict = {
        "Point_Latitude": latitude,
        "Point_Longitude": longitude,
        "Query_Time": -9999,
        "COBRA_Zone": False,
        "Fresh_Water_Distance_Miles": -9999,
        "Coast_Distance_Miles": -9999,
        "Property_Elevation": -9999,
        "BFE_Elevation": -9999,
        "BFE_Elevation_Datum": None,
        "Risk_Score": -9999,
        "CID": -9999,
        "Participating_Status": None,
        "NWS_Alerts": None
    }

    return flood_wrap_dict

if __name__ == '__main__':
    from pprint import pprint

    x, y = (-77.811651, 39.506993)

    flood_wrap_return = main(longitude=x, latitude=y)

    pprint(flood_wrap_return)