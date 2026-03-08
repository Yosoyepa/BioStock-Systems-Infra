"""
Stack de CDN y Assets Estáticos para BioStock.

Configura un bucket S3 privado para alojar el React SPA y una
distribución CloudFront con Origin Access Control (OAC) para
servir el contenido de forma segura y con baja latencia.
"""

from aws_cdk import (
    Stack,
    RemovalPolicy,
    Duration,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
)
from constructs import Construct


class CdnStack(Stack):
    """
    Stack de distribución de contenido para la infraestructura BioStock.

    Totalmente independiente de la VPC. Crea:
        - Un Bucket S3 privado (Block All Public Access) para el React SPA.
        - Una distribución CloudFront con OAC acoplada al bucket.
        - Redirecciones 403/404 → index.html para SPA routing.

    Attributes (exposed via @property):
        spa_bucket: Referencia de solo lectura al bucket S3 del SPA.
        distribution: Referencia de solo lectura a la distribución CloudFront.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._spa_bucket = self._create_spa_bucket()
        self._distribution = self._create_distribution()

    # ------------------------------------------------------------------
    # Properties (interfaz pública de solo lectura)
    # ------------------------------------------------------------------

    @property
    def spa_bucket(self) -> s3.IBucket:
        """Retorna el bucket S3 que aloja el React SPA."""
        return self._spa_bucket

    @property
    def distribution(self) -> cloudfront.IDistribution:
        """Retorna la distribución CloudFront."""
        return self._distribution

    # ------------------------------------------------------------------
    # Métodos privados de construcción
    # ------------------------------------------------------------------

    def _create_spa_bucket(self) -> s3.Bucket:
        """Crea el bucket S3 privado con destrucción y vaciado automáticos."""
        return s3.Bucket(
            self,
            "SpaBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

    def _create_distribution(self) -> cloudfront.Distribution:
        """
        Crea la distribución CloudFront con OAC y redirecciones SPA.

        Las respuestas 403 y 404 se redirigen a ``/index.html`` para
        soportar el enrutamiento del lado del cliente (React Router, etc.).
        """
        return cloudfront.Distribution(
            self,
            "BioStockCdn",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    self._spa_bucket,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            default_root_object="index.html",
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
        )
