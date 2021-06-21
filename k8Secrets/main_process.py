import logging

from kubernetes import config
from kubernetes.client import Configuration, CoreV1Api, V1PodList, V1Secret
from kubernetes.client.api import core_v1_api
from kubernetes.client.rest import ApiException

from k8Secrets.args_parser import get_args, _validate_labels
from k8Secrets.load_secrets import load_secret_to_pods

logger = logging.getLogger(__name__)

def create_api_client(config_file: str) -> CoreV1Api:
    '''

    :param config_file:
    :return:
    '''
    if config_file:
        logger.info(f"Using Kubernetes config from {config_file}")
    config.load_kube_config(config_file=config_file)

    try:
        c = Configuration().get_default_copy()
    except AttributeError:
        logger.info(f"Using default Kubernetes config")
        c = Configuration()
        c.assert_hostname = False
    Configuration.set_default(c)
    return core_v1_api.CoreV1Api()

def get_pods(api_client: CoreV1Api, labels: str) -> V1PodList:
    filtered_pods = api_client.list_namespaced_pod(namespace='default', label_selector=labels)
    logger.info(f"Found {len(filtered_pods.items)} pods with matching labels {labels}")
    return filtered_pods

def validate_secret(api_client: CoreV1Api, secret_name: str) -> V1Secret:
    try:
        logger.debug(f"Checking if secret {secret_name} exists")
        secret = api_client.read_namespaced_secret(namespace="default", name=secret_name)
        return secret
    except ApiException as e:
        if e.status != 404:
            logger.error(e)
            exit(1)

def main():

    # load arguments
    args = get_args()
    secret_name = args.secret_name
    logging.basicConfig(level=args.log_level)

    # validate args and create api client
    lookup_labels = _validate_labels(args.pod_labels)
    api_client = create_api_client(config_file=args.config_file)
    secret_to_inject = validate_secret(api_client, secret_name)

    # main process
    filtered_pods = get_pods(api_client, lookup_labels)
    if len(filtered_pods.items) == 0:
        logger.info(f"No matching pods to update secret!")
        return None

    # attach new secret and restart the pods
    load_secret_to_pods(api_client, secret_to_inject, filtered_pods)


if __name__ == '__main__':
    main()
