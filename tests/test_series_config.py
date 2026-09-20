from app.database.sync_series import load_series_config


def test_unemployment_level_series_is_configured_for_generic_pipeline():
    config = load_series_config()

    assert config["UNEMPLOY"] == {
        "name": "Unemployment Level",
        "short_name": "Unemployed Persons",
        "category": "labor",
        "frequency": "monthly",
        "unit": "thousands of persons",
        "transformations": ["level"],
        "revision_tracking": True,
    }
