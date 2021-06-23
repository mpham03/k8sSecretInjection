- Feature Name: `Inject Secret To Kubernetes Pods`
- Start Date: 2021-06-21

# Summary
This feature is used to roll out new Secret to existing Kubernetes pods based on their labels.
It leverages Kubernetes infrastructure to manage the secrets and containers to securely add an existing secret
to a number of running pods through mounted volume.

# Usage
### Installation
Please clone the project, install Python 3 and other dependencies.
```shell
git clone 
cd KubernetesSecrets
pipenv install
```

### Inject secret to pods 
Run the following command with your `key=value` pair labels and the `secret-name`.
```shell
python -m k8Secrets.main_process --pod_labels "key=value" --secret_name "secret-name"
```
For other options, please use `python -m k8Secrets.main_process --help`.

### Local example
- **Prerequisites**:
Please [install](https://kubernetes.io/docs/tasks/tools/) `minikube` and `kubernetes`
to start up a local Kubernetes cluster. Then follow this 
[guide](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)
to create an example with a test secret with a pod.
- Attempt to inject `my-secret` to any pod with `name=maya` label.
```shell
python -m k8Secrets.main_process --pod_labels "name=maya" --secret_name "my-secret"
```
  
# Technical Explanation
### Implementation
The process will execute the following steps:
- Validate and extract secret in the Kubernetes cluster.
- Select running pods that matches the given labels.
- Update the pod's configuration with the new secret volume.
- Apply `dry run` mode with new secret configuration and throw Exception if any error occurs.
- Otherwise, restart the running pods one by one to attach the new secret volume.

Below are some outcome scenarios:
Scenario | Description | Outcome
-------- | ----------- | -------
Invalid labels | Label input has wrong format | Exception thrown
Secret not found | Failed to find the given secret name in the Kubernetes cluster | Exception thrown
No matching pods | Can't filter any pods with the given labels | Exit with no secret update
Failed to roll out new secret | No change to target pod | Exception thrown
Succeed to roll out new secret | Target pod has new secret volume mounted  | Exit 0

### Rationale 
This implementation follows one of the two Kubernetes [recommendations](https://kubernetes.io/docs/tasks/inject-data-application/distribute-credentials-secure/)
to inject secrets to any application.

Using `Volume` is preferred when the secret is long, like SSL certificates, and should be stored as files with specific
access control. Afternatively, secret can be injected via a single environment variable, but it could be harder to manage.

Rolling out secret in mounted volumes requires redeployment because mounted filesystem is unchangeable. The process
would also force the app to automatically read in the new secret, but it could interrupt the running service even
for a very short period of time. If the secret is expired while target pods can't be updated, this could result in
a disaster outage.

# Unresolved questions
- Debug how to specify the new mounted volume correctly and handle some common errors when doing that.
- Set up local environment to easily explore different scenarios and possible failures.
- Examine all secret types and how to inject them.
- Add support for real Kubernetes cluster config.
- Add more functional tests for inputs validation and pod configuration changes.
- How to reduce impact on running services

# Notes after discussion
Improvements:
- Mount a default volume to any pod so secret files can be updated without mutating the resource or restarting the service
- Add a logic to restart the app inside the pod when secret file is updated
- Update pod labels after execution to avoid re-processing
- Check K8s annotation's api to validate the resource changes instead of using `loop` to iterate through filtered containers/volumes. 