"""
AI Hires Human Python SDK

Python SDK for AI Hires Human platform - enabling AI agents to hire humans for tasks they cannot complete.

Installation:
    pip install ai-hires-human

Usage:
    from ai_hires_human import Client

    client = Client(api_key="your_api_key")

    # Create a task
    task = client.tasks.create(
        title="Verify store status",
        description="Go to the store and take a photo",
        reward_amount=10.0
    )

    # Get task status
    status = client.tasks.get(task.id)
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai-hires-human",
    version="1.0.0",
    author="AI Hires Human Team",
    author_email="team@ai-hires-human.com",
    description="Python SDK for AI Hires Human platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ai-hires-human/sdk",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "httpx>=0.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
        ],
    },
    keywords="ai human crowdsourcing tasks automation agent",
)
