---
title: "Lesson 8: Practice: Partition the trips_by_week asset"
module: "dagster_essentials"
lesson: "8"
---

# Practice: Partition the trips_by_week asset

To practice what you’ve learned, update `weekly_update_job` and `trips_by_week` to be partitioned weekly. Use your existing `weekly_partition` definition from the previous practice problem.

---

## Check your work

The asset you built should look similar to the code contained in the **View answer** toggle. Click to open it.

**In `assets/metrics.py`**:

```python
# assets/metrics.py
from ..partitions import weekly_partition

@asset(
    deps=["taxi_trips"],
    partitions_def=weekly_partition
)
def trips_by_week(context, database: DuckDBResource):
    """
        The number of trips per week, aggregated by week.
    """
    
    period_to_fetch = context.asset_partition_key_for_output()

    # get all trips for the week
    query = f"""
        select vendor_id, total_amount, trip_distance, passenger_count
        from trips
        where pickup_datetime >= '{period_to_fetch}'
            and pickup_datetime < '{period_to_fetch}'::date + interval '1 week'
    """

    with database.get_connection() as conn:
        data_for_month = conn.execute(query).fetch_df()
    
    aggregate = data_for_month.agg({
        "vendor_id": "count",
        "total_amount": "sum",
        "trip_distance": "sum",
        "passenger_count": "sum"
    }).rename({"vendor_id": "num_trips"}).to_frame().T # type: ignore

    # clean up the formatting of the dataframe
    aggregate["period"] = period_to_fetch
    aggregate['num_trips'] = aggregate['num_trips'].astype(int)
    aggregate['passenger_count'] = aggregate['passenger_count'].astype(int)
    aggregate['total_amount'] = aggregate['total_amount'].round(2).astype(float)
    aggregate['trip_distance'] = aggregate['trip_distance'].round(2).astype(float)
    aggregate = aggregate[["period", "num_trips", "total_amount", "trip_distance", "passenger_count"]]

    try:
        # If the file already exists, append to it, but replace the existing month's data
        existing = pd.read_csv(constants.TRIPS_BY_WEEK_FILE_PATH)
        existing = existing[existing["period"] != period_to_fetch]
        existing = pd.concat([existing, aggregate]).sort_values(by="period")
        existing.to_csv(constants.TRIPS_BY_WEEK_FILE_PATH, index=False)
    except FileNotFoundError:
        aggregate.to_csv(constants.TRIPS_BY_WEEK_FILE_PATH, index=False)
```

**In `jobs/__init__.py`**:

```python
# jobs/__init__.py
from dagster import define_asset_job, AssetSelection
from ..partitions import weekly_partition

trips_by_week = AssetSelection.keys("trips_by_week")

weekly_update_job = define_asset_job(
  name="weekly_update_job",
  partitions_def=weekly_partition,
  selection=trips_by_week,
)
```

**If there are differences**, compare what you wrote to the asset above and change them, as this asset will be used as-is in future lessons.