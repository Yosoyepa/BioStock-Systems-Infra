"""
Constructo L3 para el despliegue de un Microservicio en ECS EC2.

Responsabilidad única: Dado un repositorio ECR, cluster, listener
y un objeto de propiedades (MicroserviceProps), crear la TaskDefinition,
el Container, el Ec2Service y registrar el Target Group en el ALB.
"""

from aws_cdk import (
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
)
from constructs import Construct

from bio_stock_infra.models import MicroserviceProps


class MicroserviceEcsDeployment(Construct):
    """
    Constructo de nivel 3 (L3) que encapsula el despliegue completo
    de un microservicio en ECS EC2 con integración al ALB.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        cluster: ecs.ICluster,
        listener: elbv2.ApplicationListener,
        repo: ecr.IRepository,
        props: MicroserviceProps,
    ) -> None:
        super().__init__(scope, construct_id)

        # --- Validación defensiva (Fail-fast) ---
        if props.priority < 1:
            raise ValueError(f"Priority must be >= 1, got {props.priority}")
        if props.container_port < 1 or props.container_port > 65535:
            raise ValueError(f"Invalid container_port: {props.container_port}")

        # --- Valores por defecto seguros ---
        base_environment = {"SPRING_PROFILES_ACTIVE": "prod"}
        if props.environment:
            base_environment.update(props.environment)

        # --- Task Definition ---
        task_def = ecs.Ec2TaskDefinition(self, "TaskDef")

        container = task_def.add_container(
            "Container",
            image=ecs.ContainerImage.from_ecr_repository(repo, "latest"),
            memory_limit_mib=props.memory_limit_mib,
            environment=base_environment,
            secrets=props.secrets,
            logging=ecs.LogDrivers.aws_logs(stream_prefix=construct_id),
        )

        container.add_port_mappings(
            ecs.PortMapping(container_port=props.container_port, protocol=ecs.Protocol.TCP)
        )

        # --- ECS Service ---
        self.service = ecs.Ec2Service(
            self,
            "Service",
            cluster=cluster,
            task_definition=task_def,
        )

        # --- Integración al ALB (Target Group + Routing Rule) ---
        self.target_group = listener.add_targets(
            f"{construct_id}Tg",
            port=props.container_port,
            targets=[
                self.service.load_balancer_target(
                    container_name="Container",
                    container_port=props.container_port,
                )
            ],
            health_check=elbv2.HealthCheck(
                path=props.health_check_path,
                healthy_http_codes="200",
            ),
            conditions=[elbv2.ListenerCondition.path_patterns(props.path_patterns)],
            priority=props.priority,
        )
