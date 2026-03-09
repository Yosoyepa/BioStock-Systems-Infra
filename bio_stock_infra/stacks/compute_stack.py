"""
Stack de Cómputo para BioStock.

Gestiona los repositorios ECR para los microservicios, el cluster ECS
sobre una instancia EC2 t2.micro (Free Tier) y el Application Load Balancer
que actúa como punto de entrada REST.
"""

from typing import Dict, List

from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_autoscaling as autoscaling,
    aws_elasticloadbalancingv2 as elbv2,
)
from constructs import Construct

from bio_stock_infra.constructs import MicroserviceEcsDeployment
from bio_stock_infra.models import MicroserviceProps


class ComputeStack(Stack):
    """
    Stack de cómputo para la infraestructura BioStock.

    Recibe la VPC y los Security Groups del NetworkStack (inyección de
    dependencias) y construye:
        - Repositorios ECR (uno por microservicio) con borrado automático.
        - Un cluster ECS respaldado por un ASG de 1 instancia t2.micro.
        - Un Application Load Balancer orientado a internet.

    El stack es agnóstico de las bases de datos. La configuración específica
    de cada microservicio (variables de entorno, secretos) se gestiona
    externamente a través del método ``add_microservice()``.
    """

    _MICROSERVICES: List[str] = [
        "product",
        "user",
    ]

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc: ec2.IVpc,
        ecs_sg: ec2.ISecurityGroup,
        alb_sg: ec2.ISecurityGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._repos = self._create_ecr_repositories()
        self._cluster, self._asg = self._create_ecs_cluster(vpc, ecs_sg)
        self._alb, self._listener = self._create_alb(vpc, alb_sg)

    # ------------------------------------------------------------------
    # Properties (interfaz pública de solo lectura)
    # ------------------------------------------------------------------

    @property
    def repos(self) -> Dict[str, ecr.IRepository]:
        """Retorna una copia del diccionario de repositorios ECR."""
        return dict(self._repos)

    @property
    def cluster(self) -> ecs.ICluster:
        """Retorna el cluster ECS."""
        return self._cluster

    @property
    def alb(self) -> elbv2.IApplicationLoadBalancer:
        """Retorna el Application Load Balancer."""
        return self._alb

    @property
    def listener(self) -> elbv2.ApplicationListener:
        """Retorna el listener HTTP del ALB."""
        return self._listener

    # ------------------------------------------------------------------
    # Método público para registrar microservicios (Open/Closed)
    # ------------------------------------------------------------------

    def add_microservice(
        self,
        name: str,
        props: MicroserviceProps,
    ) -> MicroserviceEcsDeployment:
        """
        Registra y despliega un microservicio en el cluster ECS.

        Args:
            name: Nombre del microservicio (debe coincidir con un repo ECR).
            props: Parameter Object (MicroserviceProps) con la configuración.

        Raises:
            ValueError: Si el microservicio no tiene un repositorio ECR.
        """
        repo = self._repos.get(name)
        if not repo:
            raise ValueError(
                f"No ECR repository found for '{name}'. "
                f"Available: {list(self._repos.keys())}"
            )

        return MicroserviceEcsDeployment(
            self,
            f"{name.capitalize()}Deployment",
            cluster=self._cluster,
            listener=self._listener,
            repo=repo,
            props=props,
        )

    # ------------------------------------------------------------------
    # Métodos privados de construcción
    # ------------------------------------------------------------------

    def _create_ecr_repositories(self) -> Dict[str, ecr.Repository]:
        """
        Crea un repositorio ECR por cada microservicio definido.

        Todos los repositorios se configuran con ``empty_on_delete=True``
        para garantizar limpieza total al destruir el stack.
        """
        repos: Dict[str, ecr.Repository] = {}

        for name in self._MICROSERVICES:
            repo = ecr.Repository(
                self,
                f"Ecr{name.capitalize()}",
                repository_name=f"biostock-{name}",
                removal_policy=RemovalPolicy.DESTROY,
                empty_on_delete=True,
            )
            repos[name] = repo

        return repos

    def _create_ecs_cluster(
        self, vpc: ec2.IVpc, ecs_sg: ec2.ISecurityGroup
    ) -> tuple[ecs.Cluster, autoscaling.AutoScalingGroup]:
        """
        Crea el cluster ECS con un ASG de 1 instancia t2.micro (Free Tier).

        La instancia reside en una subred pública con IP asociada para
        poder descargar imágenes de ECR sin necesidad de NAT Gateway.
        """
        cluster = ecs.Cluster(self, "BioStockCluster", vpc=vpc)

        asg = autoscaling.AutoScalingGroup(
            self,
            "EcsAsg",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            instance_type=ec2.InstanceType("t2.micro"),
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
            min_capacity=1,
            max_capacity=1,
            security_group=ecs_sg,
        )

        capacity_provider = ecs.AsgCapacityProvider(
            self,
            "AsgCapacityProvider",
            auto_scaling_group=asg,
        )
        cluster.add_asg_capacity_provider(capacity_provider)

        return cluster, asg

    def _create_alb(
        self, vpc: ec2.IVpc, alb_sg: ec2.ISecurityGroup
    ) -> tuple[elbv2.ApplicationLoadBalancer, elbv2.ApplicationListener]:
        """
        Crea el ALB orientado a internet y su listener HTTP por defecto.

        El listener devuelve una respuesta fija de salud hasta que se
        registren los Target Groups de los microservicios.
        """
        alb = elbv2.ApplicationLoadBalancer(
            self,
            "BioStockAlb",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_sg,
        )

        listener = alb.add_listener(
            "HttpListener",
            port=80,
            default_action=elbv2.ListenerAction.fixed_response(
                status_code=200,
                content_type="text/plain",
                message_body="BioStock API Gateway - ALB Active",
            ),
        )

        return alb, listener
