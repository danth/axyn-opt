from setuptools import setup

setup(
    name="axyn",
    version="0.0.0",
    author="Daniel Thwaites",
    author_email="danthwaites30@btinternet.com",
    packages=["axyn"],
    install_requires=[
        "discord.py >=2,<3",
        "torch >=1,<2",
        "transformers >=4,<5"
    ],
    entry_points={
        "console_scripts": [ "axyn=axyn.__main__:main" ]
    }
)
