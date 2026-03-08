# BioStock Infrastructure (AWS CDK)

Este repositorio contiene la Infraestructura como Código (IaC) para el proyecto **BioStock**, implementada íntegramente de forma modular usando **AWS CDK v2 (Python)**. 

La arquitectura está diseñada para ser **100% Free Tier** y **totalmente efímera**, lo que la hace ideal para entornos de desarrollo, pruebas y presentaciones breves sin incurrir en costos.

## 🏗️ Arquitectura Modular

El proyecto implementa el patrón de Diseño Orientado a Dominios (Domain-Driven Design), dividiendo el tradicional monolito en 5 Stacks granulares e independientes que se comunican inyectando dependencias.

1. **`BioStock-Network`**: Crea la VPC ($0 costo, sin NAT Gateways) y los Security Groups aplicando el principio de menor privilegio.
2. **`BioStock-Data`**: Provisión de las bases de datos efímeras (RDS PostgreSQL, RDS SQL Server Express) y almacenamiento On-Demand (DynamoDB).
3. **`BioStock-Messaging`**: Patrón Fan-out asíncrono usando un Topic SNS y colas SQS.
4. **`BioStock-Compute`**: Cómputo orquestado en ECS sobre una instancia `t2.micro` (Free Tier), repositorios ECR para 6 microservicios y un Application Load Balancer (ALB).
5. **`BioStock-Cdn`**: Almacenamiento S3 y distribución global mediante CloudFront con Origin Access Control (OAC) para el Frontend (SPA).

## 🚀 Requisitos Previos

- [Node.js](https://nodejs.org/) (para usar AWS CDK CLI)
- [Python 3.9+](https://www.python.org/downloads/)
- [AWS CLI](https://aws.amazon.com/cli/) instalado y configurado con credenciales válidas.
- [AWS CDK v2](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) (`npm install -g aws-cdk`)

## 🛠️ Configuración y Despliegue

1. **Clonar el repositorio y entrar al directorio:**
   ```bash
   git clone <repo-url>
   cd BioStock-Infra
   ```

2. **Crear y activar el entorno virtual:**
   ```bash
   # Linux/macOS/WSL
   python3 -m venv .venv
   source .venv/bin/activate

   # Windows
   .venv\Scripts\activate.bat
   ```

3. **Instalar las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Sintetizar la plantilla (Validación):**
   ```bash
   cdk synth
   ```

5. **Desplegar la infraestructura:**
   ```bash
   # Despliega todos los stacks de forma ordenada según sus dependencias
   cdk deploy --all
   ```

## 🧹 Limpieza (Destrucción Efímera)

Dado que todos los recursos tienen configurada la política `RemovalPolicy.DESTROY`, la limpieza es total y automática. Para evitar cobros, destruye la infraestructura cuando termines:

```bash
cdk destroy --all
```

## 📖 Documentación Adicional

Por favor revisa la carpeta [`docs/`](./docs) para guías específicas de integración:
- [Cómo conectar los Microservicios a esta Infraestructura](./docs/microservices_connection.md)
