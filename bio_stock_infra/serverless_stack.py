"""
Stack Serverless para BioStock.

Despliega microservicios orientados a eventos (notification, payment)
como funciones AWS Lambda que son disparadas por eventos de Amazon SQS.
"""

from typing import Dict, Optional
from pathlib import Path

from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_sqs as sqs,
    aws_lambda_event_sources as lambda_events,
)
from constructs import Construct


class SpringBootLambda(Construct):
    """
    Constructo de nivel 3 (L3) para desplegar un microservicio Spring Boot
    como una función de AWS Lambda impulsada por eventos de SQS.
    Responsabilidad única: Configurar y proveer una Lambda de Java/Spring Boot.
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        service_name: str,
        queue: sqs.IQueue,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Manejo de rutas multiplataforma con pathlib (Portabilidad)
        # Asume que el usuario correrá cdk deploy DESPUÉS de compilar localmente
        # con ./mvnw clean package para generar el JAR 'xxxx-v0.1.0.jar'
        base_dir = Path(__file__).resolve().parent.parent.parent
        jar_path = base_dir / "BioStock-System" / service_name / "target" / f"{service_name}-v0.1.0.jar"

        # Determinismo e inyección: evaluamos el estado
        jar_exists = jar_path.exists()

        if jar_exists:
            code_asset = _lambda.Code.from_asset(str(jar_path))
            runtime = _lambda.Runtime.JAVA_17
            handler = "com.selimhorri.app.StreamLambdaHandler::handleRequest"
        else:
            code_asset = _lambda.Code.from_inline("def handler(event, context): return 'Missing JAR'")
            runtime = _lambda.Runtime.PYTHON_3_9
            handler = "index.handler"

        # No definimos function_name fijo (Nombres Lógicos vs Físicos)
        # El nombre físico lo genera AWS CDK automáticamente para mayor seguridad
        self.function = _lambda.Function(
            self,
            "Function",
            runtime=runtime,
            handler=handler,
            code=code_asset,
            memory_size=512,  # Memoria base recomendada para JVM Serverless
            timeout=Duration.seconds(30),  # Límite recomendado para API Lambdas y colas
            environment={
                "SPRING_PROFILES_ACTIVE": "prod",
                # Configuración explícita para forzar arranque rápido sin Beans innecesarios
                "JAVA_TOOL_OPTIONS": "-XX:+TieredCompilation -XX:TieredStopAtLevel=1"
            }
        )

        # Configurar el origen de los eventos (SQS -> Lambda)
        self.function.add_event_source(
            lambda_events.SqsEventSource(
                queue,
                batch_size=10,
                max_batching_window=Duration.seconds(0)
            )
        )

        # Otorgar permisos a la Lambda para que borre el mensaje de la cola tras procesarlo
        queue.grant_consume_messages(self.function)


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
