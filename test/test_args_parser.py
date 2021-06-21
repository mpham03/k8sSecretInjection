from k8Secrets.args_parser import _validate_labels
import pytest


def test_valid_labels():
    valid_labels = "key1=value1,key2=value2"
    kv_pairs = _validate_labels(valid_labels)
    assert valid_labels == kv_pairs


def test_invalid_labels():
    valid_labels = "kv"
    with pytest.raises(Exception):
        _validate_labels(valid_labels)
