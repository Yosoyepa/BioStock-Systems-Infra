"""
Stack de Red y Seguridad para BioStock.

Define la VPC sin NAT Gateways (costo $0) y los Security Groups
que aíslan el tráfico entre las capas ALB, ECS y Bases de Datos.
"""

from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
)
from constructs import Construct


class NetworkStack(Stack):
    """
    Stack fundacional de red para la infraestructura BioStock.

    Crea una VPC con subredes públicas exclusivamente (sin NAT Gateways)
    y tres Security Groups que implementan aislamiento por capas:
        - ALB SG: Acepta tráfico HTTP desde internet.
        - ECS SG: Acepta tráfico únicamente desde el ALB SG.
        - DB SG:  Acepta tráfico únicamente desde el ECS SG.

    Attributes (exposed via @property):
        vpc: La VPC compartida por todos los stacks.
        alb_sg: Security Group del Application Load Balancer.
        ecs_sg: Security Group de la capa de cómputo ECS.
        db_sg:  Security Group de la capa de datos (RDS).
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._vpc = self._create_vpc()
        self._alb_sg, self._ecs_sg, self._db_sg = self._create_security_groups()

    # ------------------------------------------------------------------
    # Properties (interfaz pública de solo lectura)
    # ------------------------------------------------------------------

    @property
    def vpc(self) -> ec2.IVpc:
        """Retorna la VPC compartida de BioStock."""
        return self._vpc

    @property
    def alb_sg(self) -> ec2.ISecurityGroup:
        """Retorna el Security Group del ALB (capa pública)."""
        return self._alb_sg

    @property
    def ecs_sg(self) -> ec2.ISecurityGroup:
        """Retorna el Security Group de ECS (capa de cómputo)."""
        return self._ecs_sg

    @property
    def db_sg(self) -> ec2.ISecurityGroup:
        """Retorna el Security Group de las bases de datos (capa de datos)."""
        return self._db_sg

    # ------------------------------------------------------------------
    # Métodos privados de construcción
    # ------------------------------------------------------------------

    def _create_vpc(self) -> ec2.Vpc:
        """Crea una VPC sin NAT Gateways con subredes públicas únicamente."""
        return ec2.Vpc(
            self,
            "BioStockVpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="PublicSubnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
            ],
        )

    def _create_security_groups(
        self,
    ) -> tuple[ec2.SecurityGroup, ec2.SecurityGroup, ec2.SecurityGroup]:
        """
        Crea los Security Groups con principio de menor privilegio.

        Returns:
            Tupla con (alb_sg, ecs_sg, db_sg).
        """
        alb_sg = ec2.SecurityGroup(
            self, "AlbSg",
            vpc=self._vpc,
            description="Trafico HTTP desde Internet hacia el ALB",
            allow_all_outbound=True,
        )
        alb_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP desde internet"
        )

        ecs_sg = ec2.SecurityGroup(
            self, "EcsSg",
            vpc=self._vpc,
            description="Trafico desde ALB hacia contenedores ECS",
            allow_all_outbound=True,
        )
        ecs_sg.add_ingress_rule(
            alb_sg, ec2.Port.tcp_range(8080, 8085), "Puertos de microservicios"
        )

        db_sg = ec2.SecurityGroup(
            self, "DbSg",
            vpc=self._vpc,
            description="Trafico desde ECS hacia bases de datos",
            allow_all_outbound=True,
        )
        db_sg.add_ingress_rule(ecs_sg, ec2.Port.tcp(5432), "PostgreSQL desde ECS")
        db_sg.add_ingress_rule(ecs_sg, ec2.Port.tcp(1433), "SQL Server desde ECS")

        return alb_sg, ecs_sg, db_sg
