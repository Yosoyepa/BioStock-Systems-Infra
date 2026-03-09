"""
Punto de entrada (Orchestrator) de la infraestructura BioStock.

Instancia y vincula los 6 stacks modulares inyectando las dependencias
necesarias entre ellos. Cada stack se despliega en ``us-east-1`` dentro
de la Capa Gratuita de AWS.

La configuración específica de cada microservicio (variables de entorno,
secretos, rutas del ALB) se declara aquí, manteniendo los stacks
agnósticos y reutilizables (Principio Abierto/Cerrado).
"""

import aws_cdk as cdk
from aws_cdk import aws_ecs as ecs

from bio_stock_infra.stacks import (
    NetworkStack,
    DataStack,
    MessagingStack,
    ComputeStack,
    CdnStack,
    ServerlessStack,
)
from bio_stock_infra.models import MicroserviceProps

app = cdk.App()

_env = cdk.Environment(region="us-east-1")

# 1. Network (VPC, Security Groups) – fundación de todos los demás stacks
network = NetworkStack(app, "BioStock-Network", env=_env)

# 2. Data (RDS PostgreSQL, RDS SQL Server, DynamoDB) – depende de Network
data = DataStack(
    app,
    "BioStock-Data",
    vpc=network.vpc,
    db_sg=network.db_sg,
    env=_env,
)

# 3. Messaging (SNS, SQS) – independiente
messaging = MessagingStack(app, "BioStock-Messaging", env=_env)

# 4. Compute (ECR, ECS Cluster, ALB) – depende de Network
compute = ComputeStack(
    app,
    "BioStock-Compute",
    vpc=network.vpc,
    ecs_sg=network.ecs_sg,
    alb_sg=network.alb_sg,
    env=_env,
)

# ── Microservicios ECS (declaración explícita por servicio) ──────────

# 4a. User Service – requiere PostgreSQL
compute.add_microservice(
    "user",
    props=MicroserviceProps(
        path_patterns=["/user-service", "/user-service/*"],
        priority=1,
        memory_limit_mib=400,
        health_check_path="/user-service/actuator/health",
        environment={
            "SPRING_DATASOURCE_URL": (
                f"jdbc:postgresql://"
                f"{data.postgres_db.db_instance_endpoint_address}:5432/postgres"
            ),
        },
        secrets={
            "SPRING_DATASOURCE_USERNAME": ecs.Secret.from_secrets_manager(
                data.postgres_db.secret, "username"
            ),
            "SPRING_DATASOURCE_PASSWORD": ecs.Secret.from_secrets_manager(
                data.postgres_db.secret, "password"
            ),
        },
    )
)

# 4b. Product Service – requiere DynamoDB
compute.add_microservice(
    "product",
    props=MicroserviceProps(
        path_patterns=["/api/products", "/api/products/*"],
        priority=2,
        memory_limit_mib=400,
        health_check_path="/actuator/health",
        environment={
            "AWS_DYNAMODB_TABLENAME": data.dynamo_table.table_name,
        },
    )
)


# 5. CDN (S3, CloudFront) – independiente
cdn = CdnStack(app, "BioStock-Cdn", env=_env)

# 6. Serverless (AWS Lambda) - depende de Messaging
serverless = ServerlessStack(
    app,
    "BioStock-Serverless",
    queues=messaging.queues,
    env=_env,
)

app.synth()
