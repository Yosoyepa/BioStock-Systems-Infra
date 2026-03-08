# Conexión de Microservicios a la Infraestructura BioStock

Esta guía detalla cómo los equipos de desarrollo de backend y frontend deben integrarse con la infraestructura desplegada mediante AWS CDK.

## 1. Integración del Cómputo (Backend)

Todos los microservicios (`auth`, `product`, `order`, `payment`, `shipping`, `notification`) están diseñados para correr como contenedores Docker dentro de **Amazon ECS**.

### A. Repositorios de Imágenes (ECR)
El `ComputeStack` crea 6 repositorios ECR con los siguientes nombres:
- `biostock-auth`
- `biostock-product`
- `biostock-order`
- `biostock-payment`
- `biostock-shipping`
- `biostock-notification`

**Flujo de CI/CD o Despliegue Manual:**
1. Haz el login en ECR vía AWS CLI.
2. Haz el build de tu imagen Docker: `docker build -t biostock-<servicio> .`
3. Etiqueta y sube la imagen al repositorio correspondiente en tu cuenta de AWS.

### B. Enrutamiento del Tráfico (Application Load Balancer)
El ALB actúa como el punto de entrada REST. Cada microservicio debe definir un **Target Group** y registrarse en el `HttpListener` del ALB basado en el path de la URL (Path-based routing). Por ejemplo:
- `/api/auth/*` -> Target Group del Auth Service
- `/api/orders/*` -> Target Group del Order Service

*Nota: Actualmente el CDK crea el ALB genérico. La definición de Tareas ECS y Target Groups se puede integrar en el `ComputeStack` una vez que las imágenes Docker existan.*

## 2. Integración a las Bases de Datos (Data Tier)

La capa de datos está estrictamente protegida en subredes sin acceso público. Solo el cluster ECS (donde corren los microservicios) tiene permitido el acceso mediante los Security Groups.

### A. PostgreSQL (Microservicios transaccionales regulares)
- **Endpoint:** Exportado en CloudFormation tras el despliegue.
- **Puerto:** `5432`
- **Uso:** El microservicio inyecta el endpoint, usuario y contraseña como Variables de Entorno en su contenedor ECS.

### B. SQL Server (Si aplica a algún servicio legacy o específico)
- **Endpoint:** Exportado tras el despliegue.
- **Puerto:** `1433`

### C. DynamoDB (Sistema de Eventos / Logs)
- **Tabla:** `BioStockEventsTable`
- **Claves:** `PK` (Partition Key) y `SK` (Sort Key).
- **Acceso:** El Task Role del contenedor ECS debe tener permisos IAM (`table.grant_read_write_data()`) para interactuar con la tabla. ¡No usar Access Keys en los contenedores!

## 3. Integración de Mensajería Asíncrona (Fan-out)

El sistema utiliza SNS y SQS para desacoplar el procesamiento de dominio.

### A. Publicador (Order Service)
El Order Service publica mensajes de eventos (ej: `OrderCreated`) en el Topic SNS.
- **Topic Name:** `biostock-order-events`
- **Requisito IAM:** El Task Role del Order Service debe tener permiso de publicación sobre el Topic (`topic.grant_publish(ecs_task_role)`).

### B. Consumidores (Payment, Shipping, Notification)
Estos servicios deben leer asíncronamente de sus respectivas colas SQS.
- `biostock-payment-events` -> Payment Service
- `biostock-shipping-events` -> Shipping Service
- `biostock-notification-events` -> Notification Service
- **Requisito IAM:** El Task Role de cada contenedor consumidor debe tener permisos de consumo sobre su cola (`queue.grant_consume_messages(ecs_task_role)`).

## 4. Integración del Frontend (SPA)

El frontend (React/Angular/Vue) se despliega como archivos estáticos.

1. **Build Local:** Genera tu carpeta `dist/` o `build/`.
2. **Subida a S3:** El `CdnStack` provee el bucket S3 (su nombre se exporta tras el despliegue). Sube los contenidos generados a este bucket.
3. **Distribución CloudFront:** Apunta el CNAME de tu dominio (si tienes) a la URL de CloudFront provista. Todo el tráfico hacia los assets o las rutas del SPA (`/login`, `/dashboard`) es manejado por CloudFront con redirecciones 200 OK para no romper el enrutamiento del lado del cliente.
4. **CORS:** Asegúrate de que tu ALB esté configurado para devolver las cabeceras CORS correctas si tu CloudFront y ALB están en dominios distintos.
