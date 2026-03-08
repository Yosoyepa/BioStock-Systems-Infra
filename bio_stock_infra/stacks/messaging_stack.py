"""
Stack de Mensajería Asíncrona para BioStock.

Implementa el patrón Fan-out: un Topic SNS publica eventos de dominio
y múltiples colas SQS suscritas los consumen de forma desacoplada.
"""

from aws_cdk import (
    Stack,
    Duration,
    aws_sns as sns,
    aws_sqs as sqs,
    aws_sns_subscriptions as subs,
)
from constructs import Construct


class MessagingStack(Stack):
    """
    Stack de mensajería asíncrona para la infraestructura BioStock.

    Crea un Topic SNS al que se publican eventos de dominio (ej. órdenes)
    y tres Colas SQS (Payment, Shipping, Notification) suscritas al Topic,
    implementando el patrón de Fan-out del diagrama de arquitectura.

    Attributes (exposed via @property):
        order_topic: El Topic SNS para publicar eventos.
        queues: Diccionario inmutable (copia) de las colas SQS creadas.
    """

    _QUEUE_NAMES: list[str] = ["payment", "shipping", "notification"]

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._order_topic = self._create_topic()
        self._queues = self._create_queues_and_subscribe()

    # ------------------------------------------------------------------
    # Properties (interfaz pública de solo lectura)
    # ------------------------------------------------------------------

    @property
    def order_topic(self) -> sns.ITopic:
        """Retorna el Topic SNS de eventos de órdenes."""
        return self._order_topic

    @property
    def queues(self) -> dict[str, sqs.IQueue]:
        """Retorna una copia del diccionario de colas SQS (inmutable desde fuera)."""
        return dict(self._queues)

    # ------------------------------------------------------------------
    # Métodos privados de construcción
    # ------------------------------------------------------------------

    def _create_topic(self) -> sns.Topic:
        """Crea el Topic SNS para publicar eventos de dominio."""
        return sns.Topic(
            self,
            "OrderEventsTopic",
            topic_name="biostock-order-events",
        )

    def _create_queues_and_subscribe(self) -> dict[str, sqs.Queue]:
        """
        Crea las colas SQS y las suscribe al Topic SNS (Fan-out).

        Returns:
            Diccionario con el nombre de la cola como clave y la instancia como valor.
        """
        queues: dict[str, sqs.Queue] = {}

        for name in self._QUEUE_NAMES:
            queue = sqs.Queue(
                self,
                f"{name.capitalize()}Queue",
                queue_name=f"biostock-{name}-events",
                visibility_timeout=Duration.seconds(30),
            )
            self._order_topic.add_subscription(subs.SqsSubscription(queue))
            queues[name] = queue

        return queues
