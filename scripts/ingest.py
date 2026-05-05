import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

load_dotenv()

def main():
    print("Starting local data ingestion...")

    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_name = os.getenv("PINECONE_INDEX_NAME")

    documents = []
    
    resume_items = [
        {
            "file": "data/raw/resume/summary.md",
            "metadata": {
                "type": "resume",
                "section": "summary",
                "name": "Summary",
            },
        },
        {
            "file": "data/raw/resume/skills.md",
            "metadata": {
                "type": "resume",
                "section": "skills",
                "name": "Skills",
            },
        },
        {
            "file": "data/raw/resume/holiday_channel.md",
            "metadata": {
                "type": "resume",
                "section": "experience",
                "name": "Holiday Channel, LLC",
                "role": "Software Engineer Intern",
                "tech": [
                    "AWS Lambda",
                    "Amazon S3",
                    "FastAPI",
                    "Redis",
                    "PostgreSQL",
                    "Python",
                ],
            },
        },
        {
            "file": "data/raw/resume/wiz_freight.md",
            "metadata": {
                "type": "resume",
                "section": "experience",
                "name": "Wiz Freight",
                "role": "Software Development Engineer (Intern -> Full-time)",
                "tech": [
                    "Go",
                    "PostgreSQL",
                    "gRPC",
                    "Protobuf",
                    "Gin",
                    "GORM",
                    "SSE",
                    "AWS SQS",
                ],
            },
        },
        {
            "file": "data/raw/resume/highradius.md",
            "metadata": {
                "type": "resume",
                "section": "experience",
                "name": "HighRadius",
                "role": "Data Analyst Intern",
                "tech": [
                    "Python",
                    "Pandas",
                    "NumPy",
                    "Scikit-learn",
                    "Logistic Regression",
                    "Decision Trees",
                ],
            },
        },
        {
            "file": "data/raw/resume/cognizant.md",
            "metadata": {
                "type": "resume",
                "section": "experience",
                "name": "Cognizant",
                "role": "Programmer Analyst Intern",
                "tech": [
                    "Data Analysis",
                    "Reporting",
                    "Process Optimization",
                ],
            },
        },
        {
            "file": "data/raw/resume/prograd.md",
            "metadata": {
                "type": "resume",
                "section": "experience",
                "name": "Prograd",
                "role": "Developer Intern",
                "tech": [
                    "Code Review",
                    "Debugging",
                    "Performance Optimization",
                ],
            },
        },
    ]

    for item in resume_items:
        if os.path.exists(item["file"]):
            print(f"Loading resume section: {item['metadata']['name']}...")
            loader = TextLoader(item["file"])
            resume_docs = loader.load()

            for doc in resume_docs:
                doc.metadata.update(item["metadata"])

            documents.extend(resume_docs)
        else:
            print(f"Warning: Resume file {item['file']} not found.")


    projects = [
        {
            "file": "data/raw/projects/Bird_Flock_Simulation_with_Spark.md",
            "metadata": {
                "type": "project",
                "name": "Bird Flock Simulation with Spark",
                "tech": ["Python", "Pyspark", "Multiprocessing","Pytorch"]
            }
        },
        {
            "file": "data/raw/projects/CPP_Chat_Application.md",
            "metadata": {
                "type": "project",
                "name": "CPP Chat Application",
                "tech": ["C++", "Qt", "Network Programming","Linux"]
            }
        },
        {
            "file": "data/raw/projects/Expensely.md",
            "metadata": {
                "type": "project",
                "name": "Expensely",
                "tech": ["Java", "Spring Boot", "PostgreSQL", "Docker", "Kubernetes","AWS","Next.js","React","Tailwind CSS","WebSocket","GitHub Actions"]
            }
        },
        {
            "file": "data/raw/projects/GATEKEEPER.md",
            "metadata": {
                "type": "project",
                "name": "Gatekeeper",
                "tech": ["Node.js", "PostgreSQL", "Docker","AWS","Next.js","React","Tailwind CSS","GitHub Actions"]
            }
        },
        {
            "file": "data/raw/projects/Job_Tracker.md",
            "metadata": {
                "type": "project",
                "name": "Job Tracker",
                "tech": ["Golang", "PostgreSQL", "Docker","Next.js","React","Tailwind CSS","GitHub Actions","SSE"]
            }
        },
        {
            "file": "data/raw/projects/Neural_Networks_Project.md",
            "metadata": {
                "type": "project",
                "name": "Neural Networks Project",
                "tech": ["Python", "PyTorch", "NumPy", "Pandas", "Matplotlib", "Scikit-learn"]
            }
        },
        {
            "file": "data/raw/projects/Reinforcement_Learning_Project.md",
            "metadata": {
                "type": "project",
                "name": "Reinforcement Learning Project",
                "tech": ["Python", "PyTorch", "NumPy", "Pandas", "Matplotlib", "Scikit-learn","Gymnasium","Optuna","OpenCV","Pillow"]
            }
        },
        {
            "file": "data/raw/projects/Talky_Space.md",
            "metadata": {
                "type": "project",
                "name": "Talky Space",
                "tech": ["Golang", "React", "Docker", "WebSocket", "PostgreSQL","Next.js","Tailwind CSS","GitHub Actions"]
            }
        },
        {
            "file": "data/raw/projects/TODO_App.md",
            "metadata": {
                "type": "project",
                "name": "TODO App",
                "tech": ["React", "Vite", "ESLint", "Github Pages"]
            }
        },
        {
            "file": "data/raw/projects/University_Portal.md",
            "metadata": {
                "type": "project",
                "name": "University Portal",
                "tech": ["Golang", "HTML", "PostgreSQL", "Docker", "AWS","CSS","JavaScript","GitHub Actions"]
            }
        },
        {
            "file": "data/raw/projects/Weather_App.md",
            "metadata": {
                "type": "project",
                "name": "Weather App",
                "tech": ["React", "Node.js", "AWS Lambda", "OpenWeatherMap API"]
            }
        }
    ]

    for proj in projects:
        if os.path.exists(proj["file"]):
            print(f"Loading {proj['metadata']['name']}...")
            loader = TextLoader(proj["file"])
            proj_docs = loader.load()

            for doc in proj_docs:
                    # Update the existing metadata (which already contains 'source')
                    doc.metadata.update(proj["metadata"])
                    
            documents.extend(proj_docs)
        else:
            print(f"Warning: Project file {proj['file']} not found.")

    if not documents:
        print("No documents loaded. Exiting.")
        return

    # 3. Chunk the Documents
    # We split the text into smaller pieces so the LLM can digest specific context
    print(f"Loaded {len(documents)} document pages/files. Chunking...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks.")

    # 4. Generate Embeddings and Upload to Pinecone
    print("Generating embeddings and pushing to Pinecone...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=int(os.getenv("PINECONE_DIMENSIONS")))
    
    # This automatically embeds the chunks and upserts them to your Pinecone index
    PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=index_name
    )

    print("✅ Ingestion complete! Your Pinecone database is fully populated.")

if __name__ == "__main__":
    main()