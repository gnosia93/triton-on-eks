### [테라폼 설치](https://developer.hashicorp.com/terraform/install) ###
mac 의 경우 아래의 명령어로 설치할 수 있다. 
```
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

### EKS 설치 ###
karpenter helm 차트가 aws ecr 에 있기 때문에 ecr 로 먼저 로그인 한 후 설치한다.
```
git clone https://github.com/gnosia93/eks-agentic-ai.git
cd eks-agentic-ai/iac/tf

aws ecr-public get-login-password --region us-east-1 | \
 helm registry login --username AWS --password-stdin public.ecr.aws

terraform init
terraform apply --auto-approve
```
> [!NOTE]
> 클러스터 삭제:
> 
> terraform destroy --auto-approve


### 클러스터 등록 ###

eai-vscode 웹 콘솔로 로그인하여 아래 명령어를 실행한다.
```
export CLUSTER_NAME=eks-agentic-ai
aws configure set region ap-northeast-2

aws eks update-kubeconfig --name ${CLUSTER_NAME}

# Karpenter 설치
#helm install karpenter oci://public.ecr.aws/karpenter/karpenter \
#  --namespace karpenter --create-namespace \
#  --set settings.clusterName=${var.cluster_name} \
#  --set settings.clusterEndpoint=$(aws eks describe-cluster --name ${var.cluster_name} --query "cluster.endpoint" --output text) \
#  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=${karpenter_role_arn}
```

### 카펜터 설치 확인 ###
본 워크샵에서는 테라폼 apply 시 eks 클러스터와 함께 카펜터가 자동으로 설치된다. 하지만 노드풀 및 ec2노드 클래스는 별도로 생성해야 한다. 
```
kubectl get pods -n kube-system -l app.kubernetes.io/name=karpenter
kubectl get crd | grep karpenter

kubectl get nodepools
kubectl get ec2nodeclasses

kubectl logs -n kube-system -l app.kubernetes.io/name=karpenter --tail=50
```
test 파드 생성 테스트를 한다. 
```
kubectl run test --image=nginx --restart=Never --overrides='{"spec":{"nodeSelector":{"karpenter.sh/nodepool":"default"}}}'

kubectl delete pod test
```

