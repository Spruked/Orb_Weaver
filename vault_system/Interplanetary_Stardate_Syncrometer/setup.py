from setuptools import find_packages, setup


setup(
    name="iss-module",
    version="1.1.0",
    description="Standalone timekeeping service",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "jinja2>=3.1.2",
    ],
)
