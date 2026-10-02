"""Demo persona CV and sample postings. Recorded agent responses for each posting live in
app/demo/fixtures/<id>.json (regenerate with scripts/record_demo.py after editing these)."""

from dataclasses import dataclass

DEMO_CV = """Sam Rivera
Software Engineer · Manchester, UK · sam.rivera@example.com

Summary
Backend-leaning full-stack engineer with five years of experience building payment and
logistics products in Python and TypeScript.

Experience

Senior Software Engineer, Ledgerly (2022 - present)
Lead engineer on the invoicing platform used by 40,000 small businesses.
Designed and built REST APIs in Python with FastAPI and SQLAlchemy, handling 3 million requests a day.
Owned the PostgreSQL data model; partitioned the invoices table and tuned queries, cutting p95 API latency from 900ms to 180ms.
Introduced event-driven processing with Redis streams for payment reconciliation.
Set up pytest suites, contract tests and GitHub Actions pipelines; deploys went from weekly to daily.
Mentored three junior engineers and ran the backend guild's fortnightly design reviews.

Software Engineer, Parcelpoint (2019 - 2022)
Built React and TypeScript dashboards for warehouse operators, used by 600 staff daily.
Developed Node.js microservices for parcel tracking, deployed on AWS ECS with Terraform.
Added observability with Prometheus and Grafana, reducing incident detection time by half.
Worked with product designers to run usability tests and ship accessibility fixes (WCAG AA).

Projects
Open-source maintainer of a small Python library for parsing bank statement CSVs (900 GitHub stars).
Built a personal budgeting app with Next.js and Supabase.

Education
BSc Computer Science, University of Manchester (2015 - 2019), upper second-class honours.
Final-year project: anomaly detection on card transactions using scikit-learn.

Skills
Python, FastAPI, SQLAlchemy, PostgreSQL, Redis, pytest, TypeScript, React, Node.js, AWS (ECS, S3, RDS),
Terraform, Docker, GitHub Actions, Prometheus, Grafana
"""


@dataclass(frozen=True)
class SamplePosting:
    id: str
    title: str
    company: str
    blurb: str
    posting: str


SAMPLE_POSTINGS = [
    SamplePosting(
        id="senior-backend-fintech",
        title="Senior Backend Engineer",
        company="Northwind Pay",
        blurb="Payments API team · likely a strong fit",
        posting="""Senior Backend Engineer
Company: Northwind Pay · London or remote (UK)

Northwind Pay moves money for 20,000 online merchants. We're growing the Payments API team
and need a senior engineer to help us scale reliably.

What you'll do
- Design, build and operate high-throughput payment APIs
- Own data models and performance for our PostgreSQL clusters
- Improve our testing and delivery pipeline
- Mentor engineers and lead technical design discussions

Requirements:
- 5+ years of professional backend development
- Strong Python, ideally with FastAPI or Django
- Deep PostgreSQL experience, including query optimisation
- Experience with event-driven or asynchronous architectures
- Solid automated testing and CI/CD practices

Nice to have:
- Payments, invoicing or fintech domain experience
- Infrastructure as code (Terraform)
- Experience mentoring or leading engineers
""",
    ),
    SamplePosting(
        id="ml-platform",
        title="Machine Learning Platform Engineer",
        company="Helix Health",
        blurb="ML infrastructure · a stretch role",
        posting="""Machine Learning Platform Engineer
Company: Helix Health · Cambridge (hybrid)

Helix Health builds clinical decision-support tools. Our ML platform team gives researchers
the infrastructure to train, evaluate and deploy models safely.

Responsibilities
- Build and maintain our model training and serving platform
- Run GPU workloads on Kubernetes
- Create tooling for experiment tracking and model evaluation
- Partner with researchers to productionise models

Requirements:
- 3+ years building production ML systems or ML infrastructure
- Python and the PyData stack (pandas, NumPy, scikit-learn)
- Deep learning frameworks such as PyTorch
- Kubernetes and containerised GPU workloads
- MLOps tooling (MLflow, Kubeflow or similar)

Nice to have:
- Healthcare or regulated-industry experience
- AWS or GCP
- Strong software engineering fundamentals: testing, CI/CD
""",
    ),
    SamplePosting(
        id="frontend-product",
        title="Product Engineer (Frontend)",
        company="Lumen Studio",
        blurb="React product team · a good fit",
        posting="""Product Engineer (Frontend)
Company: Lumen Studio · Manchester (hybrid)

Lumen Studio makes scheduling software for independent clinics. We're a small product team
where engineers talk to customers and own features end to end.

You will
- Build polished, accessible interfaces in React and TypeScript
- Work closely with design and customers to shape features
- Contribute to our Node.js API when features need it

Requirements:
- 3+ years building web applications with React and TypeScript
- Strong eye for UX and accessibility (WCAG)
- Experience working directly with designers and users
- Comfortable with a Node.js backend

Nice to have:
- Next.js
- Design systems or component libraries
- Experience in a small startup team
""",
    ),
]


# Revision feedback with recorded responses. Must match the suggestion chips in the
# frontend's review workspace (REVISE_CHIPS in AnalyzePage.tsx).
REVISION_SUGGESTIONS = ["Make it shorter", "More confident tone", "Less formal"]


def normalise_posting(text: str) -> str:
    return " ".join(text.split())
