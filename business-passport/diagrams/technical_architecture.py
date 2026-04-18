"""Technical architecture diagram for Business Passport."""
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.storage import S3
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import StepFunctions, SNS, Eventbridge
from diagrams.aws.network import APIGateway
from diagrams.aws.security import SecretsManager
from diagrams.aws.management import Cloudwatch
from diagrams.gcp.compute import Run
from diagrams.gcp.ml import AIHub
from diagrams.onprem.client import User

graph_attr = {
    "fontsize": "13",
    "bgcolor": "white",
    "pad": "0.6",
    "splines": "curved",
    "nodesep": "0.8",
    "ranksep": "1.0",
    "dpi": "150",
}

for fmt in ("png", "svg"):
    with Diagram(
        "Business Passport – Technical Architecture",
        filename="diagrams/technical_architecture",
        outformat=fmt,
        show=False,
        direction="TB",
        graph_attr=graph_attr,
    ):
        user = User("Client")

        with Cluster("AWS"):
            apigw = APIGateway("API Gateway")
            eb = Eventbridge("EventBridge")
            sfn = StepFunctions("Step Functions")
            sns = SNS("SNS")
            cw = Cloudwatch("CloudWatch")
            s3 = S3("S3 Bucket")
            ddb = Dynamodb("DynamoDB")
            sm = SecretsManager("Secrets Manager")

            with Cluster("Lambda Functions"):
                fn_ingest = Lambda("ingest")
                fn_presign = Lambda("presign")
                fn_gcp_proxy = Lambda("gcp_proxy")
                fn_scrape = Lambda("scrape")
                fn_vertex_proxy = Lambda("vertex_proxy")
                fn_score = Lambda("score")
                fn_passport = Lambda("passport")
                fn_notify = Lambda("notify")

        with Cluster("GCP"):
            cloud_run = Run("Cloud Run\n(Whisper + Qwen-VL)")
            vertex = AIHub("Vertex AI\n(Gemma 2)")

        user >> apigw >> fn_ingest >> [s3, ddb]
        s3 >> eb >> sfn
        sfn >> fn_presign >> sfn
        sfn >> [fn_gcp_proxy, fn_scrape]
        sfn >> fn_vertex_proxy >> sfn
        sfn >> fn_score >> sfn
        sfn >> fn_passport >> sfn
        sfn >> fn_notify >> sns >> user
        fn_gcp_proxy >> sm
        fn_gcp_proxy >> Edge(label="HTTPS") >> cloud_run
        fn_vertex_proxy >> Edge(label="Vertex API") >> vertex
        sfn >> cw
