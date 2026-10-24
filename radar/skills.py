"""The fixed list of skills Claude is allowed to pick from."""

SKILL_GROUPS = {
    "languages": [
        "Python", "JavaScript", "TypeScript", "Java", "Kotlin", "Scala", "Go",
        "Rust", "C", "C++", "C#", "Ruby", "PHP", "Swift", "Objective-C",
        "Elixir", "Erlang", "Clojure", "Haskell", "OCaml", "F#", "Dart", "R",
        "Julia", "Lua", "Perl", "Zig", "SQL", "Bash", "Solidity",
    ],
    "frontend": [
        "React", "Next.js", "Vue", "Angular", "Svelte", "HTML/CSS",
        "Tailwind CSS", "Redux", "WebAssembly", "WebGL/Three.js",
    ],
    "backend": [
        "Node.js", "Django", "Flask", "FastAPI", "Ruby on Rails", "Spring",
        ".NET", "Laravel", "Express", "NestJS", "Phoenix", "GraphQL", "gRPC",
        "REST APIs", "Microservices", "Distributed systems",
    ],
    "mobile": [
        "iOS", "Android", "React Native", "Flutter", "SwiftUI", "Jetpack Compose",
    ],
    "databases": [
        "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Elasticsearch",
        "Cassandra", "DynamoDB", "ClickHouse", "Snowflake", "BigQuery",
        "Databricks", "Vector databases",
    ],
    "data_engineering": [
        "Kafka", "RabbitMQ", "Spark", "Airflow", "dbt", "Flink", "Pandas",
        "Ray", "ETL pipelines", "Data warehousing", "Data analysis",
    ],
    "ai_ml": [
        "Machine learning", "Deep learning", "LLMs", "RAG", "AI agents",
        "Fine-tuning", "NLP", "Computer vision", "Reinforcement learning",
        "Recommendation systems", "Speech and audio ML", "MLOps", "PyTorch",
        "TensorFlow", "JAX", "scikit-learn", "Hugging Face", "CUDA",
        "Model evaluation", "Statistics",
    ],
    "cloud_infra": [
        "AWS", "GCP", "Azure", "Kubernetes", "Docker", "Terraform", "Linux",
        "Serverless", "CI/CD", "GitHub Actions", "Ansible", "Helm", "Nginx",
        "Cloudflare", "Observability", "SRE", "Networking", "Performance optimization",
    ],
    "security": [
        "Application security", "Cloud security", "Cryptography",
        "Penetration testing", "Identity and auth", "Compliance",
    ],
    "systems_hardware": [
        "Embedded systems", "Firmware", "FPGA", "Verilog/VHDL", "RTOS",
        "Robotics", "ROS", "Compilers", "Operating systems", "Computer graphics",
        "Simulation", "PCB design", "Game engines",
    ],
    "web3": [
        "Blockchain", "Smart contracts",
    ],
    "product_design": [
        "Product management", "UX/UI design", "Figma", "Technical writing",
        "Developer relations", "Sales",
    ],
}

# One flat list: ["Python", "JavaScript", ...]
SKILLS = [skill for group in SKILL_GROUPS.values() for skill in group]

# Stop the program right away if a skill was listed twice.
assert len(SKILLS) == len(set(SKILLS)), "duplicate skill in SKILL_GROUPS"
