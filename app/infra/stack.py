"""
ProyectoFinalStack
──────────────────
Define la infraestructura serverless del proyecto final:
  - Tabla DynamoDB  (Single Table Design, PK+SK)
  - Lambda Layer    con las dependencias de las Lambdas (boto3, botocore, redis)
  - Lambda /items   (POST, GET, DELETE) con patrón Cache-Aside sobre Redis
  - Lambda /health  (GET) health check del servicio
  - API Gateway     (RestApi) que enruta las peticiones
"""
import os
import shutil
import subprocess
import sys
from typing import Any

import aws_cdk as cdk
import jsii
from aws_cdk import (
    Stack,
    aws_apigateway as apigw,
    aws_dynamodb as ddb,
    aws_lambda as _lambda,
    RemovalPolicy,
    CfnOutput,
)
from aws_cdk import aws_iam as iam
from constructs import Construct

# Runtime común a todas las Lambdas y a la layer
RUNTIME: _lambda.Runtime = _lambda.Runtime.PYTHON_3_11
DIR_LAYER: str = "layers/dependencias"
REQUIREMENTS_LAYER: str = os.path.join(DIR_LAYER, "requirements.txt")

# LocalStack Community acepta las Lambda Layers pero no las monta al ejecutar
# (es una función de LocalStack Pro). Cuando se despliega en el emulador
# (cdk-dev define AWS_ENDPOINT_URL), las dependencias se empaquetan dentro
# del código de cada Lambda en lugar de usar la layer.
ES_LOCAL: bool = "AWS_ENDPOINT_URL" in os.environ


def _pip_install(requirements: str, destino: str) -> None:
    """Instala las dependencias en `destino` para el runtime de Lambda."""
    uv = shutil.which("uv")
    command = (
        [uv, "pip", "install", "--python", sys.executable]
        if uv
        else [sys.executable, "-m", "pip", "install"]
    )
    platform_options = (
        ["--python-platform", "x86_64-manylinux2014"]
        if uv
        else ["--platform", "manylinux2014_x86_64", "--implementation", "cp", "--no-compile"]
    )
    subprocess.run(
        command + [
            "--quiet",
            "--requirement", requirements,
            "--target", destino,
            "--python-version", "3.11",
            "--only-binary=:all:",
        ] + platform_options,
        check=True,
    )


@jsii.implements(cdk.ILocalBundling)
class _PipLocal:
    """
    Empaqueta con el pip del propio contenedor cdk-dev, sin necesitar Docker.

    - Layer:  instala en "python/", donde Lambda busca las librerías de una layer.
    - Lambda: copia el código fuente y las dependencias juntas en la raíz.
    """

    def __init__(
        self,
        requirements: str,
        subdir: str = "",
        copiar_desde: str | None = None,
    ) -> None:
        self.requirements: str = requirements
        self.subdir: str = subdir
        self.copiar_desde: str | None = copiar_desde

    def try_bundle(self, output_dir: str, *args: Any, **kwargs: Any) -> bool:
        if self.copiar_desde:
            shutil.copytree(
                self.copiar_desde,
                output_dir,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            shared_modules = "modules"
            if os.path.isdir(shared_modules):
                shutil.copytree(
                    shared_modules,
                    os.path.join(output_dir, "modules"),
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__"),
                )
        _pip_install(self.requirements, os.path.join(output_dir, self.subdir))
        if self.subdir == "python" and os.path.isdir("modules"):
            shutil.copytree(
                "modules",
                os.path.join(output_dir, "python", "modules"),
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        return True


def _codigo_lambda(directorio: str) -> _lambda.Code:
    """
    Código de una Lambda. En AWS solo nuestros .py (las dependencias van en
    la layer); en LocalStack, nuestros .py + las dependencias de la layer.
    """
    if not ES_LOCAL:
        return _lambda.Code.from_asset(directorio)
    return _lambda.Code.from_asset(
        directorio,
        # El hash se calcula sobre el resultado, así también cambia
        # cuando cambian las dependencias y no solo el código
        asset_hash_type=cdk.AssetHashType.OUTPUT,
        bundling=cdk.BundlingOptions(
            # Solo se usaría si falla el bundling local (cdk-dev no tiene Docker)
            image=RUNTIME.bundling_image,
            command=["bash", "-c", "echo 'Requiere bundling local con pip' && exit 1"],
            local=_PipLocal(REQUIREMENTS_LAYER, copiar_desde=directorio),
        ),
    )


class ProyectoFinalStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        jwt_secret = cdk.CfnParameter(
            self,
            "JwtSecret",
            type="String",
            no_echo=True,
            description="JWT signing secret for the local identity adapter",
        )

        # ── 1. TABLA DYNAMODB ─────────────────────────────────────────
        # Single Table Design: PK y SK genéricos para soportar
        # múltiples tipos de entidades en una sola tabla.
        tabla: ddb.Table = ddb.Table(
            self,
            "AppTable",
            table_name="FlashBidTable",
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
            time_to_live_attribute="ttl",
        )
        tabla.add_global_secondary_index(
            index_name="GSI1",
            partition_key=ddb.Attribute(name="GSI1PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="GSI1SK", type=ddb.AttributeType.STRING),
            projection_type=ddb.ProjectionType.KEYS_ONLY,
        )
        tabla.add_global_secondary_index(
            index_name="GSI2",
            partition_key=ddb.Attribute(name="GSI2PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="GSI2SK", type=ddb.AttributeType.STRING),
            projection_type=ddb.ProjectionType.KEYS_ONLY,
        )
        tabla.add_global_secondary_index(
            index_name="GSI3",
            partition_key=ddb.Attribute(name="GSI3PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="GSI3SK", type=ddb.AttributeType.STRING),
            projection_type=ddb.ProjectionType.KEYS_ONLY,
        )
        tabla.add_global_secondary_index(
            index_name="GSI4",
            partition_key=ddb.Attribute(name="GSI4PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="GSI4SK", type=ddb.AttributeType.STRING),
            projection_type=ddb.ProjectionType.INCLUDE,
            non_key_attributes=["amount", "acceptedAt", "bidId"],
        )

        # Variables de entorno comunes para todas las Lambdas
        env_comun: dict[str, str] = {
            "TABLE_NAME": tabla.table_name,
            "REDIS_HOST": os.environ.get("REDIS_HOST", "redis"),
            "REDIS_PORT": os.environ.get("REDIS_PORT", "6379"),
            "REDIS_TTL":  "300",   # segundos de vida en caché
            "APP_ENV": os.environ.get("APP_ENV", "local"),
            "JWT_SECRET": jwt_secret.value_as_string,
            "JWT_ISSUER": os.environ.get("JWT_ISSUER", "flashbid-local-auth"),
            "JWT_AUDIENCE": os.environ.get("JWT_AUDIENCE", "flashbid-web"),
        }

        # ── 2. LAMBDA LAYER (dependencias) ────────────────────────────
        # Code.from_asset("lambdas/...") solo empaqueta nuestros .py.
        # Las librerías externas van en una layer compartida, construida
        # con pip a partir de layers/dependencias/requirements.txt.
        # Se reconstruye solo cuando cambia ese archivo.
        # En LocalStack no se crea: no la aplicaría (ver ES_LOCAL).
        layers: list[_lambda.ILayerVersion] = []
        if not ES_LOCAL:
            layer_dependencias: _lambda.LayerVersion = _lambda.LayerVersion(
                self,
                "DependenciasLayer",
                code=_lambda.Code.from_asset(
                    DIR_LAYER,
                    bundling=cdk.BundlingOptions(
                        # image/command solo se usan si falla el bundling local
                        image=RUNTIME.bundling_image,
                        command=[
                            "bash", "-c",
                            "pip install -r requirements.txt -t /asset-output/python",
                        ],
                        local=_PipLocal(REQUIREMENTS_LAYER, subdir="python"),
                    ),
                ),
                compatible_runtimes=[RUNTIME],
                description="boto3, botocore y redis para las Lambdas",
            )
            layers.append(layer_dependencias)

        # ── 3. LAMBDA /health ─────────────────────────────────────────
        # Health check: verifica conectividad con DynamoDB y Redis
        lambda_health: _lambda.Function = _lambda.Function(
            self,
            "HealthHandler",
            runtime=RUNTIME,
            handler="handler.main",
            code=_codigo_lambda("lambdas/health"),
            layers=layers,
            environment=env_comun,
            timeout=cdk.Duration.seconds(5),
        )
        lambda_health.add_to_role_policy(iam.PolicyStatement(
            actions=["dynamodb:DescribeTable"], resources=[tabla.table_arn]
        ))

        lambda_users: _lambda.Function = _lambda.Function(
            self,
            "UsersHandler",
            runtime=RUNTIME,
            handler="handler.main",
            code=_codigo_lambda("lambdas/users"),
            layers=layers,
            environment=env_comun,
            timeout=cdk.Duration.seconds(5),
        )
        lambda_users.add_to_role_policy(iam.PolicyStatement(
            actions=["dynamodb:GetItem", "dynamodb:TransactWriteItems"],
            resources=[tabla.table_arn],
        ))

        lambda_wallet: _lambda.Function = _lambda.Function(
            self,
            "WalletHandler",
            runtime=RUNTIME,
            handler="handler.main",
            code=_codigo_lambda("lambdas/wallet"),
            layers=layers,
            environment=env_comun,
            timeout=cdk.Duration.seconds(5),
        )
        lambda_wallet.add_to_role_policy(iam.PolicyStatement(
            actions=["dynamodb:Query"], resources=[tabla.table_arn],
        ))

        lambda_auctions: _lambda.Function = _lambda.Function(
            self,
            "AuctionsHandler",
            runtime=RUNTIME,
            handler="handler.main",
            code=_codigo_lambda("lambdas/auctions"),
            layers=layers,
            environment=env_comun,
            timeout=cdk.Duration.seconds(5),
        )
        lambda_auctions.add_to_role_policy(iam.PolicyStatement(
            actions=["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"],
            resources=[tabla.table_arn],
        ))

        # ── 5. API GATEWAY ────────────────────────────────────────────
        # LambdaRestApi crea automáticamente una integración proxy
        # entre API Gateway y la Lambda raíz.
        # Luego agregamos recursos adicionales para /items y /health.
        api: apigw.RestApi = apigw.RestApi(
            self,
            "Api",
            rest_api_name="ProyectoFinal-API",
            description="API del proyecto final — DynamoDB + Redis + CDK",
            deploy_options=apigw.StageOptions(stage_name="prod"),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=["http://localhost:5173"],
                allow_headers=["Authorization", "Content-Type"],
                allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            ),
        )

        # /health  → GET
        recurso_health: apigw.Resource = api.root.add_resource("health")
        recurso_health.add_method(
            "GET",
            apigw.LambdaIntegration(lambda_health),
        )

        recurso_me: apigw.Resource = api.root.add_resource("me")
        recurso_me.add_method("GET", apigw.LambdaIntegration(lambda_users))
        recurso_wallet: apigw.Resource = recurso_me.add_resource("wallet")
        recurso_movements: apigw.Resource = recurso_wallet.add_resource("movements")
        recurso_movements.add_method("GET", apigw.LambdaIntegration(lambda_wallet))

        recurso_auctions: apigw.Resource = api.root.add_resource("auctions")
        recurso_auctions.add_method("POST", apigw.LambdaIntegration(lambda_auctions))
        recurso_auction_id: apigw.Resource = recurso_auctions.add_resource("{id}")
        recurso_auction_id.add_method("DELETE", apigw.LambdaIntegration(lambda_auctions))

        # ── 6. OUTPUTS ────────────────────────────────────────────────
        CfnOutput(self, "ApiUrl",
                  value=api.url,
                  description="URL base del API Gateway")
        CfnOutput(self, "TableName",
                  value=tabla.table_name,
                  description="Nombre de la tabla DynamoDB")
