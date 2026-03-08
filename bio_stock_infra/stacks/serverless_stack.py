"""
Stack Serverless para BioStock.

Despliega microservicios orientados a eventos (notification, payment)
como funciones AWS Lambda que son disparadas por eventos de Amazon SQS.
"""

from typing import Dict, Optional

from aws_cdk import (
    Stack,
    aws_sqs as sqs,
)
from constructs import Construct

from bio_stock_infra.constructs import SpringBootLambda


class ServerlessStack(Stack):
    """
    Stack serverless para la infraestructura BioStock.

    Recibe las colas SQS creadas en MessagingStack y
    despliega funciones Lambda en Java 17 que actúan como
    consumidores (Event-Driven Builders).
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        queues: Dict[str, sqs.IQueue],
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Payment Service Lambda (disparado por payment queue)
        self._create_service("PaymentService", "payment-service", queues.get("payment"))

        # 2. Notification Service Lambda (disparado por notification queue)
        self._create_service("NotificationService", "notification-service", queues.get("notification"))

    def _create_service(
        self, id: str, service_name: str, queue: Optional[sqs.IQueue]
    ) -> Optional[SpringBootLambda]:
        """
        Abstracción defensiva para crear el servicio si la cola existe.
        """
        if not queue:
            print(f"Advertisement: Queue for {service_name} not found. Skipping Lambda creation.")
            return None

        return SpringBootLambda(
            self,
            id,
            service_name=service_name,
            queue=queue
        )
