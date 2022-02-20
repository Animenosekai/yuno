from os import path

from setuptools import setup

with open(path.join(path.abspath(path.dirname(__file__)), 'README.md'), encoding='utf-8') as f:
    readme_description = f.read()

setup(
    name="yuno",
    packages=["yuno"],
    version="1.0",
    license="MIT",
    description="Manipulate your databases as if you never leaved Python!",
    author="Anime no Sekai",
    author_email="niichannomail@gmail.com",
    url="https://github.com/Animenosekai/yuno",
    download_url="https://github.com/Animenosekai/yuno/archive/v1.0.tar.gz",
    keywords=['python', 'yuno', 'database', 'database-management', 'mongo', 'mongodb', 'account', 'account-management', 'database-client', 'client', 'mongo-client'],
    install_requires=['pymongo>=3.11.3', 'psutil>=5.8.0', 'PyYAML>=6.0', 'typing; python_version<"3.8"'],
    classifiers=['Development Status :: 4 - Beta', 'License :: OSI Approved :: MIT License', 'Programming Language :: Python :: 3', 'Programming Language :: Python :: 3.8', 'Programming Language :: Python :: 3.9'],
    long_description=readme_description,
    long_description_content_type="text/markdown",
    include_package_data=True,
    python_requires='>=3.8, <4',
    package_data={
        'yuno': ['LICENSE'],
    },
)
