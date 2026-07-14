from setuptools import find_packages, setup


setup(
    name="personal-memory-researcher",
    version="0.1.0",
    description="Hybrid BM25, embedding, and page-id research over personal-kb.",
    packages=find_packages(),
    python_requires=">=3.9",
)
