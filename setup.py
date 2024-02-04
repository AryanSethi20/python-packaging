from setuptools import find_packages, setup

setup(
    name='trading-jars',
    version='1.0.0',
    author='Varsha Balaji, Aryan Sethi',
    author_email='varshabalaji3@gmail.com, aryansethi20@gmail.com',
    description='File to download trading app jars',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/AryanSethi20/python-packaging',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=[
        'requests>=2.24.0',
    ],
    entry_points={
        'console_scripts': [
            'download-trading-jars=downloadTradingAppJars.py:initiate',
        ],
    },
)
