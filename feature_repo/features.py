from datetime import timedelta

from feast import Entity, FeatureService, FeatureView, Field, FileSource
from feast.types import Float32, Int64

airport = Entity(name="airport", join_keys=["airport_id"])
airport_stats_source = FileSource(
    path="../data/features/history.parquet",
    timestamp_field="feature_time",
    created_timestamp_column="available_time",
)
airport_stats = FeatureView(
    name="airport_stats",
    entities=[airport],
    ttl=timedelta(hours=48),
    schema=[
        Field(name="trailing_delay_rate", dtype=Float32),
        Field(name="flights_last_24h", dtype=Int64),
    ],
    source=airport_stats_source,
    online=True,
    enable_validation=True,
    tags={"course_lab": "lr13", "owner": "team-feature-platform"},
)
flight_delay_service = FeatureService(
    name="flight_delay_v1",
    features=[airport_stats],
    tags={"model": "flight-delay-classifier"},
)
