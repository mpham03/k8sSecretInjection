import copy
import time
import logging
from typing import List
from kubernetes.client import CoreV1Api, V1PodList, V1PodSpec, V1Volume, V1VolumeMount, V1SecretVolumeSource, V1Secret, \
    ApiException, V1Container, V1Pod

logger = logging.getLogger(__name__)


def load_secret_to_pods(api_client: CoreV1Api, new_secret: V1Secret, running_pods: V1PodList):
    for pod in running_pods.items:
        pod_name = pod.metadata.name

        logger.debug(f"Updating pod {pod_name} with new secret {new_secret}")
        updated_pod_dict = _update_new_secret_volume_spec(pod, new_secret)

        try:
            logger.info(f"Dry run to test attaching the new volume to pod {pod_name}")
            api_client.create_namespaced_pod(body=updated_pod_dict, namespace='default', dry_run="All")
        except ApiException as e:
            raise Exception(f"Failed to restart pod {pod_name}: {e}")

        try:
            logger.info(f"Terminating existing pod {pod_name}")
            api_client.delete_namespaced_pod(name=pod_name, namespace='default')
        except ApiException as e:
            raise Exception(f"Failed to stop existing pod {pod_name}: {e}")

        try:
            logger.info(f"Restarting pod {pod_name} with new secret volume")
            response = api_client.create_namespaced_pod(body=updated_pod_dict, namespace='default')

            # check api response status until new pod is created
            while True:
                response = api_client.read_namespaced_pod(name=pod_name, namespace='default')
                pod_status = response.status.phase
                logger.debug(f"Current pod status: {pod_name}={pod_status}")
                if pod_status != 'Pending':
                    break
                time.sleep(1)

            if pod_status == 'Failed':
                logger.error(
                    f"Failed to attach secret volume {new_secret.metadata.name}. Current pod status: {pod_name}={pod_status}.")
                logger.info(f"Restarting pod {pod_name} with old configuration")
                api_client.create_namespaced_pod(body=pod.to_dict(), namespace='default')
            else:
                logger.info(f"Successfully restarted pod {pod_name} with new secret volume {new_secret.metadata.name}")

        except ApiException as e:
            logger.error(f"Unexpected failure to restart pod {pod_name}: {e}")


def _update_new_secret_volume_spec(pod_config: V1Pod, new_secret: V1Secret) -> V1Pod:
    existing_pod = copy.deepcopy(pod_config)
    pod_name = existing_pod.metadata.name
    existing_pod_spec = existing_pod.spec
    existing_volumes = existing_pod_spec.volumes
    existing_containers = existing_pod_spec.containers
    new_secret_name = new_secret.metadata.name
    new_secret_volume_name = f"{new_secret_name}-volume"
    new_mount_path = f'/etc/secrets/{new_secret_name}'

    new_volume = V1Volume(
        name=new_secret_volume_name,
        secret=V1SecretVolumeSource(secret_name=new_secret_name)
    )
    _validate_new_volume(pod_name, new_volume, existing_volumes)
    logger.debug(f"Attaching new volume {new_volume}")
    existing_volumes.append(new_volume)

    new_volume_mount = V1VolumeMount(
        name=new_secret_volume_name,
        mount_path=new_mount_path,
        read_only=True
    )
    _validate_new_volume_mount(pod_name, new_volume_mount, existing_containers)
    logger.debug(f"Attaching new volume mount {new_volume_mount}")
    for running_container in existing_containers:
        running_container.volume_mounts.append(new_volume_mount)

    new_pod_dict = existing_pod.to_dict()
    logger.debug(f"Updated pod: {new_pod_dict}")
    return new_pod_dict


def _validate_new_volume(pod_name: str, new_volume: V1Volume, existing_volumes: List[V1Volume]):
    for existing_vol in existing_volumes:
        if existing_vol.__eq__(new_volume):
            logger.error(f"New volume: {new_volume}")
            raise Exception(f"Conflict volume {existing_vol.name} in pod {pod_name}")


def _validate_new_volume_mount(pod_name: str, new_volume_mount: V1VolumeMount, existing_containers: List[V1Container]):
    for existing_container in existing_containers:
        for existing_vol_mnt in existing_container.volume_mounts:
            if existing_vol_mnt.__eq__(new_volume_mount):
                logger.error(f"New volume mount: {new_volume_mount}")
                raise Exception(
                    f"Conflict volume mount {existing_vol_mnt.name} in pod {pod_name}, container {existing_container.name}")
