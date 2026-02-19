"""
Setup configuration for TIAS (Terra Invicta Advisory System)
"""

from setuptools import setup, find_namespace_packages

setup(
    name="tias",
    version="2.0.0",
    description="Terra Invicta Advisory System - AI-powered game advisors",
    author="Grumpy",
    python_requires=">=3.11",
    packages=find_namespace_packages(include=['src*']),  # Changed: finds packages even without __init__.py
    install_requires=[
        # No runtime dependencies - uses stdlib only
    ],
    extras_require={
        'dev': [
            'pytest>=7.4.0',
            'pytest-cov>=4.1.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'tias=src.__main__:main',
        ],
    },
    package_data={
        'resources': ['**/*'],
    },
)
