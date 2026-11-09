"""
ProyectoFinalStack
──────────────────
Define la infraestructura serverless del proyecto final:
  - Tabla DynamoDB  (Single Table Design, PK+SK)
  - Lambda /items   (GET, POST) con patrón Cache-Aside sobre Redis
  - Lambda /health  (GET) health check del servicio
  - API Gateway     (LambdaRestApi) que enruta las peticiones
"""
import os
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_dynamodb as ddb,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct


class ProyectoFinalStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── 1. TABLA DYNAMODB ─────────────────────────────────────────
        # Single Table Design: PK y SK genéricos para soportar
        # múltiples tipos de entidades en una sola tabla.
        tabla = ddb.Table(
            self,
            "AppTable",
            partition_key=ddb.Attribute(
                name="PK",
                type=ddb.AttributeType.STRING,
            ),
            sort_key=ddb.Attribute(
                name="SK",
                type=ddb.AttributeType.STRING,
            ),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            # DESTROY permite borrar la tabla al hacer `cdklocal destroy`
            # En producción usar RETAIN
            removal_policy=RemovalPolicy.DESTROY,
        )

        # Variables de entorno comunes para todas las Lambdas
        env_comun = {
            "TABLE_NAME": tabla.table_name,
            "REDIS_HOST": os.environ.get("REDIS_HOST", "redis"),
            "REDIS_PORT": os.environ.get("REDIS_PORT", "6379"),
            "REDIS_TTL":  "300",   # segundos de vida en caché
        }

        # ── 2. LAMBDA /items ──────────────────────────────────────────
        # Maneja GET /items/{id} y POST /items
        # Implementa Cache-Aside: consulta Redis antes de ir a DynamoDB
        lambda_items = _lambda.Function(
            self,
            "ItemsHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.main",
            code=_lambda.Code.from_asset("lambdas/items"),
            environment=env_comun,
            timeout=cdk.Duration.seconds(10),
        )
        tabla.grant_read_write_data(lambda_items)

        # ── 3. LAMBDA /health ─────────────────────────────────────────
        # Health check: verifica conectividad con DynamoDB y Redis
        lambda_health = _lambda.Function(
            self,
            "HealthHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.main",
            code=_lambda.Code.from_asset("lambdas/health"),
            environment=env_comun,
            timeout=cdk.Duration.seconds(5),
        )
        tabla.grant_read_data(lambda_health)

        # ── 4. API GATEWAY ────────────────────────────────────────────
        # LambdaRestApi crea automáticamente una integración proxy
        # entre API Gateway y la Lambda raíz.
        # Luego agregamos recursos adicionales para /items y /health.
        api = apigw.RestApi(
            self,
            "Api",
            rest_api_name="ProyectoFinal-API",
            description="API del proyecto final — DynamoDB + Redis + CDK",
            deploy_options=apigw.StageOptions(stage_name="prod"),
        )

        # /items  → GET (listar/obtener) y POST (crear)
        recurso_items = api.root.add_resource("items")
        recurso_items.add_method(
            "POST",
            apigw.LambdaIntegration(lambda_items),
        )
        # /items/{id}  → GET (obtener uno)
        recurso_item_id = recurso_items.add_resource("{id}")
        recurso_item_id.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_items),
        )
        recurso_item_id.add_method(
            "DELETE",
            apigw.LambdaIntegration(lambda_items),
        )

        # /health  → GET
        recurso_health = api.root.add_resource("health")
        recurso_health.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_health),
        )

        # ── 5. OUTPUTS ────────────────────────────────────────────────
        CfnOutput(self, "ApiUrl",
                  value=api.url,
                  description="URL base del API Gateway")
        CfnOutput(self, "TableName",
                  value=tabla.table_name,
                  description="Nombre de la tabla DynamoDB")
