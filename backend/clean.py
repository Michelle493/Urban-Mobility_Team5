import os
import pandas as pd

trips = pd.read_csv("data/yellow_tripdata.csv")
lookup = pd.read_csv("data/taxi_zone_lookup.csv", keep_default_na=False)

trips = trips[["VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime", "passenger_count", "trip_distance", "RatecodeID", "PULocationID", "DOLocationID", "payment_type", "fare_amount", "tip_amount", "tolls_amount", "total_amount"]]
trips.columns = ["vendor_id", "pickup_ts", "dropoff_ts", "passenger_count", "trip_distance", "rate_code_id", "pu_zone_id", "do_zone_id", "payment_type_id", "fare_amount", "tip_amount", "tolls_amount", "total_amount"]

excluded = []

def remove_rows(mask, reason):
    global trips
    bad = trips[mask].copy()
    bad["reason"] = reason
    excluded.append(bad)
    trips = trips[~mask].copy()
    print(reason + ":", len(bad))

remove_rows(trips[["pickup_ts", "dropoff_ts", "trip_distance", "pu_zone_id", "do_zone_id", "fare_amount"]].isnull().any(axis=1), "missing value")
remove_rows(trips.duplicated(), "duplicate row")

trips["pickup_ts"] = pd.to_datetime(trips["pickup_ts"])
trips["dropoff_ts"] = pd.to_datetime(trips["dropoff_ts"])
main_month = trips["pickup_ts"].dt.to_period("M").mode()[0]
remove_rows(trips["pickup_ts"].dt.to_period("M") != main_month, "pickup outside the file month")

trips["duration_min"] = (trips["dropoff_ts"] - trips["pickup_ts"]).dt.total_seconds()/60
remove_rows((trips["duration_min"]<1) | (trips["duration_min"]>180), "duration under 1 or over 180 min")
remove_rows((trips["trip_distance"] <=0) | (trips["trip_distance"] > 100), "distance 0 or over 100 miles")
remove_rows((trips["fare_amount"] <= 0) | (trips["fare_amount"] > 500), "fare 0 or negative or over 500")            

trips["avg_speed_mph"] = trips["trip_distance"] / (trips["duration_min"] / 60) 
remove_rows(trips["avg_speed_mph"] > 80, "average speed over 80 mph")

remove_rows(~trips["pu_zone_id"].isin(lookup["LocationID"]) | ~trips["do_zone_id"].isin(lookup["LocationID"]), "zone id not in lookup")


trips["passenger_count"] = trips["passenger_count"].fillna(1)
trips.loc[trips["passenger_count"] == 0, "passenger_count"] =1
trips["passenger_count"] = trips["passenger_count"].astype(int)

trips.loc[~trips["rate_code_id"].isin([1, 2, 3, 4, 5, 6]), "rate_code_id"] = 99
trips["rate_code_id"] = trips["rate_code_id"].astype(int)
trips.loc[~trips["payment_type_id"].isin([0, 1, 2, 3, 4, 5, 6]), "payment_type_id"] = 5
trips["payment_type_id"] = trips["payment_type_id"].astype(int)
trips["vendor_id"] = trips["vendor_id"].fillna(0).astype(int)

trips["fare_per_mile"] = (trips["fare_amount"] /
trips["trip_distance"]).round(2)
trips["pickup_hour"] = trips["pickup_ts"].dt.hour

trips["pickup_ts"] = trips["pickup_ts"].dt.strftime("%Y-%m-%d %H:%M:%S")
trips["dropoff_ts"] = trips["dropoff_ts"].dt.strftime("%Y-%m-%d %H:%M:%S")
trips["duration_min"] = trips["duration_min"].round(2)
trips["avg_speed_mph"] = trips["avg_speed_mph"].round(2)

os.makedirs("logs", exist_ok=True)
trips.to_parquet("data/clean_trips.parquet", index=False)
pd.concat(excluded).to_csv("logs/excluded_records.csv", index=False)
print("rows kept:", len(trips))