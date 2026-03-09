# BioStock System - Guía de Despliegue en AWS (Costo $0)

Esta guía documenta el proceso paso a paso para desplegar la infraestructura completa de **BioStock** en Amazon Web Services utilizando **AWS CDK (Python)**, manteniendo la facturación en $0.00 aprovechando la Capa Gratuita (Free Tier).

## Arquitectura Desplegada

La topología de la infraestructura está dividida en los siguientes Stacks:

1. **NetworkStack**: Red VPC con subredes públicas (Sin NAT Gateways para evitar costos).
2. **DataStack**: Bases de datos efímeras en Free Tier (RDS PostgreSQL, RDS SQL Server Express `db.t3.micro` y DynamoDB Pay-Per-Request).
3. **ComputeStack**: Repositorios ECR, un clúster ECS (1 Instancia EC2 `t2.micro` autogestionada) y un Application Load Balancer.
4. **MessagingStack**: Topic SNS (Ordenes) y Colas SQS (Payment, Shipping, Notification).
5. **ServerlessStack**: Funciones AWS Lambda consumiendo eventos SQS nativamente. 

---

## Prerrequisitos

1. **WSL (Windows Subsystem for Linux)**: Requerido para la compilación de los JARs de Java 11, evitando problemas de compatibilidad del wrapper `mvnw` en Windows.
2. **Java 11**: Instalado en WSL (`sudo apt install openjdk-11-jdk`).
3. **AWS CLI & AWS Session Manager**: Autenticado a tu cuenta de AWS.
4. **Node.js y AWS CDK**: Instalados de forma global (`npm install -g aws-cdk`).
5. **Docker**: Ejecutándose localmente para compilar imágenes y subirlas a ECR.

---

## 1. Empaquetado y Compilación de Microservicios

Es **crítico** compilar los microservicios Lambda (`payment-service` y `notification-service`) utilizando **WSL** para garantizar que el `maven-shade-plugin` genere el Uber-JAR de forma correcta.

Abre tu terminal WSL y ejecuta el empaquetado **ignorando los tests**:

```bash
# Para Notification Service (Lambda)
cd /mnt/c/Users/juanc/.../BioStock-System/notification-service
./mvnw clean package -DskipTests

# Para Payment Service (Lambda)
cd ../payment-service
./mvnw clean package -DskipTests

# Para Product Service (Docker ECS)
cd ../product-service
./mvnw clean package -DskipTests

# Para User Service (Docker ECS)
cd ../user-service
./mvnw clean package -DskipTests
```

> **Nota sobre las Lambdas:**
> Los servicios de *Payment* y *Notification* han sido adaptados para dejar de utilizar la clase `SpringBootLambdaContainerHandler` (la cual es un proxy de API Gateway) en favor de un `RequestHandler` de mapas genérico nativo. Esto corrige el error `InvalidRequestEventException` al consumir eventos de SQS. Adicionalmente, se creó un perfil interno `application-lambda.yml` para desactivar las conexiones a MySQL y usar H2 en memoria durante la invocación serverless, lo que evita errores de carga del Driver JDBC o Metaspace en frío.

---

## 2. Despliegue de Infraestructura CDK

Una vez inicializados los JARs, podemos desplegar la estructura cloud. Desde Powershell o WSL, ubícate en la carpeta `BioStock-Systems-Infra`.

```bash
cd BioStock-Systems-Infra/
```

Es recomendable desplegar los Stacks en orden explícito durante la primera vez para asegurar consistencia en las dependencias de Bases de Datos y Networking.

```bash
# Despliega VPC (Seguridad y Red)
npx cdk deploy BioStock-Network --require-approval never

# Despliega Bases de Datos (RDS y DynamoDB)
npx cdk deploy BioStock-Data --require-approval never

# Despliega la Mensajería (SNS Topics y Colas SQS)
npx cdk deploy BioStock-Messaging --require-approval never

# Despliega el Cluster ECS, Load Balancer y ECR
npx cdk deploy BioStock-Compute --require-approval never

# Despliega las Lambdas de Procesamiento y las une con SQS (Requiere JARs)
npx cdk deploy BioStock-Serverless --require-approval never
```

> **Verificación:** Ve a CloudFormation en la consola de AWS y verifica que todos los stacks estén en estado `CREATE_COMPLETE` o `UPDATE_COMPLETE`.

---

## 3. Subida de Imágenes Docker a ECR (Product y User Service)

La infraestructura CDK preparó los repositorios de ECR (vacíos). Ahora debes construir la imagen Docker en tu PC y hacer Push.

### Autenticar Docker con Amazon ECR
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 160823835096.dkr.ecr.us-east-1.amazonaws.com
```

### Construir y Subir Product Service
```bash
cd ../product-service
docker build --platform linux/amd64 -t biostock-product .
docker tag biostock-product:latest 160823835096.dkr.ecr.us-east-1.amazonaws.com/biostock-product:latest
docker push 160823835096.dkr.ecr.us-east-1.amazonaws.com/biostock-product:latest
```

### Construir y Subir User Service
```bash
cd ../user-service
docker build --platform linux/amd64 -t biostock-user .
docker tag biostock-user:latest 160823835096.dkr.ecr.us-east-1.amazonaws.com/biostock-user:latest
docker push 160823835096.dkr.ecr.us-east-1.amazonaws.com/biostock-user:latest
```

> **Cobros de ECR:** El almacenamiento de ECR es de $0.00 debido a la capa gratuita (Free Tier) de 500 MB mensuales perpetua (las dos imágenes pesarán en promedio ~400 MB).

---

## 4. Iniciar Contenedores en ECS

Una vez subidas las imágenes a ECR, debes actualizar los *servicios de ECS* para que obliguen la descarga de las nuevas imágenes `latest` a la instancia t2.micro de EC2 asignada.

```bash
# Fuerza el re-despliegue del User Service
aws ecs update-service --cluster BioStockCluster --service UserServiceDeploymentUserAwsService --force-new-deployment --region us-east-1

# Fuerza el re-despliegue del Product Service
aws ecs update-service --cluster BioStockCluster --service ProductServiceDeploymentProductAwsService --force-new-deployment --region us-east-1
```

---

## 5. Validación y Pruebas

Para validar que los microservicios sin servidor y los workers de backend asíncronos están operativos:

### Publicar un Evento SNS Simulando Carga (Fan-Out SQS)
Usa WSL para enviar un evento envuelto al Topic SNS. Esto probará que las Lambdas `payment-service` y `notification-service` reaccionen a eventos asíncronos.

```bash
aws sns publish --region us-east-1 \
  --topic-arn arn:aws:sns:us-east-1:160823835096:biostock-order-events \
  --message '{
    "eventId": "1234",
    "eventType": "payment-created",
    "occurredAt": 1718000000.000000000,
    "payload": {
      "orderId": 4,
      "userId": 1,
      "amount": 250.00,
      "paymentStatus": "COMPLETED"
    }
  }' \
  --no-cli-pager
```

### Revisar Logs en CloudWatch o Terminal
En WSL ejecuta:

**Para Notification Service**
```bash
aws logs tail --region us-east-1 /aws/lambda/$(aws lambda list-functions --region us-east-1 --query "Functions[?contains(FunctionName,'NotificationService')].FunctionName" --output text) --since 1m --no-cli-pager
```

**Para Payment Service**
```bash
aws logs tail --region us-east-1 /aws/lambda/$(aws lambda list-functions --region us-east-1 --query "Functions[?contains(FunctionName,'PaymentService')].FunctionName" --output text) --since 1m --no-cli-pager
```

Deberías observar el consumo exitoso mediante los flujos nativos de Spring Boot: `*** PaymentDto, service; save payment *`.

---

## Estrategia de Eliminación y Costo $0

Recuerda que toda la infraestructura está aprovisionada con el atributo `RemovalPolicy.DESTROY`. Para asegurar evitar fugas de capital y retornar la facturación a absoluto cero una vez culminados los laboratorios o la jornada, destruye toda la torre cloud:

```bash
cd BioStock-Systems-Infra/
npx cdk destroy --all
```
*(AWS borrará los repositorios ECR, los clusters ECS, EC2, el Load Balancer, los esquemas RDS, Amazon SNS y todos los VPCs generados).*
