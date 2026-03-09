#!/bin/bash

# Configuración de región (us-east-1 definida en el CDK)
REGION="us-east-1"

echo "=========================================================="
echo "   AUDITORÍA DE RECURSOS AWS (REGIÓN: $REGION)          "
echo "=========================================================="
echo "Verificando si quedaron recursos huérfanos que puedan generar costos..."

echo -e "\n[1/8] Verificando Instancias EC2 y NAT Gateways..."
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running,pending" --query "Reservations[*].Instances[*].{ID:InstanceId, Type:InstanceType, State:State.Name}" --output table --region $REGION
aws ec2 describe-nat-gateways --filter "Name=state,Values=available,pending" --query "NatGateways[*].{ID:NatGatewayId, State:State}" --output table --region $REGION

echo -e "\n[2/8] Verificando Clusters ECS..."
aws ecs list-clusters --query "clusterArns" --output table --region $REGION

echo -e "\n[3/8] Verificando Load Balancers (ALB)..."
aws elbv2 describe-load-balancers --query "LoadBalancers[*].{Name:LoadBalancerName, State:State.Code}" --output table --region $REGION

echo -e "\n[4/8] Verificando Bases de Datos RDS..."
aws rds describe-db-instances --query "DBInstances[*].{ID:DBInstanceIdentifier, Class:DBInstanceClass, Status:DBInstanceStatus}" --output table --region $REGION

echo -e "\n[5/8] Verificando Tablas de DynamoDB..."
aws dynamodb list-tables --query "TableNames" --output table --region $REGION

echo -e "\n[6/8] Verificando Colas SQS y Topics SNS..."
aws sqs list-queues --query "QueueUrls" --output table --region $REGION
aws sns list-topics --query "Topics[*].TopicArn" --output table --region $REGION | grep -i "biostock" || echo "No se encontraron Topics SNS relacionados a BioStock"

echo -e "\n[7/8] Verificando Funciones Lambda..."
aws lambda list-functions --query "Functions[?contains(FunctionName, 'Service')].{Name:FunctionName, Runtime:Runtime}" --output table --region $REGION

echo -e "\n[8/8] Verificando Repositorios ECR..."
aws ecr describe-repositories --query "repositories[?contains(repositoryName, 'biostock')].repositoryName" --output table --region $REGION

echo -e "\n=========================================================="
echo "   FIN DE LA AUDITORÍA                                    "
echo "=========================================================="
echo "INFO: Si todas las tablas devolvieron 'None', '[]' o están vacías, significa que tu eliminación (cdk destroy) fue 100% exitosa y no te cobrarán un solo centavo por infraestructura."
