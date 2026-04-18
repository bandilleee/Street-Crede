"""High-level (non-technical) architecture diagram for Business Passport."""
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import Lambda
from diagrams.aws.storage import S3
from diagrams.aws.database import Dynamodb
from diagrams.aws.integration import StepFunctions, SNS
from diagrams.aws.network import APIGateway
from diagrams.gcp.compute import Run
from diagrams.gcp.ml import AIHub
from diagrams.onprem.client import User

graph_attr = {
    "fontsize": "15",
    "bgcolor": "#f9f9f9",
    "pad": "0.8",
    "splines": "curved",
    "nodesep": "1.2",
    "ranksep": "1.4",
    "dpi": "150",
}

for fmt in ("png", "svg"):
    with Diagram(
        "Business Passport – How It Works",
        filename="diagrams/highlevel_architecture",
        outformat=fmt,
        show=False,
        direction="LR",
        graph_attr=graph_attr,
    ):
        applicant = User("Business Owner\n(Applicant)")

        with Cluster("① Submit"):
            api = APIGateway("Secure Entry Point")
            receive = Lambda("Register Job")
            store = S3("Document Storage")
            db = Dynamodb("Job Tracker")

        with Cluster("② Orchestrate"):
            pipeline = StepFunctions("Processing Pipeline")

        with Cluster("③ AI Analysis (GCP)"):
            ai_gw = Run("Audio & Image AI")
            llm = AIHub("Language Model\n(Gemma 2)")

        with Cluster("④ Score & Report"):
            score = Lambda("Scoring Engine")
            passport = Lambda("Passport Generator")

        with Cluster("⑤ Deliver"):
            notify = SNS("Notifications")

        result = User("Receives Passport")

        applicant >> Edge(label="submits docs") >> api >> receive
        receive >> [store, db]
        store >> Edge(label="auto-triggers") >> pipeline
        pipeline >> Edge(label="audio & images") >> ai_gw
        ai_gw >> Edge(label="synthesise") >> llm >> pipeline
        pipeline >> score >> passport >> notify
        notify >> Edge(label="SMS / Email") >> result
