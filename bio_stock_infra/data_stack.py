"""
Stack de Capa de Datos para BioStock.

Gestiona los recursos de persistencia efímeros: RDS PostgreSQL,
RDS SQL Server Express y DynamoDB. Todos configurados con
RemovalPolicy.DESTROY para garantizar costo $0 tras la destrucción.
"""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_dynamodb as dynamodb,
)
from constructs import Construct


class DataStack(Stack):
    """
    Stack de persistencia para la infraestructura BioStock.

    Recibe la VPC y el Security Group de la capa de datos desde el
    NetworkStack (inyección de dependencias) y crea:
        - RDS PostgreSQL (db.t3.micro) – Free Tier.
        - RDS SQL Server Express (db.t3.micro) – Free Tier.
        - DynamoDB (Pay-Per-Request) – Free Tier perpetuo.

    Todas las instancias están configuradas para destrucción automática
    al ejecutar ``cdk destroy``.

    Args:
        vpc: La VPC donde se alojarán las bases de datos.
        db_sg: El Security Group que controla el acceso a las BDs.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc: ec2.IVpc,
        db_sg: ec2.ISecurityGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._postgres_db = self._create_postgres(vpc, db_sg)
        self._sqlserver_db = self._create_sqlserver(vpc, db_sg)
        self._dynamo_table = self._create_dynamodb()

    # ------------------------------------------------------------------
    # Properties (interfaz pública de solo lectura)
    # ------------------------------------------------------------------

    @property
    def postgres_db(self) -> rds.IDatabaseInstance:
        """Retorna la instancia RDS PostgreSQL."""
        return self._postgres_db

    @property
    def sqlserver_db(self) -> rds.IDatabaseInstance:
        """Retorna la instancia RDS SQL Server Express."""
        return self._sqlserver_db

    @property
    def dynamo_table(self) -> dynamodb.ITable:
        """Retorna la tabla DynamoDB de eventos."""
        return self._dynamo_table

    # ------------------------------------------------------------------
    # Métodos privados de construcción
    # ------------------------------------------------------------------

    def _create_postgres(
        self, vpc: ec2.IVpc, db_sg: ec2.ISecurityGroup
    ) -> rds.DatabaseInstance:
        """Crea una instancia RDS PostgreSQL db.t3.micro (Free Tier, efímera)."""
        return rds.DatabaseInstance(
            self,
            "PostgresDB",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_15,
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=[db_sg],
            allocated_storage=20,
            multi_az=False,
            removal_policy=RemovalPolicy.DESTROY,
            deletion_protection=False,
            backup_retention=Duration.days(0),
        )

    def _create_sqlserver(
        self, vpc: ec2.IVpc, db_sg: ec2.ISecurityGroup
    ) -> rds.DatabaseInstance:
        """Crea una instancia RDS SQL Server Express db.t3.micro (Free Tier, efímera)."""
        return rds.DatabaseInstance(
            self,
            "SqlServerDB",
            engine=rds.DatabaseInstanceEngine.sql_server_ex(
                version=rds.SqlServerEngineVersion.VER_16,
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3, ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=[db_sg],
            allocated_storage=20,
            multi_az=False,
            removal_policy=RemovalPolicy.DESTROY,
            deletion_protection=False,
            backup_retention=Duration.days(0),
        )

    def _create_dynamodb(self) -> dynamodb.Table:
        """Crea una tabla DynamoDB On-Demand (Pay-Per-Request, Free Tier perpetuo)."""
        return dynamodb.Table(
            self,
            "BioStockEventsTable",
            partition_key=dynamodb.Attribute(
                name="PK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )
