from setuptools import setup, find_packages

setup(
    name="ktvgenerate",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "yt-dlp",
        "sqlmodel",
        "ffmpeg-python",
        "torch",
    ],
    entry_points={
        "console_scripts": [
            "ktvgenerate = app.cli.ktvgenerate:main"
        ]
    },
    include_package_data=True,
    python_requires=">=3.8",
)