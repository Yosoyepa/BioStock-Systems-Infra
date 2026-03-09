"""
Constructo L3 para desplegar un microservicio Spring Boot como AWS Lambda.

Responsabilidad única: Configurar y proveer una Lambda de Java/Spring Boot
con disparador SQS, manejando el fallback a un handler dummy cuando
el JAR aún no ha sido compilado localmente.
"""

from typing import Optional
from pathlib import Path

from aws_cdk import (
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
    """

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        service_name: str,
        queue: sqs.IQueue,
        jar_version: str = "v2.5.14",
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Manejo de rutas multiplataforma con pathlib (Portabilidad)
        # Resolución: constructs/ → bio_stock_infra/ → BioStock-Systems-Infra/ → BioStock-System/
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        jar_path = base_dir / service_name / "target" / f"{service_name}-{jar_version}.jar"

        # Determinismo e inyección: evaluamos el estado
        jar_exists = jar_path.exists()

        if jar_exists:
            code_asset = _lambda.Code.from_asset(str(jar_path))
            runtime = _lambda.Runtime.JAVA_11
            handler = "com.selimhorri.app.StreamLambdaHandler::handleRequest"
        else:
            code_asset = _lambda.Code.from_inline("def handler(event, context): return 'Missing JAR'")
            runtime = _lambda.Runtime.PYTHON_3_9
            handler = "index.handler"

        self.function = _lambda.Function(
            self,
            "Function",
            runtime=runtime,
            handler=handler,
            code=code_asset,
            memory_size=1024,
            timeout=Duration.seconds(30),
            environment={
                "SPRING_PROFILES_ACTIVE": "lambda",
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

        # Otorgar permisos a la Lambda para consumir mensajes de la cola
        queue.grant_consume_messages(self.function)
