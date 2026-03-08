"""
Punto de entrada (Orchestrator) de la infraestructura BioStock.

Instancia y vincula los 5 stacks modulares inyectando las dependencias
necesarias entre ellos. Cada stack se despliega en ``us-east-1`` dentro
de la Capa Gratuita de AWS.
"""

import aws_cdk as cdk

from bio_stock_infra.network_stack import NetworkStack
from bio_stock_infra.data_stack import DataStack
from bio_stock_infra.messaging_stack import MessagingStack
from bio_stock_infra.compute_stack import ComputeStack
from bio_stock_infra.cdn_stack import CdnStack

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

# 4. Compute (ECR, ECS, ALB) – depende de Network
compute = ComputeStack(
    app,
    "BioStock-Compute",
    vpc=network.vpc,
    ecs_sg=network.ecs_sg,
    alb_sg=network.alb_sg,
    env=_env,
)

# 5. CDN (S3, CloudFront) – independiente
cdn = CdnStack(app, "BioStock-Cdn", env=_env)

app.synth()
