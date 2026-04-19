# MAESTRO Compatibility

This wrapper uses MAESTRO's JSONL `plot.plot_example_metrics` entrypoint. It is compatible with ACE telemetry JSONL files after staging symlinks into flat `traces/` and `metrics/` directories. The MAESTRO parquet paper-figure scripts require a consolidated MAESTRO dataset/parquet schema and are not run directly against ACE result folders by this wrapper.
