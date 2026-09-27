from app.reference_data.features import FEATURE_CATALOG, FeatureKey


def test_all_feature_keys_present_in_catalog():
    assert set(FEATURE_CATALOG.keys()) == set(FeatureKey)


def test_every_catalog_entry_has_a_category():
    for entry in FEATURE_CATALOG.values():
        assert entry.feature_category
        assert entry.feature_name
