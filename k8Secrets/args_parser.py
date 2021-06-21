import argparse
import logging

logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser()


def get_args():
    _set_args()
    args = parser.parse_args()
    logger.debug(f"Raw app arguments: {args}")
    _validate_labels(args.pod_labels)
    return args


def _set_args():
    parser.add_argument("--config_file", action="store", required=False, default=None,
                        help="Optional Kubernetes config file, default to local cluster.")
    parser.add_argument("--pod_labels", action="store", required=True,
                        help="Key value labels separated by comma, e.g: 'k1=v1,k2=v2'.")
    parser.add_argument("--secret_name", action="store", required=True, help="Secret name to inject.")
    parser.add_argument("--log_level", action="store", required=False, default=logging.INFO,
                        help="Optional logging level config")


def _validate_labels(labels: str) -> str:
    result = ""
    key_value_pairs = labels.split(",")
    for kv in key_value_pairs:
        if "=" not in kv:
            raise Exception(f"Invalid label format {kv}")
        result += f"{kv},"
    return result[:-1]
