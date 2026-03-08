"""
Parameter Object para la configuración de microservicios ECS.

Actúa como el equivalente a una Interface/DTO para evitar
listas largas de argumentos en constructos y funciones.
"""

from typing import Dict
from dataclasses import dataclass, field

from aws_cdk import aws_ecs as ecs


@dataclass
class MicroserviceProps:
    """
    Propiedades de configuración para el despliegue de un microservicio ECS.

    Actúa como una interfaz (Parameter Object) para evitar listas largas
    de argumentos en constructos y métodos de orquestación.

    Attributes:
        path_pattern: Patrón de URL para el enrutamiento del ALB (ej. /api/users/*).
        priority: Prioridad de la regla del listener (debe ser única por servicio).
        container_port: Puerto que expone el contenedor (default: 8080).
        memory_limit_mib: Límite de memoria del contenedor en MiB (default: 256).
        environment: Variables de entorno para inyectar al contenedor.
        secrets: Secretos de ECS (ej. credenciales de base de datos).
    """

    path_pattern: str
    priority: int
    container_port: int = 8080
    memory_limit_mib: int = 256
    environment: Dict[str, str] = field(default_factory=dict)
    secrets: Dict[str, ecs.Secret] = field(default_factory=dict)
