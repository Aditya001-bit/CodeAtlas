from backend.risk.dataset.build_bugsinpy_dataset import COLUMNS
from backend.risk.dataset.codeatlas_features import FEATURES


def test_feature_schema():
    assert len(FEATURES) == 13
    assert COLUMNS[-1] == "label"
    assert COLUMNS[6:19] == FEATURES
